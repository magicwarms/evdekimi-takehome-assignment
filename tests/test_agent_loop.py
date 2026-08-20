"""Tests for the agent loop.

These prove the loop, its guard rails and its error paths work - without an
OpenAI API key and without spending anything. FakeLLM replays a scripted list of
replies, which is exactly what the real client returns.
"""

import pytest

from langchain_core.messages import AIMessage

from app.agent import runner
from app.errors import LLMError


class FakeLLM:
    """Replays scripted AIMessages, one per invoke() call."""

    def __init__(self, replies):
        self.replies = list(replies)
        self.seen_messages = []

    def invoke(self, messages):
        self.seen_messages.append(list(messages))
        return self.replies.pop(0)


class BrokenLLM:
    """Stands in for a provider outage or a bad API key."""

    def invoke(self, messages):
        raise RuntimeError("connection reset by peer")


def tool_call(name, args, call_id="call_1"):
    return AIMessage(content="", tool_calls=[
        {"name": name, "args": args, "id": call_id, "type": "tool_call"}
    ])


def test_agent_runs_a_tool_then_answers():
    fake = FakeLLM([
        tool_call("search_property", {"city": "Izmir"}),
        AIMessage(content="I found 2 places in Izmir."),
    ])

    result = runner.run_agent("Anything in Izmir?", llm=fake)

    assert result["tools_used"] == ["search_property"]
    assert result["reply"] == "I found 2 places in Izmir."
    assert result["steps"] == 2


def test_agent_answers_directly_when_no_tool_is_needed():
    fake = FakeLLM([AIMessage(content="Hello! How can I help?")])

    result = runner.run_agent("hi", llm=fake)

    assert result["tools_used"] == []
    assert result["steps"] == 1


def test_agent_can_chain_two_tools_in_one_turn():
    fake = FakeLLM([
        tool_call("list_viewing_slots", {"property_id": 1}, "call_1"),
        tool_call("book_viewing", {
            "property_id": 1,
            "customer_name": "Ada Lovelace",
            "customer_phone": "+905550001",
            "slot": "2026-08-22 10:00",
        }, "call_2"),
        AIMessage(content="Booked for Friday at 10:00."),
    ])

    result = runner.run_agent("Book me a viewing", llm=fake)

    assert result["tools_used"] == ["list_viewing_slots", "book_viewing"]


def test_agent_stops_at_the_iteration_cap():
    """Without this guard a confused model could loop forever."""
    never_settles = [
        tool_call("search_property", {}, "call_%d" % i) for i in range(10)
    ]

    result = runner.run_agent("loop forever", llm=FakeLLM(never_settles))

    assert result["steps"] == 5  # MAX_TOOL_ITERATIONS
    assert result["reply"] == runner.FALLBACK_REPLY


def test_unknown_tool_does_not_crash_the_request():
    fake = FakeLLM([
        tool_call("does_not_exist", {}),
        AIMessage(content="Sorry, I could not do that."),
    ])

    result = runner.run_agent("do something weird", llm=fake)

    assert result["reply"] == "Sorry, I could not do that."


def test_llm_failure_becomes_an_llm_error():
    with pytest.raises(LLMError):
        runner.run_agent("hello", llm=BrokenLLM())


def test_conversation_history_is_remembered():
    first = runner.run_agent("my budget is 5 million",
                             llm=FakeLLM([AIMessage(content="Noted.")]))

    second = FakeLLM([AIMessage(content="You said 5 million.")])
    runner.run_agent("what is my budget?",
                     conversation_id=first["conversation_id"], llm=second)

    replayed = [m.content for m in second.seen_messages[0]]
    assert "my budget is 5 million" in replayed
    assert "Noted." in replayed


def test_a_new_conversation_starts_empty():
    fake = FakeLLM([AIMessage(content="Hi.")])

    runner.run_agent("hello", llm=fake)

    # system prompt + the one user message, nothing else
    assert len(fake.seen_messages[0]) == 2
