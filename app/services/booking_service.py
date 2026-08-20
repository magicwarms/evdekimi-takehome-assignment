"""Business logic for viewing appointments."""

from datetime import datetime, timezone
from typing import List

from app.database import execute, query_all, query_one
from app.errors import ValidationError
from app.services import property_service

# In a real system these would come from an agent's calendar. Hardcoding them
# keeps the MVP demoable without a calendar integration.
AVAILABLE_SLOTS = [
    "2026-08-22 10:00",
    "2026-08-22 14:00",
    "2026-08-23 11:00",
    "2026-08-24 16:00",
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def list_slots(property_id: int) -> List[str]:
    property_service.get_by_id(property_id)  # raises NotFoundError if missing

    taken = [row["slot"] for row in query_all(
        "SELECT slot FROM bookings WHERE property_id = ? AND status = 'confirmed'",
        (property_id,),
    )]
    return [slot for slot in AVAILABLE_SLOTS if slot not in taken]


def create_booking(property_id: int, customer_name: str,
                   customer_phone: str, slot: str) -> dict:
    prop = property_service.get_by_id(property_id)

    if slot not in AVAILABLE_SLOTS:
        raise ValidationError(
            "Slot '%s' is not offered. Available slots: %s"
            % (slot, ", ".join(AVAILABLE_SLOTS))
        )

    already_taken = query_one(
        "SELECT id FROM bookings "
        "WHERE property_id = ? AND slot = ? AND status = 'confirmed'",
        (property_id, slot),
    )
    if already_taken:
        raise ValidationError("That slot is already booked. Please pick another one.")

    booking_id = execute(
        "INSERT INTO bookings (property_id, customer_name, customer_phone, slot, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (property_id, customer_name, customer_phone, slot, _now()),
    )

    return {
        "booking_id": booking_id,
        "property_id": property_id,
        "property_title": prop["title"],
        "customer_name": customer_name,
        "slot": slot,
        "status": "confirmed",
    }


def list_all() -> List[dict]:
    return query_all(
        "SELECT b.*, p.title AS property_title "
        "FROM bookings b LEFT JOIN properties p ON p.id = b.property_id "
        "ORDER BY b.id DESC"
    )
