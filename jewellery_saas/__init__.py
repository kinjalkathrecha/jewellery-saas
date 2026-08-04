# This project uses PostgreSQL. MySQL/PyMySQL support is not required.

from .celery import app as celery_app

__all__ = ("celery_app",)
