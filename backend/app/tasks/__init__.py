from .celery_app import celery_app
from .ingestion_tasks import process_document

__all__ = ["celery_app", "process_document"]
