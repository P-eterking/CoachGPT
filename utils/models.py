from typing import List, Optional
from pydantic import BaseModel, Field

class SpeechAssessment(BaseModel):
    chi_suggestion: str = Field(description="繁體中文建議 Traditional Chinese (zh-TW) suggestion", default_factory=lambda: "無建議。")  # 中文建議
    eng_suggestion: str = Field(description="英文建議 English suggestion", default_factory=lambda: "No suggestion.")  # 英文建議
    score: int = Field(description="評量分數", default_factory=lambda: 1)  # 分數
    transcript: str = Field(description="轉錄後文本", default_factory=lambda: "")  # 使用者回答的轉錄文本
    better_ans: str = Field(description="改善後文本", default_factory=lambda: "")  # 改進的回覆範例
    timestamp: float = Field(description="時間戳記", default_factory=lambda: 0.0) # 時間戳記
    
    def to_dict(self) -> dict:
        return self.model_dump()

class User(BaseModel):
    id: str = Field(description="學號")  # 學號
    dep: str = Field(description="系級") # 系級
    name: str = Field(description='姓名')  # 姓名
    class_time: str = Field(description='上課時段')  # 上課時段
    history: dict[str,SpeechAssessment] = Field(description='歷史紀錄')  # 歷史紀錄
    
    def to_dict(self) -> dict:
        return self.model_dump()

class Question(BaseModel):
    text: str = Field(description="問題文本")  # 問題文本
    assessment_standard: Optional[str] = Field(description="評量標準", default=None)   # 評量標準
    image_url: Optional[str] = Field(description="圖片網址", default=None) # 圖片網址
    extra_info: Optional[List[List[str]]] = Field(description="額外資訊", default=None) # 額外資訊
    max_score: Optional[int] = Field(description="最高分", default=None) # 最高分