# GitHub Actions 部署指南

本文档介绍如何使用 GitHub Actions 为 Podscript 设置 CI/CD 流水线。

## 目录

- [功能概述](#功能概述)
- [第一步：准备工作](#第一步准备工作)
- [第二步：配置 GitHub Secrets](#第二步配置-github-secrets)
- [第三步：创建 Workflow 文件](#第三步创建-workflow-文件)
- [第四步：测试 Workflow](#第四步测试-workflow)
- [高级配置](#高级配置)

---

## 功能概述

我们将配置以下 CI/CD 功能：

| 功能 | 触发条件 | 说明 |
|------|----------|------|
| 代码检查 | 每次 Push/PR | Lint、类型检查 |
| 单元测试 | 每次 Push/PR | 运行 pytest |
| 构建 Docker 镜像 | 合并到 main | 构建并推送到 Registry |
| 部署 | 合并到 main | 自动部署到服务器 |

---

## 第一步：准备工作

### 1.1 项目结构调整

确保项目有以下文件：

```
podscript/
├── .github/
│   └── workflows/
│       └── ci.yml          # CI/CD 配置
├── Dockerfile              # Docker 构建文件
├── docker-compose.yml      # Docker Compose 配置
├── requirements.txt        # Python 依赖
├── pyproject.toml          # 项目配置
└── src/                    # 源代码
```

### 1.2 创建 Dockerfile

在项目根目录创建 `Dockerfile`：

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖（ffmpeg 用于音频处理）
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制源代码
COPY src/ ./src/

# 创建 artifacts 目录
RUN mkdir -p artifacts

# 设置环境变量
ENV PYTHONPATH=/app/src
ENV ARTIFACTS_DIR=/app/artifacts

# 暴露端口
EXPOSE 8001

# 启动命令
CMD ["uvicorn", "podscript_api.main:app", "--host", "0.0.0.0", "--port", "8001"]
```

### 1.3 创建 docker-compose.yml

```yaml
version: '3.8'

services:
  podscript:
    build: .
    ports:
      - "8001:8001"
    environment:
      - ALIBABA_CLOUD_ACCESS_KEY_ID=${ALIBABA_CLOUD_ACCESS_KEY_ID}
      - ALIBABA_CLOUD_ACCESS_KEY_SECRET=${ALIBABA_CLOUD_ACCESS_KEY_SECRET}
      - STORAGE_PROVIDER=${STORAGE_PROVIDER}
      - STORAGE_BUCKET=${STORAGE_BUCKET}
      - STORAGE_PUBLIC_HOST=${STORAGE_PUBLIC_HOST}
      - STORAGE_REGION=${STORAGE_REGION}
      - TINGWU_ENABLED=${TINGWU_ENABLED}
      - TINGWU_APP_KEY=${TINGWU_APP_KEY}
    volumes:
      - ./artifacts:/app/artifacts
    restart: unless-stopped
```

---

## 第二步：配置 GitHub Secrets

在 GitHub 仓库中配置敏感信息：

1. 进入仓库 → Settings → Secrets and variables → Actions
2. 点击「New repository secret」
3. 添加以下 Secrets：

| Secret 名称 | 说明 |
|-------------|------|
| `ALIBABA_CLOUD_ACCESS_KEY_ID` | 阿里云 AccessKey ID |
| `ALIBABA_CLOUD_ACCESS_KEY_SECRET` | 阿里云 AccessKey Secret |
| `TINGWU_APP_KEY` | 通义听悟 AppKey |
| `DOCKER_USERNAME` | Docker Hub 用户名（可选）|
| `DOCKER_PASSWORD` | Docker Hub 密码（可选）|
| `DEPLOY_HOST` | 部署服务器 IP（可选）|
| `DEPLOY_KEY` | 服务器 SSH 私钥（可选）|

---

## 第三步：创建 Workflow 文件

创建 `.github/workflows/ci.yml`：

```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

env:
  PYTHON_VERSION: '3.11'

jobs:
  # ============== 代码检查 ==============
  lint:
    name: Lint & Type Check
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install ruff mypy
          pip install -r requirements.txt

      - name: Run Ruff (linting)
        run: ruff check src/

      - name: Run MyPy (type checking)
        run: mypy src/ --ignore-missing-imports
        continue-on-error: true

  # ============== 单元测试 ==============
  test:
    name: Unit Tests
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Install ffmpeg
        run: sudo apt-get update && sudo apt-get install -y ffmpeg

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install pytest pytest-cov pytest-asyncio

      - name: Run tests
        env:
          PYTHONPATH: ./src
          ARTIFACTS_DIR: ./artifacts
        run: |
          mkdir -p artifacts
          pytest tests/ -v --cov=src --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml
        continue-on-error: true

  # ============== 构建 Docker 镜像 ==============
  build:
    name: Build Docker Image
    runs-on: ubuntu-latest
    needs: [lint, test]
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Login to Docker Hub
        uses: docker/login-action@v3
        with:
          username: ${{ secrets.DOCKER_USERNAME }}
          password: ${{ secrets.DOCKER_PASSWORD }}
        if: ${{ secrets.DOCKER_USERNAME != '' }}

      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          push: ${{ secrets.DOCKER_USERNAME != '' }}
          tags: |
            ${{ secrets.DOCKER_USERNAME }}/podscript:latest
            ${{ secrets.DOCKER_USERNAME }}/podscript:${{ github.sha }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

  # ============== 部署（可选）==============
  deploy:
    name: Deploy to Server
    runs-on: ubuntu-latest
    needs: [build]
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'

    steps:
      - name: Deploy via SSH
        uses: appleboy/ssh-action@v1.0.0
        if: ${{ secrets.DEPLOY_HOST != '' }}
        with:
          host: ${{ secrets.DEPLOY_HOST }}
          username: ${{ secrets.DEPLOY_USER || 'root' }}
          key: ${{ secrets.DEPLOY_KEY }}
          script: |
            cd /opt/podscript
            docker-compose pull
            docker-compose up -d
            docker system prune -f
```

---

## 第四步：测试 Workflow

### 4.1 推送代码触发 CI

```bash
git add .github/workflows/ci.yml Dockerfile docker-compose.yml
git commit -m "ci: add GitHub Actions workflow"
git push origin main
```

### 4.2 查看运行状态

1. 进入 GitHub 仓库 → Actions 标签
2. 点击最新的 workflow run 查看详情
3. 检查每个 job 的运行结果

### 4.3 修复常见问题

**问题：Lint 检查失败**
```bash
# 本地运行 ruff 修复
pip install ruff
ruff check src/ --fix
```

**问题：测试失败**
```bash
# 本地运行测试
PYTHONPATH=./src pytest tests/ -v
```

---

## 高级配置

### 自动发布 Release

添加 `.github/workflows/release.yml`：

```yaml
name: Release

on:
  push:
    tags:
      - 'v*'

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Create Release
        uses: softprops/action-gh-release@v1
        with:
          generate_release_notes: true
```

### 定时健康检查

在 `ci.yml` 中添加：

```yaml
on:
  schedule:
    - cron: '0 0 * * *'  # 每天 UTC 0:00
```

### 多环境部署

```yaml
deploy-staging:
  if: github.ref == 'refs/heads/develop'
  environment: staging
  # ...

deploy-production:
  if: github.ref == 'refs/heads/main'
  environment: production
  # ...
```

---

## 相关文档

- [GitHub Actions 官方文档](https://docs.github.com/en/actions)
- [Docker Build Push Action](https://github.com/docker/build-push-action)
- [SSH Deploy Action](https://github.com/appleboy/ssh-action)
