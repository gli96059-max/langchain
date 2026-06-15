import json
import uuid
import base64
import asyncio
from pathlib import Path

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
    add_favorite,
    remove_favorite,
    list_favorites,
    get_dietary_profile,
    upsert_dietary_profile,
    save_recipe,
    list_all_recipes,
)
from app.agents.project import build_chief_agent
from app.seasonal import get_seasonal_context
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
import aiosqlite

router = APIRouter(prefix="/api", tags=["chef"])

# ── Shared checkpointer ────────────────────────────────────────────
CHECKPOINT_DB = Path(__file__).resolve().parent.parent.parent / "resources" / "checkpoint.db"
CHECKPOINT_DB.parent.mkdir(parents=True, exist_ok=True)

_checkpoint_conn = None


async def _get_checkpointer():
    global _checkpoint_conn
    if _checkpoint_conn is None:
        _checkpoint_conn = await aiosqlite.connect(str(CHECKPOINT_DB))
    return AsyncSqliteSaver(_checkpoint_conn)


_agent_cache = None


async def _get_agent():
    global _agent_cache
    if _agent_cache is None:
        checkpointer = await _get_checkpointer()
        _agent_cache = build_chief_agent(checkpointer=checkpointer)
    return _agent_cache


# ── Models ─────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str = Field(default="", description="用户输入文本")
    image_base64: str | None = Field(default=None, description="图片的base64编码")


class FavoriteRequest(BaseModel):
    name: str = Field(description="菜谱名称")
    recipe_data: dict = Field(description="完整菜谱数据")


class DietaryProfileRequest(BaseModel):
    allergies: str = Field(default="", description="过敏源")
    restrictions: str = Field(default="", description="饮食限制")
    preferences: str = Field(default="", description="口味偏好")


class SessionResponse(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str


class CreateSessionResponse(BaseModel):
    session: SessionResponse


# ── Helpers ────────────────────────────────────────────────────────

def _auto_title(text: str) -> str:
    text = text.strip()[:20]
    return text if text else "新对话"


def _sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _extract_assistant_text(response) -> str:
    """Extract the assistant's reply text from the agent response."""
    if isinstance(response, dict):
        msgs = response.get("messages")
        if msgs:
            for m in reversed(msgs):
                role = getattr(m, "type", getattr(m, "role", ""))
                if role in ("ai", "assistant", "AIMessage"):
                    return getattr(m, "content", "") or ""
        output = response.get("output", "")
        if output:
            return output
    if hasattr(response, "content"):
        return response.content or ""
    return str(response)


async def extract_recipes(text: str) -> dict | None:
    """Use Qwen to extract structured recipe data from the agent's natural response."""
    prompt = f"""从以下回复中提取菜谱推荐信息。如果包含菜谱推荐，按下面的 JSON 格式输出。
如果完全不包含菜谱推荐（比如只是打招呼、闲聊、回答问题），只输出: {{"has_recipes": false}}

JSON 格式:
{{{{
  "recipes": [
    {{{{
      "name": "菜名",
      "ingredients": ["食材1", "食材2"],
      "steps": ["步骤1", "步骤2"],
      "difficulty": "简单/中等/困难",
      "nutrition_score": 85,
      "overall_score": 90,
      "nutrition": {{{{
        "calories": 350,
        "protein": "20g",
        "fat": "15g",
        "carbs": "30g"
      }}}},
      "reason": "推荐理由",
      "image_url": null,
      "reference_url": null
    }}}}
  ],
  "summary": "总结建议"
}}}}

回复内容:
{text}"""
    from model_config import qwen
    try:
        response = await asyncio.to_thread(qwen.invoke, [HumanMessage(content=prompt)])
        content = response.content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1] if "\n" in content else content[3:]
        if content.endswith("```"):
            content = content.rsplit("```", 1)[0]
        if content.startswith("json"):
            content = content[4:].strip()
        content = content.strip()
        data = json.loads(content)
        if data.get("has_recipes") is False:
            return None
        return data
    except Exception:
        return None


async def enrich_recipes_with_images(recipes: list[dict]) -> list[dict]:
    """Search for dish images for each recipe via Tavily API."""
    import httpx
    import os

    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key or not recipes:
        return recipes

    async def search_one(recipe: dict) -> dict:
        name = recipe.get("name", "")
        if not name or recipe.get("image_url"):
            return recipe
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    "https://api.tavily.com/search",
                    json={
                        "api_key": api_key,
                        "query": f"{name} 美食 成品图 菜品",
                        "include_images": True,
                        "max_results": 3,
                    },
                )
                data = resp.json()
                images = data.get("images", [])
                if images:
                    recipe["image_url"] = images[0]
        except Exception:
            pass
        return recipe

    return await asyncio.gather(*[search_one(r) for r in recipes])


