from typing import Annotated, List, Optional, Dict, Any
from pydantic import BaseModel, Field, conlist

class SpeechAssessment(BaseModel):
    chi_suggestion: str = Field(description="繁體中文建議 Traditional Chinese (zh-TW) suggestion", default_factory=lambda: "無建議。")  # 中文建議
    eng_suggestion: str = Field(description="英文建議 English suggestion", default_factory=lambda: "No suggestion.")  # 英文建議
    score: int = Field(description="評量分數", default_factory=lambda: 1)  # 分數
    transcript: str = Field(description="轉錄後文本", default_factory=lambda: "")  # 使用者回答的轉錄文本
    better_ans: str = Field(description="改善後文本", default_factory=lambda: "")  # 改進的回覆範例
    timestamp: float = Field(description="時間戳記", default_factory=lambda: 0.0) # 時間戳記
    
    def to_dict(self) -> dict:
        return self.model_dump(exclude_none=True)

class GameResponse(BaseModel):
    npc_reply: str = Field(description="NPC 根據人設與劇情的回覆內容 (English)")
    feedback: str = Field(description="針對使用者的語法或用詞建議 (繁體中文)")
    score: int = Field(description="語言能力評分 (1-10)", ge=1, le=10)

# ========== 新增: NPC對話與題目回答的分離模型 ==========

class NPCChatResponse(BaseModel):
    """NPC對話回應 (不計分，僅劇情互動)"""
    npc_reply: str = Field(description="NPC的劇情回覆 (English, 1-3 sentences)")
    feedback: str = Field(description="語言學習建議 (繁體中文, 1 sentence max)", default="")
    is_english: bool = Field(description="使用者是否使用英文對話", default=True)

class QuestionAnswerResponse(BaseModel):
    """題目回答回應 (計分)"""
    score: int = Field(description="回答評分 (0-10): 內容正確性0-5 + 語言品質0-5", ge=0, le=10)
    feedback_chi: str = Field(description="評語回饋 (繁體中文)")
    feedback_eng: str = Field(description="評語回饋 (English)")
    reference_comparison: str = Field(description="與參考答案的比較說明 (English)", default="")

class GameInteractionLog(BaseModel):
    """遊戲互動紀錄"""
    user_id: str = Field(description="使用者ID")
    timestamp: float = Field(description="時間戳記")
    interaction_type: str = Field(description="互動類型: 'npc_chat' or 'question_answer'")
    theme_id: str = Field(description="主題ID")
    level_idx: Optional[int] = Field(description="關卡索引", default=None)
    question_idx: Optional[int] = Field(description="題目索引", default=None)
    npc_idx: Optional[int] = Field(description="NPC索引", default=None)
    npc_name: Optional[str] = Field(description="NPC名稱", default=None)
    user_transcript: str = Field(description="使用者語音轉錄文字")
    ai_response: str = Field(description="AI回應內容")
    score: Optional[int] = Field(description="評分 (僅題目回答)", default=None)
    feedback: Optional[str] = Field(description="回饋內容", default=None)
    
    def to_dict(self) -> dict:
        return self.model_dump(exclude_none=True)

# ========== 結束新增 ==========

# RAG 切片模型
class RagChunk(BaseModel):
    content: str = Field(description="切片後的文本內容")
    metadata: Dict[str, Any] = Field(description="元數據 (如標題來源)", default={})
    embedding: Optional[List[float]] = Field(description="向量數據", default=None)

class ChatHistory(BaseModel):
    questions: List[str] = Field(description="問題", default=[])  # 問題
    answers: List[str] = Field(description="回答", default=[])  # 回答

class ChatSummary(BaseModel):
    chi_summary: str = Field(description="繁體中文摘要 Traditional Chinese (zh-TW) summary", default_factory=lambda: "無摘要。")  # 中文摘要
    eng_summary: str = Field(description="英文摘要 English summary", default_factory=lambda: "No summary.")  # 英文摘要

class ChatSummaryAndScore(BaseModel):
    summary: ChatSummary = Field(description="摘要", default_factory=lambda: ChatSummary())  # 摘要
    score: int = Field(description="分數", default_factory=lambda: 0, ge=0, le=10)  # 分數

