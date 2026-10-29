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
    branch: '<circle cx="6" cy="5" r="2"/><circle cx="6" cy="19" r="2"/><circle cx="18" cy="8" r="2"/><path d="M6 7v10M18 10c0 4-6 3-11.2 7.4"/>',
    gear: '<circle cx="12" cy="12" r="3"/><path d="M12 2.5v3M12 18.5v3M2.5 12h3M18.5 12h3M5.3 5.3l2.1 2.1M16.6 16.6l2.1 2.1M5.3 18.7l2.1-2.1M16.6 7.4l2.1-2.1"/>',
    stop: '<rect x="6" y="6" width="12" height="12" rx="2"/>',
    history: '<path d="M4 12a8 8 0 1 0 2.4-5.7"/><path d="M4 4v4.5h4.5"/><path d="M12 8v4l3 2"/>',
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
        <a class="btn btn-primary btn-sm nav-demo magnetic" href="${C.demo.href}"${page === "demo" ? ' aria-current="page"' : ""}>${icon("play")}${esc(C.demo.label)}</a>
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

  // Splits a title into word spans for the one-by-one reveal, keeping the
  // [[accent]] words.
  function splitTitle(text) {
    let i = 0;
    return text
      .split(/(\[\[.+?\]\])/)
      .filter(Boolean)
      .map((part) => {
        const accent = part.startsWith("[[");
        const words = (accent ? part.slice(2, -2) : part).split(/\s+/).filter(Boolean);
        return words.map((w) => `<span class="w${accent ? " accent" : ""}" style="--i:${i++}">${esc(w)}</span>`).join(" ");
      })
      .join(" ");
  }

  const screenImg = (s) => `<img src="${s.src}" alt="${esc(s.alt)}" data-fallback loading="eager" decoding="async">`;

  // Hero background: drifting points joined by faint lines, pulled slightly
  // towards the pointer. Pauses when the tab is hidden or the hero is off
  // screen; draws one still frame under reduced motion.
  function heroCanvas(canvas) {
    const ctx = canvas.getContext("2d");
    let w = 0, h = 0, dpr = 1, points = [], visible = true, raf = 0;
    const mouse = { x: -9999, y: -9999, tx: -9999, ty: -9999 };
    const LINK = 130;

    function resize() {
      const r = canvas.getBoundingClientRect();
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      w = r.width;
      h = r.height;
      canvas.width = Math.round(w * dpr);
      canvas.height = Math.round(h * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      const n = Math.max(28, Math.min(90, Math.round((w * h) / 15000)));
      points = Array.from({ length: n }, () => ({
        x: Math.random() * w,
        y: Math.random() * h,
        vx: (Math.random() - 0.5) * 0.35,
        vy: (Math.random() - 0.5) * 0.35,
        r: Math.random() * 1.4 + 0.8,
      }));
      if (reduce()) draw();
    }

    function draw() {
      ctx.clearRect(0, 0, w, h);
      mouse.x += (mouse.tx - mouse.x) * 0.05;
      mouse.y += (mouse.ty - mouse.y) * 0.05;
      for (const p of points) {
        if (!reduce()) {
          const dx = mouse.x - p.x, dy = mouse.y - p.y;
          const d2 = dx * dx + dy * dy;
          if (d2 < 200 * 200) {
            p.vx += dx * 0.000012;
            p.vy += dy * 0.000012;
          }
          p.vx *= 0.995;
          p.vy *= 0.995;
          const speed = Math.hypot(p.vx, p.vy);
          if (speed < 0.08) {
            p.vx += (Math.random() - 0.5) * 0.04;
            p.vy += (Math.random() - 0.5) * 0.04;
          }
          p.x += p.vx;
          p.y += p.vy;
          if (p.x < -10) p.x = w + 10;
          if (p.x > w + 10) p.x = -10;
          if (p.y < -10) p.y = h + 10;
          if (p.y > h + 10) p.y = -10;
        }
      }
      for (let i = 0; i < points.length; i++) {
        const a = points[i];
        for (let j = i + 1; j < points.length; j++) {
          const b = points[j];
          const d = Math.hypot(a.x - b.x, a.y - b.y);
          if (d < LINK) {
            ctx.strokeStyle = `rgba(25, 230, 180, ${(1 - d / LINK) * 0.28})`;
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.moveTo(a.x, a.y);
            ctx.lineTo(b.x, b.y);
            ctx.stroke();
          }
        }
        const md = Math.hypot(a.x - mouse.x, a.y - mouse.y);
        if (md < 180) {
          ctx.strokeStyle = `rgba(46, 232, 122, ${(1 - md / 180) * 0.35})`;
          ctx.beginPath();
          ctx.moveTo(a.x, a.y);
          ctx.lineTo(mouse.x, mouse.y);
          ctx.stroke();
        }
      }
      for (const p of points) {
        ctx.fillStyle = "rgba(160, 255, 225, 0.75)";
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fill();
      }
    }

    function loop() {
      draw();
      raf = requestAnimationFrame(loop);
    }
    function start() {
      if (!raf && visible && !document.hidden && !reduce()) raf = requestAnimationFrame(loop);
    }
    function stop() {
      cancelAnimationFrame(raf);
      raf = 0;
    }

    resize();
    window.addEventListener("resize", debounce(resize, 200));
    document.addEventListener("visibilitychange", () => (document.hidden ? stop() : start()));
    if ("IntersectionObserver" in window) {
      new IntersectionObserver(([e]) => {
        visible = e.isIntersecting;
        visible ? start() : stop();
      }).observe(canvas);
    }
    if (finePointer) {
      canvas.parentElement.addEventListener("pointermove", (e) => {
        const r = canvas.getBoundingClientRect();
        mouse.tx = e.clientX - r.left;
        mouse.ty = e.clientY - r.top;
        if (mouse.x < -999) {
          mouse.x = mouse.tx;
          mouse.y = mouse.ty;
        }
      });
      canvas.parentElement.addEventListener("pointerleave", () => {
        mouse.tx = mouse.ty = -9999;
      });
    }
    start();
  }

  // Device mockups drift at different speeds while the hero scrolls away.
  function initParallax() {
    const layers = $$("[data-parallax]");
    if (!layers.length || reduce()) return;
    let queued = false;
    const update = () => {
      queued = false;
      const y = window.scrollY;
      if (y > window.innerHeight * 1.5) return;
      layers.forEach((el) => {
        el.style.transform = `translate3d(0, ${(-y * parseFloat(el.dataset.parallax)).toFixed(1)}px, 0)`;
      });
    };
    window.addEventListener("scroll", () => {
      if (!queued) {
        queued = true;
        requestAnimationFrame(update);
      }
    }, { passive: true });
  }

  function wrapText(text, maxChars) {
    const words = text.split(" ");
    const lines = [];
    let line = "";
    for (const word of words) {
      if (line && (line + " " + word).length > maxChars) {
        lines.push(line);
        line = word;
      } else line = line ? line + " " + word : word;
    }
    if (line) lines.push(line);
    return lines;
  }

  // Pipeline diagram: steps along an SVG path, glowing dots flowing along
  // it, and each step lighting up as the lead dot passes.
  function buildPipeline(el, steps) {
    let raf = 0, visible = false, nodes = [], path = null, dots = [], total = 0, positions = [];
    const DURATION = 9000;
    let t0 = performance.now();

    function render() {
      const W = Math.max(280, el.clientWidth - 2);
      const horizontal = W >= 760;
      const n = steps.length;
      let pts, H, labels;
      if (horizontal) {
        const padX = 64, y = 56;
        const gap = (W - padX * 2) / (n - 1);
        pts = steps.map((_, i) => [padX + i * gap, y]);
        H = 170;
        const maxChars = Math.max(12, Math.floor(gap / 7.4));
        labels = steps.map((s, i) => {
          const [x] = pts[i];
          const detail = wrapText(s.detail, maxChars)
            .map((l, k) => `<tspan x="${x}" dy="${k ? 16 : 0}">${esc(l)}</tspan>`)
            .join("");
          return `<text class="label" x="${x}" y="${y + 50}" text-anchor="middle">${esc(s.label)}</text>
            <text class="detail" x="${x}" y="${y + 72}" text-anchor="middle">${detail}</text>`;
        });
      } else {
        const x = 30, top = 30, gap = 86;
        pts = steps.map((_, i) => [x, top + i * gap]);
        H = top * 2 + gap * (n - 1);
        const maxChars = Math.max(16, Math.floor((W - 80) / 7.4));
        labels = steps.map((s, i) => {
          const [, y] = pts[i];
          const detail = wrapText(s.detail, maxChars)
            .map((l, k) => `<tspan x="${x + 40}" dy="${k ? 16 : 0}">${esc(l)}</tspan>`)
            .join("");
          return `<text class="label" x="${x + 40}" y="${y - 4}">${esc(s.label)}</text>
            <text class="detail" x="${x + 40}" y="${y + 16}">${detail}</text>`;
        });
      }
      positions = pts;
      const d = "M" + pts.map((p) => p.join(" ")).join(" L");
      el.innerHTML = `<svg viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" role="img" aria-label="Pipeline: ${steps.map((s) => esc(s.label)).join(", ")}">
        <defs><linearGradient id="pipeGrad" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#0fb5c9"/><stop offset="1" stop-color="#2ee87a"/></linearGradient></defs>
        <path class="pipe-track" d="${d}"/>
        <path class="pipe-glow" d="${d}"/>
        ${pts.map((p, i) => `<g class="pipe-node" data-i="${i}">
            <circle class="halo" cx="${p[0]}" cy="${p[1]}" r="20"/>
            <circle class="ring" cx="${p[0]}" cy="${p[1]}" r="20"/>
            <text class="num" x="${p[0]}" y="${p[1]}">${i + 1}</text>
          </g>`).join("")}
        ${labels.join("")}
        <circle class="pipe-dot" r="5" cx="0" cy="0"/>
        <circle class="pipe-dot" r="3.5" cx="0" cy="0" opacity="0.7"/>
        <circle class="pipe-dot" r="2.5" cx="0" cy="0" opacity="0.5"/>
      </svg>`;
      path = $(".pipe-track", el);
      total = path.getTotalLength();
      nodes = $$(".pipe-node", el);
      dots = $$(".pipe-dot", el);
      if (reduce()) {
        nodes.forEach((nd) => nd.classList.add("lit"));
        dots.forEach((dot) => (dot.style.display = "none"));
      } else frame(performance.now());
    }

    function frame(now) {
      const base = ((now - t0) % DURATION) / DURATION;
      dots.forEach((dot, k) => {
        const p = path.getPointAtLength(((base - k * 0.025 + 1) % 1) * total);
        dot.setAttribute("transform", `translate(${p.x.toFixed(1)} ${p.y.toFixed(1)})`);
      });
      const lead = path.getPointAtLength(base * total);
      nodes.forEach((nd, i) => {
        const [x, y] = positions[i];
        nd.classList.toggle("lit", Math.hypot(lead.x - x, lead.y - y) < 46);
      });
    }

    function loop(now) {
      frame(now);
      raf = requestAnimationFrame(loop);
    }

    render();
    window.addEventListener("resize", debounce(render, 200));
    if (reduce()) return;
    const start = () => {
      if (!raf && visible && !document.hidden) raf = requestAnimationFrame(loop);
    };
    const stop = () => {
      cancelAnimationFrame(raf);
      raf = 0;
    };
    document.addEventListener("visibilitychange", () => (document.hidden ? stop() : start()));
    new IntersectionObserver(([e]) => {
      visible = e.isIntersecting;
      if (visible) t0 = performance.now() - 0;
      visible ? start() : stop();
    }).observe(el);
  }

  PAGES.home = (main) => {
    const H = C.home;
    main.innerHTML = `
      <section class="hero">
        <canvas class="hero-canvas" aria-hidden="true"></canvas>
        <div class="wrap hero-grid">
          <div>
            <span class="kicker hero-fade" style="--d:0s">${fill(H.eyebrow)}</span>
            <h1>${splitTitle(H.title)}</h1>
            <p class="lead hero-fade" style="--d:0.85s">${fill(H.subtitle)}</p>
            <div class="btn-row hero-fade" style="--d:1.05s">
              ${H.ctas.map((c) => `<a class="btn ${c.primary ? "btn-primary" : ""} magnetic" href="${c.href}">${esc(c.label)}${c.primary ? icon("play") : icon("arrowRight")}</a>`).join("")}
            </div>
          </div>
          <div class="devices hero-fade" style="--d:0.5s" aria-label="Screenshots of the app">
            <div class="device-layer tablet-layer" data-parallax="0.05"><div class="float"><div class="tablet"><div class="screen">${screenImg(H.screens.tablet)}</div></div></div></div>
            <div class="device-layer phone-layer" data-parallax="0.12"><div class="float"><div class="phone"><div class="screen">${screenImg(H.screens.phone)}</div></div></div></div>
          </div>
        </div>
      </section>

      <section class="section" id="capabilities">
        <div class="wrap">
          <div class="section-head center"><h2 class="h-line" data-reveal>${fill(H.capabilitiesTitle)}</h2></div>
          <div class="grid grid-3">
            ${H.capabilities.map((c, i) => `<article class="card tilt" data-reveal style="--i:${i % 3}">
                <div class="icon-badge">${icon(c.icon)}</div>
                <h3>${fill(c.title)}</h3>
                <p>${fill(c.text)}</p>
              </article>`).join("")}
          </div>
        </div>
      </section>

      <section class="section" id="pipeline">
        <div class="wrap">
          <div class="section-head center"><h2 class="h-line" data-reveal>${fill(H.pipelineTitle)}</h2></div>
          <div class="card pipeline" data-reveal><div class="pipeline-svg"></div></div>
        </div>
      </section>

      <section class="section" id="parts">
        <div class="wrap">
          <div class="section-head center"><h2 class="h-line" data-reveal>${fill(H.partsTitle)}</h2></div>
          <div class="grid grid-2">
            ${H.parts.map((p, i) => `<a class="card part-card tilt" href="${p.href}" data-reveal style="--i:${i}">
                <span class="num-big">0${i + 1}</span>
                <span class="kicker">${fill(p.kicker)}</span>
                <h3>${fill(p.title)}</h3>
                <p>${fill(p.text)}</p>
                <span class="more">${esc(p.cta)}${icon("arrowRight")}</span>
              </a>`).join("")}
          </div>
        </div>
      </section>

      <section class="section" style="padding-top:0">
        <div class="wrap">
          <div class="card cta-band" data-reveal>
            <h2>${fill(H.closing.title)}</h2>
            <p class="lead">${fill(H.closing.text)}</p>
            <div class="btn-row">
              ${H.ctas.map((c) => `<a class="btn ${c.primary ? "btn-primary" : ""} magnetic" href="${c.href}">${esc(c.label)}</a>`).join("")}
            </div>
          </div>
        </div>
      </section>`;

    heroCanvas($(".hero-canvas", main));
    buildPipeline($(".pipeline-svg", main), H.pipeline);
    initParallax();
  };

  // ---------------------------------------------------------------- charts

  // Grouped SVG bar chart sized to its container, with optional confidence
  // interval whiskers. A null value is drawn as a dashed TBD bar. Bars grow
  // (scaleY) when the chart scrolls into view.
  function barChart(el, spec) {
    const render = () => {
      const W = Math.max(260, Math.floor(el.clientWidth));
      const H = spec.height || Math.round(Math.min(360, Math.max(250, W * 0.52)));
      const m = { l: 44, r: 8, t: 28, b: 48 };
      const pw = W - m.l - m.r;
      const ph = H - m.t - m.b;
      const ns = spec.series.length;
      const all = spec.values.flat().filter((v) => v != null);
      const ciTops = (spec.ci || []).flat().filter(Boolean).map((c) => c[1]);
      const max = spec.max || niceMax(Math.max(1, ...all, ...ciTops));
      const y = (v) => m.t + ph - (v / max) * ph;
      const label = (v) => fmt(v, { percent: spec.percent, decimals: spec.decimals });
      const parts = [];

      for (let k = 0; k <= 4; k++) {
        const v = (max * k) / 4;
        parts.push(`<line class="axis" x1="${m.l}" x2="${W - m.r}" y1="${y(v)}" y2="${y(v)}"/>`);
        parts.push(`<text class="tick" x="${m.l - 8}" y="${y(v) + 4}" text-anchor="end">${esc(spec.percent ? Math.round(v * 100) + "%" : fmt(v, { decimals: spec.decimals != null ? 2 : null }))}</text>`);
      }

      const gw = pw / spec.groups.length;
      const gap = 5;
      const bw = Math.min(46, (gw * 0.76 - (ns - 1) * gap) / ns);
      const inner = bw * ns + (ns - 1) * gap;
      const showLabels = bw >= 26;
      spec.groups.forEach((g, gi) => {
        const x0 = m.l + gi * gw + (gw - inner) / 2;
        // A group with no values at all gets one TBD label, not one per bar.
        const groupTbd = spec.values[gi].every((v) => v == null);
        if (groupTbd) parts.push(`<text class="tbd-text" x="${m.l + gi * gw + gw / 2}" y="${m.t + ph * 0.55 - 8}">TBD</text>`);
        spec.series.forEach((s, si) => {
          const x = x0 + si * (bw + gap);
          const v = spec.values[gi][si];
          const d = ((gi * ns + si) * 0.07).toFixed(2);
          const cx = x + bw / 2;
          if (v == null) {
            const top = m.t + ph * 0.55;
            parts.push(`<rect class="tbd-bar" x="${x}" y="${top}" width="${bw}" height="${ph * 0.45}" rx="4"><title>${esc(s.name)}: not measured yet</title></rect>`);
            if (!groupTbd) parts.push(`<text class="tbd-text" x="${cx}" y="${top - 8}">TBD</text>`);
            return;
          }
          const ci = spec.ci && spec.ci[gi] && spec.ci[gi][si];
          parts.push(`<rect class="bar" style="--d:${d}" x="${x}" y="${y(v)}" width="${bw}" height="${Math.max(0, m.t + ph - y(v))}" rx="4" fill="${s.color}"><title>${esc(`${g}, ${s.name}: ${label(v)}${ci ? ` (95% CI ${label(ci[0])} to ${label(ci[1])})` : ""}`)}</title></rect>`);
          let top = y(v);
          if (ci) {
            const cap = Math.min(8, bw / 3);
            parts.push(`<g class="ci" style="--d:${d}"><line x1="${cx}" x2="${cx}" y1="${y(ci[0])}" y2="${y(ci[1])}"/><line x1="${cx - cap}" x2="${cx + cap}" y1="${y(ci[0])}" y2="${y(ci[0])}"/><line x1="${cx - cap}" x2="${cx + cap}" y1="${y(ci[1])}" y2="${y(ci[1])}"/></g>`);
            top = Math.min(top, y(ci[1]));
          }
          if (showLabels) parts.push(`<text class="vlabel" style="--d:${d}" x="${cx}" y="${top - 7}">${esc(label(v))}</text>`);
        });
        const lines = wrapText(g, Math.max(6, Math.floor(gw / 7.6)));
        // Shrink the label when its longest word is wider than the group.
        const longest = Math.max(...lines.map((l) => l.length));
        const fs = Math.max(8, Math.min(13, (gw - 10) / (longest * 0.7)));
        parts.push(`<text class="glabel" x="${m.l + gi * gw + gw / 2}" y="${H - m.b + 20}" style="font-size:${fs.toFixed(1)}px">${lines
          .slice(0, 2)
          .map((l, k) => `<tspan x="${m.l + gi * gw + gw / 2}" dy="${k ? 15 : 0}">${esc(l)}</tspan>`)
          .join("")}</text>`);
      });

      el.innerHTML = `<svg viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" role="img" aria-label="${esc(spec.ariaLabel || "Bar chart")}">${parts.join("")}</svg>`;
    };
    render();
    let lastW = el.clientWidth;
    window.addEventListener("resize", debounce(() => {
      if (Math.abs(el.clientWidth - lastW) > 4) {
        lastW = el.clientWidth;
        render();
      }
    }, 200));
  }

  function niceMax(v) {
    const p = Math.pow(10, Math.floor(Math.log10(v)));
    const n = v / p;
    return (n <= 1 ? 1 : n <= 2 ? 2 : n <= 2.5 ? 2.5 : n <= 5 ? 5 : 10) * p;
  }

  const legend = (series) =>
    `<div class="chart-legend">${series.map((s) => `<span><i style="background:${s.color}"></i>${esc(s.name)}</span>`).join("")}</div>`;

  const AGENT_SERIES = [
    { name: "ReAct", color: "#19e6b4" },
    { name: "DFSDT", color: "#7c9cff" },
  ];

  // Pass-rate chart spec from a pass_rates() block of results.json.
  function passRateSpec(block, withCi) {
    const groups = block ? block.groups : ["easy", "medium", "hard", "overall"].map((c) => ({ complexity: c, n: null }));
    return {
      groups: groups.map((g) => `${g.complexity[0].toUpperCase()}${g.complexity.slice(1)}${g.n ? ` (${g.n})` : ""}`),
      series: AGENT_SERIES,
      values: groups.map((g) => (block ? [g.react.rate, g.dfsdt.rate] : [null, null])),
      ci: withCi && block ? groups.map((g) => [[g.react.ci_low, g.react.ci_high], [g.dfsdt.ci_low, g.dfsdt.ci_high]]) : null,
      percent: true,
      max: 1,
      ariaLabel: "Pass rate by difficulty for ReAct and DFSDT",
    };
  }

  // ---------------------------------------------------------------- slides

  // Each visual returns the HTML for the right-hand side of a slide; an
  // optional init runs once the HTML is in the page.
  const VISUALS = {
    problem: (s) => {
      const c = s.compare;
      return `<div class="card chat tilt">
        <div class="bubble q" data-reveal style="--i:2">${esc(c.question)}</div>
        <div class="answer-pair">
          <div class="answer bad" data-reveal style="--i:4"><div class="tag">${icon("x")}${esc(c.guess.label)}</div><div class="val">${esc(c.guess.text)}</div></div>
          <div class="answer good" data-reveal style="--i:6"><div class="tag">${icon("check")}${esc(c.tool.label)}</div><div class="val">${esc(c.tool.text)}</div></div>
        </div>
        <p class="note" data-reveal style="--i:7">${fill(c.note)}</p>
      </div>`;
    },

    existing: (s) => {
      const block = (b, i) => `<article class="card tilt" data-reveal style="--i:${i + 2}">
          <h3>${fill(b.title)}</h3>
          <dl class="def-list">${b.items.map((it) => `<div><dt>${esc(it.k)}</dt><dd>${fill(it.v)}</dd></div>`).join("")}</dl>
        </article>`;
      return `<div class="grid grid-2">${block(s.paper, 0)}${block(s.baseline, 1)}</div>`;
    },

    baselineChart: (s) => `<div class="card chart-card">
        <div class="card-title-row"><h3>Pass rate by difficulty</h3>${PROV}</div>
        <div class="chart" data-chart="baseline"></div>
        ${legend(AGENT_SERIES)}
        <p class="note">${fill(s.chartNote)}</p>
      </div>`,
  };

  const VISUAL_INIT = {
    baselineChart: (el) => barChart($(".chart", el), passRateSpec(R && R.baseline, false)),
  };

  function renderDeck(main, slides, links) {
    const first = slides[0].n;
    const last = slides[slides.length - 1].n;
    main.innerHTML = slides
      .map((s) => {
        const stack = !s.bullets;
        let foot = "";
        if (s.n === last && links.next) {
          foot = `<div class="slide-foot" data-reveal style="--i:6"><a class="btn btn-primary magnetic" href="${links.next.href}">${esc(links.next.label)}${icon("arrowRight")}</a></div>`;
        } else if (s.n === first && links.prev) {
          foot = `<div class="slide-foot" data-reveal style="--i:6"><a class="btn magnetic" href="${links.prev.href}">${icon("arrowLeft")}${esc(links.prev.label)}</a></div>`;
        }
        return `<section class="slide" id="slide-${s.n}" data-slide="${s.n}" aria-label="Slide ${s.n} of ${C.slideTotal}">
          <div class="wrap">
            <div class="slide-grid${stack ? " stack" : ""}">
              <div class="slide-text">
                <span class="kicker" data-reveal>${esc(s.kicker)} <span class="slide-num">${pad(s.n)}</span></span>
                <h2 class="h-line" data-reveal style="--i:1">${fill(s.title)}</h2>
                ${s.bullets ? `<ul class="bullets">${s.bullets.map((b, k) => `<li data-reveal style="--i:${k + 2}">${fill(b)}</li>`).join("")}</ul>` : ""}
                ${stack ? "" : foot}
              </div>
              <div class="visual" data-visual="${s.visual}">${VISUALS[s.visual](s)}</div>
              ${stack ? foot : ""}
            </div>
          </div>
          ${s.n === first ? `<div class="slide-hint" aria-hidden="true"><span class="key">↑</span><span class="key">↓</span> or <span class="key">Space</span> to move</div>` : ""}
        </section>`;
      })
      .join("");
    $$(".visual", main).forEach((el) => {
      const init = VISUAL_INIT[el.dataset.visual];
      if (init) init(el, slides.find((s) => s.visual === el.dataset.visual));
    });
    initDeck($$(".slide", main), links);
  }

  // Slide navigation: arrow keys, Page Up/Down and Space move one slide;
  // past either end of the page it continues on the other slide page.
  function initDeck(slides, links) {
    document.documentElement.classList.add("slides-page");
    document.body.insertAdjacentHTML(
      "beforeend",
      `<nav class="slide-hud" aria-label="Slide controls">
        <button class="hud-btn" type="button" data-dir="-1" aria-label="Previous slide">${icon("up")}</button>
        <span class="slide-count" aria-live="polite"></span>
        <span class="slide-bar" aria-hidden="true"><i></i></span>
        <button class="hud-btn" type="button" data-dir="1" aria-label="Next slide">${icon("down")}</button>
      </nav>`
    );
    const count = $(".slide-count");
    const bar = $(".slide-bar i");
    let current = 0;

    const update = () => {
      let idx = 0;
      slides.forEach((s, i) => {
        if (s.getBoundingClientRect().top <= window.innerHeight * 0.45) idx = i;
      });
      current = idx;
      const n = +slides[idx].dataset.slide;
      count.innerHTML = `<b>${pad(n)}</b> / ${C.slideTotal}`;
      bar.style.transform = `scaleX(${n / C.slideTotal})`;
    };

    const go = (dir) => {
      const target = current + dir;
      if (target < 0) {
        if (links.prev) location.href = links.prev.href;
        return;
      }
      if (target >= slides.length) {
        if (links.next) location.href = links.next.href;
        else $(".footer").scrollIntoView({ behavior: reduce() ? "auto" : "smooth" });
        return;
      }
      slides[target].scrollIntoView({ behavior: reduce() ? "auto" : "smooth" });
    };

    let queued = false;
    window.addEventListener("scroll", () => {
      if (!queued) {
        queued = true;
        requestAnimationFrame(() => {
          queued = false;
          update();
        });
      }
    }, { passive: true });
    window.addEventListener("resize", update);

    $$(".hud-btn").forEach((b) => b.addEventListener("click", () => go(+b.dataset.dir)));

    document.addEventListener("keydown", (e) => {
      if (e.defaultPrevented || e.altKey || e.ctrlKey || e.metaKey) return;
      const t = e.target instanceof Element ? e.target : document.body;
      if (t.closest("input, textarea, select, [contenteditable]")) return;
      const onControl = t.closest("button, a, video, summary");
      let dir = 0;
      if (e.key === "ArrowDown" || e.key === "PageDown") dir = 1;
      else if (e.key === "ArrowUp" || e.key === "PageUp") dir = -1;
      else if (e.key === " " && !onControl) dir = e.shiftKey ? -1 : 1;
      else if (e.key === "Home") dir = -current;
      else if (e.key === "End") dir = slides.length - 1 - current;
      if (!dir && e.key !== "Home" && e.key !== "End") return;
      e.preventDefault();
      if (dir) go(dir);
    });

    update();
  }

  const callText = (t) => t.replace(/^Action:\s*/, "");
  const clip = (t, n) => (t.length > n ? t.slice(0, n - 1) + "…" : t);

  Object.assign(VISUALS, {
    functionCalling: () => {
      const trace = R && R.traces && R.traces[0];
      if (!trace) return `<div class="card"><h3>Recorded trace ${TBD}</h3></div>`;
      const rows = [];
      const events = trace.events;
      let calls = 0;
      events.forEach((e, i) => {
        if (e.kind !== "call" || calls >= 2) return;
        calls++;
        rows.push(`<div class="flow-msg from-model"><div class="msg"><small>Model requests</small>${esc(callText(e.text))}</div></div>`);
        const obs = events[i + 1];
        if (obs && obs.kind === "observation") {
          rows.push(`<div class="flow-msg from-tool"><div class="msg"><small>Our code runs it, real result</small>${esc(clip(obs.text, 110))}</div></div>`);
        }
      });
      const answer = events.find((e) => e.kind === "answer");
      if (answer) rows.push(`<div class="flow-msg answer-msg"><div class="msg"><small>Final answer</small>${esc(answer.text)}</div></div>`);
      return `<div class="card flow">
        <div class="flow-lanes"><span>Model</span><span>Our code</span><span>Tool API</span></div>
        <div class="bubble q" style="justify-self:start;max-width:100%">${esc(trace.instruction)}</div>
        ${rows.join("")}
        <p class="note">From a recorded run, <code>${esc(trace.source)}</code>.</p>
      </div>`;
    },

    toolMarquee: () => {
      const tools = (R && R.tools && R.tools.tools) || [];
      const half = Math.ceil(tools.length / 2);
      const chip = (t) => `<span class="chip">${icon(CATEGORY_ICONS[t.category])}${esc(t.name)}</span>`;
      const row = (list, rev) =>
        `<div class="marquee-row${rev ? " rev" : ""}">${list.map(chip).join("")}<span aria-hidden="true" style="display:contents">${list.map(chip).join("")}</span></div>`;
      const cats = R && R.tools ? Object.entries(R.tools.categories).slice(0, 10) : [];
      return `<div class="card">
        <div class="tool-count"><span class="from">${R && R.tools ? R.tools.phase1 : TBD}</span><span class="arrow">→</span><span data-count="tools.total"></span><small>tools</small></div>
        ${tools.length ? `<div class="marquee" data-overflow-ok>${row(tools.slice(0, half))}${row(tools.slice(half), true)}</div>` : TBD}
        <div class="cat-list">${cats.map(([c, n]) => `<span>${esc(c)} · ${n}</span>`).join("")}</div>
      </div>`;
    },

    benchmark: () => {
      const b = R && R.benchmark;
      const facts = b ? b.fact_tasks : null;
      const live = b ? b.live_value_tasks : null;
      const share = (v) => (b && b.total ? (100 * v) / b.total : 0);
      const examples = b ? b.examples.filter((e) => e.difficulty === "hard" || /live/.test(e.check)).slice(0, 2) : [];
      return `<div class="card">
        <div class="stat-row">
          ${["easy", "medium", "hard"].map((d) => `<div class="stat"><span class="n" data-count="benchmark.by_difficulty.${d}"></span><span class="l">${d}</span></div>`).join("")}
        </div>
        <div class="split-bar" role="img" aria-label="${facts} tasks checked by facts, ${live} by live values">
          <i style="width:${share(facts)}%"></i><i style="width:${share(live)}%"></i>
        </div>
        <div class="legend">
          <span><i style="background:var(--accent)"></i>${facts == null ? TBD : facts} with expected facts</span>
          <span><i style="background:var(--amber)"></i>${live == null ? TBD : live} with a live-value rule</span>
        </div>
        ${examples.map((e) => `<div class="example"><q>${esc(e.instruction)}</q><div class="meta"><span class="pill diff">${esc(e.difficulty)}</span>${e.tools.map((t) => `<span class="pill">${esc(t)}</span>`).join("")}<span>check: ${esc(e.check)}</span></div></div>`).join("")}
      </div>`;
    },

    retrieverChart: () => `<div class="card chart-card">
        <div class="card-title-row"><h3>Retrievers on the generated tasks</h3></div>
        <div class="chart"></div>
        ${legend(RETRIEVER_SERIES)}
        <p class="note">${R && R.retriever ? `${R.retriever.n_tasks} tasks, ${R.retriever.pool_size} tools, from <code>${esc(R.retriever.source)}</code>. ` : ""}Dashed bars are not built yet.</p>
      </div>`,

    dfsdtTree: (s) => `<div class="card tree">
        <div class="tree-svg"></div>
        <div class="tree-controls">
          <span class="tree-status" aria-live="polite"></span>
          <button class="btn btn-sm magnetic tree-replay" type="button">${icon("restart")}Replay</button>
        </div>
        <p class="note">${fill(s.treeNote)}</p>
      </div>`,

    ciChart: () => `<div class="grid" style="gap:16px">
        <div class="card chart-card">
          <div class="card-title-row"><h3>Phase 1, with 95% intervals</h3>${PROV}</div>
          <div class="chart" data-chart="ci"></div>
          ${legend(AGENT_SERIES)}
        </div>
        <div class="card chart-card">
          <div class="card-title-row"><h3>Verified run on the new benchmark</h3>${R && R.verified ? "" : TBD}</div>
          <div class="chart" data-chart="verified"></div>
        </div>
      </div>`,

    conclusion: (s) => `<div class="grid grid-3">${s.columns
      .map((c, i) => `<article class="card col-card tilt ${["done", "limits", "next"][i]}" data-reveal style="--i:${i + 2}">
          <h3>${icon(["check", "x", "arrowRight"][i])}${esc(c.title)}</h3>
          <ul>${c.items.map((it) => `<li>${fill(it)}</li>`).join("")}</ul>
        </article>`)
      .join("")}</div>`,
  });

  const RETRIEVER_SERIES = [
    { name: "Top-1", color: "#19e6b4" },
    { name: "Recall@3", color: "#7c9cff" },
    { name: "NDCG@5", color: "#e7f59e" },
  ];

  function retrieverSpec() {
    const list = (R && R.retriever && R.retriever.retrievers) || [];
    return {
      groups: list.map((r) => r.name),
      series: RETRIEVER_SERIES,
      values: list.map((r) => [r.top1, r.recall_at_3, r.ndcg_at_5]),
      decimals: 2,
      max: 1,
      ariaLabel: "Top-1, recall at 3 and NDCG at 5 for each retriever",
    };
  }

  // Runs `rows` of a flow one after another while visible, then starts over.
  function initFlow(el) {
    const rows = $$(".flow-msg", el);
    if (reduce()) return rows.forEach((r) => r.classList.add("on"));
    let i = 0, timer = 0, visible = false;
    const tick = () => {
      if (!visible) return;
      if (i < rows.length) {
        rows[i++].classList.add("on");
        timer = setTimeout(tick, 1100);
      } else {
        timer = setTimeout(() => {
          rows.forEach((r) => r.classList.remove("on"));
          i = 0;
          timer = setTimeout(tick, 700);
        }, 3200);
      }
    };
    new IntersectionObserver(([e]) => {
      visible = e.isIntersecting;
      clearTimeout(timer);
      if (visible) tick();
    }, { threshold: 0.3 }).observe(el);
  }

  // DFSDT tree: one branch fails, turns red and fades, the search backtracks
  // to the root and a second branch succeeds down to the answer.
  const TREE_LAYOUTS = {
    wide: {
      W: 640, H: 520, font: 15,
      nodes: {
        r: [320, 40, 300], a: [150, 150, 260], b: [490, 150, 250],
        c: [490, 258, 270], d: [470, 366, 300], ans: [470, 470, 250],
      },
    },
    narrow: {
      W: 360, H: 540, font: 14,
      nodes: {
        r: [180, 40, 330], a: [92, 150, 170], b: [270, 150, 170],
        c: [200, 262, 300], d: [180, 374, 330], ans: [180, 486, 250],
      },
    },
  };
  const TREE_TEXT = {
    r: ["How high is Lisbon, in feet?", ""],
    a: ["elevation(?, ?)", "no coordinates yet"],
    b: ["geocode('Lisbon')", "38.73, -9.15"],
    c: ["elevation(38.73, -9.15)", "54 m"],
    d: ["unit_conversion(54 m → ft)", "177.2 ft"],
    ans: ["Answer: about 177 ft", ""],
  };
  const TREE_EDGES = [["r", "a"], ["r", "b"], ["b", "c"], ["c", "d"], ["d", "ans"]];

  function buildTree(card) {
    const host = $(".tree-svg", card);
    const status = $(".tree-status", card);
    let timers = [], layout = null, played = false;
    const NH = 56;

    function render() {
      const narrow = host.clientWidth < 520;
      layout = TREE_LAYOUTS[narrow ? "narrow" : "wide"];
      const N = layout.nodes;
      const edges = TREE_EDGES.map(([p, c]) => {
        const [x1, y1] = [N[p][0], N[p][1] + NH / 2];
        const [x2, y2] = [N[c][0], N[c][1] - NH / 2];
        const len = Math.hypot(x2 - x1, y2 - y1);
        const deg = (Math.atan2(y2 - y1, x2 - x1) * 180) / Math.PI;
        return `<g class="edge" data-e="${p}-${c}"><g transform="translate(${x1} ${y1}) rotate(${deg.toFixed(2)})"><g class="grow"><line x1="0" y1="0" x2="${len.toFixed(1)}" y2="0"/></g></g></g>`;
      });
      const nodes = Object.entries(N).map(([id, [x, y, w]]) => {
        const [label, sub] = TREE_TEXT[id];
        return `<g class="node${id === "ans" ? " answer" : ""}" data-n="${id}">
          <rect x="${x - w / 2}" y="${y - NH / 2}" width="${w}" height="${NH}" rx="12"/>
          <text x="${x}" y="${sub ? y - 9 : y}" font-size="${layout.font}">${esc(label)}</text>
          <text class="sub" x="${x}" y="${y + 13}">${esc(sub)}</text>
        </g>`;
      });
      host.innerHTML = `<svg viewBox="0 0 ${layout.W} ${layout.H}" role="img" aria-label="Search tree: a failed branch is abandoned and a second branch reaches the answer">
        ${edges.join("")}${nodes.join("")}
        <circle class="cursor" r="7" cx="0" cy="0" style="opacity:0"/>
      </svg>`;
    }

    const node = (id) => $(`[data-n="${id}"]`, host);
    const edge = (id) => $(`[data-e="${id}"]`, host);
    const setNode = (id, cls) => {
      const n = node(id);
      n.classList.remove("trying", "good", "bad");
      n.classList.add("shown");
      if (cls) n.classList.add(cls);
    };
    const drawEdge = (id, cls) => {
      const e = edge(id);
      e.classList.add("drawn");
      if (cls) e.classList.add(cls);
    };
    const moveCursor = (id, end) => {
      const c = $(".cursor", host);
      const [x, y] = layout.nodes[id];
      c.style.transform = `translate(${x}px, ${y + (end === "top" ? -NH / 2 : NH / 2)}px)`;
      c.style.opacity = "1";
    };

    const STEPS = [
      [0, () => { setNode("r"); status.textContent = "Start from the instruction."; }],
      [700, () => drawEdge("r-a")],
      [450, () => { setNode("a", "trying"); status.textContent = "Branch 1: elevation, but the coordinates are unknown."; }],
      [1400, () => {
        setNode("a", "bad");
        $(".sub", node("a")).textContent = "error: no latitude";
        edge("r-a").classList.add("bad");
        status.textContent = "The call fails.";
      }],
      [1400, () => {
        node("a").classList.add("faded");
        edge("r-a").classList.add("faded");
        const c = $(".cursor", host);
        c.style.transition = "none";
        moveCursor("a", "top");
        c.getBoundingClientRect();
        c.style.transition = "";
        status.textContent = "Drop the branch and backtrack to the parent.";
      }],
      [120, () => moveCursor("r", "bottom")],
      [1100, () => drawEdge("r-b")],
      [450, () => { setNode("b", "trying"); status.textContent = "Branch 2: geocode('Lisbon')."; }],
      [900, () => { setNode("b", "good"); edge("r-b").classList.add("good"); $(".cursor", host).style.opacity = "0"; status.textContent = "Coordinates found: 38.73, -9.15."; }],
      [700, () => drawEdge("b-c", "good")],
      [450, () => { setNode("c", "good"); status.textContent = "elevation(38.73, -9.15) returns 54 m."; }],
      [900, () => drawEdge("c-d", "good")],
      [450, () => { setNode("d", "good"); status.textContent = "unit_conversion returns 177.2 ft."; }],
      [900, () => drawEdge("d-ans", "good")],
      [450, () => { setNode("ans", "good"); status.textContent = "Answer found: about 177 ft."; }],
    ];

    function play() {
      timers.forEach(clearTimeout);
      timers = [];
      render();
      played = true;
      if (reduce()) {
        STEPS.forEach(([, fn]) => fn());
        $(".cursor", host).style.opacity = "0";
        return;
      }
      let at = 300;
      STEPS.forEach(([delay, fn]) => {
        at += delay;
        timers.push(setTimeout(fn, at));
      });
    }

    render();
    status.textContent = "Scroll here to start.";
    onVisible(card, play, 0.45);
    $(".tree-replay", card).addEventListener("click", play);
    let lastNarrow = host.clientWidth < 520;
    window.addEventListener("resize", debounce(() => {
      const narrow = host.clientWidth < 520;
      if (narrow !== lastNarrow) {
        lastNarrow = narrow;
        if (played) {
          render();
          STEPS.forEach(([, fn]) => fn());
          $(".cursor", host).style.opacity = "0";
        } else render();
      }
    }, 200));
  }

  Object.assign(VISUAL_INIT, {
    functionCalling: (el) => initFlow(el),
    retrieverChart: (el) => barChart($(".chart", el), retrieverSpec()),
    dfsdtTree: (el) => buildTree($(".tree", el)),
    ciChart: (el) => {
      barChart($('[data-chart="ci"]', el), passRateSpec(R && R.baseline, true));
      barChart($('[data-chart="verified"]', el), { ...passRateSpec(R && R.verified, true), height: 190 });
    },
  });

  PAGES.extension = (main) => renderDeck(main, C.slides.filter((s) => s.n >= 4), { prev: C.extensionPrev });

  PAGES.existing = (main) => renderDeck(main, C.slides.filter((s) => s.n <= 3), { next: C.existingNext });

  // ---------------------------------------------------------------- results

  const TRACE_LABELS = { instruction: "Instruction", thought: "Thought", call: "Tool call", observation: "Observation", answer: "Answer" };

  // Replays a recorded trace row by row with a typewriter effect. Under
  // reduced motion each row appears whole.
  function tracePlayer(card, trace) {
    const body = $(".trace-body", card);
    const playBtn = $(".trace-play", card);
    const stepEl = $(".trace-step", card);
    const events = [{ kind: "instruction", text: trace.instruction }].concat(
      trace.events.map((e) => ({ kind: e.kind, text: e.kind === "call" ? callText(e.text) : e.text }))
    );
    let idx = 0, chars = 0, playing = false, raf = 0, wait = 0, txt = null;

    const setButton = () => {
      playBtn.innerHTML = playing ? `${icon("pause")}Pause` : `${icon("play")}${idx >= events.length ? "Replay" : "Play"}`;
      playBtn.setAttribute("aria-pressed", String(playing));
    };
    const setStep = () => {
      stepEl.textContent = `Step ${Math.min(idx + 1, events.length)} / ${events.length}`;
    };

    function frame(now) {
      if (!playing) return;
      if (idx >= events.length) {
        playing = false;
        setButton();
        return;
      }
      if (now >= wait) {
        const e = events[idx];
        if (!txt) {
          body.insertAdjacentHTML("beforeend", `<div class="trace-row t-${e.kind}"><span class="lbl">${TRACE_LABELS[e.kind] || e.kind}</span><span class="txt"></span></div>`);
          txt = body.lastElementChild.querySelector(".txt");
          chars = 0;
          setStep();
        }
        chars = reduce() ? e.text.length : chars + (e.kind === "observation" ? 6 : 2);
        if (chars >= e.text.length) {
          txt.textContent = e.text;
          txt = null;
          idx++;
          wait = now + (reduce() ? 900 : 550);
        } else {
          txt.innerHTML = `${esc(e.text.slice(0, chars))}<span class="caret"></span>`;
        }
      }
      raf = requestAnimationFrame(frame);
    }

    const play = () => {
      if (idx >= events.length) restart(false);
      playing = true;
      setButton();
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(frame);
    };
    const pause = () => {
      playing = false;
      cancelAnimationFrame(raf);
      setButton();
    };
    function restart(autoplay = true) {
      cancelAnimationFrame(raf);
      body.innerHTML = "";
      idx = 0;
      txt = null;
      wait = 0;
      setStep();
      if (autoplay) play();
    }

    playBtn.addEventListener("click", () => (playing ? pause() : play()));
    $(".trace-restart", card).addEventListener("click", () => restart(true));
    document.addEventListener("visibilitychange", () => {
      if (document.hidden && playing) pause();
    });
    setStep();
    setButton();
    onVisible(card, play, 0.35);
  }

  PAGES.results = (main) => {
    const P = C.results;
    const trace = R && R.traces && R.traces[0];
    const b = R && R.benchmark;
    const video = R && R.media && R.media.demo_video;
    const statLabel = (l) => (/\(provisional\)/.test(l) ? `${esc(l.replace(/\s*\(provisional\)/, ""))} ${PROV}` : esc(l));

    main.innerHTML = `
      <section class="page-hero">
        <div class="wrap">
          <span class="kicker" data-reveal>Results</span>
          <h1 class="h-line" data-reveal style="--i:1">${fill(P.title)}</h1>
          <p class="lead" data-reveal style="--i:2">${fill(P.intro)}${R ? ` Exported ${esc(R.generated_at.slice(0, 10))}.` : ` ${TBD}`}</p>
        </div>
      </section>

      <section class="section" style="padding-top:20px">
        <div class="wrap">
          <div class="stats-grid">
            ${P.stats.map((s, i) => `<div class="stat card" data-reveal style="--i:${i}">
                <span class="n" data-count="${s.value}"${s.percent ? ' data-format="pct"' : ""}></span>
                <span class="l">${statLabel(s.label)}</span>
              </div>`).join("")}
          </div>
        </div>
      </section>

      <section class="section" id="charts" style="padding-top:0">
        <div class="wrap">
          <div class="section-head"><h2 class="h-line" data-reveal>${fill(P.chartsTitle)}</h2></div>
          <div class="grid grid-2 charts-grid">
            <div class="card chart-card" data-reveal>
              <div class="card-title-row"><h3>${esc(P.baselineTitle)}</h3>${PROV}</div>
              <div class="chart" data-chart="baseline"></div>
              ${legend(AGENT_SERIES)}
              <p class="note">${fill(P.baselineNote)}</p>
            </div>
            <div class="card chart-card" data-reveal style="--i:1">
              <div class="card-title-row"><h3>${esc(P.verifiedTitle)}</h3>${R && R.verified ? "" : TBD}</div>
              <div class="chart" data-chart="verified"></div>
              ${legend(AGENT_SERIES)}
            </div>
            <div class="card chart-card" data-reveal>
              <div class="card-title-row"><h3>${esc(P.retrieverTitle)}</h3></div>
              <div class="chart" data-chart="retriever"></div>
              ${legend(RETRIEVER_SERIES)}
              <p class="note">${R && R.retriever ? `${R.retriever.n_tasks} tasks over ${R.retriever.pool_size} tools. ` : ""}Dashed bars are not built yet.</p>
            </div>
            <div class="card chart-card" data-reveal style="--i:1">
              <div class="card-title-row"><h3>${esc(P.benchmarkTitle)}</h3></div>
              <div class="chart" data-chart="benchmark"></div>
              <div class="split-bar"><i style="width:${b && b.total ? (100 * b.fact_tasks) / b.total : 0}%"></i><i style="width:${b && b.total ? (100 * b.live_value_tasks) / b.total : 0}%"></i></div>
              <div class="legend">
                <span><i style="background:var(--accent)"></i>${b ? b.fact_tasks : TBD} with expected facts</span>
                <span><i style="background:var(--amber)"></i>${b ? b.live_value_tasks : TBD} with a live-value rule</span>
                <span>${b ? `${b.by_split.test} test / ${b.by_split.dev} dev` : ""}</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section class="section" id="demo">
        <div class="wrap">
          <div class="section-head"><h2 class="h-line" data-reveal>${fill(P.traceTitle)}</h2><p class="lead" data-reveal style="--i:1">${fill(P.traceIntro)}</p></div>
          ${trace ? `<div class="card trace" data-reveal>
              <div class="trace-head">
                <div class="dots" aria-hidden="true"><i></i><i></i><i></i></div>
                <span class="trace-step mono"></span>
                <div class="btn-row">
                  <button class="btn btn-sm btn-primary trace-play" type="button"></button>
                  <button class="btn btn-sm trace-restart" type="button">${icon("restart")}Restart</button>
                </div>
              </div>
              <div class="trace-body" aria-live="polite"></div>
              <div class="trace-meta">${esc(trace.agent)} agent · stop reason: ${esc(trace.stop_reason)} · recorded ${esc(trace.recorded_at.slice(0, 10))} · <code>${esc(trace.source)}</code></div>
            </div>` : `<div class="card">${TBD} No recorded trace in results/traces/ yet.</div>`}

          <div class="section-head" style="margin-top:clamp(56px,7vw,96px)"><h2 class="h-line" data-reveal>${fill(P.videoTitle)}</h2></div>
          <div class="card video-frame" data-reveal>
            ${video
              ? `<video controls preload="metadata" playsinline poster="${P.video.poster}"><source src="${video}" type="video/mp4"></video>`
              : `<div class="video-placeholder"><div class="play-ring">${icon("play")}</div><p>${esc(P.videoMissing)}</p>${TBD}</div>`}
          </div>
        </div>
      </section>

      <section class="section" id="screens" style="padding-top:0">
        <div class="wrap">
          <div class="section-head"><h2 class="h-line" data-reveal>${fill(P.screensTitle)}</h2></div>
          <div class="shots">
            ${P.screens.map((s, i) => `<figure class="card shot tilt" data-reveal style="--i:${i}">
                <img src="${s.src}" alt="${esc(s.caption)}" data-fallback loading="lazy" decoding="async">
                <figcaption>${esc(s.caption)}</figcaption>
              </figure>`).join("")}
          </div>
        </div>
      </section>`;

    barChart($('[data-chart="baseline"]', main), passRateSpec(R && R.baseline, true));
    barChart($('[data-chart="verified"]', main), passRateSpec(R && R.verified, true));
    barChart($('[data-chart="retriever"]', main), retrieverSpec());
    barChart($('[data-chart="benchmark"]', main), {
      groups: ["Easy", "Medium", "Hard"],
      series: [{ name: "Tasks", color: "#19e6b4" }],
      values: ["easy", "medium", "hard"].map((d) => [b ? b.by_difficulty[d] : null]),
      // Whole-number ticks: the axis top is the next multiple of 4.
      max: b ? Math.ceil(Math.max(4, ...Object.values(b.by_difficulty)) / 4) * 4 : 4,
      height: 230,
      ariaLabel: "Generated tasks per difficulty",
    });
    if (trace) tracePlayer($(".trace", main), trace);
    const vid = $("video", main);
    if (vid) {
      // If the file goes missing after export, fall back to the placeholder.
      $("source", vid).addEventListener("error", () => {
        vid.outerHTML = `<div class="video-placeholder"><div class="play-ring">${icon("play")}</div><p>${esc(P.videoMissing)}</p>${TBD}</div>`;
      });
    }
  };

  PAGES.team = (main) => {
    const T = C.teamPage;
    const initials = (name) => name.split(" ").map((w) => w[0]).join("").slice(0, 2);
    main.innerHTML = `
      <section class="page-hero">
        <div class="wrap">
          <span class="kicker" data-reveal>Team</span>
          <h1 class="h-line" data-reveal style="--i:1">${fill(T.title)}</h1>
          <p class="lead" data-reveal style="--i:2">${fill(T.intro)}</p>
        </div>
      </section>

      <section class="section" style="padding-top:20px">
        <div class="wrap">
          <div class="grid grid-3">
            ${C.team.map((m, i) => `<article class="card member tilt" data-reveal style="--i:${i}">
                <div class="avatar" aria-hidden="true">${esc(initials(m.name))}</div>
                <h3>${esc(m.name)}</h3>
                <div class="id">${esc(m.id)}</div>
                <div class="role">${m.role ? esc(m.role) : `Role ${TBD}`}</div>
              </article>`).join("")}
          </div>
          <div class="card repo-card" data-reveal style="margin-top:22px">
            <div>
              <h3>${esc(T.repoTitle)}</h3>
              <p>${fill(T.repoText)}</p>
              <code>${esc(C.repo.replace(/^https:\/\//, ""))}</code>
            </div>
            <a class="btn btn-primary magnetic" href="${C.repo}" rel="noopener">${icon("call")}Open the repository</a>
          </div>
        </div>
      </section>

      <section class="section" style="padding-top:0">
        <div class="wrap">
          <div class="grid grid-2">
            <article class="card" data-reveal>
              <h2 class="h-line" style="font-size:clamp(1.6rem,2.4vw,2.2rem)">${fill(T.didTitle)}</h2>
              <ul class="check-list">${T.did.map((d) => `<li>${icon("check")}${fill(d)}</li>`).join("")}</ul>
            </article>
            <article class="card" data-reveal style="--i:1">
              <h2 class="h-line" style="font-size:clamp(1.6rem,2.4vw,2.2rem)">${fill(T.didNotTitle)}</h2>
              <ul class="x-list">${T.didNot.map((d) => `<li>${icon("x")}${fill(d)}</li>`).join("")}</ul>
            </article>
          </div>
        </div>
      </section>

      <section class="section" style="padding-top:0">
        <div class="wrap">
          <div class="card" data-reveal>
            <h2 class="h-line" style="font-size:clamp(1.6rem,2.4vw,2.2rem)">${fill(T.referencesTitle)}</h2>
            <ol class="refs">${T.references.map((r) => `<li>${r.href ? `<a href="${r.href}" rel="noopener">${esc(r.text)}</a>` : esc(r.text)}</li>`).join("")}</ol>
          </div>
        </div>
      </section>`;
  };

  // ---------------------------------------------------------------- demo

  // Builds DOM nodes. String children become text nodes, so text from the
  // server is never parsed as HTML.
  function h(tag, attrs, ...children) {
    const el = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v == null || v === false) continue;
      if (k === "class") el.className = v;
      else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
      else el.setAttribute(k, v === true ? "" : v);
    }
    for (const c of children.flat()) {
      if (c != null && c !== false) el.append(c instanceof Node ? c : String(c));
    }
    return el;
  }

  // An icon from the constant ICONS table (never server text).
  function iconNode(name) {
    const t = document.createElement("template");
    t.innerHTML = icon(name);
    return t.content.firstElementChild;
  }

  const svgEl = (tag, attrs) => {
    const el = document.createElementNS("http://www.w3.org/2000/svg", tag);
    for (const [k, v] of Object.entries(attrs || {})) el.setAttribute(k, v);
    return el;
  };

  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const STRATEGY_LABEL = { react: "ReAct", dfsdt: "DFSDT" };
  const API_BASE_KEY = "toolagent.apiBase";
  const MAX_CHARS = 300;

  // The answer text uses a little Markdown (bold, bullet lists). It is
  // rendered as DOM nodes with textContent, never as HTML.
  function richText(text) {
    const frag = document.createDocumentFragment();
    let list = null;
    const inline = (line) => line.split(/(\*\*[^*]+\*\*)/).filter(Boolean).map((part) =>
      /^\*\*[^*]+\*\*$/.test(part) ? h("strong", null, part.slice(2, -2)) : part
    );
    text.split(/\n+/).forEach((raw) => {
      const line = raw.trim();
      if (!line) return;
      const bullet = line.match(/^[-*•]\s+(.*)$/);
      if (bullet) {
        if (!list) frag.append((list = h("ul")));
        list.append(h("li", null, inline(bullet[1])));
      } else {
        list = null;
        frag.append(h("p", null, inline(line)));
      }
    });
    return frag;
  }

  // Types `text` into `el`; instant under reduced motion or once the run
  // is told to hurry (cancelled, or replayed from history).
  function typeText(el, text, ctx) {
    if (!text || reduce() || ctx.instant) {
      el.textContent = text;
      return Promise.resolve();
    }
    return new Promise((resolve) => {
      const node = document.createTextNode("");
      const caret = h("span", { class: "caret" });
      el.replaceChildren(node, caret);
      const stepSize = Math.max(2, Math.ceil(text.length / 40));
      let i = 0;
      const tick = () => {
        i = ctx.instant ? text.length : Math.min(text.length, i + stepSize);
        node.data = text.slice(0, i);
        if (i < text.length) setTimeout(tick, 16);
        else {
          caret.remove();
          resolve();
        }
      };
      tick();
    });
  }

  const argText = (args) =>
    Object.entries(args || {}).map(([k, v]) => `${k}=${JSON.stringify(v)}`).join(", ");
  const jsonText = (v) => (typeof v === "string" ? v : JSON.stringify(v, null, 2));
  const fmtLatency = (ms) => (ms == null ? "–" : ms < 1000 ? `${ms} ms` : `${(ms / 1000).toFixed(1)} s`);

  // A whole run as the event sequence the stream would have sent, for
  // replaying a recorded run or a run fetched without streaming.
  function runToEvents(run) {
    const events = [["retrieved", { strategy: run.strategy, model: run.model, top_k: run.top_k, retrieved_tools: run.retrieved_tools }]];
    if (run.tree) {
      const nodes = run.tree.nodes.filter((n) => n.id !== 0).sort((a, b) => a.id - b.id);
      const parentOf = new Map(run.tree.nodes.map((n) => [n.id, n.parent]));
      const isUnder = (id, root) => {
        for (let p = id; p != null; p = parentOf.get(p)) if (p === root) return true;
        return false;
      };
      const pendingDeadEnds = [];
      const flushDeadEnds = (beforeId) => {
        while (pendingDeadEnds.length && (beforeId == null || !isUnder(beforeId, pendingDeadEnds[pendingDeadEnds.length - 1]))) {
          const id = pendingDeadEnds.pop();
          events.push(["backtrack", { node: id, reason: "dead_end", steps: run.steps.filter((s) => s.node === id).map((s) => s.index) }]);
        }
      };
      nodes.forEach((n) => {
        flushDeadEnds(n.id);
        events.push(["node", { id: n.id, parent: n.parent, depth: n.depth, tools: n.tools, status: "open" }]);
        run.steps.filter((s) => s.node === n.id).forEach((s) => events.push(["step", { ...s, backtracked: false }]));
        if (n.status === "error") {
          const reason = n.tools.length ? "tool_error" : "empty_reply";
          events.push(["backtrack", { node: n.id, reason, steps: run.steps.filter((s) => s.node === n.id).map((s) => s.index) }]);
        } else if (n.status === "dead_end") pendingDeadEnds.push(n.id);
        else if (n.status === "answer") events.push(["answer", { text: run.final_answer }]);
      });
      flushDeadEnds(null);
    } else {
      run.steps.forEach((s) => events.push(["step", s]));
      if (run.final_answer) events.push(["answer", { text: run.final_answer }]);
    }
    events.push(["done", run]);
    return events;
  }

  const BACKTRACK_TEXT = {
    tool_error: "A tool call failed, so this branch is dropped and another reply is tried.",
    empty_reply: "The model returned an empty reply, so another reply is tried.",
    dead_end: "Nothing below this branch reached an answer, so the search backtracks.",
  };

  const ERROR_TITLES = {
    rate_limited: "Slow down a little",
    demo_limit: "Demo limit reached",
    model_rate_limited: "The model is busy",
    timeout: "That took too long",
    not_configured: "Live mode is not set up",
    busy: "The server is busy",
    offline: "Cannot reach the server",
    interrupted: "The connection dropped",
    question_too_long: "Question too long",
    empty_question: "No question yet",
  };

  // ---------------------------------------------------------------- tree

  // Lays the DFSDT search tree out top-down: leaves get one column each in
  // the order explored, parents sit above the middle of their children.
  function drawTree(host, nodes, seen, chosen) {
    const kids = new Map();
    nodes.forEach((n) => {
      if (n.parent == null) return;
      if (!kids.has(n.parent)) kids.set(n.parent, []);
      kids.get(n.parent).push(n.id);
    });
    const col = new Map();
    let slot = 0, maxDepth = 0;
    const place = (id) => {
      const ch = (kids.get(id) || []).sort((a, b) => a - b);
      if (!ch.length) col.set(id, slot++);
      else {
        ch.forEach(place);
        col.set(id, (col.get(ch[0]) + col.get(ch[ch.length - 1])) / 2);
      }
    };
    place(0);
    nodes.forEach((n) => (maxDepth = Math.max(maxDepth, n.depth)));

    const NW = 124, NH = 44, GX = 140, GY = 84, P = 10;
    const W = Math.max(1, slot) * GX - (GX - NW) + P * 2;
    const H = maxDepth * GY + NH + P * 2;
    const cx = (id) => P + col.get(id) * GX + NW / 2;
    const cy = (d) => P + d * GY + NH / 2;
    const svg = svgEl("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": "DFSDT search tree" });
    svg.style.maxWidth = `${W}px`;

    nodes.forEach((n) => {
      if (n.parent == null || !col.has(n.id)) return;
      const parent = nodes.get(n.parent);
      const x1 = cx(n.parent), y1 = cy(parent.depth) + NH / 2, x2 = cx(n.id), y2 = cy(n.depth) - NH / 2;
      const my = (y1 + y2) / 2;
      const path = svgEl("path", { d: `M${x1} ${y1} C${x1} ${my} ${x2} ${my} ${x2} ${y2}`, pathLength: "1" });
      path.setAttribute("class", `t-edge s-${n.status}${chosen.has(n.id) ? " chosen" : ""}${seen.has("e" + n.id) ? "" : " enter"}`);
      seen.add("e" + n.id);
      svg.append(path);
    });

    nodes.forEach((n) => {
      if (!col.has(n.id)) return;
      const g = svgEl("g", { transform: `translate(${cx(n.id) - NW / 2} ${cy(n.depth) - NH / 2})` });
      g.setAttribute("class", `t-node s-${n.status}${chosen.has(n.id) ? " chosen" : ""}${seen.has(n.id) ? "" : " enter"}`);
      seen.add(n.id);
      const label = n.id === 0 ? "Question" : n.status === "answer" ? "Answer" : n.tools.length ? clip(n.tools.join(", "), 17) : "Empty reply";
      const sub = { root: "start", open: "running", ok: "ok", error: "failed", dead_end: "dead end", answer: "final answer" }[n.status] || n.status;
      const title = svgEl("title");
      title.textContent = n.id === 0 ? "The question" : `Branch ${n.id}: ${n.tools.join(", ") || "text reply"} (${sub})`;
      const rect = svgEl("rect", { width: NW, height: NH, rx: 11 });
      const t1 = svgEl("text", { x: NW / 2, y: 19, class: "t-label" });
      t1.textContent = label;
      const t2 = svgEl("text", { x: NW / 2, y: 34, class: "t-sub" });
      t2.textContent = n.id === 0 ? sub : `#${n.id} · ${sub}`;
      g.append(title, rect, t1, t2);
      svg.append(g);
    });
    host.replaceChildren(svg);
  }

  // ---------------------------------------------------------------- panel

  // One run's results: retrieved APIs, timeline, tree, answer, metrics.
  // Events are applied in order through a queue, so typing animations never
  // overlap however fast the stream sends them.
  function createPanel(parent, strategy, opts) {
    const ctx = { instant: !!opts.instant };
    let chain = Promise.resolve();
    const enqueue = (fn) => (chain = chain.then(fn).catch((err) => console.error(err)));
    const state = { cards: new Map(), steps: new Map(), nodes: new Map([[0, { id: 0, parent: null, depth: 0, tools: [], status: "root" }]]), seen: new Set(), run: null, error: null, ended: false };

    const stateText = h("span", { class: "run-state" }, opts.recorded ? "Replaying" : "Retrieving APIs");
    const head = h("div", { class: "run-head" },
      h("span", { class: `strategy-badge s-${strategy}` }, STRATEGY_LABEL[strategy]),
      stateText,
      opts.recorded ? h("span", { class: "mode-tag recorded", title: "Replayed from a saved run, not live" }, `Recorded ${opts.recorded}`) : null
    );
    const skel = (n, cls) => Array.from({ length: n }, () => h("div", { class: `skel ${cls}` }));
    const apiGrid = h("div", { class: "api-grid" }, skel(Math.min(opts.topK || 4, 6), "skel-card"));
    const timeline = h("ol", { class: "timeline" });
    const timelineSkel = h("div", { class: "skel-group" }, skel(2, "skel-row"));
    const treeHost = h("div", { class: "tree-host" });
    const treeSec = strategy === "dfsdt"
      ? h("section", { class: "run-sec" },
          h("h3", { class: "run-sec-title" }, iconNode("tree"), "Search tree"),
          treeHost,
          h("div", { class: "tree-legend" },
            h("span", { class: "lg chosen" }, "chosen path"),
            h("span", { class: "lg error" }, "failed call"),
            h("span", { class: "lg dead" }, "dead end")))
      : null;
    const answerBody = h("div", { class: "answer-body" }, skel(2, "skel-line"));
    const answerCard = h("div", { class: "answer-card pending" }, h("div", { class: "answer-label" }, iconNode("check"), "Final answer"), answerBody);
    const metric = (label) => {
      const v = h("span", { class: "m-v" }, "–");
      return [h("div", { class: "metric" }, v, h("span", { class: "m-l" }, label)), v];
    };
    const [mSteps, vSteps] = metric("steps");
    const [mCalls, vCalls] = metric("tool calls");
    const [mLatency, vLatency] = metric("latency");
    const [mModel, vModel] = metric("model");
    const metrics = h("div", { class: "metrics" }, mSteps, mCalls, mLatency, mModel);

    const el = h("article", { class: `run-panel s-${strategy}` },
      head,
      h("section", { class: "run-sec" }, h("h3", { class: "run-sec-title" }, iconNode("search"), "Retrieved APIs"), apiGrid),
      h("section", { class: "run-sec" }, h("h3", { class: "run-sec-title" }, iconNode("call"), "Reasoning"), timeline, timelineSkel),
      treeSec,
      answerCard,
      metrics
    );
    parent.append(el);
    if (treeSec) drawTree(treeHost, state.nodes, state.seen, new Set());

    function markCard(name, status) {
      const card = state.cards.get(name);
      if (!card) return;
      if (status === "ok") {
        card.classList.add("used");
        card.classList.remove("failed");
      } else if (!card.classList.contains("used")) card.classList.add("failed");
    }

    function onRetrieved(data) {
      stateText.textContent = opts.recorded ? "Replaying the recorded run" : `Reasoning with ${STRATEGY_LABEL[strategy]}`;
      vModel.textContent = data.model || "–";
      const max = Math.max(...data.retrieved_tools.map((t) => t.score), 0.0001);
      apiGrid.replaceChildren();
      data.retrieved_tools.forEach((t, i) => {
        const bar = h("i");
        const card = h("div", { class: "api-card", style: `--i:${i}` },
          h("div", { class: "api-top" },
            h("span", { class: "api-icon" }, iconNode(CATEGORY_ICONS[t.category])),
            h("span", { class: "api-name" }, t.name),
            h("span", { class: "api-badge used-badge" }, "used"),
            h("span", { class: "api-badge failed-badge" }, "failed")),
          h("p", { class: "api-desc" }, t.description),
          h("div", { class: "api-score" },
            h("span", { class: "score-bar" }, bar),
            h("span", { class: "score-v" }, t.score.toFixed(2))),
          h("span", { class: "api-cat" }, t.category)
        );
        card.title = `Relevance ${t.score.toFixed(3)}`;
        apiGrid.append(card);
        state.cards.set(t.name, card);
        requestAnimationFrame(() => requestAnimationFrame(() => (bar.style.width = `${Math.max(3, (100 * t.score) / max)}%`)));
      });
    }

    async function onStep(s) {
      timelineSkel.remove();
      const obsText = jsonText(s.observation);
      const thought = h("div", { class: `tl-text${s.thought ? "" : " none"}` });
      const call = h("code", { class: "tl-code" });
      const item = h("li", { class: `tl-item ${s.status}`, "data-step": s.index },
        h("span", { class: "tl-dot" }, String(s.index)),
        h("div", { class: "tl-body" },
          h("div", { class: "tl-row" }, h("span", { class: "tl-lbl thought" }, "Thought"), thought),
          h("div", { class: "tl-row" },
            h("span", { class: "tl-lbl call" }, "Tool call"),
            call,
            s.node != null ? h("span", { class: "tl-branch" }, `branch #${s.node}`) : null,
            s.status === "error" ? h("span", { class: "tl-fail" }, iconNode("x"), "failed") : null),
          h("details", { class: "tl-obs" },
            h("summary", null, h("span", { class: `tl-lbl obs` }, "Observation"), h("span", { class: "tl-preview" }, clip(typeof s.observation === "string" ? s.observation : JSON.stringify(s.observation), 110))),
            h("pre", null, obsText)))
      );
      timeline.append(item);
      state.steps.set(s.index, item);
      vCalls.textContent = String(state.steps.size);
      if (s.thought) await typeText(thought, s.thought, ctx);
      else thought.textContent = "No reasoning text came with this call; the model went straight to the tool.";
      await typeText(call, `${s.tool}(${argText(s.arguments)})`, ctx);
      markCard(s.tool, s.status);
    }

    function onNode(n) {
      state.nodes.set(n.id, { ...n });
      drawTree(treeHost, state.nodes, state.seen, new Set());
    }

    function onBacktrack(b) {
      const node = state.nodes.get(b.node);
      if (node) node.status = b.reason === "dead_end" ? "dead_end" : "error";
      (b.steps || []).forEach((i) => state.steps.get(i) && state.steps.get(i).classList.add("backtracked"));
      timelineSkel.remove();
      timeline.append(
        h("li", { class: "tl-item backtrack" },
          h("span", { class: "tl-dot" }, iconNode("branch")),
          h("div", { class: "tl-body" },
            h("div", { class: "tl-row" }, h("span", { class: "tl-lbl back" }, "Backtrack"), h("div", { class: "tl-text" }, `Branch #${b.node}: ${b.message || BACKTRACK_TEXT[b.reason] || "backtracking"}`))))
      );
      if (treeSec) drawTree(treeHost, state.nodes, state.seen, new Set());
    }

    async function onAnswer(a) {
      if (strategy === "dfsdt") {
        const open = [...state.nodes.values()].filter((n) => n.status === "open" && !n.tools.length).pop();
        if (open) {
          open.status = "answer";
          drawTree(treeHost, state.nodes, state.seen, new Set());
        }
      }
      answerCard.classList.remove("pending");
      answerCard.classList.add("ready");
      const body = h("div", { class: "answer-text" });
      answerBody.replaceChildren(body);
      await typeText(body, a.text, ctx);
      body.replaceChildren(richText(a.text));
    }

    function onDone(run) {
      state.run = run;
      state.ended = true;
      timelineSkel.remove();
      stateText.textContent = run.final_answer ? "Done" : "Stopped without an answer";
      el.classList.add("done");
      run.steps.forEach((s) => {
        const item = state.steps.get(s.index);
        if (item) item.classList.toggle("backtracked", !!s.backtracked);
      });
      const called = new Set(run.tools_called);
      state.cards.forEach((card, name) => {
        if (!called.has(name) && !card.classList.contains("failed")) card.classList.add("unused");
      });
      if (!run.final_answer) {
        answerCard.classList.remove("pending");
        answerCard.classList.add("none");
        answerBody.replaceChildren(h("p", null, `The agent stopped without an answer (${run.stop_reason.replace("_", " ")}).`));
      }
      vSteps.textContent = String(run.num_steps);
      vCalls.textContent = String(run.num_tool_calls);
      vLatency.textContent = fmtLatency(run.latency_ms);
      vModel.textContent = run.model || "–";
      if (run.tree && treeSec) {
        state.nodes = new Map(run.tree.nodes.map((n) => [n.id, n]));
        drawTree(treeHost, state.nodes, state.seen, new Set(run.tree.chosen_path));
        metrics.append(h("div", { class: "metric" }, h("span", { class: "m-v" }, String(run.tree.explored)), h("span", { class: "m-l" }, "branches explored")));
      }
    }

    function showError(err) {
      if (state.ended) return;
      state.ended = true;
      state.error = err;
      el.classList.add("failed");
      stateText.textContent = err.code === "cancelled" ? "Cancelled" : "Failed";
      el.querySelectorAll(".skel, .skel-group").forEach((s) => s.remove());
      if (err.code === "cancelled") {
        answerCard.classList.remove("pending");
        answerCard.classList.add("none");
        answerBody.replaceChildren(h("p", null, "You cancelled this run."));
        return;
      }
      answerCard.replaceWith(errorCard(err));
    }

    const handlers = { retrieved: onRetrieved, step: onStep, node: onNode, backtrack: onBacktrack, answer: onAnswer, done: onDone, error: showError };
    return {
      el,
      state,
      push(event, data) {
        const fn = handlers[event];
        if (fn) enqueue(() => (state.ended && event !== "done" ? null : fn(data)));
      },
      pace(ms) {
        enqueue(() => (ctx.instant ? null : sleep(ms)));
      },
      hurry() {
        ctx.instant = true;
      },
      fail(err) {
        ctx.instant = true;
        enqueue(() => showError(err));
      },
      settled: () => chain.then(() => state),
    };
  }

  function errorCard(err) {
    return h("div", { class: "error-card", role: "alert" },
      h("div", { class: "error-title" }, iconNode("x"), ERROR_TITLES[err.code] || "Something went wrong"),
      h("p", null, err.message || "Please try again.")
    );
  }

  // ---------------------------------------------------------------- transport

  // Reads Server-Sent Events from a fetch response body.
  async function readSSE(res, onEvent) {
    const reader = res.body.pipeThrough(new TextDecoderStream()).getReader();
    let buffer = "";
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += value.replace(/\r\n/g, "\n");
      let cut;
      while ((cut = buffer.indexOf("\n\n")) >= 0) {
        const block = buffer.slice(0, cut);
        buffer = buffer.slice(cut + 2);
        let event = "message", data = "";
        block.split("\n").forEach((line) => {
          if (line.startsWith("event:")) event = line.slice(6).trim();
          else if (line.startsWith("data:")) data += line.slice(5).trim();
        });
        if (data) onEvent(event, JSON.parse(data));
      }
    }
  }

  async function errorFrom(res) {
    try {
      const body = await res.json();
      if (body && body.error && body.error.message) return body.error;
    } catch (e) { /* not JSON */ }
    return { code: `http_${res.status}`, message: `The server answered with HTTP ${res.status}. Please try again.` };
  }

  const OFFLINE = { code: "offline", message: "The demo server could not be reached. Double-click start_demo.bat and keep its window open." };

  // Streams one live run into `panel`; falls back to POST /api/run when the
  // browser cannot read a streamed response.
  async function liveRun(base, params, panel, signal) {
    const query = new URLSearchParams({ question: params.question, strategy: params.strategy, top_k: String(params.topK) });
    let finished = false;
    const forward = (event, data) => {
      if (event === "done" || event === "error") finished = true;
      panel.push(event, data);
    };
    try {
      const canStream = "TextDecoderStream" in window && "body" in Response.prototype;
      if (canStream) {
        const res = await fetch(`${base}/api/run/stream?${query}`, { signal, headers: { Accept: "text/event-stream" } });
        if (!res.ok) return panel.fail(await errorFrom(res));
        if (res.body) {
          await readSSE(res, forward);
          if (!finished) panel.fail({ code: "interrupted", message: "The connection to the server closed before the run finished. Please try again." });
          return;
        }
      }
      const res = await fetch(`${base}/api/run`, {
        method: "POST",
        signal,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: params.question, strategy: params.strategy, top_k: params.topK }),
      });
      if (!res.ok) return panel.fail(await errorFrom(res));
      runToEvents(await res.json()).forEach(([e, d]) => forward(e, d));
    } catch (err) {
      if (signal.aborted) return panel.fail({ code: "cancelled", message: "Cancelled." });
      panel.fail(finished ? { code: "interrupted", message: "The connection dropped." } : OFFLINE);
    }
  }

  async function recordedRun(run, panel, signal, instant) {
    for (const [event, data] of runToEvents(run)) {
      if (signal.aborted) return panel.fail({ code: "cancelled", message: "Cancelled." });
      panel.push(event, data);
      if (!instant) panel.pace(event === "retrieved" ? 700 : 450);
    }
  }

  // ---------------------------------------------------------------- page

  PAGES.demo = (main) => {
    const T = C.demoPage;
    const D = window.SITE_DEMO_RUNS || { questions: [], runs: [] };
    // Live by default. Recorded replay is only ever turned on by the user.
    const st = { base: "", mode: "live", recorded: false, online: null, health: null, checking: false, strategy: "react", running: null, history: [] };

    const LOCAL_SERVER = "http://localhost:8000";
    const defaultBase = () => (/^https?:$/.test(location.protocol) ? location.origin : LOCAL_SERVER);
    const savedBase = () => {
      try {
        return localStorage.getItem(API_BASE_KEY) || "";
      } catch (e) {
        return "";
      }
    };
    st.base = savedBase() || defaultBase();

    main.innerHTML = `
      <div class="wrap demo-top">
        <div class="demo-statusbar"></div>
        <div class="demo-banners" aria-live="assertive"></div>
      </div>
      <section class="page-hero demo-hero">
        <div class="wrap">
          <span class="kicker" data-reveal>${esc(T.kicker)}</span>
          <h1 class="h-line" data-reveal style="--i:1">${fill(T.title)}</h1>
          <p class="lead" data-reveal style="--i:2">${fill(T.intro)}</p>
        </div>
      </section>
      <section class="section demo-section">
        <div class="wrap">
          <div class="card demo-console" data-reveal></div>
          <div class="demo-notice" hidden></div>
          <div class="demo-results" aria-live="polite"></div>
          <div class="demo-summary" hidden></div>
          <div class="card demo-history" hidden></div>
        </div>
      </section>`;

    const statusBar = $(".demo-statusbar", main);
    const banners = $(".demo-banners", main);
    const consoleEl = $(".demo-console", main);
    const notice = $(".demo-notice", main);
    const results = $(".demo-results", main);
    const summary = $(".demo-summary", main);
    const historyEl = $(".demo-history", main);

    // -- console
    const statusPill = h("span", { class: "status-pill checking", role: "status" }, h("i"), h("span", null, "Checking backend…"));
    const modeBadge = h("span", { class: "mode-badge live" }, "Live");
    const recordedBox = h("input", { type: "checkbox", id: "demo-rec" });
    const recordedToggle = h("label", { class: "rec-toggle", for: "demo-rec", title: "Replay runs recorded earlier instead of asking the server" },
      recordedBox, h("span", { class: "rec-switch", "aria-hidden": "true" }), h("span", null, "Use recorded demo"));
    const input = h("textarea", { id: "demo-q", rows: "3", maxlength: String(MAX_CHARS), placeholder: T.placeholder, "aria-describedby": "demo-count" });
    const counter = h("span", { id: "demo-count", class: "char-count" }, `0 / ${MAX_CHARS}`);
    const examples = h("div", { class: "examples", role: "list", "aria-label": "Example questions" },
      D.questions.map((q) => h("button", { class: "example-chip", type: "button", role: "listitem", onclick: () => {
        input.value = q;
        updateCount();
        input.focus();
      } }, q))
    );
    const strategyBtns = [["react", "ReAct"], ["dfsdt", "DFSDT"], ["compare", "Compare both"]].map(([value, label]) =>
      h("button", { type: "button", class: "seg-btn", role: "radio", "aria-checked": String(value === st.strategy), "data-value": value, onclick: () => setStrategy(value) }, label)
    );
    const seg = h("div", { class: "seg", role: "radiogroup", "aria-label": "Agent strategy" }, strategyBtns);
    const topK = h("input", { type: "range", min: "1", max: "10", value: "5", id: "demo-k", "aria-describedby": "demo-k-v" });
    const topKValue = h("output", { id: "demo-k-v", for: "demo-k" }, "5");
    const topKNote = h("span", { class: "k-note" });
    const runBtn = h("button", { class: "btn btn-primary run-btn", type: "button" }, iconNode("play"), "Run");
    const cancelBtn = h("button", { class: "btn cancel-btn", type: "button", hidden: true }, iconNode("stop"), "Cancel");
    const baseInput = h("input", { type: "url", id: "demo-base", spellcheck: "false", autocomplete: "off", placeholder: defaultBase() });
    baseInput.value = st.base;
    const baseMsg = h("span", { class: "settings-msg", role: "status" });
    const settings = h("details", { class: "demo-settings" },
      h("summary", null, iconNode("gear"), "Settings"),
      h("div", { class: "settings-body" },
        h("label", { for: "demo-base" }, "API base URL"),
        h("div", { class: "settings-row" }, baseInput,
          h("button", { class: "btn btn-sm", type: "button", onclick: () => saveBase(baseInput.value) }, "Save"),
          h("button", { class: "btn btn-sm", type: "button", onclick: () => saveBase("") }, "Reset")),
        h("p", { class: "settings-note" }, "Where the demo server runs, e.g. http://localhost:8000. Saved in this browser only."),
        baseMsg)
    );

    statusBar.append(statusPill, modeBadge, recordedToggle, settings);
    consoleEl.append(
      h("label", { class: "sr-only", for: "demo-q" }, "Your question"),
      h("div", { class: "q-wrap" }, input, counter),
      examples,
      h("div", { class: "controls" },
        h("div", { class: "control" }, h("span", { class: "control-lbl" }, "Strategy"), seg),
        h("div", { class: "control" }, h("label", { class: "control-lbl", for: "demo-k" }, "APIs to retrieve (top-k)"), h("div", { class: "k-row" }, topK, topKValue), topKNote),
        h("div", { class: "control run-ctl" }, runBtn, cancelBtn))
    );

    function updateCount() {
      counter.textContent = `${input.value.length} / ${MAX_CHARS}`;
      counter.classList.toggle("near", input.value.length > MAX_CHARS - 30);
    }
    input.addEventListener("input", updateCount);
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey && !e.isComposing) {
        e.preventDefault();
        run();
      }
    });
    topK.addEventListener("input", () => (topKValue.textContent = topK.value));
    runBtn.addEventListener("click", () => run());
    cancelBtn.addEventListener("click", () => st.running && st.running.abort());

    function setStrategy(value) {
      st.strategy = value;
      strategyBtns.forEach((b) => b.setAttribute("aria-checked", String(b.dataset.value === value)));
    }
    seg.addEventListener("keydown", (e) => {
      if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
      const i = strategyBtns.findIndex((b) => b.dataset.value === st.strategy);
      const next = strategyBtns[(i + (e.key === "ArrowRight" ? 1 : strategyBtns.length - 1)) % strategyBtns.length];
      setStrategy(next.dataset.value);
      next.focus();
    });

    // -- backend status and mode
    const liveReady = () => !!(st.online && st.health && st.health.live);
    // Opened as a file: browsers block it from talking to any server.
    const wrongPlace = () => location.protocol === "file:";
    // Servers to try, in order. Without a saved address: the page's own
    // server; on the published site, then the hosted demo server; and last
    // the one start_demo.bat runs on this computer. The hosted server comes
    // before localhost so visitors are not asked for local network access.
    const PUBLIC_SERVER = (T.serverUrl || "").replace(/\/+$/, "");
    const onLocalhost = /^(localhost|127\.0\.0\.1|\[::1\])$/.test(location.hostname);
    const notApi = new Set(); // origins that answered 404: static hosting only
    const candidates = () => {
      const saved = savedBase();
      if (saved) return [saved];
      const own = defaultBase();
      const list = onLocalhost || location.protocol === "file:" ? [own, LOCAL_SERVER]
        : own === PUBLIC_SERVER ? [own] : [own, PUBLIC_SERVER, LOCAL_SERVER];
      return [...new Set(list)].filter((b) => b && !notApi.has(b));
    };
    // Chrome asks before a public site may reach this computer; once the
    // visitor blocks it, every request fails until they allow it again.
    async function localAccessDenied() {
      if (!navigator.permissions || /^(localhost|127\.0\.0\.1|\[::1\])$/.test(location.hostname)) return false;
      for (const name of ["loopback-network", "local-network-access"]) {
        try {
          return (await navigator.permissions.query({ name })).state === "denied";
        } catch (e) { /* not known to this browser */ }
      }
      return false;
    }

    function banner(kind, title, text) {
      return h("div", { class: `demo-banner ${kind}`, role: "alert" },
        iconNode(kind === "error" ? "x" : "dot"),
        h("div", null, h("strong", null, title), text ? h("p", null, text) : null));
    }

    // Applies the mode and the backend's state to the whole console.
    function render() {
      const recorded = st.recorded;
      st.mode = recorded ? "recorded" : "live";
      recordedBox.checked = recorded;
      modeBadge.className = `mode-badge ${st.mode}`;
      modeBadge.textContent = recorded ? "Recorded demo" : "Live";
      modeBadge.title = recorded ? "Replays runs recorded earlier; nothing here is live" : "Questions are answered live by the running server";
      topK.disabled = recorded;
      topKNote.textContent = recorded ? "Recorded runs used top-k = 5." : "";
      if (recorded) {
        topK.value = "5";
        topKValue.textContent = "5";
      }
      notice.hidden = !recorded;
      notice.replaceChildren();
      if (recorded) notice.append(h("span", { class: "mode-badge recorded" }, "Recorded demo"), h("p", null, T.recordedNote));

      const shown = [];
      const hostedSite = PUBLIC_SERVER && !savedBase() && !onLocalhost && location.protocol !== "file:";
      if (st.online === false && hostedSite) shown.push(banner("error", T.hostedOfflineTitle, T.hostedOfflineText));
      else if (st.online === false && st.blocked) shown.push(banner("error", T.blockedTitle, T.blockedText));
      else if (st.online === false) shown.push(banner("error", T.offlineTitle, recorded ? T.offlineRecorded : T.offlineText));
      else if (st.online && !st.health.live) shown.push(banner("error", T.noKeyTitle, T.noKeyText));
      if (wrongPlace()) shown.push(banner("warn", T.originTitle, T.originText));
      banners.replaceChildren(...shown);

      runBtn.disabled = !!st.running || (!recorded && !liveReady());
      runBtn.title = runBtn.disabled && !st.running ? "The demo server is not available" : "";
    }

    function setRecorded(on) {
      st.recorded = on;
      render();
      if (!on) results.querySelectorAll(".info-card").forEach((c) => c.remove());
    }
    recordedBox.addEventListener("change", () => setRecorded(recordedBox.checked));

    async function checkHealth() {
      if (st.checking) return;
      st.checking = true;
      let found = null;
      for (const base of candidates()) {
        const ctrl = new AbortController();
        // A free hosted server sleeps when idle and needs up to a minute to
        // wake, so it gets a long wait and a "waking up" message.
        const hosted = base === PUBLIC_SERVER && !st.online;
        const timer = setTimeout(() => ctrl.abort(), hosted ? 75000 : 2500);
        const wake = hosted && setTimeout(() => {
          statusPill.className = "status-pill checking";
          statusPill.lastChild.textContent = "Waking up the live server… (up to a minute)";
        }, 2500);
        try {
          const res = await fetch(`${base}/api/health`, { signal: ctrl.signal, cache: "no-store" });
          if (res.status === 404 && base !== LOCAL_SERVER && !savedBase()) notApi.add(base);
          const data = res.ok ? await res.json() : null;
          if (data && data.status === "ok") {
            found = { base, data };
            break;
          }
        } catch (e) { /* not reachable: try the next one */ }
        finally {
          clearTimeout(timer);
          clearTimeout(wake);
        }
      }
      if (found) {
        st.online = true;
        st.base = found.base;
        st.health = found.data;
        statusPill.className = `status-pill ${found.data.live ? "online" : "partial"}`;
        statusPill.lastChild.textContent = found.data.live ? `Backend online · ${found.data.model}` : "Backend online · no model key";
        if (document.activeElement !== baseInput) baseInput.value = st.base;
      } else {
        st.online = false;
        st.health = null;
        st.blocked = await localAccessDenied();
        statusPill.className = "status-pill offline";
        statusPill.lastChild.textContent = "Backend offline";
      }
      st.checking = false;
      render();
    }

    function saveBase(value) {
      const v = value.trim().replace(/\/+$/, "");
      if (v && !/^https?:\/\/[^\s/]+/i.test(v)) {
        baseMsg.textContent = "Enter a full http:// or https:// address.";
        return;
      }
      try {
        if (v) localStorage.setItem(API_BASE_KEY, v);
        else localStorage.removeItem(API_BASE_KEY);
      } catch (e) { /* storage blocked: use it for this visit only */ }
      st.base = v || defaultBase();
      baseInput.value = st.base;
      baseMsg.textContent = v ? "Saved. Checking the server…" : "Reset to the default. Checking the server…";
      checkHealth().then(() => (baseMsg.textContent = st.online ? "Connected." : "Not reachable yet; checking again every few seconds."));
    }

    // -- running
    const findRecorded = (q, strategy) =>
      D.runs.find((r) => r.strategy === strategy && r.question.trim().toLowerCase() === q.trim().toLowerCase());

    function showNotice(kind, text, extra) {
      results.replaceChildren(h("div", { class: `card info-card ${kind}` }, h("p", null, text), extra || null));
    }

    function recordedChoices() {
      return h("div", { class: "examples" }, D.questions.map((q) => h("button", { class: "example-chip", type: "button", onclick: () => {
        input.value = q;
        updateCount();
        run();
      } }, q)));
    }

    async function run(fromHistory) {
      if (st.running) return;
      const question = fromHistory ? fromHistory.question : input.value.trim();
      if (!question) {
        showNotice("warn", "Type a question first, or pick one of the examples.");
        input.focus();
        return;
      }
      if (question.length > MAX_CHARS) {
        showNotice("warn", `Questions are limited to ${MAX_CHARS} characters.`);
        return;
      }
      const strategy = fromHistory ? fromHistory.strategy : st.strategy;
      const strategies = strategy === "compare" ? ["react", "dfsdt"] : [strategy];
      const mode = fromHistory ? fromHistory.mode : st.mode;
      if (mode === "live" && !fromHistory && !liveReady()) {
        checkHealth();
        banners.firstElementChild && banners.firstElementChild.scrollIntoView({ behavior: reduce() ? "auto" : "smooth", block: "center" });
        return;
      }
      const recorded = mode === "recorded" && !fromHistory ? strategies.map((s) => findRecorded(question, s)) : null;
      if (recorded && recorded.some((r) => !r)) {
        showNotice("warn", `No recording exists for “${question}”. ${T.recordedOnly}`, recordedChoices());
        return;
      }

      const ctrl = new AbortController();
      st.running = ctrl;
      runBtn.disabled = true;
      cancelBtn.hidden = false;
      summary.hidden = true;
      const params = { question, topK: +topK.value };
      const grid = h("div", { class: `run-grid${strategies.length > 1 ? " compare" : ""}` });
      results.replaceChildren(
        h("div", { class: "asked" }, h("span", { class: "asked-lbl" }, "Question"), h("q", null, question),
          h("span", { class: `mode-badge ${mode}` }, mode === "live" ? "Live" : "Recorded demo")),
        grid
      );
      if (!fromHistory) results.scrollIntoView({ behavior: reduce() ? "auto" : "smooth", block: "start" });

      const panels = strategies.map((s, i) => {
        const rec = fromHistory ? fromHistory.runs[i] : recorded && recorded[i];
        return createPanel(grid, s, {
          recorded: mode === "recorded" ? (rec && rec.recorded_at ? rec.recorded_at.slice(0, 10) : "run") : null,
          topK: params.topK,
          instant: !!fromHistory,
        });
      });
      ctrl.signal.addEventListener("abort", () => panels.forEach((p) => p.hurry()));

      await Promise.all(panels.map((panel, i) => {
        const s = strategies[i];
        if (fromHistory) {
          const saved = fromHistory.runs[i];
          if (saved) return recordedRun(saved, panel, ctrl.signal, true);
          panel.fail(fromHistory.errors[i] || { code: "unknown", message: "This run did not finish." });
          return null;
        }
        if (mode === "recorded") return recordedRun(recorded[i], panel, ctrl.signal, false);
        return liveRun(st.base, { ...params, strategy: s }, panel, ctrl.signal);
      }));
      const states = await Promise.all(panels.map((p) => p.settled()));

      st.running = null;
      cancelBtn.hidden = true;
      render();
      const runs = states.map((s) => s.run);
      if (runs.length === 2 && runs[0] && runs[1]) showSummary(runs[0], runs[1]);
      if (!fromHistory) {
        addHistory({ question, strategy, mode, runs, errors: states.map((s) => s.error), when: new Date() });
        if (mode === "live" && states.some((s) => s.error && s.error.code === "offline")) checkHealth();
      }
    }

    // -- compare summary
    function showSummary(react, dfsdt) {
      const points = [];
      const okCalls = (r) => r.steps.filter((s) => s.status === "ok").length;
      const failed = (r) => r.steps.filter((s) => s.status === "error").length;
      if (!!react.final_answer !== !!dfsdt.final_answer) {
        points.push(`${react.final_answer ? "Only ReAct" : "Only DFSDT"} reached an answer.`);
      } else if (!react.final_answer) points.push("Neither strategy reached an answer.");
      points.push(react.num_tool_calls === dfsdt.num_tool_calls
        ? `Both made ${react.num_tool_calls} tool call${react.num_tool_calls === 1 ? "" : "s"}.`
        : `ReAct made ${react.num_tool_calls} tool call${react.num_tool_calls === 1 ? "" : "s"}, DFSDT made ${dfsdt.num_tool_calls}.`);
      const a = new Set(react.tools_called), b = new Set(dfsdt.tools_called);
      const onlyA = [...a].filter((t) => !b.has(t)), onlyB = [...b].filter((t) => !a.has(t));
      if (!onlyA.length && !onlyB.length) points.push(a.size ? `They used the same tools: ${[...a].join(", ")}.` : "Neither used a tool.");
      else {
        if (onlyA.length) points.push(`Only ReAct used ${onlyA.join(", ")}.`);
        if (onlyB.length) points.push(`Only DFSDT used ${onlyB.join(", ")}.`);
      }
      const backtracks = dfsdt.tree ? dfsdt.tree.nodes.filter((n) => n.status === "error" || n.status === "dead_end").length : 0;
      points.push(backtracks
        ? `DFSDT backtracked ${backtracks} time${backtracks === 1 ? "" : "s"} over ${dfsdt.tree.explored} explored branches.`
        : "DFSDT never had to backtrack, so it followed a single path like ReAct.");
      if (failed(react)) points.push(`ReAct had ${failed(react)} failed call${failed(react) === 1 ? "" : "s"} and retried in place.`);
      const diff = react.latency_ms - dfsdt.latency_ms;
      if (Math.abs(diff) >= 300) points.push(`${diff > 0 ? "DFSDT" : "ReAct"} finished ${fmtLatency(Math.abs(diff))} sooner.`);
      else points.push("They took about the same time.");
      if (okCalls(react) && okCalls(dfsdt) && react.final_answer && dfsdt.final_answer && react.final_answer.trim() === dfsdt.final_answer.trim()) {
        points.push("Their answers are word for word the same.");
      }
      summary.replaceChildren(h("div", { class: "card summary-card" },
        h("h3", null, iconNode("chart"), "Where they differ"),
        h("ul", null, points.map((p) => h("li", null, p)))));
      summary.hidden = false;
    }

    // -- history (this page visit only)
    function addHistory(entry) {
      st.history.unshift(entry);
      st.history = st.history.slice(0, 5);
      historyEl.hidden = false;
      historyEl.replaceChildren(
        h("h3", null, iconNode("history"), "Recent questions"),
        h("ol", { class: "history-list" }, st.history.map((e) => {
          const ok = e.runs.every(Boolean);
          const answer = e.runs.find((r) => r && r.final_answer);
          return h("li", null, h("button", { class: "history-item", type: "button", onclick: () => {
            if (st.running) return;
            input.value = e.question;
            updateCount();
            run(e);
          } },
            h("span", { class: "h-q" }, e.question),
            h("span", { class: "h-meta" },
              `${e.strategy === "compare" ? "Compare" : STRATEGY_LABEL[e.strategy]} · ${e.mode === "live" ? "Live" : "Recorded"} · ${e.when.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}${ok ? "" : " · failed"}`),
            answer ? h("span", { class: "h-a" }, clip(answer.final_answer.replace(/\*\*/g, "").replace(/\s+/g, " "), 120)) : null));
        })),
        h("p", { class: "settings-note" }, "Kept for this visit only. Click one to show its results again.")
      );
    }

    render();
    checkHealth();
    // Every 3 seconds, so the page goes live as soon as the server is up.
    setInterval(() => {
      if (!document.hidden) checkHealth();
    }, 3000);
    document.addEventListener("visibilitychange", () => !document.hidden && checkHealth());
  };

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
