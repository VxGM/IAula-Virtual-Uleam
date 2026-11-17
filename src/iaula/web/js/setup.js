import { post } from "./api.js";
import { el, icon, toast } from "./ui.js";
import { runAction, setOnJobDone } from "./actions.js";
import { renderBrowserPicker } from "./browser-picker.js";

const STEPS = ["Tu cuenta", "Asistente IA", "Navegador"];

export function renderSetup(root) {
  let step = 0;

  const user = el("input", {
    class: "chat-input", type: "text", autocomplete: "username",
    placeholder: "tucorreo@live.uleam.edu.ec",
  });
  const pass = el("input", {
    class: "chat-input", type: "password", autocomplete: "current-password",
    placeholder: "Tu contraseña del aula",
  });
  const base = el("input", {
    class: "chat-input", type: "url", autocomplete: "off", spellcheck: "false",
    placeholder: "https://api.openai.com/v1",
  });
  const model = el("input", {
    class: "chat-input", type: "text", autocomplete: "off", spellcheck: "false",
    placeholder: "gpt-5.4-mini",
  });
  const key = el("input", {
    class: "chat-input", type: "password", autocomplete: "off", spellcheck: "false",
    placeholder: "sk-... (opcional)",
  });

  const error = el("p", { class: "form-error", role: "alert" });
  error.hidden = true;
  const clearError = () => { error.hidden = true; error.textContent = ""; };

  const stepNodes = STEPS.map(() => el("div", { class: "wizard-step" }));
  const indicators = STEPS.map((name, i) => el("div", { class: "wizard-step-dot" },
    el("span", { class: "wizard-dot", "aria-hidden": "true" }, String(i + 1)),
    el("span", { class: "wizard-dot-label" }, name),
  ));

  function paint() {
    stepNodes.forEach((node, i) => { node.hidden = i !== step; });
    indicators.forEach((node, i) => {
      node.classList.toggle("is-active", i === step);
      node.classList.toggle("is-done", i < step);
    });
    back.hidden = step === 0;
    next.replaceChildren();
    next.append(icon(step === STEPS.length - 1 ? "check" : "send"),
      document.createTextNode(step === STEPS.length - 1 ? "Empezar" : "Siguiente"));
    clearError();
  }

  // Paso 1: cuenta del aula
  stepNodes[0].append(
    el("p", { class: "small muted" },
      "Usa la misma cuenta con la que entras al aula virtual. Se guarda solo en este equipo."),
    el("label", { class: "setup-label", for: "su-user" }, "Usuario de la ULEAM"),
    user,
    el("label", { class: "setup-label", for: "su-pass" }, "Contraseña"),
    pass,
    el("p", { class: "field-help" },
      "Al final se abrirá una ventana de Microsoft para iniciar sesión. Solo la primera vez."),
  );
  user.id = "su-user";
  pass.id = "su-pass";

  // Paso 2: asistente (opcional)
  stepNodes[1].append(
    el("div", { class: "wizard-optional" },
      el("span", { class: "pill pill--soft" }, "Opcional"),
      el("p", { class: "small muted" },
        "El Asistente necesita una API key propia. Funciona con OpenAI o cualquier proveedor compatible. Si no tienes una ahora, puedes añadirla después en Ajustes."),
    ),
    el("label", { class: "setup-label", for: "su-base" }, "URL del proveedor"),
    base,
    el("label", { class: "setup-label", for: "su-model" }, "Modelo"),
    model,
    el("label", { class: "setup-label", for: "su-key" }, "API key"),
    key,
    el("p", { class: "field-help" },
      "Se guarda cifrada con DPAPI en este equipo. Nunca se envía a otro sitio."),
    (() => {
      const skip = el("button", { class: "link-quiet", type: "button" }, "Omitir por ahora");
      skip.addEventListener("click", () => { step = 2; paint(); });
      return skip;
    })(),
  );
  base.id = "su-base";
  model.id = "su-model";
  key.id = "su-key";

  // Paso 3: navegador
  stepNodes[2].append(
    el("p", { class: "small muted" },
      "IAula abre este navegador para iniciar sesión en el aula y para NotebookLM. Brave, Chrome y Edge son compatibles."),
  );
  renderBrowserPicker(stepNodes[2], { buttonLabel: "Guardar navegador" });

  const back = el("button", { class: "glossy-btn glossy-btn--ghost", type: "button" }, "Atrás");
  const next = el("button", { class: "glossy-btn glossy-btn--lg", type: "button" });

  back.addEventListener("click", () => { if (step > 0) { step -= 1; paint(); } });

  next.addEventListener("click", async () => {
    clearError();
    if (step === 0) {
      if (!user.value.trim() || !pass.value) {
        error.textContent = "Completa usuario y contraseña del aula.";
        error.hidden = false;
        return;
      }
      next.classList.add("is-busy");
      try {
        await post("/api/setup", { username: user.value.trim(), password: pass.value });
        step = 1;
        paint();
      } catch (e) {
        error.textContent = e.message;
        error.hidden = false;
      } finally {
        next.classList.remove("is-busy");
      }
      return;
    }

    if (step === 1) {
      if (!key.value.trim()) { step = 2; paint(); return; }
      next.classList.add("is-busy");
      try {
        const res = await post("/api/settings/chat", {
          base_url: base.value.trim() || "https://api.openai.com/v1",
          model: model.value.trim() || "gpt-5.4-mini",
          api_key: key.value.trim(),
        });
        toast(`Asistente conectado en ${res.latency_ms} ms`, "ok");
        step = 2;
        paint();
      } catch (e) {
        error.textContent = e.message;
        error.hidden = false;
      } finally {
        next.classList.remove("is-busy");
      }
      return;
    }

    next.classList.add("is-busy");
    toast("Datos guardados. Conectando con la universidad…", "ok");
    setOnJobDone((ok) => { if (ok) location.reload(); });
    runAction("login", {}, "Conectando con el aula");
  });

  pass.addEventListener("keydown", (e) => {
    if (e.key === "Enter") { e.preventDefault(); next.click(); }
  });

  const card = el("section", { class: "panel glass reveal is-visible setup-card wizard" },
    el("div", { class: "panel-head" },
      el("h2", null, "Bienvenido a IAula Virtual"), icon("book", 18)),
    el("div", { class: "panel-body" },
      el("p", { class: "small muted wizard-lead" },
        "Tu aula de la ULEAM, de un vistazo. Todo se guarda solo en este equipo."),
      el("div", { class: "wizard-steps", "aria-label": "Pasos de configuración" }, ...indicators),
      ...stepNodes,
      error,
      el("div", { class: "wizard-nav" }, back, next),
    ),
  );

  root.append(card);
  paint();
  setTimeout(() => user.focus(), 140);
}
