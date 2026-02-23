# AI智能咨询前端交互技术文档

## 重要说明
1. 本文档是copy自D:\MyProjects\MCP_coze项目，不可照搬到fintax_ai项目，而是要根据fintax_ai项目实际情况参考借鉴其实现的功能
2. 本文档中的脚本、项目结构以及数据库名称和结构都copy自供参考项目

---

## 一、页面概述

AI智能咨询前端是税务智能咨询系统的用户交互界面，基于 React 技术栈构建，通过 SSE（Server-Sent Events）实现与后端的实时通信，支持流式响应、图表展示、消息管理等功能。

### 1.1 核心组件

| 组件 | 文件路径 | 功能 |
|------|----------|------|
| AIChat | `frontend/src/components/AIChat.jsx` | 主页面组件，负责整体交互逻辑 |
| ChatWidget | `frontend/src/components/ChatWidget.jsx` | 聊天消息渲染组件 |
| ChartRenderer | `frontend/src/components/ChartRenderer.jsx` | 图表渲染组件 |
| API 服务 | `frontend/src/services/api.js` | SSE 流式请求封装 |

### 1.2 页面布局

```
┌─────────────────────────────────────────────────────────────────┐
│  💬 AI智能问答                              清空对话 │ 导出PDF │  ← 页面标题栏
├───────────────────────────────────────────────┬─────────────────┤
│                                               │                 │
│                                               │  📜 历史记录    │
│           聊天消息区域                         │  [搜索历史...]  │
│           (ChatWidget)                        │  □ 问题1       │
│                                               │  □ 问题2       │
│                                               │  □ 问题3       │
│                                               │       删除历史  │
├───────────────────────────────────────────────┴─────────────────┤
│  请输入要咨询的财务指标...                     ✨ 提交咨询      │  ← 输入区域
│  [📊图文] [📑纯数据] [📝简报] [⚙️管理消息]                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 二、交互功能详解

### 2.1 回答模式切换（图文/纯数据/简报）

**位置**: 输入区域工具栏

**功能**: 切换 AI 回答的展示模式

**代码位置**: `AIChat.jsx`，行号 564-586

```jsx
<div className="mode-toggle">
    <span
        className={`mode-opt ${responseMode === 'detailed' ? 'active' : ''}`}
        onClick={() => setResponseMode('detailed')}
        title="全量模式：显示数据表格、图表和AI分析"
    >
        📊 图文
    </span>
    <span
        className={`mode-opt ${responseMode === 'standard' ? 'active' : ''}`}
        onClick={() => setResponseMode('standard')}
        title="数据模式：显示数据表格和AI分析，不显示图表"
    >
        📑 纯数据
    </span>
    <span
        className={`mode-opt ${responseMode === 'concise' ? 'active' : ''}`}
        onClick={() => setResponseMode('concise')}
        title="简报模式：仅显示AI文字总结"
    >
        📝 简报
    </span>
</div>
```

**三种模式说明**:

| 模式 | 值 | 展示内容 |
|------|-----|----------|
| 图文 | `detailed` | 表格 + 图表 + AI分析总结 |
| 纯数据 | `standard` | 表格 + AI分析总结（无图表） |
| 简报 | `concise` | 仅 AI 文字总结（无表格无图表） |

**后端处理**: `server/routers/chat.py`，行号 572-830

```python
# 1. 生成表格 (详细/标准模式)
if response_mode in ["detailed", "standard"]:
    formatted = financial_query.format_results(results, company)
    yield send_content(formatted)

# 2. 生成图表 (仅详细模式)
if response_mode == "detailed":
    # 发送图表数据...

# 3. AI分析总结 (所有模式)
if response_mode in ["detailed", "standard"]:
    # 发送分析总结...

# 4. 简报模式 (concise)
elif response_mode == "concise":
    # 仅生成自然语言总结，无表格无图表
    raw_data_text = ...
    prompt = f"请根据以下财务查询结果，直接回答用户问题..."
