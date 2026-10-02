import { el } from "./ui.js";
import { jobStatus } from "./api.js";

let win = null, logBox = null, titleEl = null, stateEl = null, timeEl = null;

function build() {
  logBox = el("div", { class: "job-log", role: "log" });
  titleEl = el("span", { class: "job-title" }, "Trabajo");
  stateEl = el("span", null, "en curso");
  timeEl = el("span", null, "0s");
  const close = el("button", { class: "job-close", "aria-label": "Cerrar ventana" }, "✕");
  close.addEventListener("click", () => win.classList.remove("open"));
  const bar = el("div", { class: "job-titlebar" }, titleEl, close);
  const foot = el("div", { class: "job-foot" }, timeEl, stateEl);
  win = el("div", { class: "job-window glass-strong" }, bar, logBox, foot);
  document.body.append(win);

  bar.addEventListener("pointerdown", (e) => {
    const sx = e.clientX, sy = e.clientY;
    let base = [0, 0];
    try { base = JSON.parse(win.dataset.pos || "[0,0]"); } catch { /* keep */ }
    bar.setPointerCapture(e.pointerId);
    const move = (ev) => {
      const nx = base[0] + (ev.clientX - sx);
      const ny = base[1] + (ev.clientY - sy);
      win.style.translate = `${nx}px ${ny}px`;
      win.dataset.pos = JSON.stringify([nx, ny]);
    };
    const up = () => {
      bar.removeEventListener("pointermove", move);
      bar.removeEventListener("pointerup", up);
    };
    bar.addEventListener("pointermove", move);
    bar.addEventListener("pointerup", up);
  });
}

export function watchJob(jobId, title, onDone) {
  if (!win) build();
  win.classList.add("open");
  win.dataset.state = "running";
  titleEl.textContent = title;
  logBox.textContent = "";
  stateEl.textContent = "en curso";
  const t0 = Date.now();
  let seen = 0;
  const timer = setInterval(async () => {
    let st;
    try {
      st = await jobStatus(jobId);
    } catch (e) {
      st = { state: "error", error: e.message, log: [] };
    }
    while (seen < (st.log || []).length) logBox.textContent += st.log[seen++] + "\n";
    logBox.scrollTop = logBox.scrollHeight;
    timeEl.textContent = `${Math.round((Date.now() - t0) / 1000)}s`;
    if (st.state === "running") return;
    clearInterval(timer);
    win.dataset.state = st.state;
    stateEl.textContent = st.state === "done" ? "completado ✓" : "error";
    if (st.state === "error" && st.error) logBox.textContent += `\nERROR: ${st.error}\n`;
    logBox.scrollTop = logBox.scrollHeight;
    if (onDone) onDone(st.state === "done", st);
  }, 900);
}
