# 阿里云服务配置指南

本文档介绍如何从零开始配置 Podscript 所需的阿里云服务，包括 OSS 对象存储和通义听悟转写服务。

## 目录

- [前置条件](#前置条件)
- [第一步：创建阿里云账号](#第一步创建阿里云账号)
- [第二步：创建 RAM 用户和 AccessKey](#第二步创建-ram-用户和-accesskey)
- [第三步：配置 OSS 对象存储](#第三步配置-oss-对象存储)
- [第四步：开通通义听悟服务](#第四步开通通义听悟服务)
- [第五步：配置环境变量](#第五步配置环境变量)
- [故障排除](#故障排除)

---

## 前置条件

- 一个有效的阿里云账号（需要实名认证）
- 基本的命令行操作知识

---

## 第一步：创建阿里云账号

如果你还没有阿里云账号：

1. 访问 [阿里云官网](https://www.aliyun.com/)
2. 点击右上角「免费注册」
3. 完成手机号验证和实名认证

---

## 第二步：创建 RAM 用户和 AccessKey

> ⚠️ **安全提示**：不要使用主账号的 AccessKey，建议创建 RAM 子账号。

### 2.1 创建 RAM 用户

1. 登录 [RAM 访问控制台](https://ram.console.aliyun.com/users)
2. 点击「创建用户」
3. 填写用户信息：
   - 登录名称：`podscript-service`
   - 显示名称：`Podscript 服务账号`
   - 访问方式：勾选「OpenAPI 调用访问」
4. 点击「确定」

### 2.2 获取 AccessKey

创建用户后，系统会显示 AccessKey ID 和 AccessKey Secret：

```
AccessKey ID:     LTAI5txxxxxxxxxx
AccessKey Secret: YBS6uVxxxxxxxxxx
```

> ⚠️ **重要**：AccessKey Secret 只显示一次，请立即保存！

### 2.3 授权 RAM 用户

为 RAM 用户添加以下权限：

1. 在用户列表点击刚创建的用户
2. 点击「添加权限」
3. 添加以下策略：
   - `AliyunOSSFullAccess` - OSS 完全访问权限
   - `AliyunTingwuFullAccess` - 通义听悟完全访问权限

**参考文档**：[创建 RAM 用户](https://help.aliyun.com/zh/ram/user-guide/create-a-ram-user)

---

## 第三步：配置 OSS 对象存储

通义听悟需要通过 OSS 读取音频文件，因此需要先配置 OSS。

### 3.1 创建 Bucket

1. 访问 [OSS 管理控制台](https://oss.console.aliyun.com/bucket)
2. 点击「创建 Bucket」
3. 配置参数：
   - **Bucket 名称**：`podscript`（或自定义名称）
   - **地域**：选择 `华东1（杭州）` 或 `华东2（上海）`
   - **存储类型**：标准存储
   - **读写权限**：私有
4. 点击「确定」创建

### 3.2 记录配置信息

创建完成后，记录以下信息：

| 配置项 | 示例值 | 说明 |
|--------|--------|------|
| Bucket 名称 | `podscript` | 你创建的 Bucket 名称 |
| 地域 | `cn-shanghai` | Bucket 所在地域代码 |
| 公网访问域名 | `https://podscript.oss-cn-shanghai.aliyuncs.com` | 用于访问文件 |

**地域代码对照表**：
- 华东1（杭州）：`cn-hangzhou`
- 华东2（上海）：`cn-shanghai`
- 华北2（北京）：`cn-beijing`

**参考文档**：[OSS 快速入门](https://help.aliyun.com/zh/oss/getting-started/)

---

## 第四步：开通通义听悟服务

### 4.1 开通服务

1. 访问 [通义听悟控制台](https://tingwu.console.aliyun.com/)
2. 首次访问会提示开通服务，点击「立即开通」
3. 阅读并同意服务协议

### 4.2 获取 AppKey

这是最关键的一步！

1. 在通义听悟控制台左侧菜单，点击「应用管理」
2. 点击「创建应用」
3. 填写应用信息：
   - 应用名称：`podscript`
   - 应用描述：`播客转写应用`
4. 创建成功后，在应用列表中可以看到 **AppKey**

```
AppKey: REDACTED_TINGWU_APP_KEY
```

> ⚠️ **注意**：AppKey 和 AccessKey 是不同的！
> - **AccessKey**：阿里云账号的身份凭证
> - **AppKey**：通义听悟服务的应用标识

**参考文档**：
- [通义听悟文档](https://help.aliyun.com/zh/tingwu/)
- [通义听悟 API 文档](https://next.api.aliyun.com/api/tingwu/2023-09-30/GetTaskInfo?lang=PYTHON)

---

## 第五步：配置环境变量

在项目根目录创建 `.env` 文件：

```bash
# 阿里云 AccessKey（从 RAM 控制台获取）
ALIBABA_CLOUD_ACCESS_KEY_ID=你的AccessKeyID
ALIBABA_CLOUD_ACCESS_KEY_SECRET=你的AccessKeySecret

# OSS 配置
STORAGE_PROVIDER=oss
STORAGE_BUCKET=你的Bucket名称
STORAGE_PUBLIC_HOST=https://你的Bucket名称.oss-地域.aliyuncs.com
STORAGE_REGION=地域代码

# 通义听悟配置
TINGWU_ENABLED=1
TINGWU_APP_KEY=你的AppKey

# 本地存储目录
ARTIFACTS_DIR=artifacts
```

### 示例配置

```bash
ALIBABA_CLOUD_ACCESS_KEY_ID=xxx
ALIBABA_CLOUD_ACCESS_KEY_SECRET=xxx
STORAGE_PROVIDER=oss
STORAGE_BUCKET=podscript
STORAGE_PUBLIC_HOST=https://podscript.oss-cn-shanghai.aliyuncs.com
STORAGE_REGION=cn-shanghai
TINGWU_ENABLED=1
TINGWU_APP_KEY=xxxx
ARTIFACTS_DIR=artifacts
```

---

## 故障排除

### 问题 1：Tingwu service is not properly configured

**错误信息**：
```
Tingwu service is not properly configured. Check environment variables.
```

**原因分析**：

通义听悟需要以下所有配置项都正确设置：

| 配置项 | 检查方法 |
|--------|----------|
| `TINGWU_ENABLED` | 必须为 `1` |
| `ALIBABA_CLOUD_ACCESS_KEY_ID` | 必须非空 |
| `ALIBABA_CLOUD_ACCESS_KEY_SECRET` | 必须非空 |
| `TINGWU_APP_KEY` | **必须设置！这是最常见的遗漏项** |
| `STORAGE_PROVIDER` | 必须为 `oss` |
| `STORAGE_BUCKET` | 必须非空 |
| `STORAGE_REGION` | 必须非空 |

**解决步骤**：

1. 检查 `.env` 文件是否在项目根目录
2. 确认 `TINGWU_APP_KEY` 已设置（这是最常见的问题！）
3. 重启服务器使配置生效

**验证配置**：

```bash
# 检查环境变量是否加载
curl http://127.0.0.1:8001/asr/providers

# 正确响应应该显示 "available": true
{
  "tingwu": {
    "available": true,
    ...
  }
}
```

### 问题 2：OSS 上传失败

**错误信息**：
```
OSS upload failed with status: 403
```

**可能原因**：
1. AccessKey 没有 OSS 权限
2. Bucket 名称或地域配置错误
3. 系统时间不同步

**解决方法**：
1. 检查 RAM 用户是否有 `AliyunOSSFullAccess` 权限
2. 确认 `STORAGE_BUCKET` 和 `STORAGE_REGION` 配置正确
3. 同步系统时间：`sudo ntpdate time.apple.com`

### 问题 3：AccessKey 无效

**错误信息**：
```
InvalidAccessKeyId.NotFound
```

**解决方法**：
1. 确认 AccessKey ID 和 Secret 复制正确（注意前后空格）
2. 检查 RAM 用户是否被禁用
3. 确认 AccessKey 没有被删除

### 问题 4：.env 文件未加载

**症状**：配置正确但服务仍报错

**解决方法**：

1. 确认 `.env` 文件在项目根目录（不是 `src/` 目录）
2. 确认安装了 `python-dotenv`：
   ```bash
   pip install python-dotenv
   ```
3. 重启服务器

---

## 相关链接

- [阿里云 RAM 用户创建](https://help.aliyun.com/zh/ram/user-guide/create-an-accesskey-pair)
- [OSS 快速入门](https://help.aliyun.com/zh/oss/getting-started/)
- [通义听悟文档](https://help.aliyun.com/zh/tingwu/)
- [通义听悟 SDK](https://github.com/aliyun/alibabacloud-python-sdk/tree/master/tingwu-20230930)
- [通义听悟 OpenAPI](https://next.api.aliyun.com/api/tingwu/2023-09-30/GetTaskInfo?lang=PYTHON)
