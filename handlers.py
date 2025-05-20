from config import line_bot_api, line_bot_api_blob, client, question_manager, rich_menu_manager
import asyncio
from utils.message_utils import (
    handle_rich_menu, info_hint_message, result_message, send_chat_response, send_message, send_text_message,
    question_message, SYSTEM_INSTRUCTION, text_message, progress_message, chat_message, show_loading
)
from utils.models import SpeechAssessment
from utils.file_utils import *
import tempfile
import time
import base64
from pydub import AudioSegment
from io import BytesIO
import os

async def get_audio_content(event):
    result = await line_bot_api_blob.get_message_content_transcoding_by_message_id(event.message.id)
    while result.status == 'processing':
        await asyncio.sleep(1)
        result = await line_bot_api_blob.get_message_content_transcoding_by_message_id(event.message.id)
    return await line_bot_api_blob.get_message_content(event.message.id)

def convert_m4a_to_mp3_base64(message_content: bytes) -> str:
    m4a_file = BytesIO(message_content)
    audio = AudioSegment.from_file(m4a_file, format="m4a")
    mp3_io = BytesIO()
    audio.export(mp3_io, format="mp3")
    mp3_bytes = mp3_io.getvalue()
    return base64.b64encode(mp3_bytes).decode('utf-8')

async def transcribe_audio(message_content: bytes, language: str = "en") -> str:
    with tempfile.NamedTemporaryFile(suffix=".m4a", delete=True) as f:
        f.write(message_content)
        f.seek(0)
        f.flush()
        transcript_obj = await client.audio.transcriptions.create(
            model="gpt-4o-mini-transcribe",#"whisper-1",
            file=(f.name, f.read()),
            language=language,
        )
        return transcript_obj.text.strip()

async def handle_text_message(event):
    # 獲取使用者傳來的文字訊息並移除前後空白
    message: str = event.message.text.strip()
    # 獲取使用者 ID
    user_id = event.source.user_id
    
    await handle_rich_menu(user_id)
    
    # 檢查使用者是否登入，若未登入則結束
    if not await check_user_login(event, message):
        return

    # 若訊息以「/」開頭，進行指令處理
    if message.startswith('/解除綁定') or message.startswith('/unlink'):
        delData(user_id)
        await send_text_message(event, "已解除綁定！\nUnlinked!")
    elif message.startswith('/魔法'):
        await send_text_message(event, "你已變成管理員\nMagic!")
        await addAdmin(user_id)
        await save_config()

user_data_enter = {}

async def check_user_login(event, message: str = None) -> bool:
    # 檢查使用者是否已登入或已存有資料
    user_id = event.source.user_id
    
    if hasData(user_id):
        return True
    
    # 若無使用者資料，開始進行資料綁定流程
    info = user_data_enter.get(user_id, [])
    if message is None:
        # 若沒有訊息，提示使用者提供所需資料
        await send_message(event, await info_hint_message(len(info)))
        return False
    
    if message.lower() == 'back' and len(info) > 0:
        await send_message(event, await info_hint_message(len(info) - 1))
        user_data_enter[user_id] = info[:-1]
        return False
    
    # 以下依序確認使用者輸入格式
    # 上課時段
    if len(info) == 0:
        if not message.isdigit():
            await send_text_message(event, "格式錯誤！\nFormat error!")
            return False
        try:
            option = int(message)
            if option < 1 or option > 4:
                await send_text_message(event, "輸入格式錯誤！\nFormat error!")
                return False
        except ValueError:
            await send_text_message(event, "輸入格式錯誤！\nFormat error!")
            return False
        except Exception as e:
            await send_text_message(event, "處理時發生錯誤，請稍後再試。\nAn error occurred during processing, please try again later.")
            print(e)
    # 系級
    elif len(info) == 1:
        pass
    # 學號
    elif len(info) == 2:
        if not message.isdigit():
            await send_text_message(event, "學號格式錯誤！\nFormat error!")
            return False
        elif len(message) > 8:
            await send_text_message(event, "學號格式錯誤！\nFormat error!")
            return False
    # 姓名
    else:
        # 綁定完成後儲存資料並提示使用者綁定成功
        info.append(message)
        initData(user_id, info[0], info[1], info[2], info[3])
        del user_data_enter[user_id]
        await send_message(event, [
            await text_message(f"綁定完成 你好! {message}\nSuccess! Hello, {message} !"), 
        ])
        return True

    # 保存目前階段的資料以繼續下一步
    info.append(message)
    user_data_enter[user_id] = info
    await send_message(event, await info_hint_message(len(info)))
    return True

