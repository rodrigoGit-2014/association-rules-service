"""Apriori association rules service - basket building and algorithm execution"""

import logging
import time
from typing import List, Dict, Optional, Tuple
from uuid import UUID
from datetime import date

import pandas as pd
from mlxtend.frequent_patterns import apriori, association_rules
from mlxtend.preprocessing import TransactionEncoder
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.analysis_run import AnalysisRun, AnalysisStatus
from app.models.association_rule import AssociationRule
from app.repositories.analysis_run_repository import AnalysisRunRepository
from app.repositories.association_rule_repository import AssociationRuleRepository

logger = logging.getLogger(__name__)


class AprioriService:
    """Orchestrates basket building, Apriori execution, and rule storage"""

    def __init__(self, db: Session):
        self.db = db
        self.run_repo = AnalysisRunRepository(db)
        self.rule_repo = AssociationRuleRepository(db)

    def create_run(
        self,
        min_support: float = 0.01,
        min_confidence: float = 0.20,
        min_lift: float = 1.0,
        max_itemset_size: int = 3,
        max_rules: int = 500,
        fecha_inicio: Optional[date] = None,
        fecha_fin: Optional[date] = None,
        id_departamento: Optional[str] = None,
        id_seccion: Optional[str] = None
    ) -> AnalysisRun:
        """Create a new analysis run record"""
        run = AnalysisRun(
            min_support=min_support,
            min_confidence=min_confidence,
            min_lift=min_lift,
            max_itemset_size=max_itemset_size,
            max_rules=max_rules,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            id_departamento=id_departamento,
            id_seccion=id_seccion,
            status=AnalysisStatus.PENDING
        )
        return self.run_repo.create(run)

    def build_baskets(
        self,
        fecha_inicio: Optional[date] = None,
        fecha_fin: Optional[date] = None,
        id_departamento: Optional[str] = None,
        id_seccion: Optional[str] = None
    ) -> Tuple[List[List[str]], int, int]:
        """
        Query tickets and build basket transactions.

        Returns:
            Tuple of (transactions_list, total_transactions, total_products)
        """
        query = """
            SELECT id_pedido, array_agg(DISTINCT nombre_producto) AS products
            FROM tickets
            WHERE 1=1
        """
        params = {}

        if fecha_inicio:
            query += " AND fecha >= :fecha_inicio"
            params["fecha_inicio"] = fecha_inicio
        if fecha_fin:
            query += " AND fecha <= :fecha_fin"
            params["fecha_fin"] = fecha_fin
        if id_departamento:
            query += " AND id_departamento = :id_departamento"
            params["id_departamento"] = id_departamento
        if id_seccion:
            query += " AND id_seccion = :id_seccion"
            params["id_seccion"] = id_seccion

        query += " GROUP BY id_pedido HAVING COUNT(DISTINCT nombre_producto) >= 2"

        result = self.db.execute(text(query), params).fetchall()

        transactions = [list(row.products) for row in result]
        total_transactions = len(transactions)

        all_products = set()
        for t in transactions:
            all_products.update(t)
        total_products = len(all_products)

        logger.info(
            f"Built {total_transactions} baskets with {total_products} unique products"
        )

        return transactions, total_transactions, total_products

    def run_apriori(
        self,
        transactions: List[List[str]],
        min_support: float,
        min_confidence: float,
        min_lift: float,
        max_itemset_size: int,
        max_rules: int
    ) -> pd.DataFrame:
        """
        Execute the Apriori algorithm and generate association rules.

        Returns:
            DataFrame with association rules and metrics
        """
        if not transactions:
            return pd.DataFrame()

        # Encode transactions to one-hot format
        te = TransactionEncoder()
        te_array = te.fit(transactions).transform(transactions)
        df = pd.DataFrame(te_array, columns=te.columns_)

        logger.info(f"Transaction matrix: {df.shape[0]} baskets x {df.shape[1]} products")

        # Find frequent itemsets
        frequent_itemsets = apriori(
            df,
            min_support=min_support,
            max_len=max_itemset_size,
            use_colnames=True
        )

        if frequent_itemsets.empty:
            logger.warning("No frequent itemsets found with given min_support")
            return pd.DataFrame()

        logger.info(f"Found {len(frequent_itemsets)} frequent itemsets")

        # Generate association rules
        rules = association_rules(
            frequent_itemsets,
            metric="confidence",
            min_threshold=min_confidence
        )

        if rules.empty:
            logger.warning("No rules found with given min_confidence")
            return pd.DataFrame()

        # Filter by min_lift
        rules = rules[rules["lift"] >= min_lift]

        if rules.empty:
            logger.warning("No rules remaining after lift filter")
            return pd.DataFrame()

        # Limit to max_rules, sorted by lift
        rules = rules.nlargest(max_rules, "lift")

        logger.info(f"Generated {len(rules)} association rules")

        return rules

    def resolve_product_metadata(self, product_name: str) -> Dict[str, Optional[str]]:
        """Look up section and department for a product from the tickets table"""
        result = self.db.execute(
            text("""
                SELECT DISTINCT id_seccion, id_departamento
                FROM tickets
                WHERE nombre_producto = :nombre
                LIMIT 1
            """),
            {"nombre": product_name}
        ).first()

        if result:
            return {
                "section": str(result.id_seccion),
                "department": str(result.id_departamento)
            }
        return {"section": None, "department": None}

    def store_rules(self, run_id: UUID, rules_df: pd.DataFrame) -> int:
        """Convert DataFrame rules to AssociationRule models and bulk insert"""
        if rules_df.empty:
            return 0

        # Build a product metadata cache to avoid repeated queries
        all_products = set()
        for _, row in rules_df.iterrows():
            all_products.update(row["antecedents"])
            all_products.update(row["consequents"])

        metadata_cache = {}
        for product in all_products:
            metadata_cache[product] = self.resolve_product_metadata(product)

        rules = []
        for _, row in rules_df.iterrows():
            antecedents = sorted(list(row["antecedents"]))
            consequents = sorted(list(row["consequents"]))

            # Use first item's metadata for display
            ant_meta = metadata_cache.get(antecedents[0], {})
            con_meta = metadata_cache.get(consequents[0], {})

            lift_val = float(row["lift"])

            rule = AssociationRule(
                run_id=run_id,
                antecedents=antecedents,
                consequents=consequents,
                antecedent_label=", ".join(antecedents),
                consequent_label=", ".join(consequents),
                support=float(row["support"]),
                confidence=float(row["confidence"]),
                lift=lift_val,
                conviction=float(row["conviction"]) if pd.notna(row.get("conviction")) and row.get("conviction") != float("inf") else None,
                leverage=float(row["leverage"]) if pd.notna(row.get("leverage")) else None,
                antecedent_section=ant_meta.get("section"),
                consequent_section=con_meta.get("section"),
                antecedent_department=ant_meta.get("department"),
                consequent_department=con_meta.get("department"),
                strength=AssociationRule.classify_strength(lift_val),
            )
            rules.append(rule)

        return self.rule_repo.bulk_create(rules)

    def execute_analysis(self, run_id: UUID) -> Dict:
        """
        Full analysis pipeline: build baskets → run apriori → store rules.
        Called by the Celery task.
        """
        run = self.run_repo.get(run_id)
        if not run:
            raise ValueError(f"Analysis run {run_id} not found")

        # Mark as processing
        run.update_status(AnalysisStatus.PROCESSING)
        self.db.commit()

        start_time = time.time()

        try:
            # Build baskets
            transactions, total_transactions, total_products = self.build_baskets(
                fecha_inicio=run.fecha_inicio,
                fecha_fin=run.fecha_fin,
                id_departamento=run.id_departamento,
                id_seccion=run.id_seccion
            )

            if not transactions:
                run.update_status(AnalysisStatus.FAILED, error_message="No transactions found with given filters")
                run.total_transactions = 0
                run.total_products = 0
                run.rules_generated = 0
                self.db.commit()
                return {"status": "failed", "error": "No transactions found"}

            # Run Apriori
            rules_df = self.run_apriori(
                transactions=transactions,
                min_support=float(run.min_support),
                min_confidence=float(run.min_confidence),
                min_lift=float(run.min_lift),
                max_itemset_size=run.max_itemset_size,
                max_rules=run.max_rules
            )

            # Store rules
            rules_count = self.store_rules(run_id, rules_df)

            elapsed = round(time.time() - start_time, 2)

            # Update run with results
            run.total_transactions = total_transactions
            run.total_products = total_products
            run.rules_generated = rules_count
            run.execution_time_secs = elapsed
            run.update_status(AnalysisStatus.COMPLETED)
            self.db.commit()

            logger.info(
                f"Analysis {run_id} completed: {rules_count} rules "
                f"from {total_transactions} baskets in {elapsed}s"
            )

            return {
                "status": "completed",
                "run_id": str(run_id),
                "rules_generated": rules_count,
                "total_transactions": total_transactions,
                "total_products": total_products,
                "execution_time": elapsed
            }

        except Exception as e:
            elapsed = round(time.time() - start_time, 2)
            run.execution_time_secs = elapsed
            run.update_status(AnalysisStatus.FAILED, error_message=str(e))
            self.db.commit()
            logger.error(f"Analysis {run_id} failed: {e}", exc_info=True)
            raise
