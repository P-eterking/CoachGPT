import json
import aiofiles
import asyncio
from config import USER_DATA_FILE

# 狀態資料
user_state = {}
user_data = {}

def initData(user_id, classTime, dep, id, name):
    user_data[user_id] = {'dep': dep, 'id': id, 'name': name, 'class-time': classTime, 'history': {}}
    
def hasData(user_id) -> bool:
    return user_data.get(user_id) is not None

def updateHistory(user_id, key, history: dict):
    user_data[user_id]['history'][key] = history
    
async def load_user_data():
    global user_data
    try:
        async with aiofiles.open(USER_DATA_FILE, 'r', encoding='utf-8') as file:
            content = await file.read()
            user_data = json.loads(content)
            print("User data loaded successfully.")
    except FileNotFoundError:
        print("No previous data file found, starting fresh.")
    except json.JSONDecodeError:
        print("Error decoding JSON, starting fresh.")

async def save_user_data():
    global user_data
    async with aiofiles.open(USER_DATA_FILE, 'w', encoding='utf-8') as file:
        await file.write(json.dumps(user_data, indent=4))
        print("User data saved.")
        
async def user_data_task():
    while True:
        await save_user_data()
        await asyncio.sleep(60 * 60)