```

---

### 2.2 管理消息

**位置**: 输入区域工具栏

**功能**: 进入消息选择模式，支持批量删除消息

**代码位置**: `AIChat.jsx`，行号 229-287

#### 2.2.1 进入选择模式

```jsx
// 切换选择模式
const toggleSelectionMode = useCallback(() => {
    setIsSelectionMode(prev => !prev);
    setSelectedMessageIndices(new Set()); // 进入或退出都重置选择
}, []);
```

#### 2.2.2 选择消息

```jsx
// 切换单条消息选中
const toggleMessageSelection = useCallback((index) => {
    setSelectedMessageIndices(prev => {
        const newSet = new Set(prev);
        if (newSet.has(index)) {
            newSet.delete(index);
        } else {
            newSet.add(index);
        }
        return newSet;
    });
}, []);
```

#### 2.2.3 删除选中的消息

```jsx
const handleDeleteSelectedMessages = useCallback(async () => {
    if (selectedMessageIndices.size === 0) return;

    if (window.confirm(`确定删除选中的 ${selectedMessageIndices.size} 条消息吗？`)) {
        // 获取选中消息的 ID
        const idsToDelete = [];
        const indices = Array.from(selectedMessageIndices);
        indices.forEach(idx => {
            if (messages[idx] && messages[idx].id) {
                idsToDelete.push(messages[idx].id);
            }
        });

        // 调用后端 API 删除
        if (idsToDelete.length > 0) {
            await fetch('/api/chat/history', {
                method: 'DELETE',
                headers: { 'Authorization': `Bearer ${token}` },
                body: JSON.stringify({ message_ids: idsToDelete, target: 'chat' })
            });
        }

        // 更新前端状态
        setMessages(prev => prev.filter((_, index) => !selectedMessageIndices.has(index)));
        setIsSelectionMode(false);
        setSelectedMessageIndices(new Set());
    }
}, [selectedMessageIndices, messages]);
```

#### 2.2.4 选择模式 UI

```jsx
{isSelectionMode ? (
    <div className="input-section selection-bar">
        <div className="selection-info">
            已选择 <strong>{selectedMessageIndices.size}</strong> 条消息
        </div>
        <div className="selection-actions">
            <button className="select-action-btn cancel" onClick={toggleSelectionMode}>
                取消
            </button>
            <button
                className="select-action-btn delete"
                onClick={handleDeleteSelectedMessages}
                disabled={selectedMessageIndices.size === 0}
            >
                🗑️ 删除选中
            </button>
        </div>
    </div>
) : (
    // 正常输入区域
)}
```

---

### 2.3 清空对话

**位置**: 页面标题栏右侧

**功能**: 清空当前会话的所有消息

**代码位置**: `AIChat.jsx`，行号 203-226

```jsx
const handleClear = useCallback(async () => {
    if (window.confirm('确定要清空所有对话吗？此操作无法撤销。')) {
        if (currentController) currentController.abort();

        try {
            const token = localStorage.getItem('access_token');
            await fetch('/api/chat/history', {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': token ? `Bearer ${token}` : ''
                },
                body: JSON.stringify({ delete_all: true, target: 'chat' })
            });
            setMessages([]);
            setIsLoading(false);
            setIsSelectionMode(false);
            setSelectedMessageIndices(new Set());
        } catch (e) {
            alert('删除失败');
        }
    }
}, [currentController]);
```

**后端 API**: `DELETE /api/chat/history`

```python
@router.delete("/chat/history")
async def delete_chat_history(request: Request, body: dict = Body(...)):
    target = body.get('target', 'chat')
    
    if body.get('delete_all'):
        # 删除所有对话记录
        await delete_all_history(target)
    else:
        # 删除指定消息
        message_ids = body.get('message_ids', [])
        await delete_messages(message_ids)
