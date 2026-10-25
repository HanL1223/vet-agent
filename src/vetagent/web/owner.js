// Owner app, Ask panel: renders the conversation the API returns. No agent logic lives here.
// dashboard.js renders the tiles and picks the pet; both share `petId`, `forPet`, `run`,
// `send` and `showView`.

const CHIPS = [
  "What's due?",
  "Is the plan worth it?",
  "Book a check-up",
  "Limping again",
  "Holding a leg up",
  "Log weight 31.2 kg",
];
let petId = new URLSearchParams(location.search).get("pet");
let convo = null;
let busy = false;

// Every owner call names the pet it is about (OW-1).
const forPet = (path) => `${path}${path.includes("?") ? "&" : "?"}pet=${encodeURIComponent(petId)}`;

// --- Cards: one renderer per card type the tools return ------------------------
const CARDS = {
  care_due: (c) => c.items.map((i) => {
    const overdue = i.status === "overdue";
    return `
    <div class="c ${overdue ? "overdue" : ""}">
      <span class="status small ${overdue ? "overdue" : "soon"}">${esc(i.due_label)}</span>
      <div class="title">${esc(i.title)}</div>
      <div class="muted small" style="margin-top: 2px">${esc(i.reason)}</div>
      <div class="small" style="margin-top: 8px">Usually ${money(i.value)}</div>
    </div>`;
  }).join(""),

  plan_value: (c) => `
    <div class="c">
      <div class="label">${esc(c.plan)} plan</div>
      <div class="row" style="margin-top: 6px"><span class="muted">Benefits used</span><b>${money(c.benefits_used)}</b></div>
      <div class="bar-track"><div class="bar-fill" style="width: ${Math.min(100, Math.round(100 * c.benefits_used / Math.max(c.paid, 1)))}%"></div></div>
      <div class="row"><span class="muted">Paid so far</span><b>${money(c.paid)}</b></div>
      <div class="muted small">${money(c.monthly_price)} a month · ${c.months_paid} months</div>
    </div>`,

  weight: (c) => {
    const kgs = c.points.map((p) => p.kg);
    const lo = Math.min(...kgs) - 0.5, hi = Math.max(...kgs) + 0.5;
    const step = c.points.length > 1 ? 260 / (c.points.length - 1) : 0;
    const pts = c.points.map((p, i) => [20 + i * step, 8 + 44 * (hi - p.kg) / (hi - lo)]);
    const dots = pts.map(([x, y], i) => {
      const last = i === pts.length - 1;
      return `<circle cx="${x}" cy="${y}" r="${last ? 5 : 3.5}" style="fill: ${last ? "var(--sage)" : "#fff"}; stroke: var(--sage); stroke-width: 2"/>
        <text x="${x}" y="74" text-anchor="middle" style="font-size: 11px; fill: var(--muted)">${esc(c.points[i].label)}</text>`;
    }).join("");
    return `
    <div class="c">
      <b>${c.kg} kg logged</b>
      <div class="muted small">${c.shared ? "Shared with the clinic" : "Kept in your log only"}</div>
      <svg class="trend" viewBox="0 0 300 80" role="img" aria-label="Weight trend: ${esc(c.points.map((p) => `${p.label} ${p.kg} kg`).join(", "))}">
        <polyline points="${pts.map((p) => p.join(",")).join(" ")}" fill="none" stroke-width="2" stroke-linejoin="round" stroke-linecap="round" style="stroke: var(--sage)"/>
        ${dots}
      </svg>
    </div>`;
  },

  proposal: (c) => `
    <div class="c">
      <div class="label">${esc(c.title)}</div>
      <p class="small" style="margin-top: 6px; line-height: 1.55">${esc(c.detail)}</p>
      ${c.status === "pending" ? `
        <div class="actions">
          <button class="btn" data-confirm="${esc(c.proposal_id)}">${esc(c.action)}</button>
          <button class="btn ghost" data-dismiss="${esc(c.proposal_id)}">Not now</button>
        </div>` : `<div class="trace" style="margin-top: 10px">${c.status === "confirmed" ? "Sent to the clinic" : "Not sent"}</div>`}
    </div>`,

  urgent: (c) => `
    <div class="c danger" role="alert">
      <div class="urgent-head">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1.9.4 1.8.7 2.7a2 2 0 0 1-.5 2.1L8 9.8a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.4c.9.3 1.8.6 2.7.7a2 2 0 0 1 1.7 2z"/></svg>
        Call ${esc(c.clinic)} now
      </div>
      <div class="small" style="margin-top: 6px">This shouldn't wait for a chat reply. If the clinic is closed, go to your nearest emergency vet.</div>
    </div>`,

  done: (c) => `
    <div class="c done"><b style="color: var(--sage-dark)">${esc(c.title)}</b>
      <div class="small">${esc(c.detail)}</div></div>`,
};

