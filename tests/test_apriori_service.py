"""Unit tests for AprioriService"""

import pytest
import pandas as pd
from unittest.mock import MagicMock, patch
from uuid import uuid4

from app.services.apriori_service import AprioriService
from app.models.association_rule import AssociationRule


class TestAprioriAlgorithm:
    """Tests for the core Apriori algorithm execution"""

    def test_run_apriori_generates_rules(self, sample_transactions):
        """Apriori should generate association rules from transactions"""
        db = MagicMock()
        service = AprioriService(db)

        rules_df = service.run_apriori(
            transactions=sample_transactions,
            min_support=0.1,
            min_confidence=0.3,
            min_lift=1.0,
            max_itemset_size=3,
            max_rules=100
        )

        assert not rules_df.empty
        assert "antecedents" in rules_df.columns
        assert "consequents" in rules_df.columns
        assert "support" in rules_df.columns
        assert "confidence" in rules_df.columns
        assert "lift" in rules_df.columns

    def test_run_apriori_respects_min_support(self, sample_transactions):
        """Higher min_support should produce fewer or equal rules"""
        db = MagicMock()
        service = AprioriService(db)

        rules_low = service.run_apriori(
            transactions=sample_transactions,
            min_support=0.05,
            min_confidence=0.1,
            min_lift=1.0,
            max_itemset_size=3,
            max_rules=1000
        )

        rules_high = service.run_apriori(
            transactions=sample_transactions,
            min_support=0.3,
            min_confidence=0.1,
            min_lift=1.0,
            max_itemset_size=3,
            max_rules=1000
        )

        assert len(rules_high) <= len(rules_low)

    def test_run_apriori_respects_max_rules(self, sample_transactions):
        """Output should not exceed max_rules"""
        db = MagicMock()
        service = AprioriService(db)

        max_rules = 5
        rules_df = service.run_apriori(
            transactions=sample_transactions,
            min_support=0.05,
            min_confidence=0.1,
            min_lift=1.0,
            max_itemset_size=3,
            max_rules=max_rules
        )

        assert len(rules_df) <= max_rules

    def test_run_apriori_lift_filter(self, sample_transactions):
        """All returned rules should have lift >= min_lift"""
        db = MagicMock()
        service = AprioriService(db)

        min_lift = 1.5
        rules_df = service.run_apriori(
            transactions=sample_transactions,
            min_support=0.05,
            min_confidence=0.1,
            min_lift=min_lift,
            max_itemset_size=3,
            max_rules=100
        )

        if not rules_df.empty:
            assert all(rules_df["lift"] >= min_lift)

    def test_run_apriori_empty_transactions(self):
        """Empty transactions should return empty DataFrame"""
        db = MagicMock()
        service = AprioriService(db)

        rules_df = service.run_apriori(
            transactions=[],
            min_support=0.1,
            min_confidence=0.3,
            min_lift=1.0,
            max_itemset_size=3,
            max_rules=100
        )

        assert rules_df.empty

    def test_known_association(self, sample_transactions):
        """Cerveza → papas fritas should appear as a strong rule"""
        db = MagicMock()
        service = AprioriService(db)

        rules_df = service.run_apriori(
            transactions=sample_transactions,
            min_support=0.05,
            min_confidence=0.1,
            min_lift=1.0,
            max_itemset_size=2,
            max_rules=100
        )

        # Check if cerveza→papas fritas exists
        found = False
        for _, row in rules_df.iterrows():
            if "cerveza" in row["antecedents"] and "papas fritas" in row["consequents"]:
                found = True
                assert row["lift"] > 1.0
                break

        assert found, "Expected cerveza → papas fritas rule not found"


class TestStrengthClassification:
    """Tests for rule strength classification"""

    def test_strong(self):
        assert AssociationRule.classify_strength(3.0) == "strong"
        assert AssociationRule.classify_strength(2.5) == "strong"

    def test_medium(self):
        assert AssociationRule.classify_strength(2.0) == "medium"
        assert AssociationRule.classify_strength(1.5) == "medium"

    def test_weak(self):
        assert AssociationRule.classify_strength(1.2) == "weak"
        assert AssociationRule.classify_strength(1.0) == "weak"
