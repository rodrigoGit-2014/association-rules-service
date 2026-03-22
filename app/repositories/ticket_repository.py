"""Read-only repository for tickets table and materialized views"""

import logging
from typing import Optional, List, Dict, Any
from datetime import date

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class TicketRepository:
    """Queries tickets table and materialized views"""

    def __init__(self, db: Session):
        self.db = db

    def get_summary(
        self,
        start_date: date,
        end_date: date,
        department_id: Optional[str] = None,
        section_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Query mv_transaction_summary for aggregated metrics"""
        query = """
            SELECT
                COALESCE(SUM(total_transactions), 0) AS total_transactions,
                COALESCE(SUM(total_products), 0) AS total_products,
                CASE
                    WHEN COALESCE(SUM(total_transactions), 0) = 0 THEN 0
                    ELSE SUM(avg_products_per_purchase * total_transactions) / SUM(total_transactions)
                END AS avg_products_per_purchase
            FROM mv_transaction_summary
            WHERE fecha >= :start_date AND fecha <= :end_date
        """
        params: Dict[str, Any] = {"start_date": start_date, "end_date": end_date}

        if department_id:
            query += " AND id_departamento = :department_id"
            params["department_id"] = department_id
        if section_id:
            query += " AND id_seccion = :section_id"
            params["section_id"] = section_id

        result = self.db.execute(text(query), params).first()

        return {
            "total_transactions": int(result.total_transactions),
            "total_products": int(result.total_products),
            "avg_products_per_purchase": round(float(result.avg_products_per_purchase), 1),
        }

    def get_top_products(
        self,
        start_date: date,
        end_date: date,
        department_id: Optional[str] = None,
        section_id: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Query mv_top_products for most frequent products"""
        query = """
            SELECT
                nombre_producto AS product,
                SUM(transaction_count) AS count
            FROM mv_top_products
            WHERE fecha >= :start_date AND fecha <= :end_date
        """
        params: Dict[str, Any] = {"start_date": start_date, "end_date": end_date}

        if department_id:
            query += " AND id_departamento = :department_id"
            params["department_id"] = department_id
        if section_id:
            query += " AND id_seccion = :section_id"
            params["section_id"] = section_id

        query += " GROUP BY nombre_producto ORDER BY count DESC LIMIT :limit"
        params["limit"] = limit

        rows = self.db.execute(text(query), params).fetchall()
        return [{"product": row.product, "count": int(row.count)} for row in rows]

    def get_baskets(
        self,
        start_date: date,
        end_date: date,
        department_id: Optional[str] = None,
        section_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Get transaction baskets (grouped products per order) with total count"""

        # Count total distinct orders
        count_query = """
            SELECT COUNT(DISTINCT id_pedido) AS total
            FROM tickets
            WHERE fecha >= :start_date AND fecha <= :end_date
        """
        params: Dict[str, Any] = {"start_date": start_date, "end_date": end_date}

        if department_id:
            count_query += " AND id_departamento = :department_id"
            params["department_id"] = department_id
        if section_id:
            count_query += " AND id_seccion = :section_id"
            params["section_id"] = section_id

        total = int(self.db.execute(text(count_query), params).scalar())

        # Fetch baskets
        baskets_query = """
            SELECT id_pedido,
                   array_agg(DISTINCT nombre_producto ORDER BY nombre_producto) AS products
            FROM tickets
            WHERE fecha >= :start_date AND fecha <= :end_date
        """
        if department_id:
            baskets_query += " AND id_departamento = :department_id"
        if section_id:
            baskets_query += " AND id_seccion = :section_id"

        baskets_query += " GROUP BY id_pedido ORDER BY id_pedido LIMIT :limit OFFSET :offset"
        params["limit"] = limit
        params["offset"] = offset

        rows = self.db.execute(text(baskets_query), params).fetchall()
        baskets = [
            {"transaction_id": str(row.id_pedido), "products": list(row.products)}
            for row in rows
        ]

        return {"baskets": baskets, "total": total}

    def count_transactions(
        self,
        start_date: date,
        end_date: date,
        department_id: Optional[str] = None,
        section_id: Optional[str] = None,
    ) -> int:
        """Fast COUNT for estimating dataset size (sync/async threshold)"""
        query = """
            SELECT COUNT(DISTINCT id_pedido) AS cnt
            FROM tickets
            WHERE fecha >= :start_date AND fecha <= :end_date
        """
        params: Dict[str, Any] = {"start_date": start_date, "end_date": end_date}

        if department_id:
            query += " AND id_departamento = :department_id"
            params["department_id"] = department_id
        if section_id:
            query += " AND id_seccion = :section_id"
            params["section_id"] = section_id

        result = self.db.execute(text(query), params).first()
        return int(result.cnt)
