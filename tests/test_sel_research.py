import json
from pathlib import Path
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase, TestCase
from unittest.mock import AsyncMock

from pydantic import ValidationError

from utils.models import QuestionCategory, User
from utils.sel_research import (
    FollowupDecision,
    ResearchRating,
    ResearchSession,
    load_bank,
    next_research_step,
)


class ResearchBankTests(TestCase):
    def test_schedule_matches_expected_dimensions(self):
        bank = load_bank()
        self.assertEqual(set(bank.weeks), set(range(4, 16)))
        self.assertEqual(len(bank.rubrics), 5)
        for first, second in ((5, 15), (8, 10)):
            self.assertEqual(bank.weeks[first], bank.weeks[second])
        self.assertEqual(bank.weeks[6].game, "同感 2.0")
        self.assertEqual(bank.weeks[6].dimension, "社會覺察")
        self.assertEqual(bank.weeks[13].game, "同感 2.0")
        self.assertEqual(bank.weeks[13].dimension, "自我管理")
        self.assertEqual(bank.weeks[14].dimension, "自我管理")

    def test_legacy_user_loads_without_research_record(self):
        student = User(id="test", dep="test", name="test", class_time=1, history={})
        self.assertEqual(student.sel_research_sessions, {})

    def test_sel4_uses_the_loaded_banks_metadata(self):
        classroom = QuestionCategory.model_validate_json(Path("category/sel4.json").read_text())
        older = QuestionCategory.model_validate_json(Path("category7-8/sel4.json").read_text())
        self.assertEqual(classroom.sel_unit.name_chi, "同感 2.0")
        self.assertTrue(classroom.sel_unit.use_question_rubric_in_chinese)
        self.assertEqual(older.sel_unit.name_chi, "瑪利歐驚險塔")
        self.assertFalse(older.sel_unit.use_question_rubric_in_chinese)

    def test_rubric_range_cannot_exceed_five(self):
        with self.assertRaises(ValidationError):
            ResearchRating(score=6, evidence=[], suggestion="耐心等待。")


class ResearchInterviewTests(IsolatedAsyncioTestCase):
    def setUp(self):
        self.bank = load_bank()
        item = self.bank.weeks[13]
        self.session = ResearchSession(week=13, game=item.game, dimension=item.dimension, question=item.question)
        self.parse = AsyncMock()
        self.client = SimpleNamespace(
            beta=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(parse=self.parse)))
        )

    def replies(self, *results):
        self.parse.side_effect = [
            SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(parsed=result))])
            for result in results
        ]

    async def test_only_final_turn_is_scored_and_uses_both_answers(self):
        self.replies(
            FollowupDecision(action="ask_b"),
            ResearchRating(score=4, evidence=["先停一下再開口", "比較不緊張"], suggestion="下次也可以先停一下。"),
        )
        pending = await next_research_step(self.client, self.bank, self.session, "我先停一下再開口。", "11")
        self.assertEqual(pending.followup_question, self.bank.weeks[13].followups["B"].question)
        self.assertEqual(pending.status, "pending")
        self.assertIsNone(pending.result)
        self.assertEqual(self.parse.await_count, 1)

        # Simulate a fresh process loading a saved pending turn.
        pending = ResearchSession.model_validate_json(pending.model_dump_json())
        complete = await next_research_step(self.client, self.bank, pending, "後來比較不緊張。", "12")
        self.assertEqual(complete.status, "scored")
        self.assertEqual(complete.result.score, 4)
        self.assertEqual(self.parse.await_count, 2)
        request = self.parse.call_args.kwargs
        self.assertIs(request["response_format"], ResearchRating)
        payload = json.loads(request["messages"][1]["content"])
        self.assertEqual(payload["primary"], "我先停一下再開口。")
        self.assertEqual(payload["followup"], "後來比較不緊張。")
        self.assertNotIn("previousAttempts", payload)

    async def test_a_uses_the_prescribed_question(self):
        self.replies(FollowupDecision(action="ask_a"))
        pending = await next_research_step(self.client, self.bank, self.session, "大家選的情緒不一樣。", "21")
        self.assertEqual(pending.followup_question, self.bank.weeks[13].followups["A"].question)
        self.assertIsNone(pending.result)

    async def test_valid_zero_is_saved_as_scored(self):
        self.replies(
            FollowupDecision(action="complete"),
            ResearchRating(score=0, evidence=["大家選的情緒不一樣"], suggestion="下次可回顧當時的做法。"),
        )
        complete = await next_research_step(self.client, self.bank, self.session, "大家選的情緒不一樣。", "31")
        self.assertEqual(complete.result.score, 0)
        self.assertEqual(complete.status, "scored")
        self.assertIsNone(complete.missing_reason)

    async def test_no_experience_and_unintelligible_are_missing(self):
        self.replies(FollowupDecision(action="no_experience"))
        missing = await next_research_step(self.client, self.bank, self.session, "我沒遇過。", "41")
        self.assertIsNone(missing.result)
        self.assertEqual(missing.status, "insufficient")
        self.assertEqual(missing.missing_reason, "no_experience")

        empty = await next_research_step(self.client, self.bank, self.session, "", "42")
        self.assertEqual(empty.missing_reason, "unintelligible")
        self.assertEqual(self.parse.await_count, 1)

    async def test_invalid_followup_does_not_erase_primary(self):
        self.replies(
            FollowupDecision(action="ask_b"),
            ResearchRating(score=2, evidence=["深呼吸"], suggestion="回想後來有什麼變化。"),
        )
        pending = await next_research_step(self.client, self.bank, self.session, "我深呼吸。", "51")
        result = await next_research_step(self.client, self.bank, pending, "", "52")
        self.assertEqual(result.result.score, 2)
        self.assertIsNone(result.followup)

    async def test_unquoted_evidence_prevents_scoring(self):
        self.replies(
            FollowupDecision(action="complete"),
            ResearchRating(score=4, evidence=["先深呼吸"], suggestion="繼續練習。"),
        )
        with self.assertRaisesRegex(ValueError, "證據必須取自"):
            await next_research_step(self.client, self.bank, self.session, "我先停一下再開口。", "61")
        self.assertIsNone(self.session.result)
