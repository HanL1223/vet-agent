# Business walkthrough

How the vet care-plan platform makes money, whose problems it solves, and the data it builds.
The owner side is built on the ranked pain-point research in `docs/owner-pain-points.md`.
**Prices and conversion rates are assumptions to test in pilots, not facts.**

## 1. In one sentence

A clinic-branded app that turns the **estimates, discharge talks and worried phone calls** an
independent Australian vet clinic already has into **accepted treatment, booked follow-ups and
bookings kept at the clinic**. It reads the clinic's ezyVet records, and the owner confirms
before anything is sent.

## 2. Why this, and why it's different

Reminders, wellness plans and chat assistants already exist: PetDesk, Vet2Pet, Covetrus
CarePlans, Nest, ezyVet's own modules, Greencross Healthy Pets Plus. A generic "pet dashboard"
is hard to sell, because owners don't struggle for lack of one. They struggle at **moments**,
and each moment costs the clinic money:

| Owner moment | What it costs the clinic today | Who else is there |
| --- | --- | --- |
| "What will this cost? Can I afford it?" | Declined or delayed treatment, bill-shock complaints | Nobody owner-facing in AU; UK regulator now forces price transparency |
| "What did the vet say? Is the result OK?" | Callback time, follow-ups never booked | Messaging tools (PetDesk, Vello), not structured recaps |
| "Is this urgent?" | Reception triage calls; bookings lost to telehealth and emergency centres | VetChat and Vetster route owners *away* from the clinic |
| "New puppy or kitten, now what?" | Lost vaccine courses, desexing, plan sign-ups at peak motivation | Generic puppy apps, not linked to the clinic |

We serve those four moments, branded as the clinic, from the clinic's own records. Every answer
routes the owner back to the clinic.

## 3. Who it's for

| | Who | What they want |
| --- | --- | --- |
| **Customer (pays)** | Independent clinics with 1-6 vets, on ezyVet, Australia first | Treatment accepted, follow-ups booked, fewer phone interruptions, plan members who stay |
| **User (free)** | The clinic's clients: new-pet owners, owners of senior pets, multi-pet households | Clear prices, clear instructions, knowing when to worry, a plan for a new pet |
| **Not now** | Corporate groups (Greencross, VetPartners), which build their own | Later, as a white-label |

## 4. Pain points we address

The four we built, ranked by a product-owner review weighted towards "can a clinic be sold
this" (full evidence in `docs/owner-pain-points.md`):

1. **Cost surprise and distrust of price** (score 37/40).
   - 12% of Australian owners needed financial help for vet care, and about 1 in 6 put off
     check-ups or cut medication (AMA 2025).
   - Cost came up in only 23% of 917 filmed consults.
   - *Our answer:* an **estimate inbox**. Each line in plain words, recommended or optional, what
     the plan includes, what the owner pays, and ways to pay. The owner can go ahead, ask for a
     cheaper option, or ask a question.
2. **Forgetting what the vet said** (30). Owners and vets agreed on discharge instructions only
   69% of the time. *Our answer:* a **visit recap** the clinic releases. Instructions with day
   counts the owner ticks off, results in the vet's own words, and the follow-up one tap away.
3. **"Should I go to the vet?"** (30).
   - Owners under-rated urgency in 28% of cases.
   - Only 20% of Australian owners know vet telehealth exists.
   - *Our answer:* **"Something not right?"** routes to call now, see a vet within 24 hours, or
     keep an eye on it. Red flags such as a paralysis tick always mean call now, with the clinic's
     and the after-hours partner's numbers. Amber pre-fills tomorrow's booking. It never names a
     condition.
4. **New puppy or kitten overwhelm** (28). 1 in 5 Australian owners is a first-timer. *Our
   answer:* **first 90 days**. The vaccine course from clinic records, home steps, a weekly tip,
   and the young-pet plan.

Also kept: the **weekly check-in for senior pets**, which flags a decline to the clinic with
consent. It is the data moat and the start of a premium chronic-care module.

## 5. How it works

