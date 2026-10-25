# CLAUDE.md

Guidance for Claude (and humans) working in this repo.

## What this is

A demo of a vet care-plan platform with two faces:

- **Clinic dashboard** (`/clinic`): care-gap radar, reminders, plans, requests from owners.
- **Owner care agent** (`/owner`): a chat agent for one pet owner, branded as the clinic.

Requirements live in `docs/requirements.md` with IDs (CL-*, CG-*, AG-*, PR-*).
Code docstrings and test names reference these IDs. Start there before changing behaviour.

## Commands

```bash
make install   # venv + deps + copies .env.example to .env
make run       # http://localhost:8000 (uvicorn with reload)
make test      # pytest
make lint      # ruff check + format check
make reset     # delete the local SQLite file (fresh demo)
```

No API key needed: with `ANTHROPIC_API_KEY` empty the agent uses `ScriptedModel` (offline).
Set the key in `.env` to use Claude through the same loop and tools.

## Architecture (dependencies point inwards)

```
web/ (static HTML/JS) -> api/ (FastAPI routes) -> services/ (use cases)
                                                   |-> agent/ (loop, tools, safety, model adapters)
                                                   |-> domain/ (pure rules: care gaps, plan value)
                                                   |-> integrations/ (PracticeSystem port + seed adapter)
                                                   |-> store/ (SQLite for app-owned data)
```

- `domain/` is pure: no I/O, no framework imports. Put business rules here and unit-test them.
- `integrations/practice.py` defines the `PracticeSystem` protocol. `SeedPracticeSystem` reads
  `data/seed_clinic.json`. A real ezyVet adapter must implement the same protocol; nothing else changes.
- `store/sqlite.py` holds only data the app owns (chat, proposals, requests, weights, consent,
  reminders). Never copy clinic records into it (PR-3).
- `api/wiring.py` is the only place dependencies are chosen. Swap adapters there.
- `web/` holds no business or agent logic; it renders what the API returns.

## The agent

- `agent/loop.py`: `run_turn` = safety gate, then model -> tools -> model until a text reply,
  capped at `MAX_STEPS`.
- `agent/safety.py`: deterministic urgent-symptom triage. Urgent messages never reach the model (AG-3).
- `agent/tools.py`: every tool returns `ToolOutput(result, card)`. `result` goes to the model,
  `card` goes to the UI. `trace` text feeds "What I did" (AG-7).
- Tools that contact the clinic only create a **proposal**. Only `OwnerAgentService.confirm`
  sends anything to the clinic (AG-4). Keep it that way.
- `agent/llm.py`: `Model` protocol, `ClaudeModel`, `ScriptedModel`. Messages are stored in a
  provider-neutral format (see `agent/__init__.py`); adapters translate.
- `agent/prompts.py`: system prompt. The agent is not a vet: no diagnosis, no medicines or doses.

## Adding things

- **New care rule**: add a `_rule` function in `domain/care_gaps.py`, a requirement ID in
  `docs/requirements.md`, and a test in `tests/test_care_gaps.py`.
- **New agent tool**: write the handler in `agent/tools.py`, register it in `TOOLS`, add a card
  renderer in `web/owner.js` if it returns a card, teach `ScriptedModel` an intent if the offline
  demo should use it, and add a test.
- **New card type**: one function in the `CARDS` map in `web/owner.js`.
- **Real ezyVet**: new class in `integrations/` implementing `PracticeSystem`, chosen in
  `api/wiring.py`. Respect 60 calls/min per endpoint and 180/min per database; cache reads.

## Conventions

- Python 3.11+, type hints everywhere, `ruff` for lint and format (line length 100).
- Small functions, plain data classes, no clever metaprogramming. Prefer clarity over reuse.
- Code comments: short (one or two lines), explain why, not what.
- Tests: one behaviour per test, named after the requirement ID where one exists.
- Deliverable code holds no ad-hoc test or debug snippets; tests live in `tests/`.
- Dates: the demo pins "today" with `VETAGENT_TODAY` so care gaps are stable.

## Not built yet (next steps)

- Real ezyVet adapter and partner approval (IDEXX), CSV import for pilots.
- Auth and multi-tenant clinics/owners (demo uses one owner `o1` with pet `p1`).
- Reminder delivery (SMS/email), payments (Stripe direct debit), plan builder.
- Evals for the Claude path: urgent-symptom recall, no-diagnosis checks, proposal-not-claimed checks.