async def handle_audio_message(event):
    # 確認使用者登入狀態，若未登入則結束
    if not await check_user_login(event):
        return
    
    user_id = event.source.user_id
    await handle_rich_menu(user_id)
    user_state = get_user_state(user_id)
    # 檢查使用者的狀態資料是否存在
    if not user_state:
        return
    
    await show_loading(user_id, secs=30)
    try:
        text = None
        category = user_state.category
        
        if category in ['chat', 'sex', 'accent', 'audio']:
            if not isEnabled('chat'):
                await send_text_message(event, "該單元目前不可用。\nCurrently unavailable.")
                return
            await handle_chat(event)
            return
        
        if not category or not question_manager.has_question(category):
            return 
        
        # 獲取使用者的練習單元和題目
        sub = user_state.sub
        question = question_manager.get_question(category, sub)
        
        try:
            message_content = await get_audio_content(event)
            if not message_content:
                await send_text_message(event, "無法獲取音訊內容，請稍後再試。\nUnable to get audio content, please try again later.")
                return
            # 使用 Whisper 進行音訊轉錄
            text = await transcribe_audio(message_content, language="en")
        except Exception as e:
            await send_text_message(event, "文字轉錄發生錯誤，請稍後再試。\nAn error occurred, please try again later.")
            print(e)
            return
    
        if not text or len(text) < 1:
            await send_text_message(event, "無法獲取音訊內容，請稍後再試。\nUnable to get audio content, please try again later.")
            print('No text found in audio')
            return
        
        # 使用 GPT 模型進行回應分析與評估
        completion = await client.beta.chat.completions.parse(
            model="gpt-4o",
            response_format=SpeechAssessment,
            max_completion_tokens=2048,
            temperature=1,
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_INSTRUCTION,
                },
                {
                    "role": "user",
                    "content": f"<question>{question.text}</question>" \
                               f"{'<standard>'+question.assessment_standard.replace('\n','').strip()+'</standard>' if question.assessment_standard else ''}" \
                               f"<userAnswer>{text}</userAnswer>" \
                               f"{f'<maxScore>{question.max_score}</maxScore>' if question.max_score else ''}",
                }
            ],
        )
        
        # 將分析結果轉換為 SpeechAssessment 物件並儲存歷史紀錄
        result: SpeechAssessment = SpeechAssessment.model_validate_json(completion.choices[0].message.content)
        result.transcript = text
        result.timestamp = time.time()
        updateHistory(user_id, f'{category}-{sub}', result)
        await send_message(event, await result_message(result, category, sub))
    except Exception as e:
        await send_text_message(event, "發生錯誤，請稍後再試。\nAn error occurred, please try again later.")
        print(e)

async def handle_chat(event):
    user_id = event.source.user_id
    user_state = get_user_state(user_id)
    if user_state.sub < 0 or user_state.sub > 4:
        await send_text_message(event, "請先選擇主題。\nPlease select a subject first.")
        return
    history = getChatHistory(user_id)
    message_content = await get_audio_content(event)
    if not message_content:
        await send_text_message(event, "無法獲取音訊內容，請稍後再試。\nUnable to get audio content, please try again later.")
        return
    try:
        # Transcribe audio for chat history
        text = await transcribe_audio(message_content, language="en")
    except Exception as e:
        print("Transcription error in chat:", e)
    history = await send_audio_request(event, history, text)
    updateChatHistory(user_id, history)

audio = {
    '0': ['ash', 'alloy', 'American 美式口音'],
    '1': ['onyx', 'nova', 'Japanese 日式口音'],
    '2': ['onyx', 'shimmer', 'Spanish 西班牙口音'],
    '3': ['ballad', 'nova', 'British 英式口音'],
    '4': ['fable', 'sage', 'Indian 印度口音']
}
async def send_audio_request(event, history, content: bytes | str):
    user_id = event.source.user_id
    
    sex = get_user_state(user_id).sex
    accent = str(get_user_state(user_id).accent)
    
    messages = []
    # 取出前三筆對話 context（Q&A），由舊到新
    num_context = min(3, len(history.questions), len(history.answers))
    for i in range(-num_context, 0):
        messages.append({
            'role': 'user',
            'content': history.questions[i],
        })
        messages.append({
            'role': 'assistant',
            'content': history.answers[i],
        })
    messages.append({
        'role': 'user',
        'content': content,
        # 'content': [
        #     { 'type': "input_audio", 'input_audio': { 'data': convert_m4a_to_mp3_base64(content), 'format': "mp3" }} if isinstance(content, bytes) else { 'type': "text", 'text': content }
        # ],
    })
    try:
        completion = await client.responses.create(
            input=messages,
            model="gpt-4o",
            instructions=f'You are a helpful and friendly {audio[accent][-1]} friend to an English learner. Please have a relaxed and friendly conversation with them and help them improve their English. Only respond in English, if user speaks in Chinese, please ignore and correct them to speak in English strongly and kindly.',
            max_output_tokens=2048,
            temperature=0.8,
        )
        audio_output = await client.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice=audio[accent][sex],
            response_format='mp3',
            speed=0.8,
            instructions=f'''Accent: Very strong {audio[accent][-1]} accent.
                Identity: {audio[accent][-1]} speaker.
                Tone: Friendly.
                Emotion: Warm and supportive.
                Only respond in accented English. If the user speaks in Chinese, please ignore and correct them to speak in English strongly and kindly.''',
            input=completion.output_text
        )
        try:
            os.makedirs(f"templates/audio", exist_ok=True)
            audio_output.write_to_file(f"templates/audio/{user_id}.mp3")
        except Exception as e:
            print("Error saving audio file:", e)
        audio_segment = AudioSegment.from_file(BytesIO(audio_output.read()), format="mp3")
        duration_ms = len(audio_segment)
        history.answers.append(completion.output_text)
        history.questions.append(content)
        await send_chat_response(event, f"audio/{user_id}.mp3", duration_ms)
    except Exception as e:
        print("Error in audio request:", e)
        await send_text_message(event, "發生錯誤，請稍後再試。\nAn error occurred, please try again later.")
    return history

