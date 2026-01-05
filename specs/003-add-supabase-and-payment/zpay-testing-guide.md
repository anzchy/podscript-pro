# Z-Pay 支付集成测试指南

## 概述

本文档详细说明如何测试 Podscript 的 Z-Pay 支付功能，包括本地模拟测试和生产环境真实支付测试。

## 前置条件

### 1. 环境配置

确保 `.env` 文件中已配置 Z-Pay 参数：

```env
# Z-Pay 配置
ZPAY_PID=你的商户ID
ZPAY_KEY=你的密钥
ZPAY_NOTIFY_URL=https://your-domain.com/api/payment/webhook
ZPAY_RETURN_URL=https://your-domain.com/static/payment-success.html
```

**获取 Z-Pay 配置:**
1. 访问 [Z-Pay 商户后台](https://z-pay.cn)
2. 登录后进入 "商户信息" 页面
3. 复制 PID (商户ID) 和 Key (密钥)

### 2. 数据库准备

确保已运行数据库迁移，`payment_orders` 表已创建：

```sql
-- 在 Supabase SQL Editor 中验证
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public' AND table_name = 'payment_orders';
```

### 3. 启动服务器

```bash
source .venv/bin/activate
PYTHONPATH=./src uvicorn podscript_api.main:app --port 8001 --reload
```

---

## 测试步骤

### 第一步: 登录获取 Cookie

```bash
# 登录获取 access_token cookie
curl -X POST http://localhost:8001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "anzchy@163.com", "password": "5118822470"}' \
  -c cookies.txt -v

# 验证登录状态
curl -X GET http://localhost:8001/api/auth/me \
  -b cookies.txt
```

**预期结果:**
```json
{
  "user_id": "67994731-a29c-404f-80e5-048d792c897b",
  "email": "anzchy@163.com",
  "credit_balance": 10
}
```

---

### 第二步: 创建支付订单

```bash
# 创建 50 元充值订单 (支付宝)
curl -X POST http://localhost:8001/api/payment/create \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{"amount": 50, "pay_type": "alipay"}'

# 创建 100 元充值订单 (微信)
curl -X POST http://localhost:8001/api/payment/create \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{"amount": 100, "pay_type": "wxpay"}'
```

**预期返回:**
```json
{
  "order_id": "uuid-xxx",
  "payment_url": "https://api.z-pay.cn/submit.php?pid=xxx&type=alipay&out_trade_no=PDS..."
}
```

**验证数据库:**
```sql
-- 查看创建的订单
SELECT id, out_trade_no, amount, credits, status, payment_method, created_at
FROM payment_orders
ORDER BY created_at DESC
LIMIT 5;
```

---

### 第三步: 模拟支付回调 (本地测试)

由于本地环境无法接收 Z-Pay 的真实回调，需要手动模拟：

#### 3.1 获取订单信息

```sql
-- 从数据库获取待支付订单的 out_trade_no
SELECT out_trade_no, amount FROM payment_orders
WHERE status = 'pending'
ORDER BY created_at DESC LIMIT 1;
```

#### 3.2 生成签名

使用 Python 生成正确的签名：

```python
import hashlib

# 替换为你的实际值
zpay_key = "你的ZPAY_KEY"
params = {
    "pid": "你的ZPAY_PID",
    "trade_no": "TEST_TRADE_123456",
    "out_trade_no": "PDS1736071234abcd1234",  # 从数据库获取
    "type": "alipay",
    "name": "Podscript Credits x50",
    "money": "50.00",
    "trade_status": "TRADE_SUCCESS",
}

# 生成签名
sorted_params = sorted((k, v) for k, v in params.items() if v)
query_string = "&".join(f"{k}={v}" for k, v in sorted_params)
sign_string = f"{query_string}&key={zpay_key}"
sign = hashlib.md5(sign_string.encode()).hexdigest().lower()
print(f"sign={sign}")
```

#### 3.3 发送模拟回调

```bash
# 替换 out_trade_no 和 sign 为实际值
curl -X POST http://localhost:8001/api/payment/webhook \
  -d "pid=YOUR_PID&trade_no=TEST_TRADE_123456&out_trade_no=PDS1736071234abcd1234&type=alipay&name=Podscript%20Credits%20x50&money=50.00&trade_status=TRADE_SUCCESS&sign=YOUR_GENERATED_SIGN"
```

**预期返回:**
```
success
```

#### 3.4 验证结果

```sql
-- 验证订单状态已更新
SELECT id, status, paid_at, trade_no FROM payment_orders
WHERE out_trade_no = 'PDS1736071234abcd1234';
-- 预期: status = 'paid', paid_at 有值

-- 验证积分已增加
SELECT balance FROM users_credits
WHERE id = '67994731-a29c-404f-80e5-048d792c897b';
-- 预期: balance 增加了 50

-- 验证交易记录
SELECT type, amount, balance_after, description FROM credit_transactions
WHERE user_id = '67994731-a29c-404f-80e5-048d792c897b'
ORDER BY created_at DESC LIMIT 1;
-- 预期: type='recharge', amount=50, description='充值 50 积分'
```

---

### 第四步: 查询订单状态

```bash
# 查询订单详情 (替换 ORDER_ID)
curl -X GET http://localhost:8001/api/payment/orders/YOUR_ORDER_ID \
  -b cookies.txt
```

**预期返回:**
```json
{
  "id": "uuid-xxx",
  "amount": 50,
  "credits": 50,
  "status": "paid",
  "created_at": "2026-01-05T08:30:00.000Z",
  "paid_at": "2026-01-05T08:31:00.000Z"
}
```

---

### 第五步: 前端 UI 测试

#### 5.1 测试积分页面

1. 访问 http://localhost:8001/static/credits.html
2. 确保已登录状态
3. 检查显示内容:
   - 当前积分余额
   - 预设金额按钮 (10/50/100 元)
   - 自定义金额输入框 (1-500 元)
   - 支付方式选择 (支付宝/微信)
   - 交易历史记录

#### 5.2 测试充值流程

1. 选择金额 (如 50 元)
2. 选择支付方式 (如 支付宝)
3. 点击 "立即支付"
4. 应跳转到 Z-Pay 支付页面

#### 5.3 测试支付成功页面

1. 访问 http://localhost:8001/static/payment-success.html
2. 应显示当前积分余额
3. 有 "开始转写" 和 "继续充值" 按钮

---

## 生产环境测试

### 1. 配置 Webhook URL

在 Z-Pay 商户后台配置:
- **异步通知地址**: `https://your-domain.com/api/payment/webhook`
- **同步跳转地址**: `https://your-domain.com/static/payment-success.html`

### 2. 真实支付测试

1. 使用小额 (1 元) 进行真实支付测试
2. 完成支付后等待约 3-5 秒
3. 检查积分是否正确增加
4. 检查交易记录是否正确

### 3. 验证签名安全

```bash
# 尝试发送错误签名的回调 (应该失败)
curl -X POST https://your-domain.com/api/payment/webhook \
  -d "pid=YOUR_PID&trade_no=FAKE&out_trade_no=FAKE&trade_status=TRADE_SUCCESS&sign=invalid_sign"

# 预期返回: fail
```

---

## 错误场景测试

### 1. 未登录时创建订单

```bash
curl -X POST http://localhost:8001/api/payment/create \
  -H "Content-Type: application/json" \
  -d '{"amount": 50, "pay_type": "alipay"}'
```

**预期:** HTTP 401

### 2. 无效金额

```bash
# 金额为 0
curl -X POST http://localhost:8001/api/payment/create \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{"amount": 0, "pay_type": "alipay"}'

# 金额超过 500
curl -X POST http://localhost:8001/api/payment/create \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{"amount": 1000, "pay_type": "alipay"}'
```

**预期:** HTTP 422 (验证错误)

### 3. 无效支付方式

```bash
curl -X POST http://localhost:8001/api/payment/create \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{"amount": 50, "pay_type": "bitcoin"}'
```

**预期:** HTTP 422 或正常处理 (Z-Pay 会拒绝无效类型)

### 4. 重复回调 (幂等性测试)

```bash
# 发送相同的回调两次
curl -X POST http://localhost:8001/api/payment/webhook \
  -d "pid=YOUR_PID&trade_no=TEST_123&out_trade_no=PDS...&trade_status=TRADE_SUCCESS&sign=..."

curl -X POST http://localhost:8001/api/payment/webhook \
  -d "pid=YOUR_PID&trade_no=TEST_123&out_trade_no=PDS...&trade_status=TRADE_SUCCESS&sign=..."
```

**预期:** 两次都返回 `success`，但积分只增加一次

---

## 测试检查清单

### API 测试
- [ ] 创建支付订单成功
- [ ] 返回正确的 payment_url
- [ ] 订单写入数据库
- [ ] Webhook 签名验证正确
- [ ] Webhook 更新订单状态
- [ ] Webhook 增加用户积分
- [ ] Webhook 记录交易日志
- [ ] 重复回调不会重复增加积分
- [ ] 查询订单接口正常

### 前端测试
- [ ] 积分页面正确显示余额
- [ ] 预设金额按钮工作正常
- [ ] 自定义金额输入验证
- [ ] 支付方式切换正常
- [ ] 点击支付跳转正确
- [ ] 交易历史显示正确
- [ ] 支付成功页面显示正确

### 安全测试
- [ ] 未登录无法创建订单
- [ ] 无效签名的回调被拒绝
- [ ] 金额范围验证生效
- [ ] 订单只能被所属用户查询

---

## 常见问题

### Q: Webhook 返回 "fail"
**检查:**
1. ZPAY_KEY 是否正确
2. 签名生成算法是否正确
3. 查看服务器日志中的错误信息

### Q: 积分没有增加
**检查:**
1. Webhook 是否被调用 (查看服务器日志)
2. 订单状态是否为 "pending"
3. users_credits 表中是否存在用户记录

### Q: payment_url 无法访问
**检查:**
1. ZPAY_PID 是否正确
2. Z-Pay 商户账户是否正常
3. 签名是否正确生成

### Q: 本地测试 Webhook
本地开发环境无法接收外部回调，有两种解决方案:
1. 手动模拟回调 (本文档方法)
2. 使用 ngrok 暴露本地端口: `ngrok http 8001`

---

## 日志查看

```bash
# 查看支付相关日志
tail -f logs/payment.log

# 查看服务器日志
# 日志会显示在 uvicorn 终端
```

---

## 附录: Z-Pay API 参数说明

### 创建订单参数
| 参数 | 说明 | 示例 |
|------|------|------|
| pid | 商户ID | 1001 |
| type | 支付类型 | alipay/wxpay |
| out_trade_no | 商户订单号 | PDS1736071234xxx |
| notify_url | 异步通知地址 | https://... |
| return_url | 同步跳转地址 | https://... |
| name | 商品名称 | Podscript Credits x50 |
| money | 金额 | 50.00 |
| sign | 签名 | md5(...) |
| sign_type | 签名类型 | MD5 |

### 回调参数
| 参数 | 说明 | 示例 |
|------|------|------|
| pid | 商户ID | 1001 |
| trade_no | Z-Pay 交易号 | ZP202601051234 |
| out_trade_no | 商户订单号 | PDS1736071234xxx |
| type | 支付类型 | alipay |
| name | 商品名称 | Podscript Credits x50 |
| money | 金额 | 50.00 |
| trade_status | 交易状态 | TRADE_SUCCESS |
| sign | 签名 | md5(...) |
