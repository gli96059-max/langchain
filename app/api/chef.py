import json
import uuid
import base64
import asyncio
import os
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger("chef")

import httpx
from fastapi import APIRouter, Depends, HTTPException
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
    batch_delete_sessions,
    create_user,
    verify_user,
    get_pool,
)
from app.agents.project import build_chief_agent
from app.seasonal import get_seasonal_context
from app.auth import create_token, get_current_user
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from model_config import qwen

router = APIRouter(prefix="/api", tags=["chef"])

# ── Agent pool (shared PostgreSQL checkpointer) ────────────────────
# With PostgreSQL there is no need for per-user checkpoint DBs —
# MVCC + connection pool handle concurrent writes natively.
# Thread-id "{uid}:{session_id}" provides logical isolation.

_init_lock = asyncio.Lock()
_checkpointer: AsyncPostgresSaver | None = None
_agent_pool: dict[str, Any] = {}  # user_id -> agent


async def _get_checkpointer():
    global _checkpointer
    if _checkpointer is not None:
        return _checkpointer
    async with _init_lock:
        if _checkpointer is not None:
            return _checkpointer
        pool = get_pool()
        _checkpointer = AsyncPostgresSaver(pool)
        await _checkpointer.setup()
        return _checkpointer


async def _get_agent_for_user(user_id: str):
    """Get-or-create a LangGraph agent (cached per user, shared checkpointer).

    With PostgreSQL the checkpointer can safely serve all users — thread-id
    prefixes provide isolation so there is zero write contention between
    different conversations.
    """
    agent = _agent_pool.get(user_id)
    if agent is not None:
        return agent
    async with _init_lock:
        agent = _agent_pool.get(user_id)
        if agent is not None:
            return agent
        checkpointer = await _get_checkpointer()
        agent = build_chief_agent(checkpointer=checkpointer)
        _agent_pool[user_id] = agent
        return agent


# ── Auth Models ────────────────────────────────────────────────────

class AuthRequest(BaseModel):
    username: str = Field(min_length=1, description="用户名")
    password: str = Field(min_length=6, description="密码")


class AuthResponse(BaseModel):
    token: str
    user: dict


# ── Existing Models ────────────────────────────────────────────────

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
    difficulty_preference: str = Field(default="", description="菜品难度偏好")


