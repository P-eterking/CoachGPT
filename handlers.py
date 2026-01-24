from config import line_bot_api, line_bot_api_blob, client, question_manager, rich_menu_manager
import asyncio
from utils.message_utils import (
    handle_rich_menu, info_hint_message, result_message, send_chat_response, 
    chat_summary_message, send_message, send_text_message,
    question_message, SYSTEM_INSTRUCTION, text_message, progress_message, 
    chat_message, show_loading, SYSTEM_SUMMARY_INSTRUCTION, CHAT_CATEGORY, 
    SYSTEM_SUMMARY_AND_SCORE_INSTRUCTION, GAME_SYSTEM_INSTRUCTION, carousel_message,
    # 遊戲訊息
    game_prologue_message, game_level_intro_message, game_questions_carousel,
    game_score_message, game_theme_select_message, game_npc_select_message,
    game_level_select_message,
    # NPC 相關訊息
    game_npc_card_message, game_npc_chat_response_message,
    NPC_CHAT_SYSTEM_INSTRUCTION, QUESTION_ANSWER_SYSTEM_INSTRUCTION
)
from utils.models import (
    ChatSummary, ChatSummaryAndScore, SpeechAssessment, GameResponse,
    # 回應模型
    NPCChatResponse, QuestionAnswerResponse, GameInteractionLog
)
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
        # 檢查是否在 NPC 對話模式
        if user_state.in_npc_chat and user_state.game_theme and user_state.game_npc >= 0:
            await handle_npc_chat(event, user_id, user_state)
            return
        
        # 檢查使用者是否在新遊戲模式中且已選擇題目
        if user_state.game_theme and user_state.game_level >= 0 and user_state.game_question >= 0:
            await handle_game_answer(event, user_id, user_state)
            return
        # 處理舊的 rag_test 類別
        elif user_state.category == 'rag_test' and user_state.sub >= 0:
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
                               f"{'<standard>'+question.assessment_standard.replace(chr(10),'').strip()+'</standard>' if question.assessment_standard else ''}" \
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

# 舊版: 保留以維持向後相容性
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

# ========== NPC 對話處理 (不計分) ==========
async def handle_npc_chat(event, user_id, user_state):
    """處理 NPC 對話 (不計分，僅劇情互動)"""
    try:
        theme_id = user_state.game_theme
        npc_idx = user_state.game_npc
        
        if not theme_id or npc_idx < 0:
            await send_text_message(event, "請先選擇角色。\nPlease select a character first.")
            return
        
        # 取得音訊並轉錄
        try:
            message_content = await get_audio_content(event)
            text = await transcribe_audio(message_content, language="en")
        except Exception as e:
            print("Audio error:", e)
            await send_text_message(event, "音訊處理錯誤，請稍後再試。\nAudio processing error.")
            return

        if not text:
            await send_text_message(event, "聽不清楚，請再說一次。\nCould not hear clearly, please try again.")
            return

        # 取得 NPC 資訊
        npc_info = get_game_npc_info(theme_id, npc_idx)
        if not npc_info:
            npc_info = {
                "name": "The Narrator",
                "persona": "A helpful guide.",
                "file": "narrator.md"
            }
        
        # 取得 RAG 上下文
        rag_path = os.path.join("category", "rag_docs", theme_id, npc_info["file"])
        if not os.path.exists(rag_path):
            rag_path = os.path.join("category", "rag_docs", theme_id)
        
        context_content = await get_rag_context_v2(rag_path, query=text)
        
        # 取得對話歷史
        history_key = f'{theme_id}-npc-{npc_idx}'
        past_assessments = getHistory(user_id, history_key)
        history_str = ""
        if past_assessments:
            recent = past_assessments[-5:]
            for turn in recent:
                history_str += f"User: {turn.transcript}\nNPC ({npc_info['name']}): {turn.better_ans}\n"
        
        # 建構提示詞
        formatted_prompt = NPC_CHAT_SYSTEM_INSTRUCTION.format(
            persona=f"{npc_info['name']}: {npc_info['persona']}",
            context=context_content,
            history=history_str
        )

        # 取得 AI 回應
        completion = await client.beta.chat.completions.parse(
            model="gpt-4o",
            response_format=NPCChatResponse,
            max_completion_tokens=512,
            temperature=0.7, 
            messages=[
                { "role": "system", "content": formatted_prompt },
                { "role": "user", "content": text }
            ],
        )

        npc_res: NPCChatResponse = NPCChatResponse.model_validate_json(completion.choices[0].message.content)

        # 儲存對話歷史 (使用 SpeechAssessment 格式，score=0 表示非計分)
        assessment = SpeechAssessment(
            chi_suggestion=npc_res.feedback,
            eng_suggestion="", 
            score=0,  # NPC 對話不計分
            transcript=text,
            better_ans=npc_res.npc_reply,
            timestamp=time.time()
        )
        
        updateHistory(user_id, history_key, assessment)
        
        # 儲存互動紀錄
        interaction_log = GameInteractionLog(
            user_id=user_id,
            timestamp=time.time(),
            interaction_type='npc_chat',
            theme_id=theme_id,
            npc_idx=npc_idx,
            npc_name=npc_info['name'],
            user_transcript=text,
            ai_response=npc_res.npc_reply,
            feedback=npc_res.feedback
        )
        await save_interaction_log(interaction_log)
        
        # 發送回應訊息
        await send_message(event, await game_npc_chat_response_message(
            npc_info['name'],
            npc_res.npc_reply,
            npc_res.feedback,
            npc_res.is_english
        ))

    except Exception as e:
        print(f"NPC Chat Error: {e}")
        await send_text_message(event, "系統發生錯誤，請聯絡管理員。\nSystem error, please contact admin.")

