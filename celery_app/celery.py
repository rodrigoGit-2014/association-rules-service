"""Celery application configuration for Apriori tasks"""

from celery import Celery
import os
from kombu import Exchange, Queue

CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/1')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/1')

celery_app = Celery('apriori_analytics')

celery_app.conf.update(
    broker_url=CELERY_BROKER_URL,
    result_backend=CELERY_RESULT_BACKEND,
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=1800,  # 30 minutes hard limit
    task_soft_time_limit=1700,  # ~28 minutes soft limit
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=20,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    result_expires=3600,

    task_routes={
        'run_apriori': {
            'queue': 'apriori',
            'routing_key': 'apriori',
        }
    },

    task_queues=(
        Queue('apriori', Exchange('apriori'), routing_key='apriori'),
    ),

    task_annotations={
        'run_apriori': {
            'rate_limit': '3/m',
        }
    }
)

celery_app.conf.update(
    include=['celery_app.tasks.run_apriori']
)

if __name__ == '__main__':
    celery_app.start()
