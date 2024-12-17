from typing import Annotated, List, Optional
from pydantic import BaseModel, Field

class SpeechAssessment(BaseModel):
    chi_suggestion: Annotated[str, 'Traditional Chinese suggestion'] = Field(default_factory=lambda: "無建議。")  # 中文建議
    eng_suggestion: Annotated[str, 'English suggestion'] = Field(default_factory=lambda: "No suggestion.")  # 英文建議
    score: Annotated[int, '評量分數'] = Field(default_factory=lambda: 1)  # 分數
    transcript: Annotated[str, '轉錄後文本'] = Field(default_factory=lambda: "")  # 使用者回答的轉錄文本
    better_ans: Annotated[str, '改善後文本'] = Field(default_factory=lambda: "")  # 改進的回覆範例
    timestamp: Annotated[float, '時間戳記'] = Field(default_factory=lambda: 0.0) # 時間戳記
    
    def to_dict(self) -> dict:
        return self.model_dump()

class User(BaseModel):
    id: Annotated[str, '學號']  # 學號
    dep: Annotated[str, '系級']  # 系級
    name: Annotated[str, '姓名']  # 姓名
    class_time: Annotated[str, '上課時段']  # 上課時段
    history: Annotated[dict[str,SpeechAssessment], '歷史紀錄']  # 歷史紀錄
    
    def to_dict(self) -> dict:
        return self.model_dump()

class Question(BaseModel):
    text: Annotated[str, '問題文本']  # 問題文本
    assessment_standard: Annotated[str, '評量標準']   # 評量標準
    image_url: Optional[Annotated[str, '圖片網址']] = Field(default=None) # 圖片網址
    extra_info: Optional[Annotated[List[List[str]], '額外資訊']] = Field(default=None) # 額外資訊