"""Tool = thin adapter over a service.

The docstring is not a comment for humans - it is the description sent to the
model, and it is the only thing the model uses to decide whether to call this
tool. Treat it as production code.
"""

import json
from typing import Optional

from langchain_core.tools import tool

from app.services import property_service


@tool
def search_property(city: Optional[str] = None,
                    property_type: Optional[str] = None,
                    min_bedrooms: Optional[int] = None,
                    max_price: Optional[int] = None) -> str:
    """Search the agency's available property listings.

    Use this whenever the customer describes what kind of home they are looking
    for, or asks what is available. All filters are optional - pass only what the
    customer actually mentioned, and leave the rest out.

    Args:
        city: City name, for example "Istanbul", "Izmir" or "Ankara".
        property_type: Either "apartment" or "villa".
        min_bedrooms: Minimum number of bedrooms the customer needs.
        max_price: Maximum budget in Turkish Lira.
    """
    results = property_service.search(
        city=city,
        property_type=property_type,
        min_bedrooms=min_bedrooms,
        max_price=max_price,
    )

    if not results:
        return json.dumps({
            "count": 0,
            "message": "No properties matched those filters. Suggest relaxing the "
                       "budget or trying a nearby city.",
        })

    return json.dumps({"count": len(results), "properties": results})
