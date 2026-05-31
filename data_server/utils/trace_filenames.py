"""Trace file naming aligned with Tracer / retreive_job."""

from __future__ import annotations

# Tracer output: mapper-{op}.jsonl | filter-{op}.jsonl | duplicate-{op}.jsonl | count-{op}.txt


def parse_operator_name_from_trace_file(filename: str) -> str | None:
    """Same semantics as JobsManager.retreive_job split('-')[1] (operator name after first '-')."""
    base = filename.rsplit("/", 1)[-1]
    if base.endswith(".jsonl"):
        stem = base[: -len(".jsonl")]
        prefix, _, op = stem.partition("-")
        if prefix in ("mapper", "filter", "duplicate") and op:
            return op
        return None
    if base.endswith(".txt") and base.startswith("count-"):
        return base[len("count-") : -len(".txt")]
    return None


def is_legacy_trace_filename(filename: str, operator_name: str | None = None) -> bool:
    op = parse_operator_name_from_trace_file(filename)
    if not op:
        return False
    if operator_name and op != operator_name:
        return False
    return True


def expected_trace_filenames(operator_name: str) -> set[str]:
    return {
        f"mapper-{operator_name}.jsonl",
        f"filter-{operator_name}.jsonl",
        f"duplicate-{operator_name}.jsonl",
        f"count-{operator_name}.txt",
    }
