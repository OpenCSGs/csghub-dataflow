from data_engine.utils.mm_utils import size_to_bytes
from data_engine import is_cuda_available
from data_engine.utils.process_utils import calculate_np
from loguru import logger
import time
from data_engine.utils.registry import Registry
from data_server.logic.models import Tool as Tool_def, ExecutedParams
from pathlib import Path
import os
from data_engine.utils.logger_utils import setup_logger
from data_engine.ingester.load import load_ingester
from data_engine.exporter.load import load_exporter
from .._telemetry import TRACE_HELPER_TOOL, get_telemetry_envelope_metadata

TOOLS = Registry('Tools')

class TOOL:

    _accelerator = 'cpu'

    def __init__(self, tool_defination: Tool_def, params: ExecutedParams):
        """
        Base class of operators.
        """
        self.tool_def = tool_defination
        self.tool_def.export_path = os.path.join(self.tool_def.export_path, "_data")
        if not os.path.exists(self.tool_def.export_path):
            os.makedirs(self.tool_def.export_path, exist_ok=True)
        
        self.executed_params = params
        
        # setup logger
        log_dir = os.path.join(self.executed_params.work_dir, 'log')
        if not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        timestamp = time.strftime('%Y%m%d%H%M%S', time.localtime(time.time()))
        logfile_name = f'tool_{self.tool_def.name}_time_{timestamp}.txt'
        setup_logger(save_dir=log_dir,
                    filename=logfile_name,
                    level='INFO',
                    redirect=self.tool_def.executor_type == 'default')

        # setup ingester
        logger.info('Setting up data ingester...')
        # Only have one embeded ingester: from csghub
        self.ingester = load_ingester(
            dataset_path = self.tool_def.dataset_path, 
            repo_id = self.tool_def.repo_id,
            branch = self.tool_def.branch,
            user_name = self.executed_params.user_name,
            user_token = self.executed_params.user_token
        )

        # prepare exporter and check export path suffix
        logger.info('Preparing exporter...')
        # TODO Add more exporter, for csghub, for local dist .etc
        self.exporter = load_exporter(
            export_path=self.tool_def.export_path,
            export_shard_size=self.tool_def.export_shard_size,
            export_in_parallel=self.tool_def.export_in_parallel,
            num_proc=self.tool_def.np,
            keep_stats_in_res_ds=self.tool_def.keep_stats_in_res_ds,
            keep_hashes_in_res_ds=self.tool_def.keep_hashes_in_res_ds,
            repo_id = self.tool_def.repo_id,
            branch = self.tool_def.branch,
            user_name=self.executed_params.user_name,
            user_token=self.executed_params.user_token,
            work_dir=self.executed_params.work_dir,
        )

        # whether the model can be accelerated using cuda

        _accelerator = self.tool_def.accelerator if self.tool_def.accelerator else None
        if _accelerator is not None:
            self.accelerator = _accelerator
        else:
            self.accelerator = self._accelerator

        # parameters to determind the number of procs for this op
        self.num_proc = self.tool_def.np
        self.cpu_required = self.tool_def.cpu_required
        self.mem_required = self.tool_def.mem_required
        if isinstance(self.mem_required, str):
            self.mem_required = size_to_bytes(self.mem_required) / 1024**3

            
    def run(self):
        with TRACE_HELPER_TOOL.trace_block(
            "ingest",
            parent=get_telemetry_envelope_metadata(),
        ):
            # 0. ingest data
            self.tool_def.dataset_path = self.ingester.ingest()
            logger.info(f'Data ingested from {self.tool_def.dataset_path}')
        print('_accelerator', 100 * '*5')
        # 1. data process
        with TRACE_HELPER_TOOL.trace_block(
            "run",
            parent=get_telemetry_envelope_metadata(),
            extraAttributes={
                # "dataset_count": len(dataset),
                "cpu": self.runtime_np() if not self.use_cuda() else 0,
                "gpu": self.runtime_np() if self.use_cuda() else 0,
                "operation_name": self._name,
            }
        ):

            logger.info('Processing tool...')
            tstart = time.time()
            target_path: Path = self.process()
            print('_accelerator', 100 * '-5')
            tend = time.time()
            logger.info(f'Tool are done in {tend - tstart:.3f}s.')

        # 2. data export
        with TRACE_HELPER_TOOL.trace_block(
            "export",
            parent=get_telemetry_envelope_metadata(),
        ):
            logger.info(f'Exporting dataset to somewhere...')
            # TODO Add more exporter, for csghub, for local dist .etc
            output_branch_name = self.exporter.export_from_files(target_path)

        return None, output_branch_name    

    def process(self) -> Path:
        raise NotImplementedError

    def use_cuda(self):
        return self.accelerator == 'cuda' and is_cuda_available()
    
    def runtime_np(self):
        op_proc = calculate_np(self._name, self.mem_required,
                               self.cpu_required, self.num_proc,
                               self.use_cuda())
        logger.debug(
            f'Op [{self._name}] running with number of procs:{op_proc}')
        return op_proc

    @classmethod
    @property
    def description(cls):
        pass

    @classmethod
    @property
    def io_requirement(cls):
        pass

    @classmethod
    def init_params(cls, userid: str = None, isadmin: bool = False):
        pass