# 使用新的 QuestionAnswerResponse 模型
async def handle_game_answer(event, user_id, user_state):
    """處理遊戲題目的語音回答"""
    try:
        theme_id = user_state.game_theme
        level_idx = user_state.game_level
        question_idx = user_state.game_question
        npc_idx = user_state.game_npc
        
        if not theme_id or level_idx < 0 or question_idx < 0:
            await send_text_message(event, "請先選擇題目。\nPlease select a question first.")
            return
        
        # 取得音訊並轉錄
        try:
            message_content = await get_audio_content(event)
            text = await transcribe_audio(message_content, language="en")
        except Exception as e:
            print("Audio error:", e)
            await send_text_message(event, "音訊處理錯誤，請稍後再試。\nAudio processing error.")
            return

        if not text:
            await send_text_message(event, "聽不清楚，請再說一次。\nCould not hear clearly, please try again.")
            return

        # 取得題目資訊
        level_info = get_game_level_info(theme_id, level_idx)
        question_text = ""
        reference_answer = ""
        if level_info and question_idx < len(level_info.get('questions', [])):
            q_data = level_info['questions'][question_idx]
            question_text = q_data['text']
            reference_answer = q_data.get('reference_answer', '')
        
        # 使用新的題目回答系統指令
        formatted_prompt = QUESTION_ANSWER_SYSTEM_INSTRUCTION.format(
            question=question_text,
            reference_answer=reference_answer if reference_answer else "No reference answer provided.",
            user_answer=text
        )

        # 取得 AI 回應
        completion = await client.beta.chat.completions.parse(
            model="gpt-4o",
            response_format=QuestionAnswerResponse,
            max_completion_tokens=512,
            temperature=0.7, 
            messages=[
                { "role": "system", "content": formatted_prompt },
                { "role": "user", "content": text }
            ],
        )

        answer_res: QuestionAnswerResponse = QuestionAnswerResponse.model_validate_json(completion.choices[0].message.content)

        # 儲存評估結果
        assessment = SpeechAssessment(
            chi_suggestion=answer_res.feedback_chi,
            eng_suggestion=answer_res.feedback_eng, 
            score=answer_res.score,
            transcript=text,
            better_ans=answer_res.reference_comparison,
            timestamp=time.time()
        )
        
        history_key = f'{theme_id}-{level_idx}-{question_idx}'
        updateHistory(user_id, history_key, assessment)
        
        # 更新遊戲分數
        is_new_high, theme_total = update_game_score(
            user_id, theme_id, level_idx, question_idx, answer_res.score
        )
        
        # 儲存互動紀錄
        interaction_log = GameInteractionLog(
            user_id=user_id,
            timestamp=time.time(),
            interaction_type='question_answer',
            theme_id=theme_id,
            level_idx=level_idx,
            question_idx=question_idx,
            user_transcript=text,
            ai_response=answer_res.reference_comparison,
            score=answer_res.score,
            feedback=f"{answer_res.feedback_chi}\n{answer_res.feedback_eng}"
        )
        await save_interaction_log(interaction_log)
        
        # 重置題目狀態 (退出答題模式)
        user_state.game_question = -1
        
        # 發送結果訊息
        await send_message(event, await game_score_message(
            user_id, theme_id, level_idx, question_idx,
            answer_res.score, is_new_high,
            feedback_chi=answer_res.feedback_chi,
            feedback_eng=answer_res.feedback_eng
        ))

    except Exception as e:
        print(f"Game Answer Error: {e}")
        await send_text_message(event, "系統發生錯誤，請聯絡管理員。\nSystem error, please contact admin.")


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


