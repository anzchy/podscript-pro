"""JWT authentication middleware for FastAPI."""

from typing import Optional, Dict, Any

import jwt
from fastapi import Cookie, HTTPException, status

from podscript_shared.config import load_config
from podscript_shared.supabase import get_supabase_admin_client


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


def _decode_jwt(token: str) -> Dict[str, Any]:
    """
    Decode and validate a Supabase JWT token.

    Args:
        token: The JWT token to decode.

    Returns:
        The decoded token payload.

    Raises:
        AuthError: If the token is invalid or expired.
    """
    config = load_config()

    if not config.supabase_jwt_secret:
        raise AuthError("Authentication not configured")

    try:
        payload = jwt.decode(
            token,
            config.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise AuthError("Token has expired")
    except jwt.InvalidAudienceError:
        raise AuthError("Invalid token audience")
    except jwt.InvalidTokenError as e:
        raise AuthError(f"Invalid token: {str(e)}")


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
        raise AuthError("Not authenticated")

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
        response = client.table("users_credits").select("credit_balance").eq("id", user_id).single().execute()
        if response.data:
            return response.data.get("credit_balance", 0)
        return 0
    except Exception:
        return 0
