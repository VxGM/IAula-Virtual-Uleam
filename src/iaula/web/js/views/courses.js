import { get } from "../api.js";
import { el, icon, skeleton, relTime } from "../ui.js";
import { runAction } from "../actions.js";

const KIND_ICON = { resource: "file", folder: "folder", url: "link" };

function materialRow(course, m, newIds) {
  const row = el("div", { class: "row-item" },
    el("div", { class: "row-icon" }, icon(KIND_ICON[m.kind] || "file")),
    el("div", { class: "row-main" },
      el("div", { class: "row-title", title: m.title }, m.title),
      el("div", { class: "row-sub" },
        el("span", null, m.section || ""),
        relTime(m.first_seen) !== "nunca" ? el("span", null, "· " + relTime(m.first_seen)) : null,
      ),
    ),
    el("div", { class: "row-actions" },
      newIds.has(m.id) ? el("span", { class: "pill pill--green" }, "nuevo") : null,
      (() => {
        const b = el("button", { class: "glossy-btn glossy-btn--sm" }, icon("download"), "Bajar");
        b.addEventListener("click", () => runAction("download", { course_id: course.id, item: m.id }, `Bajando "${m.title}"`));
        return b;
      })(),
      el("a", { class: "glossy-btn glossy-btn--sm glossy-btn--ghost", href: m.url, target: "_blank", rel: "noopener" }, icon("open"), "Abrir"),
    ),
  );
  return row;
}

function courseCard(c) {
  const mats = el("div", { class: "course-materials" });

  const btnMats = el("button", { class: "glossy-btn glossy-btn--sm glossy-btn--ghost" }, icon("list"), "Materiales");
  btnMats.addEventListener("click", async () => {
    mats.classList.toggle("open");
    if (!mats.dataset.loaded && mats.classList.contains("open")) {
      mats.append(skeleton(2, 34));
      try {
        const items = await get(`/api/courses/${c.id}/materials`);
        const newIds = new Set(c.new_ids || []);
        mats.innerHTML = "";
        mats.append(items.length
          ? el("div", { class: "rows" }, ...items.map((m) => materialRow(c, m, newIds)))
          : el("div", { class: "empty" }, el("p", null, "Sin materiales registrados todavía.")));
        mats.dataset.loaded = "1";
      } catch (e) {
        mats.innerHTML = "";
        mats.append(el("div", { class: "empty" }, el("p", null, `Error: ${e.message}`)));
      }
    }
  });

  const btnDl = el("button", { class: "glossy-btn glossy-btn--sm glossy-btn--green" }, icon("download"), "Descargar");
  btnDl.addEventListener("click", () => runAction("download", { course_id: c.id }, `Bajando ${c.short}`));

  const btnSync = el("button", { class: "glossy-btn glossy-btn--sm" }, icon("sync"), "Sync NotebookLM");
  btnSync.addEventListener("click", () => runAction("nlm_sync", { course_id: c.id }, `Sincronizando ${c.short}`));

  return el("article", { class: "course-card glass shine reveal" },
    el("div", { class: "course-top" },
      el("div", { class: "course-name" },
        el("h3", null, c.short),
        el("div", { class: "small muted" }, c.full),
      ),
      el("a", { class: "glossy-btn glossy-btn--sm glossy-btn--ghost", href: c.url, target: "_blank", rel: "noopener" }, icon("open"), "Moodle"),
    ),
    el("div", { class: "course-stats" },
      el("span", null, el("b", null, String(c.materials)), " materiales"),
      el("span", null, el("b", null, String(c.new_materials)), " nuevos"),
      el("span", null, el("b", null, String(c.downloads)), " descargados"),
      el("span", null, el("b", null, String(c.pending_tasks)), " entregas"),
      el("span", { class: "notebook-line" }, icon("book", 15), c.notebook_id ? "notebook ✓" : "sin notebook"),
    ),
    el("div", { class: "course-actions" }, btnMats, btnDl, btnSync),
    mats,
  );
}

export async function render(root) {
  root.append(el("div", { class: "panel glass" }, el("div", { class: "panel-body" }, skeleton(3, 64))));
  let courses;
  try {
    courses = await get("/api/courses");
  } catch (e) {
    root.innerHTML = "";
    root.append(el("div", { class: "panel glass" }, el("div", { class: "panel-body" }, `Error: ${e.message}`)));
    return;
  }
  root.innerHTML = "";
  if (!courses.length) {
    root.append(el("div", { class: "panel glass" },
      el("div", { class: "empty" },
        el("div", { class: "empty-glyph", "aria-hidden": "true" }),
        el("p", null, "Todavía no conozco tus cursos: corre una revisión."),
        (() => {
          const b = el("button", { class: "glossy-btn" }, icon("refresh"), "Revisar ahora");
          b.addEventListener("click", () => runAction("check", {}, "Revisando cursos"));
          return b;
        })(),
      )));
    return;
  }
  const list = el("div", { class: "courses-list" }, ...courses.map(courseCard));
  root.append(list);
}
