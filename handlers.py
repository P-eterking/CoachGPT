from config import line_bot_api, line_bot_api_blob, client, question_manager, rich_menu_manager
import asyncio
from utils.message_utils import (
    handle_rich_menu, info_hint_message, result_message, send_chat_response, 
    chat_summary_message, send_message, send_text_message,
    question_message, SYSTEM_INSTRUCTION, text_message, progress_message, 
    chat_message, show_loading, SYSTEM_SUMMARY_INSTRUCTION, CHAT_CATEGORY, 
    SYSTEM_SUMMARY_AND_SCORE_INSTRUCTION, GAME_SYSTEM_INSTRUCTION, carousel_message,
    # Game messages
    game_prologue_message, game_level_intro_message, game_questions_carousel,
    game_score_message, game_theme_select_message, game_npc_select_message,
    game_level_select_message, game_current_questions_message,
    # NPC related messages
    game_npc_card_message, game_npc_chat_response_message,
    NPC_CHAT_QUICK_RESPONSE, NPC_CHAT_EVALUATION,
    game_npc_evaluation_message, QUESTION_ANSWER_SYSTEM_INSTRUCTION,
    # Improvement hint related
    IMPROVEMENT_HINT_SYSTEM_INSTRUCTION, game_improvement_hint_message,
    # New messages for service4 enhancements
    game_rules_instruction_message, progress_select_message,
    game_progress_message, other_progress_message,
    # Pretest / Posttest detailed progress (split by section)
    pretest_progress_message, posttest_progress_message,
    # Game lobby info messages
    game_story_message, game_characters_message, game_structure_message,
    # Helper for building tiered reference answer prompt section
    build_reference_answers_section,
    # Question card with image for service4 game_answer action
    game_answer_card_message,
    # new_test single question card (pretest1 / posttest1)
    new_test_question_message,
    # NPC voice response messages (item 4)
    game_npc_voice_response_messages, game_npc_text_card_message,
)
from utils.models import (
    ChatSummary, ChatSummaryAndScore, SpeechAssessment, GameResponse,
    # Response models
    NPCChatResponse, NPCChatEvaluation, QuestionAnswerResponse, GameInteractionLog,
    ImprovementHintResponse
)
from utils.file_utils import *
from utils.file_utils import (
    get_new_test_question,
    set_last_npc_reply, get_last_npc_reply,
    should_show_feedback,
    get_enabled_category_for_alias,
)
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


async def generate_npc_tts(npc_reply: str, voice: str = "onyx") -> tuple:
    """產生 NPC 語音 TTS，回傳 (相對於 templates/ 的路徑, 毫秒長度)。
    Generate NPC TTS audio and return (path relative to templates/, duration_ms).

    Args:
        npc_reply: NPC 回覆文字
        voice: TTS 聲音 (預設 onyx，具角色感)
    """
    import uuid
    import aiofiles

    tts_response = await client.audio.speech.create(
        model="gpt-4o-mini-tts",
        voice=voice,
        input=npc_reply,
    )

    filename = f"audio/{uuid.uuid4()}.mp3"
    os.makedirs("templates/audio", exist_ok=True)
    async with aiofiles.open(f"templates/{filename}", 'wb') as f:
        await f.write(tts_response.content)

    audio_seg = AudioSegment.from_file(f"templates/{filename}", format="mp3")
    duration = len(audio_seg)

    return filename, duration

async def transcribe_audio(message_content: bytes, language: str = "en") -> str:
    """
    Transcribe audio to text
    language parameter specifies the transcription language, default is English
    IMPORTANT: Do NOT translate, only transcribe in the specified language
    """
    with tempfile.NamedTemporaryFile(suffix=".m4a", delete=True) as f:
        f.write(message_content)
        f.seek(0)
        f.flush()
        
        # Use language parameter to force English transcription without translation
        transcript_obj = await client.audio.transcriptions.create(
            model="gpt-4o-mini-transcribe",
            file=(f.name, f.read()),
            language=language,
            # Add prompt to help with code-like content
            prompt="This is an English educational game. The user may say alphanumeric codes like CROWN-X-1859, SH-221B, OVERRIDE-PROTOCOL-007, or times like 04:18:37. Transcribe exactly what is spoken in English without translation.",
        )
        return transcript_obj.text.strip()

