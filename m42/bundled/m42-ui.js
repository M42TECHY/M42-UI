/* M42 UI: premium dashboard components (see m42-ui.css). No dependencies; Bootstrap Icons for the icons.
   The page writes the parts with data-* attributes and feeds values:
     M42UI.set('temp', 28.4)            stat card: count-up, delta, sparkline, warn/bad colours
     M42UI.gauge('hum', 64)             ring gauge (data-max, default 100)
     M42UI.push('trend', [28.4, 64])    trend chart, one value per series (data-series="Temperature,Humidity")
     M42UI.banner('pred', {title: 'Rain likely', text: 'Humidity 86%', icon: 'bi-cloud-rain', tone: 'warn'})
     M42UI.status('conn', 'online' | 'offline' | 'demo', 'Live')
     M42UI.touch()                      "Updated just now" in every .m42-updated
     M42UI.demo('temp', 28, 4)          a changing demo reading around 28 (+-4), smooth from one call to the next
     M42UI.demo('orders', 48, 4, 0)     the same, whole numbers (a count) */
(function () {
  "use strict";
  // M42_STILL: M42's own checks and pictures measure the finished page (no entrance or reveal half way)
  var reduce = !!window.M42_STILL || (window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  var page = { item: "", price: 0, picked: [] };  // what the page's binds show
  var COLORS = ["var(--m42-accent)", "var(--m42-accent-2)", "var(--m42-accent-3)", "#22c55e", "#f59e0b"];
  var state = {}, walk = {}, lastTouch = null;

  function $(id) { return typeof id === "string" ? document.getElementById(id) : id; }
  function el(tag, cls, html) { var e = document.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; return e; }
  function num(v, d) {  // 175666 -> 1,75,666 / 175,666 (the viewer's own locale), decimals kept
    return Number(v).toLocaleString(undefined, { minimumFractionDigits: d, maximumFractionDigits: d });
  }
  function decimalsOf(e, v) { var d = e.getAttribute("data-decimals"); return d != null ? +d : (Math.abs(v) < 100 && v % 1 ? 1 : 0); }

  function defs() {
    if (document.getElementById("m42-defs")) return;
    var s = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    s.setAttribute("id", "m42-defs"); s.setAttribute("width", "0"); s.setAttribute("height", "0");
    s.style.position = "absolute";
    s.innerHTML = '<defs><linearGradient id="m42-fade" x1="0" y1="0" x2="0" y2="1">' +
      '<stop offset="0" stop-color="rgb(var(--m42-accent-rgb))" stop-opacity=".35"/>' +
      '<stop offset="1" stop-color="rgb(var(--m42-accent-rgb))" stop-opacity="0"/></linearGradient>' +
      '<linearGradient id="m42-ring-grad" x1="0" y1="0" x2="1" y2="1"><stop offset="0" style="stop-color:var(--m42-accent-2)"/>' +
      '<stop offset="1" stop-color="rgb(var(--m42-accent-rgb))"/></linearGradient></defs>';
    document.body.appendChild(s);
  }

  function title(e) {
    var icon = e.getAttribute("data-icon") || "bi-activity";
    return el("div", "m42-title", '<span class="m42-chip"><i class="bi ' + icon + '"></i></span><span>' +
      (e.getAttribute("data-label") || "") + "</span>");
  }

  function renderStat(e) {
    if (e.querySelector(".m42-value")) return;
    e.appendChild(title(e));
    var unit = e.getAttribute("data-unit") || "", money = /^[₹$€£¥]$/.test(unit);  // ₹ goes before the number
    e.appendChild(el("div", "m42-value", (money ? '<span class="m42-unit">' + unit + "</span>" : "") +
      '<span class="m42-num m42-skeleton">00.0</span>' + (money ? "" : '<span class="m42-unit">' + unit + "</span>")));
    e.appendChild(el("div", "m42-foot", '<span class="m42-delta">waiting…</span>' +
      '<svg class="m42-spark" viewBox="0 0 110 34" preserveAspectRatio="none"><path class="area"/><path class="line"/></svg>'));
  }

  function renderGauge(e) {
    if (e.querySelector(".m42-ring")) return;
    e.appendChild(title(e));
    var c = 2 * Math.PI * 58;
    var ring = el("div", "m42-ring", '<svg viewBox="0 0 140 140"><circle class="track" cx="70" cy="70" r="58"/>' +
      '<circle class="bar" cx="70" cy="70" r="58" stroke-dasharray="' + c + '" stroke-dashoffset="' + c + '"/></svg>' +
      '<div class="m42-value"><span class="m42-num m42-skeleton">00</span><span class="m42-unit">' +
      (e.getAttribute("data-unit") || "") + "</span></div>");
    e.appendChild(ring);
  }

  function renderChart(e) {
    if (e.querySelector("svg")) return;
    var series = (e.getAttribute("data-series") || "Value").split(",").map(function (s) { return s.trim(); });
    var head = el("div", "d-flex flex-wrap justify-content-between align-items-center gap-2 mb-2");
    head.appendChild(el("div", "m42-title mb-0", '<span class="m42-chip"><i class="bi ' + (e.getAttribute("data-icon") ||
      "bi-graph-up") + '"></i></span><span>' + (e.getAttribute("data-label") || "Trend") + "</span>"));
    head.appendChild(el("div", "m42-legend", series.map(function (s, i) {
      return '<span><i style="background:' + COLORS[i % COLORS.length] + '"></i>' + s + "</span>"; }).join("")));
    e.appendChild(head);
    var svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("viewBox", "0 0 600 220"); svg.setAttribute("preserveAspectRatio", "none");
    e.appendChild(svg);
    state[e.id] = { series: series, data: series.map(function () { return []; }) };
    drawChart(e);
  }

  function renderBanner(e) {
    if (e.querySelector("h3")) return;
    e.innerHTML = '<span class="m42-chip"><i class="bi ' + (e.getAttribute("data-icon") || "bi-stars") + '"></i></span>' +
      '<div><h3>' + (e.getAttribute("data-title") || "") + '</h3><p>' + (e.getAttribute("data-text") || "") + "</p></div>";
  }

  function countTo(span, from, to, d) {
    if (reduce || from == null || isNaN(from)) { span.textContent = num(to, d); return; }
    var t0 = performance.now(), dur = 700;
    function step(t) {
      var k = Math.min(1, (t - t0) / dur), ease = 1 - Math.pow(1 - k, 3);
      span.textContent = num(from + (to - from) * ease, d);
      if (k < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  }

  function level(e, v) {
    var warn = e.getAttribute("data-warn"), bad = e.getAttribute("data-bad"),
      below = (e.getAttribute("data-dir") || "above") === "below";
    var over = function (lim) { return lim != null && lim !== "" && (below ? v <= +lim : v >= +lim); };
    e.classList.toggle("is-bad", over(bad));
    e.classList.toggle("is-warn", !over(bad) && over(warn));
  }

  function spark(e, hist) {
    var line = e.querySelector(".m42-spark .line"), area = e.querySelector(".m42-spark .area");
    if (!line || hist.length < 2) return;
    var lo = Math.min.apply(null, hist), hi = Math.max.apply(null, hist), span = hi - lo || 1;
    var pts = hist.map(function (v, i) { return [i * 110 / (hist.length - 1), 30 - (v - lo) / span * 26]; });
    var d = pts.map(function (p, i) { return (i ? "L" : "M") + p[0].toFixed(1) + " " + p[1].toFixed(1); }).join(" ");
    line.setAttribute("d", d);
    area.setAttribute("d", d + " L110 34 L0 34 Z");
  }

  var M42UI = {
    set: function (id, value, opts) {
      var e = $(id); if (!e) return;
      renderStat(e);
      var v = +value, s = state[e.id] = state[e.id] || { hist: [] }, span = e.querySelector(".m42-num");
      var d = (opts && opts.decimals != null) ? opts.decimals : decimalsOf(e, v);
      span.classList.remove("m42-skeleton");
      countTo(span, s.last, v, d);
      var delta = e.querySelector(".m42-delta");
      if (s.last != null) {
        var diff = v - s.last;
        delta.className = "m42-delta" + (diff > 0 ? " up" : diff < 0 ? " down" : "");
        delta.textContent = (diff > 0 ? "▲ " : diff < 0 ? "▼ " : "• ") + num(Math.abs(diff), d) + " " + (e.getAttribute("data-unit") || "");
      } else { delta.textContent = "live"; }
      s.last = v; s.hist.push(v); if (s.hist.length > 30) s.hist.shift();
      spark(e, s.hist); level(e, v);
      e.classList.remove("m42-flash"); void e.offsetWidth; e.classList.add("m42-flash");
    },
    gauge: function (id, value) {
      var e = $(id); if (!e) return;
      renderGauge(e);
      var max = +(e.getAttribute("data-max") || 100), v = +value, s = state[e.id] = state[e.id] || {};
      var bar = e.querySelector(".bar"), c = 2 * Math.PI * 58, span = e.querySelector(".m42-num");
      bar.setAttribute("stroke-dashoffset", c * (1 - Math.max(0, Math.min(1, v / max))));
      span.classList.remove("m42-skeleton");
      countTo(span, s.last, v, decimalsOf(e, v)); s.last = v; level(e, v);
    },
    push: function (id, values) {
      var e = $(id); if (!e) return;
      renderChart(e);
      var s = state[e.id], max = +(e.getAttribute("data-points") || 30);
      [].concat(values).forEach(function (v, i) { if (s.data[i]) { s.data[i].push(+v); if (s.data[i].length > max) s.data[i].shift(); } });
      drawChart(e);
    },
    banner: function (id, o) {
      var e = $(id); if (!e) return;
      renderBanner(e); o = o || {};
      e.className = e.className.replace(/\btone-\w+/g, "").trim() + (o.tone ? " tone-" + o.tone : "");
      if (o.icon) e.querySelector(".m42-chip").innerHTML = '<i class="bi ' + o.icon + '"></i>';
      if (o.title != null) e.querySelector("h3").textContent = o.title;
      if (o.text != null) e.querySelector("p").textContent = o.text;
    },
    status: function (id, kind, text) {
      var e = $(id); if (!e) return;
      e.className = "m42-status " + (kind || "");
      e.textContent = text || ({ online: "Live", offline: "Offline", demo: "Demo data" })[kind] || kind;
    },
    touch: function () { lastTouch = Date.now(); tick(); },
    // the values picked in a .m42-pick-grid / .m42-chips (data-value, else the text)
    picked: function (box) {
      box = $(box); if (!box) return [];
      return [].map.call(box.querySelectorAll(".m42-pick.selected, .m42-chip-btn.active"), function (c) {
        return c.getAttribute("data-value") || c.textContent.trim(); });
    },
    demo: function (key, base, spread, digits) {  // digits: 0 for counts (orders, staff)
      if (Array.isArray(base)) {  // a chart: one demo value per series
        var vals = base.map(function (b, i) { return M42UI.demo(key + "#" + i, b, spread, digits); });
        if ($(key) && $(key).classList.contains("m42-chart")) M42UI.push(key, vals);
        return vals;
      }
      if (typeof base !== "number" || !isFinite(base)) {  // a rule's sum of cells that are not numbers (NaN, POS run 3):
        var m = $(key) ? String($(key).textContent).match(/-?\d[\d,]*(\.\d+)?/) : null;  // the card's own first number
        var shown = walk[key] != null && isFinite(walk[key]) ? walk[key] : m ? parseFloat(m[0].replace(/,/g, "")) : NaN;
        if (!isFinite(shown)) return 0;
        base = shown;
      }
      spread = spread == null || !isFinite(spread) ? Math.abs(base) * .1 || 1 : spread;
      var w = walk[key] == null || !isFinite(walk[key]) ? base : walk[key];
      w += (Math.random() - .5) * spread * .5;
      w = Math.max(base - spread, Math.min(base + spread, w));
      if (base >= 0 && w < 0) w = 0;  // a count, a total: never below zero ("-1 bills")
      walk[key] = w;
      var v = digits === 0 || Math.abs(base) >= 100 ? Math.round(w) : Math.round(w * 10) / 10, e = $(key);
      if (e && e.classList.contains("m42-stat")) M42UI.set(key, v);  // demo('users', 1200, 50) shows it too
      else if (e && e.classList.contains("m42-gauge")) M42UI.gauge(key, v);
      return v;
    },
    theme: function (name) {
      var root = document.documentElement;
      name = name || (root.getAttribute("data-m42-theme") === "dark" ? "light" : "dark");
      root.setAttribute("data-m42-theme", name);
      [].forEach.call(document.querySelectorAll(".m42-theme-toggle"), function (b) {
        b.innerHTML = '<i class="bi ' + (name === "dark" ? "bi-sun" : "bi-moon-stars") + '"></i>';
        b.setAttribute("aria-label", name === "dark" ? "Light theme" : "Dark theme");
      });
    }
  };

  function drawChart(e) {
    var s = state[e.id], svg = e.querySelector("svg"); if (!s || !svg) return;
    var all = [].concat.apply([], s.data), W = 600, H = 220, P = 28;
    var lo = all.length ? Math.min.apply(null, all) : 0, hi = all.length ? Math.max.apply(null, all) : 1;
    if (hi - lo < 1) { hi += .5; lo -= .5; }
    var pad = (hi - lo) * .15; lo -= pad; hi += pad;
    var y = function (v) { return H - P - (v - lo) / (hi - lo) * (H - 2 * P); };
    var html = '<g class="grid">';
    for (var g = 0; g <= 4; g++) {
      var gv = lo + (hi - lo) * g / 4, gy = y(gv);
      html += '<line x1="34" x2="' + W + '" y1="' + gy + '" y2="' + gy + '"/><text x="0" y="' + (gy + 4) + '">' + gv.toFixed(0) + "</text>";
    }
    html += "</g>";
    s.data.forEach(function (d, i) {
      if (d.length < 2) return;
      var n = +(e.getAttribute("data-points") || 30), step = (W - 40) / (n - 1), x0 = W - (d.length - 1) * step;
      var path = d.map(function (v, k) { return (k ? "L" : "M") + (x0 + k * step).toFixed(1) + " " + y(v).toFixed(1); }).join(" ");
      if (i === 0) html += '<path d="' + path + " L" + W + " " + (H - P) + " L" + x0.toFixed(1) + " " + (H - P) + ' Z" fill="url(#m42-fade)"/>';
      html += '<path class="line" d="' + path + '" style="stroke:' + COLORS[i % COLORS.length] + '"/>';
      var last = d[d.length - 1];
      html += '<circle cx="' + W + '" cy="' + y(last).toFixed(1) + '" r="4" style="fill:' + COLORS[i % COLORS.length] + '"/>';
    });
    svg.innerHTML = html;
  }

  // what the page's binds show: the chosen row, the picks, and the total (picks x price, or the price)
  function binds() {
    var grid = document.querySelector("[data-m42-picks]");
    var price = page.price || (grid && parseFloat(grid.getAttribute("data-price"))) || 0;
    var count = (page.picked || []).length;
    var total = price * (grid ? count : (page.item ? 1 : 0));
    var values = { item: page.item || "—", picked: count ? page.picked.join(", ") : "—", count: String(count),
      price: price ? "₹" + price.toLocaleString("en-IN") : "—", total: "₹" + total.toLocaleString("en-IN") };
    [].forEach.call(document.querySelectorAll("[data-m42-bind]"), function (el) {
      var k = el.getAttribute("data-m42-bind");
      if (k in values && el.textContent !== values[k]) {
        el.textContent = values[k];
        if (!reduce && el.animate) el.animate([{ transform: "scale(1.12)" }, { transform: "none" }], { duration: 300 });
      }
    });
  }
  M42UI.page = page;
  M42UI.binds = binds;

  function tick() {
    var now = new Date();
    [].forEach.call(document.querySelectorAll(".m42-clock"), function (c) {
      c.textContent = now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }); });
    if (lastTouch) {
      var s = Math.round((Date.now() - lastTouch) / 1000);
      [].forEach.call(document.querySelectorAll(".m42-updated"), function (u) {
        u.textContent = s < 3 ? "Updated just now" : "Updated " + s + "s ago"; });
    }
  }

  function init() {
    document.body.classList.add("m42-ui");
    if (window.M42_STILL) document.documentElement.classList.add("m42-still");  // M42's checks: the end state
    // the page's own theme, always: a theme saved by an old page's light / dark button made every page opened after it
    // dark (or light), whatever was chosen for it (2026-11-12)
    M42UI.theme(document.documentElement.getAttribute("data-m42-theme") || "light");
    defs();
    [].forEach.call(document.querySelectorAll(".m42-stat"), renderStat);
    [].forEach.call(document.querySelectorAll(".m42-gauge"), renderGauge);
    [].forEach.call(document.querySelectorAll(".m42-chart"), renderChart);
    [].forEach.call(document.querySelectorAll(".m42-banner"), renderBanner);
    [].forEach.call(document.querySelectorAll(".m42-status:empty"), function (e) { M42UI.status(e, "", "Connecting…"); });
    [].forEach.call(document.querySelectorAll(".m42-theme-toggle"), function (b) {
      b.addEventListener("click", function () { M42UI.theme(); }); });
    var cards = document.querySelectorAll(".m42-stat, .m42-gauge, .m42-chart, .m42-banner, .m42-card");
    var mv = window.M42_MOTION || {};  // (anime.js brings them in itself; "none": no motion)
    if (!reduce && mv.level !== "none" && !window.anime) [].forEach.call(cards, function (c, i) {
      c.classList.add("m42-enter");
      setTimeout(function () { c.classList.add("m42-entered"); c.classList.remove("m42-enter"); }, 80 + i * 70);
    });
    tick(); setInterval(tick, 1000);
    site();
    widgets();
  }

  /* ---- any website: the motion and the small things a premium page has, with no code in the page ---- */
  var REVEAL = ".m42-section-head, .m42-feature, .m42-price, .m42-quote, .m42-steps > li, .m42-gallery > *, .m42-cta, " +
    ".m42-visual, .m42-section .m42-card, .m42-section .card, .m42-table, .m42-form, [data-m42-reveal]:not(html)";  // (<html> carries the page's data-m42-reveal too: it was animated, fixed bars lost)
  var HOVER = ".m42-feature, .m42-price, .m42-quote, .m42-item, .m42-card, .m42-tile, .m42-lx-card, .m42-lx-zz, .m42-w-lt, .card";
  // a section given its own reveal by an edit: its repeated things (cards, rows, list lines) come in one by one too
  // (2026-11-16: "fade-up" on a table moved only its heading, as the whole page already did: nothing looked new)
  function ownGroups(scope) {
    var sel = '[data-m42-sec-reveal]:not([data-m42-sec-reveal="none"])', out = [];
    var secs = [].slice.call(scope.querySelectorAll(sel));
    if (scope.matches && scope.matches(sel)) secs.unshift(scope);
    secs.forEach(function (s) {
      var best = [];
      [].slice.call(s.querySelectorAll("*")).forEach(function (p) {
        if (p.children.length < 2) return;
        var g = {};
        [].forEach.call(p.children, function (c) { var k = c.tagName + "." + (c.classList[0] || ""); (g[k] = g[k] || []).push(c); });
        Object.keys(g).forEach(function (k) { if (g[k].length >= 2 && g[k].length > best.length && g[k].some(function (c) { return (c.textContent || "").trim(); })) best = g[k]; });
      });
      out = out.concat(best);
    });
    return out;
  }
  function revealItems(scope) {
    var a = [].slice.call(scope.querySelectorAll(REVEAL));
    ownGroups(scope).forEach(function (x) { if (a.indexOf(x) < 0) a.push(x); });
    return a.filter(function (x) { return !x.closest(".m42-enter, .m42-entered"); });
  }
  // every popup (.modal) moved to <body> before anything opens it: inside a section that moves (its reveal leaves a
  // transform on it) the popup was drawn UNDER Bootstrap's dark backdrop, and its form could not be typed in ("Add
  // Staff: the overlay blocks the inputs", 2026-11-17); its button still finds it by its id
  function modalsToBody() {
    [].slice.call(document.querySelectorAll(".modal")).forEach(function (m) {
      if (m.parentElement !== document.body) document.body.appendChild(m);
    });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", modalsToBody); else modalsToBody();
  // charts drawn by Chart.js when the user named it (widgets._chartjs): the page's own colours, its font
  function chartjs() {
    if (!window.Chart) return;
    var css = getComputedStyle(document.documentElement), v = function (n, d) { return (css.getPropertyValue(n) || "").trim() || d; };
    var tones = [v("--m42-accent", "#4f46e5"), v("--m42-accent-2", "#06b6d4"), v("--m42-accent-3", "#f59e0b"), "#10b981", "#ef4444", "#8b5cf6"];
    window.Chart.defaults.font.family = getComputedStyle(document.body).fontFamily;
    window.Chart.defaults.color = v("--m42-muted", "#64748b");
    [].slice.call(document.querySelectorAll("canvas[data-m42-chartjs]")).forEach(function (cv) {
      var c; try { c = JSON.parse(cv.getAttribute("data-m42-chartjs")); } catch (x) { return; }
      var ring = c.type === "doughnut";
      new window.Chart(cv, { type: c.type, data: { labels: c.labels, datasets: c.series.map(function (s, k) {
        return { label: s.name, data: s.values, borderColor: ring ? "#fff" : tones[k % 6], tension: .35, fill: false,
                 backgroundColor: ring ? tones.slice(0, s.values.length) : tones[k % 6] + (c.type === "bar" ? "" : "33"),
                 borderRadius: c.type === "bar" ? 6 : 0, pointRadius: 3 }; }) },
        options: { responsive: true, maintainAspectRatio: false, animation: window.M42_STILL ? false : undefined,
                   plugins: { legend: { display: ring || c.series.length > 1, position: "bottom" } },
                   scales: ring ? {} : { y: { beginAtZero: true, grid: { color: "rgba(100,116,139,.15)" } }, x: { grid: { display: false } } } } });
    });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", chartjs); else chartjs();
  // (M42's own check of an edit counts what moves in a part: editcheck.py)
  window.M42Reveal = { items: revealItems, hoverItems: function (scope) { return [].slice.call(scope.querySelectorAll(HOVER)); } };

  function counter(e) {
    var to = parseFloat(e.getAttribute("data-m42-count")), d = (String(to).split(".")[1] || "").length;
    var suffix = e.getAttribute("data-suffix") || "", prefix = e.getAttribute("data-prefix") || "";
    if (isNaN(to)) return;
    var mv = window.M42_MOTION || {};
    if (reduce || mv.level === "none" || mv.counters === false) { e.textContent = prefix + to.toLocaleString(undefined, { minimumFractionDigits: d }) + suffix; return; }
    var t0 = performance.now(), dur = 1400;
    (function step(t) {
      var k = Math.min(1, (t - t0) / dur), v = to * (1 - Math.pow(1 - k, 3));
      e.textContent = prefix + v.toLocaleString(undefined, { minimumFractionDigits: d, maximumFractionDigits: d }) + suffix;
      if (k < 1) requestAnimationFrame(step);
    })(t0);
  }

  // sections as the page chose (anime.js): fade-up, cards one after another, or a zoom; once each
  function animeReveal(items, counters, MOv) {
    var an = window.anime, page = MOv.level === "none" ? "none" : (MOv.reveal || "fade-up");
    var kindOf = function (x) { var o = x.closest("[data-m42-sec-reveal]"); return o ? o.getAttribute("data-m42-sec-reveal") : page; };
    items = items.filter(function (x) { return kindOf(x) !== "none"; });  // (an edit can give one section its own)
    if (!items.length) { counters.forEach(counter); return; }
    items.forEach(function (x) { x.style.opacity = 0; });
    var io = new IntersectionObserver(function (es) {
      es.forEach(function (en) {
        if (!en.isIntersecting) return;
        var x = en.target; io.unobserve(x);
        if (x.hasAttribute("data-m42-count")) { counter(x); return; }
        var sib = x.parentElement ? [].indexOf.call(x.parentElement.children, x) : 0;
        var kind = kindOf(x);
        var props = { targets: x, opacity: [0, 1], duration: MOv.level === "lively" ? 850 : 620, easing: "easeOutCubic",
                      delay: Math.min(sib, 6) * (kind === "stagger" ? 120 : 60) };
        if (kind === "zoom") props.scale = [.92, 1]; else props.translateY = [kind === "stagger" ? 38 : 22, 0];
        an(props);
      });
    }, { threshold: .12, rootMargin: "0px 0px -40px 0px" });
    items.concat(counters).forEach(function (x) { io.observe(x); });
  }

  function formDone(f) {
    var msg = f.getAttribute("data-m42-done") || "Thank you! We'll get back to you soon.";
    if (window.M42Notify && window.M42Notify(msg, "success", "Sent")) { f.reset(); f.classList.remove("was-validated"); return; }
    if (window.Swal) { window.Swal.fire({ title: "Sent", text: msg, icon: "success", confirmButtonColor: getComputedStyle(document.documentElement).getPropertyValue("--bs-primary").trim() || undefined }); }
    else if (window.toastr) { window.toastr.success(msg); }
    else { var box = f.querySelector(".m42-form-done") || el("div", "m42-form-done mt-3"); box.innerHTML = '<i class="bi bi-check-circle-fill"></i> ' + msg; f.appendChild(box); }
    f.reset(); f.classList.remove("was-validated");
  }

  function site() {
    var nav = document.querySelector(".m42-nav");
    // the reading bar at the top and the back-to-top button: only when the page chose them (pagebuild, the 4B's
    // choice: a long article or blog) and, for the button, only on a page several screens long (2026-11-11: they were
    // on every page)
    var H = document.documentElement, long = H.scrollHeight > window.innerHeight * 2.5;
    var progress = H.getAttribute("data-m42-progress") === "1" ? el("div", "m42-progress") : null;
    if (progress) { progress.setAttribute("aria-hidden", "true"); document.body.appendChild(progress); }
    var top = H.getAttribute("data-m42-to-top") === "1" && long ? el("button", "m42-top", '<i class="bi bi-arrow-up"></i>') : null;
    if (top) {
      top.type = "button"; top.setAttribute("aria-label", "Back to top");
      top.addEventListener("click", function () { window.scrollTo({ top: 0, behavior: reduce ? "auto" : "smooth" }); });
      document.body.appendChild(top);
    }
    var links = [].slice.call(document.querySelectorAll('.m42-nav a.nav-link[href^="#"], .m42-side a.m42-side-link[href^="#"]'));
    function onScroll() {
      var y = window.scrollY || document.documentElement.scrollTop, h = document.documentElement.scrollHeight - window.innerHeight;
      if (nav) nav.classList.toggle("is-scrolled", y > 20);
      if (progress) progress.style.width = (h > 0 ? y / h * 100 : 0) + "%";
      if (top) top.classList.toggle("is-shown", y > window.innerHeight * .8);
      // the part nearest the top that has reached it; on a tie the earlier entry (a dashboard's banner and its
      // calendar column start on one line: Calendar was marked, not Dashboard)
      var current = null, best = -Infinity;
      links.forEach(function (a) { var h = a.getAttribute("href"), s = h.length > 1 ? document.getElementById(h.slice(1)) : null;
        if (!s) return; var t = s.getBoundingClientRect().top;
        if (t < window.innerHeight * .35 && t > best + 1) { best = t; current = a; } });
      // at the very top: the first entry that goes to a part of this page (Dashboard), whatever the screen's height
      var parts = links.filter(function (a) { return a.getAttribute("href").length > 1; });
      if (y < 8 && parts.length) current = parts[0];
      links.forEach(function (a) { a.classList.toggle("active", a === current); });
    }
    window.addEventListener("scroll", onScroll, { passive: true }); onScroll();
    links.forEach(function (a) { a.addEventListener("click", function () {  // the phone menu closes after a tap
      var open = document.querySelector(".m42-nav .navbar-collapse.show");
      if (open && window.bootstrap && window.bootstrap.Collapse) window.bootstrap.Collapse.getOrCreateInstance(open).hide();
      var side = document.querySelector(".m42-side.show");  // the app sidebar on a phone closes too
      if (side && window.bootstrap && window.bootstrap.Offcanvas) window.bootstrap.Offcanvas.getOrCreateInstance(side).hide(); }); });
    // the app's top-bar search: rows, list rows and cards on the page that don't have the words are hidden
    [].slice.call(document.querySelectorAll("input[data-m42-find]")).forEach(function (inp) {
      inp.addEventListener("input", function () {
        var q = inp.value.trim().toLowerCase();
        [].slice.call(document.querySelectorAll(".m42-table tbody tr, .m42-row, .m42-item")).forEach(function (r) {
          r.style.display = !q || r.textContent.toLowerCase().indexOf(q) >= 0 ? "" : "none"; }); }); });
    // reveal on scroll, staggered inside each group; numbers count up when they come into view
    var items = revealItems(document);
    var counters = [].slice.call(document.querySelectorAll("[data-m42-count]"));
    var MOv = window.M42_MOTION || {};
    var ownReveal = !!document.querySelector("[data-m42-sec-reveal]:not([data-m42-sec-reveal='none'])");
    if (!("IntersectionObserver" in window) || reduce || (MOv.level === "none" && !(ownReveal && window.anime))) { counters.forEach(counter); }
    else if (window.AOS && window.AOS.init) {  // the user named AOS: it reveals the parts, staggered in each group
      items.forEach(function (x) {
        if (x.hasAttribute("data-aos")) return;
        var sib = x.parentElement ? [].indexOf.call(x.parentElement.children, x) : 0;
        x.setAttribute("data-aos", "fade-up");
        x.setAttribute("data-aos-delay", String(Math.min(sib, 6) * 90));
      });
      window.AOS.init({ once: true, duration: 700, offset: 40 });
      var ioC = new IntersectionObserver(function (es) { es.forEach(function (en) { if (en.isIntersecting) { counter(en.target); ioC.unobserve(en.target); } }); });
      counters.forEach(function (x) { ioC.observe(x); });
    }
    else if (window.anime) { animeReveal(items, counters, MOv); }
    else {  // (not "return": the ripple, tilt and forms below are for everyone)
    items.forEach(function (x) { x.classList.add("m42-reveal"); });
    var io = new IntersectionObserver(function (es) {
      es.forEach(function (en) {
        if (!en.isIntersecting) return;
        var x = en.target, sib = x.parentElement ? [].indexOf.call(x.parentElement.children, x) : 0;
        if (x.hasAttribute("data-m42-count")) counter(x);
        else setTimeout(function () { x.classList.add("is-visible"); }, Math.min(sib, 6) * 90);
        io.unobserve(x);
      });
    }, { threshold: .12, rootMargin: "0px 0px -40px 0px" });
    items.concat(counters).forEach(function (x) { io.observe(x); });
    }
    // buttons: a ripple where they are pressed
    document.addEventListener("pointerdown", function (ev) {
      var b = ev.target.closest && ev.target.closest(".m42-btn, .m42-btn-ghost"); if (!b) return;
      var r = b.getBoundingClientRect(), s = Math.max(r.width, r.height), w = el("span", "m42-ripple");
      w.style.width = w.style.height = s + "px"; w.style.left = (ev.clientX - r.left - s / 2) + "px"; w.style.top = (ev.clientY - r.top - s / 2) + "px";
      b.appendChild(w); setTimeout(function () { w.remove(); }, 650);
    });
    // picks (seats, slots, sizes) and filter chips: they select themselves; the container tells the page
    // ("m42:change" with the selected values; data-max on a pick grid, data-single on chips for one at a time)
    document.addEventListener("click", function (ev) {
      var p = ev.target.closest && ev.target.closest(".m42-pick, .m42-chip-btn"); if (!p || p.disabled) return;
      var box = p.parentElement, isPick = p.classList.contains("m42-pick"), on = isPick ? "selected" : "active";
      if (p.classList.contains("taken") || p.classList.contains("gap")) return;
      if (!p.classList.contains(on)) {
        if (box.hasAttribute("data-single")) [].forEach.call(box.children, function (c) { c.classList.remove(on); c.setAttribute("aria-pressed", "false"); });
        var max = +box.getAttribute("data-max");
        if (max && box.querySelectorAll("." + on).length >= max) { if (window.toastr) window.toastr.info("You can pick up to " + max); return; }
      }
      p.classList.toggle(on); p.setAttribute("aria-pressed", p.classList.contains(on) ? "true" : "false");
      box.dispatchEvent(new CustomEvent("m42:change", { bubbles: true, detail: { selected: M42UI.picked(box) } }));
    });
    // ---- declarative behaviour: pages built by M42 (pagebuild.py) work with no code of their own ----
    // filter chips: <div class="m42-chips" data-m42-filter-for="listId"> chips with data-filter, rows with data-tags
    document.addEventListener("m42:change", function (ev) {
      var box = ev.target, list = box.getAttribute && $(box.getAttribute("data-m42-filter-for"));
      if (list) {
        var f = (ev.detail.selected[0] || "all").toLowerCase(), btn = box.querySelector(".active");
        f = btn ? (btn.getAttribute("data-filter") || f).toLowerCase() : "all";
        [].forEach.call(list.children, function (row) {
          var tags = (row.getAttribute("data-tags") || "") + " " + row.textContent.toLowerCase();
          row.style.display = f === "all" || tags.toLowerCase().indexOf(f) >= 0 ? "" : "none";
        });
      }
      if (box.hasAttribute && box.hasAttribute("data-m42-picks")) { page.picked = ev.detail.selected; binds(); }
    });
    // a search card: <form class="m42-search" data-m42-search-for="listId">: rows that match, else all of them
    [].forEach.call(document.querySelectorAll("form[data-m42-search-for]"), function (f) {
      f.addEventListener("submit", function (ev) {
        ev.preventDefault();
        var list = $(f.getAttribute("data-m42-search-for"));
        var words = [].map.call(f.querySelectorAll("input[type=text], input:not([type])"), function (i) {
          return i.value.trim().toLowerCase(); }).filter(Boolean);
        if (list) {
          var shown = 0;
          [].forEach.call(list.children, function (row) {
            var ok = words.every(function (w) { return row.textContent.toLowerCase().indexOf(w) >= 0; });
            row.style.display = ok ? "" : "none"; shown += ok ? 1 : 0;
          });
          if (!shown) [].forEach.call(list.children, function (row) { row.style.display = ""; });
          var msg = shown ? shown + " found" : "No exact match: showing everything";
          if (window.toastr) window.toastr.info(msg); else if (window.Swal) window.Swal.fire({ toast: true, position: "top-end", timer: 1800, showConfirmButton: false, icon: "info", title: msg });
          list.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "start" });
        }
      });
    });
    // choose a row: <div class="m42-item" data-name data-price> <button data-m42-choose data-m42-next="sectionId">
    document.addEventListener("click", function (ev) {
      var b = ev.target.closest && ev.target.closest("[data-m42-choose]"); if (!b) return;
      var row = b.closest(".m42-item"); if (!row) return;
      [].forEach.call(row.parentElement.children, function (r) { r.classList.remove("selected"); });
      row.classList.add("selected");
      page.item = row.getAttribute("data-name") || ""; page.price = parseFloat(row.getAttribute("data-price")) || 0;
      binds();
      var next = b.getAttribute("data-m42-next"), target = next && $(next);
      var grid = document.querySelector("[data-m42-picks]");
      (grid || target) && (grid || target).scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "center" });
    });
    binds();
    // a soft 3D tilt on .m42-tilt (mouse only)
    [].forEach.call(document.querySelectorAll(".m42-tilt"), function (c) {
      c.addEventListener("mousemove", function (ev) { var r = c.getBoundingClientRect(), x = (ev.clientX - r.left) / r.width - .5, y = (ev.clientY - r.top) / r.height - .5;
        c.style.transform = "perspective(800px) rotateX(" + (-y * 6) + "deg) rotateY(" + (x * 6) + "deg) translateY(-4px)"; });
      c.addEventListener("mouseleave", function () { c.style.transform = ""; });
    });
    // forms: Bootstrap validation, and a sent message for a form with no action of its own
    [].forEach.call(document.querySelectorAll("form.m42-form:not([data-m42-own])"), function (f) {  // data-m42-own: the page's script does it
      f.setAttribute("novalidate", "");
      f.addEventListener("submit", function (ev) {
        if (!f.checkValidity()) { ev.preventDefault(); ev.stopImmediatePropagation(); f.classList.add("was-validated"); return; }
        if (!f.getAttribute("action")) { ev.preventDefault(); formDone(f); }
      });
    });
  }

  // ---- widgets (widgets.py): every control does something ------------------------------------------------
  function toast(msg, kind) {
    if ((window.M42_MOTION || {}).notify === "toast" && window.M42Notify && window.M42Notify(msg, kind)) return;
    if (window.Swal) { window.Swal.fire({ toast: true, position: "top-end", icon: kind || "success", title: msg, showConfirmButton: false, timer: 2200 }); return; }
    var t = el("div", "m42-toast-lite", msg); document.body.appendChild(t); setTimeout(function () { t.remove(); }, 2200);
  }
  M42UI.toast = toast;
  function calDraw(box) {
    var y = +box.getAttribute("data-year"), m = +box.getAttribute("data-month"), marks = JSON.parse(box.getAttribute("data-marks") || "[]");
    var icons = JSON.parse(box.getAttribute("data-icons") || "{}");
    var today = new Date(), first = new Date(y, m - 1, 1), days = new Date(y, m, 0).getDate(), lead = (first.getDay() + 6) % 7;
    var html = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"].map(function (d) { return '<span class="dow">' + d + "</span>"; }).join("");
    for (var i = 0; i < lead; i++) html += "<span></span>";
    for (var d = 1; d <= days; d++) {
      var isToday = today.getFullYear() === y && today.getMonth() + 1 === m && today.getDate() === d;
      var k = marks.indexOf(d);
      if (k >= 0 && icons[d]) { html += '<span class="mark has-icon t' + (k % 4) + '" title="' + d + '" aria-label="' + d + '"><i class="bi ' + icons[d] + '"></i></span>'; continue; }
      html += '<span class="' + (k >= 0 ? "mark" : isToday ? "today" : "") + '">' + d + "</span>";
    }
    box.querySelector("[data-cal-grid]").innerHTML = html;
    box.querySelector("[data-cal-title]").textContent = first.toLocaleString(undefined, { month: "long", year: "numeric" });
  }
  function dtDraw(box) {
    var table = document.getElementById(box.getAttribute("data-m42-dt")); if (!table) return;
    var q = (box.querySelector("[data-m42-dt-search]") || {}).value || "", size = 6;
    var rows = [].slice.call(table.tBodies[0].rows), shown = rows.filter(function (r) { return r.textContent.toLowerCase().indexOf(q.toLowerCase()) >= 0; });
    var pages = Math.max(1, Math.ceil(shown.length / size)), page = Math.min(+(box.getAttribute("data-page") || 1), pages);
    rows.forEach(function (r) { r.style.display = "none"; });
    shown.slice((page - 1) * size, page * size).forEach(function (r) { r.style.display = ""; });
    var pager = box.querySelector("[data-m42-dt-pager]"), h = "";
    if (pages > 1) for (var p = 1; p <= pages; p++) h += '<button type="button" data-page="' + p + '"' + (p === page ? ' class="active"' : "") + ">" + p + "</button>";
    if (pager) pager.innerHTML = h;
  }
  function dial(box, step) {
    var lo = +box.getAttribute("data-min"), hi = +box.getAttribute("data-max"), v = +box.getAttribute("data-value") + step;
    v = Math.max(lo, Math.min(hi, v)); box.setAttribute("data-value", v);
    box.querySelector(".m42-w-dial b span").textContent = v;
    var pct = (v - lo) / ((hi - lo) || 1) * 75; box.querySelector(".arc").setAttribute("stroke-dasharray", pct.toFixed(1) + " " + (100 - pct).toFixed(1));
  }
  function mmss(s) { s = Math.max(0, Math.round(s)); return Math.floor(s / 60) + ":" + ("0" + s % 60).slice(-2); }
  function player(box) {
    var list = JSON.parse(box.getAttribute("data-m42-player") || "[]"), st = box._st || (box._st = { i: 0, t: 0, timer: null });
    var tr = list[st.i] || { t: "", a: "", d: 200 };
    box.querySelector("[data-p-title]").textContent = tr.t; box.querySelector("[data-p-artist]").textContent = tr.a;
    box.querySelector("[data-p-len]").textContent = mmss(tr.d); box.querySelector("[data-p-now]").textContent = mmss(st.t);
    box.querySelector("[data-p-bar]").style.width = (st.t / tr.d * 100) + "%";
    return { list: list, st: st, tr: tr };
  }
  function widgets() {
    [].forEach.call(document.querySelectorAll("[data-m42-cal]"), calDraw);
    [].forEach.call(document.querySelectorAll("[data-m42-dt]"), function (box) {
      var table = document.getElementById(box.getAttribute("data-m42-dt"));
      if (table) [].forEach.call(table.tHead.rows[0].cells, function (th, i) { if (i < table.tHead.rows[0].cells.length - 1) th.setAttribute("data-sort", i); });
      dtDraw(box);
    });
    [].forEach.call(document.querySelectorAll("[data-m42-player]"), player);
    [].forEach.call(document.querySelectorAll(".m42-today"), function (d) {
      d.textContent = new Date().toLocaleDateString([], { weekday: "long", day: "numeric", month: "long" });
    });
    [].forEach.call(document.querySelectorAll("[data-m42-cam]"), function (box) {
      var rooms = box.getAttribute("data-m42-cam").split("|"), k = 0, clock = box.querySelector(".m42-w-camtime");
      box.querySelector(".m42-w-camroom").addEventListener("click", function () {
        k = (k + 1) % rooms.length; this.querySelector("span").textContent = rooms[k];
      });
      function tick() { clock.textContent = new Date().toLocaleTimeString([], { hour12: false }); }
      tick(); if (!window.M42_STILL) setInterval(tick, 1000);
    });
    [].forEach.call(document.querySelectorAll("[data-m42-countdown]"), function (box) {
      var end = Date.now() + (+box.getAttribute("data-m42-countdown")) * 1000;
      function t() { var s = Math.max(0, (end - Date.now()) / 1000), parts = { days: s / 86400, hours: s % 86400 / 3600, mins: s % 3600 / 60, secs: s % 60 };
        Object.keys(parts).forEach(function (k) { var b = box.querySelector('[data-cd="' + k + '"]'); if (b) b.textContent = ("0" + Math.floor(parts[k])).slice(-2); }); }
      t(); setInterval(t, 1000);
    });
    document.addEventListener("input", function (ev) {
      var t = ev.target;
      if (t.matches && t.matches("[data-m42-dt-search]")) { var box = t.closest("[data-m42-dt]"); box.setAttribute("data-page", 1); dtDraw(box); }
      if (t.matches && t.matches("[data-m42-range]")) { var o = document.querySelector('output[data-for="' + t.id + '"]'); if (o) o.textContent = t.value + (t.getAttribute("data-unit") || ""); }
    });
    document.addEventListener("change", function (ev) {
      var t = ev.target;
      if (t.matches && t.matches("[data-m42-device]")) { var c = t.closest(".m42-w-device"); c.classList.toggle("is-off", !t.checked);
        var s = c.querySelector("small"); if (s) s.textContent = t.checked ? "On" : "Off"; }
      if (t.matches && t.matches("[data-m42-setting]")) toast("Saved");
      if (t.matches && t.matches("[data-m42-files]")) { var ul = t.closest(".m42-w-drop").parentElement.querySelector("[data-files-list]");
        if (ul) ul.innerHTML = [].map.call(t.files, function (f) { return '<li><i class="bi bi-file-earmark"></i><div><b>' + f.name.replace(/</g, "&lt;") +
          "</b><small>" + Math.max(1, Math.round(f.size / 1024)) + " KB</small></div></li>"; }).join(""); }
    });
    document.addEventListener("submit", function (ev) {
      var f = ev.target, id = f.getAttribute && (f.getAttribute("data-m42-taskadd") || f.getAttribute("data-m42-send"));
      if (id) {
        ev.preventDefault(); var inp = f.querySelector("input"), v = (inp.value || "").trim(); if (!v) return;
        var list = document.getElementById(id), safe = v.replace(/</g, "&lt;");
        if (f.hasAttribute("data-m42-send")) list.insertAdjacentHTML("beforeend", '<div class="m42-w-msg is-me"><b>You</b><p>' + safe + "</p><time>now</time></div>");
        else { var n = id + "-" + list.children.length + "-" + Date.now();
          list.insertAdjacentHTML("afterbegin", '<li><input class="form-check-input" type="checkbox" id="' + n + '"><label for="' + n + '"><b>' + safe +
            '</b><small>Today</small></label><button type="button" class="m42-icon-btn sm" data-m42-remove aria-label="Delete"><i class="bi bi-trash3"></i></button></li>'); }
        inp.value = ""; list.scrollTop = list.scrollHeight;
      }
      if (f.hasAttribute && f.hasAttribute("data-m42-closes") && f.checkValidity()) {
        var modal = f.closest(".modal"); setTimeout(function () { if (modal && window.bootstrap) window.bootstrap.Modal.getOrCreateInstance(modal).hide(); }, 700);
      }
    }, true);
    document.addEventListener("click", function (ev) {
      var b = ev.target.closest && ev.target.closest("button, a"); if (!b) return;
      var box;
      if ((box = b.closest("[data-m42-dial]")) && b.hasAttribute("data-step")) return dial(box, +b.getAttribute("data-step"));
      if ((box = b.closest("[data-m42-cal]")) && b.hasAttribute("data-cal")) {
        var m = +box.getAttribute("data-month") + (+b.getAttribute("data-cal")), y = +box.getAttribute("data-year");
        if (m < 1) { m = 12; y--; } if (m > 12) { m = 1; y++; }
        box.setAttribute("data-month", m); box.setAttribute("data-year", y); box.setAttribute("data-marks", "[]"); box.setAttribute("data-icons", "{}"); return calDraw(box);
      }
      if ((box = b.closest("[data-m42-dt]"))) {
        if (b.hasAttribute("data-page")) { box.setAttribute("data-page", b.getAttribute("data-page")); return dtDraw(box); }
        if (b.hasAttribute("data-m42-view") && window.Swal) { var cells = [].map.call(b.closest("tr").cells, function (c) { return c.textContent; }).slice(0, -1);
          return window.Swal.fire({ title: cells[0], html: cells.slice(1).filter(Boolean).join("<br>"), confirmButtonText: "Close" }); }
      }
      if (b.hasAttribute("data-m42-remove")) {
        var row = b.closest("li, tr, .m42-w-taskcard, .m42-w-trow"), dt = b.closest("[data-m42-dt]");
        if (row) { row.remove(); toast("Removed"); if (dt) dtDraw(dt); } return;
      }
      if (b.hasAttribute("data-m42-edit") && window.Swal) {
        var lab = b.closest("li").querySelector("b");
        return window.Swal.fire({ title: "Edit", input: "text", inputValue: lab.textContent, showCancelButton: true }).then(function (r) {
          if (r.isConfirmed && r.value) { lab.textContent = r.value; toast("Updated"); } });
      }
      if (b.hasAttribute("data-m42-approve")) { b.closest("li").classList.add("is-approved"); return toast("Approved"); }
      if (b.hasAttribute("data-m42-readall")) { [].forEach.call(document.querySelectorAll(".m42-w-notes .is-unread"), function (x) { x.classList.remove("is-unread"); });
        return toast("All read"); }
      if (b.hasAttribute("data-m42-done")) { var card = b.closest(".m42-w-taskcard"); card.style.opacity = .55; b.disabled = true; b.textContent = "Done"; return toast("Completed"); }
      if (b.hasAttribute("data-m42-toggle-text")) { var two = b.getAttribute("data-m42-toggle-text").split("|"); b.textContent = b.textContent === two[1] ? two[0] : two[1]; return; }
      if (b.hasAttribute("data-m42-inv-step") || b.hasAttribute("data-m42-inv-del")) {  // a bill's steppers and remove
        var inv = b.closest("[data-m42-inv]"), li = b.closest(".m42-inv-line");
        if (b.hasAttribute("data-m42-inv-del")) li.remove();
        else { var qe = li.querySelector("[data-m42-inv-q]"), qn = Math.max(1, (+qe.textContent || 1) + (+b.getAttribute("data-m42-inv-step"))); qe.textContent = qn; }
        var rs = function (v) { return "₹" + Math.round(v).toLocaleString("en-IN"); }, subt = 0;
        [].forEach.call(inv.querySelectorAll(".m42-inv-line"), function (l) { var a = (+l.getAttribute("data-rate") || 0) * (+l.querySelector("[data-m42-inv-q]").textContent || 1);
          subt += a; l.querySelector("[data-m42-inv-amt]").textContent = rs(a); });
        var tx = Math.round(subt * (+inv.getAttribute("data-tax") || 0));
        inv.querySelector("[data-m42-inv-sub]").textContent = rs(subt); inv.querySelector("[data-m42-inv-tax]").textContent = rs(tx);
        inv.querySelector("[data-m42-inv-total]").textContent = rs(subt + tx);
        var go = inv.querySelector(".m42-inv-go"); if (go) go.setAttribute("data-m42-confirm", "Take payment of " + rs(subt + tx) + "?");
        return;
      }
      if (b.hasAttribute("data-m42-like")) { b.classList.toggle("is-on"); var hi = b.querySelector("i"); if (hi) hi.className = "bi " + (b.classList.contains("is-on") ? "bi-heart-fill" : "bi-heart"); return; }
      if (b.hasAttribute("data-m42-open")) { ev.preventDefault(); var t = b.querySelector("b"); return toast((t ? t.textContent : "") + ": opened", "info"); }
      if (b.hasAttribute("data-m42-pick")) { var dd = document.getElementById(b.getAttribute("data-m42-pick")); if (dd) dd.textContent = b.textContent; return toast("Showing " + b.textContent, "info"); }
      if (b.hasAttribute("data-m42-toast")) return toast(b.getAttribute("data-m42-toast"), b.getAttribute("data-kind") || "success");
      if (b.hasAttribute("data-m42-confirm") && window.Swal) {
        return window.Swal.fire({ title: b.getAttribute("data-m42-confirm"), icon: "question", showCancelButton: true, confirmButtonText: "Yes" }).then(function (r) {
          if (r.isConfirmed) toast("Done"); });
      }
      if ((box = b.closest("[data-m42-qty]")) && b.hasAttribute("data-q")) {
        var nb = box.querySelector("b"), n2 = Math.max(0, (+nb.textContent) + (+b.getAttribute("data-q"))); nb.textContent = n2;
        var tot = box.parentElement.querySelector("[data-q-total]"), price = +box.getAttribute("data-price");
        if (tot && price) tot.textContent = "₹" + num(price * n2, 0); return;
      }
      if ((box = b.closest("[data-m42-stepper]")) && b.hasAttribute("data-go")) {
        var heads = box.querySelectorAll("ol li"), panes = box.querySelectorAll(".m42-w-pane"), cur = [].indexOf.call(heads, box.querySelector("ol li.active"));
        var nx = Math.max(0, Math.min(heads.length - 1, cur + (+b.getAttribute("data-go"))));
        [].forEach.call(heads, function (h, i) { h.classList.toggle("active", i === nx); h.classList.toggle("done", i < nx); });
        [].forEach.call(panes, function (p, i) { p.classList.toggle("active", i === nx); });
        if (nx === heads.length - 1 && cur === nx) toast("All steps done"); return;
      }
      if ((box = b.closest("[data-m42-player]")) && b.hasAttribute("data-p")) {
        var P = player(box), act = b.getAttribute("data-p");
        if (act === "play") {
          var on = !P.st.timer, ic = b.querySelector("i"); ic.className = "bi " + (on ? "bi-pause-fill" : "bi-play-fill");
          if (on) P.st.timer = setInterval(function () { P.st.t += 1; if (P.st.t > P.tr.d) P.st.t = 0; player(box); }, 1000);
          else { clearInterval(P.st.timer); P.st.timer = null; }
        } else if (act === "shuffle" || act === "repeat") { b.classList.toggle("active"); toast(act === "shuffle" ? "Shuffle" : "Repeat", "info"); }
        else { P.st.i = (P.st.i + (+act) + P.list.length) % Math.max(1, P.list.length); P.st.t = 0; player(box); }
      }
    });
  }

  window.M42UI = M42UI;
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init); else init();
})();

