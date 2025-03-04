#!/bin/bash

# Start Celery worker in the background
celery -A app.core.celery_utils worker --loglevel=info &

# Start Uvicorn in the foreground (for Render monitoring)
uvicorn app.main:app --host 0.0.0.0 --port 8000