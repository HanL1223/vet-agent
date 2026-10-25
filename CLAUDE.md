# CLAUDE.md

Guidance for Claude (and humans) working in this repo.

## What this is

A demo of a vet care-plan platform with two faces:

- **Clinic dashboard** (`/clinic`): care-gap radar, reminders, plans, requests from owners.
- **Owner app** (`/owner`): one page per pet the owner has. Sections: Costs (estimates and the year
  ahead), Last visit, "Something not right?", First 90 days, Coming up and, for seniors, a weekly
  check-in. The care agent sits beside them as "Ask". Branded as the clinic. See
  `docs/owner-pain-points.md` for why these sections.

Requirements live in `docs/requirements.md` with IDs (CL-*, CG-*, AG-*, OW-*, CO-*, VR-*, TR-*,
NP-*, HT-*, BR-*, PR-*).
Code docstrings and test names reference these IDs. Start there before changing behaviour.

## Commands

The project uses **uv** and is developed on **Windows** (PowerShell). Commands are the same on
every OS; never add Makefiles, shell scripts or POSIX-only paths.

```powershell
uv sync                                  # Python 3.12 + deps (dev group included)
uv run vetagent                          # http://localhost:8000; creates .env on first run
uv run vetagent --reload                 # auto-reload while coding
uv run vetagent --reset                  # delete the SQLite file, then start (fresh demo)
uv run pytest                            # tests
uv run ruff check src tests              # lint
uv run ruff format src tests             # format
uv add <package> / uv add --dev <pkg>    # dependencies (updates uv.lock; commit it)
```

Use `pathlib` for paths and avoid `%-d`-style strftime codes (not supported on Windows).

No API key needed: with the provider's key empty the agent uses `ScriptedModel` (offline).
`VETAGENT_PROVIDER` picks `anthropic` (default, `ANTHROPIC_API_KEY`) or `openai` (`OPENAI_API_KEY`);
set the key in `.env` to use that model through the same loop and tools.

## Architecture (dependencies point inwards)

```
web/ (static HTML/JS) -> api/ (FastAPI routes) -> services/ (use cases)
                                                   |-> agent/ (loop, tools, safety, model adapters)
                                                   |-> domain/ (pure rules: care gaps, plan value)
                                                   |-> integrations/ (PracticeSystem port + ezyVet adapter)
                                                   |-> store/ (SQLite for app-owned data)
```

- `domain/` is pure: no I/O, no framework imports. Put business rules here and unit-test them.
- `integrations/practice.py` defines the `PracticeSystem` protocol. `EzyVetPracticeSystem`
  (`integrations/ezyvet.py`) implements it by mapping ezyVet API records to domain models. The demo
  reads saved ezyVet list responses from `data/ezyvet/` (fictional clinic) through `FileSource`.
  `data/ezyvet/clinic_config.json` holds per-clinic settings ezyVet doesn't know.
- `store/sqlite.py` holds only data the app owns (chat per owner and pet, proposals, requests,
  weights, consent, reminders, check-ins, released recaps, ticks, triage answers). Never copy
  clinic records into it (PR-3).
- `services/home.py` builds each pet's page from pure rules in `domain/` (`estimates.py`,
  `recaps.py`, `triage.py`, `pathway.py`, `checkins.py`, `forecast.py`). It never contacts the
  clinic. Dashboard actions (estimate replies, triage requests, recap follow-ups, check-ups) go
  through `OwnerAgentService.propose_*`, so they land in Ask as proposals and AG-4 still holds.
- Owner endpoints take `?pet=`; `HomeService.pet` refuses pets the owner doesn't have (OW-1).
  `data/demo_home.json` seeds check-ins and a released visit recap.
- `domain/triage.py` is demo content: each clinic's vets approve their own symptom list. Keep its
  red flags in step with `agent/safety.py` (AG-3).
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
- `agent/llm.py`: `Model` protocol, `ClaudeModel`, `OpenAIModel`, `ScriptedModel`. Messages are stored in a
  provider-neutral format (see `agent/__init__.py`); adapters translate.
- `agent/prompts.py`: system prompt. The agent is not a vet: no diagnosis, no medicines or doses.

## Adding things

- **New care rule**: add a `_rule` function in `domain/care_gaps.py`, a requirement ID in
  `docs/requirements.md`, and a test in `tests/test_care_gaps.py`.
- **New agent tool**: write the handler in `agent/tools.py`, register it in `TOOLS`, add a card
  renderer in `web/owner.js` if it returns a card, teach `ScriptedModel` an intent if the offline
  demo should use it, and add a test.
- **New card type**: one function in the `CARDS` map in `web/owner.js`. Follow `docs/design.md`.
- **New owner section**: a pure rule in `domain/`, a section in `HomeService.dashboard`, a
  `<section class="tile">` slot in `web/owner.html`, one function in the `TILES` map in
  `web/dashboard.js` (return "" to hide it), a requirement ID and a test.
- **Real ezyVet**: a live `EzyVetSource` (OAuth, paging) in `integrations/ezyvet.py`, passed to
  `EzyVetPracticeSystem` in `api/wiring.py`. Demo data changes go in `data/ezyvet/` in the same shape. Respect 60 calls/min per endpoint and 180/min per database; cache reads.

## Conventions

- Python 3.11+, type hints everywhere, `ruff` for lint and format (line length 100).
- Small functions, plain data classes, no clever metaprogramming. Prefer clarity over reuse.
- Code comments: short (one or two lines), explain why, not what.
- Tests: one behaviour per test, named after the requirement ID where one exists.
- Deliverable code holds no ad-hoc test or debug snippets; tests live in `tests/`.
- Dates: the demo pins "today" with `VETAGENT_TODAY` so care gaps are stable.

## Not built yet (next steps)

- Real ezyVet adapter and partner approval (IDEXX), CSV import for pilots. See `docs/ezyvet.md`.
- Auth and multi-tenant clinics/owners (demo signs in as one owner, Priya `501`, with Biscuit,
  Mango and Pip).
- Clinic-side recap editor and estimate publishing (the demo seeds both); medication log.
- Reminder delivery (SMS/email), payments (Stripe direct debit), plan builder.
- Evals for the Claude path: urgent-symptom recall, no-diagnosis checks, proposal-not-claimed checks.
