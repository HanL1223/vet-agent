// Owner app, dashboard: renders what /api/owner/dashboard returns for the chosen pet.
// No rules live here: prices, routing and due dates all come from the API.

let pets = [];
let board = null;
let checkinOpen = false;
let triageOpen = false;
let triageResult = null; // { answers, result } after "Check"
let askingAbout = null; // "estimate" or "visit" while a question box is open

const PHONE = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1.9.4 1.8.7 2.7a2 2 0 0 1-.5 2.1L8 9.8a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.4c.9.3 1.8.6 2.7.7a2 2 0 0 1 1.7 2z"/></svg>';
const range = (r) => (r.low === r.high ? money(r.low) : `${money(r.low)}–${money(r.high)}`);
const tel = (phone) => `tel:${phone.replace(/\s/g, "")}`;

// --- Tiles: one renderer per section; each returns "" to hide its tile -------------------
const TILES = {
  triage: (b) => {
    if (!triageOpen) return "";
    if (!b.triage.available) {
      return `<p>For ${esc(b.pet.species)}s, please call the clinic: they often hide illness until it's serious.</p>
        <a class="btn" href="${tel(b.contact.phone)}">${PHONE} Call ${esc(b.clinic)}</a>`;
    }
    return triageResult ? triageOutcome(b) : triageForm(b);
  },

  nearby: (b) => b.nearby.map((n) => `
    <div class="notice ${esc(n.kind)}">
      <b>${esc(n.title)}</b>
      <p class="small">${esc(n.text)}</p>
      <span class="muted small">From ${esc(n.source)} open data</span>
    </div>`).join(""),

  costs: (b) => {
    const c = b.costs;
    const estimates = c.estimates.map((e) => estimateCard(e, c.payment_options)).join("");
    const y = c.year, plan = y.plan;
    const year = plan ? `
      <details class="year">
        <summary><span><b>Year ahead</b> <span class="muted">${plan.member ? `on your ${esc(plan.name)} plan` : `on the ${esc(plan.name)} plan`}</span></span>
          <span>${money(plan.total)} <span class="muted small">vs ${money(y.pay_as_you_go)} pay as you go</span></span></summary>
        <p class="note">${plan.saving >= 0
          ? `${plan.member ? "Your plan saves" : `The ${esc(plan.name)} plan would save`} about ${money(plan.saving)} this year.`
          : `${plan.member ? "Your plan costs" : `The ${esc(plan.name)} plan would cost`} ${money(-plan.saving)} more than paying as you go this year.`}</p>
        <ul class="months">${y.items.map((i) => `
          <li><span class="label">${esc(i.month)}</span><span>${esc(i.title)}${i.overdue ? ' <span class="pill clay">overdue</span>' : ""}</span>
            <span>${i.included ? '<span class="pill">included</span>' : money(i.price)}</span></li>`).join("")}</ul>
      </details>` : "";
    if (!estimates && !year) return "";
    return `${estimates || '<p class="empty-state">No estimates waiting.</p>'}${year}`;
  },

  visit: (b) => {
    const v = b.visit;
    if (!v) return "";
    return `
      <div class="row"><b>${esc(v.date)} with ${esc(v.vet)}</b></div>
      <p>${esc(v.summary)}</p>
      <ul class="checklist">${v.instructions.map((i) => `
        <li><label><input type="checkbox" data-tick="${esc(i.key)}" ${i.done ? "checked" : ""}>
          <span>${esc(i.text)}</span></label>${i.progress ? `<span class="label">${esc(i.progress)}</span>` : ""}</li>`).join("")}</ul>
      ${v.results.map((r) => `
        <div class="result ${r.status === "normal" ? "" : "attention"}">
          <div class="row"><b>${esc(r.name)}</b><span class="pill ${r.status === "normal" ? "" : "clay"}">${r.status === "normal" ? "Normal" : "Vet will call"}</span></div>
          <div class="small">${esc(v.vet)}: "${esc(r.comment)}"</div>
        </div>`).join("")}
      ${v.follow_up ? `
        <div class="row follow"><span><b>${esc(v.follow_up)}</b> <span class="muted">${esc(v.follow_up_when)}</span></span>
          <button class="btn small" data-follow-up="${esc(v.id)}">Book it</button></div>` : ""}
      ${askingAbout === "visit" ? questionBox("visit", `Question for ${v.vet}`) : `<button class="link" data-ask="visit">Ask ${esc(v.vet)} about this visit</button>`}`;
  },

  pathway: (b) => {
    const p = b.pathway;
    if (!p) return "";
    const nextVaccine = p.steps.find((s) => s.key.startsWith("vaccine") && !s.done);
    return `
      <p class="note">${esc(b.pet.name)} is ${p.weeks_old} weeks old.</p>
      <p class="tip"><span class="label">This week</span> ${esc(p.tip)}</p>
      <ul class="checklist">${p.steps.map((s) => `
        <li>${s.owner_ticks
          ? `<label><input type="checkbox" data-tick="${esc(s.key)}" ${s.done ? "checked" : ""}><span><b>${esc(s.title)}</b><br><span class="muted small">${esc(s.detail)}</span></span></label>`
          : `<span class="step ${s.done ? "done" : ""}"><b>${esc(s.title)}</b><br><span class="muted small">${esc(s.done ? s.detail : s.when)}</span></span>`}
          ${s.when && s.owner_ticks ? `<span class="label">${esc(s.when)}</span>` : ""}
          ${nextVaccine && s.key === nextVaccine.key ? `<button class="btn small" data-book="${esc(b.pet.name)}'s next vaccination">Book</button>` : ""}</li>`).join("")}</ul>
      ${p.plan_offer ? `
        <div class="offer"><b>${esc(p.plan_offer.name)} plan, ${money(p.plan_offer.monthly_price)} a month</b>
          <ul>${p.plan_offer.benefits.map((x) => `<li>${esc(x)}</li>`).join("")}</ul>
          <span class="muted small">Compare it with paying as you go under Costs.</span></div>` : ""}`;
  },

  due: (b) => b.due.length
    ? `<div class="rule-list">${b.due.map((d) => `
        <div class="row">
          <div><div style="font-weight: 700">${esc(d.title)}</div>
            <span class="status small ${d.status === "overdue" ? "overdue" : "soon"}">${esc(d.due_label)}</span></div>
          <button class="btn ghost small" data-book="${esc(d.title)}">Book</button>
        </div>`).join("")}</div>`
    : "",

  checkin: (b) => {
    const c = b.checkin;
    if (!c) return "";
    if (checkinOpen) return checkinForm(c);
    const bars = c.history.map((h, i) => {
      if (h.total === null) return '<span class="missed" title="No check-in"></span>';
      const last = i === c.history.length - 1;
      const height = 8 + Math.round(48 * h.total / c.max_total);
      return `<span class="${last ? "now" : h.low ? "low" : ""}" style="height: ${height}px"></span>`;
    }).join("");
    const done = c.history.filter((h) => h.total !== null);
    const latest = done[done.length - 1];
    return `
      ${c.trend.dropping
        ? `<p class="note clay">${esc(c.trend.message)}</p>`
        : `<p class="note">${latest ? "Steady. Thanks for keeping track." : "No check-ins yet."}</p>`}
      <div class="weeks" role="img" aria-label="Weekly totals out of ${c.max_total}: ${esc(c.history.map((h) => h.total ?? "missed").join(", "))}">${bars}</div>
      <div class="week-labels label"><span>8 weeks ago</span><span>${latest ? `Latest ${latest.total}/${c.max_total}` : ""} · this week</span></div>
      <div class="actions">
        <button class="btn ${c.done_this_week ? "ghost" : ""}" data-open-checkin>${c.done_this_week ? "Update this week" : "Check in"}</button>
        ${c.trend.dropping ? '<button class="btn ghost" data-checkup>Ask for a check-up</button>' : ""}
      </div>
      <p class="muted small">${c.shared ? "Shared with the clinic." : "Kept to you: sharing is off."} Not a diagnosis.</p>`;
  },
};

