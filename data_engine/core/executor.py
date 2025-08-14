import os
from time import time
from loguru import logger

from data_engine.config import init_configs
from data_engine.core.data import Dataset
from data_engine.format.load import load_formatter
from data_engine.ingester.load import load_ingester
from data_engine.format.mixture_formatter import MixtureFormatter
from data_engine.ops import OPERATORS, load_ops
from data_engine.utils import cache_utils
from data_engine.utils.ckpt_utils import CheckpointManager

from ..ops.selector.frequency_specified_field_selector import \
    FrequencySpecifiedFieldSelector
from ..ops.selector.topk_specified_field_selector import \
    TopkSpecifiedFieldSelector
from ..exporter.load import load_exporter
from .tracer import Tracer
from .._telemetry import TRACE_HELPER, get_telemetry_envelope_metadata
from data_celery.mongo_tools.tools import (insert_pipline_job_run_task_log_error,
                                           insert_pipline_job_run_task_log_info,
                                           insert_pipline_job_run_task_log_debug,
                                           insert_pipline_job_run_task_log_warning)
class Executor:
    """
    This Executor class is used to process a specific dataset.

    It will load the dataset and unify the format, then apply all the
    ops in the config file in order and generate a processed dataset.
    """

    def __init__(
        self, 
        cfg=None,
        job_uid=""
        ):
        """
        Initialization method.

        :param cfg: optional config dict.
        :param job_uid: pipline job uid
        """
        self.cfg = init_configs() if cfg is None else cfg

        self.work_dir = self.cfg.work_dir
        self.job_uid = job_uid

        self.tracer = None
        self.ckpt_manager = None
        logger.info(f"Using work dir: {self.work_dir}")
        insert_pipline_job_run_task_log_info(self.job_uid, f"Using work dir: {self.work_dir}")
        # only enable it when using cache
        if self.cfg.use_cache:
            logger.info(f'Using cache compression method: '
                        f'[{self.cfg.cache_compress}]')
            insert_pipline_job_run_task_log_info(self.job_uid, f'Using cache compression method: [{self.cfg.cache_compress}]')
            cache_utils.CACHE_COMPRESS = self.cfg.cache_compress

        self.user_id = self.cfg.user_id
        self.user_name = self.cfg.user_name
        self.user_token = self.cfg.user_token
        logger.info(f'Using user_id={self.user_id}, '
                    f'user_name={self.user_name}, '
                    f'user_token={"xxxxxx" if self.user_token is not None and len(self.user_token)>0 else None}')
        insert_pipline_job_run_task_log_info(self.job_uid,
                                             f'Using user_id={self.user_id}, '
                                             f'user_name={self.user_name}, '
                                             f'user_token={"xxxxxx" if self.user_token is not None and len(self.user_token)>0 else None}')
        # setup ingester
        logger.info('Setting up data ingester...')
        insert_pipline_job_run_task_log_info(self.job_uid,
                                             'Setting up data ingester...')
        # Only have one embeded ingester: from csghub
        self.ingester = load_ingester(
            dataset_path = self.cfg.dataset_path, 
            repo_id = self.cfg.repo_id,
            branch = self.cfg.branch,
            user_name = self.user_name,
            user_token = self.user_token
        )
        # assign src_path as dataset_path to format creation

        # whether to use checkpoint mechanism. If it's true, Executor will
        # check if there are existing checkpoints first and try to load the
        # checkpoints. If the checkpoints are loaded successfully, ops that
        # have been processed will be skipped.
        if self.cfg.use_checkpoint:
            logger.info('Preparing checkpoint manager...')
            insert_pipline_job_run_task_log_info(self.job_uid,
                                                 'Preparing checkpoint manager...')
            self.ckpt_dir = os.path.join(self.work_dir, 'ckpt')
            self.ckpt_manager = CheckpointManager(self.ckpt_dir,
                                                  self.cfg.process,
                                                  self.cfg.np)
            if self.ckpt_manager.ckpt_available:
                logger.info('Found existed dataset checkpoint.')
                insert_pipline_job_run_task_log_info(self.job_uid,
                                                     'Found existed dataset checkpoint.')
                self.cfg.process = self.ckpt_manager.get_left_process_list()

        # prepare exporter and check export path suffix
        logger.info('Preparing exporter...')
        insert_pipline_job_run_task_log_info(self.job_uid,
                                             'Preparing exporter...')
        self.exporter = load_exporter(
            self.cfg.export_path,
            self.cfg.export_shard_size,
            self.cfg.export_in_parallel,
            self.cfg.np,
            keep_stats_in_res_ds=self.cfg.keep_stats_in_res_ds,
            keep_hashes_in_res_ds=self.cfg.keep_hashes_in_res_ds,
            repo_id = self.cfg.repo_id,
            branch = self.cfg.branch,
            user_name=self.user_name,
            user_token=self.user_token,
            work_dir=self.work_dir
        )

        # setup tracer
        self.open_tracer = self.cfg.open_tracer
        if self.open_tracer:
            logger.info('Preparing tracer...')
            insert_pipline_job_run_task_log_info(self.job_uid,
                                                 'Preparing tracer...')
            self.tracer = Tracer(self.work_dir, show_num=self.cfg.trace_num)
            self.op_list_to_trace = self.cfg.op_list_to_trace
            if len(self.cfg.op_list_to_trace) == 0:
                logger.info('Trace for all ops.')
                insert_pipline_job_run_task_log_info(self.job_uid,
                                                     'Trace for all ops.')
                self.op_list_to_trace = set(OPERATORS.modules.keys())

    def sample_data(self,
                    dataset_to_sample: Dataset = None,
                    load_data_np=None,
                    sample_ratio: float = 1.0,
                    sample_algo: str = 'uniform',
                    **kwargs):
        """
        Sample a subset from the given dataset.

        :param dataset_to_sample: Dataset to sample from. If None, will use
            the formatter linked by the executor. Default is None.
        :param load_data_np: number of workers when loading the dataset.
        :param sample_ratio: The ratio of the sample size to the original
            dataset size. Default is 1.0 (no sampling).
        :param sample_algo: Sampling algorithm to use. Options are "uniform",
            "frequency_specified_field_selector", or
            "topk_specified_field_selector".
            Default is "uniform".
        :return: A sampled Dataset.
        """
        # Determine the dataset to sample from
        if dataset_to_sample is not None:
            dataset = dataset_to_sample
        elif self.cfg.use_checkpoint and self.ckpt_manager.ckpt_available:
            logger.info('Loading dataset from checkpoint...')
            insert_pipline_job_run_task_log_info(self.job_uid,
                                                 'Loading dataset from checkpoint...')
            dataset = self.ckpt_manager.load_ckpt()
        elif hasattr(self, 'formatter'):
            logger.info('Loading dataset from data formatter...')
            insert_pipline_job_run_task_log_info(self.job_uid,
                                                 'Loading dataset from data formatter...')
            if load_data_np is None:
                load_data_np = self.cfg.np
            dataset = self.formatter.load_dataset(load_data_np, self.cfg)
        else:
            insert_pipline_job_run_task_log_error(self.job_uid,
                                                  'No dataset available to sample from.')
            raise ValueError('No dataset available to sample from.')

        # Perform sampling based on the specified algorithm
        if sample_algo == 'uniform':
            return MixtureFormatter.random_sample(dataset, sample_ratio)
        elif sample_algo == 'frequency_specified_field_selector':
            dj_op = FrequencySpecifiedFieldSelector(**kwargs)
            return dj_op.process(dataset)
        elif sample_algo == 'topk_specified_field_selector':
            dj_op = TopkSpecifiedFieldSelector(**kwargs)
            return dj_op.process(dataset)
        else:
            insert_pipline_job_run_task_log_error(self.job_uid,
                                                  f'Unsupported sample_algo: {sample_algo}')
            raise ValueError(f'Unsupported sample_algo: {sample_algo}')

    def run(self, load_data_np=None):
        """
        Running the dataset process pipeline.

        :param load_data_np: number of workers when loading the dataset.
        :return: processed dataset.
        """
        # 0. ingest data
        with TRACE_HELPER.trace_block(
            "ingest",
            parent=get_telemetry_envelope_metadata(),
        ):
            self.src_path = self.ingester.ingest()
            logger.info(f'Data ingested from {self.src_path}')
            insert_pipline_job_run_task_log_info(self.job_uid,
                                                 f'Data ingested from {self.src_path}')
        # set src_path to format, let format continue it's job

        # 1. setup formatter
        with TRACE_HELPER.trace_block(
            "format",
            parent=get_telemetry_envelope_metadata(),
        ):
            logger.info('Setting up data formatter...')
            insert_pipline_job_run_task_log_info(self.job_uid,
                                                 'Setting up data formatter...')
            self.formatter = load_formatter(
                self.src_path,
                self.cfg.generated_dataset_config,
                self.cfg.text_keys, self.cfg.suffixes,
                self.cfg.add_suffix
            )

            # 2. format data
            if self.cfg.use_checkpoint and self.ckpt_manager.ckpt_available:
                logger.info('Loading dataset from checkpoint...')
                insert_pipline_job_run_task_log_info(self.job_uid,
                                                     'Loading dataset from checkpoint...')
                dataset = self.ckpt_manager.load_ckpt()
            else:
                logger.info('Loading dataset from data formatter...')
                insert_pipline_job_run_task_log_info(self.job_uid,
                                                     'Loading dataset from data formatter...')
                if load_data_np is None:
                    load_data_np = self.cfg.np
                dataset = self.formatter.load_dataset(load_data_np, self.cfg)

        # 3. extract processes
        logger.info('Preparing process operators...')
        insert_pipline_job_run_task_log_info(self.job_uid,
                                             'Preparing process operators...')

        ops = load_ops(self.cfg.process, self.cfg.op_fusion,job_uid=self.job_uid)

        # 4. data process
        # - If tracer is open, trace each op after it's processed
        # - If checkpoint is open, clean the cache files after each process
        with TRACE_HELPER.trace_block(
            "run",
            parent=get_telemetry_envelope_metadata(),
            extraAttributes={"dataset_count": len(dataset)}
        ):
            logger.info('Processing data...')
            insert_pipline_job_run_task_log_info(self.job_uid,
                                                 'Processing data...')
            tstart = time()
            dataset = dataset.process(
                ops,
                exporter=self.exporter,
                checkpointer=self.ckpt_manager,
                tracer=self.tracer
            )
            tend = time()
            logger.info(f'All OPs are done in {tend - tstart:.3f}s.')
            insert_pipline_job_run_task_log_info(self.job_uid,
                                                 f'All OPs are done in {tend - tstart:.3f}s.')

        # 5. data export
        with TRACE_HELPER.trace_block(
            "export",
            parent=get_telemetry_envelope_metadata(),
            extraAttributes={"dataset_count": len(dataset)}
        ):
            logger.info('Exporting dataset to disk...')
            insert_pipline_job_run_task_log_info(self.job_uid,
                                                 'Exporting dataset to disk...')

            output_branch_name = self.exporter.export(dataset)
            # compress the last dataset after exporting
            if self.cfg.use_cache and self.cfg.cache_compress:
                from data_engine.utils.compress import compress
                compress(dataset)
        
        return dataset, output_branch_name
