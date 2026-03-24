"""Apriori association rules service — basket building, algorithm execution, and rule storage"""

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

    def build_baskets(
        self,
        company_id: UUID,
        fecha_inicio: Optional[date] = None,
        fecha_fin: Optional[date] = None,
        id_departamento: Optional[str] = None,
        id_seccion: Optional[str] = None,
    ) -> Tuple[List[List[str]], int, int]:
        """
        Query tickets and build basket transactions.
        Returns (transactions_list, total_transactions, total_unique_products).
        """
        query = """
            SELECT id_pedido, array_agg(DISTINCT nombre_producto) AS products
            FROM tickets
            WHERE 1=1
            AND company_id = :company_id
        """
        params: Dict = {}
        params["company_id"] = company_id

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

        all_products: set = set()
        for t in transactions:
            all_products.update(t)
        total_products = len(all_products)

        logger.info(f"Built {total_transactions} baskets with {total_products} unique products")
        return transactions, total_transactions, total_products

    def run_apriori(
        self,
        transactions: List[List[str]],
        min_support: float,
        min_confidence: float,
        min_lift: float,
    ) -> pd.DataFrame:
        """Execute the Apriori algorithm and generate association rules"""
        if not transactions:
            return pd.DataFrame()

        te = TransactionEncoder()
        te_array = te.fit(transactions).transform(transactions)
        df = pd.DataFrame(te_array, columns=te.columns_)

        logger.info(f"Transaction matrix: {df.shape[0]} baskets x {df.shape[1]} products")

        frequent_itemsets = apriori(
            df,
            min_support=min_support,
            use_colnames=True,
            low_memory=True,
        )

        if frequent_itemsets.empty:
            logger.warning("No frequent itemsets found with given min_support")
            return pd.DataFrame()

        logger.info(f"Found {len(frequent_itemsets)} frequent itemsets")

        rules = association_rules(
            frequent_itemsets,
            metric="confidence",
            min_threshold=min_confidence,
        )

        if rules.empty:
            logger.warning("No rules found with given min_confidence")
            return pd.DataFrame()

        rules = rules[rules["lift"] >= min_lift]

        if rules.empty:
            logger.warning("No rules remaining after lift filter")
            return pd.DataFrame()

        rules = rules.nlargest(500, "lift")
        logger.info(f"Generated {len(rules)} association rules")
        return rules

    def store_rules(self, run_id: UUID, rules_df: pd.DataFrame) -> int:
        """Convert DataFrame rules to AssociationRule models and bulk insert"""
        if rules_df.empty:
            return 0

        rules = []
        for _, row in rules_df.iterrows():
            rule = AssociationRule(
                run_id=run_id,
                antecedents=sorted(list(row["antecedents"])),
                consequents=sorted(list(row["consequents"])),
                support=float(row["support"]),
                confidence=float(row["confidence"]),
                lift=float(row["lift"]),
            )
            rules.append(rule)

        return self.rule_repo.bulk_create(rules)

    def execute_sync(
        self,
        company_id: UUID,
        start_date: date,
        end_date: date,
        department_id: Optional[str] = None,
        section_id: Optional[str] = None,
        min_support: float = 0.02,
        min_confidence: float = 0.6,
        min_lift: float = 1.2,
    ) -> List[Dict]:
        """Execute Apriori analysis and return rules directly"""
        start_time = time.time()

        transactions, total_txns, total_prods = self.build_baskets(
            company_id=company_id,
            fecha_inicio=start_date,
            fecha_fin=end_date,
            id_departamento=department_id,
            id_seccion=section_id,
        )

        rules_df = self.run_apriori(
            transactions=transactions,
            min_support=min_support,
            min_confidence=min_confidence,
            min_lift=min_lift,
        )

        if rules_df.empty:
            return []

        rules = []
        for _, row in rules_df.iterrows():
            rules.append({
                "antecedent": sorted(list(row["antecedents"])),
                "consequent": sorted(list(row["consequents"])),
                "support": round(float(row["support"]), 6),
                "confidence": round(float(row["confidence"]), 6),
                "lift": round(float(row["lift"]), 4),
            })

        elapsed = round(time.time() - start_time, 2)

        # Persist run + rules for future recommendation queries
        run = AnalysisRun(
            company_id=company_id,
            min_support=min_support,
            min_confidence=min_confidence,
            min_lift=min_lift,
            fecha_inicio=start_date,
            fecha_fin=end_date,
            id_departamento=department_id,
            id_seccion=section_id,
            status=AnalysisStatus.COMPLETED,
            total_transactions=total_txns,
            total_products=total_prods,
            rules_generated=len(rules),
            execution_time_secs=elapsed,
        )
        run = self.run_repo.create(run)
        self.store_rules(run.id, rules_df)

        logger.info(f"Analysis completed: {len(rules)} rules from {total_txns} baskets in {elapsed}s")
        return rules
