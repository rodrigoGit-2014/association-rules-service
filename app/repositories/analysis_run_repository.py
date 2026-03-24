"""Repository for AnalysisRun CRUD operations"""

from typing import Optional
from datetime import date
from uuid import UUID
from sqlalchemy.orm import Session

from app.repositories.base import BaseRepository
from app.models.analysis_run import AnalysisRun, AnalysisStatus


class AnalysisRunRepository(BaseRepository[AnalysisRun]):

    def __init__(self, db: Session):
        super().__init__(AnalysisRun, db)

    def get_latest_completed(
        self,
        company_id: UUID,
        fecha_inicio: Optional[date] = None,
        fecha_fin: Optional[date] = None,
    ) -> Optional[AnalysisRun]:
        """Get the most recent completed run, optionally overlapping a date range"""
        query = (
            self.db.query(AnalysisRun)
            .filter(AnalysisRun.status == AnalysisStatus.COMPLETED)
            .filter(AnalysisRun.company_id == company_id)
        )
        if fecha_inicio:
            query = query.filter(AnalysisRun.fecha_inicio <= fecha_fin)
        if fecha_fin:
            query = query.filter(AnalysisRun.fecha_fin >= fecha_inicio)

        return query.order_by(AnalysisRun.completed_at.desc()).first()
