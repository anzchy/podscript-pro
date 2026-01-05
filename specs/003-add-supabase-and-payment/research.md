# Research: Supabase Auth + Z-Pay Payment Integration

**Generated**: 2026-01-04
**Feature Branch**: `003-add-supabase-and-payment`

## Summary

This document consolidates research findings for implementing Supabase authentication and Z-Pay payment integration in Podscript.

---

## 1. Supabase Python SDK Integration

### Decision
Use `supabase` Python package with PyJWT for local JWT validation and separate admin client for webhook operations.

### Rationale
- Local JWT validation is faster (no network round-trip)
- Service role key enables RLS bypass for payment webhooks
- Separate profiles table pattern is Supabase-recommended for extended user data

### Alternatives Considered
- **JWKS verification**: More secure for RS256 but adds complexity; HS256 with local secret is sufficient for MVP
- **auth.get_user() for validation**: Network round-trip on every request; too slow for auth middleware

### Implementation Details

**Package Installation:**
```bash
pip install supabase PyJWT
```

**Client Initialization (FastAPI lifespan):**
```python
from contextlib import asynccontextmanager
from supabase import create_client, Client
import os

supabase_user: Client = None
supabase_admin: Client = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global supabase_user, supabase_admin
    supabase_user = create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_ANON_KEY")
    )
    supabase_admin = create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    )
    yield
```

**JWT Validation Pattern:**
```python
import jwt
from fastapi import Depends, HTTPException, Cookie
from typing import Optional

async def get_current_user(access_token: Optional[str] = Cookie(None)) -> dict:
    if not access_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        payload = jwt.decode(
            access_token,
            os.getenv("SUPABASE_JWT_SECRET"),
            algorithms=["HS256"],
            audience="authenticated"  # Critical: Supabase requires this
        )
        return {"user_id": payload["sub"], "email": payload.get("email")}
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

**Service Role for Webhooks:**
```python
# Use supabase_admin for payment webhook operations
# This bypasses RLS because Authorization header = service_role
@app.post("/api/payment/webhook")
async def handle_webhook(payload: dict):
    supabase_admin.table("credit_transactions").insert({...}).execute()
```

### Key Pitfalls to Avoid
1. **Missing `audience="authenticated"`** - Token validation fails with confusing errors
2. **Exposing service role key** - Never in frontend or git
3. **Not enabling RLS** - Data leaks between users
4. **Modifying auth.users directly** - Use public profiles table instead

---

## 2. Z-Pay Payment Gateway

### Decision
Implement Z-Pay integration based on standard Chinese payment gateway patterns (MD5 signature, webhook callbacks).

### Rationale
- Z-Pay documentation is not publicly available online
- API follows standard patterns: MD5 signature, sorted params, webhook verification
- Spec already defines endpoints: `zpayz.cn/submit.php` and `zpayz.cn/api.php?act=order`

### Alternatives Considered
- **Other payment gateways**: Z-Pay already chosen by project requirements
- **Direct WeChat/Alipay SDK**: Requires business registration; Z-Pay abstracts this

### Implementation Details

**Signature Generation (per spec):**
```python
import hashlib
from urllib.parse import urlencode

def generate_zpay_signature(params: dict, secret_key: str) -> str:
    # 1. Sort parameters alphabetically (exclude sign, sign_type)
    filtered = {k: v for k, v in params.items() if k not in ('sign', 'sign_type') and v}
    sorted_params = sorted(filtered.items())

    # 2. Concatenate as key=value&key=value
    query_string = urlencode(sorted_params)

    # 3. Append secret key
    sign_string = f"{query_string}&key={secret_key}"

    # 4. MD5 hash, lowercase
    return hashlib.md5(sign_string.encode()).hexdigest().lower()
```

**Payment URL Generation:**
```python
def create_payment_url(order_id: str, amount: int, user_id: str) -> str:
    params = {
        "pid": os.getenv("ZPAY_PID"),
        "type": "alipay",  # or "wxpay"
        "out_trade_no": order_id,
        "notify_url": os.getenv("ZPAY_NOTIFY_URL"),
        "return_url": os.getenv("ZPAY_RETURN_URL"),
        "name": f"Podscript Credits - {amount}",
        "money": str(amount),
        "sitename": "Podscript"
    }
    params["sign"] = generate_zpay_signature(params, os.getenv("ZPAY_KEY"))
    params["sign_type"] = "MD5"

    return f"https://zpayz.cn/submit.php?{urlencode(params)}"
```

**Webhook Verification:**
```python
@app.post("/api/payment/webhook")
async def payment_webhook(request: Request):
    form_data = await request.form()
    params = dict(form_data)

    # Extract and verify signature
    received_sign = params.pop("sign", None)
    expected_sign = generate_zpay_signature(params, os.getenv("ZPAY_KEY"))

    if received_sign != expected_sign:
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Process payment (idempotently using out_trade_no)
    out_trade_no = params.get("out_trade_no")
    trade_status = params.get("trade_status")  # Typically "TRADE_SUCCESS"

    if trade_status == "TRADE_SUCCESS":
        await process_successful_payment(out_trade_no)

    return "success"  # Z-Pay expects plain "success" response
