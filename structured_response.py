from pydantic import BaseModel, Field


class Reference(BaseModel):
    """
    参考资料
    """
    title: str
    url: str

class AnswerInfo(BaseModel):
    """
    答案信息
    """
    answer: str = Field(description="答案")
    references: list[Reference] = Field(description="参考资料")