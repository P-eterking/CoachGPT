from config import line_bot_api, line_bot_api_blob, groq, client
import asyncio
from utils.message_utils import (
    result_message, send_message, send_text_message,
    question_message, carousel_message, handle_rich_menu,
    SpeechAssessment, get_question, get_context_url, SYSTEM_INSTRUCTION, text_message
)
from utils.file_utils import (
    user_state, save_user_data, hasData,
    updateHistory, initData
)
import tempfile

async def handle_text_message(event):
    message: str = event.message.text.strip()
    user_id = event.source.user_id

    if message.startswith('清除'):
        await line_bot_api.unlink_rich_menu_id_from_user(user_id)
        return
    
    await handle_rich_menu(user_id)
    
    if not await check_user_login(event, message):
        return

    if message.startswith('口語練習一'):
        await send_message(event, await carousel_message(1))
    elif message.startswith('口語練習二'):
        await send_message(event, await carousel_message(2))
    elif message.startswith('口語練習三'):
        await send_message(event, await carousel_message(3))
    elif message.startswith('儲存'):
        await save_user_data()

async def check_user_login(event, message: str = None) -> bool:
    user_id = event.source.user_id
    
    if not hasData(user_id):
        if message is None or len(message.split()) < 3:
            await send_text_message(
                event, 
                "請先綁定個人資料！\n依指定格式輸入：<系級> <學號> <姓名>\n如：應外一乙 11352237 王大明\n\nPlease enter your info first!\nInput format:\n<Department> <Student ID> <Name>"
            )
            return False
        try:
            depart, student_id, name = message.split(' ')[:3]
        except ValueError:
            await send_text_message(event, "輸入格式錯誤！")
            return False
        if not student_id.isdigit():
            await send_text_message(event, "學號格式錯誤！\nFormat error!")
            return False
        initData(user_id, depart, student_id, name)
        await send_message(event, [
            await text_message(f"綁定完成，Hello! {name}"), 
            await carousel_message(1)
        ])
    return True

async def handle_audio_message(event):
    if not await check_user_login(event):
        return
    
    user_id = event.source.user_id
    
    if user_state.get(user_id) is None:
        return
    
    try:
        result = await line_bot_api_blob.get_message_content_transcoding_by_message_id(event.message.id)
        while result.status == 'processing':
            result = await line_bot_api_blob.get_message_content_transcoding_by_message_id(event.message.id)
            await asyncio.sleep(1)

        message_content = await line_bot_api_blob.get_message_content(event.message.id)
        
        if not message_content:
            await send_text_message(event, "無法獲取音訊內容，請稍後再試。")
            return

        with tempfile.NamedTemporaryFile(suffix=".m4a", delete=True) as f:
            f.write(message_content)
            f.seek(0)
        
            # 使用 Whisper 進行音訊轉錄
            transcript = await groq.audio.transcriptions.create(
                model="whisper-large-v3",
                file=f.name,
                language="en",
            )
            
            text = transcript.text.strip()
        
        unit = user_state[user_id]['unit']
        sub = user_state[user_id]['sub']
        
        completion = await client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            response_format=SpeechAssessment,
            max_tokens=2048,
            temperature=1.2,
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_INSTRUCTION,
                },
                {
                    "role": "user",
                    "content": f"<question>{get_question(unit,sub)}</question><userAnswer>{text}</userAnswer>",
                }
            ],
        )
        result: SpeechAssessment = SpeechAssessment.model_validate_json(completion.choices[0].message.content)
        result.transcript = text
        
        updateHistory(user_id, f'{unit}-{sub}', result.to_dict())
        
        await send_message(event, await result_message(result, unit, sub))
    except Exception as e:
        await send_text_message(event, f"處理音訊時發生錯誤: {str(e)}")

async def handle_postback(event):
    if not await check_user_login(event):
        return
    user_id = event.source.user_id
    data: str = event.postback.data
    vars = {sep.split('=')[0]: sep.split('=')[1] for sep in data.split('&')}
    action = vars.get('action')
    
    if action == 'record':
        unit = int(vars.get('unit', 0))
        sub = int(vars.get('sub', 0))
        user_state[user_id] = {'unit': unit, 'sub': sub}
        await send_message(event, await question_message(unit, sub))
    elif action == 'unit':
        unit = int(vars.get('unit', 1))
        await send_message(event, await carousel_message(unit))