# 直播回放：

https://fclive.pandacollege.cn/p/g7BNbP

# 作业

| **作业**                                                     | 学习奖励                                                     |
| ------------------------------------------------------------ | ------------------------------------------------------------ |
| **把具体的功能加入到你的网站上！****加分项：把这个新能力部署到线上** **2.全新"双提交模式"：****群内分享**：请将部署解析后的网页链接，发布在社团群中，让群友流口水！！！**作业问卷提交-：**https://forchangesz.feishu.cn/share/base/form/shrcnM3Jn0dT85LVzprSrHSQRTc以提交在上面的问卷里哦~方便统计发奖励呀~） | **🚩奖励机制：**为了鼓励同学们笔耕不辍，持续学习，AI编程社团特推出《月度学习打卡》小奖励 每月作业完成100%，奖励200次对话工具权益每月的**直播课**都能参加，额外再送100次对话工具荣获某些**AI编程创作挑战赛奖励or商单or其他相关荣誉**等，积极跟【小源助教】报备，可能将会额外获得小小鼓励奖&风变平台的曝光哦！ |
|                                                              |                                                              |
|                                                              |                                                              |
|                                                              |                                                              |
|                                                              |                                                              |
|                                                              |                                                              |
|                                                              |                                                              |

# 教学内容

### 1.我们会先介绍下数据库和Supabase

### 2.如何在上一节课的SeeDream产品的基础上加入登录注册和初始积分领取的功能，大致来说是这么个逻辑：

This content is only supported in a Feishu Docs

在AI时代，0基础建站早已不是什么难事--**AI帮你写代码，GitHub存代码，Vercel免费部署**

全程不用懂复杂技术，鼠标点点就能搞定AI应用开发

但AI应用开发好之后，如果我们想加个登录注册功能以及积分功能，例如，首次登录送100积分，这个该如何实现呢？

登录注册得记录用户账号、密码等信息，积分得记录每个用户有多少分，这些数据都得有个地方安全存储、方便调取，于是我们就需要部署数据库，数据库就是干这个的 “数据管家” 