async def send_audio_request(event, history, text, secs):
    from utils.models import ChatHistory
    from openai import AsyncOpenAI
    import uuid
    import aiofiles
    
    user_id = event.source.user_id
    user = getUser(user_id)
    if not history:
        history = ChatHistory()
    
    history.questions.append(text)
    
    messages = [
        {
            "role": "system",
            "content": f"""You are a friendly and helpful AI English-speaking coach for college students who are non-native speakers in Taiwan. 
            Their names are {user.name}.
            Your job is to engage in natural, supportive conversations that help them practice speaking.

            Style: Speak in short, friendly sentences like a native English speaker. Use casual but clear language.
            When correcting grammar:
            - If there's a mistake, gently correct it while maintaining conversation flow
            - For severe errors, provide the correction naturally in your response
            
            Keep responses under 60 words unless explaining something complex. Do not use bullet points, markdown, or formatted text - just natural conversational language.

            If asked about topics you don't know, just say you're not sure. Don't mention being an AI assistant.
            """,
        }
    ]
    
    for q, a in zip(history.questions, history.answers):
        messages.append({"role": "user", "content": q})
        messages.append({"role": "assistant", "content": a})
    messages.append({"role": "user", "content": text})
    
    completion = await client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        max_completion_tokens=512,
        temperature=0.8,
    )
    
    reply = completion.choices[0].message.content
    history.answers.append(reply)
    
    # Generate TTS
    tts_response = await client.audio.speech.create(
        model="gpt-4o-mini-tts",
        voice="nova",
        input=reply,
    )
    
    filename = f"audio/{uuid.uuid4()}.mp3"
    os.makedirs("templates/audio", exist_ok=True)
    async with aiofiles.open(f"templates/{filename}", 'wb') as f:
        await f.write(tts_response.content)
    
    # Calculate duration
    audio = AudioSegment.from_file(f"templates/{filename}", format="mp3")
    duration = len(audio)
    
    await send_chat_response(event, filename, duration, history)
    return history


