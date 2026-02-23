         
# AI 智能问答模块前端设计详细技术文档

## 重要说明：本文档所引用的脚本文件和项目结构是另外一个项目的copy，应用到本fintax项目时需要根据fintax项目的实际情况重新规划和变更！

## 一、架构概览

### 1.1 组件关系图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           AIChat.jsx                                    │
│                      (主页面容器组件)                                    │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────┐    ┌─────────────────────┐                    │
│  │    ChatWidget       │    │   历史记录面板      │                    │
│  │  (聊天显示组件)     │    │   (右侧边栏)       │                    │
│  ├─────────────────────┤    │                    │                    │
│  │ - 消息列表渲染      │    │ - 历史记录列表      │                    │
│  │ - Markdown 解析     │    │ - 选择删除功能      │                    │
│  │ - 图表渲染         │    │ - 点击加载功能      │                    │
│  │ - 流式响应展示     │    │                    │                    │
│  └─────────────────────┘    └─────────────────────┘                    │
│            │                                                      │       │
│            ▼                                                      ▼       │
│  ┌──────────────────────────────────────────────────────────────┐     │
│  │                    ChartRenderer.jsx                          │     │
│  │                    (图表渲染组件)                               │     │
│  └──────────────────────────────────────────────────────────────┘     │
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────┐     │
│  │                    api.js (services)                          │     │
│  │                    (API 通信服务)                              │     │
│  └──────────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                          ┌─────────────────┐
                          │   FastAPI       │
                          │  /api/chat      │
                          └─────────────────┘
```

### 1.2 文件结构

```
frontend/src/
├── components/
│   ├── AIChat.jsx           # 主页面组件（容器）
│   ├── ChatWidget.jsx       # 聊天显示组件
│   ├── ChartRenderer.jsx    # 图表渲染组件
│   └── *.css               # 样式文件
└── services/
    └── api.js               # API 通信服务
```

---

## 二、核心组件详解

### 2.1 AIChat.jsx - 主页面组件

文件位置: [frontend/src/components/AIChat.jsx](file:///d:/MyProjects/MCP_coze/frontend/src/components/AIChat.jsx)

#### 状态管理

```javascript
const [messages, setMessages] = useState([]);           // 消息列表
const [isLoading, setIsLoading] = useState(false);    // 加载状态
const [history, setHistory] = useState([]);           // 历史记录
const [inputText, setInputText] = useState('');      // 输入文本
const [currentController, setCurrentController] = useState(null); // AbortController
const [responseMode, setResponseMode] = useState('detailed'); // 回答模式
const [isSelectionMode, setIsSelectionMode] = useState(false); // 选择模式
const [selectedMessageIndices, setSelectedMessageIndices] = useState(new Set()); // 选中消息
```

#### 回答模式

| 模式 | 值 | 功能 |
|------|-----|------|
| 图文模式 | `detailed` | 显示数据表格 + 图表 + AI分析 |
| 纯数据模式 | `standard` | 显示数据表格 + AI分析（无图表） |
| 简报模式 | `concise` | 仅显示 AI 文字总结 |

#### 核心功能

1. **流式聊天** - 使用 `streamChat` API 实现 SSE 流式响应 【本项目已实现响应，如果需要优化则参照此文档更改】
2. **历史记录** - 从后端加载并管理对话历史
3. **消息管理** - 选择、删除、导出 PDF
4. **输入处理** - 支持 Enter 发送、Shift+Enter 换行

---

### 2.2 ChatWidget.jsx - 聊天显示组件

文件位置: [frontend/src/components/ChatWidget.jsx](file:///d:/MyProjects/MCP_coze/frontend/src/components/ChatWidget.jsx)

#### 渲染流程

```javascript
// 消息数据结构
{
    role: 'user' | 'assistant',
    content: '...',           // Markdown 内容
    charts: [...],            // 图表数据数组
    summary: '...',          // 分析总结
    route: 'financial' | 'tax_incentive' | 'coze',  // 路由来源
    timestamp: '12:30:45'    // 时间戳
}
```

#### 渲染逻辑

```javascript
const renderMessageContent = (msg, index) => {
    return (
        <>
            {/* 1. Markdown 内容 */}
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {content}
            </ReactMarkdown>

            {/* 2. 图表渲染 */}
            {showChart && charts.map((chartData, idx) => (
                <ChartRenderer
                    key={idx}
                    chartData={chartData}
                    canvasId={`chart-canvas-${index}-${idx}`}
                />
            ))}

            {/* 3. 分析总结 */}
            {summary && (
                <div className="summary-section">
                    <ReactMarkdown>{summary}</ReactMarkdown>
                </div>
            )}
        </>
    );
};
```

#### 路由标签显示

```javascript
{msg.route && (
    <span className={`route-badge ${msg.route}`}>
        {msg.route === 'financial' && '📊 财务数据'}
        {msg.route === 'tax_incentive' && '📋 税收优惠'}
        {msg.route === 'coze' && '🤖 知识库'}
    </span>
)}
```

---

### 2.3 api.js - API 通信服务

文件位置: [frontend/src/services/api.js](file:///d:/MyProjects/MCP_coze/frontend/src/services/api.js)

#### 流式聊天函数

```javascript
export function streamChat(question, companyId, responseMode, {
    onMessage,      // 收到消息内容回调
    onRoute,        // 路由事件回调
    onChart,        // 图表数据回调
    onSummary,      // 分析总结回调
    onError,        // 错误回调
    onDone          // 完成回调
}) {
    const controller = new AbortController();
    
    // 发送请求...
    // 解析 SSE 事件...
    
    return controller;  // 返回 AbortController 用于取消请求
}
```

#### SSE 事件处理

```javascript
// 事件类型
if (currentEvent === 'chart') {
    onChart?.(data);              // 图表数据
} else if (currentEvent === 'summary') {
    onSummary?.(data.content);    // 分析总结
} else if (data.content !== undefined) {
    onMessage?.(data.content);    // 普通消息
}

