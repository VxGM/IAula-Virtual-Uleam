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

function decoratePanels() {
  view.querySelectorAll(".panel").forEach((p) => {
    const head = p.querySelector(":scope > .panel-head");
    if (!head || head.querySelector(".win-btns")) return;
    const btns = el("div", { class: "win-btns" });
    const min = el("button", { class: "win-btn", title: "Minimizar panel", "aria-label": "Minimizar panel" });
    min.innerHTML = '<span class="wb-min"></span>';
    min.addEventListener("click", () => p.classList.toggle("collapsed"));
    btns.append(min);
    if (p.closest(".cols")) {
      const max = el("button", { class: "win-btn", title: "Expandir panel", "aria-label": "Expandir panel" });
      max.innerHTML = '<span class="wb-max"></span>';
      max.addEventListener("click", () => p.classList.toggle("wide"));
      btns.append(max);
    }
    head.append(btns);
  });
}

async function renderRoute() {
  const name = current();
  document.querySelectorAll(".task-btn").forEach((b) => b.classList.toggle("active", b.dataset.route === name));
  view.innerHTML = "";
  try {
    await routes[name].render(view);
  } catch (e) {
    view.innerHTML = "";
    view.append(el("div", { class: "panel glass" }, el("div", { class: "panel-body" }, `Error: ${e.message}`)));
  }
  decoratePanels();
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

async function refreshTray() {
  try {
    const s = await get("/api/summary");
    document.getElementById("tray-info").textContent =
      s.last_check ? `Últ. revisión: ${relTime(s.last_check.ts)}` : "Sin revisiones aún";
    document.querySelectorAll(".js-portal").forEach((a) => { a.href = s.portal_url; });
  } catch { /* server offline */ }
}

function tickClock() {
  const n = new Date();
  const hh = String(n.getHours()).padStart(2, "0") + ":" + String(n.getMinutes()).padStart(2, "0");
  const dd = String(n.getDate()).padStart(2, "0") + "/" + String(n.getMonth() + 1).padStart(2, "0") + "/" + n.getFullYear();
  document.getElementById("clock").innerHTML = `${hh}<br><small>${dd}</small>`;
}

function initTaskbar() {
  const startOrb = document.getElementById("start-orb");
  const menu = document.getElementById("start-menu");
  startOrb.addEventListener("click", (e) => {
    e.stopPropagation();
    menu.classList.toggle("open");
  });
  document.addEventListener("click", (e) => {
    if (!menu.classList.contains("open")) return;
    if (!menu.contains(e.target) && e.target !== startOrb) menu.classList.remove("open");
  });
  menu.addEventListener("click", (e) => {
    const routeBtn = e.target.closest("[data-route]");
    if (routeBtn) location.hash = `#${routeBtn.dataset.route}`;
    if (e.target.closest("a, button")) menu.classList.remove("open");
  });
  document.getElementById("sm-check").addEventListener("click", () => runAction("check", {}, "Revisando cursos"));
  tickClock();
  setInterval(tickClock, 20000);
}

initScene();
initTaskbar();

const checkBtn = document.getElementById("btn-check");
checkBtn.prepend(icon("refresh"));
checkBtn.addEventListener("click", () => runAction("check", {}, "Revisando cursos"));

setOnJobDone(() => {
  renderRoute();
  refreshStatus();
  refreshTray();
});

addEventListener("hashchange", renderRoute);
renderRoute();
refreshStatus();
refreshTray();
