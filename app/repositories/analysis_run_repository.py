"""Repository for AnalysisRun CRUD operations"""

from typing import Optional, List
from uuid import UUID
from sqlalchemy.orm import Session

from app.repositories.base import BaseRepository
from app.models.analysis_run import AnalysisRun, AnalysisStatus


class AnalysisRunRepository(BaseRepository[AnalysisRun]):

    def __init__(self, db: Session):
        super().__init__(AnalysisRun, db)

    def get_by_status(self, status: AnalysisStatus, limit: int = 10) -> List[AnalysisRun]:
        return (
            self.db.query(AnalysisRun)
            .filter(AnalysisRun.status == status)
            .order_by(AnalysisRun.created_at.desc())
            .limit(limit)
            .all()
        )

    def get_latest_completed(self) -> Optional[AnalysisRun]:
        return (
            self.db.query(AnalysisRun)
            .filter(AnalysisRun.status == AnalysisStatus.COMPLETED)
            .order_by(AnalysisRun.completed_at.desc())
            .first()
        )

    def get_runs(self, limit: int = 10, offset: int = 0, status: Optional[str] = None) -> List[AnalysisRun]:
        query = self.db.query(AnalysisRun)
        if status:
            query = query.filter(AnalysisRun.status == status)
        return (
            query.order_by(AnalysisRun.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    def count_runs(self, status: Optional[str] = None) -> int:
        query = self.db.query(AnalysisRun)
        if status:
            query = query.filter(AnalysisRun.status == status)
        return query.count()
