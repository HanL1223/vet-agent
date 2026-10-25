from datetime import date

from vetagent.agent.llm import ModelReply, ScriptedModel, ToolCall, to_anthropic, to_openai
from vetagent.agent.loop import MAX_STEPS, run_turn
from vetagent.agent.safety import triage
from vetagent.api.wiring import DEMO_OWNER_ID, DEMO_PET_ID
from vetagent.domain.plan_value import months_paid
from vetagent.store.sqlite import Consent


class ExplodingModel:
    name = "must not be called"

    def reply(self, *args):
        raise AssertionError("urgent messages must not reach the model")


class LoopingModel:
    name = "always calls a tool"

    def reply(self, *args):
        return ModelReply(tool_calls=[ToolCall("c", "list_care_due", {})])


def test_ag3_urgent_symptoms_skip_the_model(ctx):
    new = run_turn(ExplodingModel(), "", [], "He's holding his leg up", ctx)
    assert new[-1]["cards"][0]["type"] == "urgent"


def test_ag3_triage_ignores_routine_messages():
    assert not triage("Is my plan worth it?").urgent
    assert triage("she ate rat bait").urgent


def test_ag4_booking_is_only_a_proposal(ctx, store):
    new = run_turn(ScriptedModel(), "", [], "Book his screening", ctx)
    card = next(m["card"] for m in new if m["role"] == "tool")
    assert card["type"] == "proposal"
    assert store.proposal(card["proposal_id"]).status == "pending"
    assert store.clinic_requests() == []


def test_ag5_weight_respects_sharing_consent(ctx, store):
    store.set_consent(DEMO_OWNER_ID, Consent(share_log=False, deidentified_use=False))
    run_turn(ScriptedModel(), "", [], "Log weight 31.2 kg", ctx)
    assert store.weights(DEMO_PET_ID)[-1]["shared_with_clinic"] == 0


def test_ag6_plan_value_matches_seed(ctx):
    new = run_turn(ScriptedModel(), "", [], "Is my plan worth it?", ctx)
    result = next(m["result"] for m in new if m["role"] == "tool")
    assert (result["paid"], result["benefits_used"]) == (590, 412)
    assert months_paid(date(2026, 1, 1), ctx.today) == 10


def test_loop_stops_after_max_steps(ctx):
    new = run_turn(LoopingModel(), "", [], "What's due?", ctx)
    assert sum(1 for m in new if m["role"] == "tool") == MAX_STEPS
    assert new[-1]["role"] == "assistant"


def test_anthropic_format_merges_roles_and_starts_with_user():
    messages = [
        {"role": "assistant", "text": "Hi", "tool_calls": [{"id": "1", "name": "t", "args": {}}]},
        {"role": "tool", "tool_call_id": "1", "name": "t", "result": {"ok": True}},
        {"role": "assistant", "text": "Done"},
        {"role": "assistant", "text": "", "cards": []},
        {"role": "user", "text": "Thanks"},
    ]
    out = to_anthropic(messages)
    assert [m["role"] for m in out] == ["user", "assistant", "user", "assistant", "user"]


def test_openai_format_keeps_tool_calls_and_drops_card_only_turns():
    messages = [
        {"role": "user", "text": "What's due?"},
        {
            "role": "assistant",
            "text": "",
            "tool_calls": [{"id": "1", "name": "list_care_due", "args": {"limit": 2}}],
        },
        {"role": "tool", "tool_call_id": "1", "name": "list_care_due", "result": {"ok": True}},
        {"role": "assistant", "text": "", "cards": []},
        {"role": "assistant", "text": "Done"},
    ]
    out = to_openai(messages)
    assert [m["role"] for m in out] == ["user", "assistant", "tool", "assistant"]
    call = out[1]["tool_calls"][0]
    assert out[1]["content"] is None
    assert call["function"] == {"name": "list_care_due", "arguments": '{"limit": 2}'}
    assert out[2] == {"role": "tool", "tool_call_id": "1", "content": '{"ok": true}'}
