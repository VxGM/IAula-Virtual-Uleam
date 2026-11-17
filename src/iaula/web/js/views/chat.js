import { get, post, postAudio, postBlob } from "../api.js";
import { el, icon, skeleton, toast } from "../ui.js";

const STORAGE_KEY = "iaula-chat-v1";
const VOICE_KEY = "iaula-chat-speak";
const BASE_SUGGESTIONS = [
  "¿Qué tareas tengo?",
  "¿Qué hay nuevo en mis cursos?",
  "Resume mi semana",
];

let history = load();
let replyAudio = null;
let speechSeq = 0;
let voiceBtn = null;

function markSpeaking(on) {
  if (voiceBtn) voiceBtn.classList.toggle("is-speaking", on);
}

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

function stopSpeech() {
  speechSeq += 1;
  markSpeaking(false);
  if (!replyAudio) return;
  try { replyAudio.pause(); } catch { /* ignore */ }
  URL.revokeObjectURL(replyAudio.src);
  replyAudio = null;
}

async function speak(text) {
  stopSpeech();
  markSpeaking(true);
  const seq = speechSeq;
  let url = "";
  try {
    const res = await postBlob("/api/voice/speak", { text });
    const blob = await res.blob();
    if (seq !== speechSeq) return;
    url = URL.createObjectURL(blob);
    const player = new Audio(url);
    replyAudio = player;
    player.addEventListener("ended", () => {
      URL.revokeObjectURL(url);
      if (replyAudio === player) {
        replyAudio = null;
        markSpeaking(false);
      }
    }, { once: true });
    await player.play();
  } catch (e) {
    if (url) URL.revokeObjectURL(url);
    replyAudio = null;
    markSpeaking(false);
    toast(`Voz: ${e.message}`, "err");
  }
}

function pickMime() {
  if (!window.MediaRecorder) return "";
  const options = ["audio/webm;codecs=opus", "audio/webm", "audio/ogg;codecs=opus", "audio/mp4"];
  return options.find((t) => MediaRecorder.isTypeSupported(t)) || "";
}

export async function render(root) {
  stopSpeech();

  const loading = el("section", { class: "panel glass reveal is-visible", "aria-busy": "true" },
    el("div", { class: "panel-head" }, el("h2", null, "Asistente")),
    el("div", { class: "panel-body" },
      el("div", { class: "chat-log" }, skeleton(4, 46)),
    ));
  root.append(loading);

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
  sendBtn.addEventListener("click", () => send());

  let speakOn = true;
  try { speakOn = localStorage.getItem(VOICE_KEY) !== "0"; } catch { /* ignore */ }

  const paintSpeak = () => {
    speakBtn.classList.toggle("is-on", speakOn);
    speakBtn.setAttribute("aria-pressed", speakOn ? "true" : "false");
    speakBtn.replaceChildren(icon(speakOn ? "sound" : "mute"), document.createTextNode("Voz"));
  };

  const speakBtn = el("button", {
    class: "glossy-btn glossy-btn--sm glossy-btn--ghost voice-btn",
    title: "Responder con voz cuando hablas por el micrófono",
    "aria-pressed": "false",
    style: "margin-left:auto",
  });
  speakBtn.addEventListener("click", () => {
    speakOn = !speakOn;
    try { localStorage.setItem(VOICE_KEY, speakOn ? "1" : "0"); } catch { /* ignore */ }
    paintSpeak();
    if (!speakOn) stopSpeech();
  });
  paintSpeak();
  voiceBtn = speakBtn;

  const micBtn = el("button", {
    class: "glossy-btn mic-btn",
    title: "Hablar (voz a texto)",
    "aria-label": "Hablar",
    "aria-pressed": "false",
    type: "button",
  }, icon("mic"));
  micBtn.addEventListener("click", toggleMic);

  const canRecord = !!(window.MediaRecorder && navigator.mediaDevices?.getUserMedia);
  if (!canRecord) micBtn.hidden = true;

  let busy = false;
  let recorder = null;
  let chunks = [];
  let stopTimer = 0;

  async function toggleMic() {
    if (recorder) { recorder.stop(); return; }
    if (busy) return;
    if (!canRecord) { toast("Este navegador no permite grabar audio", "err"); return; }
    let stream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch {
      toast("No pude acceder al micrófono: revisa el permiso", "err");
      return;
    }
    const mime = pickMime();
    try {
      recorder = new MediaRecorder(stream, mime ? { mimeType: mime } : undefined);
    } catch {
      stream.getTracks().forEach((t) => t.stop());
      toast("No pude iniciar la grabación", "err");
      return;
    }
    const type = recorder.mimeType || mime || "audio/webm";
    chunks = [];
    recorder.addEventListener("dataavailable", (e) => { if (e.data.size) chunks.push(e.data); });
    recorder.addEventListener("stop", async () => {
      clearTimeout(stopTimer);
      stream.getTracks().forEach((t) => t.stop());
      recorder = null;
      micBtn.classList.remove("is-recording");
      micBtn.setAttribute("aria-pressed", "false");
      micBtn.replaceChildren(icon("mic"));
      const blob = new Blob(chunks, { type });
      chunks = [];
      if (!blob.size) return;
      micBtn.classList.add("is-busy");
      try {
        const res = await postAudio("/api/voice/transcribe", blob);
        const { text } = await res.json();
        if (!text) { toast("No entendí el audio, intenta de nuevo", "info"); return; }
        input.value = text;
        input.dispatchEvent(new Event("input"));
        send(true);
      } catch (e) {
        toast(`Voz: ${e.message}`, "err");
      } finally {
        micBtn.classList.remove("is-busy");
      }
    });
    recorder.start();
    micBtn.classList.add("is-recording");
    micBtn.setAttribute("aria-pressed", "true");
    micBtn.replaceChildren(icon("stop"));
    stopTimer = setTimeout(() => { if (recorder) recorder.stop(); }, 60000);
  }

  async function send(byVoice = false) {
    const text = input.value.trim();
    if (!text || busy || !info.configured) return;
    stopSpeech();
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
      const reply = r.reply || "(sin respuesta)";
      history.push({ role: "assistant", content: reply });
      if (byVoice && speakOn) speak(reply);
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
    micBtn.disabled = true;
  }

  const head = el("div", { class: "panel-head" },
    el("h2", null, "Asistente"),
    info.configured
      ? el("span", { class: "pill pill--green" }, info.model)
      : el("span", { class: "pill" }, "sin API key"),
    speakBtn,
    (() => {
      const b = el("button", { class: "glossy-btn glossy-btn--sm glossy-btn--ghost" }, icon("refresh"), "Limpiar");
      b.addEventListener("click", () => { stopSpeech(); history = []; save(); paint(); });
      return b;
    })(),
  );

  const body = el("div", { class: "panel-body" }, log,
    el("div", { class: "chat-composer" }, micBtn, input, sendBtn));

  loading.remove();
  root.append(el("section", { class: "panel glass reveal" }, head, body));

  if (!info.configured) {
    const cta = el("button", { class: "glossy-btn glossy-btn--sm" }, icon("check"), "Configurar asistente");
    cta.addEventListener("click", () => { location.hash = "#ajustes"; });
    body.prepend(el("div", { class: "chat-setup" },
      el("p", null, "El Asistente está apagado: falta tu API key."),
      el("p", { class: "small muted" },
        "Funciona con OpenAI o cualquier proveedor compatible. La clave se guarda cifrada en este equipo."),
      el("div", { class: "settings-actions" }, cta),
    ));
  }
  paint();
}
