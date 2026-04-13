import json
import aiofiles
import asyncio
import os
import re
import time
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from config import USER_DATA_FILE, CONFIG_FILE, client
from utils.models import (
    ChatHistory, User, SpeechAssessment, UserState, RagChunk,
    GameThemeConfig, GameScores, GameThemeScore, GameLevelScore, GameQuestionScore,
    GameInteractionLog
)

# 使用者狀態和資料
user_state: dict[str, UserState] = {}  # 儲存每個使用者的即時狀態
user_data: dict[str, User] = {}  # 儲存每個使用者的詳細資料，包括歷史紀錄
_lock = asyncio.Lock()

# 預設設定
DEFAULT_CONFIG = {
    'admin': [],
    'rich_menu_ids': {},
    'enabled': [],
    'response': [],
    'rag_mode': False,
    'display_feedback': True,
    'service_number': 4,
    # 遊戲設定
    'game_themes': ['theme1', 'theme2', 'theme3'],
    'levels_per_theme': 5,
    'questions_per_level': 3,
    'max_score_per_question': 10,
    'min_score_to_pass': 6,
    # 遊戲大廳介紹媒體設定 (Game lobby intro media config)
    # 管理員可修改這些欄位來更新遊戲大廳頁面的內容
    # Admins may edit these fields to update game lobby intro content
    'game_story_eng': (
        "In a world where mystery lurks in every corner of London, "
        "three brilliant minds stand ready to help: Dr. John Watson, who gathers physical evidence; "
        "Mycroft Holmes, who provides government clearance and coded access; "
        "and Sherlock Holmes, who observes details invisible to ordinary eyes. "
        "Together, you must piece together clues from each character to solve the case "
        "before it is too late."
    ),
    'game_story_chi': (
        "在倫敦每個角落都潛藏謎團的世界中，"
        "三位傑出的人物隨時準備好協助你：收集實物證據的華生醫生、"
        "提供政府授權和密碼存取的麥考夫·霍姆斯，"
        "以及能觀察到常人看不見細節的夏洛克·霍姆斯。"
        "你必須從每個角色身上拼湊線索，在一切為時已晚之前破解案件。"
    ),
    # 人物介紹影片路徑設定
    # Characters intro video path configuration
    #
    # 支援兩種格式 (either format works):
    #   1. 只填檔名 (bare filename, placed in /templates/videos/ on the server):
    #      'game_characters_video': 'characters_intro.mp4'
    #   2. 完整路徑 (full URL path from site root):
    #      'game_characters_video': '/templates/videos/characters_intro.mp4'
    #
    # 留空字串代表停用，顯示佔位文字卡片。
    # Empty string disables the feature and shows a placeholder card.
    'game_characters_video': 'NPCintroduce.mp4',
    # 遊戲架構圖片路徑 (相對於網站根目錄)
    # Question structure image path (relative to site root)
    #
    # 支援兩種格式 (either format works):
    #   1. 只填檔名 (bare filename, placed in /templates/ on the server):
    #      'game_structure_image': 'structure.jpg'
    #   2. 完整路徑 (full URL path from site root):
    #      'game_structure_image': '/templates/structure.jpg'
    'game_structure_image': '/templates/structure.jpg'
}

# 設定檔案
config = DEFAULT_CONFIG.copy()

_rag_cache: Dict[str, List[RagChunk]] = {}
_rag_lock = asyncio.Lock()

# 遊戲主題配置快取
_game_theme_cache: Dict[str, GameThemeConfig] = {}

# new_test 題目快取 (pretest1 / posttest1 使用)
_new_test_questions: list = []
_new_test_loaded: bool = False

# 記錄每位使用者最近一次 NPC 回覆，用於「顯示文字 / Show Text」功能
_last_npc_replies: Dict[str, Dict] = {}

# ========== 檔案路徑處理 (修復 Docker 持久化問題) ==========

def get_user_data_file() -> str:
    """
    取得使用者資料檔案路徑。
    修復說明：在 Docker 環境中，主機的 data/user_data{N}.json 會被掛載為容器內的 /app/user_data.json。
    因此程式碼應直接操作 user_data.json (由 config.USER_DATA_FILE 定義)，
    而非嘗試在容器內建立 data/user_data{N}.json。
    """
    return USER_DATA_FILE

def get_interaction_log_file() -> str:
    """取得服務特定的互動紀錄檔案路徑"""
    # 互動紀錄同樣建議寫入掛載目錄，這裡假設寫入 data 資料夾(若有掛載)或專案根目錄
    return 'data/interaction_log.json'

