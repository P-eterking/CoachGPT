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
    # [新增] 用於 audio 評分的 <standard> 區段建構輔助函式
    # 修正 chr(10) 壓平 bug 並對 SEL 套用十級 few-shot 格式
    # Helper for building the <standard> section in audio assessment;
    # fixes the chr(10) flattening bug and applies tiered few-shot formatting for SEL.
    build_standard_section_for_audio,
    # Question card with image for service4 game_answer action
    game_answer_card_message,
    # new_test single question card (pretest1 / posttest1)
    new_test_question_message,
    # NPC voice response messages (item 4)
    game_npc_voice_response_messages, game_npc_text_card_message,
    # [新增] Chat 主題功能與 SEL 評分指示
    # New additions: chat topic helpers and SEL evaluation instruction
    # [新增] SEL 提示詞 builder（依作答語言）與 SEL 作答語言選擇卡片
    # SEL prompt builder (language-aware) and the SEL language-selection card
    SEL_SYSTEM_INSTRUCTION, build_sel_system_instruction,
    sel_language_select_message,
    get_chat_topic_system_prompt,
    chat_welcome_message, chat_topic_intro_message,
    # [新增 (SEL 多單元)] SEL 單元介紹卡片
    # SEL multi-unit intro card
    sel_unit_intro_message,
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
    get_npc_chat_memory, append_npc_chat_memory,
    increment_show_text_count, get_show_text_count,
    is_fallback_guide_enabled, load_guide_content,
    # [新增] 逐題模式開關、SEL 語言選擇開關、跨關卡未作答題目查找
    # one-by-one mode switch, SEL language-selection switch, first-never-answered finder
    is_one_by_one, is_sel_language_selection_enabled,
    get_first_never_answered_question_global,
)
import tempfile
import time
import base64
from pydub import AudioSegment
from io import BytesIO
import os

# ========== 引導型客服機器人系統提示詞 ==========
# 作為文件載入失敗時的備援，直接嵌入核心指引。
# Embedded as fallback in case the guide file cannot be loaded.
_FALLBACK_GUIDE_SYSTEM_PROMPT_CORE = """
You are a concise bilingual (English / Traditional Chinese) support assistant for CoachGPT, an English-learning LINE chatbot.
Your ONLY purpose: guide users on how to use this chatbot. Never engage in extended conversation or off-topic discussion.
Always respond in BOTH English AND Traditional Chinese in the same reply. Keep total response under 60 words. Be direct and action-oriented.

CoachGPT features: Mystery Game (NPC chat + voice Q&A), Exercises (ex1-ex6 voice practice), Pre/Post-Test, Chat Practice, Progress view.
All features are accessed via the rich menu (tap the three-bar icon next to the text input box).
Answering questions requires recording a voice message (tap the microphone icon in LINE).

If user's message is unrelated to CoachGPT, always reply:
English: "This assistant only handles CoachGPT-related questions. Please use the menu below to start practicing."
Traditional Chinese: "此助理僅回應 CoachGPT 相關問題，請點選下方選單開始練習。"
"""


async def handle_fallback_guide(event, user_id: str, message_text: str) -> None:
    """
    引導型客服機器人：當使用者在無特定模式下傳送訊息時，以 AI 提供簡短的雙語引導回應。
    僅在 service4/5 (rag_mode) 中啟用，不影響 service1/2/3。

    Fallback guide handler: provides a short bilingual AI-generated guidance response
    when the user sends a message outside any active interaction mode.
    Only active for service 4/5. Does not affect service 1/2/3.
    """
    try:
        # 載入引導文件（優先使用外部文件，備援使用內建提示詞）
        # Load guide document; fall back to embedded prompt if file unavailable
        guide_doc = load_guide_content()
        system_prompt = (
            f"{_FALLBACK_GUIDE_SYSTEM_PROMPT_CORE}\n\n--- Detailed Guide ---\n{guide_doc}"
            if guide_doc
            else _FALLBACK_GUIDE_SYSTEM_PROMPT_CORE
        )

        completion = await client.chat.completions.create(
            model="gpt-4o-mini",
            max_completion_tokens=150,
            temperature=0.3,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message_text},
            ],
        )

        reply = completion.choices[0].message.content.strip()
        if reply:
            await send_text_message(event, reply)
    except Exception as e:
        print(f"Fallback Guide Error: {e}")
        import traceback
        traceback.print_exc()
        await send_text_message(
            event,
            "This assistant only handles CoachGPT-related questions. Please use the menu below to start practicing.\n"
            "此助理僅回應 CoachGPT 相關問題，請點選下方選單開始練習。"
        )


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

# 儲存尚未完成綁定的使用者資料暫存，key 為 user_id，value 為已填寫的資料列表
# Temporary store for users in the middle of the account binding flow
user_data_enter = {}


# ========== [新增] SEL 類別判別小工具 (SEL category helper) ==========
# 涵蓋舊的單一 'sel' 類別與新的多單元 'sel1'..'sel6'，作為評分路由的統一判斷點。
# Covers both the legacy single 'sel' category and the new multi-unit 'sel1'..'sel6';
# used as the unified routing predicate for SEL-specific evaluation.
_SEL_CATEGORIES = {'sel', 'sel1', 'sel2', 'sel3', 'sel4', 'sel5', 'sel6'}


def _is_sel_category(category) -> bool:
    """判斷給定類別是否為SEL系列（單一 'sel' 或六個單元 'sel1'..'sel6'）。
    Determine whether a given category belongs to the SEL family
    (the legacy 'sel' or any of the six units 'sel1'..'sel6').
    """
    if not category:
        return False
    return category in _SEL_CATEGORIES