# ── Session endpoints ──────────────────────────────────────────────

@router.post("/sessions", response_model=CreateSessionResponse)
def api_create_session():
    session = create_session()
    return CreateSessionResponse(session=SessionResponse(**session))


@router.get("/sessions", response_model=list[SessionResponse])
def api_list_sessions():
    return [SessionResponse(**s) for s in list_sessions()]


@router.get("/sessions/{session_id}", response_model=dict)
def api_get_session(session_id: str):
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    messages = get_messages(session_id)
    return {"session": SessionResponse(**session), "messages": messages}


@router.delete("/sessions/{session_id}")
def api_delete_session(session_id: str):
    if not get_session(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    delete_session(session_id)
    return {"ok": True}


# ── Favorites endpoints ──────────────────────────────────────────────

@router.get("/favorites")
def api_list_favorites():
    return list_favorites()


@router.post("/favorites")
def api_add_favorite(req: FavoriteRequest):
    fav = add_favorite(req.name, req.recipe_data)
    return fav


@router.delete("/favorites/{favorite_id}")
def api_remove_favorite(favorite_id: str):
    remove_favorite(favorite_id)
    return {"ok": True}


# ── Recipe library ──────────────────────────────────────────────────

@router.get("/recipes")
def api_list_recipes():
    return list_all_recipes()


# ── Dietary profile endpoints ────────────────────────────────────────

@router.get("/dietary-profile")
def api_get_dietary_profile():
    profile = get_dietary_profile()
    if not profile:
        return {"allergies": "", "restrictions": "", "preferences": ""}
    return profile


@router.put("/dietary-profile")
def api_update_dietary_profile(req: DietaryProfileRequest):
    profile = upsert_dietary_profile(req.allergies, req.restrictions, req.preferences)
    return profile


# ── Chat endpoint ─────────────────────────────────────────────────

@router.post("/chat/{session_id}")
async def api_chat(session_id: str, req: ChatRequest):
    if not get_session(session_id):
        raise HTTPException(status_code=404, detail="Session not found")

    # Build human message (text + optional image)
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

    # DB: save user message & auto-title
    add_message(session_id, "user", req.message, None)
    existing = get_messages(session_id)
    if len(existing) == 1:
        update_session_title(session_id, _auto_title(req.message))

    # Inject dietary profile if set
    profile = get_dietary_profile()
    extra_msgs = []
    if profile and (profile["allergies"] or profile["restrictions"] or profile["preferences"]):
        parts = []
        if profile["allergies"]:
            parts.append(f"过敏源: {profile['allergies']}")
        if profile["restrictions"]:
            parts.append(f"饮食限制: {profile['restrictions']}")
        if profile["preferences"]:
            parts.append(f"口味偏好: {profile['preferences']}")
        extra_msgs.append(SystemMessage(content=f"## 用户的饮食档案\n{'，'.join(parts)}\n\n推荐菜谱时必须严格遵守以上饮食限制。"))
    # Inject seasonal context
    seasonal = get_seasonal_context()
    if seasonal:
        extra_msgs.append(SystemMessage(content="## " + seasonal))

    config = {"configurable": {"thread_id": session_id}}

    async def event_stream():
        agent = await _get_agent()

        yield _sse_event("status", {"step": "thinking", "message": "思考中..."})
        error_occurred = False
        assistant_text = ""

        try:
            # Run the agent (sync invoke in thread)
            msgs = [*extra_msgs, human_msg]
            response = await asyncio.to_thread(
                agent.invoke,
                {"messages": msgs},
                config,
            )

            assistant_text = _extract_assistant_text(response)

            if not assistant_text:
                yield _sse_event("error", {"message": "未收到有效回复"})
                add_message(session_id, "assistant", "抱歉，我没有生成有效回复。", None)
                return

            # Send the natural language response
            yield _sse_event("response", {"text": assistant_text})

            # Try to extract structured recipe data
            recipes_data = await extract_recipes(assistant_text)
            if recipes_data:
                # Enrich with dish images
                enriched = await enrich_recipes_with_images(recipes_data.get("recipes", []))
                recipes_data["recipes"] = enriched
                yield _sse_event("result", recipes_data)
                # Save to recipe library
                for r in enriched:
                    save_recipe(session_id, r)
                summary = recipes_data.get("summary", "")
                names = [r.get("name", "") for r in recipes_data.get("recipes", [])]
                db_text = f"推荐了 {len(names)} 个菜谱: {', '.join(names)}"
                add_message(session_id, "assistant", db_text, None)
            else:
                add_message(session_id, "assistant", assistant_text, None)

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


# ── Image upload ──────────────────────────────────────────────────

UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads"


@router.post("/upload")
async def api_upload(image_base64: str):
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
