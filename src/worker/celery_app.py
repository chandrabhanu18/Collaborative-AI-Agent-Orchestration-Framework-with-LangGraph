"""
Celery application instance and configuration.
"""
import logging
from celery import Celery
from src.config.settings import settings
from src.db.session import init_db_sync

logger = logging.getLogger(__name__)

celery_app = Celery(
    "agent_orchestrator",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["src.worker.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,
    worker_prefetch_multiplier=1,
)


@celery_app.on_after_configure.connect
def setup_worker(sender, **kwargs):
    """Ensure database schema is ready on worker startup."""
    try:
        init_db_sync()
        logger.info("Worker initialized database schema successfully.")
    except Exception as e:
        logger.error(f"Worker DB init error: {e}")
