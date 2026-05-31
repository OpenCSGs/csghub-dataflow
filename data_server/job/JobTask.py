from datetime import datetime


def submit_pipeline_task_legacy(task_uuid: str, user_id: int, user_name: str, user_token: str, task_run_time: datetime):
    raise RuntimeError("Legacy pipeline scheduling has been retired. Use the CSGHub scheduling chain instead.")


def stop_legacy_task(task_uid: str, *_args, **_kwargs):
    return False


def run_pipline_task(task_uuid: str, user_id: int, user_name: str, user_token: str, task_run_time: datetime):
    return submit_pipeline_task_legacy(task_uuid, user_id, user_name, user_token, task_run_time)


def stop_celery_task(task_uid: str, *_args, **_kwargs):
    return stop_legacy_task(task_uid, *_args, **_kwargs)