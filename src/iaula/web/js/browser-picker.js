import { get, post } from "./api.js";
import { el, icon, toast } from "./ui.js";

export async function renderBrowserPicker(container, { buttonLabel = "Guardar", onSaved } = {}) {
  let info;
  try {
    info = await get("/api/notebooklm/browsers");
  } catch {
    container.append(el("p", { class: "small muted" }, "No pude detectar los navegadores instalados."));
    return;
  }
  const browsers = info.browsers || [];
  if (!browsers.length) {
    container.append(el("p", { class: "small muted" },
      "No detecté Brave, Chrome ni Edge. IAula descargará su navegador interno cuando haga falta."));
    return;
  }

  const group = el("div", { class: "choice-list", role: "radiogroup", "aria-label": "Navegador preferido" });
  for (const b of browsers) {
    const id = `browser-${b.key}`;
    const input = el("input", { type: "radio", name: "browser-pref", id, value: b.key });
    if ((info.default || browsers[0].key) === b.key) input.checked = true;
    group.append(el("label", { class: "choice", for: id },
      input,
      el("span", { class: "choice-label" }, b.name),
      b.key === "brave" ? el("span", { class: "pill pill--soft" }, "recomendado") : null,
    ));
  }

  const save = el("button", { class: "glossy-btn glossy-btn--sm" }, icon("check"), buttonLabel);
  save.addEventListener("click", async () => {
    const sel = group.querySelector("input:checked") || group.querySelector("input");
    if (!sel) return;
    save.classList.add("is-busy");
    try {
      await post("/api/setup/browser", { browser: sel.value });
      toast("Navegador guardado", "ok");
      if (onSaved) onSaved(sel.value);
    } catch (e) {
      toast(e.message, "err");
    } finally {
      save.classList.remove("is-busy");
    }
  });

  container.append(group, el("div", { class: "settings-actions" }, save));
}
