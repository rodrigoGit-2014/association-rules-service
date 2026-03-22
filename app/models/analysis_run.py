"""AnalysisRun model for tracking Apriori analysis executions"""

from sqlalchemy import Column, String, Integer, Text, DateTime, Numeric, Enum as SQLAlchemyEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum
from datetime import datetime
from typing import Optional

from app.db.base import Base


class AnalysisStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class AnalysisRun(Base):
    """Tracks each Apriori analysis execution with its configuration and results"""

    __tablename__ = "analysis_runs"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique analysis run identifier"
    )

    status = Column(
        SQLAlchemyEnum(AnalysisStatus, name="analysis_status", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=AnalysisStatus.PENDING,
        index=True,
        comment="Current analysis status"
    )

    # Algorithm configuration
    min_support = Column(Numeric(6, 4), nullable=False, default=0.01)
    min_confidence = Column(Numeric(6, 4), nullable=False, default=0.20)
    min_lift = Column(Numeric(6, 2), nullable=False, default=1.0)
    max_itemset_size = Column(Integer, nullable=False, default=3)
    max_rules = Column(Integer, nullable=False, default=500)

    # Input filters
    fecha_inicio = Column(DateTime(timezone=False), nullable=True)
    fecha_fin = Column(DateTime(timezone=False), nullable=True)
    id_departamento = Column(String(50), nullable=True)
    id_seccion = Column(String(50), nullable=True)

    # Execution metadata
    total_transactions = Column(Integer, nullable=True, comment="Baskets processed")
    total_products = Column(Integer, nullable=True, comment="Unique products in input")
    rules_generated = Column(Integer, nullable=True, comment="Rules generated")
    execution_time_secs = Column(Numeric(8, 2), nullable=True)

    # Error handling
    error_message = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Extensible metadata
    run_metadata = Column('metadata', JSONB, default=dict, nullable=False)

    # Relationship
    rules = relationship("AssociationRule", back_populates="run", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return (
            f"<AnalysisRun(id={self.id}, status={self.status.value}, "
            f"rules={self.rules_generated})>"
        )

    @property
    def duration_seconds(self) -> Optional[float]:
        if self.started_at:
            end_time = self.completed_at or datetime.now(self.started_at.tzinfo)
            return (end_time - self.started_at).total_seconds()
        return None

    def update_status(
        self,
        status: AnalysisStatus,
        error_message: Optional[str] = None
    ) -> None:
        self.status = status

        if status == AnalysisStatus.PROCESSING and not self.started_at:
            self.started_at = func.now()

        if status in (AnalysisStatus.COMPLETED, AnalysisStatus.FAILED):
            self.completed_at = func.now()

        if error_message:
            self.error_message = error_message
