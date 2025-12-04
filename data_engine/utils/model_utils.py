import fnmatch
import os
from functools import partial
from pickle import UnpicklingError
from typing import Optional, Union
import subprocess
import re

import multiprocess as mp
import wget
from loguru import logger

from data_engine import cuda_device_count, is_cuda_available

from .cache_utils import DATA_JUICER_MODELS_CACHE as DJMC
import requests
import json

MODEL_ZOO = {}

# Default cached models links for downloading
MODEL_LINKS = 'https://dail-wlcb.oss-cn-wulanchabu.aliyuncs.com/' \
               'data_juicer/models/'

# Backup cached models links for downloading
BACKUP_MODEL_LINKS = {
    # language identification model from fasttext
    'lid.176.bin':
    'https://dl.fbaipublicfiles.com/fasttext/supervised-models/',

    # tokenizer and language model for English from sentencepiece and KenLM
    '*.sp.model':
    'https://huggingface.co/edugp/kenlm/resolve/main/wikipedia/',
    '*.arpa.bin':
    'https://huggingface.co/edugp/kenlm/resolve/main/wikipedia/',

    # sentence split model from nltk punkt
    'punkt.*.pickle':
    'https://dail-wlcb.oss-cn-wulanchabu.aliyuncs.com/'
    'data_juicer/models/',
}

CSGHUBModel_LINKS = {
    "alibaba-pai/pai-qwen1_5-7b-doc2qa": "https://s-aiwizards-alibaba-pai-pai-qwen1-5-7b-doc2qa-44ve.space.opencsg.com/v1/chat/completions",
    "alibaba-pai/Qwen2-7B-Instruct-Refine": "https://s-aiwizards-qwen2-7b-instruct-refine-44vj.space.opencsg.com/v1/chat/completions",
    "AIWizards/Llama2-Chinese-7b-Chat": "https://s-aiwizards-llama2-chinese-7b-chat-3l.space.opencsg.com/v1/chat/completions",
}


def get_backup_model_link(model_name):
    for pattern, url in BACKUP_MODEL_LINKS.items():
        if fnmatch.fnmatch(model_name, pattern):
            return url
    return None


def check_model(model_name, force=False):
    """
    Check whether a model exists in DATA_JUICER_MODELS_CACHE.
    If exists, return its full path.
    Else, download it from cached models links.

    :param model_name: a specified model name
    :param force: Whether to download model forcefully or not, Sometimes
        the model file maybe incomplete for some reason, so need to
        download again forcefully.
    """
    logger.info(f'[check_model] Checking model: {model_name}, force={force}')
    
    # check for local model
    if os.path.exists(model_name):
        logger.info(f'[check_model] ✓ Found model at absolute path: {model_name}')
        return model_name

    if not os.path.exists(DJMC):
        logger.info(f'[check_model] Creating models cache directory: {DJMC}')
        os.makedirs(DJMC)

    # check if the specified model exists. If it does not exist, download it
    cached_model_path = os.path.join(DJMC, model_name)
    logger.info(f'[check_model] Expected model path: {cached_model_path}')
    
    if os.path.exists(cached_model_path):
        logger.info(f'[check_model] ✓ Found cached model (no network access needed)')
        if not force:
            return cached_model_path
    
    if force:
        if os.path.exists(cached_model_path):
            os.remove(cached_model_path)
            logger.warning(
                f'[check_model] Model [{cached_model_path}] marked invalid, force downloading...'
            )
        else:
            logger.warning(
                f'[check_model] ✗ Model [{cached_model_path}] not found. Attempting download...')

        try:
            model_link = os.path.join(MODEL_LINKS, model_name)
            logger.info(f'[check_model] ⬇ Downloading from primary link: {model_link}')
            wget.download(model_link, cached_model_path, bar=None)
            logger.info(f'[check_model] ✓ Successfully downloaded to: {cached_model_path}')
        except:  # noqa: E722
            try:
                backup_model_link = os.path.join(
                    get_backup_model_link(model_name), model_name)
                logger.warning(f'[check_model] Primary download failed, trying backup: {backup_model_link}')
                wget.download(backup_model_link, cached_model_path, bar=None)
                logger.info(f'[check_model] ✓ Successfully downloaded from backup')
            except:  # noqa: E722
                logger.error(
                    f'[check_model] ✗ Download failed for [{model_name}]. '
                    f'Please download it manually into {DJMC} '
                    f'from {model_link} or {backup_model_link} ')
                exit(1)
    return cached_model_path


def prepare_fasttext_model(model_name='lid.176.bin'):
    """
    Prepare and load a fasttext model.

    :param model_name: input model name
    :return: model instance.
    """
    import fasttext

    logger.info('Loading fasttext language identification model...')
    try:
        ft_model = fasttext.load_model(check_model(model_name))
    except:  # noqa: E722
        ft_model = fasttext.load_model(check_model(model_name, force=True))
    return ft_model


