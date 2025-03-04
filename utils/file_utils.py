import json
import aiofiles  # 非同步檔案處理庫，用於讀取與寫入資料
import asyncio
from config import USER_DATA_FILE, CONFIG_FILE  # 使用者資料檔案的路徑
from utils.models import User, SpeechAssessment, UserState  # 使用者和評分資料的模型

# 使用者狀態和資料
user_state: dict[str, UserState] = {}  # 儲存每個使用者的即時狀態
user_data: dict[str, User] = {}  # 儲存每個使用者的詳細資料，包括歷史紀錄

# 預設設定
DEFAULT_CONFIG = {
    'admin': [],
    'rich_menu_ids': {},
}

# 設定檔案
config = DEFAULT_CONFIG.copy()

def get_user_state(user_id: str) -> UserState | None:
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
    # 將新的使用者資料加入 user_data 字典，並初始化歷史紀錄為空字典
    user_data[user_id] = User(dep=dep, id=id, name=name, class_time=classTime, history={}, chat={})

# 刪除使用者資料
def delData(user_id):
    # 若 user_data 中存在此 user_id 的資料，則刪除之
    if user_data.get(user_id) is not None:
        del user_data[user_id]

# 檢查是否已有使用者資料
def hasData(user_id) -> bool:
    # 若 user_data 中存在此 user_id 的資料，返回 True，否則返回 False
    return user_data.get(user_id) is not None

# 獲取使用者資料
def getData() -> dict:
    return user_data

# 更新使用者的歷史紀錄
def updateHistory(user_id, key, history: SpeechAssessment):
    # 將指定的歷史紀錄（history）新增或更新到 user_data 中該使用者的歷史紀錄
    if key not in user_data[user_id].history:
        user_data[user_id].history[key] = []
    user_data[user_id].history[key].append(history)

# 獲取使用者的歷史紀錄
def getHistory(user_id, key) -> list[SpeechAssessment] | None:
    # 獲取指定使用者的指定歷史紀錄
    return user_data[user_id].history.get(key,None)

def isAdmin(user_id) -> bool:
    return user_id in config['admin']

async def addAdmin(user_id):
    config['admin'].append(user_id)
    config['admin'] = list(set(config['admin']))

# 非同步加載設定
async def load_config():
    global config
    try:
        # 讀取 CONFIG_FILE 中的內容，並解析為 config 字典
        async with aiofiles.open(CONFIG_FILE, 'r', encoding='utf-8') as file:
            content = await file.read()
            loaded_config = json.loads(content)
            config.update(loaded_config)
            print("Config loaded successfully.")
    except FileNotFoundError:
        # 如果 CONFIG_FILE 不存在，則建立一個空的字典並儲存至檔案中
        async with aiofiles.open(CONFIG_FILE, 'w', encoding='utf-8') as file:
            await file.write(json.dumps(config, indent=4))
            print("Config created successfully.")

# 非同步儲存設定
async def save_config():
    global config
    # 將 config 字典轉換為 JSON 字串，並儲存至 CONFIG_FILE 中
    async with aiofiles.open(CONFIG_FILE, 'w', encoding='utf-8') as file:
        await file.write(json.dumps(config, indent=4))
        print("Config saved successfully.")

# 儲存所有資料
async def save_all():
    await save_config()
    await save_user_data()
    return 'All data saved.'

# 非同步加載使用者資料
async def load_user_data():
    global user_data
    try:
        # 讀取 USER_DATA_FILE 中的內容，並解析為 user_data 字典
        async with aiofiles.open(USER_DATA_FILE, 'r', encoding='utf-8') as file:
            content = await file.read()
            raw_data = json.loads(content)
            user_data = {key: User(**value) for key, value in raw_data.items()}
            print("User data loaded successfully.")
    except FileNotFoundError:
        # 若找不到檔案，顯示訊息並初始化 user_data
        print("No previous data file found, starting fresh.")
    except json.JSONDecodeError as e:
        # 若檔案無法解析，顯示訊息並重新初始化 user_data
        print("Error decoding JSON, starting fresh.",e)

# 非同步儲存使用者資料
async def save_user_data():
    global user_data
    # 將 user_data 轉換為 JSON 字串，並寫入 USER_DATA_FILE
    async with aiofiles.open(USER_DATA_FILE, 'w', encoding='utf-8') as file:
        serializable_data = {key: user.to_dict() for key, user in user_data.items()}
        json_data = json.dumps(serializable_data, indent=4)
        await file.write(json_data)
        print("User data saved.")
        
# 每小時自動儲存使用者資料
async def user_data_task():
    while True:
        # 每 60 分鐘呼叫一次 save_user_data 儲存資料
        await save_user_data()
        await asyncio.sleep(60 * 60)
