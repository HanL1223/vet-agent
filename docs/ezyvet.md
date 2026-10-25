# ezyVet: data mapping and API access

The demo doesn't call ezyVet. `SeedPracticeSystem` reads `data/seed_clinic.json`, which is in the
app's own shape: string IDs, ISO dates, and one flat list of care events. This page records where
each seed field would come from in ezyVet. It also lists the gaps a real adapter must handle, and
explains how to get API access.

Sources are ezyVet's public developer and help pages, checked October 2026. Each mapping row is
rated **Confirmed** (documented by ezyVet), **Likely** (follows ezyVet's documented `/v1/{resource}`
pattern, but no field list was checked) or **App** (not an ezyVet field; the app or the clinic sets
it). Before building the adapter, check every row against the partner Postman collection, which
you get after approval.

## API basics (Confirmed)

- Base URL `https://api.ezyvet.com`, REST, JSON. Resources sit under `/v1/...`, and newer ones
  under `/v2/...`.
- Auth: OAuth 2.0 client credentials. Send `partner_id`, `client_id`, `client_secret`,
  `grant_type=client_credentials` and a space-separated `scope` to `POST /v1/oauth/access_token`.
  Scopes are named per resource, for example `read-animal` and `write-diagnosticresult`.
- Rate limits: usually 60 calls/min per endpoint, and 180 calls/min per database per partner. Going
  over returns HTTP 429. Each clinic is its own database, so cache reads and page through lists.
- IDs are integers. Most records also carry a `uid`. Timestamps are Unix epoch seconds.

## Field mapping

| Seed field | ezyVet source | Status | Notes for the adapter |
| --- | --- | --- | --- |
| `clinic.name` | Site / separation name | Likely | One database can hold several sites. |
| `clinic.lead_vet` | `v1/user` | Likely | ezyVet doesn't have a "lead vet". Pick one per clinic in config, or use the animal's last consulting vet. |
| `price_list.*` | `v1/product` (price) | Likely | Each key (`vaccination`, `heartworm`, ...) is **App** config that points at one product ID. |
| `owners[].id`, `name` | `v1/contact` (`id`, `first_name`, `last_name`) | Likely | The seed holds one display name, for example "Priya S."; build it from first and last name. |
| `pets[].id`, `name` | `v1/animal` | Confirmed | |
| `pets[].owner_id` | `v1/animal.contact_id` | Confirmed | |
| `pets[].birth_date` | `v1/animal.date_of_birth` | Confirmed | May be an estimate (`is_estimated_birth`-style flag). |
| `pets[].species`, `breed` | `v1/animal` `species_id`, `breed_id` -> `v1/species`, `v1/breed` | Likely | IDs, not text. Map species to `dog` or `cat` and skip other species, since care rules only cover dogs and cats. |
| *(missing)* deceased / inactive | `v1/animal.date_of_death`, active flag | Confirmed | **Gap.** The seed has no deceased pets, so nothing filters them. A real adapter must leave them out, or the clinic will remind owners about a pet that has died. |
| `events[type=vaccination]` | `v2/standardofcare` (`last_fulfilled_at`, `due_at`) or vaccination records | Confirmed (SoC) | ezyVet works out due dates from its Standard of Care setup, so its `due_at` can replace our 365-day rule (CG-1). |
| `events[type=parasite]`, `repeat_days` | `v2/standardofcare` (care group such as "Flea and Tick", `due_at`) | Confirmed | `repeat_days` is the seed's stand-in for the clinic's SoC interval. Prefer `due_at`. |
| `events[type=screening]` | SoC care group, or invoice lines for a screening product | Likely | Depends on how each clinic sets up SoC. |
| `events[type=consult]`, `detail` | `v1/consult` + clinical records / history | Likely | Free text. Treat it as clinical data (the agent may quote it, never interpret it). |
| `events[type=finding]`, `finding=dental_recommended` | Clinical records (free text) | **App** | **Gap.** ezyVet has no structured "dental recommended" flag. Use a SoC care group, a clinic-specific presenting problem / diagnosis code, or a dental product quoted but not invoiced. Agree this with each pilot clinic. |
| `events[type=dental]` | Invoice lines for dental products | Likely | |
| `events[type=weight]`, `kg` | `v1/healthstatus.weight` | Confirmed | `healthstatus` also supports POST, which would allow writing shared home weights back. That needs a write scope and partner terms that allow it. |
| `plans[]` | `v2/wellnessplan` | Confirmed (endpoint) | Field names not checked. `covers` (which gap types a plan includes) is **App** config. |
| `plans[].benefits` | `v2/wellnessplanbenefit`, benefit items | Confirmed (endpoint) | |
| `memberships[]` | `v2/wellnessplanmembership` | Confirmed (endpoint) | |
| `benefit_usage[]` | Invoice lines covered by a plan | Likely | Not checked. It may need invoice lines joined to membership benefits. |