def prepare_sentencepiece_model(model_path):
    """
    Prepare and load a sentencepiece model.

    :param model_path: input model path
    :return: model instance
    """
    import sentencepiece

    logger.info(f'[prepare_sentencepiece_model] Preparing sentencepiece model: {model_path}')
    sentencepiece_model = sentencepiece.SentencePieceProcessor()
    try:
        model_file = check_model(model_path)
        logger.info(f'[prepare_sentencepiece_model] Loading model from: {model_file}')
        sentencepiece_model.load(model_file)
        logger.info(f'[prepare_sentencepiece_model] ✓ Successfully loaded sentencepiece model (no download needed)')
    except:  # noqa: E722
        logger.warning(f'[prepare_sentencepiece_model] First load attempt failed, retrying with force=True...')
        model_file = check_model(model_path, force=True)
        sentencepiece_model.load(model_file)
        logger.info(f'[prepare_sentencepiece_model] ✓ Successfully loaded sentencepiece model after download')
    return sentencepiece_model


def prepare_sentencepiece_for_lang(lang, name_pattern='{}.sp.model'):
    """
    Prepare and load a sentencepiece model for specific langauge.

    :param lang: language to render model name
    :param name_pattern: pattern to render the model name
    :return: model instance.
    """

    model_name = name_pattern.format(lang)
    return prepare_sentencepiece_model(model_name)


def prepare_kenlm_model(lang, name_pattern='{}.arpa.bin'):
    """
    Prepare and load a kenlm model.

    :param model_name: input model name in formatting syntax.
    :param lang: language to render model name
    :return: model instance.
    """
    import kenlm

    model_name = name_pattern.format(lang)

    logger.info('Loading kenlm language model...')
    try:
        kenlm_model = kenlm.Model(check_model(model_name))
    except:  # noqa: E722
        kenlm_model = kenlm.Model(check_model(model_name, force=True))
    return kenlm_model


def prepare_nltk_model(lang, name_pattern='punkt.{}.pickle'):
    """
    Prepare and load a nltk punkt model.

    :param model_name: input model name in formatting syntax
    :param lang: language to render model name
    :return: model instance.
    """
    from nltk.data import load

    nltk_to_punkt = {
        'en': 'english',
        'fr': 'french',
        'pt': 'portuguese',
        'es': 'spanish'
    }
    assert lang in nltk_to_punkt.keys(
    ), 'lang must be one of the following: {}'.format(
        list(nltk_to_punkt.keys()))
    model_name = name_pattern.format(nltk_to_punkt[lang])

    logger.info('Loading nltk punkt split model...')
    try:
        nltk_model = load(check_model(model_name))
    except:  # noqa: E722
        nltk_model = load(check_model(model_name, force=True))
    return nltk_model


