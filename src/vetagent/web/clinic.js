// Clinic dashboard: KPIs, care-gap radar, plans and owner requests.

const FILTERS = [
  ["", "All"], ["vaccination", "Vaccines"], ["parasite", "Parasite"],
  ["senior", "Senior"], ["dental", "Dental"],
];
const state = { filter: "", rows: [] };

async function loadSummary() {
  const s = await api("/api/clinic/summary");
  document.getElementById("clinic-name").textContent = s.clinic;
  const day = new Date(s.today + "T00:00:00");
  document.getElementById("today").textContent =
    day.toLocaleDateString("en-AU", { weekday: "long", day: "numeric", month: "long" }) +
    " · care gaps refreshed from clinic records";
  const kpis = [
    ["Plan members", s.plan_members, ""],
    ["Recurring plan revenue", money(s.monthly_plan_revenue) + " /month", ""],
    ["Pets with open care gaps", s.pets_with_gaps, `of ${s.active_pets} active pets`],
    ["Care value at risk", money(s.value_at_risk), `${s.reminders_sent} reminder${s.reminders_sent === 1 ? "" : "s"} sent`],
  ];
  document.getElementById("kpis").innerHTML = kpis.map(([label, value, note]) => `
    <div class="card kpi"><span class="muted small">${esc(label)}</span><b>${esc(value)}</b>
    <span class="muted small">${esc(note)}</span></div>`).join("");
}

function renderFilters() {
  document.getElementById("filters").innerHTML = FILTERS.map(([key, label]) =>
    `<button class="chip" data-filter="${key}" aria-pressed="${key === state.filter}">${label}</button>`
  ).join("");
}

async function loadGaps() {
  const query = state.filter ? `?type=${state.filter}` : "";
  state.rows = await api("/api/clinic/care-gaps" + query);
  const html = state.rows.map((r) => `
    <div class="row">
      <div class="who">
        <b>${esc(r.pet)}</b> <span class="muted small">${esc(r.breed)}</span>
        ${r.member ? '<span class="pill">Plan member</span>' : ""}
        <div class="muted small">Owner: ${esc(r.owner)}</div>
      </div>
      <div class="what"><div style="font-weight: 600">${esc(r.title)}</div>
        <div class="muted small">${esc(r.reason)}</div></div>
      <div class="when"><div class="${r.overdue ? "overdue" : "soon"}">${esc(r.due_label)}</div>
        <div class="muted small">${money(r.value)} value</div></div>
      <div class="act">${r.reminded
        ? '<span class="sent">Reminder sent</span>'
        : `<button class="btn" data-remind="${esc(r.key)}">Send reminder</button>`}</div>
    </div>`).join("");
  document.getElementById("gap-rows").innerHTML =
    html || '<p class="empty muted">No open care gaps for this filter.</p>';
}

async function loadPlans() {
  const plans = await api("/api/clinic/plans");
  document.getElementById("plans").innerHTML = plans.map((p) => `
    <div class="card plan">
      <div style="display: flex; justify-content: space-between"><b>${esc(p.name)}</b>
        <span class="muted small">${p.members} members</span></div>
      <div style="font-size: 28px; font-weight: 700">${money(p.monthly_price)}
        <span class="muted small">/month per pet</span></div>
      <ul>${p.benefits.map((b) => `<li>${esc(b)}</li>`).join("")}</ul>
    </div>`).join("");
}

async function loadRequests() {
  const reqs = await api("/api/clinic/requests");
  const label = { booking_request: "Booking request", vet_note: "Note for the vet" };
  document.getElementById("requests").innerHTML = reqs.map((r) => `
    <div class="row">
      <div class="who"><b>${esc(r.pet)}</b><div class="muted small">${esc(label[r.kind] || r.kind)}</div></div>
      <div class="what">${esc(r.detail)}</div>
      <div class="when muted small">${new Date(r.created_at).toLocaleString("en-AU")}</div>
    </div>`).join("") ||
    '<p class="empty muted">No requests yet. Confirm a booking in the owner agent to see one here.</p>';
}

async function remind(keys) {
  await api("/api/clinic/reminders", { method: "POST", body: { keys } });
  await Promise.all([loadGaps(), loadSummary()]);
}

function showTab(name) {
  for (const tab of document.querySelectorAll("[data-tab]")) {
    tab.setAttribute("aria-selected", String(tab.dataset.tab === name));
  }
  for (const id of ["gaps", "plans", "requests"]) {
    document.getElementById("tab-" + id).hidden = id !== name;
  }
  if (name === "plans") loadPlans();
  if (name === "requests") loadRequests();
}

document.addEventListener("click", async (event) => {
  const el = event.target.closest("button");
  if (!el) return;
  if (el.dataset.tab) showTab(el.dataset.tab);
  if (el.dataset.filter !== undefined) {
    state.filter = el.dataset.filter;
    renderFilters();
    await loadGaps();
  }
  if (el.dataset.remind) {
    el.disabled = true;
    await remind([el.dataset.remind]);
  }
  if (el.id === "send-all") {
    const keys = state.rows.filter((r) => !r.reminded).map((r) => r.key);
    if (keys.length) await remind(keys);
  }
});

renderFilters();
loadSummary();
loadGaps();
