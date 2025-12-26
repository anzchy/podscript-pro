# Railway 部署指南

本文档介绍如何将 Podscript 部署到 [Railway](https://railway.app/)，实现一键部署和自动扩缩容。

## 目录

- [Railway 简介](#railway-简介)
- [第一步：准备工作](#第一步准备工作)
- [第二步：创建 Railway 项目](#第二步创建-railway-项目)
- [第三步：配置环境变量](#第三步配置环境变量)
- [第四步：部署应用](#第四步部署应用)
- [第五步：配置域名](#第五步配置域名)
- [高级配置](#高级配置)
- [费用说明](#费用说明)

---

## Railway 简介

Railway 是一个现代化的 PaaS 平台，特点包括：

- ✅ 从 GitHub 一键部署
- ✅ 自动 HTTPS
- ✅ 自动扩缩容
- ✅ 支持 Docker 和 Nixpacks
- ✅ 每月 $5 免费额度（Hobby 计划）

---

## 第一步：准备工作

### 1.1 创建必要文件

确保项目根目录有以下文件：

**`Procfile`**（启动命令）：
```
web: uvicorn podscript_api.main:app --host 0.0.0.0 --port $PORT
```

**`runtime.txt`**（Python 版本）：
```
python-3.11
```

**`nixpacks.toml`**（构建配置）：
```toml
[phases.setup]
nixPkgs = ["python311", "ffmpeg"]

[phases.install]
cmds = ["pip install -r requirements.txt"]

[start]
cmd = "uvicorn podscript_api.main:app --host 0.0.0.0 --port ${PORT:-8001}"
```

### 1.2 更新 requirements.txt

确保包含所有依赖：

```
fastapi>=0.100.0
uvicorn[standard]>=0.22.0
python-dotenv>=1.0.0
httpx>=0.24.0
oss2>=2.18.0
pydub>=0.25.0
yt-dlp>=2023.7.0
aliyunsdkcore>=2.13.0
alibabacloud-tingwu20230930>=1.0.0
openai-whisper>=20231117
```

### 1.3 确保代码结构正确

```
podscript/
├── Procfile
├── runtime.txt
├── nixpacks.toml
├── requirements.txt
├── src/
│   ├── podscript_api/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   └── static/
│   ├── podscript_pipeline/
│   └── podscript_shared/
└── ...
```

---

## 第二步：创建 Railway 项目

### 2.1 注册 Railway

1. 访问 [railway.app](https://railway.app/)
2. 使用 GitHub 账号登录（推荐）

### 2.2 新建项目

**方法一：从 GitHub 部署**

1. 点击「New Project」
2. 选择「Deploy from GitHub repo」
3. 授权 Railway 访问你的 GitHub
4. 选择 `podscript` 仓库
5. Railway 会自动检测项目类型并开始部署

**方法二：使用 Railway CLI**

```bash
# 安装 CLI
npm install -g @railway/cli

# 登录
railway login

# 初始化项目
railway init

# 链接到现有项目
railway link
```

---

## 第三步：配置环境变量

### 3.1 在 Railway Dashboard 配置

1. 进入项目 → 点击服务卡片
2. 点击「Variables」标签
3. 添加以下环境变量：

```
PYTHONPATH=/app/src
ARTIFACTS_DIR=/app/artifacts

# 阿里云配置
ALIBABA_CLOUD_ACCESS_KEY_ID=你的AccessKeyID
ALIBABA_CLOUD_ACCESS_KEY_SECRET=你的AccessKeySecret
STORAGE_PROVIDER=oss
STORAGE_BUCKET=你的Bucket名称
STORAGE_PUBLIC_HOST=https://你的Bucket.oss-地域.aliyuncs.com
STORAGE_REGION=cn-shanghai

# 通义听悟配置
TINGWU_ENABLED=1
TINGWU_APP_KEY=你的AppKey
```

### 3.2 使用 CLI 配置

```bash
# 添加单个变量
railway variables set TINGWU_APP_KEY=你的AppKey

# 从 .env 文件批量导入
railway variables set < .env.production
```

### 3.3 使用 Shared Variables（推荐）

对于多服务项目，可以创建共享变量：

1. 项目设置 → Shared Variables
2. 添加公共配置
3. 在各服务中引用：`${{shared.ALIBABA_CLOUD_ACCESS_KEY_ID}}`

---

## 第四步：部署应用

### 4.1 自动部署

默认情况下，每次推送到 `main` 分支会自动触发部署：

```bash
git add .
git commit -m "feat: add Railway deployment"
git push origin main
```

### 4.2 手动部署

```bash
# 使用 CLI
railway up

# 或在 Dashboard 点击「Deploy」
```

### 4.3 查看部署日志

```bash
# CLI
railway logs

# 或在 Dashboard → Deployments → 点击具体部署
```

### 4.4 验证部署

```bash
# 获取临时域名
railway domain

# 测试 API
curl https://你的域名.railway.app/docs
```

---

## 第五步：配置域名

### 5.1 使用 Railway 提供的域名

1. 服务卡片 → Settings → Networking
2. 点击「Generate Domain」
3. 获得类似 `podscript-xxx.up.railway.app` 的域名

### 5.2 自定义域名

1. Settings → Networking → Custom Domain
2. 添加你的域名，如 `api.example.com`
3. 在 DNS 服务商添加 CNAME 记录：
   ```
   api.example.com CNAME podscript-xxx.up.railway.app
   ```
4. Railway 会自动配置 SSL 证书

---

## 高级配置

### 持久化存储

Railway 的文件系统是临时的。对于 `artifacts` 目录，有两个选择：

**选项一：使用 Railway Volume**

```bash
# 在项目中添加 Volume
railway volume add

# 挂载到 artifacts 目录
# 在 railway.json 中配置：
{
  "build": {},
  "deploy": {
    "volumes": {
      "/app/artifacts": "artifacts-volume"
    }
  }
}
```

**选项二：使用外部存储（推荐）**

将转写结果直接保存到 OSS，而不是本地文件系统。

### 健康检查

在 `main.py` 中添加健康检查端点：

```python
@app.get("/health")
async def health_check():
    return {"status": "healthy"}
```

在 Railway Settings 中配置：
- Health Check Path: `/health`
- Health Check Timeout: `10s`

### 自动扩缩容

Railway Pro 计划支持自动扩缩容：

1. Settings → Scaling
2. 配置最小/最大实例数
3. 配置扩容触发条件（CPU/内存阈值）

### 环境隔离

创建多个环境（开发/预发/生产）：

```bash
# 创建新环境
railway environment create staging

# 切换环境
railway environment use staging

# 部署到特定环境
railway up --environment staging
```

---

## 费用说明

### Hobby 计划（个人使用）

- **价格**：$5/月
- **资源**：8GB RAM，8 vCPU（共享）
- **执行时间**：500 小时/月
- **适合**：个人项目、测试

### Pro 计划（团队使用）

- **价格**：$20/月起（按实际使用计费）
- **资源**：可自定义
- **功能**：团队协作、自动扩缩容、SLA 保障

### 资源消耗估算

| 操作 | CPU | 内存 | 预估费用 |
|------|-----|------|----------|
| API 待机 | 0.1 vCPU | 256MB | ~$0.01/小时 |
| Whisper 转写 | 2 vCPU | 2GB | ~$0.10/小时 |
| 通义听悟转写 | 0.2 vCPU | 512MB | ~$0.02/小时 |

> 💡 **提示**：使用通义听悟比本地 Whisper 更省 Railway 资源。

---

## 故障排除

### 部署失败：找不到模块

**错误**：`ModuleNotFoundError: No module named 'podscript_api'`

**解决**：确保设置了 `PYTHONPATH=/app/src`

### 部署失败：ffmpeg 未安装

**错误**：`ffmpeg not found`

**解决**：使用 `nixpacks.toml` 配置：
```toml
[phases.setup]
nixPkgs = ["ffmpeg"]
```

### 内存不足

**错误**：`OOMKilled`

**解决**：
1. 使用更小的 Whisper 模型（tiny/base）
2. 升级到更高配置
3. 改用通义听悟（云端处理）

### 健康检查失败

**错误**：`Health check failed`

**解决**：
1. 确认端口配置正确（使用 `$PORT` 环境变量）
2. 检查应用是否正常启动
3. 增加健康检查超时时间

---

## 相关链接

- [Railway 官方文档](https://docs.railway.app/)
- [Railway CLI](https://docs.railway.app/develop/cli)
- [Nixpacks 配置](https://nixpacks.com/docs/configuration/file)
- [Railway 定价](https://railway.app/pricing)
