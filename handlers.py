from config import line_bot_api, line_bot_api_blob, client, question_manager, rich_menu_manager
import asyncio
from utils.message_utils import (
    handle_rich_menu, info_hint_message, result_message, send_chat_response, chat_summary_message, send_message, send_text_message,
    question_message, SYSTEM_INSTRUCTION, text_message, progress_message, chat_message, show_loading, SYSTEM_SUMMARY_INSTRUCTION, CHAT_CATEGORY, SYSTEM_SUMMARY_AND_SCORE_INSTRUCTION,
    GAME_SYSTEM_INSTRUCTION, carousel_message
)
from utils.models import ChatSummary, ChatSummaryAndScore, SpeechAssessment, GameResponse
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
            model="gpt-4o-mini-transcribe",
            file=(f.name, f.read()),
            language=language,
        )
        return transcript_obj.text.strip()

async def handle_text_message(event):
    message: str = event.message.text.strip()
    user_id = event.source.user_id
    
    await handle_rich_menu(user_id)
    
    if not await check_user_login(event, message):
        return

    if message.startswith('/解除綁定') or message.startswith('/unlink'):
        delData(user_id)
        await send_text_message(event, "已解除綁定！\nUnlinked!")
    elif message.startswith('/魔法'):
        await send_text_message(event, "你已變成管理員\nMagic!")
        await addAdmin(user_id)
        await save_config()

user_data_enter = {}