```

---

### 2.4 导出 PDF

**位置**: 页面标题栏右侧

**功能**: 将当前对话记录导出为 PDF（通过浏览器打印功能）

**代码位置**: `AIChat.jsx`，行号 289-370

```jsx
const handleExportPDF = useCallback(async () => {
    if (messages.length === 0) {
        alert('没有对话内容需要导出');
        return;
    }

    // 1. 打开新窗口
    const printWindow = window.open('', '_blank');
    if (!printWindow) {
        alert('无法打开打印窗口，请检查是否被浏览器拦截');
        return;
    }

    // 2. 显示加载提示
    printWindow.document.write('<!DOCTYPE html><html><head><title>正在生成...</title></head><body><div style="font-family: sans-serif; padding: 20px; text-align: center;">正在生成对话记录，请稍候...</div></body></html>');

    try {
        const { marked } = await import('marked');
        marked.setOptions({ breaks: true, gfm: true });

        // 3. 构建 HTML 内容
        let htmlContent = `<!DOCTYPE html><html><head><meta charset="UTF-8"><title>对话记录</title>
        <style>
            * { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }
            body { font-family: 'Microsoft YaHei', sans-serif; padding: 15px; line-height: 1.5; font-size: 12px; }
            .user { background: #eff6ff !important; padding: 8px 12px; border-radius: 6px; margin: 8px 0; }
            .assistant { background: #f8fafc !important; border: 1px solid #e5e7eb; padding: 10px 12px; border-radius: 6px; margin: 8px 0; }
            .assistant table { width: 100%; border-collapse: collapse; margin: 8px 0; }
            .assistant th, .assistant td { border: 1px solid #d1d5db !important; padding: 4px 8px; }
            h1.title { text-align: center; font-size: 18px; }
        </style></head><body>
        <h1 class="title">💬 税务智能咨询 - 对话记录</h1>
        <p style="text-align: center; color: #6b7280;">导出时间: ${new Date().toLocaleString('zh-CN')}</p><hr>`;

        // 4. 遍历消息生成 HTML
        messages.forEach((msg, msgIndex) => {
            if (msg.role === 'user') {
                htmlContent += `<div class="user"><strong>您：</strong>${msg.content}</div>`;
            } else {
                let msgContent = `<div class="assistant"><strong>智能体：</strong><br>${marked.parse(msg.content)}`;

                // 处理图表导出（将 Canvas 转为图片）
                if (msg.charts && msg.charts.length > 0) {
                    msg.charts.forEach((_, chartIndex) => {
                        const canvasId = `chart-canvas-${msgIndex}-${chartIndex}`;
                        const canvas = document.getElementById(canvasId);
                        if (canvas) {
                            const imgData = canvas.toDataURL('image/png');
                            msgContent += `<div style="text-align: center; margin: 15px 0;">
                                <img src="${imgData}" style="max-width: 100%;">
                            </div>`;
                        }
                    });
                }

                msgContent += `</div>`;
                htmlContent += msgContent;
            }
        });

        htmlContent += `<div style="text-align:center;color:#9ca3af;margin-top:20px;">本文档由税务智能咨询系统自动生成</div></body></html>`;

        // 5. 写入内容并打印
        printWindow.document.open();
        printWindow.document.write(htmlContent);
        printWindow.document.close();

        // 6. 延迟调用打印
        setTimeout(() => printWindow.print(), 500);

    } catch (error) {
        console.error('导出PDF出错:', error);
    }
}, [messages]);
```

**导出流程**:

```
用户点击"导出PDF"
    │
    ▼
window.open() 打开新窗口
    │
    ▼
构建 HTML 模板（包含样式）
    │
    ▼
遍历 messages，生成用户/AI消息 HTML
    │
    ▼
将 Chart.js Canvas 转为 Base64 图片
    │
    ▼
document.write() 写入内容
    │
    ▼
window.print() 调用浏览器打印
    │
    ▼
