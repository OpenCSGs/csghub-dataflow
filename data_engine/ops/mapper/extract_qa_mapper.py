import json
import re
from typing import Dict

from loguru import logger

from data_engine.ops.base_op import OPERATORS, UNFORKABLE, Mapper, Sample, Param, DataType
from data_engine.utils.availability_utils import AvailabilityChecking
from data_engine.utils.model_utils import get_model, prepare_model

OP_NAME = 'extract_qa_mapper'

with AvailabilityChecking(['torch', 'transformers'], OP_NAME):
    import torch
    import transformers  # noqa: F401

    # avoid hanging when calling model in multiprocessing
    torch.set_num_threads(1)


# TODO: Extend LLM-based OPs into API-based implementation.
@UNFORKABLE.register_module(OP_NAME)
@OPERATORS.register_module(OP_NAME)
class ExtractQAMapper(Mapper):
    """
    Mapper to extract question and answer pair from text samples.
    Recommended model list: [
        'alibaba-pai/pai-llama3-8b-doc2qa',
        'alibaba-pai/pai-baichuan2-7b-doc2qa',
        'alibaba-pai/pai-qwen1_5-4b-doc2qa',
        'alibaba-pai/pai-qwen1_5-7b-doc2qa',
        'alibaba-pai/pai-qwen1_5-1b8-doc2qa',
        'alibaba-pai/pai-qwen1_5-0b5-doc2qa'
    ]
    These recommended models are all trained with Chinese data
    and are suitable for Chinese.
    """

    _accelerator = 'cuda'

    def __init__(self,
                 hf_model: str = 'alibaba-pai/pai-qwen1_5-7b-doc2qa',
                 trust_remote_code=True,
                 pattern: str = None,
                 qa_format: str = 'chatml',
                 enable_vllm: bool = False,
                 tensor_parallel_size: int = None,
                 max_model_len: int = None,
                 max_num_seqs: int = 256,
                 sampling_params: Dict = {'temperature': 0.3},
                 *args,
                 **kwargs):
        """
        Initialization method.
        :param hf_model: Hugginface model id.
        :param trust_remote_code: passed to transformers
        :param pattern: regular expression pattern to search for within text.
        :param qa_format: Output format of question and answer pair.
        :param enable_vllm: Whether to use vllm for inference acceleration.
        :param tensor_parallel_size: It is only valid when enable_vllm is True.
            The number of GPUs to use for distributed execution with tensor
            parallelism.
        :param max_model_len: It is only valid when enable_vllm is True.
            Model context length. If unspecified, will be automatically
            derived from the model config.
        :param max_num_seqs: It is only valid when enable_vllm is True.
            Maximum number of sequences to be processed in a single iteration.
        :param sampling_params: Sampling parameters for text generation.
            e.g {'temperature': 0.9, 'top_p': 0.95}
        :param args: extra args
        :param kwargs: extra args

        The default data format parsed by this interface is as follows:
        Model Input:
            蒙古国的首都是乌兰巴托（Ulaanbaatar）
            冰岛的首都是雷克雅未克（Reykjavik）
        Model Output:
            蒙古国的首都是乌兰巴托（Ulaanbaatar）
            冰岛的首都是雷克雅未克（Reykjavik）
            Human: 请问蒙古国的首都是哪里？
            Assistant: 你好，根据提供的信息，蒙古国的首都是乌兰巴托（Ulaanbaatar）。
            Human: 冰岛的首都是哪里呢？
            Assistant: 冰岛的首都是雷克雅未克（Reykjavik）。
            ...
        """

        super().__init__(*args, **kwargs)
        self.num_proc = 1

        if pattern is None:
            self.pattern = r'Human: (.*?)\nAssistant: (.*?)(?=\nHuman|$)'
        else:
            self.pattern = pattern

        self.qa_format = qa_format
        self.enable_vllm = enable_vllm

        if enable_vllm:
            import torch
            from vllm import SamplingParams

            assert torch.cuda.device_count() >= 1, 'must be executed in CUDA'
            if not tensor_parallel_size:
                tensor_parallel_size = torch.cuda.device_count()
                logger.info(f'Set tensor_parallel_size to \
                    {tensor_parallel_size} for vllm.')
            self.model_key = prepare_model(
                model_type='vllm',
                pretrained_model_name_or_path=hf_model,
                trust_remote_code=trust_remote_code,
                tensor_parallel_size=tensor_parallel_size,
                max_model_len=max_model_len,
                max_num_seqs=max_num_seqs)
            self.sampling_params = SamplingParams(**sampling_params)
        else:
            self.model_key = prepare_model(
                model_type='opcsg_inference',
                pretrained_model_name_or_path=hf_model,
                trust_remote_code=trust_remote_code)
            self.sampling_params = sampling_params

    def _extract_qa(self, output):
        """Extract qestion and answer pair from model output response."""
        qa_list = []

        pat = re.compile(self.pattern, re.DOTALL)
        qa_pairs = pat.findall(output)

        for _, qa in enumerate(qa_pairs, 1):
            user, assistant = qa
            qa_list.append((user.strip(), assistant.strip()))

        return qa_list

    def process(self, sample, rank=None):
        model, _ = get_model(self.model_key, rank, self.use_cuda())
        logger.info(f'Process with sampling_params: {self.sampling_params}')
        if self.enable_vllm:
            response = model.generate([sample[self.text_key]],
                                      self.sampling_params)
            output = response[0].outputs[0].text
        else:
            response = model.generate(sample[self.text_key], self.sampling_params)
            output = response

        qa_list = self._extract_qa(output)

        if not len(qa_list):
            logger.info(
                'No question and answer data was extracted from this sample!')

        dialogue_data = []
        if self.qa_format == 'chatml':
            for qa in qa_list:
                dialogue_data.append({
                    'messages': [{
                        'role': 'user',
                        'content': qa[0]
                    }, {
                        'role': 'assistant',
                        'content': qa[1]
                    }]
                })
        else:
            raise ValueError(f'Not support {self.qa_format}!')

        sample[self.text_key] = json.dumps(dialogue_data, ensure_ascii=False)

        return sample

    @classmethod
    @property
    def description(cls):
        return """
    Mapper to extract question and answer pair from text samples.
    Recommended model list: [
        'alibaba-pai/pai-qwen1_5-7b-doc2qa',
    ]
    These recommended models are all trained with Chinese data
    and are suitable for Chinese.
    """

    @classmethod
    @property
    def sample(cls):
        return Sample('蒙古国的首都是乌兰巴托（Ulaanbaatar）', 
                      'Human: 请问蒙古国的首都是哪里？'
                    'Assistant: 你好，根据提供的信息，蒙古国的首都是乌兰巴托（Ulaanbaatar）')

    @classmethod
    @property
    def init_params(cls):
        return [
            Param("hf_model", DataType.STRING, {
                "alibaba-pai/pai-qwen1_5-7b-doc2qa": "alibaba-pai/pai-qwen1_5-7b-doc2qa",
            }, "alibaba-pai/pai-qwen1_5-7b-doc2qa"),
        ]