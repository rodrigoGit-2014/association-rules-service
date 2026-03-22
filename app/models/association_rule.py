"""AssociationRule model for storing generated association rules"""

from sqlalchemy import Column, String, Text, DateTime, Numeric, Integer, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, ARRAY
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
        index=True
    )

    # Rule components
    antecedents = Column(ARRAY(Text), nullable=False)
    consequents = Column(ARRAY(Text), nullable=False)
    antecedent_label = Column(Text, nullable=False)
    consequent_label = Column(Text, nullable=False)

    # Metrics
    support = Column(Numeric(8, 6), nullable=False)
    confidence = Column(Numeric(8, 6), nullable=False)
    lift = Column(Numeric(8, 4), nullable=False, index=True)
    conviction = Column(Numeric(10, 4), nullable=True)
    leverage = Column(Numeric(10, 6), nullable=True)

    # Category info
    antecedent_section = Column(String(50), nullable=True)
    consequent_section = Column(String(50), nullable=True)
    antecedent_department = Column(String(50), nullable=True)
    consequent_department = Column(String(50), nullable=True)

    # Strength classification
    strength = Column(
        String(10),
        nullable=False,
        default="weak",
        index=True
    )

    # LLM interpretation cache
    llm_explanation = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationship
    run = relationship("AnalysisRun", back_populates="rules")

    __table_args__ = (
        CheckConstraint("strength IN ('strong', 'medium', 'weak')", name="ck_strength_values"),
    )

    def __repr__(self) -> str:
        return (
            f"<AssociationRule({self.antecedent_label} -> {self.consequent_label}, "
            f"lift={self.lift}, strength={self.strength})>"
        )

    @staticmethod
    def classify_strength(lift: float) -> str:
        if lift >= 2.5:
            return "strong"
        elif lift >= 1.5:
            return "medium"
        else:
            return "weak"
