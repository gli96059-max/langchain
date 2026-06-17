import os
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model

load_dotenv()


qwen = init_chat_model(
    model="qwen3.7-plus",
    model_provider="openai",
    base_url=os.getenv("DASHSCOPE_BASE_URL"),
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    extra_body={"enable_thinking": False},
)