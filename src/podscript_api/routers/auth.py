"""Authentication endpoints for user registration, login, and logout."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response
# Import both error classes - gotrue is deprecated wrapper, but actual exceptions
# come from supabase_auth. We need to catch the actual exception type.
from supabase_auth.errors import AuthApiError

from podscript_shared.models import AuthRequest, AuthResponse
from podscript_shared.supabase import get_supabase_client, get_supabase_admin_client
from podscript_api.middleware.auth import get_current_user, get_current_user_optional, CurrentUser

router = APIRouter()


def _set_auth_cookie(response: Response, access_token: str) -> None:
    """Set the access token cookie with secure defaults."""
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        samesite="lax",
        secure=False,  # Set to True in production with HTTPS
        max_age=60 * 60 * 24 * 7,  # 7 days
        path="/",
    )


def _clear_auth_cookie(response: Response) -> None:
    """Clear the access token cookie."""
    response.delete_cookie(
        key="access_token",
        path="/",
    )


def _get_user_credits(user_id: str) -> int:
    """Get user's current credit balance."""
    client = get_supabase_admin_client()
    if not client:
        return 0

    try:
        result = client.table("users_credits").select("balance").eq("id", user_id).single().execute()
        if result.data:
            return result.data.get("balance", 0)
        return 0
    except Exception:
        return 0


@router.post("/register", response_model=AuthResponse)
async def register(
    request: AuthRequest,
    response: Response,
) -> AuthResponse:
    """
    Register a new user with email and password.

    New users receive 10 free credits automatically via database trigger.
    Sets access_token cookie on successful registration.
    """
    client = get_supabase_client()
    if not client:
        raise HTTPException(
            status_code=503,
            detail="Authentication service unavailable",
        )

    try:
        # Register with Supabase Auth
        auth_response = client.auth.sign_up({
            "email": request.email,
            "password": request.password,
        })

        if not auth_response.user or not auth_response.session:
            raise HTTPException(
                status_code=400,
                detail="Registration failed - please try again",
            )

        user = auth_response.user
        session = auth_response.session

        # Set auth cookie
        _set_auth_cookie(response, session.access_token)

        # Get credit balance (created by database trigger)
        credit_balance = _get_user_credits(user.id)

        return AuthResponse(
            user_id=user.id,
            email=user.email or request.email,
            credit_balance=credit_balance,
        )

    except AuthApiError as e:
        if "already registered" in str(e).lower():
            raise HTTPException(
                status_code=400,
                detail="User already registered with this email",
            )
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )


@router.post("/login", response_model=AuthResponse)
async def login(
    request: AuthRequest,
    response: Response,
) -> AuthResponse:
    """
    Login with email and password.

    Sets access_token cookie on successful login.
    """
    client = get_supabase_client()
    if not client:
        raise HTTPException(
            status_code=503,
            detail="Authentication service unavailable",
        )

    try:
        # Sign in with Supabase Auth
        auth_response = client.auth.sign_in_with_password({
            "email": request.email,
            "password": request.password,
        })

        if not auth_response.user or not auth_response.session:
            raise HTTPException(
                status_code=401,
                detail="Invalid email or password",
            )

        user = auth_response.user
        session = auth_response.session

        # Set auth cookie
        _set_auth_cookie(response, session.access_token)

        # Get credit balance
        credit_balance = _get_user_credits(user.id)

        return AuthResponse(
            user_id=user.id,
            email=user.email or request.email,
            credit_balance=credit_balance,
        )

    except AuthApiError as e:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
        )


@router.post("/logout")
async def logout(
    response: Response,
    current_user: Optional[CurrentUser] = Depends(get_current_user_optional),
) -> dict:
    """
    Logout the current user.

    Clears the access_token cookie. This endpoint is idempotent -
    it succeeds even if the user is not logged in.
    """
    # Try to sign out from Supabase if we have a client
    if current_user:
        try:
            client = get_supabase_client()
            if client:
                client.auth.sign_out()
        except Exception:
            # Ignore sign out errors - we'll clear the cookie anyway
            pass

    # Clear the cookie
    _clear_auth_cookie(response)

    return {"message": "Logged out successfully"}


@router.get("/me", response_model=AuthResponse)
async def get_me(
    current_user: CurrentUser = Depends(get_current_user),
) -> AuthResponse:
    """
    Get current user information.

    Returns user ID, email, and current credit balance.
    Requires authentication.
    """
    credit_balance = _get_user_credits(current_user.user_id)

    return AuthResponse(
        user_id=current_user.user_id,
        email=current_user.email,
        credit_balance=credit_balance,
    )
