"""AssociationRule model for storing generated association rules"""

from sqlalchemy import Column, Integer, DateTime, Numeric, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, ARRAY, TEXT
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class AssociationRule(Base):
    """Stores individual association rules linked to an analysis run"""

    __tablename__ = "association_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)

    run_id = Column(
        UUID(as_uuid=True),
        ForeignKey("analysis_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Rule components
    antecedents = Column(ARRAY(TEXT), nullable=False)
    consequents = Column(ARRAY(TEXT), nullable=False)

    # Metrics
    support = Column(Numeric(8, 6), nullable=False)
    confidence = Column(Numeric(8, 6), nullable=False)
    lift = Column(Numeric(8, 4), nullable=False, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationship
    run = relationship("AnalysisRun", back_populates="rules")

    def __repr__(self) -> str:
        return (
            f"<AssociationRule({', '.join(self.antecedents)} -> "
            f"{', '.join(self.consequents)}, lift={self.lift})>"
        )
