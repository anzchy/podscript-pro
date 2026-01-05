"""Tests for credits management and transcription gating."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from typing import Generator, Dict, Any, List

import jwt

# Test fixtures for credits operations


@pytest.fixture
def mock_supabase_config() -> Dict[str, str]:
    """Mock Supabase configuration values."""
    return {
        "supabase_url": "https://test-project.supabase.co",
        "supabase_anon_key": "test-anon-key",
        "supabase_service_role_key": "test-service-role-key",
        "supabase_jwt_secret": "test-jwt-secret-key-for-testing-purposes",
    }


@pytest.fixture
def mock_config(mock_supabase_config: Dict[str, str]) -> Generator[Mock, None, None]:
    """Mock the load_config function."""
    mock_app_config = Mock()
    for key, value in mock_supabase_config.items():
        setattr(mock_app_config, key, value)

    with patch("podscript_shared.config.load_config", return_value=mock_app_config):
        yield mock_app_config


@pytest.fixture
def valid_jwt_token(mock_supabase_config: Dict[str, str]) -> str:
    """Generate a valid JWT token for testing."""
    payload = {
        "sub": "test-user-id-12345",
        "email": "test@example.com",
        "aud": "authenticated",
        "exp": datetime.utcnow() + timedelta(hours=1),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(
        payload,
        mock_supabase_config["supabase_jwt_secret"],
        algorithm="HS256",
    )


@pytest.fixture
def mock_supabase_client() -> Generator[MagicMock, None, None]:
    """Mock Supabase client for database operations."""
    mock_client = MagicMock()

    # Mock table operations
    mock_table = MagicMock()
    mock_client.table.return_value = mock_table
    mock_table.select.return_value = mock_table
    mock_table.insert.return_value = mock_table
    mock_table.update.return_value = mock_table
    mock_table.eq.return_value = mock_table
    mock_table.single.return_value = mock_table
    mock_table.order.return_value = mock_table
    mock_table.range.return_value = mock_table

    # Mock RPC calls
    mock_client.rpc.return_value = mock_table

    with patch("podscript_shared.supabase.get_supabase_client", return_value=mock_client):
        with patch("podscript_shared.supabase.get_supabase_admin_client", return_value=mock_client):
            yield mock_client


@pytest.fixture
def mock_user_with_credits() -> Dict[str, Any]:
    """Mock user with 50 credits."""
    return {
        "id": "test-user-id-12345",
        "credit_balance": 50,
        "created_at": datetime.utcnow().isoformat(),
    }


@pytest.fixture
def mock_user_with_zero_credits() -> Dict[str, Any]:
    """Mock user with 0 credits."""
    return {
        "id": "test-user-id-12345",
        "credit_balance": 0,
        "created_at": datetime.utcnow().isoformat(),
    }


@pytest.fixture
def mock_transaction_history() -> List[Dict[str, Any]]:
    """Mock credit transaction history."""
    base_time = datetime.utcnow()
    return [
        {
            "id": "tx-001",
            "user_id": "test-user-id-12345",
            "type": "bonus",
            "amount": 10,
            "balance_after": 10,
            "description": "Registration bonus",
            "related_order_id": None,
            "related_task_id": None,
            "created_at": (base_time - timedelta(days=5)).isoformat(),
        },
        {
            "id": "tx-002",
            "user_id": "test-user-id-12345",
            "type": "recharge",
            "amount": 50,
            "balance_after": 60,
            "description": "+50 Credits",
            "related_order_id": "order-001",
            "related_task_id": None,
            "created_at": (base_time - timedelta(days=3)).isoformat(),
        },
        {
            "id": "tx-003",
            "user_id": "test-user-id-12345",
            "type": "consumption",
            "amount": -2,
            "balance_after": 58,
            "description": "Transcription: 2 hours",
            "related_order_id": None,
            "related_task_id": "task-001",
            "created_at": (base_time - timedelta(days=1)).isoformat(),
        },
    ]


def calculate_transcription_cost(duration_seconds: int) -> int:
    """
    Calculate credit cost for transcription.

    Cost: 1 credit per hour, rounded up, minimum 1 credit.
    """
    hours = duration_seconds / 3600
    return max(1, int(hours) + (1 if hours % 1 > 0 else 0))


# Test classes will be added in Phase 5 when implementing credits endpoints


class TestCreditCostCalculation:
    """Tests for credit cost calculation."""

    def test_one_hour_costs_one_credit(self) -> None:
        """Test that exactly one hour costs one credit."""
        assert calculate_transcription_cost(3600) == 1

    def test_partial_hour_rounds_up(self) -> None:
        """Test that partial hours round up."""
        # 1.5 hours = 2 credits
        assert calculate_transcription_cost(5400) == 2

        # 1 minute over an hour = 2 credits
        assert calculate_transcription_cost(3660) == 2

    def test_minimum_one_credit(self) -> None:
        """Test that minimum cost is 1 credit."""
        # 1 second = 1 credit
        assert calculate_transcription_cost(1) == 1

        # 30 minutes = 1 credit
        assert calculate_transcription_cost(1800) == 1

    def test_multi_hour_transcription(self) -> None:
        """Test multi-hour transcriptions."""
        # 2 hours = 2 credits
        assert calculate_transcription_cost(7200) == 2

        # 2.5 hours = 3 credits
        assert calculate_transcription_cost(9000) == 3

        # 10 hours = 10 credits
        assert calculate_transcription_cost(36000) == 10


class TestTransactionHistory:
    """Tests for transaction history fixtures."""

    def test_transaction_history_has_multiple_types(
        self, mock_transaction_history: List[Dict[str, Any]]
    ) -> None:
        """Test that mock history includes different transaction types."""
        types = {tx["type"] for tx in mock_transaction_history}
        assert "bonus" in types
        assert "recharge" in types
        assert "consumption" in types

    def test_transaction_history_chronological(
        self, mock_transaction_history: List[Dict[str, Any]]
    ) -> None:
        """Test that transactions are in chronological order."""
        dates = [tx["created_at"] for tx in mock_transaction_history]
        assert dates == sorted(dates)

    def test_balance_after_is_consistent(
        self, mock_transaction_history: List[Dict[str, Any]]
    ) -> None:
        """Test that balance_after values are consistent with amounts."""
        running_balance = 0
        for tx in mock_transaction_history:
            running_balance += tx["amount"]
            assert tx["balance_after"] == running_balance
