"""Apriori analysis endpoints"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.config import settings
from app.services.apriori_service import AprioriService
from app.models.analysis_run import AnalysisStatus
from app.schemas.analysis import (
    AprioriRequest,
    AprioriResponse,
    AssociationRuleResponse,
    AprioriAsyncResponse,
    DeleteRunResponse,
    DeleteAllRunsResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/analysis/apriori",
    response_model=AprioriResponse,
    responses={202: {"model": AprioriAsyncResponse}},
)
def run_apriori_analysis(
    request: AprioriRequest,
    db: Session = Depends(get_db),
):
    """
    Run Apriori analysis on transactions within a date range.

    Small datasets (< SYNC_THRESHOLD) execute synchronously and return rules.
    Large datasets dispatch to Celery and return 202 with a poll URL.
    """
    service = AprioriService(db)

    transaction_count = service.estimate_size(
        start_date=request.start_date,
        end_date=request.end_date,
        department_id=request.department_id,
        section_id=request.section_id,
    )

    logger.info(f"Estimated {transaction_count} transactions for analysis")

    if transaction_count <= settings.SYNC_THRESHOLD:
        rules = service.execute_sync(
            start_date=request.start_date,
            end_date=request.end_date,
            department_id=request.department_id,
            section_id=request.section_id,
            min_support=request.min_support,
            min_confidence=request.min_confidence,
            min_lift=request.min_lift,
        )
        return AprioriResponse(
            rules=[AssociationRuleResponse(**r) for r in rules]
        )

    # Async execution for large datasets
    run = service.create_run(
        min_support=request.min_support,
        min_confidence=request.min_confidence,
        min_lift=request.min_lift,
        fecha_inicio=request.start_date,
        fecha_fin=request.end_date,
        id_departamento=request.department_id,
        id_seccion=request.section_id,
    )

    from celery_app.tasks.run_apriori import run_apriori_task
    run_apriori_task.delay(str(run.id))

    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={
            "run_id": str(run.id),
            "status": "processing",
            "poll_url": f"/api/v1/analysis/apriori/{run.id}",
        },
    )


@router.get("/analysis/apriori/{run_id}", response_model=AprioriResponse)
def get_analysis_result(
    run_id: UUID,
    db: Session = Depends(get_db),
):
    """Poll for async analysis results"""
    service = AprioriService(db)
    run = service.run_repo.get(run_id)

    if not run:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": f"Analysis run {run_id} not found"},
        )

    if run.status == AnalysisStatus.PROCESSING or run.status == AnalysisStatus.PENDING:
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={
                "run_id": str(run.id),
                "status": run.status.value,
                "poll_url": f"/api/v1/analysis/apriori/{run.id}",
            },
        )

    if run.status == AnalysisStatus.FAILED:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "run_id": str(run.id),
                "status": "failed",
                "error": run.error_message,
            },
        )

    # COMPLETED — return rules
    rules = service.rule_repo.get_rules_by_run(run_id)
    return AprioriResponse(
        rules=[
            AssociationRuleResponse(
                antecedent=list(r.antecedents),
                consequent=list(r.consequents),
                support=round(float(r.support), 6),
                confidence=round(float(r.confidence), 6),
                lift=round(float(r.lift), 4),
            )
            for r in rules
        ]
    )


@router.delete("/analysis/apriori/{run_id}", response_model=DeleteRunResponse)
def delete_analysis_run(
    run_id: UUID,
    db: Session = Depends(get_db),
):
    """Delete an analysis run and all its associated rules (CASCADE)"""
    service = AprioriService(db)
    run = service.run_repo.get(run_id)

    if not run:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": f"Analysis run {run_id} not found"},
        )

    rules_count = len(run.rules)
    service.run_repo.delete(run_id)

    logger.info(f"Deleted analysis run {run_id} with {rules_count} rules")

    return DeleteRunResponse(
        run_id=str(run_id),
        rules_deleted=rules_count,
        message="Analysis run and associated rules deleted",
    )


@router.delete("/analysis/apriori", response_model=DeleteAllRunsResponse)
def delete_all_analysis_runs(
    db: Session = Depends(get_db),
):
    """Delete all analysis runs and their associated rules"""
    from app.models.analysis_run import AnalysisRun
    from app.models.association_rule import AssociationRule

    rules_count = db.query(AssociationRule).count()
    runs_count = db.query(AnalysisRun).count()

    db.query(AssociationRule).delete()
    db.query(AnalysisRun).delete()
    db.commit()

    logger.info(f"Deleted all analysis: {runs_count} runs, {rules_count} rules")

    return DeleteAllRunsResponse(
        runs_deleted=runs_count,
        rules_deleted=rules_count,
        message="All analysis runs and rules deleted",
    )
