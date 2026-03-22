"""Association rules analysis endpoints"""

from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.services.apriori_service import AprioriService
from app.repositories.analysis_run_repository import AnalysisRunRepository
from app.repositories.association_rule_repository import AssociationRuleRepository
from app.models.analysis_run import AnalysisStatus
from app.schemas.association import (
    AprioriConfigRequest,
    AnalysisRunResponse,
    AnalysisRunCreateResponse,
    AssociationRuleResponse,
    RulesListResponse,
    RulesKPIs,
    LLMExplanationRequest,
    LLMExplanationResponse,
)

router = APIRouter()


@router.post(
    "/association/analyze",
    response_model=AnalysisRunCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger Apriori analysis"
)
def trigger_analysis(
    config: AprioriConfigRequest,
    db: Session = Depends(get_db)
):
    if config.fecha_inicio and config.fecha_fin and config.fecha_inicio > config.fecha_fin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="fecha_inicio must be before or equal to fecha_fin"
        )

    service = AprioriService(db)

    try:
        run = service.create_run(
            min_support=config.min_support,
            min_confidence=config.min_confidence,
            min_lift=config.min_lift,
            max_itemset_size=config.max_itemset_size,
            max_rules=config.max_rules,
            fecha_inicio=config.fecha_inicio,
            fecha_fin=config.fecha_fin,
            id_departamento=config.id_departamento,
            id_seccion=config.id_seccion
        )

        from celery_app.tasks.run_apriori import run_apriori_task
        run_apriori_task.delay(str(run.id))

        return AnalysisRunCreateResponse(
            run_id=run.id,
            status=run.status.value,
            message="Analysis queued for processing",
            created_at=run.created_at
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger analysis: {str(e)}"
        )


@router.get(
    "/association/runs",
    response_model=list[AnalysisRunResponse],
    summary="List analysis runs"
)
def list_runs(
    limit: int = Query(10, ge=1, le=50),
    offset: int = Query(0, ge=0),
    run_status: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db)
):
    repo = AnalysisRunRepository(db)
    runs = repo.get_runs(limit=limit, offset=offset, status=run_status)
    return [AnalysisRunResponse.model_validate(r) for r in runs]


# IMPORTANT: /latest/rules MUST be before /{run_id}/rules to avoid UUID parse conflict
@router.get(
    "/association/runs/latest/rules",
    response_model=RulesListResponse,
    summary="Get rules from the latest completed analysis"
)
def get_latest_rules(
    min_lift: Optional[float] = Query(None, ge=0),
    min_confidence: Optional[float] = Query(None, ge=0, le=1),
    product: Optional[str] = Query(None),
    strength: Optional[str] = Query(None),
    sort_by: str = Query("lift", pattern="^(lift|confidence|support)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    run_repo = AnalysisRunRepository(db)
    run = run_repo.get_latest_completed()
    if not run:
        raise HTTPException(status_code=404, detail="No completed analysis runs found")

    return _get_rules_response(
        run_id=run.id,
        min_lift=min_lift,
        min_confidence=min_confidence,
        product=product,
        strength=strength,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
        db=db
    )


@router.get(
    "/association/runs/{run_id}",
    response_model=AnalysisRunResponse,
    summary="Get analysis run status"
)
def get_run(run_id: UUID, db: Session = Depends(get_db)):
    repo = AnalysisRunRepository(db)
    run = repo.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Analysis run not found")
    return AnalysisRunResponse.model_validate(run)


@router.get(
    "/association/runs/{run_id}/rules",
    response_model=RulesListResponse,
    summary="Get rules for an analysis run"
)
def get_rules(
    run_id: UUID,
    min_lift: Optional[float] = Query(None, ge=0),
    min_confidence: Optional[float] = Query(None, ge=0, le=1),
    product: Optional[str] = Query(None),
    strength: Optional[str] = Query(None),
    sort_by: str = Query("lift", pattern="^(lift|confidence|support)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    # Verify run exists and is completed
    run_repo = AnalysisRunRepository(db)
    run = run_repo.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Analysis run not found")
    if run.status != AnalysisStatus.COMPLETED:
        raise HTTPException(status_code=400, detail=f"Analysis run is {run.status.value}, not completed")

    return _get_rules_response(
        run_id=run_id,
        min_lift=min_lift,
        min_confidence=min_confidence,
        product=product,
        strength=strength,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
        db=db
    )


@router.post(
    "/association/runs/{run_id}/explain",
    response_model=LLMExplanationResponse,
    summary="Generate LLM explanations for rules"
)
def explain_rules(
    run_id: UUID,
    request: LLMExplanationRequest,
    db: Session = Depends(get_db)
):
    from app.core.config import settings

    if not settings.LLM_ENABLED:
        raise HTTPException(
            status_code=400,
            detail="LLM interpretation is disabled. Set LLM_ENABLED=true to activate."
        )

    run_repo = AnalysisRunRepository(db)
    run = run_repo.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Analysis run not found")
    if run.status != AnalysisStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Analysis must be completed before explaining")

    from app.services.llm_service import LLMService
    llm_service = LLMService(db)

    try:
        explanations = llm_service.explain_rules(
            run_id=run_id,
            rule_ids=request.rule_ids,
            top_n=request.top_n
        )
        return LLMExplanationResponse(run_id=run_id, explanations=explanations)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate explanations: {str(e)}"
        )


@router.delete(
    "/association/runs/{run_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an analysis run and its rules"
)
def delete_run(run_id: UUID, db: Session = Depends(get_db)):
    repo = AnalysisRunRepository(db)
    if not repo.delete(run_id):
        raise HTTPException(status_code=404, detail="Analysis run not found")


def _get_rules_response(
    run_id: UUID,
    min_lift: Optional[float],
    min_confidence: Optional[float],
    product: Optional[str],
    strength: Optional[str],
    sort_by: str,
    sort_order: str,
    page: int,
    page_size: int,
    db: Session
) -> RulesListResponse:
    """Shared logic for building rules response"""
    rule_repo = AssociationRuleRepository(db)

    rules, total = rule_repo.get_rules_by_run(
        run_id=run_id,
        min_lift=min_lift,
        min_confidence=min_confidence,
        product=product,
        strength=strength,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size
    )

    kpis_data = rule_repo.get_kpis(run_id)

    rules_response = [
        AssociationRuleResponse(
            id=r.id,
            antecedent=r.antecedent_label,
            consequent=r.consequent_label,
            antecedents=r.antecedents,
            consequents=r.consequents,
            support=float(r.support),
            confidence=float(r.confidence),
            lift=float(r.lift),
            conviction=float(r.conviction) if r.conviction else None,
            leverage=float(r.leverage) if r.leverage else None,
            strength=r.strength,
            antecedent_section=r.antecedent_section,
            consequent_section=r.consequent_section,
            antecedent_department=r.antecedent_department,
            consequent_department=r.consequent_department,
            llm_explanation=r.llm_explanation,
        )
        for r in rules
    ]

    return RulesListResponse(
        run_id=run_id,
        rules=rules_response,
        total=total,
        page=page,
        page_size=page_size,
        kpis=RulesKPIs(**kpis_data)
    )
