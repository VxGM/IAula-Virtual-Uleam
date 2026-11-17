import { get, post } from "../api.js";
import { el, icon, skeleton, toast } from "../ui.js";
import { runAction } from "../actions.js";
import { renderBrowserPicker } from "../browser-picker.js";

const PROVIDER_KEYS = "https://platform.openai.com/api-keys";

function card(title, iconName, ...children) {
  return el("section", { class: "panel glass reveal" },
    el("div", { class: "panel-head" }, el("h2", null, title), icon(iconName, 18)),
    el("div", { class: "panel-body" }, ...children),
  );
}

function field(id, labelText, input, help) {
  const lab = el("label", { class: "setup-label", for: id }, labelText);
  input.id = id;
  return [lab, input, help ? el("p", { class: "field-help" }, help) : null];
}

function row(...children) {
  return el("div", { class: "settings-actions" }, ...children);
}

async function chatCard() {
  let info;
  try {
    info = await get("/api/settings/chat");
  } catch (e) {
    return card("Asistente IA", "chat", el("p", { class: "form-error" }, `No pude leer la configuración: ${e.message}`));
  }

  const base = el("input", {
    class: "chat-input", type: "url", autocomplete: "off", spellcheck: "false",
    value: info.base_url || info.defaults.base_url,
  });
  const model = el("input", {
    class: "chat-input", type: "text", autocomplete: "off", spellcheck: "false",
    value: info.model || info.defaults.model,
  });
  const key = el("input", {
    class: "chat-input", type: "password", autocomplete: "off", spellcheck: "false",
    placeholder: info.configured ? `${info.key_hint} (deja vacío para conservarla)` : "sk-... o la clave de tu proveedor",
  });
  if (info.locked_by_env) {
    key.disabled = true;
    key.placeholder = "La clave la define la variable OPENAI_API_KEY del servidor";
  }

  const state = el("p", { class: info.configured ? "pill pill--green" : "pill" },
    info.configured ? "Conectado" : "Sin clave");
  const error = el("p", { class: "form-error", role: "alert" });
  error.hidden = true;

  const save = el("button", { class: "glossy-btn" }, icon("check"), "Probar y guardar");
  save.addEventListener("click", async () => {
    error.hidden = true;
    if (!base.value.trim() || !model.value.trim()) {
      error.textContent = "Completa la URL del proveedor y el modelo.";
      error.hidden = false;
      return;
    }
    save.classList.add("is-busy");
    try {
      const res = await post("/api/settings/chat", {
        base_url: base.value.trim(),
        model: model.value.trim(),
        api_key: info.locked_by_env ? "" : key.value.trim(),
      });
      key.value = "";
      state.textContent = "Conectado";
      state.className = "pill pill--green";
      toast(`Proveedor conectado en ${res.latency_ms} ms`, "ok");
      const fresh = await get("/api/settings/chat");
      key.placeholder = `${fresh.key_hint} (deja vacío para conservarla)`;
    } catch (e) {
      error.textContent = e.message;
      error.hidden = false;
    } finally {
      save.classList.remove("is-busy");
    }
  });

  const clear = el("button", { class: "glossy-btn glossy-btn--ghost glossy-btn--sm" }, icon("mute"), "Quitar clave");
  clear.hidden = !info.configured || info.locked_by_env;
  clear.addEventListener("click", async () => {
    if (!window.confirm("¿Quitar la API key guardada? El Asistente dejará de responder hasta que pongas otra.")) return;
    clear.classList.add("is-busy");
    try {
      await post("/api/settings/chat/clear");
      state.textContent = "Sin clave";
      state.className = "pill";
      clear.hidden = true;
      key.placeholder = "sk-... o la clave de tu proveedor";
      toast("Clave eliminada", "ok");
    } catch (e) {
      toast(e.message, "err");
    } finally {
      clear.classList.remove("is-busy");
    }
  });

  return card("Asistente IA", "chat",
    el("div", { class: "settings-head" },
      el("p", { class: "small muted" },
        "Funciona con OpenAI y con cualquier proveedor compatible (Groq, OpenRouter, Together, un modelo local)."),
      state,
    ),
    ...field("chat-base", "URL del proveedor", base,
      "Por defecto https://api.openai.com/v1. Para un modelo local, http://127.0.0.1:11434/v1."),
    ...field("chat-model", "Modelo", model, "El nombre exacto que usa tu proveedor, por ejemplo gpt-5.4-mini."),
    ...field("chat-key", "API key", key,
      info.locked_by_env
        ? "La gestiona el entorno del servidor; no se puede cambiar desde aquí."
        : "Se guarda cifrada con DPAPI en este equipo. Nunca se envía a otro sitio."),
    row(save, clear,
      info.locked_by_env ? null : el("a", {
        class: "link-quiet", href: PROVIDER_KEYS, target: "_blank", rel: "noopener",
      }, icon("open"), "Cómo obtener una clave")),
    error,
    el("p", { class: "field-help" },
      "La voz (micrófono y respuestas habladas) usa los modelos de audio de OpenAI; con otros proveedores puede no estar disponible."),
  );
}

