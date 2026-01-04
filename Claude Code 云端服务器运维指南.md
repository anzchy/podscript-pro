# Podscript 服务器部署复盘指南

> 本文档记录了使用 Claude Code 远程部署 Podscript 到 Ubuntu 服务器的完整流程。

## 目录

1. [环境概述](#环境概述)
2. [SSH远程连接](#ssh远程连接)
3. [项目安装与配置](#项目安装与配置)
4. [Nginx反向代理配置（宝塔面板）](#nginx反向代理配置宝塔面板)
5. [Cloudflare DNS设置](#cloudflare-dns设置)
6. [SSL证书配置](#ssl证书配置)
7. [常见问题排查](#常见问题排查)
8. [服务器维护](#服务器维护)

---

## 环境概述

| 项目 | 值 |
|------|-----|
| 服务器IP | `66.154.105.210` |
| 操作系统 | Ubuntu 22.04 LTS |
| Python版本 | 3.10.12 |
| Web服务器 | Nginx（宝塔面板安装） |
| 域名 | `podscript.jackcheng.tech` |
| DNS服务 | Cloudflare |
| SSL证书 | Let's Encrypt |

---

## SSH远程连接

### 使用 Claude Code 通过 sshpass 连接

Claude Code 可以通过 `sshpass` 工具实现自动化 SSH 连接：

```bash
# 安装 sshpass（macOS）
brew install sshpass

# 基本连接命令格式
sshpass -p '密码' ssh -o StrictHostKeyChecking=no 用户名@服务器IP "命令"

# 示例：测试连接
sshpass -p 'your_password' ssh -o StrictHostKeyChecking=no lighthouse@66.154.105.210 "echo '连接成功'"
```

### 执行远程命令

```bash
# 单条命令
sshpass -p 'password' ssh user@host "ls -la"

# 多条命令（使用引号包裹）
sshpass -p 'password' ssh user@host "cd /path && command1 && command2"

# 需要 sudo 权限的命令
sshpass -p 'password' ssh user@host 'echo "password" | sudo -S command'
```

### 文件传输

```bash
# 上传文件到服务器
sshpass -p 'password' scp -o StrictHostKeyChecking=no /local/file user@host:/remote/path

# 从服务器下载文件
sshpass -p 'password' scp -o StrictHostKeyChecking=no user@host:/remote/file /local/path
```

---

## 项目安装与配置

### 1. 克隆项目

```bash
# SSH到服务器后执行
cd ~
mkdir -p podscript
cd podscript
git clone https://github.com/your-username/podscript-pro.git
cd podscript-pro
```

### 2. 创建虚拟环境

```bash
# 创建虚拟环境
python3 -m venv .venv

# 激活虚拟环境
source .venv/bin/activate

# 确认 Python 路径
which python  # 应显示 .venv/bin/python
```

### 3. 安装依赖

**注意：** 服务器磁盘空间有限时，可跳过大型依赖（如 `openai-whisper`）

```bash
# 升级 pip
pip install --upgrade pip

# 安装核心依赖（精简版，跳过 whisper）
pip install 'uvicorn[standard]>=0.30.0' \
    'python-multipart>=0.0.9' \
    'python-dotenv>=1.0.1' \
    'httpx>=0.27.0' \
    'aliyun-python-sdk-core>=2.15.0' \
    'fastapi>=0.115.0' \
    'pydantic>=2.8.0'

# 或安装完整依赖（需要足够磁盘空间）
pip install -r requirements.txt
```

### 4. 配置环境变量

```bash
# 创建 .env 文件
cat > .env << 'EOF'
ALIBABA_CLOUD_ACCESS_KEY_ID=your_key_id
ALIBABA_CLOUD_ACCESS_KEY_SECRET=your_key_secret
TINGWU_APP_KEY=your_tingwu_app_key
STORAGE_PROVIDER=oss
STORAGE_BUCKET=your_bucket
STORAGE_REGION=cn-shanghai
TINGWU_ENABLED=1
EOF
```

### 5. 启动应用

```bash
# 前台运行（测试用）
PYTHONPATH=./src python -m uvicorn podscript_api.main:app --host 0.0.0.0 --port 8001

# 后台运行（生产用）
nohup bash -c 'cd ~/podscript/podscript-pro && source .venv/bin/activate && PYTHONPATH=./src python -m uvicorn podscript_api.main:app --host 0.0.0.0 --port 8001' > app.log 2>&1 &

# 查看日志
tail -f app.log

# 检查进程
ps aux | grep uvicorn
```

### 常见错误：ModuleNotFoundError

**问题：** `ModuleNotFoundError: No module named 'fastapi'`

**原因：** 虚拟环境中未安装依赖，或使用了系统级的 uvicorn

**解决：**
```bash
# 确保使用虚拟环境中的 uvicorn
source .venv/bin/activate
which uvicorn  # 应显示 .venv/bin/uvicorn

# 使用 python -m 运行确保使用正确环境
python -m uvicorn podscript_api.main:app --port 8001
```

---

## Nginx反向代理配置（宝塔面板）

### 宝塔面板 Nginx 路径

| 项目 | 路径 |
|------|------|
| Nginx主程序 | `/www/server/nginx/sbin/nginx` |
| 主配置文件 | `/www/server/nginx/conf/nginx.conf` |
| 站点配置目录 | `/www/server/panel/vhost/nginx/` |
| 站点根目录 | `/www/wwwroot/` |
| 日志目录 | `/www/wwwlogs/` |

### 创建站点配置

创建文件 `/www/server/panel/vhost/nginx/podscript.jackcheng.tech.conf`：

```nginx
# Podscript SSL config
map $http_upgrade $connection_upgrade {
    default upgrade;
    '' close;
}

server {
    listen 80;
    listen [::]:80;
    server_name podscript.jackcheng.tech;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    listen 443 quic;
    http2 on;
    server_name podscript.jackcheng.tech;

    root /www/wwwroot/podscript.jackcheng.tech;

    # SSL 证书配置
    ssl_certificate /etc/letsencrypt/live/podscript.jackcheng.tech/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/podscript.jackcheng.tech/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    add_header Strict-Transport-Security "max-age=31536000" always;

    # 反向代理配置
    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_http_version 1.1;

        # WebSocket 支持
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $connection_upgrade;

        # 请求头转发
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # 超时配置
        proxy_connect_timeout 60s;
        proxy_send_timeout 600s;
        proxy_read_timeout 600s;
        proxy_buffering off;

        # 上传大小限制
        client_max_body_size 500M;
    }

    # Let's Encrypt 证书续期
    location /.well-known {
        root /www/wwwroot/podscript.jackcheng.tech;
    }

    # 日志
    access_log /www/wwwlogs/podscript.jackcheng.tech.log;
    error_log /www/wwwlogs/podscript.jackcheng.tech.error.log;
}
```

### 测试并重载 Nginx

```bash
# 测试配置语法
sudo /www/server/nginx/sbin/nginx -t

# 重载配置
sudo /www/server/nginx/sbin/nginx -s reload
```

### 多站点共用同一 IP

Nginx 通过 `server_name` 区分不同域名的请求：

```
请求 n8n.jackcheng.tech     → server_name n8n.jackcheng.tech     → proxy_pass 127.0.0.1:5678
请求 podscript.jackcheng.tech → server_name podscript.jackcheng.tech → proxy_pass 127.0.0.1:8001
```

---

## Cloudflare DNS设置

### 添加 A 记录

1. 登录 [Cloudflare Dashboard](https://dash.cloudflare.com)
2. 选择域名 `jackcheng.tech`
3. 进入 **DNS** → **Records**
4. 点击 **Add record**

| 字段 | 值 |
|------|-----|
| Type | A |
| Name | podscript |
| IPv4 address | 66.154.105.210 |
| Proxy status | DNS only (灰色云) |
| TTL | Auto |

### 代理状态说明

| 状态 | 图标 | 说明 |
|------|------|------|
| **Proxied** | 🟠 橙色云 | 流量经过 Cloudflare，提供 CDN/DDoS 防护，Cloudflare 提供 SSL |
| **DNS only** | ⚫ 灰色云 | 仅 DNS 解析，流量直连服务器，需要服务器自己配置 SSL |

**建议：** 使用灰色云（DNS only），这样可以在服务器直接使用 Let's Encrypt 申请 SSL 证书。

### 验证 DNS 解析

```bash
# 使用 dig 查询
dig +short podscript.jackcheng.tech

# 应返回服务器 IP
66.154.105.210
```

---

## SSL证书配置

### 使用 Certbot 申请 Let's Encrypt 证书

```bash
# 安装 certbot
sudo apt-get update
sudo apt-get install -y certbot

# 申请证书（webroot 方式）
sudo certbot certonly --webroot \
    -w /www/wwwroot/podscript.jackcheng.tech \
    -d podscript.jackcheng.tech \
    --non-interactive \
    --agree-tos \
    --email your-email@example.com
```

### 证书路径

| 文件 | 路径 |
|------|------|
| 证书链 | `/etc/letsencrypt/live/podscript.jackcheng.tech/fullchain.pem` |
| 私钥 | `/etc/letsencrypt/live/podscript.jackcheng.tech/privkey.pem` |

### 自动续期

Certbot 会自动创建 systemd timer 进行证书续期：

```bash
# 查看续期定时任务
sudo systemctl status certbot.timer

# 手动测试续期
sudo certbot renew --dry-run
```

### 验证 SSL 配置

```bash
# 测试 HTTPS 访问
curl -I https://podscript.jackcheng.tech

# 查看证书信息
echo | openssl s_client -connect podscript.jackcheng.tech:443 -servername podscript.jackcheng.tech 2>/dev/null | openssl x509 -noout -subject -dates
```

---

## 常见问题排查

### 1. 502 Bad Gateway

**原因：** Nginx 无法连接到后端应用

**检查步骤：**
```bash
# 检查应用是否运行
ps aux | grep uvicorn

# 检查端口是否监听
ss -tlnp | grep 8001

# 查看应用日志
tail -50 ~/podscript/podscript-pro/app.log
```

### 2. 磁盘空间不足

```bash
# 查看磁盘使用
df -h

# 清理 pip 缓存
rm -rf ~/.cache/pip

# 清理 Docker（如有）
sudo docker system prune -a

# 清理系统日志
sudo journalctl --vacuum-time=3d

# 清理临时文件
sudo rm -rf /tmp/pip-*
```

### 3. 僵尸进程

```bash
# 查看僵尸进程
ps aux | awk '$8 ~ /Z/'

# 找到父进程
ps -o ppid= -p <zombie_pid>

# 重启产生僵尸进程的服务（如 Docker 容器）
sudo docker restart <container_name>
```

### 4. SSL 证书申请失败

```bash
# 检查 80 端口是否开放
sudo ss -tlnp | grep :80

# 检查防火墙
sudo ufw status

# 检查域名解析
dig +short podscript.jackcheng.tech
```

---

## 服务器维护

### 开机自启动 Podscript

创建 systemd 服务文件 `/etc/systemd/system/podscript.service`：

```ini
[Unit]
Description=Podscript API Service
After=network.target

[Service]
Type=simple
User=lighthouse
WorkingDirectory=/home/lighthouse/podscript/podscript-pro
Environment="PYTHONPATH=/home/lighthouse/podscript/podscript-pro/src"
ExecStart=/home/lighthouse/podscript/podscript-pro/.venv/bin/python -m uvicorn podscript_api.main:app --host 0.0.0.0 --port 8001
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启用服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable podscript
sudo systemctl start podscript
sudo systemctl status podscript
```

### 日志管理

```bash
# 查看应用日志
tail -f ~/podscript/podscript-pro/app.log

# 查看 Nginx 访问日志
sudo tail -f /www/wwwlogs/podscript.jackcheng.tech.log

# 查看 Nginx 错误日志
sudo tail -f /www/wwwlogs/podscript.jackcheng.tech.error.log
```

### 更新应用

```bash
cd ~/podscript/podscript-pro

# 拉取最新代码
git pull origin master

# 重新安装依赖（如有更新）
source .venv/bin/activate
pip install -r requirements.txt

# 重启应用
sudo systemctl restart podscript
# 或者
pkill -f 'uvicorn podscript_api'
nohup bash -c 'cd ~/podscript/podscript-pro && source .venv/bin/activate && PYTHONPATH=./src python -m uvicorn podscript_api.main:app --host 0.0.0.0 --port 8001' > app.log 2>&1 &
```

---

## 参考链接

- [Podscript GitHub 仓库](https://github.com/your-username/podscript-pro)
- [Let's Encrypt 官方文档](https://letsencrypt.org/docs/)
- [Nginx 反向代理配置](https://nginx.org/en/docs/http/ngx_http_proxy_module.html)
- [Cloudflare DNS 文档](https://developers.cloudflare.com/dns/)

---

*文档更新时间：2026-01-03*
