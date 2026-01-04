# Data Model: Supabase Auth + Z-Pay Payment Integration

**Generated**: 2026-01-04
**Feature Branch**: `003-add-supabase-and-payment`

## Overview

This document defines the database schema for user authentication, credits system, and payment integration. All tables are created in Supabase PostgreSQL with Row Level Security (RLS) enabled.

---

## Entity Relationship Diagram

```
┌─────────────────────┐
│    auth.users       │  (Supabase managed)
│─────────────────────│
│ id (UUID) PK        │
│ email               │
│ created_at          │
└─────────┬───────────┘
          │ 1:1
          ▼
┌─────────────────────┐
│   users_credits     │  (Extended user data)
│─────────────────────│
│ id (UUID) PK/FK     │──────────────────────────────┐
│ credit_balance      │                              │
│ created_at          │                              │
└─────────────────────┘                              │
          │                                          │
          │ 1:N                                      │ 1:N
          ▼                                          ▼
┌─────────────────────┐                   ┌─────────────────────┐
│ credit_transactions │                   │   payment_orders    │
│─────────────────────│                   │─────────────────────│
│ id (UUID) PK        │                   │ id (UUID) PK        │
│ user_id (UUID) FK   │                   │ user_id (UUID) FK   │
│ type                │                   │ out_trade_no        │
│ amount              │                   │ amount              │
│ balance_after       │                   │ credits             │
│ description         │                   │ status              │
│ related_order_id FK │◄──────────────────│ payment_method      │
│ related_task_id     │                   │ trade_no            │
│ created_at          │                   │ created_at          │
└─────────────────────┘                   │ paid_at             │
                                          └─────────────────────┘
```

---

## Table Definitions

### 1. users_credits

Extended user data storing credit balance. Linked 1:1 with `auth.users`.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK, FK → auth.users(id) ON DELETE CASCADE | User ID from Supabase Auth |
| `credit_balance` | INTEGER | NOT NULL, DEFAULT 10, CHECK >= 0 | Current credit balance (10 = initial bonus) |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Record creation timestamp |

**Indexes:**
- Primary key on `id`

**RLS Policies:**
- SELECT: `auth.uid() = id`
- UPDATE: `auth.uid() = id`

**SQL:**
```sql
CREATE TABLE public.users_credits (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    credit_balance INTEGER NOT NULL DEFAULT 10 CHECK (credit_balance >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE public.users_credits ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can read own credits"
    ON public.users_credits FOR SELECT
    USING (auth.uid() = id);

CREATE POLICY "Users can update own credits"
    ON public.users_credits FOR UPDATE
    USING (auth.uid() = id);

-- Service role can insert (for trigger) and update (for webhooks)
CREATE POLICY "Service role full access"
    ON public.users_credits FOR ALL
    USING (auth.role() = 'service_role');
```

---

### 2. credit_transactions

Audit log of all credit changes (purchases, consumption, bonuses).

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK, DEFAULT gen_random_uuid() | Transaction ID |
| `user_id` | UUID | NOT NULL, FK → users_credits(id) ON DELETE CASCADE | User who made the transaction |
| `type` | TEXT | NOT NULL, CHECK IN ('recharge', 'consumption', 'bonus', 'refund') | Transaction type |
| `amount` | INTEGER | NOT NULL | Credits added (+) or deducted (-) |
| `balance_after` | INTEGER | NOT NULL | Balance after this transaction |
| `description` | TEXT | NOT NULL | Human-readable description |
| `related_order_id` | UUID | NULLABLE, FK → payment_orders(id) | For recharges: linked payment order |
| `related_task_id` | TEXT | NULLABLE | For consumption: linked transcription task ID |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Transaction timestamp |

**Indexes:**
- Primary key on `id`
- Index on `user_id` for user history queries
- Index on `related_order_id` for idempotency checks
- Index on `created_at` for sorting

**RLS Policies:**
- SELECT: `auth.uid() = user_id`
- INSERT: Service role only (backend)

