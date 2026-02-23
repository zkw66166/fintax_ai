# 前端 5 个 Bug 修复计划

## Context

上一轮实施已完成后端接口扩展、状态提升、管理消息、清空确认、历史搜索等功能。用户测试后发现 5 个问题需要修复。本次仅修改前端代码，不动后端。

---

## Bug 1: AI 回答区域没有撑满中间 frame，右侧留有大空隙

**根因**: `ChatMessage.module.css` 第 15 行 `.aiMsg { max-width: 85%; }` 限制了 AI 消息容器宽度。子组件（ResultTable/ChartRenderer/GrowthTable）内部都是 `width: 100%`，被父级 85% 卡住。

**文件**: `frontend/src/components/ChatMessage/ChatMessage.module.css`
**改动**: `.aiMsg` 的 `max-width: 85%` → `max-width: 100%`

---

## Bug 2: 单击历史记录没有将问题回填到输入框

**根因**: `handleHistoryClick` 只做了滚动定位或替换消息，从未设置输入框文本。ChatInput 使用本地 `text` state，外部无法设置。

**改动**:

### App.jsx
- 新增 `pendingInputText` / `setPendingInputText` state
- `handleHistoryClick` 开头加 `setPendingInputText(entry.query)`
- 将 `pendingInputText` + `onPendingInputTextConsumed` 传给 ChatArea

### ChatArea.jsx
- 接收 `pendingInputText` / `onPendingInputTextConsumed` props，透传给 ChatInput

### ChatInput.jsx
- 添加 `useEffect` import
- 接收 `pendingInputText` / `onPendingInputTextConsumed` props
- `useEffect` 监听 `pendingInputText`：非空时 `setText(pendingInputText)` + 调用 `onPendingInputTextConsumed()` + focus textarea

---

## Bug 3: 切换历史记录时，历史对话回答部分消失

**根因**: `App.jsx` 的 `handleHistoryClick` else 分支（无匹配时）调用 `setMessages([...])` 替换整个消息数组。且加载的 assistant 消息只有 `content: entry.main_output`，而 financial_data 成功时 `main_output` 为空字符串，导致显示空白。

**改动**: `App.jsx` — 删除 `handleHistoryClick` 中的 else 分支（不再替换消息数组）。无匹配时仅回填输入框（Bug 2 的修复已覆盖），用户可选择重新提交。

修改后的 `handleHistoryClick`:
```jsx
const handleHistoryClick = useCallback((entry) => {
  setPendingInputText(entry.query)  // 始终回填输入框

  const matchIndices = messages
    .map((m, i) => (m.role === 'user' && m.content === entry.query ? i : -1))
    .filter((i) => i !== -1)

  if (matchIndices.length > 0) {
    // 循环定位
    const key = entry.query
    const lastIdx = historyNavRef.current[key] ?? -1
    const nextPos = matchIndices.findIndex((i) => i > lastIdx)
    const targetIdx = nextPos !== -1 ? matchIndices[nextPos] : matchIndices[0]
    historyNavRef.current[key] = targetIdx
    chatAreaRef.current?.scrollToMessage(targetIdx)
  }
  // 无匹配：仅回填输入框，不替换消息
}, [messages])
```

---

## Bug 4: 导出 PDF 只导出当前一页，不是所有内容

**根因**: `handleExport` 用 `escapeHtml(msg.content)` 重建 HTML，丢失了渲染好的表格/图表/格式化数据。图表 canvas 被追加到末尾而非内联。缺少分页 CSS。

**文件**: `frontend/src/components/ChatArea/ChatArea.jsx`
**改动**: 重写 `handleExport`，改用 DOM 克隆方式：
1. `containerRef.current.cloneNode(true)` 克隆已渲染的消息区域 DOM
2. 遍历克隆体中的 `<canvas>`，用原始 canvas 的 `toDataURL('image/png')` 替换为 `<img>`（内联位置不变）
3. 移除交互元素（button、checkbox、PipelineDetail 折叠区）
4. 写入打印窗口，添加打印 CSS：`@page { size: A4; margin: 15mm; }`、`page-break-inside: avoid`
5. 延迟 500ms 后调用 `window.print()`

---

## Bug 5: "图文""纯数据""简报"模式切换没有效果

**根因**: 模式切换 UI 和数据流已接通（responseMode 从 App → ChatArea → ChatInput → useSSE → 后端 → 返回 → 存到 msg.responseMode）。ChatMessage 中 `standard` 模式（隐藏图表）正常工作。但 `concise` 模式有问题：
- 条件 `isDone && mode === 'concise' && dd` 要求 `dd` 存在
- `dd.summary` 仅在 cross_domain 结果中有值，普通 table/kv/metric 结果的 summary 为 null
- `msg.content` 对 financial_data 成功结果也是空字符串
- 结果：concise 模式对普通财务查询什么都不显示

**文件**: `frontend/src/components/ChatMessage/ChatMessage.jsx`
**改动**: 重写 concise 模式渲染块，添加多级 fallback：
1. `dd.summary` 存在 → 显示摘要文本
2. metric 类型 → 直接显示 MetricDisplay（本身就是简洁的）
3. kv 类型 → 直接显示 KVDisplay（单行数据，本身简洁）
4. table 类型 → 生成文字摘要："查询成功，共 N 条记录。字段1: 值1；字段2: 值2..."
5. `msg.content` 非空 → ReactMarkdown 渲染（tax_incentive/regulation 路由）
6. 兜底 → "查询完成"

同时去掉 `&& dd` 条件，让 concise 模式在无 display_data 时也能走 fallback。

---

## 涉及文件清单

| 文件 | Bug | 改动 |
|------|-----|------|
| `frontend/src/components/ChatMessage/ChatMessage.module.css` | #1 | `.aiMsg` max-width 改为 100% |
| `frontend/src/App.jsx` | #2 #3 | 新增 pendingInputText state；重写 handleHistoryClick |
| `frontend/src/components/ChatArea/ChatArea.jsx` | #2 #4 | 透传 pendingInputText props；重写 handleExport |
| `frontend/src/components/ChatInput/ChatInput.jsx` | #2 | 接收 pendingInputText + useEffect 同步 |
| `frontend/src/components/ChatMessage/ChatMessage.jsx` | #5 | 重写 concise 模式渲染逻辑 |

## 验证

1. 查询后确认 AI 回答区域撑满中间 frame（无右侧空隙）
2. 点击历史记录 → 确认输入框被回填为对应问题
3. 多次查询后切换历史记录 → 确认当前对话不消失，匹配时滚动定位
4. 导出 PDF → 确认打印窗口包含所有消息（含表格、图表图片），多页内容完整
5. 切换"图文"→查询→确认表格+图表+增长分析全部显示
6. 切换"纯数据"→查询→确认表格+增长分析显示，图表隐藏
7. 切换"简报"→查询→确认显示文字摘要（非空白）
