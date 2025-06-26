import time

from loguru import logger

from data_engine.config import init_configs
from data_engine.core.ray_data import RayDataset
from data_engine.ops import load_ops, OPERATORS
from data_engine.utils.availability_utils import AvailabilityChecking
from data_engine.ingester.load import load_ingester
from ..exporter.load import load_exporter
from data_engine.format.load import load_formatter
import datasets
from data_engine.utils.env import GetRayAddress
from .tracer import Tracer

import os

with AvailabilityChecking(['ray'], requires_type='dist'):
    import ray
    import ray.data as rd
    from ray.data.datasource import FilenameProvider
    from ray.data.block import Block
    from dotenv import load_dotenv

load_dotenv()
# class FixedWithIndexFilenameProvider(FilenameProvider):
#     def __init__(self, file_format: str):
#         self.file_format = file_format
#         self.fixed_filename = '_df_dataset'
#         self.index = 0

#     def get_filename_for_block(
#         self, block: Block, task_index: int, block_index: int
#     ) -> str:
#         filename = f"{self.fixed_filename}_{self.index}.{self.file_format}"
#         self.index += 1
#         return filename

#     def get_filename_for_row(
#         self, row: Dict[str, Any], task_index: int, block_index: int, row_index: int
#     ) -> str:
#         filename = f"{self.fixed_filename}_{self.index}.{self.file_format}"
#         self.index += 1
#         return filename


class RayExecutor:
    """
    Executor based on Ray.

    Run Data-Juicer data processing in a distributed cluster.

        1. Support Filter, Mapper and Exact Deduplicator operators for now.
        2. Only support loading `.json` files.
        3. Advanced functions such as checkpoint, tracer are not supported.

    """

    def __init__(self, cfg=None):
        """
        Initialization method.

        :param cfg: optional config dict.
        """
        self.cfg = init_configs() if cfg is None else cfg
        self.work_dir = self.cfg.work_dir

        logger.info(f"Using work dir: {self.work_dir}")

        self.work_dir = self.cfg.work_dir
        self.tracer = None

        self.user_id = self.cfg.user_id
        self.user_name = self.cfg.user_name
        self.user_token = self.cfg.user_token
        logger.info(f'Using user_id={self.user_id}, '
                    f'user_name={self.user_name}, '
                    f'user_token={"xxxxxx" if self.user_token is not None and len(self.user_token)>0 else None}')

        # setup ingester
        logger.info('Setting up data ingester...')
        # Only have one embeded ingester: from csghub
        self.ingester = load_ingester(
            dataset_path=self.cfg.dataset_path,
            repo_id=self.cfg.repo_id,
            branch=self.cfg.branch,
            user_name=self.user_name,
            user_token=self.user_token
        )

        # prepare exporter and check export path suffix
        logger.info('Preparing exporter...')
        self.exporter = load_exporter(
            self.cfg.export_path,
            self.cfg.export_shard_size,
            self.cfg.export_in_parallel,
            self.cfg.np,
            keep_stats_in_res_ds=self.cfg.keep_stats_in_res_ds,
            keep_hashes_in_res_ds=self.cfg.keep_hashes_in_res_ds,
            repo_id=self.cfg.repo_id,
            branch=self.cfg.branch,
            user_name=self.user_name,
            user_token=self.user_token,
            work_dir=self.work_dir
        )

        # setup tracer
        self.open_tracer = self.cfg.open_tracer
        if self.open_tracer:
            logger.info('Preparing tracer...')
            self.tracer = Tracer(self.work_dir, show_num=self.cfg.trace_num)
            self.op_list_to_trace = self.cfg.op_list_to_trace
            if len(self.cfg.op_list_to_trace) == 0:
                logger.info('Trace for all ops.')
                self.op_list_to_trace = set(OPERATORS.modules.keys())

        # init ray
        logger.info('Initing Ray ...')
        ray.init(address=GetRayAddress(), ignore_reinit_error=True)

    def run(self, load_data_np=None):
        """
        Running the dataset process pipeline.

        :param load_data_np: number of workers when loading the dataset.
        :return: processed dataset.
        """
        # 0. ingest data
        self.src_path = self.ingester.ingest()
        logger.info(f'Data ingested from {self.src_path}')

        # 1. setup formatter
        logger.info('Setting up data formatter...')
        self.formatter = load_formatter(
            self.src_path,
            self.cfg.generated_dataset_config,
            self.cfg.text_keys, self.cfg.suffixes,
            self.cfg.add_suffix
        )

        # 2. format data
        if self.cfg.use_checkpoint and self.ckpt_manager.ckpt_available:
            logger.info('Loading dataset from checkpoint...')
            dataset = self.ckpt_manager.load_ckpt()
        else:
            logger.info('Loading dataset from data formatter...')
            if load_data_np is None:
                load_data_np = self.cfg.np
            dataset = self.formatter.load_dataset(load_data_np, self.cfg)

        # convert hf dataset to ray dataset
        if isinstance(dataset, datasets.Dataset):
            hf_ds_arrow = dataset.with_format("arrow")
            ray_dataset = rd.from_arrow(hf_ds_arrow[:])

        # convert all the path in dataset to absolute path
        dataset = RayDataset(dataset=ray_dataset, 
                             dataset_path=self.cfg.dataset_path, 
                             cfg=self.cfg)
        
        # 2. extract processes
        logger.info('Preparing process operators...')
        ops = load_ops(self.cfg.process, self.cfg.op_fusion)

        # 3. data process
        logger.info('Processing data...')
        tstart = time.time()
        dataset.process(ops, tracer=self.tracer)
        tend = time.time()
        logger.info(f'All Ops are done in {tend - tstart:.3f}s.')

        # 4. data export
        logger.info('Exporting dataset to somewhere...')
        # TODO Add more exporter, for csghub, for local dist .etc
        # output_branch_name = self.exporter.export_from_files(export_dir)
        hf_dataset = datasets.Dataset.from_list(dataset.data)
        output_branch_name = self.exporter.export(hf_dataset)

        return hf_dataset, output_branch_name
