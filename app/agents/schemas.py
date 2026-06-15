from pydantic import BaseModel, Field


class Recipe(BaseModel):
    """推荐食谱"""
    name: str = Field(description="菜名")
    ingredients: list[str] = Field(description="所需食材")
    steps: list[str] = Field(description="简洁做法步骤")
    difficulty: str = Field(description="难度: 简单/中等/困难")
    nutrition_score: int = Field(description="营养评分 0-100")
    overall_score: int = Field(description="综合评分 0-100")
    reason: str = Field(description="推荐理由")
    image_url: str | None = Field(default=None, description="成品图片URL")
    reference_url: str | None = Field(default=None, description="参考链接")
