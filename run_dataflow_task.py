#!/usr/bin/env python3

import argparse
import json
import os
import sys
import warnings
from datetime import datetime, timezone

from loguru import logger


# Suppress Pydantic V2 namespace warnings from third-party packages
# (e.g. AWS SDK models using "model_arn" which conflicts with Pydantic V2 "model_" namespace)
warnings.filterwarnings(
    "ignore",
    message='Field "model_arn" has conflict with protected namespace "model_"',
    category=UserWarning,
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def parse_args():
    parser = argparse.ArgumentParser(description="Run unified DataFlow task in Argo pod")
    parser.add_argument("--task-type", required=True,
                        help="task type: datasource|formatify|pipeline|tool")
    parser.add_argument("--task-params", required=True,
                        help="JSON string for task parameters")
    return parser.parse_args()


def _sync_step_started_early(task_type: str, task_params: dict):
    """Send step_started sync before heavy imports to eliminate ~36s startup delay."""
    try:
        # Lazy-import workflow_sync_client (stdlib+loguru only, no heavy deps)
        from data_server.pod.workflow_sync_client import push_workflow_sync

        started_at = _utc_now_iso()
        push_workflow_sync(
            task_params=task_params,
            event="step_started",
            finalize=False,
            started_at=started_at,
            main_status="Running",
            fail_on_error=False,
        )
    except Exception as exc:
        logger.warning("Early workflow step_started sync failed: {}", exc)


def main():
    args = parse_args()
    try:
        task_params = json.loads(args.task_params)
    except json.JSONDecodeError as exc:
        raise ValueError(f"task_params is not valid JSON: {exc}") from exc

    # Resolve DATA_DIR inline (avoid pulling in common_tasks heavy import chain)
    data_dir = os.getenv("DATA_DIR", "").strip().rstrip("/") or "/dataflow_data"

    logger.info(
        "Starting dataflow pod task, type={} | DATA_DIR={}",
        args.task_type,
        data_dir,
    )

    # Send step_started BEFORE heavy imports (data_engine, models, etc.)
    _sync_step_started_early(args.task_type, task_params)

    # Deferred import: this triggers data_engine + data_server.logic.models + all heavy modules
    from data_server.pod.task_runner import run_task

    run_task(args.task_type, task_params)
    logger.info("Dataflow pod task finished, type={}", args.task_type)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        logger.exception("Dataflow pod task failed: {}", exc)
        sys.exit(1)