async def handle_follow(event) -> None:
    """處理使用者首次加入（或封鎖後重新加入）機器人好友的事件。
    Handle the FollowEvent triggered when a user adds (or re-adds after blocking) the bot as a friend.

    修正說明：
      原本的同意聲明僅由 check_user_login 觸發，而 check_user_login 需要使用者先主動
      發送訊息才會執行。若 Greeting message 為純文字（無按鈕），新使用者加入後不會有任何
      事件打到 check_user_login，導致同意聲明完全不出現。
      本函式直接攔截 FollowEvent，在使用者加入的瞬間主動推送同意聲明，
      不再依賴使用者主動發送訊息。

    Fix:
      The consent notice was previously only shown inside check_user_login, which requires
      the user to send a message first. With a plain-text Greeting Message (no buttons),
      new users trigger no events, so check_user_login is never reached and the notice never
      appears. This function intercepts FollowEvent and proactively pushes the consent notice
      the moment the user adds the bot, without relying on the user sending any message.

    正確流程 / Correct onboarding flow:
      1. 使用者加入好友 -> LINE 平台送出 Greeting Message (由 LINE Manager 設定)
         User adds bot -> LINE platform sends Greeting Message (configured in LINE Manager)
      2. FollowEvent 觸發 -> 本函式立即推送「語音資料與AI處理同意聲明」
         FollowEvent fires -> this function immediately sends the voice data consent notice
      3. 使用者點擊「我同意 / I agree」-> handle_postback 處理 consent -> 進入帳號綁定
         User taps "I agree" -> handle_postback handles consent -> account binding starts
      4. 使用者點擊「我不同意 / I disagree」-> 顯示拒絕授權卡片
         User taps "I disagree" -> consent declined card is shown

    重新綁定流程 / Re-binding flow (after /unlink, without leaving the chat):
      - 使用者使用 /unlink 解除綁定後仍在聊天室，不會再次觸發 FollowEvent
      - 此時使用者發送任意訊息 -> handle_text_message -> check_user_login 顯示同意聲明
      - After /unlink, the user stays in chat so FollowEvent does not fire again.
      - Any message they send goes through check_user_login which shows the notice.
    """
    user_id = event.source.user_id

    # 若使用者已完成綁定（封鎖後重新加入的老使用者），直接略過
    # If the user is already bound (returning user who re-followed after blocking), skip
    if hasData(user_id):
        return

    # 若使用者已在進行帳號綁定流程中，直接略過，避免中斷進行中的流程
    # If the user is already in the middle of the binding flow, skip
    if user_id in user_data_enter:
        return

    # 推送同意聲明卡片
    # Push the consent notice card immediately
    await send_message(event, _build_privacy_notice_message())


async def handle_text_message(event):
    message: str = event.message.text.strip()
    user_id = event.source.user_id
    
    await handle_rich_menu(user_id)
    
    if not await check_user_login(event, message):
        return

    # ===== [新增] 所有「/」開頭的訊息都交由 slash 指令分派器處理，不再 fall through 到 AI =====
    # Any message starting with "/" is routed through the slash-command dispatcher and
    # never falls through to the fallback guide AI. This guarantees that mistyped or
    # not-yet-implemented commands receive a clear "unknown command" reply rather than
    # an unrelated AI answer. Adding a new command only requires appending an entry to
    # the _SLASH_COMMANDS table near the bottom of this file.
    if message.startswith('/'):
        await _dispatch_slash_command(event, user_id, message)
        return

    if is_fallback_guide_enabled() and hasData(user_id):
        #Service4/5：對任意非指令文字訊息啟用引導型客服機器人回應。
        # Service4/5: respond to any non-command text message with the guide AI.
        await show_loading(user_id, secs=15)
        await handle_fallback_guide(event, user_id, message)


# ============================================================================
# Slash command dispatcher
# ============================================================================
# 設計目標 / Design goals
#   1. 任何以「/」開頭的訊息都會被攔截，不會交給 AI fallback guide 處理（避免
#      AI 機器人對「/unmagic」這類指令回覆「我只能回答課程相關問題」這類無關訊息）。
#   2. 用「最長別名優先」策略比對，未來若有 /something 與 /something_else 共存
#      也不會誤判（雖然目前 /magic vs /unmagic 因字頭不同其實沒有衝突問題）。
#   3. 新增指令時只需要：寫一個 async handler，然後在 _SLASH_COMMANDS 加一行。
#
#   1. Any message starting with "/" is intercepted by this dispatcher and is
#      NEVER sent to the fallback guide AI. This avoids the AI replying to typos
#      or unknown commands with unrelated answers.
#   2. Longest-alias-first matching prevents future commands sharing a prefix
#      from shadowing each other.
#   3. Adding a new command = write an async handler + add one row to
#      _SLASH_COMMANDS at the bottom of this section.


async def _cmd_unlink(event, user_id, _message):
    """指令：/unlink — 解除帳號綁定"""
    delData(user_id)
    await send_text_message(event, "已解除綁定！\nUnlinked!")


async def _cmd_magic(event, user_id, _message):
    """指令：/magic — 讓自己成為管理員"""
    await send_text_message(event, "你已變成管理員\nMagic!")
    await addAdmin(user_id)
    await save_config()


async def _cmd_unmagic(event, user_id, _message):
    """指令：/unmagic — 暫時移除自己的管理員身分，方便以學生視角測試"""
    if not isAdmin(user_id):
        await send_text_message(
            event,
            "你目前不是管理員，無需解除。\nYou are not currently an admin; nothing to remove."
        )
        return
    await removeAdmin(user_id)
    await save_config()
    # 切回預設主選單，方便立即以學生身分操作；切換失敗不影響權限變更。
    # Switch the user back to the default main menu for immediate student-view
    # testing; a switch failure does not affect the permission change.
    try:
        _default_menu_alias = 'menu_game' if config.get('rag_mode', False) else 'menu'
        _default_menu_id = get_rich_menu_id(_default_menu_alias)
        if _default_menu_id:
            await rich_menu_manager.link_rich_menu_to_user(user_id, _default_menu_id)
    except Exception as _e:
        print(f"[WARN] Failed to switch rich menu after /unmagic: {_e}")
    await send_text_message(
        event,
        "已移除管理員身分，現在以一般學生身分運作；輸入 /magic 可隨時恢復管理員。\n"
        "Admin status removed. You are now in regular student mode; type /magic anytime to regain admin."
    )


