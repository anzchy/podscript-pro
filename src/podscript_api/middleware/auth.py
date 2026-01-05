"""JWT authentication middleware for FastAPI."""

import logging
from typing import Optional, Dict, Any

import httpx
import jwt
from jwt import PyJWKClient
from fastapi import Cookie, HTTPException, status

from podscript_shared.config import load_config
from podscript_shared.supabase import get_supabase_admin_client

logger = logging.getLogger(__name__)

# Cache for JWKS client
_jwks_client: Optional[PyJWKClient] = None


class AuthError(HTTPException):
    """Authentication error with 401 status."""

    def __init__(self, detail: str = "Not authenticated"):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


class CurrentUser:
    """Represents the currently authenticated user."""

    def __init__(self, user_id: str, email: str):
        self.user_id = user_id
        self.email = email

    def __repr__(self) -> str:
        return f"CurrentUser(user_id={self.user_id}, email={self.email})"


def _get_jwks_client(supabase_url: str) -> PyJWKClient:
    """Get or create a cached JWKS client for the Supabase project."""
    global _jwks_client
    if _jwks_client is None:
        jwks_url = f"{supabase_url}/auth/v1/.well-known/jwks.json"
        logger.info(f"Initializing JWKS client from: {jwks_url}")
        _jwks_client = PyJWKClient(jwks_url)
    return _jwks_client


def _decode_jwt(token: str) -> Dict[str, Any]:
    """
    Decode and validate a Supabase JWT token.

    Supports both HS256 (symmetric, uses JWT secret) and ES256 (asymmetric, uses JWKS).

    Args:
        token: The JWT token to decode.

    Returns:
        The decoded token payload.

    Raises:
        AuthError: If the token is invalid or expired.
    """
    config = load_config()

    # First, decode header to see the algorithm (without verification)
    try:
        header = jwt.get_unverified_header(token)
        token_alg = header.get("alg", "unknown")
        logger.debug(f"JWT token algorithm: {token_alg}")
    except Exception as e:
        logger.warning(f"Could not read JWT header: {e}")
        raise AuthError("Invalid token format")

    try:
        if token_alg == "ES256":
            # ES256 uses asymmetric keys - fetch public key from JWKS
            if not config.supabase_url:
                logger.error("JWT validation failed: SUPABASE_URL not configured for ES256")
                raise AuthError("Authentication not configured")

            jwks_client = _get_jwks_client(config.supabase_url)
            signing_key = jwks_client.get_signing_key_from_jwt(token)

            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["ES256"],
                audience="authenticated",
            )
        else:
            # HS256/RS256 uses the JWT secret
            if not config.supabase_jwt_secret:
                logger.error("JWT validation failed: SUPABASE_JWT_SECRET not configured")
                raise AuthError("Authentication not configured")

            payload = jwt.decode(
                token,
                config.supabase_jwt_secret,
                algorithms=["HS256", "RS256"],
                audience="authenticated",
            )

        logger.debug(f"JWT decoded successfully for user: {payload.get('sub')}")
        return payload

    except jwt.ExpiredSignatureError:
        logger.warning("JWT validation failed: Token has expired")
        raise AuthError("登录已过期，请重新登录")
    except jwt.InvalidAudienceError:
        logger.warning("JWT validation failed: Invalid audience")
        raise AuthError("Invalid token audience")
    except jwt.InvalidTokenError as e:
        logger.warning(f"JWT validation failed: {str(e)}")
        raise AuthError(f"Invalid token: {str(e)}")
    except Exception as e:
        logger.error(f"JWT validation error: {str(e)}")
        raise AuthError("Authentication failed")


async def get_current_user(
    access_token: Optional[str] = Cookie(default=None),
) -> CurrentUser:
    """
    FastAPI dependency to get the current authenticated user.

    Extracts and validates the JWT from the access_token cookie.
    Raises 401 if not authenticated or token is invalid.

    Usage:
        @app.get("/protected")
        async def protected_route(user: CurrentUser = Depends(get_current_user)):
            return {"user_id": user.user_id}
    """
    if not access_token:
        logger.warning("Auth failed: No access_token cookie received")
        raise AuthError("未登录或登录已过期")

    payload = _decode_jwt(access_token)

    user_id = payload.get("sub")
    email = payload.get("email")

    if not user_id:
        raise AuthError("Invalid token: missing user ID")

    return CurrentUser(user_id=user_id, email=email or "")


async def get_current_user_optional(
    access_token: Optional[str] = Cookie(default=None),
) -> Optional[CurrentUser]:
    """
    FastAPI dependency to optionally get the current user.

    Returns None if not authenticated instead of raising an error.
    Useful for endpoints that work for both authenticated and anonymous users.

    Usage:
        @app.get("/public")
        async def public_route(user: Optional[CurrentUser] = Depends(get_current_user_optional)):
            if user:
                return {"message": f"Hello, {user.email}"}
            return {"message": "Hello, guest"}
    """
    if not access_token:
        return None

    try:
        payload = _decode_jwt(access_token)
        user_id = payload.get("sub")
        email = payload.get("email")

        if not user_id:
            return None

        return CurrentUser(user_id=user_id, email=email or "")
    except AuthError:
        return None


async def get_user_credits(user_id: str) -> int:
    """
    Get the credit balance for a user.

    Args:
        user_id: The user's UUID.

    Returns:
        The user's credit balance, or 0 if not found.
    """
    client = get_supabase_admin_client()
    if not client:
        return 0

    try:
        response = client.table("users_credits").select("balance").eq("id", user_id).single().execute()
        if response.data:
            return response.data.get("balance", 0)
        return 0
    except Exception:
        return 0
