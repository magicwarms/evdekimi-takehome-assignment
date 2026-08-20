"""Tool registry.

This is the extensibility seam of the whole service. To add a capability:

  1. create a new file in this folder containing an @tool function,
  2. import it here and add it to ALL_TOOLS.

Nothing else changes - not the agent loop, not the router, not the prompt. A
future second agent (say, a landlord-facing one) is just a different system
prompt plus a different subset of this list.
"""

from app.agent.tools.answer_faq import answer_faq
from app.agent.tools.book_viewing import book_viewing, list_viewing_slots
from app.agent.tools.escalate_to_human import escalate_to_human
from app.agent.tools.search_property import search_property

ALL_TOOLS = [
    search_property,
    list_viewing_slots,
    book_viewing,
    answer_faq,
    escalate_to_human,
]

TOOLS_BY_NAME = {t.name: t for t in ALL_TOOLS}
