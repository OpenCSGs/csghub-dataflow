from typing import Callable

from ...utils.constant import Fields, StatsKeys
from ..base_op import OPERATORS, Filter, Sample, Param, DataType
from pybloom_live import ScalableBloomFilter
from text_dedup.utils.hashfunc import md5_digest
from text_dedup.utils.hashfunc import sha256_digest
from text_dedup.utils.hashfunc import xxh3_128_digest

OP_NAME = 'text_bloom_filter'


@OPERATORS.register_module('text_bloom_filter')
class TextBloomFilter(Filter):
    """A filter class that uses a Bloom filter to detect and remove duplicate text samples."""

    def __init__(self,
                 error_rate: float = 1e-6,
                 hash_func: str = 'md5',
                 initial_capacity: int = 100,
                 *args,
                 **kwargs):
        """
        Initialization method.

        :param error_rate: The desired error rate for the bloom filter, default is 1e-6
        :param hash_func: The hash function to use, supported options are 'md5', 'sha256', 'xxh3', default is 'md5'
        :param initial_capacity: The initial capacity of the bloom filter, default is 100
        :param args: extra args
        :param kwargs: extra args
        """
        super().__init__(*args, **kwargs)
        self.hash_func: Callable = {
            "md5": md5_digest,  # type: ignore
            "sha256": sha256_digest,  # type: ignore
            "xxh3": xxh3_128_digest,  # type: ignore
        }[hash_func]

        self.bf = ScalableBloomFilter(
            initial_capacity=initial_capacity,
            error_rate=error_rate,
        )
        self.flags = set()

    def compute_stats(self, sample, context=False):
        # check if it's computed already
        if StatsKeys.bloom in sample[Fields.stats]:
            return sample
        text = sample[self.text_key]

        # 计算hash值
        text_bytes = text.encode('utf-8')
        hash_value = self.hash_func(text_bytes)

        # 检查是否已存在（使用in操作符）
        is_duplicate = hash_value in self.bf

        # 添加到Bloom Filter（add方法返回是否已存在）
        self.bf.add(hash_value)

        # 记录是否为重复项
        sample[Fields.stats][StatsKeys.bloom] = is_duplicate
        self.flags.add(is_duplicate)
        return sample

    def process(self, sample):

        if True in self.flags:
            return not sample[Fields.stats][StatsKeys.bloom]
        else:
            return False

    @classmethod
    @property
    def description(cls):
        return "Filter to deduplicate samples using Bloom Filter."

    @classmethod
    @property
    def sample(cls):
        return Sample(
            before="包含重复文本的数据集，如多次出现的相同句子",
            after="去重后的数据集，只保留每个唯一文本的一个实例"
        )

    @classmethod
    @property
    def init_params(cls):
        return [
            Param("error_rate", DataType.FLOAT, {}, 1e-6),
            Param("hash_func", DataType.STRING, {
                'sha256': 'sha256',
                'md5': 'md5',
                'xxh3': 'xxh3'}, 'md5'),
            Param("initial_capacity", DataType.INTEGER, {}, 100),
        ]
