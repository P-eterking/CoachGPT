from fastapi import Request, HTTPException
from fastapi.templating import Jinja2Templates
from config import app_config
from handlers import handle_text_message, handle_audio_message, handle_postback
from linebot.v3.webhooks import MessageEvent, PostbackEvent, TextMessageContent, AudioMessageContent
from linebot.v3.exceptions import InvalidSignatureError
from analyze import analyze_by_question
from utils.file_utils import getData

async def callback(request: Request):
    """
    Handle LINE Bot webhook callback.
    
    Args:
        request: The incoming HTTP request
        
    Returns:
        'OK' response for LINE Bot platform
    """
    signature = request.headers["X-Line-Signature"]
    body = await request.body()
    body = body.decode()
    
    try:
        events = app_config.parser.parse(body, signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    # Process each event
    for event in events:
        try:
            if isinstance(event, PostbackEvent):
                await handle_postback(event)
            elif isinstance(event, MessageEvent):
                if isinstance(event.message, TextMessageContent):
                    await handle_text_message(event)
                elif isinstance(event.message, AudioMessageContent):
                    await handle_audio_message(event)
        except Exception as e:
            print(f"Error processing event: {e}")
            # Continue processing other events
    
    return 'OK'

templates = Jinja2Templates(directory="templates")

async def index(request: Request):
    """
    Render the main dashboard page with user analytics.
    
    Args:
        request: The incoming HTTP request
        
    Returns:
        Rendered HTML template with analytics data
    """
    try:
        users = getData()
        analysis = analyze_by_question(users.values(), app_config.question_manager)
        
        # Prepare chart data
        labels = []
        average_scores = []
        completion_rates = []
        
        for category in analysis["category_analysis"]:
            category_name = f"Category {category['category']}"
            for unit in category["units"]:
                label = f"{category_name} - Unit {unit['unit']}"
                labels.append(label)
                average_scores.append(unit["average_score"])
                completion_rate = (
                    (unit["users_completed"] / analysis["user_count"] * 100) 
                    if analysis["user_count"] > 0 else 0
                )
                completion_rates.append(completion_rate)
        
        analysis_data = {
            "labels": labels,
            "average_scores": average_scores,
            "completion_rates": completion_rates
        }
        
        latest_histories = analysis["latest_histories"]
        
        return templates.TemplateResponse("index.html", {
            "request": request,
            "category_analysis": analysis["category_analysis"],
            "analysis_data": analysis_data,
            "latest_histories": latest_histories
        })
        
    except Exception as e:
        print(f"Error rendering index page: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")