from typing import Dict

from loguru import logger

from data_engine.ops.base_op import OPERATORS, UNFORKABLE, Mapper, Sample, Param, DataType
from data_engine.utils.availability_utils import AvailabilityChecking
from data_engine.utils.model_utils import get_model, prepare_model

DEFAULT_SYSTEM_PROMPT = '请优化这个指令，将其修改为一个更详细具体的指令。'

OP_NAME = 'optimize_instruction_mapper'

with AvailabilityChecking(['torch', 'transformers'], OP_NAME):
    import torch
    import transformers  # noqa: F401

    # avoid hanging when calling model in multiprocessing
    torch.set_num_threads(1)


# TODO: Extend LLM-based OPs into API-based implementation.
@UNFORKABLE.register_module(OP_NAME)
@OPERATORS.register_module(OP_NAME)
class OptimizeInstructionMapper(Mapper):
    """Mapper to optimize instruction.
    Recommended model list: [
        alibaba-pai/Qwen2-7B-Instruct-Refine
    ]
    """
    _accelerator = 'cuda'

    def __init__(self,
                 hf_model: str = 'alibaba-pai/Qwen2-7B-Instruct-Refine',
                 trust_remote_code: bool = False,
                 system_prompt: str = None,
                 enable_vllm: bool = False,
                 tensor_parallel_size: int = None,
                 max_model_len: int = None,
                 max_num_seqs: int = 256,
                 sampling_params: Dict = {'temperature': 0.1},
                 *args,
                 **kwargs):
        """
        Initialization method.
        :param hf_model: Hugginface model id.
        :param trust_remote_code: passed to transformers
        :param system_prompt: System prompt for optimize samples.
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
        """
        super().__init__(*args, **kwargs)
        self.num_proc = 1

        if system_prompt is None:
            system_prompt = DEFAULT_SYSTEM_PROMPT
        self.system_prompt = system_prompt
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

    def process(self, sample=None, rank=None):
        model, _ = get_model(self.model_key, rank=rank)
        logger.info(f'Process with sampling_params: {self.sampling_params}')
        if self.enable_vllm:
            pass
        else:
            response = model.generate(sample[self.text_key], self.sampling_params, self.system_prompt)
            output = response

        sample[self.text_key] = output

        return sample

    @classmethod
    @property
    def description(cls):
        return """Mapper to optimize instruction."""

    @classmethod
    @property
    def sample(cls):
        return Sample('鱼香肉丝怎么做？',
                    '请提供一份完整的“鱼香肉丝”食谱，包括以下详细信息：'
                    '所需材料清单：请列出所有必要的主料和辅料，包括肉的种类和处理方式，以及所有蔬菜和调味料的具体量。'
                    '准备工作指南：描述准备工作的具体步骤，如肉丝的腌制过程、蔬菜的切割技巧等。'
                    '详细烹饪步骤：请按照烹饪的逻辑顺序，逐步解释如何将材料炒制成鱼香肉丝，包括火候控制、调味料添加的时机等详细操作。'
                    '盛盘和陈设建议：给出如何将完成的鱼香肉丝装盘摆放，以及可以搭配的其他菜品或饭类推荐，以便提升整体用餐体验。'
                    '附加小贴士：如有任何专业小窍门或注意事项，例如如何切肉更易入味，或特定调味料的选择建议等，也请一并提供。')

    @classmethod
    @property
    def init_params(cls):
        return [
            Param("hf_model", DataType.STRING, {
                "alibaba-pai/Qwen2-7B-Instruct-Refine": "alibaba-pai/Qwen2-7B-Instruct-Refine",
            }, "alibaba-pai/Qwen2-7B-Instruct-Refine"),
        ]