function estimateCard(e, paymentOptions) {
  const lines = e.lines.map((l, i) => `
    <li class="${l.optional ? "optional" : ""}">
      <div class="row">
        ${l.optional
          ? `<label><input type="checkbox" data-optional="${esc(l.name)}" id="opt-${i}"><span><b>${esc(l.name)}</b></span></label>`
          : `<b>${esc(l.name)}</b>`}
        <span class="price">${l.included ? '<span class="pill">included</span>' : range(l)}</span>
      </div>
      <div class="muted small">${l.optional ? "Optional. " : "Recommended. "}${esc(l.explanation)}</div>
    </li>`).join("");
  return `
    <div class="estimate" data-estimate="${esc(e.id)}">
      <div class="row"><b>${esc(e.title)}</b><span class="label">from ${esc(e.vet)}</span></div>
      <p class="muted small">Given ${esc(e.given)} · price held until ${esc(e.valid_until)}</p>
      <ul class="lines">${lines}</ul>
      <div class="totals">
        <div><span class="label">You pay, recommended</span><div class="big-number">${range(e.recommended)}</div></div>
        <div><span class="label">With every option</span><div class="big-number muted-number">${range(e.with_optional)}</div></div>
      </div>
      ${e.included ? `<p class="small">Your ${esc(e.plan)} plan includes ${money(e.included)} of this.</p>` : ""}
      ${paymentOptions.length ? `<p class="muted small">Ways to pay at the clinic: ${paymentOptions.map(esc).join(" · ")}.</p>` : ""}
      ${askingAbout === "estimate" ? questionBox("estimate", "Your question about this estimate") : `
      <div class="actions">
        <button class="btn" data-estimate-reply="accept">Go ahead</button>
        <button class="btn ghost" data-estimate-reply="cheaper">Ask for a cheaper option</button>
        <button class="btn ghost" data-ask="estimate">Ask a question</button>
      </div>`}
    </div>`;
}

