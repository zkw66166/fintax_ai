# AI智能问答前端重构计划

## Context

当前 fintax_ai 前端是一个简单的 Gradio UI（`app.py`, 280行），仅有文本输入框、Markdown 输出、管线详情折叠面板和历史下拉。目标是按照设计截图（"D:\fintax_ai\docs\AI智能问答财税咨询系统前端页面截图详细提示.md"）和技术文档（"D:\fintax_ai\docs\AI智能问答模块前端设计详细技术文档.md"），构建一个专业的企业级三栏布局 SaaS 界面，完整支持三条查询路由（税收优惠政策、法规知识库、财税数据）的前端展示。

**技术选型：React (Vite) + FastAPI**。用户确认选择 React 而非 Vanilla JS。保留原 `app.py` 作为开发/测试备用。JS 库通过 npm 安装（本地，非 CDN）。Header/Sidebar 导航等功能仅做 UI 占位，不实现后端逻辑。

## 文件结构

```
D:\fintax_ai\
├── app.py                              # (保留) Gradio UI :7861
├── api/                                # (新建) FastAPI 后端
│   ├── __init__.py
│   ├── main.py                         # FastAPI 入口, CORS, 静态文件挂载
│   ├── schemas.py                      # Pydantic 模型
│   └── routes/
│       ├── __init__.py
│       ├── chat.py                     # POST /api/chat (SSE 流式)
│       ├── history.py                  # GET/DELETE /api/chat/history
│       └── company.py                  # GET /api/companies
├── frontend/                           # (新建) React 应用
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html
│   └── src/
│       ├── main.jsx                    # ReactDOM 入口
│       ├── App.jsx                     # 根布局 (CSS Grid 三栏)
│       ├── App.module.css
│       ├── styles/
│       │   └── global.css              # CSS 变量, reset, 字体
│       ├── components/
│       │   ├── Header/                 # 顶部导航栏 (占位)
│       │   ├── Sidebar/                # 左侧菜单 (占位)
│       │   ├── ChatArea/               # 消息列表 + 自动滚动
│       │   ├── ChatMessage/            # 单条消息气泡 (用户/AI, 路由标签)
│       │   ├── ChatInput/              # 输入框 + 模式标签 + 提交
│       │   ├── ResultTable/            # 财务数据表格渲染
│       │   ├── PipelineDetail/         # 可折叠: 实体/意图/SQL
│       │   ├── HistoryPanel/           # 右侧历史面板
│       │   └── Footer/                 # 页脚 (占位)
│       ├── hooks/
│       │   ├── useSSE.js               # POST-based SSE 客户端 hook
│       │   └── useChatHistory.js       # localStorage 历史管理
│       ├── services/
│       │   └── api.js                  # API 客户端封装
│       └── utils/
│           └── sseParser.js            # ReadableStream SSE 解析器
├── mvp_pipeline.py                     # (不变)
├── modules/                            # (不变)
├── config/                             # (不变)
└── requirements.txt                    # 追加 fastapi, uvicorn
```

## 实施步骤

### Step 1: FastAPI 后端骨架

**修改文件**: `requirements.txt`
- 追加: `fastapi>=0.115.0`, `uvicorn[standard]>=0.30.0`

**新建文件**: `api/__init__.py`, `api/schemas.py`, `api/routes/__init__.py`

**新建 `api/main.py`**:
- FastAPI app 实例
- CORS 中间件（允许 Vite dev server `localhost:5173`）
- 注册路由: chat, history, company
- 生产模式: 挂载 `frontend/dist/` 为静态文件
- 复用 `app.py` 的 `ensure_db()` 确保数据库就绪
- 启动命令: `uvicorn api.main:app --reload --port 8000`

### Step 2: SSE 流式端点 (`api/routes/chat.py`)

核心：将同步 `run_pipeline_stream()` 生成器包装为 SSE `StreamingResponse`。

- POST `/api/chat` 接收 `ChatRequest(query: str)`
- Starlette 的 `StreamingResponse` 原生支持同步生成器（自动在线程池中运行）
- SSE 事件直接透传 pipeline 的三种事件类型：
  - `stage` → `event: stage\ndata: {route, text}`
  - `chunk` → `event: chunk\ndata: {text}`
  - `done` → `event: done\ndata: {完整 result 对象}`
