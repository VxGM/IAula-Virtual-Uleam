export function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v == null || v === false) continue;
    if (k === "class") node.className = v;
    else if (k === "dataset") Object.assign(node.dataset, v);
    else if (k.startsWith("on") && typeof v === "function") node.addEventListener(k.slice(2).toLowerCase(), v);
    else node.setAttribute(k, v);
  }
  for (const child of children.flat(9)) {
    if (child == null || child === false) continue;
    node.append(child.nodeType ? child : document.createTextNode(String(child)));
  }
  return node;
}

const ICONS = {
  file: '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5"/>',
  folder: '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
  link: '<path d="M10 13a5 5 0 0 0 7 0l3-3a5 5 0 0 0-7-7l-1 1"/><path d="M14 11a5 5 0 0 0-7 0l-3 3a5 5 0 0 0 7 7l1-1"/>',
  download: '<path d="M12 3v12"/><path d="m7 10 5 5 5-5"/><path d="M5 21h14"/>',
  sync: '<path d="M21 12a9 9 0 0 1-15 6.7L3 16"/><path d="M3 12a9 9 0 0 1 15-6.7L21 8"/>',
  open: '<path d="M14 4h6v6"/><path d="M20 4 10 14"/><path d="M20 14v4a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h4"/>',
  refresh: '<path d="M21 12a9 9 0 1 1-2.6-6.4"/><path d="M21 3v6h-6"/>',
  check: '<path d="m5 13 4 4L19 7"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  book: '<path d="M4 5a2 2 0 0 1 2-2h12v16H6a2 2 0 0 0-2 2z"/><path d="M4 19a2 2 0 0 1 2-2h12"/>',
  chat: '<path d="M21 11.5a8.4 8.4 0 0 1-8.5 8.3 9 9 0 0 1-3.8-.8L4 20l1.1-4.2A8.4 8.4 0 0 1 12.5 3a8.4 8.4 0 0 1 8.5 8.5z"/>',
  send: '<path d="M22 2 11 13"/><path d="M22 2 15 22l-4-9-9-4z"/>',
  list: '<path d="M8 6h13"/><path d="M8 12h13"/><path d="M8 18h13"/><path d="M3 6h.01"/><path d="M3 12h.01"/><path d="M3 18h.01"/>',
};

export function icon(name, size = 17) {
  const span = el("span", { class: "i", "aria-hidden": "true" });
  span.innerHTML =
    `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" ` +
    `stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${ICONS[name] || ICONS.file}</svg>`;
  return span;
}

export function toast(message, kind = "info") {
  const box = document.getElementById("toasts");
  const node = el("div", { class: `toast toast--${kind}`, role: "status" }, message);
  box.append(node);
  setTimeout(() => {
    node.classList.add("hide");
    node.addEventListener("animationend", () => node.remove(), { once: true });
  }, 4200);
}

export function relTime(tsSeconds) {
  if (!tsSeconds) return "nunca";
  const s = Math.max(0, Date.now() / 1000 - tsSeconds);
  if (s < 90) return "hace un momento";
  if (s < 3600) return `hace ${Math.round(s / 60)} min`;
  if (s < 86400) return `hace ${Math.round(s / 3600)} h`;
  return `hace ${Math.round(s / 86400)} d`;
}

export function fmtFull(tsSeconds) {
  const d = new Date(tsSeconds * 1000);
  const dias = ["dom", "lun", "mar", "mié", "jue", "vie", "sáb"];
  const hh = String(d.getHours()).padStart(2, "0");
  const mm = String(d.getMinutes()).padStart(2, "0");
  return `${dias[d.getDay()]} ${d.getDate()}/${d.getMonth() + 1} ${hh}:${mm}`;
}

export function dueInfo(dueSeconds) {
  const now = Date.now() / 1000;
  const days = Math.floor((dueSeconds - now) / 86400);
  if (days < 0) return { label: "Vencida", cls: "due--over", days };
  if (days === 0) return { label: "Hoy", cls: "due--today", days };
  if (days <= 7) return { label: `en ${days} día${days === 1 ? "" : "s"}`, cls: "due--soon", days };
  return { label: fmtFull(dueSeconds).slice(0, 10), cls: "due--later", days };
}

export function skeleton(n = 3, h = 44) {
  const wrap = el("div", { class: "rows" });
  for (let i = 0; i < n; i++) wrap.append(el("div", { class: "skel", style: `height:${h}px;margin:6px 0` }));
  return wrap;
}
