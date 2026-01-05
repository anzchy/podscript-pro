"""Tests for payment endpoints and Z-Pay integration."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from typing import Generator, Dict, Any
import hashlib

import jwt

# Test fixtures for mocking Z-Pay and Supabase


@pytest.fixture
def mock_zpay_config() -> Dict[str, str]:
    """Mock Z-Pay configuration values."""
    return {
        "zpay_pid": "test-merchant-id",
        "zpay_key": "test-secret-key",
        "zpay_notify_url": "https://example.com/api/payment/webhook",
        "zpay_return_url": "https://example.com/static/payment-success.html",
    }


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
def mock_config(
    mock_zpay_config: Dict[str, str],
    mock_supabase_config: Dict[str, str],
) -> Generator[Mock, None, None]:
    """Mock the load_config function."""
    mock_app_config = Mock()
    for key, value in {**mock_zpay_config, **mock_supabase_config}.items():
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

    with patch("podscript_shared.supabase.get_supabase_client", return_value=mock_client):
        with patch("podscript_shared.supabase.get_supabase_admin_client", return_value=mock_client):
            yield mock_client


@pytest.fixture
def mock_payment_order() -> Dict[str, Any]:
    """Mock payment order data."""
    return {
        "id": "order-uuid-12345",
        "user_id": "test-user-id-12345",
        "out_trade_no": "PDS1704326400123456",
        "amount": 50,
        "credits": 50,
        "status": "pending",
        "payment_method": "alipay",
        "trade_no": None,
        "created_at": datetime.utcnow().isoformat(),
        "paid_at": None,
    }


def generate_zpay_signature(params: Dict[str, str], secret_key: str) -> str:
    """
    Generate Z-Pay signature for testing.

    Signature algorithm:
    1. Sort parameters alphabetically (exclude sign, sign_type)
    2. Concatenate as key1=value1&key2=value2...
    3. Append secret key: ...&key=SECRET_KEY
    4. MD5 hash, lowercase
    """
    # Sort parameters, excluding sign and sign_type
    sorted_params = sorted(
        (k, v) for k, v in params.items()
        if k not in ("sign", "sign_type") and v
    )

    # Build query string
    query_string = "&".join(f"{k}={v}" for k, v in sorted_params)

    # Append secret key
    sign_string = f"{query_string}&key={secret_key}"

    # MD5 hash
    return hashlib.md5(sign_string.encode()).hexdigest().lower()


@pytest.fixture
def valid_webhook_payload(mock_zpay_config: Dict[str, str]) -> Dict[str, str]:
    """Generate a valid webhook payload with correct signature."""
    params = {
        "pid": mock_zpay_config["zpay_pid"],
        "trade_no": "zpay-trade-12345",
        "out_trade_no": "PDS1704326400123456",
        "type": "alipay",
        "name": "Credits Purchase",
        "money": "50.00",
        "trade_status": "TRADE_SUCCESS",
        "sign_type": "MD5",
    }

    # Generate signature
    params["sign"] = generate_zpay_signature(params, mock_zpay_config["zpay_key"])

    return params


@pytest.fixture
def invalid_signature_webhook_payload(mock_zpay_config: Dict[str, str]) -> Dict[str, str]:
    """Generate a webhook payload with invalid signature."""
    return {
        "pid": mock_zpay_config["zpay_pid"],
        "trade_no": "zpay-trade-12345",
        "out_trade_no": "PDS1704326400123456",
        "type": "alipay",
        "name": "Credits Purchase",
        "money": "50.00",
        "trade_status": "TRADE_SUCCESS",
        "sign": "invalid-signature",
        "sign_type": "MD5",
    }


# Test classes will be added in Phase 4 when implementing payment endpoints


class TestZPaySignature:
    """Tests for Z-Pay signature generation and verification."""

    def test_generate_signature(self, mock_zpay_config: Dict[str, str]) -> None:
        """Test that signature generation produces consistent results."""
        params = {
            "pid": "test-pid",
            "money": "50.00",
            "name": "Test Order",
        }

        sig1 = generate_zpay_signature(params, mock_zpay_config["zpay_key"])
        sig2 = generate_zpay_signature(params, mock_zpay_config["zpay_key"])

        assert sig1 == sig2
        assert len(sig1) == 32  # MD5 hash length

    def test_signature_excludes_sign_field(
        self, mock_zpay_config: Dict[str, str]
    ) -> None:
        """Test that existing sign field is excluded from calculation."""
        params = {
            "pid": "test-pid",
            "money": "50.00",
            "sign": "existing-signature",
        }

        sig = generate_zpay_signature(params, mock_zpay_config["zpay_key"])

        # Should produce same result as without sign field
        params_no_sign = {"pid": "test-pid", "money": "50.00"}
        sig_no_sign = generate_zpay_signature(params_no_sign, mock_zpay_config["zpay_key"])

        assert sig == sig_no_sign


class TestWebhookPayload:
    """Tests for webhook payload validation."""

    def test_valid_webhook_has_correct_signature(
        self,
        valid_webhook_payload: Dict[str, str],
        mock_zpay_config: Dict[str, str],
    ) -> None:
        """Test that valid webhook payload has correct signature."""
        expected_sig = generate_zpay_signature(
            valid_webhook_payload, mock_zpay_config["zpay_key"]
        )
        assert valid_webhook_payload["sign"] == expected_sig

    def test_invalid_signature_detected(
        self,
        invalid_signature_webhook_payload: Dict[str, str],
        mock_zpay_config: Dict[str, str],
    ) -> None:
        """Test that invalid signature is detected."""
        expected_sig = generate_zpay_signature(
            invalid_signature_webhook_payload, mock_zpay_config["zpay_key"]
        )
        assert invalid_signature_webhook_payload["sign"] != expected_sig
