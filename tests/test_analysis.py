"""Tests for Apriori analysis endpoint"""

from unittest.mock import patch, MagicMock


class TestAprioriAnalysis:

    def test_sync_execution_small_dataset(self, client, mock_redis):
        """Test synchronous execution for small datasets"""
        mock_rules = [
            {
                "antecedent": ["Beer"],
                "consequent": ["Chips"],
                "support": 0.12,
                "confidence": 0.62,
                "lift": 1.8,
            }
        ]

        with patch("app.api.v1.endpoints.analysis.AprioriService") as MockService:
            instance = MockService.return_value
            instance.estimate_size.return_value = 1000
            instance.execute_sync.return_value = mock_rules

            response = client.post(
                "/api/v1/analysis/apriori",
                json={
                    "start_date": "2025-01-01",
                    "end_date": "2025-02-01",
                    "min_support": 0.02,
                    "min_confidence": 0.6,
                    "min_lift": 1.2,
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert "rules" in data
        assert len(data["rules"]) == 1
        assert data["rules"][0]["antecedent"] == ["Beer"]
        assert data["rules"][0]["consequent"] == ["Chips"]

    def test_async_execution_large_dataset(self, client, mock_redis):
        """Test async dispatch for large datasets"""
        mock_run = MagicMock()
        mock_run.id = "test-uuid-123"

        with patch("app.api.v1.endpoints.analysis.AprioriService") as MockService:
            instance = MockService.return_value
            instance.estimate_size.return_value = 100000
            instance.create_run.return_value = mock_run

            with patch("app.api.v1.endpoints.analysis.run_apriori_task") as mock_task:
                mock_task.delay.return_value = None

                response = client.post(
                    "/api/v1/analysis/apriori",
                    json={
                        "start_date": "2025-01-01",
                        "end_date": "2025-06-01",
                        "min_support": 0.02,
                        "min_confidence": 0.6,
                        "min_lift": 1.2,
                    },
                )

        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "processing"
        assert "run_id" in data
        assert "poll_url" in data

    def test_request_validation(self, client):
        """Test request validation for min_support range"""
        response = client.post(
            "/api/v1/analysis/apriori",
            json={
                "start_date": "2025-01-01",
                "end_date": "2025-02-01",
                "min_support": 2.0,  # Invalid: > 0.5
            },
        )
        assert response.status_code == 422
