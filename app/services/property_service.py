"""Business logic for property listings. Knows nothing about the LLM or HTTP."""

from typing import List, Optional

from app.database import query_all, query_one
from app.errors import NotFoundError


def search(city: Optional[str] = None,
           property_type: Optional[str] = None,
           min_bedrooms: Optional[int] = None,
           max_price: Optional[int] = None,
           limit: int = 5) -> List[dict]:
    """Filter available properties. Every filter is optional."""
    sql = "SELECT * FROM properties WHERE is_available = 1"
    params = []

    if city:
        sql += " AND LOWER(city) = LOWER(?)"
        params.append(city)
    if property_type:
        sql += " AND LOWER(property_type) = LOWER(?)"
        params.append(property_type)
    if min_bedrooms is not None:
        sql += " AND bedrooms >= ?"
        params.append(min_bedrooms)
    if max_price is not None:
        sql += " AND price <= ?"
        params.append(max_price)

    sql += " ORDER BY price ASC LIMIT ?"
    params.append(limit)

    return query_all(sql, tuple(params))


def get_by_id(property_id: int) -> dict:
    row = query_one("SELECT * FROM properties WHERE id = ?", (property_id,))
    if not row:
        raise NotFoundError("Property %s does not exist." % property_id)
    return row


def list_all() -> List[dict]:
    return query_all("SELECT * FROM properties ORDER BY id")
