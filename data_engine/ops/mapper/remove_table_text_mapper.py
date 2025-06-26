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

    def process(self, sample):

        text = sample[self.text_key]
        for i in range(self.min_col - 1, self.max_col):
            pattern = re.compile(self.pattern % i)
            text = pattern.sub('', text)

        sample[self.text_key] = text
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