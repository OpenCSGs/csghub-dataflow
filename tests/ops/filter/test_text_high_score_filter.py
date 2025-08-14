import unittest

from data_engine.core.data import NestedDataset as Dataset
from data_engine.ops.filter.text_high_score_filter import TextHighScoreFilter
from data_engine.utils.constant import Fields
from data_engine.utils.unittest_utils import DataJuicerTestCaseBase


class TextHighScoreFilterTest(DataJuicerTestCaseBase):

    def _run_high_score_filter(self, dataset: Dataset, target_list, op):
        if Fields.stats not in dataset.features:
            dataset = dataset.add_column(name=Fields.stats,
                                         column=[{}] * dataset.num_rows)
        dataset = dataset.map(op.compute_stats)
        dataset = dataset.filter(op.process)
        dataset = dataset.select_columns(column_names=['text', 'score'])
        res_list = dataset.to_list()
        self.assertEqual(res_list, target_list)

    def test_case(self):
        ds_list = [
            # Default range [0.6, 2.0): should pass
            {'text': 'score is 0.7', 'score': 0.7},
            # On the boundary: should pass
            {'text': 'score is 0.6', 'score': 0.6},
            # On the boundary: should fail
            {'text': 'score is 2.0', 'score': 2.0},
            # Below the range: should fail
            {'text': 'score is 0.5', 'score': 0.5},
            # Missing score field: should fail
            {'text': 'score is missing', 'score': None},
            # Score is None: should fail
            {'text': 'score is None', 'score': None},
        ]
        tgt_list = [
            {'text': 'score is 0.7', 'score': 0.7},
            {'text': 'score is 0.6', 'score': 0.6},
        ]
        dataset = Dataset.from_list(ds_list)
        op = TextHighScoreFilter()
        self._run_high_score_filter(dataset, tgt_list, op)


if __name__ == '__main__':
    unittest.main()
