"""Main API v1 router aggregating all endpoints"""

from fastapi import APIRouter

from app.api.v1.endpoints import association, products

api_router = APIRouter()

api_router.include_router(
    association.router,
    tags=["Association"]
)

api_router.include_router(
    products.router,
    tags=["Products"]
)
