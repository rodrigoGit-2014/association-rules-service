"""Celery task for refreshing materialized views"""

import logging

from celery_app.celery import celery_app
from app.db.session import engine
from app.db.matviews import refresh_matviews
from app.core.cache import cache

logger = logging.getLogger(__name__)


@celery_app.task(name='refresh_matviews')
def refresh_matviews_task() -> dict:
    """Refresh materialized views and invalidate related caches"""
    try:
        refresh_matviews(engine)
        cache.delete_pattern("v2:txn_summary:*")
        logger.info("Materialized views refreshed and cache invalidated")
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Failed to refresh materialized views: {e}", exc_info=True)
        return {"status": "failed", "error": str(e)}
