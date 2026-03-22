"""Pydantic schemas for association rules API"""

from datetime import date, datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict


# ── Request Schemas ──

class AprioriConfigRequest(BaseModel):
    min_support: float = Field(0.01, ge=0.001, le=0.5, description="Minimum support threshold")
    min_confidence: float = Field(0.20, ge=0.01, le=1.0, description="Minimum confidence threshold")
    min_lift: float = Field(1.0, ge=0.5, le=10.0, description="Minimum lift threshold")
    max_itemset_size: int = Field(3, ge=2, le=5, description="Maximum itemset size")
    max_rules: int = Field(500, ge=10, le=5000, description="Maximum number of rules to generate")
    fecha_inicio: Optional[date] = Field(None, description="Start date filter")
    fecha_fin: Optional[date] = Field(None, description="End date filter")
    id_departamento: Optional[str] = Field(None, description="Department filter")
    id_seccion: Optional[str] = Field(None, description="Section filter")


class LLMExplanationRequest(BaseModel):
    rule_ids: Optional[List[int]] = Field(None, description="Specific rule IDs to explain, or None for top N")
    top_n: int = Field(10, ge=1, le=50, description="Number of top rules to explain")


# ── Response Schemas ──

class AnalysisRunResponse(BaseModel):
    id: UUID
    status: str
    min_support: float
    min_confidence: float
    min_lift: float
    max_itemset_size: int
    max_rules: int
    fecha_inicio: Optional[date] = None
    fecha_fin: Optional[date] = None
    id_departamento: Optional[str] = None
    id_seccion: Optional[str] = None
    total_transactions: Optional[int] = None
    total_products: Optional[int] = None
    rules_generated: Optional[int] = None
    execution_time_secs: Optional[float] = None
    error_message: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class AnalysisRunCreateResponse(BaseModel):
    run_id: UUID
    status: str
    message: str
    created_at: datetime


class AssociationRuleResponse(BaseModel):
    id: int
    antecedent: str
    consequent: str
    antecedents: List[str]
    consequents: List[str]
    support: float
    confidence: float
    lift: float
    conviction: Optional[float] = None
    leverage: Optional[float] = None
    strength: str
    antecedent_section: Optional[str] = None
    consequent_section: Optional[str] = None
    antecedent_department: Optional[str] = None
    consequent_department: Optional[str] = None
    llm_explanation: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class RulesKPIs(BaseModel):
    total_rules: int
    avg_confidence: float
    avg_lift: float
    avg_support: float
    strong_count: int
    medium_count: int
    weak_count: int


class RulesListResponse(BaseModel):
    run_id: UUID
    rules: List[AssociationRuleResponse]
    total: int
    page: int
    page_size: int
    kpis: RulesKPIs


class RuleExplanation(BaseModel):
    rule_id: int
    antecedent: str
    consequent: str
    lift: float
    explanation: str


class LLMExplanationResponse(BaseModel):
    run_id: UUID
    explanations: List[RuleExplanation]


# ── Product Recommendation Schemas ──

class ProductRecommendation(BaseModel):
    product: str
    section: Optional[str] = None
    department: Optional[str] = None
    lift: float
    confidence: float
    support: float
    strength: str
    direction: str  # "consequent" or "antecedent"
    llm_explanation: Optional[str] = None


class ProductRecommendationsResponse(BaseModel):
    product: str
    product_section: Optional[str] = None
    total_associations: int
    recommendations: List[ProductRecommendation]
