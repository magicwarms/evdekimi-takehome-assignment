# AI Coding-Agent Usage

The brief asked for evidence of AI coding-agent usage, including my own review and
corrections. This is that record.

**Agent used:** Claude Code (Opus), driven from the terminal in this repository.

I want to be straightforward about the division of labour, because I think a vague answer
here is worth less than an honest one: **the agent wrote most of the lines in this repo.**
What follows is what I directed, what I rejected, and what I checked — which is the part
that actually decides whether the result is any good.

---

## How the work was split

| I did this | The agent did this |
|---|---|
| Set the requirements and the constraints | Proposed the file layout and the layering |
| Chose the framework, the runtime, and the admin approach | Wrote the SQL schema, seed data, services, tools, routers and templates |
| Reviewed each slice before moving to the next | Wrote the test suite once I asked for specific cases |
| Rejected the parts I disagreed with (below) | Drafted the architecture and scaling write-ups |
| Ran the verification myself | |

The working pattern was **one thin slice at a time**: ask for a layer, read it, correct
the design, then move on. I did not ask for the whole application in one go — I would not
have been able to review that, and reviewing it is the only thing that makes this useful.

---

## Where I overrode the agent

This is the section I would point to if asked how much of this was my judgement.

### 1. Framework: I chose LangChain over the agent's recommendation

The agent recommended a **raw OpenAI SDK loop** — roughly forty lines, no framework — and
argued it would be the easiest to explain and have the fewest dependencies. It was a
reasonable argument and I went the other way.

**My reasoning:** the brief explicitly mentions using an orchestration library, and
`bind_tools()` gives me the same native OpenAI function calling with a provider-agnostic
seam. If we later swap OpenAI for Anthropic or a local model, `build_llm()` changes and
nothing else does. I accepted a dependency to get that.

I did scope the dependency, though. We use exactly three things — the `@tool` decorator,
the message classes, and `bind_tools()` — so the repo depends on `langchain-core` and
`langchain-openai` only, not the full `langchain` package. Agent executors and chains
would have added dependencies and hidden the loop I want to be able to explain.

### 2. Runtime: I rejected the agent's plan to pin around Python 3.9

My machine had Python 3.9. The agent checked PyPI, found that the current
`langchain-core`, `fastapi`, `uvicorn`, `openai` and `pytest` all require 3.10+, and
produced a `requirements.txt` pinned to the last 3.9-compatible release of each.

It worked. I told it to install Python 3.12 instead.

**My reasoning:** it had optimised for "don't make the user install anything" over "ship
on a supported runtime." Python 3.9 reaches end of life and libraries are actively
dropping it. Shipping a stack of superseded pins to avoid a five-minute install is a bad
trade, and it is exactly the kind of thing a reviewer notices. This is the correction I am
most confident was right.

### 3. The videos: I caught a requirement the agent had misread

The agent's first plan had one 5–10 minute video with the scaling explanation as a segment
inside it. Re-reading the brief, those are two separate lines: a **5–10 min demo video**
under the deliverables, and the architecture-scaling explanation **"in a video, less than
5 minutes"** under the minimum requirements. That second number is a hard cap, not a
suggestion about a segment — and no single recording can be both longer than five minutes
and shorter than five minutes.

So the submission ships **two videos**: the demo, and a separate scaling explanation that
comes in under 5:00. Both are linked from the README. Reading two adjacent constraints as
one requirement is the kind of mistake that is cheap to make and expensive to discover
after submitting, which is why I re-read the brief against the plan rather than against my
memory of it.

### 4. I confirmed this document belongs in the submission

Re-reading the deliverables list, "evidence of AI coding-agent usage (prompts, generated
code, and your review/corrections)" is explicitly required and carries 15% of the rubric.
It is not optional, and I would rather describe my process accurately than leave someone
to guess at it.

---

## Direction I gave the agent

I did not keep a full transcript, so rather than reconstruct prompts from memory and
present them as verbatim, here is the substance of what I asked for, in order:

1. Read the brief and produce a **plan first, no code** — file layout and trade-offs, so I
   could disagree before anything was written.
2. Restructure so that **business logic does not live inside tool functions**, and explain
   what that separation buys.
3. Write the agent loop with specific guard rails: a cap on tool iterations, a timeout,
   and a failing tool must not kill the request.
4. Write tests that **pass without an OpenAI API key**, using a fake LLM. Cover tool
   chaining, the iteration cap, an unknown tool name, and a provider outage.
5. **Check every dependency's `requires-python` on PyPI before pinning.** Do not guess
   versions.

Point 5 is what surfaced the Python 3.9 problem in the first place.

---

## Defects found during the build

Three real defects, all in code that looked fine on the page. Two were caught by tests and
one by exercising the failure path by hand. All three are visible in the commit history.

### 1. The user's message was sent to the model twice — caught by a test

I asked for a test asserting that a brand-new conversation sends exactly two messages to
the model: the system prompt and the user's message. It failed with three.

The cause was real. `run_agent()` saved the incoming message to the database **before**
calling `load_history()`, so the message was replayed from the database *and* appended
again. Every turn duplicated the user's latest message in the model's context.

**Fix:** load history first, then persist the new turn — there is a comment in
`run_agent()` explaining why the order matters. Worth noting that nothing about the
application *looked* broken. Only an assertion on message count exposed it.

### 2. A client-construction failure escaped as an unhandled 500

`build_llm()` sat outside the `try` block, so a missing or malformed key produced an
unhandled exception rather than the intended 503.

**Fix:** wrapped, and reported as `LLMError`. Caught by
`test_chat_returns_503_when_the_llm_is_unavailable`.

### 3. A bad API key leaked the provider's error text to the client

Testing the failure path against the running server with a placeholder key, the 503
response body contained OpenAI's raw error — including a masked fragment of the key and an
account URL.

**Fix:** the full detail stays in the server log; the HTTP response carries the generic
`LLMError` message. Committed separately as `fix: do not return provider error text to
the client`.

---

## What I checked myself

Agent-written code reads plausibly whether or not it is correct, so nothing here was
accepted on appearance alone:

- **46 tests**, all passing with no API key: `python -m pytest -q`.
- Failure paths exercised by hand against the running server: empty body returns 422; an
  invalid API key returns a clean 503 with a request id and no stack trace.
- Every admin page loaded and checked for real data; `/admin` returns 401 without
  credentials.
- **The extensibility claim was tested, not asserted.** I added a sixth tool — one new
  file plus two lines in `ALL_TOOLS` — restarted, confirmed `/health` listed it, and
  reverted. That claim in `ARCHITECTURE.md` is measured, not aspirational.

Two of the three defects above were found by tests rather than by reading. That ratio is the
argument for writing the tests before trusting the code.

---

## What I would not delegate

Every row of the trade-off table in `ARCHITECTURE.md`.

Left alone, an agent will reach for Postgres, Redis and Celery in a take-home, because
more infrastructure reads as more competence. Deciding that SQLite is *correct here* — and
being able to say precisely when it stops being correct — is the judgement this assessment
is testing, and it is the last thing worth outsourcing.

The same was true of the scaling section. The agent's first draft was a generic "add
caching and horizontal scaling" list. The useful version needed the observation that this
service is I/O-bound and that the LLM is the cost bottleneck, not the CPU.

---

## Honest limitations

- I did not keep a verbatim prompt transcript from the start. Next time I would, because
  it is better evidence than a reconstruction.
- Tool-selection accuracy is verified by hand with the four `curl` examples in the README,
  not by an automated evaluation set. That is the weakest point in this submission, and
  building that eval set is first on the "what I would do next" list in
  `ARCHITECTURE.md`.
