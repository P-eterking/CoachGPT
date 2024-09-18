import os
from pathlib import Path
import aiofiles
from fastapi import FastAPI, Request, HTTPException
from linebot.v3.webhook import WebhookParser
from linebot.v3.exceptions import (
    InvalidSignatureError
)
from linebot.v3.messaging import (
    Configuration,
    AsyncApiClient,
    AsyncMessagingApi,
    AsyncMessagingApiBlob,
    ReplyMessageRequest,
    TextMessage,
    ApiException,
    ErrorResponse,
    FlexMessage,
    FlexContainer
)
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent,
    AudioMessageContent
)
from groq import Groq
from openai import OpenAI

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
)
groq  = Groq(api_key=os.getenv("GROQ_API_KEY"))
app = FastAPI()

LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")

configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
parser = WebhookParser(LINE_CHANNEL_SECRET)
async_api_client = AsyncApiClient(configuration)
line_bot_api = AsyncMessagingApi(async_api_client)
line_bot_api_blob = AsyncMessagingApiBlob(async_api_client)

@app.post("/callback")
async def callback(request: Request):
    signature = request.headers["X-Line-Signature"]
    body = await request.body()  # Get the request body as bytes
    body = body.decode()
    try:
        events = parser.parse(body, signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    for event in events:
        try:
            if not isinstance(event, MessageEvent):
                continue
            if isinstance(event.message, TextMessageContent):
                # 處理文字消息
                await send_redirect_message(event)
                # await handle_text_message(event)
            elif isinstance(event.message, AudioMessageContent):
                # 處理語音消息
                await handle_audio_message(event)
            
        except ApiException:
            print("Got response with http status code: " + str(event.status))
            print("Got x-line-request-id: " + event.headers['x-line-request-id'])
            print("Got response with http body: " + str(ErrorResponse.from_json(event.body)))
    
    return 'OK'

async def handle_text_message(event):
    # 現有的文字消息處理邏輯
    await line_bot_api.reply_message(
        ReplyMessageRequest(
            reply_token=event.reply_token,
            messages=[TextMessage(text=event.message.text)]
        )
    )

async def handle_audio_message(event):
    # 獲取音頻文件
    message_content = await line_bot_api_blob.get_message_content(event.message.id)
    
    # 保存音頻文件
    async with aiofiles.open(f"{event.message.id}.m4a", "wb") as f:
        await f.write(message_content)
    
    # 使用 Whisper API 轉錄音頻
    transcript = groq.audio.transcriptions.create(
        model="whisper-large-v3",
        file=Path(f"{event.message.id}.m4a"),  # Pass the audio content as bytes
        prompt="",
    )
    
    # 回覆轉錄結果
    await line_bot_api.reply_message(
        ReplyMessageRequest(
            reply_token=event.reply_token,
            messages=[TextMessage(text=f"您說的是: {transcript.text}")]
        )
    )
    

async def send_redirect_message(event):
    flex_message = FlexMessage(
        alt_text="请点击链接",
        contents=FlexContainer.from_dict({
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                {
                    "type": "image",
                    "url": "https://developers-resource.landpress.line.me/fx/clip/clip3.jpg",
                    "size": "full",
                    "aspectMode": "cover",
                    "aspectRatio": "1:1",
                    "gravity": "center"
                },
                {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [],
                    "position": "absolute",
                    "background": {
                    "type": "linearGradient",
                    "angle": "0deg",
                    "endColor": "#00000000",
                    "startColor": "#00000099"
                    },
                    "width": "100%",
                    "height": "40%",
                    "offsetBottom": "0px",
                    "offsetStart": "0px",
                    "offsetEnd": "0px"
                },
                {
                    "type": "box",
                    "layout": "horizontal",
                    "contents": [
                    {
                        "type": "button",
                        "action": {
                        "type": "uri",
                        "label": "登入 iTouch",
                        "uri": "https://itouch.cycu.edu.tw/active_system/login/loginfailt.jsp?returnPath=https://glorious-ghost-workable.ngrok-free.app/login/?id=123"
                        },
                        "style": "primary",
                        "scaling": True,
                        "gravity": "bottom"
                    }
                    ],
                    "position": "absolute",
                    "offsetBottom": "0px",
                    "offsetStart": "0px",
                    "offsetEnd": "0px",
                    "paddingAll": "20px"
                }
                ],
                "paddingAll": "0px"
            }
        })
    )

    await line_bot_api.reply_message(
        ReplyMessageRequest(
            reply_token=event.reply_token,
            messages=[flex_message]
        )
    )

@app.post('/login')
async def login(request: Request):
    body = await request.body()  # Get the request body as bytes
    body = body.decode()
    print(body)