def prepare_video_blip_model(pretrained_model_name_or_path,
                             return_model=True,
                             trust_remote_code=False):
    """
    Prepare and load a video-clip model with the correspoding processor.

    :param pretrained_model_name_or_path: model name or path
    :param return_model: return model or not
    :param trust_remote_code: passed to transformers
    :return: a tuple (model, input processor) if `return_model` is True;
        otherwise, only the processor is returned.
    """
    import torch
    import torch.nn as nn
    from transformers import (AutoModelForCausalLM, AutoModelForSeq2SeqLM,
                              Blip2Config, Blip2ForConditionalGeneration,
                              Blip2QFormerModel, Blip2VisionModel)
    from transformers.modeling_outputs import BaseModelOutputWithPooling

    class VideoBlipVisionModel(Blip2VisionModel):
        """A simple, augmented version of Blip2VisionModel to handle
        videos."""

        def forward(
            self,
            pixel_values: Optional[torch.FloatTensor] = None,
            output_attentions: Optional[bool] = None,
            output_hidden_states: Optional[bool] = None,
            return_dict: Optional[bool] = None,
        ) -> Union[tuple, BaseModelOutputWithPooling]:
            """Flatten `pixel_values` along the batch and time dimension,
            pass it through the original vision model,
            then unflatten it back.

            :param pixel_values: a tensor of shape
            (batch, channel, time, height, width)

            :returns:
                last_hidden_state: a tensor of shape
                (batch, time * seq_len, hidden_size)
                pooler_output: a tensor of shape
                (batch, time, hidden_size)
                hidden_states:
                    a tuple of tensors of shape
                    (batch, time * seq_len, hidden_size),
                    one for the output of the embeddings +
                    one for each layer
                attentions:
                    a tuple of tensors of shape
                    (batch, time, num_heads, seq_len, seq_len),
                    one for each layer
            """
            if pixel_values is None:
                raise ValueError('You have to specify pixel_values')

            batch, _, time, _, _ = pixel_values.size()

            # flatten along the batch and time dimension to create a
            # tensor of shape
            # (batch * time, channel, height, width)
            flat_pixel_values = pixel_values.permute(0, 2, 1, 3,
                                                     4).flatten(end_dim=1)

            vision_outputs: BaseModelOutputWithPooling = super().forward(
                pixel_values=flat_pixel_values,
                output_attentions=output_attentions,
                output_hidden_states=output_hidden_states,
                return_dict=True,
            )

            # now restore the original dimensions
            # vision_outputs.last_hidden_state is of shape
            # (batch * time, seq_len, hidden_size)
            seq_len = vision_outputs.last_hidden_state.size(1)
            last_hidden_state = vision_outputs.last_hidden_state.view(
                batch, time * seq_len, -1)
            # vision_outputs.pooler_output is of shape
            # (batch * time, hidden_size)
            pooler_output = vision_outputs.pooler_output.view(batch, time, -1)
            # hidden_states is a tuple of tensors of shape
            # (batch * time, seq_len, hidden_size)
            hidden_states = (tuple(
                hidden.view(batch, time * seq_len, -1)
                for hidden in vision_outputs.hidden_states)
                             if vision_outputs.hidden_states is not None else
                             None)
            # attentions is a tuple of tensors of shape
            # (batch * time, num_heads, seq_len, seq_len)
            attentions = (tuple(
                hidden.view(batch, time, -1, seq_len, seq_len)
                for hidden in vision_outputs.attentions)
                          if vision_outputs.attentions is not None else None)
            if return_dict:
                return BaseModelOutputWithPooling(
                    last_hidden_state=last_hidden_state,
                    pooler_output=pooler_output,
                    hidden_states=hidden_states,
                    attentions=attentions,
                )
            return (last_hidden_state, pooler_output, hidden_states,
                    attentions)

    class VideoBlipForConditionalGeneration(Blip2ForConditionalGeneration):

        def __init__(self, config: Blip2Config) -> None:
            # HACK: we call the grandparent super().__init__() to bypass
            # Blip2ForConditionalGeneration.__init__() so we can replace
            # self.vision_model
            super(Blip2ForConditionalGeneration, self).__init__(config)

            self.vision_model = VideoBlipVisionModel(config.vision_config)

            self.query_tokens = nn.Parameter(
                torch.zeros(1, config.num_query_tokens,
                            config.qformer_config.hidden_size))
            self.qformer = Blip2QFormerModel(config.qformer_config)

            self.language_projection = nn.Linear(
                config.qformer_config.hidden_size,
                config.text_config.hidden_size)
            if config.use_decoder_only_language_model:
                language_model = AutoModelForCausalLM.from_config(
                    config.text_config)
            else:
                language_model = AutoModelForSeq2SeqLM.from_config(
                    config.text_config)
            self.language_model = language_model

            # Initialize weights and apply final processing
            self.post_init()

    from transformers import AutoProcessor
    processor = AutoProcessor.from_pretrained(
        pretrained_model_name_or_path, trust_remote_code=trust_remote_code)
    if return_model:
        model_class = VideoBlipForConditionalGeneration
        model = model_class.from_pretrained(
            pretrained_model_name_or_path, trust_remote_code=trust_remote_code)
    return (model, processor) if return_model else processor


def prepare_simple_aesthetics_model(pretrained_model_name_or_path,
                                    return_model=True,
                                    trust_remote_code=False):
    """
    Prepare and load a simple aesthetics model.

    :param pretrained_model_name_or_path: model name or path
    :param return_model: return model or not
    :return: a tuple (model, input processor) if `return_model` is True;
        otherwise, only the processor is returned.
    """
    from aesthetics_predictor import (AestheticsPredictorV1,
                                      AestheticsPredictorV2Linear,
                                      AestheticsPredictorV2ReLU)
    from transformers import CLIPProcessor

    processor = CLIPProcessor.from_pretrained(
        pretrained_model_name_or_path, trust_remote_code=trust_remote_code)
    if not return_model:
        return processor
    else:
        if 'v1' in pretrained_model_name_or_path:
            model = AestheticsPredictorV1.from_pretrained(
                pretrained_model_name_or_path,
                trust_remote_code=trust_remote_code)
        elif ('v2' in pretrained_model_name_or_path
              and 'linear' in pretrained_model_name_or_path):
            model = AestheticsPredictorV2Linear.from_pretrained(
                pretrained_model_name_or_path,
                trust_remote_code=trust_remote_code)
        elif ('v2' in pretrained_model_name_or_path
              and 'relu' in pretrained_model_name_or_path):
            model = AestheticsPredictorV2ReLU.from_pretrained(
                pretrained_model_name_or_path,
                trust_remote_code=trust_remote_code)
        else:
            raise ValueError(
                'Not support {}'.format(pretrained_model_name_or_path))
        return (model, processor)


