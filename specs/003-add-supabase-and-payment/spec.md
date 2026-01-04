# Feature Specification: Supabase Auth + Z-Pay Payment Integration

**Feature Branch**: `003-add-supabase-and-payment`
**Created**: 2026-01-04
**Status**: Draft
**Input**: User description: "增加登录页面（Supabase Auth）和充值页面（Z-Pay国内支付），支持积分系统。每1元对应1积分，支持充10元、50元、100元以及自定义充值金额。"

## Overview

This feature adds user authentication and a credits payment system to Podscript. Currently, Podscript operates without user accounts - anyone can transcribe audio/video without limits. This feature introduces:

1. **User Authentication**: Login/registration via Supabase Auth, enabling user accounts and data isolation
2. **Credits System**: A virtual currency where 1 CNY = 1 credit, used to pay for transcription services
3. **Payment Integration**: Z-Pay gateway for WeChat Pay and Alipay, supporting preset amounts (10/50/100 CNY) and custom amounts

**Why this is needed**: To monetize the transcription service while providing fair usage limits and premium features for paying users.

## Visual Design

- **User Flow Diagram**: [user-flow.html](./diagrams/user-flow.html) - 用户完整旅程流程图（访问→登录→充值→转写）
- **Wireframe Diagram**: [wireframe.html](./diagrams/wireframe.html) - 界面布局线框图
- **Site Diagram**: [site-diagram.html](./diagrams/site-diagram.html) - 应用架构和数据流图
- **Updated UI Prototype**: [claude-style-ui-v3.html](./claude-style-ui-v3.html) - 包含登录和充值页面的完整UI原型

## Architecture Changes

### Current Architecture (Python + FastAPI)

```
src/
├── podscript_api/         # FastAPI gateway
│   ├── main.py            # API endpoints
│   └── static/            # Frontend UI (vanilla HTML/JS/CSS)
├── podscript_pipeline/    # Processing pipeline
└── podscript_shared/      # Shared utilities
    ├── models.py          # Pydantic models
    └── config.py          # Environment config
```

### Proposed Architecture Updates

```
src/
├── podscript_api/
│   ├── main.py            # Add auth middleware, credits validation
│   ├── routers/
│   │   ├── auth.py        # Login/register/logout endpoints
│   │   ├── payment.py     # Payment creation, webhook
│   │   └── credits.py     # Balance query, transaction history
│   ├── middleware/
│   │   └── auth.py        # JWT validation middleware
│   ├── static/
│   │   ├── login.html     # New: Login/register page
│   │   ├── credits.html   # New: Credits/payment page
│   │   ├── login.js       # New: Auth logic
│   │   └── credits.js     # New: Payment logic
├── podscript_shared/
│   ├── models.py          # Add User, CreditTransaction, PaymentOrder
│   ├── config.py          # Add Supabase, Z-Pay config
│   └── supabase.py        # New: Supabase client wrapper
```

### New Pages to Add

| Page | URL | Purpose |
|------|-----|---------|
| Login | `/static/login.html` | User login and registration |
| Credits | `/static/credits.html` | View balance, purchase credits |
| Payment Success | `/static/payment-success.html` | Post-payment landing page |

### UI Updates to Existing Pages

