# AI Coding-Agent Usage

The brief asked for evidence of AI coding-agent usage, including my own review and
corrections. This is that log, written as an engineering record rather than a transcript
dump.

**Agent used:** Claude Code (Opus), driven from the terminal in this repository.

---

## How I split the work

The split I aimed for: **I decide the shape, the agent types the volume.**

| I decided | The agent produced |
|---|---|
| The layering, and the rule that tools hold no business logic | The SQL schema and the seed data |
| That tool docstrings — not code — carry the tool-selection signal | Jinja2 templates and their CSS |
| The iteration cap and the "tools return errors, never raise" contract | Boilerplate: Pydantic schemas, router wiring, the JSON log formatter |
| Every row of the trade-off table in `ARCHITECTURE.md` | First drafts of the service functions |
| The scaling story, and that the bottleneck is cost/latency not CPU | Test scaffolding once I had specified the cases |
| Which library to depend on, and which to leave out | |

The pattern that worked: ask for a **thin slice end to end**, read it, correct the design,
then ask for the next slice. Asking for the whole app at once produced code I could not
have defended, which defeats the purpose.

---

## Representative prompts

Verbatim, in the order I used them.

> Build a plan for this take-home first, don't write code yet. Python, FastAPI, LangChain
> for tool calling, OpenAI. The AI must choose the tool itself — no keyword if/else
> routing, that's an explicit requirement. Show me the file layout and the trade-offs
> before you touch anything.

> Where does the business logic go? I don't want booking rules living inside a tool
> function. Restructure so tools are thin adapters over a service layer, and explain what
> that buys me.

> Write the agent loop. Guard rails I want: a cap on tool iterations, a timeout, and a
> failing tool must not kill the request — the error goes back to the model so it can
> recover on the next turn.

> Now write tests for that loop that pass without an OpenAI API key. Use a fake LLM that
> replays scripted messages. Cover: tool chaining, the iteration cap, an unknown tool
> name, and a provider outage.

> Check every dependency's `requires-python` on PyPI before you pin anything. Don't guess
> versions.

---

## What it got wrong, and how I caught it

This is the part worth reading.

### 1. It pinned a whole stack around an outdated runtime

My machine had Python 3.9, so the agent's first `requirements.txt` pinned every library to
its last 3.9-compatible release. It worked — and it was the wrong call. Checking
`requires-python` on PyPI showed the current `langchain-core`, `fastapi`, `uvicorn`,
`openai` and `pytest` all require 3.10+. The agent had quietly optimised for "don't make
the user install anything" over "ship on a supported runtime."

**Correction:** installed Python 3.12, pinned to current releases. Working around an
outdated runtime to save a five-minute install is a bad trade, and a reviewer would have
spotted the stale versions immediately.

### 2. Keyword routing crept in

An early draft of the runner had a helper that looked at the message text and pre-selected
a tool before calling the model. That directly violates the brief.

**Correction:** deleted it, and moved the selection signal into the tool docstrings where
the model can actually use it. This also reframed how I think about the tools: a docstring
is production code here, not a comment. The current rule in the repo is that if the model
picks the wrong tool, the fix is the docstring, never an `if`.

### 3. Tools raised exceptions instead of returning errors

The first `book_viewing` let `ValidationError` propagate. Booking an already-taken slot
returned a 500 and ended the conversation.

**Correction:** tools now catch `AppError` and return `{"success": false, "error": ...}`.
The error goes back into the conversation as a `ToolMessage`, so the model apologises and
offers a different slot on the very next turn — which is the behaviour a customer would
expect. This is now a stated contract in `ARCHITECTURE.md`.

### 4. `while True` in the agent loop

The first runner looped until the model stopped asking for tools. One confused model and
that is an unbounded spend.

**Correction:** `MAX_TOOL_ITERATIONS`, configurable, with a fallback reply and a warning
log when it trips. `test_agent_stops_at_the_iteration_cap` pins the behaviour.

### 5. A bug my own test spec caught: the user message was sent twice

I asked for a test asserting that a brand-new conversation sends exactly two messages to
the model (system prompt + the user's message). It failed with 3.

The cause was real: `run_agent()` saved the incoming message to the database **before**
calling `load_history()`, so the message was replayed from the database *and* appended
again. Every turn duplicated the user's latest message in the model's context — wasting
tokens and probably skewing the model's attention.

**Correction:** load history first, then persist the new turn — see the comment in
`run_agent()` explaining why the order matters. Worth noting: nothing about the app
*looked* broken. Only the assertion on message count exposed it.

### 6. A bad API key leaked the provider's error text to the client

Testing the failure path with a placeholder key, the 503 response body contained OpenAI's
raw error — including a masked fragment of the key and an account URL.

**Correction:** the full detail stays in the server log; the HTTP body gets the generic
`LLMError` message. Fixed in its own commit.

---

## What I would not delegate

Every row of the trade-off table in `ARCHITECTURE.md`. An agent will happily produce a
Postgres-plus-Redis-plus-Celery architecture for a take-home, because more infrastructure
reads as more competence. Deciding that SQLite is *correct here* — and being able to say
exactly when it stops being correct — is the judgment the assessment is actually testing,
and it is not something to outsource.

The same applies to the scaling section. The agent's first draft was a generic
"add caching and horizontal scaling" list. The useful version required knowing that this
particular service is I/O-bound and that the LLM is the cost bottleneck, not the CPU.

---

## Verification, not vibes

Because agent-written code reads plausibly whether or not it is correct, nothing here was
accepted on appearance:

- **37 tests**, all passing without an API key (`python -m pytest -q`).
- The failure paths were exercised by hand against the running server: empty body → 422,
  invalid API key → clean 503 with a request id and no stack trace.
- Two of the six defects above were found by tests, not by reading. That ratio is the
  argument for writing the tests first.
