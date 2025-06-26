from typing import Dict

from loguru import logger

from data_engine.utils.availability_utils import AvailabilityChecking
from data_engine.utils.model_utils import get_model, prepare_model

from ..base_op import OPERATORS, UNFORKABLE, Mapper, Sample, Param, DataType

DEFAULT_PROMPT_TEMPLATE = """
为了输出下面代码片段，请生成对应prompt内容，该prompt应该用中文详细描述需求， 比如使用python实现什么功能。请回复：prompt=？
代码片段：
{input_data}
"""

OP_NAME = 'generate_code_qa_pair_mapper'

with AvailabilityChecking(['torch', 'transformers'], OP_NAME):
    import torch

    # avoid hanging when calling model in multiprocessing
    torch.set_num_threads(1)


@UNFORKABLE.register_module(OP_NAME)
@OPERATORS.register_module(OP_NAME)
class GenerateCodeQAPairMapper(Mapper):
    _accelerator = 'cuda'

    def __init__(self,
                 hf_model,
                 trust_remote_code: bool = True,
                 prompt_template: str = None,
                 # {'temperature': 0.2, 'top_k': 10, 'top_p': 0.95}
                 sampling_params: Dict = {
                     'temperature': 0.2, 'top_k': 10, 'top_p': 0.95},
                 *args,
                 **kwargs):
        """
        Initialization method.

        :param hf_model: Hugginface model id.
        :param trust_remote_code: passed to transformers
        :param prompt_template: Prompt template for generate samples.
            Please make sure the template contains "{augmented_data}",
            which corresponds to the augmented samples.
        :param sampling_params: Sampling parameters for text generation.
            e.g {'temperature': 0.9, 'top_p': 0.95}
        :param args: extra args
        :param kwargs: extra args
        """
        super().__init__(*args, **kwargs)
        self.num_proc = 1

        if prompt_template is None:
            prompt_template = DEFAULT_PROMPT_TEMPLATE

        self.prompt_template = prompt_template

        self.model_key = prepare_model(
            model_type='opcsg_inference',
            pretrained_model_name_or_path=hf_model,
            trust_remote_code=trust_remote_code)
        self.sampling_params = sampling_params

    def build_prompt(self, sample, prompt_template):
        return prompt_template.format(input_data=sample)

    def process(self, sample=None, rank=None):
        model, _ = get_model(self.model_key, rank=rank)
        data = sample[self.text_key]
        input_prompt = self.build_prompt(data,
                                         self.prompt_template)

        response_str = model.generate(
            message=input_prompt, sampling_params=self.sampling_params, system_prompt='You are a helpful assistant.')
        logger.debug(f'input_prompt is: {input_prompt}')
        logger.debug(f'response_str is: {response_str}')
        message_list = {self.text_key: {
            'input': response_str.replace('prompt=', ''), 'response': data}}

        return message_list

    @classmethod
    @property
    def description(cls):
        return """Mapper to generate new instruction data based on code.
    """

    @classmethod
    @property
    def sample(cls):
        return Sample('def hello_world():\n    print("Hello, World!")\nhello_world()',
                      'message:[{"input": "create hello word function by python", "response": "def hello_world():\n    print("Hello, World!")\nhello_world()" }]')

    @classmethod
    @property
    def init_params(cls):
        return [
            Param("hf_model", DataType.STRING, {
                "AIWizards/Llama2-Chinese-7b-Chat": "AIWizards/Llama2-Chinese-7b-Chat",
            }, "AIWizards/Llama2-Chinese-7b-Chat"),
            Param("prompt_template", DataType.STRING, None, None),
        ]
