"""Plain REST access to the property catalogue.

These endpoints call exactly the same services as the agent's tools. Nothing is
reimplemented here - that is the point. Because business logic lives in the
service layer rather than inside the tool functions, a capability written for the
agent is also available over ordinary HTTP, with no LLM call and no token spend,
for callers that already know what they want.
"""

from typing import List, Optional

from fastapi import APIRouter, Query

from app.logging_config import get_logger
from app.schemas import ErrorResponse, PropertyResponse, ViewingSlotsResponse
from app.services import booking_service, property_service

router = APIRouter(prefix="/api/properties", tags=["properties"])
logger = get_logger(__name__)

NOT_FOUND = {404: {"model": ErrorResponse}}


@router.get("", response_model=List[PropertyResponse])
def search_properties(
    city: Optional[str] = Query(None, description="Exact city name, case-insensitive."),
    property_type: Optional[str] = Query(None, description="apartment, villa, ..."),
    min_bedrooms: Optional[int] = Query(None, ge=0),
    max_price: Optional[int] = Query(None, ge=0),
    limit: int = Query(5, ge=1, le=50),
):
    """Search available listings. Every filter is optional."""
    return property_service.search(
        city=city,
        property_type=property_type,
        min_bedrooms=min_bedrooms,
        max_price=max_price,
        limit=limit,
    )


@router.get("/{property_id}", response_model=PropertyResponse, responses=NOT_FOUND)
def get_property(property_id: int):
    """One listing. Returns 404 if it does not exist."""
    return property_service.get_by_id(property_id)


@router.get("/{property_id}/slots", response_model=ViewingSlotsResponse,
            responses=NOT_FOUND)
def viewing_slots(property_id: int):
    """Viewing slots still free for this property."""
    return ViewingSlotsResponse(
        property_id=property_id,
        slots=booking_service.list_slots(property_id),
    )
