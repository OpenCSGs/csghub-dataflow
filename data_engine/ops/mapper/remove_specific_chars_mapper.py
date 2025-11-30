from typing import List, Union

import regex as re

from ..base_op import OPERATORS, Mapper, Sample, Param, DataType


@OPERATORS.register_module('remove_specific_chars_mapper')
class RemoveSpecificCharsMapper(Mapper):
    """Mapper to clean specific chars in text samples."""

    def __init__(self,
                 chars_to_remove: Union[str, List[str]] = '◆●■►▼▲▴∆▻▷❖♡□',
                 *args,
                 **kwargs):
        """
        Initialization method.

        :param chars_to_remove: a list or a string including all
            characters that need to be removed from text.
        :param args: extra args
        :param kwargs: extra args
        """

        super().__init__(*args, **kwargs)
        if chars_to_remove:
            self.pattern = '[' + '|'.join(chars_to_remove) + ']'
        else:
            self.pattern = None

    def process(self, sample):

        if self.pattern is None:
            return sample

        sample[self.text_key] = re.sub(pattern=self.pattern,
                                       repl=r'',
                                       string=sample[self.text_key],
                                       flags=re.DOTALL)
        return sample

    @classmethod
    @property
    def description(cls):
        return """Mapper to clean specific chars in text samples. now support: ◆●■►▼▲▴∆▻▷❖♡□"""

    @classmethod
    @property
    def sample(cls):
        return Sample("多个●■►▼这样的特殊字符可以►▼▲▴∆吗？", 
                      "多个这样的特殊字符可以吗？")

    @classmethod
    @property
    def init_params(cls):
        return [
            Param("chars_to_remove", DataType.LIST, None, ['◆●■►▼▲▴∆▻▷❖♡□']),
        ]