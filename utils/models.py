from typing import Annotated, List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, conlist, field_validator, model_validator, ConfigDict

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

# ========== NPC 聊天專用回應模型 ==========
class NPCChatResponse(BaseModel):
    """NPC 對話快速回應 (僅 NPC 回覆，用於立即顯示)"""
    npc_reply: str = Field(description="NPC的劇情回覆 (English, 1-3 sentences)")
    is_english: bool = Field(description="使用者是否使用英文對話", default=True)

class NPCChatEvaluation(BaseModel):
    """NPC 對話評估 (異步處理，包含評分和中英對照回饋)"""
    language_score: int = Field(description="語言品質評分 (1-10): 文法和用詞準確性", ge=1, le=10)
    relevance_score: int = Field(description="相關性評分 (1-10): 問題理解度和主題相關性", ge=1, le=10)
    feedback_eng: str = Field(description="英文回饋 (1-2 sentences, empty if perfect)", default="")
    feedback_chi: str = Field(description="對應的繁體中文翻譯 (1-2 sentences, empty if perfect)", default="")

class QuestionAnswerResponse(BaseModel):
    """問題回答評估回應 (用於回答關卡問題時)"""
    score: int = Field(description="總分 (0-10)，根據答案正確性與語言品質", ge=0, le=10)
    feedback_chi: str = Field(description="繁體中文回饋，針對文法和用詞準確度給建議", default="")
    feedback_eng: str = Field(description="English feedback on grammar and vocabulary accuracy", default="")
    reference_comparison: str = Field(description="與參考答案的比較說明 (English)", default="")
    is_correct: bool = Field(description="答案是否基本正確", default=False)

class ImprovementHintResponse(BaseModel):
    """改善提示回應 - 不透露答案，只給方向性提示"""
    hint_eng: str = Field(
        description="English improvement hint - direction guidance without revealing answer",
        default=""
    )
    hint_chi: str = Field(
        description="繁體中文改善提示 - 方向性引導，不透露答案",
        default=""
    )

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

# ========== 遊戲計分模型 ==========
class GameQuestionScore(BaseModel):
    """追蹤單一題目的最高分"""
    question_idx: int = Field(description="題目索引")  # 題目索引
    best_score: int = Field(description="最高分數", default=0)  # 最高分數
    attempts: int = Field(description="嘗試次數", default=0)  # 嘗試次數
    hint_count: int = Field(description="使用改善提示次數", default=0)  # 新增：提示使用次數

class GameLevelScore(BaseModel):
    """追蹤單一關卡的分數 (包含多個題目)"""
    level_idx: int = Field(description="關卡索引")  # 關卡索引
    questions: Dict[int, GameQuestionScore] = Field(
        description="題目分數 (以題目索引為鍵)",
        default_factory=dict
    )
    completed: bool = Field(description="關卡是否完成", default=False)  # 關卡完成狀態
    
    def get_total_score(self) -> int:
        """計算此關卡的總分"""
        return sum(q.best_score for q in self.questions.values())
    
    def get_max_possible_score(self, questions_per_level: int = 3, max_score_per_question: int = 10) -> int:
        """計算此關卡的滿分"""
        return questions_per_level * max_score_per_question
    
    def check_completion(self, questions_per_level: int = 3, min_score_per_question: int = 6) -> bool:
        """檢查關卡是否完成 (所有題目都達到及格分數)"""
        if len(self.questions) < questions_per_level:
            return False
        for q in self.questions.values():
            if q.best_score < min_score_per_question:
                return False
        return True

