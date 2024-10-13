from config import line_bot_api, line_bot_api_blob, groq, client
import asyncio
from utils.message_utils import result_message, send_message, send_text_message, question_message, carousel_message, SpeechAssessment, qs, SYSTEM_INSTRUCTION, richMenuId
from utils.file_utils import user_data, user_state
import tempfile

async def handle_text_message(event):
    # user_id = event.source.user_id
    message = event.message.text.strip()

    response = line_bot_api.get_rich_menu_id_of_user(event.source.user_id).get()
    if not response.to_dict()['richMenuId']:
        await line_bot_api.link_rich_menu_id_to_user(event.source.user_id, richMenuId).get()
    
    # 用戶資料綁定
    if not await check_user_login(event, message):
        return

    if message.startswith('口語練習一'):
        await send_message(event, await carousel_message(1))
        return
    elif message.startswith('口語練習二'):
        await send_message(event, await carousel_message(2))
        return
    elif message.startswith('口語練習三'):
        await send_message(event, await carousel_message(3))
        return
    
    # 如果是其他指令或回應
    # await send_carousel_message(event, unit=1)

async def check_user_login(event, message = None):
    user_id = event.source.user_id
    
    if user_data.get(user_id) is None:
        if message is None or len(message.split()) < 3:
            await send_text_message(event, "請先綁定個人資料！\n依指定格式輸入：<系級> <學號> <姓名>\n如：應外一乙 11352237 王大明\n\nPlease enter your info first!\nInput format:\n<Department> <Student ID> <Name>")
            return False
        depart, student_id, name = message.split(' ')[0], message.split(' ')[1], message.split(' ')[2]
        if not student_id.isdigit():
            await send_text_message(event, "學號格式錯誤！\nFormat error!")
            return False
        user_data[user_id] = {'dep': depart, 'id': student_id, 'name': name}
        await send_text_message(event, f"綁定完成，Hello! {name}")
        
    return True

async def handle_audio_message(event):
    if not await check_user_login(event):
        return
    
    user_id = event.source.user_id
    
    if user_state.get(user_id) is None:
        return
    
    result = await line_bot_api_blob.get_message_content_transcoding_by_message_id(event.message.id)
    
    while result.status == 'processing':
        result = await line_bot_api_blob.get_message_content_transcoding_by_message_id(event.message.id)
        await asyncio.sleep(1)

    message_content = await line_bot_api_blob.get_message_content(event.message.id)
    
    text = None
    
    with tempfile.NamedTemporaryFile(suffix=".m4a", delete=True) as f:
        f.write(message_content)
        f.seek(0)
    
        if message_content is None:
            await send_text_message(event, "無法獲取音訊內容，請稍後再試。")
            return

        # 使用 Whisper 進行音訊轉錄
        transcript = await groq.audio.transcriptions.create(
            model="whisper-large-v3",
            file=f.file,
            language="en",
        )
        
        text = transcript.text
        f.flush()
    
    unit = user_state[user_id]['unit']
    sub = user_state[user_id]['sub']
    
    # completion =  await groq.chat.completions.create(
    completion = await client.beta.chat.completions.parse(
        # model="llama-3.2-11b-vision-preview",
        model="gpt-4o-mini",
        response_format=SpeechAssessment,
        # response_format={"type": "json_object"},
        max_tokens=2048,
        temperature=0.8,
        messages=[
            {
                "role": "system",
                "content": SYSTEM_INSTRUCTION
            },
            {
                "role": "user",
                "content": f"<question>{qs[unit][sub]}</question><userAnswer>使用者回答：{text}</userAnswer>",
            }
        ],
    )
    result : SpeechAssessment = SpeechAssessment.model_validate_json(completion.choices[0].message.content)
    
    await send_message(event, await result_message(result, unit, sub))

async def handle_postback(event):
    if not await check_user_login(event):
        return
    user_id = event.source.user_id
    data :str = event.postback.data
    vars = {}
    for sep in data.split('&'):
        vars[sep.split('=')[0]] = sep.split('=')[1]
    if vars['action'] == 'record':
        user_state[user_id] = {'unit': int(vars['unit']), 'sub': int(vars['sub'])}
        await send_message(event, await question_message(int(vars['unit']), int(vars['sub'])))
    elif vars['action'] == 'unit':
        await send_message(event, await carousel_message(int(vars['unit'])))
    return