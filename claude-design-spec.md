# Claude / Anthropic 设计规范 (Design Specification)

> 基于 claude.ai、website.claude.com/blog、anthropic.com 等官方网站提取的完整设计系统。

---

## Design Tone (设计调性)

### 主调性：**Organic/Natural + Editorial/Magazine**

Claude/Anthropic 的设计语言是一种独特的 **"有机编辑"** 风格，融合了：

| 调性维度 | 特征描述 |
|----------|----------|
| **Organic/Natural** | 温暖的纸张色背景、自然主题插画（树木、叶片）、叶片形状的非对称圆角 |
| **Editorial/Magazine** | 衬线字体大标题、网格布局、清晰的信息层级、专业的排版细节 |
| **Refined/Luxury** | 精致的间距、克制的动效、高品质的视觉细节 |

### 设计哲学
- **人文科技 (Humanistic Technology)**: 温暖而非冰冷，像纸张而非金属
- **内容优先 (Content-First)**: 设计服务于阅读，不喧宾夺主
- **克制优雅 (Restrained Elegance)**: 少即是多，细节处见功夫

---

## 1. Typography (字体排印)

### 字体家族

```css
/* 主字体 - 用于正文、UI 元素 */
font-family: "Anthropic Sans", Arial, sans-serif;

/* 展示字体 - 用于大标题、装饰性文字 */
font-family: "Anthropic Serif", Georgia, serif;
```

### 字号体系

| 元素 | 字号 | 字重 | 行高 | 字体 | 用途 |
|------|------|------|------|------|------|
| Display XL | 62px | 700 | 1.1 | Anthropic Sans | 首页主标题 |
| Display L | 52px | 500 | 1.2 | Anthropic Serif | 文章标题、板块标题 |
| Display M | 32px | 600 | 1.1 | Anthropic Sans | 卡片标题、H2 |
| Heading | 24px | 600 | 1.3 | Anthropic Sans | H3、小标题 |
| Lead | 23px | 400 | 1.5 | Anthropic Sans | 文章导语、副标题 |
| Body | 20px | 400 | 1.6 | Anthropic Sans | 正文 |
| Small | 16px | 400 | 1.4 | Anthropic Sans | 元信息、日期 |
| Caption | 14px | 500 | 1.4 | Anthropic Sans | 标签、按钮 |

### 排版细节

```css
/* 正文排版 */
.body-text {
  font-size: 20px;
  line-height: 1.6;        /* 32px */
  letter-spacing: normal;
  color: #30302E;
}

/* 大标题排版 */
.display-heading {
  font-family: "Anthropic Serif", Georgia, serif;
  font-size: 52px;
  font-weight: 500;
  line-height: 1.2;        /* 62.4px */
  color: #141413;
}

/* 导语/副标题 */
.lead-text {
  font-size: 23px;
  line-height: 1.5;
  color: #5E5D59;          /* 较浅的灰色 */
}
```

---

## 2. Color & Theme (色彩与主题)

### 核心色板

```css
:root {
  /* ===== 背景色 ===== */
  --bg-primary: #FAF9F5;        /* 暖米色/纸张色 - 主背景 */
  --bg-secondary: #F5F4F0;      /* 略深的米色 - 卡片背景 */
  --bg-tertiary: #E8E6DC;       /* 浅灰褐 - 分割/边框 */
  --bg-dark: #191918;           /* 深炭黑 - Footer */

  /* ===== 文字色 ===== */
  --text-primary: #141413;      /* 深炭黑 - 主标题 */
  --text-body: #30302E;         /* 暗灰 - 正文 */
  --text-secondary: #5E5D59;    /* 中灰 - 副文字 */
  --text-tertiary: #8A8985;     /* 浅灰 - 辅助信息 */
  --text-inverse: #FAF9F5;      /* 反白文字 */

  /* ===== 品牌/强调色 ===== */
  --accent-orange: #DA7756;     /* 赭橙色 - 品牌标识、按钮 */
  --accent-terracotta: #C4653A; /* 赤陶色 - 插画、卡片 */
  --accent-rust: #B85A3B;       /* 铁锈红 - 深色强调 */

  /* ===== 功能色 ===== */
  --link: #141413;              /* 链接 - 与正文同色 */
  --link-hover: #DA7756;        /* 链接悬停 */
  --border: #E8E6DC;            /* 边框 */
  --divider: #E8E6DC;           /* 分割线 */

  /* ===== 插画配色 ===== */
  --illust-blue: #5B8FA8;       /* 灰蓝 */
  --illust-sage: #7A9B8A;       /* 灰绿 */
  --illust-sand: #D4C8B8;       /* 沙色 */
  --illust-cream: #F2EDE4;      /* 奶油色 */
}
```

