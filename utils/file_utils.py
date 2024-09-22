import json
import aiofiles
import asyncio
from config import USER_STATE_FILE, USER_DATA_FILE

# 狀態資料
user_state = {}
user_data = {}

async def load_user_state():
    global user_state
    try:
        async with aiofiles.open(USER_STATE_FILE, 'r') as file:
            content = await file.read()
            user_state = json.loads(content)
            print("User state loaded successfully.")
    except FileNotFoundError:
        print("No previous state file found, starting fresh.")
    except json.JSONDecodeError:
        print("Error decoding JSON, starting fresh.")

async def load_user_data():
    global user_data
    try:
        async with aiofiles.open(USER_DATA_FILE, 'r') as file:
            content = await file.read()
            user_data = json.loads(content)
            print("User data loaded successfully.")
    except FileNotFoundError:
        print("No previous data file found, starting fresh.")
    except json.JSONDecodeError:
        print("Error decoding JSON, starting fresh.")

async def save_user_state():
    while True:
        async with aiofiles.open(USER_STATE_FILE, 'w') as file:
            await file.write(json.dumps(user_state, indent=4))
            print("User state saved.")
        await asyncio.sleep(60 * 60)

async def save_user_data():
    while True:
        async with aiofiles.open(USER_DATA_FILE, 'w') as file:
            await file.write(json.dumps(user_data, indent=4))
            print("User data saved.")
        await asyncio.sleep(60 * 60)