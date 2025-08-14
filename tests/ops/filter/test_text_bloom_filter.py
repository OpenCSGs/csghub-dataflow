
import os
import unittest

from data_engine.core.data import NestedDataset as Dataset

from data_engine.ops.filter.text_bloom_filter import TextBloomFilter
from data_engine.utils.constant import Fields
from data_engine.utils.unittest_utils import DataJuicerTestCaseBase


class TextBloomFilterTest(DataJuicerTestCaseBase):
    data_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..',
                             'data')

    def _run_text_bloom_filter(self,
                               dataset: Dataset,
                               target_list,
                               op,
                               columns,
                               ):
        if Fields.stats not in dataset.features:
            dataset = dataset.add_column(name=Fields.stats,
                                         column=[{}] * dataset.num_rows)
        dataset = dataset.map(op.compute_stats)
        dataset = dataset.filter(op.process)
        dataset = dataset.select_columns(column_names=columns)
        res_list = dataset.to_list()
        self.assertEqual(res_list, target_list)

    def test_en_text_case(self):
        ds_list = [{
            'text': 'Tom is playing piano.'
        }, {
            'text': 'Tom is playing piano.'
        }, {
            'text': 'Tom is playing piano.'
        }, {
            'text': 'Tom plays piano.'
        }, {
            'text': 'Tom played piano.'
        }, {
            'text': 'Tom played piano.'
        }, {
            'text': 'Tom played piano.'
        }]
        tgt_list = [{
            'text': 'Tom is playing piano.'
        }, {
            'text': 'Tom plays piano.'
        }, {
            'text': 'Tom played piano.'
        }]
        dataset = Dataset.from_list(ds_list)
        op = TextBloomFilter()
        self._run_text_bloom_filter(dataset, tgt_list, op, ['text'])


if __name__ == '__main__':
    unittest.main()