**SQL:**
```sql
CREATE TABLE public.credit_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.users_credits(id) ON DELETE CASCADE,
    type TEXT NOT NULL CHECK (type IN ('recharge', 'consumption', 'bonus', 'refund')),
    amount INTEGER NOT NULL,
    balance_after INTEGER NOT NULL,
    description TEXT NOT NULL,
    related_order_id UUID REFERENCES public.payment_orders(id),
    related_task_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_credit_transactions_user_id ON public.credit_transactions(user_id);
CREATE INDEX idx_credit_transactions_order_id ON public.credit_transactions(related_order_id);
CREATE INDEX idx_credit_transactions_created_at ON public.credit_transactions(created_at DESC);

ALTER TABLE public.credit_transactions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can read own transactions"
    ON public.credit_transactions FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Service role can insert"
    ON public.credit_transactions FOR INSERT
    WITH CHECK (auth.role() = 'service_role');
```

---

### 3. payment_orders

Payment orders for credit purchases via Z-Pay.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK, DEFAULT gen_random_uuid() | Order ID |
| `user_id` | UUID | NOT NULL, FK → users_credits(id) ON DELETE CASCADE | User who created the order |
| `out_trade_no` | TEXT | NOT NULL, UNIQUE | Unique order number for Z-Pay |
| `amount` | INTEGER | NOT NULL, CHECK > 0 AND <= 500 | Payment amount in CNY |
| `credits` | INTEGER | NOT NULL, CHECK > 0 | Credits to be added (= amount) |
| `status` | TEXT | NOT NULL, DEFAULT 'pending', CHECK IN (...) | Order status |
| `payment_method` | TEXT | NULLABLE, CHECK IN ('wxpay', 'alipay') | Payment method used |
| `trade_no` | TEXT | NULLABLE | Z-Pay transaction ID (set after payment) |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Order creation timestamp |
| `paid_at` | TIMESTAMPTZ | NULLABLE | Payment confirmation timestamp |

**Status Values:**
- `pending`: Order created, awaiting payment
- `paid`: Payment confirmed, credits added
- `failed`: Payment failed
- `expired`: Order expired (30 min timeout)

**Indexes:**
- Primary key on `id`
- Unique index on `out_trade_no` (idempotency key)
- Index on `user_id` for user order history
- Index on `status` for pending order cleanup

**RLS Policies:**
- SELECT: `auth.uid() = user_id`
- INSERT: `auth.uid() = user_id`
- UPDATE: Service role only (webhooks)

**SQL:**
```sql
CREATE TABLE public.payment_orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.users_credits(id) ON DELETE CASCADE,
    out_trade_no TEXT NOT NULL UNIQUE,
    amount INTEGER NOT NULL CHECK (amount > 0 AND amount <= 500),
    credits INTEGER NOT NULL CHECK (credits > 0),
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'paid', 'failed', 'expired')),
    payment_method TEXT CHECK (payment_method IN ('wxpay', 'alipay')),
    trade_no TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    paid_at TIMESTAMPTZ
);

CREATE INDEX idx_payment_orders_user_id ON public.payment_orders(user_id);
CREATE INDEX idx_payment_orders_status ON public.payment_orders(status);
CREATE INDEX idx_payment_orders_created_at ON public.payment_orders(created_at DESC);

ALTER TABLE public.payment_orders ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can read own orders"
    ON public.payment_orders FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can create own orders"
    ON public.payment_orders FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Service role can update"
    ON public.payment_orders FOR UPDATE
    USING (auth.role() = 'service_role');
```

---

## Database Functions

### 1. handle_new_user()

Trigger function to create `users_credits` record when a new user registers.

```sql
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER SET search_path = public
AS $$
BEGIN
    INSERT INTO public.users_credits (id, credit_balance)
    VALUES (NEW.id, 10);  -- 10 free credits for new users

    -- Log the bonus transaction
    INSERT INTO public.credit_transactions (user_id, type, amount, balance_after, description)
    VALUES (NEW.id, 'bonus', 10, 10, '新用户注册奖励');

    RETURN NEW;
END;
$$;

CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();
```

### 2. add_credits()

Atomic function for adding credits (used by payment webhook).