if (data.path !== undefined) {
    onRoute?.(data.path, data.company);  // 路由信息
}
```

---

## 三、SSE 事件协议

### 3.1 事件类型

| 事件名 | 数据格式 | 说明 |
|--------|----------|------|
| `start` | `{status: "processing"}` | 开始处理 |
| `route` | `{path: "financial", company: "公司名"}` | 路由信息 |
| `message` | `{content: "..."}` | 消息内容（流式） |
| `chart` | `{chartType: "bar", ...}` | 图表数据 |
| `summary` | `{content: "..."}` | 分析总结 |
| `error` | `{message: "错误信息"}` | 错误信息 |
| `done` | `{status: "completed"}` | 完成 |

### 3.2 响应示例

```
event: start
data: {"status": "processing"}

event: route
data: {"path": "financial", "company": "ABC公司"}

event: message
data: {"content": "📊 **企业财务数据查询**\n\n"}

event: message
data: {"content": "📋 ABC公司 2023年销售额: 1,000万元\n"}

event: chart
data: {"chartType": "bar", "title": "ABC公司 销售额趋势", ...}

event: summary
data: {"content": "\n**分析总结**:\n2023年销售额同比增长..."}

event: done
data: {"status": "completed"}
```

---

## 四、前端交互流程

### 4.1 发送消息流程

```
用户输入问题
    │
    ▼
┌─────────────────┐
│ handleSend()   │  1. 添加用户消息到列表
│                 │  2. 添加空 assistant 消息占位
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ streamChat()    │  1. 调用 /api/chat
│                 │  2. 建立 SSE 连接
└────────┬────────┘
         │
         ▼
    ┌─────────────────────────────────┐
    │     SSE 事件循环                │
    │  - onMessage: 追加内容          │
    │  - onRoute: 更新路由标签        │
    │  - onChart: 渲染图表            │
    │  - onSummary: 追加总结          │
    └────────────┬────────────────────┘
                 │
                 ▼
┌─────────────────┐
│ onDone()       │  设置 isLoading = false
└─────────────────┘
```

### 4.2 消息数据结构

```javascript
// 用户消息
{
    role: 'user',
    content: 'ABC公司2023年销售额是多少？',
    timestamp: '14:30:25'
}