class SessionResponse(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str


class CreateSessionResponse(BaseModel):
    session: SessionResponse


# ── Auth endpoints ─────────────────────────────────────────────────

@router.post("/auth/register")
async def api_register(req: AuthRequest):
    user = await create_user(req.username, req.password)
    if not user:
        raise HTTPException(status_code=409, detail="用户名已存在或密码不符合要求")
    token = create_token(user["id"])
    return AuthResponse(token=token, user=user)


@router.post("/auth/login")
async def api_login(req: AuthRequest):
    user = await verify_user(req.username, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    token = create_token(user["id"])
    return AuthResponse(token=token, user=user)


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


# ── Parallel Search Pipeline ────────────────────────────────────────

def _clean_json(content: str) -> str:
    """Strip markdown code fences from a model response."""
    content = content.strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[1] if "\n" in content else content[3:]
    if content.endswith("```"):
        content = content.rsplit("```", 1)[0]
    if content.startswith("json"):
        content = content[4:].strip()
    return content.strip()


def _try_extract_json(text: str) -> tuple[dict | None, str | None]:
    """Try to find and parse recipe JSON in text. Returns (data, raw_json_str)."""
    # Strategy 1: marker
    if "=====JSON=====" in text:
        _, json_part = text.split("=====JSON=====", 1)
        json_str = _clean_json(json_part)
        try:
            return json.loads(json_str), json_str
        except json.JSONDecodeError:
            pass

    # Strategy 2: ```json code block
    if "```json" in text:
        for block in text.split("```json"):
            if "```" in block:
                json_str = block.split("```")[0].strip()
                try:
                    data = json.loads(json_str)
                    if "recipes" in data:
                        return data, json_str
                except json.JSONDecodeError:
                    pass

    # Strategy 3: find {"recipes": in text, extract brace-balanced JSON
    idx = text.find('"recipes"')
    while idx != -1:
        search_start = max(0, idx - 200)
        before = text[search_start:idx]
        brace_idx = before.rfind("{")
        if brace_idx != -1:
            candidate = text[search_start + brace_idx:]
            depth = 0
            for i, ch in enumerate(candidate):
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        json_str = candidate[:i+1]
                        try:
                            data = json.loads(json_str)
                            if "recipes" in data:
                                return data, json_str
                        except json.JSONDecodeError:
                            break
        idx = text.find('"recipes"', idx + 1)

    return None, None


async def analyze_input(
    latest_text: str,
    image_base64: str | None,
    existing_messages: list,
) -> dict:
    """Use Qwen to understand what the user wants and extract ingredients."""
    has_history = len(existing_messages) > 2
    history_note = "用户之前已经发过消息，这次可能是追问、修改要求或闲聊。" if has_history else "这是用户的第一条消息。"

    prompt = f"""{history_note}

分析用户输入，输出 JSON（不要 markdown 代码块）：

{{
  "action": "search" | "refine" | "chat",
  "ingredients": ["食材1", "食材2"],
  "difficulty_preference": "简单" | "中等" | "困难" | "all",
  "requirements": "其他要求"
}}

action 取值规则：
- "search"：用户提供了食材或明确要求推荐菜谱
- "refine"：用户对之前推荐的内容提出修改要求（换一个、加辣、不放蒜等）
- "chat"：只是打招呼、闲聊、问问题，不涉及菜谱

用户输入：{latest_text}"""

    if image_base64:
        prompt += "\n[用户同时上传了一张图片]"

    try:
        response = await asyncio.to_thread(qwen.invoke, [HumanMessage(content=prompt)])
        content = _clean_json(response.content)
        return json.loads(content)
    except Exception:
        return {"action": "chat", "ingredients": [], "difficulty_preference": "all", "requirements": ""}


async def parallel_search(ingredients: list[str], difficulty_pref: str, requirements: str) -> dict:
    """Search Tavily concurrently across difficulty levels."""
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key or not ingredients:
        return {}

    ingredient_text = " ".join(ingredients)
    difficulties = ["简单", "中等", "困难"] if difficulty_pref == "all" else [difficulty_pref]

    async def search_level(level: str) -> tuple[str, dict]:
        query = f"{ingredient_text} {level} {requirements} 菜谱做法"
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    "https://api.tavily.com/search",
                    json={
                        "api_key": api_key,
                        "query": query,
                        "include_images": True,
                        "include_answer": True,
                        "max_results": 6,
                    },
                )
                data = resp.json()
                return level, {
                    "results": data.get("results", []),
                    "images": data.get("images", []),
                    "answer": data.get("answer", ""),
                }
        except Exception:
            return level, {"results": [], "images": [], "answer": ""}

    results_list = await asyncio.gather(*[search_level(level) for level in difficulties])
    return dict(results_list)


ANALYSIS_PROMPT_TEMPLATE = """你是一位专业 chefs 助手。根据以下信息推荐菜谱。

主要食材：{ingredients}
难度偏好：{difficulty_pref}
特殊要求：{requirements}
{seasonal_context}
{dietary_context}

搜索到的参考信息：
{search_context}

请按以下两步输出：
1. 先给用户一段自然、友好的回复，推荐 3-6 个菜谱（必须严格按照上面的难度偏好推荐），介绍每个菜谱的特点和推荐理由。
2. 然后在回复的最后，用以下标记输出结构化数据：

=====JSON=====
{{
  "recipes": [
    {{
      "name": "菜名",
      "ingredients": ["食材1", "食材2"],
      "steps": ["步骤1", "步骤2"],
      "difficulty": "简单/中等/困难",
      "cuisine_type": "中餐/西餐/日料/韩餐/东南亚/其他",
      "taste": "清淡/麻辣/酸甜/咸鲜/甜/辣",
      "nutrition_score": 85,
      "overall_score": 90,
      "nutrition": {{
        "calories": 350,
        "protein": "20g",
        "fat": "15g",
        "carbs": "30g"
      }},
      "reason": "推荐理由"
    }}
  ],
  "summary": "总结建议"
}}

注意：
- 推荐菜谱必须严格尊重用户的饮食限制（如有）
- 菜谱名称、食材、步骤必须准确、可操作
- 自然回复部分要热情、专业
- 如果搜索信息不足，可以根据你的知识补充"""


REFINE_PROMPT_TEMPLATE = """你是一位专业 chefs 助手。用户看了之前的推荐后提出了新的要求。

用户的新要求：{user_message}

之前的推荐菜谱：
{previous_recipes}

{dietary_context}

请根据用户的新要求调整推荐，必须严格遵守{dietary_context}中的饮食限制和难度偏好，输出格式同之前一样：
1. 自然语言回复（调整后的推荐）
2. 然后输出 =====JSON===== 标记和结构化数据

JSON 格式与之前完全相同。"""


async def generate_full_response(
    ingredients: list[str],
    search_data: dict,
    requirements: str,
    difficulty_pref: str,
    seasonal_context: str,
    dietary_profile: dict | None,
) -> tuple[str, dict | None]:
    """Single Qwen call producing natural text + structured recipe JSON."""
    search_parts = []
    for level, data in search_data.items():
        if data.get("answer"):
            search_parts.append(f"[{level}难度]\n综述: {data['answer']}")
        for r in data.get("results", []):
            title = r.get("title", "")
            content = r.get("content", "")
            if title or content:
                search_parts.append(f"- {title}: {content[:300]}")
    search_context = "\n".join(search_parts) if search_parts else "（无搜索结果）"

    dietary_context = ""
    if dietary_profile:
        parts = []
        if dietary_profile.get("allergies"):
            parts.append(f"过敏源: {dietary_profile['allergies']}")
        if dietary_profile.get("restrictions"):
            parts.append(f"饮食限制: {dietary_profile['restrictions']}")
        if dietary_profile.get("preferences"):
            parts.append(f"口味偏好: {dietary_profile['preferences']}")
        if dietary_profile.get("difficulty_preference"):
            parts.append(f"菜品难度偏好: {dietary_profile['difficulty_preference']}")
        if parts:
            dietary_context = f"用户饮食档案：{'，'.join(parts)}"

    seasonal = f"当前时令信息：{seasonal_context}" if seasonal_context else ""

    prompt = ANALYSIS_PROMPT_TEMPLATE.format(
        ingredients="、".join(ingredients) if ingredients else "（未指定）",
        difficulty_pref=difficulty_pref,
        requirements=requirements or "无",
        seasonal_context=seasonal,
        dietary_context=dietary_context,
        search_context=search_context,
    )

    try:
        response = await asyncio.to_thread(qwen.invoke, [HumanMessage(content=prompt)])
        full_text = response.content.strip()

        recipes_data, raw_json = _try_extract_json(full_text)
        if recipes_data and raw_json:
            text_part = full_text.replace(raw_json, "").replace("=====JSON=====", "").strip()
            if not text_part:
                text_part = "为你推荐以下菜谱："
            return text_part, recipes_data

        return full_text, None
    except Exception as e:
        logger.warning("generate_full_response failed: %s", e)
        return "", None


async def generate_refinement(
    user_message: str,
    existing_messages: list,
    dietary_profile: dict | None,
) -> tuple[str, dict | None]:
    """Qwen modifies previous recommendations without new searches."""
    previous_recipes = ""
    for m in reversed(existing_messages):
        if getattr(m, "type", "") == "ai" and hasattr(m, "content"):
            prev = m.content or ""
            if any(kw in prev for kw in ["菜谱", "做法", "步骤"]):
                previous_recipes = prev[:2000]
                break

    dietary_context = ""
    if dietary_profile:
        parts = []
        if dietary_profile.get("allergies"):
            parts.append(f"过敏源: {dietary_profile['allergies']}")
        if dietary_profile.get("restrictions"):
            parts.append(f"饮食限制: {dietary_profile['restrictions']}")
        if dietary_profile.get("preferences"):
            parts.append(f"口味偏好: {dietary_profile['preferences']}")
        if dietary_profile.get("difficulty_preference"):
            parts.append(f"菜品难度偏好: {dietary_profile['difficulty_preference']}")
        if parts:
            dietary_context = f"用户饮食档案：{'，'.join(parts)}"

    prompt = REFINE_PROMPT_TEMPLATE.format(
        user_message=user_message,
        previous_recipes=previous_recipes or "（没有历史记录）",
        dietary_context=dietary_context,
    )

    try:
        response = await asyncio.to_thread(qwen.invoke, [HumanMessage(content=prompt)])
        full_text = response.content.strip()

        recipes_data, raw_json = _try_extract_json(full_text)
        if recipes_data and raw_json:
            text_part = full_text.replace(raw_json, "").replace("=====JSON=====", "").strip()
            if not text_part:
                text_part = "已为你调整推荐："
            return text_part, recipes_data

        return full_text, None
    except Exception as e:
        logger.warning("generate_refinement failed: %s", e)
        return "", None


async def enrich_recipes_with_images(recipes: list[dict]) -> list[dict]:
    """Search for dish images for each recipe with multiple fallback strategies."""
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key or not recipes:
        return recipes

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
async def api_create_session(current_user: dict = Depends(get_current_user)):
    session = await create_session(current_user["id"])
    return CreateSessionResponse(session=SessionResponse(**session))


@router.get("/sessions")
async def api_list_sessions(current_user: dict = Depends(get_current_user)):
    return await list_sessions(current_user["id"])


@router.get("/sessions/{session_id}", response_model=dict)
async def api_get_session(session_id: str, current_user: dict = Depends(get_current_user)):
    session = await get_session(current_user["id"], session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    messages = await get_messages(current_user["id"], session_id)
    return {"session": SessionResponse(**session), "messages": messages}


@router.put("/sessions/{session_id}")
async def api_rename_session(session_id: str, req: ChatRequest, current_user: dict = Depends(get_current_user)):
    if not session_id or not req.message:
        raise HTTPException(status_code=400, detail="Title is required")
    await update_session_title(current_user["id"], session_id, req.message.strip()[:50])
    return {"ok": True}


@router.delete("/sessions/{session_id}")
async def api_delete_session(session_id: str, current_user: dict = Depends(get_current_user)):
    session = await get_session(current_user["id"], session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    await delete_session(current_user["id"], session_id)
    return {"ok": True}


class BatchDeleteRequest(BaseModel):
    ids: list[str] = Field(description="要删除的会话ID列表")


@router.post("/sessions/batch-delete")
async def api_batch_delete_sessions(req: BatchDeleteRequest, current_user: dict = Depends(get_current_user)):
    if not req.ids:
        return {"ok": True}
    await batch_delete_sessions(current_user["id"], req.ids)
    return {"ok": True}


# ── Recipe library ────────────────────────────────────────────────

@router.get("/recipes")
async def api_list_recipes(
    search: str | None = None,
    difficulty: str | None = None,
    ingredient: str | None = None,
    cuisine_type: str | None = None,
    taste: str | None = None,
    current_user: dict = Depends(get_current_user),
):
    return await list_all_recipes(
        user_id=current_user["id"],
        search_text=search,
        difficulty=difficulty,
        ingredient=ingredient,
        cuisine_type=cuisine_type,
        taste=taste,
    )


@router.delete("/recipes/{recipe_id}")
async def api_delete_recipe(recipe_id: str, current_user: dict = Depends(get_current_user)):
    deleted = await delete_recipe(current_user["id"], recipe_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return {"ok": True}


@router.post("/recipes/batch-delete")
async def api_batch_delete_recipes(req: BatchDeleteRecipesRequest, current_user: dict = Depends(get_current_user)):
    if not req.ids:
        return {"ok": True}
    await batch_delete_recipes(current_user["id"], req.ids)
    return {"ok": True}


# ── Shopping list endpoints ───────────────────────────────────────

class ShoppingListSaveRequest(BaseModel):
    name: str = Field(description="清单名称")
    session_id: str = Field(default="", description="关联会话ID")
    items: list[dict] = Field(description="食材项目列表 [{text, category, checked, source_recipe}]")


class ShoppingListItemsRequest(BaseModel):
    items: list[dict] = Field(description="更新后的食材项目列表")


@router.post("/shopping-lists")
async def api_save_shopping_list(req: ShoppingListSaveRequest, current_user: dict = Depends(get_current_user)):
    return await save_shopping_list(current_user["id"], req.name, req.session_id, req.items)


@router.get("/shopping-lists")
async def api_list_shopping_lists(current_user: dict = Depends(get_current_user)):
    return await list_shopping_lists(current_user["id"])


@router.get("/shopping-lists/{list_id}")
async def api_get_shopping_list(list_id: str, current_user: dict = Depends(get_current_user)):
    lst = await get_shopping_list(current_user["id"], list_id)
    if not lst:
        raise HTTPException(status_code=404, detail="Shopping list not found")
    return lst


@router.put("/shopping-lists/{list_id}")
async def api_update_shopping_list(list_id: str, req: ShoppingListItemsRequest, current_user: dict = Depends(get_current_user)):
    lst = await update_shopping_list_items(current_user["id"], list_id, req.items)
    if not lst:
        raise HTTPException(status_code=404, detail="Shopping list not found")
    return lst


@router.delete("/shopping-lists/{list_id}")
async def api_delete_shopping_list(list_id: str, current_user: dict = Depends(get_current_user)):
    await delete_shopping_list(current_user["id"], list_id)
    return {"ok": True}


# ── Dietary profile endpoints ─────────────────────────────────────

@router.get("/dietary-profile")
async def api_get_dietary_profile(current_user: dict = Depends(get_current_user)):
    profile = await get_dietary_profile(current_user["id"])
    if not profile:
        return {"allergies": "", "restrictions": "", "preferences": "", "difficulty_preference": ""}
    return profile


@router.put("/dietary-profile")
async def api_update_dietary_profile(req: DietaryProfileRequest, current_user: dict = Depends(get_current_user)):
    profile = await upsert_dietary_profile(current_user["id"], req.allergies, req.restrictions, req.preferences, req.difficulty_preference)
    return profile


# ── Manual recipe save ────────────────────────────────────────────

@router.post("/recipes")
async def api_save_recipe(req: SaveRecipeRequest, current_user: dict = Depends(get_current_user)):
    r = await save_recipe(current_user["id"], req.session_id, req.recipe_data)
    return {"ok": True, "recipe": r}


# ── Chat endpoint ─────────────────────────────────────────────────

@router.post("/chat/{session_id}")
async def api_chat(session_id: str, req: ChatRequest, current_user: dict = Depends(get_current_user)):
    uid = current_user["id"]
    if not await get_session(uid, session_id):
        raise HTTPException(status_code=404, detail="Session not found")

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
    image_url = f"data:image/png;base64,{req.image_base64}" if req.image_base64 else None
    await add_message(uid, session_id, "user", req.message, image_url)
    existing = await get_messages(uid, session_id)
    if len(existing) == 1:
        await update_session_title(uid, session_id, _auto_title(req.message))

    # Inject dietary profile if set
    profile = await get_dietary_profile(uid)
    extra_msgs = []
    if profile and (profile["allergies"] or profile["restrictions"] or profile["preferences"] or profile.get("difficulty_preference")):
        parts = []
        if profile["allergies"]:
            parts.append(f"过敏源: {profile['allergies']}")
        if profile["restrictions"]:
            parts.append(f"饮食限制: {profile['restrictions']}")
        if profile["preferences"]:
            parts.append(f"口味偏好: {profile['preferences']}")
        if profile.get("difficulty_preference"):
            parts.append(f"菜品难度偏好: {profile['difficulty_preference']}")
        extra_msgs.append(SystemMessage(content=f"## 用户的饮食档案\n{'，'.join(parts)}\n\n推荐菜谱时必须严格遵守以上饮食限制和难度偏好。"))

    seasonal = get_seasonal_context()
    if seasonal:
        extra_msgs.append(SystemMessage(content="## " + seasonal))

    config = {"configurable": {"thread_id": f"{uid}:{session_id}"}}

    async def event_stream():
        yield _sse_event("status", {"step": "thinking", "message": "思考中..."})
        error_occurred = False

        try:
            # Step 1: analyze input
            analysis = await analyze_input(req.message, req.image_base64, existing)
            action = analysis.get("action", "chat")

            # Build messages for langchain callbacks / agent fallback
            msgs = [*extra_msgs, human_msg]

            if action == "search":
                yield _sse_event("status", {"step": "searching", "message": "搜索食材做法中..."})
                ingredients = analysis.get("ingredients", [])
                diff_pref = analysis.get("difficulty_preference", "all")
                requirements = analysis.get("requirements", "")
                # Use dietary profile's difficulty preference as default if user didn't specify
                profile_diff = profile.get("difficulty_preference", "") if profile else ""
                if profile_diff and diff_pref == "all":
                    diff_pref = profile_diff

                search_data = await parallel_search(ingredients, diff_pref, requirements)

                yield _sse_event("status", {"step": "generating", "message": "生成菜谱推荐中..."})
                text_result, recipes_data = await generate_full_response(
                    ingredients, search_data, requirements, diff_pref,
                    seasonal, profile,
                )

                if not text_result:
                    # Fallback to agent
                    agent = await _get_agent_for_user(uid)
                    response = await asyncio.to_thread(agent.invoke, {"messages": msgs}, config)
                    text_result = _extract_assistant_text(response)
                    recipes_data = None

                if not text_result:
                    yield _sse_event("error", {"message": "未收到有效回复"})
                    await add_message(uid, session_id, "assistant", "抱歉，我没有生成有效回复。", None)
                    return

                yield _sse_event("response", {"text": text_result})

                if recipes_data:
                    enriched = await enrich_recipes_with_images(recipes_data.get("recipes", []))
                    recipes_data["recipes"] = enriched
                    yield _sse_event("result", recipes_data)
                    await add_message(uid, session_id, "assistant_recipes", json.dumps(recipes_data, ensure_ascii=False), None)
                else:
                    await add_message(uid, session_id, "assistant", text_result, None)

            elif action == "refine":
                yield _sse_event("status", {"step": "refining", "message": "根据要求调整推荐中..."})
                text_result, recipes_data = await generate_refinement(req.message, existing, profile)

                if not text_result:
                    agent = await _get_agent_for_user(uid)
                    response = await asyncio.to_thread(agent.invoke, {"messages": msgs}, config)
                    text_result = _extract_assistant_text(response)
                    recipes_data = None

                if not text_result:
                    yield _sse_event("error", {"message": "未收到有效回复"})
                    await add_message(uid, session_id, "assistant", "抱歉，我没有生成有效回复。", None)
                    return

                yield _sse_event("response", {"text": text_result})

                if recipes_data:
                    enriched = await enrich_recipes_with_images(recipes_data.get("recipes", []))
                    recipes_data["recipes"] = enriched
                    yield _sse_event("result", recipes_data)
                    await add_message(uid, session_id, "assistant_recipes", json.dumps(recipes_data, ensure_ascii=False), None)
                else:
                    await add_message(uid, session_id, "assistant", text_result, None)

            else:  # "chat" — general chat, fall through to agent
                yield _sse_event("status", {"step": "chatting", "message": "回复中..."})
                agent = await _get_agent_for_user(uid)
                response = await asyncio.to_thread(agent.invoke, {"messages": msgs}, config)
                assistant_text = _extract_assistant_text(response)

                if not assistant_text:
                    yield _sse_event("error", {"message": "未收到有效回复"})
                    await add_message(uid, session_id, "assistant", "抱歉，我没有生成有效回复。", None)
                    return

                yield _sse_event("response", {"text": assistant_text})
                await add_message(uid, session_id, "assistant", assistant_text, None)

        except Exception as e:
            logger.exception("chat_stream exception: %s", e)
            error_occurred = True
            # Final fallback: try the original agent
            try:
                agent = await _get_agent_for_user(uid)
                response = await asyncio.to_thread(agent.invoke, {"messages": msgs}, config)
                assistant_text = _extract_assistant_text(response)
                if assistant_text:
                    yield _sse_event("response", {"text": assistant_text})
                    await add_message(uid, session_id, "assistant", assistant_text, None)
                    yield _sse_event("done", {})
                    return
            except Exception as e2:
                logger.exception("chat_stream fallback agent failed: %s", e2)
                pass
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
async def api_upload(image_base64: str, current_user: dict = Depends(get_current_user)):
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
