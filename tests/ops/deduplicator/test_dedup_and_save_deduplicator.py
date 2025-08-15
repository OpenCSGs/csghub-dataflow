import unittest

from data_engine.core.data import NestedDataset as Dataset
from data_engine.ops.deduplicator.dedup_and_save_deduplicator import \
    DedupAndSaveDeduplicator
from data_engine.utils.unittest_utils import DataJuicerTestCaseBase


class DedupAndSaveDeduplicatorTest(DataJuicerTestCaseBase):

    def _run_dedup(self, dataset: Dataset, target_list, op):
        print("before data:", [row for row in dataset])
        dataset = dataset.map(op.compute_hash)
        dataset, _ = op.process(dataset)
        print("after data:", [row for row in dataset])
        dataset = dataset.select_columns(column_names=['text'])
        res_list = dataset.to_list()
        self.assertEqual(res_list, target_list)

    def test_transitive_deduplication(self):
        """Test for transitive cases like A~B, B~C -> group (A,B,C)."""
        ds_list = [
            {'text': 'A', 'nn_indices': [[1]], 'nn_scores': [[0.99]]},      # 0
            {'text': 'B', 'nn_indices': [[0, 2]], 'nn_scores': [[0.99, 0.98]]}, # 1
            {'text': 'C', 'nn_indices': [[1]], 'nn_scores': [[0.98]]},      # 2
            {'text': 'D', 'nn_indices': [[]], 'nn_scores': [[]]},           # 3
        ]
        # A, B, C form a connected component. min(0,1,2) is 0. D is isolated.
        # So, only A and D should be kept.
        tgt_list = [{'text': 'A'}, {'text': 'D'}]
        dataset = Dataset.from_list(ds_list)
        op = DedupAndSaveDeduplicator(similarity_threshold=0.95)
        self._run_dedup(dataset, tgt_list, op)

    def test_multiple_separate_groups(self):
        """Test for multiple separate groups like A~B, C~D."""
        ds_list = [
            {'text': 'A1', 'nn_indices': [[1]], 'nn_scores': [[0.96]]},     # 0
            {'text': 'A2', 'nn_indices': [[0]], 'nn_scores': [[0.96]]},     # 1
            {'text': 'B1', 'nn_indices': [[3]], 'nn_scores': [[0.97]]},     # 2
            {'text': 'B2', 'nn_indices': [[2]], 'nn_scores': [[0.97]]},     # 3
        ]
        # Group 1: (0, 1), keep 0. Group 2: (2, 3), keep 2.
        tgt_list = [{'text': 'A1'}, {'text': 'B1'}]
        dataset = Dataset.from_list(ds_list)
        op = DedupAndSaveDeduplicator(similarity_threshold=0.95)
        self._run_dedup(dataset, tgt_list, op)

    def test_no_duplicates(self):
        """Test case where no similarity scores are above the threshold."""
        ds_list = [
            {'text': 'A', 'nn_indices': [[1]], 'nn_scores': [[0.90]]},
            {'text': 'B', 'nn_indices': [[0]], 'nn_scores': [[0.90]]},
        ]
        # No scores >= 0.95, so no edges are added. All nodes are kept.
        tgt_list = [{'text': 'A'}, {'text': 'B'}]
        dataset = Dataset.from_list(ds_list)
        op = DedupAndSaveDeduplicator(similarity_threshold=0.95)
        self._run_dedup(dataset, tgt_list, op)


if __name__ == '__main__':
    unittest.main(verbosity=2)
