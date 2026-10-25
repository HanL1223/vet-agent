// Clinic view: estimates sent to owners (CL-7) and visit recaps (CL-8).
// Renders what the API returns; validation and wording rules live on the server.

const care = { estimates: [], openEstimate: null, options: null, instructions: [], results: [] };
const shortDate = (iso) =>
  new Date(iso + "T00:00:00").toLocaleDateString("en-AU", { day: "numeric", month: "short" });
const span = (low, high) => (low === high ? money(low) : `${money(low)}–${money(high)}`);
const STATUS = {
  not_sent: '<span class="pill clay">Not sent</span>',
  sent: '<span class="pill">Sent to owner</span>',
  replied: '<span class="pill">Owner replied</span>',
};

// --- Estimates ----------------------------------------------------------------------------
async function loadEstimates() {
  care.estimates = await api("/api/clinic/estimates");
  renderEstimates();
}

function renderEstimates() {
  const rows = care.estimates.map((e) => `
    <div class="row est">
      <div><b>${esc(e.pet)}</b><div class="muted small">${esc(e.owner)}</div></div>
      <div><div style="font-weight: 700">${esc(e.title)}</div>
        <div class="muted small">${esc(e.vet)} · given ${esc(e.given)} · held until ${esc(e.valid_until)}</div></div>
      <div class="when"><b>${span(e.low, e.high)}</b><div class="muted small">before any plan</div></div>
      <div class="act" style="gap: 8px; align-items: center">${STATUS[e.status]}
        <button class="btn ${e.status === "not_sent" ? "" : "ghost"} small" data-review="${esc(e.id)}">${e.status === "not_sent" ? "Review and send" : "Edit wording"}</button></div>
    </div>
    ${e.reply ? `<p class="reply small"><b>Owner:</b> ${esc(e.reply)}</p>` : ""}
    ${care.openEstimate === e.id ? estimateEditor(e) : ""}`).join("");
  document.getElementById("estimates").innerHTML =
    rows || '<p class="empty muted">No open estimates in ezyVet.</p>';
}

function estimateEditor(e) {
  const lines = e.lines.map((l, i) => `
    <div class="est-line">
      <div><b>${esc(l.name)}</b><div class="muted small">${l.optional ? "Optional" : "Recommended"} · ${span(l.low, l.high)}</div></div>
      <div class="field"><label class="sr-only" for="exp-${i}">What ${esc(l.name)} is for</label>
        <textarea id="exp-${i}" rows="2" maxlength="400" data-explanation>${esc(l.explanation)}</textarea></div>
    </div>`).join("");
  return `
    <form class="est-editor" data-send="${esc(e.id)}">
      <p class="muted small">Say what each line is for, in words the owner will understand. Don't argue for or against a line: the app shows both recommended and optional honestly.</p>
      ${lines}
      <div class="form-actions"><button class="btn">${e.status === "not_sent" ? "Send to owner" : "Update what the owner sees"}</button>
        <button type="button" class="btn ghost" data-review-close>Cancel</button>
        <span class="bad" id="est-error" role="alert"></span></div>
    </form>`;
}

// --- Visit recaps -------------------------------------------------------------------------
async function loadRecaps() {
  const body = await api("/api/clinic/recaps");
  if (!care.options) {
    care.options = body;
    resetRecapForm();
  }
  renderRecapList(body.recaps);
}

function resetRecapForm() {
  care.instructions = [{ text: "", days: "" }];
  care.results = [];
  renderRecapForm({ visit: care.options.today, vet: care.options.vets[0] || "" });
}