def get_display_feedback() -> bool:
    """取得是否顯示回饋的設定"""
    return config.get('display_feedback', True)

# ========== 使用者狀態管理 ==========

def get_user_state(user_id: str) -> UserState | None:
    global user_state
    if user_state.get(user_id) is None:
        user_state[user_id] = UserState()
    return user_state.get(user_id)

def clear_rich_menu_id():
    config['rich_menu_ids'] = {}

def get_rich_menu_id(category: str) -> str | None:
    return config.get('rich_menu_ids').get(category)

def get_rich_menu_category_from_id(rich_menu_id: str) -> str | None:    
    for category, id in config.get('rich_menu_ids').items():
        if id == rich_menu_id:
            return category
    return None

def set_rich_menu_id(rich_menu_id: str, category: str):
    config['rich_menu_ids'][category] = rich_menu_id

# ========== 使用者資料操作 ==========

# 初始化使用者資料
def initData(user_id, classTime, dep, id, name):
    user_data[user_id] = User(
        dep=dep, id=id, name=name, class_time=classTime, 
        history={}, chat={}, game_scores=GameScores(),
        npc_chat_history={}, question_history={}
    )

# 刪除使用者資料
def delData(user_id):
    if user_data.get(user_id) is not None:
        del user_data[user_id]

# 檢查是否已有使用者資料
def hasData(user_id) -> bool:
    return user_data.get(user_id) is not None

# 獲取使用者資料
def getData() -> dict:
    return user_data

# 獲取單一使用者
def getUser(user_id: str) -> User | None:
    return user_data.get(user_id)

# 更新使用者的聊天紀錄
def getChatHistory(user_id: str) -> ChatHistory:
    return user_data[user_id].chat

def updateChatHistory(user_id, chat: ChatHistory):
    user_data[user_id].chat = chat

# 更新使用者的歷史紀錄
def updateHistory(user_id, key, history: SpeechAssessment):
    if key not in user_data[user_id].history:
        user_data[user_id].history[key] = []
    user_data[user_id].history[key].append(history)

# 獲取使用者的歷史紀錄
def getHistory(user_id, key) -> list[SpeechAssessment] | None:
    return user_data[user_id].history.get(key, None)

# ========== 管理員與功能開關 ==========

def isAdmin(user_id) -> bool:
    return user_id in config['admin']

async def addAdmin(user_id):
    config['admin'].append(user_id)
    config['admin'] = list(set(config['admin']))

def addEnabled(category):
    config['enabled'].append(category)
    config['enabled'] = list(set(config['enabled']))

def removeEnabled(category):
    config['enabled'].remove(category)

def isEnabled(category):
    return category in config['enabled']

def addResponse(category):
    config['response'].append(category)
    config['response'] = list(set(config['response']))

def removeResponse(category):
    config['response'].remove(category)

def isResponse(category):
    return category in config['response']

# ========== Feature Display Names (for admin messages) ==========

FEATURE_DISPLAY_NAMES = {
    'pretest': '前測',
    'posttest': '後測',
    'chat': '聊天功能',
    'rag_test': '遊戲功能',
    'ex1': '練習一',
    'ex2': '練習二',
    'ex3': '練習三',
    'ex4': '練習四',
    'ex5': '練習五',
    'ex6': '練習六',
}

def get_feature_display_name(alias: str) -> str:
    """取得功能的中文顯示名稱"""
    return FEATURE_DISPLAY_NAMES.get(alias, alias)

# ========== 遊戲主題功能 ==========

def get_game_themes() -> List[str]:
    """取得可用的遊戲主題ID列表"""
    return config.get('game_themes', ['theme1', 'theme2', 'theme3'])

def get_levels_per_theme() -> int:
    """取得每個主題的關卡數"""
    return config.get('levels_per_theme', 5)

def get_questions_per_level() -> int:
    """取得每個關卡的題目數"""
    return config.get('questions_per_level', 3)

def get_max_score_per_question() -> int:
    """取得每題滿分"""
    return config.get('max_score_per_question', 10)

def get_min_score_to_pass() -> int:
    """取得及格分數"""
    return config.get('min_score_to_pass', 6)

