# 播客转写应用技术调研笔记

## 1. 音视频下载技术

### 1.1 yt-dlp
- **项目地址**: https://github.com/yt-dlp/yt-dlp
- **Star数**: 135k+
- **主要特性**:
  - 支持数千个网站的视频和音频下载（包括 YouTube、Spotify 等）
  - 命令行工具，也提供 Python API
  - 支持多种格式、多种认证方式
  - 支持下载直播、分段、章节拆分
  - 支持字幕、缩略图等元数据下载
  - 支持插件扩展

- **Python API 调用示例**:
```python
from yt_dlp import YoutubeDL
with YoutubeDL() as ydl:
    info = ydl.extract_info(URL, download=False)
```

- **技术要求**:
  - Python 3.10+ (CPython) 或 3.11+ (PyPy)
  - 推荐安装 ffmpeg、ffprobe

- **使用限制**:
  - 可能受网站反爬机制限制
  - 部分站点可能无法下载
  - 需要定期更新以应对网站变化

### 1.2 小宇宙播客下载
- **相关项目**: https://github.com/anfushuang/xiaoyuzhoufmdownload
- **技术方案**: 
  - 通过解析小宇宙网页获取音频链接
  - 直接下载音频文件
  - 可通过浏览器插件或自定义脚本实现

### 1.3 Spotify / Apple Podcasts
- **Spotify Web API**: https://developer.spotify.com/documentation/web-api
  - 提供官方 API 获取播客元数据
  - 但不直接提供音频下载功能
  - 需要结合 yt-dlp 或其他工具下载
  
- **Apple Podcasts**:
  - 基于 RSS feed 标准
  - 可通过解析 RSS 获取音频链接
  - 直接下载音频文件


## 2. 千问音视频转写 API

### 2.1 通义听悟 API
- **官方文档**: https://tingwu.aliyun.com/helpcenter/api
- **主要功能模块**:
  - **语音转写**: 支持中文、英文、粤语、中英混、日语，提供段落、句子划分和词级别时间戳
  - **说话人分离**: 区分对话中的不同说话人
  - **章节速览**: 自动分割章节、生成章节标题和摘要
  - **大模型摘要**: 全文摘要、发言总结、问答摘要
  - **智能纪要**: 提取关键词、待办事项、重点内容、识别场景
  - **PPT抽取和总结**: 抽取视频中的PPT并总结讲解内容
  - **文本翻译**: 中英、中日双向实时互译
  - **口语书面化**: 对转写结果进行润色

- **应用场景**: 会议记录、录音转写、面试、教学视频分析、访谈等

### 2.2 Qwen3-ASR (录音文件识别)
- **官方文档**: https://help.aliyun.com/zh/model-studio/qwen-speech-recognition
- **支持的模型**: 
  - **qwen3-asr-flash** (稳定版，推荐生产环境)
  - **qwen-audio-asr** (Beta版，仅供体验)

- **功能特性**:
  - **多语种识别**: 支持19种语言（普通话、粤语、四川话、闽南语、吴语、英语、日语、德语、韩语等）
  - **复杂环境适应**: 自动语种检测、智能非人声过滤
  - **歌唱识别**: 支持带BGM的歌曲转写
  - **上下文增强**: 通过提供上下文提高专有词汇识别准确率
  - **情感识别**: 识别惊讶、平静、愉快、悲伤、厌恶、愤怒、恐惧等情绪

- **技术参数**:
  - **支持的采样率**: 16kHz
  - **定价**: 0.00022元/秒
  - **免费额度**: 36,000秒（10小时），有效期90天
  - **上下文长度限制**: 不超过10000 Token

- **API调用方式**:
```python
import os
import dashscope

dashscope.base_http_api_url = 'https://dashscope.aliyuncs.com/api/v1'

messages = [
    {"role": "system", "content": [{"text": ""}]},  # 配置上下文
    {"role": "user", "content": [{"audio": "音频URL或本地文件"}]}
]
response = dashscope.MultiModalConversation.call(
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    model="qwen3-asr-flash",
    messages=messages,
    result_format="message",
    asr_options={
        "enable_itn": True
    }
)
```

- **支持的输入方式**:
  - 音频URL（需公网可访问）
  - 本地文件上传
  - 流式输出


### 2.3 API 返回格式

**返回体结构**:
- **request_id**: 唯一请求标识
- **output**: 调用结果信息
  - **choices**: 模型输出内容数组
    - **finish_reason**: 结束原因（stop、length等）
    - **message**: 模型输出的消息对象
      - **role**: 角色（assistant）
      - **content**: 输出内容数组
        - **text**: 语音识别结果文本
      - **annotations**: 标注信息数组（包含时间戳等）
        - **language**: 识别出的语言类型
        - **timestamps**: 时间戳信息（词级别或句子级别）
