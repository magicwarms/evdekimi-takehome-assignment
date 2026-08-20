"""Viewing appointment tools.

Both tools catch AppError and return it as JSON instead of raising. That is
deliberate: a raised exception would end the request, whereas a returned error
goes back into the conversation and lets the model apologise and offer another
slot on the very next turn.
"""

import json

from langchain_core.tools import tool

from app.errors import AppError
from app.services import booking_service


@tool
def list_viewing_slots(property_id: int) -> str:
    """List the viewing times that are still free for one property.

    Call this before book_viewing whenever the customer has not named a specific
    time, so you can offer them real options instead of guessing.

    Args:
        property_id: The id of the property, taken from search_property results.
    """
    try:
        slots = booking_service.list_slots(property_id)
    except AppError as exc:
        return json.dumps({"success": False, "error": exc.message})

    return json.dumps({"property_id": property_id, "available_slots": slots})


@tool
def book_viewing(property_id: int, customer_name: str,
                 customer_phone: str, slot: str) -> str:
    """Book a viewing appointment for a specific property.

    Only call this once you actually know all four arguments. If the customer has
    not given their name, phone number, or a preferred time, ask them for it
    first - never invent placeholder values.

    Args:
        property_id: The id of the property, taken from search_property results.
        customer_name: The customer's full name.
        customer_phone: A phone number we can reach the customer on.
        slot: The chosen time, formatted "YYYY-MM-DD HH:MM", taken from
            list_viewing_slots.
    """
    try:
        booking = booking_service.create_booking(
            property_id=property_id,
            customer_name=customer_name,
            customer_phone=customer_phone,
            slot=slot,
        )
    except AppError as exc:
        return json.dumps({"success": False, "error": exc.message})

    return json.dumps({"success": True, "booking": booking})
