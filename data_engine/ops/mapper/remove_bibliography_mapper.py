# Some code here has been modified from:
# https://github.com/togethercomputer/RedPajama-Data/tree/rp_v1/
# --------------------------------------------------------

import regex as re

from ..base_op import OPERATORS, Mapper, Sample, Param, DataType


@OPERATORS.register_module('remove_bibliography_mapper')
class RemoveBibliographyMapper(Mapper):
    """Mapper to remove bibliography at the end of documents in Latex
    samples."""

    def __init__(self, *args, **kwargs):
        """
        Initialization method.

        :param args: extra args
        :param kwargs: extra args
        """
        super().__init__(*args, **kwargs)
        self.pattern = r'(\\appendix|'
        self.pattern += r'\\begin\{references\}|'
        self.pattern += r'\\begin\{REFERENCES\}|'
        self.pattern += r'\\begin\{thebibliography\}|'
        self.pattern += r'\\bibliography\{.*\}'
        self.pattern += r').*$'

    def process(self, sample):
        sample[self.text_key] = re.sub(pattern=self.pattern,
                                       repl=r'',
                                       string=sample[self.text_key],
                                       flags=re.DOTALL)
        return sample

    @classmethod
    @property
    def description(cls):
        return """Mapper to remove bibliography at the end of documents in Latex
    samples."""

    @classmethod
    @property
    def sample(cls):
        return Sample("%%\n%% This is file `sample-sigconf.tex\\clearpage\n\\bibliographystyle{ACM-Reference-Format}\n\\bibliography{sample-base}\n\\end{document}\n\\endinput\n%%\n%% End of file `sample-sigconf.tex'.\n", 
                      "%%\n%% This is file `sample-sigconf.tex\\clearpage\n\\bibliographystyle{ACM-Reference-Format}\n")

    @classmethod
    @property
    def init_params(cls):
        return None