def prepare_huggingface_model(pretrained_model_name_or_path,
                              return_model=True,
                              trust_remote_code=False):
    """
    Prepare and load a HuggingFace model with the correspoding processor.

    :param pretrained_model_name_or_path: model name or path
    :param return_model: return model or not
    :param trust_remote_code: passed to transformers
    :return: a tuple (model, input processor) if `return_model` is True;
        otherwise, only the processor is returned.
    """
    import transformers
    from transformers import AutoConfig, AutoProcessor, AutoTokenizer

    if return_model:
        processor = AutoProcessor.from_pretrained(
            pretrained_model_name_or_path, trust_remote_code=trust_remote_code)
        config = AutoConfig.from_pretrained(
            pretrained_model_name_or_path, trust_remote_code=trust_remote_code)
        if hasattr(config, 'auto_map'):
            class_name = next(
                (k for k in config.auto_map if k.startswith('AutoModel')),
                'AutoModel')
        else:
            # TODO: What happens if more than one
            class_name = config.architectures[0]

        model_class = getattr(transformers, class_name)
        model = model_class.from_pretrained(
            pretrained_model_name_or_path, trust_remote_code=trust_remote_code)

        return (model, processor)
    else:
        # For text processing tasks, use AutoTokenizer
        # Since we download models from OpenCSG via git clone, we should only use local files
        # Transformers library can load models from local paths without downloading from HuggingFace Hub
        if os.path.exists(pretrained_model_name_or_path) and os.path.isdir(pretrained_model_name_or_path):
            # Local path exists (downloaded from OpenCSG), load with local_files_only=True to ensure no HuggingFace downloads
            try:
                tokenizer = AutoTokenizer.from_pretrained(
                    pretrained_model_name_or_path,
                    trust_remote_code=trust_remote_code,
                    local_files_only=True
                )
                return tokenizer
            except Exception as e:
                # If loading fails, it might be missing some files in the git clone
                # Check if essential files exist, if not, raise error instead of falling back to HuggingFace
                logger.error(f'Failed to load tokenizer from local path {pretrained_model_name_or_path}: {str(e)}')
                logger.error('Model files may be incomplete. Please check the downloaded model directory.')
                # List files in directory to help debug
                try:
                    files = os.listdir(pretrained_model_name_or_path)
                    logger.error(f'Files in model directory: {files[:10]}')  # Show first 10 files
                except:
                    pass
                raise RuntimeError(
                    f'Failed to load tokenizer from local path {pretrained_model_name_or_path}. '
                    f'This should not download from HuggingFace. Error: {str(e)}'
                )
        else:
            # Not a local path - this shouldn't happen if model was downloaded from OpenCSG
            # But if it does, still try to load (might be a HuggingFace model name as fallback)
            logger.warning(f'Model path does not exist locally: {pretrained_model_name_or_path}')
            tokenizer = AutoTokenizer.from_pretrained(
                pretrained_model_name_or_path, trust_remote_code=trust_remote_code)
            return tokenizer


def prepare_vllm_model(pretrained_model_name_or_path,
                       return_model=True,
                       trust_remote_code=False,
                       tensor_parallel_size=1,
                       max_model_len=None,
                       max_num_seqs=256):
    """
    Prepare and load a HuggingFace model with the correspoding processor.

    :param pretrained_model_name_or_path: model name or path
    :param return_model: return model or not
    :param trust_remote_code: passed to transformers
    :param tensor_parallel_size: The number of GPUs to use for distributed
        execution with tensor parallelism.
    :param max_model_len: Model context length. If unspecified, will
        be automatically derived from the model config.
    :param max_num_seqs: Maximum number of sequences to be processed in a
        single iteration.
    :return: a tuple (model, input processor) if `return_model` is True;
        otherwise, only the processor is returned.
    """
    from transformers import AutoProcessor
    from vllm import LLM as vLLM

    processor = AutoProcessor.from_pretrained(
        pretrained_model_name_or_path, trust_remote_code=trust_remote_code)

    if return_model:
        import torch
        model = vLLM(model=pretrained_model_name_or_path,
                     trust_remote_code=trust_remote_code,
                     dtype=torch.float16,
                     tensor_parallel_size=tensor_parallel_size,
                     max_model_len=max_model_len,
                     max_num_seqs=max_num_seqs)

    return (model, processor) if return_model else processor


