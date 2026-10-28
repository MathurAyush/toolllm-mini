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
        parts.push(`<text class="tick" x="${m.l - 8}" y="${y(v) + 4}" text-anchor="end">${esc(spec.percent ? Math.round(v * 100) + "%" : fmt(v, { decimals: spec.decimals != null ? 1 : null }))}</text>`);
      }

      const gw = pw / spec.groups.length;
      const gap = 5;
      const bw = Math.min(46, (gw * 0.76 - (ns - 1) * gap) / ns);
      const inner = bw * ns + (ns - 1) * gap;
      const showLabels = bw >= 26;
      spec.groups.forEach((g, gi) => {
        const x0 = m.l + gi * gw + (gw - inner) / 2;
        spec.series.forEach((s, si) => {
          const x = x0 + si * (bw + gap);
          const v = spec.values[gi][si];
          const d = ((gi * ns + si) * 0.07).toFixed(2);
          const cx = x + bw / 2;
          if (v == null) {
            const top = m.t + ph * 0.55;
            parts.push(`<rect class="tbd-bar" x="${x}" y="${top}" width="${bw}" height="${ph * 0.45}" rx="4"><title>${esc(s.name)}: not measured yet</title></rect>`);
            parts.push(`<text class="tbd-text" x="${cx}" y="${top - 8}" font-size="${bw < 30 ? 9 : 11}">TBD</text>`);
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
        parts.push(`<text class="glabel" x="${m.l + gi * gw + gw / 2}" y="${H - m.b + 20}">${lines
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

  PAGES.existing = (main) => renderDeck(main, C.slides.filter((s) => s.n <= 3), { next: C.existingNext });

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
