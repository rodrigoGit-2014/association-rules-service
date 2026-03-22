"""Celery application configuration for Apriori v2 tasks"""

from celery import Celery
import os
from kombu import Exchange, Queue

CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/2')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/2')
MATVIEW_REFRESH_MINUTES = int(os.getenv('MATVIEW_REFRESH_MINUTES', '30'))

celery_app = Celery('apriori_v2')

celery_app.conf.update(
    broker_url=CELERY_BROKER_URL,
    result_backend=CELERY_RESULT_BACKEND,
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=1800,
    task_soft_time_limit=1700,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=10,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    result_expires=3600,

    task_routes={
        'run_apriori': {'queue': 'apriori', 'routing_key': 'apriori'},
        'refresh_matviews': {'queue': 'maintenance', 'routing_key': 'maintenance'},
    },

    task_queues=(
        Queue('apriori', Exchange('apriori'), routing_key='apriori'),
        Queue('maintenance', Exchange('maintenance'), routing_key='maintenance'),
    ),

    task_annotations={
        'run_apriori': {'rate_limit': '3/m'},
    },

    beat_schedule={
        'refresh-materialized-views': {
            'task': 'refresh_matviews',
            'schedule': MATVIEW_REFRESH_MINUTES * 60,
        },
    },
)

celery_app.conf.update(
    include=[
        'celery_app.tasks.run_apriori',
        'celery_app.tasks.refresh_matviews',
    ]
)

if __name__ == '__main__':
    celery_app.start()
