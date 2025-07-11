import regex as re

from ..base_op import OPERATORS, Mapper, Sample, Param, DataType


def split_sentence(text):
    text = re.sub('([.。！!？\?])([^’”])', r'\1\n\2', text)  # noqa
    text = re.sub('(\.{6})([^’”])', r'\1\n\2', text)  # noqa
    text = re.sub('(\…{2})([^’”])', r'\1\n\2', text)  # noqa
    text = re.sub('([.。!！？\?\.{6}\…{2}][’”])([^’”])', r'\1\n\2', text)  # noqa
    return text.split('\n')


@OPERATORS.register_module('remove_repeat_sentences_mapper')
class RemoveRepeatSentencesMapper(Mapper):
    """Mapper to remove repeat sentences in text samples."""

    def __init__(self,
                 lowercase: bool = False,
                 ignore_special_character: bool = True,
                 min_repeat_sentence_length: int = 2,
                 *args,
                 **kwargs):
        """
        Initialization method.

        :param lowercase: Whether to convert sample text to lower case
        :param ignore_special_character: Whether to ignore special
            characters when judging repeated sentences. Special characters
            are all characters except Chinese characters, letters and
            numbers.
        :param min_repeat_sentence_length: Sentences shorter than this
            length will not be deduplicated. If ignore_special_character is
            set to True, then special characters are not included in this
            length.
        :param args: extra args
        :param kwargs: extra args
        """

        super().__init__(*args, **kwargs)
        self.lowercase = lowercase
        self.min_repeat_sentence_length = min_repeat_sentence_length
        self.remove_regex = re.compile(r'[^a-zA-Z0-9\u4e00-\u9fa5\n\t ]'
                                       ) if ignore_special_character else None

    def process(self, sample):

        lines = [e for e in sample[self.text_key].split('\n')]
        new_lines = []
        hash_set = set([])
        for line in lines:
            new_sent = ''
            if line:
                sentences = split_sentence(line)
                for sentence in sentences:
                    copy = sentence.strip()
                    if self.lowercase:
                        copy = copy.lower()
                    if self.remove_regex:
                        copy = self.remove_regex.sub('', copy)

                    if len(copy) < self.min_repeat_sentence_length:
                        new_sent += sentence
                    elif copy not in hash_set:
                        new_sent += sentence
                        hash_set.add(copy)
            new_lines.append(new_sent)

        sample[self.text_key] = '\n'.join(new_lines)
        return sample

    @classmethod
    @property
    def description(cls):
        return """Mapper to remove repeat sentences in text samples."""

    @classmethod
    @property
    def sample(cls):
        return Sample("今天天气真不错，阳光明媚，适合出去散步。小明说：“今天天气真不错，我们去海边吧。” 小红回答说：“好主意！” 但是，小李觉得：“今天天气真不错，我们去爬山吧。” 今天天气真不错，阳光明媚，适合出去散步。昨天下了一整天的雨，今天终于放晴了。昨天下了一整天的雨，今天终于放晴了。", 
                      "今天天气真不错，阳光明媚，适合出去散步。小明说：“今天天气真不错，我们去海边吧。” 小红回答说：“好主意！” 但是，小李觉得：“今天天气真不错，我们去爬山吧。”昨天下了一整天的雨，今天终于放晴了。")

    @classmethod
    @property
    def init_params(cls):
        return [
            Param("lowercase", DataType.BOOLEAN, None, False),
            Param("ignore_special_character", DataType.BOOLEAN, None, False),
            Param("min_repeat_sentence_length", DataType.INTEGER, None, 2),
        ]