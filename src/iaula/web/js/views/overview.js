import { get } from "../api.js";
import { el, icon, skeleton, dueInfo, relTime } from "../ui.js";
import { runAction } from "../actions.js";

const KIND_ICON = { resource: "file", folder: "folder", url: "link", assign: "clock", forum: "list" };

function tm(label, value, extra) {
  return el("div", { class: "tm-cell" },
    el("span", { class: "tm-label" }, label),
    el("span", { class: "tm-value" }, value, extra ? el("span", { class: "muted" }, extra) : null),
  );
}

function panel(title, count, bodyNode) {
  return el("section", { class: "panel glass reveal" },
    el("div", { class: "panel-head" }, el("h2", null, title),
      count != null ? el("span", { class: "head-count" }, String(count)) : null),
    el("div", { class: "panel-body" }, bodyNode),
  );
}

function emptyBox(message, ctaLabel, ctaFn) {
  const box = el("div", { class: "empty" },
    el("div", { class: "empty-glyph", "aria-hidden": "true" }),
    el("p", null, message),
  );
  if (ctaLabel) {
    const b = el("button", { class: "glossy-btn" }, icon("refresh"), ctaLabel);
    b.addEventListener("click", ctaFn);
    box.append(b);
  }
  return box;
}

function materialRow(m) {
  const row = el("div", { class: "row-item" },
    el("div", { class: "row-icon" }, icon(KIND_ICON[m.kind] || "file")),
    el("div", { class: "row-main" },
      el("div", { class: "row-title", title: m.title }, m.title),
      el("div", { class: "row-sub" }, el("span", { class: "pill pill--soft" }, m.course),
        el("span", null, relTime(m.first_seen))),
    ),
    el("div", { class: "row-actions" },
      (() => {
        const b = el("button", { class: "glossy-btn glossy-btn--sm" }, icon("download"), "Bajar");
        b.addEventListener("click", () => runAction("download", { course_id: m.course_id, item: m.id }, `Bajando "${m.title}"`));
        return b;
      })(),
      el("a", { class: "glossy-btn glossy-btn--sm glossy-btn--ghost", href: m.url, target: "_blank", rel: "noopener" }, icon("open"), "Abrir"),
    ),
  );
  return row;
}

function taskRow(t) {
  const due = dueInfo(t.due);
  return el("div", { class: "row-item" },
    el("span", { class: `due ${due.cls}` }, due.label),
    el("div", { class: "row-main" },
      el("div", { class: "row-title", title: t.name }, t.name),
      el("div", { class: "row-sub" }, el("span", { class: "pill pill--soft" }, t.course)),
    ),
    el("div", { class: "row-actions" },
      el("a", { class: "glossy-btn glossy-btn--sm glossy-btn--ghost", href: t.url, target: "_blank", rel: "noopener" }, icon("open"), "Abrir"),
    ),
  );
}

export async function render(root) {
  root.append(el("div", { class: "panel glass" }, el("div", { class: "panel-body" }, skeleton(3, 46))));
  let s;
  try {
    s = await get("/api/summary");
  } catch (e) {
    root.innerHTML = "";
    root.append(el("div", { class: "panel glass" }, el("div", { class: "panel-body" }, `Error: ${e.message}`)));
    return;
  }
  root.innerHTML = "";

  const last = s.last_check
    ? `Última revisión: ${relTime(s.last_check.ts)}${s.last_check.baseline ? " (línea base)" : ""}`
    : "Aún sin revisar";

  const checkBtn = el("button", { class: "glossy-btn" }, icon("refresh"), "Revisar ahora");
  checkBtn.addEventListener("click", () => runAction("check", {}, "Revisando cursos"));

  root.append(el("section", { class: "hero-strip glass-strong shine reveal" },
    el("div", { class: "hero-main" },
      el("h1", null, "Tu aula, de un vistazo"),
      el("div", { class: "hero-sub" },
        el("span", null, last),
        el("span", { class: "muted" }, "·"),
        el("span", null, `${s.counts.courses} cursos`),
      ),
    ),
    el("div", { class: "hero-actions" },
      checkBtn,
      el("a", { class: "glossy-btn glossy-btn--ghost", href: s.portal_url, target: "_blank", rel: "noopener" }, icon("open"), "Abrir aula"),
    ),
  ));

  const next = s.next_due;
  root.append(el("section", { class: "telemetry glass reveal" },
    tm("Cursos", String(s.counts.courses)),
    tm("Materiales nuevos", String(s.counts.new_materials)),
    tm("Entregas pendientes", String(s.counts.pending_tasks)),
    tm("Próxima entrega", next ? next.name : "—", next ? dueInfo(next.due).label : null),
  ));

  const novBody = s.new_materials.length
    ? el("div", { class: "rows" }, ...s.new_materials.map(materialRow))
    : emptyBox("Sin novedades desde la última revisión.", "Revisar ahora",
        () => runAction("check", {}, "Revisando cursos"));

  const entBody = s.upcoming_tasks.length
    ? el("div", { class: "rows" }, ...s.upcoming_tasks.map(taskRow))
    : emptyBox("Sin entregas próximas registradas.", null, null);

  root.append(el("div", { class: "cols" },
    panel("Novedades", s.new_materials.length, novBody),
    panel("Próximas entregas", s.upcoming_tasks.length, entBody),
  ));
}