def load_game_theme_config(theme_id: str) -> Optional[GameThemeConfig]:
    """從JSON檔案載入遊戲主題配置"""
    global _game_theme_cache
    
    if theme_id in _game_theme_cache:
        return _game_theme_cache[theme_id]
    
    config_path = Path(f'category/rag_docs/{theme_id}/theme_config.json')
    print(f"[DEBUG] Attempting to load theme config from: {config_path.absolute()}")
    
    if not config_path.exists():
        print(f"[WARNING] Theme config file not found: {config_path.absolute()}")
        return None
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            print(f"[DEBUG] Successfully loaded JSON for theme: {theme_id}")
            theme_config = GameThemeConfig(**data)
            _game_theme_cache[theme_id] = theme_config
            print(f"[DEBUG] Successfully parsed GameThemeConfig for theme: {theme_id}")
            return theme_config
    except json.JSONDecodeError as e:
        print(f"[ERROR] JSON decode error for {theme_id}: {e}")
        import traceback
        traceback.print_exc()
        return None
    except Exception as e:
        print(f"[ERROR] Error loading game theme config for {theme_id}: {e}")
        import traceback
        traceback.print_exc()
        return None

def clear_game_theme_cache():
    """清除遊戲主題配置快取"""
    global _game_theme_cache
    _game_theme_cache = {}

# ========== new_test 題目管理 (pretest1 / posttest1) ==========

