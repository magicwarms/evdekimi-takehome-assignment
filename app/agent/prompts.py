"""The system prompt describes the assistant's ROLE, not routing rules.

Note what is deliberately NOT in here: no "if the user mentions price, call
answer_faq". Choosing the tool is the model's job - that is the whole point of
the assignment. The only selection signal we give it is each tool's docstring.

The live prompt is stored in the database so it can be edited from the admin
page without a redeploy. DEFAULT_SYSTEM_PROMPT is only the seed value.
"""

from app.database import execute, query_one

DEFAULT_SYSTEM_PROMPT = """You are Eva, a helpful real estate assistant for a Turkish \
property agency.

You help customers with three things: answering questions about our agency and the \
buying process, finding properties that match what they want, and booking viewing \
appointments.

Guidelines:
- Use the tools available to you to get real information. Never invent property \
details, prices, availability, or policies.
- Before booking a viewing you need a property, the customer's full name, their phone \
number, and a time slot. Ask for whatever is missing instead of guessing.
- If the customer asks for something outside your abilities, seems frustrated, asks to \
speak to a person, or wants to negotiate price or legal terms, hand the conversation to \
a human colleague.
- Keep replies short and friendly. Reply in the customer's language.
- Always reply in English unless the customer writes in Turkish, in which case reply in Turkish.
"""


def get_system_prompt():
    """Read the live prompt from the database, falling back to the default."""
    row = query_one("SELECT value FROM settings WHERE key = 'system_prompt'")
    return row["value"] if row else DEFAULT_SYSTEM_PROMPT


def set_system_prompt(value):
    execute(
        "INSERT INTO settings (key, value) VALUES ('system_prompt', ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (value,),
    )
