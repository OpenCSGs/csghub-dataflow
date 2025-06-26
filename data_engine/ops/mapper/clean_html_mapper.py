# Some code here has been modified from:
# https://github.com/togethercomputer/RedPajama-Data/tree/rp_v1/
# --------------------------------------------------------

from data_engine.utils.availability_utils import AvailabilityChecking

from ..base_op import OPERATORS, Mapper, Sample, Param, DataType

OP_NAME = 'clean_html_mapper'

with AvailabilityChecking(['selectolax'], OP_NAME):
    from selectolax.parser import HTMLParser


@OPERATORS.register_module(OP_NAME)
class CleanHtmlMapper(Mapper):
    """Mapper to clean html code in text samples."""

    def __init__(self, *args, **kwargs):
        """
        Initialization method.

        :param args: extra args
        :param kwargs: extra args
        """
        super().__init__(*args, **kwargs)

    def process(self, sample):

        def _clean_html(raw_html):
            raw_html = raw_html.replace('<li>', '\n*')
            raw_html = raw_html.replace('</li>', '')
            raw_html = raw_html.replace('<ol>', '\n*')
            raw_html = raw_html.replace('</ol>', '')
            parser = HTMLParser(raw_html)
            return parser.text()

        sample[self.text_key] = _clean_html(sample[self.text_key])
        return sample

    @classmethod
    @property
    def description(cls):
        return """Mapper to clean html code in text samples."""

    @classmethod
    @property
    def sample(cls):
        return Sample('<a href=\'https://www.example.com/file.html?;name=Test\''
                ' rel=\'noopener noreferrer\' target=\'_blank\'>Test</a>', 
                      'Test')

    @classmethod
    @property
    def init_params(cls):
        return None