def load_new_test_questions() -> list:
    """
    載入 category/new_test.json 中的題目，供前測1 / 後測1使用。
    Load new_test.json questions for pretest1 / posttest1.
    回傳 Question 物件清單。
    """
    global _new_test_questions, _new_test_loaded
    if _new_test_loaded:
        return _new_test_questions

    try:
        with open('category/new_test.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        from utils.models import Question
        _new_test_questions = [
            Question(
                text=item.get('prompt', ''),
                assessment_standard=item.get('reference_answer'),
                image_url=item.get('image_url'),
            )
            for item in data
        ]
        _new_test_loaded = True
        print(f"new_test.json loaded: {len(_new_test_questions)} questions.")
    except Exception as e:
        print(f"[ERROR] load_new_test_questions: {e}")
        _new_test_questions = []
    return _new_test_questions


def get_new_test_question(idx: int):
    """取得 new_test 第 idx 道題目 (0-based)。
    Get the new_test question at the given index (0-based)."""
    questions = load_new_test_questions()
    if 0 <= idx < len(questions):
        return questions[idx]
    return None


def get_new_test_questions_count() -> int:
    """取得 new_test 題目總數。
    Get the total number of new_test questions."""
    return len(load_new_test_questions())


def get_new_test_questions_all() -> list:
    """取得全部 new_test 題目。
    Get all new_test questions."""
    return load_new_test_questions()


# ========== NPC 最後回覆快取 (Show Text / 顯示文字 功能) ==========

def set_last_npc_reply(user_id: str, npc_name: str, npc_reply: str, npc_image):
    """記錄使用者最近一次收到的 NPC 回覆，供「顯示文字」功能使用。
    Store the most recent NPC reply for the 'Show Text' quick reply feature.
    """
    _last_npc_replies[user_id] = {
        'npc_name': npc_name,
        'npc_reply': npc_reply,
        'npc_image': npc_image,
    }


def get_last_npc_reply(user_id: str) -> dict:
    """取得使用者最近一次收到的 NPC 回覆資訊。
    Get the most recent NPC reply info for the user.
    """
    return _last_npc_replies.get(user_id)

def get_game_info_config() -> dict:
    """取得遊戲大廳介紹所需的媒體設定
    Get game lobby intro media configuration."""
    return {
        'story_eng': config.get('game_story_eng', ''),
        'story_chi': config.get('game_story_chi', ''),
        'characters_video': config.get('game_characters_video', ''),
        'structure_image': config.get('game_structure_image', '')
    }

def get_theme_display_number(theme_id: str) -> str:
    """從主題 ID 取得顯示用的主題編號，例如 'theme1' -> '1'
    Get display number from theme ID, e.g. 'theme1' -> '1'."""
    if theme_id and theme_id.startswith('theme'):
        return theme_id.replace('theme', '')
    return theme_id if theme_id else '?'

def get_game_prologue(theme_id: str) -> str:
    """取得遊戲主題的前情提要"""
    theme_config = load_game_theme_config(theme_id)
    if theme_config:
        return theme_config.prologue
    return ""

def get_game_npcs(theme_id: str) -> List[dict]:
    """取得遊戲主題的NPC列表"""
    theme_config = load_game_theme_config(theme_id)
    if theme_config:
        return [{"id": npc.id, "name": npc.name} for npc in theme_config.npcs]
    return []

def get_game_level_info(theme_id: str, level_idx: int) -> Optional[dict]:
    """取得關卡資訊，包含影片和描述"""
    theme_config = load_game_theme_config(theme_id)
    if theme_config:
        level = theme_config.get_level(level_idx)
        if level:
            return {
                "id": level.id,
                "title": level.title,
                "description": level.description,
                "video_file": level.video_file,
                "questions": [
                    {
                        "text": q.text, 
                        "hint": q.hint,
                        "reference_answers": q.get_all_reference_answers(), # 支援多個參考答案
                        "tiered_reference_answers": q.get_tiered_reference_answers() # 十級評分參考答案 (若有)
                    } for q in level.questions
                ]
            }
    return None

def get_game_npc_info(theme_id: str, npc_idx: int) -> Optional[dict]:
    """取得NPC資訊供RAG使用 (修正 Bug #1 與 #5)"""
    theme_config = load_game_theme_config(theme_id)
    if theme_config:
        npc = theme_config.get_npc(npc_idx)
        if npc:
            return {
                "id": npc.id,
                "name": npc.name,
                "persona": npc.persona,
                "description": npc.description,  # 使用者可見的描述
                "file": npc.file,
                "image": npc.image,
                "background": npc.background,  # 新增 background 欄位支援
                "tts_voice": npc.tts_voice,          # TTS 語音名稱 (可為 None)
                "tts_instructions": npc.tts_instructions,  # TTS 風格指示 (可為 None)
            }
    return None

# ========== 遊戲計分功能 ==========

def update_game_score(user_id: str, theme_id: str, level_idx: int, question_idx: int, score: int) -> Tuple[bool, int]:
    """
    更新使用者的遊戲分數。回傳 (是否為新高分, 新的主題總分)。
    """
    user = user_data.get(user_id)
    if not user:
        return False, 0
    
    # 確保 game_scores 已初始化
    if not user.game_scores:
        user.game_scores = GameScores()

    is_new_high = user.game_scores.update_score(theme_id, level_idx, question_idx, score)
    theme_total = user.game_scores.get_theme_score(theme_id)
    return is_new_high, theme_total

def check_and_unlock_next_level(user_id: str, theme_id: str, level_idx: int) -> bool:
    """檢查並解鎖下一關"""
    user = user_data.get(user_id)
    if not user or not user.game_scores:
        return False
    
    questions_per_level = get_questions_per_level()
    min_score = get_min_score_to_pass()
    max_levels = get_levels_per_theme()
    
    return user.game_scores.check_and_unlock_level(
        theme_id, level_idx, questions_per_level, min_score, max_levels
    )

def get_user_unlocked_level(user_id: str, theme_id: str) -> int:
    """取得使用者在某主題已解鎖的最高關卡"""
    user = user_data.get(user_id)
    if not user or not user.game_scores:
        return 0
    return user.game_scores.get_unlocked_level(theme_id)

# Alias for backward compatibility
get_user_current_level = get_user_unlocked_level

def get_user_game_score(user_id: str, theme_id: str) -> int:
    """取得使用者在某主題的總分"""
    user = user_data.get(user_id)
    if not user or not user.game_scores:
        return 0
    return user.game_scores.get_theme_score(theme_id)

def get_user_level_score(user_id: str, theme_id: str, level_idx: int) -> int:
    """取得使用者在某關卡的總分"""
    user = user_data.get(user_id)
    if not user or not user.game_scores:
        return 0
    
    if theme_id in user.game_scores.themes:
        theme = user.game_scores.themes[theme_id]
        if level_idx in theme.levels:
            return theme.levels[level_idx].get_total_score()
    return 0

def get_user_question_score(user_id: str, theme_id: str, level_idx: int, question_idx: int) -> int:
    """取得使用者在某題目的最高分"""
    user = user_data.get(user_id)
    if not user or not user.game_scores:
        return 0
    
    if theme_id in user.game_scores.themes:
        theme = user.game_scores.themes[theme_id]
        if level_idx in theme.levels:
            level = theme.levels[level_idx]
            if question_idx in level.questions:
                return level.questions[question_idx].best_score
    return 0

def get_max_theme_score() -> int:
    """取得主題滿分"""
    levels = get_levels_per_theme()
    questions = get_questions_per_level()
    max_score = get_max_score_per_question()
    return levels * questions * max_score

def get_user_game_progress(user_id: str, theme_id: str) -> dict:
    """取得使用者在某主題的進度"""
    user = user_data.get(user_id)
    if not user or not user.game_scores:
        return {
            "total_score": 0, 
            "max_score": get_max_theme_score(), 
            "levels_completed": 0, 
            "questions_answered": 0,
            "current_level": 0
        }
    
    total_score = user.game_scores.get_theme_score(theme_id)
    max_score = get_max_theme_score()
    unlocked_level = user.game_scores.get_unlocked_level(theme_id)
    
    levels_completed = 0
    questions_answered = 0
    
    if theme_id in user.game_scores.themes:
        theme = user.game_scores.themes[theme_id]
        for level in theme.levels.values():
            questions_answered += len(level.questions)
            if level.completed:
                levels_completed += 1
    
    return {
        "total_score": total_score,
        "max_score": max_score,
        "levels_completed": levels_completed,
        "questions_answered": questions_answered,
        "current_level": unlocked_level
    }

def is_level_all_questions_passed(user_id: str, theme_id: str, level_idx: int) -> bool:
    """檢查使用者是否已通過該關卡的所有題目 (每題都達到及格分數)"""
    questions_per_level = get_questions_per_level()
    min_score = get_min_score_to_pass()
    
    user = user_data.get(user_id)
    if not user or not user.game_scores:
        return False
    
    if theme_id not in user.game_scores.themes:
        return False
    
    theme = user.game_scores.themes[theme_id]
    if level_idx not in theme.levels:
        return False
    
    level = theme.levels[level_idx]
    
    # 檢查是否所有題目都有回答且達到及格分數
    for q_idx in range(questions_per_level):
        if q_idx not in level.questions:
            return False
        if level.questions[q_idx].best_score < min_score:
            return False
    
    return True

def get_level_answered_questions(user_id: str, theme_id: str, level_idx: int) -> list:
    """取得使用者在該關卡已回答的題目索引列表"""
    user = user_data.get(user_id)
    if not user or not user.game_scores:
        return []
    
    if theme_id not in user.game_scores.themes:
        return []
    
    theme = user.game_scores.themes[theme_id]
    if level_idx not in theme.levels:
        return []
    
    return list(theme.levels[level_idx].questions.keys())

def get_next_unanswered_question(user_id: str, theme_id: str, level_idx: int) -> int:
    """取得下一個未回答的題目索引，若全部已回答則回傳 -1"""
    questions_per_level = get_questions_per_level()
    answered = get_level_answered_questions(user_id, theme_id, level_idx)
    
    for q_idx in range(questions_per_level):
        if q_idx not in answered:
            return q_idx
    
    return -1  # 全部已回答

def get_next_unpassed_question(user_id: str, theme_id: str, level_idx: int) -> int:
    """取得下一個未通過(分數低於及格)的題目索引，若全部已通過則回傳 -1"""
    questions_per_level = get_questions_per_level()
    min_score = get_min_score_to_pass()
    
    user = user_data.get(user_id)
    if not user or not user.game_scores:
        return 0  # 還沒回答任何題目，從第一題開始
    
    if theme_id not in user.game_scores.themes:
        return 0
    
    theme = user.game_scores.themes[theme_id]
    if level_idx not in theme.levels:
        return 0
    
    level = theme.levels[level_idx]
    
    for q_idx in range(questions_per_level):
        if q_idx not in level.questions:
            return q_idx  # 未回答的題目
        if level.questions[q_idx].best_score < min_score:
            return q_idx  # 未通過的題目
    
    return -1  # 全部已通過

# ========== 跨關卡題目進度追蹤功能 (新增) ==========

def get_next_unanswered_question_global(user_id: str, theme_id: str) -> tuple:
    """
    取得整個主題中下一個未回答或未通過的題目。
    回傳 (level_idx, question_idx)，若全部已通過則回傳 (-1, -1)。
    搜尋順序：按關卡順序、題目順序檢查。
    Get the next unanswered or unpassed question across all levels in a theme.
    Returns (level_idx, question_idx), or (-1, -1) if all completed.
    """
    theme_config = load_game_theme_config(theme_id)
    if not theme_config:
        return (-1, -1)
    
    levels_count = len(theme_config.levels)
    min_score = get_min_score_to_pass()
    
    user = user_data.get(user_id)
    
    # 遍歷所有關卡和題目
    for level_idx in range(levels_count):
        level_info = theme_config.get_level(level_idx)
        if not level_info:
            continue
        
        actual_questions = len(level_info.questions)
        
        for q_idx in range(actual_questions):
            # 檢查是否未回答或未通過
            if not user or not user.game_scores:
                return (level_idx, q_idx)
            
            if theme_id not in user.game_scores.themes:
                return (level_idx, q_idx)
            
            theme = user.game_scores.themes[theme_id]
            if level_idx not in theme.levels:
                return (level_idx, q_idx)
            
            level = theme.levels[level_idx]
            if q_idx not in level.questions:
                return (level_idx, q_idx)
            
            if level.questions[q_idx].best_score < min_score:
                return (level_idx, q_idx)
    
    # 全部已通過
    return (-1, -1)

def is_all_questions_completed(user_id: str, theme_id: str) -> bool:
    """
    檢查使用者是否已完成該主題的所有題目
    Check if user has completed all questions in a theme
    """
    level_idx, q_idx = get_next_unanswered_question_global(user_id, theme_id)
    return level_idx == -1 and q_idx == -1

# ========== 提示使用次數追蹤功能 (新增) ==========

def increment_hint_count(user_id: str, theme_id: str, level_idx: int, question_idx: int) -> int:
    """增加特定題目的提示使用次數，並回傳新的使用次數"""
    user = user_data.get(user_id)
    if not user:
        return 0
    
    # 確保 game_scores 已初始化
    if not user.game_scores:
        user.game_scores = GameScores()
    
    return user.game_scores.increment_hint_count(theme_id, level_idx, question_idx)

def get_hint_count(user_id: str, theme_id: str, level_idx: int, question_idx: int) -> int:
    """取得特定題目的提示使用次數"""
    user = user_data.get(user_id)
    if not user or not user.game_scores:
        return 0
    
    return user.game_scores.get_hint_count(theme_id, level_idx, question_idx)

# ========== NPC聊天和問題回答紀錄功能 (新增，解決 Bug #2) ==========

def save_npc_chat_record(user_id: str, theme_id: str, npc_idx: int, npc_name: str, 
                          user_text: str, npc_reply: str, relevance_score: int, 
                          language_score: int, feedback_chi: str, feedback_eng: str):
    """儲存NPC聊天紀錄"""
    user = user_data.get(user_id)
    if not user:
        return
    
    # 確保 npc_chat_history 已初始化
    if not hasattr(user, 'npc_chat_history') or user.npc_chat_history is None:
        user.npc_chat_history = {}

    key = f"{theme_id}-npc-{npc_idx}"
    if key not in user.npc_chat_history:
        user.npc_chat_history[key] = []
    
    record = {
        "timestamp": time.time(),
        "npc_name": npc_name,
        "user_text": user_text,
        "npc_reply": npc_reply,
        "relevance_score": relevance_score,
        "language_score": language_score,
        "total_score": (relevance_score + language_score) // 2,
        "feedback_chi": feedback_chi,
        "feedback_eng": feedback_eng
    }
    user.npc_chat_history[key].append(record)

def save_question_answer_record(user_id: str, theme_id: str, level_idx: int, 
                                  question_idx: int, question_text: str,
                                  user_answer: str, score: int, is_correct: bool,
                                  feedback_chi: str, feedback_eng: str, reference_comparison: str):
    """儲存問題回答紀錄"""
    user = user_data.get(user_id)
    if not user:
        return
    
    # 確保 question_history 已初始化
    if not hasattr(user, 'question_history') or user.question_history is None:
        user.question_history = {}

    key = f"{theme_id}-{level_idx}-{question_idx}"
    if key not in user.question_history:
        user.question_history[key] = []
    
    record = {
        "timestamp": time.time(),
        "question_text": question_text,
        "user_answer": user_answer,
        "score": score,
        "is_correct": is_correct,
        "feedback_chi": feedback_chi,
        "feedback_eng": feedback_eng,
        "reference_comparison": reference_comparison
    }
    user.question_history[key].append(record)

async def save_interaction_log(log: GameInteractionLog):
    """儲存互動紀錄到檔案"""
    log_file = get_interaction_log_file()
    
    # 確保目錄存在
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    try:
        # 讀取現有紀錄
        logs = []
        if os.path.exists(log_file):
            async with aiofiles.open(log_file, 'r', encoding='utf-8') as f:
                content = await f.read()
                if content:
                    try:
                        logs = json.loads(content)
                    except json.JSONDecodeError:
                        logs = [] # 檔案格式錯誤時重置
        
        # 加入新紀錄
        if hasattr(log, 'model_dump'):
            logs.append(log.model_dump())
        else:
            logs.append(log)
        
        # 寫入檔案
        async with aiofiles.open(log_file, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(logs, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"Error saving interaction log: {e}")

# ========== 遊戲進度查詢 (新增) ==========

def get_game_progress_detail(user_id: str, theme_id: str) -> dict:
    """
    取得使用者在某主題的詳細遊戲進度
    Get detailed game progress for a specific theme
    """
    theme_config = load_game_theme_config(theme_id)
    if not theme_config:
        return {"error": "Theme not found"}
    
    user = user_data.get(user_id)
    levels_detail = []
    
    for level in theme_config.levels:
        level_data = {
            "level_idx": level.id,
            "title": level.title,
            "questions": []
        }
        for q_idx, q in enumerate(level.questions):
            score = get_user_question_score(user_id, theme_id, level.id, q_idx)
            level_data["questions"].append({
                "q_idx": q_idx,
                "text": q.text[:50],
                "score": score,
                "passed": score >= get_min_score_to_pass()
            })
        levels_detail.append(level_data)
    
    return {
        "theme_id": theme_id,
        "theme_name": theme_config.name,
        "total_score": get_user_game_score(user_id, theme_id),
        "max_score": get_max_theme_score(),
        "unlocked_level": get_user_unlocked_level(user_id, theme_id),
        "levels": levels_detail
    }

# ========== RAG 功能 (保留 Embeddings 版本) ==========

class RagManager:
    @staticmethod
    def split_markdown_by_headers(text: str) -> List[RagChunk]:
        lines = text.split('\n')
        chunks = []
        current_chunk_lines = []
        current_headers = [] 
        
        for line in lines:
            header_match = re.match(r'^(#{1,3})\s+(.*)', line)
            
            if header_match:
                if current_chunk_lines:
                    content = "\n".join(current_chunk_lines).strip()
                    if content:
                        meta = {"headers": list(current_headers)}
                        chunks.append(RagChunk(content=content, metadata=meta))
                    current_chunk_lines = []
                
                level = len(header_match.group(1))
                title = header_match.group(2)
                
                while len(current_headers) >= level:
                    current_headers.pop()
                current_headers.append(title)
                
                current_chunk_lines.append(line)
            else:
                current_chunk_lines.append(line)
        
        if current_chunk_lines:
            content = "\n".join(current_chunk_lines).strip()
            if content:
                meta = {"headers": list(current_headers)}
                chunks.append(RagChunk(content=content, metadata=meta))
                
        return chunks

    @staticmethod
    async def get_embeddings(texts: List[str]) -> List[List[float]]:
        try:
            response = await client.embeddings.create(
                input=texts,
                model="text-embedding-3-small"
            )
            return [data.embedding for data in response.data]
        except Exception as e:
            print(f"Embedding Error: {e}")
            return []

    @staticmethod
    def cosine_similarity(v1: List[float], v2: List[float]) -> float:
        vec1 = np.array(v1)
        vec2 = np.array(v2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return np.dot(vec1, vec2) / (norm1 * norm2)

    @staticmethod
    async def get_relevant_context(rag_path: str, query: str, top_k: int = 3) -> str:
        global _rag_cache
        
        async with _rag_lock:
            if rag_path not in _rag_cache:
                path = Path(rag_path)
                full_text = ""
                
                if path.is_file():
                    async with aiofiles.open(path, 'r', encoding='utf-8') as f:
                        full_text = await f.read()
                elif path.is_dir():
                    texts = []
                    for file in path.glob('*.md'):
                        async with aiofiles.open(file, 'r', encoding='utf-8') as f:
                            texts.append(await f.read())
                    full_text = "\n\n".join(texts)
                else:
                    return "No RAG document found."

                chunks = RagManager.split_markdown_by_headers(full_text)
                if not chunks:
                    return full_text 

                chunk_texts = [c.content for c in chunks]
                vectors = await RagManager.get_embeddings(chunk_texts)
                
                if len(vectors) != len(chunks):
                    print("Embedding count mismatch, fallback to full text")
                    return full_text

                for i, chunk in enumerate(chunks):
                    chunk.embedding = vectors[i]
                
                _rag_cache[rag_path] = chunks
                print(f"RAG Index built for {rag_path}: {len(chunks)} chunks.")

        chunks = _rag_cache[rag_path]
        query_vecs = await RagManager.get_embeddings([query])
        if not query_vecs:
            return ""
        query_vec = query_vecs[0]

        scored_chunks = []
        for chunk in chunks:
            if chunk.embedding:
                score = RagManager.cosine_similarity(query_vec, chunk.embedding)
                scored_chunks.append((score, chunk))
        
        scored_chunks.sort(key=lambda x: x[0], reverse=True)
        top_results = scored_chunks[:top_k]
        
        context_str = ""
        for score, chunk in top_results:
            context_str += f"---\n[Similarity: {score:.2f}]\n{chunk.content}\n"
            
        return context_str

async def get_rag_context_v2(file_path_or_dir: str, query: str) -> str:
    return await RagManager.get_relevant_context(file_path_or_dir, query)

def load_rag_config(category: str) -> dict:
    config_path = Path(f'category/rag_docs/{category}/config.json')
    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading rag config for {category}: {e}")
            return {}
    return {}

# ========== 配置載入與儲存 ==========

async def load_config():
    global config
    try:
        async with _lock:
            async with aiofiles.open(CONFIG_FILE, 'r', encoding='utf-8') as file:
                content = await file.read()
        loaded_config = json.loads(content)
        # 與預設值合併以確保新欄位存在
        merged_config = DEFAULT_CONFIG.copy()
        merged_config.update(loaded_config)
        config.update(merged_config)
        print("Config loaded successfully.")
    except FileNotFoundError:
        async with _lock:
            async with aiofiles.open(CONFIG_FILE, 'w', encoding='utf-8') as file:
                await file.write(json.dumps(config, indent=4))
        print("Config created successfully.")

async def save_config():
    global config
    async with _lock:
        async with aiofiles.open(CONFIG_FILE, 'w', encoding='utf-8') as file:
            await file.write(json.dumps(config, indent=4))
    print("Config saved successfully.")

async def save_all():
    await save_config()
    await save_user_data()
    return 'All data saved.'

# ========== User Data 載入與儲存 (核心修復：統一寫入 Docker 掛載點) ==========

async def load_user_data():
    """載入使用者資料 (修復：直接讀取 USER_DATA_FILE)"""
    global user_data
    user_data_file = get_user_data_file()
    
    # 確保目錄存在
    if os.path.dirname(user_data_file):
        os.makedirs(os.path.dirname(user_data_file), exist_ok=True)
    
    try:
        async with _lock:
            async with aiofiles.open(user_data_file, 'r', encoding='utf-8') as file:
                content = await file.read()
        raw_data = json.loads(content)
        
        # 將舊格式資料轉換為新格式，並建立 User 物件
        for key, value in raw_data.items():
            # 確保新欄位存在
            if 'npc_chat_history' not in value:
                value['npc_chat_history'] = {}
            if 'question_history' not in value:
                value['question_history'] = {}
            if 'game_scores' not in value:
                value['game_scores'] = {'themes': {}}
            # 確保 hint_count 欄位存在於舊資料中
            if 'themes' in value.get('game_scores', {}):
                for theme_key, theme_data in value['game_scores']['themes'].items():
                    if 'levels' in theme_data:
                        for level_key, level_data in theme_data['levels'].items():
                            if 'questions' in level_data:
                                for q_key, q_data in level_data['questions'].items():
                                    if 'hint_count' not in q_data:
                                        q_data['hint_count'] = 0
        
        user_data = {key: User(**value) for key, value in raw_data.items()}
        print(f"User data loaded successfully from {user_data_file}.")
    except FileNotFoundError:
        print(f"No previous data file found at {user_data_file}, starting fresh.")
        user_data = {}
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from {user_data_file}, starting fresh.", e)
        user_data = {}

async def save_user_data():
    """儲存使用者資料 (修復：直接寫入 USER_DATA_FILE)"""
    global user_data
    user_data_file = get_user_data_file()
    
    # 確保目錄存在
    if os.path.dirname(user_data_file):
        os.makedirs(os.path.dirname(user_data_file), exist_ok=True)
    
    async with _lock:
        async with aiofiles.open(user_data_file, 'w', encoding='utf-8') as file:
            serializable_data = {key: user.to_dict() for key, user in user_data.items()}
            json_data = json.dumps(serializable_data, indent=4, ensure_ascii=False)
            await file.write(json_data)
    print(f"User data saved to {user_data_file}.")
        
async def user_data_task():
    while True:
        await save_user_data()
        await asyncio.sleep(60 * 60)