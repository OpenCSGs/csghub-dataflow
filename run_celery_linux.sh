#!/bin/sh

export DATABASE_HOSTNAME=127.0.0.1
export DATABASE_PORT=5433
export DATABASE_USERNAME=postgres
export DATABASE_PASSWORD=postgres
export DATABASE_DB=data_flow

export DATA_DIR=/tmp/data_flow/data 
export CSGHUB_ENDPOINT=https://hub.opencsg-stg.com
export REDIS_HOST_URL=redis://127.0.0.1:16379
export MONG_HOST_URL=mongodb://root:example@net-power.9free.com.cn:18123

export STUDIO_JUMP_URL=https://opencsg.com

export MAX_WORKERS=99

MILLISECOND_TIMESTAMP=$(date +%s%3N)
HOSTNAME=$(hostname -f)
NODENAME="worker_${MILLISECOND_TIMESTAMP}_${HOSTNAME}"

# celery -A data_celery.main:celery_app worker --loglevel=info --pool=eventlet -n $NODENAME

NODENAME=$HOSTNAME
celery -A data_celery.main:celery_app worker --loglevel=info --pool=gevent -n $NODENAME