def prepare_spacy_model(lang, name_pattern='{}_core_web_md-3.7.0'):
    """
    Prepare spacy model for specific language.

    :param lang: language of sapcy model. Should be one of ["zh",
        "en"]
    :return: corresponding spacy model
    """
    import spacy

    assert lang in ['zh', 'en'], 'Diversity only support zh and en'
    model_name = name_pattern.format(lang)
    logger.info(f'Loading spacy model [{model_name}]...')
    compressed_model = '{}.tar.gz'.format(model_name)

    # decompress the compressed model if it's not decompressed
    def decompress_model(compressed_model_path):
        if not compressed_model_path.endswith('.tar.gz'):
            raise ValueError('Only .tar.gz files are supported')

        decompressed_model_path = compressed_model_path.replace('.tar.gz', '')
        if os.path.exists(decompressed_model_path) \
                and os.path.isdir(decompressed_model_path):
            return decompressed_model_path

        ver_name = os.path.basename(decompressed_model_path)
        unver_name = ver_name.rsplit('-', maxsplit=1)[0]
        target_dir_in_archive = f'{ver_name}/{unver_name}/{ver_name}/'

        import tarfile
        with tarfile.open(compressed_model_path, 'r:gz') as tar:
            for member in tar.getmembers():
                if member.name.startswith(target_dir_in_archive):
                    # relative path without unnecessary directory levels
                    relative_path = os.path.relpath(
                        member.name, start=target_dir_in_archive)
                    target_path = os.path.join(decompressed_model_path,
                                               relative_path)

                    if member.isfile():
                        # ensure the directory exists
                        target_directory = os.path.dirname(target_path)
                        os.makedirs(target_directory, exist_ok=True)
                        # for files, extract to the specific location
                        with tar.extractfile(member) as source:
                            with open(target_path, 'wb') as target:
                                target.write(source.read())
        return decompressed_model_path

    try:
        diversity_model = spacy.load(
            decompress_model(check_model(compressed_model)))
    except:  # noqa: E722
        diversity_model = spacy.load(
            decompress_model(check_model(compressed_model, force=True)))
    return diversity_model


def prepare_diffusion_model(pretrained_model_name_or_path,
                            diffusion_type,
                            torch_dtype='fp32',
                            revision='main',
                            trust_remote_code=False):
    """
        Prepare and load an Diffusion model from HuggingFace.

        :param pretrained_model_name_or_path: input Diffusion model name
            or local path to the model
        :param diffusion_type: the use of the diffusion model. It can be
            'image2image', 'text2image', 'inpainting'
        :param torch_dtype: the floating point to load the diffusion
            model. Can be one of ['fp32', 'fp16', 'bf16']
        :param revision: The specific model version to use. It can be a
            branch name, a tag name, a commit id, or any identifier allowed
            by Git.
        :return: a Diffusion model.
    """
    import torch
    from diffusers import (AutoPipelineForImage2Image,
                           AutoPipelineForInpainting,
                           AutoPipelineForText2Image)

    diffusion_type_to_pipeline = {
        'image2image': AutoPipelineForImage2Image,
        'text2image': AutoPipelineForText2Image,
        'inpainting': AutoPipelineForInpainting
    }

    if diffusion_type not in diffusion_type_to_pipeline.keys():
        raise ValueError(
            f'Not support {diffusion_type} diffusion_type for diffusion '
            'model. Can only be one of '
            '["image2image", "text2image", "inpainting"].')

    if torch_dtype not in ['fp32', 'fp16', 'bf16']:
        raise ValueError(
            f'Not support {torch_dtype} torch_dtype for diffusion '
            'model. Can only be one of '
            '["fp32", "fp16", "bf16"].')

    if not is_cuda_available() and (torch_dtype == 'fp16'
                                    or torch_dtype == 'bf16'):
        raise ValueError(
            'In cpu mode, only fp32 torch_dtype can be used for diffusion'
            ' model.')

    pipeline = diffusion_type_to_pipeline[diffusion_type]
    if torch_dtype == 'bf16':
        torch_dtype = torch.bfloat16
    elif torch_dtype == 'fp16':
        torch_dtype = torch.float16
    else:
        torch_dtype = torch.float32

    model = pipeline.from_pretrained(pretrained_model_name_or_path,
                                     revision=revision,
                                     torch_dtype=torch_dtype,
                                     trust_remote_code=trust_remote_code)

    return model


def prepare_recognizeAnything_model(
        pretrained_model_name_or_path='ram_plus_swin_large_14m.pth',
        input_size=384):
    """
    Prepare and load recognizeAnything model.

    :param model_name: input model name.
    :param input_size: the input size of the model.
    """
    from ram.models import ram_plus
    logger.info('Loading recognizeAnything model...')
    try:
        model = ram_plus(pretrained=check_model(pretrained_model_name_or_path),
                         image_size=input_size,
                         vit='swin_l')
    except (RuntimeError, UnpicklingError) as e:  # noqa: E722
        logger.warning(e)
        model = ram_plus(pretrained=check_model(pretrained_model_name_or_path,
                                                force=True),
                         image_size=input_size,
                         vit='swin_l')
    model.eval()
    return model


def prepare_opencv_classifier(model_path):
    import cv2
    model = cv2.CascadeClassifier(model_path)
    return model