async def _cmd_refresh_menu(event, user_id, message):
    """指令：/refresh_menu <name> — 管理員專用，重建單一 rich menu（用於更換圖片）"""
    if not isAdmin(user_id):
        await send_text_message(event, "無權限！僅管理員可使用此指令。\nNo permission. Admins only.")
        return
    parts = message.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        await send_text_message(
            event,
            "用法：/refresh_menu <選單名稱>\n例如：/refresh_menu sel1\n\n"
            "Usage: /refresh_menu <menu_name>\nExample: /refresh_menu sel1"
        )
        return
    target_name = parts[1].strip()
    # Lazy import to avoid top-level cycles.
    from utils.message_utils import refresh_single_rich_menu
    await send_text_message(
        event,
        f"開始重建選單「{target_name}」，請稍候…\nRefreshing menu '{target_name}', please wait..."
    )
    ok, info = await refresh_single_rich_menu(target_name)
    await send_text_message(event, info)


async def _cmd_refresh_all_menus(event, user_id, _message):
    """指令：/refresh_all_menus — 管理員專用，強制重建全部 rich menu"""
    if not isAdmin(user_id):
        await send_text_message(event, "無權限！僅管理員可使用此指令。\nNo permission. Admins only.")
        return
    await send_text_message(
        event,
        "開始強制重建所有 rich menu，依選單數量約需 30-60 秒…\n"
        "Force rebuilding all rich menus, this takes ~30-60 seconds..."
    )
    from utils.message_utils import create_rich_menu as _rebuild_all
    try:
        await _rebuild_all(force_rebuild=True)
        await send_text_message(event, "全部 rich menu 已重建完成。\nAll rich menus rebuilt successfully.")
    except Exception as e:
        import traceback
        traceback.print_exc()
        await send_text_message(event, f"重建過程發生錯誤：{e}\nRebuild error: {e}")


async def _cmd_help(event, user_id, _message):
    """指令：/help — 列出可用指令"""
    is_user_admin = isAdmin(user_id)
    lines = ["可用指令 / Available commands:", ""]
    for aliases, _handler, desc_zh, desc_en, admin_only in _SLASH_COMMANDS:
        if admin_only and not is_user_admin:
            continue
        alias_str = " 或 ".join(aliases)
        suffix = " [admin]" if admin_only else ""
        lines.append(f"{alias_str}{suffix}")
        lines.append(f"  {desc_zh}")
        lines.append(f"  {desc_en}")
        lines.append("")
    await send_text_message(event, "\n".join(lines).rstrip())


# ----------------------------------------------------------------------------
# Slash 指令登錄表 (Slash command registry)
# 每筆: (別名 tuple, handler, 中文說明, 英文說明, 是否管理員專用)
# Each row: (aliases_tuple, handler, zh_desc, en_desc, admin_only)
# 加入新指令 = 上面寫個 _cmd_xxx，這裡加一行。
# To add a new command: write _cmd_xxx above, then append one row here.
# ----------------------------------------------------------------------------
_SLASH_COMMANDS = (
    (('/unlink', '/解除綁定'), _cmd_unlink,
     "解除帳號綁定",
     "Unbind your account",
     False),
    (('/magic', '/魔法'), _cmd_magic,
     "讓自己成為管理員",
     "Grant yourself admin status",
     False),
    (('/unmagic', '/解除魔法'), _cmd_unmagic,
     "移除自己的管理員身分（用於以學生視角測試）",
     "Remove your own admin status (useful for testing as a student)",
     False),
    (('/refresh_menu', '/重建選單'), _cmd_refresh_menu,
     "管理員專用：刪除並重建單一 rich menu，用於更換圖片或修正單一選單",
     "Admin only: delete and rebuild a single rich menu (useful after image updates)",
     True),
    (('/refresh_all_menus', '/全部重建選單'), _cmd_refresh_all_menus,
     "管理員專用：強制重建全部 rich menu（耗時較長）",
     "Admin only: force-rebuild every rich menu (takes longer)",
     True),
    (('/help', '/幫助'), _cmd_help,
     "顯示本指令清單",
     "Show this command list",
     False),
)


async def _dispatch_slash_command(event, user_id, message: str):
    """將「/」開頭的訊息分派至對應 handler；未知指令給出明確錯誤訊息。
    Dispatch a slash-prefixed message to the matching handler; emit a clear error
    for unknown commands.

    匹配規則：別名長度由長到短排序，要求訊息完全等於別名，或別名後緊接一個空白
    （後者用於支援帶參數的指令，例如 /refresh_menu sel1）。
    Matching: aliases are sorted longest-first; the message must equal the alias
    exactly OR start with `alias + ' '` (the latter supports commands with args
    such as /refresh_menu sel1).
    """
    pairs = []
    for aliases, handler, _zh, _en, _admin in _SLASH_COMMANDS:
        for alias in aliases:
            pairs.append((alias, handler))
    pairs.sort(key=lambda x: -len(x[0]))

    for alias, handler in pairs:
        if message == alias or message.startswith(alias + ' '):
            try:
                await handler(event, user_id, message)
            except Exception as e:
                import traceback
                traceback.print_exc()
                await send_text_message(
                    event,
                    f"指令執行錯誤：{e}\nCommand execution error: {e}"
                )
            return

    # 未知 / 字頭指令：明確回應，不要落入 AI fallback。
    # Unknown slash command: explicit reply, do NOT fall through to the AI.
    cmd_token = message.split(maxsplit=1)[0] if message else '/'
    await send_text_message(
        event,
        f"未知的指令：{cmd_token}\n輸入 /help 查看可用指令清單。\n\n"
        f"Unknown command: {cmd_token}\nType /help to see all available commands."
    )

