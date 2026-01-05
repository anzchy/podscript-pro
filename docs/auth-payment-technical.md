# 认证与支付技术文档

本文档详细介绍 Podscript 的用户认证系统和支付集成的技术实现细节。

## 目录

1. [架构概览](#架构概览)
2. [用户认证](#用户认证)
3. [积分系统](#积分系统)
4. [支付集成](#支付集成)
5. [API 参考](#api-参考)
6. [安全考虑](#安全考虑)
7. [故障排查](#故障排查)

---

## 架构概览

### 技术栈

| 组件 | 技术选型 | 用途 |
|------|----------|------|
| 认证后端 | Supabase Auth | 用户注册、登录、会话管理 |
| 数据库 | Supabase PostgreSQL | 用户积分、交易记录、支付订单 |
| JWT 验证 | PyJWT | 服务端 token 验证 |
| 支付网关 | Z-Pay | 支付宝/微信支付聚合 |
| Cookie 管理 | httponly cookie | 安全的会话存储 |

### 数据流

```
┌─────────────────────────────────────────────────────────────────┐
│                        用户认证流程                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  用户 ──► 登录表单 ──► /api/auth/login ──► Supabase Auth       │
│                              │                                   │
│                              ▼                                   │
│                   Set-Cookie: access_token (httponly)           │
│                              │                                   │
│                              ▼                                   │
│  后续请求 ──► Cookie ──► JWT 验证中间件 ──► 受保护的端点         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                        支付回调流程                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  用户 ──► 创建订单 ──► 跳转 Z-Pay ──► 完成支付                   │
│                                           │                     │
│                                           ▼                     │
│                          Z-Pay Webhook ──► /api/payment/webhook │
│                                           │                     │
│                                           ▼                     │
│                               验证签名 + 添加积分                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 用户认证

### Supabase 客户端配置

**文件**: `src/podscript_shared/supabase.py`

```python
from supabase import create_client, Client

def get_supabase_client() -> Optional[Client]:
    """获取 Supabase 客户端实例（使用 anon key）"""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_ANON_KEY")
    if not url or not key:
        return None
    return create_client(url, key)

def get_supabase_admin_client() -> Optional[Client]:
    """获取 Supabase 管理员客户端（使用 service role key）"""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        return None
    return create_client(url, key)
```

### JWT 验证中间件

**文件**: `src/podscript_api/middleware/auth.py`

```python
import jwt
from fastapi import Depends, HTTPException, Request
from pydantic import BaseModel

class CurrentUser(BaseModel):
    id: str
    email: str

async def get_current_user(request: Request) -> CurrentUser:
    """从请求 Cookie 中提取并验证 JWT token"""
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    jwt_secret = os.getenv("SUPABASE_JWT_SECRET")
    try:
        payload = jwt.decode(
            token,
            jwt_secret,
            algorithms=["HS256"],
            audience="authenticated"
        )
        return CurrentUser(
            id=payload.get("sub"),
            email=payload.get("email")
        )
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_current_user_optional(request: Request) -> Optional[CurrentUser]:
    """可选的用户验证，未登录返回 None"""
    try:
        return await get_current_user(request)
    except HTTPException:
        return None
```

### 认证端点

**文件**: `src/podscript_api/routers/auth.py`

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/auth/register` | POST | 用户注册，自动赠送 10 积分 |
| `/api/auth/login` | POST | 用户登录，设置 httponly cookie |
| `/api/auth/logout` | POST | 用户登出，清除 cookie |
| `/api/auth/me` | GET | 获取当前用户信息和积分 |

#### 注册流程

```python
@router.post("/register", response_model=AuthResponse)
async def register(request: AuthRequest, response: Response):
    supabase = get_supabase_client()

    # 1. 通过 Supabase Auth 创建用户
    auth_response = supabase.auth.sign_up({
        "email": request.email,
        "password": request.password,
    })

    # 2. 初始化用户积分（10 积分）
    admin = get_supabase_admin_client()
    admin.table("users_credits").insert({
        "user_id": auth_response.user.id,
        "balance": 10,
    }).execute()

    # 3. 记录赠送积分交易
    admin.table("credit_transactions").insert({
        "user_id": auth_response.user.id,
        "amount": 10,
        "type": "bonus",
        "description": "注册赠送积分",
    }).execute()

    # 4. 设置 Cookie
    response.set_cookie(
        key="access_token",
        value=auth_response.session.access_token,
        httponly=True,
        samesite="lax",
        max_age=3600 * 24 * 7,  # 7 天
    )

    return AuthResponse(user_id=..., email=..., credits=10)
```

#### Cookie 配置

| 属性 | 值 | 说明 |
|------|-----|------|
| `httponly` | `True` | 防止 XSS 攻击读取 token |
| `samesite` | `lax` | 防止 CSRF 攻击 |
| `secure` | `True` (生产环境) | 仅 HTTPS 传输 |
| `max_age` | 604800 (7天) | Cookie 有效期 |

---

## 积分系统

### 数据模型

```sql
-- 用户积分表
CREATE TABLE users_credits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id),
    balance INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(user_id)
);

-- 积分交易记录表
CREATE TABLE credit_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id),
    amount INTEGER NOT NULL,
    type VARCHAR(20) NOT NULL,  -- 'bonus', 'purchase', 'consume', 'refund'
    description TEXT,
    reference_id VARCHAR(100),   -- 关联的订单ID或任务ID
    created_at TIMESTAMPTZ DEFAULT now()
);
```

### 积分操作

**文件**: `src/podscript_api/routers/credits.py`

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/credits/balance` | GET | 获取当前积分余额 |
| `/api/credits/transactions` | GET | 获取交易历史（分页） |

#### 积分扣除逻辑

转写时按音频时长扣除积分：

```python
# 扣费规则：1 积分 = 1 小时音频
credits_required = math.ceil(audio_duration_hours)

# 检查余额
if user_balance < credits_required:
    raise HTTPException(status_code=402, detail="积分不足")

# 扣除积分
admin.table("users_credits").update({
    "balance": user_balance - credits_required
}).eq("user_id", user_id).execute()

# 记录交易
admin.table("credit_transactions").insert({
    "user_id": user_id,
    "amount": -credits_required,
    "type": "consume",
    "description": f"转写任务扣费",
    "reference_id": task_id,
}).execute()
```

---

## 支付集成

### Z-Pay 配置

| 环境变量 | 说明 |
|----------|------|
| `ZPAY_PID` | 商户 ID |
| `ZPAY_KEY` | 签名密钥 |
| `ZPAY_NOTIFY_URL` | 异步回调地址 |
| `ZPAY_RETURN_URL` | 支付成功跳转地址 |

### 支付流程

```
1. 用户选择充值金额
       │
       ▼
2. POST /api/payment/create
   - 创建 payment_orders 记录
   - 生成 MD5 签名
   - 返回 Z-Pay 支付页面 URL
       │
       ▼
3. 用户跳转至 Z-Pay 完成支付
       │
       ▼
4. Z-Pay 回调 POST /api/payment/webhook
   - 验证 MD5 签名
   - 检查订单状态
   - 添加积分到用户账户
   - 返回 "success"
```

### 签名验证

**文件**: `src/podscript_api/routers/payment.py`

```python
def verify_zpay_signature(params: dict, key: str) -> bool:
    """验证 Z-Pay 回调签名"""
    # 1. 过滤空值和签名字段
    filtered = {k: v for k, v in params.items()
                if v and k not in ["sign", "sign_type"]}

    # 2. 按 key 排序拼接
    sorted_str = "&".join(f"{k}={filtered[k]}"
                          for k in sorted(filtered.keys()))

    # 3. 追加密钥并 MD5
    sign_str = sorted_str + key
    expected_sign = hashlib.md5(sign_str.encode()).hexdigest()

    # 4. 比对签名
    return params.get("sign", "").lower() == expected_sign.lower()
```

### Webhook 处理

```python
@router.post("/webhook")
async def payment_webhook(request: Request):
    form_data = await request.form()
    params = dict(form_data)

    # 1. 验证签名
    if not verify_zpay_signature(params, ZPAY_KEY):
        payment_logger.warning("Invalid signature", extra={"params": params})
        return Response(content="fail", media_type="text/plain")

    # 2. 检查订单状态
    if params.get("trade_status") != "TRADE_SUCCESS":
        return Response(content="success", media_type="text/plain")

    # 3. 查询订单
    order_id = params.get("out_trade_no")
    admin = get_supabase_admin_client()
    order = admin.table("payment_orders").select("*").eq("id", order_id).single().execute()

    if order.data["status"] == "paid":
        return Response(content="success", media_type="text/plain")  # 幂等处理

    # 4. 更新订单状态
    admin.table("payment_orders").update({
        "status": "paid",
        "paid_at": datetime.utcnow().isoformat(),
    }).eq("id", order_id).execute()

    # 5. 添加积分
    credits = int(float(params.get("money", 0)))  # 1元 = 1积分
    admin.rpc("add_user_credits", {
        "p_user_id": order.data["user_id"],
        "p_amount": credits,
        "p_type": "purchase",
        "p_description": f"充值 {credits} 积分",
        "p_reference_id": order_id,
    }).execute()

    payment_logger.info("Payment processed", extra={
        "order_id": order_id,
        "amount": credits,
        "user_id": order.data["user_id"],
    })

    return Response(content="success", media_type="text/plain")
```

### 支付日志

**文件**: `src/podscript_shared/logging.py`

支付相关操作使用结构化 JSON 日志记录，保存在 `logs/payment.log`：

```python
import logging
from pythonjsonlogger import jsonlogger

def get_payment_logger() -> logging.Logger:
    logger = logging.getLogger("payment")
    handler = logging.FileHandler("logs/payment.log")
    formatter = jsonlogger.JsonFormatter(
        fmt="%(asctime)s %(levelname)s %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger
```

日志示例：

```json
{"asctime": "2024-01-15 10:30:45", "levelname": "INFO", "message": "Payment processed", "order_id": "abc123", "amount": 50, "user_id": "user-uuid"}
{"asctime": "2024-01-15 10:31:00", "levelname": "WARNING", "message": "Invalid signature", "params": {...}}
```

---

## API 参考

### 认证 API

#### POST /api/auth/register

注册新用户。

**请求体**:
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**响应** (200):
```json
{
  "user_id": "uuid",
  "email": "user@example.com",
  "credits": 10
}
```

**错误**:
- `400`: 用户已存在 / 密码太弱

---

#### POST /api/auth/login

用户登录。

**请求体**:
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**响应** (200):
```json
{
  "user_id": "uuid",
  "email": "user@example.com",
  "credits": 50
}
```

**Cookie 设置**: `access_token=<jwt>; HttpOnly; SameSite=Lax`

**错误**:
- `401`: 邮箱或密码错误

---

#### POST /api/auth/logout

用户登出。

**响应** (200):
```json
{
  "message": "Logged out successfully"
}
```

**Cookie 操作**: 清除 `access_token`

---

#### GET /api/auth/me

获取当前用户信息。

**请求头**: Cookie: `access_token=<jwt>`

**响应** (200):
```json
{
  "user_id": "uuid",
  "email": "user@example.com",
  "credits": 50
}
```

**错误**:
- `401`: 未登录 / token 无效

---

### 积分 API

#### GET /api/credits/balance

获取当前积分余额。

**请求头**: Cookie: `access_token=<jwt>`

**响应** (200):
```json
{
  "balance": 50
}
```

---

#### GET /api/credits/transactions

获取交易历史。

**查询参数**:
- `page`: 页码 (默认 1)
- `limit`: 每页数量 (默认 20)

**响应** (200):
```json
{
  "transactions": [
    {
      "id": "uuid",
      "amount": 10,
      "type": "bonus",
      "description": "注册赠送积分",
      "created_at": "2024-01-15T10:00:00Z"
    }
  ],
  "total": 5,
  "page": 1,
  "limit": 20
}
```

---

### 支付 API

#### POST /api/payment/create

创建支付订单。

**请求体**:
```json
{
  "amount": 50,
  "pay_type": "alipay"
}
```

**响应** (200):
```json
{
  "order_id": "uuid",
  "payment_url": "https://z-pay.cn/submit.php?..."
}
```

---

#### POST /api/payment/webhook

Z-Pay 异步回调（仅 Z-Pay 调用）。

**表单参数**: Z-Pay 标准回调参数

**响应**: `success` 或 `fail`

---

## 安全考虑

### Token 安全

1. **httponly Cookie**: 防止 XSS 攻击读取 token
2. **SameSite=Lax**: 防止 CSRF 攻击
3. **Secure 标志**: 生产环境强制 HTTPS
4. **JWT 验证**: 使用 `audience` 验证防止 token 混用

### 支付安全

1. **签名验证**: 所有 webhook 必须验证 MD5 签名
2. **幂等处理**: 相同订单重复回调不会重复加积分
3. **日志审计**: 所有支付操作记录结构化日志
4. **Service Role Key**: webhook 使用管理员权限绕过 RLS

### 数据库安全

1. **RLS 策略**: 所有表启用行级安全
2. **权限隔离**: 用户只能访问自己的数据
3. **Service Role**: 仅服务端使用，不暴露给客户端

---

## 故障排查

### "Invalid token" 错误

1. 检查 `SUPABASE_JWT_SECRET` 是否正确
2. 确认 JWT 使用 `audience="authenticated"` 验证
3. 检查 token 是否过期

### Webhook 不生效

1. 检查 `ZPAY_NOTIFY_URL` 是否可公网访问
2. 查看 `logs/payment.log` 确认是否收到请求
3. 验证签名密钥 `ZPAY_KEY` 是否正确

### 积分未更新

1. 确认 `SUPABASE_SERVICE_ROLE_KEY` 已配置
2. 检查 RLS 策略是否阻止了更新
3. 查看 Supabase Dashboard 的 Database Logs

### Cookie 未设置

1. 确认 CORS 配置允许 credentials
2. 检查响应头是否包含 `Set-Cookie`
3. 开发环境可能需要 `secure=False`
