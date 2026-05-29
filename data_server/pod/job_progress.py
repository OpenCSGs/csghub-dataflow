"""After Argo Pod task completes, report job.data_count / process_count to workflow sync."""

from __future__ import annotations

import os
from typing import Any


def _safe_int(value) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def read_trace_operator_count(output_dir: str, operator_name: str) -> int | None:
    if not operator_name:
        return None
    count_path = os.path.join(output_dir, "trace", f"count-{operator_name}.txt")
    if not os.path.isfile(count_path):
        return None
    try:
        with open(count_path, "r", encoding="utf-8") as f:
            text = f.read().strip()
        return _safe_int(text) if text else None
    except OSError:
        return None


def count_jsonl_file_lines(file_path: str) -> int:
    if not file_path or not os.path.isfile(file_path):
        return 0
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return sum(1 for _ in f)
    except OSError:
        return 0


def normalize_tool_run_progress(run_result: Any) -> dict[str, int]:
    data_count = 0
    if isinstance(run_result, tuple):
        if run_result:
            data_count = _safe_int(run_result[0]) or 0
    elif isinstance(run_result, dict):
        data_count = _safe_int(run_result.get("data_count")) or 0
    elif run_result is not None:
        data_count = _safe_int(run_result) or 0
    return {"data_count": data_count, "process_count": data_count}


def build_operator_run_progress(
    *,
    output_dir: str,
    operator_name: str,
    operator_index: int,
    export_file: str,
) -> dict[str, int]:
    count = read_trace_operator_count(output_dir, operator_name)
    if count is None:
        count = count_jsonl_file_lines(export_file)

    progress: dict[str, int] = {}
    if operator_index <= 0:
        progress["data_count"] = count
        progress["process_count"] = count
    else:
        progress["process_count"] = count
    return progress


def extract_job_progress_from_task_result(result: Any) -> dict[str, int]:
    if not isinstance(result, dict):
        return {}
    progress: dict[str, int] = {}
    for key in ("data_count", "process_count"):
        val = _safe_int(result.get(key))
        if val is not None:
            progress[key] = val
    return progress
