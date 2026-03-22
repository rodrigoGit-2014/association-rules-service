"""Product recommendation endpoints"""

from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.repositories.analysis_run_repository import AnalysisRunRepository
from app.repositories.association_rule_repository import AssociationRuleRepository
from app.models.analysis_run import AnalysisStatus
from app.schemas.association import (
    ProductRecommendation,
    ProductRecommendationsResponse,
)

router = APIRouter()


@router.get(
    "/products/{product_name}/recommendations",
    response_model=ProductRecommendationsResponse,
    summary="Get product recommendations",
    description="Get all products associated with a given product, suitable for radial and card views"
)
def get_product_recommendations(
    product_name: str,
    run_id: Optional[UUID] = Query(None, description="Analysis run ID. If omitted, uses latest completed run"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    run_repo = AnalysisRunRepository(db)

    # Resolve run
    if run_id:
        run = run_repo.get(run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Analysis run not found")
    else:
        run = run_repo.get_latest_completed()
        if not run:
            raise HTTPException(status_code=404, detail="No completed analysis runs found")

    if run.status != AnalysisStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Analysis run is not completed")

    rule_repo = AssociationRuleRepository(db)
    rules = rule_repo.get_rules_for_product(run.id, product_name, limit=limit * 2)

    if not rules:
        raise HTTPException(
            status_code=404,
            detail=f"No associations found for product '{product_name}'"
        )

    # Aggregate recommendations: extract the "other" product from each rule
    seen_products = set()
    recommendations = []
    product_section = None

    for rule in rules:
        if product_name in rule.antecedents:
            # Product is antecedent → consequent is the recommendation
            other_products = [p for p in rule.consequents if p != product_name]
            direction = "consequent"
            other_section = rule.consequent_section
            other_department = rule.consequent_department
            # Track the source product's section
            if not product_section:
                product_section = rule.antecedent_section
        elif product_name in rule.consequents:
            # Product is consequent → antecedent is the recommendation
            other_products = [p for p in rule.antecedents if p != product_name]
            direction = "antecedent"
            other_section = rule.antecedent_section
            other_department = rule.antecedent_department
            if not product_section:
                product_section = rule.consequent_section
        else:
            continue

        for other in other_products:
            if other in seen_products:
                continue
            seen_products.add(other)

            recommendations.append(ProductRecommendation(
                product=other,
                section=other_section,
                department=other_department,
                lift=float(rule.lift),
                confidence=float(rule.confidence),
                support=float(rule.support),
                strength=rule.strength,
                direction=direction,
                llm_explanation=rule.llm_explanation,
            ))

        if len(recommendations) >= limit:
            break

    # Sort by lift descending
    recommendations.sort(key=lambda r: r.lift, reverse=True)
    recommendations = recommendations[:limit]

    return ProductRecommendationsResponse(
        product=product_name,
        product_section=product_section,
        total_associations=len(recommendations),
        recommendations=recommendations
    )
