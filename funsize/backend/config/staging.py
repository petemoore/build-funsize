"""
Celery configuration for dev environment
export FUNSIZE_CELERY_CONFIG="funsize.backend.config.dev" to use it
"""
import os

FUNSIZE_CONF_NAME = "staging"
CELERY_ACKS_LATE = True
CELERY_DEFAULT_QUEUE = "funsize_staging"
BROKER_URL = os.environ.get('BROKER_URL')
