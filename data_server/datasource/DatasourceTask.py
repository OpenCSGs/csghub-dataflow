from data_server.datasource.DatasourceModels import DataSource


def submit_datasource_task_legacy(data_source_db: DataSource, task_uid: str, user_name: str, user_token: str):
    raise RuntimeError("Legacy datasource scheduling has been retired. Use the CSGHub scheduling chain instead.")


def stop_legacy_task(task_uid: str):
    return False


def run_celery_task(data_source_db: DataSource, task_uid: str, user_name: str, user_token: str):
    return submit_datasource_task_legacy(data_source_db, task_uid, user_name, user_token)


def stop_celery_task(task_uid: str):
    return stop_legacy_task(task_uid)

