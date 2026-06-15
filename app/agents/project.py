import json
from typing import TypedDict, Annotated, Sequence

from langgraph.graph import StateGraph, START, END
from langchain_core.messages import (
    HumanMessage,
    AIMessage,
    SystemMessage,
    BaseMessage,
)
from langchain_core.runnables.config import RunnableConfig
from app.agents.schemas import Recipe

from model_config import qwen
from tools import web_search

SYSTEM_PROMPT = """
你是AI私厨助手。你帮助用户根据现有食材推荐菜谱。

# 核心流程
1. 识别用户提供的食材清单
2. 搜索可行菜谱
3. 从营养价值和制作难度两个维度评价菜谱
4. 推荐最佳菜谱

# 输出要求
你最后必须输出JSON格式的结果，包含:
- recipes: 菜谱列表，每个菜谱包含 name(菜名), ingredients(食材清单), steps(做法步骤), difficulty(难度), nutrition_score(营养评分0-100), overall_score(综合评分0-100), reason(推荐理由), image_url(成品图片URL), reference_url(参考链接)
- summary: 总结建议

确保结果丰富多样，每次推荐3-5个菜谱。
"""


class ChefState(TypedDict):
    """厨师助手的对话状态"""
    messages: Annotated[Sequence[BaseMessage], lambda x, y: x + y]
    ingredients: str
    search_results: str
    recipes: list[Recipe]
    summary: str
    current_step: str


def call_identify_ingredients(state: ChefState, config: RunnableConfig) -> dict:
    """
    Node 1: 使用 Qwen 多模态模型识别用户提供的食材
    """
    messages = list(state["messages"])

    system = SystemMessage(content="你是一个专业的食材识别专家。从用户输入中提取所有食材信息，整理为清晰的食材清单。如果用户提供了图片，请仔细辨识图片中的食材。只返回食材清单，不要添加其他内容。")
    response = qwen.invoke([system] + messages)

    return {
        "ingredients": response.content,
        "current_step": "食材识别完成",
        "messages": [response],
    }


def call_search_recipes(state: ChefState, config: RunnableConfig) -> dict:
    """
    Node 2: 根据食材搜索菜谱
    """
    ingredients = state.get("ingredients", "")
    query = f"用以下食材可以做哪些菜: {ingredients}"

    search_raw = web_search.invoke(query)
    return {
        "search_results": str(search_raw),
        "current_step": "菜谱搜索完成",
    }


def call_evaluate_recipes(state: ChefState, config: RunnableConfig) -> dict:
    """
    Node 3: 使用 Qwen 评估搜索结果，输出结构化菜谱
    """
    ingredients = state.get("ingredients", "")
    search_results = state.get("search_results", "")

    eval_prompt = f"""你是一个专业的菜谱评估专家。根据以下食材和搜索结果，推荐最佳菜谱。

当前可用食材: {ingredients}

搜索结果: {search_results}

请按以下JSON格式输出推荐结果（包含3-5个菜谱）:
{{
  "recipes": [
    {{
      "name": "菜名",
      "ingredients": ["食材1", "食材2"],
      "steps": ["步骤1", "步骤2", "步骤3"],
      "difficulty": "简单/中等/困难",
      "nutrition_score": 85,
      "overall_score": 90,
      "reason": "推荐理由",
      "image_url": "搜索结果中的成品图片URL（如果有）",
      "reference_url": "参考链接（如果有）"
    }}
  ],
  "summary": "总结建议"
}}

要求:
1. 确保菜谱覆盖不同口味和做法
2. nutrition_score 根据食材营养均衡程度评分
3. overall_score 综合营养、难度、口感评分
4. difficulty 根据步骤复杂度和烹饪时间判断
5. 步骤要简洁清晰，控制在3-5步
6. 如果搜索结果中有图片URL，填入 image_url
7. 如果搜索结果中有参考链接，填入 reference_url
8. 只返回JSON，不要添加其他文字
"""

    response = qwen.invoke([HumanMessage(content=eval_prompt)])
    content = response.content.strip()

    # Clean potential markdown code fences
    if content.startswith("```"):
        content = content.split("\n", 1)[1]
    if content.endswith("```"):
        content = content.rsplit("```", 1)[0]
    if content.startswith("json"):
        content = content[4:].strip()
    content = content.strip()

    try:
        data = json.loads(content)
        recipes = [Recipe(**r) for r in data.get("recipes", [])]
        summary = data.get("summary", "")
    except (json.JSONDecodeError, Exception):
        recipes = []
        summary = content

    return {
        "recipes": recipes,
        "summary": summary,
        "current_step": "菜谱评估完成",
        "messages": [response],
    }


def build_chef_graph(checkpointer=None) -> StateGraph:
    builder = StateGraph(ChefState)

    builder.add_node("identify_ingredients", call_identify_ingredients)
    builder.add_node("search_recipes", call_search_recipes)
    builder.add_node("evaluate_recipes", call_evaluate_recipes)

    builder.add_edge(START, "identify_ingredients")
    builder.add_edge("identify_ingredients", "search_recipes")
    builder.add_edge("search_recipes", "evaluate_recipes")
    builder.add_edge("evaluate_recipes", END)

    return builder.compile(checkpointer=checkpointer)


chief_agent = build_chef_graph()
