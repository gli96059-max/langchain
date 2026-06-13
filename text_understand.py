from langchain.messages import HumanMessage, AIMessage, SystemMessage
from langchain.tools import tool
from langchain.agents import create_agent
from pydantic import BaseModel
from model_config import deepseek,qwen
from tools import get_weather,web_search
from structured_response import AnswerInfo
from langgraph.checkpoint.memory import InMemorySaver



# response = model.invoke(
#     [
#         SystemMessage(
#             content="You are a helpful assistant."
#         ),
#         HumanMessage(content="你是谁"),
#     ]
# )
#
# response.pretty_print()

system_prompt = """
# 身份
- 你是一个地理专家，你帮助用户查询城市
# 指令 
- 不要返回markdown格式说明，仅仅返回城市信息即可。
# 示例

#
"""
config = {"configurable": {"thread_id": "thread_11"}}
agent = create_agent(
    model = qwen,
    tools = [web_search],
    system_prompt = "你是一个智能助手",
    # system_prompt = system_prompt,
    # response_format= AnswerInfo,
    checkpointer=InMemorySaver()
  )
response = agent.invoke(
    {
    "messages": [
        HumanMessage(content="我是龙哥 ")
    ]
    },
    config
)
print(response)
