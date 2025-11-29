import sys
import traceback
from loguru import logger

from data_engine.utils.availability_utils import UNAVAILABLE_OPERATORS

from .base_op import OPERATORS
from .op_fusion import fuse_operators
from data_celery.mongo_tools.tools import (insert_pipline_job_run_task_log_error,
                                           set_pipline_job_operator_status,
                                           OperatorStatusEnum)


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
    try:
        for process in process_list:
            op_name, args = list(process.items())[0]
            # 检查 OP 是否可用
            if op_name in UNAVAILABLE_OPERATORS:
                # OP 不可用，记录日志，抛出异常，退出进程
                error_msg = UNAVAILABLE_OPERATORS[op_name].get_warning_msg()
                logger.error(error_msg)
                logger.error("Exiting process due to operator unavailability.")
                insert_pipline_job_run_task_log_error(job_uid, error_msg, operator_name=op_name, operator_index=index)
                set_pipline_job_operator_status(job_uid, OperatorStatusEnum.ERROR, op_name, operator_index=index)
                # 抛出异常，让上层能够捕获并更新任务状态
                raise RuntimeError(error_msg)
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
    except Exception as e:
        # 捕获异常，记录日志，抛出异常
        logger.error(f"Error occurred while loading operators: {e}")
        traceback.print_exc()
        if job_uid:
            insert_pipline_job_run_task_log_error(job_uid, f"Error occurred while loading operators: {e}")
        # 抛出异常，让上层能够捕获并更新任务状态
        raise
