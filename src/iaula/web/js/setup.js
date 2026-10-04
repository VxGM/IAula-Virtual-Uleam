import { post } from "./api.js";
import { el, icon, toast } from "./ui.js";
import { runAction, setOnJobDone } from "./actions.js";

export function renderSetup(root) {
  const user = el("input", { class: "chat-input", type: "text", placeholder: "tucorreo@live.uleam.edu.ec", autocomplete: "username" });
  const pass = el("input", { class: "chat-input", type: "password", placeholder: "Tu contraseña", autocomplete: "current-password" });
  const key = el("input", { class: "chat-input", type: "password", placeholder: "Déjalo vacío para usar la incluida", autocomplete: "off" });
  const btn = el("button", { class: "glossy-btn glossy-btn--lg" }, icon("check"), "Guardar y conectar");
  const err = el("p", { class: "small", style: "color:#8c2f24;margin-top:10px" });

  async function save() {
    err.textContent = "";
    if (!user.value.trim() || !pass.value) {
      err.textContent = "Completa usuario y contraseña del aula.";
      return;
    }
    btn.classList.add("is-busy");
    try {
      await post("/api/setup", {
        username: user.value.trim(),
        password: pass.value,
        openai_key: key.value.trim(),
      });
      toast("Datos guardados. Conectando con la universidad…", "ok");
      setOnJobDone((ok) => { if (ok) location.reload(); });
      runAction("login", {}, "Conectando con el aula");
    } catch (e) {
      err.textContent = e.message;
      btn.classList.remove("is-busy");
    }
  }

  btn.addEventListener("click", save);
  pass.addEventListener("keydown", (e) => { if (e.key === "Enter") save(); });

  root.append(el("section", { class: "panel glass reveal is-visible setup-card" },
    el("div", { class: "panel-head" }, el("h2", null, "Bienvenido a IAula Virtual"), icon("book", 18)),
    el("div", { class: "panel-body" },
      el("p", { class: "small muted", style: "margin-bottom:14px" },
        "Tu aula de la ULEAM, de un vistazo. Los datos se guardan solo en este equipo."),
      el("label", { class: "setup-label" }, "Usuario del aula (ULEAM)"),
      user,
      el("label", { class: "setup-label" }, "Contraseña"),
      pass,
      el("label", { class: "setup-label" }, "OpenAI (opcional)"),
      key,
      el("div", { style: "margin-top:18px;display:flex;align-items:center;gap:10px" }, btn),
      err,
      el("p", { class: "small muted", style: "margin-top:14px" },
        "Al guardar se abrirá una ventana de Microsoft para iniciar sesión (solo la primera vez)."),
    )));
  setTimeout(() => user.focus(), 120);
}
