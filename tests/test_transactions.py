"""Tests for transaction summary endpoint"""

from unittest.mock import patch, MagicMock


class TestTransactionSummary:

    def test_summary_returns_correct_shape(self, client, mock_redis):
        """Test that the response has the expected fields"""
        mock_summary = {
            "total_transactions": 100,
            "total_products": 50,
            "avg_products_per_purchase": 3.2,
        }
        mock_top = [
            {"product": "Bread", "count": 80},
            {"product": "Milk", "count": 60},
        ]

        with patch("app.services.transaction_service.TicketRepository") as MockRepo:
            instance = MockRepo.return_value
            instance.get_summary.return_value = mock_summary
            instance.get_top_products.return_value = mock_top

            response = client.get(
                "/api/v1/transactions/summary",
                params={"start_date": "2025-01-01", "end_date": "2025-03-01"},
            )

        assert response.status_code == 200
        data = response.json()
        assert "total_transactions" in data
        assert "total_products" in data
        assert "avg_products_per_purchase" in data
        assert "top_products" in data
        assert isinstance(data["top_products"], list)

    def test_summary_requires_dates(self, client):
        """Test that start_date and end_date are required"""
        response = client.get("/api/v1/transactions/summary")
        assert response.status_code == 422

    def test_summary_with_optional_filters(self, client, mock_redis):
        """Test that optional filters are accepted"""
        mock_summary = {
            "total_transactions": 50,
            "total_products": 20,
            "avg_products_per_purchase": 2.5,
        }

        with patch("app.services.transaction_service.TicketRepository") as MockRepo:
            instance = MockRepo.return_value
            instance.get_summary.return_value = mock_summary
            instance.get_top_products.return_value = []

            response = client.get(
                "/api/v1/transactions/summary",
                params={
                    "start_date": "2025-01-01",
                    "end_date": "2025-03-01",
                    "department_id": "D001",
                    "section_id": "S001",
                },
            )

        assert response.status_code == 200
