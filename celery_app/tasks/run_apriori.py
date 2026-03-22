"""Celery task for running Apriori analysis"""

import logging
from typing import Dict
from celery import Task
from sqlalchemy.exc import SQLAlchemyError

from celery_app.celery import celery_app
from app.db.session import SessionLocal
from app.services.apriori_service import AprioriService

logger = logging.getLogger(__name__)


class AprioriProcessingTask(Task):
    """Base task class with retry logic for Apriori analysis"""
    autoretry_for = (SQLAlchemyError,)
    retry_kwargs = {'max_retries': 2}
    retry_backoff = True
    retry_backoff_max = 300
    retry_jitter = True


@celery_app.task(bind=True, base=AprioriProcessingTask, name='run_apriori')
def run_apriori_task(self, run_id: str) -> Dict:
    """Execute Apriori analysis asynchronously"""
    db = SessionLocal()

    try:
        logger.info(f"Starting Apriori analysis for run {run_id}")
        service = AprioriService(db)
        result = service.execute_analysis(run_id)
        logger.info(f"Apriori analysis completed for run {run_id}: {result}")
        return result

    except Exception as e:
        logger.error(f"Critical error in Apriori analysis {run_id}: {e}", exc_info=True)

        try:
            from app.models.analysis_run import AnalysisRun, AnalysisStatus
            run = db.query(AnalysisRun).filter(AnalysisRun.id == run_id).first()
            if run and run.status != AnalysisStatus.FAILED:
                run.update_status(AnalysisStatus.FAILED, error_message=str(e))
                db.commit()
        except Exception as update_error:
            logger.error(f"Failed to update run status: {update_error}")

        raise

    finally:
        db.close()
