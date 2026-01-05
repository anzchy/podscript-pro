# 测试指南: Supabase Auth + Z-Pay Payment Integration

## 前置条件

- Python 3.10-3.12
- 虚拟环境已激活
- Supabase 配置已完成 (.env)

## 第一步: 数据库设置

### 1.1 运行数据库迁移

1. 打开 Supabase SQL Editor: https://supabase.jackcheng.tech
2. 复制并执行 `specs/003-add-supabase-and-payment/migration.sql`
3. 验证表已创建:

```sql
-- 检查表
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;

-- 预期结果:
-- credit_transactions
-- payment_orders
-- users_credits
```

4. 验证函数已创建:

```sql
SELECT proname FROM pg_proc
WHERE proname IN ('handle_new_user', 'add_credits', 'deduct_credits', 'refund_credits');

-- 预期结果: 4 rows
```

5. 验证触发器已创建:

```sql
SELECT trigger_name FROM information_schema.triggers
WHERE trigger_name = 'on_auth_user_created';

-- 预期结果: on_auth_user_created
```

---

## 第二步: 启动服务器

```bash
# 激活虚拟环境
source .venv/bin/activate

# 启动 API 服务器
PYTHONPATH=./src uvicorn podscript_api.main:app --port 8001 --reload
```

服务器启动后访问: http://localhost:8001

---

## 第三步: 测试用户认证 (无需 Z-Pay)

### 3.1 测试用户注册

1. 访问 http://localhost:8001/login
2. 点击 "注册" 标签
3. 填写表单:
   - 邮箱: `test@example.com`
   - 密码: `TestPassword123!`
4. 点击 "注册" 按钮

**预期结果:**
- 页面跳转到首页
- 右上角显示用户邮箱和 "10 积分"
- 数据库中创建了 `users_credits` 记录 (10 积分)
- 数据库中创建了 `credit_transactions` 记录 (bonus, +10)

**数据库验证:**
```sql
-- 查看用户积分
SELECT u.email, c.balance
FROM auth.users u
JOIN public.users_credits c ON u.id = c.id;

-- 查看交易记录
SELECT type, amount, balance_after, description
FROM public.credit_transactions
ORDER BY created_at DESC LIMIT 5;
```

### 3.2 测试用户登出

1. 点击右上角 "登出" 按钮

**预期结果:**
- 页面跳转到首页
- 右上角显示 "登录/注册" 链接
- Cookie 被清除

### 3.3 测试用户登录

1. 访问 http://localhost:8001/login
2. 填写之前注册的账号:
   - 邮箱: `test@example.com`
   - 密码: `TestPassword123!`
3. 点击 "登录" 按钮

**预期结果:**
- 页面跳转到首页
- 右上角显示用户邮箱和积分
- Session cookie 被设置

### 3.4 测试查看用户信息 (API)

```bash
# 获取 cookie (从浏览器开发者工具复制)
curl -X GET "http://localhost:8001/api/auth/me" \
  -H "Cookie: access_token=YOUR_TOKEN_HERE"
```

**预期返回:**
```json
{
  "user_id": "uuid-here",
  "email": "test@example.com",
  "balance": 10
}
```

---

## 第四步: 测试积分系统 (无需 Z-Pay)

### 4.1 测试获取积分余额

```bash
curl -X GET "http://localhost:8001/api/credits/balance" \
  -H "Cookie: access_token=YOUR_TOKEN_HERE"
```

**预期返回:**
```json
{
  "balance": 10
}
```

### 4.2 测试获取交易历史

```bash
curl -X GET "http://localhost:8001/api/credits/transactions" \
  -H "Cookie: access_token=YOUR_TOKEN_HERE"
```

**预期返回:**
```json
{
  "transactions": [
    {
      "id": "uuid",
      "type": "bonus",
      "amount": 10,
      "balance_after": 10,
      "description": "新用户注册奖励",
      "created_at": "2026-01-05T..."
    }
  ],
  "total": 1,
  "page": 1,
  "limit": 20
}
```

### 4.3 测试积分页面 UI

1. 登录后访问 http://localhost:8001/static/credits.html
2. 检查页面显示:
   - 当前积分余额
   - 充值选项 (10元/50元/100元/自定义)
   - 交易历史表格

**预期结果:**
- 显示 "当前积分: 10"
- 显示注册奖励的交易记录

