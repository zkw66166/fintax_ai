"""外部法规查询模块：对接 Coze RAG API（SSE 流式解析）"""
import json

import requests

from config.settings import (
    COZE_API_URL, COZE_PAT_TOKEN, COZE_BOT_ID, COZE_USER_ID, COZE_TIMEOUT,
)


def _parse_sse_line(line: str):
    """解析单行 SSE 数据，返回 (event, data_dict) 或 (None, None)"""
    line = line.strip()
    if not line:
        return None, None
    if line.startswith("event:"):
        return line[len("event:"):].strip(), None
    if line.startswith("data:"):
        raw = line[len("data:"):].strip()
        if raw == "[DONE]":
            return None, None
        try:
            return None, json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            return None, None
    return None, None


def query_regulation(question: str, progress_callback=None) -> dict:
    """调用 Coze RAG API 查询法规知识库。

    Returns:
        {
            'success': bool,
            'route': 'regulation',
            'answer': str,
            'error': str | None,
        }
    """
    result = {"success": False, "route": "regulation", "answer": "", "error": None}

    headers = {
        "Authorization": f"Bearer {COZE_PAT_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "bot_id": COZE_BOT_ID,
        "user_id": COZE_USER_ID,
        "stream": True,
        "auto_save_history": False,
        "additional_messages": [
            {"role": "user", "content": question, "content_type": "text"}
        ],
    }

    try:
        resp = requests.post(
            COZE_API_URL,
            headers=headers,
            json=payload,
            stream=True,
            timeout=COZE_TIMEOUT,
        )

        if resp.status_code != 200:
            result["error"] = f"外部知识库API错误: {resp.status_code}"
            return result

        # Coze 可能在 HTTP 200 内返回业务错误（非SSE格式的JSON）
        # 先读取第一块数据判断是否为错误响应
        content_type = resp.headers.get("Content-Type", "")
        if "text/event-stream" not in content_type:
            # 非 SSE 流：尝试解析为 JSON 错误
            try:
                body = resp.json() if not resp.encoding else json.loads(resp.text)
            except Exception:
                body = {}
            if body.get("code") and body.get("code") != 0:
                result["error"] = f"外部知识库业务错误: {body.get('msg', body.get('code'))}"
                return result

        # 强制 UTF-8 解码（requests 对 text/event-stream 默认用 ISO-8859-1）
        resp.encoding = "utf-8"

        # 累积 answer 片段
        answer_parts = []
        current_event = None
        first_line_checked = False

        for raw_line in resp.iter_lines(decode_unicode=True):
            if raw_line is None:
                continue
            line = raw_line.strip()
            if not line:
                current_event = None
                continue

            # 检测首行是否为非SSE的JSON错误响应
            if not first_line_checked:
                first_line_checked = True
                if not line.startswith("event:") and not line.startswith("data:"):
                    try:
                        err_body = json.loads(line)
                        if err_body.get("code") and err_body.get("code") != 0:
                            result["error"] = f"外部知识库业务错误: {err_body.get('msg', err_body.get('code'))}"
                            return result
                    except (json.JSONDecodeError, ValueError):
                        pass

            if line.startswith("event:"):
                current_event = line[len("event:"):].strip()
                continue

            if line.startswith("data:"):
                raw_data = line[len("data:"):].strip()
                if raw_data == "[DONE]":
                    break
                try:
                    data = json.loads(raw_data)
                except (json.JSONDecodeError, ValueError):
                    continue

                # 只累积 type=answer 的纯文本内容，跳过卡片模板等 JSON 结构
                if isinstance(data, dict) and data.get("type") == "answer" and data.get("content"):
                    content = data["content"]
                    # 跳过 Coze 卡片模板（以 JSON 对象开头的非文本内容）
                    stripped = content.strip()
                    if stripped.startswith("{") and "card_type" in stripped:
                        continue
                    answer_parts.append(content)

        result["answer"] = "".join(answer_parts)
        result["success"] = bool(result["answer"])
        if not result["answer"]:
            result["error"] = "外部知识库未返回有效回答"

    except requests.exceptions.Timeout:
        result["error"] = "外部知识库请求超时"
    except requests.exceptions.ConnectionError:
        result["error"] = "无法连接外部知识库"
    except Exception as e:
        result["error"] = f"外部知识库查询异常: {e}"

    return result


def query_regulation_stream(question: str, progress_callback=None):
    """流式版本：逐步 yield Coze RAG API 的回答片段。

    Yields:
        (chunk_text, is_done, result_dict)
        - chunk_text: 文本片段（is_done=False 时）
        - is_done: True 表示最后一次 yield
        - result_dict: 完整结果字典（仅 is_done=True 时有效）
    """
    result = {"success": False, "route": "regulation", "answer": "", "error": None}

    headers = {
        "Authorization": f"Bearer {COZE_PAT_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "bot_id": COZE_BOT_ID,
        "user_id": COZE_USER_ID,
        "stream": True,
        "auto_save_history": False,
        "additional_messages": [
            {"role": "user", "content": question, "content_type": "text"}
        ],
    }

    try:
        resp = requests.post(
            COZE_API_URL,
            headers=headers,
            json=payload,
            stream=True,
            timeout=COZE_TIMEOUT,
        )

        if resp.status_code != 200:
            result["error"] = f"外部知识库API错误: {resp.status_code}"
            yield "", True, result
            return

        content_type = resp.headers.get("Content-Type", "")
        if "text/event-stream" not in content_type:
            try:
                body = resp.json() if not resp.encoding else json.loads(resp.text)
            except Exception:
                body = {}
            if body.get("code") and body.get("code") != 0:
                result["error"] = f"外部知识库业务错误: {body.get('msg', body.get('code'))}"
                yield "", True, result
                return

        resp.encoding = "utf-8"

        answer_parts = []
        current_event = None
        first_line_checked = False

        for raw_line in resp.iter_lines(decode_unicode=True):
            if raw_line is None:
                continue
            line = raw_line.strip()
            if not line:
                current_event = None
                continue

            if not first_line_checked:
                first_line_checked = True
                if not line.startswith("event:") and not line.startswith("data:"):
                    try:
                        err_body = json.loads(line)
                        if err_body.get("code") and err_body.get("code") != 0:
                            result["error"] = f"外部知识库业务错误: {err_body.get('msg', err_body.get('code'))}"
                            yield "", True, result
                            return
                    except (json.JSONDecodeError, ValueError):
                        pass

            if line.startswith("event:"):
                current_event = line[len("event:"):].strip()
                continue

            if line.startswith("data:"):
                raw_data = line[len("data:"):].strip()
                if raw_data == "[DONE]":
                    break
                try:
                    data = json.loads(raw_data)
                except (json.JSONDecodeError, ValueError):
                    continue

                if isinstance(data, dict) and data.get("type") == "answer" and data.get("content"):
                    content = data["content"]
                    stripped = content.strip()
                    if stripped.startswith("{") and "card_type" in stripped:
                        continue
                    answer_parts.append(content)
                    yield content, False, None

        result["answer"] = "".join(answer_parts)
        result["success"] = bool(result["answer"])
        if not result["answer"]:
            result["error"] = "外部知识库未返回有效回答"

    except requests.exceptions.Timeout:
        result["error"] = "外部知识库请求超时"
    except requests.exceptions.ConnectionError:
        result["error"] = "无法连接外部知识库"
    except Exception as e:
        result["error"] = f"外部知识库查询异常: {e}"

    yield "", True, result
