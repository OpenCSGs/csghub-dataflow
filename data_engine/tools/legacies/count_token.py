from multiprocessing import Pool

import fire
import jsonlines as jl
from loguru import logger
from tqdm import tqdm
from transformers import AutoTokenizer
import os

def count_token_single(sample, text_keys, tokenizer):
    num = 0
    for key in text_keys:
        num += len(tokenizer.tokenize(sample[key]))
    return num


def prepare_tokenizer(tokenizer_method):
    logger.info('Loading tokenizer from HuggingFace...')
    tokenizer = AutoTokenizer.from_pretrained(tokenizer_method,
                                              trust_remote_code=True)
    return tokenizer


def main(data_path,
         text_keys='text',
         tokenizer_method='EleutherAI/pythia-6.9b-deduped',
         num_proc=1):
    """
    Count the number of tokens for given dataset and tokenizer.

    :param data_path: path to the input dataset. Only support 'jsonl' now.
    :param text_keys: field keys that will be considered into token counts.
    :param tokenizer_method: name of the Hugging Face tokenizer.
    :param num_proc: number of processes to count tokens.
    """
    tokenizer = prepare_tokenizer(tokenizer_method)

    if isinstance(text_keys, str):
        text_keys = [text_keys]

    if os.path.isdir(data_path):
        files = [os.path.join(data_path, f) for f in os.listdir(data_path) if os.path.isfile(os.path.join(data_path, f)) and f.endswith(".jsonl")]
        data_path = files[0]

    with jl.open(data_path) as reader:
        token_count = 0
        result_list = []
        with Pool(num_proc) as p:
            for sample in tqdm(reader):
                result_list.append(
                    p.apply_async(count_token_single,
                                  args=(
                                      sample,
                                      text_keys,
                                      tokenizer,
                                  )))
            for res in tqdm(result_list):
                token_count += res.get()

        logger.info(f'Total num of tokens: {token_count}')


if __name__ == '__main__':
    fire.Fire(main)