- **usage**: Token 使用情况
  - **input_tokens_details**: 输入 Token 详情
  - **output_tokens_details**: 输出 Token 详情

**时间戳信息**: 
- 返回的 annotations 中包含语言类型和时间戳
- 可用于生成 SRT 字幕文件
- 支持词级别和句子级别的时间戳


## 3. 技术可行性分析

### 3.1 音视频下载可行性

**YouTube 和主流视频平台**:
- yt-dlp 是成熟的开源工具，支持数千个网站
- 提供 Python API，易于集成到 Web 应用
- 支持多种格式和质量选择
- 活跃维护，Star 数 135k+
- **风险**: 可能受平台反爬限制，需定期更新

**小宇宙播客**:
- 可通过网页解析获取音频链接
- 已有开源项目验证可行性
- 相对简单，直接下载音频文件

**Spotify / Apple Podcasts**:
- Spotify 提供官方 API，但不直接提供下载
- Apple Podcasts 基于 RSS，可解析获取音频链接
- yt-dlp 也支持部分播客平台

**结论**: 技术可行，但需要针对不同平台采用不同策略

### 3.2 音视频转写可行性

**千问 API 优势**:
- 官方 API，稳定可靠
- 支持 19 种语言，覆盖主流播客语言
- 价格合理（0.00022元/秒），有免费额度
- 支持上下文增强，提高专有词汇识别准确率
- 返回时间戳信息，可生成 SRT 字幕

**技术限制**:
- 需要音频文件公网可访问或本地上传
- 采样率要求 16kHz
- 可能需要音频格式转换

**结论**: 完全可行，API 成熟稳定

### 3.3 整体架构可行性

**核心流程**:
1. 用户提交播客链接
2. 后端识别平台类型
3. 调用 yt-dlp 或自定义下载器获取音视频
4. 音频格式转换（如需要）
5. 上传到云存储或提供公网访问
6. 调用千问 API 进行转写
7. 解析返回结果，生成 SRT/Markdown 等格式
8. 返回给用户下载

**技术挑战**:
- 大文件处理和存储
- 异步任务管理
- 下载速度和稳定性
- API 调用成本控制

**结论**: 技术架构清晰，挑战可控

## 4. 技术栈推荐

### 4.1 前端技术栈

**推荐方案**: React + TypeScript + Tailwind CSS
- **React**: 成熟的前端框架，生态丰富
- **TypeScript**: 类型安全，提高代码质量
- **Tailwind CSS**: 快速构建现代 UI
- **状态管理**: Zustand 或 Redux Toolkit
- **UI 组件库**: shadcn/ui 或 Ant Design

**替代方案**: Vue 3 + TypeScript + Element Plus

### 4.2 后端技术栈

**推荐方案**: Node.js + Express/Fastify + TypeScript
- **Node.js**: 与前端技术栈统一，易于共享代码
- **Express/Fastify**: 成熟的 Web 框架
- **TypeScript**: 类型安全
- **yt-dlp**: 通过子进程调用
- **任务队列**: Bull (基于 Redis)

**替代方案**: Python + FastAPI
- **优势**: yt-dlp 原生 Python，集成更简单
- **FastAPI**: 现代、高性能的 Python Web 框架
- **任务队列**: Celery + Redis

### 4.3 数据库

**推荐方案**: PostgreSQL + Redis
- **PostgreSQL**: 存储用户数据、任务记录、转写结果
- **Redis**: 任务队列、缓存、会话管理

### 4.4 文件存储

**推荐方案**: 阿里云 OSS 或 AWS S3
- 存储下载的音视频文件
- 提供公网访问 URL 给千问 API
- 成本可控，按需付费

### 4.5 部署方案

**推荐方案**: Docker + 云服务器
- **前端**: Vercel 或 Netlify（静态部署）
- **后端**: 阿里云 ECS 或 AWS EC2
- **容器化**: Docker + Docker Compose
- **CI/CD**: GitHub Actions

### 4.6 音频处理

**推荐工具**: FFmpeg
- 音频格式转换
- 采样率调整（转为 16kHz）
- 音视频分离

## 5. 成本估算

### 5.1 千问 API 成本
- 价格: 0.00022元/秒
- 1小时音频: 3600秒 × 0.00022 = 0.792元
- 免费额度: 36,000秒（10小时）

### 5.2 存储成本
- 阿里云 OSS: 约 0.12元/GB/月
- 1小时音频约 50-100MB
- 100小时音频约 5-10GB，成本约 0.6-1.2元/月

### 5.3 服务器成本
- 阿里云 ECS 基础配置: 约 100-300元/月
- 可根据流量和用户量调整

