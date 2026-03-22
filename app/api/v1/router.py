"""Main API v1 router aggregating all endpoints"""

from fastapi import APIRouter

from app.api.v1.endpoints import transactions, analysis, recommendations

api_router = APIRouter()

api_router.include_router(transactions.router, tags=["Transactions"])
api_router.include_router(analysis.router, tags=["Analysis"])
api_router.include_router(recommendations.router, tags=["Recommendations"])
