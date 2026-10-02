import { el } from "./ui.js";

const rand = (min, max) => min + Math.random() * (max - min);

function seededRand(seed) {
  let s = seed;
  return () => {
    s = (s * 16807) % 2147483647;
    return (s - 1) / 2147483646;
  };
}

function spawnBubbles() {
  const box = document.getElementById("fx-bubbles");
  const count = window.innerWidth < 700 ? 8 : 14;
  for (let i = 0; i < count; i++) {
    const size = rand(10, 52);
    const b = el("span", { class: "bubble" });
    b.style.cssText = `left:${rand(2, 96)}%;width:${size}px;height:${size}px;` +
      `--dur:${rand(12, 24)}s;--delay:${rand(-24, 0)}s;--drift:${rand(-46, 46)}px;--op:${rand(0.35, 0.8)}`;
    box.append(b);
  }
}

function spawnBokeh() {
  const box = document.getElementById("fx-bokeh");
  for (let i = 0; i < 8; i++) {
    const size = rand(28, 110);
    const d = el("span", { class: "bokeh-dot" });
    d.style.cssText = `left:${rand(4, 92)}%;top:${rand(6, 88)}%;width:${size}px;height:${size}px;` +
      `--dur:${rand(7, 14)}s;--delay:${rand(-12, 0)}s;--dx:${rand(-26, 26)}px;--dy:${rand(-30, 14)}px`;
    box.append(d);
  }
}

function buildGrass() {
  const host = document.getElementById("fx-grass");
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 1440 140");
  svg.setAttribute("preserveAspectRatio", "none");
  const layer = (seed, height, baseY, fill, cls) => {
    const rnd = seededRand(seed);
    let d = "";
    for (let x = -10; x < 1450; x += 12 + rnd() * 14) {
      const h = height * (0.55 + rnd() * 0.75);
      const w = 9 + rnd() * 8;
      const lean = (rnd() - 0.5) * 14;
      d += `M${x} ${baseY} Q${x + w / 2 + lean} ${baseY - h * 0.7} ${x + w / 2 + lean} ${baseY - h} ` +
        `Q${x + w / 2} ${baseY - h * 0.55} ${x + w} ${baseY} Z `;
    }
    d += `M0 ${baseY - 2} H1440 V140 H0 Z`;
    const g = document.createElementNS("http://www.w3.org/2000/svg", "g");
    g.setAttribute("class", cls);
    const p = document.createElementNS("http://www.w3.org/2000/svg", "path");
    p.setAttribute("d", d);
    p.setAttribute("fill", fill);
    g.append(p);
    return g;
  };
  svg.append(layer(7, 46, 92, "#2c6b12", "grass-sway grass-sway--slow"));
  svg.append(layer(42, 64, 112, "#46a82a", "grass-sway"));
  host.append(svg);
}

export function initScene() {
  spawnBubbles();
  spawnBokeh();
  buildGrass();

  let mx = 0, my = 0, queued = false;
  document.addEventListener("pointermove", (e) => {
    mx = e.clientX;
    my = e.clientY;
    if (queued) return;
    queued = true;
    requestAnimationFrame(() => {
      queued = false;
      const root = document.documentElement;
      root.style.setProperty("--par-x", `${(mx / window.innerWidth - 0.5) * 36}px`);
      root.style.setProperty("--par-y", `${(my / window.innerHeight - 0.5) * 26}px`);
      root.style.setProperty("--mx", `${(mx / window.innerWidth) * 100}%`);
      root.style.setProperty("--my", `${(my / window.innerHeight) * 100}%`);
    });
  });

  document.addEventListener("pointerdown", (e) => {
    const r = el("div", { class: "ripple-ring" });
    r.style.left = `${e.clientX}px`;
    r.style.top = `${e.clientY}px`;
    document.body.append(r);
    r.addEventListener("animationend", () => r.remove(), { once: true });
  });

  const obs = new IntersectionObserver((entries) => {
    for (const en of entries) {
      if (en.isIntersecting) {
        en.target.classList.add("is-visible");
        obs.unobserve(en.target);
      }
    }
  }, { threshold: 0.12 });
  document.querySelectorAll(".reveal").forEach((n) => obs.observe(n));
  window.observeReveals = () => document.querySelectorAll(".reveal:not(.is-visible)").forEach((n) => obs.observe(n));
}