async function portalCard() {
  let info = { username: "", has_password: false };
  try {
    info = await get("/api/settings/portal");
  } catch { /* use defaults */ }

  const user = el("input", {
    class: "chat-input", type: "text", autocomplete: "username",
    value: info.username || "", placeholder: "tucorreo@live.uleam.edu.ec",
  });
  const pass = el("input", {
    class: "chat-input", type: "password", autocomplete: "current-password",
    placeholder: info.has_password ? "•••••••• (deja vacío para conservarla)" : "Tu contraseña del aula",
  });
  const error = el("p", { class: "form-error", role: "alert" });
  error.hidden = true;

  const save = el("button", { class: "glossy-btn" }, icon("check"), "Guardar cuenta");
  save.addEventListener("click", async () => {
    error.hidden = true;
    if (!user.value.trim() || (!info.has_password && !pass.value)) {
      error.textContent = info.has_password
        ? "Escribe el usuario del aula."
        : "Completa usuario y contraseña.";
      error.hidden = false;
      return;
    }
    save.classList.add("is-busy");
    try {
      await post("/api/settings/portal", { username: user.value.trim(), password: pass.value });
      pass.value = "";
      toast("Cuenta guardada", "ok");
      runAction("login", {}, "Conectando con el aula");
    } catch (e) {
      error.textContent = e.message;
      error.hidden = false;
    } finally {
      save.classList.remove("is-busy");
    }
  });

  const reconnect = el("button", { class: "glossy-btn glossy-btn--ghost" }, icon("refresh"), "Reconectar el aula");
  reconnect.addEventListener("click", () => runAction("login", {}, "Conectando con el aula"));

  return card("Cuenta del aula", "book",
    el("p", { class: "small muted" },
      `Portal de la ULEAM (${info.base_url || "aulavirtualmoodle.uleam.edu.ec"}). La contraseña se guarda cifrada.`),
    ...field("portal-user", "Usuario", user, null),
    ...field("portal-pass", "Contraseña", pass,
      "Solo se usa para iniciar sesión en Microsoft cuando la sesión caduca."),
    row(save, reconnect),
    error,
  );
}

async function diagnosticsCard() {
  let result;
  try {
    result = await get("/api/diagnostics");
  } catch {
    return card("Diagnóstico", "shield",
      el("p", { class: "small muted" }, "No pude ejecutar el diagnóstico ahora mismo."));
  }
  const bad = result.summary.error;
  const warn = result.summary.warn;
  const label = bad
    ? `${bad} problema${bad === 1 ? "" : "s"} que impide${bad === 1 ? "" : "n"} funcionar`
    : warn ? `${warn} aviso${warn === 1 ? "" : "s"} de configuración` : "Todo en orden";

  const open = el("button", { class: "glossy-btn glossy-btn--ghost glossy-btn--sm" }, icon("shield"), "Ver diagnóstico");
  open.addEventListener("click", () => { location.hash = "#diagnostico"; });

  return card("Diagnóstico", "shield",
    el("div", { class: "diagnostics-mini" },
      el("span", { class: `status status--onpanel ${bad ? "status--err" : warn ? "status--warn" : "status--ok"}` },
        el("span", { class: "status-dot" }), el("span", null, label)),
      el("p", { class: "small muted" },
        `${result.summary.ok} comprobaciones correctas de ${result.items.length}.`),
    ),
    row(open),
  );
}

function privacyCard() {
  return card("Privacidad y datos", "shield",
    el("ul", { class: "privacy-list" },
      el("li", null, "Todo se guarda en tu equipo: no hay servidores de IAula ni telemetría."),
      el("li", null, "Tu contraseña del aula y tu API key se cifran con DPAPI, ligadas a tu usuario de Windows."),
      el("li", null, "Las únicas conexiones salen al aula de la ULEAM, al proveedor de IA que elijas y a NotebookLM si lo usas."),
      el("li", null, "Desinstalar la app borra las credenciales, las descargas y el navegador interno."),
    ),
    el("p", { class: "field-help" },
      "Puedes revisar el código y los hashes del instalador en el repositorio del proyecto."),
  );
}

export async function render(root) {
  root.append(el("section", { class: "panel glass" },
    el("div", { class: "panel-body" }, skeleton(6, 46))));

  const [chat, portal, diag] = await Promise.all([
    chatCard().catch((e) => card("Asistente IA", "chat", el("p", { class: "form-error" }, e.message))),
    portalCard(),
    diagnosticsCard(),
  ]);

  root.innerHTML = "";
  const browser = el("div");
  root.append(el("section", { class: "hero-strip glass-strong shine reveal" },
    el("div", { class: "hero-main" },
      el("h1", null, "Ajustes"),
      el("p", { class: "hero-sub" }, "Tu cuenta, tu proveedor de IA y el estado de la app."),
    ),
  ));

  root.append(el("div", { class: "settings-grid" },
    el("div", { class: "settings-col" }, chat, portal),
    el("div", { class: "settings-col" },
      card("Navegador preferido", "globe",
        el("p", { class: "small muted" },
          "IAula lo usa para iniciar sesión en el aula y para NotebookLM. Brave, Chrome y Edge son compatibles."),
        browser),
      diag,
      privacyCard(),
    ),
  ));

  renderBrowserPicker(browser, { buttonLabel: "Guardar navegador" });
}
