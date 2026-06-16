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
    get_dietary_profile,
    upsert_dietary_profile,
    save_recipe,
    list_all_recipes,
    delete_recipe,
    batch_delete_recipes,
    save_shopping_list,
    list_shopping_lists,
    get_shopping_list,
    update_shopping_list_items,
    delete_shopping_list,
    cleanup_empty_sessions,
    batch_delete_sessions,
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


class SaveRecipeRequest(BaseModel):
    name: str = Field(description="菜谱名称")
    session_id: str = Field(description="来源会话ID")
    recipe_data: dict = Field(description="完整菜谱数据")


class BatchDeleteRecipesRequest(BaseModel):
    ids: list[str] = Field(description="要删除的菜谱ID列表")


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
    prompt = f"""从以下回复中提取菜谱推荐信息。回复中可能包含多个不同难度的菜谱，全部提取出来。
如果完全不包含菜谱推荐（比如只是打招呼、闲聊、回答问题），只输出: {{"has_recipes": false}}

JSON 格式:
{{{{
  "recipes": [
    {{{{
      "name": "菜名",
      "ingredients": ["食材1", "食材2"],
      "steps": ["步骤1", "步骤2"],
      "difficulty": "简单/中等/困难",
      "cuisine_type": "中餐/西餐/日料/韩餐/东南亚/其他",
      "taste": "清淡/麻辣/酸甜/咸鲜/甜/辣",
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
    """Search for dish images for each recipe with multiple fallback strategies."""
    import httpx
    import os

    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key or not recipes:
        return recipes

    # Multiple query strategies to maximize chance of finding an image
    QUERIES = [
        "{name} 成品图 美食",
        "{name} 做法 菜品图片",
        "{name} 菜谱",
        "{name} recipe food",
    ]

    async def search_one(recipe: dict) -> dict:
        name = recipe.get("name", "")
        if not name or recipe.get("image_url"):
            return recipe
        try:
            async with httpx.AsyncClient(timeout=8) as client:
                for q in QUERIES:
                    query = q.format(name=name)
                    resp = await client.post(
                        "https://api.tavily.com/search",
                        json={
                            "api_key": api_key,
                            "query": query,
                            "include_images": True,
                            "max_results": 5,
                        },
                    )
                    data = resp.json()
                    images = data.get("images", [])
                    if images:
                        recipe["image_url"] = images[0]
                        return recipe
        except Exception:
            pass
        return recipe

    results = await asyncio.gather(*[search_one(r) for r in recipes])
    return results


# ── Session endpoints ──────────────────────────────────────────────

@router.post("/sessions", response_model=CreateSessionResponse)
def api_create_session():
    session = create_session()
    return CreateSessionResponse(session=SessionResponse(**session))


@router.get("/sessions")
def api_list_sessions():
    return list_sessions()


@router.get("/sessions/{session_id}", response_model=dict)
def api_get_session(session_id: str):
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    messages = get_messages(session_id)
    return {"session": SessionResponse(**session), "messages": messages}


@router.put("/sessions/{session_id}")
def api_rename_session(session_id: str, req: ChatRequest):
    if not session_id or not req.message:
        raise HTTPException(status_code=400, detail="Title is required")
    update_session_title(session_id, req.message.strip()[:50])
    return {"ok": True}


@router.delete("/sessions/{session_id}")
def api_delete_session(session_id: str):
    if not get_session(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    delete_session(session_id)
    return {"ok": True}


class BatchDeleteRequest(BaseModel):
    ids: list[str] = Field(description="要删除的会话ID列表")


@router.post("/sessions/batch-delete")
def api_batch_delete_sessions(req: BatchDeleteRequest):
    if not req.ids:
        return {"ok": True}
    batch_delete_sessions(req.ids)
    return {"ok": True}


@router.delete("/sessions/cleanup")
def api_cleanup_sessions():
    cleanup_empty_sessions()
    return {"ok": True}


# ── Recipe library ──────────────────────────────────────────────────

@router.get("/recipes")
def api_list_recipes(
    search: str | None = None,
    difficulty: str | None = None,
    ingredient: str | None = None,
    cuisine_type: str | None = None,
    taste: str | None = None,
):
    return list_all_recipes(
        search_text=search,
        difficulty=difficulty,
        ingredient=ingredient,
        cuisine_type=cuisine_type,
        taste=taste,
    )


@router.delete("/recipes/{recipe_id}")
def api_delete_recipe(recipe_id: str):
    deleted = delete_recipe(recipe_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return {"ok": True}


@router.post("/recipes/batch-delete")
def api_batch_delete_recipes(req: BatchDeleteRecipesRequest):
    if not req.ids:
        return {"ok": True}
    batch_delete_recipes(req.ids)
    return {"ok": True}


# ── Shopping list endpoints ───────────────────────────────────────────

class ShoppingListSaveRequest(BaseModel):
    name: str = Field(description="清单名称")
    session_id: str = Field(default="", description="关联会话ID")
    items: list[dict] = Field(description="食材项目列表 [{text, category, checked, source_recipe}]")


class ShoppingListItemsRequest(BaseModel):
    items: list[dict] = Field(description="更新后的食材项目列表")


@router.post("/shopping-lists")
def api_save_shopping_list(req: ShoppingListSaveRequest):
    return save_shopping_list(req.name, req.session_id, req.items)


@router.get("/shopping-lists")
def api_list_shopping_lists():
    return list_shopping_lists()


@router.get("/shopping-lists/{list_id}")
def api_get_shopping_list(list_id: str):
    lst = get_shopping_list(list_id)
    if not lst:
        raise HTTPException(status_code=404, detail="Shopping list not found")
    return lst


@router.put("/shopping-lists/{list_id}")
def api_update_shopping_list(list_id: str, req: ShoppingListItemsRequest):
    lst = update_shopping_list_items(list_id, req.items)
    if not lst:
        raise HTTPException(status_code=404, detail="Shopping list not found")
    return lst


@router.delete("/shopping-lists/{list_id}")
def api_delete_shopping_list(list_id: str):
    delete_shopping_list(list_id)
    return {"ok": True}


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


# ── Manual recipe save ────────────────────────────────────────────────

@router.post("/recipes")
def api_save_recipe(req: SaveRecipeRequest):
    r = save_recipe(req.session_id, req.recipe_data)
    return {"ok": True, "recipe": r}


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
                # Persist full recipe data so cards survive session reload
                add_message(session_id, "assistant_recipes", json.dumps(recipes_data, ensure_ascii=False), None)
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