# ========== 新增: 遊戲計分模型 ==========
class GameQuestionScore(BaseModel):
    """追蹤單一題目的最高分"""
    question_idx: int = Field(description="題目索引")  # 題目索引
    best_score: int = Field(description="最高分數", default=0)  # 最高分數
    attempts: int = Field(description="嘗試次數", default=0)  # 嘗試次數

class GameLevelScore(BaseModel):
    """追蹤單一關卡的分數 (包含多個題目)"""
    level_idx: int = Field(description="關卡索引")  # 關卡索引
    questions: Dict[int, GameQuestionScore] = Field(
        description="題目分數 (以題目索引為鍵)",
        default_factory=dict
    )
    
    def get_total_score(self) -> int:
        """計算此關卡的總分"""
        return sum(q.best_score for q in self.questions.values())
    
    def get_max_possible_score(self, questions_per_level: int = 3, max_score_per_question: int = 10) -> int:
        """計算此關卡的滿分"""
        return questions_per_level * max_score_per_question

class GameThemeScore(BaseModel):
    """追蹤整個主題的分數 (包含多個關卡)"""
    theme_id: str = Field(description="主題識別碼")  # 主題識別碼
    levels: Dict[int, GameLevelScore] = Field(
        description="關卡分數 (以關卡索引為鍵)",
        default_factory=dict
    )
    
    def get_total_score(self) -> int:
        """計算此主題的總分"""
        return sum(level.get_total_score() for level in self.levels.values())
    
    def get_max_possible_score(self, num_levels: int = 5, questions_per_level: int = 3, max_score_per_question: int = 10) -> int:
        """計算此主題的滿分"""
        return num_levels * questions_per_level * max_score_per_question

class GameScores(BaseModel):
    """所有主題的遊戲分數容器"""
    themes: Dict[str, GameThemeScore] = Field(
        description="主題分數 (以主題識別碼為鍵)",
        default_factory=dict
    )
    
    def update_score(self, theme_id: str, level_idx: int, question_idx: int, score: int) -> bool:
        """
        更新特定題目的分數。若為新高分則回傳 True。
        若該題目已作答過，則取較高分數。
        """
        # 若主題不存在則初始化
        if theme_id not in self.themes:
            self.themes[theme_id] = GameThemeScore(theme_id=theme_id)
        
        theme = self.themes[theme_id]
        
        # 若關卡不存在則初始化
        if level_idx not in theme.levels:
            theme.levels[level_idx] = GameLevelScore(level_idx=level_idx)
        
        level = theme.levels[level_idx]
        
        # 初始化或更新題目分數
        if question_idx not in level.questions:
            level.questions[question_idx] = GameQuestionScore(
                question_idx=question_idx,
                best_score=score,
                attempts=1
            )
            return True
        else:
            q = level.questions[question_idx]
            q.attempts += 1
            if score > q.best_score:
                q.best_score = score
                return True
            return False
    
    def get_theme_score(self, theme_id: str) -> int:
        """取得主題總分"""
        if theme_id in self.themes:
            return self.themes[theme_id].get_total_score()
        return 0
    
    def to_dict(self) -> dict:
        return self.model_dump(exclude_none=True)

# ========== 結束新增 ==========

class User(BaseModel):
    id: str = Field(description="學號")  # 學號
    dep: str = Field(description="系級") # 系級
    name: str = Field(description='姓名')  # 姓名
    class_time: int = Field(description='上課時段')  # 上課時段 
    history: dict[str, list[SpeechAssessment]] = Field(description='歷史紀錄')  # 歷史紀錄
    chat: ChatHistory = Field(description='聊天紀錄', default_factory=lambda: ChatHistory())  # 聊天紀錄
    # 新增: 遊戲分數
    game_scores: GameScores = Field(description='遊戲分數', default_factory=lambda: GameScores())  # 遊戲分數
    
    def to_dict(self) -> dict:
        return self.model_dump(exclude_none=True)

