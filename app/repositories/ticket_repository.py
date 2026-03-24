"""Read-only repository for tickets table and materialized views"""

import logging
from typing import Optional, List, Dict, Any
from datetime import date
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class TicketRepository:
    """Queries tickets table and materialized views"""

    def __init__(self, db: Session):
        self.db = db

    def get_summary(
        self,
        company_id: UUID,
        start_date: date,
        end_date: date,
        department_id: Optional[str] = None,
        section_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Query tickets table for aggregated metrics"""
        filters = " AND id_departamento = :department_id" if department_id else ""
        filters += " AND id_seccion = :section_id" if section_id else ""

        query = f"""
            SELECT
                COUNT(DISTINCT id_pedido) AS total_transactions,
                COUNT(DISTINCT nombre_producto) AS total_products,
                CASE
                    WHEN COUNT(DISTINCT id_pedido) = 0 THEN 0
                    ELSE COUNT(id_producto)::FLOAT / COUNT(DISTINCT id_pedido)
                END AS avg_products_per_purchase
            FROM tickets
            WHERE fecha BETWEEN :start_date AND :end_date
            AND company_id = :company_id
            {filters}
        """
        params: Dict[str, Any] = {"start_date": start_date, "end_date": end_date}
        params["company_id"] = company_id

        if department_id:
            params["department_id"] = department_id
        if section_id:
            params["section_id"] = section_id

        result = self.db.execute(text(query), params).first()

        return {
            "total_transactions": int(result.total_transactions or 0),
            "total_products": int(result.total_products or 0),
            "avg_products_per_purchase": round(float(result.avg_products_per_purchase or 0), 2),
        }

    def get_top_products(
        self,
        company_id: UUID,
        start_date: date,
        end_date: date,
        department_id: Optional[str] = None,
        section_id: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Query tickets table for most frequent products"""
        query = """
            SELECT
                nombre_producto AS product,
                COUNT(DISTINCT id_pedido) AS count
            FROM tickets
            WHERE fecha >= :start_date AND fecha <= :end_date
            AND company_id = :company_id
        """
        params: Dict[str, Any] = {"start_date": start_date, "end_date": end_date}
        params["company_id"] = company_id

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
        company_id: UUID,
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
            AND company_id = :company_id
        """
        params: Dict[str, Any] = {"start_date": start_date, "end_date": end_date}
        params["company_id"] = company_id

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
            AND company_id = :company_id
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
        company_id: UUID,
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
            AND company_id = :company_id
        """
        params: Dict[str, Any] = {"start_date": start_date, "end_date": end_date}
        params["company_id"] = company_id

        if department_id:
            query += " AND id_departamento = :department_id"
            params["department_id"] = department_id
        if section_id:
            query += " AND id_seccion = :section_id"
            params["section_id"] = section_id

        result = self.db.execute(text(query), params).first()
        return int(result.cnt)
