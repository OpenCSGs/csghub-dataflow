# This tool is used to reformat jsonl files which may have Nan values
# in some field.

import os
import pathlib
from multiprocessing import Pool

import fire
import jsonlines
import pandas as pd
from datasets import Dataset
from tqdm import tqdm


def check_dict_non_nan(obj):
    """
    Check if all fields in the dict object are non-Nan
    :papram: a dict object
    :return: True if all fields in the dict object are non-Nan,
            else False
    """
    no_nan = True
    for key, value in obj.items():
        if isinstance(value, dict):
            no_nan = no_nan & check_dict_non_nan(value)
        elif pd.isna(value) or pd.isnull(value):
            return False
    return no_nan


def replace_nan_with_none(obj):
    """
    Recursively replace all NaN values with None in a dict object.
    This ensures JSON compliance since JSON only supports null, not NaN.
    :param obj: a dict object that may contain NaN values
    :return: dict object with NaN values replaced by None
    """
    if isinstance(obj, dict):
        return {key: replace_nan_with_none(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [replace_nan_with_none(item) for item in obj]
    elif pd.isna(obj) or pd.isnull(obj):
        return None
    else:
        return obj


def get_non_nan_features(src_dir):
    """
    Get the first object feature which does not contain Nan value.
    :param src_dir: path which stores jsonl files.
    :return: reference feature of dataset.
    """
    for fp in fp_iter(src_dir):
        with jsonlines.open(fp, 'r') as reader:
            for obj in reader:
                if check_dict_non_nan(obj):
                    ds = Dataset.from_list([obj])
                    return ds.features
    return None


def reformat_jsonl(fp, jsonl_fp, features):
    """
    Reformat a jsonl file with reference features (Legacy mode - full load)
    :param fp: input jsonl file
    :param jsonl_fp: formated jsonl file
    :param features: reference feature to use for dataset.
    """
    with jsonlines.open(fp, 'r') as reader:
        objs = [obj for obj in reader]
    # Replace all NaN values with None to ensure JSON compliance
    objs = [replace_nan_with_none(obj) for obj in objs]
    ds = Dataset.from_list(objs, features=features)
    ds.to_json(jsonl_fp, force_ascii=False)


def reformat_jsonl_streaming(fp, jsonl_fp, features, batch_size=100):
    """
    Reformat a jsonl file with reference features (Streaming mode - batch processing)
    :param fp: input jsonl file
    :param jsonl_fp: formatted jsonl file
    :param features: reference feature to use for dataset.
    :param batch_size: number of samples to process in each batch
    """

    # First pass: count total lines for accurate progress bar
    print(f"Counting samples in {os.path.basename(fp)}...")
    with jsonlines.open(fp, 'r') as reader:
        total_lines = sum(1 for _ in reader)
    
    total_batches = (total_lines + batch_size - 1) // batch_size
    print(f"Processing {total_lines:,} samples in {total_batches} batches (batch_size={batch_size})")
    
    batch = []
    processed = 0
    
    # Use a single jsonlines writer for consistent serialization
    with jsonlines.open(jsonl_fp, 'w') as writer:
        # Progress bar for batch processing
        with tqdm(total=total_lines, desc="Streaming processing", unit="sample") as pbar:
            with jsonlines.open(fp, 'r') as reader:
                for obj in reader:
                    # Replace NaN values with None
                    cleaned_obj = replace_nan_with_none(obj)
                    batch.append(cleaned_obj)
                    
                    # Process batch when it reaches batch_size
                    if len(batch) >= batch_size:
                        # Convert to Dataset to apply features schema, then write
                        ds = Dataset.from_list(batch, features=features)
                        for item in ds:
                            writer.write(dict(item))
                        
                        processed += len(batch)
                        pbar.update(len(batch))
                        batch = []
                
                # Process remaining samples in the last batch
                if batch:
                    ds = Dataset.from_list(batch, features=features)
                    for item in ds:
                        writer.write(dict(item))
                    processed += len(batch)
                    pbar.update(len(batch))
    
    print(f"✓ Completed: {processed:,} samples processed")



def fp_iter(src_dir):
    """
    Find all jsonl files in the source directory.
    :param src_dir: path to source dataset directory
    :return: iterator over jsonl files
    """
    for fp in pathlib.Path(src_dir).glob('*.jsonl'):
        yield fp


def main(src_dir, target_dir, num_proc=1, processing_mode='legacy', batch_size=100):
    """
    Reformat the jsonl files which may contain Nan values. Traverse jsonl
    files to find the first object that does not contain Nan as a
    reference feature type, then set it for loading all jsonl files.
    :param src_dir: path thats stores jsonl files.
    :param target_dir: path to store the converted jsonl files.
    :param num_proc: number of process workers. Default it's 1. (Only used in legacy mode)
    :param processing_mode: processing mode, 'legacy' or 'streaming'. Default is 'legacy'.
    :param batch_size: batch size for streaming mode. Default is 100.
    """

    # check if the source directory exists
    if not os.path.exists(src_dir):
        raise ValueError('The raw source data directory does not exist,'
                         ' Please check and retry.')
    if not os.path.exists(target_dir):
        os.makedirs(target_dir, exist_ok=True)

    # Get reference features from first non-NaN sample
    features = get_non_nan_features(src_dir)
    
    # Validate processing_mode
    if processing_mode not in ['legacy', 'streaming']:
        raise ValueError(f"Invalid processing_mode='{processing_mode}'. Must be 'legacy' or 'streaming'.")
    
    if processing_mode == 'streaming':
        # Validate batch_size for streaming mode
        if batch_size <= 0:
            raise ValueError(f'Invalid batch_size={batch_size}. batch_size must be a positive integer (>= 1).')
        # Streaming mode: single process, batch processing
        print(f"Using streaming mode with batch_size={batch_size}")
        for fp in fp_iter(src_dir):
            print(fp)
            jsonl_fp = os.path.join(target_dir, fp.name)
            reformat_jsonl_streaming(str(fp), jsonl_fp, features, batch_size)
    else:
        # Legacy mode: multi-process, full file loading
        print(f"Using legacy mode with num_proc={num_proc}")
        pool = Pool(num_proc)
        for fp in fp_iter(src_dir):
            print(fp)
            jsonl_fp = os.path.join(target_dir, fp.name)
            pool.apply_async(reformat_jsonl, args=(str(fp), jsonl_fp, features))
        pool.close()
        pool.join()


if __name__ == '__main__':
    fire.Fire(main)
