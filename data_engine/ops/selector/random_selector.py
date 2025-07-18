from jsonargparse.typing import ClosedUnitInterval, PositiveInt

from data_engine.format.mixture_formatter import MixtureFormatter

from ..base_op import OPERATORS, Selector, Sample, Param, DataType


@OPERATORS.register_module('random_selector')
class RandomSelector(Selector):
    """Selector to random select samples. """

    def __init__(self,
                 select_ratio: ClosedUnitInterval = None,
                 select_num: PositiveInt = None,
                 *args,
                 **kwargs):
        """
        Initialization method.

        :param select_ratio: The ratio to select. When both
            select_ratio and select_num are set, the value corresponding
            to the smaller number of samples will be applied.
        :param select_num: The number of samples to select. When both
            select_ratio and select_num are set, the value corresponding
            to the smaller number of samples will be applied.
        :param args: extra args
        :param kwargs: extra args
        """
        super().__init__(*args, **kwargs)
        self.select_ratio = select_ratio
        self.select_num = select_num

    def process(self, dataset):
        if len(dataset) <= 1:
            return dataset

        if self.select_ratio is None and self.select_num is None:
            return dataset

        select_num = 0
        if not self.select_ratio:
            select_num = self.select_num
        else:
            select_num = int(self.select_ratio * len(dataset))
            if self.select_num and self.select_num < select_num:
                select_num = self.select_num

        return MixtureFormatter.random_sample(dataset,
                                              sample_number=select_num)

    @classmethod
    @property
    def description(cls):
        return """Selector to random select samples. """

    @classmethod
    @property
    def sample(cls):
        return Sample("{"
            "'text': '，。、„”“«»１」「《》´∶：？！',"
            "'count': None,"
            "'meta': {"
            "    'suffix': '.html',"
            "    'key1': {"
            "        'key2': {"
            "            'count': 18"
            "        },"
            "        'count': 48"
            "    }"
            "}"
        "}", 
                      "")

    @classmethod
    @property
    def init_params(cls):
        return [
            Param("select_ratio", DataType.ClosedUnitInterval, None, None),
            Param("select_num", DataType.PositiveFloat, None, None),
        ]