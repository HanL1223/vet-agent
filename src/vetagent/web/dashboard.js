// Owner app, dashboard tiles: renders what /api/owner/dashboard returns. No rules live here.

let board = null;
let checkinOpen = false;

const TILES = {
  due: (b) => b.due.length
    ? `<div class="rule-list">${b.due.map((d) => `
        <div class="row">
          <div><div style="font-weight: 700">${esc(d.title)}</div>
            <span class="status small ${d.status === "overdue" ? "overdue" : "soon"}">${esc(d.due_label)}</span></div>
          <button class="btn small" data-book="${esc(d.title)}">Book</button>
        </div>`).join("")}</div>`
    : `<p class="empty-state">Nothing due for ${esc(b.pet.name)} right now.</p>`,

  checkin: (b) => {
    const c = b.checkin;
    if (checkinOpen) return checkinForm(c);
    const bars = c.history.map((h, i) => {
      const last = i === c.history.length - 1;
      const height = 8 + Math.round(48 * h.total / c.max_total);
      return `<span class="${last ? "now" : h.mobility <= 2 ? "low" : ""}" style="height: ${height}px"></span>`;
    }).join("");
    const latest = c.history[c.history.length - 1];
    return `
      ${c.trend.dropping
        ? `<p class="note clay">${esc(c.trend.message)}</p>`
        : `<p class="note">${latest ? "Steady. Thanks for keeping track." : "No check-ins yet."}</p>`}
      <div class="weeks" role="img" aria-label="Weekly totals out of ${c.max_total}: ${esc(c.history.map((h) => h.total).join(", "))}">${bars}</div>
      <div class="week-labels label"><span>8 weeks ago</span><span>${latest ? `Latest ${latest.total}/${c.max_total}` : ""}</span></div>
      <div class="actions">
        <button class="btn ${c.done_this_week ? "ghost" : ""}" data-open-checkin>${c.done_this_week ? "Update this week" : "Check in"}</button>
        ${c.trend.dropping ? '<button class="btn ghost" data-checkup>Ask for a check-up</button>' : ""}
      </div>
      <p class="muted small">${c.shared ? "Shared with the clinic." : "Kept to you: sharing is off."} Not a diagnosis.</p>`;
  },

  cover: (b) => b.cover.length
    ? `<div class="rule-list">${b.cover.map((c) => `
        <div style="display: grid; gap: 6px">
          <div class="row"><b>${esc(c.product)}</b><span class="small">${c.percent}% covered</span></div>
          <div class="strip" role="img" aria-label="${c.percent}% of the last 12 months covered">${c.spans.map(([s, e]) =>
            `<span style="left: ${(100 * s / c.window_days).toFixed(2)}%; width: ${(100 * (e - s) / c.window_days).toFixed(2)}%"></span>`).join("")}</div>
          <div class="row small">
            <span class="${c.days_left ? "muted" : "note clay"}">${c.days_left ? `${c.days_left} days left` : "Not covered now"} · last ${esc(c.last_given)}${c.owner_reported ? " (you logged)" : ""}</span>
            ${c.can_log ? `<button class="btn ghost small" data-dose="${esc(c.product)}">Given today</button>` : ""}
          </div>
        </div>`).join("")}</div>`
    : '<p class="empty-state">No flea, tick, worm or heartworm treatments on record.</p>',

  cost: (b) => {
    const f = b.forecast, plan = f.plan;
    const compare = plan ? `
      <div class="cost-compare">
        <div class="${plan.member ? "mine" : ""}"><div class="label">${esc(plan.name)} plan</div>
          <div class="big-number">${money(plan.total)}</div>
          <div class="muted small">${money(plan.fees)} fees${plan.extras ? ` + ${money(plan.extras)} extra` : ""}</div></div>
        <div class="${plan.member ? "" : "mine"}"><div class="label">Pay as you go</div>
          <div class="big-number">${money(f.pay_as_you_go)}</div>
          <div class="muted small">at the clinic's prices</div></div>
      </div>
      <p class="note">${plan.saving >= 0
        ? `${plan.member ? "Your plan saves" : `The ${esc(plan.name)} plan would save`} about ${money(plan.saving)} this year.`
        : `${plan.member ? "Your plan costs" : `The ${esc(plan.name)} plan would cost`} ${money(-plan.saving)} more than paying as you go this year.`}</p>`
      : `<div class="big-number">${money(f.pay_as_you_go)}</div>`;
    const items = f.items.map((i) => `
      <li><span class="label">${esc(i.month)}</span>
        <span>${esc(i.title)}${i.overdue ? ' <span class="pill clay">overdue</span>' : ""}</span>
        <span>${i.included ? '<span class="pill">included</span>' : money(i.price)}</span></li>`).join("");
    return `${compare}${items ? `<ul class="months">${items}</ul>` : ""}`;
  },

  weight: (b) => {
    const w = b.weight;
    if (!w) return '<p class="empty-state">No weights yet. Log one in Ask.</p>';
    const lo = Math.min(...w.points) - 0.3, hi = Math.max(...w.points) + 0.3;
    const step = w.points.length > 1 ? 280 / (w.points.length - 1) : 0;
    const pts = w.points.map((kg, i) => `${10 + i * step},${4 + 32 * (hi - kg) / (hi - lo)}`).join(" ");
    const change = w.change_kg === 0 ? "no change" : `${w.change_kg > 0 ? "+" : ""}${w.change_kg} kg`;
    return `
      <div class="row"><span class="big-number">${w.kg} kg</span><span class="muted small">${change} since ${esc(w.since)}</span></div>
      <svg class="spark" viewBox="0 0 300 40" role="img" aria-label="Weight trend: ${esc(w.points.join(", "))} kg">
        <polyline points="${pts}" fill="none" stroke-width="2" stroke-linejoin="round" style="stroke: var(--ink)"/></svg>`;
  },
};

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

