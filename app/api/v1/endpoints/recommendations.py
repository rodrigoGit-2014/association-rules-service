"""Product recommendation endpoint"""

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.auth_deps import get_current_user, TokenData
from app.services.recommendation_service import RecommendationService
from app.schemas.recommendations import RecommendationResponse

router = APIRouter()


@router.get("/recommendations", response_model=RecommendationResponse)
def get_recommendations(
    product: str = Query(..., description="Product name to get recommendations for"),
    start_date: date = Query(..., description="Start date for analysis scope"),
    end_date: date = Query(..., description="End date for analysis scope"),
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """Get product recommendations based on association rules"""
    service = RecommendationService(db)
    return service.get_recommendations(
        company_id=current_user.company_id,
        product=product,
        start_date=start_date,
        end_date=end_date,
    )
