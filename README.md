# Vet care agent

Demo of a vet care-plan platform for independent clinics on ezyVet:

- **Clinic dashboard**: a care-gap radar that ranks overdue care by value, one-click reminders,
  care plans, and requests that owners sent from the agent.
- **Owner pet dashboard**: a page per pet, branded as the clinic. Tiles show what needs attention,
  a 30-second weekly check-in with its 8-week trend, parasite cover over the last 12 months, the
  next 12 months of care priced with and without the plan, and weight. A dropping check-in trend
  offers "Ask for a check-up", and the clinic sees it when the owner shares their log.
- **Care assistant** (beside the dashboard): raises what's due, checks plan value honestly, logs
  weights with consent, drafts notes for the vet, and prepares bookings. Anything that contacts
  the clinic waits for the owner to confirm. Urgent symptoms skip the model and tell the owner to
  call the clinic now.

`docs/business-model.md` explains the business: who pays, the pain points, and the data it
builds.

Runs offline with no API key (a scripted model drives the same agent loop and tools).
Add an Anthropic API key to use Claude.

## Run it

Requires [uv](https://docs.astral.sh/uv/). On Windows (PowerShell):

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Then, the same on Windows, macOS and Linux:

```powershell
uv sync                 # installs Python 3.12 if needed, plus all dependencies
uv run vetagent         # http://localhost:8000
```

The first run creates `.env` from `.env.example`. To use Claude, set `ANTHROPIC_API_KEY` in
`.env` and restart. To use OpenAI instead, set `VETAGENT_PROVIDER=openai` and `OPENAI_API_KEY`.

| Task | Command |
| --- | --- |
| Run the demo | `uv run vetagent` |
| Run with auto-reload while coding | `uv run vetagent --reload` |
| Wipe demo state and run | `uv run vetagent --reset` |
| Tests | `uv run pytest` |
| Lint and format check | `uv run ruff check src tests` and `uv run ruff format --check src tests` |

## Five-minute walkthrough

1. **Clinic dashboard** (`/clinic`): 8 care gaps worth $1,802, ranked by value. Biscuit carries
   a "Home check-ins: mobility down" tag from Priya's weekly check-ins.
2. **Owner dashboard** (`/owner`): Biscuit's check-in tile says mobility has been lower for two
   weeks. Tap **Ask for a check-up**, then **Send to clinic**. Nothing is sent before that tap.
3. **Next 12 months of care**: $944 pay-as-you-go against $708 on his Senior plan.
4. **Parasite cover**: 85% of the last year for flea and tick, with two gaps. Tap **Given today**.
5. Do this week's check-in (**Update this week** if you've already done one).
6. In **Ask**: *He's limping again* drafts a note for Dr Lee (no diagnosis); *He's holding his
   leg up* takes the urgent path with no model involved; *Log weight 31.2 kg* updates the tile.
7. Open **Data** (shield icon) and turn sharing off: the clinic's tag disappears.
8. Back in the clinic dashboard, open **Requests** to see what Priya sent.

*Start over* (under the chat) resets the conversation; `uv run vetagent --reset` wipes all demo
state, including check-ins.

## Project layout

```
src/vetagent/
  domain/        pure rules: care gaps, plan value, check-in trend, cover, cost forecast
  integrations/  PracticeSystem port + ezyVet adapter (mapping: docs/ezyvet.md)
  store/         SQLite for app-owned data
  agent/         loop, tools, safety gate, prompts, model adapters
  services/      clinic dashboard, owner dashboard (home.py) and owner agent use cases
  api/           FastAPI routes and wiring
  web/           static pages (no framework, no build step)
  data/ezyvet/   demo clinic as saved ezyVet API responses (fictional)
  data/demo_home.json   demo app-owned history (8 weeks of check-ins)
docs/requirements.md   requirement IDs referenced by code and tests
tests/                 pytest
```

See `CLAUDE.md` for architecture rules and how to extend it.

## Credits

Pet silhouettes from [game-icons.net](https://game-icons.net), CC BY 3.0: sitting dog, rabbit
and kiwi by Delapouite, cat by Lorc.
