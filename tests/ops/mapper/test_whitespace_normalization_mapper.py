import unittest

from data_engine.ops.mapper.whitespace_normalization_mapper import \
    WhitespaceNormalizationMapper
from data_engine.utils.unittest_utils import DataJuicerTestCaseBase


class WhitespaceNormalizationMapperTest(DataJuicerTestCaseBase):

    def setUp(self):
        self.op = WhitespaceNormalizationMapper()

    def _run_whitespace_normalization(self, samples):
        for sample in samples:
            result = self.op.process(sample)
            self.assertEqual(result['text'], result['target'])

    def test_case(self):

        samples = [{
            'text': 'x \t              　\u200B\u200C\u200D\u2060￼\u0084y',
            'target': 'x                       y'
        }]

        self._run_whitespace_normalization(samples)


if __name__ == '__main__':
    unittest.main()