```

### Key Considerations
1. **Idempotency**: Use `out_trade_no` as idempotency key; check if already processed before adding credits
2. **Webhook retries**: Z-Pay will retry on failure; ensure idempotent handling
3. **Order expiry**: Expire pending orders after 30 minutes
4. **Amount validation**: Always validate amount server-side; never trust client input

---

## 3. FastAPI Authentication Middleware

### Decision
Use FastAPI's dependency injection (`Depends`) for authentication, not middleware.

### Rationale
- Dependency injection provides cleaner, type-safe code
- Only runs for protected routes (performance)
- Direct access to user in route handlers
- Easier to test

### Alternatives Considered
- **Middleware**: Runs on every request; needed only for token auto-refresh
- **HTTPBearer security scheme**: Expects Authorization header; we use cookies

### Implementation Details

**Cookie-Based JWT Extraction:**
```python
from fastapi import Cookie, Depends, HTTPException
from typing import Optional

async def get_current_user(access_token: Optional[str] = Cookie(None)) -> dict:
    if not access_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        payload = jwt.decode(
            access_token,
            os.getenv("SUPABASE_JWT_SECRET"),
            algorithms=["HS256"],
            audience="authenticated"
        )
        return {"user_id": payload["sub"], "email": payload.get("email")}
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

**Optional Authentication (for homepage):**
```python
async def get_current_user_optional(
    access_token: Optional[str] = Cookie(None)
) -> Optional[dict]:
    if not access_token:
        return None

    try:
        payload = jwt.decode(
            access_token,
            os.getenv("SUPABASE_JWT_SECRET"),
            algorithms=["HS256"],
            audience="authenticated"
        )
        return {"user_id": payload["sub"], "email": payload.get("email")}
    except jwt.InvalidTokenError:
        return None  # Silent failure for public routes

@app.get("/api/user/status")
async def user_status(user: Optional[dict] = Depends(get_current_user_optional)):
    if user:
        return {"authenticated": True, "user_id": user["user_id"]}
    return {"authenticated": False}
```

**Router-Level Protection:**
```python
from fastapi import APIRouter

# All routes in this router require authentication
protected_router = APIRouter(
    prefix="/api",
    dependencies=[Depends(get_current_user)]
)

@protected_router.get("/credits/balance")
async def get_balance(user: dict = Depends(get_current_user)):
    # user is guaranteed to be authenticated
    return {"balance": await fetch_balance(user["user_id"])}

app.include_router(protected_router)
```

### Session Persistence (Refresh Tokens)

Supabase handles refresh tokens automatically via `supabase.auth.get_session()` on the frontend. The backend only needs to validate access tokens; Supabase JS SDK manages refresh.

**Frontend (login.js):**
```javascript
const { data, error } = await supabase.auth.signInWithPassword({
    email: email,
    password: password
});

// Supabase sets cookies automatically if configured
// Or manually set: document.cookie = `access_token=${data.session.access_token}; path=/; SameSite=Lax`;
```

**Cookie Settings:**
```python
response.set_cookie(
    key="access_token",
    value=token,
    max_age=3600,  # 1 hour (match Supabase default)
    httponly=True,
    secure=True,  # HTTPS only in production
    samesite="lax"
)
```

---

## 4. Credit Transaction Atomicity

### Decision
Use database transactions for all credit operations to ensure atomicity.

### Rationale
- Prevents double-crediting from webhook retries
- Ensures balance + transaction log stay in sync
- PostgreSQL transactions via Supabase are reliable

### Implementation Details

**Atomic Credit Update (using Supabase RPC):**
```sql
-- Create Supabase function for atomic credit update
CREATE OR REPLACE FUNCTION add_credits(
    p_user_id UUID,
    p_amount INTEGER,
    p_order_id UUID,
    p_description TEXT
) RETURNS INTEGER AS $$
DECLARE
    v_new_balance INTEGER;
BEGIN
    -- Check if transaction already exists (idempotency)
    IF EXISTS (SELECT 1 FROM credit_transactions WHERE related_order_id = p_order_id) THEN
        SELECT credit_balance INTO v_new_balance FROM users_credits WHERE id = p_user_id;
        RETURN v_new_balance;
    END IF;

    -- Update balance
    UPDATE users_credits
    SET credit_balance = credit_balance + p_amount
    WHERE id = p_user_id
    RETURNING credit_balance INTO v_new_balance;

    -- Insert transaction log
    INSERT INTO credit_transactions (user_id, type, amount, balance_after, description, related_order_id)
    VALUES (p_user_id, 'recharge', p_amount, v_new_balance, p_description, p_order_id);

    RETURN v_new_balance;
END;
$$ LANGUAGE plpgsql;
```

**Python Usage:**
```python
async def add_credits_atomic(user_id: str, amount: int, order_id: str, description: str) -> int:
    result = supabase_admin.rpc('add_credits', {
        'p_user_id': user_id,
        'p_amount': amount,
        'p_order_id': order_id,
        'p_description': description
    }).execute()

    return result.data  # New balance
```

---

## 5. Environment Variables

**Required for this feature:**
```env
# Supabase
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_ROLE_KEY=eyJ...
SUPABASE_JWT_SECRET=your-jwt-secret

# Z-Pay
ZPAY_PID=your_merchant_id
ZPAY_KEY=your_secret_key
ZPAY_NOTIFY_URL=https://your-domain.com/api/payment/webhook
ZPAY_RETURN_URL=https://your-domain.com/static/payment-success.html
```

---

## Sources

- [Supabase Python SDK Documentation](https://supabase.com/docs/reference/python/initializing)
- [Supabase JWT Documentation](https://supabase.com/docs/guides/auth/jwts)
- [FastAPI JWT Auth Patterns](https://testdriven.io/blog/fastapi-jwt-auth/)
- [JWT and Cookie Auth in FastAPI](https://retz.dev/blog/jwt-and-cookie-auth-in-fastapi/)
- [Supabase User Management](https://supabase.com/docs/guides/auth/managing-user-data)
