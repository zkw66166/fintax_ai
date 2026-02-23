
# 外部 API 知识库查询技术文档

## 一、架构概述

外部 API 知识库是本系统的**第三路由方向**，当用户问题无法被识别为财务数据查询或税收优惠查询时，问题将被路由至 Coze API 进行处理。

```
用户问题 → IntentClassifier → 无法识别为 financial_data 或 tax_incentive
                                                        │
                                                        ▼
                                              ┌─────────────────┐
                                              │  Coze API      │
                                              │ (外部知识库)    │
                                              └─────────────────┘
```

## 重要说明：本文档所引用的脚本文件名称和项目结构是另外一个项目的copy，应用到本fintax项目时需要根据fintax项目的实际情况重新规划和变更！

---

## 二、Coze API 配置

文件位置: [server/routers/chat.py](file:///d:/MyProjects/MCP_coze/server/routers/chat.py#L35-L38)

```python
# Coze API 配置
PAT_TOKEN = "pat_vfbLQz46C21deblJhKhahPLcjYb5xcdB1KKVyEQliGzdhsBZgCi01DzUD0GQ7aYb"
BOT_ID = "7592905400907989034"
USER_ID = "123"
```

| 配置项 | 说明 |
|--------|------|
| `PAT_TOKEN` | Coze 平台 Personal Access Token |
| `BOT_ID` | Coze 机器人 ID（智能体） |
| `USER_ID` | 用户标识符 |

---

## 三、API 调用流程

### 3.1 核心函数

```python
# server/routers/chat.py 第 855-911 行
async def stream_coze_response(question: str) -> AsyncGenerator[str, None]:
    """流式调用 Coze API"""
```

### 3.2 请求构建

```python
headers = {
    "Authorization": f"Bearer {PAT_TOKEN}",
    "Content-Type": "application/json; charset=utf-8",
    "Accept": "text/event-stream",
    "User-Agent": "Mozilla/5.0"
}

payload = {
    "bot_id": BOT_ID,
    "user_id": USER_ID,
    "stream": True,                    # 启用流式响应
    "auto_save_history": True,         # 自动保存对话历史
    "additional_messages": [
        {"role": "user", "content": question, "content_type": "text"}
    ],
    "temperature": 0.7,                # 创造性参数 (0-2)
    "max_tokens": 2000                 # 最大生成 token 数
}
```

### 3.3 请求发送

```python
response = requests.post(
    "https://api.coze.cn/v3/chat",    # Coze API v3 端点
    headers=headers,
    json=payload,
    stream=True,                        # 流式接收
    timeout=180,                       # 超时时间 180 秒
    verify=False                       # 跳过 SSL 验证
)
```

---

## 四、SSE 流式响应解析

### 4.1 响应格式

Coze API 使用 **Server-Sent Events (SSE)** 格式返回流式数据：

```
event: conversation.message.delta
data: {"role": "assistant", "type": "answer", "content": "..."}

event: conversation.message.delta
data: {"role": "assistant", "type": "answer", "content": "..."}

event: done
data: {"code": 0, "msg": "success"}
```

### 4.2 解析逻辑

```python
def parse_sse_line(line: str):
    """解析 SSE 行"""
    line = line.strip()
    if not line:
        return None, None
    
    if line.startswith('event:'):
        return line[6:].strip(), None
    
    if line.startswith('data:'):
        try:
            return None, json.loads(line[5:].strip())
        except:
            return None, None
    
    return None, None

# 处理响应
current_event = None
for chunk in response.iter_content(chunk_size=1024):
    chunk_str = chunk.decode('utf-8', errors='ignore')
    lines = chunk_str.split('\n')
    
    for line in lines:
        event_type, data = parse_sse_line(line)
        if event_type:
            current_event = event_type
        
        # 提取回答内容
        if data and current_event == "conversation.message.delta":
            if data.get("role") == "assistant" and data.get("type") == "answer":
                content = data.get("content", "")
                if content:
                    yield send_content(content)
```

---

## 五、路由触发条件

### 5.1 何时调用 Coze API

根据 [intent_classifier.py](file:///d:/MyProjects/MCP_coze/modules/intent_classifier.py) 的逻辑，当问题属于以下情况时，路由至 Coze API：

```python
# 路由到 "other" 的情况：
# 1. 知识库优先关键词
if self._should_route_to_knowledge_base(question):
    return "other"  # → Coze API

# 2. 排除词命中（明确不是税收优惠的问题）
if keyword_result == "exclude":
    return "other"  # → Coze API

# 3. 无法确定意图，LLM 返回 "other"
if self.use_llm:
    llm_result = self._llm_classify(question)
    return llm_result  # 可能返回 "other" → Coze API
```

### 5.2 知识库优先关键词

```python
knowledge_base_priority_keywords = [
    "指南", "指引", "操作", "申报", "申请", "备案", "管理", 
    "办理", "注销", "注册", "登记注册", "注册登记", 
    "认定", "扣缴", "目录", "汇编", "流程", "怎么办",
    "如何办", "怎样办", "程序", "步骤", "手续", "享受"
]
```

### 5.3 排除关键词

```python
exclude_keywords = [
    "发票", "申报流程", "缴纳流程", "登记流程",
    "什么是", "定义", "概念", "计算公式"
]
```

---

## 六、API 请求示例

### 6.1 请求消息格式

```bash
curl -X POST 'https://api.coze.cn/v3/chat' \
  -H 'Authorization: Bearer pat_vfbLQz46C21deblJhKhahPLcjYb5xcdB1KKVyEQliGzdhsBZgCi01DzUD0GQ7aYb' \
  -H 'Content-Type: application/json; charset=utf-8' \
  -H 'Accept: text/event-stream' \
  -d '{
    "bot_id": "7592905400907989034",
    "user_id": "123",
    "stream": true,
    "auto_save_history": true,
    "additional_messages": [
      {"role": "user", "content": "如何申报增值税?", "content_type": "text"}
    ],
    "temperature": 0.7,
    "max_tokens": 2000
  }'
```

### 6.2 响应示例

```
event: conversation.message.delta
data: {"conversation_id": "123456789", "message_id": "msg_xxx", "role": "assistant", "type": "answer", "content": "增值税申报流程如下：", "index": 0}

event: conversation.message.delta
data: {"conversation_id": "123456789", "message_id": "msg_xxx", "role": "assistant", "type": "answer", "content": "1. 登录电子税务局...", "index": 1}

event: done
data: {"code": 0, "msg": "success"}
```

---

## 七、前端展示

文件位置: [frontend/src/components/ChatWidget.jsx](file:///d:/MyProjects/MCP_coze/frontend/src/components/ChatWidget.jsx#L174)

```jsx
{msg.route === 'coze' && '🤖 知识库'}
```

当消息来源为 Coze API 时，前端显示 "🤖 知识库" 标签。

---

## 八、错误处理

### 8.1 HTTP 状态码错误

```python
if response.status_code != 200:
    yield send_content(f"❌ API 错误: {response.status_code}\n")
    return
```

### 8.2 请求异常

```python
except Exception as e:
    yield send_content(f"❌ 请求失败: {str(e)}\n")
```

### 8.3 常见错误码

| 错误码 | 含义 | 处理方式 |
|--------|------|----------|
| 401 | Token 无效 | 检查 PAT_TOKEN |
| 403 | 权限不足 | 检查 BOT_ID 是否正确 |
| 404 | 资源不存在 | 检查 BOT_ID |
| 429 | 请求过于频繁 | 增加重试间隔 |
| 500 | 服务器错误 | 重试或联系 Coze 支持 |

---

## 九、参数调优

### 9.1 temperature (创造性参数)

```python
"temperature": 0.7  # 默认值
```

| 值 | 效果 |
|----|------|
| 0.0-0.3 | 更确定性，答案更稳定 |
| 0.4-0.7 | 平衡，创造性与准确性兼顾 |
| 0.8-2.0 | 更创造性，答案更多样化 |

### 9.2 max_tokens (最大 token 数)

```python
"max_tokens": 2000  # 默认值
```

- 根据问题复杂度调整
- 财务分析类问题建议 2000-4000
- 简单咨询类问题 500-1000

### 9.3 timeout (超时时间)

```python
timeout=180  # 180 秒
```

- 流式响应耗时较长，建议 120-300 秒
- 需要根据 Coze 机器人响应时间调整

---

## 十、与本地数据库的区别

| 特性 | 本地数据库 (financial.db / tax_incentives.db) | Coze API (知识库) |
|------|---------------------------------------------|-------------------|
| **数据来源** | SQLite 本地文件 | Coze 云端智能体 |
| **响应速度** | 毫秒级 | 秒级 (依赖网络) |
| **数据准确性** | 精确匹配 | AI 生成 (可能有幻觉) |
| **适用范围** | 结构化数据查询 | 开放域问答 |
| **可控性** | 高 (完全可控) | 中 (依赖 prompt) |
| **维护成本** | 需要手动维护数据库 | 需要维护 Coze 机器人 |

---

## 十一、扩展配置

### 11.1 添加新的外部知识源

如需接入其他 API (如 OpenAI、文心一言等)，可参考以下结构：

```python
async def stream_external_response(
    question: str, 
    provider: str = "coze"  # 可扩展
) -> AsyncGenerator[str, None]:
    
    if provider == "coze":
        async for chunk in stream_coze_response(question):
            yield chunk
    elif provider == "openai":
        async for chunk in stream_openai_response(question):
            yield chunk
    # 扩展更多 provider...
```

### 11.2 修改 Coze 机器人

1. 登录 [Coze 平台](https://www.coze.cn)
2. 编辑对应的 Bot (BOT_ID: 7592905400907989034)
3. 配置知识库、插件、工作流
4. 发布新版本

---

## 十二、监控与日志

### 12.1 日志输出

```python
# 路由日志
print(f"📚 检测到知识库优先关键词,路由到知识库")

# API 调用日志
print(f"🤖 Coze API 调用: {question}")
```

### 12.2 性能监控

- 监控 `/api/chat` 响应时间
- 记录 `route` 事件中的 `path` 分布
- 统计 Coze API 错误率

---

本系统通过 Coze API 实现了开放域问答能力，作为本地数据库查询的补充，为用户提供更全面的税务咨询服务。