```sql
CREATE OR REPLACE FUNCTION public.add_credits(
    p_user_id UUID,
    p_amount INTEGER,
    p_order_id UUID,
    p_description TEXT
) RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER SET search_path = public
AS $$
DECLARE
    v_new_balance INTEGER;
BEGIN
    -- Idempotency check: if transaction for this order exists, return current balance
    IF EXISTS (SELECT 1 FROM credit_transactions WHERE related_order_id = p_order_id) THEN
        SELECT credit_balance INTO v_new_balance FROM users_credits WHERE id = p_user_id;
        RETURN v_new_balance;
    END IF;

    -- Update balance atomically
    UPDATE users_credits
    SET credit_balance = credit_balance + p_amount
    WHERE id = p_user_id
    RETURNING credit_balance INTO v_new_balance;

    -- Insert transaction log
    INSERT INTO credit_transactions (user_id, type, amount, balance_after, description, related_order_id)
    VALUES (p_user_id, 'recharge', p_amount, v_new_balance, p_description, p_order_id);

    RETURN v_new_balance;
END;
$$;
```

### 3. deduct_credits()

Atomic function for deducting credits (used by transcription).

```sql
CREATE OR REPLACE FUNCTION public.deduct_credits(
    p_user_id UUID,
    p_amount INTEGER,
    p_task_id TEXT,
    p_description TEXT
) RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER SET search_path = public
AS $$
DECLARE
    v_current_balance INTEGER;
    v_new_balance INTEGER;
BEGIN
    -- Get current balance with lock
    SELECT credit_balance INTO v_current_balance
    FROM users_credits
    WHERE id = p_user_id
    FOR UPDATE;

    -- Check sufficient balance
    IF v_current_balance < p_amount THEN
        RAISE EXCEPTION 'Insufficient credits: has %, needs %', v_current_balance, p_amount;
    END IF;

    -- Update balance
    UPDATE users_credits
    SET credit_balance = credit_balance - p_amount
    WHERE id = p_user_id
    RETURNING credit_balance INTO v_new_balance;

    -- Insert transaction log
    INSERT INTO credit_transactions (user_id, type, amount, balance_after, description, related_task_id)
    VALUES (p_user_id, 'consumption', -p_amount, v_new_balance, p_description, p_task_id);

    RETURN v_new_balance;
END;
$$;
```

### 4. refund_credits()

Atomic function for refunding credits (used when transcription fails).

```sql
CREATE OR REPLACE FUNCTION public.refund_credits(
    p_user_id UUID,
    p_amount INTEGER,
    p_task_id TEXT,
    p_description TEXT
) RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER SET search_path = public
AS $$
DECLARE
    v_new_balance INTEGER;
BEGIN
    -- Update balance
    UPDATE users_credits
    SET credit_balance = credit_balance + p_amount
    WHERE id = p_user_id
    RETURNING credit_balance INTO v_new_balance;

    -- Insert transaction log
    INSERT INTO credit_transactions (user_id, type, amount, balance_after, description, related_task_id)
    VALUES (p_user_id, 'refund', p_amount, v_new_balance, p_description, p_task_id);

    RETURN v_new_balance;
END;
$$;
```

---

## State Transitions

### PaymentOrder Status

```
[pending] ──────┬──────────────────► [paid]
     │          │                      │
     │          │ (webhook: success)   │
     │          │                      │
     │          └──────────────────► [failed]
     │            (webhook: failure)
     │
     └─────────────────────────────► [expired]
               (30 min timeout cron)
```

### Credit Transaction Types

| Type | Amount Sign | Trigger | Description |
|------|-------------|---------|-------------|
| `bonus` | + | User registration | Initial 10 free credits |
| `recharge` | + | Payment webhook (success) | Credits purchased |
| `consumption` | - | Transcription start | Credits used for service |
| `refund` | + | Transcription failure | Credits returned |

---

## Pydantic Models (Python)

```python
from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime
from uuid import UUID

class UserCredits(BaseModel):
    id: UUID
    credit_balance: int = Field(ge=0)
    created_at: datetime

class CreditTransaction(BaseModel):
    id: UUID
    user_id: UUID
    type: Literal['recharge', 'consumption', 'bonus', 'refund']
    amount: int
    balance_after: int
    description: str
    related_order_id: Optional[UUID] = None
    related_task_id: Optional[str] = None
    created_at: datetime

class PaymentOrder(BaseModel):
    id: UUID
    user_id: UUID
    out_trade_no: str
    amount: int = Field(gt=0, le=500)
    credits: int = Field(gt=0)
    status: Literal['pending', 'paid', 'failed', 'expired'] = 'pending'
    payment_method: Optional[Literal['wxpay', 'alipay']] = None
    trade_no: Optional[str] = None
    created_at: datetime
    paid_at: Optional[datetime] = None

# Request/Response models
class CreatePaymentRequest(BaseModel):
    amount: int = Field(gt=0, le=500, description="Payment amount in CNY")
    payment_method: Literal['wxpay', 'alipay'] = 'alipay'

class CreatePaymentResponse(BaseModel):
    order_id: UUID
    payment_url: str

class CreditsBalanceResponse(BaseModel):
    balance: int

class TransactionHistoryResponse(BaseModel):
    transactions: list[CreditTransaction]
    total: int
```

