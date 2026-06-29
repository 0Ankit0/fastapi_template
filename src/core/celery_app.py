from celery import Celery
from src.core.config import settings
from src.core.logging import configure_logging

configure_logging()

celery_app = Celery(
    settings.APP_INSTANCE_NAME,
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        'src.apps.iam.tasks',
        'src.apps.organizations.tasks',
        'src.apps.communication.tasks',
    ]
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=settings.CELERY_TASK_TIME_LIMIT,
    result_expires=settings.CELERY_RESULT_EXPIRES,
    task_default_queue=settings.CELERY_QUEUE_DEFAULT,
    
    # --- RabbitMQ Specific Optimization Best Practices ---
    # Late ACKs ensure tasks are acknowledged *after* execution completes.
    # If a worker dies mid-email/notification transmission, RabbitMQ safely requeues it.
    task_acks_late=True,
    
    # Prevents a single worker from hoarding tasks. Workers pull 1 task at a time,
    # distributing the load evenly across all active notification processes.
    worker_prefetch_multiplier=1,
    # ------------------------------------------------------

    # In development, run tasks inline (no worker / broker needed) unless overridden.
    task_always_eager=settings.CELERY_TASK_ALWAYS_EAGER,
    task_eager_propagates=settings.CELERY_TASK_ALWAYS_EAGER,
)

if __name__ == '__main__':
    celery_app.start()