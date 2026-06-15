import json
import uuid
import base64
import asyncio
from pathlib import Path
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.db import (
    create_session,
    list_sessions,
    get_session,
    delete_session,
    update_session_title,
    add_message,
    get_messages,
)
from app.agents.project import build_chef_graph, ChefState
from app.agents.schemas import Recipe

from langgraph.checkpoint.sqlite import SqliteSaver
from langchain_core.messages import HumanMessage, AIMessage
import sqlite3

router = APIRouter(prefix="/api", tags=["chef"])

# ── Shared LangGraph checkpointer ──────────────────────────────────
CHECKPOINT_DB = Path(__file__).resolve().parent.parent.parent / "resources" / "checkpoint.db"
_checkpoint_conn = sqlite3.connect(str(CHECKPOINT_DB), check_same_thread=False)
_checkpointer = SqliteSaver(_checkpoint_conn)


_compiled_agent = None


def _get_compiled_agent():
    """Return (cached) chef graph compiled with the shared checkpointer."""
    global _compiled_agent
    if _compiled_agent is None:
        _compiled_agent = build_chef_graph(checkpointer=_checkpointer)
    return _compiled_agent


# ── Request / Response models ──────────────────────────────────────

class ChatRequest(BaseModel):
    message: str = Field(default="", description="用户输入文本")
    image_base64: str | None = Field(default=None, description="图片的base64编码")


class SessionResponse(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str


class MessageResponse(BaseModel):
    id: int
    session_id: str
    role: str
    content: str
    image_url: str | None
    created_at: str


class CreateSessionResponse(BaseModel):
    session: SessionResponse


# ── Helper: generate session title from first message ──────────────

def _auto_title(text: str) -> str:
    """Generate a short session title from the first user message."""
    text = text.strip()[:20]
    return text if text else "新对话"


# ── SSE event helpers ──────────────────────────────────────────────

def _sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


# ── Session endpoints ──────────────────────────────────────────────

@router.post("/sessions", response_model=CreateSessionResponse)
def api_create_session():
    """Create a new chat session."""
    session = create_session()
    return CreateSessionResponse(session=SessionResponse(**session))


@router.get("/sessions", response_model=list[SessionResponse])
def api_list_sessions():
    """List all sessions ordered by last update."""
    return [SessionResponse(**s) for s in list_sessions()]


@router.get("/sessions/{session_id}", response_model=dict)
def api_get_session(session_id: str):
    """Get a session with its message history."""
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    messages = get_messages(session_id)
    return {"session": SessionResponse(**session), "messages": messages}


@router.delete("/sessions/{session_id}")
def api_delete_session(session_id: str):
    """Delete a session."""
    if not get_session(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    delete_session(session_id)
    return {"ok": True}


# ── Chat endpoint (SSE streaming) ─────────────────────────────────

@router.post("/chat/{session_id}")
async def api_chat(session_id: str, req: ChatRequest):
    """Send a message and stream the Chef Agent's response via SSE."""
    if not get_session(session_id):
        raise HTTPException(status_code=404, detail="Session not found")

    # 1. Build human message (text + optional image)
    content_parts = []
    if req.message:
        content_parts.append({"type": "text", "text": req.message})
    if req.image_base64:
        content_parts.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{req.image_base64}"},
        })

    if not content_parts:
        raise HTTPException(status_code=400, detail="Message or image is required")

    human_msg = HumanMessage(content=content_parts if len(content_parts) > 1 else req.message)

    # 2. Save user message to DB
    add_message(session_id, "user", req.message, None)

    # 3. Auto-title on first message
    existing = get_messages(session_id)
    if len(existing) == 1:
        update_session_title(session_id, _auto_title(req.message))

    config = {"configurable": {"thread_id": session_id}}

    # 4. SSE streaming generator
    async def event_stream():
        agent = _get_compiled_agent()

        # Send initial status
        yield _sse_event("status", {"step": "identifying", "message": "正在识别食材..."})

        recipes_result = []
        summary_result = ""
        error_occurred = False

        try:
            # Run graph in thread (sync calls), stream state after each node
            async for state in agent.astream(
                {"messages": [human_msg]},
                config,
                stream_mode="values",
            ):
                step = state.get("current_step", "")

                if step == "食材识别完成":
                    yield _sse_event("status", {
                        "step": "ingredients_done",
                        "message": f"食材识别完成！\n{state.get('ingredients', '')}",
                        "ingredients": state.get("ingredients", ""),
                    })
                    yield _sse_event("status", {
                        "step": "searching",
                        "message": "正在搜索菜谱...",
                    })

                elif step == "菜谱搜索完成":
                    yield _sse_event("status", {
                        "step": "searching_done",
                        "message": "菜谱搜索完成，正在评估推荐...",
                    })

                elif step == "菜谱评估完成":
                    recipes_raw = state.get("recipes", [])
                    summary_raw = state.get("summary", "")
                    recipes_result = [r.model_dump() if hasattr(r, 'model_dump') else r for r in recipes_raw]
                    summary_result = summary_raw

            # 5. Send final structured result
            if recipes_result:
                yield _sse_event("result", {
                    "recipes": recipes_result,
                    "summary": summary_result,
                })
                # Save assistant response to DB
                recipe_summary_text = summary_result
                if recipes_result:
                    names = [r.get("name", "") for r in recipes_result]
                    recipe_summary_text = f"推荐了 {len(recipes_result)} 个菜谱: {', '.join(names)}"
                add_message(session_id, "assistant", recipe_summary_text, None)
            else:
                yield _sse_event("error", {"message": "未能生成菜谱推荐，请重试"})
                add_message(session_id, "assistant", "抱歉，我没能成功生成菜谱推荐，请再试一次。", None)

        except Exception as e:
            error_occurred = True
            yield _sse_event("error", {"message": f"处理出错: {str(e)}"})

        finally:
            if not error_occurred:
                yield _sse_event("done", {})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ── Image upload endpoint ─────────────────────────────────────────

UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads"


@router.post("/upload")
async def api_upload(image_base64: str):
    """Upload a base64-encoded image and return its URL."""
    try:
        header, _, b64_data = image_base64.partition(",")
        if not b64_data:
            b64_data = image_base64
        img_bytes = base64.b64decode(b64_data)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 image data")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}.png"
    file_path = UPLOAD_DIR / filename
    file_path.write_bytes(img_bytes)

    return {"url": f"/uploads/{filename}"}
