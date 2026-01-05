"""Credits management router."""

import logging
import math
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from podscript_api.middleware.auth import get_current_user, CurrentUser
from podscript_shared.supabase import get_supabase_client, get_supabase_admin_client


router = APIRouter()
logger = logging.getLogger(__name__)


# Response models
class BalanceResponse(BaseModel):
    """Credit balance response."""
    balance: int


class Transaction(BaseModel):
    """Credit transaction."""
    id: str
    type: str
    amount: int
    balance_after: Optional[int] = None
    description: Optional[str] = None
    created_at: str


class TransactionsResponse(BaseModel):
    """Transaction history response."""
    transactions: List[Transaction]
    total: int
    page: int
    limit: int


@router.get("/balance", response_model=BalanceResponse)
async def get_balance(
    current_user: CurrentUser = Depends(get_current_user),
) -> BalanceResponse:
    """Get current user's credit balance."""
    client = get_supabase_admin_client()
    if not client:
        raise HTTPException(status_code=503, detail="Database service unavailable")

    try:
        result = client.table("users_credits").select("balance").eq(
            "id", current_user.user_id
        ).single().execute()

        if result.data:
            return BalanceResponse(balance=result.data["balance"])
        else:
            # User has no credits record, return 0
            return BalanceResponse(balance=0)
    except Exception as e:
        # If no record found, return 0
        return BalanceResponse(balance=0)