```
ezyVet (estimates, records, standard of care) --read--> Platform --> Clinic dashboard:
                                                         |           ranked care gaps, reminders,
Clinic releases recaps, approves the triage list ------> |           plans, owner requests,
                                                         |           home-trend flags
Owner: estimate replies, ticks, "Something not right?",  |
check-ins, questions -----------------------------------> +--> Owner app, per pet: Costs, Last
                                                              visit, Something not right?,
                                                              First 90 days, Coming up,
                                                              Check-in, Ask (assistant)
```

1. **Reading clinic data.** The platform reads ezyVet and never copies clinic records into its own
   store (PR-3).
2. **What the owner sees.** The owner opens a pet from a reminder or after a visit: the estimate
   they were given, what the vet asked them to do, or a "should I come in?" check.
3. **Confirming before sending.** Any action that reaches the clinic (accept an estimate, book a
   follow-up, request tomorrow's appointment, ask the vet) is prepared as a proposal. It is sent
   only when the owner taps send (AG-4).
4. **What the clinic receives.** Triaged, ready-to-act requests: "go ahead with screening and hip
   X-rays", "vomiting for 2 days, first slot tomorrow", "recheck by 5 Nov". There's no phone tag.

## 6. Where the revenue is

| Stream | Model | Assumption | When |
| --- | --- | --- | --- |
| **Clinic subscription** | Per clinic per month, by number of vets | A$249 (1-2 vets), A$449 (3-6 vets) | Day one |
| **Plan growth fee** | Per active plan member per month, on plans the app grows (new-pet pathway, year-ahead comparison) | A$1.50 per member | Day one |
| **Setup** | One-off: estimate wording, triage list review by the clinic's vets, data import | A$750 | Day one |
| **Premium: senior and chronic care** | Weekly check-ins with validated scales, trend reports for the vet | +A$99 per month | Year 2 |
| **Premium: medication log** | Refill proposals that keep pharmacy at the clinic (pain point #2) | +A$99 per month | Year 2 |
| **Partnerships** | Opt-in insurance or pet-health savings, never at the cost of clinical neutrality | Revenue share | Year 2+ |
| **De-identified insights** | Benchmarks from consented, de-identified data (PR-2 is off by default) | Licensing | Year 3+, with ethics review |

We take no payments and send no SMS outside ezyVet's systems. The estimate tile only lists the
ways to pay the clinic offers.

**Why a clinic pays: an illustrative return.**

| Assumption | Value |
| --- | --- |
| Estimates written per month | 120, averaging A$650 |
| Extra acceptance from plain-language estimates | +5 points = 6 more accepted per month = about A$3,900 a month |
| Follow-ups booked instead of forgotten | 10 a month at A$92 = about A$920 a month |
| Triage calls taken by the app instead of reception | 60 a month at 6 minutes = 6 staff hours a month |
| New-pet plan sign-ups | 3 a month at A$49 = about A$1,760 a year of recurring revenue added each month |
| Platform cost | A$449 + 100 members x A$1.50 = about A$600 a month |

**Payback is in the first month on estimates alone.** The pilot must prove the acceptance number.

**Company scale (illustrative):** 300 clinics x (A$449 + A$150) x 12 = about A$2.2M ARR before
premium modules.

## 7. Data we generate

| Data | From | Use |
| --- | --- | --- |
| **Estimate decisions** (viewed, accepted, which options, "cheaper?" requests, questions) | Costs | Price sensitivity by line and region; better estimate design; proves ROI |
| **After-hours worry** (what owners saw, how long, the outcome, the time) | Something not right? | Clinic staffing and after-hours partner decisions; triage-list tuning by the clinic's vets |
| **Instruction follow-through** (ticks, follow-ups booked, questions per visit type) | Last visit | Discharge-communication quality; which visits need a callback |
| **First-year engagement** (course completion, home steps, plan conversion) | First 90 days | Lifetime value models; new-client onboarding |
| **Home wellbeing trends** (senior check-ins) | Check-in | Early-decline flags; the chronic-care premium module |
| **Intent** (what owners ask the assistant) | Ask | FAQ content, service design |

**Public data we add on top** (free, Australian, attributed; `docs/open-data.md`):

| Data | From | Use |
| --- | --- | --- |
| Pets registered per suburb, desexed or not | Council registrations (data.gov.au) | Catchment size for sales; where desexing outreach reaches most; new-site decisions |
| Labels of registered parasite products | APVMA PubCRIS | Label check against the species each product was dispensed to; the base for the medication log |
| Paralysis tick records by month | Atlas of Living Australia | Seasonal tick notices to owners, timed reminders for prevention |
| Vets nearby, opening hours, emergency tag | OpenStreetMap | The after-hours number on "Call now"; local competition for sales |
| 7-day forecast | Open-Meteo (a paid plan in production) | Hot-day notices for dog owners |

They make the product useful on day one, before a clinic's own data has built up, and they are
the same for every clinic in an area, so they don't depend on ezyVet access.

**Rules that protect the data:**
- Clinic records stay in ezyVet.
- Sharing with the clinic is the owner's switch (PR-1); de-identified use is off by default
  (PR-2).
- No diagnosis or dosing (AG-2); triage only routes (TR-1).
- Australian Privacy Principles compliance, with a data processing agreement per clinic.

## 8. Competition and positioning

| | Price clarity | Visit recap | Urgency routing | New-pet pathway | Routes back to the clinic |
| --- | --- | --- | --- | --- | --- |
| PetDesk / Vello | No | Messages | No | Reminders | Yes |
| VetChat / Vetster | No | No | Yes (paid call) | No | **No** |
| GapOnly / VetPay | At the counter | No | No | No | n/a |
| Generic puppy apps | No | No | No | Yes | No |
| **Us** | **Yes, before the visit** | **Yes, structured** | **Yes, free to the owner** | **Yes, from clinic records** | **Yes** |

## 9. Going to market

1. **Free estimate-acceptance audit:** "Send us last quarter's estimates and invoices from ezyVet.
   We'll show your acceptance rate and what's being left on the table." This needs no API
   approval.
2. **Pilot with 3-5 independent clinics for 90 days.** Headline metric: **estimate acceptance
   rate** (dollars accepted ÷ dollars estimated) against the clinic's own previous 90 days.
   Secondary metrics: follow-ups booked, triage calls avoided, new-pet plan sign-ups.
3. **ezyVet commercial partnership** with pilot results (`docs/ezyvet.md`). Estimates need an
   endpoint we haven't confirmed; the CSV export is the pilot fallback.
4. **Referrals** through AVA and practice-manager groups.
5. **Later:** Covetrus, then NZ and the UK, where price lists and written estimates are now
   mandatory.

## 10. Measuring success

| Metric | Target to test |
| --- | --- |
| Estimate acceptance uplift | +5 points |
| Recap follow-ups booked | 60% of recaps with a follow-up |
| "Within 24 hours" outcomes booked at the clinic | 70% |
| New-pet plan sign-ups | 3+ per clinic per month |
| Clinics churning | under 1% a month |

## 11. Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| No estimate endpoint, or slow ezyVet approval | CSV pilots; next, estimates created directly in our clinic dashboard |
| Triage liability and vet nervousness | Routing only, never a condition; each clinic's vets approve the list; red flags always mean call now; urgent chat messages never reach the model (AG-3) |
| "Is this upselling?" distrust | Clinic's own words, recommended and optional marked clearly, "ask for a cheaper option" built in, plan comparisons honest even when the plan costs more |
| Clinics don't write recaps | The Visit recaps tab is one short form, released in one click; it saves the callback it replaces |
| Privacy | App-owned data only, consent switches, de-identification off by default |
| Corporates copy it | Focus on independents; the decision and worry data is hard to copy |

## 12. Roadmap

1. **Done:** the clinic-side recap editor and estimate sending (Estimates and Visit recaps tabs).
2. **Next:** the **medication log**
   (pain point #2, refills kept at the clinic).
3. **Year 2:** the senior and chronic premium module (validated mobility scales).
4. **Later:** an emergency-readiness view (#7), end-of-life quality-of-life journal (#9), weight
   programmes (#10).

## Sources

See `docs/owner-pain-points.md` for every figure's source. Key sources: Animal Medicines
Australia, *Pets in Australia 2025*; Groves et al. 2022 (cost discussions in consults); JVIM 2024
(discharge comprehension); RVC urgency study; AVA workforce survey 2023/24; UK CMA final decision
(March 2026).
