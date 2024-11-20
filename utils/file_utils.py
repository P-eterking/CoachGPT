import json
import aiofiles  # 非同步檔案處理庫，用於讀取與寫入資料
import asyncio
from config import USER_DATA_FILE, CONFIG_FILE  # 使用者資料檔案的路徑
from utils.models import User, SpeechAssessment  # 使用者和評分資料的模型
# 使用者狀態和資料
user_state = {}  # 儲存每個使用者的即時狀態
user_data : dict[str,User] = {}  # 儲存每個使用者的詳細資料，包括歷史紀錄
config = {}  # 儲存系統設定

test_mode = False
answerable = True

# 切換答題模式
def switch_answerable() -> bool:
    global answerable
    answerable = not(answerable)
    return answerable

# 獲取答題模式狀態
def get_answerable() -> bool:
    global answerable
    return answerable

# 切換測試模式
def switch_test_mode() -> bool:
    global test_mode
    test_mode = not(test_mode)
    return test_mode

# 獲取測試模式
def get_test_mode() -> bool:
    global test_mode
    return test_mode

# 初始化使用者資料
def initData(user_id, classTime, dep, id, name):
    # 將新的使用者資料加入 user_data 字典，並初始化歷史紀錄為空字典
    user_data[user_id] = User(dep=dep, id=id, name=name, class_time=classTime, history={})

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
    user_data[user_id].history[key] = history

# 獲取使用者的歷史紀錄
def getHistory(user_id, key) -> SpeechAssessment | None:
    # 獲取指定使用者的指定歷史紀錄
    return user_data[user_id].history.get(key,None)

def get_rich_menu_id():
    return config.get('rich_menu_id')

def set_rich_menu_id(rich_menu_id: str):
    config['rich_menu_id'] = rich_menu_id

async def load_config():
    global config
    try:
        # 讀取 CONFIG_FILE 中的內容，並解析為 config 字典
        async with aiofiles.open(CONFIG_FILE, 'r', encoding='utf-8') as file:
            content = await file.read()
            config = json.loads(content)
            print("Config loaded successfully.")
    except FileNotFoundError:
        # 如果 CONFIG_FILE 不存在，則建立一個空的字典並儲存至檔案中
        async with aiofiles.open(CONFIG_FILE, 'w', encoding='utf-8') as file:
            await file.write(json.dumps({}))
            print("Config created successfully.")

async def save_config():
    global config
    # 將 config 字典轉換為 JSON 字串，並儲存至 CONFIG_FILE 中
    async with aiofiles.open(CONFIG_FILE, 'w', encoding='utf-8') as file:
        await file.write(json.dumps(config))
        print("Config saved successfully.")

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
    except json.JSONDecodeError:
        # 若檔案無法解析，顯示訊息並重新初始化 user_data
        print("Error decoding JSON, starting fresh.")

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
