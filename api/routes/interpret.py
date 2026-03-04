"""SSE streaming interpretation endpoint."""
import json
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from api.auth import get_current_user, require_company_access
from api.schemas import InterpretRequest
from config.settings import INTERPRETATION_ENABLED
from api.services.query_cache import update_cache_interpretation

router = APIRouter()


def _sse_interpret_generator(query: str, result: dict, response_mode: str, cache_key: str = ""):
    """Wrap interpret_stream as SSE text/event-stream."""
    if not INTERPRETATION_ENABLED or response_mode == "concise":
        yield f"event: done\ndata: {json.dumps({'text': ''}, ensure_ascii=False)}\n\n"
        return

    from modules.interpretation_service import interpret_stream

    full_text = ""
    try:
        for chunk_text, is_done in interpret_stream(result, query, response_mode):
            if not is_done:
                full_text += chunk_text
                data = json.dumps({"text": chunk_text}, ensure_ascii=False)
                yield f"event: chunk\ndata: {data}\n\n"
            else:
                # done event from interpret_stream contains full accumulated text;
                # use it as the authoritative full_text (avoid double-counting)
                if chunk_text:
                    full_text = chunk_text
                data = json.dumps({"text": chunk_text}, ensure_ascii=False)
                yield f"event: done\ndata: {data}\n\n"
    except Exception as e:
        error_data = json.dumps({"text": "", "error": str(e)}, ensure_ascii=False)
        yield f"event: done\ndata: {error_data}\n\n"

    # Write interpretation back to persistent cache
    if cache_key and full_text:
        update_cache_interpretation(cache_key, full_text)


@router.post("/chat/interpret")
async def interpret(req: InterpretRequest, user: dict = Depends(get_current_user)):
    if req.company_id:
        require_company_access(user, req.company_id)
    return StreamingResponse(
        _sse_interpret_generator(req.query, req.result, req.response_mode, req.cache_key),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
