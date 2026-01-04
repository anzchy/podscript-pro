# Implementation Plan: Supabase Auth + Z-Pay Payment Integration

**Branch**: `003-add-supabase-and-payment` | **Date**: 2026-01-04 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/003-add-supabase-and-payment/spec.md`

## Summary

Add user authentication (Supabase Auth) and credits-based payment system (Z-Pay) to Podscript. Users must register/login to transcribe, purchase credits (1 CNY = 1 credit), and credits are deducted per transcription hour. The system extends the existing Python/FastAPI backend with new routers for auth, payment, and credits, plus new frontend pages for login and credits management.

## Technical Context

**Language/Version**: Python 3.10-3.12 (per pyproject.toml)
**Primary Dependencies**: FastAPI 0.115+, Pydantic 2.8+, Supabase Python SDK (new), httpx
**Storage**: Supabase PostgreSQL (new - users_credits, credit_transactions, payment_orders tables)
**Testing**: pytest with 80% coverage threshold, httpx.AsyncClient for API tests
**Target Platform**: Linux server (uvicorn), vanilla HTML/JS frontend
**Project Type**: Single monolithic Python backend with static frontend
**Performance Goals**: 100 concurrent authenticated requests, <50ms auth overhead, <5s webhook processing
**Constraints**: CNY only, integer credits only, max 500 CNY single payment
**Scale/Scope**: Initial launch on Supabase free tier, single server deployment

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Note**: Constitution file contains placeholder template (not project-specific). Applying general best practices:

| Principle | Status | Notes |
|-----------|--------|-------|
| Test-First | PASS | Will write tests for auth, payment, credits APIs before implementation |
| Simplicity | PASS | No new external frameworks; extends existing FastAPI structure |
| Security | PASS | JWT validation, webhook signature verification, RLS specified |
| Observability | PASS | Structured logging for payment events specified in clarifications |

**No violations requiring justification.**

## Project Structure

### Documentation (this feature)

```text
specs/003-add-supabase-and-payment/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── openapi.yaml     # API contract
└── tasks.md             # Phase 2 output (from /speckit.tasks)
```

### Source Code (repository root)

```text
src/
├── podscript_api/
│   ├── main.py            # Add auth middleware, credits validation
│   ├── routers/           # NEW: API route modules
│   │   ├── __init__.py
│   │   ├── auth.py        # Login/register/logout endpoints
│   │   ├── payment.py     # Payment creation, webhook
│   │   └── credits.py     # Balance query, transaction history
│   ├── middleware/        # NEW: Middleware modules
│   │   ├── __init__.py
│   │   └── auth.py        # JWT validation middleware
│   └── static/
│       ├── index.html     # UPDATE: Add auth UI, disable for guests
│       ├── login.html     # NEW: Login/register page
│       ├── credits.html   # NEW: Credits/payment page
│       ├── payment-success.html  # NEW: Post-payment page
│       ├── login.js       # NEW: Auth logic
│       ├── credits.js     # NEW: Payment logic
│       └── [existing files...]
├── podscript_pipeline/    # MINIMAL CHANGES: Add credits check in transcription
└── podscript_shared/
    ├── models.py          # ADD: User, CreditTransaction, PaymentOrder models
    ├── config.py          # ADD: Supabase, Z-Pay config
    └── supabase.py        # NEW: Supabase client wrapper

tests/
├── test_api.py            # UPDATE: Add auth header to existing tests
├── test_auth.py           # NEW: Auth endpoint tests
├── test_payment.py        # NEW: Payment flow tests
├── test_credits.py        # NEW: Credits operation tests
└── [existing files...]

logs/                      # NEW: Structured payment logs
└── payment.log
```

**Structure Decision**: Extend existing single-project structure. New routers/middleware directories follow FastAPI conventions. No new packages or major architectural changes.

## Complexity Tracking

> No violations requiring justification. Feature extends existing patterns.

---

## Phase 0: Research Required

### Research Topics

1. **Supabase Python SDK best practices** - Server-side JWT validation, RLS bypass for webhooks
2. **Z-Pay API integration patterns** - Signature generation, webhook handling, error codes
3. **FastAPI authentication middleware** - JWT cookie handling, dependency injection patterns
4. **Credit transaction atomicity** - Ensuring balance updates are atomic with transactions

### Research Agents to Dispatch

- Research Supabase Python SDK for FastAPI integration
- Research Z-Pay payment gateway API specification
- Research FastAPI JWT middleware patterns

---

## Phase 0 Complete: Research

**Generated**: [research.md](./research.md)

Key decisions from research:
- **Supabase SDK**: Use `supabase` package with PyJWT for local JWT validation
- **Service Role**: Separate admin client for webhook operations (RLS bypass)
- **Z-Pay Integration**: Standard MD5 signature pattern per spec
- **Auth Pattern**: FastAPI dependency injection (not middleware) for authentication
- **Atomicity**: Database functions for atomic credit operations

---

## Phase 1 Complete: Design Artifacts

**Generated artifacts:**

| Artifact | Purpose |
|----------|---------|
| [data-model.md](./data-model.md) | Database schema, RLS policies, migration SQL |
| [contracts/openapi.yaml](./contracts/openapi.yaml) | API contract for auth, credits, payment endpoints |
| [quickstart.md](./quickstart.md) | Setup guide for developers |

**Key design decisions:**
1. Three new tables: `users_credits`, `credit_transactions`, `payment_orders`
2. Trigger-based user initialization (10 free credits on signup)
3. Database functions for atomic credit operations
4. Cookie-based JWT authentication (not Authorization header)
5. Separate routers for auth, credits, payment

---

## Next Step

Run `/speckit.tasks` to generate the task breakdown for implementation.
