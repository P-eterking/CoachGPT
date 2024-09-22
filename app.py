import asyncio
from fastapi import FastAPI
from routes import callback
from utils.file_utils import load_user_state, load_user_data, save_user_state, save_user_data

app = FastAPI()

# 註冊路由
app.post("/callback")(callback)

if __name__ == "__main__":
    # 載入之前儲存的狀態資料
    asyncio.run(load_user_state())
    asyncio.run(load_user_data())
    # 開始執行定時儲存任務
    asyncio.create_task(save_user_state())
    asyncio.create_task(save_user_data())