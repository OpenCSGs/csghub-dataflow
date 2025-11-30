import os

import pyarrow as pa
from loguru import logger

from data_engine import cuda_device_count
from data_engine.core.data import DJDataset
from data_engine.ops import Filter, Mapper, Deduplicator, Selector
from data_engine.utils.availability_utils import AvailabilityChecking
from data_engine.utils.constant import Fields
from data_engine.utils.process_utils import calculate_np

import datasets
with AvailabilityChecking(['ray'], requires_type='dist'):
    from ray.data import Dataset
    import ray


def is_valid_path(item, dataset_dir):
    full_path = os.path.abspath(os.path.join(dataset_dir, item))
    return os.path.exists(full_path)


def convert_to_absolute_paths(dict_with_paths, dataset_dir, path_keys):
    for key in path_keys:
        if key not in dict_with_paths:
            continue
        if isinstance(dict_with_paths[key], list):
            dict_with_paths[key] = [
                os.path.abspath(os.path.join(dataset_dir, item))
                if isinstance(item, str) and is_valid_path(dataset_dir, item)
                else item for item in dict_with_paths[key]
            ]
        elif isinstance(dict_with_paths[key], str):
            dict_with_paths[key] = os.path.abspath(
                os.path.join(dataset_dir,
                             dict_with_paths[key])) if is_valid_path(
                                 dict_with_paths[key],
                                 dataset_dir) else dict_with_paths[key]
    return dict_with_paths


# TODO: check path for nestdataset
def set_dataset_to_absolute_path(dataset, dataset_path, cfg):
    """
    Set all the path in input data to absolute path.
    Checks dataset_dir and project_dir for valid paths.
    """
    if not (cfg.video_key in dataset.columns() or cfg.image_key
            in dataset.columns() or cfg.audio_key in dataset.columns()):
        return dataset
    dataset_dir = os.path.dirname(dataset_path)
    dataset = dataset.map(lambda item: convert_to_absolute_paths(
        item, dataset_dir, [cfg.video_key, cfg.image_key, cfg.audio_key]))
    logger.info(f"transfer {dataset.count()} sample's paths")
    return dataset


def preprocess_dataset(dataset: Dataset, dataset_path, cfg) -> Dataset:
    if dataset_path:
        dataset = set_dataset_to_absolute_path(dataset, dataset_path, cfg)
    columns = dataset.columns()
    if Fields.stats not in columns:
        logger.info(f'columns {columns}')

        def process_batch_arrow(table: pa.Table) -> pa.Table:
            new_column_data = [{} for _ in range(len(table))]
            new_talbe = table.append_column(Fields.stats, [new_column_data])
            return new_talbe

        dataset = dataset.map_batches(process_batch_arrow,
                                      batch_format='pyarrow')
    return dataset


def get_num_gpus(op, op_proc):
    if not op.use_cuda():
        return 0
    proc_per_gpu = op_proc / cuda_device_count()
    return 1.0 / proc_per_gpu

def reset_log(log_dir: str):
    # setup logger
    from data_engine.utils.logger_utils import setup_logger
    log_dir = os.path.join(log_dir, 'log')
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    logfile_name = 'pipeline_fake.txt'
    setup_logger(save_dir=log_dir,
                filename=logfile_name,
                level='INFO',
                redirect=True)


@ray.remote
def ray_run_filter(op: filter, data: Dataset, num_gpus: int, concurrency: int, log_dir: str):
    reset_log(log_dir)
    data = data.map_batches(op.compute_stats,
                            batch_size=1,
                            batch_format='pyarrow',
                            num_gpus=num_gpus,
                            num_cpus=1,
                            concurrency=concurrency)

    data = data.filter(op.process, concurrency=concurrency)
    return data.take_all()

@ray.remote
def ray_run_mapper(op: Mapper, data: Dataset, num_gpus: int,  concurrency: int, log_dir: str):
    reset_log(log_dir)
    data = data.map_batches(op.process,
                            batch_size=1,
                            batch_format='pyarrow',
                            num_gpus=num_gpus,
                            num_cpus=1,
                            concurrency=concurrency)

    return data.take_all()

@ray.remote
def ray_run_deduplicator(op: Deduplicator, data: Dataset, num_gpus: int,  concurrency: int, log_dir: str):
    reset_log(log_dir)
    data = data.map_batches(op.compute_hash,
                            batch_size=1,
                            batch_format='pyarrow',
                            num_gpus=num_gpus,
                            num_cpus=1,
                            concurrency=concurrency)
    
    data = datasets.Dataset.from_list(data.take_all())
    new_dataset, dup_pairs = op.process(data, 10)
    return (new_dataset.to_list(), dup_pairs)

@ray.remote
def ray_run_selector(op: Selector, data: Dataset, num_gpus: int,  concurrency: int, log_dir: str):
    reset_log(log_dir)
    data = datasets.Dataset.from_list(data.take_all())
    new_dataset = op.process(data)
    return new_dataset.to_list()

class RayDataset(DJDataset):

    def __init__(self,
                 *,
                 dataset: Dataset,
                 dataset_path: str = None,
                 cfg=None) -> None:
        self.data = preprocess_dataset(dataset, dataset_path, cfg)
        self.num_proc = None
        if cfg:
            self.num_proc = cfg.np

    def process(self,
                operators,
                *,
                exporter=None,
                checkpointer=None,
                tracer=None) -> DJDataset:
        if operators is None:
            return self
        if not isinstance(operators, list):
            operators = [operators]
        for op in operators:
            self._run_single_op(op, tracer)
        return self

    def _run_single_op(self, op, tracer):
        op_proc = calculate_np(op._name, op.mem_required, op.cpu_required,
                               self.num_proc, op.use_cuda())
        num_gpus = get_num_gpus(op, op_proc)
        log_dir = os.environ.get("RAY_LOG_DIR")
        try:
            if isinstance(op, Mapper):
                origin_dataset = self.data

                self.data = ray.get(ray_run_mapper.options(num_cpus=op_proc).remote(op, self.data, num_gpus, op_proc, log_dir))
                if tracer:
                    tracer.trace_mapper(op._name, origin_dataset, self.data,
                                        op.text_key)

            elif isinstance(op, Filter):
                origin_dataset = self.data

                self.data = ray.get(ray_run_filter.options(num_cpus=op_proc).remote(op, self.data, num_gpus, op_proc, log_dir))
                if tracer:
                    tracer.trace_filter(op._name, origin_dataset, self.data)

            elif isinstance(op, Deduplicator):
                origin_dataset = self.data

                self.data, dup_pairs = ray.get(ray_run_deduplicator.options(num_cpus=op_proc).remote(op, self.data, num_gpus, op_proc, log_dir))
                if tracer:
                    tracer.trace_deduplicator(op._name, origin_dataset, dup_pairs)

            elif isinstance(op, Selector):
                origin_dataset = self.data

                self.data = ray.get(ray_run_selector.options(num_cpus=1).remote(op, self.data, num_gpus, op_proc, log_dir))
                if tracer:
                    tracer.trace_filter(op._name, origin_dataset, self.data)

            else:
                logger.error(
                    'Ray executor only support Filter and Mapper OPs for now')
                raise NotImplementedError
        except:  # noqa: E722
            logger.error(f'An error occurred during Op [{op._name}].')
            import traceback
            traceback.print_exc()
            exit(1)
