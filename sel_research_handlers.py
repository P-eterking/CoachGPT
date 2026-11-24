import asyncio
import logging
import os
import time
from functools import lru_cache
from uuid import uuid4
from weakref import WeakValueDictionary

from config import client
from utils.file_utils import get_user_state, getUser, save_user_data, should_show_feedback
from utils.message_utils import send_message, send_text_message, text_message
from utils.models import SpeechAssessment
from utils.sel_research import MenuSELSession, ResearchSession, load_bank, next_research_step

_locks: WeakValueDictionary[str, asyncio.Lock] = WeakValueDictionary()
_logger = logging.getLogger(__name__)
_bank = lru_cache(maxsize=1)(load_bank)


def research_enabled() -> bool:
    return os.getenv("SEL_RESEARCH_ENABLED") == "1"


def _user_lock(user_id: str) -> asyncio.Lock:
    return _locks.setdefault(user_id, asyncio.Lock())


def _predates_selection(event, state) -> bool:
    timestamp = getattr(event, "timestamp", None)
    return timestamp is not None and state.sel_selected_at is not None and timestamp < state.sel_selected_at


def _session_message(session: ResearchSession | MenuSELSession) -> str:
    menu = isinstance(session, MenuSELSession)
    label = f"Q{session.sub + 1}" if menu else f"第 {session.week} 週《{session.game}》"
    heading = label if menu else f"{label}｜{session.dimension}"
    if session.status == "insufficient":
        return f"{label} 已記為資料不足。"
    if session.result is not None:
        score = f"{heading}\n{session.result.score}／10 分"
        return f"{score}\n{session.result.suggestion}" if not menu or should_show_feedback(session.category) else score
    if session.followup_question:
        return f"補問｜{session.followup_question}\n可直接打字或錄音補充。"
    return (
        f"{heading}\n"
        f"{session.question}\n可用中文錄音或打字回答，也可輸入 /sel 略過 或 /sel 離開。"
    )


async def _send_session_reply(event, session: ResearchSession | MenuSELSession) -> None:
    await send_text_message(event, _session_message(session))
    # A redelivery uses the original one-use reply token.
    session.pending_reply_id = None


def _selected_session(user, state):
    if state.sel_menu_session_id is not None:
        return user.sel_menu_sessions, state.sel_menu_session_id
    return user.sel_teacher_sessions, state.sel_research_week


async def _save_session(user, records, key, session) -> None:
    previous = records.get(key)
    history_key = None
    previous_history = None
    if isinstance(session, MenuSELSession) and session.result is not None and (previous is None or previous.result is None):
        history_key = f"{session.category}-{session.sub}"
        previous_history = user.history.get(history_key)
        summary = SpeechAssessment(
            score=session.result.score,
            transcript="\n".join(part for part in (session.primary, session.followup) if part),
            chi_suggestion=session.result.suggestion,
            eng_suggestion="",
            timestamp=time.time(),
        )
        user.history[history_key] = [*(previous_history or []), summary]
    records[key] = session
    try:
        await save_user_data()
    except Exception:
        if previous is None:
            del records[key]
        else:
            records[key] = previous
        if history_key is not None:
            if previous_history is None:
                del user.history[history_key]
            else:
                user.history[history_key] = previous_history
        raise


async def begin_menu_question(event, user_id: str, category: str, sub: int, question: str, language, card) -> None:
    user = getUser(user_id)
    state = get_user_state(user_id)
    if user is None or state is None:
        return
    async with _user_lock(user_id):
        if _predates_selection(event, state):
            return
        event_id = getattr(event, "webhook_event_id", None) or uuid4().hex
        sessions = user.sel_menu_sessions
        delivery = next((
            (key, attempt) for key, attempt in reversed(sessions.items())
            if attempt.card_event_id == event_id
        ), None)
        if delivery is not None:
            session_id, session = delivery
            if not session.card_pending:
                return
            if (session.category, session.sub, session.question, session.language) != (category, sub, question, language):
                await send_text_message(event, "題目或作答語言已切換，請重新點選原題。")
                return
        else:
            if event_id in sessions:
                return
            previous = next((
                (key, attempt) for key, attempt in reversed(sessions.items())
                if (attempt.category, attempt.sub, attempt.question, attempt.language) == (category, sub, question, language)
                and (attempt.status == "pending" or attempt.pending_reply_id is not None or attempt.card_pending)
            ), None)
            if previous is None:
                session_id = event_id
                session = MenuSELSession(category=category, sub=sub, question=question, language=language)
            else:
                session_id, session = previous
            session = session.model_copy(update={"card_event_id": event_id, "card_pending": True})
            await _save_session(user, sessions, session_id, session)

        state.sel_research_week = None
        state.sel_menu_session_id = None
        state.sel_selected_at = getattr(event, "timestamp", state.sel_selected_at)
        messages = [card]
        if session.followup_question or session.status != "pending":
            messages.append(await text_message(_session_message(session)))
        await send_message(event, messages)
        state.sel_menu_session_id = session_id
        state.sub = sub

        # LINE reply tokens can only be used once, so keep the confirmed delivery in memory
        # even if persisting this acknowledgement fails.
        session.card_pending = False
        session.pending_reply_id = None
        await save_user_data()


