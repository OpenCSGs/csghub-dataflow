from data_engine.utils.availability_utils import AvailabilityChecking
from data_engine.utils.model_utils import get_model, prepare_model

from ..base_op import OPERATORS, Mapper, Sample, Param, DataType
from ..common import get_sentences_from_document

OP_NAME = 'sentence_split_mapper'

with AvailabilityChecking(['nltk'], OP_NAME):
    import nltk  # noqa: F401


@OPERATORS.register_module(OP_NAME)
class SentenceSplitMapper(Mapper):
    """Mapper to split text samples to sentences."""

    def __init__(self, lang: str = 'en', *args, **kwargs):
        """
        Initialization method.

        :param lang: split sentence of text in which language.
        :param args: extra args
        :param kwargs: extra args
        """
        super().__init__(*args, **kwargs)
        self.lang = lang
        self.model_key = prepare_model(model_type='nltk', lang=lang)
        
        # Enable detailed logging
        self.enable_detailed_logging = True
        self.total_samples = 0
        self.modified_samples = 0
        self.unmodified_samples = 0

    def process(self, sample):
        if getattr(self, 'enable_detailed_logging', False):
            self.total_samples += 1
        original_text = sample[self.text_key]

        nltk_model = get_model(self.model_key)
        sample[self.text_key] = get_sentences_from_document(
            sample[self.text_key],
            model_func=nltk_model.tokenize if nltk_model else None)
        
        if getattr(self, 'enable_detailed_logging', False):
            if sample[self.text_key] != original_text:
                self.modified_samples += 1
            else:
                self.unmodified_samples += 1
        return sample

    @classmethod
    @property
    def description(cls):
        return """Mapper to split text samples to sentences."""

    @classmethod
    @property
    def sample(cls):
        return Sample('Smithfield employs 3,700 people at its plant in Sioux Falls, '
                'South Dakota. The plant slaughters 19,500 pigs a day — 5 '
                'percent of U.S. pork.',
                'Smithfield employs 3,700 people at its plant in Sioux Falls, '
                'South Dakota.\nThe plant slaughters 19,500 pigs a day — 5 '
                'percent of U.S. pork.')

    @classmethod
    @property
    def init_params(cls):
        return [
            Param("lang", DataType.STRING, {
                "en": "en",
                "zh": "zh",
            }, "en"),
        ]
    
    def run(self, dataset, *, exporter=None, tracer=None):
        if getattr(self, 'enable_detailed_logging', False):
            self.total_samples = 0
            self.modified_samples = 0
            self.unmodified_samples = 0
        result = super().run(dataset, exporter=exporter, tracer=tracer)
        if getattr(self, 'enable_detailed_logging', False):
            self._log_mapper_summary()
        return result
    
    def _log_mapper_summary(self):
        try:
            from loguru import logger
            total, modified, unmodified = self.total_samples, self.modified_samples, self.unmodified_samples
            if total == 0: return
            self._log_line("="*60)
            self._log_line(f"[{self._name}] Sentence Split Summary")
            self._log_line("="*60)
            self._log_line(f"Total: {total}, Split: {modified} ({modified/total*100:.2f}%), Unchanged: {unmodified} ({unmodified/total*100:.2f}%)")
            self._log_line("="*60)
        except: pass
    
    def _log_line(self, message):
        from loguru import logger
        logger.info(message)
        if hasattr(self, 'job_uid') and self.job_uid:
            from data_celery.mongo_tools.tools import insert_pipline_job_run_task_log_info
            insert_pipline_job_run_task_log_info(self.job_uid, message, operator_name=self._name, operator_index=self.pipline_index)