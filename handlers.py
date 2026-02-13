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
    game_progress_message, other_progress_message
)
from utils.models import (
    ChatSummary, ChatSummaryAndScore, SpeechAssessment, GameResponse,
    # Response models
    NPCChatResponse, NPCChatEvaluation, QuestionAnswerResponse, GameInteractionLog,
    ImprovementHintResponse
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
            await handle_npc_chat(event, user_id, user_state)
            return
        
        # Check if user is in game mode and has selected a question
        if user_state.game_theme and user_state.game_level >= 0 and user_state.game_question >= 0:
            await handle_game_answer(event, user_id, user_state)
            return
        # Handle old rag_test category
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
        
        assessment = completion.choices[0].message.parsed
        assessment.transcript = text
        assessment.timestamp = time.time()
        
        history_key = f'{category}-{sub}'
        updateHistory(user_id, history_key, assessment)
        
        if get_display_feedback():
            await send_message(event, await result_message(assessment, category, sub))
        else:
            await send_text_message(event, "已收到您的回答！\nReceived your answer!")
        
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
        await send_message(event, await game_npc_chat_response_message(
            npc_info['name'],
            quick_res.npc_reply,
            quick_res.is_english,
            npc_image=npc_image
        ))
        
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
        
        if eval_message:
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
        if level_info and question_idx < len(level_info.get('questions', [])):
            q_data = level_info['questions'][question_idx]
            question_text = q_data['text']
            reference_answers = q_data.get('reference_answers', [])
        
        # Format reference answers
        reference_answers_str = "\n".join(f"- {ans}" for ans in reference_answers) if reference_answers else "No reference answers provided."
        
        # Use question answer system instruction
        formatted_prompt = QUESTION_ANSWER_SYSTEM_INSTRUCTION.format(
            question=question_text,
            reference_answers=reference_answers_str,
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
        
        # Send result message
        await send_message(event, await game_score_message(
            user_id, theme_id, level_idx, question_idx,
            answer_res.score, is_new_high,
            feedback_chi=answer_res.feedback_chi if answer_res.feedback_chi else "",
            feedback_eng=answer_res.feedback_eng if answer_res.feedback_eng else ""
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
        
        if alias not in ['rag_test', 'menu_other'] and alias in ['pretest', 'posttest', 'ex1', 'ex2', 'ex3', 'ex4', 'ex5', 'ex6', 'chat'] and not isEnabled(alias):
            await send_text_message(event, "該單元目前不可用。\nCurrently unavailable.")
            return
        
        user_state.category = alias.split('-')[0]
        # Reset NPC chat state on menu switch
        user_state.in_npc_chat = False
        
        rich_menu_id = get_rich_menu_id(alias)
        if rich_menu_id:
            await rich_menu_manager.link_rich_menu_to_user(user_id, rich_menu_id)
        else:
            await send_text_message(event, f"Menu '{alias}' is not registered. Please ask admin to reload.\nMenu '{alias}' 尚未註冊，請通知管理員重新載入。")
            return
        
        # Auto popup menu
        if question_manager.has_question(user_state.category) and alias not in ['chat', 'admin', 'game_admin']:
            await send_message(event, await carousel_message(user_id, user_state.category, 0)) # Start from first page

    elif action == 'progress':
        await send_message(event, await progress_message(user_id))
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
        elif category in ['pretest', 'posttest']:
            # Reuse existing progress message filtered by category
            await send_message(event, await progress_message(user_id))
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
        # [Fix #4] Show game rules instruction first, then theme selection
        rules_msg = await game_rules_instruction_message()
        theme_msg = await game_theme_select_message()
        await send_message(event, [rules_msg, theme_msg])
    
    elif action == 'game_theme':
        # Enter theme - Show prologue only (level details shown when user selects a level)
        theme_id = vars.get('theme')
        if not theme_id:
            await send_text_message(event, "未指定主題。\nTheme not specified.")
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
            await send_text_message(event, "載入主題時發生錯誤，請稍後再試。\nError loading theme, please try again later.")
    
    elif action == 'game_npcs':
        # Show current theme's NPC selection
        theme_id = vars.get('theme', user_state.game_theme)
        if not theme_id:
            await send_text_message(event, "請先選擇主題。\nPlease select a theme first.")
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
            await send_text_message(event, "請先選擇主題。\nPlease select a theme first.")
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
            await send_text_message(event, "請先選擇主題。\nPlease select a theme first.")
            return
        await send_message(event, await game_level_select_message(theme_id, user_id))
    
    elif action == 'game_level':
        # Enter level - Show video intro
        theme_id = vars.get('theme', user_state.game_theme)
        level_idx = int(vars.get('level', 0))
        
        if not theme_id:
            await send_text_message(event, "請先選擇主題。\nPlease select a theme first.")
            return
        
        user_state.game_theme = theme_id
        user_state.game_level = level_idx
        user_state.game_question = -1
        user_state.in_npc_chat = False  # Exit NPC chat mode
        
        # Collect all messages into a single list
        all_messages = []
        
        messages = await game_level_intro_message(theme_id, level_idx, user_id)
        if messages:
            all_messages.extend(messages if isinstance(messages, list) else [messages])
        
        # Send question selection
        questions_carousel = await game_questions_carousel(theme_id, level_idx, user_id)
        if questions_carousel:
            all_messages.append(questions_carousel)
        
        # LINE API allows max 5 messages per reply
        if all_messages:
            await send_message(event, all_messages[:5])
    
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
            await send_text_message(event, "請先選擇主題。\nPlease select a theme first.")
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
        # [Fix #6] Use level-question numbering format
        q_label = f"{level_idx + 1}-{question_idx + 1}"
        if level_info and question_idx < len(level_info.get('questions', [])):
            q_text = level_info['questions'][question_idx]['text']
            # [Fix #4] Check if user has talked to NPC before answering
            npc_hint = ""
            if not getattr(user_state, 'has_talked_to_npc', False):
                npc_hint = (
                    "\n\n是不是還不知道答案啊？可以先去選單中點擊角色圖像，向 NPC 詢問案件細節喔！\n"
                    "Not sure about the answer? Try clicking on NPC icons in the menu to ask for clues!"
                )
            await send_text_message(event, f"{q_label}: {q_text}\n\n請發送語音訊息作答！\nSend a voice message with your answer!{npc_hint}")
        else:
            await send_text_message(event, "請發送語音訊息作答！\nSend a voice message with your answer!")
    
    elif action == 'game_improvement_hint':
        # Handle improvement hint request
        await handle_game_improvement_hint(event, user_id, user_state)
        
    elif action == 'game_score':
        # Show current theme score
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
    
    elif action == 'game_next_answer':
        # Jump to the next unanswered question across all levels
        theme_id = vars.get('theme', user_state.game_theme)
        if not theme_id:
            await send_text_message(event, "請先選擇主題。\nPlease select a theme first.")
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
        if level_info and question_idx < len(level_info.get('questions', [])):
            q_text = level_info['questions'][question_idx]['text']
            level_title = level_info.get('title', f'Level {level_idx + 1}')
            await send_text_message(event, 
                f"關卡 Level {level_idx + 1}: {level_title}\n"
                f"{level_idx + 1}-{question_idx + 1}: {q_text}\n\n"
                f"請發送語音訊息作答！\nSend a voice message with your answer!"
            )
        else:
            await send_text_message(event, "請發送語音訊息作答！\nSend a voice message with your answer!")