import os
import unittest

from data_engine.core.data import NestedDataset as Dataset

from data_engine.ops.filter.text_gather_filter import TextGatherFilter
from data_engine.utils.constant import Fields
from data_engine.utils.unittest_utils import DataJuicerTestCaseBase


class TextGatherFilterTest(DataJuicerTestCaseBase):
    data_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..',
                             'data')

    def _run_text_gather_filter(self,
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

    def test_gather_and_filter_case_english(self):
        # Test data with instruction and response fields as required by the filter
        ds_list = [{
            'text': 'What is Python?',
            'instruction': 'What is Python?||',
            'response': 'Python is a programming language.||<|im_end|>'
        }, {
            'text': 'What is Python?',
            'instruction': 'What is Python||?<|im_end|>',
            'response': 'Python is a high-level programming language.||<|im_end|>'
        }, {
            'text': 'What is Java?',
            'instruction': 'What is Java?<|im_end|>',
            'response': 'Java is an object-oriented programming language.||<|im_end|>'
        }, {
            'text': 'Hello',
            'instruction': 'Hi||!<|im_end|>',
            'response': 'Hello!||<|im_end|>'
        }, {
            'text': 'Short',
            'instruction': 'A',
            'response': 'B'
        }]

        # Expected results after filtering (duplicates removed, short content filtered)
        tgt_list = [{
            'text': 'What is Python?',
            'first_prompt': 'What is Python?',
            'first_answer': 'Python is a programming language.',
            'conversation': [
                {"role": "user", "content": "What is Python?"},
                {"role": "assistant", "content": "Python is a programming language."}
            ]
        }, {
            'text': 'What is Java?',
            'first_prompt': 'What is Java?',
            'first_answer': 'Java is an object-oriented programming language.',
            'conversation': [
                {"role": "user", "content": "What is Java?"},
                {"role": "assistant", "content": "Java is an object-oriented programming language."}
            ]
        }, {
            'text': 'Hello',
            'first_prompt': 'Hi!',
            'first_answer': 'Hello!',
            'conversation': [
                {"role": "user", "content": "Hi!"},
                {"role": "assistant", "content": "Hello!"}
            ]
        }]

        dataset = Dataset.from_list(ds_list)
        op = TextGatherFilter()
        self._run_text_gather_filter(dataset, tgt_list, op,
                                         ['text', 'first_prompt', 'first_answer', 'conversation'])

    def test_gather_and_filter_case_chinese(self):

        ds_list = [{
            'text': '什么是Python？',
            'instruction': '什么是Python？||',
            'response': 'Python是一种编程语言。||<|im_end|>'
        }, {
            'text': '什么是Python？',
            'instruction': '什么是Python||？<|im_end|>',
            'response': 'Python是一种高级编程语言。||<|im_end|>'
        }, {
            'text': '什么是Java？',
            'instruction': '什么是Java？<|im_end|>',
            'response': 'Java是一种面向对象的编程语言。||<|im_end|>'
        }, {
            'text': '你好',
            'instruction': '你好||！<|im_end|>',
            'response': '你好！||<|im_end|>'
        }, {
            'text': '短内容',
            'instruction': '短',
            'response': '内容'
        }]


        tgt_list = [{
            'text': '什么是Python？',
            'first_prompt': '什么是Python？',
            'first_answer': 'Python是一种编程语言。',
            'conversation': [
                {"role": "user", "content": "什么是Python？"},
                {"role": "assistant", "content": "Python是一种编程语言。"}
            ]
        }, {
            'text': '什么是Java？',
            'first_prompt': '什么是Java？',
            'first_answer': 'Java是一种面向对象的编程语言。',
            'conversation': [
                {"role": "user", "content": "什么是Java？"},
                {"role": "assistant", "content": "Java是一种面向对象的编程语言。"}
            ]
        }, {
            'text': '你好',
            'first_prompt': '你好！',
            'first_answer': '你好！',
            'conversation': [
                {"role": "user", "content": "你好！"},
                {"role": "assistant", "content": "你好！"}
            ]
        }]

        dataset = Dataset.from_list(ds_list)
        op = TextGatherFilter()
        self._run_text_gather_filter(dataset, tgt_list, op,
                                         ['text', 'first_prompt', 'first_answer', 'conversation'])


if __name__ == '__main__':
    unittest.main()