SAMPLING_PARAMS = {
    "temperature": 0.2,
    "max_tokens": 2000,
    "top_k": 10,
    "top_p": 0.9,
    "repetition_penalty": 1
}
class CSGHUBModel:
    def __init__(self, url: str, pretrained_model_name_or_path: str):
        self.url = url
        self.pretrained_model_name_or_path = pretrained_model_name_or_path

    def generate(self, message: str, sampling_params: dict, system_prompt: str=None):
        # invoke model via csghub inference
        headers = {
            'Content-Type': 'application/json'
        }
        data = {
            # TODO mapping to csghub model id
            "model": self.pretrained_model_name_or_path,
            "messages": [
                {
                    "role": "user",
                    "content": message,
                }
            ],
            "stream": False,
        }

        data = {**data, **sampling_params} if sampling_params else {
            **data, **SAMPLING_PARAMS
        }

        # Handling system content
        system = {
            "role": "system",
            "content": system_prompt,
        }
        if system_prompt:
            data["messages"].insert(0, system)

        response = requests.post(url=self.url, json=data, headers=headers, stream=False)
        text = json.loads(response.text)["choices"][0]["message"]["content"]

        response.raise_for_status()
        return text

def prepare_opencsg_inference(pretrained_model_name_or_path,
                              return_model=True,
                              trust_remote_code=False):
    assert (pretrained_model_name_or_path in CSGHUBModel_LINKS.keys()
            ), 'model must be one of the following: {}'.format(
                list(CSGHUBModel_LINKS.keys()))
    
    url = CSGHUBModel_LINKS[pretrained_model_name_or_path]
    model = CSGHUBModel(url, pretrained_model_name_or_path)
    
    return (model, None) if return_model else None