用户选择"另存为 PDF"
```

---

### 2.5 历史记录

**位置**: 页面右侧面板

**功能**: 显示历史咨询记录，支持单击加载、批量删除

**代码位置**: `AIChat.jsx`，行号 24-95, 372-478

#### 2.5.1 加载历史记录

```jsx
const fetchHistory = useCallback(async () => {
    const token = localStorage.getItem('access_token');
    const res = await fetch('/api/chat/history?limit=100', {
        headers: { 'Authorization': token ? `Bearer ${token}` : '' }
    });
    
    if (res.ok) {
        const data = await res.json();
        
        // 格式化消息
        const formattedMessages = data.map(msg => {
            let content = msg.content;
            let charts = [];
            let summary = '';

            // 解析 <CHART_DATA> 标签
            if (content && content.includes('<CHART_DATA>')) {
                const parts = content.split('<CHART_DATA>');
                content = parts[0];
                try {
                    const chartJson = parts[1].split('</CHART_DATA>')[0];
                    charts.push(JSON.parse(chartJson));
                } catch (e) { }
            }

            return {
                id: msg.id,
                role: msg.role,
                content: content,
                charts: charts.length > 0 ? charts : undefined,
                summary: summary || undefined,
                timestamp: new Date(msg.created_at).toLocaleTimeString('zh-CN')
            };
        });

        setMessages(formattedMessages);

        // 提取历史记录列表
        const userQuestions = formattedMessages
            .filter(m => m.role === 'user')
            .map(m => m.content)
            .reverse();
        setHistory([...new Set(userQuestions)]);
    }
}, []);
```

#### 2.5.2 单击历史记录：循环定位

```jsx
// 历史记录单击: 循环定位所有回答（最新 -> 上一个 -> ...）
const handleHistoryClick = (item) => {
    setInputText(item);  // 填充到输入框

    // 1. 找到所有匹配的消息索引
    const indices = [];
    messages.forEach((msg, idx) => {
        if (msg.role === 'user' && msg.content === item) {
            indices.push(idx);
        }
    });

    if (indices.length === 0) return;

    let targetIndex;
    const lastNavIndex = historyNavRef.current[item];

    // 2. 决定跳转目标
    if (indices.length === 1) {
        targetIndex = indices[0];
        historyNavRef.current[item] = targetIndex;
    } else {
        // 多条记录，循环逻辑
        if (lastNavIndex === undefined || !indices.includes(lastNavIndex)) {
            targetIndex = indices[indices.length - 1]; // 最新
        } else {
            const currentPos = indices.indexOf(lastNavIndex);
            if (currentPos > 0) {
                targetIndex = indices[currentPos - 1]; // 上一个
            } else {
                targetIndex = indices[indices.length - 1]; // 循环
            }
        }
        historyNavRef.current[item] = targetIndex;
    }

    // 3. 执行跳转
    if (targetIndex !== undefined && chatWidgetRef.current) {
        chatWidgetRef.current.scrollToMessage(targetIndex);
    }
};
```

**循环定位逻辑**:

```
用户单击历史记录 "2023年收入是多少？"
    │
    ├──▶ 找到 3 条匹配记录（索引: 5, 12, 20）
    │
    ├──▶ 首次点击 → 定位到索引 20（最新）
    │
    ├──▶ 再次点击 → 定位到索引 12（上一个）
    │
    ├──▶ 第三次点击 → 定位到索引 5（再上一个）
    │
    └──▶ 第四次点击 → 循环回索引 20（最新）
```

#### 2.5.3 删除历史记录

```jsx
// 选择性删除历史记录
const handleClearHistory = useCallback(async () => {
    if (selectedHistory.size > 0) {
        // 删除选中的历史记录
        if (window.confirm(`确定删除选中的 ${selectedHistory.size} 条历史记录吗？`)) {
            const contentToDelete = Array.from(selectedHistory);

            await fetch('/api/chat/history', {
                method: 'DELETE',
                headers: { 'Authorization': `Bearer ${token}` },
                body: JSON.stringify({ content_list: contentToDelete, target: 'history' })
            });

            setHistory(prev => prev.filter(h => !selectedHistory.has(h)));
            setSelectedHistory(new Set());
        }
    } else if (history.length > 0) {
        // 清空所有历史记录
        if (window.confirm('确定要清空所有历史记录吗？')) {
            await fetch('/api/chat/history', {
                method: 'DELETE',
                headers: { 'Authorization': `Bearer ${token}` },
                body: JSON.stringify({ delete_all: true, target: 'history' })
            });
            setHistory([]);
        }
    }
}, [selectedHistory, history]);
```

#### 2.5.4 切换历史记录选中状态

```jsx
const toggleHistorySelection = (item, e) => {
    e.stopPropagation();
    const newSelected = new Set(selectedHistory);
    if (newSelected.has(item)) {
        newSelected.delete(item);
    } else {
        newSelected.add(item);
    }
    setSelectedHistory(newSelected);
};
```

---

### 2.6 提交咨询

**位置**: 输入区域底部

**功能**: 发送用户问题到后端，获取流式响应

**代码位置**: `AIChat.jsx`，行号 105-200

```jsx
const handleSend = useCallback(() => {
    const question = inputText.trim();
    if (!question || isLoading) return;

    // 1. 添加用户消息
    const timestamp = new Date().toLocaleTimeString('zh-CN', { hour12: false });
    setMessages(prev => [...prev, { role: 'user', content: question, timestamp }]);
    setMessages(prev => [...prev, { role: 'assistant', content: '', route: null }]);
    setIsLoading(true);
    setInputText('');

    // 2. 更新历史记录
    const filteredHistory = history.filter(h => h !== question);
    const newHistory = [question, ...filteredHistory.slice(0, 49)];
    setHistory(newHistory);

    // 3. 滚动到顶部
    if (historyListRef.current) {
        setTimeout(() => { historyListRef.current.scrollTop = 0; }, 0);
    }

    // 4. 流式请求
    const controller = streamChat(question, selectedCompanyId, responseMode, {
        onMessage: (content) => {
            setMessages(prev => {
                const newMessages = [...prev];
                const lastIdx = newMessages.length - 1;
                if (lastIdx >= 0 && newMessages[lastIdx].role === 'assistant') {
                    newMessages[lastIdx] = {
                        ...newMessages[lastIdx],
                        content: newMessages[lastIdx].content + content
                    };
                }
                return newMessages;
            });
        },
        onChart: (chartData) => {
            setMessages(prev => {
                const newMessages = [...prev];
                const lastIdx = newMessages.length - 1;
                if (lastIdx >= 0) {
                    const currentCharts = newMessages[lastIdx].charts || [];
                    newMessages[lastIdx] = {
                        ...newMessages[lastIdx],
                        charts: [...currentCharts, chartData]
                    };
                }
                return newMessages;
            });
        },
        onSummary: (content) => {
            setMessages(prev => {
                const newMessages = [...prev];
                const lastIdx = newMessages.length - 1;
                if (lastIdx >= 0) {
                    const currentSummary = newMessages[lastIdx].summary || '';
                    newMessages[lastIdx] = {
                        ...newMessages[lastIdx],
                        summary: currentSummary + content
                    };
                }
                return newMessages;
            });
        },
        onError: (error) => {
            setMessages(prev => {
                const newMessages = [...prev];
                const lastIdx = newMessages.length - 1;
                if (lastIdx >= 0) {
                    newMessages[lastIdx] = {
                        ...newMessages[lastIdx],
                        content: newMessages[lastIdx].content + `\n\n❌ 错误: ${error}`
                    };
                }
                return newMessages;
            });
            setIsLoading(false);
        },
        onDone: () => setIsLoading(false)
    });

    setCurrentController(controller);
}, [inputText, isLoading, selectedCompanyId, history, responseMode]);
```

---

### 2.7 其他交互功能

#### 2.7.1 输入框事件

```jsx
<textarea
    value={inputText}
    onChange={(e) => setInputText(e.target.value)}
    onKeyDown={(e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    }}
    placeholder="例如：2022-2025收入、利润变动情况..."
    disabled={isLoading}
    rows={2}
