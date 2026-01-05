-- ============================================================
-- Podscript Database Migration Script
-- Run this in Supabase SQL Editor: https://supabase.jackcheng.tech
-- ============================================================

-- 1. Create tables (order matters for foreign keys)

-- payment_orders first (will be referenced by credit_transactions)
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

-- users_credits (linked to auth.users)
CREATE TABLE IF NOT EXISTS public.users_credits (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    balance INTEGER NOT NULL DEFAULT 10 CHECK (balance >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Add FK to payment_orders now that users_credits exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'payment_orders_user_id_fkey'
    ) THEN
        ALTER TABLE public.payment_orders
        ADD CONSTRAINT payment_orders_user_id_fkey
        FOREIGN KEY (user_id) REFERENCES public.users_credits(id) ON DELETE CASCADE;
    END IF;
END $$;

-- credit_transactions
CREATE TABLE IF NOT EXISTS public.credit_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.users_credits(id) ON DELETE CASCADE,
    type TEXT NOT NULL CHECK (type IN ('recharge', 'consumption', 'bonus', 'refund')),
    amount INTEGER NOT NULL,
    balance_after INTEGER,
    description TEXT NOT NULL,
    related_order_id UUID REFERENCES public.payment_orders(id),
    related_task_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 2. Create indexes
CREATE INDEX IF NOT EXISTS idx_payment_orders_user_id ON public.payment_orders(user_id);
CREATE INDEX IF NOT EXISTS idx_payment_orders_status ON public.payment_orders(status);
CREATE INDEX IF NOT EXISTS idx_payment_orders_created_at ON public.payment_orders(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_credit_transactions_user_id ON public.credit_transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_credit_transactions_order_id ON public.credit_transactions(related_order_id);
CREATE INDEX IF NOT EXISTS idx_credit_transactions_created_at ON public.credit_transactions(created_at DESC);

-- 3. Enable RLS
ALTER TABLE public.users_credits ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.credit_transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.payment_orders ENABLE ROW LEVEL SECURITY;

-- 4. Drop existing policies if they exist (for re-running)
DROP POLICY IF EXISTS "Users can read own credits" ON public.users_credits;
DROP POLICY IF EXISTS "Service role full access on users_credits" ON public.users_credits;
DROP POLICY IF EXISTS "Users can read own transactions" ON public.credit_transactions;
DROP POLICY IF EXISTS "Service role full access on transactions" ON public.credit_transactions;
DROP POLICY IF EXISTS "Users can read own orders" ON public.payment_orders;
DROP POLICY IF EXISTS "Users can create own orders" ON public.payment_orders;
DROP POLICY IF EXISTS "Service role full access on orders" ON public.payment_orders;

-- 5. Create RLS policies
-- users_credits
CREATE POLICY "Users can read own credits" ON public.users_credits
    FOR SELECT USING (auth.uid() = id);
CREATE POLICY "Service role full access on users_credits" ON public.users_credits
    FOR ALL USING (auth.role() = 'service_role');

-- credit_transactions
CREATE POLICY "Users can read own transactions" ON public.credit_transactions
    FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Service role full access on transactions" ON public.credit_transactions
    FOR ALL USING (auth.role() = 'service_role');

-- payment_orders
CREATE POLICY "Users can read own orders" ON public.payment_orders
    FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can create own orders" ON public.payment_orders
    FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Service role full access on orders" ON public.payment_orders
    FOR ALL USING (auth.role() = 'service_role');

-- 6. Create trigger function for new user registration
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER SET search_path = public
AS $$
BEGIN
    -- Create users_credits record with 10 bonus credits
    INSERT INTO public.users_credits (id, balance)
    VALUES (NEW.id, 10);

    -- Log the bonus transaction
    INSERT INTO public.credit_transactions (user_id, type, amount, balance_after, description)
    VALUES (NEW.id, 'bonus', 10, 10, '新用户注册奖励');

    RETURN NEW;
END;
$$;

-- Drop existing trigger if exists
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;

-- Create trigger
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- 7. Create add_credits function (for payment webhook)
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
        SELECT balance INTO v_new_balance FROM users_credits WHERE id = p_user_id;
        RETURN v_new_balance;
    END IF;

    -- Update balance atomically
    UPDATE users_credits
    SET balance = balance + p_amount
    WHERE id = p_user_id
    RETURNING balance INTO v_new_balance;

    -- Insert transaction log
    INSERT INTO credit_transactions (user_id, type, amount, balance_after, description, related_order_id)
    VALUES (p_user_id, 'recharge', p_amount, v_new_balance, p_description, p_order_id);

    RETURN v_new_balance;
END;
$$;

-- 8. Create deduct_credits function (for transcription)
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
    SELECT balance INTO v_current_balance
    FROM users_credits
    WHERE id = p_user_id
    FOR UPDATE;

    -- Check sufficient balance
    IF v_current_balance < p_amount THEN
        RAISE EXCEPTION 'Insufficient credits: has %, needs %', v_current_balance, p_amount;
    END IF;

    -- Update balance
    UPDATE users_credits
    SET balance = balance - p_amount
    WHERE id = p_user_id
    RETURNING balance INTO v_new_balance;

    -- Insert transaction log
    INSERT INTO credit_transactions (user_id, type, amount, balance_after, description, related_task_id)
    VALUES (p_user_id, 'consumption', -p_amount, v_new_balance, p_description, p_task_id);

    RETURN v_new_balance;
END;
$$;

-- 9. Create refund_credits function (for failed transcription)
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
    SET balance = balance + p_amount
    WHERE id = p_user_id
    RETURNING balance INTO v_new_balance;

    -- Insert transaction log
    INSERT INTO credit_transactions (user_id, type, amount, balance_after, description, related_task_id)
    VALUES (p_user_id, 'refund', p_amount, v_new_balance, p_description, p_task_id);

    RETURN v_new_balance;
END;
$$;

-- ============================================================
-- Migration Complete!
-- ============================================================
-- Tables created:
--   - users_credits (1:1 with auth.users, 10 bonus credits on signup)
--   - credit_transactions (audit log)
--   - payment_orders (Z-Pay orders)
--
-- Functions created:
--   - handle_new_user() - Trigger for new user registration
--   - add_credits() - For payment webhook
--   - deduct_credits() - For transcription
--   - refund_credits() - For failed transcription
--
-- Run this to verify:
--   SELECT * FROM pg_tables WHERE schemaname = 'public';
--   SELECT * FROM pg_proc WHERE proname LIKE '%credits%';
-- ============================================================
