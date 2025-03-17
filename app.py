import asyncio
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from routes import callback, index
from config import question_manager
from utils.file_utils import load_user_data, save_all, save_config, save_user_data, user_data_task, load_config
from utils.message_utils import create_rich_menu
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    await load_user_data()
    await load_config()
    await create_rich_menu()
    asyncio.create_task(user_data_task())
    yield
    await save_config()
    await save_user_data()

# 創建 FastAPI 應用
app = FastAPI(lifespan=lifespan)

# 註冊路由
app.post("/callback")(callback)
app.get("/saveall")(save_all)
app.get("/qreload")(question_manager.load_questions)
app.mount('/templates', StaticFiles(directory='templates'))
app.get("/")(index)