async def handle_postback(event):
    user_id = event.source.user_id
    
    await handle_rich_menu(user_id)
    
    if not await check_user_login(event):
        return
    
    user_state = get_user_state(user_id)
    if not user_state:
        return
    
    data = event.postback.data
    params = dict(p.split('=') for p in data.split('&'))
    action = params.get('action')
    vars = {k: v for k, v in params.items() if k != 'action'}
    
    if action == 'chat':
        if vars.get('summary'):
            await handle_chat_summary(event)
        else:
            history = getChatHistory(user_id)
            if history and len(history.answers) > 0:
                await send_text_message(event, history.answers[-1])
    elif action == 'sub':
        sub = int(vars.get('sub'))
        user_state.sub = sub
        await send_message(event, await chat_message(user_id, sub))
    elif action == 'record':
        sub = int(vars.get('sub'))
        user_state.sub = sub
        await send_message(event, await question_message(user_id, user_state.category, sub))
    elif action == 'carousel':
        page = int(vars.get('page', 0))
        await send_message(event, await carousel_message(user_id, user_state.category, page))
    elif action == 'last':
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
        # 切換選單時重置 NPC 對話狀態
        user_state.in_npc_chat = False
        
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
        clear_game_theme_cache()
        await send_text_message(event, '已重新載入問題與主題！\nQuestions and themes reloaded!')
    elif action == 'save':
        await save_all()
        await send_text_message(event, '儲存成功！\nSave successful!')
    
    # ========== 遊戲動作 ==========
    elif action == 'game_themes':
        # 顯示主題選擇
        await send_message(event, await game_theme_select_message())
    
    elif action == 'game_theme':
        # 進入主題 - 顯示前情提要
        theme_id = vars.get('theme')
        if not theme_id:
            await send_text_message(event, "未指定主題。\nTheme not specified.")
            return
        
        user_state.game_theme = theme_id
        user_state.game_level = -1
        user_state.game_question = -1
        user_state.in_npc_chat = False  # 重置 NPC 對話狀態
        
        # 顯示前情提要並切換到主題選單
        theme_menu_id = get_rich_menu_id(f'game_{theme_id}')
        if theme_menu_id:
            await rich_menu_manager.link_rich_menu_to_user(user_id, theme_menu_id)
        
        # game_prologue_message 現在回傳列表 (可能包含影片)
        messages = await game_prologue_message(theme_id)
        await send_message(event, messages)
    
    elif action == 'game_npcs':
        # 顯示當前主題的NPC選擇
        theme_id = vars.get('theme', user_state.game_theme)
        if not theme_id:
            await send_text_message(event, "請先選擇主題。\nPlease select a theme first.")
            return
        await send_message(event, await game_npc_select_message(theme_id, user_id))
    
    elif action == 'game_npc':
        # 選擇要對話的NPC
        theme_id = vars.get('theme', user_state.game_theme)
        npc_idx = int(vars.get('npc', 0))
        
        if not theme_id:
            await send_text_message(event, "請先選擇主題。\nPlease select a theme first.")
            return
        
        user_state.game_theme = theme_id
        user_state.game_npc = npc_idx
        user_state.game_question = -1  # 確保不在答題模式
        user_state.in_npc_chat = True  # 設置 NPC 對話模式
        
        # 顯示 NPC 卡片而非純文字
        await send_message(event, await game_npc_card_message(theme_id, npc_idx))
    
    elif action == 'game_levels':
        # 顯示關卡選擇
        theme_id = vars.get('theme', user_state.game_theme)
        if not theme_id:
            await send_text_message(event, "請先選擇主題。\nPlease select a theme first.")
            return
        await send_message(event, await game_level_select_message(theme_id, user_id))
    
    elif action == 'game_level':
        # 進入關卡 - 顯示影片介紹
        theme_id = vars.get('theme', user_state.game_theme)
        level_idx = int(vars.get('level', 0))
        
        if not theme_id:
            await send_text_message(event, "請先選擇主題。\nPlease select a theme first.")
            return
        
        user_state.game_theme = theme_id
        user_state.game_level = level_idx
        user_state.game_question = -1
        user_state.in_npc_chat = False  # 退出 NPC 對話模式
        
        messages = await game_level_intro_message(theme_id, level_idx, user_id)
        await send_message(event, messages)
    
    elif action == 'game_questions':
        # 顯示當前關卡的題目卡片
        theme_id = vars.get('theme', user_state.game_theme)
        level_idx = int(vars.get('level', user_state.game_level))
        
        if not theme_id or level_idx < 0:
            await send_text_message(event, "請先選擇關卡。\nPlease select a level first.")
            return
        
        await send_message(event, await game_questions_carousel(theme_id, level_idx, user_id))
    
    elif action == 'game_answer':
        # 選擇要回答的題目
        theme_id = vars.get('theme', user_state.game_theme)
        level_idx = int(vars.get('level', user_state.game_level))
        question_idx = int(vars.get('question', 0))
        
        if not theme_id or level_idx < 0:
            await send_text_message(event, "請先選擇關卡。\nPlease select a level first.")
            return
        
        user_state.game_theme = theme_id
        user_state.game_level = level_idx
        user_state.game_question = question_idx
        user_state.in_npc_chat = False  # 確保退出 NPC 對話模式
        
        # 取得題目文字
        level_info = get_game_level_info(theme_id, level_idx)
        if level_info and question_idx < len(level_info.get('questions', [])):
            q_text = level_info['questions'][question_idx]['text']
            await send_text_message(event, f"Q{question_idx + 1}: {q_text}\n\n請發送語音訊息作答！\nSend a voice message with your answer!")
        else:
            await send_text_message(event, "請發送語音訊息作答！\nSend a voice message with your answer!")
    
    elif action == 'game_score':
        # 顯示當前主題分數
        theme_id = vars.get('theme', user_state.game_theme)
        if not theme_id:
            await send_text_message(event, "請先選擇主題。\nPlease select a theme first.")
            return
        
        progress = get_user_game_progress(user_id, theme_id)
        await send_text_message(event, 
            f"主題分數 Theme Score: {progress['total_score']}/{progress['max_score']}\n"
            f"已回答題數 Questions Answered: {progress['questions_answered']}\n"
            f"已完成關卡 Levels Completed: {progress['levels_completed']}"
        )