### 配色原则

1. **主色调温暖中性**: `#FAF9F5` 背景贯穿始终，营造纸张质感
2. **文字层级分明**: 从 `#141413` 到 `#8A8985`，四级灰度
3. **强调色克制使用**: 橙色系仅用于 Logo、按钮、重要操作
4. **深色区域对比**: Footer 使用 `#191918`，形成呼吸节奏

---

## 3. Motion (动效)

### 动效原则
- **克制优雅**: 动效是功能性的，不是装饰性的
- **自然流畅**: 缓动曲线模拟自然物理运动
- **快速响应**: 保持界面的即时反馈感

### 动效参数

```css
:root {
  /* 时长 */
  --duration-fast: 150ms;
  --duration-normal: 200ms;
  --duration-slow: 300ms;
  --duration-emphasis: 400ms;

  /* 缓动曲线 */
  --ease-default: cubic-bezier(0.4, 0, 0.2, 1);
  --ease-in: cubic-bezier(0.4, 0, 1, 1);
  --ease-out: cubic-bezier(0, 0, 0.2, 1);
  --ease-spring: cubic-bezier(0.34, 1.56, 0.64, 1);
}
```

### 常用动效

```css
/* 链接/按钮悬停 */
.link, .button {
  transition: color var(--duration-fast) var(--ease-default),
              background-color var(--duration-fast) var(--ease-default),
              opacity var(--duration-fast) var(--ease-default);
}

/* 卡片悬停 */
.card {
  transition: transform var(--duration-normal) var(--ease-out),
              box-shadow var(--duration-normal) var(--ease-out);
}

.card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(20, 20, 19, 0.08);
}

/* 页面元素入场 */
.fade-in {
  animation: fadeIn var(--duration-slow) var(--ease-out);
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 错开入场动画 */
.stagger-item {
  animation: fadeIn var(--duration-slow) var(--ease-out) backwards;
}
.stagger-item:nth-child(1) { animation-delay: 0ms; }
.stagger-item:nth-child(2) { animation-delay: 50ms; }
.stagger-item:nth-child(3) { animation-delay: 100ms; }
.stagger-item:nth-child(4) { animation-delay: 150ms; }
```

---

## 4. Spatial Composition (空间构成)

### 网格系统

```css
/* 12列网格 */
.container {
  max-width: 1440px;
  margin: 0 auto;
  padding: 0 clamp(24px, 5vw, 80px);
}

/* 内容区宽度 */
.content-narrow { max-width: 720px; }   /* 文章正文 */
.content-medium { max-width: 960px; }   /* 一般内容 */
.content-wide { max-width: 1200px; }    /* 卡片网格 */
```

### 间距系统

```css
:root {
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 20px;
  --space-6: 24px;
  --space-8: 32px;
  --space-10: 40px;
  --space-12: 48px;
  --space-16: 64px;
  --space-20: 80px;
  --space-24: 96px;
}
```

### 间距应用

| 场景 | 间距 | 变量 |
|------|------|------|
| 页面板块间 | 80-96px | `--space-20` / `--space-24` |
| 卡片间距 | 24-32px | `--space-6` / `--space-8` |
| 元素内边距 | 24-32px | `--space-6` / `--space-8` |
| 段落间距 | 24px | `--space-6` |
| 紧凑间距 | 8-16px | `--space-2` / `--space-4` |

### 布局特征

