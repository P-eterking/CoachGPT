"""Refactored FastAPI application with clean architecture."""

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.webhooks import MessageEvent, PostbackEvent, TextMessageContent, AudioMessageContent

from core.container import container, configure_container
from core.logging_config import setup_logging, get_logger
from core.constants import AUTO_SAVE_INTERVAL
from handlers_refactored import MessageHandler
from analyze import analyze_by_question


# Set up logging
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting application...")
    
    # Configure dependency injection container
    configure_container()
    
    # Get repositories
    user_repository = container.get('user_repository')
    
    # Load initial data
    await user_repository.load_user_data()
    await user_repository.load_config()
    
    # Create rich menu
    try:
        from utils.message_utils import create_rich_menu
        await create_rich_menu()
    except Exception as e:
        logger.error(f"Failed to create rich menu: {e}")
    
    # Start auto-save task
    auto_save_task = asyncio.create_task(auto_save_user_data(user_repository))
    
    logger.info("Application started successfully")
    
    yield
    
    # Cleanup
    logger.info("Shutting down application...")
    
    # Cancel auto-save task
    auto_save_task.cancel()
    try:
        await auto_save_task
    except asyncio.CancelledError:
        pass
    
    # Save final data
    await user_repository.save_config()
    await user_repository.save_user_data()
    
    logger.info("Application shut down successfully")


async def auto_save_user_data(user_repository):
    """Periodically save user data."""
    while True:
        try:
            await asyncio.sleep(AUTO_SAVE_INTERVAL)
            await user_repository.save_user_data()
            logger.debug("Auto-saved user data")
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error in auto-save: {e}")


# Create FastAPI application
app = FastAPI(
    title="LINE Bot Application",
    description="Refactored LINE Bot with clean architecture",
    version="2.0.0",
    lifespan=lifespan
)

# Initialize templates
templates = Jinja2Templates(directory="templates")

# Initialize message handler
message_handler = MessageHandler()


@app.post("/callback")
async def callback(request: Request):
    """Handle LINE webhook callbacks."""
    signature = request.headers.get("X-Line-Signature")
    if not signature:
        raise HTTPException(status_code=400, detail="Missing signature")
    
    body = await request.body()
    body_text = body.decode()
    
    # Get parser from container
    parser = container.get('parser')
    
    try:
        events = parser.parse(body_text, signature)
    except InvalidSignatureError:
        logger.warning("Invalid signature received")
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    # Process events
    for event in events:
        try:
            if isinstance(event, PostbackEvent):
                await message_handler.handle_postback(event)
            elif isinstance(event, MessageEvent):
                if isinstance(event.message, TextMessageContent):
                    await message_handler.handle_text_message(event)
                elif isinstance(event.message, AudioMessageContent):
                    await message_handler.handle_audio_message(event)
                else:
                    logger.debug(f"Unsupported message type: {type(event.message)}")
        except Exception as e:
            logger.error(f"Error processing event: {e}")
    
    return {"status": "OK"}


@app.get("/")
async def index(request: Request):
    """Display analytics dashboard."""
    try:
        user_repository = container.get('user_repository')
        question_manager = container.get('question_manager')
        
        users = user_repository.get_all_users()
        analysis = analyze_by_question(users.values(), question_manager)
        
        # Prepare chart data
        labels = []
        average_scores = []
        completion_rates = []
        
        for category in analysis.get("category_analysis", []):
            category_name = f"Category {category['category']}"
            for unit in category.get("units", []):
                label = f"{category_name} - Unit {unit['unit']}"
                labels.append(label)
                average_scores.append(unit.get("average_score", 0))
                
                user_count = analysis.get("user_count", 1)
                completion_rate = (
                    (unit.get("users_completed", 0) / user_count * 100) 
                    if user_count > 0 else 0
                )
                completion_rates.append(completion_rate)
        
        analysis_data = {
            "labels": labels,
            "average_scores": average_scores,
            "completion_rates": completion_rates
        }
        
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "category_analysis": analysis.get("category_analysis", []),
                "analysis_data": analysis_data,
                "latest_histories": analysis.get("latest_histories", [])
            }
        )
    except Exception as e:
        logger.error(f"Error generating index page: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "2.0.0"}


@app.get("/saveall")
async def save_all():
    """Manually trigger save of all data."""
    try:
        user_repository = container.get('user_repository')
        await user_repository.save_user_data()
        await user_repository.save_config()
        logger.info("Manual save completed")
        return {"status": "success", "message": "Data saved successfully"}
    except Exception as e:
        logger.error(f"Error saving data: {e}")
        raise HTTPException(status_code=500, detail="Failed to save data")


@app.get("/qreload")
async def reload_questions():
    """Reload questions from files."""
    try:
        question_manager = container.get('question_manager')
        question_manager.load_questions()
        logger.info("Questions reloaded")
        return {"status": "success", "message": "Questions reloaded successfully"}
    except Exception as e:
        logger.error(f"Error reloading questions: {e}")
        raise HTTPException(status_code=500, detail="Failed to reload questions")


# Mount static files
app.mount('/templates', StaticFiles(directory='templates'), name='static')


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app_refactored:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_config={
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                },
            },
            "handlers": {
                "default": {
                    "formatter": "default",
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout",
                },
            },
            "root": {
                "level": "INFO",
                "handlers": ["default"],
            },
        }
    )