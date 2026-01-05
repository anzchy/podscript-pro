"""Tests for authentication endpoints and middleware."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from typing import Generator, Dict, Any

import jwt
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Test fixtures for mocking Supabase client


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
    """Mock the load_config function to return test configuration."""
    from podscript_shared.models import AppConfig

    # Create a real AppConfig with test values to avoid Mock pathing issues
    mock_app_config = AppConfig(
        supabase_url=mock_supabase_config["supabase_url"],
        supabase_anon_key=mock_supabase_config["supabase_anon_key"],
        supabase_service_role_key=mock_supabase_config["supabase_service_role_key"],
        supabase_jwt_secret=mock_supabase_config["supabase_jwt_secret"],
    )

    with patch("podscript_api.middleware.auth.load_config", return_value=mock_app_config):
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
def expired_jwt_token(mock_supabase_config: Dict[str, str]) -> str:
    """Generate an expired JWT token for testing."""
    payload = {
        "sub": "test-user-id-12345",
        "email": "test@example.com",
        "aud": "authenticated",
        "exp": datetime.utcnow() - timedelta(hours=1),
        "iat": datetime.utcnow() - timedelta(hours=2),
    }
    return jwt.encode(
        payload,
        mock_supabase_config["supabase_jwt_secret"],
        algorithm="HS256",
    )


@pytest.fixture
def invalid_audience_token(mock_supabase_config: Dict[str, str]) -> str:
    """Generate a JWT token with wrong audience."""
    payload = {
        "sub": "test-user-id-12345",
        "email": "test@example.com",
        "aud": "wrong-audience",
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

    # Mock auth operations
    mock_auth = MagicMock()
    mock_client.auth = mock_auth

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
def mock_user_credits_response() -> Dict[str, Any]:
    """Mock response for user credits query."""
    return {
        "id": "test-user-id-12345",
        "credit_balance": 10,
        "created_at": datetime.utcnow().isoformat(),
    }


# Test classes will be added in Phase 3 when implementing auth endpoints


class TestAuthMiddleware:
    """Tests for authentication middleware."""

    def test_get_current_user_valid_token(
        self,
        mock_config: Mock,
        valid_jwt_token: str,
    ) -> None:
        """Test get_current_user with valid token."""
        from podscript_api.middleware.auth import get_current_user, CurrentUser
        import asyncio

        # Run the async function
        result = asyncio.get_event_loop().run_until_complete(
            get_current_user(access_token=valid_jwt_token)
        )

        assert isinstance(result, CurrentUser)
        assert result.user_id == "test-user-id-12345"
        assert result.email == "test@example.com"

    def test_get_current_user_no_token(self, mock_config: Mock) -> None:
        """Test get_current_user with no token raises 401."""
        from podscript_api.middleware.auth import get_current_user, AuthError
        import asyncio

        with pytest.raises(AuthError) as exc_info:
            asyncio.get_event_loop().run_until_complete(
                get_current_user(access_token=None)
            )

        assert exc_info.value.status_code == 401
        assert "Not authenticated" in str(exc_info.value.detail)

    def test_get_current_user_expired_token(
        self,
        mock_config: Mock,
        expired_jwt_token: str,
    ) -> None:
        """Test get_current_user with expired token raises 401."""
        from podscript_api.middleware.auth import get_current_user, AuthError
        import asyncio

        with pytest.raises(AuthError) as exc_info:
            asyncio.get_event_loop().run_until_complete(
                get_current_user(access_token=expired_jwt_token)
            )

        assert exc_info.value.status_code == 401
        assert "expired" in str(exc_info.value.detail).lower()

    def test_get_current_user_optional_valid_token(
        self,
        mock_config: Mock,
        valid_jwt_token: str,
    ) -> None:
        """Test get_current_user_optional with valid token returns user."""
        from podscript_api.middleware.auth import get_current_user_optional, CurrentUser
        import asyncio

        result = asyncio.get_event_loop().run_until_complete(
            get_current_user_optional(access_token=valid_jwt_token)
        )

        assert isinstance(result, CurrentUser)
        assert result.user_id == "test-user-id-12345"

    def test_get_current_user_optional_no_token(self, mock_config: Mock) -> None:
        """Test get_current_user_optional with no token returns None."""
        from podscript_api.middleware.auth import get_current_user_optional
        import asyncio

        result = asyncio.get_event_loop().run_until_complete(
            get_current_user_optional(access_token=None)
        )

        assert result is None

    def test_get_current_user_optional_invalid_token(
        self,
        mock_config: Mock,
        expired_jwt_token: str,
    ) -> None:
        """Test get_current_user_optional with invalid token returns None."""
        from podscript_api.middleware.auth import get_current_user_optional
        import asyncio

        result = asyncio.get_event_loop().run_until_complete(
            get_current_user_optional(access_token=expired_jwt_token)
        )

        assert result is None


class TestAuthEndpoints:
    """Tests for authentication API endpoints."""

    @pytest.fixture
    def mock_supabase_auth(self) -> Generator[MagicMock, None, None]:
        """Mock Supabase auth operations for endpoint testing."""
        mock_client = MagicMock()
        mock_auth = MagicMock()
        mock_client.auth = mock_auth

        # Mock table operations for credits
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        mock_table.select.return_value = mock_table
        mock_table.insert.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.single.return_value = mock_table

        with patch("podscript_api.routers.auth.get_supabase_client", return_value=mock_client):
            with patch("podscript_api.routers.auth.get_supabase_admin_client", return_value=mock_client):
                yield mock_client

    def test_register_success(self, mock_supabase_auth: MagicMock) -> None:
        """Test successful user registration."""
        from fastapi.testclient import TestClient
        from podscript_api.main import app

        # Mock successful signup
        mock_user = MagicMock()
        mock_user.id = "new-user-id-12345"
        mock_user.email = "newuser@example.com"

        mock_session = MagicMock()
        mock_session.access_token = "test-access-token"
        mock_session.refresh_token = "test-refresh-token"

        mock_response = MagicMock()
        mock_response.user = mock_user
        mock_response.session = mock_session

        mock_supabase_auth.auth.sign_up.return_value = mock_response

        # Mock credits table for initial balance
        mock_supabase_auth.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
            "id": "new-user-id-12345",
            "credit_balance": 10,
        }

        client = TestClient(app)
        response = client.post(
            "/api/auth/register",
            json={"email": "newuser@example.com", "password": "password123"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == "new-user-id-12345"
        assert data["email"] == "newuser@example.com"
        assert data["credit_balance"] == 10

    def test_register_duplicate_email(self, mock_supabase_auth: MagicMock) -> None:
        """Test registration with duplicate email fails."""
        from fastapi.testclient import TestClient
        from podscript_api.main import app
        from gotrue.errors import AuthApiError

        # Mock signup failure for duplicate email
        mock_supabase_auth.auth.sign_up.side_effect = AuthApiError(
            message="User already registered",
            status=400,
            code="user_already_exists",
        )

        client = TestClient(app)
        response = client.post(
            "/api/auth/register",
            json={"email": "existing@example.com", "password": "password123"},
        )

        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()

    def test_login_success(self, mock_supabase_auth: MagicMock) -> None:
        """Test successful user login."""
        from fastapi.testclient import TestClient
        from podscript_api.main import app

        # Mock successful sign in
        mock_user = MagicMock()
        mock_user.id = "test-user-id-12345"
        mock_user.email = "test@example.com"

        mock_session = MagicMock()
        mock_session.access_token = "test-access-token"
        mock_session.refresh_token = "test-refresh-token"

        mock_response = MagicMock()
        mock_response.user = mock_user
        mock_response.session = mock_session

        mock_supabase_auth.auth.sign_in_with_password.return_value = mock_response

        # Mock credits query
        mock_supabase_auth.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
            "id": "test-user-id-12345",
            "credit_balance": 50,
        }

        client = TestClient(app)
        response = client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "password123"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == "test-user-id-12345"
        assert data["email"] == "test@example.com"
        assert data["credit_balance"] == 50

        # Check cookie is set
        assert "access_token" in response.cookies

    def test_login_invalid_credentials(self, mock_supabase_auth: MagicMock) -> None:
        """Test login with invalid credentials fails."""
        from fastapi.testclient import TestClient
        from podscript_api.main import app
        from gotrue.errors import AuthApiError

        # Mock sign in failure
        mock_supabase_auth.auth.sign_in_with_password.side_effect = AuthApiError(
            message="Invalid login credentials",
            status=400,
            code="invalid_credentials",
        )

        client = TestClient(app)
        response = client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "wrongpassword"},
        )

        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()

    def test_logout_success(
        self, mock_config: Mock, valid_jwt_token: str, mock_supabase_auth: MagicMock
    ) -> None:
        """Test successful logout."""
        from fastapi.testclient import TestClient
        from podscript_api.main import app

        # Mock sign out
        mock_supabase_auth.auth.sign_out.return_value = None

        client = TestClient(app)
        response = client.post(
            "/api/auth/logout",
            cookies={"access_token": valid_jwt_token},
        )

        assert response.status_code == 200
        assert response.json()["message"] == "Logged out successfully"

        # Check cookie is cleared (Set-Cookie header contains the deletion)
        set_cookie = response.headers.get("set-cookie", "")
        assert "access_token" in set_cookie
        # Cookie deletion sets max-age=0 or expires in the past
        assert 'max-age=0' in set_cookie.lower() or 'expires=' in set_cookie.lower()

    def test_logout_without_auth(self) -> None:
        """Test logout without authentication still succeeds."""
        from fastapi.testclient import TestClient
        from podscript_api.main import app

        client = TestClient(app)
        response = client.post("/api/auth/logout")

        # Logout without token should still succeed (idempotent)
        assert response.status_code == 200

    def test_me_authenticated(
        self, mock_config: Mock, valid_jwt_token: str, mock_supabase_auth: MagicMock
    ) -> None:
        """Test GET /api/auth/me with valid token."""
        from fastapi.testclient import TestClient
        from podscript_api.main import app

        # Mock credits query
        mock_supabase_auth.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
            "id": "test-user-id-12345",
            "credit_balance": 25,
        }

        client = TestClient(app)
        response = client.get(
            "/api/auth/me",
            cookies={"access_token": valid_jwt_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == "test-user-id-12345"
        assert data["email"] == "test@example.com"
        assert data["credit_balance"] == 25

    def test_me_unauthenticated(self) -> None:
        """Test GET /api/auth/me without token returns 401."""
        from fastapi.testclient import TestClient
        from podscript_api.main import app

        client = TestClient(app)
        response = client.get("/api/auth/me")

        assert response.status_code == 401
