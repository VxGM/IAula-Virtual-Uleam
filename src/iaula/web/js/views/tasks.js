import { get } from "../api.js";
import { el, icon, skeleton, dueInfo } from "../ui.js";
import { runAction } from "../actions.js";

function groupTasks(tasks) {
  const now = Date.now() / 1000;
  const groups = [
    { key: "over", title: "Vencidas", items: [] },
    { key: "today", title: "Hoy", items: [] },
    { key: "soon", title: "Esta semana", items: [] },
    { key: "later", title: "Después", items: [] },
  ];
  for (const t of tasks) {
    const days = Math.floor((t.due - now) / 86400);
    const g = days < 0 ? groups[0] : days === 0 ? groups[1] : days <= 7 ? groups[2] : groups[3];
    g.items.push(t);
  }
  return groups.filter((g) => g.items.length);
}

function taskItem(t) {
  const due = dueInfo(t.due);
  return el("div", { class: "tl-item" },
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
  root.append(el("div", { class: "panel glass" }, el("div", { class: "panel-body" }, skeleton(4, 42))));
  let tasks;
  try {
    tasks = await get("/api/tasks");
  } catch (e) {
    root.innerHTML = "";
    root.append(el("div", { class: "panel glass" }, el("div", { class: "panel-body" }, `Error: ${e.message}`)));
    return;
  }
  root.innerHTML = "";

  if (!tasks.length) {
    root.append(el("section", { class: "panel glass reveal" },
      el("div", { class: "panel-head" }, el("h2", null, "Entregas")),
      el("div", { class: "panel-body" },
        el("div", { class: "empty" },
          el("div", { class: "empty-glyph", "aria-hidden": "true" }),
          el("p", null, "Sin entregas registradas: corre una revisión para llenar la línea de tiempo."),
          (() => {
            const b = el("button", { class: "glossy-btn" }, icon("refresh"), "Revisar ahora");
            b.addEventListener("click", () => runAction("check", {}, "Revisando cursos"));
            return b;
          })(),
        ))));
    return;
  }

  const groups = groupTasks(tasks);
  const body = el("div", { class: "timeline" },
    ...groups.map((g) =>
      el("div", { class: "tl-group" },
        el("h3", { class: "tl-group-title" }, g.title),
        ...g.items.map(taskItem),
      )),
  );

  root.append(el("section", { class: "panel glass reveal" },
    el("div", { class: "panel-head" }, el("h2", null, "Línea de entregas"), el("span", { class: "head-count" }, String(tasks.length))),
    el("div", { class: "panel-body" }, body),
  ));
}
