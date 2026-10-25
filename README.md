# Vet care agent

Demo of a vet care-plan platform for independent clinics on ezyVet:

- **Clinic dashboard**: a care-gap radar that ranks overdue care by value, one-click reminders,
  care plans, and requests that owners sent from the agent.
- **Owner care agent**: a chat assistant branded as the clinic. It raises what's due, checks
  plan value honestly, logs weights with consent, drafts notes for the vet, and prepares bookings.
  Anything that contacts the clinic waits for the owner to confirm. Urgent symptoms skip the
  model and tell the owner to call the clinic now.

Runs offline with no API key (a scripted model drives the same agent loop and tools).
Add an Anthropic API key to use Claude.

## Run it

Requires Python 3.11+.

```bash
make install
make run
```

Open http://localhost:8000.

On Windows (PowerShell), without `make`:

```powershell
py -m venv .venv
.venv\Scripts\pip install -e ".[dev]"
copy .env.example .env
.venv\Scripts\uvicorn vetagent.api.app:create_app --factory --reload --port 8000 --env-file .env
```

To use Claude, set `ANTHROPIC_API_KEY` in `.env` and restart.

## Five-minute walkthrough

1. **Clinic dashboard** (`/clinic`): 8 care gaps worth $1,802, ranked by value. Filter to
   *Senior*, send Biscuit's reminder, and watch the KPI update.
2. **Owner agent** (`/owner`): it greets Priya and raises Biscuit's overdue senior screening.
3. Tap *Is my plan worth it?*: $590 paid vs $412 used, and the screening would put her ahead.
4. Tap *Book his screening*, then **Send to clinic**. Nothing is sent before that tap.
5. Tap *He's limping again*: the agent won't diagnose, it drafts a note for Dr Lee.
6. Tap *He's holding his leg up*: urgent path, "call the clinic now", no model involved.
7. Tap *Log weight 31.2 kg*. Open **Data** (shield icon), turn sharing off, log again.
8. Back in the clinic dashboard, open **Requests** to see what Priya sent.

*Start over* (under the chat) resets the conversation; `make reset` wipes all demo state.

## Project layout

```
src/vetagent/
  domain/        pure rules: care gaps, plan value
  integrations/  PracticeSystem port + seed (ezyVet-shaped) adapter
  store/         SQLite for app-owned data
  agent/         loop, tools, safety gate, prompts, model adapters
  services/      clinic dashboard + owner agent use cases
  api/           FastAPI routes and wiring
  web/           static pages (no framework, no build step)
  data/          seed clinic data
docs/requirements.md   requirement IDs referenced by code and tests
tests/                 pytest
```

See `CLAUDE.md` for architecture rules and how to extend it.
