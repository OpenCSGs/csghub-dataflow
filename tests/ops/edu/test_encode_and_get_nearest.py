import unittest

from datasets import Dataset

from data_engine.ops.edu.encode_and_get_nearest import EncodeAndGetNearestSelector
from data_engine.utils.unittest_utils import DataJuicerTestCaseBase


class EncodeAndGetNearestSelectTest(DataJuicerTestCaseBase):

    def _run_encode_and_get_nearest_selector(self, dataset: Dataset, op):
        res_num = len(dataset)
        dataset = op.process(dataset)
        tgt_num = len(dataset['nn_scores'])
        self.assertEqual(res_num, tgt_num)

    def test_encode_and_get_nearest(self):
        ds_list = [
            {'first_prompt': 'What is artificial intelligence?'},
            {'first_prompt': 'How does machine learning work?'},
            {'first_prompt': 'Explain the concept of deep learning.'},
        ]
        dataset = Dataset.from_list(ds_list)
        op = EncodeAndGetNearestSelector()
        self._run_encode_and_get_nearest_selector(dataset, op)


if __name__ == '__main__':
    unittest.main()
