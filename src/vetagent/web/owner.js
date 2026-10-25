// Owner care agent: renders the conversation the API returns. No agent logic lives here.

const CHIPS = [
  "What's due?",
  "Is my plan worth it?",
  "Book his screening",
  "He's limping again",
  "He's holding his leg up",
  "Log weight 31.2 kg",
];
let convo = null;
let busy = false;

// --- Cards: one renderer per card type the tools return ------------------------
const CARDS = {
  care_due: (c) => c.items.map((i) => `
    <div class="c ${i.status === "overdue" ? "warn" : ""}">
      <div class="label ${i.status === "overdue" ? "warn" : ""}">${i.status === "overdue" ? "OVERDUE" : "DUE SOON"}</div>
      <div style="font-weight: 700; margin-top: 4px">${esc(i.title)}</div>
      <div class="small" style="margin-top: 4px">${esc(i.due_label)} · ${money(i.value)}</div>
      <div class="muted small" style="margin-top: 4px">${esc(i.reason)}</div>
    </div>`).join(""),

  plan_value: (c) => `
    <div class="c">
      <div class="row"><span class="muted">Benefits used</span><b>${money(c.benefits_used)}</b></div>
      <div class="bar-track"><div class="bar-fill" style="width: ${Math.min(100, Math.round(100 * c.benefits_used / Math.max(c.paid, 1)))}%"></div></div>
      <div class="row"><span class="muted">Plan payments so far</span><b>${money(c.paid)}</b></div>
      <div class="muted small">${esc(c.plan)} plan · ${money(c.monthly_price)} a month · ${c.months_paid} months</div>
    </div>`,

  weight: (c) => {
    const kgs = c.points.map((p) => p.kg);
    const lo = Math.min(...kgs) - 0.5, hi = Math.max(...kgs) + 0.5;
    const bars = c.points.map((p, i) =>
      `<div class="${i === c.points.length - 1 ? "now" : ""}" style="height: ${8 + Math.round(52 * (p.kg - lo) / (hi - lo))}px"></div>`).join("");
    return `
    <div class="c">
      <b>Logged ${c.kg} kg</b>
      <div class="muted small">${c.shared ? "Shared with the clinic" : "Kept in your log only"}</div>
      <div class="bars" role="img" aria-label="Weight trend: ${c.points.map((p) => `${p.label} ${p.kg} kg`).join(", ")}">${bars}</div>
      <div class="bar-labels">${c.points.map((p) => `<span>${esc(p.label)}</span>`).join("")}</div>
    </div>`;
  },

  proposal: (c) => `
    <div class="c">
      <div class="label">${esc(c.title.toUpperCase())}</div>
      <p class="small" style="margin-top: 6px; line-height: 1.5">${esc(c.detail)}</p>
      ${c.status === "pending" ? `
        <div class="actions">
          <button class="btn" data-confirm="${esc(c.proposal_id)}">${esc(c.action)}</button>
          <button class="btn ghost" data-dismiss="${esc(c.proposal_id)}">Not now</button>
        </div>` : `<div class="muted small" style="margin-top: 8px">${c.status === "confirmed" ? "Sent" : "Not sent"}</div>`}
    </div>`,

  urgent: (c) => `
    <div class="c danger">
      <b style="color: var(--danger)">Call ${esc(c.clinic)} now</b>
      <div class="small" style="margin-top: 4px">This shouldn't wait for a chat reply. If the clinic is closed, go to your nearest emergency vet.</div>
    </div>`,

  done: (c) => `
    <div class="c done"><b style="color: var(--brand-dark)">${esc(c.title)}</b>
      <div class="small">${esc(c.detail)}</div></div>`,
};

function renderItem(item) {
  if (item.role === "user") return `<div class="msg-user">${esc(item.text)}</div>`;
  const texts = item.texts.map((t) => `<div class="bubble">${esc(t)}</div>`).join("");
  const cards = item.cards.map((c) => (CARDS[c.type] ? CARDS[c.type](c) : "")).join("");
  const trace = item.trace.length ? `<div class="trace">What I did: ${esc(item.trace.join(", "))}</div>` : "";
  return `<div class="msg-agent"><div class="dot" aria-hidden="true">${esc(convo.pet.name[0])}</div>
    <div class="stack">${texts}${cards}${trace}</div></div>`;
}

function render() {
  if (!convo) {
    document.getElementById("chat").innerHTML = '<div class="typing">Loading...</div>';
    return;
  }
  document.getElementById("clinic").textContent = convo.clinic;
  document.getElementById("title").textContent = `${convo.pet.name}'s care assistant`;
  document.getElementById("avatar").textContent = convo.pet.name[0];
  document.getElementById("mode").textContent = `Model: ${convo.model}`;
  document.getElementById("chat").innerHTML =
    convo.items.map(renderItem).join("") + (busy ? '<div class="typing">Thinking...</div>' : "");
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
  }
}

function setError(text) {
  document.getElementById("error").textContent = text;
}

function send(text) {
  run(() => api("/api/owner/messages", { method: "POST", body: { text } }));
}

function setConsent(change) {
  const body = { ...convo.consent, ...change };
  run(() => api("/api/owner/consent", { method: "PUT", body }));
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
  if (el.dataset.chip) send(el.dataset.chip);
  if (el.dataset.confirm) run(() => api(`/api/owner/proposals/${el.dataset.confirm}/confirm`, { method: "POST" }));
  if (el.dataset.dismiss) run(() => api(`/api/owner/proposals/${el.dataset.dismiss}/dismiss`, { method: "POST" }));
  if (el.id === "reset") run(() => api("/api/owner/reset", { method: "POST" }));
  if (el.id === "open-data") document.getElementById("sheet").hidden = false;
  if (el.id === "close-data") document.getElementById("sheet").hidden = true;
  if (el.id === "share-log") setConsent({ share_log: !convo.consent.share_log });
  if (el.id === "deidentified") setConsent({ deidentified_use: !convo.consent.deidentified_use });
});

run(() => api("/api/owner/conversation"));
