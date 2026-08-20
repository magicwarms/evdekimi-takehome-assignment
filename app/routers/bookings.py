"""Plain REST access to viewing appointments.

`booking_service.create_booking()` is the same function `book_viewing` hands its
arguments to, so the booking rules - the property must exist, the slot must be
one we offer, a confirmed slot cannot be double-booked - hold identically here.
A 400 or a 404 from this endpoint comes from the service, not from the router.
"""

from fastapi import APIRouter, status

from app.logging_config import get_logger
from app.schemas import BookingRequest, BookingResponse, ErrorResponse
from app.services import booking_service

router = APIRouter(prefix="/api/bookings", tags=["bookings"])
logger = get_logger(__name__)


@router.post("", response_model=BookingResponse,
             status_code=status.HTTP_201_CREATED,
             responses={400: {"model": ErrorResponse},
                        404: {"model": ErrorResponse}})
def create_booking(payload: BookingRequest):
    """Book a viewing directly, without going through the assistant."""
    logger.info("Booking request", extra={"extra_data": {
        "property_id": payload.property_id,
        "slot": payload.slot,
    }})
    return booking_service.create_booking(
        property_id=payload.property_id,
        customer_name=payload.customer_name,
        customer_phone=payload.customer_phone,
        slot=payload.slot,
    )
