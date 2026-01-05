"""Payment router for Z-Pay integration."""

import os
import hashlib
import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from podscript_api.middleware.auth import get_current_user, CurrentUser
from podscript_shared.supabase import get_supabase_admin_client
from podscript_shared.config import load_config


router = APIRouter()


# Request/Response models
class CreatePaymentRequest(BaseModel):
    """Create payment request."""
    amount: int = Field(..., ge=1, le=500, description="Amount in CNY (1-500)")
    pay_type: str = Field(default="alipay", description="Payment type: alipay or wxpay")


class CreatePaymentResponse(BaseModel):
    """Create payment response."""
    order_id: str
    payment_url: str


class OrderResponse(BaseModel):
    """Order details response."""
    id: str
    amount: int
    credits: int
    status: str
    created_at: str
    paid_at: Optional[str] = None


def generate_zpay_signature(params: dict, secret_key: str) -> str:
    """
    Generate Z-Pay signature.

    Algorithm:
    1. Sort parameters alphabetically (exclude sign, sign_type, empty values)
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


def verify_zpay_signature(params: dict, secret_key: str) -> bool:
    """Verify Z-Pay webhook signature."""
    received_sign = params.get("sign", "")
    expected_sign = generate_zpay_signature(params, secret_key)
    return received_sign.lower() == expected_sign.lower()


@router.post("/create", response_model=CreatePaymentResponse)
async def create_payment(
    request: CreatePaymentRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> CreatePaymentResponse:
    """Create a payment order."""
    config = load_config()

    if not config.zpay_pid or not config.zpay_key:
        raise HTTPException(status_code=503, detail="Payment service not configured")

    client = get_supabase_admin_client()
    if not client:
        raise HTTPException(status_code=503, detail="Database service unavailable")

    # Generate order ID
    order_id = str(uuid.uuid4())
    out_trade_no = f"PDS{int(datetime.utcnow().timestamp())}{order_id[:8]}"

    # Create order in database
    try:
        client.table("payment_orders").insert({
            "id": order_id,
            "user_id": current_user.user_id,
            "out_trade_no": out_trade_no,
            "amount": request.amount,
            "credits": request.amount,  # 1 CNY = 1 credit
            "status": "pending",
            "payment_method": request.pay_type,
        }).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create order: {str(e)}")

    # Build Z-Pay payment URL
    params = {
        "pid": config.zpay_pid,
        "type": request.pay_type,
        "out_trade_no": out_trade_no,
        "notify_url": config.zpay_notify_url or "",
        "return_url": config.zpay_return_url or "",
        "name": f"Podscript Credits x{request.amount}",
        "money": f"{request.amount}.00",
    }

    # Generate signature
    params["sign"] = generate_zpay_signature(params, config.zpay_key)
    params["sign_type"] = "MD5"

    # Build payment URL
    base_url = "https://api.z-pay.cn/submit.php"
    query_string = "&".join(f"{k}={v}" for k, v in params.items())
    payment_url = f"{base_url}?{query_string}"

    return CreatePaymentResponse(order_id=order_id, payment_url=payment_url)


@router.post("/webhook")
async def payment_webhook(request: Request) -> Response:
    """Handle Z-Pay payment webhook."""
    config = load_config()

    if not config.zpay_key:
        return Response(content="fail", media_type="text/plain")

    # Parse form data
    form_data = await request.form()
    params = dict(form_data)

    # Verify signature
    if not verify_zpay_signature(params, config.zpay_key):
        return Response(content="fail", media_type="text/plain")

    # Check trade status
    if params.get("trade_status") != "TRADE_SUCCESS":
        return Response(content="success", media_type="text/plain")

    # Get order
    out_trade_no = params.get("out_trade_no", "")
    client = get_supabase_admin_client()
    if not client:
        return Response(content="fail", media_type="text/plain")

    try:
        # Find order
        result = client.table("payment_orders").select("*").eq(
            "out_trade_no", out_trade_no
        ).single().execute()

        if not result.data:
            return Response(content="fail", media_type="text/plain")

        order = result.data

        # Check if already processed (idempotency)
        if order["status"] == "paid":
            return Response(content="success", media_type="text/plain")

        # Update order status
        client.table("payment_orders").update({
            "status": "paid",
            "trade_no": params.get("trade_no"),
            "paid_at": datetime.utcnow().isoformat(),
        }).eq("id", order["id"]).execute()

        # Add credits to user
        credits = order["credits"]
        user_id = order["user_id"]

        # Get current balance (users_credits.id = user_id)
        balance_result = client.table("users_credits").select("balance").eq(
            "id", user_id
        ).single().execute()

        if balance_result.data:
            new_balance = balance_result.data["balance"] + credits
            client.table("users_credits").update({
                "balance": new_balance,
            }).eq("id", user_id).execute()
        else:
            new_balance = credits
            client.table("users_credits").insert({
                "id": user_id,
                "balance": new_balance,
            }).execute()

        # Record transaction
        client.table("credit_transactions").insert({
            "user_id": user_id,
            "type": "recharge",
            "amount": credits,
            "balance_after": new_balance,
            "description": f"充值 {credits} 积分",
            "related_order_id": order["id"],
        }).execute()

        return Response(content="success", media_type="text/plain")

    except Exception as e:
        return Response(content="fail", media_type="text/plain")


@router.get("/orders/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: str,
    current_user: CurrentUser = Depends(get_current_user),
) -> OrderResponse:
    """Get order details."""
    client = get_supabase_admin_client()
    if not client:
        raise HTTPException(status_code=503, detail="Database service unavailable")

    try:
        result = client.table("payment_orders").select("*").eq(
            "id", order_id
        ).eq("user_id", current_user.user_id).single().execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Order not found")

        order = result.data
        return OrderResponse(
            id=order["id"],
            amount=order["amount"],
            credits=order["credits"],
            status=order["status"],
            created_at=order["created_at"],
            paid_at=order.get("paid_at"),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