![img](https://forchangesz.feishu.cn/space/api/box/stream/download/asynccode/?code=MDFjZWJjYjY4Y2E3M2E3ZGMyM2E4YmRiZjY4ZmRkMTdfVFh4MGhSVlpSSEIxN015bHZIN2FSWXhTYUo3bnVHMkFfVG9rZW46TnBONWJxWGxab0thSDF4SjF1emNCY2d5bmdmXzE3NjcxOTI5NTE6MTc2NzE5NjU1MV9WNA)

数据库的选择

- 中小型项目、低成本 → MySQL/PostgreSQL；
- 大型企业、高安全需求 → Oracle；
- **对于新手小白，推荐Supabase**

什么是Supabse?

Supabase是一个开源的，建构于开源PostgreSQL之上的后端即服务（BaaS）平台，旨在替代Firebase等商业化BaaS平台，Supabase整合了多个优秀的开源框架，并基于PostgreSQL进行了深度适配，提供了API化的数据库管理能力、用户管理、身份认证、对象存储服务以及基于PostgreSQL CDC和Websocket的实时通信服务，基于这些平台化基础能力，能够使开发者简化全栈应用开发的流程，帮助开发者快速构建高性能，可扩展的应用程序，同时避免传统开发流程中需要维护复杂后端基础设施的问题。

1. # 对AI提需求

下载github代码到本地

https://github.com/Backtthefuture/seedreamred

![img](https://forchangesz.feishu.cn/space/api/box/stream/download/asynccode/?code=N2QzYzU2MjliMjA3ZjVjNWRkYTQyZGIzYmQ0YjIyYTBfVlNSRzNLSTJ6cFJPbXdPcTdTTEdjTFFqTm1RUGJsTENfVG9rZW46S1htY2IwS0s0b25uSU94cm52YmNlb0hXbnBlXzE3NjcxOTI5NTE6MTc2NzE5NjU1MV9WNA)

没有github账号的话，可以下载下面的文件：

This content is only supported in a Feishu Docs

打开Trae，输入提示词：

> ```Plain
> 请帮我用Supabase在我的项目中实现登录注册功能，登录简化流程即可，注册时只要输入用户名和两次密码，就可以直接注册成功，首次注册时赠送100积分。请包含注册、登录验证、积分更新和保存的完整代码示例，使用JavaScript/TypeScript
> ```

提示词我是让AI先给我写一遍，然后我再加了简化注册流程的话。如果你不知道该怎么写提示词的话，就把你的要求一股脑给AI，让AI给你理一遍。

![img](https://forchangesz.feishu.cn/space/api/box/stream/download/asynccode/?code=ODlmYTA2MjEyOWJlMDk5NjI3ZDg1MTk0MDk5YTJiZDhfZWxxZDU2cWY1bzdheFI3RnVxUUlPMkRrWjIwbThPNEhfVG9rZW46TFBzdGJqT01Ib3doNVh4TGtWS2NZOHZubmZnXzE3NjcxOTI5NTE6MTc2NzE5NjU1MV9WNA)

点了一次继续，Trae完成了整个开发工作：

```Markdown
## 🎉 Supabase 认证功能集成完成！
我已经成功为你的小红书文案生成器应用集成了完整的 Supabase 认证功能。以下是实现的功能总结：

### ✅ 已完成的功能
1.🔧 Supabase 配置
   
   - 安装并配置了 Supabase 客户端
   - 创建了环境变量配置文件
   - 添加了配置检查和错误处理
2.👤 用户认证系统
   
   - 用户注册功能（用户名 + 密码）
   - 用户登录功能
   - 用户登出功能
   - 认证状态管理
3.💰 积分管理系统
   
   - 注册赠送 100 积分
   - 积分消费功能
   - 积分更新功能
   - 积分显示组件
4.🎨 UI 组件
   
   - 登录表单组件
   - 注册表单组件
   - 认证模态框
   - 积分显示组件
   - 用户菜单（登录/登出）
5.📊 状态管理
   
   - 使用 Zustand 管理认证状态
   - 集成到现有的应用状态管理
   - 自动会话恢复
### 🚀 如何使用
1.配置 Supabase ：
   
   - 访问 Supabase 创建项目
   - 在 .env 文件中配置你的项目 URL 和 API Key
   - 在 Supabase 项目中执行 supabase-init.sql 脚本
2.测试功能 ：
   
   - 应用已在 http://localhost:5175/ 运行
   - 点击右上角的"登录/注册"按钮
   - 测试注册和登录流程
   - 查看积分显示和管理
### 📁 创建的文件
- src/config/supabase.ts - Supabase 配置
- src/services/authService.ts - 认证服务
- src/stores/useAuthStore.ts - 认证状态管理
- src/components/Auth/ - 认证相关组件
- .env.example - 环境变量示例
- supabase-init.sql - 数据库初始化脚本
- AUTH_SETUP.md - 详细配置指南
### 🔒 安全特性
- 行级安全策略（RLS）
- 密码加密
- JWT 令牌管理
- 输入验证
- 错误处理
应用现在已经具备完整的用户认证和积分管理功能！用户可以注册账户、登录、管理积分，为后续的付费功能奠定了基础。
```

1. # Supabase配置

Supabase，这个被誉为开源版 Firebase 的后端即服务（BaaS）平台，凭借其强大的实时数据库、身份验证、存储等功能，正成为越来越多开发者的首选。

但是对于使用步骤中复制 “env.example”为 “.env” 并填入配置，我并不理解

![img](https://forchangesz.feishu.cn/space/api/box/stream/download/asynccode/?code=OGFkZjljNTg3ZGQwNjMxZjg5YTc0NjA2OTY1MDUxMTdfUVc1NTZZalBwYzI1UkJXbExEb1dzeERpcDIyenQ0cVRfVG9rZW46WU1ZT2IzSTNDb1JLUm94WnpuQ2M1NWRqbnNlXzE3NjcxOTI5NTE6MTc2NzE5NjU1MV9WNA)

于是我问Trae：复制 env.example 为 .env 并填入配置，这句话怎么理解

Trae给出的答复：

~~~Markdown
这句话的意思是你需要手动创建环境变量配置文件。让我为你详细解释并帮你操作：

## 📋 操作步骤解释

### 1. 什么是环境变量文件？
- `.env` 文件用于存储应用的配置信息（如API密钥、数据库连接等）
- 这些信息不应该直接写在代码中，而是通过环境变量来管理
- `.env` 文件通常不会提交到代码仓库（为了安全）

### 2. 为什么要复制 `env.example`？
- `env.example` 是一个模板文件，显示了需要哪些环境变量
- 你需要基于这个模板创建真正的 `.env` 文件
- 然后填入你的实际配置值

让我帮你创建这个文件：

[2 tools called]

我看到 `.env` 文件被系统阻止创建（这是正常的安全措施）。让我通过终端命令来帮你创建：

[1 tool called]

很好！现在 `.env` 文件已经创建了。接下来你需要：

## 🔧 配置步骤

### 第一步：获取 Supabase 配置信息

1. **访问 Supabase 控制台**：
   - 打开 [https://supabase.com](https://supabase.com)
   - 登录你的账户
   - 创建新项目或选择现有项目

2. **获取项目配置**：
   - 在项目仪表板左侧菜单中，点击 **Settings** (设置)
   - 点击 **API** 选项
   - 你会看到两个重要信息：
     - **Project URL**：形如 `https://your-project-id.supabase.co`
     - **anon public key**：一长串字符

### 第二步：编辑 .env 文件

现在你需要手动编辑 `.env` 文件，将其中的占位符替换为真实值：

```env
# 将这个替换为你的实际 Project URL
VITE_SUPABASE_URL=https://your-project-id.supabase.co

# 将这个替换为你的实际 anon public key  
VITE_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### 第三步：创建数据库表

在 Supabase 控制台中：
1. 点击左侧菜单的 **SQL Editor**
2. 复制 `supabase-schema.sql` 文件中的内容
3. 粘贴到 SQL 编辑器中执行

## 🎯 简化说明

**"复制 env.example 为 .env 并填入配置"** 的意思就是：

1. ✅ **复制文件**：我已经帮你完成了 `copy env.example .env`
2. ⏳ **填入配置**：你需要手动编辑 `.env` 文件，把里面的 `your_supabase_project_url` 和 `your_supabase_anon_key` 替换为你在 Supabase 控制台获取的真实值

这样做的好处是：
- 🔒 保护敏感信息（API 密钥等）
- 🚀 不同环境可以有不同配置
- 👥 团队协作时每人可以有自己的配置

你现在需要做的就是：
1. 去 Supabase 获取你的项目配置信息
2. 用文本编辑器打开 `.env` 文件
3. 替换里面的占位符为真实值
4. 保存文件

需要我帮你创建 Supabase 项目的详细步骤吗？
~~~

这里你可以让Trae生成详细步骤，然后根据它的指导进行，不会就问它。

## 第一步：获取 Supabase 配置信息

访问 Supabase 控制台https://supabase.com

我选择的是用github账号登录

![img](https://forchangesz.feishu.cn/space/api/box/stream/download/asynccode/?code=ZWI1MDY2NDcxNjg2YzI1ODAxMTc2YzNjOTJjNmYyZmVfUmRldUZacHRNSFNwUlRiT3RYTVFadkJQRUJ4ajBSZk9fVG9rZW46R1JnS2IyREVzbzhsVVN4RTNGcmN0WVJrbkhkXzE3NjcxOTI5NTE6MTc2NzE5NjU1MV9WNA)

填入账号名和密码

![img](https://forchangesz.feishu.cn/space/api/box/stream/download/asynccode/?code=YzdmOGQwZGE3YWI0MDRiYzVlMTBhNjg0OWRiMjIwNmRfaUdFMklNWERLZ05zdEdhemhkYTR4alJjZ1FROUg2aVRfVG9rZW46WHNTemJFWEVrb3VGQmt4dDkxeGNGSEtFbnBoXzE3NjcxOTI5NTE6MTc2NzE5NjU1MV9WNA)

选择授权给supabase

![img](https://forchangesz.feishu.cn/space/api/box/stream/download/asynccode/?code=M2U1MzVlMDg2MjUxNmZjMTU3MjJmOGI3MjE1MmQ0MGRfT2JyYnlVZExWOUh2ZFhnOEM4VU92dDBHTnhFajR0VmhfVG9rZW46RzlzN2JuVEhIb1ZSMWx4d25SUWM3cDF0bkhiXzE3NjcxOTI5NTE6MTc2NzE5NjU1MV9WNA)

下一步是创建组织：

![img](https://forchangesz.feishu.cn/space/api/box/stream/download/asynccode/?code=YjM1ZTkzMDZkMzhmZmQwMDJmNDY5ZGI1YzY4NjlmZTVfdjY3dkExdzh1S0pkZ3E0enZJaHFaZXI4RUo0em80aU5fVG9rZW46SjZjQmIyMWMyb3duRW14S291WWNUUGYwbk9OXzE3NjcxOTI5NTE6MTc2NzE5NjU1MV9WNA)

接着在组织里创建项目：

![img](https://forchangesz.feishu.cn/space/api/box/stream/download/asynccode/?code=OGYzZTVjMWM0ZWJmNzg1Mzk5ZGFkZjZlNzQ3ZGZkMDRfTjVSakNnMnZ5aUNYQVQ2UGlnSHB6b2NKS1BmWlNwNjRfVG9rZW46VU1yc2JYUDdhb1JhU2R4ZnJNMWNqQWI3bmdjXzE3NjcxOTI5NTE6MTc2NzE5NjU1MV9WNA)

获取项目配置

在项目仪表板左侧菜单中，选择Project Overview，往下滑找到下面的Project API

![img](https://forchangesz.feishu.cn/space/api/box/stream/download/asynccode/?code=MzM5NTE4YmM2ZGVkZjVkYTEyYTg1ZGJlNjU2YzhkYmNfb3V1RFFtejlhTmVrYnViNWx5TjltRWhPSkhMVzFDcTdfVG9rZW46WHRDQ2JJa2lxb3FWSFV4Q1Y5NWN6WU11blplXzE3NjcxOTI5NTE6MTc2NzE5NjU1MV9WNA)

把下面两个参数记一下：     - Project URL：形如 “https://your-project-id.supabase.co”     - API Key anon public：一长串字符

## 第二步：编辑 .env 文件

现在你需要手动编辑 “.env” 文件，将其中的占位符替换为真实值：

```env
# 将这个替换为你的实际 Project URL
VITE_SUPABASE_URL=https://your-project-id.supabase.co

# 将这个替换为你的实际 anon public key  
VITE_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

![img](https://forchangesz.feishu.cn/space/api/box/stream/download/asynccode/?code=Y2ZkN2E5NTE2YzRiOWUwZDk2NGJiODNhOTI4ZWJkNzZfeUFINnIwTWtvM3lGN0pzRHhVVEhDVGQ2N3AxemhyRTNfVG9rZW46Tlo1WGJBWXNVbzVDd3l4eXZORmMwOFpubnFkXzE3NjcxOTI5NTE6MTc2NzE5NjU1MV9WNA)

然后记得保存。

##  第三步：创建数据库表

在 Supabase 控制台中： 1. 点击左侧菜单的 **`SQL Editor`** 2. 复制 文件`supabase-init.sql`文件中的内容 3. 粘贴到 SQL 编辑器中执行

![img](https://forchangesz.feishu.cn/space/api/box/stream/download/asynccode/?code=OTZjNzBhMmQ1MWYzOGIyYTljMmJiYzdmZGExNzFlOTBfTzJtOWxEb2ZLaTFFd0QwUkU1S1huSHRxMW9PUGp5SnRfVG9rZW46V1ByVWJUU0t5b29rWTV4MDhzbmNQUEtzbmNiXzE3NjcxOTI5NTE6MTc2NzE5NjU1MV9WNA)

![img](https://forchangesz.feishu.cn/space/api/box/stream/download/asynccode/?code=MTk5MDIzOGYwY2NkOTYzMGY1ODA4NTRhNmE2NGU4NjVfNmRKejhZM2VFT1hjaDZUVjljSHBUSkZkS293WFM0RmVfVG9rZW46TlRmaWJEOVkxb09MeVl4WkVjdWNQMFJvbmhoXzE3NjcxOTI5NTE6MTc2NzE5NjU1MV9WNA)

![img](https://forchangesz.feishu.cn/space/api/box/stream/download/asynccode/?code=NjU3ODkyMTgxZTRlMDM0ZjE2NTFjOTYyZmU0YjIzMjFfQlY1MXZGRnBJaFlJZURadjJRN1BvdDhoWndVcnRCSjBfVG9rZW46TUFjY2JOQU9ib1I3ajR4aExsbWMwOU42bk1jXzE3NjcxOTI5NTE6MTc2NzE5NjU1MV9WNA)

正常情况下，下面会显示：

Success. No rows returned

## 第四步：关掉邮箱验证功能

因为我们这次只采用简单的用户名和密码就可以登录注册了，但是Supabase默认是会要求用邮箱注册的，所以可以先暂时关掉这个功能：

在Supabase的**`Authentication`** 里，选择**`Sign in / Providers`**，按照下图所指的**`Confirm email`**，关掉选项，然后点击下面的**`save changes`**就可以了

![img](https://forchangesz.feishu.cn/space/api/box/stream/download/asynccode/?code=N2VjYjdiOWZjNDZkMzQxN2M5NzMyMmU2NGJkNjc5N2Nfb0xiVGNscFZWR2ZjVEFQVG8xelZkWDZEU0VXVjdpTkZfVG9rZW46SkpiUWJWMXJyb3RON3h4RzlxS2NnMHJRbjZkXzE3NjcxOTI5NTE6MTc2NzE5NjU1MV9WNA)

1. # 测试验证功能

在Trae里输入下面的语句：

```Plain
我在Supabase里把相关信息粘贴到了env文件里，以及把supabase-setup.sql语句复制到Supabase的SQL Editor里Run了，提示成功，下一步我应该做什么？
```

![img](https://forchangesz.feishu.cn/space/api/box/stream/download/asynccode/?code=ZDQ3OTA2ZmRkNWRkZWQyZmViNTNjYmJlNWQwZjNhYjdfaXFhaUpqMlVJN0huOXRlQTJFZlBYcDZhVEhCQXVCd25fVG9rZW46QVFwa2IycVI3b0phTkt4b1pFUmNTcVp1bmlmXzE3NjcxOTI5NTE6MTc2NzE5NjU1MV9WNA)

很快运行完了，Trae让我们验证一下，我们打开浏览器，输入测试链接：

![img](https://forchangesz.feishu.cn/space/api/box/stream/download/asynccode/?code=YTVjMzY1NDVlMzdhMTkxMzQ3NzFlMWY5ZGY0YzI2NTdfcHI4Ym10c1FkZFpEamZ0UFZEck11WDVlSTR2VDdCWDBfVG9rZW46SGxWaWJiMkFFb0RvQ054b2ZOVGNlOWhubnNkXzE3NjcxOTI5NTE6MTc2NzE5NjU1MV9WNA)

测试后发现注册没有响应，然后我们切到Supabase里的Table Editor发现有了

![img](https://forchangesz.feishu.cn/space/api/box/stream/download/asynccode/?code=NTBjOTJkYTU4Mjk3ZDVjN2NmNDQzMzJiZTUzYjZjOTdfMHRhYWpWeTJVSjRxaDRxWnY3ZTZUVzkwUzJkTWdYYWdfVG9rZW46RXhyVWJvd05Yb3ZnZm14TTV5bWNvY2wzblZiXzE3NjcxOTI5NTE6MTc2NzE5NjU1MV9WNA)

说明已经成功了，但是，目前在网页上，还没有正常显示用户名和积分：

![img](https://forchangesz.feishu.cn/space/api/box/stream/download/asynccode/?code=ZDZhMTU3ZGY2YTFhMzU2NmFiMDg4NmI3Y2Q3NTc5MmNfN1JHTjE0dVd5WXo4ODZySll3OWRQbUJoOXRpdnY4RmdfVG9rZW46QUFiWGJoTlRJb25NS0d4MVFodWMzMWw0bldnXzE3NjcxOTI5NTE6MTc2NzE5NjU1MV9WNA)

这一步继续让Trae修复即可！
