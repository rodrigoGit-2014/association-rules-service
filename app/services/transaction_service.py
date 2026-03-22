"""Transaction summary service using materialized views"""

import logging
from typing import Optional, Dict, Any
from datetime import date

from sqlalchemy.orm import Session

from app.repositories.ticket_repository import TicketRepository
from app.core.cache import cache, make_cache_key

logger = logging.getLogger(__name__)

CACHE_PREFIX = "txn_summary"
CACHE_TTL = 900  # 15 minutes


class TransactionService:
    """Provides transaction summary data from materialized views"""

    def __init__(self, db: Session):
        self.ticket_repo = TicketRepository(db)

    def get_baskets(
        self,
        start_date: date,
        end_date: date,
        department_id: Optional[str] = None,
        section_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Get transaction baskets with caching"""
        cache_key = make_cache_key(
            "txn_baskets",
            start_date=start_date,
            end_date=end_date,
            department_id=department_id,
            section_id=section_id,
            limit=limit,
            offset=offset,
        )

        cached_result = cache.get(cache_key)
        if cached_result is not None:
            logger.debug("Cache hit for transaction baskets")
            return cached_result

        result = self.ticket_repo.get_baskets(
            start_date=start_date,
            end_date=end_date,
            department_id=department_id,
            section_id=section_id,
            limit=limit,
            offset=offset,
        )

        cache.set(cache_key, result, CACHE_TTL)
        return result

    def get_summary(
        self,
        start_date: date,
        end_date: date,
        department_id: Optional[str] = None,
        section_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get transaction summary with caching"""
        cache_key = make_cache_key(
            CACHE_PREFIX,
            start_date=start_date,
            end_date=end_date,
            department_id=department_id,
            section_id=section_id,
        )

        cached_result = cache.get(cache_key)
        if cached_result is not None:
            logger.debug("Cache hit for transaction summary")
            return cached_result

        summary = self.ticket_repo.get_summary(
            start_date=start_date,
            end_date=end_date,
            department_id=department_id,
            section_id=section_id,
        )

        top_products = self.ticket_repo.get_top_products(
            start_date=start_date,
            end_date=end_date,
            department_id=department_id,
            section_id=section_id,
            limit=10,
        )

        result = {
            **summary,
            "top_products": top_products,
        }

        cache.set(cache_key, result, CACHE_TTL)
        return result
