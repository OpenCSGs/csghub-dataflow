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
from data_engine.ops.mapper.text_make_cosmopedia import MakeCosmopediaMapper
from data_engine.utils.constant import Fields, StatsKeys

def main(src_dir, target_dir, suffixes=[], num_proc=1,
         web_text_max_len=800, model_url="https://euqnoct5ophc.space.opencsg.com/v1/chat/completions",
         model="THUDM/LongWriter-glm4-9b", auth_token="9acc3ea387b5479607bdeb5386af6e3483fbf070",
         content='''网页摘录："{web_text}"。
以 WikiHow 的风格写一篇长而非常详细的教程，教程与此网页摘录有相关性。
教程中需要包括对每个步骤的深入解释以及它如何帮助实现预期结果。你可以自由补充其他相关知识。
确保清晰性和实用性，让读者能够轻松遵循教程完成任务。内容中不应包含广告或涉及隐私的信息。
不要使用图像。请直接开始撰写教程。''',
         processing_mode='legacy', batch_size=100):
    # check if the source directory exists.
    if not os.path.exists(src_dir):
        raise ValueError('The raw source data directory does not exist,'
                         ' Please check and retry.')
    if not os.path.exists(target_dir):
        os.makedirs(target_dir, exist_ok=True)

    formatter = load_formatter(src_dir, text_keys=['text', 'title'], suffixes=suffixes)
    
    # Create operator instance
    op = MakeCosmopediaMapper()
    op.web_text_max_len = web_text_max_len
    op.model_url = model_url
    op.model = model
    op.auth_token = auth_token
    op.content = content
    
    # Validate processing_mode
    if processing_mode not in ['legacy', 'streaming']:
        raise ValueError(f"Invalid processing_mode='{processing_mode}'. Must be 'legacy' or 'streaming'.")
    
    if processing_mode == 'streaming':
        # Validate batch_size for streaming mode
        if batch_size <= 0:
            raise ValueError(f'Invalid batch_size={batch_size}. batch_size must be a positive integer (>= 1).')
        return _process_streaming(formatter, op, target_dir, batch_size, src_dir, suffixes)
    else:
        return _process_legacy(formatter, op, target_dir, num_proc)


def _process_legacy(formatter, op, target_dir, num_proc):
    """Legacy processing mode - loads entire dataset into memory"""
    dataset = formatter.load_dataset(num_proc)
    dataset = dataset.map(op.process, num_proc=num_proc)

    output_file = os.path.join(target_dir, 'cosmopedia_output.jsonl')
    dataset.to_json(output_file, force_ascii=False)
    logger.info(f'Dataset saved to {output_file}')

    return output_file


def _process_streaming(formatter, op, target_dir, batch_size, src_dir, suffixes):
    """Streaming processing mode - processes samples in batches without loading all into memory"""
    
    # Helper function to iterate through all files in batches (supports multiple formats)
    def iterate_files_batched(src_dir, suffixes, batch_size):
        """Iterate through all data files and yield batches of samples
        
        Supports: .jsonl, .json, .parquet, .csv, .txt, .tsv
        """
        import json
        import csv
        
        batch = []
        
        for suffix in suffixes:
            for file_path in pathlib.Path(src_dir).glob(f'*{suffix}'):
                logger.info(f'Reading file: {file_path}')
                file_ext = ''.join(file_path.suffixes).lower()  # Handle .jsonl.zst
                
                try:
                    # JSONL/JSON formats
                    if file_ext in ['.jsonl', '.jsonl.zst', '.json']:
                        with jsonlines.open(file_path, 'r') as reader:
                            for sample in reader:
                                batch.append(sample)
                                if len(batch) >= batch_size:
                                    yield batch
                                    batch = []
                    
                    # Parquet format
                    elif file_ext == '.parquet':
                        import pyarrow.parquet as pq
                        parquet_file = pq.ParquetFile(file_path)
                        for batch_data in parquet_file.iter_batches(batch_size=batch_size):
                            df = batch_data.to_pandas()
                            for _, row in df.iterrows():
                                sample = row.to_dict()
                                batch.append(sample)
                                if len(batch) >= batch_size:
                                    yield batch
                                    batch = []
                    
                    # CSV/TSV formats
                    elif file_ext in ['.csv', '.tsv']:
                        delimiter = '\t' if file_ext == '.tsv' else ','
                        with open(file_path, 'r', encoding='utf-8') as f:
                            reader = csv.DictReader(f, delimiter=delimiter)
                            for row in reader:
                                batch.append(dict(row))
                                if len(batch) >= batch_size:
                                    yield batch
                                    batch = []
                    
                    # Plain text format (each line is a sample with text field)
                    elif file_ext == '.txt':
                        with open(file_path, 'r', encoding='utf-8') as f:
                            for line in f:
                                line = line.strip()
                                if line:  # Skip empty lines
                                    sample = {'text': line}
                                    batch.append(sample)
                                    if len(batch) >= batch_size:
                                        yield batch
                                        batch = []
                    
                    else:
                        logger.warning(f'Unsupported file format: {file_ext} for {file_path}')
                        continue
                
                except Exception as e:
                    logger.error(f'Error reading file {file_path}: {e}')
                    continue
        
        # Yield remaining samples
        if batch:
            yield batch
    
    logger.info(f"Streaming mode: batch_size={batch_size}")
    
    # Statistics
    total_samples = 0
    generated_samples = 0
    failed_samples = 0
    
    output_file = os.path.join(target_dir, 'cosmopedia_output.jsonl')
    
    # Open output file for writing
    with jsonlines.open(output_file, 'w') as writer:
        # Process in batches
        for batch in tqdm(iterate_files_batched(src_dir, suffixes, batch_size), 
                         desc="Processing batches", unit="batch"):
            processed_batch = []
            
            # Process each sample in the batch (串行调用 LLM API)
            for sample in tqdm(batch, desc="Batch samples", leave=False, unit="sample"):
                total_samples += 1
                
                try:
                    # Process sample (calls LLM API)
                    processed_sample = op.process(sample)
                    
                    # Check if generation was successful
                    if processed_sample.get('data'):
                        generated_samples += 1
                    else:
                        failed_samples += 1
                    
                    processed_batch.append(processed_sample)
                    
                except Exception as e:
                    failed_samples += 1
                    logger.warning(f"Failed to process sample: {e}")
                    # Still add the sample with empty data field
                    sample['data'] = ""
                    processed_batch.append(sample)
            
            # Write batch to file
            for sample in processed_batch:
                writer.write(sample)
            
            # Log progress
            logger.info(f"Processed {total_samples} samples | "
                       f"Generated: {generated_samples} ({generated_samples/total_samples*100:.1f}%) | "
                       f"Failed: {failed_samples} ({failed_samples/total_samples*100:.1f}%)")
    
    # Final summary
    logger.info("="*60)
    logger.info(f"[Cosmopedia Streaming] Generation Summary")
    logger.info("="*60)
    logger.info(f"Total: {total_samples}, Generated: {generated_samples} ({generated_samples/total_samples*100:.2f}%), "
               f"Failed: {failed_samples} ({failed_samples/total_samples*100:.2f}%)")
    logger.info(f"Output saved to: {output_file}")
    logger.info("="*60)
    
    return target_dir

