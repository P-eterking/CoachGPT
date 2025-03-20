from fastapi import Request, HTTPException
from fastapi.templating import Jinja2Templates
from config import parser, question_manager
from handlers import handle_text_message, handle_audio_message, handle_postback
from linebot.v3.webhooks import MessageEvent, PostbackEvent, TextMessageContent, AudioMessageContent
from linebot.v3.exceptions import InvalidSignatureError
from analyze import analyze_by_question
from utils.file_utils import getData

async def callback(request: Request):
    signature = request.headers["X-Line-Signature"]
    body = await request.body()
    body = body.decode()
    
    try:
        events = parser.parse(body, signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    for event in events:
        if isinstance(event, PostbackEvent):
            await handle_postback(event)
        elif isinstance(event, MessageEvent):
            if isinstance(event.message, TextMessageContent):
                await handle_text_message(event)
            elif isinstance(event.message, AudioMessageContent):
                await handle_audio_message(event)
    
    return 'OK'

templates = Jinja2Templates(directory="templates")

async def index(request: Request):
    users = getData()
    analysis = analyze_by_question(users.values(), question_manager)
    
    labels = []
    average_scores = []
    completion_rates = []
    for category in analysis["category_analysis"]:
        category_name = f"Category {category['category']}"
        for unit in category["units"]:
            label = f"{category_name} - Unit {unit['unit']}"
            labels.append(label)
            average_scores.append(unit["average_score"])
            completion_rate = (unit["users_completed"] / analysis["user_count"] * 100) if analysis["user_count"] > 0 else 0
            completion_rates.append(completion_rate)
    
    analysis_data = {
        "labels": labels,
        "average_scores": average_scores,
        "completion_rates": completion_rates
    }
    
    latest_histories = analysis["latest_histories"]  # Extract latest_histories
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "category_analysis": analysis["category_analysis"],
        "analysis_data": analysis_data,
        "latest_histories": latest_histories  # Pass latest_histories to template
    })