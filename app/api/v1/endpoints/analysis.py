"""Apriori analysis endpoints"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.auth_deps import get_current_user, TokenData
from app.services.apriori_service import AprioriService
from app.schemas.analysis import (
    AprioriRequest,
    AprioriResponse,
    AssociationRuleResponse,
    DeleteRunResponse,
    DeleteAllRunsResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/analysis/apriori", response_model=AprioriResponse)
def run_apriori_analysis(
    request: AprioriRequest,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """Run Apriori analysis synchronously and return rules"""
    service = AprioriService(db)

    logger.info(f"Running Apriori analysis: {request.start_date} to {request.end_date}")

    rules = service.execute_sync(
        company_id=current_user.company_id,
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


@router.get("/analysis/apriori/{run_id}", response_model=AprioriResponse)
def get_analysis_result(
    run_id: UUID,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """Get rules from a previous analysis run"""
    service = AprioriService(db)
    run = service.run_repo.get(run_id)

    if not run:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": f"Analysis run {run_id} not found"},
        )

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
    current_user: TokenData = Depends(get_current_user),
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
    current_user: TokenData = Depends(get_current_user),
):
    """Delete all analysis runs and their associated rules"""
    from app.models.analysis_run import AnalysisRun
    from app.models.association_rule import AssociationRule

    rules_count = db.query(AssociationRule).join(AnalysisRun).filter(AnalysisRun.company_id == current_user.company_id).count()
    runs_count = db.query(AnalysisRun).filter(AnalysisRun.company_id == current_user.company_id).count()

    db.query(AssociationRule).filter(AssociationRule.run_id.in_(
        db.query(AnalysisRun.id).filter(AnalysisRun.company_id == current_user.company_id)
    )).delete(synchronize_session=False)
    db.query(AnalysisRun).filter(AnalysisRun.company_id == current_user.company_id).delete(synchronize_session=False)
    db.commit()

    logger.info(f"Deleted all analysis: {runs_count} runs, {rules_count} rules")

    return DeleteAllRunsResponse(
        runs_deleted=runs_count,
        rules_deleted=rules_count,
        message="All analysis runs and rules deleted",
    )
