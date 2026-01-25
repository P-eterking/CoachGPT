"""
file_utils.py - 檔案工具模組
File Utilities Module

處理使用者資料、配置、遊戲狀態等的讀寫操作。
Handles reading and writing of user data, configuration, game state, etc.

[重要修復 IMPORTANT FIX]:
Docker 掛載 ./data/user_data{N}.json 到容器內的 /app/user_data.json
因此程式碼必須直接寫入 /app/user_data.json (USER_DATA_FILE)
而不是 data/user_data{N}.json

Docker mounts ./data/user_data{N}.json to /app/user_data.json inside container
So code must write directly to /app/user_data.json (USER_DATA_FILE)
Not to data/user_data{N}.json
"""

import json
import os
import time
import traceback
from typing import Dict, Optional, List, Any
from config import USER_DATA_FILE, CONFIG_FILE

# ========== 全域變數 Global Variables ==========

# 使用者資料 (從 JSON 載入)
user_data: Dict[str, dict] = {}

# 使用者狀態 (記憶體中，不持久化)
user_state: Dict[str, Any] = {}

# 配置資料
config: Dict[str, Any] = {}

# 遊戲主題配置快取
_game_theme_cache: Dict[str, Any] = {}

# ========== 基礎資料操作 Basic Data Operations ==========

def load_user_data():
    """載入使用者資料 Load user data"""
    global user_data
    try:
        # [FIX] 直接使用 USER_DATA_FILE，這是 Docker 掛載的路徑
        if os.path.exists(USER_DATA_FILE):
            with open(USER_DATA_FILE, 'r', encoding='utf-8') as f:
                user_data = json.load(f)
            print(f"User data loaded from {USER_DATA_FILE}: {len(user_data)} users")
        else:
            user_data = {}
            print(f"User data file not found at {USER_DATA_FILE}, starting fresh")
    except json.JSONDecodeError as e:
        print(f"Error decoding user data JSON: {e}")
        user_data = {}
    except Exception as e:
        print(f"Error loading user data: {e}")
        traceback.print_exc()
        user_data = {}