function renderItem(item) {
  if (item.role === "user") return `<div class="msg-user">${esc(item.text)}</div>`;
  const texts = item.texts.map((t) => `<p>${esc(t)}</p>`).join("");
  const cards = item.cards.map((c) => (CARDS[c.type] ? CARDS[c.type](c) : "")).join("");
  const did = item.trace.join(" · ");
  const trace = did
    ? `<div class="trace"><span><span class="sr-only">What I did: </span>${esc(did[0].toUpperCase() + did.slice(1))}</span></div>`
    : "";
  return `<div class="msg-agent">${texts}${cards}${trace}</div>`;
}

function render() {
  if (!convo) {
    document.getElementById("chat").innerHTML = '<div class="typing">Loading...</div>';
    return;
  }
  const pet = convo.pet;
  document.getElementById("clinic").textContent = convo.clinic;
  document.getElementById("mode").textContent = convo.model;
  document.getElementById("chat").innerHTML = convo.items.map(renderItem).join("") +
    (busy ? `<div class="typing">Checking ${esc(pet.name)}'s records...</div>` : "");
  document.getElementById("share-log").setAttribute("aria-checked", String(convo.consent.share_log));
  document.getElementById("deidentified").setAttribute("aria-checked", String(convo.consent.deidentified_use));
  const scroller = document.getElementById("chat-scroll");
  scroller.scrollTop = scroller.scrollHeight;
}

async function run(request) {
  if (busy) return;
  busy = true;
  setError("");
  render();
  try {
    convo = await request();
  } catch (err) {
    setError(err.message);
  } finally {
    busy = false;
    render();
    // Chat actions (a consent change, a sent request) can change the tiles.
    document.dispatchEvent(new Event("conversation-changed"));
  }
}

function setError(text) {
  document.getElementById("error").textContent = text;
}

function send(text) {
  run(() => api(forPet("/api/owner/messages"), { method: "POST", body: { text } }));
}

// Phones show one view at a time; on wide screens both are always visible.
function showView(name) {
  document.querySelector(".layout").dataset.show = name;
  for (const tab of document.querySelectorAll("[data-view]")) {
    tab.setAttribute("aria-selected", String(tab.dataset.view === name));
  }
  const scroller = document.getElementById("chat-scroll");
  scroller.scrollTop = scroller.scrollHeight; // a hidden panel can't scroll, so catch up now
}

function setConsent(change) {
  const body = { ...convo.consent, ...change };
  run(() => api(forPet("/api/owner/consent"), { method: "PUT", body }));
}

// --- Events ------------------------------------------------------------------
document.getElementById("chips").innerHTML =
  CHIPS.map((c) => `<button class="chip" data-chip="${esc(c)}">${esc(c)}</button>`).join("");

document.getElementById("form").addEventListener("submit", (event) => {
  event.preventDefault();
  const input = document.getElementById("input");
  const text = input.value.trim();
  if (!text) return setError("Type a message first.");
  input.value = "";
  send(text);
});
document.getElementById("input").addEventListener("input", () => setError(""));

document.addEventListener("click", (event) => {
  const el = event.target.closest("button");
  if (!el) return;
  if (el.dataset.view) showView(el.dataset.view);
  if (el.dataset.chip) send(el.dataset.chip);
  if (el.dataset.confirm) run(() => api(`/api/owner/proposals/${el.dataset.confirm}/confirm`, { method: "POST" }));
  if (el.dataset.dismiss) run(() => api(`/api/owner/proposals/${el.dataset.dismiss}/dismiss`, { method: "POST" }));
  if (el.id === "reset") run(() => api(forPet("/api/owner/reset"), { method: "POST" }));
  if (el.id === "open-data") document.getElementById("sheet").hidden = false;
  if (el.id === "close-data") document.getElementById("sheet").hidden = true;
  if (el.id === "share-log") setConsent({ share_log: !convo.consent.share_log });
  if (el.id === "deidentified") setConsent({ deidentified_use: !convo.consent.deidentified_use });
});

function loadConversation() {
  return run(() => api(forPet("/api/owner/conversation")));
}