In short: every record the demo uses has an ezyVet source. Three things don't come straight from
ezyVet and need a decision per clinic: the dental finding, the `price_key` / `covers` config, and
the lead vet. The seed is also missing the deceased flag, which real data will need.

## Other constraints to know before applying

- **SMS and payments.** ezyVet's private-integration terms say SMS and payment features must run
  through ezyVet's own framework. "Reminder delivery (SMS/email)" and "Stripe direct debit" in our
  roadmap may clash with that. Ask the partnerships team what applies to commercial partners
  before building either.
- **Writes.** Our app writes nothing to ezyVet today: booking requests and vet notes go to the
  clinic dashboard. Starting read-only keeps the application simpler. Writes such as appointments,
  health status or communications can be added later.
- **Cost.** Third-party reports mention IDEXX partnership approval, setup fees, per-hospital
  monthly fees for write access, and a certification path that ends in a multi-site beta. This
  isn't confirmed on ezyVet's own pages, so ask on the first call.

## How to apply for API access

ezyVet has two routes. **We need the commercial partner route:** we are a vendor serving several
clinics, and private integration credentials may not be handed to a third party.

| Route | Who it's for | Fits us? |
| --- | --- | --- |
| Private integration (`developers.ezyvet.com/apply/private.html`) | One ezyVet customer reading **its own** data with its own tools. Credentials can't be shared with another company. Replies take 5-10 business days. | No, unless one pilot clinic builds it for itself. |
| Commercial integration partner (`ezyvet.com/become-a-partner`) | Vendors whose product connects to many ezyVet clinics. | **Yes.** |

### Steps

1. **Fill in the API Partner Application Form** on <https://www.ezyvet.com/become-a-partner>.
   Choose general API integration (not the Diagnostic, PACS or supplier specs). Cover:
   - What the product does: a care-gap dashboard and an owner care agent sold to ezyVet clinics.
   - The data needed (start read-only): animal, contact, standard of care, health status, consult
     and clinical records, products, invoice lines, wellness plans and memberships.
   - The scopes, following the `read-<resource>` pattern: `read-animal read-contact
     read-standardofcare read-healthstatus read-consult read-product read-invoiceline
     read-wellnessplan read-wellnessplanmembership`. Confirm the exact names with ezyVet.
   - Expected call volume per clinic, and that reads are cached under the 60/min and 180/min
     limits.
   - Privacy: clinic records stay in ezyVet and the app stores only what it owns (PR-3); owner
     consent is recorded (PR-1, PR-2); no diagnosis or dosing (AG-3).
   - One or more pilot clinics already on ezyVet that will sponsor the beta. Having these helps
     a lot.
2. **Partnership review.** ezyVet and IDEXX review the application and send terms. Ask for a
   sandbox or trial database to build against, and for the partner Postman collection.
3. **Receive credentials.** You get a `partner_id` (your integration's UUID) plus a `client_id` and
   `client_secret`. Treat them as secrets: keep them in `.env`, never in the repo.
4. **Each clinic turns you on.** A clinic admin opens **Admin > Integrations**, searches for
   **API Partner**, finds us, ticks the scopes (labelled *Permissions* on some setups) and
   downloads the credentials file. Credentials are per clinic database, so store one set per
   clinic.
5. **Get a token and test a read.** In PowerShell:

   ```powershell
   $body = @{
     partner_id    = $env:EZYVET_PARTNER_ID
     client_id     = $env:EZYVET_CLIENT_ID
     client_secret = $env:EZYVET_CLIENT_SECRET
     grant_type    = "client_credentials"
     scope         = "read-animal read-contact"
   }
   $token = (Invoke-RestMethod -Method Post -Uri "https://api.ezyvet.com/v1/oauth/access_token" -Body $body).access_token
   Invoke-RestMethod -Uri "https://api.ezyvet.com/v1/animal?limit=5" -Headers @{ Authorization = "Bearer $token" }
   ```

   Tokens last for hours (third parties report 12), so cache the token and refresh it on 401.
6. **Build `EzyVetPracticeSystem`** in `integrations/`, implementing `PracticeSystem`, and select it
   in `api/wiring.py` (see `CLAUDE.md`). Nothing else changes.

## References

- ezyVet API docs: <https://developers.ezyvet.com/>
- Standard of care and the API: <https://developers.ezyvet.com/guides/soc.html>
- Become an integration partner: <https://www.ezyvet.com/become-a-partner>
- Private integration application: <https://developers.ezyvet.com/apply/private.html>
- Private integration terms: <https://www.ezyvet.com/private-api-terms-and-conditions>