@router.get("/transactions", response_model=TransactionsResponse)
async def get_transactions(
    current_user: CurrentUser = Depends(get_current_user),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
) -> TransactionsResponse:
    """Get user's credit transaction history."""
    client = get_supabase_admin_client()
    if not client:
        raise HTTPException(status_code=503, detail="Database service unavailable")

    offset = (page - 1) * limit

    try:
        # Get transactions with pagination
        result = client.table("credit_transactions").select("*").eq(
            "user_id", current_user.user_id
        ).order("created_at", desc=True).range(offset, offset + limit - 1).execute()

        # Get total count
        count_result = client.table("credit_transactions").select(
            "id", count="exact"
        ).eq("user_id", current_user.user_id).execute()

        total = count_result.count if count_result.count else 0

        transactions = [
            Transaction(
                id=tx["id"],
                type=tx["type"],
                amount=tx["amount"],
                balance_after=tx.get("balance_after"),
                description=tx.get("description"),
                created_at=tx["created_at"],
            )
            for tx in (result.data or [])
        ]

        return TransactionsResponse(
            transactions=transactions,
            total=total,
            page=page,
            limit=limit,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Credit Operations Helper Functions ====================
# These functions are used by other routers (e.g., main.py for transcription gating)


def calculate_credit_cost(duration_seconds: float) -> int:
    """
    Calculate the credit cost for a transcription based on audio duration.

    Cost: 1 credit per hour of audio, rounded up, minimum 1 credit.

    Args:
        duration_seconds: Audio duration in seconds

    Returns:
        Credit cost (integer, minimum 1)
    """
    if duration_seconds <= 0:
        return 1  # Minimum cost

    hours = duration_seconds / 3600.0
    cost = math.ceil(hours)  # Round up to nearest hour
    return max(1, cost)  # Minimum 1 credit


async def get_user_balance(user_id: str) -> int:
    """
    Get a user's current credit balance.

    Args:
        user_id: The user's UUID

    Returns:
        Current credit balance (0 if not found)
    """
    client = get_supabase_admin_client()
    if not client:
        logger.error("Supabase client not available for balance check")
        return 0

    try:
        result = client.table("users_credits").select("balance").eq(
            "id", user_id
        ).single().execute()

        if result.data:
            return result.data.get("balance", 0)
        return 0
    except Exception as e:
        logger.error(f"Failed to get balance for user {user_id}: {e}")
        return 0


async def deduct_user_credits(
    user_id: str,
    amount: int,
    task_id: str,
    description: str
) -> int:
    """
    Deduct credits from a user's account using the database RPC function.

    Args:
        user_id: The user's UUID
        amount: Amount of credits to deduct (positive integer)
        task_id: Related transcription task ID
        description: Human-readable description

    Returns:
        New balance after deduction

    Raises:
        HTTPException: If insufficient credits or database error
    """
    client = get_supabase_admin_client()
    if not client:
        raise HTTPException(status_code=503, detail="Database service unavailable")

    try:
        # Call the deduct_credits RPC function
        result = client.rpc("deduct_credits", {
            "p_user_id": user_id,
            "p_amount": amount,
            "p_task_id": task_id,
            "p_description": description
        }).execute()

        if result.data is not None:
            logger.info(f"Deducted {amount} credits from user {user_id} for task {task_id}")
            return result.data

        # Fallback: manually update if RPC not available
        logger.warning("RPC not available, using manual credit deduction")
        return await _manual_deduct_credits(client, user_id, amount, task_id, description)

    except Exception as e:
        error_msg = str(e)
        if "Insufficient credits" in error_msg:
            raise HTTPException(
                status_code=402,
                detail="积分不足，请先充值"
            )
        logger.error(f"Failed to deduct credits: {e}")
        raise HTTPException(status_code=500, detail=f"Credit deduction failed: {error_msg}")


async def refund_user_credits(
    user_id: str,
    amount: int,
    task_id: str,
    description: str
) -> int:
    """
    Refund credits to a user's account using the database RPC function.

    Args:
        user_id: The user's UUID
        amount: Amount of credits to refund (positive integer)
        task_id: Related transcription task ID
        description: Human-readable description

    Returns:
        New balance after refund
    """
    client = get_supabase_admin_client()
    if not client:
        logger.error("Supabase client not available for refund")
        return 0

    try:
        # Call the refund_credits RPC function
        result = client.rpc("refund_credits", {
            "p_user_id": user_id,
            "p_amount": amount,
            "p_task_id": task_id,
            "p_description": description
        }).execute()

        if result.data is not None:
            logger.info(f"Refunded {amount} credits to user {user_id} for task {task_id}")
            return result.data

        # Fallback: manually update if RPC not available
        logger.warning("RPC not available, using manual credit refund")
        return await _manual_refund_credits(client, user_id, amount, task_id, description)

    except Exception as e:
        logger.error(f"Failed to refund credits: {e}")
        return 0  # Don't fail the overall operation if refund fails


async def _manual_deduct_credits(
    client,
    user_id: str,
    amount: int,
    task_id: str,
    description: str
) -> int:
    """Manual credit deduction fallback when RPC is not available."""
    # Get current balance
    balance_result = client.table("users_credits").select("balance").eq(
        "id", user_id
    ).single().execute()

    if not balance_result.data:
        raise HTTPException(status_code=402, detail="积分不足，请先充值")

    current_balance = balance_result.data.get("balance", 0)

    if current_balance < amount:
        raise HTTPException(status_code=402, detail="积分不足，请先充值")

    new_balance = current_balance - amount

    # Update balance
    client.table("users_credits").update({
        "balance": new_balance
    }).eq("id", user_id).execute()

    # Record transaction
    client.table("credit_transactions").insert({
        "user_id": user_id,
        "type": "consumption",
        "amount": -amount,
        "balance_after": new_balance,
        "description": description,
        "related_task_id": task_id
    }).execute()

    return new_balance


async def _manual_refund_credits(
    client,
    user_id: str,
    amount: int,
    task_id: str,
    description: str
) -> int:
    """Manual credit refund fallback when RPC is not available."""
    # Get current balance
    balance_result = client.table("users_credits").select("balance").eq(
        "id", user_id
    ).single().execute()

    current_balance = balance_result.data.get("balance", 0) if balance_result.data else 0
    new_balance = current_balance + amount

    # Update balance
    client.table("users_credits").update({
        "balance": new_balance
    }).eq("id", user_id).execute()

    # Record transaction
    client.table("credit_transactions").insert({
        "user_id": user_id,
        "type": "refund",
        "amount": amount,
        "balance_after": new_balance,
        "description": description,
        "related_task_id": task_id
    }).execute()

    return new_balance