class GameThemeScore(BaseModel):
    """追蹤整個主題的分數 (包含多個關卡)"""
    theme_id: str = Field(description="主題識別碼")  # 主題識別碼
    levels: Dict[int, GameLevelScore] = Field(
        description="關卡分數 (以關卡索引為鍵)",
        default_factory=dict
    )
    current_level: int = Field(description="當前解鎖到的關卡 (0-based)", default=0)  #當前進度
    
    def get_total_score(self) -> int:
        """計算此主題的總分"""
        return sum(level.get_total_score() for level in self.levels.values())
    
    def get_max_possible_score(self, num_levels: int = 5, questions_per_level: int = 3, max_score_per_question: int = 10) -> int:
        """計算此主題的滿分"""
        return num_levels * questions_per_level * max_score_per_question
    
    def get_unlocked_level(self) -> int:
        """取得已解鎖的最高關卡索引"""
        return self.current_level
    
    def unlock_next_level(self, max_levels: int = 5) -> bool:
        """解鎖下一關，回傳是否成功"""
        if self.current_level < max_levels - 1:
            self.current_level += 1
            return True
        return False

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
    
    def increment_hint_count(self, theme_id: str, level_idx: int, question_idx: int) -> int:
        """增加特定題目的提示使用次數，並回傳新的使用次數"""
        # 若主題不存在則初始化
        if theme_id not in self.themes:
            self.themes[theme_id] = GameThemeScore(theme_id=theme_id)
        
        theme = self.themes[theme_id]
        
        # 若關卡不存在則初始化
        if level_idx not in theme.levels:
            theme.levels[level_idx] = GameLevelScore(level_idx=level_idx)
        
        level = theme.levels[level_idx]
        
        # 若題目不存在則初始化
        if question_idx not in level.questions:
            level.questions[question_idx] = GameQuestionScore(
                question_idx=question_idx,
                best_score=0,
                attempts=0,
                hint_count=1
            )
            return 1
        else:
            level.questions[question_idx].hint_count += 1
            return level.questions[question_idx].hint_count
    
    def get_hint_count(self, theme_id: str, level_idx: int, question_idx: int) -> int:
        """取得特定題目的提示使用次數"""
        if theme_id not in self.themes:
            return 0
        theme = self.themes[theme_id]
        if level_idx not in theme.levels:
            return 0
        level = theme.levels[level_idx]
        if question_idx not in level.questions:
            return 0
        return level.questions[question_idx].hint_count
    
    def check_and_unlock_level(self, theme_id: str, level_idx: int, 
                                questions_per_level: int = 3, 
                                min_score_per_question: int = 6,
                                max_levels: int = 5) -> bool:
        """檢查並解鎖下一關卡"""
        if theme_id not in self.themes:
            return False
        
        theme = self.themes[theme_id]
        if level_idx not in theme.levels:
            return False
        
        level = theme.levels[level_idx]
        if level.check_completion(questions_per_level, min_score_per_question):
            level.completed = True
            # 如果當前關卡等於已解鎖關卡，則解鎖下一關
            if level_idx == theme.current_level:
                return theme.unlock_next_level(max_levels)
        return False
    
    def get_unlocked_level(self, theme_id: str) -> int:
        """取得某主題已解鎖的最高關卡"""
        if theme_id in self.themes:
            return self.themes[theme_id].get_unlocked_level()
        return 0  # 預設第一關解鎖
    
    def get_theme_score(self, theme_id: str) -> int:
        """取得主題總分"""
        if theme_id in self.themes:
            return self.themes[theme_id].get_total_score()
        return 0
    
    def to_dict(self) -> dict:
        return self.model_dump(exclude_none=True)

# ========== 互動紀錄模型 ==========
class GameInteractionLog(BaseModel):
    """遊戲互動紀錄 (優化版：支持詳細評分)"""
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
    score: Optional[int] = Field(description="總評分", default=None)
    feedback: Optional[str] = Field(description="回饋內容 (可能包含中英對照)", default=None)
    
    def to_dict(self) -> dict:
        return self.model_dump(exclude_none=True)

class User(BaseModel):
    id: str = Field(description="學號")  # 學號
    dep: str = Field(description="系級") # 系級
    name: str = Field(description='姓名')  # 姓名
    class_time: int = Field(description='上課時段')  # 上課時段 
    history: dict[str, list[SpeechAssessment]] = Field(description='歷史紀錄')  # 歷史紀錄
    chat: ChatHistory = Field(description='聊天紀錄', default_factory=lambda: ChatHistory())  # 聊天紀錄
    # 遊戲分數
    game_scores: GameScores = Field(description='遊戲分數', default_factory=lambda: GameScores())  # 遊戲分數
    # NPC聊天紀錄 (分開儲存)
    npc_chat_history: dict[str, list[dict]] = Field(description='NPC聊天紀錄', default_factory=dict)  # NPC聊天紀錄
    # NPC對話評估紀錄 (用於教學研究分析)
    npc_evaluation_history: dict[str, list[dict]] = Field(description='NPC對話詳細評估紀錄', default_factory=dict)  # NPC評估紀錄
    # 問題回答紀錄 (分開儲存)
    question_history: dict[str, list[dict]] = Field(description='問題回答紀錄', default_factory=dict)  # 問題回答紀錄
    
    def to_dict(self) -> dict:
        return self.model_dump(exclude_none=True)

