"""Schemas for product recommendation endpoint"""

from pydantic import BaseModel


class ProductRecommendation(BaseModel):
    product: str
    confidence: float


class RecommendationResponse(BaseModel):
    product: str
    recommendations: list[ProductRecommendation]
