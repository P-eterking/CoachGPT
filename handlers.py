from config import line_bot_api, line_bot_api_blob, groq, client
import asyncio
from utils.message_utils import (
    info_hint_message, result_message, send_message, send_text_message,
    question_message, carousel_message, handle_rich_menu,
    category, SpeechAssessment, get_question, SYSTEM_INSTRUCTION, text_message
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
        
user_data_enter = {}

async def check_user_login(event, message: str = None) -> bool:
    user_id = event.source.user_id
    
    if not hasData(user_id):
        info = user_data_enter.get(user_id,[])
        if message is None:
            await send_message(event, await info_hint_message(len(info)))
            return False
        # 上課時段
        if len(info) == 0:
            if '-' not in message:
                await send_text_message(event, "輸入格式錯誤！\nFormat error!")
                return False
        # 系級
        elif len(info) == 1:
            pass
        # 學號
        elif len(info) == 2:
            if not message.isdigit():
                await send_text_message(event, "學號格式錯誤！\nFormat error!")
                return False
        # 姓名
        else:
            info.append(message)
            initData(user_id, info[0], info[1], info[2], info[3])
            del user_data_enter[user_id]
            await send_message(event, [
                await text_message(f"綁定完成 你好! {message}\nSuccess! Hello, {message} !"), 
                await carousel_message(1)
            ])
            return True

        info.append(message)
        user_data_enter[user_id] = info
        await send_message(event, await info_hint_message(len(info)))
    
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
            await send_text_message(event, "無法獲取音訊內容，請稍後再試。\nUnable to get audio content, please try again later.")
            return

        with tempfile.NamedTemporaryFile(suffix=".m4a", delete=True) as f:
            f.write(message_content)
            f.seek(0)

            # 使用 Whisper 進行音訊轉錄
            transcript = await groq.audio.transcriptions.create(
                model="whisper-large-v3",
                file=(f.name,f.read()),
                language="en",
            )
            
            text = transcript.text.strip()
        
        unit = user_state[user_id]['unit']
        sub = user_state[user_id]['sub']
        question = get_question(unit,sub)
        
        completion = await client.beta.chat.completions.parse(
            model="gpt-4o",
            response_format=SpeechAssessment,
            max_completion_tokens=2048,
            temperature=1.2,
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_INSTRUCTION,
                },
                {
                    "role": "user",
                    "content": f"<question>{question['text']}</question>{"<standard>"+question['assessment_standard'].replace('\n','').strip()+"</standard>" if question.get('assessment_standard') else ""}<userAnswer>{text}</userAnswer>",
                }
            ],
        )
        result: SpeechAssessment = SpeechAssessment.model_validate_json(completion.choices[0].message.content)
        result.transcript = text
        
        updateHistory(user_id, f'{category}-{unit}-{sub}', result.to_dict())
        
        await send_message(event, await result_message(result, unit, sub))
    except Exception as e:
        print(e)

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