"""Repository for AssociationRule queries"""

from typing import Optional, List, Tuple
from uuid import UUID
from sqlalchemy import func, or_, any_
from sqlalchemy.orm import Session

from app.repositories.base import BaseRepository
from app.models.association_rule import AssociationRule


class AssociationRuleRepository(BaseRepository[AssociationRule]):

    def __init__(self, db: Session):
        super().__init__(AssociationRule, db)

    def get_rules_by_run(
        self,
        run_id: UUID,
        min_lift: Optional[float] = None,
        min_confidence: Optional[float] = None,
        product: Optional[str] = None,
        strength: Optional[str] = None,
        sort_by: str = "lift",
        sort_order: str = "desc",
        page: int = 1,
        page_size: int = 100
    ) -> Tuple[List[AssociationRule], int]:
        """Get rules for a run with filtering, sorting, and pagination"""

        query = self.db.query(AssociationRule).filter(AssociationRule.run_id == run_id)

        # Apply filters
        if min_lift is not None:
            query = query.filter(AssociationRule.lift >= min_lift)
        if min_confidence is not None:
            query = query.filter(AssociationRule.confidence >= min_confidence)
        if strength:
            query = query.filter(AssociationRule.strength == strength)
        if product:
            query = query.filter(
                or_(
                    AssociationRule.antecedents.any(product),
                    AssociationRule.consequents.any(product)
                )
            )

        # Count before pagination
        total = query.count()

        # Sorting
        sort_column = getattr(AssociationRule, sort_by, AssociationRule.lift)
        if sort_order == "asc":
            query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(sort_column.desc())

        # Pagination
        offset = (page - 1) * page_size
        rules = query.offset(offset).limit(page_size).all()

        return rules, total

    def get_rules_for_product(
        self,
        run_id: UUID,
        product_name: str,
        limit: int = 20
    ) -> List[AssociationRule]:
        """Get all rules where a product appears as antecedent or consequent"""
        return (
            self.db.query(AssociationRule)
            .filter(
                AssociationRule.run_id == run_id,
                or_(
                    AssociationRule.antecedents.any(product_name),
                    AssociationRule.consequents.any(product_name)
                )
            )
            .order_by(AssociationRule.lift.desc())
            .limit(limit)
            .all()
        )

    def get_kpis(self, run_id: UUID) -> dict:
        """Calculate KPI metrics for a run"""
        result = (
            self.db.query(
                func.count(AssociationRule.id).label("total_rules"),
                func.avg(AssociationRule.confidence).label("avg_confidence"),
                func.avg(AssociationRule.lift).label("avg_lift"),
                func.avg(AssociationRule.support).label("avg_support"),
            )
            .filter(AssociationRule.run_id == run_id)
            .first()
        )

        strength_counts = (
            self.db.query(
                AssociationRule.strength,
                func.count(AssociationRule.id)
            )
            .filter(AssociationRule.run_id == run_id)
            .group_by(AssociationRule.strength)
            .all()
        )

        strength_map = {s: c for s, c in strength_counts}

        return {
            "total_rules": result.total_rules or 0,
            "avg_confidence": float(result.avg_confidence or 0),
            "avg_lift": float(result.avg_lift or 0),
            "avg_support": float(result.avg_support or 0),
            "strong_count": strength_map.get("strong", 0),
            "medium_count": strength_map.get("medium", 0),
            "weak_count": strength_map.get("weak", 0),
        }

    def bulk_create(self, rules: List[AssociationRule]) -> int:
        """Bulk insert rules"""
        self.db.bulk_save_objects(rules)
        self.db.commit()
        return len(rules)

    def get_top_rules(self, run_id: UUID, limit: int = 20) -> List[AssociationRule]:
        """Get top rules by lift for a run"""
        return (
            self.db.query(AssociationRule)
            .filter(AssociationRule.run_id == run_id)
            .order_by(AssociationRule.lift.desc())
            .limit(limit)
            .all()
        )

    def get_rules_by_ids(self, rule_ids: List[int]) -> List[AssociationRule]:
        """Get rules by their IDs"""
        return (
            self.db.query(AssociationRule)
            .filter(AssociationRule.id.in_(rule_ids))
            .all()
        )

    def update_explanations(self, explanations: dict) -> None:
        """Batch update LLM explanations: {rule_id: explanation_text}"""
        for rule_id, explanation in explanations.items():
            self.db.query(AssociationRule).filter(
                AssociationRule.id == rule_id
            ).update({"llm_explanation": explanation})
        self.db.commit()
