"""Tests for recommendation endpoint"""

from unittest.mock import patch


class TestRecommendations:

    def test_recommendations_with_results(self, client, mock_redis):
        """Test recommendations when analysis exists"""
        mock_result = {
            "product": "Beer",
            "recommendations": [
                {"product": "Chips", "confidence": 0.62},
                {"product": "Peanuts", "confidence": 0.51},
            ],
        }

        with patch("app.api.v1.endpoints.recommendations.RecommendationService") as MockService:
            instance = MockService.return_value
            instance.get_recommendations.return_value = mock_result

            response = client.get(
                "/api/v1/recommendations",
                params={
                    "product": "Beer",
                    "start_date": "2025-01-01",
                    "end_date": "2025-03-01",
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["product"] == "Beer"
        assert len(data["recommendations"]) == 2
        assert data["recommendations"][0]["product"] == "Chips"

    def test_recommendations_empty(self, client, mock_redis):
        """Test recommendations when no analysis exists"""
        mock_result = {"product": "Unknown", "recommendations": []}

        with patch("app.api.v1.endpoints.recommendations.RecommendationService") as MockService:
            instance = MockService.return_value
            instance.get_recommendations.return_value = mock_result

            response = client.get(
                "/api/v1/recommendations",
                params={
                    "product": "Unknown",
                    "start_date": "2025-01-01",
                    "end_date": "2025-03-01",
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["recommendations"] == []

    def test_recommendations_requires_product(self, client):
        """Test that product parameter is required"""
        response = client.get(
            "/api/v1/recommendations",
            params={"start_date": "2025-01-01", "end_date": "2025-03-01"},
        )
        assert response.status_code == 422