```css
/* 编辑式布局 - 边框分割 */
.section {
  border-top: 1px solid var(--border);
  padding: var(--space-12) 0;
}

/* 文章布局 - 主内容 + 侧边栏 */
.article-layout {
  display: grid;
  grid-template-columns: 1fr 280px;
  gap: var(--space-16);
}

/* 卡片网格 */
.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: var(--space-8);
}
```

---

## 5. Backgrounds & Visual Details (背景与视觉细节)

### 标志性圆角 - 叶片形状 (Leaf Shape)

这是 Claude/Anthropic 设计中最具辨识度的视觉符号：**非对称圆角**，模拟叶片或水滴形状。

```css
/* 叶片圆角变体 */

/* 变体 A: 左上直角 */
.leaf-tl {
  border-radius: 0 16px 16px 16px;
}

/* 变体 B: 右上直角 */
.leaf-tr {
  border-radius: 16px 0 16px 16px;
}

/* 变体 C: 左下直角 */
.leaf-bl {
  border-radius: 16px 16px 16px 0;
}

/* 变体 D: 右下直角 */
.leaf-br {
  border-radius: 16px 16px 0 16px;
}

/* 大圆角版本 (用于大卡片) */
.leaf-lg {
  border-radius: 0 24px 24px 24px;
}
```

### 卡片样式

```css
/* 标准卡片 */
.card {
  background: var(--bg-secondary);
  border-radius: 0 16px 16px 16px;  /* 叶片形状 */
  padding: var(--space-6);
  border: none;                      /* 无边框 */
}

/* 带图片的特色卡片 */
.card-featured {
  background: var(--accent-terracotta);
  border-radius: 16px;
  overflow: hidden;
}

/* 浅色卡片 */
.card-light {
  background: var(--bg-primary);
  border: 1px solid var(--border);
  border-radius: 0 16px 16px 16px;
}
```

### 插画风格

- **主题**: 自然元素（树木、叶片、有机形状）
- **风格**: 简约扁平、几何化的自然物
- **配色**: 赭橙、灰蓝、灰绿、沙色
- **特点**: 与 UI 融为一体，非独立装饰

### 按钮样式

```css
/* 主按钮 */
.btn-primary {
  background: var(--text-primary);
  color: var(--text-inverse);
  padding: 12px 24px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  border: none;
  cursor: pointer;
  transition: opacity var(--duration-fast) var(--ease-default);
}

.btn-primary:hover {
  opacity: 0.9;
}

/* 次按钮 */
.btn-secondary {
  background: transparent;
  color: var(--text-primary);
  padding: 12px 24px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  border: 1px solid var(--border);
  cursor: pointer;
  transition: border-color var(--duration-fast) var(--ease-default);
}

.btn-secondary:hover {
  border-color: var(--text-primary);
}

/* 品牌色按钮 */
.btn-brand {
  background: var(--accent-orange);
  color: white;
  border-radius: 50%;  /* 圆形 - 用于发送按钮 */
}
```

---

## 6. Components (组件规范)

### 导航栏

```css
.navbar {
  background: var(--bg-primary);
  padding: var(--space-4) 0;
  position: sticky;
  top: 0;
  z-index: 100;
}

.nav-logo {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.nav-links {
  display: flex;
  gap: var(--space-8);
  font-size: 14px;
  font-weight: 500;
}

.nav-link {
  color: var(--text-primary);
  text-decoration: none;
  transition: opacity var(--duration-fast);
}

.nav-link:hover {
  opacity: 0.7;
}
```

### Footer

```css
.footer {
  background: var(--bg-dark);
  color: var(--text-inverse);
  padding: var(--space-16) 0;
}

.footer-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: var(--space-8);
}

.footer-heading {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: var(--space-4);
  color: var(--text-inverse);
}

.footer-link {
  font-size: 14px;
  color: rgba(250, 249, 245, 0.7);
  text-decoration: none;
  display: block;
  padding: var(--space-1) 0;
  transition: color var(--duration-fast);
}

.footer-link:hover {
  color: var(--text-inverse);
}

.footer-bottom {
  margin-top: var(--space-12);
  padding-top: var(--space-6);
  border-top: 1px solid rgba(250, 249, 245, 0.1);
  font-size: 14px;
  color: rgba(250, 249, 245, 0.5);
}
```

