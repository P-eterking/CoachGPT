import asyncio
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from routes import callback
from utils.file_utils import load_user_data, user_data_task
from utils.message_utils import create_rich_menu

app = FastAPI()

# 註冊路由
app.post("/callback")(callback)
app.mount('/templates', StaticFiles(directory='templates'))

async def init():
    # 載入之前儲存的狀態資料
    # await load_user_state()
    await load_user_data()
    await create_rich_menu()

    # 開始執行定時儲存任務
    asyncio.create_task(user_data_task())
    # asyncio.create_task(save_user_data())

loop = asyncio.get_running_loop()
loop.create_task(init())