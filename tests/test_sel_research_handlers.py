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
            user.sel_research_sessions[13] = session
            state = UserState(sel_research_week=13)
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
            sender = AsyncMock(side_effect=[TimeoutError(), None, None, TimeoutError(), None])
            read_answer = AsyncMock(side_effect=["我先停一下。", "後來比較冷靜。"])
            primary = SimpleNamespace(message=SimpleNamespace(id="primary"))
            repeated_text = SimpleNamespace(message=SimpleNamespace(id="repeat-as-new-input"))
            supplement = SimpleNamespace(message=SimpleNamespace(id="supplement"))
            resume = SimpleNamespace(message=SimpleNamespace(id="resume"))

            with (
                patch.object(handler, "getUser", return_value=user) as get_user,
                patch.object(handler, "get_user_state", return_value=state),
                patch.object(handler, "next_research_step", advance),
                patch.object(handler, "save_user_data", save),
                patch.object(handler, "send_text_message", sender),
            ):
                with self.assertRaises(TimeoutError):
                    await handler.handle_research_input(primary, "student", read_answer)
                self.assertEqual(user.sel_research_sessions[13].pending_reply_id, "primary")

                # A newly sent answer cannot be mistaken for the unseen supplement.
                self.assertTrue(await handler.handle_research_input(repeated_text, "student", read_answer))
                self.assertIn("/sel 13", sender.await_args.args[1])
                self.assertEqual(advance.await_count, 1)

                self.assertTrue(await handler.handle_research_input(primary, "student", read_answer))
                self.assertIn(item.followups["B"].question, sender.await_args.args[1])
                self.assertIsNone(user.sel_research_sessions[13].pending_reply_id)
                self.assertTrue(await handler.handle_research_input(primary, "student", read_answer))
                self.assertEqual(sender.await_count, 3)
                self.assertEqual(advance.await_count, 1)

                with self.assertRaises(TimeoutError):
                    await handler.handle_research_input(supplement, "student", read_answer)
                self.assertEqual(user.sel_research_sessions[13].pending_reply_id, "supplement")
                self.assertEqual(state.sel_research_week, 13)

                # Reading the saved score through /sel works after a service restart.
                restored = User.model_validate_json(user.model_dump_json())
                get_user.return_value = restored
                state.sel_research_week = None
                await handler.research_command(resume, "student", "/sel 13")
                self.assertIn("4／5 分", sender.await_args.args[1])
                self.assertIsNone(restored.sel_research_sessions[13].pending_reply_id)
                self.assertIsNone(state.sel_research_week)
                self.assertEqual(advance.await_count, 2)
                self.assertEqual(save.await_count, 2)