async def handle_text_message(event):
    message: str = event.message.text.strip()
    user_id = event.source.user_id
    
    await handle_rich_menu(user_id)
    
    if not await check_user_login(event, message):
        return

    if message.startswith('/unlink') or message.startswith('/解除綁定'):
        delData(user_id)
        await send_text_message(event, "已解除綁定！\nUnlinked!")
    elif message.startswith('/magic') or message.startswith('/魔法'):
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
            await send_text_message(event, "學號格式錯誤！\nStudent ID format error!")
            return False
        elif len(message) > 8:
            await send_text_message(event, "學號格式錯誤！\nStudent ID format error!")
            return False
    else:
        info.append(message)
        initData(user_id, info[0], info[1], info[2], info[3])
        del user_data_enter[user_id]
        await send_message(event, [
            await text_message(f"綁定完成 你好! {message}\nSuccess! Hello, {message}!"), 
        ])
        # Save after binding
        await save_user_data()
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
    
    # Prioritize game mode
    if config.get('rag_mode'):
        # Check if in NPC chat mode
        if user_state.in_npc_chat and user_state.game_theme and user_state.game_npc >= 0:
            if not isEnabled('rag_test') and not isAdmin(user_id):
                await send_text_message(event, "該區塊功能尚未開放。\nThis feature has not been unlocked yet.")
                return
            await handle_npc_chat(event, user_id, user_state)
            return
        
        # Check if user is in game mode and has selected a question
        if user_state.game_theme and user_state.game_level >= 0 and user_state.game_question >= 0:
            if not isEnabled('rag_test') and not isAdmin(user_id):
                await send_text_message(event, "該區塊功能尚未開放。\nThis feature has not been unlocked yet.")
                return
            await handle_game_answer(event, user_id, user_state)
            return
        # Handle old rag_test category
        elif user_state.category == 'rag_test' and user_state.sub >= 0:
            if not isEnabled('rag_test') and not isAdmin(user_id):
                await send_text_message(event, "該區塊功能尚未開放。\nThis feature has not been unlocked yet.")
                return
            await handle_game_mode(event, user_id, user_state)
            return

    try:
        text = None
        category = user_state.category
        
        if category in ['chat', 'sex', 'accent', 'audio']:
            if not isEnabled('chat'):
                await send_text_message(event, "該區塊功能尚未開放。\nThis feature has not been unlocked yet.")
                return
            await handle_chat(event)
            return
        
        # ===== pretest1 / posttest1：使用 new_test.json 題目與十級評分 =====
        if category in ['pretest1', 'posttest1']:
            base_cat = 'pretest' if category == 'pretest1' else 'posttest'
            if not isEnabled(base_cat) and not isAdmin(user_id):
                await send_text_message(event, "該區塊功能尚未開放。\nThis feature has not been unlocked yet.")
                return
            sub = user_state.sub
            if sub < 0:
                await send_text_message(event, "請先選擇題目。\nPlease select a question first.")
                return

            question = get_new_test_question(sub)
            if not question:
                await send_text_message(event, "找不到題目。\nQuestion not found.")
                return

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
                print('No text found in audio (pretest1/posttest1)')
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
                        "content": f"<question>{question.text}</question>"
                                   f"{'<standard>' + question.assessment_standard.replace(chr(10), '').strip() + '</standard>' if question.assessment_standard else ''}"
                                   f"<userAnswer>{text}</userAnswer>",
                    }
                ],
            )

            assessment = completion.choices[0].message.parsed
            assessment.transcript = text
            assessment.timestamp = time.time()

            history_key = f'{category}-{sub}'
            updateHistory(user_id, history_key, assessment)

            if should_show_feedback(base_cat):
                await send_message(event, await result_message(assessment, category, sub, show_feedback=True))
            else:
                await send_message(event, await result_message(assessment, category, sub, show_feedback=False))

            await save_user_data()
            return
        # ===== end pretest1 / posttest1 =====

        if not category or not question_manager.has_question(category):
            return 
        
        if not isEnabled(category) and not isAdmin(user_id):
            await send_text_message(event, "該區塊功能尚未開放。\nThis feature has not been unlocked yet.")
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
        
        assessment = completion.choices[0].message.parsed
        assessment.transcript = text
        assessment.timestamp = time.time()
        
        history_key = f'{category}-{sub}'
        updateHistory(user_id, history_key, assessment)
        
        if should_show_feedback(category):
            await send_message(event, await result_message(assessment, category, sub, show_feedback=True))
        else:
            await send_message(event, await result_message(assessment, category, sub, show_feedback=False))
        
        # Save user data
        await save_user_data()

    except Exception as e:
        print(f"Audio Message Error: {e}")
        import traceback
        traceback.print_exc()
        await send_text_message(event, "系統發生錯誤，請聯絡管理員。\nSystem error.")

async def handle_game_mode(event, user_id, user_state):
    """Handle old rag_test mode (backward compatibility)"""
    try:
        category = user_state.category
        sub = user_state.sub
        
        message_content = await get_audio_content(event)
        if not message_content:
            await send_text_message(event, "無法獲取音訊內容，請稍後再試。\nUnable to get audio content, please try again later.")
            return
        
        text = await transcribe_audio(message_content, language="en")
        
        if not text or len(text) < 1:
            await send_text_message(event, "無法獲取音訊內容，請稍後再試。\nUnable to get audio content, please try again later.")
            return
        
        rag_config = load_rag_config(category)
        npc_id = rag_config.get('npcs', [{}])[sub].get('id', 'narrator')
        npc_name = rag_config.get('npcs', [{}])[sub].get('name', 'Narrator')
        persona = rag_config.get('npcs', [{}])[sub].get('persona', '')
        rag_file = rag_config.get('npcs', [{}])[sub].get('file', 'narrator.md')
        rag_path = f'category/rag_docs/{category}/{rag_file}'
        
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
            max_completion_tokens=512,
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
        
        # Save user data
        await save_user_data()

    except Exception as e:
        print(f"Game Mode Error: {e}")
        import traceback
        traceback.print_exc()
        await send_text_message(event, "系統發生錯誤，請聯絡管理員。\nSystem error.")