/* ---- app views (appviews.py, 2026-11-10): the chat screen and the mail screen ---- */
(function () {
  "use strict";
  function say(msg) { if (window.M42UI && window.M42UI.toast) window.M42UI.toast(msg, "success"); }
  function esc(s) { return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;"); }
  function initials(name) { return (String(name).match(/[A-Za-z0-9]+/g) || ["?"]).slice(0, 2).map(function (w) { return w[0]; }).join("").toUpperCase(); }
  function clock() { var d = new Date(); return ("0" + d.getHours()).slice(-2) + ":" + ("0" + d.getMinutes()).slice(-2); }
  function filter(list, q) {
    q = q.trim().toLowerCase();
    Array.prototype.forEach.call(list.children, function (li) { li.hidden = !!q && li.textContent.toLowerCase().indexOf(q) < 0; });
  }

  // ---- chat: open a conversation, send a message, search ----
  function openChat(app, li) {
    var thread = app.querySelector(".m42-ca-thread"), old = app.querySelector(".m42-ca-list li.active");
    if (old === li) return;
    if (old) { old.classList.remove("active"); old.querySelector("template").innerHTML = thread.innerHTML; }  // what was sent stays
    li.classList.add("active");
    thread.innerHTML = li.querySelector("template").innerHTML;
    var name = li.getAttribute("data-name") || "", status = li.getAttribute("data-status") || "";
    Array.prototype.forEach.call(app.querySelectorAll("[data-ca-name]"), function (x) { x.textContent = name; });
    Array.prototype.forEach.call(app.querySelectorAll("[data-ca-status]"), function (x) { x.textContent = status; });
    Array.prototype.forEach.call(app.querySelectorAll(".m42-ca-main > header .m42-av, .m42-ca-info > .m42-av"), function (x) {
      x.textContent = initials(name); x.classList.toggle("is-on", status === "Online" && !x.classList.contains("is-big"));
    });
    var badge = li.querySelector(".m42-ca-meta em"); if (badge) badge.remove();
    thread.scrollTop = thread.scrollHeight;
  }
  function sendChat(app, form) {
    var inp = form.querySelector("input"), v = (inp.value || "").trim(); if (!v) return;
    var thread = app.querySelector(".m42-ca-thread"), li = app.querySelector(".m42-ca-list li.active");
    thread.insertAdjacentHTML("beforeend", '<div class="m42-ca-msg is-me"><p>' + esc(v) + "</p><time>" + clock() + ' <i class="bi bi-check2-all"></i></time></div>');
    if (li) { li.querySelector(".m42-ca-who small").textContent = "You: " + v; li.querySelector(".m42-ca-meta time").textContent = clock(); }
    inp.value = ""; thread.scrollTop = thread.scrollHeight;
    if (window.M42_STILL) return;
    var replies = (app.getAttribute("data-replies") || "Okay").split("|"), n = +(app.getAttribute("data-n") || 0);
    app.setAttribute("data-n", n + 1);
    setTimeout(function () {
      if (app.querySelector(".m42-ca-list li.active") !== li) return;
      thread.insertAdjacentHTML("beforeend", '<div class="m42-ca-msg is-typing"><p>...</p></div>'); thread.scrollTop = thread.scrollHeight;
      setTimeout(function () {
        var t = thread.querySelector(".is-typing"); if (!t) return;
        t.classList.remove("is-typing"); t.innerHTML = "<p>" + esc(replies[n % replies.length]) + "</p><time>" + clock() + "</time>";
        if (li) li.querySelector(".m42-ca-who small").textContent = replies[n % replies.length];
        thread.scrollTop = thread.scrollHeight;
      }, 1100);
    }, 500);
  }

  // ---- mail: open a mail, folders, star, trash, reply, search ----
  function openMail(app, li) {
    Array.prototype.forEach.call(app.querySelectorAll(".m42-ma-list li.active"), function (x) { x.classList.remove("active"); });
    li.classList.add("active"); li.classList.remove("is-unread");
    var set = function (key, val) { var x = app.querySelector('[data-ma="' + key + '"]'); if (x) x.textContent = val; };
    var from = li.getAttribute("data-from") || "";
    set("subject", li.getAttribute("data-subject") || ""); set("from", from); set("sign", from);
    set("time", li.getAttribute("data-time") || ""); set("body", li.getAttribute("data-body") || "");
    var face = app.querySelector('[data-ma="face"] .m42-av'); if (face) face.textContent = initials(from);
    counts(app);
  }
  function counts(app) {
    Array.prototype.forEach.call(app.querySelectorAll(".m42-ma-folders button"), function (b) {
      var f = b.getAttribute("data-folder"), n = app.querySelectorAll('.m42-ma-list li.is-unread[data-folder="' + f + '"]').length, em = b.querySelector("em");
      if (!n && em) em.remove(); else if (n && em) em.textContent = n; else if (n) b.insertAdjacentHTML("beforeend", "<em>" + n + "</em>");
    });
  }
  function showFolder(app, folder) {
    var any = false;
    Array.prototype.forEach.call(app.querySelectorAll(".m42-ma-list li"), function (li) {
      var on = folder === "starred" ? li.classList.contains("is-starred") : li.getAttribute("data-folder") === folder;
      li.hidden = !on; any = any || on;
    });
    Array.prototype.forEach.call(app.querySelectorAll(".m42-ma-folders button"), function (b) { b.classList.toggle("active", b.getAttribute("data-folder") === folder); });
    var none = app.querySelector(".m42-ma-none"); if (none) none.hidden = any;
    var first = app.querySelector(".m42-ma-list li:not([hidden])"); if (first) openMail(app, first);
  }

  document.addEventListener("click", function (ev) {
    var t = ev.target, chat = t.closest && t.closest("[data-m42-chatapp]"), mail = t.closest && t.closest("[data-m42-mailapp]"), li, b;
    if (chat && (li = t.closest(".m42-ca-list li"))) return openChat(chat, li);
    if (!mail) return;
    if ((b = t.closest(".m42-ma-star"))) { b.closest("li").classList.toggle("is-starred"); return; }
    if ((li = t.closest(".m42-ma-list li"))) return openMail(mail, li);
    if ((b = t.closest(".m42-ma-folders button"))) return showFolder(mail, b.getAttribute("data-folder"));
    if ((b = t.closest("[data-ma-act]"))) {
      var act = b.getAttribute("data-ma-act"), cur = mail.querySelector(".m42-ma-list li.active");
      if (act === "reply") { var inp = mail.querySelector(".m42-ma-reply input"); if (inp) inp.focus(); return; }
      if (act === "trash" && cur) {
        var was = (mail.querySelector(".m42-ma-folders button.active") || b).getAttribute("data-folder") || "inbox";
        cur.setAttribute("data-folder", "trash"); cur.classList.remove("active", "is-unread"); say("Moved to Trash"); showFolder(mail, was);
      }
    }
  });
  document.addEventListener("submit", function (ev) {
    var f = ev.target, app;
    if (f.classList && f.classList.contains("m42-ca-send") && (app = f.closest("[data-m42-chatapp]"))) { ev.preventDefault(); sendChat(app, f); }
    if (f.classList && f.classList.contains("m42-ma-reply")) { ev.preventDefault(); f.reset(); say("Reply sent"); }
  }, true);
  document.addEventListener("input", function (ev) {
    var t = ev.target, box = t.closest && t.closest(".m42-ca-search"); if (!box) return;
    var app = t.closest("[data-m42-chatapp], [data-m42-mailapp]"); if (!app) return;
    filter(app.querySelector(".m42-ca-list ul, .m42-ma-list ul"), t.value || "");
  });
  function ready() {
    Array.prototype.forEach.call(document.querySelectorAll(".m42-ca-thread"), function (x) { x.scrollTop = x.scrollHeight; });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", ready); else ready();
})();

/* ---- motion and notices the page's plan chose (pagebuild: <html data-m42-motion ...>), 2026-11-11 ----
   The 4B decides per page: how much motion, how the top comes in, how sections appear, card hover, counting numbers,
   how the page answers (a corner toast with Toastr, a dialog with SweetAlert2, or a small note). anime.js, Toastr and
   SweetAlert2 are on the page only when that choice needs them; without them everything still works. */
(function () {
  "use strict";
  var reduce = !!window.M42_STILL || (window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  function cfg() {
    var h = document.documentElement, a = function (n, d) { return h.getAttribute(n) || d; };
    return { level: a("data-m42-motion", "subtle"), hero: a("data-m42-hero-in", "fade"), reveal: a("data-m42-reveal", "fade-up"),
             counters: a("data-m42-counters", "1") !== "0", notify: a("data-m42-notify", "popup") };
  }
  var MO = cfg();
  window.M42_MOTION = MO;
  var A = function () { return !reduce && MO.level !== "none" && window.anime; };

  function wrapWords(h1) {
    [].slice.call(h1.childNodes).forEach(function (n) {
      if (n.nodeType === 3) {
        var f = document.createDocumentFragment();
        n.textContent.split(/(\s+)/).forEach(function (w) {
          if (!w) return;
          if (/^\s+$/.test(w)) { f.appendChild(document.createTextNode(w)); return; }
          var s = document.createElement("span"); s.className = "m42-word"; s.textContent = w; f.appendChild(s);
        });
        h1.replaceChild(f, n);
      } else if (n.nodeType === 1) { n.classList.add("m42-word"); }
    });
  }

  function heroIn() {
    var an = A(); if (!an || MO.hero === "none") return;
    var box = document.querySelector(".m42-hero .container"); if (!box) return;
    var parts = [].slice.call(box.querySelectorAll(".m42-eyebrow, h1, .lead, .m42-actions, .m42-search, .m42-showcase, .m42-visual"));
    var stats = box.querySelector(".m42-actions + .d-flex, .lead + .d-flex"); if (stats) parts.push(stats);
    var slow = MO.level === "lively" ? 900 : 650, start = 0;
    if (MO.hero === "words") {
      var h1 = box.querySelector("h1");
      if (h1) {
        wrapWords(h1); parts = parts.filter(function (p) { return p !== h1; });
        an({ targets: h1.querySelectorAll(".m42-word"), opacity: [0, 1], translateY: [26, 0], delay: an.stagger(70), duration: 700, easing: "easeOutCubic" });
        start = 260;
      }
    }
    var slide = MO.hero === "slide";
    an({ targets: parts, opacity: [0, 1], duration: slow, easing: "easeOutCubic", delay: an.stagger(110, { start: start }),
         translateY: slide ? 0 : [22, 0],
         translateX: slide ? function (e) { return e.matches(".m42-showcase, .m42-visual") ? [70, 0] : [-40, 0]; } : 0 });
    if (MO.level === "lively") {  // the hero's floating preview cards keep a slow drift
      an({ targets: box.querySelectorAll(".m42-float"), translateY: [0, -8], direction: "alternate", loop: true, duration: 2600,
           easing: "easeInOutSine", delay: an.stagger(400) });
    }
  }

  function dataIn(scope) {  // charts draw, bars grow, progress fills, when they come into view
    var an = A(); if (!an) return;
    var bars = [].slice.call(scope.querySelectorAll(".m42-w-bar i, .m42-w-bars i"));
    var tracks = [].slice.call(scope.querySelectorAll(".m42-w-track > i"));
    var lines = [].slice.call(scope.querySelectorAll(".m42-w-plot svg path, .m42-chart svg path")).filter(function (p) {
      return (p.getAttribute("fill") || "") === "none" || (getComputedStyle(p).fill || "") === "none"; });
    if (bars.length) an({ targets: bars, height: function (e) { return ["0%", e.style.height || "100%"]; }, delay: an.stagger(35), duration: 900, easing: "easeOutCubic" });
    if (tracks.length) an({ targets: tracks, width: function (e) { return ["0%", e.style.width || "100%"]; }, delay: an.stagger(60), duration: 1000, easing: "easeOutCubic" });
    if (lines.length) an({ targets: lines, strokeDashoffset: [an.setDashoffset, 0], duration: 1300, easing: "easeInOutSine", delay: an.stagger(150) });
  }

  function watchData() {
    if (!A() || !("IntersectionObserver" in window)) return;
    var boxes = [].slice.call(document.querySelectorAll(".m42-w-chart, .m42-w-hbars, .m42-w-kpi, .m42-chart, .m42-w-progress, .m42-panel, .m42-w-krow"))
      .filter(function (b) { return !b.parentElement.closest(".m42-w-chart, .m42-w-hbars, .m42-chart, .m42-panel"); });
    var io = new IntersectionObserver(function (es) {
      es.forEach(function (en) { if (!en.isIntersecting) return; io.unobserve(en.target); dataIn(en.target); });
    }, { threshold: .2 });
    boxes.forEach(function (b) { io.observe(b); });
  }

  function appIn() {  // an admin page: its cards come in one after another
    var an = A(); if (!an || !document.body.classList.contains("m42-app")) return;
    var cards = document.querySelectorAll(".m42-main .m42-panel, .m42-main .m42-stat, .m42-main .m42-card");
    if (cards.length) an({ targets: cards, opacity: [0, 1], translateY: [18, 0], delay: an.stagger(60), duration: 600, easing: "easeOutCubic" });
  }

  // how the page answers: a toast (Toastr), a dialog (SweetAlert2), or a small note
  window.M42Notify = function (msg, kind, title) {
    kind = kind || "success";
    if (MO.notify === "toast" && window.toastr) {
      window.toastr.options = { positionClass: "toast-top-right", progressBar: true, timeOut: 2600, closeButton: true };
      (window.toastr[kind] || window.toastr.success)(msg, title || ""); return true;
    }
    if (MO.notify === "popup" && window.Swal) {
      window.Swal.fire({ title: title || (kind === "success" ? "Done" : ""), text: msg, icon: kind,
        confirmButtonColor: getComputedStyle(document.documentElement).getPropertyValue("--bs-primary").trim() || undefined });
      return true;
    }
    return false;
  };

  function go() { heroIn(); appIn(); watchData(); }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", go); else go();
})();

/* ---- the hero's moving background (2026-11-12, the 4B's pick: agent._motion "backdrop", data-m42-backdrop on <html>):
   fireworks (a click bursts one too), particles, stars, bubbles, waves or aurora, drawn on a canvas behind the hero's
   words in the page's own colours. No library; still when the visitor asks for less motion; paused off screen. ---- */
(function () {
  "use strict";
  var kind = document.documentElement.getAttribute("data-m42-backdrop");
  if (!kind || kind === "none" || !window.HTMLCanvasElement) return;
  var still = !!window.M42_STILL || (window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches);

  function start() {
    var host = document.querySelector(".m42-hero");
    if (!host) return;
    var cv = document.createElement("canvas");
    cv.className = "m42-backdrop";
    cv.setAttribute("aria-hidden", "true");
    host.insertBefore(cv, host.firstChild);
    var ctx = cv.getContext("2d"), W = 0, H = 0, dpr = Math.min(2, window.devicePixelRatio || 1);
    var css = getComputedStyle(document.documentElement);
    var cols = ["--m42-accent", "--m42-accent-2", "--m42-accent-3"].map(function (v) { return css.getPropertyValue(v).trim(); })
      .filter(function (c) { return /^#|^rgb/.test(c); });
    if (!cols.length) cols = ["#f59e0b", "#ef4444", "#facc15"];
    if (kind === "fireworks") cols = cols.concat(["#fde047", "#ffffff"]);
    var R = Math.random, parts = [], t = 0, run = true, seen = true;
    function col() { return cols[(R() * cols.length) | 0]; }
    function size() {
      var r = host.getBoundingClientRect();
      W = r.width; H = r.height;
      cv.width = Math.round(W * dpr); cv.height = Math.round(H * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }
    size();
    window.addEventListener("resize", size);

    function burst(x, y, n) {
      for (var i = 0; i < (n || 70); i++) {
        var a = R() * Math.PI * 2, s = 1 + R() * 4.2;
        parts.push({ k: "spark", x: x, y: y, vx: Math.cos(a) * s, vy: Math.sin(a) * s, life: 55 + R() * 45, age: 0, c: col(), r: 1.4 + R() * 1.6 });
      }
    }
    function rocket() {
      parts.push({ k: "rocket", x: W * (.12 + R() * .76), y: H + 4, vx: (R() - .5) * 1.4, vy: -(H / 75 + R() * 3), age: 0, c: col(), r: 2.2 });
    }
    var n = { stars: 150, particles: 70, bubbles: 36 }[kind] || 0;
    for (var i = 0; i < n; i++) {
      parts.push({ x: R() * W, y: R() * H, vx: (R() - .5) * .45, vy: kind === "bubbles" ? -(.3 + R() * .9) : (R() - .5) * .45,
                   r: kind === "bubbles" ? 4 + R() * 16 : kind === "stars" ? .4 + R() * 1.6 : 1.4 + R() * 2.2, c: col(), tw: R() * 6.3 });
    }

    function alpha(c, a) { ctx.globalAlpha = Math.max(0, Math.min(1, a)); ctx.fillStyle = c; ctx.strokeStyle = c; }
    function dot(x, y, r) { ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.fill(); }

    function draw() {
      t++;
      ctx.clearRect(0, 0, W, H);
      if (kind === "fireworks") {
        if (t % 38 === 1 || (t % 38 === 19 && R() < .5)) rocket();
        parts = parts.filter(function (p) {
          p.age++;
          if (p.k === "rocket") {
            p.x += p.vx; p.y += p.vy; p.vy += .06;
            alpha(p.c, 1); dot(p.x, p.y, p.r);
            alpha(p.c, .35); dot(p.x - p.vx * 2, p.y - p.vy * 2, p.r * .8);
            if (p.vy > -1.2 || p.y < H * .18) { burst(p.x, p.y, 60 + (R() * 40 | 0)); return false; }
            return true;
          }
          p.x += p.vx; p.y += p.vy; p.vy += .045; p.vx *= .985; p.vy *= .985;
          alpha(p.c, 1 - p.age / p.life); dot(p.x, p.y, p.r);
          return p.age < p.life;
        });
      } else if (kind === "particles") {
        parts.forEach(function (p) {
          p.x = (p.x + p.vx + W) % W; p.y = (p.y + p.vy + H) % H;
          alpha(p.c, .7); dot(p.x, p.y, p.r);
        });
        ctx.lineWidth = 1;
        for (var a = 0; a < parts.length; a++) for (var b = a + 1; b < parts.length; b++) {
          var dx = parts[a].x - parts[b].x, dy = parts[a].y - parts[b].y, d = dx * dx + dy * dy;
          if (d < 12000) { alpha(parts[a].c, .22 * (1 - d / 12000)); ctx.beginPath(); ctx.moveTo(parts[a].x, parts[a].y); ctx.lineTo(parts[b].x, parts[b].y); ctx.stroke(); }
        }
        parts = parts.filter(function (p) { return p.k !== "spark" || (p.age = (p.age || 0) + 1) < 40; });
      } else if (kind === "stars") {
        parts.forEach(function (p) {
          p.x = (p.x + p.vx * .3 + W) % W;
          alpha(p.c === cols[0] ? "#ffffff" : p.c, .35 + .65 * Math.abs(Math.sin(t * .025 + p.tw))); dot(p.x, p.y, p.r);
        });
      } else if (kind === "bubbles") {
        ctx.lineWidth = 1.5;
        parts.forEach(function (p) {
          p.y += p.vy; p.x += Math.sin((t + p.tw * 60) * .02) * .4;
          if (p.y < -p.r * 2) { p.y = H + p.r * 2; p.x = R() * W; }
          alpha(p.c, .22); dot(p.x, p.y, p.r);
          alpha(p.c, .5); ctx.beginPath(); ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2); ctx.stroke();
        });
      } else if (kind === "waves") {
        for (var w = 0; w < 3; w++) {
          alpha(cols[w % cols.length], .14 + w * .05);
          ctx.beginPath(); ctx.moveTo(0, H);
          for (var x = 0; x <= W; x += 12) {
            ctx.lineTo(x, H * (.72 + w * .08) + Math.sin(x * (.008 + w * .002) + t * (.02 + w * .008)) * (18 + w * 8));
          }
          ctx.lineTo(W, H); ctx.closePath(); ctx.fill();
        }
      } else if (kind === "aurora") {
        for (var g = 0; g < 3; g++) {
          var gx = W * (.2 + .3 * g) + Math.sin(t * .006 + g * 2) * W * .15, gy = H * (.35 + .1 * g) + Math.cos(t * .005 + g) * H * .15;
          var grd = ctx.createRadialGradient(gx, gy, 0, gx, gy, Math.max(W, H) * .45);
          grd.addColorStop(0, cols[g % cols.length]); grd.addColorStop(1, "transparent");
          ctx.globalAlpha = .28; ctx.fillStyle = grd; ctx.fillRect(0, 0, W, H);
        }
      }
      ctx.globalAlpha = 1;
    }

    host.addEventListener("pointerdown", function (e) {  // a click in the hero (not on its buttons): a burst there
      if (e.target.closest("a, button, input, select, textarea, label")) return;
      var r = host.getBoundingClientRect();
      if (kind === "fireworks" || kind === "particles") burst(e.clientX - r.left, e.clientY - r.top, kind === "fireworks" ? 90 : 30);
    });
    if ("IntersectionObserver" in window) {
      new IntersectionObserver(function (es) { seen = es[0].isIntersecting; }).observe(host);
    }
    document.addEventListener("visibilitychange", function () { run = !document.hidden; });

    if (still) {  // one quiet frame: a few bursts or the stars as they are
      if (kind === "fireworks") { burst(W * .3, H * .35, 80); burst(W * .7, H * .3, 80); for (var s = 0; s < 18; s++) draw(); }
      else draw();
      return;
    }
    if (kind === "fireworks") { burst(W * .28, H * .32, 80); burst(W * .74, H * .26, 80); }  // (not an empty sky at first)
    (function loop() {
      if (run && seen) draw();
      window.requestAnimationFrame(loop);
    })();
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start); else start();
})();

/* ---- a carousel's arrows (pagebuild.p_carousel): the row scrolls by most of its width ---- */
document.addEventListener("click", function (ev) {
  var b = ev.target.closest && ev.target.closest("[data-car]");
  if (!b) return;
  var box = b.closest("[data-m42-carousel]"), track = box && box.querySelector(".m42-car-track");
  if (!track) return;
  var step = track.clientWidth * .8 * (+b.getAttribute("data-car"));
  if (track.scrollLeft + step < 0 || track.scrollLeft + step > track.scrollWidth - track.clientWidth + 2) {
    track.scrollTo({ left: step > 0 ? 0 : track.scrollWidth, behavior: "smooth" });  // (round again at the ends)
  } else {
    track.scrollBy({ left: step, behavior: "smooth" });
  }
});

// 📷 M42's preview asks how far the page is scrolled (its screenshot is the part on screen): window or an app's
// scrolling main area, whichever moved
window.addEventListener("message", (e) => {
  if (e.data !== "m42:scroll?" || !e.source) return;
  const inner = [...document.querySelectorAll(".m42-main, .m42-content")].map((el) => el.scrollTop).filter(Boolean);
  e.source.postMessage({ m42scroll: Math.round(window.scrollY || document.documentElement.scrollTop || inner[0] || 0),
                         m42path: location.pathname }, "*");
});

/* ---- 🧱 a block's fan of quotes (blocks.py: .m42-b-cyc): the arrows bring the next / previous one to the front ---- */
document.addEventListener("click", function (ev) {
  var b = ev.target.closest && ev.target.closest("[data-m42-cycle]");
  if (!b) return;
  var box = b.closest(".m42-b-cyc"), its = box ? [].slice.call(box.querySelectorAll(".m42-b-cyc-it")) : [];
  if (its.length < 2) return;
  var on = 0;
  its.forEach(function (el, k) { if (el.classList.contains("is-on")) on = k; });
  on = (on + (+b.getAttribute("data-m42-cycle")) + its.length) % its.length;
  its.forEach(function (el, k) {
    var d = (k - on + its.length) % its.length;
    el.classList.remove("is-on", "is-next", "is-prev", "is-back");
    el.classList.add(d === 0 ? "is-on" : d === 1 ? "is-next" : d === its.length - 1 ? "is-prev" : "is-back");
  });
});

/* ---- 🧱 blocks (blocks.py): a pricing card's plan tabs, a before / after slider, an arc of tiles, filter chips ---- */
document.addEventListener("click", function (ev) {
  var t = ev.target.closest && ev.target.closest("[data-m42-plan]");
  if (t) {
    var card = t.closest(".m42-b-acc-card"), k = t.getAttribute("data-m42-plan");
    card.querySelectorAll("[data-m42-plan]").forEach(function (b) { b.classList.toggle("is-on", b === t); });
    card.querySelectorAll("[data-m42-plan-pane]").forEach(function (p) { p.classList.toggle("is-on", p.getAttribute("data-m42-plan-pane") === k); });
    return;
  }
  var a = ev.target.closest && ev.target.closest("[data-m42-arc]");
  if (a) {
    var box = a.closest("[data-m42-arcs]"), its = [].slice.call(box.querySelectorAll("[data-m42-arc]")), on = its.indexOf(a);
    its.forEach(function (el, k) { el.style.setProperty("--i", k - on); el.classList.toggle("is-on", k === on); });
    var cap = box.querySelector(".m42-b-arc-cap");
    if (cap) { cap.querySelector("b").textContent = a.getAttribute("data-name"); cap.querySelector("span").textContent = a.getAttribute("data-text"); }
    return;
  }
  var f = ev.target.closest && ev.target.closest("[data-m42-filter]");
  if (f) {
    var grid = f.closest("[data-m42-filters]"), tag = f.getAttribute("data-m42-filter");
    grid.querySelectorAll("[data-m42-filter]").forEach(function (b) { b.classList.toggle("is-on", b === f); });
    grid.querySelectorAll(".m42-b-fg").forEach(function (c) { c.classList.toggle("is-out", tag !== "*" && c.getAttribute("data-tag") !== tag); });
  }
});
document.addEventListener("input", function (ev) {
  var r = ev.target, fr = r.closest && r.closest("[data-m42-ba]");
  if (fr) fr.style.setProperty("--p", r.value + "%");
});

/* ---- 🧱 blocks: an agenda's day tabs, and today's line in a card of opening hours ---- */
document.addEventListener("click", function (ev) {
  var d = ev.target.closest && ev.target.closest("[data-m42-day]");
  if (!d) return;
  var box = d.closest("[data-m42-days]"), day = d.getAttribute("data-m42-day");
  box.querySelectorAll("[data-m42-day]").forEach(function (b) { b.classList.toggle("is-on", b === d); });
  box.querySelectorAll("li[data-day]").forEach(function (li) { li.hidden = li.getAttribute("data-day") !== day; });
});
(function () {
  function today() {
    var dow = (new Date().getDay() + 6) % 7;  // (Monday = 0, as the blocks write them)
    document.querySelectorAll("[data-m42-hours] li[data-m42-dow]").forEach(function (li) { li.classList.toggle("is-today", +li.getAttribute("data-m42-dow") === dow); });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", today); else today();
})();

/* ---- ⚖ app blocks (appblocks.py): a product's + adds it to the bill, a category or a search shows only its products,
   a status tab shows only its rows ---- */
(function () {
  function bill() { return document.querySelector("[data-m42-inv]"); }
  document.addEventListener("click", function (ev) {
    var a = ev.target.closest && ev.target.closest("[data-m42-add]");
    if (a) {
      var inv = bill(), name = a.getAttribute("data-name"), rate = +a.getAttribute("data-rate") || 0;
      a.classList.remove("is-added"); void a.offsetWidth; a.classList.add("is-added");
      if (!inv) return;
      var lines = inv.querySelectorAll(".m42-inv-line"), hit = null;
      [].forEach.call(lines, function (l) { var b = l.querySelector(".m42-inv-name b"); if (b && b.textContent === name) hit = l; });
      if (!hit && lines.length) {  // a new line like the first, for this product, quantity 1
        hit = lines[0].cloneNode(true);
        hit.setAttribute("data-rate", rate);
        hit.querySelector(".m42-inv-name b").textContent = name;
        var sm = hit.querySelector(".m42-inv-name small"); if (sm) sm.textContent = "₹" + Math.round(rate).toLocaleString("en-IN") + " each";
        hit.querySelector("[data-m42-inv-q]").textContent = "1";
        var del = hit.querySelector("[data-m42-inv-del]"); if (del) del.setAttribute("aria-label", "Remove " + name);
        inv.querySelector(".m42-inv-lines").appendChild(hit);
      }
      if (hit && hit.parentNode && [].indexOf.call(lines, hit) < 0) {  // a new line: quantity 1, the bill totalled by its own script
        hit.querySelector("[data-m42-inv-step='1']").click(); hit.querySelector("[data-m42-inv-step='-1']").click();
      } else if (hit) hit.querySelector("[data-m42-inv-step='1']").click();  // (already on the bill: one more)
      return;
    }
    var c = ev.target.closest && ev.target.closest("[data-m42-cat]");
    if (c) {
      var box = c.closest("[data-m42-cats]"), cat = c.getAttribute("data-m42-cat");
      box.querySelectorAll("[data-m42-cat]").forEach(function (x) { x.classList.toggle("is-on", x === c); });
      document.querySelectorAll(".m42-a-tile[data-cat], .m42-a-rows li[data-cat]").forEach(function (t) {
        var tc = t.getAttribute("data-cat");
        t.classList.toggle("is-out", cat !== "*" && !!tc && tc !== cat);
      });
      return;
    }
    var tb = ev.target.closest && ev.target.closest("[data-m42-tab]");
    if (tb) {
      var tabs = tb.closest("[data-m42-tabs]"), want = tb.getAttribute("data-m42-tab");
      tabs.querySelectorAll("[data-m42-tab]").forEach(function (x) { x.classList.toggle("is-on", x === tb); });
      var table = tabs.parentElement.querySelector("table");
      if (table) table.querySelectorAll("tbody tr").forEach(function (tr) {
        tr.style.display = want === "*" || tr.textContent.indexOf(want) >= 0 ? "" : "none";
      });
    }
  });
  document.addEventListener("input", function (ev) {
    var s = ev.target;
    if (!s.hasAttribute || !s.hasAttribute("data-m42-prod-search")) return;
    var q = s.value.trim().toLowerCase(), box = s.closest(".m42-a-prod");
    box.querySelectorAll(".m42-a-tile, .m42-a-rows li").forEach(function (t) {
      t.classList.toggle("is-out", !!q && t.textContent.toLowerCase().indexOf(q) < 0);
    });
  });
})();
