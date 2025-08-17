from copy import deepcopy

from loguru import logger

from data_engine.utils.availability_utils import AvailabilityChecking
from data_engine.utils.logger_utils import HiddenPrints

from ..base_op import OPERATORS, Mapper, Sample, Param, DataType

OP_NAME = 'nlpcda_zh_mapper'

with AvailabilityChecking(['nlpcda'], OP_NAME), HiddenPrints():
    import nlpcda


@OPERATORS.register_module(OP_NAME)
class NlpcdaZhMapper(Mapper):
    """Mapper to simply augment samples in Chinese based on nlpcda library."""

    _batched_op = True

    def __init__(self,
                 sequential: bool = False,
                 aug_num: int = 1,
                 keep_original_sample: bool = True,
                 replace_similar_word: bool = False,
                 replace_homophone_char: bool = False,
                 delete_random_char: bool = False,
                 swap_random_char: bool = False,
                 replace_equivalent_num: bool = False,
                 *args,
                 **kwargs):

        super().__init__(*args, **kwargs)

        self.aug_num = aug_num
        if aug_num >= 10:
            logger.warning(f'Relatively large augmentation number [{aug_num}]'
                           f' might generate large number of new samples and '
                           f'requires more memory and disk space.')
        self.sequential = sequential
        self.keep_original_sample = keep_original_sample

        # hide the redundant outputs from nlpcda library
        with HiddenPrints():
            import warnings
            warnings.filterwarnings('ignore')

            self.aug_pipeline = []
            # sample level

            # word level
            if replace_similar_word:
                # the first sample of augmented sample list is the same as the
                # original sample, so we need generate one more augmented
                # sample to get the expected number of augmented samples. Same
                # below
                create_num = (self.aug_num + 1) \
                    if not self.sequential or len(self.aug_pipeline) == 0 \
                    else 2
                self.aug_pipeline.append(
                    nlpcda.Similarword(create_num=create_num))

            # char level
            if replace_homophone_char:
                create_num = (self.aug_num + 1) \
                    if not self.sequential or len(self.aug_pipeline) == 0 \
                    else 2
                self.aug_pipeline.append(
                    nlpcda.Homophone(create_num=create_num))
            if delete_random_char:
                create_num = (self.aug_num + 1) \
                    if not self.sequential or len(self.aug_pipeline) == 0 \
                    else 2
                self.aug_pipeline.append(
                    nlpcda.RandomDeleteChar(create_num=create_num))
            if swap_random_char:
                create_num = (self.aug_num + 1) \
                    if not self.sequential or len(self.aug_pipeline) == 0 \
                    else 2
                # only use char_gram=1 for relatively minor changes
                self.aug_pipeline.append(
                    nlpcda.CharPositionExchange(create_num=create_num,
                                                char_gram=1))

            # only for numbers now
            if replace_equivalent_num:
                create_num = (self.aug_num + 1) \
                    if not self.sequential or len(self.aug_pipeline) == 0 \
                    else 2
                self.aug_pipeline.append(
                    nlpcda.EquivalentChar(create_num=create_num))

    def process(self, samples):
        # no augmentation methods are opened
        if len(self.aug_pipeline) == 0:
            if self.keep_original_sample:
                return samples
            else:
                return {key: [] for key in samples}

        texts_to_aug = samples[self.text_key]
        res_samples = deepcopy(samples)

        # get augmented texts
        if self.sequential:
            aug_texts = texts_to_aug
            for aug_method in self.aug_pipeline:
                results = []
                for text in aug_texts:
                    # aug and skip the original text
                    result = aug_method.replace(text)
                    results += result[1:] if len(result) > 1 else result
                aug_texts = results[:]
            if len(aug_texts) == 1 and aug_texts[0] == texts_to_aug[0]:
                aug_texts = []
        else:
            # apply each aug method to generate several augmented texts
            aug_texts = []
            for aug_method in self.aug_pipeline:
                aug_texts += aug_method.replace(texts_to_aug[0])[1:]

        # add augmented samples to the batch with other replicate fields
        if self.keep_original_sample:
            res_samples[self.text_key] += aug_texts
        else:
            res_samples[self.text_key] = aug_texts
        # add other replicate fields
        for key in res_samples:
            if key != self.text_key:
                res_samples[key] = res_samples[key] * \
                                   len(res_samples[self.text_key])
        return res_samples

    @classmethod
    @property
    def description(cls):
        return """Mapper to simply augment samples in Chinese based on nlpcda library."""

    @classmethod
    @property
    def sample(cls):
        return Sample('这里一共有5种不同的数据增强方法',
                    '这里一共有伍种不同的数据增强方法')

    @classmethod
    @property
    def init_params(cls):
        return [
            Param("replace_similar_word", DataType.BOOLEAN,
                None, False),
            Param("swap_random_word", DataType.BOOLEAN,
                None, False),
            Param("delete_random_char", DataType.BOOLEAN,
                None, False),
            Param("swap_random_char", DataType.BOOLEAN,
                None, False),
            Param("replace_equivalent_num", DataType.BOOLEAN,
                None, False),
        ]