function renderRecapForm(values) {
  const o = care.options;
  const option = (value, label, selected) =>
    `<option value="${esc(value)}" ${value === selected ? "selected" : ""}>${esc(label)}</option>`;
  document.getElementById("recap-form").innerHTML = `
    <h3 class="serif" style="font-size: 19px">Write a recap</h3>
    <div class="two">
      <div class="field"><label for="r-pet">Patient</label>
        <select id="r-pet" name="pet_id" required><option value="">Choose a patient</option>
          ${o.patients.map((p) => option(p.id, `${p.name} (${p.owner})`, values.pet_id)).join("")}</select></div>
      <div class="field"><label for="r-vet">Vet</label>
        <select id="r-vet" name="vet">${o.vets.map((v) => option(v, v, values.vet)).join("")}</select></div>
    </div>
    <div class="field"><label for="r-visit">Visit date</label>
      <input type="date" id="r-visit" name="visit" value="${esc(values.visit || "")}" max="${esc(o.today)}"></div>
    <div class="field"><label for="r-summary">Summary for the owner</label>
      <textarea id="r-summary" name="summary" rows="4" maxlength="1200" placeholder="What you found and what happens next, in plain words.">${esc(values.summary || "")}</textarea></div>
    <div class="field"><span class="group-title">Instructions</span>
      <span class="muted small">Add a number of days for anything that runs over time ("Day 3 of 14").</span>
      ${care.instructions.map((it, i) => `
        <div class="item-row">
          <input type="text" aria-label="Instruction ${i + 1}" data-ins="${i}" data-key="text" value="${esc(it.text)}" maxlength="200" placeholder="e.g. Lead walks only">
          <input type="number" aria-label="Days for instruction ${i + 1}" data-ins="${i}" data-key="days" value="${esc(it.days)}" min="1" max="90" placeholder="days">
          <button type="button" class="remove" data-remove-ins="${i}" aria-label="Remove instruction ${i + 1}">&times;</button>
        </div>`).join("")}
      <button type="button" class="link" data-add-ins>+ Add an instruction</button></div>
    <div class="field"><span class="group-title">Results</span>
      ${care.results.map((r, i) => `
        <div class="result-row">
          <input type="text" aria-label="Result ${i + 1} name" data-res="${i}" data-key="name" value="${esc(r.name)}" maxlength="80" placeholder="e.g. Urine test">
          <select aria-label="Result ${i + 1} status" data-res="${i}" data-key="status">
            ${option("normal", "Normal", r.status)}${option("follow_up", "Vet will call", r.status)}</select>
          <button type="button" class="remove" data-remove-res="${i}" aria-label="Remove result ${i + 1}">&times;</button>
          <textarea rows="2" aria-label="Your comment on result ${i + 1}" data-res="${i}" data-key="comment" maxlength="400" placeholder="Your comment, as the owner will read it">${esc(r.comment)}</textarea>
        </div>`).join("")}
      <button type="button" class="link" data-add-res>+ Add a result</button></div>
    <div class="two">
      <div class="field"><label for="r-follow">Follow-up</label>
        <input type="text" id="r-follow" name="follow_up" value="${esc(values.follow_up || "")}" maxlength="120" placeholder="e.g. Recheck with Dr Lee"></div>
      <div class="field"><label for="r-follow-by">Follow-up by</label>
        <input type="date" id="r-follow-by" name="follow_up_by" value="${esc(values.follow_up_by || "")}"></div>
    </div>
    <div class="form-actions"><button class="btn">Release to owner</button>
      <span id="recap-status" role="status"></span></div>`;
}

function formValues() {
  const form = document.getElementById("recap-form");
  const data = Object.fromEntries(new FormData(form));
  return { ...data, follow_up_by: data.follow_up_by || null };
}

function renderRecapList(recaps) {
  document.getElementById("recap-list").innerHTML = recaps.map((r) => `
    <div class="recap-item">
      <div class="recap-head"><b>${esc(r.pet)}</b><span class="muted small">${esc(shortDate(r.visit))} · ${esc(r.vet)}</span></div>
      <div class="small">${esc(r.summary)}</div>
      <div class="muted small">${r.instructions.length} instruction${r.instructions.length === 1 ? "" : "s"} · ${r.results.length} result${r.results.length === 1 ? "" : "s"}${r.follow_up ? ` · ${esc(r.follow_up)}` : ""}</div>
    </div>`).join("") || '<p class="empty muted">No recaps released yet.</p>';
}

// --- Events ---------------------------------------------------------------------------------
document.getElementById("estimates").addEventListener("click", (event) => {
  const el = event.target.closest("button");
  if (!el) return;
  if (el.dataset.review) { care.openEstimate = el.dataset.review; renderEstimates(); }
  if (el.dataset.reviewClose !== undefined) { care.openEstimate = null; renderEstimates(); }
});

document.getElementById("estimates").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.target;
  const explanations = [...form.querySelectorAll("[data-explanation]")].map((t) => t.value);
  try {
    await api(`/api/clinic/estimates/${form.dataset.send}/send`, { method: "POST", body: { explanations } });
    care.openEstimate = null;
    await loadEstimates();
  } catch (err) {
    document.getElementById("est-error").textContent = err.message;
  }
});

const recapForm = document.getElementById("recap-form");

recapForm.addEventListener("input", (event) => {
  const el = event.target;
  if (el.dataset.ins !== undefined) care.instructions[el.dataset.ins][el.dataset.key] = el.value;
  if (el.dataset.res !== undefined) care.results[el.dataset.res][el.dataset.key] = el.value;
});

recapForm.addEventListener("click", (event) => {
  const el = event.target.closest("button");
  if (!el || el.type === "submit") return;
  const d = el.dataset;
  if (d.addIns !== undefined) care.instructions.push({ text: "", days: "" });
  if (d.removeIns !== undefined) care.instructions.splice(Number(d.removeIns), 1);
  if (d.addRes !== undefined) care.results.push({ name: "", status: "normal", comment: "" });
  if (d.removeRes !== undefined) care.results.splice(Number(d.removeRes), 1);
  renderRecapForm(formValues());
});

recapForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const values = formValues();
  const status = document.getElementById("recap-status");
  const body = {
    ...values,
    instructions: care.instructions
      .filter((i) => i.text.trim())
      .map((i) => ({ text: i.text, days: i.days ? Number(i.days) : null })),
    results: care.results.filter((r) => r.name.trim() || r.comment.trim()),
  };
  if (!body.pet_id) { status.className = "bad"; status.textContent = "Choose a patient first."; return; }
  try {
    const recap = await api("/api/clinic/recaps", { method: "POST", body });
    const pet = care.options.patients.find((p) => p.id === recap.pet_id);
    resetRecapForm();
    const done = document.getElementById("recap-status");
    done.className = "ok";
    done.textContent = `Released to ${pet.owner}'s app.`;
    renderRecapList((await api("/api/clinic/recaps")).recaps);
  } catch (err) {
    status.className = "bad";
    status.textContent = err.message;
  }
});