---

## Validation Rules

1. **Credit Balance**: Must be >= 0 (enforced by CHECK constraint)
2. **Payment Amount**: Must be 1-500 CNY (enforced by CHECK constraint)
3. **Credits = Amount**: 1:1 ratio enforced at application level
4. **Order Uniqueness**: `out_trade_no` must be unique (UNIQUE constraint)
5. **Idempotency**: `add_credits()` function checks for existing transaction before inserting
6. **Cascade Delete**: All user data deleted when auth.users record is deleted

---

## Migration Script

Complete SQL to run in Supabase SQL Editor:

```sql
-- Run this in Supabase SQL Editor to set up the database

-- 1. Create tables (order matters for foreign keys)
-- payment_orders first (referenced by credit_transactions)
CREATE TABLE IF NOT EXISTS public.payment_orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    out_trade_no TEXT NOT NULL UNIQUE,
    amount INTEGER NOT NULL CHECK (amount > 0 AND amount <= 500),
    credits INTEGER NOT NULL CHECK (credits > 0),
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'paid', 'failed', 'expired')),
    payment_method TEXT CHECK (payment_method IN ('wxpay', 'alipay')),
    trade_no TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    paid_at TIMESTAMPTZ
);

-- users_credits
CREATE TABLE IF NOT EXISTS public.users_credits (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    credit_balance INTEGER NOT NULL DEFAULT 10 CHECK (credit_balance >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Add FK to payment_orders now that users_credits exists
ALTER TABLE public.payment_orders
ADD CONSTRAINT payment_orders_user_id_fkey
FOREIGN KEY (user_id) REFERENCES public.users_credits(id) ON DELETE CASCADE;

-- credit_transactions
CREATE TABLE IF NOT EXISTS public.credit_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.users_credits(id) ON DELETE CASCADE,
    type TEXT NOT NULL CHECK (type IN ('recharge', 'consumption', 'bonus', 'refund')),
    amount INTEGER NOT NULL,
    balance_after INTEGER NOT NULL,
    description TEXT NOT NULL,
    related_order_id UUID REFERENCES public.payment_orders(id),
    related_task_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 2. Create indexes
CREATE INDEX IF NOT EXISTS idx_payment_orders_user_id ON public.payment_orders(user_id);
CREATE INDEX IF NOT EXISTS idx_payment_orders_status ON public.payment_orders(status);
CREATE INDEX IF NOT EXISTS idx_credit_transactions_user_id ON public.credit_transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_credit_transactions_order_id ON public.credit_transactions(related_order_id);
CREATE INDEX IF NOT EXISTS idx_credit_transactions_created_at ON public.credit_transactions(created_at DESC);

-- 3. Enable RLS
ALTER TABLE public.users_credits ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.credit_transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.payment_orders ENABLE ROW LEVEL SECURITY;

-- 4. Create RLS policies
-- users_credits
CREATE POLICY "Users can read own credits" ON public.users_credits FOR SELECT USING (auth.uid() = id);
CREATE POLICY "Service role full access on users_credits" ON public.users_credits FOR ALL USING (auth.role() = 'service_role');

-- credit_transactions
CREATE POLICY "Users can read own transactions" ON public.credit_transactions FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Service role full access on transactions" ON public.credit_transactions FOR ALL USING (auth.role() = 'service_role');

-- payment_orders
CREATE POLICY "Users can read own orders" ON public.payment_orders FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can create own orders" ON public.payment_orders FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Service role full access on orders" ON public.payment_orders FOR ALL USING (auth.role() = 'service_role');

-- 5. Create functions and triggers
-- (Include all functions from above: handle_new_user, add_credits, deduct_credits, refund_credits)
```
