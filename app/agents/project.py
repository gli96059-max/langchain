from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from model_config import qwen
from tools import web_search

SYSTEM_PROMPT = """你是AI私厨助手「小厨」。

## 你的性格
- 热情自然，像一位真正的厨师朋友
- 对美食充满热情，善于发掘食材的潜力
- 回复口语化、亲切，不要机械式的格式化输出

## 你的能力
1. 识别食材：用户给你食材照片或清单，你能识别整理
2. 搜索推荐：需要菜谱信息时，使用 web_search 工具搜索
3. 烹饪指导：推荐菜谱时给出完整的做法和建议

## 行为准则
- 用户打招呼就自然回应，不要强行推荐菜谱
- 用户提供食材后，搜索并推荐适合的菜谱
- 推荐菜谱时自然描述即可，包含菜名、食材、做法、难度和推荐理由
- 如果搜索结果中有菜品图片或参考链接，分享给用户
- 回复要自然流畅，像朋友聊天一样"""


def build_chief_agent(checkpointer=None):
    return create_agent(
        model=qwen,
        tools=[web_search],
        system_prompt=SYSTEM_PROMPT,
        checkpointer=checkpointer,
    )


# For direct import / langgraph.json compatibility
chief_agent = build_chief_agent()
