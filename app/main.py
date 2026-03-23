"""FastAPI application entry point for Apriori Market Basket Analysis v2"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
import logging

from app.core.config import settings
from app.core.logging import setup_logging
from app.core.exceptions import (
    validation_exception_handler,
    sqlalchemy_exception_handler,
    general_exception_handler,
)
from app.db.session import engine, create_tables
from app.db.matviews import create_matviews, refresh_matviews
from app.api.v1.router import api_router

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    import app.models.analysis_run  # noqa: F401
    import app.models.association_rule  # noqa: F401
    create_tables()
    create_matviews(engine)
    try:
        refresh_matviews(engine)
    except Exception as e:
        logger.warning(f"Could not refresh matviews on startup: {e}")
    yield
    logger.info(f"Shutting down {settings.APP_NAME}")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Market basket analysis microservice using the Apriori algorithm.",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/", status_code=status.HTTP_200_OK, tags=["Health"])
def root():
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "api_v1": settings.API_V1_PREFIX,
    }


@app.post("/refresh-matviews", status_code=status.HTTP_200_OK, tags=["Admin"])
def refresh_materialized_views():
    """Manually refresh materialized views after new data is loaded"""
    refresh_matviews(engine)
    return {"status": "ok", "message": "Materialized views refreshed"}


@app.get("/health", status_code=status.HTTP_200_OK, tags=["Health"])
def health_check():
    return {"status": "healthy", "service": settings.APP_NAME, "version": settings.APP_VERSION}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.PORT, reload=settings.DEBUG, log_level=settings.LOG_LEVEL.lower())