def get_opencsg_model_path(model_name: str, cache_dir: Optional[str] = None) -> str:
    """
    Get model's http_clone_url from OpenCSG Hub API and download the model to local.
    
    :param model_name: Model name, e.g., "Qwen3-0.6B" or "bert-base-chinese"
    :param cache_dir: Cache directory, if None, use default DATA_JUICER_MODELS_CACHE
    :return: Local model path
    """
    if cache_dir is None:
        cache_dir = DJMC
    
    # Ensure cache directory exists
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir, exist_ok=True)
    
    # Check if model is already downloaded
    model_cache_path = os.path.join(cache_dir, model_name.replace('/', '_'))
    if os.path.exists(model_cache_path) and os.path.isdir(model_cache_path):
        # Check if it's a valid git repository
        git_dir = os.path.join(model_cache_path, '.git')
        if os.path.exists(git_dir):
            logger.info(f'Model {model_name} already exists in cache: {model_cache_path}')
            return model_cache_path
    
    # Get model information from OpenCSG API
    # Use environment variable for endpoint, consistent with model_validator.py
    csghub_endpoint = os.getenv('CSGHUB_ENDPOINT', 'https://hub.opencsg.com')
    api_url = f'{csghub_endpoint}/api/v1/models'
    params = {
        'page': 1,
        'per': 1,
        'search': model_name,
        'sort': 'trending',
        'source': ''
    }
    
    try:
        logger.info(f'Using endpoint: {csghub_endpoint}')
        logger.info(f'Searching for model from OpenCSG Hub API: {model_name}')
        response = requests.get(api_url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        if not data.get('data') or len(data['data']) == 0:
            raise ValueError(f'Model not found: {model_name}')
        
        model_info = data['data'][0]
        repository = model_info.get('repository', {})
        http_clone_url = repository.get('http_clone_url')
        
        if not http_clone_url:
            raise ValueError(f'Model {model_name} has no http_clone_url')
        
        logger.info(f'Found git URL for model {model_name}: {http_clone_url}')
        
        # Download model using git clone
        logger.info(f'Downloading model to: {model_cache_path}')
        if os.path.exists(model_cache_path):
            # If directory exists but is not a git repo, remove it
            if not os.path.exists(os.path.join(model_cache_path, '.git')):
                logger.info(f'Removing existing non-git directory: {model_cache_path}')
                import shutil
                shutil.rmtree(model_cache_path)
            else:
                # If it's a git repo, try to update
                logger.info(f'Detected existing git repository, attempting to update...')
                try:
                    result = subprocess.run(['git', 'pull'], cwd=model_cache_path, 
                                         check=True, capture_output=True, text=True, timeout=300)
                    logger.info(f'Model {model_name} updated')
                    logger.debug(f'Git pull output: {result.stdout}')
                    return model_cache_path
                except subprocess.CalledProcessError as e:
                    logger.warning(f'Failed to update model: {e.stderr or e.stdout}, will re-clone')
                    import shutil
                    shutil.rmtree(model_cache_path)
                except subprocess.TimeoutExpired:
                    logger.warning(f'Update timeout, will re-clone')
                    import shutil
                    shutil.rmtree(model_cache_path)
        
        # Clone repository with real-time output for progress tracking
        logger.info(f'Starting to clone repository: {http_clone_url}')
        try:
            # Set git environment variables to avoid interactive prompts
            env = os.environ.copy()
            env['GIT_TERMINAL_PROMPT'] = '0'  # Disable terminal prompts
            env['GIT_ASKPASS'] = 'echo'  # Use echo as password prompt to avoid hanging
            env['GIT_LFS_SKIP_SMUDGE'] = '1'  # Skip LFS file download - we only need tokenizer files
            
            # Use Popen for real-time output and timeout control
            import threading
            import queue
            import time
            
            output_queue = queue.Queue()
            
            def read_output(pipe, queue_obj):
                """Read output from pipe and put into queue"""
                try:
                    for line in iter(pipe.readline, ''):
                        if line:
                            queue_obj.put(line.strip())
                    pipe.close()
                except Exception as e:
                    queue_obj.put(f'Error reading output: {str(e)}')
            
            logger.info('Cloning git repository...')
            process = subprocess.Popen(
                ['git', 'clone', '--progress', '--verbose', http_clone_url, model_cache_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
                env=env
            )
            
            # Start output reading thread
            output_thread = threading.Thread(target=read_output, args=(process.stdout, output_queue))
            output_thread.daemon = True
            output_thread.start()
            
            # Wait for process to complete, max 10 minutes
            start_time = time.time()
            timeout_seconds = 600  # 10 minutes
            last_log_time = start_time
            
            output_lines = []
            clone_completed = False
            no_output_count = 0
            max_no_output_count = 10  # If no output for 5 seconds (10 * 0.5s), consider clone done
            
            while process.poll() is None:
                # Check timeout
                elapsed = time.time() - start_time
                if elapsed > timeout_seconds:
                    logger.error(f'Download timeout, terminating process...')
                    try:
                        process.kill()
                        process.wait(timeout=5)
                    except:
                        pass
                    raise RuntimeError(f'Model download timeout (exceeded {timeout_seconds} seconds): {model_name}')
                
                # Read output queue
                has_output = False
                try:
                    while True:
                        line = output_queue.get_nowait()
                        if line:
                            logger.info(f'Git clone: {line}')
                            output_lines.append(line)
                            last_log_time = time.time()
                            has_output = True
                            no_output_count = 0  # Reset counter
                            # Check if clone is completed
                            if 'done' in line.lower() or 'complete' in line.lower() or 'checkout' in line.lower():
                                clone_completed = True
                                # Immediately check if files exist - if yes, we can proceed
                                if os.path.exists(model_cache_path):
                                    files_in_dir = [f for f in os.listdir(model_cache_path) if f != '.git' and not f.startswith('.')]
                                    if files_in_dir:
                                        # Clone is done and files exist, wait a bit then exit
                                        logger.info('Git clone completed and files detected, proceeding...')
                                        time.sleep(1)  # Brief wait for process to finish
                                        if process.poll() is None:
                                            # Process still running (likely stuck on LFS), terminate it
                                            logger.info('Terminating git process (files already available, no need to wait for LFS)')
                                            try:
                                                process.terminate()
                                                process.wait(timeout=2)
                                            except:
                                                try:
                                                    process.kill()
                                                except:
                                                    pass
                                        break  # Exit the while loop
                except queue.Empty:
                    pass
                
                # If no output, increment counter
                if not has_output:
                    no_output_count += 1
                
                # If clone completed and no output for a while, check if files exist and exit
                if clone_completed and no_output_count >= max_no_output_count:
                    # Check if we have files (not just .git directory)
                    if os.path.exists(model_cache_path):
                        files_in_dir = [f for f in os.listdir(model_cache_path) if f != '.git' and not f.startswith('.')]
                        if files_in_dir:
                            logger.info('Git clone appears completed (no output for 5s), checking files and proceeding...')
                            # Give process a moment to finish, then break
                            time.sleep(2)
                            if process.poll() is None:
                                # Process still running but no output, likely stuck on LFS
                                logger.warning('Git clone process still running but no output. Terminating to proceed with available files.')
                                try:
                                    process.terminate()
                                    process.wait(timeout=3)
                                except:
                                    try:
                                        process.kill()
                                    except:
                                        pass
                            break
                
                # If no output for more than 30 seconds, log warning
                if time.time() - last_log_time > 30 and last_log_time > start_time:
                    elapsed_seconds = int(time.time() - start_time)
                    if process.poll() is None:
                        logger.warning(f'Git clone has been running for {elapsed_seconds} seconds, still downloading... (downloaded: {len(output_lines)} lines)')
                    last_log_time = time.time()
                
                time.sleep(0.5)  # Avoid high CPU usage
            
            # Read remaining output
            output_thread.join(timeout=5)
            try:
                while True:
                    line = output_queue.get_nowait()
                    if line:
                        logger.info(f'Git clone: {line}')
                        output_lines.append(line)
            except queue.Empty:
                pass
            
            # Check if clone succeeded or if only LFS files failed
            clone_failed = process.returncode != 0
            lfs_error = any('lfs' in line.lower() or 'smudge' in line.lower() for line in output_lines)
            
            # Verify download success
            if not os.path.exists(model_cache_path) or not os.path.exists(os.path.join(model_cache_path, '.git')):
                raise RuntimeError(f'Git clone failed: directory is invalid: {model_cache_path}')
            
            # Check if we have actual files (not just .git directory)
            files_in_dir = [f for f in os.listdir(model_cache_path) if f != '.git' and not f.startswith('.')]
            if not files_in_dir:
                logger.warning('No files found after clone, attempting checkout...')
                try:
                    # Try to checkout files, but skip LFS files if they fail
                    # Use GIT_LFS_SKIP_SMUDGE to skip LFS file download
                    env_checkout = env.copy()
                    env_checkout['GIT_LFS_SKIP_SMUDGE'] = '1'  # Skip LFS smudge filter
                    checkout_result = subprocess.run(
                        ['git', 'checkout', 'HEAD', '--', '.'],
                        cwd=model_cache_path,
                        env=env_checkout,
                        capture_output=True,
                        text=True,
                        timeout=300
                    )
                    if checkout_result.returncode == 0:
                        logger.info('Files checked out successfully (skipped LFS files)')
                    else:
                        logger.warning(f'Checkout failed: {checkout_result.stderr}')
                except Exception as e:
                    logger.warning(f'Checkout failed: {str(e)}')
            
            # Skip Git LFS download - we only need tokenizer files, not model weights
            # This saves time and space. Tokenizer files are usually small and not in LFS
            logger.info('Skipping Git LFS download - only tokenizer files are needed, not model weights')
            
            # Verify that we have at least some tokenizer files
            files_in_dir = [f for f in os.listdir(model_cache_path) if f != '.git' and not f.startswith('.')]
            tokenizer_files = [f for f in files_in_dir if any(keyword in f.lower() for keyword in 
                            ['tokenizer', 'vocab', 'config.json', 'merges', 'special_tokens'])]
            
            if not tokenizer_files:
                if clone_failed and lfs_error:
                    # If clone failed due to LFS and we have no tokenizer files, it's a real error
                    error_msg = '\n'.join(output_lines[-10:]) if output_lines else 'No output'
                    raise RuntimeError(
                        f'Git clone failed and no tokenizer files found (return code: {process.returncode}). '
                        f'This may be due to Git LFS download failure. Error: {error_msg}'
                    )
                else:
                    logger.warning('No tokenizer files found in downloaded model directory')
                    logger.info(f'Available files: {files_in_dir[:10]}')  # Show first 10 files
            else:
                logger.info(f'Found tokenizer files: {tokenizer_files[:5]}')  # Show first 5 files
                # Even if Git LFS failed, we can still use the model if tokenizer files exist
                if clone_failed and lfs_error:
                    logger.warning('Git LFS download failed, but tokenizer files are available. Continuing...')
            
            logger.info(f'Model {model_name} download completed: {model_cache_path}')
            return model_cache_path
            
        except FileNotFoundError:
            raise RuntimeError(f'Git command not found, please ensure git is installed')
        
    except requests.RequestException as e:
        raise RuntimeError(f'Failed to request OpenCSG API: {str(e)}')
    except subprocess.TimeoutExpired:
        raise RuntimeError(f'Model download timeout: {model_name}')
    except Exception as e:
        raise RuntimeError(f'Failed to download model: {str(e)}')

MODEL_FUNCTION_MAPPING = {
    'fasttext': prepare_fasttext_model,
    'sentencepiece': prepare_sentencepiece_for_lang,
    'kenlm': prepare_kenlm_model,
    'nltk': prepare_nltk_model,
    'huggingface': prepare_huggingface_model,
    'simple_aesthetics': prepare_simple_aesthetics_model,
    'spacy': prepare_spacy_model,
    'diffusion': prepare_diffusion_model,
    'video_blip': prepare_video_blip_model,
    'recognizeAnything': prepare_recognizeAnything_model,
    'vllm': prepare_vllm_model,
    'opencv_classifier': prepare_opencv_classifier,
    'opcsg_inference': prepare_opencsg_inference,
}


def prepare_model(model_type, **model_kwargs):
    assert (model_type in MODEL_FUNCTION_MAPPING.keys()
            ), 'model_type must be one of the following: {}'.format(
                list(MODEL_FUNCTION_MAPPING.keys()))
    global MODEL_ZOO
    model_func = MODEL_FUNCTION_MAPPING[model_type]
    model_key = partial(model_func, **model_kwargs)
    return model_key


def move_to_cuda(model, rank):
    # Assuming model can be either a single module or a tuple of modules
    if not isinstance(model, tuple):
        model = (model, )

    for module in model:
        if callable(getattr(module, 'to', None)):
            logger.debug(
                f'Moving {module.__class__.__name__} to CUDA device {rank}')
            module.to(f'cuda:{rank}')


def get_model(model_key=None, rank=None, use_cuda=False):
    if model_key is None:
        return None

    global MODEL_ZOO
    if model_key not in MODEL_ZOO:
        logger.debug(
            f'{model_key} not found in MODEL_ZOO ({mp.current_process().name})'
        )
        MODEL_ZOO[model_key] = model_key()
    if use_cuda:
        rank = 0 if rank is None else rank
        rank = rank % cuda_device_count()
        move_to_cuda(MODEL_ZOO[model_key], rank)
    return MODEL_ZOO[model_key]