// AI 回复（路由到财务数据库）
{
    role: 'assistant',
    content: '📊 **企业财务数据查询**\n\n📋 ABC公司 2023年销售额: 1,000万元\n',
    charts: [
        {
            chartType: 'bar',
            title: 'ABC公司 销售额趋势',
            labels: ['2021', '2022', '2023'],
            datasets: [...]
        }
    ],
    summary: '\n**分析总结**:\n2023年销售额同比增长20%...',
    route: 'financial',
    timestamp: '14:30:28'
}
```

---

## 五、图表渲染

### 5.1 ChartRenderer 组件

文件位置: [frontend/src/components/ChartRenderer.jsx](file:///d:/MyProjects/MCP_coze/frontend/src/components/ChartRenderer.jsx)

```javascript
// 支持的图表类型
const chartTypes = {
    'bar': '柱状图',
    'line': '折线图',
    'pie': '饼图',
    'combo': '组合图(柱+线)',
    'radar': '雷达图'
};
```

### 5.2 图表数据结构

```javascript
// 柱状图示例
{
    chartType: 'bar',
    title: 'ABC公司 销售额趋势分析',
    labels: ['2021年', '2022年', '2023年'],
    datasets: [
        {
            type: 'bar',
            label: '销售额(万元)',
            data: [800, 950, 1200],
            backgroundColor: 'rgba(54, 162, 235, 0.8)',
            borderColor: 'rgba(54, 162, 235, 1)'
        }
    ]
}

// 组合图示例（柱+线）
{
    chartType: 'combo',
    title: 'ABC公司 利润率趋势分析',
    labels: ['2021年', '2022年', '2023年'],
    datasets: [
        {type: 'bar', label: '利润率(%)', data: [5.2, 6.1, 7.8], yAxisID: 'y'},
        {type: 'line', label: '增长率(%)', data: [null, 17.3, 27.9], yAxisID: 'y1'}
    ],
    options: {
        scales: {
            y: {type: 'linear', position: 'left'},
            y1: {type: 'linear', position: 'right', grid: {drawOnChartArea: false}}
        }
    }
}
```

---

## 六、消息管理功能

### 6.1 选择模式

```javascript
// 进入选择模式
const toggleSelectionMode = () => {
    setIsSelectionMode(prev => !prev);
    setSelectedMessageIndices(new Set());
};

// 切换单条消息选中
const toggleMessageSelection = (index) => {
    setSelectedMessageIndices(prev => {
        const newSet = new Set(prev);
        if (newSet.has(index)) {
            newSet.delete(index);
        } else {
            newSet.add(index);
        }
        return newSet;
    });
};
```

### 6.2 删除消息

```javascript
const handleDeleteSelectedMessages = async () => {
    const idsToDelete = messages
        .filter((_, index) => selectedMessageIndices.has(index))
        .map(msg => msg.id)
        .filter(id => id);  // 过滤掉没有 id 的
    
    await fetch('/api/chat/history', {
        method: 'DELETE',
        body: JSON.stringify({ message_ids: idsToDelete })
    });
    
    // 更新本地状态
    setMessages(prev => prev.filter((_, i) => !selectedMessageIndices.has(i)));
};
```

### 6.3 导出 PDF

```javascript
const handleExportPDF = async () => {
    // 1. 创建打印窗口
    const printWindow = window.open('', '_blank');
    
    // 2. 生成 HTML 内容
    let htmlContent = `<html><head>...</head><body>`;
    
    messages.forEach((msg, index) => {
        if (msg.role === 'user') {
            htmlContent += `<div class="user">...</div>`;
        } else {
            // 渲染 Markdown
            htmlContent += `<div class="assistant">${marked.parse(msg.content)}</div>`;
            
            // 渲染图表（转换为图片）
            if (msg.charts) {
                const canvas = document.getElementById(`chart-canvas-${index}-0`);
                if (canvas) {
                    const imgData = canvas.toDataURL('image/png');
                    htmlContent += `<img src="${imgData}">`;
                }
            }
        }
    });
    
    // 3. 写入并打印
    printWindow.document.write(htmlContent);
    printWindow.print();
};
```

---

## 七、历史记录管理

### 7.1 加载历史

```javascript
const fetchHistory = async () => {
    const res = await fetch('/api/chat/history?limit=100');
    const data = await res.json();
    
    // 转换数据格式
    const formatted = data.map(msg => ({
        id: msg.id,
        role: msg.role,
        content: msg.content,
        charts: extractCharts(msg.content),  // 从 <CHART_DATA> 提取
        summary: extractSummary(msg.content),
        timestamp: new Date(msg.created_at).toLocaleTimeString()
    }));
    
    setMessages(formatted);
    
    // 提取唯一问题作为历史列表
    const userQuestions = formatted
        .filter(m => m.role === 'user')
        .map(m => m.content)
        .reverse();
    setHistory([...new Set(userQuestions)]);
};
```

### 7.2 循环定位

```javascript
// 点击历史记录时，循环定位所有匹配的回答
const handleHistoryClick = (question) => {
    // 找到所有包含该问题的消息索引
    const indices = messages
        .map((msg, idx) => msg.role === 'user' && msg.content === question ? idx : -1)
        .filter(idx => idx !== -1);
    
    // 循环切换：上一次 → 上一次的上一次 → ... → 最新 → 循环
    const currentNav = historyNavRef.current[question];
    let targetIndex;
    
    if (indices.length === 1) {
        targetIndex = indices[0];
    } else {
        const currentPos = indices.indexOf(currentNav);
        if (currentPos <= 0) {
            targetIndex = indices[indices.length - 1];  // 回到最新
        } else {
            targetIndex = indices[currentPos - 1];  // 上一个
        }
    }
    
    historyNavRef.current[question] = targetIndex;
    chatWidgetRef.current.scrollToMessage(targetIndex);
};
```

---

## 八、样式与交互

### 8.1 CSS 文件

| 文件 | 作用 |
|------|------|
| `AIChat.css` | 主页面布局、输入框、历史面板 |
| `ChatWidget.css` | 消息样式、路由标签、加载动画 |

### 8.2 关键样式类

```css
/* 消息容器 */
.chat-message { }
.chat-message.user { }     /* 用户消息 - 右侧 */
.chat-message.assistant { } /* AI 消息 - 左侧 */

