#!/bin/bash

# 启动 Celery beat 作为后台进程
celery -A data_celery.main:celery_app beat

# 启动 FastAPI API 服务器，并替换当前 shell 进程
exec uvicorn data_server.main:app --host 0.0.0.0 --port 8000