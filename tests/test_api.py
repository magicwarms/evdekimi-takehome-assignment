"""End-to-end tests through the HTTP layer, using FastAPI's TestClient."""

from unittest.mock import patch

from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

from app.main import app

client = TestClient(app)
ADMIN = ("admin", "admin123")


class FakeLLM:
    def __init__(self, replies):
        self.replies = list(replies)

    def invoke(self, messages):
        return self.replies.pop(0)


# ------------------------------------------------------------------- health

def test_health_lists_the_registered_tools():
    body = client.get("/health").json()

    assert body["status"] == "ok"
    for name in ("search_property", "book_viewing", "escalate_to_human"):
        assert name in body["tools"]


# --------------------------------------------------------------------- chat

def test_chat_returns_the_reply_and_the_tools_used():
    fake = FakeLLM([
        AIMessage(content="", tool_calls=[{
            "name": "search_property", "args": {"city": "Izmir"},
            "id": "call_1", "type": "tool_call",
        }]),
        AIMessage(content="I found a seafront flat in Karsiyaka."),
    ])

    with patch("app.agent.runner.build_llm", return_value=fake):
        response = client.post("/api/chat", json={"message": "anything in Izmir?"})

    assert response.status_code == 200
    body = response.json()
    assert body["tools_used"] == ["search_property"]
    assert body["conversation_id"]


def test_chat_rejects_an_empty_message():
    assert client.post("/api/chat", json={"message": ""}).status_code == 422


def test_chat_rejects_a_missing_message():
    assert client.post("/api/chat", json={}).status_code == 422


def test_chat_returns_503_when_the_llm_is_unavailable():
    """A provider outage must be a clean JSON 503, never a stack trace."""
    with patch("app.agent.runner.build_llm", side_effect=Exception("no api key")):
        response = client.post("/api/chat", json={"message": "hello"})

    assert response.status_code == 503
    body = response.json()
    assert "error" in body
    assert body["request_id"]


def test_every_response_carries_a_request_id():
    assert client.get("/health").headers["X-Request-ID"]


# -------------------------------------------------------- plain REST access
#
# These endpoints share their services with the agent's tools. The tests assert
# that the business rules hold identically whichever door you come in through.

def test_properties_can_be_searched_without_the_llm():
    response = client.get("/api/properties", params={"city": "Izmir"})

    assert response.status_code == 200
    results = response.json()
    assert results
    assert all(item["city"] == "Izmir" for item in results)


def test_property_search_applies_every_filter():
    results = client.get("/api/properties", params={
        "city": "Istanbul", "max_price": 3000000, "min_bedrooms": 1,
    }).json()

    assert all(item["price"] <= 3000000 for item in results)
    assert all(item["bedrooms"] >= 1 for item in results)


def test_a_missing_property_is_a_clean_404():
    response = client.get("/api/properties/9999")

    assert response.status_code == 404
    assert "error" in response.json()


def test_free_slots_are_listed_for_a_property():
    body = client.get("/api/properties/1/slots").json()

    assert body["property_id"] == 1
    assert body["slots"]


def test_a_booking_can_be_made_over_plain_rest():
    slot = client.get("/api/properties/1/slots").json()["slots"][0]

    response = client.post("/api/bookings", json={
        "property_id": 1, "customer_name": "Ada Lovelace",
        "customer_phone": "05551112233", "slot": slot,
    })

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "confirmed"
    assert body["booking_id"]

    # The service rule, not the router, is what removes the slot.
    assert slot not in client.get("/api/properties/1/slots").json()["slots"]


def test_the_same_slot_cannot_be_booked_twice_over_rest():
    """The double-booking rule lives in the service, so it holds here too."""
    slot = client.get("/api/properties/1/slots").json()["slots"][0]
    payload = {"property_id": 1, "customer_name": "Ada Lovelace",
               "customer_phone": "05551112233", "slot": slot}

    assert client.post("/api/bookings", json=payload).status_code == 201

    second = client.post("/api/bookings", json=payload)
    assert second.status_code == 400
    assert "already booked" in second.json()["error"]


def test_booking_an_unoffered_slot_is_rejected():
    response = client.post("/api/bookings", json={
        "property_id": 1, "customer_name": "Ada Lovelace",
        "customer_phone": "05551112233", "slot": "1999-01-01 09:00",
    })

    assert response.status_code == 400


def test_booking_a_missing_property_is_a_404():
    slot = client.get("/api/properties/1/slots").json()["slots"][0]

    response = client.post("/api/bookings", json={
        "property_id": 9999, "customer_name": "Ada Lovelace",
        "customer_phone": "05551112233", "slot": slot,
    })

    assert response.status_code == 404


def test_booking_rejects_an_incomplete_body():
    assert client.post("/api/bookings", json={"property_id": 1}).status_code == 422


# -------------------------------------------------------------------- admin

def test_admin_requires_authentication():
    assert client.get("/admin").status_code == 401


def test_admin_rejects_a_wrong_password():
    assert client.get("/admin", auth=("admin", "wrong")).status_code == 401


def test_admin_dashboard_loads_with_credentials():
    response = client.get("/admin", auth=ADMIN)

    assert response.status_code == 200
    assert "Dashboard" in response.text


def test_admin_pages_all_render():
    for path in ("/admin/conversations", "/admin/prompt",
                 "/admin/properties", "/admin/escalations"):
        assert client.get(path, auth=ADMIN).status_code == 200, path


def test_admin_can_edit_the_system_prompt():
    response = client.post("/admin/prompt", auth=ADMIN,
                           data={"system_prompt": "You are a pirate."})

    assert response.status_code == 200

    from app.agent.prompts import get_system_prompt
    assert get_system_prompt() == "You are a pirate."


def test_conversation_detail_shows_the_tool_trace():
    fake = FakeLLM([
        AIMessage(content="", tool_calls=[{
            "name": "answer_faq", "args": {"question": "do you charge a commission?"},
            "id": "call_1", "type": "tool_call",
        }]),
        AIMessage(content="Our commission is 2% plus VAT."),
    ])

    with patch("app.agent.runner.build_llm", return_value=fake):
        conversation_id = client.post(
            "/api/chat", json={"message": "do you charge a commission?"}
        ).json()["conversation_id"]

    page = client.get("/admin/conversations/%s" % conversation_id, auth=ADMIN)

    assert page.status_code == 200
    assert "answer_faq" in page.text
