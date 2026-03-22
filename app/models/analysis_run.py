"""AnalysisRun model for tracking Apriori analysis executions"""

from sqlalchemy import Column, String, Integer, Text, DateTime, Numeric, Enum as SQLAlchemyEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum
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

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    status = Column(
        SQLAlchemyEnum(AnalysisStatus, name="analysis_status", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=AnalysisStatus.PENDING,
        index=True,
    )

    # Algorithm configuration
    min_support = Column(Numeric(6, 4), nullable=False, default=0.01)
    min_confidence = Column(Numeric(6, 4), nullable=False, default=0.20)
    min_lift = Column(Numeric(6, 2), nullable=False, default=1.0)

    # Input filters
    fecha_inicio = Column(DateTime(timezone=False), nullable=True)
    fecha_fin = Column(DateTime(timezone=False), nullable=True)
    id_departamento = Column(String(50), nullable=True)
    id_seccion = Column(String(50), nullable=True)

    # Execution metadata
    total_transactions = Column(Integer, nullable=True)
    total_products = Column(Integer, nullable=True)
    rules_generated = Column(Integer, nullable=True)
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
        return f"<AnalysisRun(id={self.id}, status={self.status.value}, rules={self.rules_generated})>"

    def update_status(self, status: AnalysisStatus, error_message: Optional[str] = None) -> None:
        self.status = status

        if status == AnalysisStatus.PROCESSING and not self.started_at:
            self.started_at = func.now()

        if status in (AnalysisStatus.COMPLETED, AnalysisStatus.FAILED):
            self.completed_at = func.now()

        if error_message:
            self.error_message = error_message
