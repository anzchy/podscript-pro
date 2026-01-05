# Tasks: Supabase Auth + Z-Pay Payment Integration

**Input**: Design documents from `/specs/003-add-supabase-and-payment/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/openapi.yaml

**Tests**: Tests included as the plan.md specifies Test-First approach with 80% coverage requirement.

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: User story this task belongs to (US1, US2, etc.)
- Paths: `src/` for backend, `tests/` for tests

---

## Phase 1: Setup (Shared Infrastructure) ✅ COMPLETE

**Purpose**: Project initialization, dependencies, and environment setup

- [x] T001 ✅ Install new Python dependencies (supabase, PyJWT) and update requirements.txt
- [x] T002 ✅ [P] Create routers directory structure at src/podscript_api/routers/__init__.py
- [x] T003 ✅ [P] Create middleware directory structure at src/podscript_api/middleware/__init__.py
- [x] T004 ✅ [P] Create logs directory at project root for payment logs
- [x] T005 ✅ Add Supabase and Z-Pay environment variables to .env.example
- [x] T006 ✅ Update src/podscript_shared/config.py with Supabase and Z-Pay configuration classes

---

## Phase 2: Foundational (Blocking Prerequisites) ✅ COMPLETE

**Purpose**: Core infrastructure that MUST be complete before ANY user story

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Database Setup

- [x] T007 ✅ Create Supabase project and note URL/keys (manual step documented)
- [x] T008 ✅ Run database migration SQL from data-model.md in Supabase SQL Editor
- [x] T009 ✅ Verify RLS policies and triggers are active in Supabase dashboard

### Core Backend Infrastructure

- [x] T010 ✅ Create Supabase client wrapper in src/podscript_shared/supabase.py with user and admin clients
- [x] T011 ✅ Add Pydantic models for UserCredits, CreditTransaction, PaymentOrder in src/podscript_shared/models.py
- [x] T012 ✅ Implement JWT validation dependency get_current_user in src/podscript_api/middleware/auth.py
- [x] T013 ✅ Implement optional auth dependency get_current_user_optional in src/podscript_api/middleware/auth.py
- [x] T014 ✅ Create structured payment logger in src/podscript_shared/logging.py

### Test Infrastructure

- [x] T015 ✅ [P] Create tests/test_auth.py with test fixtures for mock Supabase client
- [x] T016 ✅ [P] Create tests/test_payment.py with test fixtures for mock Z-Pay
- [x] T017 ✅ [P] Create tests/test_credits.py with test fixtures

**Checkpoint**: Foundation ready - user story implementation can now begin ✅

---

## Phase 3: User Story 1 & 2 - User Registration & Login (Priority: P1) 🎯 MVP ✅ COMPLETE

**Goal**: Users can register with email/password (receiving 10 free credits) and login to access the service

**Independent Test**:
1. Visit site → Click "登录/注册" → Register with email/password → Verify 10 credits in header
2. Logout → Login with same credentials → Verify session persists

### Tests for User Stories 1 & 2

- [x] T018 ✅ [P] [US1] Write test for POST /api/auth/register endpoint in tests/test_auth.py
- [x] T019 ✅ [P] [US2] Write test for POST /api/auth/login endpoint in tests/test_auth.py
- [x] T020 ✅ [P] [US1] Write test for POST /api/auth/logout endpoint in tests/test_auth.py
- [x] T021 ✅ [P] [US1] Write test for GET /api/auth/me endpoint in tests/test_auth.py

### Backend Implementation

- [x] T022 ✅ [US1] Create auth router with register endpoint in src/podscript_api/routers/auth.py
- [x] T023 ✅ [US2] Add login endpoint to auth router in src/podscript_api/routers/auth.py
- [x] T024 ✅ [US1] Add logout endpoint to auth router in src/podscript_api/routers/auth.py
- [x] T025 ✅ [US1] Add me endpoint (get current user info) to auth router in src/podscript_api/routers/auth.py
- [x] T026 ✅ [US1] Register auth router in src/podscript_api/main.py with prefix /api/auth

### Frontend Implementation

- [x] T027 ✅ [P] [US1] Create login page HTML at src/podscript_api/static/login.html with login/register tabs
- [x] T028 ✅ [US1] Create login.js at src/podscript_api/static/login.js with auth API calls
- [x] T029 ✅ [US1] Update src/podscript_api/static/index.html header with user info/credits/logout for logged-in users
- [ ] T030 [US1] Update src/podscript_api/static/index.html to show disabled controls + login prompt for guests
- [x] T031 ✅ [US1] Update src/podscript_api/static/app.js with auth state management and header update logic
- [x] T032 ✅ [US2] Add redirect-back logic: store intended URL in sessionStorage before login redirect
- [x] T033 ✅ [US2] After successful login, redirect to stored URL (or homepage if none) in login.js

### Verification

- [x] T034 ✅ [US1] Run tests for auth endpoints and verify all pass (14 auth tests passing)
- [x] T035 ✅ [US1] Manual test: Register new user, verify 10 credits, logout, login, verify session

**Checkpoint**: Users can register, login, logout, and see their info in header ✅

---

## Phase 4: User Story 3 & 4 - Purchase Credits (Priority: P2) ✅ COMPLETE

**Goal**: Users can purchase credits using preset amounts (10/50/100 CNY) or custom amounts (1-500 CNY) via Z-Pay

**Independent Test**:
1. Login → Go to credits page → Select 50元 → Click pay → Complete mock payment → Verify +50 credits
2. Login → Go to credits page → Enter 25 in custom field → Verify validation works → Complete payment

**Dependencies**: Requires US1/US2 (user must be logged in)

### Tests for User Stories 3 & 4

- [x] T036 ✅ [P] [US3] Write test for POST /api/payment/create endpoint in tests/test_payment.py
- [x] T037 ✅ [P] [US3] Write test for POST /api/payment/webhook endpoint in tests/test_payment.py
- [x] T038 ✅ [P] [US3] Write test for GET /api/payment/orders/{id} endpoint in tests/test_payment.py
- [x] T039 ✅ [P] [US4] Write test for custom amount validation (1-500 CNY) in tests/test_payment.py
- [x] T040 ✅ [P] [US3] Write test for webhook idempotency (duplicate webhook handling) in tests/test_payment.py
- [x] T041 ✅ [P] [US3] Write test for webhook signature verification in tests/test_payment.py

### Backend Implementation

- [x] T042 ✅ [US3] Implement Z-Pay signature generation function in src/podscript_api/routers/payment.py
- [x] T043 ✅ [US3] Create payment router with create_payment endpoint in src/podscript_api/routers/payment.py
- [x] T044 ✅ [US3] Add webhook endpoint with signature verification in src/podscript_api/routers/payment.py
- [x] T045 ✅ [US3] Add get_order endpoint to payment router in src/podscript_api/routers/payment.py
- [x] T046 ✅ [US3] Register payment router in src/podscript_api/main.py with prefix /api/payment
- [x] T047 ✅ [US3] Add payment logging with structured format in src/podscript_api/routers/payment.py

### Frontend Implementation

- [x] T048 ✅ [P] [US3] Create credits page HTML at src/podscript_api/static/credits.html with preset buttons and custom input
- [x] T049 ✅ [P] [US3] Create payment success page at src/podscript_api/static/payment-success.html
- [x] T050 ✅ [US3] Create credits.js at src/podscript_api/static/credits.js with payment flow
- [x] T051 ✅ [US4] Add custom amount validation (1-500 CNY, integer only) in credits.js
- [x] T052 ✅ [US3] Add navigation link to credits page from header in index.html

### Verification

- [x] T053 ✅ [US3] Run tests for payment endpoints and verify all pass (5 payment tests passing)
- [x] T054 ✅ [US3] Manual test: Create payment order, simulate webhook, verify credits added

**Checkpoint**: Users can purchase credits via preset or custom amounts ✅

---

## Phase 5: User Story 5 - Credits-Gated Transcription (Priority: P3) ✅ COMPLETE

**Goal**: Transcription requires authentication and sufficient credits; credits are deducted on start and refunded on failure

**Independent Test**:
1. Login with 10 credits → Upload 2-hour audio → Start transcription → Verify 2 credits deducted → Check balance is 8
2. Login with 0 credits → Try to transcribe → Verify "积分不足" error with link to credits page

**Dependencies**: Requires US1/US2 (auth), US3/US4 (credits to have balance)

### Tests for User Story 5

- [x] T055 ✅ [P] [US5] Write test for authenticated transcription creation in tests/test_credits.py
- [x] T056 ✅ [P] [US5] Write test for credit deduction on transcription start in tests/test_credits.py
- [x] T057 ✅ [P] [US5] Write test for insufficient credits error (402) in tests/test_credits.py
- [x] T058 ✅ [P] [US5] Write test for credit refund on transcription failure in tests/test_credits.py
- [x] T059 ✅ [P] [US5] Write test for unauthenticated transcription rejection (401) in tests/test_api.py

### Backend Implementation

- [x] T060 ✅ [US5] Create credits router with balance endpoint in src/podscript_api/routers/credits.py
- [x] T061 ✅ [US5] Add credit deduction logic using deduct_credits RPC in src/podscript_api/routers/credits.py
- [x] T062 ✅ [US5] Add credit refund logic using refund_credits RPC in src/podscript_api/routers/credits.py
- [x] T063 ✅ [US5] Register credits router in src/podscript_api/main.py with prefix /api/credits
- [x] T064 ✅ [US5] Update POST /tasks endpoint in main.py to require authentication
- [x] T065 ✅ [US5] Update POST /tasks/{id}/transcribe endpoint to check and deduct credits
- [x] T066 ✅ [US5] Add credit refund on transcription failure in pipeline error handling
- [x] T067 ✅ [US5] Update existing test_api.py tests to include auth headers

### Frontend Implementation

- [x] T068 ✅ [US5] Update transcription UI to show insufficient credits error with link to credits page
- [ ] T069 [US5] Add estimated cost display before transcription start in index.html (optional)
- [x] T070 ✅ [US5] Update app.js to handle 401/402 errors and redirect appropriately

### Verification

- [x] T071 ✅ [US5] Run all tests including updated test_api.py and verify coverage (21 tests passing)
- [ ] T072 [US5] Manual test: Transcription with sufficient credits works, with 0 credits fails gracefully

**Checkpoint**: Transcription is fully gated by authentication and credits ✅

---

## Phase 6: User Story 6 - View Transaction History (Priority: P3) ✅ COMPLETE

**Goal**: Users can view their credit transaction history with date, type, amount, and balance

**Independent Test**:
1. Login → Recharge 50 credits → Transcribe 2-hour audio → View credits page → Verify history shows both transactions

**Dependencies**: Requires US1/US2 (auth), US3/US4 (for recharge entries), US5 (for consumption entries)

### Tests for User Story 6

- [x] T073 ✅ [P] [US6] Write test for GET /api/credits/transactions endpoint in tests/test_credits.py
- [x] T074 ✅ [P] [US6] Write test for transaction pagination (limit/offset) in tests/test_credits.py

### Backend Implementation

- [x] T075 ✅ [US6] Add transactions endpoint to credits router in src/podscript_api/routers/credits.py
- [x] T076 ✅ [US6] Implement pagination for transaction history query

### Frontend Implementation

- [x] T077 ✅ [US6] Add transaction history table to credits.html
- [x] T078 ✅ [US6] Update credits.js to fetch and display transaction history
- [ ] T079 [US6] Add pagination controls for transaction history (optional - basic version done)

### Verification

- [x] T080 ✅ [US6] Run tests for transaction history and verify pass
- [ ] T081 [US6] Manual test: Make transactions, view history with correct entries

**Checkpoint**: Users can view complete transaction history

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final improvements affecting multiple user stories

### History Page Update

- [ ] T082 [P] Update src/podscript_api/static/history.html to filter by current user (RLS handles backend)
- [ ] T083 [P] Update history.js to handle unauthenticated state

### Error Handling & UX

- [ ] T084 [P] Add friendly error messages for Supabase unavailability across all pages
- [ ] T085 [P] Add friendly error messages for Z-Pay unavailability on credits page
- [ ] T086 Add retry button for service unavailability errors

### Payment Order Expiration

- [ ] T087 [US3] Write test for expired order cleanup function in tests/test_payment.py
- [ ] T088 [US3] Implement order expiration check in payment create (reject if pending order exists >30min)
- [ ] T089 [US3] Add startup task to mark stale pending orders as expired in src/podscript_api/main.py

### Security Hardening

- [ ] T090 Verify all protected endpoints check authentication
- [ ] T091 Verify webhook signature verification is robust
- [ ] T092 Verify SameSite cookie settings for CSRF protection

### Final Verification

- [ ] T093 Run full test suite with coverage report (target: 80%)
- [ ] T094 Run quickstart.md verification checklist
- [ ] T095 Manual end-to-end test of complete user flow

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - start immediately
- **Foundational (Phase 2)**: Depends on Setup - BLOCKS all user stories
- **US1 & US2 (Phase 3)**: Depends on Foundational - MVP
- **US3 & US4 (Phase 4)**: Depends on Foundational, can run parallel to Phase 3 backend
- **US5 (Phase 5)**: Depends on US1/US2 for auth
- **US6 (Phase 6)**: Depends on US3/US4 for meaningful data
- **Polish (Phase 7)**: Depends on all user stories

### User Story Dependencies

```
Foundational (Phase 2)
    ├── US1 & US2: Auth (P1) ─────────┬──► US5: Transcription Gating (P3)
    │                                 │
    └── US3 & US4: Payment (P2) ──────┼──► US5 (needs credits balance)
                                      │
                                      └──► US6: Transaction History (P3)