async def save_user_data():
    """儲存使用者資料 Save user data"""
    global user_data
    try:
        # [FIX] 直接寫入 USER_DATA_FILE，這是 Docker 掛載的路徑
        # 確保目錄存在
        dir_path = os.path.dirname(USER_DATA_FILE)
        if dir_path and not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)
        
        with open(USER_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(user_data, f, ensure_ascii=False, indent=2)
        print(f"User data saved to {USER_DATA_FILE}: {len(user_data)} users")
    except Exception as e:
        print(f"Error saving user data: {e}")
        traceback.print_exc()

def load_config():
    """載入配置 Load configuration"""
    global config
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
            print(f"Config loaded from {CONFIG_FILE}")
        else:
            config = {}
            print(f"Config file not found at {CONFIG_FILE}")
    except Exception as e:
        print(f"Error loading config: {e}")
        traceback.print_exc()
        config = {}

async def save_config():
    """儲存配置 Save configuration"""
    global config
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        print(f"Config saved to {CONFIG_FILE}")
    except Exception as e:
        print(f"Error saving config: {e}")
        traceback.print_exc()

async def save_all():
    """儲存所有資料 Save all data"""
    await save_user_data()
    await save_config()

# ========== 使用者資料操作 User Data Operations ==========

def hasData(user_id: str) -> bool:
    """檢查使用者是否已註冊 Check if user is registered"""
    return user_id in user_data

def getData(user_id: str) -> Optional[dict]:
    """取得使用者資料 Get user data"""
    return user_data.get(user_id)

def setData(user_id: str, data: dict):
    """設定使用者資料 Set user data"""
    user_data[user_id] = data

def delData(user_id: str):
    """刪除使用者資料 Delete user data"""
    if user_id in user_data:
        del user_data[user_id]

def addUser(user_id: str, class_time: int, dep: str, student_id: str, name: str):
    """新增使用者 Add new user"""
    from utils.models import User, ChatHistory, GameScores
    new_user = User(
        id=student_id,
        dep=dep,
        name=name,
        class_time=class_time,
        history={},
        chat=ChatHistory(),
        game_scores=GameScores(),
        npc_chat_history={},
        question_history={}
    )
    user_data[user_id] = new_user.to_dict()
    return new_user

# ========== 使用者狀態操作 User State Operations ==========

def get_user_state(user_id: str):
    """取得使用者狀態 (記憶體中) Get user state (in memory)"""
    from utils.models import UserState
    if user_id not in user_state:
        user_state[user_id] = UserState()
    elif not isinstance(user_state[user_id], UserState):
        user_state[user_id] = UserState(**user_state[user_id]) if isinstance(user_state[user_id], dict) else UserState()
    return user_state[user_id]

def set_user_state(user_id: str, state):
    """設定使用者狀態 Set user state"""
    user_state[user_id] = state

# ========== 歷史紀錄操作 History Operations ==========

def getHistory(user_id: str, key: str) -> Optional[list]:
    """取得歷史紀錄 Get history"""
    if user_id not in user_data:
        return None
    user = user_data[user_id]
    if 'history' not in user:
        return None
    history = user.get('history', {})
    if key not in history:
        return None
    
    from utils.models import SpeechAssessment
    result = []
    for item in history[key]:
        if isinstance(item, dict):
            result.append(SpeechAssessment(**item))
        else:
            result.append(item)
    return result

def updateHistory(user_id: str, key: str, assessment):
    """更新歷史紀錄 Update history"""
    if user_id not in user_data:
        return
    
    if 'history' not in user_data[user_id]:
        user_data[user_id]['history'] = {}
    
    if key not in user_data[user_id]['history']:
        user_data[user_id]['history'][key] = []
    
    if hasattr(assessment, 'to_dict'):
        user_data[user_id]['history'][key].append(assessment.to_dict())
    elif isinstance(assessment, dict):
        user_data[user_id]['history'][key].append(assessment)
    else:
        user_data[user_id]['history'][key].append(assessment)

# ========== 聊天紀錄操作 Chat History Operations ==========

def getChatHistory(user_id: str):
    """取得聊天紀錄 Get chat history"""
    if user_id not in user_data:
        return None
    user = user_data[user_id]
    if 'chat' not in user:
        return None
    
    from utils.models import ChatHistory
    chat_data = user.get('chat', {})
    if isinstance(chat_data, dict):
        return ChatHistory(**chat_data)
    return chat_data

def updateChatHistory(user_id: str, question_or_history, answer: str = None):
    """
    更新聊天紀錄 Update chat history
    
    可接受兩種呼叫方式:
    1. updateChatHistory(user_id, question, answer) - 新增單一問答
    2. updateChatHistory(user_id, history) - 直接設定整個 ChatHistory 物件
    """
    if user_id not in user_data:
        return
    
    # 檢查是否為 ChatHistory 物件或字典
    if answer is None:
        # 傳入的是整個 ChatHistory 物件
        if hasattr(question_or_history, 'model_dump'):
            user_data[user_id]['chat'] = question_or_history.model_dump()
        elif hasattr(question_or_history, 'to_dict'):
            user_data[user_id]['chat'] = question_or_history.to_dict()
        elif isinstance(question_or_history, dict):
            user_data[user_id]['chat'] = question_or_history
        else:
            # 嘗試轉換
            user_data[user_id]['chat'] = {
                'questions': getattr(question_or_history, 'questions', []),
                'answers': getattr(question_or_history, 'answers', [])
            }
    else:
        # 傳入的是單一問答
        question = question_or_history
        if 'chat' not in user_data[user_id]:
            user_data[user_id]['chat'] = {'questions': [], 'answers': []}
        
        chat = user_data[user_id]['chat']
        if 'questions' not in chat:
            chat['questions'] = []
        if 'answers' not in chat:
            chat['answers'] = []
        
        chat['questions'].append(question)
        chat['answers'].append(answer)

# ========== 管理員操作 Admin Operations ==========

def isAdmin(user_id: str) -> bool:
    """檢查是否為管理員 Check if user is admin"""
    return user_id in config.get('admin', [])

async def addAdmin(user_id: str):
    """新增管理員 Add admin"""
    if 'admin' not in config:
        config['admin'] = []
    if user_id not in config['admin']:
        config['admin'].append(user_id)

def removeAdmin(user_id: str):
    """移除管理員 Remove admin"""
    if 'admin' in config and user_id in config['admin']:
        config['admin'].remove(user_id)

# ========== 功能開關操作 Feature Toggle Operations ==========

def isEnabled(alias: str) -> bool:
    """檢查功能是否啟用 Check if feature is enabled"""
    return alias in config.get('enabled', [])

def addEnabled(alias: str):
    """啟用功能 Enable feature"""
    if 'enabled' not in config:
        config['enabled'] = []
    if alias not in config['enabled']:
        config['enabled'].append(alias)

def removeEnabled(alias: str):
    """停用功能 Disable feature"""
    if 'enabled' in config and alias in config['enabled']:
        config['enabled'].remove(alias)

def isResponse(alias: str) -> bool:
    """檢查功能是否提供回饋 Check if feature provides response"""
    return alias in config.get('response', [])

def addResponse(alias: str):
    """啟用回饋 Enable response"""
    if 'response' not in config:
        config['response'] = []
    if alias not in config['response']:
        config['response'].append(alias)

def removeResponse(alias: str):
    """停用回饋 Disable response"""
    if 'response' in config and alias in config['response']:
        config['response'].remove(alias)

def get_display_feedback() -> bool:
    """取得是否顯示回饋 Get display feedback setting"""
    return config.get('display_feedback', True)

# ========== Rich Menu 操作 Rich Menu Operations ==========

def get_rich_menu_id(alias: str) -> Optional[str]:
    """取得 Rich Menu ID Get Rich Menu ID"""
    return config.get('rich_menu_ids', {}).get(alias)

def set_rich_menu_id(rich_menu_id: str, alias: str):
    """設定 Rich Menu ID Set Rich Menu ID"""
    if 'rich_menu_ids' not in config:
        config['rich_menu_ids'] = {}
    config['rich_menu_ids'][alias] = rich_menu_id

def clear_rich_menu_id():
    """清除所有 Rich Menu ID Clear all Rich Menu IDs"""
    config['rich_menu_ids'] = {}

def get_rich_menu_category_from_id(rich_menu_id: str) -> Optional[str]:
    """從 Rich Menu ID 取得類別 Get category from Rich Menu ID"""
    for alias, rid in config.get('rich_menu_ids', {}).items():
        if rid == rich_menu_id:
            return alias
    return None

# ========== 遊戲主題配置 Game Theme Configuration ==========

def load_game_theme_config(theme_id: str):
    """載入遊戲主題配置 Load game theme configuration"""
    global _game_theme_cache
    
    # 檢查快取
    if theme_id in _game_theme_cache:
        return _game_theme_cache[theme_id]
    
    try:
        # 嘗試從 category/rag_docs/{theme_id}/theme_config.json 載入
        config_path = os.path.join("category", "rag_docs", theme_id, "theme_config.json")
        
        if not os.path.exists(config_path):
            print(f"Theme config not found at {config_path}")
            return None
        
        with open(config_path, 'r', encoding='utf-8') as f:
            theme_data = json.load(f)
        
        from utils.models import GameThemeConfig
        theme_config = GameThemeConfig(**theme_data)
        
        # 存入快取
        _game_theme_cache[theme_id] = theme_config
        print(f"Theme config loaded for {theme_id}")
        return theme_config
    
    except Exception as e:
        print(f"Error loading theme config for {theme_id}: {e}")
        traceback.print_exc()
        return None

def clear_game_theme_cache():
    """清除遊戲主題快取 Clear game theme cache"""
    global _game_theme_cache
    _game_theme_cache = {}
    print("Game theme cache cleared")

def get_game_themes() -> List[str]:
    """取得所有遊戲主題 ID Get all game theme IDs"""
    return config.get('game_themes', ['theme1', 'theme2', 'theme3'])

def get_levels_per_theme() -> int:
    """取得每個主題的關卡數 Get levels per theme"""
    return config.get('levels_per_theme', 5)

def get_questions_per_level() -> int:
    """取得每關的題目數 Get questions per level"""
    return config.get('questions_per_level', 3)

def get_max_score_per_question() -> int:
    """取得每題最高分 Get max score per question"""
    return config.get('max_score_per_question', 10)

def get_min_score_to_pass() -> int:
    """取得及格分數 Get minimum score to pass"""
    return config.get('min_score_to_pass', 6)

# ========== 遊戲資訊取得 Game Info Retrieval ==========

def get_game_level_info(theme_id: str, level_idx: int) -> Optional[dict]:
    """取得關卡資訊 Get level info"""
    theme_config = load_game_theme_config(theme_id)
    if not theme_config:
        return None
    
    level = theme_config.get_level(level_idx)
    if not level:
        return None
    
    # 轉換為字典格式，並處理 reference_answers
    questions = []
    for q in level.questions:
        q_dict = {
            'text': q.text,
            'hint': q.hint,
            'reference_answers': q.get_all_reference_answers()  # [FIX] 使用新方法取得所有參考答案
        }
        questions.append(q_dict)
    
    return {
        'id': level.id,
        'title': level.title,
        'description': level.description,
        'video_file': level.video_file,
        'questions': questions
    }

def get_game_npc_info(theme_id: str, npc_idx: int) -> Optional[dict]:
    """取得 NPC 資訊 Get NPC info"""
    theme_config = load_game_theme_config(theme_id)
    if not theme_config:
        return None
    
    npc = theme_config.get_npc(npc_idx)
    if not npc:
        return None
    
    return {
        'id': npc.id,
        'name': npc.name,
        'persona': npc.persona,
        'description': npc.description,  # [FIX] 現在會正確讀取 display_description
        'file': npc.file,
        'image': npc.image,
        'background': npc.background  # [FIX] 新增 background 欄位
    }

# ========== 使用者遊戲進度 User Game Progress ==========

def get_user_game_score(user_id: str, theme_id: str) -> int:
    """取得使用者在特定主題的總分 Get user's total score in a theme"""
    if user_id not in user_data:
        return 0
    
    user = user_data[user_id]
    game_scores = user.get('game_scores', {})
    themes = game_scores.get('themes', {})
    theme = themes.get(theme_id, {})
    
    total = 0
    for level in theme.get('levels', {}).values():
        for q in level.get('questions', {}).values():
            total += q.get('best_score', 0)
    
    return total

def get_max_theme_score(theme_id: str) -> int:
    """取得主題滿分 Get max theme score"""
    levels = get_levels_per_theme()
    questions = get_questions_per_level()
    max_score = get_max_score_per_question()
    return levels * questions * max_score

def get_user_unlocked_level(user_id: str, theme_id: str) -> int:
    """取得使用者解鎖的最高關卡 Get user's highest unlocked level"""
    if user_id not in user_data:
        return 0
    
    user = user_data[user_id]
    game_scores = user.get('game_scores', {})
    themes = game_scores.get('themes', {})
    theme = themes.get(theme_id, {})
    
    return theme.get('current_level', 0)

def get_user_level_score(user_id: str, theme_id: str, level_idx: int) -> int:
    """取得使用者在特定關卡的總分 Get user's total score in a level"""
    if user_id not in user_data:
        return 0
    
    user = user_data[user_id]
    game_scores = user.get('game_scores', {})
    themes = game_scores.get('themes', {})
    theme = themes.get(theme_id, {})
    levels = theme.get('levels', {})
    level = levels.get(str(level_idx), {})
    
    total = 0
    for q in level.get('questions', {}).values():
        total += q.get('best_score', 0)
    
    return total

def get_user_question_score(user_id: str, theme_id: str, level_idx: int, question_idx: int) -> int:
    """取得使用者在特定題目的最高分 Get user's best score for a question"""
    if user_id not in user_data:
        return 0
    
    user = user_data[user_id]
    game_scores = user.get('game_scores', {})
    themes = game_scores.get('themes', {})
    theme = themes.get(theme_id, {})
    levels = theme.get('levels', {})
    level = levels.get(str(level_idx), {})
    questions = level.get('questions', {})
    question = questions.get(str(question_idx), {})
    
    return question.get('best_score', 0)

def get_user_game_progress(user_id: str, theme_id: str) -> dict:
    """取得使用者遊戲進度摘要 Get user's game progress summary"""
    total_score = get_user_game_score(user_id, theme_id)
    max_score = get_max_theme_score(theme_id)
    unlocked_level = get_user_unlocked_level(user_id, theme_id)
    
    # 計算已回答題數和已完成關卡數
    questions_answered = 0
    levels_completed = 0
    
    if user_id in user_data:
        user = user_data[user_id]
        game_scores = user.get('game_scores', {})
        themes = game_scores.get('themes', {})
        theme = themes.get(theme_id, {})
        
        for level in theme.get('levels', {}).values():
            if level.get('completed', False):
                levels_completed += 1
            for q in level.get('questions', {}).values():
                if q.get('best_score', 0) > 0:
                    questions_answered += 1
    
    return {
        'total_score': total_score,
        'max_score': max_score,
        'unlocked_level': unlocked_level,
        'questions_answered': questions_answered,
        'levels_completed': levels_completed
    }

def update_user_game_score(user_id: str, theme_id: str, level_idx: int, question_idx: int, score: int) -> bool:
    """更新使用者遊戲分數 Update user's game score"""
    if user_id not in user_data:
        return False
    
    user = user_data[user_id]
    
    # 確保結構存在
    if 'game_scores' not in user:
        user['game_scores'] = {'themes': {}}
    if 'themes' not in user['game_scores']:
        user['game_scores']['themes'] = {}
    if theme_id not in user['game_scores']['themes']:
        user['game_scores']['themes'][theme_id] = {
            'theme_id': theme_id,
            'levels': {},
            'current_level': 0
        }
    
    theme = user['game_scores']['themes'][theme_id]
    level_key = str(level_idx)
    
    if level_key not in theme['levels']:
        theme['levels'][level_key] = {
            'level_idx': level_idx,
            'questions': {},
            'completed': False
        }
    
    level = theme['levels'][level_key]
    question_key = str(question_idx)
    
    is_new_high = False
    if question_key not in level['questions']:
        level['questions'][question_key] = {
            'question_idx': question_idx,
            'best_score': score,
            'attempts': 1
        }
        is_new_high = True
    else:
        question = level['questions'][question_key]
        question['attempts'] = question.get('attempts', 0) + 1
        if score > question.get('best_score', 0):
            question['best_score'] = score
            is_new_high = True
    
    # 檢查是否完成關卡
    check_and_unlock_next_level(user_id, theme_id, level_idx)
    
    return is_new_high

def check_and_unlock_next_level(user_id: str, theme_id: str, level_idx: int) -> bool:
    """檢查並解鎖下一關 Check and unlock next level"""
    if user_id not in user_data:
        return False
    
    user = user_data[user_id]
    game_scores = user.get('game_scores', {})
    themes = game_scores.get('themes', {})
    theme = themes.get(theme_id, {})
    levels = theme.get('levels', {})
    level = levels.get(str(level_idx), {})
    
    questions_per_level = get_questions_per_level()
    min_score = get_min_score_to_pass()
    max_levels = get_levels_per_theme()
    
    # 檢查所有題目是否都達到及格分數
    questions = level.get('questions', {})
    if len(questions) < questions_per_level:
        return False
    
    for q in questions.values():
        if q.get('best_score', 0) < min_score:
            return False
    
    # 標記關卡完成
    level['completed'] = True
    
    # 解鎖下一關
    current_level = theme.get('current_level', 0)
    if level_idx == current_level and current_level < max_levels - 1:
        theme['current_level'] = current_level + 1
        return True
    
    return False

def update_game_score(user_id: str, theme_id: str, level_idx: int, question_idx: int, score: int) -> tuple:
    """
    更新遊戲分數並回傳 (is_new_high, theme_total)
    Update game score and return (is_new_high, theme_total)
    
    用於 handlers.py 中的 handle_game_answer
    Used by handle_game_answer in handlers.py
    """
    is_new_high = update_user_game_score(user_id, theme_id, level_idx, question_idx, score)
    theme_total = get_user_game_score(user_id, theme_id)
    return (is_new_high, theme_total)

# ========== NPC 聊天紀錄 NPC Chat History ==========

def save_npc_chat_record(user_id: str, theme_id: str, npc_idx: int, npc_name: str,
                         user_text: str, npc_reply: str, 
                         relevance_score: int, language_score: int,
                         feedback_chi: str, feedback_eng: str):
    """儲存 NPC 聊天紀錄 Save NPC chat record"""
    if user_id not in user_data:
        return
    
    user = user_data[user_id]
    if 'npc_chat_history' not in user:
        user['npc_chat_history'] = {}
    
    history_key = f"{theme_id}-npc-{npc_idx}"
    if history_key not in user['npc_chat_history']:
        user['npc_chat_history'][history_key] = []
    
    record = {
        'timestamp': time.time(),
        'theme_id': theme_id,
        'npc_idx': npc_idx,
        'npc_name': npc_name,
        'user_text': user_text,
        'npc_reply': npc_reply,
        'relevance_score': relevance_score,
        'language_score': language_score,
        'feedback_chi': feedback_chi,
        'feedback_eng': feedback_eng
    }
    
    user['npc_chat_history'][history_key].append(record)

def get_npc_chat_history(user_id: str, theme_id: str, npc_idx: int) -> List[dict]:
    """取得 NPC 聊天紀錄 Get NPC chat history"""
    if user_id not in user_data:
        return []
    
    user = user_data[user_id]
    history_key = f"{theme_id}-npc-{npc_idx}"
    return user.get('npc_chat_history', {}).get(history_key, [])

# ========== 問題回答紀錄 Question Answer History ==========

def save_question_answer_record(user_id: str, theme_id: str, level_idx: int, question_idx: int,
                                 question_text: str, user_text: str, score: int, is_correct: bool,
                                 feedback_chi: str, feedback_eng: str, reference_comparison: str):
    """儲存問題回答紀錄 Save question answer record"""
    if user_id not in user_data:
        return
    
    user = user_data[user_id]
    if 'question_history' not in user:
        user['question_history'] = {}
    
    history_key = f"{theme_id}-level-{level_idx}-q-{question_idx}"
    if history_key not in user['question_history']:
        user['question_history'][history_key] = []
    
    record = {
        'timestamp': time.time(),
        'theme_id': theme_id,
        'level_idx': level_idx,
        'question_idx': question_idx,
        'question_text': question_text,
        'user_text': user_text,
        'score': score,
        'is_correct': is_correct,
        'feedback_chi': feedback_chi,
        'feedback_eng': feedback_eng,
        'reference_comparison': reference_comparison
    }
    
    user['question_history'][history_key].append(record)

def get_question_answer_history(user_id: str, theme_id: str, level_idx: int, question_idx: int) -> List[dict]:
    """取得問題回答紀錄 Get question answer history"""
    if user_id not in user_data:
        return []
    
    user = user_data[user_id]
    history_key = f"{theme_id}-level-{level_idx}-q-{question_idx}"
    return user.get('question_history', {}).get(history_key, [])

# ========== 互動紀錄檔案 Interaction Log File ==========

def get_interaction_log_file() -> str:
    """取得互動紀錄檔案路徑 Get interaction log file path"""
    # 確保 data 目錄存在
    log_dir = "data"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    return os.path.join(log_dir, "interaction_logs.jsonl")

async def save_interaction_log(log):
    """儲存互動紀錄 Save interaction log"""
    try:
        log_file = get_interaction_log_file()
        with open(log_file, 'a', encoding='utf-8') as f:
            if hasattr(log, 'model_dump'):
                log_data = log.model_dump()
            elif hasattr(log, 'to_dict'):
                log_data = log.to_dict()
            else:
                log_data = log
            f.write(json.dumps(log_data, ensure_ascii=False) + '\n')
    except Exception as e:
        print(f"Error saving interaction log: {e}")
        traceback.print_exc()

# ========== RAG 相關 RAG Related ==========

async def get_rag_context_v2(rag_path: str, query: str = "", max_chunks: int = 5) -> str:
    """取得 RAG 上下文 (簡化版) Get RAG context (simplified)"""
    try:
        if os.path.isfile(rag_path):
            # 直接讀取檔案
            with open(rag_path, 'r', encoding='utf-8') as f:
                content = f.read()
            # 限制長度
            if len(content) > 4000:
                content = content[:4000] + "..."
            return content
        elif os.path.isdir(rag_path):
            # 讀取目錄中的所有 .md 和 .txt 檔案
            contents = []
            for filename in os.listdir(rag_path):
                if filename.endswith(('.md', '.txt')):
                    filepath = os.path.join(rag_path, filename)
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    contents.append(f"=== {filename} ===\n{content}")
            
            combined = "\n\n".join(contents)
            if len(combined) > 8000:
                combined = combined[:8000] + "..."
            return combined
        else:
            return "No context available."
    except Exception as e:
        print(f"Error loading RAG context from {rag_path}: {e}")
        return "Error loading context."

# ========== 初始化 Initialization ==========

def initialize():
    """初始化模組 Initialize module"""
    load_config()
    load_user_data()
    print("File utils initialized")

# 模組載入時自動初始化
initialize()