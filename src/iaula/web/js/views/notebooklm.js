import { get, post } from "../api.js";
import { el, icon, skeleton, toast } from "../ui.js";
import { runAction } from "../actions.js";

const REFRESH_CMD = "python scripts\\refresh-google-session.py";

function renewSession() {
  const ok = confirm("Se cerrará Brave por completo para renovar la sesión de Google.\n¿Continuar?");
  if (!ok) return;
  runAction("refresh_session", {}, "Renovando sesión de Google");
}

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

  const actions = el("div", { style: "display:flex;gap:8px;flex-wrap:wrap;margin-top:12px" });

  if (!ok) {
    body.append(el("p", { class: "small muted", style: "margin:10px 0 0" },
      "Renueva con un clic (cierra Brave por ti) o a mano:"));
    body.append(el("div", { class: "cmd", style: "margin-top:8px" }, REFRESH_CMD));
    const renew = el("button", { class: "glossy-btn glossy-btn--sm" }, icon("refresh"), "Renovar sesión (cierra Brave)");
    renew.addEventListener("click", renewSession);
    const check = el("button", { class: "glossy-btn glossy-btn--sm glossy-btn--ghost" }, icon("check"), "Comprobar de nuevo");
    check.addEventListener("click", () => fillStatus(body));
    actions.append(renew, check);
  } else {
    const renew = el("button", { class: "glossy-btn glossy-btn--sm glossy-btn--ghost", title: "Cierra Brave y vuelve a extraer la sesión de Google" }, icon("refresh"), "Renovar sesión");
    renew.addEventListener("click", renewSession);
    const check = el("button", { class: "glossy-btn glossy-btn--sm glossy-btn--ghost" }, icon("check"), "Comprobar de nuevo");
    check.addEventListener("click", () => fillStatus(body));
    actions.append(renew, check);
  }
  body.append(actions);
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

function browserPanel(info) {
  const { browsers = [], default: defKey } = info;
  if (!browsers.length) return null;
  const radios = [];
  const labels = browsers.map((b) => {
    const radio = el("input", { type: "radio", name: "browser-pick", value: b.key });
    if (b.key === defKey) radio.checked = true;
    radios.push(radio);
    return el("label", { class: "setup-label", style: "display:flex;align-items:center;gap:8px;cursor:pointer" },
      radio, b.name, b.key === defKey ? el("span", { class: "small muted" }, "(recomendado)") : null);
  });
  const save = el("button", { class: "glossy-btn glossy-btn--sm" }, icon("check"), "Guardar navegador");
  save.addEventListener("click", async () => {
    const sel = radios.find((r) => r.checked) || radios[0];
    const name = browsers.find((b) => b.key === sel.value)?.name || sel.value;
    save.classList.add("is-busy");
    try {
      await post("/api/setup/browser", { browser: sel.value });
      toast(`Navegador guardado: ${name}`, "ok");
    } catch (e) {
      toast(e.message, "err");
    } finally {
      save.classList.remove("is-busy");
    }
  });
  return el("section", { class: "panel glass reveal" },
    el("div", { class: "panel-head" }, el("h2", null, "Navegador preferido"), icon("globe", 18)),
    el("div", { class: "panel-body" },
      el("p", { class: "small muted", style: "margin-bottom:10px" },
        "IAula abre uno de tus navegadores instalados para iniciar sesión en el aula."),
      ...labels,
      el("div", { style: "margin-top:14px" }, save)),
  );
}

export async function render(root) {
  root.append(el("div", { class: "panel glass" }, el("div", { class: "panel-body" }, skeleton(3, 52))));
  let data;
  let browserInfo = null;
  try {
    data = await get("/api/notebooklm");
  } catch (e) {
    root.innerHTML = "";
    root.append(el("div", { class: "panel glass" }, el("div", { class: "panel-body" }, `Error: ${e.message}`)));
    return;
  }
  try { browserInfo = await get("/api/notebooklm/browsers"); } catch { /* ignore */ }
  root.innerHTML = "";
  const extra = browserInfo ? browserPanel(browserInfo) : null;
  root.append(el("div", { class: "nlm-grid" },
    statusShell(),
    coursesPanel(data),
    uploadedPanel(data),
    ...(extra ? [extra] : []),
  ));
}