| Page | Changes |
|------|---------|
| `index.html` | **保持转写界面在首页**：Header 添加用户信息/积分/充值/退出；未登录时显示完整转写界面但控件禁用 + "登录后开始转写"提示；已登录时显示完整转写界面 + 最近转写记录摘要 |
| `result.html` | No changes (already task-based, will work with user's tasks) |
| `history.html` | Filter to show only current user's history (RLS enforced) |

### Page Structure Decision

**方案选择**：合并式首页（方案A）

首页 `/` 同时承载用户信息展示和转写功能，理由：
1. Podscript 是单一用途工具，转写是核心功能
2. 减少用户操作步骤，登录后立即可工作
3. 保持界面简洁，无需复杂仪表盘

**首页布局**：
```
┌─────────────────────────────────────────┐
│ Header: Logo | 积分: 50 | [充值] | [退出] │
├─────────────────────────────────────────┤
│                                         │
│     [URL输入框 / 文件上传区域]            │
│                                         │
│     [开始转写按钮]                        │
│                                         │
├─────────────────────────────────────────┤
│ 最近转写: task1, task2...    [查看全部 →] │
└─────────────────────────────────────────┘
```

## User Scenarios & Testing *(mandatory)*

### User Story 1 - New User Registration (Priority: P1)

A new user visits Podscript, sees they need to login to transcribe, creates an account, and receives initial free credits.

**Why this priority**: Core functionality - without registration, no other features work. First-time user experience sets the tone.

**Independent Test**: Can be tested by visiting the site, clicking "Login", registering a new account, and verifying free credits are received.

**Acceptance Scenarios**:

1. **Given** visitor is on the homepage, **When** they click "登录/注册", **Then** they are taken to the login page with login/register tabs
2. **Given** user is on register tab, **When** they enter email+password and submit, **Then** account is created and user is logged in
3. **Given** user just registered, **When** they view their profile, **Then** they see 10 free credits (initial bonus)
4. **Given** user is logged in, **When** they return to homepage, **Then** the header shows their email and credit balance

---

### User Story 2 - Existing User Login (Priority: P1)

A returning user logs in with their email and password.

**Why this priority**: Equal priority with registration - users must be able to return.

**Independent Test**: Can be tested by logging in with a known test account and verifying session persistence.

**Acceptance Scenarios**:

1. **Given** user is on login page, **When** they enter valid credentials, **Then** they are logged in and redirected to homepage
2. **Given** user enters invalid credentials, **When** they submit, **Then** they see an error message and can retry
3. **Given** user is logged in, **When** they close browser and return later, **Then** session is preserved (using refresh tokens)

---

### User Story 3 - Purchase Credits with Preset Amount (Priority: P2)

A user wants to buy credits using a preset amount (10, 50, or 100 CNY).

**Why this priority**: Revenue-generating feature, but requires auth to work first.

**Independent Test**: Can be tested by selecting a preset amount, completing mock payment, and verifying credits are added.

**Acceptance Scenarios**:

1. **Given** logged-in user is on credits page, **When** they see preset amounts, **Then** options show 10元(10积分), 50元(50积分), 100元(100积分)
2. **Given** user selects "50元", **When** they click "立即支付", **Then** they are redirected to Z-Pay payment page
3. **Given** user completes WeChat/Alipay payment, **When** payment succeeds, **Then** they return to payment-success page with updated balance
4. **Given** payment webhook is received, **When** signature is valid and payment confirmed, **Then** credits are added to user account in database

---

### User Story 4 - Purchase Credits with Custom Amount (Priority: P2)

A user wants to buy a custom amount of credits (e.g., 25 CNY).

**Why this priority**: Same as preset - different UX path for same core functionality.

**Independent Test**: Can be tested by entering custom amount and completing payment flow.

**Acceptance Scenarios**:

1. **Given** user is on credits page, **When** they enter "25" in custom amount field, **Then** they see "25积分" preview
2. **Given** custom amount is less than 1, **When** user tries to pay, **Then** validation error shows "最低充值1元"
3. **Given** custom amount is valid, **When** user clicks pay, **Then** same payment flow as preset amounts

---

### User Story 5 - Credits-Gated Transcription (Priority: P3)

A logged-in user with sufficient credits can start a transcription, which deducts credits.

**Why this priority**: Depends on auth and credits features being complete.

**Independent Test**: Can be tested by uploading audio, starting transcription, and verifying credit deduction.

**Acceptance Scenarios**:

1. **Given** user has 50 credits and uploads 2-hour audio, **When** they click "开始转写", **Then** transcription starts and deducts 2 credits (cost: 1 credit per hour of audio, rounded up)
2. **Given** user has 0 credits, **When** they try to transcribe, **Then** they see "积分不足" error with link to credits page
3. **Given** transcription completes successfully, **When** user checks balance, **Then** appropriate credits were deducted

---

### User Story 6 - View Transaction History (Priority: P3)

A user wants to see their credit transaction history.

**Why this priority**: Nice-to-have for transparency, not blocking core flow.

**Independent Test**: Can be tested by making purchases/transcriptions and viewing history table.

**Acceptance Scenarios**:

1. **Given** user has made transactions, **When** they view credits page, **Then** they see a history table with date, type, amount, balance
2. **Given** user recharges 50 credits, **When** they check history, **Then** entry shows "+50 充值" with new balance
3. **Given** user transcribes a 2-hour audio, **When** they check history, **Then** entry shows "-2 转写消费 (2小时)" with new balance

---

### Edge Cases

- **Payment timeout**: User starts payment but doesn't complete within 30 minutes - order expires, no credits added
- **Duplicate webhook**: Z-Pay sends webhook multiple times - system idempotently handles (only processes once)
- **Concurrent access**: User opens credits page in two tabs, both try to pay - only one order should succeed
- **Session expiry**: User's session expires mid-payment - after login, redirect back to pending order or credits page
- **Insufficient credits mid-transcription**: User starts transcription, but credits depleted (shouldn't happen due to upfront deduction) - handle gracefully
- **Z-Pay unavailable**: Payment gateway down - show friendly error, suggest retry later
- **Supabase unavailable**: Auth/database service down - show friendly error message with retry button, no cached offline operation

## Requirements *(mandatory)*

### Functional Requirements

#### Authentication (FR-1xx)
- **FR-101**: System MUST allow users to register with email and password
- **FR-102**: System MUST allow users to login with email and password
- **FR-103**: System MUST persist user sessions using JWT tokens stored in cookies
- **FR-104**: System MUST validate JWT tokens on protected API endpoints
- **FR-105**: System MUST allow users to logout, clearing their session
- **FR-106**: System MUST grant 10 free credits to new users upon registration
- **FR-107**: System MUST show user's email and credit balance in header when logged in

#### Credits System (FR-2xx)
- **FR-201**: System MUST maintain a credit balance for each user
- **FR-202**: System MUST support credit purchases via Z-Pay (WeChat Pay, Alipay)
- **FR-203**: System MUST convert CNY to credits at 1:1 ratio (1 CNY = 1 credit)
- **FR-204**: System MUST support preset purchase amounts: 10, 50, 100 CNY
- **FR-205**: System MUST support custom purchase amounts (minimum 1 CNY, maximum 500 CNY, integer only)
- **FR-206**: System MUST record all credit transactions (purchases, consumption)
- **FR-207**: System MUST display transaction history to users

#### Payment Integration (FR-3xx)
- **FR-301**: System MUST integrate with Z-Pay payment gateway
- **FR-302**: System MUST generate signed payment URLs per Z-Pay specification
- **FR-303**: System MUST handle Z-Pay webhook callbacks with signature verification
- **FR-304**: System MUST update user credits upon successful payment confirmation
- **FR-305**: System MUST handle payment failures gracefully (no credit update)
- **FR-306**: System MUST handle duplicate webhook notifications idempotently

#### Transcription Gating (FR-4xx)
- **FR-401**: System MUST require user authentication to start transcription
- **FR-402**: System MUST require sufficient credits to start transcription
- **FR-403**: System MUST deduct credits upon transcription start (not completion)
- **FR-404**: System MUST calculate transcription cost as 1 credit per hour (rounded up, minimum 1 credit)
- **FR-405**: System MUST refund deducted credits if transcription fails due to system error (corrupt audio, ASR service failure)

### Key Entities

#### User
- **id**: UUID, from Supabase Auth
- **email**: User's email address
- **credit_balance**: Current credit balance (integer)
- **created_at**: Account creation timestamp

#### CreditTransaction
- **id**: UUID, auto-generated
- **user_id**: Reference to User
- **type**: ENUM (recharge, consumption, bonus)
- **amount**: Integer (positive for additions, negative for deductions)
- **balance_after**: Balance after this transaction
- **description**: Human-readable description
- **related_order_id**: For recharges, link to PaymentOrder
- **related_task_id**: For consumption, link to transcription task
- **created_at**: Transaction timestamp

#### PaymentOrder
- **id**: UUID, auto-generated
- **user_id**: Reference to User
- **out_trade_no**: Unique order number (for Z-Pay)
- **amount**: Payment amount in CNY
- **credits**: Credits to be added
- **status**: ENUM (pending, paid, failed, expired)
- **payment_method**: ENUM (wxpay, alipay)
- **trade_no**: Z-Pay transaction ID (set after payment)
- **created_at**: Order creation timestamp
- **paid_at**: Payment confirmation timestamp

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can complete registration and receive free credits within 1 minute
- **SC-002**: Users can complete a credit purchase (from clicking "pay" to seeing updated balance) within 2 minutes
- **SC-003**: System processes payment webhooks within 5 seconds of receipt
- **SC-004**: System handles 100 concurrent authenticated requests without degradation
- **SC-005**: 95% of payment attempts result in successful credit addition (accounting for user abandonment)
- **SC-006**: Session persistence works across browser restarts (refresh token mechanism)
- **SC-007**: All API endpoints validate authentication in under 50ms overhead

## Technical Considerations

### Supabase Configuration

**Required Tables** (created via Supabase SQL Editor):
1. `users_credits` - Extended user data (credit_balance)
2. `credit_transactions` - Transaction log
3. `payment_orders` - Payment records

**Row Level Security (RLS)**:
- Users can only read/write their own credit data
- Payment webhook uses service role key to bypass RLS

**Environment Variables**:
```
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_ROLE_KEY=eyJ...  # For webhook processing
```

### Z-Pay Configuration

**Endpoints**:
- Payment URL: `https://zpayz.cn/submit.php`
- Query Order: `https://zpayz.cn/api.php?act=order`

**Environment Variables**:
```
ZPAY_PID=your_merchant_id
ZPAY_KEY=your_secret_key
ZPAY_NOTIFY_URL=https://your-domain.com/api/payment/webhook
ZPAY_RETURN_URL=https://your-domain.com/static/payment-success.html
```

**Signature Algorithm**:
1. Sort parameters alphabetically (exclude sign, sign_type)
2. Concatenate as `key1=value1&key2=value2...`
3. Append secret key: `...&key=SECRET_KEY`
4. MD5 hash, lowercase

### Security Considerations

1. **JWT Validation**: Verify token signature, expiry, and audience on every protected request
2. **Webhook Security**: Verify Z-Pay signature before processing any payment notification
3. **CSRF Protection**: Use SameSite cookies and verify origin headers
4. **Amount Validation**: Server-side validation of payment amounts (prevent manipulation)
5. **Idempotency**: Use `out_trade_no` as idempotency key for payment processing
6. **Audit Trail**: Log all credit transactions for dispute resolution

### Observability

1. **Structured Logging**: All payment and credit operations logged with order_id, user_id, timestamp, and operation result
2. **Log Format**: JSON structured logs to file (`logs/payment.log`) for easy parsing
3. **Key Events to Log**: Payment creation, webhook receipt, signature verification result, credit update, refund operations
4. **Error Details**: Failed operations include error type, message, and stack trace for debugging

## Assumptions

1. Users have WeChat or Alipay accounts for payment
2. Z-Pay service is available and reliable (99%+ uptime)
3. Initial free credits (10) provide 10 hours of free transcription - sufficient for users to try the service
4. Pricing model: 1 credit = 1 hour transcription = 1 CNY (cost basis: Tingwu charges ~0.6 CNY/hour, 40% margin)
5. Supabase free tier is sufficient for initial launch
6. Server has stable internet connection for webhook callbacks

## Clarifications

### Session 2026-01-04

- Q: What happens to credits if transcription fails after deduction? → A: Refund credits on failure
- Q: What is the maximum single custom payment amount? → A: 500 CNY
- Q: How should the system support payment debugging? → A: Structured logging with order IDs, timestamps, error details to file
- Q: What should happen if Supabase is temporarily unavailable? → A: Show friendly error message with retry button
- Q: What should unauthenticated users see on homepage? → A: Full interface with disabled controls + "Login to transcribe" prompt

## Out of Scope

- Social login (Google, GitHub) - future enhancement
- Subscription plans - future enhancement
- Refund processing - manual for now
- Credit expiry - credits don't expire
- Multi-currency support - CNY only
- Invoice generation - future enhancement
- Admin dashboard for user management - future enhancement
