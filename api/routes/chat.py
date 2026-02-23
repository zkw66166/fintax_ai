"""SSE streaming chat endpoint."""
import json
import sqlite3
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from api.schemas import ChatRequest
from mvp_pipeline import run_pipeline_stream
from modules.display_formatter import build_display_data
from config.settings import DB_PATH

router = APIRouter()


def _resolve_company_name(company_id: str) -> str:
    """Look up taxpayer_name from taxpayer_info by taxpayer_id."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.execute(
            "SELECT taxpayer_name FROM taxpayer_info WHERE taxpayer_id = ?",
            (company_id,),
        )
        row = cur.fetchone()
        conn.close()
        return row[0] if row else ""
    except Exception:
        return ""


def _sse_generator(query: str, response_mode: str = "detailed", original_query: str = ""):
    """Wrap run_pipeline_stream as SSE text/event-stream."""
    for event in run_pipeline_stream(query, original_query=original_query or query):
        etype = event.get("type", "")
        if etype == "stage":
            data = json.dumps({"route": event.get("route", ""), "text": event.get("text", "")}, ensure_ascii=False)
            yield f"event: stage\ndata: {data}\n\n"
        elif etype == "chunk":
            data = json.dumps({"text": event.get("text", "")}, ensure_ascii=False)
            yield f"event: chunk\ndata: {data}\n\n"
        elif etype == "done":
            result = event.get("result", {})
            # 为 financial_data 路由附加结构化展示数据
            route = result.get("route", "financial_data")
            if route not in ("tax_incentive", "regulation") and result.get("success"):
                try:
                    result["display_data"] = build_display_data(result)
                except Exception as e:
                    print(f"[display_data] 构建失败: {e}")
            result["response_mode"] = response_mode
            data = json.dumps(result, ensure_ascii=False)
            yield f"event: done\ndata: {data}\n\n"


@router.post("/chat")
async def chat(req: ChatRequest):
    query = req.query
    if req.company_id:
        name = _resolve_company_name(req.company_id)
        if name:
            query = f"{name} {query}"
    original_query = req.query
    return StreamingResponse(
        _sse_generator(query, req.response_mode, original_query=original_query),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
