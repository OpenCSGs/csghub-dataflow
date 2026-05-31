def submit_formatify_task_legacy(task_id: int, user_name: str, user_token: str):
    raise RuntimeError("Legacy formatify scheduling has been retired. Use the CSGHub scheduling chain instead.")


def stop_legacy_task(task_uid: str):
    return False


def run_format_task(task_id: int, user_name: str, user_token: str):
    return submit_formatify_task_legacy(task_id, user_name, user_token)


def stop_celery_task(task_uid: str):
    return stop_legacy_task(task_uid)