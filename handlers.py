import aiofiles
from config import line_bot_api, line_bot_api_blob, groq
import asyncio
from utils.message_utils import send_carousel_message, send_text_message
from utils.file_utils import user_data
from pathlib import Path 

async def handle_text_message(event):
    user_id = event.source.user_id
    message = event.message.text.strip()

    # 用戶資料綁定
    if user_data.get(user_id) is None:
        if len(message.split()) < 3:
            await send_text_message(event, "請先綁定個人資料！\n依指定格式輸入：<系級> <學號> <姓名>\n如：應外一乙 11352237 王大明\n\nPlease enter your info first!\nInput format:\n<Department> <Student ID> <Name>")
            return
        depart, student_id, name = message.split(' ')[0], message.split(' ')[1], message.split(' ')[2]
        if not student_id.isdigit():
            await send_text_message(event, "學號格式錯誤！\nFormat error!")
            return
        user_data[user_id] = {'dep': depart, 'id': student_id, 'name': name}
        await send_text_message(event, f"綁定完成，Hello! {name}")
        return

    # 如果是其他指令或回應
    await send_carousel_message(event)

async def handle_audio_message(event):
    user_id = event.source.user_id
    
    result = await line_bot_api_blob.get_message_content_transcoding_by_message_id(event.message.id)
    
    while result.status == 'processing':
        result = await line_bot_api_blob.get_message_content_transcoding_by_message_id(event.message.id)
        await asyncio.sleep(1)

    message_content = await line_bot_api_blob.get_message_content(event.message.id)

    async with aiofiles.open(f"{event.message.id}.m4a", "wb") as f:
        await f.write(message_content)
    
    if message_content is None:
        await send_text_message(event, "無法獲取音訊內容，請稍後再試。")
        return
    
    # 使用 Whisper 進行音訊轉錄
    transcript = groq.audio.transcriptions.create(
        model="whisper-large-v3",
        file=Path(f"{event.message.id}.m4a"),
        language="en",
    )

    await send_text_message(event, f"您說的是: {transcript.text}")

async def handle_postback(event):
    data = event.postback.data
    if data == 'action=buy&itemid=111':
        await send_text_message(event,"您點擊了購買按鈕")
    else:
        await send_text_message(event,"您點擊了其他按鈕")