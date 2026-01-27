import regex as re
from jsonargparse.typing import restricted_number_type

from ..base_op import OPERATORS, Mapper, Sample, Param, DataType

from_2_to_20 = restricted_number_type('from_2_to_20', int, [('>=', 2),
                                                            ('<=', 20)])


@OPERATORS.register_module('remove_table_text_mapper')
class RemoveTableTextMapper(Mapper):
    """
    Mapper to remove table texts from text samples.

    Regular expression is used to remove tables in the range of column
    number of tables.
    """

    def __init__(self,
                 min_col: from_2_to_20 = 2,
                 max_col: from_2_to_20 = 20,
                 *args,
                 **kwargs):
        """
        Initialization method.

        :param min_col: The min number of columns of table to remove.
        :param max_col: The max number of columns of table to remove.
        :param args: extra args
        :param kwargs: extra args
        """
        super().__init__(*args, **kwargs)
        self.min_col = min_col
        self.max_col = max_col
        self.pattern = r'(?<=\n)((\S+?)([ |\t](\S+?)){%d}\n+){2,}'
        
        # Enable detailed logging
        self.enable_detailed_logging = True
        self.total_samples = 0
        self.modified_samples = 0
        self.unmodified_samples = 0

    def process(self, sample):
        # Track statistics
        if getattr(self, 'enable_detailed_logging', False):
            self.total_samples += 1
        
        original_text = sample[self.text_key]

        text = sample[self.text_key]
        for i in range(self.min_col - 1, self.max_col):
            pattern = re.compile(self.pattern % i)
            text = pattern.sub('', text)

        sample[self.text_key] = text
        
        # Track if modified
        if getattr(self, 'enable_detailed_logging', False):
            if sample[self.text_key] != original_text:
                self.modified_samples += 1
            else:
                self.unmodified_samples += 1
        
        return sample

    @classmethod
    @property
    def description(cls):
        return     """
    Mapper to remove table texts from text samples.

    Regular expression is used to remove tables in the range of column
    number of tables.
    """

    @classmethod
    @property
    def sample(cls):
        return Sample("This is a table:\n编号 分行 营运资金1 营运资金2 营运资金3 营运资金4 营运资金5\n① 北京分行 495,000,000.00 200,000,000.00 295,000,000.00 - 495,000,000.00\n② 大连分行 440,000,000.00 100,000,000.00 340,000,000.00 - 440,000,000.00\n③ 重庆分行 500,000,000.00 100,000,000.00 400,000,000.00 - 500,000,000.00\n④ 南京分行 430,000,000.00 100,000,000.00 330,000,000.00 - 430,000,000.00\n⑤ 青岛分行 500,000,000.00 - 100,159,277.60 399,840,722.40 500,000,000.00\nThe end of the table.", 
                      "This is a table:\nThe end of the table.")

    @classmethod
    @property
    def init_params(cls):
        return [
            Param("min_col", DataType.from_2_to_20, None, 2),
            Param("max_col", DataType.from_2_to_20, None, 20),
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
            total = self.total_samples
            modified = self.modified_samples
            unmodified = self.unmodified_samples
            if total == 0:
                return
            self._log_line("="*60)
            self._log_line(f"[{self._name}] Table Text Removal Summary")
            self._log_line("="*60)
            self._log_line(f"Total samples processed: {total}")
            self._log_line(f"Samples with table text removed: {modified} ({modified/total*100:.2f}%)")
            self._log_line(f"Samples unchanged: {unmodified} ({unmodified/total*100:.2f}%)")
            self._log_line("="*60)
        except Exception as e:
            import traceback
            from loguru import logger
            logger.error(f"Failed to generate mapper logging: {e}\n{traceback.format_exc()}")
    
    def _log_line(self, message):
        from loguru import logger
        logger.info(message)
        if hasattr(self, 'job_uid') and self.job_uid:
            from data_celery.mongo_tools.tools import insert_pipline_job_run_task_log_info
            insert_pipline_job_run_task_log_info(self.job_uid, message, operator_name=self._name, operator_index=self.pipline_index)