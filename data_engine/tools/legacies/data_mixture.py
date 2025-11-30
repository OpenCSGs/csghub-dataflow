import argparse

from data_engine.exporter.base_exporter import Exporter
from data_engine.format import load_formatter
import os
import glob
import fire
from pathlib import Path

def main(data_path, 
         export_path, 
         max_samples, 
         weights, 
         export_shard_size=0,
         num_proc=1):
    """
    Mix multiple datasets into one dataset.
    Randomly select samples from every dataset and mix theses
    samples, then export to a new mixed dataset

    `data_path` with optional weight(1.0 as default),
        e.g.
        1) a single data path
        2) multiple datasets in the format: <w1> dataset1-path
            <w2> dataset1-file  <w3>dataset3-path ...'

    """
    if os.path.isdir(data_path):
        file_types = ['*.parquet', '*.json', '*.jsonl']
        file_list = []
        for file_type in file_types:
            file_list += glob.glob(os.path.join(data_path, file_type))

        sorted_file_list = sorted(file_list, key=lambda x: os.path.basename(x))

    mix_path = ''
    while len(weights) < len(sorted_file_list):
        weights.append(weights[0])
    weights = weights[:len(sorted_file_list)]
    for weight, file in zip(weights, sorted_file_list):
        mix_path += (' ' + weight + ' ' + file)

    if Path(export_path).is_dir():
        export_file = os.path.join(export_path, "mixture.jsonl")

    formatter = load_formatter(mix_path, max_samples=max_samples)
    dataset = formatter.load_dataset(num_proc)
    exporter = Exporter(export_path=export_file,
                        export_shard_size=export_shard_size,
                        num_proc=num_proc,
                        export_stats=False)
    exporter.export(dataset)

    return Path(os.path.join(export_path, "_data"))


if __name__ == '__main__':
    fire.Fire(main)
