# This tool is used to split datasets to sub-datasets
# by fast-text lanuage model.

import os
import pathlib

import fire
import pandas as pd
import jsonlines
from loguru import logger
from tqdm import tqdm

from data_engine.core.data import add_same_content_to_new_column
from data_engine.format import load_formatter
from data_engine.ops.filter.language_id_score_filter import \
    LanguageIDScoreFilter
from data_engine.utils.constant import Fields, StatsKeys


def keep_by_lang(sample, lang):
    """
    Keep samples with the specified language.
    :param sample: a sample in dataset
    :param lang: the specified language
    :return: True to keep,  False to discard
    """
    if sample[Fields.stats][StatsKeys.lang] == lang:
        return True
    return False


def main(src_dir, target_dir, text_key=None, suffixes=[], num_proc=1,
         processing_mode='legacy', batch_size=1000):
    """
    Load dataset from the source directory, then apply language identification
    using the operation filter called `LanguageIDScoreFilter`,
    finally, split the dataset by language and save it.
    :param src_dir: path to store the dataset.
    :param target_dir: path to store subset files(`jsonl` format)
    :param text_key: key name of field that stores sample text, default `text`
    :param suffixes: files with suffixes to be loaded, default None
    :param num_proc: number of processes to process dataset, default 1 (only for legacy mode)
    :param processing_mode: 'legacy' or 'streaming', default 'legacy'
    :param batch_size: batch size for streaming mode, default 1000
    """
    if text_key is None:
        text_key = 'text'

    # check if the source directory exists.
    if not os.path.exists(src_dir):
        raise ValueError('The raw source data directory does not exist,'
                         ' Please check and retry.')
    if not os.path.exists(target_dir):
        os.makedirs(target_dir, exist_ok=True)

    formatter = load_formatter(src_dir, text_keys=text_key, suffixes=suffixes)
    op = LanguageIDScoreFilter(text_key=text_key)
    
    if processing_mode == 'streaming':
        return _process_streaming(formatter, op, text_key, target_dir, batch_size, src_dir, suffixes)
    else:
        return _process_legacy(formatter, op, text_key, target_dir, num_proc)


def _process_legacy(formatter, op, text_key, target_dir, num_proc):
    """Legacy processing mode - loads entire dataset into memory"""
    dataset = formatter.load_dataset(num_proc)

    if Fields.stats not in dataset.features:
        # only add stats when calling filter op
        dataset = dataset.map(add_same_content_to_new_column,
                              fn_kwargs={
                                  'new_column_name': Fields.stats,
                                  'initial_value': {}
                              },
                              num_proc=num_proc,
                              desc='Adding new column for stats')

    # identify language
    dataset = dataset.map(op.compute_stats, num_proc=num_proc)

    langs = pd.DataFrame(dataset[Fields.stats])[StatsKeys.lang]
    unique_langs = list(set(langs))

    logger.info(f'There are {len(dataset)} samples in dataset')
    logger.info(f'Languages in dataset are {unique_langs}')

    # split and save subset of dataset by language
    for lang in unique_langs:
        ds = dataset.filter(keep_by_lang,
                            num_proc=num_proc,
                            fn_kwargs=dict(lang=lang))

        logger.info(f'There are {len(ds)} samples with language [{lang}]')
        jsonl_fp = os.path.join(target_dir, lang + '.jsonl')
        ds.to_json(jsonl_fp, force_ascii=False)

    return jsonl_fp

def _process_streaming(formatter, op, text_key, target_dir, batch_size, src_dir, suffixes):
    """Streaming processing mode - processes samples in batches without loading all into memory"""
    
    # Helper function to iterate through all JSONL files in batches
    def iterate_jsonl_files_batched(src_dir, suffixes, batch_size):
        """Iterate through all JSONL files and yield batches of samples"""
        batch = []
        for suffix in suffixes:
            for file_path in pathlib.Path(src_dir).glob(f'*{suffix}'):
                logger.info(f'Reading file: {file_path}')
                with jsonlines.open(file_path, 'r') as reader:
                    for sample in reader:
                        batch.append(sample)
                        if len(batch) >= batch_size:
                            yield batch
                            batch = []
        # Yield remaining samples
        if batch:
            yield batch
    
    # Helper function to convert numpy types to Python native types
    def convert_numpy_types(obj):
        """Recursively convert numpy types to Python native types for JSON serialization"""
        import numpy as np
        
        if isinstance(obj, dict):
            return {key: convert_numpy_types(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [convert_numpy_types(item) for item in obj]
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.bool_):
            return bool(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        else:
            return obj
    
    # ====== First pass: Detect languages and count statistics ======
    logger.info(f"First pass: Detecting languages (batch_size={batch_size})...")
    language_counts = {}
    total_samples = 0
    
    # Process in batches for better performance
    for batch in tqdm(iterate_jsonl_files_batched(src_dir, suffixes, batch_size), 
                     desc="Language detection", unit="batch"):
        for sample in batch:
            # Add stats field if not exists
            if Fields.stats not in sample:
                sample[Fields.stats] = {}
            
            # Identify language
            sample = op.compute_stats(sample)
            lang = sample[Fields.stats][StatsKeys.lang]
            
            # Count statistics
            language_counts[lang] = language_counts.get(lang, 0) + 1
            total_samples += 1
    
    unique_langs = list(language_counts.keys())
    
    logger.info(f'There are {total_samples} samples in dataset')
    logger.info(f'Languages in dataset are {unique_langs}')
    for lang, count in language_counts.items():
        logger.info(f'  - {lang}: {count:,} samples ({count/total_samples*100:.1f}%)')
    
    # ====== Second pass: Split by language and write to files ======
    logger.info(f"Second pass: Splitting by language (batch_size={batch_size})...")
    
    # Create writers for each language
    writers = {}
    for lang in unique_langs:
        jsonl_fp = os.path.join(target_dir, lang + '.jsonl')
        writers[lang] = jsonlines.open(jsonl_fp, 'w')
    
    processed_samples = 0
    try:
        # Create progress bar for the second pass
        pbar = tqdm(total=total_samples, desc="Splitting data", unit="sample")
        
        for batch in iterate_jsonl_files_batched(src_dir, suffixes, batch_size):
            for sample in batch:
                # Add stats and identify language
                if Fields.stats not in sample:
                    sample[Fields.stats] = {}
                sample = op.compute_stats(sample)
                lang = sample[Fields.stats][StatsKeys.lang]
                
                # Convert numpy types to Python native types for JSON serialization
                sample = convert_numpy_types(sample)
                
                # Write to corresponding language file
                writers[lang].write(sample)
                processed_samples += 1
                pbar.update(1)
        
        pbar.close()
    
    finally:
        # Close all writers
        for writer in writers.values():
            writer.close()
    
    logger.info(f"✓ Completed: {processed_samples:,} samples split into {len(unique_langs)} language files")
    
    return target_dir
if __name__ == '__main__':
    fire.Fire(main)
