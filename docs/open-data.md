# Australian open data

The demo clinic is fictional, but it is placed at a real address area, Kirwan in Townsville,
Queensland, so that five free public sources can describe its area with real data. Each source
was tried, and each one feeds something in the product. Requirement IDs are OD-1 to OD-6 in
`docs/requirements.md`.

| # | Source | What we take | Feeds | Licence |
| --- | --- | --- | --- | --- |
| 1 | [Townsville City Council animal registrations](https://data.gov.au/data/dataset/tcc-animal-registrations) (data.gov.au) | Dogs and cats per suburb, desexed or not; most registered breeds | Clinic **Local area**: pets around the clinic and where desexing outreach reaches most (OD-1) | CC BY 4.0 |
| 2 | [APVMA PubCRIS register](https://data.gov.au/data/dataset/0de37904-43e0-4814-b21b-5b64fafefe6f) (data.gov.au) | The labels of the parasite products the clinic sells: species, pests, registration expiry; counts of dog and cat products per pest | Clinic **Local area**: label check against the species each product was dispensed to (OD-2) | CC BY 3.0 AU |
| 3 | [Atlas of Living Australia](https://www.ala.org.au/) occurrence API | Paralysis tick (*Ixodes holocyclus*) records by month in Queensland, and the count within 100 km of the clinic | Owner **Near you**: tick-season notice for dogs and cats; clinic season chart (OD-3) | Per record, mostly CC BY |
| 4 | [OpenStreetMap](https://www.openstreetmap.org/) via the Overpass API | Vets within 30 km: name, location, phone, opening hours, emergency tag | Owner **Something not right?**: the nearest real 24-hour vet on "Call now"; clinic After hours card (OD-4) | ODbL 1.0, "© OpenStreetMap contributors" |
| 5 | [Open-Meteo](https://open-meteo.com/) forecast API | Feels-like maximum for the next 7 days | Owner **Near you**: hot-day notice for dog owners; clinic forecast card (OD-5) | CC BY 4.0; free API for non-commercial use |

## How it works

```
uv run vetagent-open-data            # fetch all five sources, write data/open/*.json
uv run vetagent-open-data ticks vets # or only some
```

- `integrations/open_data_refresh.py` fetches each source and turns it into a small **aggregate
  snapshot** (`src/vetagent/data/open/<source>.json`). Each snapshot records its publisher,
  licence, URL and fetch date (OD-6). The `summarise_*` functions are pure and tested.
- `integrations/open_data.py` (`OpenData`) reads the snapshots. A missing snapshot means no data,
  never an error.
- `domain/local_area.py` and `domain/labels.py` hold the rules: area summary, tick season,
  nearest after-hours vet, hot days, label check.
- `services/local_area.py` builds the clinic's Local area view and the owner notices;
  `HomeService` uses it for the "Near you" tile and the emergency number.
- The app never calls these APIs at runtime, so the demo and the tests are offline and
  repeatable. A busy server (Overpass at capacity, Open-Meteo rate limits) is retried with
  backoff; a source that still fails keeps its previous snapshot.
- Where the clinic is, its catchment suburbs, the search radii and which APVMA registration each
  of its products is (`"302": "68870"`) live in `clinic_config.json` under `open_data`.

## What each source showed when tried (25 October 2026)

1. **Registrations** (October 2026 release, two sheets: 22,561 dogs and 4,295 cats). No ages and
   no owner details. Around Kirwan's 14 suburbs: 10,877 dogs (86% desexed) and 2,184 cats (89%);
   1,790 not desexed, the most in Kirwan (391) and Kelso (292).
2. **APVMA**: 3,406 veterinary products. Vet products are found by `typedesc` ("VM" or "VP"),
   dogs by host codes starting "AD" and cats by "AF". Fleas are the "WFL..." pest codes plus
   "VGP1". 116 products are registered for paralysis tick in dogs and 25 in cats. The demo
   links the clinic's chew to Bravecto 1000 mg (68870), the heartworm injection to ProHeart SR-12
   (51805) and the wormer to Drontal Allwormer for large dogs (35824). All are dog-only labels and
   were dispensed only to dogs, so nothing is flagged.
3. **ALA**: 648 Queensland records, peaking from August to December (October has 137). Only 10
   are within 100 km of Townsville: the paralysis tick is mostly an east-coast species, and
   records follow where people look. So the app shows a season, never a risk score.
4. **OpenStreetMap**: 9 vets within 30 km, 8 with names. JCU Vet is tagged `emergency=yes` and
   `24/7`, 4.4 km from the clinic, so it is the after-hours vet. Owners see where the number
   came from.
5. **Open-Meteo**: rate-limited at first (the shared IP had used its daily quota), then
   available. The week's feels-like maximum was 33–34 °C, below the 35 °C notice threshold, so
   no heat notice shows in the demo.

## Rules for using this data

- **Aggregates only.** No row-level records and no personal information are stored.
- **Attribution is shown** where the data is used: the Local area tab lists every source and
  licence, owner notices name their source, and the emergency number says it is from
  OpenStreetMap.
- **No clinical advice.** Label data checks a registration; it never suggests a medicine or a
  dose (AG-2). Tick and heat notices are general care advice. A tick on a pet is still a red flag
  in "Something not right?" (TR-2).
- **Confirm before going live.** A real clinic confirms its after-hours partner and the heat
  threshold with its vets, as it does with the triage list.
- **Commercial use.** Open-Meteo's free API is for non-commercial use; a paying product needs
  its subscription or another forecast source. Overpass is a shared public service: refresh
  rarely. The data.gov.au and ALA licences allow commercial use with attribution.

## Other places that publish council registrations

Other councils publish registration data on data.gov.au and state portals, with different
columns. Pointing `fetch_registrations` at another council needs that council's dataset name and
a column mapping. Check that a council's release has no owner details before using it.
