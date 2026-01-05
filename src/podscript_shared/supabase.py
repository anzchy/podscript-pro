"""Supabase client wrapper for authentication and database operations."""

from typing import Optional
from functools import lru_cache

from supabase import create_client, Client

from .config import load_config


@lru_cache(maxsize=1)
def get_supabase_client() -> Optional[Client]:
    """
    Get the Supabase client for regular user operations.
    Uses the anon key - respects RLS policies.

    Returns:
        Supabase client or None if not configured.
    """
    config = load_config()
    if not config.supabase_url or not config.supabase_anon_key:
        return None
    return create_client(config.supabase_url, config.supabase_anon_key)


@lru_cache(maxsize=1)
def get_supabase_admin_client() -> Optional[Client]:
    """
    Get the Supabase admin client for server-side operations.
    Uses the service role key - bypasses RLS policies.

    Use this for:
    - Payment webhook processing
    - Credit operations from backend
    - Any operation that needs to bypass RLS

    Returns:
        Supabase admin client or None if not configured.
    """
    config = load_config()
    if not config.supabase_url or not config.supabase_service_role_key:
        return None
    return create_client(config.supabase_url, config.supabase_service_role_key)


def is_supabase_configured() -> bool:
    """Check if Supabase is properly configured."""
    config = load_config()
    return bool(
        config.supabase_url
        and config.supabase_anon_key
        and config.supabase_service_role_key
        and config.supabase_jwt_secret
    )


def clear_supabase_cache() -> None:
    """Clear cached Supabase clients. Useful for testing."""
    get_supabase_client.cache_clear()
    get_supabase_admin_client.cache_clear()
