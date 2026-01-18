import json
import aiofiles  # 非同步檔案處理庫，用於讀取與寫入資料
import asyncio
import os
import re
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple
from config import USER_DATA_FILE, CONFIG_FILE, client
from utils.models import ChatHistory, User, SpeechAssessment, UserState, RagChunk

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
    'display_feedback': True
}

# 設定檔案
config = DEFAULT_CONFIG.copy()

_rag_cache: Dict[str, List[RagChunk]] = {}
_rag_lock = asyncio.Lock()

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
    user_data[user_id] = User(dep=dep, id=id, name=name, class_time=classTime, history={}, chat={})

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
        config.update(loaded_config)
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

async def load_user_data():
    global user_data
    try:
        async with _lock:
            async with aiofiles.open(USER_DATA_FILE, 'r', encoding='utf-8') as file:
                content = await file.read()
        raw_data = json.loads(content)
        user_data = {key: User(**value) for key, value in raw_data.items()}
        print("User data loaded successfully.")
    except FileNotFoundError:
        print("No previous data file found, starting fresh.")
    except json.JSONDecodeError as e:
        print("Error decoding JSON, starting fresh.",e)

async def save_user_data():
    global user_data
    async with _lock:
        async with aiofiles.open(USER_DATA_FILE, 'w', encoding='utf-8') as file:
            serializable_data = {key: user.to_dict() for key, user in user_data.items()}
            json_data = json.dumps(serializable_data, indent=4)
            await file.write(json_data)
    print("User data saved.")
        
async def user_data_task():
    while True:
        await save_user_data()
        await asyncio.sleep(60 * 60)