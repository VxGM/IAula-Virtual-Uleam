import { get } from "../api.js";
import { el, icon, skeleton } from "../ui.js";
import { runAction } from "../actions.js";

const REFRESH_CMD = "python scripts\\refresh-google-session.py";

function statusShell() {
  const body = el("div", null, skeleton(1, 34));
  const panel = el("section", { class: "panel glass reveal" },
    el("div", { class: "panel-head" }, el("h2", null, "Sesión de NotebookLM"), icon("book", 18)),
    el("div", { class: "panel-body" }, body),
  );
  fillStatus(body);
  return panel;
}

async function fillStatus(body) {
  body.innerHTML = "";
  body.append(el("div", { class: "status status--onpanel" }, el("span", { class: "status-dot" }), "Comprobando sesión…"));
  let ok = false;
  try {
    ok = (await get("/api/notebooklm/auth?force=1")).ok;
  } catch { ok = false; }
  body.innerHTML = "";
  body.append(el("div", { class: `status status--onpanel ${ok ? "status--ok" : "status--err"}`, style: "font-size:.92rem" },
    el("span", { class: "status-dot" }),
    el("span", null, ok ? "Sesión activa: el CLI de NotebookLM responde." : "Sin sesión de Google."),
  ));
  if (!ok) {
    body.append(el("p", { class: "small muted", style: "margin:10px 0 6px" }, "Cierra Brave por completo y corre:"));
    body.append(el("div", { class: "cmd" }, REFRESH_CMD));
    const b = el("button", { class: "glossy-btn glossy-btn--sm", style: "margin-top:12px" }, icon("refresh"), "Comprobar de nuevo");
    b.addEventListener("click", () => fillStatus(body));
    body.append(b);
  }
}

function coursesPanel(data) {
  const rows = data.courses.map((c) =>
    el("div", { class: "row-item" },
      el("div", { class: "row-icon" }, icon("book")),
      el("div", { class: "row-main" },
        el("div", { class: "row-title" }, c.short),
        el("div", { class: "row-sub" },
          c.notebook_id
            ? el("span", { class: "pill pill--aqua" }, "notebook " + c.notebook_id.slice(0, 8))
            : el("span", { class: "pill pill--soft" }, "sin notebook"),
          el("span", null, `${c.files} archivo(s) listos para subir`),
          el("span", null, `· ${c.uploaded} subido(s)`),
        ),
      ),
      el("div", { class: "row-actions" },
        (() => {
          const b = el("button", { class: "glossy-btn glossy-btn--sm" }, icon("sync"), "Sync");
          b.addEventListener("click", () => runAction("nlm_sync", { course_id: c.id }, `Sincronizando ${c.short}`));
          return b;
        })(),
      ),
    ));
  return el("section", { class: "panel glass reveal" },
    el("div", { class: "panel-head" }, el("h2", null, "Cursos y notebooks"), el("span", { class: "head-count" }, String(data.courses.length))),
    el("div", { class: "panel-body" }, data.courses.length ? el("div", { class: "rows" }, ...rows)
      : el("div", { class: "empty" }, el("p", null, "Sin cursos registrados: corre una revisión."))),
  );
}

function uploadedPanel(data) {
  const table = el("table", { class: "table" },
    el("thead", null, el("tr", null, el("th", null, "Curso"), el("th", null, "Archivo"))),
    el("tbody", null, ...data.uploaded.map((u) =>
      el("tr", null, el("td", null, u.course), el("td", null, u.filename)))),
  );
  return el("section", { class: "panel glass reveal" },
    el("div", { class: "panel-head" }, el("h2", null, "Subidos a NotebookLM"), el("span", { class: "head-count" }, String(data.uploaded.length))),
    el("div", { class: "panel-body" }, data.uploaded.length ? table
      : el("div", { class: "empty" }, el("p", null, "Aún no has subido archivos."))),
  );
}

export async function render(root) {
  root.append(el("div", { class: "panel glass" }, el("div", { class: "panel-body" }, skeleton(3, 52))));
  let data;
  try {
    data = await get("/api/notebooklm");
  } catch (e) {
    root.innerHTML = "";
    root.append(el("div", { class: "panel glass" }, el("div", { class: "panel-body" }, `Error: ${e.message}`)));
    return;
  }
  root.innerHTML = "";
  root.append(el("div", { class: "nlm-grid" },
    statusShell(),
    coursesPanel(data),
    uploadedPanel(data),
  ));
}
