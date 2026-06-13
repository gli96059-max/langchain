import os
import certifi

os.environ["SSL_CERT_FILE"] = certifi.where()
from typing import Literal
from langchain.tools import tool
from pydantic import BaseModel,Field
from langchain_tavily import TavilySearch

class wheather_input(BaseModel):
    location: str = Field(description="城市")
    units: Literal['celsius', 'fahrenheit'] = Field(default="celsius",description="单位")
    include_forecast: bool = Field(default=False,description="是否包含预报")

@tool(args_schema=wheather_input)
def get_weather(location: str, units: Literal['celsius', 'fahrenheit'] = "celsius", include_forecast: bool = False):
    """
    用来获取天气的工具
    """
    temp = 22 if units == "celsius" else 72
    result = f"It's {temp} degrees in {location}."
    if include_forecast:
        result += " The forecast is partly cloudy."
    return  result



tavily = TavilySearch(
    max_results=5,
    topic="general",
    # include_answer=False,
    # include_raw_content=False,
    # include_images=False,
    # include_image_descriptions=False,
    # search_depth="basic",
    # time_range="day",
    # include_domains=None,
    # exclude_domains=None
)
@tool
def web_search(query: str):
    """
    用来搜索的工具
    """
    return tavily.invoke(query)