function questionBox(kind, label) {
  return `
    <form class="question" data-question="${kind}">
      <label for="q-${kind}" class="small"><b>${esc(label)}</b></label>
      <textarea id="q-${kind}" rows="3" maxlength="1000" required></textarea>
      <div class="actions"><button class="btn small">Prepare it</button>
        <button type="button" class="btn ghost small" data-ask-cancel>Cancel</button></div>
    </form>`;
}

function triageForm(b) {
  const t = b.triage;
  const option = (s) => `<option value="${esc(s.key)}">${esc(s.label)}</option>`;
  const yesNo = (name, label) => `
    <fieldset class="yes-no"><legend>${esc(label)}</legend>
      <label><input type="radio" name="${name}" value="yes" required> Yes</label>
      <label><input type="radio" name="${name}" value="no"> No</label></fieldset>`;
  return `
    <form id="triage-form" style="display: grid; gap: 12px">
      <label class="small" for="symptom"><b>What are you seeing?</b></label>
      <select id="symptom" name="symptom" required>
        <option value="">Choose the closest one</option>
        <optgroup label="Emergency signs">${t.symptoms.filter((s) => s.red_flag).map(option).join("")}</optgroup>
        <optgroup label="Other">${t.symptoms.filter((s) => !s.red_flag).map(option).join("")}</optgroup>
      </select>
      <fieldset class="yes-no"><legend>For how long?</legend>
        ${t.durations.map((d) => `<label><input type="radio" name="hours" value="${d.hours}" required> ${esc(d.label)}</label>`).join("")}</fieldset>
      ${yesNo("eating", `Is ${b.pet.name} eating and drinking normally?`)}
      ${yesNo("bright", `Is ${b.pet.name} bright and alert?`)}
      <div class="actions"><button class="btn">Check</button>
        <button type="button" class="btn ghost" data-close-triage>Cancel</button></div>
      <p class="muted small">This helps you decide where to go. It doesn't diagnose. If you're worried, call: you know ${esc(b.pet.name)} best.</p>
    </form>`;
}

