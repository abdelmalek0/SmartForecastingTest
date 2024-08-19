# celery_config.py
from celery import Celery
from constants import CELERY_RESULT_BACKEND, CELERY_BROKER_URL, MODULE

def make_celery(app):
    celery = Celery(
        MODULE,
        backend=CELERY_RESULT_BACKEND,
        broker=CELERY_BROKER_URL
    )
    # celery.conf.update(app.config)
    celery.autodiscover_tasks(['async_tasks'])
    return celery