- 不做事件类型转换，前端直接处理 stage/chunk/done

关键文件：`D:\fintax_ai\mvp_pipeline.py:30-89` (`run_pipeline_stream`)

### Step 3: 历史与企业 API

**`api/routes/history.py`**: 复用 `app.py` 的 JSON 文件持久化逻辑
- GET `/api/chat/history?limit=100` → 返回历史列表
- DELETE `/api/chat/history` body `{ids: [...]}` → 删除指定条目

**`api/routes/company.py`**: 从 `taxpayer_info` 表查询
- GET `/api/companies` → `[{taxpayer_id, taxpayer_name, taxpayer_type}]`

### Step 4: React 项目初始化

```bash
cd D:\fintax_ai
npm create vite@latest frontend -- --template react
cd frontend
npm install react-markdown chart.js react-chartjs-2
```

**`frontend/vite.config.js`**:
- `server.proxy`: `/api` → `http://localhost:8000`（开发时代理到 FastAPI）
- `build.outDir`: `dist`

**npm 依赖**:
- `react`, `react-dom` (Vite 模板自带)
- `react-markdown` — Markdown 渲染（替代 marked.js，React 生态更好）
- `chart.js` + `react-chartjs-2` — 图表（本期仅安装，stub 实现）

**CSS 方案**: CSS Modules (`.module.css`)，无需额外依赖

### Step 5: 页面布局组件

**`App.jsx`** — CSS Grid 三栏布局:
```
grid-template: "header header header" 56px
               "sidebar main history" 1fr
               "footer footer footer" 36px
             / 220px 1fr 280px;
```

**`Header.jsx`** (UI 占位):
- 左: 公文包图标 + "智能财税咨询系统" + 英文副标题
- 中: 企业选择器 `<select>`（从 `/api/companies` 加载）
- 右: 时钟（`setInterval` 每秒更新）、通知铃铛(静态角标"3")、"超级管理员"文字、退出图标

**`Sidebar.jsx`** (UI 占位):
- 菜单项: 工作台、AI智问(高亮)、企业画像、数据管理、系统设置
- 仅 AI智问 可交互，其余 disabled

**`Footer.jsx`** (UI 占位):
- "© 2024 智能财税咨询系统" + "版本 v1.0.0 | 帮助中心 | 技术支持"

### Step 6: SSE 客户端 + 聊天核心

**`utils/sseParser.js`** — ReadableStream SSE 解析器:
- `async function* parseSSE(response)` — 从 fetch Response 解析 SSE 事件
- 处理 `event:` 和 `data:` 行，yield `{event, data}` 对象
- 正确处理 UTF-8 多字节字符（`TextDecoder` with `stream: true`）

**`hooks/useSSE.js`** — React Hook:
- `startStream(query, onEvent)` — fetch POST `/api/chat` + 解析 SSE
- `cancel()` — AbortController 取消请求
- `isStreaming` 状态

**`ChatArea.jsx`** — 消息列表:
- 消息状态数组: `[{id, role, content, route, status, chunks[], result, pipelineDetail}]`
- SSE `onEvent` 回调:
  - `stage` → 创建 AI 消息，设置 route，显示 loading
  - `chunk` → 追加到 chunks[]，实时渲染 Markdown
  - `done` → 设置 status='done'，存储完整 result
- 智能滚动：仅当用户在底部时自动滚动
- 标题栏: "AI智能问答" + "清空对话"/"导出PDF" 按钮

**`ChatMessage.jsx`** — 单条消息:
- 用户消息: 浅蓝背景 `#eff6ff`，右对齐时间戳
- AI 消息: 白底卡片，顶部路由标签:
  - `financial_data` → 📊 蓝色标签
  - `tax_incentive` → 📋 橙色标签
  - `regulation` → 🤖 紫色标签
- 流式内容: `react-markdown` 渲染 chunks.join('') + ▌ 光标
- 完成后: 根据 route 渲染不同内容（见 Step 7）

