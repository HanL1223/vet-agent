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
| CL-7 | **Estimates tab.** Open ezyVet estimates for current patients, newest first, with where each is up to: not sent, sent to owner, or owner replied (with the reply). The clinic reviews the plain-language explanation of every line (pre-filled from `clinic_config.json`), then sends. Sending again updates the wording. One explanation per line, each under 400 characters. |
| CL-8 | **Visit recaps tab.** The clinic writes a recap (patient, vet, visit date, plain-language summary, instructions with optional day counts, results with a status and the vet's comment, follow-up and date) and releases it to the owner's Last visit (VR-1). It is refused if the visit is in the future or over 60 days ago, the summary is empty, an instruction runs outside 1-90 days, a result lacks a name or comment, the vet or patient isn't the clinic's, or a follow-up date has no follow-up. Recently released recaps are listed. |

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

## Owner app (OW, CO, VR, TR, NP, HT, BR)

Built around the moments owners get stuck (`docs/owner-pain-points.md`). Every action that
contacts the clinic is a proposal the owner confirms (AG-4).

| ID | Requirement |
| --- | --- |
| OW-1 | The owner sees each pet they registered and switches between them. Every owner call names the pet; another owner's pet is not found. Each pet has its own conversation. |
| CO-1 | **Costs.** Open estimates the clinic has sent (CL-7) show line by line: what each line is for (in the clinic's words), recommended or optional, and its price or price range. Expired estimates are not shown. |
| CO-2 | Lines the pet's plan includes show as included and cost the owner nothing. Totals show what the owner pays for the recommended lines and with every option, plus the ways to pay the clinic offers. We take no payments. |
| CO-3 | "Go ahead" (with any optional lines ticked), "Ask for a cheaper option" and "Ask a question" each create a proposal. The app explains lines but never says whether one is clinically needed. |
| CO-4 | The year ahead (HT-4) sits with costs. Plans are compared only for pets they're meant for (life stage and species). |
| VR-1 | **Last visit.** The latest recap the clinic released (within 60 days) shows the vet's plain-language summary, each instruction with its progress ("Day 6 of 14"), and results with the vet's own comment. |
| VR-2 | The owner ticks instructions off. Ticks are app-owned data. |
| VR-3 | "Book it" turns the vet's follow-up into a booking proposal; "Ask about this visit" turns a question into a note for the vet. |
| TR-1 | **Should I come in?** The owner picks what they see, for how long, and whether the pet is eating normally and bright. The answer is one of: call now, see a vet within 24 hours, or keep an eye on it. It never names a condition. |
| TR-2 | Red-flag signs (for example breathing trouble, collapse, a paralysis tick, a leg held up) always mean call now, with the clinic's and the after-hours partner's numbers. A pet that is neither eating nor bright also means call now. Keep the list in step with AG-3. |
| TR-3 | "Within 24 hours" offers to request tomorrow's first appointment; "keep an eye on it" offers a note for the vet. "Call now" never becomes a proposal. The outcome is worked out on the server, never trusted from the page. |
| TR-4 | The rules cover dogs and cats only; owners of other species are asked to call the clinic. |
| TR-5 | Each answer is logged as app-owned data, for clinic insight into after-hours worry. |
| NP-1 | **First 90 days.** Pets under about six months get a pathway: the vaccine course from clinic records (a dose every 4 weeks until one at 16 weeks or older), home steps the owner ticks (microchip and registration, parasite prevention, puppy class or kitten kindy, a desexing talk), and the plan for young pets with what it includes. Remaining course doses count in the year ahead. |
| NP-2 | One practical tip for the pet's age each week. |
| HT-1 | **Weekly check-in (senior pets only).** Five questions (appetite, energy, mobility, comfort, toileting), each 0 to 4. One per pet per ISO week; checking in again that week replaces it. |
| HT-2 | Trends use calendar weeks: the latest week is this one if checked in, otherwise last week. When the latest two weeks are each 2+ points below the average of the four weeks before (at least three answered; mobility first, then the total), the dashboard says so in plain words and offers "Ask for a check-up", which creates a booking proposal. It is refused when there is no drop. A missed or stale week means no trend. No diagnosis. |
| HT-3 | The clinic's care-gap list flags a dropping home trend, only for owners who share their home log (PR-1). |
| HT-4 | The next 12 months of care, priced from the clinic's price list (CG-6): overdue care this month, repeats at their interval. Totals pay-as-you-go and on the pet's plan (or, for non-members, the cheapest plan meant for them), and shows the difference honestly, even when the plan costs more. Memberships of retired plans are ignored. |
| BR-1 | The app's mark is a silhouette of the owner's registered pet; with more than one pet, one is picked at random per visit. |

Retired: HT-5 and HT-6 (parasite cover and home-given doses) and the weight tile. The ranking
folds them into a future medication log (pain point #2). Weight logging stays an assistant
action (AG-5).

## Consent and privacy

| ID | Requirement |
| --- | --- |
| PR-1 | Two separate owner switches: share home log with the clinic; allow de-identified use. Both are stored with a timestamp. |
| PR-2 | De-identified use is off by default. |
| PR-3 | Clinic-sourced records stay in the practice-system adapter; app-owned data (chat, logs, consent, requests) lives in the app database. |
