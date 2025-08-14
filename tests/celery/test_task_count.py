from data_celery.main import celery_app as app

i = app.control.inspect()
active_tasks = i.active()


if active_tasks:
    for worker, tasks in active_tasks.items():
        print(f"Worker {worker} is executing {len(tasks)} tasks.")
else:
    print("No active tasks found or unable to inspect workers.")