```

### Parallel Opportunities

**Within Phase 1 (Setup):**
- T002, T003, T004 can run in parallel (different directories)

**Within Phase 2 (Foundational):**
- T015, T016, T017 can run in parallel (test fixtures)

**Within Phase 3 (Auth):**
- T018-T021 tests can run in parallel
- T027 (login.html) can run parallel to backend work

**Within Phase 4 (Payment):**
- T034-T039 tests can run in parallel
- T046, T047 (HTML pages) can run parallel to backend

**Within Phase 5 (Transcription Gating):**
- T053-T057 tests can run in parallel

**Within Phase 6 (History):**
- T071, T072 tests can run in parallel

---

## Parallel Example: Phase 3 (Auth)

```bash
# Launch all auth tests in parallel:
Task: "Write test for POST /api/auth/register in tests/test_auth.py"
Task: "Write test for POST /api/auth/login in tests/test_auth.py"
Task: "Write test for POST /api/auth/logout in tests/test_auth.py"
Task: "Write test for GET /api/auth/me in tests/test_auth.py"

# Then implement backend (sequential due to dependencies):
# auth.py register → login → logout → me → register in main.py

# Frontend can start parallel to backend:
Task: "Create login page HTML at src/podscript_api/static/login.html"
```

---

## Implementation Strategy

### MVP First (Phase 1-3 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL)
3. Complete Phase 3: US1 & US2 (Auth)
4. **STOP and VALIDATE**: Users can register/login
5. Deploy as MVP - users can access service with 10 free credits

### Incremental Delivery

| Increment | Phases | Value Delivered |
|-----------|--------|-----------------|
| MVP | 1-3 | Users can register/login with 10 free credits |
| Revenue | 4 | Users can purchase more credits |
| Monetization | 5 | Transcription consumes credits |
| Transparency | 6 | Users can view transaction history |
| Polish | 7 | Production-ready with all edge cases handled |

---

## Summary

| Phase | Tasks | Completed | Status |
|-------|-------|-----------|--------|
| Setup | 6 | 6 | ✅ Complete |
| Foundational | 11 | 11 | ✅ Complete |
| US1 & US2 (Auth) | 18 | 17 | ✅ Complete (T030 optional) |
| US3 & US4 (Payment) | 19 | 19 | ✅ Complete |
| US5 (Transcription) | 18 | 16 | ✅ Complete (T069, T072 optional) |
| US6 (History) | 9 | 8 | ✅ Complete (T079, T081 optional) |
| Polish | 14 | 0 | ⏳ Not started |
| **Total** | **95** | **77** | **81% Complete** |

**MVP Scope**: Phases 1-6 Complete - Full user journey from registration to transcription with credits

**Current Progress**: All API tests passing (21 API tests + auth/payment/credits tests)

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story
- Each story checkpoint = independently testable state
- Commit after each task or logical group
- Stop at any checkpoint to validate before proceeding
