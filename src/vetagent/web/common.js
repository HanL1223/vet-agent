// Small helpers shared by both pages.

function esc(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;").replaceAll("'", "&#39;");
}

const money = (n) => "$" + Number(n).toLocaleString("en-AU");

async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
    body: options.body ? JSON.stringify(options.body) : undefined,
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail || `Request failed (${res.status})`);
  }
  return res.json();
}

// Simple line portraits so pets get a face instead of an initial.
const PET_ICONS = {
  dog: '<path d="M15 17c-4 1-6 8-4 13 2 1 4 0 5-2"/><path d="M33 17c4 1 6 8 4 13-2 1-4 0-5-2"/>' +
    '<path d="M16 22c0-5 3.5-8 8-8s8 3 8 8v6c0 6-3.5 9-8 9s-8-3-8-9z"/>' +
    '<circle cx="20.5" cy="24" r="1.2" fill="currentColor"/><circle cx="27.5" cy="24" r="1.2" fill="currentColor"/>' +
    '<path d="M22 29.5h4l-2 2z" fill="currentColor"/><path d="M24 31.5v1.5m-3 .5c1.5 1 4.5 1 6 0"/>',
  cat: '<path d="M14 21l-1-9 7 4m15 5l1-9-7 4"/><path d="M14 21c0-3 4-5 10-5s10 2 10 5v6c0 6-4.5 9-10 9s-10-3-10-9z"/>' +
    '<circle cx="20" cy="25" r="1.2" fill="currentColor"/><circle cx="28" cy="25" r="1.2" fill="currentColor"/>' +
    '<path d="M22.5 29h3L24 30.5z" fill="currentColor"/><path d="M24 30.5v1m-6.5-2.5H12m5.5 2.5-5 1m19-3.5H36m-5.5 2.5 5 1"/>',
};

function petIcon(species) {
  return `<svg viewBox="0 0 48 48" fill="none" stroke="currentColor" stroke-width="2"
    stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${PET_ICONS[species] || PET_ICONS.dog}</svg>`;
}

const PAW = `<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
  <ellipse cx="6" cy="10" rx="2.2" ry="2.8"/><ellipse cx="10" cy="6" rx="2.2" ry="2.8"/>
  <ellipse cx="14.5" cy="6" rx="2.2" ry="2.8"/><ellipse cx="18.5" cy="10" rx="2.2" ry="2.8"/>
  <path d="M12 11c-3 0-6.5 4-6.5 6.5 0 2 1.5 3 3.2 3 1.4 0 2.2-.8 3.3-.8s1.9.8 3.3.8c1.7 0 3.2-1 3.2-3C18.5 15 15 11 12 11z"/></svg>`;
