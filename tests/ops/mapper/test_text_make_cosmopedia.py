import unittest

from data_engine.core.data import NestedDataset as Dataset
from data_engine.ops.mapper.text_make_cosmopedia import MakeCosmopediaMapper
from data_engine.utils.unittest_utils import DataJuicerTestCaseBase


class MakeCosmopediaMapperTest(DataJuicerTestCaseBase):

    def _run_make_cosmopedia(self, dataset: Dataset, ):
        op = MakeCosmopediaMapper()
        new_dataset = dataset.map(op.process)
        target_list = dataset.select_columns(['title', 'text']).to_list()
        res_list = new_dataset.select_columns(['title', 'text']).to_list()
        self.assertEqual(res_list, target_list)

    def test_en_text_case(self):
        """Test processing sample with only text field."""
        samples = [
            {
                'title': 'Dog',
                'text': 'What are the classifications of dogs'
            },
            {
                'title': 'Cat',
                'text': 'What are the classifications of cats'
            }
        ]

        dataset = Dataset.from_list(samples)
        self._run_make_cosmopedia(dataset)


if __name__ == '__main__':
    unittest.main()
