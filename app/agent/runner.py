"""The agent loop.

The pattern is simple: send the conversation to the model. If the model asks for
tools, run them, append the results, and send everything back. Repeat until the
model replies with plain text or we hit the iteration cap.

The model - not our code - decides which tool to call. There is deliberately no
keyword matching anywhere in this file.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI

from app.agent.prompts import get_system_prompt
from app.agent.tools import ALL_TOOLS, TOOLS_BY_NAME
from app.config import settings
from app.database import execute, query_all, query_one
from app.errors import LLMError
from app.logging_config import get_logger

logger = get_logger(__name__)

FALLBACK_REPLY = (
    "Sorry, I got stuck working that out. Let me pass you to a colleague who can help."
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_llm():
    """Create the model client.

    Kept as its own function for two reasons: tests swap it for a fake, and
    changing LLM provider means editing this function and nothing else.
    """
    if not settings.openai_api_key:
        raise LLMError("OPENAI_API_KEY is not set.")

    llm = ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=0,
        timeout=30,
        max_retries=2,
    )
    return llm.bind_tools(ALL_TOOLS)


# --------------------------------------------------------------- conversation

def ensure_conversation(conversation_id: Optional[str],
                        user_id: Optional[str] = None) -> str:
    """Return an existing conversation id, or start a new conversation."""
    if conversation_id and query_one(
        "SELECT id FROM conversations WHERE id = ?", (conversation_id,)
    ):
        return conversation_id

    new_id = conversation_id or str(uuid.uuid4())
    execute(
        "INSERT INTO conversations (id, user_id, created_at) VALUES (?, ?, ?)",
        (new_id, user_id, _now()),
    )
    return new_id


def save_message(conversation_id: str, role: str, content: str,
                 tool_name: Optional[str] = None) -> None:
    execute(
        "INSERT INTO messages (conversation_id, role, content, tool_name, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (conversation_id, role, content, tool_name, _now()),
    )


def load_history(conversation_id: str, limit: int = 20) -> List:
    """Rebuild the LangChain message list from the database.

    Only user and assistant turns are replayed. Tool results are left out on
    purpose - the assistant reply already summarises them, and replaying raw
    tool JSON would burn context for no benefit.
    """
    rows = query_all(
        "SELECT role, content FROM messages "
        "WHERE conversation_id = ? AND role IN ('user', 'assistant') "
        "ORDER BY id DESC LIMIT ?",
        (conversation_id, limit),
    )
    rows.reverse()

    history = []
    for row in rows:
        if row["role"] == "user":
            history.append(HumanMessage(content=row["content"]))
        else:
            history.append(AIMessage(content=row["content"]))
    return history


# --------------------------------------------------------------------- tools

def run_tool(name: str, args: dict) -> str:
    """Run one tool. A failing tool must never crash the request."""
    tool = TOOLS_BY_NAME.get(name)
    if tool is None:
        logger.warning("Model asked for an unknown tool",
                       extra={"extra_data": {"tool": name}})
        return json.dumps({"error": "Unknown tool '%s'." % name})

    try:
        return tool.invoke(args)
    except Exception as exc:
        # Anything unexpected is reported back to the model rather than raised,
        # so it can apologise or try a different approach on the next turn.
        logger.exception("Tool failed", extra={"extra_data": {"tool": name}})
        return json.dumps({"error": "Tool '%s' failed: %s" % (name, exc)})


# ------------------------------------------------------------------ the loop

def run_agent(user_message: str,
              conversation_id: Optional[str] = None,
              user_id: Optional[str] = None,
              llm=None) -> dict:
    """Handle one user message end to end and return the assistant's reply."""
    conversation_id = ensure_conversation(conversation_id, user_id)

    # Read the earlier turns BEFORE storing this one, otherwise the new message
    # would be replayed from the database and appended again - the model would
    # see it twice.
    history = load_history(conversation_id)
    save_message(conversation_id, "user", user_message)

    if llm is None:
        # Building the client can fail too (missing key, bad base url). That is
        # still an "AI unavailable" problem, so report it as one rather than
        # letting it escape as an unhandled 500.
        try:
            llm = build_llm()
        except LLMError:
            raise
        except Exception:
            # The detail is in the log above; the client gets the generic
            # message so we never leak provider internals or key fragments.
            logger.exception("Could not build the LLM client")
            raise LLMError()

    messages = [SystemMessage(content=get_system_prompt())]
    messages.extend(history)
    messages.append(HumanMessage(content=user_message))

    tools_used = []

    for step in range(settings.max_tool_iterations):
        try:
            ai_message = llm.invoke(messages)
        except Exception:
            # Network error, bad API key, rate limit, provider outage. The full
            # detail goes to the log; the customer gets a generic message.
            logger.exception("LLM call failed", extra={"extra_data": {
                "conversation_id": conversation_id,
            }})
            save_message(conversation_id, "assistant", FALLBACK_REPLY)
            raise LLMError()

        messages.append(ai_message)

        # No tool calls means the model is done: this is the final answer.
        if not ai_message.tool_calls:
            reply = ai_message.text or FALLBACK_REPLY
            save_message(conversation_id, "assistant", reply)

            logger.info("Agent finished", extra={"extra_data": {
                "conversation_id": conversation_id,
                "steps": step + 1,
                "tools_used": tools_used,
            }})
            return {
                "conversation_id": conversation_id,
                "reply": reply,
                "tools_used": tools_used,
                "steps": step + 1,
            }

        for call in ai_message.tool_calls:
            logger.info("Tool call", extra={"extra_data": {
                "conversation_id": conversation_id,
                "tool": call["name"],
                "args": call["args"],
            }})

            result = run_tool(call["name"], call["args"])
            tools_used.append(call["name"])
            save_message(conversation_id, "tool", result, tool_name=call["name"])

            messages.append(ToolMessage(content=result, tool_call_id=call["id"]))

    # Safety net: the model kept asking for tools and never settled on an answer.
    logger.warning("Iteration cap reached", extra={"extra_data": {
        "conversation_id": conversation_id,
        "tools_used": tools_used,
    }})
    save_message(conversation_id, "assistant", FALLBACK_REPLY)
    return {
        "conversation_id": conversation_id,
        "reply": FALLBACK_REPLY,
        "tools_used": tools_used,
        "steps": settings.max_tool_iterations,
    }
