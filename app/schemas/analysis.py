"""Schemas for Apriori analysis endpoint"""

from datetime import date, datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field


class AprioriRequest(BaseModel):
    start_date: date
    end_date: date
    department_id: Optional[str] = None
    section_id: Optional[str] = None
    min_support: float = Field(0.02, ge=0.001, le=0.5)
    min_confidence: float = Field(0.6, ge=0.01, le=1.0)
    min_lift: float = Field(1.2, ge=0.5)


class AssociationRuleResponse(BaseModel):
    antecedent: list[str]
    consequent: list[str]
    support: float
    confidence: float
    lift: float


class AprioriResponse(BaseModel):
    rules: list[AssociationRuleResponse]


class AnalysisRunResponse(BaseModel):
    id: UUID
    status: str
    min_support: float
    min_confidence: float
    min_lift: float
    fecha_inicio: Optional[date] = None
    fecha_fin: Optional[date] = None
    id_departamento: Optional[str] = None
    id_seccion: Optional[str] = None
    total_transactions: Optional[int] = None
    total_products: Optional[int] = None
    rules_generated: Optional[int] = None
    execution_time_secs: Optional[float] = None
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AnalysisRunDetailResponse(BaseModel):
    run: AnalysisRunResponse
    rules: list[AssociationRuleResponse]


class AnalysisRunListResponse(BaseModel):
    runs: list[AnalysisRunResponse]
    total: int


class DeleteRunResponse(BaseModel):
    run_id: str
    rules_deleted: int
    message: str


class DeleteAllRunsResponse(BaseModel):
    runs_deleted: int
    rules_deleted: int
    message: str
