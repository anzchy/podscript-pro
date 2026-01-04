# Quickstart: Supabase Auth + Z-Pay Payment Integration

**Feature Branch**: `003-add-supabase-and-payment`
**Estimated Setup Time**: 30 minutes

## Prerequisites

- Python 3.10-3.12 installed
- Supabase account (free tier sufficient)
- Z-Pay merchant account (contact: api.z-pay.cn)
- Existing Podscript codebase cloned

## Step 1: Install New Dependencies

```bash
# Activate virtual environment
source .venv/bin/activate

# Install new packages
pip install supabase PyJWT

# Update requirements.txt
pip freeze > requirements.txt
```

## Step 2: Configure Supabase

### 2.1 Create Supabase Project

1. Go to [supabase.com](https://supabase.com) → New Project
2. Note down your project URL and keys from Settings → API

### 2.2 Run Database Migrations

In Supabase Dashboard → SQL Editor, run the migration script from `data-model.md`:

```sql
-- See specs/003-add-supabase-and-payment/data-model.md for full script
-- Creates: users_credits, credit_transactions, payment_orders tables
-- Enables: RLS policies, triggers, functions
```

### 2.3 Configure Environment Variables

Add to your `.env` file:

```env
# Supabase
SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_ANON_KEY=eyJ...your_anon_key...
SUPABASE_SERVICE_ROLE_KEY=eyJ...your_service_role_key...
SUPABASE_JWT_SECRET=your-jwt-secret-from-settings

# Z-Pay
ZPAY_PID=your_merchant_id
ZPAY_KEY=your_secret_key
ZPAY_NOTIFY_URL=https://your-domain.com/api/payment/webhook
ZPAY_RETURN_URL=https://your-domain.com/static/payment-success.html
```

**Where to find Supabase JWT Secret:**
Settings → API → JWT Settings → JWT Secret

## Step 3: Create Backend Files

### 3.1 Directory Structure

```bash
mkdir -p src/podscript_api/routers
mkdir -p src/podscript_api/middleware
touch src/podscript_api/routers/__init__.py
touch src/podscript_api/middleware/__init__.py
```

### 3.2 Create Files

Create the following files (implementation details in spec):

| File | Purpose |
|------|---------|
| `src/podscript_shared/supabase.py` | Supabase client wrapper |
| `src/podscript_api/middleware/auth.py` | JWT validation dependency |
| `src/podscript_api/routers/auth.py` | Login/register/logout endpoints |
| `src/podscript_api/routers/credits.py` | Balance/transactions endpoints |
| `src/podscript_api/routers/payment.py` | Payment creation/webhook endpoints |

### 3.3 Update main.py

```python
# Add to imports
from podscript_api.routers import auth, credits, payment
from podscript_api.middleware.auth import get_current_user_optional

# Add routers
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(credits.router, prefix="/api/credits", tags=["Credits"])
app.include_router(payment.router, prefix="/api/payment", tags=["Payment"])

# Update existing transcription endpoints to require auth
# (See contracts/openapi.yaml for updated endpoints)
```

## Step 4: Create Frontend Files

### 4.1 New Pages

| File | Purpose |
|------|---------|
| `src/podscript_api/static/login.html` | Login/register page |
| `src/podscript_api/static/credits.html` | Credits/payment page |
| `src/podscript_api/static/payment-success.html` | Post-payment page |
| `src/podscript_api/static/login.js` | Auth logic |
| `src/podscript_api/static/credits.js` | Payment logic |

### 4.2 Update index.html

- Add header with user info/credits/logout
- Disable transcription controls when not logged in
- Show "登录后开始转写" prompt for guests

## Step 5: Test Locally

### 5.1 Start Server

```bash
PYTHONPATH=./src uvicorn podscript_api.main:app --port 8001 --reload
```

### 5.2 Test Auth Flow

```bash
# Register
curl -X POST http://localhost:8001/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "password123"}'

# Login
curl -X POST http://localhost:8001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "password123"}' \
  -c cookies.txt

# Get balance (using cookie)
curl -X GET http://localhost:8001/api/credits/balance \
  -b cookies.txt
```

### 5.3 Test Payment Flow (Mock)

For local testing without real Z-Pay:

1. Create payment order → get order_id
2. Manually simulate webhook:

```bash
# Simulate successful payment webhook
curl -X POST http://localhost:8001/api/payment/webhook \
  -d "pid=YOUR_PID&out_trade_no=ORDER_ID&money=50&trade_status=TRADE_SUCCESS&sign=..."
```

## Step 6: Run Tests

```bash
# Run all tests with coverage
PYTHONPATH=./src pytest --disable-warnings --cov=src --cov-report=term-missing

# Run specific test files
PYTHONPATH=./src pytest tests/test_auth.py -v
PYTHONPATH=./src pytest tests/test_payment.py -v
PYTHONPATH=./src pytest tests/test_credits.py -v
```

## Step 7: Deploy

### 7.1 Update Production Environment

```bash
# SSH to production server
ssh your-server

# Update code
cd /path/to/podscript
git pull origin 003-add-supabase-and-payment

# Update dependencies
source .venv/bin/activate
pip install -r requirements.txt

# Update .env with production values
# IMPORTANT: Use production Supabase URL and keys
# IMPORTANT: Set ZPAY_NOTIFY_URL to production domain
```

### 7.2 Configure Z-Pay Webhook

In Z-Pay merchant dashboard:
- Set notify_url to: `https://your-domain.com/api/payment/webhook`
- Set return_url to: `https://your-domain.com/static/payment-success.html`

### 7.3 Restart Server

```bash
sudo systemctl restart podscript
# or
pm2 restart podscript
```

## Verification Checklist

- [ ] Supabase project created and tables exist
- [ ] Environment variables set correctly
- [ ] User can register and receive 10 free credits
- [ ] User can login and see credit balance in header
- [ ] Guest users see disabled transcription UI
- [ ] Payment order creates and redirects to Z-Pay
- [ ] Webhook successfully adds credits
- [ ] Transcription deducts credits
- [ ] All tests pass with 80% coverage

## Troubleshooting

### "Invalid token" on protected endpoints
- Check `SUPABASE_JWT_SECRET` is correct
- Ensure `audience="authenticated"` in JWT decode

### Webhook not updating credits
- Check Z-Pay signature verification
- Verify `SUPABASE_SERVICE_ROLE_KEY` is set
- Check logs in `logs/payment.log`

### RLS blocking queries
- Ensure RLS policies are created
- Use service role key for webhook operations
- Check `auth.uid()` matches user_id

### Session expires unexpectedly
- Supabase handles token refresh automatically via the JS SDK
- Access tokens expire after 1 hour by default; refresh tokens last 7 days
- The Supabase client automatically refreshes tokens before expiry
- **No manual refresh token handling is required** - the SDK manages this internally
- If using server-side validation only, ensure cookies are set with proper expiry

### Session lost after browser restart
- Supabase stores session in localStorage by default
- Ensure `persistSession: true` (default) in Supabase client config
- Check browser isn't in private/incognito mode
- The refresh token is used automatically to restore the session
