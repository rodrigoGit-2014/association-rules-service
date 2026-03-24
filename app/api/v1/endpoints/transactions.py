"""Transaction summary endpoint"""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.auth_deps import get_current_user, TokenData
from app.services.transaction_service import TransactionService
from app.schemas.transactions import TransactionSummaryResponse, TransactionBasketsResponse

router = APIRouter()


@router.get("/transactions/baskets", response_model=TransactionBasketsResponse)
def get_transaction_baskets(
    start_date: date = Query(..., description="Start date for analysis"),
    end_date: date = Query(..., description="End date for analysis"),
    department_id: Optional[str] = Query(None, description="Filter by department"),
    section_id: Optional[str] = Query(None, description="Filter by section"),
    limit: int = Query(100, ge=1, le=500, description="Max baskets to return"),
    offset: int = Query(0, ge=0, description="Number of baskets to skip"),
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """Get transaction baskets (products grouped by order) for preview"""
    service = TransactionService(db)
    return service.get_baskets(
        company_id=current_user.company_id,
        start_date=start_date,
        end_date=end_date,
        department_id=department_id,
        section_id=section_id,
        limit=limit,
        offset=offset,
    )


@router.get("/transactions/summary", response_model=TransactionSummaryResponse)
def get_transaction_summary(
    start_date: date = Query(..., description="Start date for analysis"),
    end_date: date = Query(..., description="End date for analysis"),
    department_id: Optional[str] = Query(None, description="Filter by department"),
    section_id: Optional[str] = Query(None, description="Filter by section"),
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
):
    """Get aggregated transaction summary for a date range"""
    service = TransactionService(db)
    return service.get_summary(
        company_id=current_user.company_id,
        start_date=start_date,
        end_date=end_date,
        department_id=department_id,
        section_id=section_id,
    )