/* 路由标签 */
.route-badge { padding: 2px 8px; border-radius: 4px; }
.route-badge.financial { background: #e0f2fe; color: #0284c7; }
.route-badge.tax_incentive { background: #fef3c7; color: #d97706; }
.route-badge.coze { background: #f3e8ff; color: #9333ea; }

/* 加载动画 */
.loading-indicator { display: flex; gap: 4px; }
.loading-dot {
    width: 8px; height: 8px;
    background: #3b82f6;
    border-radius: 50%;
    animation: bounce 1.4s infinite ease-in-out both;
}
```

---

## 九、性能优化

### 9.1 智能滚动

```javascript
// 检测用户是否在底部
const handleScroll = () => {
    const { scrollTop, scrollHeight, clientHeight } = container;
    isUserAtBottomRef.current = scrollHeight - scrollTop - clientHeight < 50;
};

// 仅当用户在底部时才自动滚动
if (isUserAtBottomRef.current) {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
}
```

### 9.2 消息引用优化

```javascript
const messageRefs = useRef([]);

// 跳转定位
const scrollToMessage = (index) => {
    messageRefs.current[index]?.scrollIntoView({
        behavior: 'smooth',
        block: 'start'
    });
};
```

### 9.3 AbortController 取消请求

```javascript
// 发送请求前取消上一个请求
if (currentController) {
    currentController.abort();
}

const controller = streamChat(...);
setCurrentController(controller);
```

---

## 十、API 请求示例

### 10.1 请求

```javascript
// POST /api/chat
{
    question: "ABC公司2023年销售额是多少？",
    company_id: 1,
    enable_routing: true,
    show_chart: true,
    response_mode: "detailed"
}
```

### 10.2 响应 (SSE)

```
event: route
data: {"path": "financial", "company": "ABC公司"}

event: message
data: {"content": "📊 **企业财务数据查询**\n\n"}

event: message
data: {"content": "📋 ABC公司 2023年销售额: 1,000万元\n"}

event: chart
data: {"chartType": "bar", "title": "...", ...}

event: done
data: {"status": "completed"}
```

---

## 十一、扩展开发

### 11.1 添加新组件

```javascript
// 1. 在 AIChat.jsx 中导入
import NewComponent from './NewComponent';

// 2. 在 renderMessageContent 中添加
{msg.newField && <NewComponent data={msg.newField} />}
```

### 11.2 添加新事件

```javascript
// 后端发送新事件
yield send_event("custom_event", {data: "..."});

// 前端处理
if (currentEvent === 'custom_event') {
    onCustom?.(data);
}
```

---

本技术文档详细介绍了 AI 智能问答模块的前端设计实现，涵盖组件架构、数据流、交互逻辑、样式处理等各个方面。