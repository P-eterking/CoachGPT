from fastapi import Request, HTTPException
from config import parser
from handlers import handle_text_message, handle_audio_message, handle_postback
from linebot.v3.webhooks import MessageEvent, PostbackEvent, TextMessageContent, AudioMessageContent
from linebot.v3.exceptions import InvalidSignatureError

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