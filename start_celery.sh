#!/bin/bash

# Set the PYTHONPATH to include the parent directory
export PYTHONPATH=/home/debian/SmartForecasting

# Change to the directory where Celery should run
cd /home/debian/SmartForecasting/smartforecasting

# Run Celery worker within the Poetry environment
exec /home/debian/.local/bin/poetry run celery -A async_tasks worker --loglevel=info --logfile=/home/debian/SmartForecasting/logs/celery_worker.log --pidfile=/home/debian/SmartForecasting/logs/celery_worker.pid