function triageOutcome(b) {
  const r = triageResult.result;
  const tone = { call_now: "danger", within_24h: "attention", watch: "calm" }[r.level];
  const action = {
    call_now: `<a class="btn" href="${tel(b.contact.phone)}">${PHONE} Call ${esc(b.clinic)}</a>
      <a class="btn ghost" href="${tel(b.contact.emergency_phone)}">${PHONE} ${esc(b.contact.emergency_name)}</a>`,
    within_24h: '<button class="btn" data-triage-request>Request the first appointment tomorrow</button>',
    watch: '<button class="btn ghost" data-triage-request>Send the vet a note for the morning</button>',
  }[r.level];
  return `
    <div class="outcome ${tone}" role="status">
      <div class="headline">${esc(r.headline)}</div>
      <p class="small">${esc(r.symptom)} · ${esc(r.duration.toLowerCase())}</p>
      <p>${esc(r.advice)}</p>
    </div>
    <div class="actions">${action}</div>
    ${r.level === "call_now" ? "" : `<p class="muted small">Closed? ${esc(b.contact.emergency_name)}: <a href="${tel(b.contact.emergency_phone)}">${esc(b.contact.emergency_phone)}</a></p>`}
    ${b.contact.emergency_source ? `<p class="muted small">After-hours vet from ${esc(b.contact.emergency_source)}.</p>` : ""}
    <button class="link" data-triage-again>Start again</button>`;
}

function checkinForm(c) {
  const rows = c.questions.map((q) => `
    <fieldset class="form-q">
      <legend>${esc(q.question)}</legend>
      <div class="scale">${[0, 1, 2, 3, 4].map((n) => `
        <input type="radio" id="${q.key}-${n}" name="${q.key}" value="${n}" ${c.latest && c.done_this_week && c.latest[q.key] === n ? "checked" : ""}>
        <label for="${q.key}-${n}">${n}</label>`).join("")}</div>
      <div class="scale-ends label"><span>${esc(q.low)}</span><span>${esc(q.high)}</span></div>
    </fieldset>`).join("");
  return `
    <form id="checkin-form" style="display: grid; gap: 14px">
      <p class="muted small">How has ${esc(board.pet.name)} been this week? 4 is normal for them.</p>
      ${rows}
      <div class="actions"><button class="btn">Save check-in</button>
        <button type="button" class="btn ghost" data-close-checkin>Cancel</button></div>
    </form>`;
}

// --- Rendering -----------------------------------------------------------------------
function renderPets() {
  document.getElementById("pets").innerHTML = pets.map((p) => `
    <button role="tab" data-pet="${esc(p.id)}" aria-selected="${p.id === petId}">
      <span class="mini">${petIcon(p.species)}</span>${esc(p.name)}</button>`).join("");
}

function renderBoard() {
  const p = board.pet;
  const age = board.pathway ? `${board.pathway.weeks_old} weeks` : `${p.age} yrs`;
  document.getElementById("pet-name").textContent = p.name;
  document.getElementById("pet-meta").textContent =
    [p.breed, age, p.plan ? `${p.plan} plan` : ""].filter(Boolean).join(" · ");
  document.getElementById("avatar").innerHTML = petIcon(p.species);
  document.getElementById("worry-pet").textContent = p.name;
  document.getElementById("open-triage").setAttribute("aria-expanded", String(triageOpen));
  document.getElementById("input").placeholder = `Ask about ${p.name}...`;
  document.title = `${p.name} · ${board.clinic}`;
  for (const name of Object.keys(TILES)) {
    const html = TILES[name](board);
    document.getElementById(name).innerHTML = html;
    document.getElementById(`t-${name}`).hidden = !html;
  }
}

async function boardAction(request) {
  document.getElementById("board-error").textContent = "";
  try {
    board = await request();
    renderBoard();
  } catch (err) {
    // Never leave another pet's tiles on screen after a failure.
    for (const tile of document.querySelectorAll(".tile")) tile.hidden = true;
    document.getElementById("board-error").textContent = err.message;
  }
}

function loadBoard() {
  return boardAction(() => api(forPet("/api/owner/dashboard")));
}

function choosePet(id) {
  petId = id;
  checkinOpen = triageOpen = false;
  triageResult = askingAbout = null;
  history.replaceState(null, "", `?pet=${encodeURIComponent(id)}`);
  renderPets();
  loadBoard();
  loadConversation();
}