async def handle_postback(event):
    if not await check_user_login(event):
        return
    user_id = event.source.user_id
    await handle_rich_menu(user_id)
    user_state = get_user_state(user_id)
    data: str = event.postback.data
    vars = {sep.split('=')[0]: sep.split('=')[1] for sep in data.split('&')}
    action = vars.get('action')
    if action == 'record':
        category = user_state.category
        if not isEnabled(category):
            await send_text_message(event, "該單元目前不可用。\nCurrently unavailable.")
            return
        sub = int(vars.get('sub', 0))
        user_state.sub = sub
        # if not getHistory(user_id, f'{category}-{sub}') or 'force' in vars.keys():
        await send_message(event, await question_message(user_id, category, sub)) 
        # else:
        #     await send_message(event, await result_message(getHistory(user_id, f'{category}-{sub}'), category, sub))
    elif action == 'chat':
        if not isEnabled('chat'):
            await send_text_message(event, "該單元目前不可用。\nCurrently unavailable.")
            return
        await show_loading(user_id)
        sub = int(vars.get('sub', -1))
        user_state.sub = sub
        if 'question' in vars.keys():
            history = getChatHistory(user_id)
            history = await send_audio_request(event, history, vars.get('question'))
            updateChatHistory(user_id, history)
            return
        elif 'lookup' in vars.keys():
            history = getChatHistory(user_id)
            if not history:
                await send_text_message(event, "無法獲取歷史紀錄，請稍後再試。\nUnable to get chat history, please try again later.")
                return
            await send_text_message(event, f"{history.answers[-1]}")
            return
        await send_message(event, await chat_message(user_id, sub))
    elif action == 'sex':
        user_state.sex = int(vars.get('sub'))
        await send_text_message(event, f"成功將語音設為 {"男性" if user_state.sex == 0 else "女性"}\nSuccessfully set voice to {"Male" if user_state.sex == 0 else "Female"}")
    elif action == 'accent':
        user_state.accent = int(vars.get('sub'))
        await send_text_message(event, f"成功將口音設為 Successfully set accent to:\n{audio[str(user_state.accent)][-1]}")
    elif action == 'result':
        category = vars.get('category', user_state.category)
        sub = int(vars.get('sub', 0))
        result = getHistory(user_id, f'{category}-{sub}')
        if not result:
            await send_text_message(event, f'Q{sub+1} 查無紀錄！\nNo history found in Q{sub+1}!')
            return
        if not isEnabled(category):
            await send_text_message(event, "該單元目前不可用。\nCurrently unavailable.")
            return
        if not isResponse(category):
            await send_text_message(event, "該單元目前不提供回饋。\nCurrently unavailable.")
            return
        await send_message(event, await result_message(result[-1], category, sub))
    elif action == 'switch':
        alias = vars.get('to')
        if alias in ['admin'] and not isAdmin(user_id):
            await send_text_message(event, '無權限！\nNo permission!')
            return
        if alias in ['pretest', 'posttest', 'ex1', 'ex2', 'ex3', 'chat'] and not isEnabled(alias):
            await send_text_message(event, "該單元目前不可用。\nCurrently unavailable.")
            return
        user_state.category = alias.split('-')[0]
        await rich_menu_manager.link_rich_menu_to_user(user_id, get_rich_menu_id(alias))
    elif action == 'progress':
        await send_message(event, await progress_message(user_id))
    elif action == 'enabled':
        alias = vars.get('alias')
        if isEnabled(alias):
            removeEnabled(alias)
        else:
            addEnabled(alias)
        await save_config()
        await send_text_message(event, f'已{"啟用" if isEnabled(alias) else "停用"} {alias}！\n{alias} {"enabled" if isEnabled(alias) else "disabled"}!')
        if alias in ['chat']:
            return
        await question_manager.save_category(alias)
    elif action == 'respond':
        alias = vars.get('alias')
        if isResponse(alias):
            removeResponse(alias)
        else:
            addResponse(alias)
        await save_config()
        await send_text_message(event, f'已{"開啟" if isResponse(alias) else "關閉"} {alias} 回饋！\n{alias} feedback {"enabled" if isResponse(alias) else "disabled"}!')
        await question_manager.save_category(alias)
    elif action == 'reload':
        question_manager.load_questions()
        await send_text_message(event, '已重新載入問題！\nQuestions reloaded!')
    elif action == 'save':
        await save_all()
        await send_text_message(event, '儲存成功！\nSave successful!')
