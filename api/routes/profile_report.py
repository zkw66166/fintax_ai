"""企业画像分析报告 API 路由"""
import json
import sqlite3
import logging
import threading
import queue
from datetime import datetime

from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse

from api.auth import get_current_user, require_company_access
from config.settings import DB_PATH, PROFILE_REPORT_ENABLED
from modules.profile_service import get_company_profile
from modules.profile_report_service import generate_report_stream

logger = logging.getLogger(__name__)
router = APIRouter()

_SENTINEL = object()  # 标记后台线程结束


def _get_conn():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


# ---------------------------------------------------------------------------
# 启动时清理长期卡在 generating 状态的旧记录
# ---------------------------------------------------------------------------
def _cleanup_stale_generating():
    """将超过 30 分钟仍为 generating 的记录标记为 failed。"""
    try:
        conn = _get_conn()
        conn.execute(
            "UPDATE profile_reports SET status='failed', error_msg='生成超时或服务重启', "
            "completed_at=? WHERE status='generating' "
            "AND created_at < datetime('now', '-30 minutes')",
            (datetime.now().isoformat(),),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error("[ProfileReport] Cleanup stale generating records error: %s", e)

_cleanup_stale_generating()


# ---------------------------------------------------------------------------
# POST /api/profile/{taxpayer_id}/report  — 生成报告（SSE流式）
# ---------------------------------------------------------------------------

def _background_generate(report_id: int, profile_data: dict, taxpayer_name: str, year: int, q: queue.Queue):
    """后台线程：执行 LLM 生成，将事件放入队列，最终更新 DB。"""
    full_content = ""
    error_msg = None

    try:
        for evt in generate_report_stream(profile_data, taxpayer_name, year):
            evt_type = evt.get("type", "chunk")

            if evt_type == "stage":
                q.put(("stage", {"text": evt["text"]}))

            elif evt_type == "chunk":
                q.put(("chunk", {"text": evt["text"]}))
                full_content += evt.get("text", "")

            elif evt_type == "done":
                result = evt.get("result", {})
                full_content = result.get("content", full_content)
                error_msg = result.get("error")

    except Exception as e:
        logger.error("[ProfileReport] Background generate error: %s", e)
        error_msg = str(e)

    # 更新 DB 记录
    try:
        conn = _get_conn()
        if error_msg and not full_content:
            conn.execute(
                "UPDATE profile_reports SET status='failed', error_msg=?, completed_at=? WHERE id=?",
                (error_msg, datetime.now().isoformat(), report_id),
            )
        else:
            conn.execute(
                "UPDATE profile_reports SET status='completed', content=?, completed_at=? WHERE id=?",
                (full_content, datetime.now().isoformat(), report_id),
            )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error("[ProfileReport] DB update error: %s", e)

    # 通知 SSE 生成完成
    q.put(("done", {"text": full_content, "error": error_msg}))
    q.put(_SENTINEL)


def _sse_report_generator(taxpayer_id: str, year: int, user: dict):
    """SSE 流式接口：启动后台线程生成，从队列转发事件给前端。"""
    if not PROFILE_REPORT_ENABLED:
        yield f"event: done\ndata: {json.dumps({'error': '报告功能未启用'}, ensure_ascii=False)}\n\n"
        return

    # 1. 获取画像数据
    try:
        profile_data = get_company_profile(taxpayer_id, year)
    except Exception as e:
        logger.error("[ProfileReport] Failed to fetch profile: %s", e)
        yield f"event: done\ndata: {json.dumps({'error': f'获取画像数据失败: {e}'}, ensure_ascii=False)}\n\n"
        return

    if not profile_data or profile_data.get("error"):
        err = profile_data.get("error", "暂无画像数据") if profile_data else "暂无画像数据"
        yield f"event: done\ndata: {json.dumps({'error': err}, ensure_ascii=False)}\n\n"
        return

    taxpayer_name = (profile_data.get("basic_info") or {}).get("taxpayer_name", taxpayer_id)

    # 2. 插入 generating 记录
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO profile_reports (taxpayer_id, taxpayer_name, year, user_id, username, status) "
        "VALUES (?, ?, ?, ?, ?, 'generating')",
        (taxpayer_id, taxpayer_name, year, user["id"], user["username"]),
    )
    report_id = cur.lastrowid
    conn.commit()
    conn.close()

    # 发送 report_id 给前端
    yield f"event: meta\ndata: {json.dumps({'report_id': report_id}, ensure_ascii=False)}\n\n"

    # 3. 启动后台线程执行 LLM 生成
    q = queue.Queue()
    t = threading.Thread(
        target=_background_generate,
        args=(report_id, profile_data, taxpayer_name, year, q),
        daemon=True,
    )
    t.start()

    # 4. 从队列转发 SSE 事件给前端（前端断开时此循环自然结束，后台线程继续）
    try:
        while True:
            try:
                item = q.get(timeout=1.0)
            except queue.Empty:
                continue
            if item is _SENTINEL:
                break
            evt_type, data_dict = item
            data = json.dumps(data_dict, ensure_ascii=False)
            yield f"event: {evt_type}\ndata: {data}\n\n"
    except GeneratorExit:
        # 前端断开 SSE 连接，后台线程继续运行
        logger.info("[ProfileReport] SSE disconnected for report %s, background generation continues", report_id)


