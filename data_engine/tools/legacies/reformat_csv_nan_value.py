# This tool is used to reformat csv or tsv files which may contain Nan values
# in some field to several jsonl files.

import os
import pathlib
from multiprocessing import Pool

import fire
from datasets import Dataset
from tqdm import tqdm


def reformat_nan_value(fp, jsonl_fp, keep_default_na, kwargs):
    """
    Reformat a csv/tsv file with kwargs (Legacy mode - full load).
    :param fp: a csv/tsv file
    :param jsonl_fp: path to save jsonl file
    :param keep_default_na: if False, no string will be parsed as NaN,
            otherwise only the default NaN values are used for parsing.
    :param kwargs: for tsv file,  kwargs["sep"] is `\t`
    """
    ds = Dataset.from_csv(fp, keep_default_na=keep_default_na, **kwargs)
    ds.to_json(jsonl_fp, force_ascii=False)


def reformat_nan_value_streaming(fp, jsonl_fp, keep_default_na, kwargs, batch_size=100):
    """
    Reformat a csv/tsv file with kwargs (Streaming mode - true streaming with pandas chunks).
    :param fp: a csv/tsv file
    :param jsonl_fp: path to save jsonl file
    :param keep_default_na: if False, no string will be parsed as NaN
    :param kwargs: for tsv file, kwargs["sep"] is `\t`
    :param batch_size: number of rows to read in each chunk
    """
    import jsonlines
    import pandas as pd
    
    # First pass: count total rows for progress bar (fast, doesn't load data)
    print(f"Counting rows in {os.path.basename(fp)}...")
    total_rows = sum(1 for _ in open(fp, 'r', encoding='utf-8')) - 1  # -1 for header
    total_batches = (total_rows + batch_size - 1) // batch_size
    
    print(f"Processing {os.path.basename(fp)}: {total_rows:,} rows in {total_batches} batches (batch_size={batch_size})")
    
    # Streaming read with pandas in chunks
    with jsonlines.open(jsonl_fp, 'w') as writer:
        with tqdm(total=total_rows, desc="Streaming processing", unit="row") as pbar:
            # Use pandas to read CSV in chunks
            chunk_iterator = pd.read_csv(
                fp,
                sep=kwargs.get('sep', ','),
                chunksize=batch_size,
                keep_default_na=keep_default_na,
                encoding='utf-8'
            )
            
            for chunk_df in chunk_iterator:
                # Convert DataFrame chunk to Dataset for consistency
                chunk_ds = Dataset.from_pandas(chunk_df, preserve_index=False)
                
                # Write chunk to jsonl
                for item in chunk_ds:
                    writer.write(dict(item))
                
                pbar.update(len(chunk_df))
    
    print(f"✓ Completed: {total_rows:,} rows processed")


def fp_iter(src_dir, suffix):
    """
    Find all files endswith the specified suffix in the source directory.
    :param src_dir: path to source dataset directory
    :return: iterator over files,
    """
    for fp in pathlib.Path(src_dir).glob(f'*{suffix}'):
        yield fp


def main(src_dir,
         target_dir,
         suffixes=['.csv'],
         is_tsv=False,
         keep_default_na=False,
         num_proc=1,
         processing_mode='legacy',
         batch_size=100,
         **kwargs):
    """
    Reformat csv or tsv files that may contain Nan values using HuggingFace
    to load with extra args, e.g. set `keep_default_na` to False
    :param src_dir: path that stores filenames like "*.csv" or "*.tsv".
    :param target_dir: path to store the converted jsonl files.
    :param suffixes: files with suffixes to process, multi-suffixes args
                   like `--suffixes "'.tsv', '.csv'"`
    :param is_tsv: if True, sep will be set to '\t'. Default ','.
    :param keep_default_na: if False, no strings will be parsed as NaN,
                otherwise only the default NaN values are used for parsing.
    :param num_proc: number of process workers, Default 1. (Only used in legacy mode)
    :param processing_mode: processing mode, 'legacy' or 'streaming'. Default is 'legacy'.
    :param batch_size: batch size for streaming mode. Default is 100.
    :param kwargs: optional extra args for Dataset loading csv/tsv
    :return: target_dir path where the converted files are saved
    """
    # check if the source directory exists
    if not os.path.exists(src_dir):
        raise ValueError('The raw source data directory does not exist,'
                         ' Please check and retry.')
    if not os.path.exists(target_dir):
        os.makedirs(target_dir, exist_ok=True)

    if kwargs is None:
        kwargs = {}

    if is_tsv:
        kwargs['sep'] = '\t'
    else:
        # Explicit CSV comma delimiter for correct column name parsing
        kwargs['sep'] = ','

    if isinstance(suffixes, str):
        suffixes = [suffixes]

    if processing_mode == 'streaming':
        # Streaming mode: single process, batch processing
        print(f"Using streaming mode with batch_size={batch_size}")
        for suffix in suffixes:
            for fp in fp_iter(src_dir, suffix):
                print(fp)
                jsonl_fp = os.path.join(target_dir,
                                        fp.name.replace(suffix, '.jsonl'))
                reformat_nan_value_streaming(str(fp), jsonl_fp, keep_default_na, kwargs, batch_size)
    else:
        # Legacy mode: multi-process, full file loading
        print(f"Using legacy mode with num_proc={num_proc}")
        pool = Pool(num_proc)
        for suffix in suffixes:
            for fp in fp_iter(src_dir, suffix):
                print(fp)
                jsonl_fp = os.path.join(target_dir,
                                        fp.name.replace(suffix, '.jsonl'))
                pool.apply_async(reformat_nan_value,
                                 args=(str(fp), jsonl_fp, keep_default_na, kwargs))
        pool.close()
        pool.join()
    
    return target_dir


if __name__ == '__main__':
    fire.Fire(main)
