import pytest

from app.errors import NotFoundError, ValidationError
from app.services import booking_service, faq_service, property_service


def test_search_filters_by_city_and_budget():
    results = property_service.search(city="Istanbul", max_price=5000000)

    assert results
    assert all(r["city"] == "Istanbul" and r["price"] <= 5000000 for r in results)


def test_search_without_filters_returns_listings():
    assert len(property_service.search()) > 0


def test_search_returns_empty_for_impossible_filters():
    assert property_service.search(city="Atlantis") == []


def test_get_by_id_raises_for_unknown_property():
    with pytest.raises(NotFoundError):
        property_service.get_by_id(9999)


def test_faq_search_matches_keywords():
    results = faq_service.search("how much is your commission?")

    assert results
    assert "commission" in results[0]["question"].lower()


def test_faq_search_returns_nothing_for_unrelated_question():
    assert faq_service.search("what is the weather on mars") == []


def test_booking_succeeds_and_removes_the_slot():
    slot = booking_service.list_slots(1)[0]

    booking = booking_service.create_booking(1, "Ada Lovelace", "+905550001", slot)

    assert booking["status"] == "confirmed"
    assert slot not in booking_service.list_slots(1)


def test_double_booking_is_rejected():
    slot = booking_service.list_slots(1)[0]
    booking_service.create_booking(1, "Ada Lovelace", "+905550001", slot)

    with pytest.raises(ValidationError):
        booking_service.create_booking(1, "Alan Turing", "+905550002", slot)


def test_unknown_slot_is_rejected():
    with pytest.raises(ValidationError):
        booking_service.create_booking(1, "Ada Lovelace", "+905550001", "not-a-slot")
