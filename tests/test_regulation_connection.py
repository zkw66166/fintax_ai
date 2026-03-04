"""测试外部法规知识库API连接"""
import requests
import json
from config.settings import COZE_API_URL, COZE_PAT_TOKEN, COZE_BOT_ID, COZE_USER_ID, COZE_TIMEOUT

def test_coze_connection():
    """测试Coze API基本连接"""
    print("=" * 60)
    print("测试 Coze API 连接")
    print("=" * 60)

    # 配置信息
    print(f"\n配置信息:")
    print(f"  API URL: {COZE_API_URL}")
    print(f"  Bot ID: {COZE_BOT_ID}")
    print(f"  User ID: {COZE_USER_ID}")
    print(f"  Token: {COZE_PAT_TOKEN[:20]}...{COZE_PAT_TOKEN[-10:]}")
    print(f"  Timeout: {COZE_TIMEOUT}s")

    # 测试问题
    test_question = "增值税发票管理办法的主要内容是什么？"
    print(f"\n测试问题: {test_question}")

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
            {"role": "user", "content": test_question, "content_type": "text"}
        ],
    }

    print("\n发送请求...")
    print(f"Headers: {json.dumps({k: v[:50] + '...' if len(v) > 50 else v for k, v in headers.items()}, indent=2, ensure_ascii=False)}")
    print(f"Payload: {json.dumps(payload, indent=2, ensure_ascii=False)}")

    try:
        resp = requests.post(
            COZE_API_URL,
            headers=headers,
            json=payload,
            stream=True,
            timeout=COZE_TIMEOUT,
        )

        print(f"\n响应状态码: {resp.status_code}")
        print(f"响应头:")
        for key, value in resp.headers.items():
            print(f"  {key}: {value}")

        if resp.status_code != 200:
            print(f"\n❌ API返回错误状态码: {resp.status_code}")
            print(f"响应内容: {resp.text[:500]}")
            return False

        # 检查Content-Type
        content_type = resp.headers.get("Content-Type", "")
        print(f"\nContent-Type: {content_type}")

        if "text/event-stream" not in content_type:
            print(f"\n⚠️  非SSE流格式，尝试解析为JSON...")
            try:
                body = resp.json()
                print(f"JSON响应: {json.dumps(body, indent=2, ensure_ascii=False)}")
                if body.get("code") and body.get("code") != 0:
                    print(f"\n❌ 业务错误: {body.get('msg', body.get('code'))}")
                    return False
            except Exception as e:
                print(f"❌ 无法解析响应: {e}")
                print(f"原始内容: {resp.text[:500]}")
                return False

        # 强制UTF-8编码
        resp.encoding = "utf-8"

        # 解析SSE流
        print("\n开始解析SSE流...")
        answer_parts = []
        line_count = 0

        for raw_line in resp.iter_lines(decode_unicode=True):
            if raw_line is None:
                continue

            line = raw_line.strip()
            if not line:
                continue

            line_count += 1
            print(f"\n[行 {line_count}] {line[:200]}")

            # 检测首行错误
            if line_count == 1:
                if not line.startswith("event:") and not line.startswith("data:"):
                    try:
                        err_body = json.loads(line)
                        if err_body.get("code") and err_body.get("code") != 0:
                            print(f"\n❌ 首行业务错误: {err_body.get('msg', err_body.get('code'))}")
                            return False
                    except (json.JSONDecodeError, ValueError):
                        pass

            if line.startswith("event:"):
                event_type = line[len("event:"):].strip()
                print(f"  → Event: {event_type}")
                continue

            if line.startswith("data:"):
                raw_data = line[len("data:"):].strip()
                if raw_data == "[DONE]":
                    print("  → [DONE]")
                    break

                try:
                    data = json.loads(raw_data)
                    print(f"  → Data: {json.dumps(data, ensure_ascii=False)[:200]}")

                    if isinstance(data, dict) and data.get("type") == "answer" and data.get("content"):
                        content = data["content"]
                        stripped = content.strip()

                        # 检测卡片模板
                        if stripped.startswith("{") and "card_type" in stripped:
                            print(f"  → 跳过卡片模板")
                            continue

                        answer_parts.append(content)
                        print(f"  → 累积答案片段: {content[:100]}")

                except (json.JSONDecodeError, ValueError) as e:
                    print(f"  → JSON解析失败: {e}")
                    continue

        # 汇总结果
        final_answer = "".join(answer_parts)
        print("\n" + "=" * 60)
        print("测试结果")
        print("=" * 60)
        print(f"总行数: {line_count}")
        print(f"答案片段数: {len(answer_parts)}")
        print(f"答案长度: {len(final_answer)} 字符")
        print(f"\n完整答案:\n{final_answer}")

        if final_answer:
            print("\n✅ 测试成功！API连接正常，返回了有效答案。")
            return True
        else:
            print("\n⚠️  API连接成功，但未返回有效答案。")
            return False

    except requests.exceptions.Timeout:
        print(f"\n❌ 请求超时 (>{COZE_TIMEOUT}s)")
        return False
    except requests.exceptions.ConnectionError as e:
        print(f"\n❌ 连接错误: {e}")
        return False
    except Exception as e:
        print(f"\n❌ 未知异常: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_coze_connection()
    exit(0 if success else 1)