async def check_user_login(event, message: str = None) -> bool:
    user_id = event.source.user_id
    
    if hasData(user_id):
        return True
    
    info = user_data_enter.get(user_id, [])
    if message is None:
        await send_message(event, await info_hint_message(len(info)))
        return False
    
    if message.lower() == 'back' and len(info) > 0:
        await send_message(event, await info_hint_message(len(info) - 1))
        user_data_enter[user_id] = info[:-1]
        return False
    
    if len(info) == 0:
        if not message.isdigit():
            await send_text_message(event, "輸入格式錯誤！\nFormat error!")
            return False
        try:
            option = int(message)
            if option < 1 or option > 9:
                await send_text_message(event, "輸入格式錯誤！\nFormat error!")
                return False
        except ValueError:
            await send_text_message(event, "輸入格式錯誤！\nFormat error!")
            return False
        except Exception as e:
            await send_text_message(event, "處理時發生錯誤，請稍後再試。\nAn error occurred during processing, please try again later.")
            print(e)
    elif len(info) == 1:
        pass
    elif len(info) == 2:
        if not message.isdigit():
            await send_text_message(event, "學號格式錯誤！\nFormat error!")
            return False
        elif len(message) > 8:
            await send_text_message(event, "學號格式錯誤！\nFormat error!")
            return False
    else:
        info.append(message)
        initData(user_id, info[0], info[1], info[2], info[3])
        del user_data_enter[user_id]
        await send_message(event, [
            await text_message(f"綁定完成 你好! {message}\nSuccess! Hello, {message} !"), 
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
    await handle_rich_menu(user_id)
    user_state = get_user_state(user_id)
    if not user_state:
        return
    
    await show_loading(user_id, secs=30)
    
    # 優先處理遊戲模式
    if config.get('rag_mode'):
        await handle_game_mode(event, user_id, user_state)
        return

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
        
        sub = user_state.sub
        
        if sub == -1:
            await send_text_message(event, "請選擇單元。\nPlease select a unit.")
            return
        
        question = question_manager.get_question(category, sub)
        
        try:
            message_content = await get_audio_content(event)
            if not message_content:
                await send_text_message(event, "無法獲取音訊內容，請稍後再試。\nUnable to get audio content, please try again later.")
                return
            text = await transcribe_audio(message_content, language="en")
        except Exception as e:
            await send_text_message(event, "文字轉錄發生錯誤，請稍後再試。\nAn error occurred, please try again later.")
            print(e)
            return
    
        if not text or len(text) < 1:
            await send_text_message(event, "無法獲取音訊內容，請稍後再試。\nUnable to get audio content, please try again later.")
            print('No text found in audio')
            return
        
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
        
        result: SpeechAssessment = SpeechAssessment.model_validate_json(completion.choices[0].message.content)
        result.transcript = text
        result.timestamp = time.time()
        updateHistory(user_id, f'{category}-{sub}', result)
        await send_message(event, await result_message(result, category, sub))
    except Exception as e:
        await send_text_message(event, "發生錯誤，請稍後再試。\nAn error occurred, please try again later.")
        print(e)

async def handle_game_mode(event, user_id, user_state):
    try:
        category = user_state.category
        sub = user_state.sub
        
        if not category or sub == -1:
             await send_text_message(event, "請先選擇劇本與角色。\nPlease select a scenario first.")
             return
        
        try:
            message_content = await get_audio_content(event)
            text = await transcribe_audio(message_content, language="en")
        except Exception as e:
            print("Audio error:", e)
            await send_text_message(event, "音訊處理錯誤，請稍後再試。\nAudio error.")
            return

        if not text:
            await send_text_message(event, "聽不清楚，請再說一次。\nCould not hear clearly.")
            return

        rag_config = load_rag_config(category)
        
        # 預設值
        npc_name = "The Narrator"
        persona = "A helpful guide in a mystery game."
        rag_file = f"{sub}.md" 
        
        # 讀取特定角色設定
        str_sub = str(sub)
        if str_sub in rag_config:
            npc_entry = rag_config[str_sub]
            npc_name = npc_entry.get("name", npc_name)
            persona = npc_entry.get("persona", persona)
            rag_file = npc_entry.get("file", rag_file)
        
        rag_path = os.path.join("category", "rag_docs", category, rag_file)
        if not os.path.exists(rag_path):
             # Fallback
             rag_path = os.path.join("category", "rag_docs", category, f"{sub}.md")

        context_content = await get_rag_context_v2(rag_path, query=text)

        history_key = f'{category}-{sub}'
        past_assessments = getHistory(user_id, history_key)
        history_str = ""
        if past_assessments:
            recent = past_assessments[-5:]
            for turn in recent:
                history_str += f"User: {turn.transcript}\nNPC ({npc_name}): {turn.better_ans}\n"
        
        formatted_prompt = GAME_SYSTEM_INSTRUCTION.format(
            persona=f"{npc_name}: {persona}",
            context=context_content,
            history=history_str
        )

        completion = await client.beta.chat.completions.parse(
            model="gpt-4o",
            response_format=GameResponse,
            max_completion_tokens=1024,
            temperature=0.7, 
            messages=[
                { "role": "system", "content": formatted_prompt },
                { "role": "user", "content": text }
            ],
        )

        game_res: GameResponse = GameResponse.model_validate_json(completion.choices[0].message.content)

        assessment = SpeechAssessment(
            chi_suggestion=game_res.feedback,
            eng_suggestion="", 
            score=game_res.score,
            transcript=text,
            better_ans=game_res.npc_reply,
            timestamp=time.time()
        )
        
        updateHistory(user_id, history_key, assessment)
        await send_message(event, await result_message(assessment, category, sub))

    except Exception as e:
        print(f"Game Mode Error: {e}")
        await send_text_message(event, "系統發生錯誤，請聯絡管理員。\nSystem error.")


def get_audio_duration(message_content: bytes, format: str = "m4a") -> int:
    audio_segment = AudioSegment.from_file(BytesIO(message_content), format=format)
    return len(audio_segment)

async def handle_chat(event):
    user_id = event.source.user_id
    history = getChatHistory(user_id)
    message_content = await get_audio_content(event)
    duration = get_audio_duration(message_content)
    if not message_content:
        await send_text_message(event, "無法獲取音訊內容，請稍後再試。\nUnable to get audio content, please try again later.")
        return
    try:
        text = await transcribe_audio(message_content, language="en")
    except Exception as e:
        print("Transcription error in chat:", e)
        return
    history = await send_audio_request(event, history, text, duration//1000)
    updateChatHistory(user_id, history)

async def handle_chat_summary(event):
    user_id = event.source.user_id
    history = getChatHistory(user_id)
    if not history:
        await send_text_message(event, "無法獲取對話歷史，請稍後再試。\nUnable to get chat history, please try again later.")
        return
    if len(history.questions) < 5:
        await send_text_message(event, "對話歷史不足，無法生成摘要。\nInsufficient chat history to generate summary.")
        return
    conversation = "\n".join(f"<user>{q}</user><AI>{a}</AI>" for q, a in zip(history.questions[-5:], history.answers[-5:]))
    summary = await client.responses.parse(
        model="gpt-4o",
        max_output_tokens=1024,
        temperature=0.8,
        instructions=SYSTEM_SUMMARY_INSTRUCTION,
        text_format=ChatSummary,
        input=conversation
    )
    summary = summary.output_parsed
    if not summary:
        await send_text_message(event, "無法生成對話摘要，請稍後再試。\nUnable to generate chat summary, please try again later.")
        return
    await send_message(event, await chat_summary_message(summary))


async def handle_chat_summary_and_score(event):
    user_id = event.source.user_id
    history = getChatHistory(user_id)
    if not history:
        await send_text_message(event, "無法獲取對話歷史，請稍後再試。\nUnable to get chat history, please try again later.")
        return
    if len(history.questions) < 5:
        await send_text_message(event, "對話歷史不足，無法生成摘要。\nInsufficient chat history to generate summary.")
        return
    conversation = "\n".join(f"<user>{q.split('|')[1] if '|' in q else q}</user><AI>{a}</AI>" if not q.startswith('[') else q for q, a in zip(history.questions, history.answers))
    summary = await client.responses.parse(
        model="gpt-4o",
        max_output_tokens=1024,
        temperature=0.8,
        instructions=SYSTEM_SUMMARY_AND_SCORE_INSTRUCTION,
        text_format=ChatSummaryAndScore,
        input=conversation
    )
    summary = summary.output_parsed
    if not summary:
        await send_text_message(event, "無法生成對話摘要，請稍後再試。\nUnable to generate chat summary, please try again later.")
        return
    await send_message(event, await chat_summary_message(summary))

async def switch_topic(user_id, sub: int = -1):
    history = getChatHistory(user_id)
    if not history:
        return
    history.answers.append(f"[Switch to topic {CHAT_CATEGORY[sub]}]")
    history.questions.append(f"[Switch to topic {CHAT_CATEGORY[sub]}]")
    updateChatHistory(user_id, history)

audio = {
    '0': ['ash', 'alloy', 'American 美式口音'],
    '1': ['onyx', 'nova', 'Japanese 日式口音'],
    '2': ['onyx', 'shimmer', 'Spanish 西班牙口音'],
    '3': ['ballad', 'nova', 'British 英式口音'],
    '4': ['fable', 'sage', 'Indian 印度口音']
}
async def send_audio_request(event, history, content: bytes | str, duration: int = 0):
    user_id = event.source.user_id
    
    sex = get_user_state(user_id).sex
    accent = str(get_user_state(user_id).accent)
    
    messages = []
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
    })
    try:
        completion = await client.responses.create(
            input=messages,
            model="gpt-4o",
            instructions=f'You are a helpful and friendly {audio[accent][-1]} friend to an English learner. Please have a relaxed and friendly conversation with them and help them improve their English. Only respond in English, if user speaks in Chinese, please ignore and correct them to speak in English kindly.',
            max_output_tokens=768,
            top_p=0.9,
            temperature=1.1,
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
        duration_ms = get_audio_duration(audio_output.read(), format="mp3")
        history.answers.append(completion.output_text)
        history.questions.append(f'{duration}|{content}')
        await send_chat_response(event, f"audio/{user_id}.mp3", duration_ms, history)
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
        
        # [修改] 允許 rag_test 或 enabled 列表中的單元
        if category != 'rag_test' and not isEnabled(category):
            await send_text_message(event, "該單元目前不可用。\nCurrently unavailable.")
            return
            
        sub = int(vars.get('sub', 0))
        user_state.sub = sub
        
        # 顯示題目卡片
        await send_message(event, await question_message(user_id, category, sub)) 

    elif action == 'chat':
        if not isEnabled('chat'):
            await send_text_message(event, "該單元目前不可用。\nCurrently unavailable.")
            return
        await show_loading(user_id)
        if 'lookup' in vars.keys():
            history = getChatHistory(user_id)
            if not history:
                await send_text_message(event, "無法獲取歷史紀錄，請稍後再試。\nUnable to get chat history, please try again later.")
                return
            await send_text_message(event, history.answers[-1])
            return
        elif 'summary' in vars.keys():
            await handle_chat_summary(event)
            return
        sub = int(vars.get('sub', 0))
        await switch_topic(user_id, sub)
        await send_message(event, await chat_message(user_id, sub))
        
    elif action == 'sex':
        user_state.sex = int(vars.get('sub'))
        await send_text_message(event, f"成功將語音設為 {'男性' if user_state.sex == 0 else '女性'}\nSuccessfully set voice to {'Male' if user_state.sex == 0 else 'Female'}")
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
        
        is_rag = config.get('rag_mode', False)
        if not isResponse(category) and not is_rag:
            await send_text_message(event, "該單元目前不提供回饋。\nCurrently unavailable.")
            return
        await send_message(event, await result_message(result[-1], category, sub))
        
    elif action == 'switch':
        alias = vars.get('to')
        if alias in ['admin'] and not isAdmin(user_id):
            await send_text_message(event, '無權限！\nNo permission!')
            return
        
        # RAG 模式下的選單切換邏輯
        is_rag = config.get('rag_mode', False)
        if alias == 'menu':
            if is_rag:
                alias = 'menu_game'
        elif alias == 'menu_game':
            if not is_rag:
                alias = 'menu'
        
        if alias not in ['rag_test'] and alias in ['pretest', 'posttest', 'ex1', 'ex2', 'ex3', 'ex4', 'ex5', 'ex6', 'chat'] and not isEnabled(alias):
            await send_text_message(event, "該單元目前不可用。\nCurrently unavailable.")
            return
        
        user_state.category = alias.split('-')[0]
        
        rich_menu_id = get_rich_menu_id(alias)
        if rich_menu_id:
            await rich_menu_manager.link_rich_menu_to_user(user_id, rich_menu_id)
        
        # 自動彈出選單
        if question_manager.has_question(user_state.category) and alias not in ['chat', 'admin']:
            await send_message(event, await carousel_message(user_id, user_state.category, 0)) # 從第一頁開始
        else:
            if alias not in ['chat', 'admin', 'menu', 'menu_game']:
                 await send_text_message(event, f"已切換至 {alias}。\nSwitched to {alias}.")

    elif action == 'progress':
        await send_message(event, await progress_message(user_id))
    elif action == 'enabled':
        alias = vars.get('alias')
        if isEnabled(alias):
            removeEnabled(alias)
        else:
            addEnabled(alias)
        await save_config()
        await send_text_message(event, f'已{"啟用" if isEnabled(alias) else "停用"} {alias.capitalize()}!\n{alias.capitalize()} {"enabled" if isEnabled(alias) else "disabled"}!')
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
        await send_text_message(event, f'已{"開啟" if isResponse(alias) else "關閉"} {alias.capitalize()} 回饋!\n{alias.capitalize()} feedback {"enabled" if isResponse(alias) else "disabled"}!')
        await question_manager.save_category(alias)
    elif action == 'reload':
        question_manager.load_questions()
        await send_text_message(event, '已重新載入問題！\nQuestions reloaded!')
    elif action == 'save':
        await save_all()
        await send_text_message(event, '儲存成功！\nSave successful!')