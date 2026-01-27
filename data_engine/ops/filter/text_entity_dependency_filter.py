import numpy as np

from data_engine.utils.constant import Fields, StatsKeys
from data_engine.utils.mm_utils import remove_special_tokens
from data_engine.utils.model_utils import get_model, prepare_model

from ..base_op import OPERATORS, Filter, Sample, Param, DataType

OP_NAME = 'text_entity_dependency_filter'


@OPERATORS.register_module(OP_NAME)
class TextEntityDependencyFilter(Filter):
    """
    Identify the entities in the text which are independent with other token,
    and filter them. The text containing no entities will be omitted.
    """

    def __init__(self,
                 lang: str = 'en',
                 min_dependency_num: int = 1,
                 any_or_all: str = 'all',
                 *args,
                 **kwargs):
        """
        Initialization method.

        :param lang: language of the text in the samples. 'en' for detection of
            entities in English and 'zh' for detection of entities in Chinese.
        :param mini_dependency_num: The min token number in the filtering.
            Objects is independent if their number of edges in the dependency
            tree is below this parameter.
        :param any_or_all: keep this sample with 'any' or 'all' strategy.
            'any': keep this sample if any objet is dependent. 'all': keep this
            sample only if all images are dependent.
        """
        super().__init__(*args, **kwargs)

        if lang not in ['en', 'zh']:
            raise ValueError(
                f'Language [{lang}] is not supported in entities detection.'
                f'Can only be one of ["en", "zh"].')
        self.lang = lang
        
        # Enable detailed logging for this filter
        self.enable_detailed_logging = True
        
        self.model_key = prepare_model(model_type='spacy', lang=lang)
        self.entity_poss = ['NOUN', 'PROPN', 'PRON']
        self.entity_tags = ['NN', 'NR', 'PN', 'NNS', 'NNP', 'NNPS', 'PRP']
        self.min_dependency_num = min_dependency_num
        if any_or_all not in ['any', 'all']:
            raise ValueError(f'Keep strategy [{any_or_all}] is not supported. '
                             f'Can only be one of ["any", "all"].')
        self.any = (any_or_all == 'any')

    def compute_stats(self, sample, context=False):
        # check if it's computed already
        if StatsKeys.num_dependency_edges in sample[Fields.stats]:
            return sample

        text = remove_special_tokens(sample[self.text_key])

        # identify entities
        model = get_model(self.model_key)
        doc = model(text)
        entity_to_dependency_nums = {}
        for token in doc:
            if token.pos_ in self.entity_poss \
             and token.tag_ in self.entity_tags:
                entity_to_dependency_nums[token] = 0

        # count the edges of each entity in dependency tree
        for obj in entity_to_dependency_nums:
            if obj.dep_ != 'ROOT':
                entity_to_dependency_nums[obj] += 1
        for token in doc:
            # the punctation mark such as ',', '.'
            if token.pos_ == 'PUNCT':
                continue

            if token.head in entity_to_dependency_nums.keys(
            ) and token.dep_ != 'ROOT':
                entity_to_dependency_nums[token.head] += 1

        sample[Fields.stats][StatsKeys.num_dependency_edges] = [
            n for _, n in entity_to_dependency_nums.items()
        ]
        
        # Determine filter result and reason for detailed logging
        num_dependency_edges = sample[Fields.stats][StatsKeys.num_dependency_edges]
        keep_bools = np.array([
            self.min_dependency_num <= num_edge
            for num_edge in num_dependency_edges
        ])
        
        # omit the samples without entity
        if len(keep_bools) <= 0:
            keep = False
            reason = 'no_entities'
        else:
            # different strategies
            if self.any:
                keep = keep_bools.any()
            else:
                keep = keep_bools.all()
            reason = 'kept' if keep else 'dependency_too_low'
        
        # Store detailed information for logging
        sample[Fields.stats][f'{StatsKeys.num_dependency_edges}_detail'] = {
            'num_entities': len(num_dependency_edges),
            'dependency_edges': str(num_dependency_edges),
            'keep': keep,
            'reason': reason,
            'strategy': 'any' if self.any else 'all'
        }

        return sample

    def process(self, sample):
        num_dependency_edges = sample[Fields.stats][
            StatsKeys.num_dependency_edges]
        keep_bools = np.array([
            self.min_dependency_num <= num_edge
            for num_edge in num_dependency_edges
        ])
        # omit the samples without entity
        if len(keep_bools) <= 0:
            return False

        # different strategies
        if self.any:
            return keep_bools.any()
        else:
            return keep_bools.all()
        
    @classmethod
    @property
    def description(cls):
        return """
    Identify the entities in the text which are independent with other token,
    and filter them. The text containing no entities will be omitted.
    """

    @classmethod
    @property
    def sample(cls):
        return Sample("上上下下左左右右", "")

    @classmethod
    @property
    def init_params(cls):
        return [
            Param("lang", DataType.STRING, {
                "zh": "zh",
                "en": "en",
            }, "zh"),
            Param("min_dependency_num", DataType.INTEGER, None, 1),
            Param("any_or_all", DataType.STRING, {
                "all": "all",
                "any": "any",
            }, "all"),
        ]