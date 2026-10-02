import { initScene } from "./motion.js";
import { get } from "./api.js";
import { el, icon, relTime } from "./ui.js";
import { runAction, setOnJobDone } from "./actions.js";
import * as overview from "./views/overview.js";
import * as courses from "./views/courses.js";
import * as tasks from "./views/tasks.js";
import * as notebooklm from "./views/notebooklm.js";
import * as chat from "./views/chat.js";

const routes = { resumen: overview, cursos: courses, tareas: tasks, notebooklm: notebooklm, asistente: chat };
const view = document.getElementById("view");

function current() {
  const name = location.hash.replace("#", "") || "resumen";
  return routes[name] ? name : "resumen";
}

async function renderRoute() {
  const name = current();
  document.querySelectorAll(".nav-btn").forEach((b) => b.classList.toggle("active", b.dataset.route === name));
  view.innerHTML = "";
  try {
    await routes[name].render(view);
  } catch (e) {
    view.innerHTML = "";
    view.append(el("div", { class: "panel glass" }, el("div", { class: "panel-body" }, `Error: ${e.message}`)));
  }
  if (window.observeReveals) window.observeReveals();
}

function setDot(id, ok, text) {
  const n = document.getElementById(id);
  n.className = "status status--onpanel " + (ok ? "status--ok" : "status--err");
  n.querySelector(".st-txt").textContent = text;
}

async function refreshStatus() {
  try {
    const s = await get("/api/sessions");
    setDot("st-portal", s.portal.ok, s.portal.ok ? "aula" : "aula ✕");
    setDot("st-nlm", s.notebooklm.ok, s.notebooklm.ok ? "NLM" : "NLM ✕");
  } catch { /* server offline */ }
}

async function refreshFooter() {
  try {
    const s = await get("/api/summary");
    document.getElementById("foot-right").textContent =
      s.last_check ? `Última revisión: ${relTime(s.last_check.ts)}` : "Sin revisiones aún";
  } catch { /* server offline */ }
}

initScene();
const checkBtn = document.getElementById("btn-check");
checkBtn.prepend(icon("refresh"));
checkBtn.addEventListener("click", () => runAction("check", {}, "Revisando cursos"));

setOnJobDone(() => {
  renderRoute();
  refreshStatus();
  refreshFooter();
});

addEventListener("hashchange", renderRoute);
renderRoute();
refreshStatus();
refreshFooter();
