"""Materialized view management for pre-aggregated transaction data"""

import logging
from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

MV_TRANSACTION_SUMMARY = """
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_transaction_summary AS
SELECT
    fecha,
    id_departamento,
    id_seccion,
    COUNT(DISTINCT id_pedido) AS total_transactions,
    COUNT(DISTINCT id_producto) AS total_products,
    COUNT(id_producto)::FLOAT / NULLIF(COUNT(DISTINCT id_pedido), 0) AS avg_products_per_purchase
FROM tickets
GROUP BY fecha, id_departamento, id_seccion
WITH DATA
"""

MV_TRANSACTION_SUMMARY_INDEX = """
CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_txn_summary
    ON mv_transaction_summary (fecha, id_departamento, id_seccion)
"""

MV_TOP_PRODUCTS = """
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_top_products AS
SELECT
    fecha,
    id_departamento,
    id_seccion,
    nombre_producto,
    COUNT(DISTINCT id_pedido) AS transaction_count
FROM tickets
GROUP BY fecha, id_departamento, id_seccion, nombre_producto
WITH DATA
"""

MV_TOP_PRODUCTS_INDEX = """
CREATE INDEX IF NOT EXISTS idx_mv_top_products
    ON mv_top_products (fecha, id_departamento, id_seccion)
"""


def create_matviews(engine: Engine) -> None:
    """Create materialized views if they don't exist (idempotent)"""
    with engine.connect() as conn:
        try:
            conn.execute(text(MV_TRANSACTION_SUMMARY))
            conn.execute(text(MV_TRANSACTION_SUMMARY_INDEX))
            conn.execute(text(MV_TOP_PRODUCTS))
            conn.execute(text(MV_TOP_PRODUCTS_INDEX))
            conn.commit()
            logger.info("Materialized views created/verified successfully")
        except Exception as e:
            conn.rollback()
            logger.warning(f"Could not create materialized views: {e}")


def refresh_matviews(engine: Engine) -> None:
    """Refresh materialized views concurrently (requires unique index)"""
    with engine.connect() as conn:
        try:
            conn.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY mv_transaction_summary"))
            conn.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY mv_top_products"))
            conn.commit()
            logger.info("Materialized views refreshed successfully")
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to refresh materialized views: {e}")
            raise
