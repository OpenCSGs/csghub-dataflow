from .base_exporter import Exporter
from .csghub_exporter import ExporterCSGHUB

def load_exporter(
    export_path,
    export_shard_size=0,
    export_in_parallel=True,
    num_proc=1,
    export_ds=True,
    keep_stats_in_res_ds=False,
    keep_hashes_in_res_ds=False,
    export_stats=True,
    repo_id: str=None,
    branch: str=None,
    user_name: str=None,
    user_token: str=None,
    work_dir: str=None,
) -> Exporter:
    return ExporterCSGHUB(
        export_path=export_path,
        export_shard_size=export_shard_size,
        export_in_parallel=export_in_parallel,
        num_proc=num_proc,
        export_ds=export_ds,
        keep_stats_in_res_ds=keep_stats_in_res_ds,
        keep_hashes_in_res_ds=keep_hashes_in_res_ds,
        export_stats=export_stats,
        repo_id=repo_id,
        branch=branch,
        user_name=user_name,
        user_token=user_token,
        work_dir=work_dir
    )