// A dashboard action that lands as a proposal in Ask, where the owner confirms it (AG-4).
function propose(path, body) {
  showView("ask");
  run(() => api(forPet(path), { method: "POST", body }));
}

// --- Events ----------------------------------------------------------------------------
const boardEl = document.getElementById("board");

boardEl.addEventListener("submit", (event) => {
  event.preventDefault();
  const form = event.target;
  if (form.id === "checkin-form") {
    const scores = {};
    for (const q of board.checkin.questions) {
      const picked = form.querySelector(`input[name="${q.key}"]:checked`);
      if (!picked) {
        document.getElementById("board-error").textContent = `Answer "${q.question}" first.`;
        return;
      }
      scores[q.key] = Number(picked.value);
    }
    checkinOpen = false;
    boardAction(() => api(forPet("/api/owner/checkins"), { method: "POST", body: { scores } }));
  }
  if (form.id === "triage-form") {
    const data = new FormData(form);
    const answers = {
      symptom: data.get("symptom"),
      hours: Number(data.get("hours")),
      eating: data.get("eating") === "yes",
      bright: data.get("bright") === "yes",
    };
    api(forPet("/api/owner/triage"), { method: "POST", body: answers })
      .then((result) => { triageResult = { answers, result }; renderBoard(); })
      .catch((err) => { document.getElementById("board-error").textContent = err.message; });
  }
  if (form.dataset.question) {
    const question = form.querySelector("textarea").value.trim();
    const kind = form.dataset.question;
    askingAbout = null;
    renderBoard();
    if (kind === "estimate") {
      const id = form.closest("[data-estimate]").dataset.estimate;
      propose(`/api/owner/estimates/${id}/reply`, { choice: "question", question });
    } else {
      propose(`/api/owner/visits/${board.visit.id}/question`, { question });
    }
  }
});

boardEl.addEventListener("change", (event) => {
  const box = event.target;
  if (box.dataset.tick) {
    boardAction(() => api(forPet("/api/owner/ticks"), { method: "POST", body: { item: box.dataset.tick, done: box.checked } }));
  }
});

boardEl.addEventListener("click", (event) => {
  const el = event.target.closest("button");
  if (!el) return;
  const d = el.dataset;
  if (d.pet) choosePet(d.pet);
  if (el.id === "open-triage") { triageOpen = !triageOpen; triageResult = null; renderBoard(); }
  if (d.closeTriage !== undefined) { triageOpen = false; renderBoard(); }
  if (d.triageAgain !== undefined) { triageResult = null; renderBoard(); }
  if (d.triageRequest !== undefined) propose("/api/owner/triage/request", triageResult.answers);
  if (d.estimateReply) {
    const card = el.closest("[data-estimate]");
    const chosen = [...card.querySelectorAll("[data-optional]:checked")].map((c) => c.dataset.optional);
    propose(`/api/owner/estimates/${card.dataset.estimate}/reply`, { choice: d.estimateReply, optional_lines: chosen });
  }
  if (d.ask) { askingAbout = d.ask; renderBoard(); }
  if (d.askCancel !== undefined) { askingAbout = null; renderBoard(); }
  if (d.followUp) propose(`/api/owner/visits/${d.followUp}/follow-up`);
  if (d.openCheckin !== undefined) { checkinOpen = true; renderBoard(); }
  if (d.closeCheckin !== undefined) { checkinOpen = false; renderBoard(); }
  if (d.checkup !== undefined) propose("/api/owner/checkup");
  if (d.book) { showView("ask"); send(`Book ${d.book}`); }
});

document.addEventListener("conversation-changed", () => { if (petId) loadBoard(); });

(async function start() {
  try {
    pets = await api("/api/owner/pets");
  } catch (err) {
    document.getElementById("board-error").textContent = err.message;
    return;
  }
  const known = pets.some((p) => p.id === petId);
  choosePet(known ? petId : pets[0].id);
  paintMark("[data-mark]", pets.map((p) => p.species));
})();
