from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
import os

load_dotenv()

dp_base_url = os.getenv("DEEPSEEK_BASE_URL")
dp_api_key = os.getenv("DEEPSEEK_API_KEY")
qw_base_url = os.getenv("DASHSCOPE_BASE_URL")
qw_api_key = os.getenv("DASHSCOPE_API_KEY")


deepseek = init_chat_model(
    model="deepseek-v4-flash",
    model_provider="deepseek",
    base_url=dp_base_url,
    api_key=dp_api_key,
)

qwen= init_chat_model(
    model="qwen3.7-plus",
    model_provider="openai",
    base_url=qw_base_url,
    api_key=qw_api_key,
    extra_body={"enable_thinking": False},
)