@router.post("/profile/{taxpayer_id}/report")
async def generate_report(
    taxpayer_id: str,
    year: int = Query(default=2025),
    user: dict = Depends(get_current_user),
):
    require_company_access(user, taxpayer_id)
    return StreamingResponse(
        _sse_report_generator(taxpayer_id, year, user),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ---------------------------------------------------------------------------
# GET /api/profile/reports  — 报告列表
# ---------------------------------------------------------------------------

@router.get("/profile/reports")
async def list_reports(
    taxpayer_id: str = Query(default=""),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    user: dict = Depends(get_current_user),
):
    conn = _get_conn()
    offset = (page - 1) * size

    # sys/admin 可看所有，其他角色只看自己的
    role = user.get("role", "enterprise")
    conditions = []
    params = []

    if role not in ("sys", "admin"):
        conditions.append("user_id = ?")
        params.append(user["id"])

    if taxpayer_id:
        conditions.append("taxpayer_id = ?")
        params.append(taxpayer_id)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    total = conn.execute(f"SELECT COUNT(*) FROM profile_reports {where}", params).fetchone()[0]

    rows = conn.execute(
        f"SELECT id, taxpayer_id, taxpayer_name, year, user_id, username, status, "
        f"error_msg, created_at, completed_at "
        f"FROM profile_reports {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
        params + [size, offset],
    ).fetchall()

    conn.close()

    items = [dict(r) for r in rows]
    return {"items": items, "total": total, "page": page, "size": size}


# ---------------------------------------------------------------------------
# GET /api/profile/reports/{report_id}  — 获取单个报告
# ---------------------------------------------------------------------------

@router.get("/profile/reports/{report_id}")
async def get_report(report_id: int, user: dict = Depends(get_current_user)):
    conn = _get_conn()
    row = conn.execute("SELECT * FROM profile_reports WHERE id = ?", (report_id,)).fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="报告不存在")

    report = dict(row)
    role = user.get("role", "enterprise")
    if role not in ("sys", "admin") and report["user_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="无权访问该报告")

    return report


# ---------------------------------------------------------------------------
# DELETE /api/profile/reports/{report_id}  — 删除报告
# ---------------------------------------------------------------------------

@router.delete("/profile/reports/{report_id}")
async def delete_report(report_id: int, user: dict = Depends(get_current_user)):
    conn = _get_conn()
    row = conn.execute("SELECT id, user_id FROM profile_reports WHERE id = ?", (report_id,)).fetchone()

    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="报告不存在")

    role = user.get("role", "enterprise")
    if role not in ("sys", "admin") and dict(row)["user_id"] != user["id"]:
        conn.close()
        raise HTTPException(status_code=403, detail="无权删除该报告")

    conn.execute("DELETE FROM profile_reports WHERE id = ?", (report_id,))
    conn.commit()
    conn.close()
    return {"ok": True}
