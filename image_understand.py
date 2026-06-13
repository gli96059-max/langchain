from langchain.agents import create_agent
from langchain.messages import HumanMessage,AIMessage,SystemMessage
from base_64 import img_base64
from model_config import qwen


qwen_agent = create_agent(
    model=qwen,
    system_prompt="请你以硬件工程师的口吻对话"
)


# response = qwen_agent.stream(
#     {
#     "messages": [
#         HumanMessage(content = [
#             {"type": "text", "text": "描述下面的图片"},
#             {"type": "image_url",
#              "image_url": {"url": "https://img.iplaysoft.com/wp-content/uploads/2019/free-images/free_stock_photo_2x.jpg!0x0.webp"}}
#         ])
#     ]
#     }
# )

# message = HumanMessage(content = [
#     {"type": "text", "text": "描述下面的图片"},
#     {"type": "image_url",
#      "image_url": "https://img.iplaysoft.com/wp-content/uploads/2019/free-images/free_stock_photo_2x.jpg!0x0.webp"}
# ])
#
# stream = qwen_agent.stream(
#     {"messages":[message]},
#     stream_mode= "messages"
# )
# for chunk,metadata in stream:
#     if chunk.content:
#         print(chunk.content,end="",flush=True)

base64_question = HumanMessage(content = [
    {"type": "text", "text": "描述下面的图片"},
    {"type": "image_url",
     "image_url": f"data:image/png;base64,{img_base64}"
    }
])

stream = qwen_agent.stream(
    {"messages":[base64_question]},
    stream_mode= "messages"
)
for chunk,metadata in stream:
    if chunk.content:
        print(chunk.content,end="",flush=True)