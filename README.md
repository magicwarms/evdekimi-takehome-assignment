# Real Estate AI Assistant — Agentic Backend

A backend service for a real estate AI assistant. It answers agency FAQs, searches
property listings, and books viewing appointments — and it decides **on its own** which of
those to do, using LLM function calling. There is no keyword routing in this codebase.

- **Architecture and trade-offs:** [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- **AI coding-agent log:** [`docs/AI_USAGE.md`](docs/AI_USAGE.md)
- **Plan the build followed:** [`PLAN.md`](PLAN.md)

---

## Setup

Requires **Python 3.10+** (built and tested on 3.12).

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python --version                 # confirm 3.12.x before continuing

pip install -r requirements.txt
copy .env.example .env           # then paste your OpenAI key into .env
python -m app.seed               # creates app.db with demo properties and FAQs
uvicorn app.main:app --reload
```

macOS / Linux: `python3 -m venv .venv && source .venv/bin/activate`, and `cp` instead of
`copy`.

| URL | What it is |
|---|---|
| http://127.0.0.1:8000/docs | Swagger UI — try the API in a browser |
| http://127.0.0.1:8000/health | Liveness, plus the list of registered tools |
| http://127.0.0.1:8000/admin | Admin pages (`admin` / `admin123`) |

### Configuration

Everything is read from `.env`; nothing is hardcoded.

| Variable | Default | Purpose |
|---|---|---|
| `OPENAI_API_KEY` | — | Required for real conversations. Tests do not need it. |
| `OPENAI_MODEL` | `gpt-4o-mini` | Any OpenAI model that supports tool calling. |
| `MAX_TOOL_ITERATIONS` | `5` | Guard rail: how many tool rounds before the agent gives up. |
| `DATABASE_PATH` | `app.db` | SQLite file. |
| `ADMIN_USERNAME` / `ADMIN_PASSWORD` | `admin` / `admin123` | HTTP Basic auth on `/admin`. |
| `LOG_LEVEL` | `INFO` | Standard Python levels. |

---

## Try it

Each response includes `tools_used`, so you can see which tool the model chose without
reading the logs.

```bash
# FAQ -> the model should choose answer_faq
curl -X POST localhost:8000/api/chat -H "Content-Type: application/json" \
  -d '{"message":"Do you charge a commission?"}'

# Search -> search_property
curl -X POST localhost:8000/api/chat -H "Content-Type: application/json" \
  -d '{"message":"I need a 2 bedroom flat in Istanbul under 5 million"}'

# Booking -> list_viewing_slots, then book_viewing
curl -X POST localhost:8000/api/chat -H "Content-Type: application/json" \
  -d '{"message":"Book a viewing for property 1. I am Ada Lovelace, 05551112233","conversation_id":"demo"}'

# Handover -> escalate_to_human
curl -X POST localhost:8000/api/chat -H "Content-Type: application/json" \
  -d '{"message":"I want to negotiate the price, let me talk to a real person"}'
```

Example response:

```json
{
  "conversation_id": "3f8c1a92-...",
  "reply": "Our commission is 2% of the sale price plus VAT, paid only after the sale closes.",
  "tools_used": ["answer_faq"],
  "steps": 2
}
```

Pass the returned `conversation_id` back on the next request to continue the conversation.

### The same capabilities without the model

Because the business rules live in services rather than inside the tools, every capability
the agent has is also a plain REST endpoint — no LLM call, no token spend — for callers
that already know what they want.

| Endpoint | What it does |
|---|---|
| `GET /api/properties?city=Izmir&max_price=6000000` | Search listings |
| `GET /api/properties/{id}` | One listing, `404` if it does not exist |
| `GET /api/properties/{id}/slots` | Viewing slots still free |
| `POST /api/bookings` | Book a viewing directly |

```bash
curl -X POST localhost:8000/api/bookings -H "Content-Type: application/json" \
  -d '{"property_id":1,"customer_name":"Ada Lovelace","customer_phone":"05551112233","slot":"2026-08-22 10:00"}'
```

These routers hold no logic of their own. `POST /api/bookings` calls the same
`booking_service.create_booking()` the `book_viewing` tool calls, so the same rules apply:
book that slot twice and the second attempt is a `400`, whichever door you came in through.

## Demo video
Demo: https://www.loom.com/share/29a3c694279f40eba9fc15c4af9155fd

---

## Admin pages

Server-rendered with Jinja2 — no build step, no JavaScript framework.

| Page | What it shows |
|---|---|
| `/admin` | Counts: conversations, messages, bookings, open escalations, listings, FAQs |
| `/admin/conversations` | Every conversation, newest first |
| `/admin/conversations/{id}` | **The full trace** — customer turn, which tool the model chose, the raw tool JSON, the final reply |
| `/admin/prompt` | Edit the system prompt. It is stored in the database, so changes apply immediately with no redeploy |
| `/admin/properties` | Listings and bookings |
| `/admin/escalations` | Handovers to a human, with a Close button |

The conversation trace is the page worth looking at: it makes the agent's tool choice
visible per turn.

---

## Tests

```bash
python -m pytest -q       # 46 tests, no API key needed
```

The agent loop is tested against a `FakeLLM` that replays scripted messages, so the loop,
the iteration cap, unknown-tool handling, provider failure and history replay are all
covered without network calls or spend.

---

## Design decisions

The full reasoning is in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md); the short version:

- **Tools contain no business logic.** They are thin adapters over a service layer, so the
  same `booking_service.create_booking()` is reachable from the agent, from
  `POST /api/bookings`, from the admin page, and from any future agent — without
  duplication. The tests assert the rules hold on every one of those paths.
- **Tool choice belongs to the model.** The system prompt describes a role, not routing
  rules. Each tool's docstring says *when* to use it, and that docstring is what the model
  actually reads. If the model picks wrong, the fix is the docstring, not an `if`.
- **Adding a capability is two lines.** New file in `app/agent/tools/`, plus one import and
  one entry in `ALL_TOOLS`. Nothing else changes.
- **A failing tool never kills the request.** It returns `{"success": false, "error": ...}`
  to the model, which can then apologise or offer an alternative in the same turn.
- **SQLite on purpose**, so a reviewer can clone and run. `app/database.py` is the only
  file that knows about it.

---

## Project layout

```
app/
  main.py              FastAPI app: routers, middleware, error handlers
  config.py            Settings from .env
  logging_config.py    JSON logging
  errors.py            Exceptions, each mapped to an HTTP status
  schemas.py           Request/response models
  database.py          The only file that knows about SQLite
  seed.py              Demo data
  agent/
    runner.py          The agent loop
    prompts.py         System prompt (stored in the DB, editable in admin)
    tools/__init__.py  Tool registry -- the extensibility seam
    tools/*.py         One file per tool
  services/            All business logic
  routers/             chat, properties, bookings, health, admin
  templates/           Jinja2 admin pages
tests/                 46 tests, no API key required
docs/                  Architecture, diagram source, AI usage log
```

---

## Explanation video: Explain how your architecture would scale to 100× traffic

The video is deliberately kept **under 5 minutes**, because the brief requires the
architecture-scaling explanation to be delivered in a video of less than five minutes.
The long-form version of everything it covers is in
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

The video: https://www.loom.com/share/347c70bd3dd9410192cfd74ee13a48c0