/>
```

- **Enter 键提交**: 按 Enter 发送消息（Shift+Enter 换行）
- **字符计数**: 显示 `inputText.length/500字符`
- **禁用状态**: 加载中时禁用输入

#### 2.7.2 消息滚动

`ChatWidget.jsx`，行号 40-83

```jsx
// 智能自动滚动
useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    // 1. 响应结束时，强制滚动到底部
    if (prevIsLoadingRef.current && !isLoading) {
        chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }

    // 2. 正在响应时，智能滚动（仅当用户在底部时）
    else if (isLoading) {
        const lastMsg = messages[messages.length - 1];
        const hasContent = lastMsg && lastMsg.role === 'assistant' && lastMsg.content?.length > 0;

        if (!hasContent) {
            // 新问题开始，尚未输出内容 -> 强制滚动
            chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
        } else {
            // 流式显示 -> 智能滚动
            if (isUserAtBottomRef.current) {
                chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
            }
        }
    }

    prevIsLoadingRef.current = isLoading;
}, [messages, isLoading]);
```

#### 2.7.3 路由事件处理

```jsx
onRoute: (route) => {
    setMessages(prev => {
        const newMessages = [...prev];
        const lastIdx = newMessages.length - 1;
        if (lastIdx >= 0 && newMessages[lastIdx].role === 'assistant') {
            newMessages[lastIdx] = { ...newMessages[lastIdx], route };
        }
        return newMessages;
    });
}
```

---

## 三、SSE 事件流

### 3.1 事件类型

| 事件类型 | 说明 | 数据格式 |
|----------|------|----------|
| `start` | 开始处理 | `{"status": "processing"}` |
| `message` | 文本内容 | `{"content": "..."}` |
| `route` | 路由信息 | `{"path": "...", "company": "..."}` |
| `chart` | 图表数据 | `{"chartType": "...", ...}` |
| `summary` | 分析总结 | `{"content": "..."}` |
| `error` | 错误信息 | `{"message": "..."}` |
| `done` | 完成 | `{"status": "completed"}` |

### 3.2 前端 SSE 处理

`api.js`，行号 197-280

```javascript
export function streamChat(question, companyId, responseMode, { onMessage, onRoute, onChart, onSummary, onError, onDone }) {
    const controller = new AbortController();

    const fetchData = async () => {
        const response = await fetch(`${API_BASE_URL}/api/chat`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({
                question,
                company_id: companyId,
                enable_routing: true,
                show_chart: responseMode === 'detailed',
                response_mode: responseMode
            }),
            signal: controller.signal
        });

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let currentEvent = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() || '';

            for (const line of lines) {
                if (line.startsWith('event: ')) {
                    currentEvent = line.slice(7).trim();
                    continue;
                }

                if (line.startsWith('data: ')) {
                    const data = JSON.parse(line.slice(6));

                    if (currentEvent === 'chart') {
                        onChart?.(data);
                    } else if (currentEvent === 'summary') {
                        onSummary?.(data.content);
                    } else if (data.content !== undefined) {
                        onMessage?.(data.content);
                    }

                    if (data.path !== undefined) {
                        onRoute?.(data.path, data.company);
                    }

                    if (data.status === 'completed') {
                        onDone?.();
                    }

                    if (data.message !== undefined && currentEvent === 'error') {
                        onError?.(data.message);
                    }
                }
            }
        }
    };

    fetchData();
    return controller;
}
```

---

## 四、状态管理

### 4.1 核心状态

| 状态 | 类型 | 说明 |
|------|------|------|
| `messages` | Array | 当前会话的所有消息 |
| `isLoading` | Boolean | 是否正在处理请求 |
| `history` | Array | 历史记录列表 |
| `inputText` | String | 输入框内容 |
| `responseMode` | String | 回答模式 (detailed/standard/concise) |
| `isSelectionMode` | Boolean | 是否处于消息选择模式 |
| `selectedMessageIndices` | Set | 选中的消息索引集合 |
| `selectedHistory` | Set | 选中的历史记录集合 |

### 4.2 消息结构

```typescript
interface Message {
    id: number;              // 消息 ID（用于删除）
    role: 'user' | 'assistant';
    content: string;        // 文本内容
    charts?: ChartData[];   // 图表数据数组
    summary?: string;       // 分析总结
    route?: string;         // 路由信息
    timestamp: string;      // 时间戳
}
```

---

## 五、扩展指南

### 5.1 添加新的回答模式

1. 在 `responseMode` 状态添加新值
2. 在模式切换 UI 添加新按钮
3. 在后端 `chat.py` 添加对应的处理逻辑

### 5.2 添加新的交互按钮

1. 在 `AIChat.jsx` 中添加按钮元素
2. 实现对应的处理函数
3. 添加必要的样式到 `AIChat.css`

### 5.3 自定义图表导出

修改 `handleExportPDF` 函数中的图表处理逻辑：

```jsx
// 处理图表导出
if (msg.charts && msg.charts.length > 0) {
    msg.charts.forEach((chartData, chartIndex) => {
        // 自定义导出逻辑
    });
}
```

---

## 附录 A: 文件清单

| 文件路径 | 说明 |
|----------|------|
| `frontend/src/components/AIChat.jsx` | 主页面组件（约 650 行） |
| `frontend/src/components/AIChat.css` | 页面样式 |
| `frontend/src/components/ChatWidget.jsx` | 聊天组件 |
| `frontend/src/components/ChatWidget.css` | 聊天样式 |
| `frontend/src/components/ChartRenderer.jsx` | 图表渲染组件 |
| `frontend/src/services/api.js` | API 服务层 |

## 附录 B: 后端 API 端点

| 方法 | 路径 | 功能 |
|------|------|------|
| POST | `/api/chat` | 流式对话（支持 SSE） |
| GET | `/api/chat/history` | 获取历史记录 |
| DELETE | `/api/chat/history` | 删除消息/历史 |

## 附录 C: 关键代码行号

| 功能 | 文件 | 行号 |
|------|------|------|
| 回答模式切换 | AIChat.jsx | 564-586 |
| 管理消息 | AIChat.jsx | 229-287 |
| 清空对话 | AIChat.jsx | 203-226 |
| 导出 PDF | AIChat.jsx | 289-370 |
| 历史记录加载 | AIChat.jsx | 24-95 |
| 单击历史记录 | AIChat.jsx | 432-478 |
| 提交咨询 | AIChat.jsx | 105-200 |
| SSE 事件处理 | api.js | 197-280 |
| 消息渲染 | ChatWidget.jsx | 85-117 |
| 智能滚动 | ChatWidget.jsx | 40-83 |
