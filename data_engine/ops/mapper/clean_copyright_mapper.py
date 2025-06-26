# Some code here has been modified from:
# https://github.com/togethercomputer/RedPajama-Data/tree/rp_v1/
# --------------------------------------------------------

import regex as re

from ..base_op import OPERATORS, Mapper, Sample, Param, DataType


@OPERATORS.register_module('clean_copyright_mapper')
class CleanCopyrightMapper(Mapper):
    """Mapper to clean copyright comments at the beginning of the text
    samples."""

    def __init__(self, *args, **kwargs):
        """
        Initialization method.

        :param args: extra args
        :param kwargs: extra args
        """
        super().__init__(*args, **kwargs)
        self.pat = re.compile('/\\*[^*]*\\*+(?:[^/*][^*]*\\*+)*/')
        self.cpat = re.compile('copyright', re.IGNORECASE)

    def process(self, sample):

        r = self.pat.search(sample[self.text_key])
        if r:
            # found one, now see if it contains "copyright", if so strip it
            span = r.span()
            sub = sample[self.text_key][span[0]:span[1]]
            if self.cpat.search(sub):
                # cut it
                sample[self.text_key] = sample[
                    self.text_key][:span[0]] + sample[self.text_key][span[1]:]

            return sample

        lines = sample[self.text_key].split('\n')
        skip = 0

        # Greedy replace any file that begins with comment block, most
        # are copyright headers
        for k in range(len(lines)):
            if (lines[k].startswith('//') or lines[k].startswith('#')
                    or lines[k].startswith('--') or not lines[k]):
                skip = skip + 1
            else:
                break

        if skip:
            # we skipped, consume it
            sample[self.text_key] = '\n'.join(lines[skip:])
        return sample
    @classmethod
    @property
    def description(cls):
        return """Mapper to clean copyright comments at the beginning of the text
    samples."""

    @classmethod
    @property
    def sample(cls):
        return Sample("这是一段 /* 多行注释\n注释内容copyright\n*/ 的文本。另外还有一些 // 单行注释。", 
                      "这是一段  的文本。另外还有一些 // 单行注释。")

    @classmethod
    @property
    def init_params(cls):
        return None