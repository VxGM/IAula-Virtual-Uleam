import { get, post } from "../api.js";
import { el, icon, toast } from "../ui.js";

const STORAGE_KEY = "iaula-chat-v1";
const BASE_SUGGESTIONS = [
  "¿Qué tareas tengo?",
  "¿Qué hay nuevo en mis cursos?",
  "Resume mi semana",
];

let history = load();

function load() {
  try { return JSON.parse(localStorage.getItem(STORAGE_KEY)) || []; } catch { return []; }
}

function save() {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(history.slice(-40))); } catch { /* ignore */ }
}

function mdLite(text) {
  const esc = String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
  return esc
    .replace(/^#{1,4}\s+(.+)$/gm, "<strong>$1</strong>")
    .replace(/\*\*([^*\n]+)\*\*/g, "<strong>$1</strong>")
    .replace(/`([^`\n]+)`/g, "<code>$1</code>")
    .replace(/^\s*[-*]\s+/gm, "• ");
}

function bubble(role, text) {
  const body = el("div", { class: "msg-body" });
  body.innerHTML = mdLite(text);
  return el("div", { class: `msg msg--${role === "user" ? "user" : "bot"}` },
    el("div", { class: "msg-avatar", "aria-hidden": "true" }),
    body,
  );
}

export async function render(root) {
  let info = { configured: false, model: "" };
  try { info = await get("/api/chat/info"); } catch { /* ignore */ }

  let suggestions = BASE_SUGGESTIONS;
  try {
    const s = await get("/api/summary");
    const dynamic = (s.upcoming_tasks || []).slice(0, 2)
      .map((t) => `Explícame la tarea: ${t.name}`);
    suggestions = [...BASE_SUGGESTIONS, ...dynamic].slice(0, 5);
  } catch { /* ignore */ }

  const log = el("div", { class: "chat-log" });
  const typed = el("div", { class: "msg msg--bot typing" },
    el("div", { class: "msg-avatar", "aria-hidden": "true" }),
    el("div", { class: "msg-body" },
      el("span", { class: "dot" }), el("span", { class: "dot" }), el("span", { class: "dot" })),
  );
  typed.hidden = true;

  const scrollDown = () => { log.scrollTop = log.scrollHeight; };

  const paint = () => {
    log.innerHTML = "";
    if (!history.length) {
      log.append(el("div", { class: "chat-empty" },
        el("p", null, "Pregúntame por tus cursos, tareas o materiales."),
        el("div", { class: "chat-suggest" }, ...suggestions.map((s) => {
          const b = el("button", { class: "glossy-btn glossy-btn--sm glossy-btn--ghost" }, s);
          b.addEventListener("click", () => { input.value = s; send(); });
          return b;
        })),
      ));
    } else {
      for (const m of history) log.append(bubble(m.role, m.content));
    }
    log.append(typed);
    scrollDown();
  };

  const input = el("textarea", { class: "chat-input", rows: "1", placeholder: "Escribe tu pregunta…", "aria-label": "Mensaje" });
  input.addEventListener("input", () => {
    input.style.height = "auto";
    input.style.height = Math.min(input.scrollHeight, 120) + "px";
  });
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
  });

  const sendBtn = el("button", { class: "glossy-btn" }, icon("send"), "Enviar");
  sendBtn.addEventListener("click", send);

  let busy = false;

  async function send() {
    const text = input.value.trim();
    if (!text || busy || !info.configured) return;
    busy = true;
    sendBtn.classList.add("is-busy");
    input.value = "";
    input.style.height = "auto";
    history.push({ role: "user", content: text });
    save();
    paint();
    typed.hidden = false;
    scrollDown();
    try {
      const r = await post("/api/chat", { messages: history });
      history.push({ role: "assistant", content: r.reply || "(sin respuesta)" });
    } catch (e) {
      toast(`Asistente: ${e.message}`, "err");
      history.push({ role: "assistant", content: `Error: ${e.message}` });
    } finally {
      busy = false;
      sendBtn.classList.remove("is-busy");
      save();
      typed.hidden = true;
      paint();
    }
  }

  if (!info.configured) {
    input.disabled = true;
    sendBtn.disabled = true;
  }

  const head = el("div", { class: "panel-head" },
    el("h2", null, "Asistente"),
    info.configured
      ? el("span", { class: "pill pill--green" }, info.model)
      : el("span", { class: "pill" }, "sin API key"),
    (() => {
      const b = el("button", { class: "glossy-btn glossy-btn--sm glossy-btn--ghost", style: "margin-left:auto" }, icon("refresh"), "Limpiar");
      b.addEventListener("click", () => { history = []; save(); paint(); });
      return b;
    })(),
  );

  const body = el("div", { class: "panel-body" }, log,
    el("div", { class: "chat-composer" }, input, sendBtn));

  root.append(el("section", { class: "panel glass reveal" }, head, body));

  if (!info.configured) {
    body.prepend(el("div", { class: "chat-setup" },
      el("p", null, "Falta la API key de OpenAI. Añádela en config.local.toml:"),
      el("div", { class: "cmd" }, '[chat] api_key = "sk-..."'),
    ));
  }
  paint();
}
