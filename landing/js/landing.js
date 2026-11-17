const CONFIG = {
  repo: "VxGM/IAula-Virtual-Uleam",
  fallbackVersion: "1.2.0",
  cacheKey: "iaula-release-v1",
  cacheTtl: 6 * 60 * 60 * 1000,
};

const RELEASES_PAGE = `https://github.com/${CONFIG.repo}/releases/latest`;

/* ---------- Escena: burbujas, bokeh y lente ---------- */
function seeded(seed) {
  let value = seed;
  return () => {
    value = (value * 9301 + 49297) % 233280;
    return value / 233280;
  };
}

function scene() {
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (reduce) return;

  const rnd = seeded(17);
  const bubbles = document.getElementById("bubbles");
  if (bubbles) {
    for (let i = 0; i < 18; i++) {
      const node = document.createElement("span");
      const size = 8 + Math.round(rnd() * 26);
      node.className = "bubble";
      node.style.left = `${Math.round(rnd() * 100)}%`;
      node.style.setProperty("--s", `${size}px`);
      node.style.setProperty("--d", `${14 + rnd() * 16}s`);
      node.style.setProperty("--delay", `${-rnd() * 24}s`);
      node.style.setProperty("--drift", `${Math.round((rnd() - 0.5) * 90)}px`);
      bubbles.append(node);
    }
  }

  const fx = document.getElementById("fx");
  if (fx) {
    for (let i = 0; i < 12; i++) {
      const dot = document.createElement("span");
      dot.className = "bokeh";
      dot.style.left = `${Math.round(rnd() * 100)}%`;
      dot.style.top = `${Math.round(rnd() * 80)}%`;
      dot.style.width = dot.style.height = `${4 + Math.round(rnd() * 10)}px`;
      dot.style.setProperty("--d", `${8 + rnd() * 12}s`);
      dot.style.setProperty("--delay", `${-rnd() * 10}s`);
      fx.append(dot);
    }
  }

  const lens = document.getElementById("lens");
  if (lens) {
    let pending = false;
    let x = 0;
    let y = 0;
    window.addEventListener("pointermove", (event) => {
      x = (event.clientX / window.innerWidth) * 100;
      y = (event.clientY / window.innerHeight) * 100;
      if (pending) return;
      pending = true;
      requestAnimationFrame(() => {
        pending = false;
        document.documentElement.style.setProperty("--mx", `${x}%`);
        document.documentElement.style.setProperty("--my", `${y}%`);
      });
    }, { passive: true });
  }
}

/* ---------- Revelado al entrar en pantalla ---------- */
function reveals() {
  if (!("IntersectionObserver" in window)) return;
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

  const targets = document.querySelectorAll(".section, .final-cta");
  targets.forEach((node) => node.classList.add("reveal"));
  const io = new IntersectionObserver((entries) => {
    for (const entry of entries) {
      if (!entry.isIntersecting) continue;
      entry.target.classList.add("in");
      io.unobserve(entry.target);
    }
  }, { threshold: 0.12 });
  targets.forEach((node) => io.observe(node));
}

/* ---------- Descarga de la última release ---------- */
function formatSize(bytes) {
  if (!bytes || bytes < 0) return "";
  const mb = bytes / (1024 * 1024);
  return `${mb.toFixed(0)} MB`;
}

function applyRelease(release) {
  const url = release.url || RELEASES_PAGE;
  document.querySelectorAll("[data-download]").forEach((link) => {
    link.href = url;
    link.removeAttribute("target");
  });
  if (release.version) {
    const version = String(release.version).replace(/^v/i, "");
    document.querySelectorAll("[data-version]").forEach((node) => { node.textContent = version; });
  }
  if (release.size) {
    document.querySelectorAll("[data-size]").forEach((node) => {
      node.textContent = `Instalador para Windows · ${formatSize(release.size)}`;
    });
  }
}

function readCache() {
  try {
    const data = JSON.parse(localStorage.getItem(CONFIG.cacheKey) || "null");
    if (!data || !data.at || Date.now() - data.at > CONFIG.cacheTtl) return null;
    return data;
  } catch {
    return null;
  }
}

async function resolveRelease() {
  const cached = readCache();
  if (cached) applyRelease(cached);

  try {
    const res = await fetch(`https://api.github.com/repos/${CONFIG.repo}/releases/latest`, {
      headers: { Accept: "application/vnd.github+json" },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    const assets = Array.isArray(data.assets) ? data.assets : [];
    const setup = assets.find((a) => /^IAulaVirtual-Setup-.*\.exe$/i.test(a.name))
      || assets.find((a) => /\.exe$/i.test(a.name));
    const release = {
      at: Date.now(),
      url: setup ? setup.browser_download_url : (data.html_url || RELEASES_PAGE),
      version: data.tag_name || data.name || CONFIG.fallbackVersion,
      size: setup ? setup.size : 0,
    };
    applyRelease(release);
    try { localStorage.setItem(CONFIG.cacheKey, JSON.stringify(release)); } catch { /* ignore */ }
  } catch {
    applyRelease({ url: RELEASES_PAGE, version: CONFIG.fallbackVersion });
  }
}

/* ---------- Copiar comandos ---------- */
function copyButtons() {
  document.querySelectorAll("[data-copy]").forEach((button) => {
    button.addEventListener("click", async () => {
      const target = document.querySelector(button.dataset.copy);
      if (!target) return;
      const text = target.innerText;
      let copied = false;
      try {
        await navigator.clipboard.writeText(text);
        copied = true;
      } catch {
        const area = document.createElement("textarea");
        area.value = text;
        area.setAttribute("readonly", "");
        area.style.position = "fixed";
        area.style.opacity = "0";
        document.body.append(area);
        area.select();
        copied = document.execCommand("copy");
        area.remove();
      }
      button.textContent = copied ? "Copiado" : "No se pudo copiar";
      setTimeout(() => { button.textContent = "Copiar"; }, 1800);
    });
  });
}

/* ---------- Menú móvil ---------- */
function mobileMenu() {
  document.querySelectorAll(".mobile-menu nav a").forEach((link) => {
    link.addEventListener("click", () => {
      const menu = link.closest(".mobile-menu");
      if (menu) menu.open = false;
    });
  });
  document.addEventListener("click", (event) => {
    document.querySelectorAll("details.mobile-menu[open]").forEach((menu) => {
      if (!menu.contains(event.target)) menu.open = false;
    });
  });
  document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape") return;
    document.querySelectorAll("details.mobile-menu[open]").forEach((menu) => { menu.open = false; });
  });
}

function init() {
  scene();
  reveals();
  copyButtons();
  mobileMenu();
  const year = document.getElementById("year");
  if (year) year.textContent = String(new Date().getFullYear());
  resolveRelease();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init, { once: true });
} else {
  init();
}