class UserState(BaseModel):
    category: Optional[str] = Field(description="類別", default=None)  # 類別
    sub:  Optional[int] = Field(description="子題", default=-1)  # 子題
    sex: Optional[int] = Field(description="性別", default=0)  # 性別
    accent: Optional[int] = Field(description="口音", default=0)  # 口音
    # 遊戲狀態
    game_theme: Optional[str] = Field(description="目前遊戲主題", default=None)  # 目前遊戲主題
    game_level: Optional[int] = Field(description="目前遊戲關卡", default=-1)  # 目前遊戲關卡
    game_question: Optional[int] = Field(description="目前遊戲題目", default=-1)  # 目前遊戲題目
    # [FIX] 改為 -1 表示尚未選擇 NPC，避免 npc_idx=0 被誤認為已選擇第一個 NPC
    game_npc: Optional[int] = Field(description="目前NPC索引 (-1 表示未選擇)", default=-1)  # 目前NPC索引
    in_npc_chat: bool = Field(description="是否在NPC對話模式", default=False)  # NPC對話模式標記
    # 關卡內的答題進度追蹤 (格式: "theme_id-level_idx" -> 目前應回答的題目索引)
    level_question_progress: Dict[str, int] = Field(
        description="關卡內的題目進度追蹤", 
        default_factory=dict
    )
    # 記錄使用者是否已與NPC對話過 (用於提示使用者先與NPC對話)
    has_talked_to_npc: bool = Field(description="是否已與NPC對話過", default=False)
    # 記錄上次回答的資訊，用於改善提示功能
    last_answer_info: Optional[Dict[str, Any]] = Field(
        description="上次回答的資訊 (題目、回答、分數等)", 
        default=None
    )


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

# ========== 遊戲主題配置模型 ==========
class GameNPC(BaseModel):
    """遊戲主題的NPC配置"""
    # Pydantic v2 正確語法
    model_config = ConfigDict(populate_by_name=True)
    
    id: str = Field(description="NPC識別碼")  # NPC識別碼
    name: str = Field(description="NPC顯示名稱")  # NPC顯示名稱
    persona: str = Field(description="NPC人設/背景 (給AI用)")  # NPC人設/背景
    # 支援 theme_config.json 中的 "display_description" 欄位名稱
    description: str = Field(
        description="NPC描述 (顯示給使用者)", 
        default="",
        alias="display_description"  # 允許從 display_description 讀取
    )
    file: str = Field(description="此NPC的RAG文件檔案")  # RAG文件檔案
    image: Optional[str] = Field(description="NPC頭像圖片檔名", default=None)  # 頭像圖片
    background: Optional[str] = Field(description="NPC背景故事", default=None)

class GameLevelQuestion(BaseModel):
    """遊戲關卡中的單一題目"""
    text: str = Field(description="題目文字")  # 題目文字
    hint: Optional[str] = Field(description="可選提示", default=None)  # 可選提示
    reference_answers: List[str] = Field(description="參考答案列表", default_factory=list)  # 參考答案
    # [FIX] 支援單數形式的 reference_answer (theme_config.json 使用此欄位)
    reference_answer: Optional[str] = Field(description="單一參考答案 (會被合併到 reference_answers)", default=None, exclude=True)
    
    @model_validator(mode='before')
    @classmethod
    def merge_reference_answer(cls, data: Any) -> Any:
        """將單數的 reference_answer 合併到 reference_answers 列表中"""
        if isinstance(data, dict):
            # 取得已有的 reference_answers
            ref_answers = data.get('reference_answers', [])
            if isinstance(ref_answers, str):
                ref_answers = [ref_answers]
            elif ref_answers is None:
                ref_answers = []
            
            # 取得單數的 reference_answer
            single_answer = data.get('reference_answer')
            if single_answer and single_answer not in ref_answers:
                ref_answers.append(single_answer)
            
            data['reference_answers'] = ref_answers
        return data
    
    def get_all_reference_answers(self) -> List[str]:
        """取得所有參考答案"""
        return self.reference_answers if self.reference_answers else []

    def parse_tiered_reference_answers(self) -> Optional[Dict[int, List[str]]]:
        """
        解析十級評分參考答案格式。
        格式：每行以「分數\\t例句1|例句2|...」構成，行之間以\\n分隔。
        若 reference_answers 不符合此格式，回傳 None。

        Parse tiered (10-level) reference answer format.
        Format: each line is 'score\\texample1|example2|...', lines separated by \\n.
        Returns None if reference_answers does not match this format.
        """
        if not self.reference_answers:
            return None

        # 合併成單一字串進行解析
        raw = "\n".join(self.reference_answers)

        tiered: Dict[int, List[str]] = {}
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            # 期待格式：「10\t例句1|例句2」
            if '\t' not in line:
                return None  # 非十級格式，放棄解析
            parts = line.split('\t', 1)
            try:
                score_level = int(parts[0].strip())
            except ValueError:
                return None
            examples = [ex.strip() for ex in parts[1].split('|') if ex.strip()]
            tiered[score_level] = examples

        if not tiered:
            return None
        return tiered

    def get_tiered_reference_answers(self) -> Optional[Dict[int, List[str]]]:
        """取得十級評分參考答案（若格式不符則回傳 None）"""
        return self.parse_tiered_reference_answers()

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
    intro_video: Optional[str] = Field(description="主題介紹影片", default=None)  # 主題介紹影片
    novel_url: Optional[str] = Field(description="小說全文網頁連結", default=None)  # 小說全文連結
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