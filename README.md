# Vet care agent

Demo of a vet care-plan platform for independent clinics on ezyVet:

- **Clinic dashboard**: a care-gap radar that ranks overdue care by value, one-click reminders,
  estimates to check and send to owners, visit recaps to write and release, care plans, and
  requests that owners sent from the app.
- **Owner app**: a page per pet, branded as the clinic, built around the moments owners get stuck:
  - **Costs:** the clinic's estimates in plain language, with what the plan includes and the year
    ahead.
  - **Last visit:** the recap, instructions to tick off, results, and the follow-up.
  - **Something not right?:** call now, see a vet within 24 hours, or keep an eye on it.
  - **First 90 days:** for new puppies and kittens.
  - **Weekly check-in:** for senior pets.
- **Care assistant** (beside the dashboard): raises what's due, checks plan value honestly, logs
  weights with consent, drafts notes for the vet, and prepares bookings. Anything that contacts
  the clinic waits for the owner to confirm. Urgent symptoms skip the model and tell the owner to
  call the clinic now.

`docs/business-model.md` explains the business: who pays, the pain points, and the data it
builds. `docs/owner-pain-points.md` has the ranked research behind the owner app.

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

The demo signs in as Priya, who has three pets: Biscuit (9-year-old Labrador, Senior plan),
Mango (cockatiel) and Pip (9-week-old kitten).

1. **Clinic dashboard** (`/clinic`): 8 care gaps worth $1,802, ranked by value. Biscuit carries
   a "Home check-ins: mobility down" tag.
2. **Owner app** (`/owner`), **Biscuit, Costs**: Dr Lee's estimate from Thursday's recheck, line by
   line. The screening is included in his plan, so the recommended part is $92. Tick *Hip
   X-rays*, tap **Go ahead**, then **Send to clinic** in Ask. Nothing is sent before that tap.
3. **Last visit**: tick off "lead walks only" (day 6 of 14), read the urine result in Dr Lee's
   words, and tap **Book it** for the recheck.
4. **Something not right?** Choose *Vomiting*, *1 to 3 days*, eating yes, bright yes: "See a vet
   within 24 hours" and a request for tomorrow's first slot. Try *Wobbly back legs (paralysis
   tick)*: "Call now", with the clinic's and the emergency vet's numbers.
5. **Pip**: First 90 days. Vaccination 2 from 12 Nov, home steps to tick, this week's tip, and the
   Puppy and Kitten plan (with an honest year-ahead comparison under Costs).
6. **Mango**: birds are asked to call the clinic rather than use the checker.
7. **Biscuit, Weekly check-in**: mobility lower for two weeks. Do this week's check-in, or tap **Ask
   for a check-up**. In **Data** (shield icon), turn sharing off and the clinic's tag disappears.
8. Back in the clinic dashboard, open **Requests** to see what Priya sent, and **Estimates** to see
   that she replied. Edit a line's wording and send again: her Costs section updates.
9. **Visit recaps**: write one for Pip (patient, summary, an instruction with days, a result) and
   release it. It appears under Last visit in Priya's app.

The mark at the top left is one of Priya's pets, picked at random on each visit. *Start over*
resets the current pet's conversation; `uv run vetagent --reset` wipes all demo state.

## Project layout

```
src/vetagent/
  domain/        pure rules: care gaps, plan value, estimates, recaps, triage, new-pet
                 pathway, check-in trend, cost forecast
  integrations/  PracticeSystem port + ezyVet adapter (mapping: docs/ezyvet.md)
  store/         SQLite for app-owned data
  agent/         loop, tools, safety gate, prompts, model adapters
  services/      clinic dashboard, owner dashboard (home.py) and owner agent use cases
  api/           FastAPI routes and wiring
  web/           static pages (no framework, no build step)
  data/ezyvet/   demo clinic as saved ezyVet API responses (fictional)
  data/demo_home.json   demo app-owned data (8 weeks of check-ins, a released visit recap)
docs/requirements.md   requirement IDs referenced by code and tests
tests/                 pytest
```

See `CLAUDE.md` for architecture rules and how to extend it.

## Credits

Pet silhouettes from [game-icons.net](https://game-icons.net), CC BY 3.0: sitting dog, rabbit
and kiwi by Delapouite, cat by Lorc.
