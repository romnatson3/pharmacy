from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from celery.app.log import TaskFormatter as CeleryTaskFormatter
from celery.signals import after_setup_task_logger, after_setup_logger
from celery._state import get_current_task
import logging
import re


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')

app = Celery('bot')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

app.conf.update(
    task_default_queue='sender'
)


class TaskFormatter(CeleryTaskFormatter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        green = '\033[32m'
        reset = '\033[0m'
        self.success_fmt = green + self._fmt + reset

    def format(self, record):
        task = get_current_task()
        if task and task.request:
            short_task_id = task.request.id.split('-')[0]
            record.__dict__.update(short_task_id=short_task_id)
        else:
            record.__dict__.setdefault('short_task_id', '--------')

        if record.levelno == logging.INFO and re.search(r'success', record.msg.lower()):
            formatter = CeleryTaskFormatter(self.success_fmt)
            return formatter.format(record)
        return super().format(record)


@after_setup_logger.connect
@after_setup_task_logger.connect
def setup_task_logger(logger, *args, **kwargs):
    for handler in logger.handlers:
        handler.setFormatter(TaskFormatter('[%(asctime)s] %(short_task_id)s [%(levelname)s] %(message)s'))
