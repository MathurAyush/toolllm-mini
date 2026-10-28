// ToolAgent site: renders every page from data/content.js and
// data/results.json, and runs the shared effects. No dependencies.
(function () {
  "use strict";

  const C = window.SITE_CONTENT;
  let R = window.SITE_RESULTS || null;
  const page = document.body.dataset.page;
  const reduceQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
  const reduce = () => reduceQuery.matches;
  const finePointer = window.matchMedia("(hover: hover) and (pointer: fine)").matches;

  // ---------------------------------------------------------------- helpers

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
  const ESC = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ESC[c]);
  const pad = (n) => String(n).padStart(2, "0");
  const TBD = '<span class="tbd" title="Not measured yet">TBD</span>';
  const PROV = '<span class="prov" title="Measured before the fix for made-up tool results">provisional</span>';

  function get(path) {
    return path.split(".").reduce((o, k) => (o == null ? undefined : o[k]), R);
  }

  function fmt(v, opts = {}) {
    if (v == null || Number.isNaN(v)) return null;
    if (opts.percent) return Math.round(v * 100) + "%";
    if (opts.decimals != null) return v.toFixed(opts.decimals);
    if (typeof v === "number") return Number.isInteger(v) ? v.toLocaleString("en-US") : v.toFixed(2);
    return String(v);
  }

  // Escapes text, then fills {result.path} tokens (TBD badge when missing),
  // turns a literal "TBD" into a badge and [[word]] into an accent span.
  function fill(text) {
    return esc(text)
      .replace(/\bTBD\b/g, TBD)
      .replace(/\{([\w.]+)\}/g, (_, path) => {
        const v = fmt(get(path));
        return v == null ? TBD : esc(v);
      })
      .replace(/\[\[(.+?)\]\]/g, '<span class="accent">$1</span>');
  }

  const ICONS = {
    search: '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
    call: '<path d="M8 9l-4 3 4 3"/><path d="M16 9l4 3-4 3"/><path d="M13.5 5l-3 14"/>',
    tree: '<circle cx="12" cy="4.5" r="2"/><circle cx="5.5" cy="19" r="2"/><circle cx="12" cy="19" r="2"/><circle cx="18.5" cy="19" r="2"/><path d="M12 6.5V17M12 10.5c-6.5 0-6.5 3-6.5 6.5M12 10.5c6.5 0 6.5 3 6.5 6.5"/>',
    grid: '<rect x="3.5" y="3.5" width="7" height="7" rx="1.5"/><rect x="13.5" y="3.5" width="7" height="7" rx="1.5"/><rect x="3.5" y="13.5" width="7" height="7" rx="1.5"/><rect x="13.5" y="13.5" width="7" height="7" rx="1.5"/>',
    check: '<circle cx="12" cy="12" r="9"/><path d="m8 12.5 2.7 2.7L16.5 9"/>',
    chart: '<path d="M4 20V10M10 20V4M16 20v-7M21 20H3"/>',
    arrowRight: '<path d="M5 12h14M13 6l6 6-6 6"/>',
    arrowLeft: '<path d="M19 12H5M11 6l-6 6 6 6"/>',
    up: '<path d="M12 19V5M6 11l6-6 6 6"/>',
    down: '<path d="M12 5v14M6 13l6 6 6-6"/>',
    play: '<path d="M7 4.5v15l12-7.5z"/>',
    pause: '<path d="M8 5v14M16 5v14"/>',
    restart: '<path d="M4 12a8 8 0 1 0 2.4-5.7"/><path d="M4 4v4.5h4.5"/>',
    x: '<circle cx="12" cy="12" r="9"/><path d="m9 9 6 6M15 9l-6 6"/>',
    pin: '<path d="M12 21s-6.5-6-6.5-11a6.5 6.5 0 0 1 13 0c0 5-6.5 11-6.5 11z"/><circle cx="12" cy="10" r="2.3"/>',
    cloud: '<path d="M7 18h10a4 4 0 0 0 .5-8 5.5 5.5 0 0 0-10.6 1.5A3.3 3.3 0 0 0 7 18z"/>',
    rocket: '<path d="M12 15l-3-3c1.5-4.5 4.5-7.5 10-8-.5 5.5-3.5 8.5-7 11z"/><path d="M9 12l-3.5.5L4 15l4 1M12 15l-.5 3.5L9 20l-1-4"/>',
    coin: '<circle cx="12" cy="12" r="8.5"/><path d="M14.5 9.2c-.5-.8-1.4-1.2-2.5-1.2-1.6 0-2.7.9-2.7 2s1 1.6 2.7 2 2.7.9 2.7 2.1-1.2 2-2.7 2c-1.2 0-2.1-.5-2.6-1.3M12 6.5v11"/>',
    smile: '<circle cx="12" cy="12" r="8.5"/><path d="M8.5 14c.9 1.3 2.1 2 3.5 2s2.6-.7 3.5-2M9 9.5h.01M15 9.5h.01"/>',
    calendar: '<rect x="3.5" y="5" width="17" height="15" rx="2"/><path d="M3.5 10h17M8 3v4M16 3v4"/>',
    book: '<path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v15H6.5A2.5 2.5 0 0 0 4 20.5z"/><path d="M4 20.5A2.5 2.5 0 0 1 6.5 18H20v3H6.5"/>',
    cup: '<path d="M5 8h12v5a6 6 0 0 1-12 0z"/><path d="M17 9.5h1.5a2.5 2.5 0 0 1 0 5H17M8 2.5V5M11 2.5V5M14 2.5V5"/>',
    paw: '<circle cx="7" cy="9" r="1.8"/><circle cx="11" cy="6" r="1.8"/><circle cx="15" cy="6.5" r="1.8"/><circle cx="18" cy="10" r="1.8"/><path d="M8 17.5c0-2.8 2-5 4-5s4.5 2 4.5 4.5c0 2-1.5 2.5-3 2.5-1 0-1.5-.5-2.5-.5S9.5 20 8.8 19.6A2 2 0 0 1 8 17.5z"/>',
    user: '<circle cx="12" cy="8" r="4"/><path d="M4 20.5c1.2-3.8 4.3-5.5 8-5.5s6.8 1.7 8 5.5"/>',
    type: '<path d="M5 6.5v-2h14v2M12 4.5v15M9 19.5h6"/>',
    calc: '<rect x="5" y="3" width="14" height="18" rx="2"/><path d="M8.5 7h7M8.5 12h.01M12 12h.01M15.5 12h.01M8.5 16h.01M12 16h.01M15.5 16h.01"/>',
    news: '<rect x="3.5" y="4.5" width="17" height="15" rx="2"/><path d="M7 9h10M7 12.5h10M7 16h6"/>',
    wave: '<path d="M3 12h3l2-5 3 10 3-8 2 3h5"/>',
    clock: '<circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/>',
    help: '<circle cx="12" cy="12" r="8.5"/><path d="M9.6 9.5a2.5 2.5 0 0 1 4.8.8c0 1.7-2.4 2.2-2.4 3.7M12 17h.01"/>',
    cap: '<path d="M2.5 9.5 12 5l9.5 4.5L12 14z"/><path d="M6.5 11.5V16c1.5 1.3 3.5 2 5.5 2s4-.7 5.5-2v-4.5"/>',
    game: '<rect x="2.5" y="7" width="19" height="11" rx="4"/><path d="M7 11v3M5.5 12.5h3M15.5 12h.01M18 13.5h.01"/>',
    drop: '<path d="M12 3.5s-6 6.5-6 10.5a6 6 0 0 0 12 0c0-4-6-10.5-6-10.5z"/>',
    ruler: '<path d="M3.5 15.5 15.5 3.5l5 5-12 12z"/><path d="M7 12l2 2M10 9l2 2M13 6l2 2"/>',
    dot: '<circle cx="12" cy="12" r="3"/>',
  };

  const CATEGORY_ICONS = {
    geo: "pin", weather: "cloud", space: "rocket", finance: "coin", entertainment: "smile",
    calendar: "calendar", books: "book", food: "cup", animals: "paw", people: "user",
    knowledge: "search", words: "type", tech: "call", math: "calc", news: "news",
    science: "wave", clock: "clock", trivia: "help", education: "cap", games: "game",
    design: "drop", utility: "ruler",
  };

  const icon = (name) =>
    `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICONS[name] || ICONS.dot}</svg>`;

  let markId = 0;
  function brandMark() {
    const id = "bm" + ++markId;
    return `<svg class="brand-mark" viewBox="0 0 32 32" aria-hidden="true"><defs><linearGradient id="${id}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#0fb5c9"/><stop offset="1" stop-color="#2ee87a"/></linearGradient></defs><path d="M16 2.5 28 9.5v13L16 29.5 4 22.5v-13z" fill="none" stroke="url(#${id})" stroke-width="2"/><path d="M16 11l-5.5 9h11z" fill="none" stroke="#19e6b4" stroke-width="1.4" opacity=".6"/><circle cx="16" cy="11" r="2.6" fill="#19e6b4"/><circle cx="10.5" cy="20" r="2.6" fill="#19e6b4"/><circle cx="21.5" cy="20" r="2.6" fill="#19e6b4"/></svg>`;
  }

  // Calls `cb(el)` once, the first time `el` scrolls into view.
  function onVisible(el, cb, threshold = 0.2) {
    if (!("IntersectionObserver" in window)) return cb(el);
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting) {
            io.disconnect();
            cb(el);
          }
        });
      },
      { threshold }
    );
    io.observe(el);
  }

  function debounce(fn, ms) {
    let t;
    return (...args) => {
      clearTimeout(t);
      t = setTimeout(() => fn(...args), ms);
    };
  }

  // ---------------------------------------------------------------- chrome

  function renderChrome() {
    const links = C.nav
      .map((l) => {
        const current = l.href === `${page}.html` || (page === "home" && l.href === "index.html");
        return `<li><a href="${l.href}"${current ? ' aria-current="page"' : ""}>${esc(l.label)}</a></li>`;
      })
      .join("");
    document.body.insertAdjacentHTML(
      "afterbegin",
      `<a class="skip-link" href="#main">Skip to content</a>
      <div class="bg" aria-hidden="true"><div class="bg-blob"></div></div>
      <div class="cursor-glow" aria-hidden="true"></div>
      <div class="scroll-progress" aria-hidden="true"></div>
      <header class="nav">
        <a class="brand" href="index.html" aria-label="${esc(C.brand)} home">${brandMark()}<span>${esc(C.brand)}</span></a>
        <ul class="nav-links" id="nav-links">${links}</ul>
        <a class="btn btn-primary btn-sm nav-demo magnetic" href="${C.demo.href}">${icon("play")}${esc(C.demo.label)}</a>
        <button class="menu-btn" type="button" aria-expanded="false" aria-controls="nav-links" aria-label="Open menu"><span></span></button>
      </header>`
    );

    const team = C.team
      .map((m) => `<li class="team-line">${esc(m.name)} <span>${esc(m.id)}</span></li>`)
      .join("");
    const pages = C.nav.map((l) => `<li><a href="${l.href}">${esc(l.label)}</a></li>`).join("");
    document.body.insertAdjacentHTML(
      "beforeend",
      `<footer class="footer">
        <div class="wrap">
          <div class="footer-grid">
            <div>
              <a class="brand" href="index.html">${brandMark()}<span>${esc(C.brand)}</span></a>
              <p style="margin-top:14px;max-width:42ch">${esc(C.footer.note)}</p>
            </div>
            <div><h4>Team</h4><ul>${team}</ul></div>
            <div><h4>Pages</h4><ul>${pages}<li><a href="${C.repo}" rel="noopener">Repository</a></li></ul></div>
          </div>
          <div class="footer-bottom">${esc(C.brand)} · ${esc(C.tagline)} · ${C.team.map((m) => esc(m.name)).join(", ")}</div>
        </div>
      </footer>`
    );
  }

  function initNav() {
    const btn = $(".menu-btn");
    const list = $("#nav-links");
    const setOpen = (open) => {
      list.classList.toggle("open", open);
      btn.setAttribute("aria-expanded", String(open));
      btn.setAttribute("aria-label", open ? "Close menu" : "Open menu");
    };
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      setOpen(!list.classList.contains("open"));
    });
    list.addEventListener("click", (e) => {
      if (e.target.closest("a")) setOpen(false);
    });
    document.addEventListener("click", (e) => {
      if (!e.target.closest(".nav")) setOpen(false);
    });
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") setOpen(false);
    });
  }

  // ---------------------------------------------------------------- effects

  function initScrollProgress() {
    const bar = $(".scroll-progress");
    let queued = false;
    const update = () => {
      queued = false;
      const max = document.documentElement.scrollHeight - window.innerHeight;
      bar.style.transform = `scaleX(${max > 0 ? Math.min(1, window.scrollY / max) : 0})`;
    };
    window.addEventListener(
      "scroll",
      () => {
        if (!queued) {
          queued = true;
          requestAnimationFrame(update);
        }
      },
      { passive: true }
    );
    window.addEventListener("resize", update);
    update();
  }

  function initReveal(root = document) {
    const targets = $$("[data-reveal], .h-line, .chart, .split-bar", root).filter((el) => !el.classList.contains("in"));
    if (reduce() || !("IntersectionObserver" in window)) {
      targets.forEach((el) => el.classList.add("in"));
      return;
    }
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting) {
            e.target.classList.add("in");
            io.unobserve(e.target);
          }
        });
      },
      { threshold: 0.15, rootMargin: "0px 0px -6% 0px" }
    );
    targets.forEach((el) => io.observe(el));
  }

  // Animated number counters: <span data-count="tools.total" data-format="pct">.
  function initCounters(root = document) {
    $$("[data-count]", root).forEach((el) => {
      const value = get(el.dataset.count);
      const opts = { percent: el.dataset.format === "pct", decimals: el.dataset.decimals ? +el.dataset.decimals : null };
      if (typeof value !== "number") {
        el.innerHTML = value == null ? TBD : esc(value);
        return;
      }
      const final = fmt(value, opts);
      if (reduce()) {
        el.textContent = final;
        return;
      }
      el.textContent = fmt(0, opts);
      onVisible(el, () => {
        const start = performance.now();
        const dur = 1400;
        const step = (now) => {
          const t = Math.min(1, (now - start) / dur);
          const eased = 1 - Math.pow(1 - t, 3);
          const v = value * eased;
          el.textContent = t < 1 ? fmt(opts.percent || opts.decimals != null ? v : Math.round(v), opts) : final;
          if (t < 1) requestAnimationFrame(step);
        };
        requestAnimationFrame(step);
      }, 0.4);
    });
  }

  function initCursorGlow() {
    const glow = $(".cursor-glow");
    if (!finePointer || reduce()) return;
    let x = window.innerWidth / 2, y = window.innerHeight / 2, tx = x, ty = y, running = false;
    const loop = () => {
      x += (tx - x) * 0.12;
      y += (ty - y) * 0.12;
      glow.style.transform = `translate3d(${x}px, ${y}px, 0)`;
      if (Math.abs(tx - x) > 0.5 || Math.abs(ty - y) > 0.5) requestAnimationFrame(loop);
      else running = false;
    };
    window.addEventListener("pointermove", (e) => {
      tx = e.clientX;
      ty = e.clientY;
      glow.classList.add("on");
      if (!running) {
        running = true;
        requestAnimationFrame(loop);
      }
    }, { passive: true });
    document.addEventListener("pointerleave", () => glow.classList.remove("on"));
  }

  function initTilt(root = document) {
    if (!finePointer || reduce()) return;
    $$(".tilt", root).forEach((el) => {
      el.addEventListener("pointermove", (e) => {
        const r = el.getBoundingClientRect();
        const px = (e.clientX - r.left) / r.width - 0.5;
        const py = (e.clientY - r.top) / r.height - 0.5;
        el.classList.add("tilting");
        el.style.transform = `perspective(900px) rotateX(${(-py * 6).toFixed(2)}deg) rotateY(${(px * 8).toFixed(2)}deg) translateY(-3px)`;
      });
      el.addEventListener("pointerleave", () => {
        el.classList.remove("tilting");
        el.style.transform = "";
      });
    });
  }

  function initMagnetic(root = document) {
    if (!finePointer || reduce()) return;
    $$(".magnetic", root).forEach((el) => {
      el.addEventListener("pointermove", (e) => {
        const r = el.getBoundingClientRect();
        const dx = e.clientX - (r.left + r.width / 2);
        const dy = e.clientY - (r.top + r.height / 2);
        el.style.transform = `translate(${(dx * 0.22).toFixed(1)}px, ${(dy * 0.3).toFixed(1)}px)`;
      });
      el.addEventListener("pointerleave", () => {
        el.style.transform = "";
      });
    });
  }

  // Page transitions: cross-document View Transitions where the browser
  // supports them (CSS @view-transition), otherwise a short fade.
  function initPageTransitions() {
    const native = "PageRevealEvent" in window && location.protocol !== "file:";
    if (native || reduce()) return;
    document.body.classList.add("no-vt");
    document.addEventListener("click", (e) => {
      const a = e.target.closest("a[href]");
      if (!a || e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      if (a.target && a.target !== "_self") return;
      const url = new URL(a.href, location.href);
      if (url.origin !== location.origin || !/\.html$/.test(url.pathname)) return;
      if (url.pathname === location.pathname) return; // same page, maybe a hash
      e.preventDefault();
      document.body.classList.add("leaving");
      setTimeout(() => (location.href = a.href), 220);
    });
    window.addEventListener("pageshow", (e) => {
      if (e.persisted) document.body.classList.remove("leaving");
    });
  }

  // Replaces an image that fails to load with a clearly named placeholder.
  function initImageFallbacks(root = document) {
    $$("img[data-fallback]", root).forEach((img) => {
      const swap = () => {
        const box = document.createElement("div");
        box.className = "screen-placeholder";
        box.textContent = `Placeholder: ${img.getAttribute("src")}`;
        img.replaceWith(box);
      };
      if (img.complete && img.naturalWidth === 0) swap();
      else img.addEventListener("error", swap, { once: true });
    });
  }

  function initEffects(root = document) {
    initReveal(root);
    initCounters(root);
    initTilt(root);
    initMagnetic(root);
    initImageFallbacks(root);
  }

  // ---------------------------------------------------------------- pages

  const PAGES = {};

  // @pages

  // ---------------------------------------------------------------- boot

  async function loadResults() {
    if (R) return;
    try {
      const res = await fetch("data/results.json", { cache: "no-cache" });
      if (res.ok) R = await res.json();
    } catch (err) {
      R = null; // opened from disk without results.js: values show as TBD
    }
  }

  async function boot() {
    await loadResults();
    renderChrome();
    initNav();
    const main = $("#main");
    if (PAGES[page]) PAGES[page](main);
    initEffects(document);
    initScrollProgress();
    initCursorGlow();
    initPageTransitions();
    if (location.hash) {
      const target = document.getElementById(location.hash.slice(1));
      if (target) requestAnimationFrame(() => target.scrollIntoView());
    }
  }

  boot();
})();
