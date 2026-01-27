# Some code here has been modified from:
# https://huggingface.co/spaces/huggingface/text-data-filtering
# --------------------------------------------------------

from jsonargparse.typing import ClosedUnitInterval, List

from data_engine.utils.availability_utils import AvailabilityChecking
from data_engine.utils.constant import Fields, InterVars, StatsKeys
from data_engine.utils.model_utils import get_model, prepare_model

from ...utils.asset_utils import ASSET_DIR, load_words_asset
from ..base_op import OPERATORS, Filter, Sample, Param, DataType
from ..common import (SPECIAL_CHARACTERS, get_words_from_document,
                      words_refinement)
from ..op_fusion import INTER_WORDS
from loguru import logger
import os
from data_celery.mongo_tools.tools import (
    insert_pipline_job_run_task_log_info,
    insert_pipline_job_run_task_log_warning,
    insert_pipline_job_run_task_log_error
)

OP_NAME = 'flagged_words_filter'

with AvailabilityChecking(['sentencepiece'], OP_NAME):
    import sentencepiece  # noqa: F401


@OPERATORS.register_module(OP_NAME)
@INTER_WORDS.register_module(OP_NAME)
class FlaggedWordFilter(Filter):
    """Filter to keep samples with flagged-word ratio less than a specific max
    value."""

    def __init__(self,
                 lang: str = 'en',
                 tokenization: bool = False,
                 max_ratio: ClosedUnitInterval = 0.045,
                 flagged_words_dir: str = ASSET_DIR,
                 use_words_aug: bool = False,
                 words_aug_group_sizes: List = [2],
                 words_aug_join_char: str = '',
                 *args,
                 **kwargs):
        """
        Initialization method.

        :param lang: Consider flagged words in what language. If lang ==
            "all", we will adopt the one merged from all the available
            languages
        :param tokenization: Whether to use model to tokenize documents
        :param max_ratio: The max filter ratio in this op.
        :param flagged_words_dir: The directory storing the
            flagged_words file(s) whose name includes "flagged_words"
            and in json format
        :param use_words_aug: Whether to augment words, especially for
            Chinese and Vietnamese
        :param words_aug_group_sizes: The group size of words to augment
        :param words_aug_join_char: The join char between words to
            augment
        :param args: extra args
        :param kwargs: extra args
        """
        super().__init__(*args, **kwargs)
        self.lang = lang
        self.max_ratio = max_ratio
        self.use_words_aug = use_words_aug
        self.words_aug_group_sizes = words_aug_group_sizes
        self.words_aug_join_char = words_aug_join_char
        self.model_key = None
        
        # Enable detailed logging for this filter
        self.enable_detailed_logging = True

        # Log flagged_words_filter initialization
        msg = f"[flagged_words_filter] Initializing with lang='{lang}', tokenization={tokenization}"
        logger.info(msg)
        insert_pipline_job_run_task_log_info(self.job_uid, msg, operator_name=OP_NAME, operator_index=self.pipline_index)
        
        msg = f"[flagged_words_filter] flagged_words_dir: {flagged_words_dir}"
        logger.info(msg)
        insert_pipline_job_run_task_log_info(self.job_uid, msg, operator_name=OP_NAME, operator_index=self.pipline_index)
        
        # Check if flagged_words file exists before loading
        expected_file = os.path.join(flagged_words_dir, 'flagged_words.json')
        if os.path.exists(expected_file):
            msg = f"[flagged_words_filter] ✓ Found local flagged_words.json at: {expected_file}"
            logger.info(msg)
            insert_pipline_job_run_task_log_info(self.job_uid, msg, operator_name=OP_NAME, operator_index=self.pipline_index)
        else:
            msg = f"[flagged_words_filter] ✗ Local flagged_words.json NOT found at: {expected_file}, will attempt download"
            logger.warning(msg)
            insert_pipline_job_run_task_log_warning(self.job_uid, msg, operator_name=OP_NAME, operator_index=self.pipline_index)
        
        # Load flagged words
        msg = "[flagged_words_filter] Loading flagged words..."
        logger.info(msg)
        insert_pipline_job_run_task_log_info(self.job_uid, msg, operator_name=OP_NAME, operator_index=self.pipline_index)
        
        self.FLAGGED_WORDS = load_words_asset(words_dir=flagged_words_dir,
                                              words_type='flagged_words')
        
        total_words = sum(len(words) for words in self.FLAGGED_WORDS.values())
        msg = f"[flagged_words_filter] ✓ Successfully loaded flagged_words: {len(self.FLAGGED_WORDS)} languages, {total_words} total words"
        logger.info(msg)
        insert_pipline_job_run_task_log_info(self.job_uid, msg, operator_name=OP_NAME, operator_index=self.pipline_index)

        if 'all' not in self.FLAGGED_WORDS:
            self.FLAGGED_WORDS['all'] = [
                val for vals in self.FLAGGED_WORDS.values() for val in vals
            ]
        
        if tokenization:
            msg = f"[flagged_words_filter] Tokenization enabled, preparing sentencepiece model for lang='{lang}'"
            logger.info(msg)
            insert_pipline_job_run_task_log_info(self.job_uid, msg, operator_name=OP_NAME, operator_index=self.pipline_index)
            
            msg = f"[flagged_words_filter] Expected model file: {lang}.sp.model"
            logger.info(msg)
            insert_pipline_job_run_task_log_info(self.job_uid, msg, operator_name=OP_NAME, operator_index=self.pipline_index)
            
            self.model_key = prepare_model(model_type='sentencepiece',
                                           lang=lang)
            msg = f"[flagged_words_filter] ✓ Successfully prepared sentencepiece model"
            logger.info(msg)
            insert_pipline_job_run_task_log_info(self.job_uid, msg, operator_name=OP_NAME, operator_index=self.pipline_index)

    def compute_stats(self, sample, context=False):
        # check if it's computed already
        if StatsKeys.flagged_words_ratio in sample[Fields.stats]:
            return sample

        # try to get words from context
        words_key = f'{InterVars.words}-{self.model_key}'
        if context and words_key in sample[Fields.context]:
            words = sample[Fields.context][words_key]
        else:
            tokenizer = get_model(self.model_key)
            words = get_words_from_document(
                sample[self.text_key],
                token_func=tokenizer.encode_as_pieces if tokenizer else None)
            if context:
                sample[Fields.context][words_key] = words

        # try to get refined words from context
        refined_words_key = f'{InterVars.refined_words}-True-SPECIAL_CHARS-' \
                            f'{self.use_words_aug}-' \
                            f'{self.words_aug_group_sizes}-' \
                            f'{self.words_aug_join_char}'
        if context and refined_words_key in sample[Fields.context]:
            words = sample[Fields.context][refined_words_key]
        else:
            words = words_refinement(
                words,
                lower_case=True,
                strip_chars=SPECIAL_CHARACTERS,
                use_words_aug=self.use_words_aug,
                words_aug_group_sizes=self.words_aug_group_sizes,
                words_aug_join_char=self.words_aug_join_char)
            if context:
                sample[Fields.context][refined_words_key] = words

        flagged_words_ratio = (len(
            [word
             for word in words if word in self.FLAGGED_WORDS[self.lang]]) /
                               len(words)) if len(words) != 0 else 0.0

        if flagged_words_ratio > 1.0:
            flagged_words_ratio = 1.0

        sample[Fields.stats][
            StatsKeys.flagged_words_ratio] = flagged_words_ratio
        
        # Determine filter result and reason for detailed logging
        if len(words) == 0:
            keep = False
            reason = 'empty_text'
        elif flagged_words_ratio <= self.max_ratio:
            keep = True
            reason = 'kept'
        else:
            keep = False
            reason = 'ratio_too_high'
        
        # Store detailed information for logging
        sample[Fields.stats][f'{StatsKeys.flagged_words_ratio}_detail'] = {
            'ratio': str(flagged_words_ratio),
            'keep': keep,
            'reason': reason,
            'total_words': len(words),
            'flagged_count': len([word for word in words if word in self.FLAGGED_WORDS[self.lang]])
        }
        
        return sample

    def process(self, sample):
        return sample[Fields.stats][
            StatsKeys.flagged_words_ratio] <= self.max_ratio

    @classmethod
    @property
    def description(cls):
        return """Filter to keep samples with flagged-word ratio less than a specific max
    value."""

    @classmethod
    @property
    def sample(cls):
        return Sample("基于前一步结果，除掉骂人、脏字等污秽数据和敏感词", "")

    @classmethod
    @property
    def init_params(cls):
        return [
            Param("lang", DataType.STRING, {
                "en": "en",
                "zh": "zh",
            }, "zh"),
            Param("tokenization", DataType.BOOLEAN, None, False),
            Param("max_ratio", DataType.ClosedUnitInterval, None, 0.045),
            Param("use_words_aug", DataType.BOOLEAN, None, False),
        ]