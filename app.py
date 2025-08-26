import asyncio
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from routes import callback, index
from config import app_config
from utils.file_utils import load_user_data, save_all, save_config, save_user_data, user_data_task, load_config, user_data, user_state
from utils.message_utils import create_rich_menu, SYSTEM_INSTRUCTION
from contextlib import asynccontextmanager
from services.container import container
from services.audio_service import AudioService
from services.assessment_service import AssessmentService
from services.user_service import UserService

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize services
    audio_service = AudioService(app_config.openai_client, app_config.line_bot_api_blob)
    assessment_service = AssessmentService(app_config.openai_client, SYSTEM_INSTRUCTION)
    user_service = UserService(user_data, user_state)
    
    # Register services in container
    container.set_audio_service(audio_service)
    container.set_assessment_service(assessment_service)
    container.set_user_service(user_service)
    
    # Load data and initialize
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
app.get("/qreload")(app_config.question_manager.load_questions)
app.mount('/templates', StaticFiles(directory='templates'))
app.get("/")(index)