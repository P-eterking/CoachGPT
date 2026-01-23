import json
import aiofiles  # 非同步檔案處理庫，用於讀取與寫入資料
import asyncio
import os
import re
import numpy as np
import time
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from config import USER_DATA_FILE, CONFIG_FILE, client
from utils.models import (
    ChatHistory, User, SpeechAssessment, UserState, RagChunk,
    GameThemeConfig, GameScores, GameThemeScore, GameLevelScore, GameQuestionScore,
    GameInteractionLog  # 修改7: 新增
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
    # 新增: 遊戲設定
    'game_themes': ['theme1', 'theme2', 'theme3'],  # 遊戲主題列表
    'levels_per_theme': 5,  # 每個主題的關卡數
    'questions_per_level': 3,  # 每個關卡的題目數
    'max_score_per_question': 10,  # 每題滿分
    # 修改7: 新增 service_number
    'service_number': 4  # 服務編號，用於區分資料檔案
}

# 設定檔案
config = DEFAULT_CONFIG.copy()

_rag_cache: Dict[str, List[RagChunk]] = {}
_rag_lock = asyncio.Lock()

# 新增: 遊戲主題配置快取
_game_theme_cache: Dict[str, GameThemeConfig] = {}

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

# 初始化使用者資料
def initData(user_id, classTime, dep, id, name):
    user_data[user_id] = User(
        dep=dep, id=id, name=name, class_time=classTime, 
        history={}, chat={}, game_scores=GameScores()
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

# ========== 修改7: 服務特定資料檔案功能 ==========

def get_service_number() -> int:
    """取得服務編號"""
    return config.get('service_number', 4)

def get_user_data_file() -> str:
    """取得服務特定的使用者資料檔案路徑"""
    service_num = get_service_number()
    return f'data/user_data{service_num}.json'

def get_interaction_log_file() -> str:
    """取得服務特定的互動紀錄檔案路徑"""
    service_num = get_service_number()
    return f'data/interaction_log{service_num}.json'

def get_display_feedback() -> bool:
    """取得是否顯示回饋的設定"""
    return config.get('display_feedback', True)

async def save_interaction_log(log: GameInteractionLog):
    """儲存遊戲互動紀錄"""
    log_file = get_interaction_log_file()
    
    # 確保目錄存在
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    try:
        # 讀取現有紀錄
        existing_logs = []
        if os.path.exists(log_file):
            async with aiofiles.open(log_file, 'r', encoding='utf-8') as f:
                content = await f.read()
                if content:
                    existing_logs = json.loads(content)
        
        # 新增紀錄
        existing_logs.append(log.to_dict())
        
        # 寫入檔案
        async with aiofiles.open(log_file, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(existing_logs, indent=2, ensure_ascii=False))
            
    except Exception as e:
        print(f"Error saving interaction log: {e}")

# ========== 結束修改7 ==========

# ========== 新增: 遊戲主題功能 ==========

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

def load_game_theme_config(theme_id: str) -> Optional[GameThemeConfig]:
    """從JSON檔案載入遊戲主題配置"""
    global _game_theme_cache
    
    if theme_id in _game_theme_cache:
        return _game_theme_cache[theme_id]
    
    config_path = Path(f'category/rag_docs/{theme_id}/theme_config.json')
    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                theme_config = GameThemeConfig(**data)
                _game_theme_cache[theme_id] = theme_config
                return theme_config
        except Exception as e:
            print(f"Error loading game theme config for {theme_id}: {e}")
            return None
    return None

def clear_game_theme_cache():
    """清除遊戲主題配置快取"""
    global _game_theme_cache
    _game_theme_cache = {}

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
                        "reference_answer": q.reference_answer  # 新增: 參考答案
                    } 
                    for q in level.questions
                ]
            }
    return None

def get_game_npc_info(theme_id: str, npc_idx: int) -> Optional[dict]:
    """取得NPC資訊供RAG使用"""
    theme_config = load_game_theme_config(theme_id)
    if theme_config:
        npc = theme_config.get_npc(npc_idx)
        if npc:
            return {
                "id": npc.id,
                "name": npc.name,
                "persona": npc.persona,
                "file": npc.file,
                "image": npc.image  # 修改5: 新增 image
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
    
    is_new_high = user.game_scores.update_score(theme_id, level_idx, question_idx, score)
    theme_total = user.game_scores.get_theme_score(theme_id)
    return is_new_high, theme_total

def get_user_game_score(user_id: str, theme_id: str) -> int:
    """取得使用者在某主題的總分"""
    user = user_data.get(user_id)
    if not user:
        return 0
    return user.game_scores.get_theme_score(theme_id)

def get_user_level_score(user_id: str, theme_id: str, level_idx: int) -> int:
    """取得使用者在某關卡的總分"""
    user = user_data.get(user_id)
    if not user:
        return 0
    
    if theme_id in user.game_scores.themes:
        theme = user.game_scores.themes[theme_id]
        if level_idx in theme.levels:
            return theme.levels[level_idx].get_total_score()
    return 0

def get_user_question_score(user_id: str, theme_id: str, level_idx: int, question_idx: int) -> int:
    """取得使用者在某題目的最高分"""
    user = user_data.get(user_id)
    if not user:
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
    if not user:
        return {"total_score": 0, "max_score": get_max_theme_score(), "levels_completed": 0, "questions_answered": 0}
    
    total_score = user.game_scores.get_theme_score(theme_id)
    max_score = get_max_theme_score()
    
    levels_completed = 0
    questions_answered = 0
    questions_per_level = get_questions_per_level()
    
    if theme_id in user.game_scores.themes:
        theme = user.game_scores.themes[theme_id]
        for level in theme.levels.values():
            questions_answered += len(level.questions)
            if len(level.questions) >= questions_per_level:
                levels_completed += 1
    
    return {
        "total_score": total_score,
        "max_score": max_score,
        "levels_completed": levels_completed,
        "questions_answered": questions_answered
    }

# ========== 結束新增 ==========

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

# 修改7: 使用服務特定檔案
async def load_user_data():
    global user_data
    user_data_file = get_user_data_file()
    
    # 確保目錄存在
    os.makedirs(os.path.dirname(user_data_file), exist_ok=True)
    
    try:
        async with _lock:
            async with aiofiles.open(user_data_file, 'r', encoding='utf-8') as file:
                content = await file.read()
        raw_data = json.loads(content)
        user_data = {key: User(**value) for key, value in raw_data.items()}
        print(f"User data loaded successfully from {user_data_file}.")
    except FileNotFoundError:
        print(f"No previous data file found at {user_data_file}, starting fresh.")
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from {user_data_file}, starting fresh.", e)

# 修改7: 使用服務特定檔案
async def save_user_data():
    global user_data
    user_data_file = get_user_data_file()
    
    # 確保目錄存在
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