async def research_command(event, user_id: str, message: str) -> None:
    if not research_enabled():
        await send_text_message(event, "SEL 研究對答尚未開放。")
        return
    user = getUser(user_id)
    state = get_user_state(user_id)
    if user is None or state is None:
        return

    arg = message.partition(" ")[2].strip()
    async with _user_lock(user_id):
        if _predates_selection(event, state):
            return
        selected_at = getattr(event, "timestamp", state.sel_selected_at)
        if arg == "離開":
            state.sel_research_week = None
            state.sel_menu_session_id = None
            state.sel_selected_at = selected_at
            reply = "已離開 SEL 對答。重新點選原題或輸入原週次即可繼續。"
        elif arg == "略過":
            records, key = _selected_session(user, state)
            session = records.get(key)
            if session is None or session.status != "pending":
                reply = "請先點選 SEL 題目或輸入 /sel 與本週的週次。"
            else:
                session = session.model_copy(update={"status": "insufficient", "missing_reason": "skipped", "pending_reply_id": None})
                await _save_session(user, records, key, session)
                state.sel_research_week = None
                state.sel_menu_session_id = None
                state.sel_selected_at = selected_at
                reply = _session_message(session)
        elif arg in {str(week) for week in _bank().weeks}:
            week = int(arg)
            session = user.sel_teacher_sessions.get(week)
            if session is None:
                item = _bank().weeks[week]
                session = ResearchSession(week=week, game=item.game, dimension=item.dimension, question=item.question)
                await _save_session(user, user.sel_teacher_sessions, week, session)
            state.sel_menu_session_id = None
            state.sel_research_week = week if session.status == "pending" else None
            state.sel_selected_at = selected_at
            await _send_session_reply(event, session)
            return
        else:
            reply = "請輸入 /sel 與本週的週次（第 4–15 週），例如 /sel 13。"
    await send_text_message(event, reply)


async def close_research_input(user_id: str, event) -> bool:
    if research_enabled():
        async with _user_lock(user_id):
            state = get_user_state(user_id)
            if state is not None:
                if _predates_selection(event, state):
                    return False
                state.sel_research_week = None
                state.sel_menu_session_id = None
                state.sel_selected_at = getattr(event, "timestamp", state.sel_selected_at)
    return True


async def handle_research_input(event, user_id: str, read_answer) -> bool:
    if not research_enabled():
        return False
    async with _user_lock(user_id):
        user = getUser(user_id)
        state = get_user_state(user_id)
        if user is None or state is None:
            return False
        records, key = _selected_session(user, state)
        session = records.get(key)
        message_id = str(event.message.id)
        previous = next((
            entry
            for attempts in (user.sel_menu_sessions, user.sel_teacher_sessions, user.sel_research_sessions)
            for entry in attempts.values()
            if message_id in (entry.primary_message_id, entry.followup_message_id)
        ), None)
        if previous is not None:
            if previous is session and previous.pending_reply_id == message_id:
                await _send_session_reply(event, previous)
                if isinstance(previous, ResearchSession) and previous.status != "pending":
                    state.sel_research_week = None
            return True
        if session is None:
            return False
        if _predates_selection(event, state):
            await send_text_message(event, "這則回答是在目前這題開啟前送出的。請選回原題後再傳一次。")
            return True
        menu = isinstance(session, MenuSELSession)
        if session.pending_reply_id is not None:
            resume = f"再按一次 Q{session.sub + 1}" if menu else f"輸入 /sel {session.week}"
            await send_text_message(event, f"請先{resume}取得尚未送出的補問或評分。")
            return True
        if session.status != "pending":
            if menu:
                await send_text_message(event, f"這次 Q{session.sub + 1} 已結束。再點一次題目就能重新作答。")
            return menu

        try:
            answer = (await read_answer(session.language if menu else "zh")).strip()
            updated = await next_research_step(client, _bank(), session, answer, message_id)
            updated.pending_reply_id = message_id
            await _save_session(user, records, key, updated)
        except Exception as error:
            _logger.warning("SEL answer failed (%s)", type(error).__name__)
            await send_text_message(event, "這次對答暫時處理失敗，請重新傳送剛才的回答。")
            return True
        await _send_session_reply(event, updated)
        if not menu and updated.status != "pending":
            state.sel_research_week = None
        return True
