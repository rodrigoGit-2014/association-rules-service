"""Schemas for Apriori analysis endpoint"""

from datetime import date
from typing import Optional
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


class AprioriAsyncResponse(BaseModel):
    run_id: str
    status: str
    poll_url: str


class DeleteRunResponse(BaseModel):
    run_id: str
    rules_deleted: int
    message: str


class DeleteAllRunsResponse(BaseModel):
    runs_deleted: int
    rules_deleted: int
    message: str