class UserState(BaseModel):
    category: Optional[str] = Field(description="類別", default=None)  # 類別
    sub:  Optional[int] = Field(description="子題", default=-1)  # 子題
    sex: Optional[int] = Field(description="性別", default=0)  # 性別
    accent: Optional[int] = Field(description="口音", default=0)  # 口音
    # 新增: 遊戲狀態
    game_theme: Optional[str] = Field(description="目前遊戲主題", default=None)  # 目前遊戲主題
    game_level: Optional[int] = Field(description="目前遊戲關卡", default=-1)  # 目前遊戲關卡
    game_question: Optional[int] = Field(description="目前遊戲題目", default=-1)  # 目前遊戲題目
    game_npc: Optional[int] = Field(description="目前NPC索引", default=0)  # 目前NPC索引
    # 修改2: 新增 in_npc_chat 狀態標記
    in_npc_chat: bool = Field(description="是否正在與NPC對話中", default=False)  # NPC對話模式
    

class Question(BaseModel):
    text: str = Field(description="問題文本")  # 問題文本
    assessment_standard: Optional[str] = Field(description="評量標準", default=None)   # 評量標準
    image_url: Optional[str] = Field(description="圖片網址", default=None) # 圖片網址
    extra_info: Optional[List[List[str]]] = Field(description="額外資訊", default=None) # 額外資訊
    max_score: Optional[int] = Field(description="最高分", default=None) # 最高分
    
    def to_dict(self) -> dict:
        return self.model_dump(exclude_none=True)

class QuestionCategory(BaseModel):
    # enabled: bool = Field(description="是否啟用", default=True)  # 是否啟用
    # response: bool = Field(description="是否回饋", default=True)  # 是否回饋
    content: List[Question] = Field(description="問題")  # 問題
    
    def to_dict(self) -> dict:
        return self.model_dump(exclude_none=True)

class QuestionSet(BaseModel):
    questions: list[str] = Field(description="問題集") # 問題集

# ========== 新增: 遊戲主題配置模型 ==========
class GameNPC(BaseModel):
    """遊戲主題的NPC配置"""
    id: str = Field(description="NPC識別碼")  # NPC識別碼
    name: str = Field(description="NPC顯示名稱")  # NPC顯示名稱
    persona: str = Field(description="NPC人設/背景")  # NPC人設/背景
    file: str = Field(description="此NPC的RAG文件檔案")  # RAG文件檔案
    # 修改5: 新增 image 欄位
    image: Optional[str] = Field(description="NPC頭像圖片檔案名稱", default=None)  # NPC頭像圖片

class GameLevelQuestion(BaseModel):
    """遊戲關卡中的單一題目"""
    text: str = Field(description="題目文字")  # 題目文字
    hint: Optional[str] = Field(description="可選提示", default=None)  # 可選提示
    reference_answer: Optional[str] = Field(description="參考答案", default=None)  # 參考答案 (用於評分)

class GameLevel(BaseModel):
    """遊戲主題中的單一關卡"""
    id: int = Field(description="關卡索引 (從0開始)")  # 關卡索引
    title: str = Field(description="關卡標題")  # 關卡標題
    description: str = Field(description="關卡描述")  # 關卡描述
    video_file: Optional[str] = Field(description="影片檔案路徑", default=None)  # 影片檔案路徑
    questions: List[GameLevelQuestion] = Field(description="此關卡的題目")  # 題目列表

class GameThemeConfig(BaseModel):
    """單一遊戲主題的配置"""
    id: str = Field(description="主題識別碼")  # 主題識別碼
    name: str = Field(description="主題顯示名稱")  # 主題顯示名稱
    prologue: str = Field(description="主題前情提要/背景故事")  # 前情提要
    cover_image: Optional[str] = Field(description="封面圖片網址", default=None)  # 封面圖片
    # 修改4: 新增 intro_video 欄位
    intro_video: Optional[str] = Field(description="主題介紹影片檔案名稱", default=None)  # 介紹影片
    npcs: List[GameNPC] = Field(description="可用的NPC列表")  # NPC列表
    levels: List[GameLevel] = Field(description="遊戲關卡列表")  # 關卡列表
    
    def get_npc(self, npc_idx: int) -> Optional[GameNPC]:
        if 0 <= npc_idx < len(self.npcs):
            return self.npcs[npc_idx]
        return None
    
    def get_level(self, level_idx: int) -> Optional[GameLevel]:
        if 0 <= level_idx < len(self.levels):
            return self.levels[level_idx]
        return None

# ========== 結束新增 ==========