function renderBoard() {
  const p = board.pet;
  document.getElementById("pet-name").textContent = p.name;
  document.getElementById("pet-meta").textContent =
    `${p.breed} · ${p.age} yrs${board.forecast.plan?.member ? ` · ${board.forecast.plan.name} plan` : ""}`;
  document.getElementById("avatar").innerHTML = petIcon(p.species);
  document.getElementById("input").placeholder = `Ask about ${p.name}...`;
  document.title = `${p.name} · ${board.clinic}`;
  for (const name of Object.keys(TILES)) {
    document.getElementById(name).innerHTML = TILES[name](board);
  }
}

async function boardAction(request) {
  document.getElementById("board-error").textContent = "";
  try {
    board = await request();
    renderBoard();
  } catch (err) {
    document.getElementById("board-error").textContent = err.message;
  }
}

function loadBoard() {
  return boardAction(() => api("/api/owner/dashboard"));
}

document.getElementById("board").addEventListener("submit", (event) => {
  if (event.target.id !== "checkin-form") return;
  event.preventDefault();
  const scores = {};
  for (const q of board.checkin.questions) {
    const picked = event.target.querySelector(`input[name="${q.key}"]:checked`);
    if (!picked) {
      document.getElementById("board-error").textContent = `Answer "${q.question}" first.`;
      return;
    }
    scores[q.key] = Number(picked.value);
  }
  checkinOpen = false;
  boardAction(() => api("/api/owner/checkins", { method: "POST", body: { scores } }));
});

document.getElementById("board").addEventListener("click", (event) => {
  const el = event.target.closest("button");
  if (!el) return;
  if (el.dataset.openCheckin !== undefined) { checkinOpen = true; renderBoard(); }
  if (el.dataset.closeCheckin !== undefined) { checkinOpen = false; renderBoard(); }
  if (el.dataset.dose) {
    boardAction(() => api("/api/owner/doses", { method: "POST", body: { product: el.dataset.dose } }));
  }
  if (el.dataset.book) { showView("ask"); send(`Book ${el.dataset.book.toLowerCase()}`); }
  if (el.dataset.checkup !== undefined) {
    showView("ask");
    run(() => api("/api/owner/checkup", { method: "POST" }));
  }
});

document.addEventListener("conversation-changed", loadBoard);
paintMark("[data-mark]");
loadBoard();