---

## 第五步: 测试积分控制转写

### 5.1 测试未登录时创建任务

```bash
curl -X POST "http://localhost:8001/tasks" \
  -H "Content-Type: application/json" \
  -d '{"source_url": "https://example.com/audio.mp3"}'
```

**预期返回:** HTTP 401
```json
{
  "detail": "未登录或登录已过期"
}
```

### 5.2 测试登录后创建任务

```bash
curl -X POST "http://localhost:8001/tasks" \
  -H "Content-Type: application/json" \
  -H "Cookie: access_token=YOUR_TOKEN_HERE" \
  -d '{"source_url": "https://example.com/audio.mp3"}'
```

**预期返回:** HTTP 200
```json
{
  "id": "task-id",
  "status": "queued",
  ...
}
```

### 5.3 测试积分不足时转写

假设用户积分为 0:

```sql
-- 在 Supabase 中将积分设为 0
UPDATE public.users_credits SET balance = 0 WHERE id = 'your-user-id';
```

然后尝试转写:

```bash
curl -X POST "http://localhost:8001/tasks/TASK_ID/transcribe" \
  -H "Cookie: access_token=YOUR_TOKEN_HERE"
```

**预期返回:** HTTP 402
```json
{
  "detail": "积分不足，请先充值"
}
```

### 5.4 测试积分充足时转写

```sql
-- 恢复积分
UPDATE public.users_credits SET balance = 10 WHERE id = 'your-user-id';
```

转写时会扣除积分 (1 积分/小时，向上取整，最少 1 积分)

---

## 第六步: 测试 401/402 错误处理 (前端)

### 6.1 测试 401 重定向

1. 在浏览器中访问 http://localhost:8001
2. 清除所有 cookies (或使用无痕模式)
3. 输入一个 URL 并点击 "开始转写"

**预期结果:**
- 跳转到登录页面
- 登录后应该返回原页面

### 6.2 测试 402 积分不足提示

1. 登录账号
2. 在 Supabase 中将积分设为 0
3. 创建任务并点击转写

**预期结果:**
- 显示 "积分不足，点击充值" (带链接)
- 点击链接跳转到积分页面

---

## 第七步: 运行自动化测试

```bash
# 运行所有测试
source .venv/bin/activate
PYTHONPATH=./src pytest tests/ -v --disable-warnings

# 只运行认证测试
PYTHONPATH=./src pytest tests/test_auth.py -v

# 只运行积分测试
PYTHONPATH=./src pytest tests/test_credits.py -v

# 只运行 API 测试
PYTHONPATH=./src pytest tests/test_api.py -v
```

**预期结果:**
- test_auth.py: 14 tests passed
- test_credits.py: 6 tests passed
- test_payment.py: 5 tests passed
- test_api.py: 21 tests passed

---

## 测试检查清单

### 认证功能
- [ ] 用户可以注册新账号
- [ ] 注册后自动获得 10 积分
- [ ] 用户可以登录
- [ ] 用户可以登出
- [ ] 登录状态在刷新后保持
- [ ] 未登录用户无法创建任务 (401)

### 积分功能
- [ ] 可以查看积分余额
- [ ] 可以查看交易历史
- [ ] 积分不足时无法转写 (402)
- [ ] 错误信息包含充值链接

### 前端功能
- [ ] 登录页面正常显示
- [ ] 登录/注册标签切换正常
- [ ] 登录成功后重定向正确
- [ ] 用户信息显示在 header
- [ ] 积分页面正常显示

---

## Z-Pay 测试 (需要配置后)

配置 Z-Pay 后，可以测试:

1. 创建支付订单
2. 支付回调处理
3. 积分充值完成

详见 `quickstart.md` 中的 Z-Pay 配置部分。

---

## 常见问题

### Q: 注册时提示 "邮箱格式错误"
A: 确保使用有效的邮箱格式，如 `user@domain.com`

### Q: 登录后页面不跳转
A: 检查浏览器控制台是否有错误，确保 cookie 设置正确

### Q: 积分不显示
A: 检查 Supabase 数据库中是否有对应的 `users_credits` 记录

### Q: API 返回 503
A: 检查 Supabase 连接配置 (.env 中的 URL 和 Key)

### Q: 触发器不生效
A: 确保运行了完整的 migration.sql，包括触发器创建语句
