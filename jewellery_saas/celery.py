import os
from celery import Celery

# Set default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'jewellery_saas.settings')

app = Celery('jewellery_saas')

# Read config from Django settings with namespace CELERY
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs
app.autodiscover_tasks()

from celery.signals import task_failure

@task_failure.connect
def handle_task_failure(sender=None, task_id=None, exception=None, args=None, kwargs=None, traceback=None, einfo=None, **extra):
    """
    Hook connecting to task failures. If a task has exhausted all of its retries,
    this sends a cloned audit message to the 'failed' queue.
    """
    # sender is the task object itself
    max_retries = getattr(sender, 'max_retries', 0)
    request_retries = getattr(sender.request, 'retries', 0)

    # Note: if it has failed and current retries >= max_retries, it's permanently failed.
    if request_retries >= max_retries:
        from celery import current_app
        current_app.send_task(
            "core.tasks.handle_failed_task",
            args=[sender.name, task_id, args, kwargs, str(exception)],
            queue="failed"
        )

