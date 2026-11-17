import { get, post } from "../api.js";
import { el, icon, skeleton, toast, relTime } from "../ui.js";
import { watchJob } from "../jobwindow.js";

const META = {
  ok: { label: "Correcto", cls: "diag--ok", icon: "check" },
  warn: { label: "Aviso", cls: "diag--warn", icon: "clock" },
  error: { label: "Error", cls: "diag--err", icon: "stop" },
  skip: { label: "Omitido", cls: "diag--skip", icon: "list" },
};

export function fetchDiagnostics(force = false) {
  return get(`/api/diagnostics${force ? "?force=1" : ""}`);
}

async function runRepair(ids, onDone) {
  if (ids.includes("chromium") &&
      !window.confirm("Se descargará el navegador interno (≈180 MB, una sola vez). ¿Continuar?")) {
    return;
  }
  try {
    const { job_id } = await post("/api/diagnostics/repair", { ids });
    watchJob(job_id, "Preparando componentes", (ok) => onDone(ok));
  } catch (e) {
    toast(e.message, "err");
  }
}

function statusLine(item) {
  const meta = META[item.status] || META.warn;
  return el("span", { class: `diag-status ${meta.cls}` },
    el("span", { class: "diag-dot" }), meta.label);
}

function itemRow(item, onRepair) {
  const row = el("li", { class: `diag-row diag-row--${item.status}` },
    el("div", { class: "diag-main" },
      el("div", { class: "diag-title" }, el("b", null, item.label), statusLine(item)),
      el("div", { class: "diag-detail" }, item.detail || ""),
      item.hint && item.status !== "ok" && item.status !== "skip"
        ? el("div", { class: "diag-hint" }, item.hint) : null,
    ),
  );
  if (item.fixable && (item.status === "warn" || item.status === "error")) {
    const fix = el("button", { class: "glossy-btn glossy-btn--sm", type: "button" }, icon("refresh"), "Reparar");
    fix.addEventListener("click", () => {
      fix.classList.add("is-busy");
      runRepair([item.id], () => onRepair());
    });
    row.append(fix);
  }
  return row;
}

function summaryLine(result) {
  const s = result.summary;
  const bad = s.error;
  const warn = s.warn;
  const text = bad
    ? `${bad} problema${bad === 1 ? "" : "s"} que requiere${bad === 1 ? "" : "n"} atención`
    : warn
      ? `${warn} aviso${warn === 1 ? "" : "s"} de configuración`
      : "Todo listo para usar IAula";
  return el("div", { class: `diag-summary ${bad ? "diag--err" : warn ? "diag--warn" : "diag--ok"}` },
    el("span", { class: "status-dot" }),
    el("span", { class: "diag-summary-text" }, text),
    el("span", { class: "small muted" }, `Revisado ${relTime(result.checked_at)}`),
  );
}

function fixableIds(result) {
  return result.items
    .filter((i) => i.fixable && (i.status === "warn" || i.status === "error"))
    .map((i) => i.id);
}

export function diagnosticsPanel(result, { title = "Diagnóstico", compact = false, onRefresh } = {}) {
  const list = el("ul", { class: "diag-list" });
  const rerun = async () => {
    const fresh = await fetchDiagnostics(true);
    const host = list.closest(".diag-host");
    if (host) host.replaceWith(diagnosticsPanel(fresh, { title, compact, onRefresh }));
    renderNotice(fresh);
    if (onRefresh) onRefresh(fresh);
  };
  for (const item of result.items) {
    if (compact && (item.status === "ok" || item.status === "skip")) continue;
    list.append(itemRow(item, rerun));
  }

  const actions = el("div", { class: "settings-actions" });
  const recheck = el("button", { class: "glossy-btn glossy-btn--ghost glossy-btn--sm" }, icon("refresh"), "Volver a comprobar");
  recheck.addEventListener("click", () => {
    recheck.classList.add("is-busy");
    rerun().finally(() => recheck.classList.remove("is-busy"));
  });
  actions.append(recheck);

  const ids = fixableIds(result);
  if (ids.length) {
    const fixAll = el("button", { class: "glossy-btn glossy-btn--sm" }, icon("check"), "Reparar todo");
    fixAll.addEventListener("click", () => {
      fixAll.classList.add("is-busy");
      runRepair(ids, rerun);
    });
    actions.append(fixAll);
  }

  const body = el("div", { class: "panel-body" },
    summaryLine(result),
    list,
    actions,
  );
  return el("section", { class: "panel glass diag-host" },
    el("div", { class: "panel-head" }, el("h2", null, title), icon("shield", 18)),
    body,
  );
}

export async function render(root) {
  root.append(el("section", { class: "panel glass" },
    el("div", { class: "panel-body" }, skeleton(6, 46))));
  let result;
  try {
    result = await fetchDiagnostics(true);
  } catch (e) {
    root.innerHTML = "";
    root.append(el("section", { class: "panel glass" },
      el("div", { class: "panel-body" }, el("p", { class: "form-error" }, `No pude ejecutar el diagnóstico: ${e.message}`))));
    return;
  }
  root.innerHTML = "";
  root.append(el("section", { class: "hero-strip glass-strong shine reveal" },
    el("div", { class: "hero-main" },
      el("h1", null, "Diagnóstico"),
      el("p", { class: "hero-sub" },
        "Comprueba que todo lo que IAula necesita esté en su sitio. Nada sale de tu equipo."),
    ),
  ));
  root.append(diagnosticsPanel(result, { title: "Comprobaciones" }));
}

export function renderBlocking(root, result) {
  root.innerHTML = "";
  document.body.classList.add("setup-mode");
  const panel = diagnosticsPanel(result, {
    title: "Prepara IAula", compact: true,
    onRefresh: (fresh) => { if (!fresh.fatal) location.reload(); },
  });
  panel.classList.add("blocking-card");
  root.append(el("div", { class: "blocking-wrap" },
    el("p", { class: "small muted blocking-lead" },
      "Falta algo para que IAula pueda funcionar. Revisa estos puntos y vuelve a comprobar."),
    panel,
  ));
}

export function renderNotice(result) {
  const box = document.getElementById("notices");
  if (!box) return;
  box.innerHTML = "";
  const bad = result.summary.error;
  const warn = result.summary.warn;
  if (!bad && !warn) return;
  const signature = result.items
    .filter((i) => i.status === "warn" || i.status === "error")
    .map((i) => `${i.id}:${i.status}`).join(",");
  let dismissed = "";
  try { dismissed = localStorage.getItem("iaula-diag-dismissed") || ""; } catch { /* ignore */ }
  if (dismissed === signature) return;

  const open = el("button", { class: "glossy-btn glossy-btn--sm" }, icon("shield"), "Ver diagnóstico");
  open.addEventListener("click", () => { location.hash = "#diagnostico"; });
  const close = el("button", {
    class: "notice-close", type: "button", "aria-label": "Ocultar aviso",
  }, "✕");
  close.addEventListener("click", () => {
    try { localStorage.setItem("iaula-diag-dismissed", signature); } catch { /* ignore */ }
    box.innerHTML = "";
  });
  const node = el("div", { class: `notice glass ${bad ? "notice--err" : "notice--warn"}`, role: "status" },
    el("span", { class: "notice-text" },
      bad ? `${bad} problema${bad === 1 ? "" : "s"} en el diagnóstico.`
        : `${warn} aviso${warn === 1 ? "" : "s"} de configuración.`),
    open,
    close,
  );
  box.append(node);
}
