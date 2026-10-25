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
| CL-6 | Deceased or inactive patients are left out of every list, count and reminder. |

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

## Owner pet dashboard (HT)

| ID | Requirement |
| --- | --- |
| HT-1 | The owner can do a weekly check-in: five questions (appetite, energy, mobility, comfort, toileting), each 0 to 4. One per pet per ISO week; checking in again that week replaces it. |
| HT-2 | Trends use calendar weeks: the latest week is this one if checked in, else last week. When the latest two weeks are each 2+ points below the average of the four weeks before (at least three answered; mobility first, then the total), the dashboard says so in plain words and offers "Ask for a check-up", which creates a booking proposal (AG-4) and is refused when there is no drop. A missed or stale week means no trend. No diagnosis. |
| HT-3 | The clinic's care-gap list flags a dropping home trend, only for owners who share their home log (PR-1). |
| HT-4 | The dashboard forecasts the next 12 months of care, priced from the clinic's price list (CG-6): overdue care this month, repeats at their interval. It totals pay-as-you-go and on the pet's plan (or, for non-members, the cheapest plan for the pet's life stage), and shows the difference honestly, even when the plan costs more. Memberships of retired plans are ignored. |
| HT-5 | For each parasite product, the dashboard shows the share of the last 365 days covered, days of cover left, and when it was last given. |
| HT-6 | The owner can record a home-given dose (chews, tablets; not injections). It counts towards cover, is marked owner-reported, and is never written to the practice system. |
| BR-1 | The app's mark is a silhouette of the owner's registered pet; with more than one pet, one is picked at random per visit. |

## Consent and privacy

| ID | Requirement |
| --- | --- |
| PR-1 | Two separate owner switches: share home log with the clinic; allow de-identified use. Both are stored with a timestamp. |
| PR-2 | De-identified use is off by default. |
| PR-3 | Clinic-sourced records stay in the practice-system adapter; app-owned data (chat, logs, consent, requests) lives in the app database. |
