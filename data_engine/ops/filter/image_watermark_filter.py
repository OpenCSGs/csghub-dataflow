import numpy as np
from jsonargparse.typing import ClosedUnitInterval

from data_engine.utils.availability_utils import AvailabilityChecking
from data_engine.utils.constant import Fields, StatsKeys
from data_engine.utils.mm_utils import load_data_with_context, load_image
from data_engine.utils.model_utils import get_model, prepare_model

from ..base_op import OPERATORS, Filter
from ..op_fusion import LOADED_IMAGES

OP_NAME = 'image_watermark_filter'

with AvailabilityChecking(['torch', 'transformers'], OP_NAME):
    import torch
    import transformers  # noqa: F401

    # avoid hanging when calling watermark detection in multiprocessing
    torch.set_num_threads(1)


@OPERATORS.register_module(OP_NAME)
@LOADED_IMAGES.register_module(OP_NAME)
class ImageWatermarkFilter(Filter):
    """
        Filter to keep samples whose images have no watermark with high
        probability.
    """

    _accelerator = 'cuda'

    def __init__(self,
                 hf_watermark_model='amrul-hzz/watermark_detector',
                 trust_remote_code=False,
                 prob_threshold: ClosedUnitInterval = 0.8,
                 any_or_all: str = 'any',
                 *args,
                 **kwargs):
        """
        Initialization method.

        :param hf_watermark_model: watermark detection model name on
            huggingface.
        :param prob_threshold: the predicted watermark probability threshold
            for samples. range from 0 to 1. Samples with watermark probability
            less than this threshold will be kept.
        :param any_or_all: keep this sample with 'any' or 'all' strategy of
            all images. 'any': keep this sample if any images meet the
            condition. 'all': keep this sample only if all images meet the
            condition.
        :param args: extra args
        :param kwargs: extra args
        """
        super().__init__(*args, **kwargs)
        self.prob_threshold = prob_threshold
        if any_or_all not in ['any', 'all']:
            raise ValueError(f'Keep strategy [{any_or_all}] is not supported. '
                             f'Can only be one of ["any", "all"].')
        self.any = (any_or_all == 'any')
        self.model_key = prepare_model(
            model_type='huggingface',
            pretrained_model_name_or_path=hf_watermark_model,
            trust_remote_code=trust_remote_code)

    def compute_stats(self, sample, rank=None, context=False):
        # check if it's computed already
        if StatsKeys.image_watermark_prob in sample[Fields.stats]:
            return sample

        # there is no image in this sample
        if self.image_key not in sample or not sample[self.image_key]:
            sample[Fields.stats][StatsKeys.image_watermark_prob] = np.array(
                [], dtype=np.float64)
            return sample

        # load images
        loaded_image_keys = sample[self.image_key]
        sample, images = load_data_with_context(sample, context,
                                                loaded_image_keys, load_image)

        model, processor = get_model(self.model_key, rank, self.use_cuda())

        images = [images[key] for key in images]
        inputs = processor(images=images, return_tensors='pt').to(model.device)
        outputs = model(**inputs)
        logits = outputs.logits
        watermark_probs = [
            float(probs[1]) for probs in torch.softmax(logits, dim=-1)
        ]

        sample[Fields.stats][StatsKeys.image_watermark_prob] = watermark_probs

        return sample

    def process(self, sample, rank=None):
        itm_probs = sample[Fields.stats][StatsKeys.image_watermark_prob]
        if len(itm_probs) <= 0:
            return True

        keep_bools = np.array(
            [itm_prob < self.prob_threshold for itm_prob in itm_probs])

        # different strategies
        if self.any:
            return keep_bools.any()
        else:
            return keep_bools.all()
