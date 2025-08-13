import sys

from loguru import logger

from data_engine.utils.availability_utils import UNAVAILABLE_OPERATORS

from .base_op import OPERATORS
from .op_fusion import fuse_operators
from data_celery.mongo_tools.tools import insert_pipline_job_run_task_log_error

def load_ops(process_list, op_fusion=False,job_uid=""):
    """
    Load op list according to the process list from config file.

    :param process_list: A process list. Each item is an op name and its
        arguments.
    :param op_fusion: whether to fuse ops that share the same intermediate
        variables.
    :param job_uid: pipline job uid
    :return: The op instance list.
    """
    ops = []
    new_process_list = []
    index = 0
    for process in process_list:
        op_name, args = list(process.items())[0]
        if op_name in UNAVAILABLE_OPERATORS:
            logger.error(UNAVAILABLE_OPERATORS[op_name].get_warning_msg())
            insert_pipline_job_run_task_log_error(job_uid, UNAVAILABLE_OPERATORS[op_name].get_warning_msg())
            sys.exit(UNAVAILABLE_OPERATORS[op_name].get_warning_msg())
        op = OPERATORS.modules[op_name](**args)
        op.pipline_index = index
        op.job_uid = job_uid
        ops.append(op)
        new_process_list.append(process)
        index += 1

    # detect filter groups
    if op_fusion:
        new_process_list, ops = fuse_operators(new_process_list, ops,job_uid=job_uid)

    for op_cfg, op in zip(new_process_list, ops):
        op._op_cfg = op_cfg

    return ops
