"""Tests for the tool layer - the contract between the model and our services."""

import json

from app.agent.tools import ALL_TOOLS, TOOLS_BY_NAME


def test_every_tool_has_a_description_for_the_model():
    """The docstring IS the selection signal. A missing one breaks tool choice."""
    for tool in ALL_TOOLS:
        assert tool.description, "%s has no docstring" % tool.name


def test_the_three_required_tools_are_registered():
    for name in ("search_property", "book_viewing", "escalate_to_human"):
        assert name in TOOLS_BY_NAME


def test_search_property_tool_returns_json():
    payload = json.loads(TOOLS_BY_NAME["search_property"].invoke({"city": "Izmir"}))

    assert payload["count"] >= 1
    assert all(p["city"] == "Izmir" for p in payload["properties"])


def test_search_property_explains_an_empty_result():
    payload = json.loads(TOOLS_BY_NAME["search_property"].invoke({"city": "Atlantis"}))

    assert payload["count"] == 0
    assert "message" in payload


def test_answer_faq_finds_the_commission_policy():
    payload = json.loads(
        TOOLS_BY_NAME["answer_faq"].invoke({"question": "do you charge a commission?"})
    )

    assert payload["found"] is True
    assert "2%" in payload["answers"][0]["answer"]


def test_book_viewing_reports_errors_instead_of_raising():
    """A tool must never raise - the model needs the error back to recover."""
    payload = json.loads(TOOLS_BY_NAME["book_viewing"].invoke({
        "property_id": 999,
        "customer_name": "Ada Lovelace",
        "customer_phone": "+905550001",
        "slot": "2026-08-22 10:00",
    }))

    assert payload["success"] is False
    assert "error" in payload


def test_book_viewing_succeeds_with_a_real_slot():
    slots = json.loads(
        TOOLS_BY_NAME["list_viewing_slots"].invoke({"property_id": 1})
    )["available_slots"]

    payload = json.loads(TOOLS_BY_NAME["book_viewing"].invoke({
        "property_id": 1,
        "customer_name": "Ada Lovelace",
        "customer_phone": "+905550001",
        "slot": slots[0],
    }))

    assert payload["success"] is True
    assert payload["booking"]["status"] == "confirmed"


def test_escalate_to_human_opens_a_ticket():
    payload = json.loads(TOOLS_BY_NAME["escalate_to_human"].invoke({
        "reason": "price negotiation",
        "summary": "Customer wants to negotiate on property 2.",
    }))

    assert payload["status"] == "open"
