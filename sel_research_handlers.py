import asyncio
import logging
import os
from functools import lru_cache
from weakref import WeakValueDictionary

from config import client
from utils.file_utils import get_user_state, getUser, save_user_data
from utils.message_utils import send_text_message
from utils.sel_research import ResearchSession, load_bank, next_research_step

_locks: WeakValueDictionary[str, asyncio.Lock] = WeakValueDictionary()
_logger = logging.getLogger(__name__)
_bank = lru_cache(maxsize=1)(load_bank)


def research_enabled() -> bool:
    return os.getenv("SEL_RESEARCH_ENABLED") == "1"


def _user_lock(user_id: str) -> asyncio.Lock:
    return _locks.setdefault(user_id, asyncio.Lock())


def _session_message(session: ResearchSession) -> str:
    if session.status == "insufficient":
        return f"第 {session.week} 週《{session.game}》已記為資料不足。"
    if session.result is not None:
        return (
            f"第 {session.week} 週《{session.game}》｜{session.dimension}\n"
            f"{session.result.score}／10 分\n{session.result.suggestion}"
        )
    if session.followup_question:
        return f"補問｜{session.followup_question}\n可輸入 /sel 略過 或 /sel 離開。"
    return (
        f"第 {session.week} 週《{session.game}》｜{session.dimension}\n"
        f"{session.question}\n可用中文錄音或打字回答，也可輸入 /sel 略過 或 /sel 離開。"
    )


async def _send_session_reply(event, session: ResearchSession) -> None:
    await send_text_message(event, _session_message(session))
    # The saved marker survives a restart until the next normal data save.
    # LINE's one-use reply token prevents a second reply to the same event.
    session.pending_reply_id = None


async def _save_session(user, session: ResearchSession) -> None:
    previous = user.sel_teacher_sessions.get(session.week)
    user.sel_teacher_sessions[session.week] = session
    try:
        await save_user_data()
    except Exception:
        if previous is None:
            del user.sel_teacher_sessions[session.week]
        else:
            user.sel_teacher_sessions[session.week] = previous
        raise


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
        if arg == "離開":
            state.sel_research_week = None
            reply = "已離開研究對答。重新輸入 /sel 與週次可回到同一筆紀錄。"
        elif arg == "略過":
            week = state.sel_research_week
            session = user.sel_teacher_sessions.get(week)
            if session is None or session.status != "pending":
                reply = "請先輸入 /sel 與本週的週次。"
            else:
                session = session.model_copy(update={"status": "insufficient", "missing_reason": "skipped"})
                await _save_session(user, session)
                state.sel_research_week = None
                reply = _session_message(session)
        elif arg in {str(week) for week in _bank().weeks}:
            week = int(arg)
            session = user.sel_teacher_sessions.get(week)
            if session is None:
                item = _bank().weeks[week]
                session = ResearchSession(week=week, game=item.game, dimension=item.dimension, question=item.question)
                await _save_session(user, session)
            state.sel_research_week = week if session.status == "pending" else None
            await _send_session_reply(event, session)
            return
        else:
            reply = "請輸入 /sel 與本週的週次（第 4–15 週），例如 /sel 13。"
    await send_text_message(event, reply)


async def close_research_input(user_id: str) -> None:
    if research_enabled():
        async with _user_lock(user_id):
            state = get_user_state(user_id)
            if state is not None:
                state.sel_research_week = None


async def handle_research_input(event, user_id: str, read_answer) -> bool:
    if not research_enabled():
        return False
    async with _user_lock(user_id):
        user = getUser(user_id)
        state = get_user_state(user_id)
        if user is None or state is None:
            return False
        message_id = str(event.message.id)
        for entry in user.sel_teacher_sessions.values():
            if message_id not in (entry.primary_message_id, entry.followup_message_id):
                continue
            if entry.pending_reply_id == message_id and state.sel_research_week == entry.week:
                await _send_session_reply(event, entry)
                state.sel_research_week = entry.week if entry.status == "pending" else None
            return True
        if any(
            message_id in (entry.primary_message_id, entry.followup_message_id)
            for entry in user.sel_research_sessions.values()
        ):
            return True
        session = user.sel_teacher_sessions.get(state.sel_research_week)
        if session is None:
            return False
        if session.pending_reply_id is not None:
            await send_text_message(event, f"請先輸入 /sel {session.week} 取得尚未送出的補問或評分。")
            return True
        if session.status != "pending":
            return False

        try:
            text = (await read_answer()).strip()
            updated = await next_research_step(client, _bank(), session, text, message_id)
            updated.pending_reply_id = message_id
            await _save_session(user, updated)
        except Exception as error:
            _logger.warning("SEL research answer failed (%s)", type(error).__name__)
            await send_text_message(event, "這次對答暫時處理失敗，請重新傳送剛才的回答。")
            return True
        await _send_session_reply(event, updated)
        if updated.status != "pending":
            state.sel_research_week = None
        return True
