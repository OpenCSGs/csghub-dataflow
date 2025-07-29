from data_celery.main import celery_app as app
# 使用Inspect API查询正在执行的任务
i = app.control.inspect()
active_tasks = i.active()

# 打印每台worker正在执行的任务数量
if active_tasks:
    for worker, tasks in active_tasks.items():
        print(f"Worker {worker} is executing {len(tasks)} tasks.")
else:
    print("No active tasks found or unable to inspect workers.")