# ========== NPC Chat Handling (Optimized: Async Two-Phase) ==========
async def handle_npc_chat(event, user_id, user_state):
    """Handle NPC chat - Phase 1: Quick response (3-5 sec) + Phase 2: Background evaluation"""
    try:
        theme_id = user_state.game_theme
        npc_idx = user_state.game_npc
        
        if not theme_id or npc_idx < 0:
            await send_text_message(event, "請先選擇角色。\nPlease select a character first.")
            return
        
        # Get audio and transcribe
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

        # Get NPC info
        npc_info = get_game_npc_info(theme_id, npc_idx)
        if not npc_info:
            npc_info = {
                "name": "The Narrator",
                "persona": "A helpful guide.",
                "file": "narrator.md"
            }
        
        # Get RAG context
        rag_path = os.path.join("category", "rag_docs", theme_id, npc_info["file"])
        if not os.path.exists(rag_path):
            rag_path = os.path.join("category", "rag_docs", theme_id)
        
        context_content = await get_rag_context_v2(rag_path, query=text)
        
        # Get chat history
        history_key = f'{theme_id}-npc-{npc_idx}'
        past_assessments = getHistory(user_id, history_key)
        history_str = ""
        if past_assessments:
            recent = past_assessments[-5:]
            for turn in recent:
                history_str += f"User: {turn.transcript}\nNPC ({npc_info['name']}): {turn.better_ans}\n"
        
        # ===== Phase 1: Quick NPC response (target: 3-5 sec) =====
        quick_prompt = NPC_CHAT_QUICK_RESPONSE.format(
            persona=f"{npc_info['name']}: {npc_info['persona']}",
            context=context_content,
            history=history_str
        )

        quick_completion = await client.beta.chat.completions.parse(
            model="gpt-4o",
            response_format=NPCChatResponse,
            max_completion_tokens=256,  # Limit tokens for speed
            temperature=0.7,
            messages=[
                { "role": "system", "content": quick_prompt },
                { "role": "user", "content": text }
            ],
        )

        quick_res: NPCChatResponse = NPCChatResponse.model_validate_json(
            quick_completion.choices[0].message.content
        )

        # Send NPC response immediately with image
        npc_image = npc_info.get('image') if npc_info else None

        # ===== NPC 語音輸出模式 (由 config 中的 npc_voice_output 控制) =====
        npc_voice_output = config.get('npc_voice_output', False)

        if npc_voice_output:
            # 儲存最近一次 NPC 回覆，供「顯示文字 / Show Text」功能使用
            set_last_npc_reply(user_id, npc_info['name'], quick_res.npc_reply, npc_image)

            # 嘗試生成 TTS 語音；若失敗則退回純文字卡片
            npc_audio_file = None
            npc_audio_duration = 0
            try:
                npc_audio_file, npc_audio_duration = await generate_npc_tts(quick_res.npc_reply)
            except Exception as tts_err:
                print(f"NPC TTS error (falling back to text card): {tts_err}")

            if npc_audio_file:
                voice_msgs = await game_npc_voice_response_messages(
                    npc_info['name'],
                    quick_res.npc_reply,
                    quick_res.is_english,
                    npc_image,
                    npc_audio_file,
                    npc_audio_duration
                )
                await send_message(event, voice_msgs)
            else:
                # TTS 失敗時退回文字卡片
                await send_message(event, await game_npc_chat_response_message(
                    npc_info['name'],
                    quick_res.npc_reply,
                    quick_res.is_english,
                    npc_image=npc_image
                ))
        else:
            # 預設行為：純文字卡片
            await send_message(event, await game_npc_chat_response_message(
                npc_info['name'],
                quick_res.npc_reply,
                quick_res.is_english,
                npc_image=npc_image
            ))
        # ===== end NPC 語音輸出模式 =====
        
        # ===== Phase 2: Background async evaluation (non-blocking) =====
        asyncio.create_task(
            evaluate_and_save_npc_chat(
                event, user_id, theme_id, npc_idx, npc_info,
                text, quick_res.npc_reply, quick_res.is_english,
                history_key
            )
        )
        
    except Exception as e:
        print(f"NPC Chat Error: {e}")
        import traceback
        traceback.print_exc()
        await send_text_message(event, "系統發生錯誤，請聯絡管理員。\nSystem error, please contact admin.")

async def evaluate_and_save_npc_chat(event, user_id, theme_id, npc_idx, npc_info,
                                       user_text, npc_reply, is_english, history_key):
    """Async evaluation and save NPC chat (background, non-blocking)"""
    try:
        # Get theme context for evaluation
        theme_config = load_game_theme_config(theme_id)
        theme_context = f"Theme: {theme_config.name}\n{theme_config.prologue[:200]}" if theme_config else ""
        
        # Call evaluation API
        eval_prompt = NPC_CHAT_EVALUATION.format(
            user_text=user_text,
            persona=f"{npc_info['name']}: {npc_info['persona']}",
            theme_context=theme_context
        )
        
        eval_completion = await client.beta.chat.completions.parse(
            model="gpt-4o-mini",  # Faster model for evaluation
            response_format=NPCChatEvaluation,
            max_completion_tokens=256,
            temperature=0.3,  # Lower temperature for consistency
            messages=[
                { "role": "system", "content": eval_prompt },
                { "role": "user", "content": f"Question: {user_text}" }
            ],
        )
        
        eval_res: NPCChatEvaluation = NPCChatEvaluation.model_validate_json(
            eval_completion.choices[0].message.content
        )
        
        # Save detailed evaluation to history
        assessment = SpeechAssessment(
            chi_suggestion=eval_res.feedback_chi,
            eng_suggestion=eval_res.feedback_eng,
            score=(eval_res.language_score + eval_res.relevance_score) // 2,
            transcript=user_text,
            better_ans=npc_reply,
            timestamp=time.time()
        )
        updateHistory(user_id, history_key, assessment)
        
        # Save to dedicated NPC chat record
        save_npc_chat_record(
            user_id, theme_id, npc_idx, npc_info['name'],
            user_text, npc_reply,
            eval_res.relevance_score, eval_res.language_score,
            eval_res.feedback_chi, eval_res.feedback_eng
        )
        
        # Save interaction log
        interaction_log = GameInteractionLog(
            user_id=user_id,
            timestamp=time.time(),
            interaction_type='npc_chat',
            theme_id=theme_id,
            npc_idx=npc_idx,
            npc_name=npc_info['name'],
            user_transcript=user_text,
            ai_response=npc_reply,
            score=(eval_res.language_score + eval_res.relevance_score) // 2,
            feedback=f"{eval_res.feedback_eng}\n{eval_res.feedback_chi}" if eval_res.feedback_eng else None
        )
        await save_interaction_log(interaction_log)
        
        # Save user data
        await save_user_data()
        
        # If feedback display is enabled, send evaluation results
        eval_message = await game_npc_evaluation_message(
            npc_info['name'],
            eval_res.language_score,
            eval_res.relevance_score,
            eval_res.feedback_eng,
            eval_res.feedback_chi
        )
        
        if eval_message and should_show_feedback('rag_test'):
            await send_message(event, eval_message)
        
    except Exception as e:
        print(f"NPC Chat Evaluation Error: {e}")
        import traceback
        traceback.print_exc()
        # Evaluation failure doesn't affect user experience, just log error

