#!/bin/sh
MILLISECOND_TIMESTAMP=$(date +%s%3N)
HOSTNAME=$(hostname -f)
NODENAME="worker_${MILLISECOND_TIMESTAMP}_${HOSTNAME}"
celery -A data_celery.main:celery_app worker --loglevel=info --pool=eventlet -n "$NODENAME"