### 输入框

```css
.input {
  width: 100%;
  padding: var(--space-4) var(--space-5);
  font-size: 16px;
  font-family: inherit;
  background: var(--bg-primary);
  border: 1px solid var(--border);
  border-radius: 12px;
  color: var(--text-primary);
  transition: border-color var(--duration-fast),
              box-shadow var(--duration-fast);
}

.input:focus {
  outline: none;
  border-color: var(--text-primary);
  box-shadow: 0 0 0 1px var(--text-primary);
}

.input::placeholder {
  color: var(--text-tertiary);
}
```

---

## 7. 品牌标识 (Brand Identity)

### Claude Logo

```css
/* Claude 星形 Logo */
.claude-logo {
  color: var(--accent-orange);
  /* 使用 SVG 星形图标 */
}

/* 文字 Logo */
.claude-wordmark {
  font-family: "Anthropic Serif", Georgia, serif;
  font-size: 24px;
  font-weight: 500;
  color: var(--text-primary);
  letter-spacing: -0.02em;
}
```

### Anthropic Logo

```css
/* Anthropic 文字 Logo */
.anthropic-wordmark {
  font-family: "Anthropic Sans", Arial, sans-serif;
  font-size: 18px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-primary);
}
```

---

## 8. Responsive Design (响应式设计)

```css
/* 断点 */
@media (max-width: 1200px) {
  :root {
    --space-20: 64px;
    --space-24: 80px;
  }
}

@media (max-width: 768px) {
  :root {
    --space-16: 48px;
    --space-20: 48px;
  }

  .display-heading {
    font-size: 36px;
    line-height: 1.2;
  }

  body {
    font-size: 18px;
  }

  .article-layout {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 480px) {
  .container {
    padding: 0 16px;
  }

  .display-heading {
    font-size: 28px;
  }
}
```

---

## 9. Quick Reference (速查表)

### 核心色值

| 名称 | HEX | RGB | 用途 |
|------|-----|-----|------|
| Paper | `#FAF9F5` | 250, 249, 245 | 主背景 |
| Charcoal | `#141413` | 20, 20, 19 | 主文字 |
| Body | `#30302E` | 48, 48, 46 | 正文 |
| Secondary | `#5E5D59` | 94, 93, 89 | 副文字 |
| Border | `#E8E6DC` | 232, 230, 220 | 边框 |
| Orange | `#DA7756` | 218, 119, 86 | 品牌色 |
| Dark | `#191918` | 25, 25, 24 | Footer |

### 字体规范

| 用途 | 字体 | 大小 | 行高 |
|------|------|------|------|
| Display | Anthropic Serif | 52px | 1.2 |
| Heading | Anthropic Sans | 24px | 1.3 |
| Body | Anthropic Sans | 20px | 1.6 |
| Small | Anthropic Sans | 14px | 1.4 |

### 间距规范

| 级别 | 值 | 使用场景 |
|------|-----|----------|
| XS | 8px | 紧凑元素 |
| SM | 16px | 元素间距 |
| MD | 24px | 组件间距 |
| LG | 32px | 区块间距 |
| XL | 64px | 板块间距 |
| 2XL | 96px | 页面大分区 |

---

## 10. Design DNA 总结

1. **温暖纸张质感**: `#FAF9F5` 背景奠定整体调性
2. **双字体系统**: Sans (UI) + Serif (Display) 的经典组合
3. **叶片形状圆角**: 非对称圆角是最具辨识度的视觉符号
4. **自然主题插画**: 树木、叶片等有机元素融入设计
5. **宽松行高 (1.6)**: 重视阅读舒适度
6. **克制的强调色**: 橙色系仅用于关键操作
7. **编辑式布局**: 边框线分割、网格结构、专业排版
8. **深色 Footer 对比**: 形成视觉节奏和呼吸感

---

*Generated from claude.ai, website.claude.com, anthropic.com - December 2024*
