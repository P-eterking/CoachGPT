import asyncio
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from routes import callback
from config import question_manager
from utils.file_utils import load_user_data, save_all, save_config, save_user_data, user_data_task, load_config
from utils.message_utils import create_rich_menu
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    await load_user_data()
    await load_config()
    try:
        await create_rich_menu()
    except (RuntimeError, FileNotFoundError) as e:
        # 選單未完整同步或本機資源缺失：應讓啟動失敗以便 Docker / 部署立刻發現，避免寫入殘缺 rich_menu_ids
        print(f'[FATAL] Rich menu startup check failed: {e}')
        raise
    except Exception as e:
        print(f"Warning: Failed to create rich menus during startup. Error: {e}")
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
# app.get("/")(index)