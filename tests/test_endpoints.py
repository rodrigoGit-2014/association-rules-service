"""Integration tests for API endpoints"""

import pytest
from unittest.mock import patch, MagicMock
from uuid import uuid4


class TestHealthEndpoints:
    """Tests for health check endpoints"""

    def test_root(self, client):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert data["api_v1"] == "/api/v1"

    def test_health(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


class TestAssociationEndpoints:
    """Tests for association rules endpoints"""

    @patch("app.api.v1.endpoints.association.AnalysisRunRepository")
    def test_list_runs_empty(self, MockRepo, client):
        MockRepo.return_value.get_runs.return_value = []
        response = client.get("/api/v1/association/runs")
        assert response.status_code == 200
        assert response.json() == []

    @patch("app.api.v1.endpoints.association.AnalysisRunRepository")
    def test_get_run_not_found(self, MockRepo, client):
        MockRepo.return_value.get.return_value = None
        response = client.get(f"/api/v1/association/runs/{uuid4()}")
        assert response.status_code == 404

    @patch("app.api.v1.endpoints.association.AnalysisRunRepository")
    def test_get_latest_rules_no_runs(self, MockRepo, client):
        MockRepo.return_value.get_latest_completed.return_value = None
        response = client.get("/api/v1/association/runs/latest/rules")
        assert response.status_code == 404

    @patch("app.api.v1.endpoints.association.AnalysisRunRepository")
    def test_delete_run_not_found(self, MockRepo, client):
        MockRepo.return_value.delete.return_value = False
        response = client.delete(f"/api/v1/association/runs/{uuid4()}")
        assert response.status_code == 404

    def test_explain_disabled(self, client):
        """LLM explanation should fail when LLM_ENABLED=false"""
        # Need to mock repo to get past run check
        with patch("app.api.v1.endpoints.association.AnalysisRunRepository") as MockRepo:
            MockRepo.return_value.get.return_value = None
            response = client.post(
                f"/api/v1/association/runs/{uuid4()}/explain",
                json={"top_n": 5}
            )
            # LLM_ENABLED is false by default, so should get 400 before run check
            assert response.status_code == 400
            assert "disabled" in response.json()["detail"].lower()


class TestProductEndpoints:
    """Tests for product recommendation endpoints"""

    @patch("app.api.v1.endpoints.products.AnalysisRunRepository")
    def test_recommendations_no_runs(self, MockRepo, client):
        MockRepo.return_value.get_latest_completed.return_value = None
        response = client.get("/api/v1/products/leche/recommendations")
        assert response.status_code == 404

    @patch("app.api.v1.endpoints.products.AnalysisRunRepository")
    def test_recommendations_invalid_run_id(self, MockRepo, client):
        MockRepo.return_value.get.return_value = None
        response = client.get(
            f"/api/v1/products/leche/recommendations?run_id={uuid4()}"
        )
        assert response.status_code == 404


class TestValidation:
    """Tests for request validation"""

    def test_analyze_invalid_support(self, client):
        response = client.post(
            "/api/v1/association/analyze",
            json={"min_support": 2.0}
        )
        assert response.status_code == 422

    def test_analyze_invalid_confidence(self, client):
        response = client.post(
            "/api/v1/association/analyze",
            json={"min_confidence": 1.5}
        )
        assert response.status_code == 422

    def test_analyze_date_order(self, client):
        with patch("app.api.v1.endpoints.association.AprioriService"):
            response = client.post(
                "/api/v1/association/analyze",
                json={
                    "fecha_inicio": "2024-12-31",
                    "fecha_fin": "2024-01-01"
                }
            )
            assert response.status_code == 400
