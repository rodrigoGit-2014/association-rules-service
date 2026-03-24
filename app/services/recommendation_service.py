"""Product recommendation service based on stored association rules"""

import logging
from typing import Optional, Dict, Any, List
from datetime import date
from uuid import UUID

from sqlalchemy.orm import Session

from app.repositories.analysis_run_repository import AnalysisRunRepository
from app.repositories.association_rule_repository import AssociationRuleRepository
from app.core.cache import cache, make_cache_key

logger = logging.getLogger(__name__)

CACHE_PREFIX = "recommendations"
CACHE_TTL = 1800  # 30 minutes


class RecommendationService:
    """Generates product recommendations from stored association rules"""

    def __init__(self, db: Session):
        self.run_repo = AnalysisRunRepository(db)
        self.rule_repo = AssociationRuleRepository(db)

    def get_recommendations(
        self,
        company_id: UUID,
        product: str,
        start_date: date,
        end_date: date,
    ) -> Dict[str, Any]:
        """Find product recommendations from the latest completed analysis"""
        cache_key = make_cache_key(
            CACHE_PREFIX,
            company_id=str(company_id),
            product=product,
            start_date=start_date,
            end_date=end_date,
        )

        cached_result = cache.get(cache_key)
        if cached_result is not None:
            logger.debug("Cache hit for recommendations")
            return cached_result

        run = self.run_repo.get_latest_completed(
            company_id=company_id,
            fecha_inicio=start_date,
            fecha_fin=end_date,
        )

        if not run:
            return {"product": product, "recommendations": []}

        rules = self.rule_repo.get_rules_for_product(
            run_id=run.id,
            product_name=product,
            limit=20,
        )

        seen: set = set()
        recommendations: List[Dict[str, Any]] = []

        for rule in rules:
            for consequent in rule.consequents:
                if consequent not in seen and consequent != product:
                    seen.add(consequent)
                    recommendations.append({
                        "product": consequent,
                        "confidence": round(float(rule.confidence), 4),
                    })

        recommendations.sort(key=lambda x: x["confidence"], reverse=True)

        result = {
            "product": product,
            "recommendations": recommendations,
        }

        cache.set(cache_key, result, CACHE_TTL)
        return result
