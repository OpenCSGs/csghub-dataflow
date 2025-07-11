from data_engine.utils.availability_utils import AvailabilityChecking

from ..base_op import OPERATORS, Mapper, Sample, Param, DataType

OP_NAME = 'fix_unicode_mapper'

with AvailabilityChecking(['ftfy'], OP_NAME):
    import ftfy


@OPERATORS.register_module(OP_NAME)
class FixUnicodeMapper(Mapper):
    """Mapper to fix unicode errors in text samples."""

    def __init__(self, normalization: str = None, *args, **kwargs):
        """
        Initialization method.

        :param normalization: the specified form of Unicode
             normalization mode, which can be one of
             ['NFC', 'NFKC', 'NFD', and 'NFKD'], default 'NFC'.
        :param args: extra args
        :param kwargs: extra args
        """
        super().__init__(*args, **kwargs)
        if normalization and len(normalization) > 0:
            self.normalization = normalization.upper()
        else:
            self.normalization = 'NFC'

        if self.normalization.upper() not in ['NFC', 'NFKC', 'NFD', 'NFKD']:
            raise ValueError(f'Normalization mode [{normalization}] is not '
                             'supported. Can only be one of '
                             '["NFC", "NFKC", "NFD", "NFKD"]')

    def process(self, sample):
        sample[self.text_key] = ftfy.fix_text(sample[self.text_key],
                                              normalization=self.normalization)
        return sample

    @classmethod
    @property
    def description(cls):
        return "Mapper to fix unicode errors in text samples."

    @classmethod
    @property
    def sample(cls):
        return Sample("The Mona Lisa doesnÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢t have eyebrows.", "The Mona Lisa doesn\'t have eyebrows.")

    @classmethod
    @property
    def init_params(cls):
        return [
            Param("normalization", DataType.STRING, {
                "NFC": "NFC",
                "NFKC": "NFKC",
                "NFD": "NFD",
                "NFKD": "NFKD",
            }, "NFC"),
        ]