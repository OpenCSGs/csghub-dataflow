"""Split task_params.config by node when Pipeline submits to CSGHub."""

from typing import Any

from data_server.logic.utils import strip_recipe_scheduler_fields

# data_engine init_configs / operator execution; excludes project_name, repo_id, branch, etc.
OPERATOR_RUNTIME_KEYS = (
    "type",
    "text_keys",
    "suffixes",
    "np",
    "executor_type",
    "ray_address",
    "op_fusion",
    "use_cache",
    "ds_cache_dir",
    "use_checkpoint",
    "temp_dir",
    "export_shard_size",
    "export_in_parallel",
    "open_tracer",
    "trace_num",
    "op_list_to_trace",
    "cache_compress",
    "keep_stats_in_res_ds",
    "keep_hashes_in_res_ds",
    "percentiles",
    "export_original_dataset",
    "save_stats_in_one_file",
)


def split_task_params_without_config(task_params: dict[str, Any]) -> dict[str, Any]:
    """Keep scheduling/auth/path fields; drop full Recipe config."""
    return {k: v for k, v in task_params.items() if k != "config"}


def extract_operator_runtime(full_config: dict[str, Any]) -> dict[str, Any]:
    if not full_config:
        return {}
    return {k: full_config[k] for k in OPERATOR_RUNTIME_KEYS if k in full_config}


def build_per_operator_config(full_config: dict[str, Any], op: dict[str, Any]) -> dict[str, Any]:
    """Single-operator Pod: data_engine runtime params + current operator process (no repo/path/scheduling)."""
    clean_full = strip_recipe_scheduler_fields(full_config)
    cfg = extract_operator_runtime(clean_full)
    # Required for Recipe model validation; excluded by exclude_fields_config when generating operator YAML
    cfg.setdefault("project_name", clean_full.get("project_name") or "pipeline_operator")
    cfg["process"] = [op]
    return cfg