async def handle_game_answer(event, user_id, user_state):
    """Handle game question voice answers"""
    try:
        theme_id = user_state.game_theme
        level_idx = user_state.game_level
        question_idx = user_state.game_question
        
        if not theme_id or level_idx < 0 or question_idx < 0:
            await send_text_message(event, "請先選擇題目。\nPlease select a question first.")
            return
        
        # Get audio and transcribe
        try:
            message_content = await get_audio_content(event)
            # Transcribe directly, keep original language (no translation)
            text = await transcribe_audio(message_content, language="en")
        except Exception as e:
            print("Audio error:", e)
            import traceback
            traceback.print_exc()
            await send_text_message(event, "音訊處理錯誤，請稍後再試。\nAudio processing error.")
            return

        if not text:
            await send_text_message(event, "聽不清楚，請再說一次。\nCould not hear clearly, please try again.")
            return

        # Get question info
        level_info = get_game_level_info(theme_id, level_idx)
        question_text = ""
        reference_answers = []
        tiered_reference_answers = None
        if level_info and question_idx < len(level_info.get('questions', [])):
            q_data = level_info['questions'][question_idx]
            question_text = q_data['text']
            reference_answers = q_data.get('reference_answers', [])
            tiered_reference_answers = q_data.get('tiered_reference_answers', None)
        
        # Build reference answers section for prompt (supports tiered few-shot format)
        reference_answers_section = build_reference_answers_section(
            tiered_reference_answers=tiered_reference_answers,
            reference_answers=reference_answers
        )
        
        # Use question answer system instruction
        formatted_prompt = QUESTION_ANSWER_SYSTEM_INSTRUCTION.format(
            question=question_text,
            reference_answers_section=reference_answers_section,
            user_answer=text
        )

        # Get AI response
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

        # Handle response parsing with robust fallback
        answer_res = None
        try:
            answer_res = completion.choices[0].message.parsed
        except Exception as parse_error:
            print(f"Parsed attribute error: {parse_error}")
        
        # Fallback if parsed is None
        if answer_res is None:
            try:
                content = completion.choices[0].message.content
                if content:
                    print(f"[DEBUG] Fallback parsing from content: {content[:200]}...")
                    answer_res = QuestionAnswerResponse.model_validate_json(content)
                else:
                    raise ValueError("AI response is empty")
            except Exception as fallback_error:
                print(f"Fallback parsing error: {fallback_error}")
                import traceback
                traceback.print_exc()
                # Create default response when all parsing fails
                answer_res = QuestionAnswerResponse(
                    score=0,
                    feedback_chi="無法評估您的回答，請再試一次。\nUnable to evaluate your answer. Please try again.",
                    feedback_eng="Unable to evaluate your answer. Please try again.",
                    reference_comparison="Evaluation failed.",
                    is_correct=False
                )

        # Save evaluation result
        assessment = SpeechAssessment(
            chi_suggestion=answer_res.feedback_chi if answer_res.feedback_chi else "",
            eng_suggestion=answer_res.feedback_eng if answer_res.feedback_eng else "", 
            score=answer_res.score if answer_res.score is not None else 0,
            transcript=text,
            better_ans=answer_res.reference_comparison if answer_res.reference_comparison else "",
            timestamp=time.time()
        )
        
        history_key = f'{theme_id}-{level_idx}-{question_idx}'
        updateHistory(user_id, history_key, assessment)
        
        # Use new save function to record question answer
        save_question_answer_record(
            user_id, theme_id, level_idx, question_idx, question_text,
            text, answer_res.score, answer_res.is_correct,
            answer_res.feedback_chi if answer_res.feedback_chi else "",
            answer_res.feedback_eng if answer_res.feedback_eng else "",
            answer_res.reference_comparison if answer_res.reference_comparison else ""
        )
        
        # Update game score
        is_new_high, theme_total = update_game_score(
            user_id, theme_id, level_idx, question_idx, answer_res.score
        )
        
        # Check and unlock next level
        unlocked = check_and_unlock_next_level(user_id, theme_id, level_idx)
        
        # Save last answer info for improvement hint feature
        user_state.last_answer_info = {
            'theme_id': theme_id,
            'level_idx': level_idx,
            'question_idx': question_idx,
            'question_text': question_text,
            'reference_answers': reference_answers,
            'tiered_reference_answers': tiered_reference_answers,
            'user_answer': text,
            'score': answer_res.score,
            'is_correct': answer_res.is_correct
        }
        
        # Save interaction log
        interaction_log = GameInteractionLog(
            user_id=user_id,
            timestamp=time.time(),
            interaction_type='question_answer',
            theme_id=theme_id,
            level_idx=level_idx,
            question_idx=question_idx,
            user_transcript=text,
            ai_response=answer_res.reference_comparison if answer_res.reference_comparison else "",
            score=answer_res.score,
            feedback=f"{answer_res.feedback_eng}\n{answer_res.feedback_chi}" if answer_res.feedback_eng else None
        )
        await save_interaction_log(interaction_log)
        
        # Reset question state (exit answer mode)
        user_state.game_question = -1
        
        # Send result message (score always shown; feedback controlled per-category)
        await send_message(event, await game_score_message(
            user_id, theme_id, level_idx, question_idx,
            answer_res.score, is_new_high,
            feedback_chi=answer_res.feedback_chi if answer_res.feedback_chi else "",
            feedback_eng=answer_res.feedback_eng if answer_res.feedback_eng else "",
            show_feedback=should_show_feedback('rag_test')
        ))
        
        # If new level unlocked, send notification
        if unlocked:
            await send_text_message(event, "恭喜！已解鎖下一關！\nCongratulations! Next level unlocked!")
        
        # Save user data
        await save_user_data()

    except Exception as e:
        print(f"Game Answer Error: {e}")
        import traceback
        traceback.print_exc()
        await send_text_message(event, "系統發生錯誤，請聯絡管理員。\nSystem error, please contact admin.")

