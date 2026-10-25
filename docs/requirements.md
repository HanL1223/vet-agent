# Requirements

Scope of the demo. Each requirement has an ID; code and tests reference these IDs.

## Clinic dashboard (B)

| ID | Requirement |
| --- | --- |
| CL-1 | Show today's KPIs: plan members, recurring plan revenue, pets with open care gaps, care value at risk. |
| CL-2 | List care gaps ranked by value, each with pet, owner, gap, reason, due status and value. |
| CL-3 | Filter care gaps by type: vaccination, parasite, senior screening, dental. |
| CL-4 | Send a reminder for one gap, or for all gaps shown. A sent reminder is recorded and shown. |
| CL-5 | Show the clinic's care plans with price, benefits and member count. |

## Care-gap rules (shared engine)

| ID | Rule |
| --- | --- |
| CG-1 | Vaccination is due 365 days after the last vaccination. Pets with no vaccination history are skipped. |
| CG-2 | A parasite product is due `repeat_days` after it was last dispensed. |
| CG-3 | Senior screening applies from age 8 (dogs) or 10 (cats). Due 365 days after the last screening, or on the senior birthday if never screened. |
| CG-4 | A dental finding with no later dental procedure is due from the finding date. |
| CG-5 | Status is `overdue` before today, `due_soon` within 14 days, otherwise not shown. |
| CG-6 | Value is the clinic's price-list amount for that care type. |

## Owner care agent (C)

| ID | Requirement |
| --- | --- |
| AG-1 | On open, the agent greets the owner and raises the pet's most important care gap without being asked. |
| AG-2 | The agent answers only from the pet's records and plan; it never diagnoses or suggests doses. |
| AG-3 | Urgent symptoms (for example a leg held up, collapse, bleeding, poisoning) skip the model and tell the owner to call the clinic now. |
| AG-4 | Actions that contact the clinic (booking request, note to the vet) are proposed first and run only after the owner confirms. |
| AG-5 | The owner can log a weight; it is shared with the clinic only if the owner's sharing consent is on. |
| AG-6 | "Is my plan worth it?" shows benefits used against plan payments, honestly. |
| AG-7 | Each agent reply lists what it did (tools used) so the owner can see its actions. |
| AG-8 | The demo runs with no API key using an offline scripted model; with a key it uses Claude, or OpenAI when `VETAGENT_PROVIDER=openai`. |

## Consent and privacy

| ID | Requirement |
| --- | --- |
| PR-1 | Two separate owner switches: share home log with the clinic; allow de-identified use. Both are stored with a timestamp. |
| PR-2 | De-identified use is off by default. |
| PR-3 | Clinic-sourced records stay in the practice-system adapter; app-owned data (chat, logs, consent, requests) lives in the app database. |
