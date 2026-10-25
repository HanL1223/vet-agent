# Business walkthrough

How the vet care-plan platform makes money, whose problems it solves, and the data it builds.
Market figures are sourced at the end. **Prices and conversion rates are assumptions to test in
pilots, not facts.**

## 1. In one sentence

A clinic-branded **between-visit care platform** for independent Australian vet clinics on ezyVet.
The clinic gets a ranked list of care waiting to be booked and grows its wellness plans. The pet
owner gets a dashboard that tracks their pet at home, and their vet gets that data with consent.

## 2. Why this, and why it's different

Reminders, wellness plans and chat assistants already exist (PetDesk, Vet2Pet, Covetrus
CarePlans, Nest, ezyVet's own wellness module, Greencross Healthy Pets Plus). On their own they
aren't a business. The gap is **what happens between visits**:

- Owner logbook apps (11pets, DogLog, PawLog) collect home data, but it never reaches the vet.
- Clinic apps (PetDesk, Digitail) push reminders and show records, but collect little from home.
- Wearables (PetPace) send data to vets, but cost hundreds of dollars, suit dogs only, and most
  owners won't buy one.

We close that loop for the clinic the owner already trusts: a few taps a week at home, structured
and consented, shown to their own vet, who can act on it.

## 3. Who it's for

| | Who | What they want |
| --- | --- | --- |
| **Customer (pays)** | Independent clinics, 1-6 vets, on ezyVet, in Australia first | More preventive work booked, more plan members who stay, less phone time, loyal clients |
| **User (free)** | Their clients, especially owners of senior, chronic or multi-pet households | To know their pet is OK, not forget treatments, and know what care will cost |
| **Not now** | Corporate groups (Greencross, VetPartners), which build their own | Later, as a white-label |

## 4. Pain points we address

**Clinics**
1. **Preventive revenue leaks.** Overdue vaccines, lapsed parasite repeats, senior screens and
   recommended dentals go unbooked. In the demo, one small clinic has $1,802 of care waiting
   across 8 pets.
2. **Plans churn when owners can't see their value.** Members cancel when they don't feel they've
   used the plan.
3. **Staff time.** Reception spends hours on reminder calls and "is this urgent?" calls.
4. **No data between visits.** A senior dog's slow decline is noticed late, at the next annual
   visit or in an emergency.
5. **Price-transparency pressure.** The UK regulator (the CMA) now requires price lists and written
   estimates, and Australian owners are asking the same questions about cost.

**Owners**
1. **Cost anxiety.** 12% of Australian owners needed financial help for vet care, and US surveys
   show about 46% delayed a visit or refill because of cost.
2. **Forgetting.** One study found owners bought only about 6 of 12 months of flea and tick cover.
3. **Missing gradual change.** Mobility and comfort decline slowly. Validated owner scales (CBPI,
   LOAD) exist, but nobody gives them to owners in a habit-forming way.
4. **Scattered information.** What's due, what was given, what the plan covers.
5. **"Should I worry?"** Most owners google first.

## 5. How it works

```
ezyVet (clinic records) --read--> Platform --> Clinic dashboard: ranked care gaps, reminders,
                                     |          plan revenue, home-trend flags, owner requests
Owner at home --check-ins, doses,--> |
                weights, questions   +--> Owner dashboard: needs attention, weekly check-in,
                                          parasite cover, 12-month cost, weight, assistant
```

1. The platform reads clinic records from ezyVet (patients, standard of care, invoices, wellness
   plans). Clinic records are never copied into our database (PR-3).
2. The care-gap engine ranks what each pet is due for, by value.
3. The owner opens their pet's dashboard from a reminder link. In under a minute they can do this
   week's check-in, mark a chew as given, see the year's costs, or ask the assistant.
4. Anything that contacts the clinic (a booking, a note to the vet, a check-up request) is
   prepared, then **sent only when the owner taps send** (AG-4).
5. With the owner's consent, check-in trends flag the pet on the clinic's list ("Home check-ins:
   mobility down"), so the clinic can call before it becomes an emergency.

## 6. Where the revenue is

**Assumed prices, to test with pilot clinics:**

| Stream | Model | Assumption | When |
| --- | --- | --- | --- |
| **Clinic subscription** | Per clinic per month, by number of vets | A$199 (1-2 vets), A$349 (3-6 vets) | Day one |
| **Plan growth fee** | Per active plan member per month, for plans the platform manages or grows | A$1.50 per member | Day one; billed to the clinic, not through payments |
| **Setup and onboarding** | One-off: care-rule mapping, plan design, data import | A$500 | Day one |
| **Premium modules** | Chronic-care programs (arthritis, weight, diabetes) with structured check-ins for the vet | +A$99 per month | Year 2 |
| **Partnerships** | Insurance referrals, pet-food or parasite-product programs. Only opt-in, never at the cost of clinical neutrality | Revenue share | Year 2+ |
| **De-identified insights** | Research and industry benchmarks from consented, de-identified data (PR-2 is off by default) | Licensing | Year 3+, with ethics review |

We don't take payments, and we don't send SMS outside ezyVet's own systems. ezyVet's integration
terms route those through ezyVet, so our revenue doesn't depend on them.

**Why a clinic pays: the return on one clinic (illustrative)**

| Assumption | Value |
| --- | --- |
| Active patients | 2,500 |
| Patients with open care gaps at any time | 30% = 750 |
| Average value of a gap | A$220 (demo average: $1,802 / 8) |
| Care waiting | about A$165,000 |
| Extra gaps converted because of the platform | 8% a year = 60 bookings, about A$13,200 |
| New plan members a year | 40 x A$55 x 12 = about A$26,400 of recurring revenue |
| Platform cost | A$349 x 12 + 40 x A$1.50 x 12 = about A$4,900 |

**Payback in about 2 months.** The pilot must prove the conversion and plan numbers.

**Company scale (illustrative).** Australia has roughly 3,000+ vet practices; check the latest AVA
figures. At 300 clinics x (A$349 + 100 members x A$1.50) x 12, that's about A$1.8M ARR before
premium modules.

## 7. Data we generate

Every feature produces structured, consented data that nobody else collects.

| Data | From | Use |
| --- | --- | --- |
| **Weekly home wellbeing** (appetite, energy, mobility, comfort, toileting) | Check-in | Early-decline flags for vets; trend models by breed and age; evidence for chronic-care programs |
| **Real adherence** (days protected, gaps, owner-given doses) | Cover tile | Shows clinics where protection lapses; better reminder timing; product partners (aggregated) |
| **Weight trajectories** | Clinic records plus home logs | Weight programs; spotting unexplained loss, as in the demo dog's 0.6 kg drop |
| **Price sensitivity and plan conversion** | Forecast views, plan comparisons, bookings | Plan design, pricing advice for clinics |
| **Intent and worries** (what owners ask, what they book) | Assistant questions and proposals | FAQ content, triage gaps, service design |
| **Reminder to booking conversion** | Clinic dashboard | Proving ROI; benchmarking clinics |

**Rules that protect the data (and the business):**
- Clinic records stay in ezyVet. We store only what the app creates (PR-3).
- Sharing with the clinic is the owner's switch (PR-1). De-identified use is off by default (PR-2).
- No diagnosis and no dosing (AG-2). Check-ins track change and never conclude.
- Comply with the Australian Privacy Act and its Privacy Principles (APPs). Data processing
  agreements with each clinic.

The data compounds: more weeks of check-ins make the trend more sensitive, and more clinics make
benchmarks useful. That is the moat. Reminder software is a commodity; a clinic's longitudinal
home-health record is not.

## 8. Competition and positioning

| | Reminders | Wellness plans | Home tracking | Reaches the vet | Clinic-branded |
| --- | --- | --- | --- | --- | --- |
| PetDesk / Vet2Pet | Yes | Some | No | Records only | Yes |
| Covetrus CarePlans / Nest | No | Yes | No | No | Yes |
| Owner logbook apps | Owner-set | No | Yes | No (PDF at best) | No |
| PetPace collar | No | No | Sensors | Yes | No, and costly |
| **Us** | Yes (ranked by value) | Yes (value shown honestly) | Yes (check-ins, cover, weight) | Yes, with consent | Yes |

## 9. Going to market

1. **Free care-gap audit.** "Send us your ezyVet export and we'll show you the care waiting to be
   booked." The CSV pilot needs no API approval.
2. **Pilot with 3-5 independent clinics** for 90 days. Measure gap conversion, plan sign-ups,
   weekly check-in retention and phone calls avoided.
3. **ezyVet commercial partnership**, using the pilot results (see `docs/ezyvet.md`).
4. **Grow through referrals** in vet networks (AVA, practice-manager groups), with case studies.
5. **Later:** a second practice system (Covetrus), then NZ and the UK, where price transparency
   is now required.

## 10. Measuring success

| Metric | Target to test |
| --- | --- |
| Care-gap conversion uplift | +8 points |
| Weekly check-in retention at 12 weeks | 40% of activated owners |
| Plan sign-ups per clinic per month | 3+ |
| Home-trend flags that lead to a booking | 30% |
| Clinic logo churn | under 1% a month |

## 11. Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| ezyVet access is slow, costly or refused | CSV pilots first; the adapter design supports other systems; apply with pilot evidence |
| SMS and payments must go through ezyVet | Our revenue doesn't depend on either; use ezyVet's communication tools |
| Owners stop checking in | 30 seconds, weekly, attached to the reminder they already get; show them their trend |
| Vets worry about AI advice | No diagnosis or dosing, urgent symptoms go straight to "call the clinic", every action needs owner confirmation |
| Privacy breach or misuse | App-owned data only, consent switches, de-identification off by default, APP compliance |
| Corporates copy it | Focus on independents who can't build it; the longitudinal data is hard to copy |

## 12. Roadmap (the other 7 researched features)

Weight goal tracker; medication log with refill requests; symptom diary with photos; visit prep and
recap; care card for sitters; life-stage plan; multi-pet household view. Each adds a data stream
from section 7 and a reason to open the app between visits.

## Sources

- Animal Medicines Australia, *Pets in Australia 2025*: ownership, spending, financial help, insurance.
- Frontiers in Veterinary Science (2025): medication adherence review (6.1 of 12 months of cover).
- GoodRx pet prescription survey: cost-driven delays (US, sponsor-run).
- UK CMA veterinary market investigation, final decision March 2026.
- Greencross Vets Healthy Pets Plus terms; PetPace press materials; app store listings for owner
  logbooks.
- Canine Brief Pain Inventory validation studies (PMC5493851); University of Liverpool DogMA.