async def handle_game_improvement_hint(event, user_id, user_state):
    """Handle improvement hint request - on-demand generation, doesn't affect scoring speed"""
    try:
        # Check if there's last answer info
        last_info = getattr(user_state, 'last_answer_info', None)
        if not last_info:
            await send_text_message(event, "找不到上次回答記錄，請先作答。\nNo previous answer found. Please answer a question first.")
            return
        
        # Show loading animation
        await show_loading(user_id, 15)
        
        # Get last answer info
        question_text = last_info.get('question_text', '')
        reference_answers = last_info.get('reference_answers', [])
        user_answer = last_info.get('user_answer', '')
        score = last_info.get('score', 0)
        theme_id = last_info.get('theme_id', '')
        level_idx = last_info.get('level_idx', 0)
        question_idx = last_info.get('question_idx', 0)
        
        # Increment and get hint usage count
        hint_count = increment_hint_count(user_id, theme_id, level_idx, question_idx)
        
        # Format reference answers
        reference_answers_str = "\n".join(f"- {ans}" for ans in reference_answers) if reference_answers else "No reference answers provided."
        
        # If there is tiered reference answers info saved, use it for better hints
        tiered_reference_answers = last_info.get('tiered_reference_answers', None)
        if tiered_reference_answers:
            from utils.message_utils import build_reference_answers_section
            reference_answers_str = build_reference_answers_section(
                tiered_reference_answers=tiered_reference_answers,
                reference_answers=reference_answers
            )
        
        # Use improvement hint system instruction
        formatted_prompt = IMPROVEMENT_HINT_SYSTEM_INSTRUCTION.format(
            question=question_text,
            reference_answers=reference_answers_str,
            user_answer=user_answer,
            score=score
        )
        
        # Get AI response
        completion = await client.beta.chat.completions.parse(
            model="gpt-4o",
            response_format=ImprovementHintResponse,
            max_completion_tokens=512,
            temperature=0.7,
            messages=[
                { "role": "system", "content": formatted_prompt },
                { "role": "user", "content": "請給我改善提示。\nPlease give me improvement hints." }
            ],
        )
        
        hint_res = completion.choices[0].message.parsed
        
        # If parsed is None, try manual parsing
        if hint_res is None:
            content = completion.choices[0].message.content
            if content:
                hint_res = ImprovementHintResponse.model_validate_json(content)
            else:
                raise ValueError("AI response is empty")
        
        # Send improvement hint message - includes usage count
        await send_message(event, await game_improvement_hint_message(
            theme_id, level_idx, question_idx,
            hint_res.hint_eng, hint_res.hint_chi,
            hint_count=hint_count
        ))
        
        # Save user data
        await save_user_data()
        
    except Exception as e:
        print(f"Improvement Hint Error: {e}")
        import traceback
        traceback.print_exc()
        await send_text_message(event, "無法生成改善提示，請稍後再試。\nUnable to generate improvement hints. Please try again later.")

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
    
    # Save user data
    await save_user_data()

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
        if not isEnabled('chat') and not isAdmin(user_id):
            await send_text_message(event, "該區塊功能尚未開放。\nThis feature has not been unlocked yet.")
            return
        user_state.sub = sub
        await send_message(event, await chat_message(user_id, sub))
    elif action == 'record':
        sub = int(vars.get('sub'))
        # pretest1/posttest1 should use new_test_record, not record; guard against stale state
        if user_state.category in ['pretest1', 'posttest1']:
            base = 'pretest' if user_state.category == 'pretest1' else 'posttest'
            if not isEnabled(base) and not isAdmin(user_id):
                await send_text_message(event, "該區塊功能尚未開放。\nThis feature has not been unlocked yet.")
                return
            user_state.sub = sub
            await send_message(event, await new_test_question_message(user_id, sub, base))
            return
        _record_cat = get_enabled_category_for_alias(user_state.category)
        if not isEnabled(_record_cat) and not isAdmin(user_id):
            await send_text_message(event, "該區塊功能尚未開放。\nThis feature has not been unlocked yet.")
            return
        user_state.sub = sub
        await send_message(event, await question_message(user_id, user_state.category, sub))
    elif action == 'carousel':
        page = int(vars.get('page', 0))
        _carousel_cat = get_enabled_category_for_alias(user_state.category)
        if not isEnabled(_carousel_cat) and not isAdmin(user_id):
            await send_text_message(event, "該區塊功能尚未開放。\nThis feature has not been unlocked yet.")
            return
        await send_message(event, await carousel_message(user_id, user_state.category, page))
    elif action == 'last':
        category = vars.get('category', user_state.category)
        sub = int(vars.get('sub', 0))
        result = getHistory(user_id, f'{category}-{sub}')
        if not result:
            await send_text_message(event, f'Q{sub+1} 查無紀錄！\nNo history found in Q{sub+1}!')
            return
        _last_enabled_cat = get_enabled_category_for_alias(category)
        if not isEnabled(_last_enabled_cat) and not isAdmin(user_id):
            await send_text_message(event, "該區塊功能尚未開放。\nThis feature has not been unlocked yet.")
            return
        
        is_rag = config.get('rag_mode', False)
        if not isResponse(category) and not is_rag:
            await send_text_message(event, "該單元目前不提供回饋。\nCurrently unavailable.")
            return
        await send_message(event, await result_message(result[-1], category, sub))
        
    elif action == 'switch':
        alias = vars.get('to')
        if alias in ['admin', 'game_admin'] and not isAdmin(user_id):
            await send_text_message(event, '無權限!\nNo permission!')
            return
        
        # RAG mode menu switch logic
        is_rag = config.get('rag_mode', False)
        if alias == 'menu':
            if is_rag:
                alias = 'menu_game'
        elif alias == 'menu_game':
            if not is_rag:
                alias = 'menu'
        
        # Check enabled status using alias resolution (covers sub-aliases like pretest1, pretest1-2, etc.)
        _switch_enabled_cat = get_enabled_category_for_alias(alias)
        _SWITCH_CONTROLLED = {'pretest', 'posttest', 'rag_test', 'ex1', 'ex2', 'ex3', 'ex4', 'ex5', 'ex6', 'chat'}
        if alias not in ['menu_other'] and _switch_enabled_cat in _SWITCH_CONTROLLED and not isEnabled(_switch_enabled_cat) and not isAdmin(user_id):
            await send_text_message(event, "該區塊功能尚未開放。\nThis feature has not been unlocked yet.")
            # 若 LINE 平台已先執行了選單跳轉（RichMenuSwitchAction），立刻將使用者拉回預設主選單，
            # 確保不論底層用哪種 action 類型，使用者都不會停留在被關閉的選單上。
            # If LINE's platform already performed a rich menu switch before the webhook fired
            # (RichMenuSwitchAction), immediately re-link the user to the default main menu so
            # they never remain on the locked section regardless of the action type used.
            _default_menu_alias = 'menu_game' if config.get('rag_mode', False) else 'menu'
            _default_menu_id = get_rich_menu_id(_default_menu_alias)
            if _default_menu_id:
                try:
                    await rich_menu_manager.link_rich_menu_to_user(user_id, _default_menu_id)
                except Exception as _relink_err:
                    print(f"[WARN] Failed to re-link rich menu after blocked switch: {_relink_err}")
            return
        
        # pretest2/posttest2 are rich-menu aliases for the original pretest/posttest questions;
        # map the internal category back so question_manager can find the questions.
        # Pretest1/posttest1 sub-pages (e.g. pretest1-2) extract category with split('-')[0].
        _MENU_CATEGORY_MAP = {'pretest2': 'pretest', 'posttest2': 'posttest'}
        raw_cat = alias.split('-')[0]
        user_state.category = _MENU_CATEGORY_MAP.get(raw_cat, raw_cat)
        # Reset NPC chat state on menu switch
        user_state.in_npc_chat = False
        
        rich_menu_id = get_rich_menu_id(alias)
        if rich_menu_id:
            await rich_menu_manager.link_rich_menu_to_user(user_id, rich_menu_id)
        else:
            await send_text_message(event, f"Menu '{alias}' is not registered. Please ask admin to reload.\nMenu '{alias}' 尚未註冊，請通知管理員重新載入。")
            return
        
        # Auto popup menu
        # pretest/posttest family: the rich menu itself IS the navigation UI, no auto-popup needed.
        _NO_POPUP_PREFIXES = ('pretest', 'posttest')
        if any(alias.startswith(p) for p in _NO_POPUP_PREFIXES):
            pass
        elif question_manager.has_question(user_state.category) and alias not in ['chat', 'admin', 'game_admin']:
            await send_message(event, await carousel_message(user_id, user_state.category, 0))

    elif action == 'progress':
        await send_message(event, await progress_message(user_id))

    # ===== new_test 題目作答 (pretest1 / posttest1) — 由 rich menu 按鈕觸發 =====

    elif action == 'new_test_record':
        # 使用者點擊 rich menu 中的 Q 按鈕，顯示題目卡片
        # Triggered when user taps a Q button in the pretest1/posttest1 rich menus
        sub = int(vars.get('sub', 0))
        base = vars.get('base', 'pretest')
        if not isEnabled(base) and not isAdmin(user_id):
            await send_text_message(event, "該區塊功能尚未開放。\nThis feature has not been unlocked yet.")
            return
        user_state.category = f'{base}1'
        user_state.sub = sub
        await send_message(event, await new_test_question_message(user_id, sub, base))

    elif action == 'new_test_last':
        # 查看 new_test 某題的上次評分回饋
        # Show last assessment result for a new_test question
        sub = int(vars.get('sub', 0))
        base = vars.get('base', 'pretest')
        section_category = f'{base}1'
        result = getHistory(user_id, f'{section_category}-{sub}')
        if not result:
            await send_text_message(event, f'Q{sub + 1} 查無紀錄！\nNo history found in Q{sub + 1}!')
            return
        await send_message(event, await result_message(result[-1], section_category, sub))

    # ===== NPC 顯示文字 (語音模式) =====

    elif action == 'game_show_npc_text':
        last_info = get_last_npc_reply(user_id)
        if not last_info:
            await send_text_message(event, "找不到最近的 NPC 回覆。\nNo recent NPC reply found.")
            return
        await send_message(event, await game_npc_text_card_message(
            last_info.get('npc_name', 'NPC'),
            last_info.get('npc_reply', ''),
            last_info.get('npc_image')
        ))

    elif action == 'progress_select':
        # [Fix #1] Show progress category selection for service4
        await send_message(event, await progress_select_message())
    elif action == 'progress_detail':
        # Show progress detail for specific category
        category = vars.get('category', '')
        if category == 'game':
            await send_message(event, await game_progress_message(user_id))
        elif category == 'other':
            await send_message(event, await other_progress_message(user_id))
        elif category == 'pretest':
            # 前測進度：前測1 (10題) + 前測2 (5題) 分開呈現
            # Pre-test progress: Pre-test 1 (10 Qs) + Pre-test 2 (5 Qs) shown separately
            await send_message(event, await pretest_progress_message(user_id))
        elif category == 'posttest':
            # 後測進度：後測1 (10題) + 後測2 (5題) 分開呈現
            # Post-test progress: Post-test 1 (10 Qs) + Post-test 2 (5 Qs) shown separately
            await send_message(event, await posttest_progress_message(user_id))
        else:
            await send_text_message(event, "未知的進度類別。\nUnknown progress category.")
    elif action == 'enabled':
        alias = vars.get('alias')
        if isEnabled(alias):
            removeEnabled(alias)
        else:
            addEnabled(alias)
        await save_config()
        display = get_feature_display_name(alias)
        if isEnabled(alias):
            await send_text_message(event, f'已開啟{display}!\n{alias.capitalize()} enabled!')
        else:
            await send_text_message(event, f'已關閉{display}!\n{alias.capitalize()} disabled!')
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
        display = get_feature_display_name(alias)
        if isResponse(alias):
            await send_text_message(event, f'已開啟{display}的回饋!\n{alias.capitalize()} feedback enabled!')
        else:
            await send_text_message(event, f'已關閉{display}的回饋!\n{alias.capitalize()} feedback disabled!')
        await question_manager.save_category(alias)
    elif action == 'reload':
        question_manager.load_questions()
        clear_game_theme_cache()
        await send_text_message(event, '已重新載入問題與主題！\nQuestions and themes reloaded!')
    elif action == 'save':
        await save_all()
        await send_text_message(event, '儲存成功！\nSave successful!')
    
    # ========== Game Actions ==========
    elif action == 'game_themes':
        # Switch to game lobby menu
        lobby_menu_id = get_rich_menu_id('game_lobby')
        if lobby_menu_id:
            await rich_menu_manager.link_rich_menu_to_user(user_id, lobby_menu_id)
        else:
            await send_text_message(event, "遊戲大廳選單尚未設定，請聯絡管理員。\nGame lobby menu not configured, please contact admin.")
    
    elif action == 'game_info':
        # Handle game lobby info section buttons
        # Fix #3: always switch menu back to game_lobby regardless of which section is shown
        lobby_menu_id = get_rich_menu_id('game_lobby')
        if lobby_menu_id:
            await rich_menu_manager.link_rich_menu_to_user(user_id, lobby_menu_id)
        
        section = vars.get('section', 'rules')
        if section == 'rules':
            rules_msg = await game_rules_instruction_message()
            await send_message(event, rules_msg)
        elif section == 'story':
            story_msg = await game_story_message()
            await send_message(event, story_msg)
        elif section == 'characters':
            chars_msgs = await game_characters_message()
            await send_message(event, chars_msgs)
        elif section == 'structure':
            structure_msg = await game_structure_message()
            await send_message(event, structure_msg)
        else:
            await send_text_message(event, "未知的遊戲資訊類別。\nUnknown game info section.")
    
    elif action == 'game_show_themes':
        # Triggered when user presses "Select Theme" from the lobby menu or quick reply.
        # Switch to theme selection menu and show theme cards.
        theme_select_menu_id = get_rich_menu_id('game_theme_select')
        if theme_select_menu_id:
            await rich_menu_manager.link_rich_menu_to_user(user_id, theme_select_menu_id)
        theme_msg = await game_theme_select_message()
        await send_message(event, theme_msg)
    
    elif action == 'game_theme':
        # Enter theme - Show prologue only (level details shown when user selects a level)
        theme_id = vars.get('theme')
        if not theme_id:
            await send_text_message(event, "未指定主題。\nTopic not specified.")
            return
        
        try:
            user_state.game_theme = theme_id
            user_state.game_level = -1
            user_state.game_question = -1
            user_state.in_npc_chat = False
            user_state.has_talked_to_npc = False
            
            # Switch to theme menu
            theme_menu_id = get_rich_menu_id(f'game_{theme_id}')
            if theme_menu_id:
                await rich_menu_manager.link_rich_menu_to_user(user_id, theme_menu_id)
            
            # Only show prologue message (level intro is deferred to game_level action)
            all_messages = []
            
            prologue_msgs = await game_prologue_message(theme_id)
            if prologue_msgs:
                all_messages.extend(prologue_msgs if isinstance(prologue_msgs, list) else [prologue_msgs])
            
            if all_messages:
                await send_message(event, all_messages[:5])
        except Exception as e:
            print(f"Error in game_theme action: {e}")
            import traceback
            traceback.print_exc()
            await send_text_message(event, "載入主題時發生錯誤，請稍後再試。\nError loading topic, please try again later.")
    
    elif action == 'game_npcs':
        # Show current theme's NPC selection
        theme_id = vars.get('theme', user_state.game_theme)
        if not theme_id:
            await send_text_message(event, "請先選擇主題。\nPlease select a topic first.")
            return
        try:
            npc_select = await game_npc_select_message(theme_id, user_id)
            if npc_select:
                await send_message(event, npc_select)
            else:
                await send_text_message(event, "無法載入角色列表。\nFailed to load NPC list.")
        except Exception as e:
            print(f"Error in game_npcs action: {e}")
            import traceback
            traceback.print_exc()
            await send_text_message(event, "載入角色列表時發生錯誤。\nError loading NPC list.")
    
    elif action == 'game_npc':
        # Select NPC to chat with
        theme_id = vars.get('theme', user_state.game_theme)
        try:
            npc_idx = int(vars.get('npc', 0))
        except (ValueError, TypeError):
            npc_idx = 0
        
        if not theme_id:
            await send_text_message(event, "請先選擇主題。\nPlease select a topic first.")
            return
        
        user_state.game_theme = theme_id
        user_state.game_npc = npc_idx
        user_state.game_question = -1  # Ensure not in answer mode
        user_state.in_npc_chat = True  # Set NPC chat mode
        user_state.has_talked_to_npc = True  # [Fix #4] Mark that user has interacted with NPC
        
        # Show NPC card instead of plain text
        try:
            npc_card = await game_npc_card_message(theme_id, npc_idx)
            if npc_card:
                await send_message(event, npc_card)
            else:
                await send_text_message(event, "無法載入角色資訊，請稍後再試。\nFailed to load NPC info, please try again.")
        except Exception as e:
            print(f"Error in game_npc action: {e}")
            import traceback
            traceback.print_exc()
            await send_text_message(event, "載入角色時發生錯誤，請稍後再試。\nError loading NPC, please try again.")
    
    elif action == 'game_levels':
        # Show level selection
        theme_id = vars.get('theme', user_state.game_theme)
        if not theme_id:
            await send_text_message(event, "請先選擇主題。\nPlease select a topic first.")
            return
        await send_message(event, await game_level_select_message(theme_id, user_id))
    
    elif action == 'game_level':
        # Enter level - Show description card and video only.
        # Questions are revealed only after the user presses "Show Questions" in the intro card.
        theme_id = vars.get('theme', user_state.game_theme)
        level_idx = int(vars.get('level', 0))
        
        if not theme_id:
            await send_text_message(event, "請先選擇主題。\nPlease select a topic first.")
            return
        
        user_state.game_theme = theme_id
        user_state.game_level = level_idx
        user_state.game_question = -1
        user_state.in_npc_chat = False  # Exit NPC chat mode
        
        # Send only the level intro (description card + video).
        # The "Show Questions / 顯示題目" button in the card triggers game_questions action.
        messages = await game_level_intro_message(theme_id, level_idx, user_id)
        if messages:
            await send_message(event, messages[:5])
    
    elif action == 'game_questions':
        # Show current level's question cards
        theme_id = vars.get('theme', user_state.game_theme)
        level_idx = int(vars.get('level', user_state.game_level))
        
        if not theme_id or level_idx < 0:
            await send_text_message(event, "請先選擇關卡。\nPlease select a level first.")
            return
        
        await send_message(event, await game_questions_carousel(theme_id, level_idx, user_id))
    
    elif action == 'game_current_questions':
        # Show current theme's current level questions (for menu button)
        theme_id = vars.get('theme', user_state.game_theme)
        if not theme_id:
            await send_text_message(event, "請先選擇主題。\nPlease select a topic first.")
            return
        
        await send_message(event, await game_current_questions_message(theme_id, user_id))
    
    elif action == 'game_answer':
        # Select question to answer
        theme_id = vars.get('theme', user_state.game_theme)
        level_idx = int(vars.get('level', user_state.game_level))
        question_idx = int(vars.get('question', 0))
        
        if not theme_id or level_idx < 0:
            await send_text_message(event, "請先選擇關卡。\nPlease select a level first.")
            return
        
        user_state.game_theme = theme_id
        user_state.game_level = level_idx
        user_state.game_question = question_idx
        user_state.in_npc_chat = False  # Ensure exit NPC chat mode
        
        # Get question text
        level_info = get_game_level_info(theme_id, level_idx)
        # [Fix #5] Use topic-level-question numbering format
        from utils.file_utils import get_theme_display_number
        topic_num = get_theme_display_number(theme_id)
        q_label = f"Topic {topic_num} Q{level_idx + 1}-{question_idx + 1}"
        q_label_chi = f"主題 {topic_num} 題目 {level_idx + 1}-{question_idx + 1}"
        if level_info and question_idx < len(level_info.get('questions', [])):
            q_text = level_info['questions'][question_idx]['text']
            has_talked_to_npc = getattr(user_state, 'has_talked_to_npc', False)
            await send_message(event, await game_answer_card_message(
                theme_id, level_idx, question_idx, q_text, has_talked_to_npc
            ))
        else:
            # Fallback: no question data found, show card without question text
            await send_message(event, await game_answer_card_message(
                theme_id, level_idx, question_idx, '', True
            ))
    
    elif action == 'game_improvement_hint':
        # Handle improvement hint request
        await handle_game_improvement_hint(event, user_id, user_state)
        
    elif action == 'game_score':
        # Show current theme score
        theme_id = vars.get('theme', user_state.game_theme)
        if not theme_id:
            await send_text_message(event, "請先選擇主題。\nPlease select a topic first.")
            return
        
        progress = get_user_game_progress(user_id, theme_id)
        await send_text_message(event, 
            f"主題分數 Topic Score: {progress['total_score']}/{progress['max_score']}\n"
            f"已回答題數 Questions Answered: {progress['questions_answered']}\n"
            f"已完成關卡 Levels Completed: {progress['levels_completed']}"
        )
    
    elif action == 'game_next_answer':
        # Jump to the next unanswered question across all levels
        theme_id = vars.get('theme', user_state.game_theme)
        if not theme_id:
            await send_text_message(event, "請先選擇主題。\nPlease select a topic first.")
            return
        
        # Find the next unanswered question globally
        level_idx, question_idx = get_next_unanswered_question_global(user_id, theme_id)
        
        if level_idx == -1 and question_idx == -1:
            # All questions completed
            await send_text_message(event, "所有題目皆已作答完畢！\nAll questions have been answered!")
            return
        
        # Update user state
        user_state.game_theme = theme_id
        user_state.game_level = level_idx
        user_state.game_question = question_idx
        user_state.in_npc_chat = False  # Ensure exit NPC chat mode
        
        # Get question text
        level_info = get_game_level_info(theme_id, level_idx)
        from utils.file_utils import get_theme_display_number
        topic_num = get_theme_display_number(theme_id)
        if level_info and question_idx < len(level_info.get('questions', [])):
            q_text = level_info['questions'][question_idx]['text']
            has_talked_to_npc = getattr(user_state, 'has_talked_to_npc', False)
            await send_message(event, await game_answer_card_message(
                theme_id, level_idx, question_idx, q_text, has_talked_to_npc
            ))
        else:
            # Fallback: no question data found, show card without question text
            await send_message(event, await game_answer_card_message(
                theme_id, level_idx, question_idx, '', True
            ))