**`ChatInput.jsx`** — 输入区:
- `<textarea>` maxLength=500, Enter 发送 / Shift+Enter 换行
- 免责声明文字
- 回答模式标签: 图文/纯数据/简报（视觉切换，本期不影响后端）
- 字数统计 "0/500字符"
- 蓝色 "提交咨询" 按钮（流式中显示 "取消" 按钮）

### Step 7: 三条路由的前端渲染

**tax_incentive（税收优惠政策）— 完整实现**
- 路由标签: 📋 本地知识库查询结果
- 流式显示 LLM 摘要（`react-markdown` 渲染 chunks，带 ▌ 光标）
- done 后显示 "找到 N 条相关政策" 提示（从 `result.result_count`）
- Markdown 内容包含: 政策标题、关键优惠、适用条件等结构化信息

**regulation（法规知识库）— 完整实现**
- 路由标签: 🤖 法规知识库
- 流式显示 Coze RAG 回答（同上 Markdown 流式渲染）
- done 后完整显示

**financial_data（财税数据）— 基本输出**
- 路由标签: 📊 财务数据查询
- 非流式: 等待 done 事件后一次性渲染
- `ResultTable` 组件: HTML `<table>` 带斑马纹、横向滚动、数字右对齐
- 显示 "查询成功（N 行）" 提示
- 错误/澄清状态正常显示
- `PipelineDetail` 可折叠面板: 实体识别 JSON、意图解析 JSON、生成 SQL
- 图表/趋势: 本期不实现，`chart.js` 仅安装备用

### Step 8: 历史面板

**`hooks/useChatHistory.js`**:
- 从 `/api/chat/history` 加载历史
- 新查询完成后 POST 保存
- 提供 delete 方法

**`HistoryPanel.jsx`** — 右侧面板:
- 标题 "历史记录" + 红色 "删除历史" 链接
- 复选框列表，每项显示查询文本
- 点击条目 → 在消息区显示该历史对话
- 勾选 + 删除 → DELETE 请求

### Step 9: 收尾

- "导出PDF": `window.print()` + `@media print` 样式
- 实时时钟: Header 中 `setInterval` 每秒更新
- 企业选择器: 页面加载时 GET `/api/companies` 填充
- 键盘快捷键: Enter 发送, Shift+Enter 换行, Escape 取消流式

## 开发工作流

```bash
# 终端 1: FastAPI 后端
cd D:\fintax_ai
uvicorn api.main:app --reload --port 8000

# 终端 2: React 开发服务器
cd D:\fintax_ai\frontend
npm run dev    # Vite :5173, 代理 /api → :8000

# 生产部署
cd D:\fintax_ai\frontend && npm run build
# FastAPI 自动挂载 frontend/dist/ 为静态文件
uvicorn api.main:app --port 8000
```

## 关键文件引用

| 文件 | 用途 |
|------|------|
| `mvp_pipeline.py:30-89` | `run_pipeline_stream()` — SSE 端点包装的数据源 |
| `app.py:100-138` | `_format_result()` — 结果格式化逻辑参考 |
| `app.py:20-41` | `_load_history()`/`_save_history()` — 历史持久化复用 |
| `modules/tax_incentive_query.py:368-430` | `search_stream()` — 税收优惠流式接口 |
| `modules/regulation_api.py:147-256` | `query_regulation_stream()` — 法规流式接口 |
| `config/settings.py` | 所有配置常量 |

## 验证方案

1. `pip install -r requirements.txt` 安装 Python 新依赖
2. `cd frontend && npm install && npm run build` 构建 React 应用
3. `uvicorn api.main:app --port 8000` 启动服务
4. 浏览器访问 `http://localhost:8000`，验证三栏布局
5. 测试税收优惠: "加计扣除政策有哪些" → 流式显示政策摘要 + 路由标签
6. 测试法规知识库: "出口退税需要申请吗" → 流式显示 Coze 回答
7. 测试财税数据: "查询华兴科技2025年1月的销项税额" → 表格显示
8. 验证历史面板: 查询后右侧出现记录，可点击回看，可勾选删除
9. 验证企业选择器: 下拉显示企业列表
10. 原 Gradio UI 仍可通过 `python app.py`（:7861）正常使用
