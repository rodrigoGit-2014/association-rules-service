"""Repository for AssociationRule queries"""

from typing import List
from uuid import UUID
from sqlalchemy.orm import Session

from app.repositories.base import BaseRepository
from app.models.association_rule import AssociationRule


class AssociationRuleRepository(BaseRepository[AssociationRule]):

    def __init__(self, db: Session):
        super().__init__(AssociationRule, db)

    def get_rules_by_run(self, run_id: UUID) -> List[AssociationRule]:
        """Get all rules for a given analysis run, sorted by lift desc"""
        return (
            self.db.query(AssociationRule)
            .filter(AssociationRule.run_id == run_id)
            .order_by(AssociationRule.lift.desc())
            .all()
        )

    def get_rules_for_product(
        self,
        run_id: UUID,
        product_name: str,
        limit: int = 20,
    ) -> List[AssociationRule]:
        """Get rules where product appears as antecedent"""
        return (
            self.db.query(AssociationRule)
            .filter(
                AssociationRule.run_id == run_id,
                AssociationRule.antecedents.any(product_name),
            )
            .order_by(AssociationRule.confidence.desc())
            .limit(limit)
            .all()
        )

    def bulk_create(self, rules: List[AssociationRule]) -> int:
        """Bulk insert rules"""
        self.db.bulk_save_objects(rules)
        self.db.commit()
        return len(rules)
