#!/usr/bin/env python3

import argparse
import json
import os
import sys

from loguru import logger

from data_server.pod.common_tasks import get_data_dir
from data_server.pod.task_runner import run_task


def parse_args():
    parser = argparse.ArgumentParser(description="Run unified DataFlow task in Argo pod")
    parser.add_argument("--task-type", required=True, help="task type: datasource|formatify|pipeline|tool")
    parser.add_argument("--task-params", required=True, help="JSON string for task parameters")
    return parser.parse_args()


def main():
    args = parse_args()
    try:
        task_params = json.loads(args.task_params)
    except json.JSONDecodeError as exc:
        raise ValueError(f"task_params is not valid JSON: {exc}") from exc

    data_dir = get_data_dir()
    logger.info(
        "Starting dataflow pod task, type={} | DATA_DIR={}",
        args.task_type,
        data_dir,
    )
    run_task(args.task_type, task_params)
    logger.info(f"Dataflow pod task finished, type={args.task_type}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        logger.exception(f"Dataflow pod task failed: {exc}")
        sys.exit(1)
