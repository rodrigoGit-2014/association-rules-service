"""Test fixtures and configuration"""

import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.api.deps import get_db


@pytest.fixture(scope="function")
def mock_db():
    """Create a mock database session"""
    db = MagicMock()
    return db


@pytest.fixture(scope="function")
def client(mock_db):
    """Create a test client with mocked database"""
    def override_get_db():
        try:
            yield mock_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def sample_transactions():
    """Sample transaction data for testing Apriori"""
    return [
        ["leche", "pan", "mantequilla"],
        ["cerveza", "papas fritas"],
        ["leche", "cereal"],
        ["pan", "mantequilla"],
        ["cerveza", "papas fritas", "salsa"],
        ["leche", "pan"],
        ["leche", "cereal", "pan"],
        ["cerveza", "papas fritas", "nueces"],
        ["leche", "mantequilla"],
        ["pan", "mantequilla", "mermelada"],
        ["cerveza", "papas fritas"],
        ["leche", "pan", "cereal"],
        ["pan", "mantequilla"],
        ["cerveza", "papas fritas", "salsa"],
        ["leche", "cereal"],
        ["leche", "pan", "mantequilla"],
        ["cerveza", "papas fritas"],
        ["pan", "mantequilla", "queso"],
        ["leche", "cereal", "pan"],
        ["cerveza", "papas fritas", "salsa"],
    ]