def _build_privacy_notice_message():
    from linebot.v3.messaging import (
        FlexMessage, FlexBubble, FlexBox, FlexText, FlexSeparator, FlexButton, PostbackAction
    )
    chi_inform = "語音資料與AI處理同意聲明"
    eng_inform = "Consent for Voice Data Use and AI Processing"
    chi_text = "本人同意於本課程中使用「CoachGPT AI情境解謎聊天機器人」時，提供之口說錄音資料供研究者用於教學分析與學術研究。本系統使用第三方 AI 技術（例如 ChatGPT）進行語音辨識與評分，語音資料可能會傳送至相關系統進行處理。使用者可獲得 AI 即時回饋，聊天機器人將提供英語口說改進之方法與具體建議。研究團隊將妥善保護資料安全，並以匿名方式使用，不會揭露個人身分。本人可選擇不提供錄音或隨時停止使用相關功能，且不影響課程成績或權益。同意上述聲明者可繼續進行帳號綁定；不同意者可選擇退出。"
    eng_text = "I consent to providing my voice recordings while using the CoachGPT AI Scenario-Based Chatbot” for teaching analysis and academic research. This system uses third-party AI technologies (e.g., ChatGPT) for speech recognition and evaluation, and my data may be transmitted to external systems for processing. I will receive real-time AI feedback and suggestions for improving my English speaking. All data will be securely protected and anonymized without revealing my identity. I may choose not to provide recordings or stop using the features at any time without affecting my grade or rights. By agreeing, I may proceed with account binding; otherwise, I may choose to exit."
    
    bubble = FlexBubble(
        size='giga',
        body=FlexBox(
            layout='vertical',
            spacing='md',
            contents=[
                FlexText(
                    text='重要告知 / Important Notice',
                    wrap=True,
                    weight='bold',
                    size='xl',
                    color='#cc0000',
                    align='center',
                ),
                FlexSeparator(margin='md'),
                FlexText(
                    text=chi_inform,
                    wrap=True,
                    weight='bold',
                    size='md',
                    color='#333333',
                    margin='md',
                ),
                FlexText(
                    text=chi_text,
                    wrap=True,
                    size='sm',
                    color='#333333',
                    margin='md',
                ),
                FlexSeparator(margin='md'),
                FlexText(
                    text=eng_inform,
                    wrap=True,
                    weight='bold',
                    size='md',
                    color='#333333',
                    margin='md',
                ),
                FlexText(
                    text=eng_text,
                    wrap=True,
                    size='sm',
                    color='#333333',
                    margin='md',
                ),
            ]
        ),
        footer=FlexBox(
            layout='vertical',
            spacing='sm',
            contents=[
                FlexButton(
                    style='primary',
                    color='#00aa00',
                    action=PostbackAction(label='我同意 / I agree', data='action=consent&agree=true')
                ),
                FlexButton(
                    style='primary',
                    color='#dd0000',
                    action=PostbackAction(label='我不同意 / I disagree', data='action=consent&agree=false')
                )
            ]
        )
    )
    return FlexMessage(altText='重要告知 / Important Notice', contents=bubble)


def _build_consent_declined_message():
    from linebot.v3.messaging import (
        FlexMessage, FlexBubble, FlexBox, FlexText, FlexButton, PostbackAction
    )
    chi_text = "您已拒絕AI處理您的語音資料，因為本機器人旨在透過AI輔導學生從情境式解謎遊戲過程中，提升其英語口說能力，因此同意本條款為使用此機器人的必要條件。若您想重新查看「語音資料與AI處理同意聲明」，請點擊下方按鈕。"
    eng_text = "You have declined AI processing of your voice data. Since this chatbot aims to tutor students and improve their English speaking skills through an AI-assisted scenario-based puzzle game, agreeing to these terms is a necessary condition for using this chatbot. If you wish to review the 'Consent for Voice Data Use and AI Processing' again, please click the button below."
    
    bubble = FlexBubble(
        size='giga',
        body=FlexBox(
            layout='vertical',
            spacing='md',
            contents=[
                FlexText(
                    text='Consent Declined / 已拒絕授權',
                    wrap=True,
                    weight='bold',
                    size='xl',
                    color='#cc0000',
                    align='center',
                ),
                FlexText(
                    text=chi_text,
                    wrap=True,
                    size='sm',
                    color='#333333',
                    margin='md',
                ),
                FlexText(
                    text=eng_text,
                    wrap=True,
                    size='sm',
                    color='#333333',
                    margin='md',
                )
            ]
        ),
        footer=FlexBox(
            layout='vertical',
            spacing='sm',
            contents=[
                FlexButton(
                    style='primary',
                    color='#0066cc',
                    action=PostbackAction(label='再次查看 / View Again', data='action=consent_view')
                )
            ]
        )
    )
    return FlexMessage(altText='Consent Declined / 已拒絕授權', contents=bubble)


