import os
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, patch

from utils.models import SpeechAssessment, User, UserState
from utils.sel_research import ResearchRating, ResearchSession, load_bank


class ResearchHandlerTests(IsolatedAsyncioTestCase):
    async def test_existing_history_and_research_reply_recovery(self):
        with patch.dict(os.environ, {
            "OPENAI_API_KEY": "test-key",
            "LINE_CHANNEL_SECRET": "test-secret",
            "LINE_CHANNEL_ACCESS_TOKEN": "test-token",
            "SEL_RESEARCH_ENABLED": "1",
        }):
            import config
            import sel_research_handlers as handler
            from utils import file_utils

            self.addAsyncCleanup(config.client.close)
            self.addAsyncCleanup(config.async_api_client.close)
            user = User(id="test", dep="test", name="test", class_time=1, history={
                "sel4-0": [SpeechAssessment(score=7, transcript="既有同感作答")],
            })
            with patch.object(file_utils, "user_data", {"student": user}):
                self.assertEqual(file_utils.getHistory("student", "sel4-0")[0].score, 7)

            item = load_bank().weeks[13]
            session = ResearchSession(week=13, game=item.game, dimension=item.dimension, question=item.question)
            user = User.model_validate({
                **user.model_dump(),
                "sel_research_sessions": {13: {
                    **session.model_dump(exclude={"result"}),
                    "status": "scored",
                    "primary": "舊版作答",
                    "primary_message_id": "legacy-primary",
                    "result": {"score": 0, "evidence": ["舊版作答"], "suggestion": "試答回饋。"},
                }},
            })
            state = UserState()
            pending = session.model_copy(update={
                "primary": "我先停一下。",
                "primary_message_id": "primary",
                "followup_key": "B",
                "followup_question": item.followups["B"].question,
            })
            completed = pending.model_copy(update={
                "followup": "後來比較冷靜。",
                "followup_message_id": "supplement",
                "status": "scored",
                "result": ResearchRating(score=4, evidence=["比較冷靜"], suggestion="下次可以先聽完對方的理由。"),
            })
            advance = AsyncMock(side_effect=[pending, completed])
            save = AsyncMock()
            sender = AsyncMock(side_effect=[None, TimeoutError(), None, None, TimeoutError(), None])
            read_answer = AsyncMock(side_effect=["我先停一下。", "後來比較冷靜。"])
            primary = SimpleNamespace(message=SimpleNamespace(id="primary"))
            repeated_text = SimpleNamespace(message=SimpleNamespace(id="repeat-as-new-input"))
            supplement = SimpleNamespace(message=SimpleNamespace(id="supplement"))
            legacy_primary = SimpleNamespace(message=SimpleNamespace(id="legacy-primary"))
            resume = SimpleNamespace(message=SimpleNamespace(id="resume"))

            with (
                patch.object(handler, "getUser", return_value=user) as get_user,
                patch.object(handler, "get_user_state", return_value=state),
                patch.object(handler, "next_research_step", advance),
                patch.object(handler, "save_user_data", save),
                patch.object(handler, "send_text_message", sender),
            ):
                await handler.research_command(resume, "student", "/sel 13")
                self.assertIn(item.question, sender.await_args.args[1])
                self.assertEqual(user.sel_research_sessions[13].result.score, 0)
                self.assertIsNone(user.sel_teacher_sessions[13].result)
                self.assertTrue(await handler.handle_research_input(legacy_primary, "student", read_answer))
                advance.assert_not_awaited()

                with self.assertRaises(TimeoutError):
                    await handler.handle_research_input(primary, "student", read_answer)
                self.assertEqual(user.sel_teacher_sessions[13].pending_reply_id, "primary")

                # A newly sent answer cannot be mistaken for the unseen supplement.
                self.assertTrue(await handler.handle_research_input(repeated_text, "student", read_answer))
                self.assertIn("/sel 13", sender.await_args.args[1])
                self.assertEqual(advance.await_count, 1)

                self.assertTrue(await handler.handle_research_input(primary, "student", read_answer))
                self.assertIn(item.followups["B"].question, sender.await_args.args[1])
                self.assertIsNone(user.sel_teacher_sessions[13].pending_reply_id)
                self.assertTrue(await handler.handle_research_input(primary, "student", read_answer))
                self.assertEqual(sender.await_count, 4)
                self.assertEqual(advance.await_count, 1)

                with self.assertRaises(TimeoutError):
                    await handler.handle_research_input(supplement, "student", read_answer)
                self.assertEqual(user.sel_teacher_sessions[13].pending_reply_id, "supplement")
                self.assertEqual(state.sel_research_week, 13)

                # Reading the saved score through /sel works after a service restart.
                restored = User.model_validate_json(user.model_dump_json())
                get_user.return_value = restored
                state.sel_research_week = None
                await handler.research_command(resume, "student", "/sel 13")
                self.assertIn("4／10 分", sender.await_args.args[1])
                self.assertIsNone(restored.sel_teacher_sessions[13].pending_reply_id)
                self.assertIsNone(state.sel_research_week)
                self.assertEqual(advance.await_count, 2)
                self.assertEqual(restored.sel_research_sessions[13].result.score, 0)
                self.assertEqual(restored.sel_teacher_sessions[13].result.score, 4)
                self.assertEqual(save.await_count, 3)

    async def test_existing_q_button_routes_card_text_and_audio_to_one_score(self):
        from json import loads

        with patch.dict(os.environ, {
            "OPENAI_API_KEY": "test-key",
            "LINE_CHANNEL_SECRET": "test-secret",
            "LINE_CHANNEL_ACCESS_TOKEN": "test-token",
            "DOMAIN": "example.invalid",
            "SEL_RESEARCH_ENABLED": "1",
        }):
            import config
            import handlers
            import sel_research_handlers as research
            from utils import file_utils
            from utils.sel_research import MenuFollowupDecision

            self.addAsyncCleanup(config.client.close)
            self.addAsyncCleanup(config.async_api_client.close)
            user = User(id="test", dep="test", name="test", class_time=1, history={})
            state = UserState(category="sel4", sel_language="chi")
            question = config.question_manager.get_question("sel4", 4).text
            source = SimpleNamespace(user_id="student")
            click = SimpleNamespace(
                source=source, webhook_event_id="clicked-q5",
                postback=SimpleNamespace(data="action=record&sub=4"),
            )
            main = SimpleNamespace(
                source=source,
                message=SimpleNamespace(id="main-answer", text="下次分組有人沈默，我會先問他有沒有不同想法。"),
            )
            supplement = SimpleNamespace(source=source, message=SimpleNamespace(id="voice-answer"))
            followup = "你為什麼會想先問他的想法？"
            parse = AsyncMock(side_effect=[
                SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(
                    parsed=MenuFollowupDecision(action="ask", question=followup)
                ))]),
                SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(
                    parsed=ResearchRating(score=7, evidence=["也許他不同意"], suggestion="可以先問對方的想法。")
                ))]),
            ])
            model_client = SimpleNamespace(beta=SimpleNamespace(
                chat=SimpleNamespace(completions=SimpleNamespace(parse=parse)),
            ))
            with (
                patch.object(file_utils, "user_data", {"student": user}),
                patch.object(file_utils, "user_state", {"student": state}),
                patch.object(handlers, "handle_rich_menu", AsyncMock()),
                patch.object(handlers, "check_user_login", AsyncMock(return_value=True)),
                patch.object(handlers, "isEnabled", return_value=True),
                patch.object(handlers, "show_loading", AsyncMock()),
                patch.object(handlers, "get_audio_content", AsyncMock(return_value=b"audio")),
                patch.object(handlers, "transcribe_audio", AsyncMock(return_value="也許他不同意，但沒有機會說。")) as transcribe,
                patch.object(handlers, "send_message", AsyncMock()) as old_card,
                patch.object(research, "send_message", AsyncMock()) as card_sender,
                patch.object(research, "send_text_message", AsyncMock()) as reply,
                patch.object(research, "save_user_data", AsyncMock()),
                patch.object(research, "client", model_client),
            ):
                await handlers.handle_postback(click)
                card = card_sender.await_args.args[1][0]
                self.assertEqual(card.alt_text, "Q5")
                self.assertEqual(card.contents.contents[0].body.contents[1].text, question)
                self.assertIn("打字或錄音", card.contents.contents[-1].body.contents[0].text)
                self.assertEqual(state.sel_menu_session_id, "clicked-q5")

                await handlers.handle_text_message(main)
                self.assertIn(followup, reply.await_args.args[1])
                self.assertEqual(parse.await_count, 1)
                self.assertNotIn("sel4-4", user.history)
                decision_payload = loads(parse.await_args.kwargs["messages"][1]["content"])
                self.assertEqual(decision_payload["question"], question)

                click_again = SimpleNamespace(
                    source=source, webhook_event_id="clicked-q5-again", postback=click.postback,
                )
                await handlers.handle_postback(click_again)
                self.assertEqual(state.sel_menu_session_id, "clicked-q5")
                self.assertIn(followup, card_sender.await_args.args[1][1].text)

                await handlers.handle_audio_message(supplement)
                transcribe.assert_awaited_once_with(b"audio", language="zh")
                self.assertIn("7／10 分", reply.await_args.args[1])
                self.assertEqual(parse.await_count, 2)
                score_payload = loads(parse.await_args.kwargs["messages"][1]["content"])
                self.assertFalse(score_payload["require_actual_experience"])
                self.assertEqual(score_payload["followup_question"], followup)
                self.assertEqual(user.history["sel4-4"][0].score, 7)
                self.assertEqual(user.sel_menu_sessions["clicked-q5"].result.score, 7)
                self.assertEqual(user.sel_teacher_sessions, {})

                await handlers.handle_audio_message(supplement)
                self.assertEqual(parse.await_count, 2)
                self.assertEqual(len(user.history["sel4-4"]), 1)

                with patch.dict(os.environ, {"SEL_RESEARCH_ENABLED": "0"}):
                    await handlers.handle_postback(click)
                old_card.assert_awaited_once()
                self.assertEqual(len(user.sel_menu_sessions), 1)

                q1_click = SimpleNamespace(
                    source=source, webhook_event_id="clicked-q1",
                    postback=SimpleNamespace(data="action=record&sub=0"),
                )
                q1_answer = "選情緒卡時，我發現自己先緊張，聽完同學的理由才放心。"
                parse.side_effect = [
                    SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(
                        parsed=MenuFollowupDecision(action="complete", question=None)
                    ))]),
                    SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(
                        parsed=ResearchRating(score=8, evidence=["我發現自己先緊張"], suggestion="留意情緒變化。")
                    ))]),
                ]
                await handlers.handle_postback(q1_click)
                await handlers.handle_text_message(SimpleNamespace(
                    source=source, message=SimpleNamespace(id="q1-answer", text=q1_answer),
                ))
                self.assertIn("8／10 分", reply.await_args.args[1])
                self.assertIsNone(user.sel_menu_sessions["clicked-q1"].followup_question)
                self.assertEqual(user.sel_menu_sessions["clicked-q5"].result.score, 7)

    async def test_audio_cannot_score_a_newer_question_or_an_exited_question(self):
        with patch.dict(os.environ, {
            "OPENAI_API_KEY": "test-key",
            "LINE_CHANNEL_SECRET": "test-secret",
            "LINE_CHANNEL_ACCESS_TOKEN": "test-token",
            "DOMAIN": "example.invalid",
            "SEL_RESEARCH_ENABLED": "1",
        }):
            import config
            import handlers
            import sel_research_handlers as research
            from utils import file_utils

            self.addAsyncCleanup(config.client.close)
            self.addAsyncCleanup(config.async_api_client.close)
            user = User(id="test", dep="test", name="test", class_time=1, history={})
            state = UserState(category="sel4", sel_language="chi")
            source = SimpleNamespace(user_id="student")
            q1 = SimpleNamespace(source=source, timestamp=100, webhook_event_id="q1",
                                 postback=SimpleNamespace(data="action=record&sub=0"))
            q2 = SimpleNamespace(source=source, timestamp=300, webhook_event_id="q2",
                                 postback=SimpleNamespace(data="action=record&sub=1"))
            late_q1_audio = SimpleNamespace(source=source, timestamp=200, message=SimpleNamespace(id="q1-audio"))
            exit_command = SimpleNamespace(source=source, timestamp=400,
                                           message=SimpleNamespace(id="leave", text="/sel 離開"))
            after_exit_audio = SimpleNamespace(source=source, timestamp=500,
                                              message=SimpleNamespace(id="closed-audio"))

            with (
                patch.object(file_utils, "user_data", {"student": user}),
                patch.object(file_utils, "user_state", {"student": state}),
                patch.object(handlers, "handle_rich_menu", AsyncMock()),
                patch.object(handlers, "check_user_login", AsyncMock(return_value=True)),
                patch.object(handlers, "isEnabled", return_value=True),
                patch.object(handlers, "show_loading", AsyncMock()),
                patch.object(handlers, "get_audio_content", AsyncMock()) as download,
                patch.object(handlers, "send_text_message", AsyncMock()) as prompt,
                patch.object(research, "send_message", AsyncMock()),
                patch.object(research, "send_text_message", AsyncMock()) as research_reply,
                patch.object(research, "save_user_data", AsyncMock()),
            ):
                await handlers.handle_postback(q1)
                await handlers.handle_postback(q2)
                await handlers.handle_audio_message(late_q1_audio)
                self.assertIn("請選回原題後再傳一次", research_reply.await_args.args[1])
                self.assertEqual(state.sel_menu_session_id, "q2")
                self.assertIsNone(user.sel_menu_sessions["q1"].primary)
                self.assertIsNone(user.sel_menu_sessions["q2"].primary)

                await handlers.handle_text_message(exit_command)
                self.assertIsNone(state.sel_menu_session_id)
                await handlers.handle_audio_message(after_exit_audio)
                self.assertIn("請先點選", prompt.await_args.args[1])
                download.assert_not_awaited()
                self.assertEqual(user.history, {})

                # A delayed replay of the original click cannot reopen the exited question.
                await handlers.handle_postback(q2)
                self.assertIsNone(state.sel_menu_session_id)

    async def test_failed_card_is_retried_on_redelivery_after_reload(self):
        with patch.dict(os.environ, {
            "OPENAI_API_KEY": "test-key",
            "LINE_CHANNEL_SECRET": "test-secret",
            "LINE_CHANNEL_ACCESS_TOKEN": "test-token",
            "SEL_RESEARCH_ENABLED": "1",
        }):
            import config
            import sel_research_handlers as research

            self.addAsyncCleanup(config.client.close)
            self.addAsyncCleanup(config.async_api_client.close)
            user = User(id="test", dep="test", name="test", class_time=1, history={})
            state = UserState(sel_research_week=13)
            click = SimpleNamespace(webhook_event_id="click", timestamp=100)
            card = object()
            sender = AsyncMock(side_effect=[TimeoutError(), None])
            persisted = []

            async def save():
                persisted.append(get_user.return_value.model_dump_json())

            with (
                patch.object(research, "getUser", return_value=user) as get_user,
                patch.object(research, "get_user_state", return_value=state) as get_state,
                patch.object(research, "send_message", sender),
                patch.object(research, "save_user_data", side_effect=save),
            ):
                with self.assertRaises(TimeoutError):
                    await research.begin_menu_question(click, "student", "sel4", 0, "第一題", "zh", card)
                self.assertIsNone(state.sel_research_week)
                self.assertIsNone(state.sel_menu_session_id)
                self.assertTrue(user.sel_menu_sessions["click"].card_pending)

                get_user.return_value = User.model_validate_json(persisted[-1])
                get_state.return_value = UserState()
                await research.begin_menu_question(click, "student", "sel4", 0, "第一題", "zh", card)
                self.assertEqual(get_state.return_value.sel_menu_session_id, "click")
                sender.assert_awaited_with(click, [card])

                restored = User.model_validate_json(persisted[-1])
                self.assertFalse(restored.sel_menu_sessions["click"].card_pending)
                self.assertEqual(len(restored.sel_menu_sessions), 1)

                get_user.return_value = restored
                await research.begin_menu_question(click, "student", "sel4", 0, "第一題", "zh", card)
                self.assertEqual(sender.await_count, 2)
