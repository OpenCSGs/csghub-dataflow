from data_engine.utils.availability_utils import AvailabilityChecking

from ..base_op import OPERATORS, Mapper, Sample, Param, DataType

OP_NAME = 'chinese_convert_mapper'

with AvailabilityChecking(['opencc'], OP_NAME):
    import opencc  # noqa: F401

OPENCC_CONVERTER = None


def prepare_converter(mode):
    mode_path = mode + '.json'
    global OPENCC_CONVERTER
    if OPENCC_CONVERTER is None:
        # empty converter
        OPENCC_CONVERTER = opencc.OpenCC(mode_path)
    if not OPENCC_CONVERTER.config.endswith(mode_path):
        # the config is actually a config path
        # update and get a new converter with specified mode
        OPENCC_CONVERTER = opencc.OpenCC(mode_path)


@OPERATORS.register_module(OP_NAME)
class ChineseConvertMapper(Mapper):
    """Mapper to convert Chinese between Traditional Chinese, Simplified Chinese
    and Japanese Kanji."""

    def __init__(self, mode: str = 's2t', *args, **kwargs):
        """
        Initialization method.

        :param mode: Choose the mode to convert Chinese:

            s2t: Simplified Chinese to Traditional Chinese,

            t2s: Traditional Chinese to Simplified Chinese,

            s2tw: Simplified Chinese to Traditional Chinese (Taiwan Standard),

            tw2s: Traditional Chinese (Taiwan Standard) to Simplified Chinese,

            s2hk: Simplified Chinese to Traditional Chinese
            (Hong Kong variant),

            hk2s: Traditional Chinese (Hong Kong variant) to Simplified
            Chinese,

            s2twp: Simplified Chinese to Traditional Chinese (Taiwan Standard)
            with Taiwanese idiom,

            tw2sp: Traditional Chinese (Taiwan Standard) to Simplified Chinese
            with Mainland Chinese idiom,

            t2tw: Traditional Chinese to Traditional Chinese (Taiwan Standard),

            tw2t: Traditional Chinese (Taiwan standard) to Traditional Chinese,

            hk2t: Traditional Chinese (Hong Kong variant) to Traditional
            Chinese,

            t2hk: Traditional Chinese to Traditional Chinese
            (Hong Kong variant),

            t2jp: Traditional Chinese Characters (Kyūjitai) to New Japanese
            Kanji,

            jp2t: New Japanese Kanji (Shinjitai) to Traditional Chinese
            Characters,

        :param args: extra args
        :param kwargs: extra args
        """
        super().__init__(*args, **kwargs)
        mode_list = [
            's2t', 't2s', 's2tw', 'tw2s', 's2hk', 'hk2s', 's2twp', 'tw2sp',
            't2tw', 'tw2t', 'hk2t', 't2hk', 't2jp', 'jp2t'
        ]
        assert mode in mode_list, 'Please make sure mode is one of {}'.format(
            mode_list)
        self.mode = mode
        prepare_converter(self.mode)

    def process(self, sample):
        prepare_converter(self.mode)

        sample[self.text_key] = OPENCC_CONVERTER.convert(sample[self.text_key])
        return sample
    
    @classmethod
    @property
    def description(cls):
        return "Mapper to convert Chinese between Traditional Chinese, Simplified Chinese and Japanese Kanji."

    @classmethod
    @property
    def sample(cls):
        return Sample("这是几个简体字，会被转换为繁体字", "這是幾個簡體字，會被轉換爲繁體字")

    @classmethod
    @property
    def init_params(cls):
        return [
            Param("mode", DataType.STRING, {
                "s2t": "s2t",
                "t2s": "t2s",
                "s2tw": "s2tw",
                "tw2s": "tw2s",
                "s2hk": "s2hk",
                "hk2s": "hk2s",
                "s2twp": "s2twp",
                "tw2sp": "tw2sp",
                "t2tw": "t2tw",
                "tw2t": "tw2t",
                "hk2t": "hk2t",
                "t2hk": "t2hk",
                "t2jp": "t2jp",
                "jp2t": "jp2t",
            }, "s2t")
        ]