async def check_user_login(event, message: str = None) -> bool:
    user_id = event.source.user_id
    
    if hasData(user_id):
        return True
    
    # 如果使用者尚未同意聲明（也就是尚未進到資料填寫階段），阻擋所有對話強制他們同意
    if user_id not in user_data_enter:
        await send_message(event, _build_privacy_notice_message())
        return False
    
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
        
        # 綁定成功後，僅顯示歡迎訊息不再重複推送同意條款卡片
        await send_message(event, [
            await text_message(f"綁定完成 你好! {message}\nSuccess! Hello, {message}!\n\n請點擊訊息輸入框左側的三條橫槓圖示，以切換至選單開始使用此CoachGPT聊天機器人。\nTap the three-bar icon to the left of the input field to switch to the menu and start using the CoachGPT Chatbot."),
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

            standard_section_pp = build_standard_section_for_audio(
                question.assessment_standard, is_sel=False
            )

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
                                   f"{standard_section_pp}"
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
            # Service4/5：對無法識別類別的語音訊息，轉錄後由引導型客服機器人回應。
            # Service4/5: transcribe unmatched audio and pass to guide AI.
            if is_fallback_guide_enabled():
                try:
                    message_content_fb = await get_audio_content(event)
                    if message_content_fb:
                        text_fb = await transcribe_audio(message_content_fb, language="en")
                        if text_fb:
                            await handle_fallback_guide(event, user_id, text_fb)
                            return
                except Exception as _fb_err:
                    print(f"Fallback guide audio error: {_fb_err}")
            return
        
        if not isEnabled(category) and not isAdmin(user_id):
            await send_text_message(event, "該區塊功能尚未開放。\nThis feature has not been unlocked yet.")
            return
        
        sub = user_state.sub
        
        if sub == -1:
            await send_text_message(event, "請選擇單元。\nPlease select a unit.")
            return
        
        question = question_manager.get_question(category, sub)

        # SEL 作答語言判斷（提前到轉錄之前，因為轉錄語言需依此決定）。
        # 'chi' = 用中文作答（中文轉錄、全中文回饋、不評英文文法、不給建議回答）。
        # 'eng' = 用英文作答（英文轉錄、中英對照回饋）。未選擇預設為中文。
        # Determine the SEL answering language up front (transcription language depends on it).
        _is_sel = _is_sel_category(category)
        _sel_language = None
        if _is_sel:
            _sel_language = getattr(user_state, 'sel_language', None) or 'chi'
        # SEL 中文模式以中文轉錄；其餘（含英文 SEL 與一般練習）維持英文轉錄。
        # Chinese SEL mode transcribes in Chinese; everything else stays in English.
        _transcribe_lang = 'zh' if (_is_sel and _sel_language == 'chi') else 'en'

        try:
            message_content = await get_audio_content(event)
            if not message_content:
                await send_text_message(event, "無法獲取音訊內容，請稍後再試。\nUnable to get audio content, please try again later.")
                return
            text = await transcribe_audio(message_content, language=_transcribe_lang)
        except Exception as e:
            await send_text_message(event, "文字轉錄發生錯誤，請稍後再試。\nAn error occurred, please try again later.")
            print(e)
            return
    
        if not text or len(text) < 1:
            await send_text_message(event, "無法獲取音訊內容，請稍後再試。\nUnable to get audio content, please try again later.")
            print('No text found in audio')
            return
        
        # SEL（'sel' 或多單元 'sel1'..'sel6'）改用以 SEL 五大核心能力為主軸的評分提示詞，
        # 並依作答語言（中 / 英）選擇對應版本；其餘練習維持原本的 SYSTEM_INSTRUCTION。
        # SEL now uses an SEL-competency-based evaluation prompt selected by answering language;
        # all other exercises keep using SYSTEM_INSTRUCTION.
        if _is_sel:
            _system_prompt_for_audio = build_sel_system_instruction(_sel_language)
        else:
            _system_prompt_for_audio = SYSTEM_INSTRUCTION

        # SEL 中文作答模式不附上 <standard>（題庫的十級參考答案為英文，對中文作答不適用）。
        # 其餘情況維持原本行為（SEL 英文模式仍展開十級 few-shot；一般練習照舊）。
        # In SEL Chinese mode, skip the <standard> section (the tiered English references do not
        # apply to Chinese answers). Otherwise keep the original behaviour.
        if _is_sel and _sel_language == 'chi':
            standard_section = ""
        else:
            standard_section = build_standard_section_for_audio(
                question.assessment_standard, is_sel=_is_sel
            )

        # [新增] SEL：帶入該生「同一題」先前每一次的作答紀錄，讓 AI 將歷次回答視為同一段
        # 持續完善的答案來合併評分，避免引導後的片段式補充因脫離題目脈絡而被低估，
        # 使最終分數能忠實反映學生對該題的實際表達內容。
        # 此處在 updateHistory 之前讀取，因此只包含本次之前的歷史，不含當前作答。
        # For SEL, feed the student's previous attempts on THIS SAME question so the AI can treat
        # all attempts as one evolving answer and score the combined expression. Read before
        # updateHistory, so it contains only prior attempts (not the current one).
        previous_attempts_section = ""
        if _is_sel:
            _prev = getHistory(user_id, f'{category}-{sub}') or []
            _prev_lines = [
                f"  Attempt {i + 1}: {a.transcript}"
                for i, a in enumerate(_prev)
                if getattr(a, 'transcript', '')
            ]
            if _prev_lines:
                previous_attempts_section = (
                    "<previousAttempts>\n" + "\n".join(_prev_lines) + "\n</previousAttempts>"
                )

        completion = await client.beta.chat.completions.parse(
            model="gpt-4o",
            response_format=SpeechAssessment,
            max_completion_tokens=2048,
            temperature=1,
            messages=[
                {
                    "role": "system",
                    "content": _system_prompt_for_audio,
                },
                {
                    "role": "user",
                    "content": f"<question>{question.text}</question>" \
                               f"{standard_section}" \
                               f"{previous_attempts_section}" \
                               f"<userAnswer>{text}</userAnswer>" \
                               f"{f'<maxScore>{question.max_score}</maxScore>' if question.max_score else ''}",
                }
            ],
        )
        
        assessment = completion.choices[0].message.parsed
        assessment.transcript = text
        assessment.timestamp = time.time()

        # SEL 一律不提供「建議回答」(better_ans)，避免框架住學生回應；
        # 中文作答模式同時清空英文回饋，確保只給中文回饋。
        # SEL never provides a "suggested answer" (better_ans); in Chinese mode also clear the
        # English feedback so only Chinese feedback is shown.
        if _is_sel:
            assessment.better_ans = ""
            if _sel_language == 'chi':
                assessment.eng_suggestion = ""
        
        history_key = f'{category}-{sub}'
        updateHistory(user_id, history_key, assessment)
        
        if should_show_feedback(category):
            await send_message(event, await result_message(assessment, category, sub, show_feedback=True, sel_language=_sel_language))
        else:
            await send_message(event, await result_message(assessment, category, sub, show_feedback=False, sel_language=_sel_language))
        
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
        
        # [修正] 補上 NPC 對話用的 history_key，原本在後續 Phase 2 評估呼叫中被引用但未定義。
        # Define history_key here; it was referenced by the Phase 2 evaluation task but never set.
        history_key = f'{theme_id}-npc-{npc_idx}'
        
        # Get RAG context
        rag_path = os.path.join("category", "rag_docs", theme_id, npc_info["file"])
        if not os.path.exists(rag_path):
            rag_path = os.path.join("category", "rag_docs", theme_id)
        
        context_content = await get_rag_context_v2(rag_path, query=text)
        
        # Get chat history
        # 使用即時記憶快取取代 SpeechAssessment 歷史，解決 Phase 2 非同步儲存的競態問題。
        # 快取在 Phase 1 回覆生成後立即更新，確保下一輪對話能正確看到本輪的內容。
        # Use in-memory cache instead of persisted history to avoid Phase 2 async race condition.
        # Cache is updated immediately after Phase 1 reply so next turn sees current conversation.
        history_str = get_npc_chat_memory(user_id, theme_id, npc_idx, npc_info['name'])
        
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

        # 立即將本輪對話存入即時記憶快取，使下一輪 Phase 1 能看到本輪內容。
        # Immediately save this turn to in-memory cache so the next Phase 1 sees it.
        append_npc_chat_memory(user_id, theme_id, npc_idx, text, quick_res.npc_reply)

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
        # 僅在逐關解鎖模式 (one_by_one=True) 顯示解鎖通知；
        # 開放模式下所有關卡本就開放，顯示解鎖訊息會造成誤解，故略過。
        # Only show the unlock notice in sequential mode; in open mode all levels are already
        # available, so the unlock message would be misleading and is skipped.
        if unlocked and is_one_by_one():
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
    user_state = get_user_state(user_id)
    if not history:
        history = ChatHistory()
    
    history.questions.append(text)
    
    # [新增] 根據使用者目前所選的 chat 主題（user_state.sub）附加主題專屬提示詞。
    # 若使用者尚未選擇主題（sub < 0），則回傳空字串，AI 走一般對話模式。
    # 僅在 service4/5 (rag_mode) 啟用主題感知，避免改變 service1/2/3 的原始行為。
    #
    # Append topic-specific prompt fragment based on the user's selected chat topic
    # (user_state.sub). If no topic is selected, the fragment is an empty string and the
    # AI behaves in generic conversation mode. Topic awareness is gated to service4/5
    # (rag_mode) to preserve the original behavior of service1/2/3.
    _topic_prompt = ""
    if config.get('rag_mode', False) and user_state is not None:
        _topic_prompt = get_chat_topic_system_prompt(user_state.sub)

    base_prompt = f"""You are a friendly and helpful AI English-speaking coach for college students who are non-native speakers in Taiwan. 
            Their names are {user.name}.
            Your job is to engage in natural, supportive conversations that help them practice speaking.

            Style: Speak in short, friendly sentences like a native English speaker. Use casual but clear language.
            When correcting grammar:
            - If there's a mistake, gently correct it while maintaining conversation flow
            - For severe errors, provide the correction naturally in your response
            
            Keep responses under 60 words unless explaining something complex. Do not use bullet points, markdown, or formatted text - just natural conversational language.

            If asked about topics you don't know, just say you're not sure. Don't mention being an AI assistant.
            """
    if _topic_prompt:
        base_prompt = base_prompt + "\n\n" + _topic_prompt

    messages = [
        {
            "role": "system",
            "content": base_prompt,
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

    data = event.postback.data
    params = dict(p.split('=') for p in data.split('&'))
    action = params.get('action')
    vars = {k: v for k, v in params.items() if k != 'action'}
    
    if action == 'consent':
        if hasData(user_id):
            return
        agree = vars.get('agree')
        if agree == 'true':
            if user_id not in user_data_enter:
                user_data_enter[user_id] = []
                await send_message(event, await info_hint_message(0))
            else:
                info = user_data_enter[user_id]
                await send_message(event, await info_hint_message(len(info)))
        else:
            if user_id in user_data_enter:
                del user_data_enter[user_id]
            await send_message(event, _build_consent_declined_message())
        return
    elif action == 'consent_view':
        if hasData(user_id):
            return
        await send_message(event, _build_privacy_notice_message())
        return
    
    if not await check_user_login(event):
        return
    
    user_state = get_user_state(user_id)
    if not user_state:
        return
    
    if action == 'chat':
        if vars.get('summary'):
            await handle_chat_summary(event)
        elif 'sub' in vars:
            # [新增] 使用者點擊 chat rich menu 中的主題按鈕（旅遊 / 運動 / 面試 / 英語技巧）。
            # 將該主題索引存入 user_state.sub，後續 send_audio_request 會依此調整 AI 系統提示詞。
            # User picked a chat topic button (Travel / Sports / Interview / English Skills).
            # Save the topic index into user_state.sub so the subsequent AI system prompt
            # can be tailored in send_audio_request.
            try:
                sub = int(vars.get('sub'))
            except (TypeError, ValueError):
                sub = -1
            if not isEnabled('chat') and not isAdmin(user_id):
                await send_text_message(event, "該區塊功能尚未開放。\nThis feature has not been unlocked yet.")
                return
            user_state.category = 'chat'
            user_state.sub = sub
            # 傳送中英對照的主題確認訊息（英文在前、中文在後）。
            # Send the bilingual topic confirmation message (English first, Chinese second).
            await send_message(event, await chat_topic_intro_message(sub))
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
            await send_message(event, await new_test_question_message(user_id, sub, base, show_feedback=should_show_feedback(base)))
            return
        _record_cat = get_enabled_category_for_alias(user_state.category)
        if not isEnabled(_record_cat) and not isAdmin(user_id):
            await send_text_message(event, "該區塊功能尚未開放。\nThis feature has not been unlocked yet.")
            return
        user_state.sub = sub
        # SEL 題目卡片依使用者選擇的作答語言（中 / 英）顯示；
        # 非 SEL 類別 sel_language 傳 None，行為完全不變。
        # SEL question cards render in the chosen answering language; non-SEL passes None.
        _record_sel_lang = getattr(user_state, 'sel_language', None) if _is_sel_category(user_state.category) else None
        await send_message(event, await question_message(user_id, user_state.category, sub, show_feedback=should_show_feedback(user_state.category), sel_language=_record_sel_lang))
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
        # 後台關閉回饋時，即使 postback 被直接觸發也拒絕顯示詳細回饋
        # Block detailed feedback when admin has disabled it, even if postback is triggered directly
        if not should_show_feedback(category):
            await send_text_message(event, "此單元目前不提供詳細回饋。\nDetailed feedback is not available for this section.")
            return
        await send_message(event, await result_message(result[-1], category, sub))
        
    elif action == 'switch':
        alias = vars.get('to')
        if alias in ['admin', 'game_admin'] and not isAdmin(user_id):
            await send_text_message(event, '無權限!\nNo permission!')
            return
        
        # [新增] 保存切換前所在的類別，供後續邏輯判斷使用（例如：判斷是否該補送 chat 進入提示）。
        # Capture the category the user was on BEFORE the switch, used by downstream logic
        # (e.g. deciding whether to send the chat welcome card).
        previous_category = user_state.category

        # RAG mode menu switch logic
        is_rag = config.get('rag_mode', False)
        if alias == 'menu':
            # [新增] service4/5 (rag_mode=true) 中，若使用者目前位於 chat 區塊，
            # 「menu」按鈕應回到 menu_other，而非主選單 menu_game。
            # In service4/5 (rag_mode=true), when the user is currently on the chat menu,
            # the "menu" button should return to menu_other rather than the top menu_game.
            if is_rag and previous_category == 'chat':
                alias = 'menu_other'
            elif is_rag:
                alias = 'menu_game'
        elif alias == 'menu_game':
            if not is_rag:
                alias = 'menu'

        _switch_enabled_cat = get_enabled_category_for_alias(alias)
        _SWITCH_CONTROLLED = {
            'pretest', 'posttest', 'rag_test',
            'ex1', 'ex2', 'ex3', 'ex4', 'ex5', 'ex6',
            'chat', 'sel',
            'sel1', 'sel2', 'sel3', 'sel4', 'sel5', 'sel6',
        }
        if alias not in ['menu_other'] and _switch_enabled_cat in _SWITCH_CONTROLLED and not isEnabled(_switch_enabled_cat):
            await send_text_message(event, "此區塊尚未開放作答或使用，請等待老師開啟。\nThis section is not yet open for answering or use. Please wait for your teacher to enable it.")
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
        # [新增] 進入 chat 區時主動發送中英對照歡迎訊息，但若使用者從語音設定（audio/sex/accent）
        # 或已在 chat 內返回，則略過，避免重複打擾。
        # When entering the chat section, proactively send the bilingual welcome message,
        # but skip it when the user is bouncing back from audio settings or is already on chat,
        # to avoid repeated notices.
        if alias == 'chat' and is_rag and previous_category not in ('chat', 'audio', 'sex', 'accent'):
            await send_message(event, await chat_welcome_message())
            return
        # [新增 (SEL 多單元)] 進入單一 SEL 單元 (sel1..sel6) 時，主動發送該單元的介紹卡片，
        # 取代原本針對有題目類別會自動彈出的題目輪播。
        # When entering a single SEL unit (sel1..sel6), send the unit intro card instead of the
        # default question carousel that would otherwise auto-pop for categories with questions.
        if alias in ('sel1', 'sel2', 'sel3', 'sel4', 'sel5', 'sel6'):
            try:
                unit_num = int(alias.replace('sel', ''))
            except ValueError:
                unit_num = 1
            user_state.sub = -1
            # 依使用者已選的作答語言顯示介紹卡（未選擇預設中文）。
            # Show the intro card in the chosen answering language (defaults to Chinese).
            _sel_lang = getattr(user_state, 'sel_language', None) or 'chi'
            await send_message(event, await sel_unit_intro_message(unit_num, language=_sel_lang))
            return
        if any(alias.startswith(p) for p in _NO_POPUP_PREFIXES):
            pass
        elif alias in ('chat', 'admin', 'game_admin', 'sel', 'sel-2'):
            # chat 與 sel 系列大廳頁面（unit selection）不自動彈題目；交由其他邏輯處理。
            # chat and SEL lobby pages (unit selection) do not auto-pop a question carousel.
            pass
        elif question_manager.has_question(user_state.category):
            await send_message(event, await carousel_message(user_id, user_state.category, 0))

    elif action == 'progress':
        await send_message(event, await progress_message(user_id))

    # ===== [新增 (SEL 多單元)] SEL 單元選擇 =====
    # 使用者在 'sel' / 'sel-2' rich menu 點擊單元按鈕後觸發。
    # 將使用者切到該單元的 rich menu (sel1..sel6) 並送出該單元的介紹卡片。
    # User taps a unit button in the 'sel' / 'sel-2' rich menu; switch them to the
    # individual unit menu (sel1..sel6) and show that unit's bilingual intro card.

    elif action == 'sel_unit':
        try:
            unit_num = int(vars.get('unit', 1))
        except (TypeError, ValueError):
            unit_num = 1
        if unit_num < 1 or unit_num > 6:
            await send_text_message(event, "未知的 SEL 單元。\nUnknown SEL unit.")
            return

        unit_category = f'sel{unit_num}'
        # 每個單元獨立開關控制；管理員不受此限制（與其他類別一致）。
        # Per-unit enable gate; admins bypass (consistent with other categories).
        if not isEnabled(unit_category) and not isAdmin(user_id):
            await send_text_message(event, "該單元尚未開放，請等待老師開啟。\nThis unit is not yet open. Please wait for your teacher to enable it.")
            return

        # 切換至該單元的 rich menu。若該 rich menu 尚未註冊，提示管理員處理。
        # Switch the user to that unit's rich menu. If the rich menu has not been
        # registered yet, prompt the admin to reload.
        rich_menu_id = get_rich_menu_id(unit_category)
        if rich_menu_id:
            try:
                await rich_menu_manager.link_rich_menu_to_user(user_id, rich_menu_id)
            except Exception as _link_err:
                print(f"[WARN] Failed to link SEL unit rich menu: {_link_err}")
        else:
            await send_text_message(
                event,
                f"Menu '{unit_category}' is not registered. Please ask admin to reload.\n"
                f"Menu '{unit_category}' 尚未註冊，請通知管理員重新載入。"
            )
            return

        user_state.category = unit_category
        user_state.sub = -1
        user_state.in_npc_chat = False

        # 進入 SEL 單元時，若開啟語言選擇功能，先以卡片詢問要用中文或英文作答；
        # 重設本次的作答語言，待使用者點選後再以對應語言顯示介紹卡與題目。
        # 若功能關閉，預設以中文作答並直接顯示介紹卡。
        # On entering a SEL unit, if language selection is enabled, show the language-choice
        # card first (resetting the per-entry language). If disabled, default to Chinese and
        # show the intro card directly.
        if is_sel_language_selection_enabled():
            user_state.sel_language = None
            await send_message(event, await sel_language_select_message(unit_num))
        else:
            user_state.sel_language = 'chi'
            await send_message(event, await sel_unit_intro_message(unit_num, language='chi'))

    # ===== [新增 1] SEL 作答語言選擇 (Chinese / English) =====
    # 使用者在語言選擇卡片點選「用中文 / 用英文作答」後觸發。
    # 將選擇存入 user_state.sel_language，並以對應語言顯示該單元的介紹卡片。
    # Triggered when the user taps a language button on the SEL language-selection card.
    # Stores the choice in user_state.sel_language and shows the unit intro card in that language.

    elif action == 'sel_lang':
        lang = vars.get('lang', 'chi')
        lang = 'eng' if lang == 'eng' else 'chi'
        try:
            unit_num = int(vars.get('unit', 1))
        except (TypeError, ValueError):
            unit_num = 1
        if unit_num < 1 or unit_num > 6:
            unit_num = 1

        unit_category = f'sel{unit_num}'
        # 與 sel_unit 一致的開關保護；管理員 bypass。
        # Same enable gate as sel_unit; admins bypass.
        if not isEnabled(unit_category) and not isAdmin(user_id):
            await send_text_message(event, "該單元尚未開放，請等待老師開啟。\nThis unit is not yet open. Please wait for your teacher to enable it.")
            return

        user_state.category = unit_category
        user_state.sub = -1
        user_state.in_npc_chat = False
        user_state.sel_language = lang
        await send_message(event, await sel_unit_intro_message(unit_num, language=lang))

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
        await send_message(event, await new_test_question_message(user_id, sub, base, show_feedback=should_show_feedback(base)))

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
        # 後台關閉回饋時，即使 postback 被直接觸發也拒絕顯示詳細回饋
        # Block detailed feedback when admin has disabled it, even if postback is triggered directly
        if not should_show_feedback(base):
            await send_text_message(event, "此單元目前不提供詳細回饋。\nDetailed feedback is not available for this section.")
            return
        await send_message(event, await result_message(result[-1], section_category, sub))

    # ===== NPC 顯示文字 (語音模式) =====

    elif action == 'game_show_npc_text':
        last_info = get_last_npc_reply(user_id)
        if not last_info:
            await send_text_message(event, "找不到最近的 NPC 回覆。\nNo recent NPC reply found.")
            return
        # 當語音輸出功能開啟時，記錄使用者使用「顯示文字」的次數，以供研究分析。
        # Track 'Show Text' usage when npc_voice_output is enabled, for research analysis.
        if config.get('npc_voice_output', False):
            new_count = increment_show_text_count(user_id)
            print(f"[STAT] User {user_id} used Show Text feature (total: {new_count} times)")
            await save_user_data()
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
        # 選單「作答」按鈕：跳到最前面（關卡較低、題號較低）尚未作答任何一次的題目，
        # 鼓勵學生把每一題都至少作答一次。若所有題目皆已作答過，回報已全部作答。
        # The menu "Answer" button jumps to the earliest question never answered yet
        # (lowest level, lowest question). If every question has been answered at least once,
        # report that all questions have been attempted.
        theme_id = vars.get('theme', user_state.game_theme)
        if not theme_id:
            await send_text_message(event, "請先選擇主題。\nPlease select a topic first.")
            return
        
        # Find the earliest never-answered question across all levels
        level_idx, question_idx = get_first_never_answered_question_global(user_id, theme_id)
        
        if level_idx == -1 and question_idx == -1:
            # Every question has already been answered at least once
            await send_text_message(event, "所有題目都已經作答過囉！你仍可從關卡選單挑選任一題再次挑戰。\nYou have already answered every question at least once! You can still pick any question from the level menu to try again.")
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