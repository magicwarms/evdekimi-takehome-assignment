import json

from langchain_core.tools import tool

from app.services import faq_service


@tool
def answer_faq(question: str) -> str:
    """Look up the agency's official answer to a common customer question.

    Use this for questions about commissions and fees, required documents,
    whether foreigners can buy, how long a purchase takes, office hours, and
    similar policy questions. Always prefer this over answering from your own
    knowledge, because only this tool has the agency's real policies.

    Args:
        question: The customer's question, in their own words.
    """
    matches = faq_service.search(question)

    if not matches:
        return json.dumps({
            "found": False,
            "message": "No official answer on file. Do not guess - offer to connect "
                       "the customer with a human colleague instead.",
        })

    return json.dumps({
        "found": True,
        "answers": [
            {"question": m["question"], "answer": m["answer"]} for m in matches
        ],
    })
