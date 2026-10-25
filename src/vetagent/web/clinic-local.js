// Clinic view: Local area, from Australian open data (OD-1 to OD-6).
// Renders what /api/clinic/local returns; the rules live in domain/local_area.py.

const num = (n) => n.toLocaleString("en-AU");

async function loadLocal() {
  const v = await api("/api/clinic/local");
  const cards = [registrationsCard(v), ticksCard(v), afterHoursCard(v), weatherCard(v), labelsCard(v)];
  document.getElementById("local").innerHTML = cards.filter(Boolean).join("") ||
    '<p class="card empty muted">No open data yet. Run <code>uv run vetagent-open-data</code>.</p>';
  document.getElementById("local-sources").innerHTML = v.sources.length
    ? "Sources: " + v.sources.map((s) =>
      `<a href="${esc(s.url)}" rel="noopener">${esc(s.publisher)}</a> (${esc(s.licence)}, fetched ${esc(s.fetched)})`).join(" · ")
    : "";
}

function registrationsCard(v) {
  const r = v.registrations;
  if (!r) return "";
  const most = Math.max(...r.outreach.map((o) => o.not_desexed), 1);
  return `
    <div class="card">
      <h3 class="label">Pets registered around ${esc(v.area.suburb)}</h3>
      <div class="stats">
        <div><b>${num(r.dogs)}</b><span class="muted small">dogs, ${r.dogs_desexed_pct}% desexed</span></div>
        <div><b>${num(r.cats)}</b><span class="muted small">cats, ${r.cats_desexed_pct}% desexed</span></div>
        <div><b>${num(r.not_desexed)}</b><span class="muted small">not desexed</span></div>
      </div>
      <p class="small"><b>Where desexing outreach reaches most</b></p>
      <div class="outreach">${r.outreach.map((o) => `
        <span class="small">${esc(o.suburb)}</span>
        <span class="meter" title="${num(o.not_desexed)} of ${num(o.pets)} registered pets not desexed"><span style="width: ${Math.round(100 * o.not_desexed / most)}%"></span></span>
        <span class="small" style="text-align: right">${num(o.not_desexed)}</span>`).join("")}</div>
      <p class="muted small">Most registered dogs: ${r.top_breeds.dog.slice(0, 4).map(([b, n]) => `${esc(b)} (${num(n)})`).join(", ")}.</p>
      <p class="muted small">${r.suburbs.length} suburbs: ${r.suburbs.map(esc).join(", ")}. Council counts only; no owner details.</p>
    </div>`;
}

function ticksCard(v) {
  const t = v.ticks;
  if (!t) return "";
  const most = Math.max(...t.by_month.map((m) => m.records), 1);
  const bars = t.by_month.map((m) => `<span class="${m.now ? "now" : m.season ? "season" : ""}"
    style="height: ${Math.round(100 * m.records / most)}%" title="${esc(m.month)}: ${m.records} records"></span>`).join("");
  return `
    <div class="card">
      <h3 class="label">Paralysis tick season, ${esc(v.area.state)}</h3>
      <p>${t.in_season ? '<span class="pill clay">In season now</span>' : '<span class="pill">Out of season</span>'}
        <span class="small">Most records: ${esc(t.season)}. Peak: ${esc(t.peak)}.</span></p>
      <div class="bars" role="img" aria-label="Records by month: ${esc(t.by_month.map((m) => `${m.month} ${m.records}`).join(", "))}">${bars}</div>
      <div class="bar-labels label">${t.by_month.map((m) => `<span>${esc(m.month[0])}</span>`).join("")}</div>
      <p class="muted small">${t.local_records} record${t.local_records === 1 ? "" : "s"} within ${t.radius_km} km of the clinic. Records follow where people look as well as where ticks are, so read this as a season, not a risk score. Owners with dogs and cats see a tick notice while it's in season.</p>
    </div>`;
}

function afterHoursCard(v) {
  const a = v.after_hours;
  if (!a) return "";
  return `
    <div class="card">
      <h3 class="label">After hours</h3>
      <div><b class="serif" style="font-size: 20px">${esc(a.name)}</b>
        <div class="small">${esc(a.phone)} · ${a.km} km away · open 24 hours</div></div>
      <p class="muted small">The nearest 24-hour vet on OpenStreetMap, out of ${v.vets_nearby} vets mapped nearby. Owners see it on "Call now". Confirm the arrangement with them before going live.</p>
    </div>`;
}

function weatherCard(v) {
  if (!v.forecast.length) return "";
  const hot = v.hot_days.length;
  return `
    <div class="card">
      <h3 class="label">Feels-like maximum this week</h3>
      <div class="days">${v.forecast.map((f) => `
        <div class="${f.feels_like_max >= v.hot_threshold ? "hot" : ""}"><b>${Math.round(f.feels_like_max)}°</b><span class="muted small">${esc(f.day)}</span></div>`).join("")}</div>
      <p class="muted small">${hot
        ? `${hot} hot day${hot === 1 ? "" : "s"} (feels like ${v.hot_threshold}°C or more): dog owners see a heat notice.`
        : `No day reaches ${v.hot_threshold}°C feels-like, so owners see no heat notice.`}</p>
    </div>`;
}

function labelsCard(v) {
  if (!v.labels.length) return "";
  const counts = v.registered.map((r) => `${r.products} for ${esc(r.pest)} in ${esc(r.species)}s`).join(", ");
  return `
    <div class="card wide">
      <h3 class="label">Your parasite products on the APVMA register</h3>
      ${v.labels.map((l) => `
        <div class="label-row">
          <div><b>${esc(l.sold_as || l.name)}</b> ${l.current ? '<span class="pill">Registered</span>' : '<span class="pill clay">Registration lapsed</span>'}</div>
          <div class="small">${esc(l.name)} · APVMA ${esc(l.apvma_number)} · ${esc(l.registrant)} · to ${esc(l.expires)}</div>
          <div class="muted small">Label: ${esc(l.species.join(" and "))}${l.covers.length ? `; ${esc(l.covers.join(", "))}` : ""}${l.other_uses ? ` and ${l.other_uses} other use${l.other_uses === 1 ? "" : "s"}` : ""}.
            ${l.given_to.length ? `Dispensed to ${esc(l.given_to.join(" and "))}s.` : "Not dispensed in these records."}</div>
          ${l.off_label.length ? `<div class="bad-strong small">Dispensed to ${esc(l.off_label.join(" and "))}s, which the label doesn't list. Check with the vet.</div>` : ""}
        </div>`).join("")}
      <p class="muted small">Registered companion-animal products: ${counts}.</p>
    </div>`;
}
