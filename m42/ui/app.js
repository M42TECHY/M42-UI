"use strict";

const TOKEN = new URLSearchParams(location.search).get("t") || "";
const $ = (id) => document.getElementById(id);
const chat = $("chat");
const EMPTY_HTML = $("empty").outerHTML;  // welcome screen, restored for new chats
let busy = false;
let current = null;          // streaming assistant message {el, body, raw}
const cards = new Map();     // tool call id -> card element
let lastModels = [];
let lastLocal = [];
let statusTimer = null;

// ---------------------------------------------------------------- api

async function api(path, opts = {}) {
  const res = await fetch(path, {
    ...opts,
    headers: { "Content-Type": "application/json", "X-M42-Token": TOKEN, ...(opts.headers || {}) },
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || res.statusText);
  return data;
}
const post = (path, body) => api(path, { method: "POST", body: JSON.stringify(body || {}) });

// ---------------------------------------------------------------- markdown

function esc(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
function inline(s) {
  return esc(s)
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<b>$1</b>")
    .replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>')
    .replace(/(?<![">=\/])\bhttps?:\/\/[^\s<)\]]+/g, (u) => `<a href="${u}" target="_blank" rel="noopener">${u}</a>`);
}
function renderBlocks(text) {
  let out = "", para = [], list = null;
  const flushPara = () => { if (para.length) { out += `<p>${para.map(inline).join("<br>")}</p>`; para = []; } };
  const flushList = () => {
    if (list) {
      const start = list.tag === "ol" && list.start > 1 ? ` start="${list.start}"` : "";
      out += `<${list.tag}${start}>${list.items.map((i) => `<li>${inline(i)}</li>`).join("")}</${list.tag}>`;
      list = null;
    }
  };
  const addItem = (tag, item, start = 1) => {
    flushPara();
    if (!list || list.tag !== tag) { flushList(); list = { tag, items: [], start }; }
    list.items.push(item);
  };
  for (const line of text.split("\n")) {
    let m;
    if (!line.trim()) { flushPara(); flushList(); continue; }
    if ((m = line.match(/^(#{1,3})\s+(.*)/))) {
      flushPara(); flushList();
      out += `<h${m[1].length}>${inline(m[2])}</h${m[1].length}>`;
    } else if ((m = line.match(/^\s*[-*]\s+(.*)/))) addItem("ul", m[1]);
    else if ((m = line.match(/^\s*(\d+)[.)]\s+(.*)/))) addItem("ol", m[2], Number(m[1]));  // keep "3." as 3
    else { flushList(); para.push(line); }
  }
  flushPara(); flushList();
  return out;
}
function renderMarkdown(src) {
  return src.split("```").map((part, i) => {
    if (i % 2 === 0) return renderBlocks(part);
    const nl = part.indexOf("\n");
    const code = nl >= 0 ? part.slice(nl + 1) : part;
    if (nl >= 0 && part.slice(0, nl).trim().toLowerCase() === "mermaid") {  // drawn by renderDiagrams()
      return `<div class="diagram" data-code="${encodeURIComponent(code)}"><pre><code>${esc(code.replace(/\n$/, ""))}</code></pre></div>`;
    }
    // every code block: its language and a 📋 Copy button (the whole block, exactly as written)
    const lang = nl >= 0 ? part.slice(0, nl).trim().split(/\s+/)[0] : "";
    // a whole web page: ▶ Run shows it working in a popup, with ⬇ Download (HTML + CSS + JS) under it
    const page = /^(html?|)$/i.test(lang) && /<!doctype html|<html[\s>]|<body[\s>]/i.test(code);
    const body = code.replace(/\n$/, "");
    const lines = body ? body.split("\n").length : 0;
    if (page) {  // a whole page: a file card, its code folded away (the user, 2026-11-12: "not a huge code dump, as Claude shows it")
      const title = (code.match(/<title>([^<]{1,80})<\/title>/i) || [])[1] || "index.html";
      return `<div class="code-block file-card" data-page="1"><div class="fc-main">` +
        `<span class="fc-icon" aria-hidden="true">&lt;/&gt;</span><div class="fc-text"><b>${esc(title)}</b>` +
        `<small>HTML page · ${lines.toLocaleString()} lines</small></div><div class="fc-actions">` +
        `<button type="button" class="code-run" title="Open this page in the preview">Preview</button>` +
        `<button type="button" class="code-copy" title="Copy the page's code">Copy</button>` +
        `<button type="button" class="code-toggle" title="Show the code" aria-expanded="false">Code</button></div></div>` +
        `<pre hidden><code>${esc(body)}</code></pre></div>`;
    }
    const long = lines > 24;  // a long block is folded; "Show all" opens it
    return `<div class="code-block${long ? " long folded" : ""}"><div class="code-head"><span class="code-lang">${esc(lang || "code")}</span>` +
      `<span class="code-lines">${lines} lines</span>` +
      `<button type="button" class="code-copy" title="Copy this code">Copy</button></div>` +
      `<pre><code>${esc(body)}</code></pre>` +
      (long ? `<button type="button" class="code-more">Show all ${lines} lines</button>` : "") + `</div>`;
  }).join("");
}

async function copyText(text) {
  try { await navigator.clipboard.writeText(text); return true; } catch { /* the older way below */ }
  const t = Object.assign(document.createElement("textarea"), { value: text });
  t.style.cssText = "position:fixed;opacity:0";
  document.body.appendChild(t);
  t.select();
  const ok = document.execCommand("copy");
  t.remove();
  return ok;
}

document.addEventListener("click", async (e) => {
  const btn = e.target.closest(".code-copy");
  if (!btn) return;
  const code = btn.closest(".code-block")?.querySelector("code");
  if (!code) return;
  const ok = await copyText(code.textContent);
  btn.textContent = ok ? "✓ Copied" : "Copy failed";
  btn.classList.toggle("done", ok);
  clearTimeout(btn._t);
  btn._t = setTimeout(() => { btn.textContent = "Copy"; btn.classList.remove("done"); }, 1500);
});
document.addEventListener("click", (e) => {
  const tog = e.target.closest(".code-toggle");
  if (tog) {  // a page's code, shown / folded again
    const pre = tog.closest(".code-block")?.querySelector("pre");
    if (!pre) return;
    pre.hidden = !pre.hidden;
    tog.setAttribute("aria-expanded", String(!pre.hidden));
    tog.classList.toggle("on", !pre.hidden);
    return;
  }
  const more = e.target.closest(".code-more");
  if (more) {
    const block = more.closest(".code-block");
    const folded = block.classList.toggle("folded");
    more.textContent = folded ? more.textContent.replace(/^Show less$/, `Show all ${block.querySelector("code").textContent.split("\n").length} lines`) : "Show less";
  }
});

// ---------------------------------------------------------------- ▶ Run: a page from the chat, working, in a popup

/** The page runs in a sandboxed iframe (scripts yes, M42's own origin no) from its own preview folder, with
 * desktop / tablet / phone widths, and ⬇ Download under it: a zip with index.html and the CSS / JS it uses. */
async function openPreview(code) {
  let d;
  try { d = await post("/api/page/preview", { html: code }); } catch (e) { showError(e.message); return; }
  showPreview(d);
}

/** The preview M42 made (one page from the chat, or a site built in the project folder), in the panel beside the
 * chat: the page and the chat side by side, its width (desktop / tablet / phone), reload, open in the browser,
 * download. (The user, 2026-11-12: no popup over the chat.) */
let lastPreview = null;
function showPreview(d) {
  lastPreview = d;
  const pane = $("previewPane"), frame = $("ppFrame");
  $("ppAddress").textContent = (d.url || "").split("/").pop() || "index.html";
  frame.src = d.url;
  $("ppOpen").href = d.url;
  $("ppDownload").href = `${d.download}&t=${encodeURIComponent(TOKEN)}`;
  $("ppDownload").setAttribute("download", "m42-page.zip");
  pane.hidden = false;
  if (typeof files !== "undefined" && files.open) {
    if (files.editing) {  // a change asked from the files panel: the panel stays, the page waits behind it
      pane.hidden = true; files.previewWasOpen = true;
      return;
    }
    $("filesPane").hidden = true; files.open = false; $("filesBtn").classList.remove("on");  // (the new page is shown)
  }
  document.querySelector(".app").classList.add("has-preview");
}
function closePreview() {
  $("previewPane").hidden = true;
  $("ppFrame").src = "about:blank";
  document.querySelector(".app").classList.remove("has-preview");
}
(function previewPaneTools() {
  $("ppReload").onclick = () => { if (lastPreview) $("ppFrame").src = lastPreview.url + "?r=" + Date.now(); };
  // 🎯 pick a part: the page outlines the block under the mouse; a click on it puts it in the message box, and the
  // words written then are a change to that block only (the user, 2026-11-17: click-to-edit)
  const pickBtn = $("ppPick");
  const pickOff = () => { pickBtn.classList.remove("on"); try { $("ppFrame").contentWindow.postMessage("m42:pick-off", "*"); } catch { /* */ } };
  pickBtn.onclick = () => {
    if (!lastPreview) return;
    if (pickBtn.classList.contains("on")) { pickOff(); return; }
    pickBtn.classList.add("on");
    try { $("ppFrame").contentWindow.postMessage("m42:pick-on", "*"); } catch { /* */ }
  };
  $("ppFrame").addEventListener("load", () => pickBtn.classList.remove("on"));
  window.addEventListener("message", (e) => {
    if (e.source !== $("ppFrame").contentWindow || !e.data || !("m42pick" in e.data)) return;
    pickBtn.classList.remove("on");
    if (!e.data.m42pick) return;
    pendingPick = e.data.m42pick;
    renderAttachments();
    $("input").focus();
  });
  $("ppClose").onclick = closePreview;
  // 📷 the part of the page on screen, as a picture in the message box: the user writes the correction with it
  $("ppShot").onclick = async () => {
    const frame = $("ppFrame"), btn = $("ppShot");
    if (!lastPreview || btn.disabled) return;
    if (pendingImages.length >= 3) { showError("Up to 3 pictures in one message."); return; }
    const where = await new Promise((done) => {  // how far the page is scrolled, and which page (it answers; else the top)
      const t = setTimeout(() => { window.removeEventListener("message", on); done({}); }, 400);
      function on(e) {
        if (e.source !== frame.contentWindow || typeof e.data?.m42scroll !== "number") return;
        clearTimeout(t); window.removeEventListener("message", on); done(e.data);
      }
      window.addEventListener("message", on);
      try { frame.contentWindow.postMessage("m42:scroll?", "*"); } catch { /* */ }
    });
    btn.disabled = true;
    btn.classList.add("busy");
    try {
      const r = frame.getBoundingClientRect();
      const url = /^\/preview\//.test(where.m42path || "") ? where.m42path : frame.src.split("?")[0];  // (a page opened from its menu)
      const d = await post("/api/page/shot", { url, width: r.width, height: r.height, scroll: where.m42scroll || 0 });
      pendingImages.push(d.image);
      // (a picture of the page itself: a correction of it; where it was taken, so a mark on it is a place on the page)
      imgMeta.set(d.image, { own: true, shot: { page: url.split("/").pop(), width: Math.round(r.width), scroll: where.m42scroll || 0 } });
      renderAttachments();
      $("input").focus();
    } catch (e) { showError(e.message); }
    finally { btn.disabled = false; btn.classList.remove("busy"); }
  };
  // the preview's width: dragged at its left edge (the user, 2026-11-12: no phone / tablet / wider buttons), kept
  // (the 📁 files panel in the same place: its own grip, the same width; the user, 2026-11-13)
  const app = document.querySelector(".app");
  const setW = (w) => {
    // the chat keeps 320 px at least; the sidebar as wide as it is now (folded away in a narrow window: dragging
    // wider there made the panel narrower, 2026-11-13)
    const side = document.querySelector(".sidebar")?.getBoundingClientRect().width || 0;
    const max = Math.max(320, app.clientWidth - side - 320);
    w = Math.round(Math.min(max, Math.max(320, w)));
    app.style.setProperty("--pv-w", w + "px");
    return w;
  };
  try { const w = +localStorage.getItem("m42.previewWidth"); if (w) setW(w); } catch { /* private window */ }
  for (const grip of [$("ppResize"), $("fpResize")]) {
  grip.addEventListener("pointerdown", (e) => {
    e.preventDefault();
    grip.setPointerCapture(e.pointerId);
    app.classList.add("pv-resizing");
    const move = (ev) => setW(app.getBoundingClientRect().right - ev.clientX);
    const up = (ev) => {
      grip.releasePointerCapture(ev.pointerId);
      grip.removeEventListener("pointermove", move);
      grip.removeEventListener("pointerup", up);
      app.classList.remove("pv-resizing");
      try { localStorage.setItem("m42.previewWidth", parseInt(app.style.getPropertyValue("--pv-w"), 10) || ""); } catch { /* */ }
    };
    grip.addEventListener("pointermove", move);
    grip.addEventListener("pointerup", up);
  });
  grip.addEventListener("dblclick", () => {  // back to the usual width
    app.style.removeProperty("--pv-w");
    try { localStorage.removeItem("m42.previewWidth"); } catch { /* */ }
  });
  }
})();

document.addEventListener("click", (e) => {
  const btn = e.target.closest(".code-run");
  if (!btn) return;
  const code = btn.closest(".code-block")?.querySelector("code");
  if (code) openPreview(code.textContent);
});

// a request that ended with a new page: its preview opens by itself (once per page)
let pagesShown = 0;
function countPages() { return chat.querySelectorAll('.code-block[data-page="1"]').length; }
function previewNewPage() {
  const blocks = chat.querySelectorAll('.code-block[data-page="1"]');
  if (blocks.length > pagesShown && !replaying) {  // (a chat opened again: its old pages stay closed)
    const code = blocks[blocks.length - 1].querySelector("code");
    if (code) openPreview(code.textContent);
  }
  pagesShown = blocks.length;
}

// ---------------------------------------------------------------- diagrams (Mermaid, bundled: works offline)

let mermaidReady = null, diagramCount = 0;
function loadMermaid() {
  if (!mermaidReady) {
    mermaidReady = new Promise((ok, fail) => {
      const s = document.createElement("script");
      s.src = "vendor/mermaid.min.js";
      s.onload = () => {
        const bg = getComputedStyle(document.body).backgroundColor.match(/\d+/g) || [255, 255, 255];
        const dark = (+bg[0] + +bg[1] + +bg[2]) / 3 < 128;
        // no HTML labels: plain SVG text, so "⬇ PNG" can draw it on a canvas
        mermaid.initialize({ startOnLoad: false, securityLevel: "strict", theme: dark ? "dark" : "default",
          htmlLabels: false, flowchart: { htmlLabels: false } });
        ok();
      };
      s.onerror = () => { mermaidReady = null; fail(new Error("vendor/mermaid.min.js is missing")); };
      document.head.appendChild(s);
    });
  }
  return mermaidReady;
}
async function renderDiagrams(root) {
  const boxes = [...root.querySelectorAll(".diagram:not(.drawn)")];
  if (!boxes.length) return;
  try { await loadMermaid(); } catch { return; }  // the code stays visible
  for (const box of boxes) {
    box.classList.add("drawn");
    const code = decodeURIComponent(box.dataset.code);
    const id = "m42diagram" + (++diagramCount);
    try {
      const { svg } = await mermaid.render(id, code);
      box.innerHTML = `<div class="diagram-svg">${svg}</div><div class="diagram-bar">` +
        `<button class="btn small" data-act="svg">⬇ SVG</button><button class="btn small" data-act="png">⬇ PNG</button>` +
        `<button class="btn small ghost" data-act="code">&lt;/&gt; Code</button></div>` +
        `<pre class="diagram-code" hidden><code>${esc(code)}</code></pre>`;
    } catch (e) {
      document.getElementById("d" + id)?.remove();  // mermaid leaves its error drawing in <body>
      box.insertAdjacentHTML("beforeend", `<div class="diagram-error">⚠ This diagram doesn't draw: ` +
        `${esc(String((e && e.message) || e).split("\n")[0])}</div>`);
    }
  }
}
function saveBlob(blob, name) {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 5000);
}
chat.addEventListener("click", (e) => {
  const btn = e.target.closest(".diagram-bar button");
  if (!btn) return;
  const box = btn.closest(".diagram");
  const svgEl = box.querySelector("svg");
  if (btn.dataset.act === "code") { const pre = box.querySelector(".diagram-code"); pre.hidden = !pre.hidden; return; }
  if (!svgEl) return;
  const clone = svgEl.cloneNode(true);
  clone.setAttribute("xmlns", "http://www.w3.org/2000/svg");
  const text = new XMLSerializer().serializeToString(clone);
  if (btn.dataset.act === "svg") { saveBlob(new Blob([text], { type: "image/svg+xml" }), "diagram.svg"); return; }
  const box2 = svgEl.getBoundingClientRect(), scale = 3;  // 3x: sharp enough for slides and papers
  const img = new Image();
  img.onload = () => {
    const c = document.createElement("canvas");
    c.width = Math.ceil(box2.width * scale); c.height = Math.ceil(box2.height * scale);
    const g = c.getContext("2d");
    g.fillStyle = getComputedStyle(document.body).backgroundColor || "#fff";
    g.fillRect(0, 0, c.width, c.height);
    g.drawImage(img, 0, 0, c.width, c.height);
    try { c.toBlob((b) => saveBlob(b, "diagram.png"), "image/png"); }
    catch { showNote("PNG isn't possible for this diagram; use ⬇ SVG."); }
  };
  img.src = "data:image/svg+xml;charset=utf-8," + encodeURIComponent(text);
});

// The game's elements, drawn before any code: the user checks each one, redraws what's wrong, then starts the code
function showElements(ev) {
  const card = make("div", "plan-card elements-card");
  const v = Date.now();  // a redrawn picture keeps its file name: don't show the cached old one
  card.innerHTML = `<div class="plan-head">🎨 <b>Elements for ${esc(ev.plan_title || "the game")}</b>` +
    `<div class="sub">Check each picture. Wrong? Change its description and press ↻. The code starts only after ` +
    `"Elements OK".</div></div><div class="el-grid">` +
    (ev.items || []).map((it, i) => `<div class="el-item" data-i="${i}">` +
      `<img src="${mediaUrl(it.path)}&v=${v}" alt="${esc(it.name)}" class="${it.kind === "background" ? "el-bg" : ""}">` +
      ((it.options || []).length > 1 ? `<div class="el-opts">` + it.options.map((p, k) =>
        `<img src="${mediaUrl(p)}&v=${v}" data-p="${esc(p)}" title="Use this one"${k === 0 ? ' class="picked"' : ""}>`).join("") +
        `</div>` : "") +
      `<b>${esc(it.name)}</b>${it.kind === "background" ? ' <span class="tag">background</span>' : ""}` +
      `<textarea rows="2" class="el-what">${esc(it.what)}</textarea>` +
      `<button class="btn small el-redo">↻ Redraw</button></div>`).join("") +
    `</div><div class="plan-foot"><span class="sub">${(ev.items || []).length} elements · click a small picture to use it</span>` +
    (ev.after_build ? `<span class="sub">The game already uses these names: reload it to see the new pictures.</span>`
      : `<button class="btn primary el-ok">▶ Elements OK — start code</button>`) + `</div>`;
  card.querySelectorAll(".el-opts img").forEach((im) => (im.onclick = async () => {
    const box = im.closest(".el-item"), it = ev.items[+box.dataset.i];
    try {
      await api("/api/element/choose", { method: "POST", body: JSON.stringify({ name: it.name, path: im.dataset.p }) });
      box.querySelector(":scope > img").src = mediaUrl(it.path) + "&v=" + Date.now();
      box.querySelectorAll(".el-opts img").forEach((x) => x.classList.toggle("picked", x === im));
    } catch (e) { showError(e.message); }
  }));
  card.querySelectorAll(".el-redo").forEach((b) => (b.onclick = () => {
    if (busy) return;
    const box = b.closest(".el-item"), it = ev.items[+box.dataset.i];
    const what = box.querySelector(".el-what").value.trim() || it.what;
    card.querySelectorAll("button, textarea").forEach((el) => (el.disabled = true));
    send("Redraw " + it.name, { endpoint: "/api/element", body: { name: it.name, what, kind: it.kind },
                                shown: `↻ Redraw ${it.name}: ${what}` });
  }));
  if (card.querySelector(".el-ok")) card.querySelector(".el-ok").onclick = () => {
    if (busy) return;
    card.querySelectorAll("button, textarea").forEach((el) => (el.disabled = true));
    send("Start code", { endpoint: "/api/build", body: { elements_ok: true }, shown: "▶ Elements OK — start code" });
  };
  append(card);
}

// Charts made by make_chart: the PNG in the chat, with its SVG / PDF for papers
function mediaUrl(p) { return `/api/media?t=${encodeURIComponent(TOKEN)}&path=${encodeURIComponent(p)}`; }
function showImage(ev) {
  const files = ev.files && ev.files.length ? ev.files : [ev.path];
  const links = files.map((f) => {
    const name = f.split(/[\\/]/).pop();
    return `<a class="btn small" href="${mediaUrl(f)}" download="${esc(name)}">⬇ ${esc(name.split(".").pop().toUpperCase())}</a>`;
  }).join("");
  append(make("div", "chart-card", `<a href="${mediaUrl(ev.path)}" target="_blank"><img src="${mediaUrl(ev.path)}" alt="chart"></a>` +
    `<div class="diagram-bar"><span class="sub">${esc(ev.caption || "")}</span>${links}</div>`));
}
// Hide raw <tool_call> text that some models print instead of using native tool calls.
function visibleText(raw, streaming = false) {
  let t = raw.replace(/<tool_call>[\s\S]*?(<\/tool_call>|$)/g, "")
    .replace(/<tool_response>[\s\S]*?(<\/tool_response>|$)/g, "");  // fake tool output from the model
  if (streaming) t = t.replace(/(```(json)?\s*)?\{\s*"name"\s*:[\s\S]*$/, "");  // bare JSON tool call in progress
  const tag = "<tool_call>";
  for (let n = tag.length - 1; n > 0; n--) {
    if (t.endsWith(tag.slice(0, n))) { t = t.slice(0, -n); break; }
  }
  // a line edit being written (SEARCH / REPLACE blocks): its plan stays, the raw code is not shown (the user,
  // 2026-11-12: "the edit runs down the chat like a search dump"); the edit card shows the diff when it is done
  const at = t.search(/^\s*<{5,}\s*SEARCH/m);
  if (at >= 0) {
    const n = (t.match(/^\s*<{5,}\s*SEARCH/gm) || []).length;
    t = t.slice(0, at).trim() + `\n\n✏ ${streaming ? "Writing" : "Wrote"} ${n} change${n === 1 ? "" : "s"} to the page${streaming ? "…" : ""}`;
  }
  return t.trim();
}

// ---------------------------------------------------------------- chat rendering

function nearBottom() { return chat.scrollHeight - chat.scrollTop - chat.clientHeight < 120; }
function append(el) {
  const stick = nearBottom();
  $("empty")?.remove();
  chat.appendChild(el);
  if (stick) chat.scrollTop = chat.scrollHeight;
  return el;
}
function make(tag, cls, html) {
  const el = document.createElement(tag);
  if (cls) el.className = cls;
  if (html !== undefined) el.innerHTML = html;
  return el;
}

function clock(t) {
  return new Date(t * 1000).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}
function duration(s) {
  s = Math.round(s);
  return s < 60 ? `${s}s` : `${Math.floor(s / 60)}m ${String(s % 60).padStart(2, "0")}s`;
}
function addUser(text, time, images, raw) {
  const m = make("div", "msg user");
  const b = make("div", "bubble");
  b.textContent = text;
  m.appendChild(b);
  if (images && images.length) {  // the screenshots sent with this message (live view only)
    const row = make("div", "msg-images");
    images.forEach((u) => row.appendChild(make("img", "", "")).setAttribute("src", u));
    m.appendChild(row);
  }
  // ✎ Edit and send again, ⧉ Copy (as in Claude; also after Stop: the user, 2026-11-13). The words alone: the
  // markers M42 shows after them (🖼×1, ✏ marked, 📄 file) are not part of what was typed
  const words = raw ?? String(text).replace(/(?:\s+(?:🖼×\d+|✏ marked|📄 .*))+\s*$/u, "").replace(/^🎨 /u, "");
  const acts = make("div", "msg-actions");
  const copy = make("button", "msg-act", '<svg viewBox="0 0 24 24" width="15" height="15" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V6a2 2 0 0 1 2-2h9"/></svg>');
  copy.type = "button"; copy.title = "Copy"; copy.setAttribute("aria-label", "Copy");
  copy.onclick = () => navigator.clipboard?.writeText(words).then(() => showNote("Copied")).catch(() => {});
  const edit = make("button", "msg-act", '<svg viewBox="0 0 24 24" width="15" height="15" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M4 20h4L19 9l-4-4L4 16z"/><path d="M13.5 6.5l4 4"/></svg>');
  edit.type = "button"; edit.title = "Edit and send again"; edit.setAttribute("aria-label", "Edit");
  // a change asked for lines of a file (📁 Files): edited as that ask, for the same lines
  const lm = /^✏ (.+?) · lines? (\d+)(?:–(\d+))?: ([\s\S]*)$/u.exec(String(text));
  const lines = lm ? { path: lm[1], start: +lm[2], end: +(lm[3] || lm[2]) } : null;
  edit.onclick = () => editUserMessage(m, lines ? lm[4] : words, !lines && (!!(images && images.length) || words !== text), lines);
  acts.append(copy, edit);
  if (time) acts.prepend(make("span", "msg-time", esc(clock(time))));
  m.appendChild(acts);
  append(m);
}

/** ✎ A message sent before, edited and sent again: what came after it goes (on screen and in the saved chat), as in
 * Claude; a request still running is stopped first. */
function editUserMessage(m, words, hadExtras, lines = null) {
  if (m.querySelector(".edit-box")) return;
  const bubble = m.querySelector(".bubble"), acts = m.querySelector(".msg-actions");
  bubble.hidden = true; if (acts) acts.hidden = true;
  const box = make("div", "edit-box"), ta = make("textarea", "edit-input");
  ta.value = words; ta.rows = 1;
  const fit = () => { ta.style.height = "auto"; ta.style.height = Math.min(ta.scrollHeight, 320) + "px"; };
  ta.addEventListener("input", fit);
  const row = make("div", "edit-row");
  if (hadExtras) row.appendChild(make("span", "edit-hint", "Pictures / files sent with it are not sent again: add them with +"));
  const cancel = make("button", "btn small ghost", "Cancel"), go = make("button", "btn small primary", "Send");
  cancel.type = go.type = "button";
  const close = () => { box.remove(); bubble.hidden = false; if (acts) acts.hidden = false; };
  cancel.onclick = close;
  go.onclick = async () => {
    const t = ta.value.trim();
    if (!t) return;
    go.disabled = cancel.disabled = true;
    const nth = [...chat.querySelectorAll(".msg.user")].indexOf(m);
    if (busy) {  // the request still running: stopped, and waited for (its stream ends)
      await post("/api/stop").catch(() => {});
      for (let i = 0; i < 600 && busy; i++) await new Promise((r) => setTimeout(r, 100));
    }
    try { await post("/api/sessions/truncate", { nth, words }); }
    catch (e) { showError(e.message); go.disabled = cancel.disabled = false; return; }
    for (let n = m; n;) { const next = n.nextSibling; n.remove(); n = next; }  // this message and all after it
    if (lines) {  // the same lines of the same file, with the new ask
      const span = lines.start === lines.end ? `line ${lines.start}` : `lines ${lines.start}–${lines.end}`;
      send(t, { shown: `✏ ${lines.path} · ${span}: ${t}`, body: { message: t, lines } });
    } else send(t);
  };
  ta.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); go.click(); }
    else if (e.key === "Escape") { e.preventDefault(); close(); }
  });
  row.append(cancel, go);
  box.append(ta, row);
  m.insertBefore(box, bubble);
  fit(); ta.focus(); ta.setSelectionRange(ta.value.length, ta.value.length);
}

function startAssistant() {
  finishAssistant();
  const el = make("div", "msg assistant");
  const body = make("div", "md cursor", '<span class="thinking">Reading context…</span>');
  el.appendChild(body);
  append(el);
  current = { el, body, raw: "", pending: false };
}
function renderAssistant() {
  if (!current || current.pending) return;
  current.pending = true;
  requestAnimationFrame(() => {
    if (!current) return;
    current.pending = false;
    const stick = nearBottom();
    const text = visibleText(current.raw, true);
    current.body.innerHTML = text ? renderMarkdown(text) : '<span class="thinking">Working…</span>';
    if (stick) chat.scrollTop = chat.scrollHeight;
  });
}
function finishAssistant() {
  if (!current) return;
  const text = visibleText(current.raw);
  if (text) {
    current.body.classList.remove("cursor");
    current.body.innerHTML = renderMarkdown(text);
    renderDiagrams(current.body);
    lastAnswer = current.el;
  } else {
    current.el.remove();
  }
  current = null;
}

const TOOL_META = {
  list_dir: ["📁", "List", (a) => a.path || "."],
  read_file: ["📄", "Read", (a) => a.path],
  write_file: ["📝", "Write", (a) => a.path],
  edit_file: ["✏️", "Edit", (a) => a.path],
  search: ["🔍", "Search", (a) => a.pattern],
  run_command: ["▶", "Run", (a) => a.command],
  check_page: ["🌐", "Browser check", (a) => a.path],
  make_chart: ["📊", "Chart", (a) => a.name],
  download_library: ["📦", "Download library", (a) => a.name + (a.save_as ? ` → ${a.save_as}` : "")],
  web_search: ["🌐", "Search web", (a) => a.query + (a.source && a.source !== "all" ? ` (${a.source})` : "")],
  fetch_url: ["🔗", "Read page", (a) => a.url],
  search_docs: ["📚", "Local docs", (a) => a.query + (a.doc ? ` (${a.doc})` : "")],
  read_doc: ["📖", "Read doc", (a) => a.ref],
  auto_verify: ["🛡️", "Auto-check online", (a) => `${a.reason ? a.reason + ": " : ""}${a.query}`],
  search_library: ["📚", "Paper library", (a) => a.query],
  check_references: ["📑", "Check references", (a) => a.bib_path + (a.tex_paths?.length ? ` + ${a.tex_paths.length} .tex` : "")],
  get_bibtex: ["🔖", "BibTeX", (a) => (Array.isArray(a.dois) ? a.dois.join(", ") : a.dois || "") + (a.save_to ? ` → ${a.save_to}` : "")],
  list_library: ["📚", "List library", () => ""],
  search_papers: ["🎓", "Research papers", (a) => a.query + (a.quartile ? ` · ${a.quartile}` : "") +
    (a.limit ? ` · ${a.limit}` : "")],
  make_tool: ["🧰", "New M42 tool", (a) => a.name],
};
const toolMeta = (name) => TOOL_META[name]
  || (name.startsWith("tool_") ? ["🧰", "M42 tool", () => name.slice(5)] : ["🔧", name, () => ""]);
const QUIET_TOOLS = new Set(["web_search", "fetch_url", "read_file", "list_dir", "search",
  "search_docs", "read_doc", "auto_verify", "search_papers", "search_library", "list_library", "check_references"]);
const VERIFY_MESSAGE = "Verify my previous answer online.";  // the server does the web search itself
let lastAnswer = null;   // element of the most recent final answer
let replaying = false;   // re-drawing a saved chat: skip side effects like file-tree refreshes

function toolCard(ev) {
  finishAssistant();
  const [icon, label, argOf] = toolMeta(ev.name);
  const card = make("div", "tool running");
  card.dataset.tool = ev.name;
  const head = make("div", "tool-head",
    `<span class="tool-icon">${icon}</span>
     <span class="tool-title"><b>${esc(label)}</b><span class="arg">${esc(argOf(ev.args || {}) || "")}</span></span>
     <span class="tool-state">Running</span><span class="tool-chev" aria-hidden="true"></span>`);
  head.addEventListener("click", () => card.classList.toggle("open"));
  card.append(head, make("div", "tool-body"));
  cards.set(ev.id, card);
  append(card);
}

function approvalCard(ev) {
  const card = cards.get(ev.id);
  if (!card) return;
  card.classList.add("approval");
  card.querySelector(".tool-state").textContent = "Needs approval";
  const a = ev.args || {};
  const what = ev.name === "run_command" ? a.command
    : ev.name === "edit_file" ? `--- replace ---\n${a.old_text}\n--- with ---\n${a.new_text}`
    : ev.name === "make_tool" ? `${a.description || ""}\n\nTest with: ${JSON.stringify(a.example || {})}\n\n${a.code || ""}`
    : a.content ?? JSON.stringify(a, null, 2);
  const verb = ev.name === "run_command" ? "Run this command?"
    : ev.name === "download_library" ? `Download ${a.name} from cdnjs into ${a.save_as || "the project"}?`
    : ev.name === "make_tool" ? `Keep a new M42 tool "${a.name}"? (it is tested first, then offered in later chats)`
    : `${TOOL_META[ev.name]?.[1] || ev.name} ${a.path || ""}?`;
  const why = ev.why ? `<div class="approval-why">⚠ M42 asks because ${esc(ev.why)}</div>` : "";
  const box = make("div", "approval-box", `<div>${esc(verb)}</div>${why}<pre>${esc(what || "")}</pre>`);
  const row = make("div", "row");
  const deny = make("button", "btn small ghost", "Deny");
  const allow = make("button", "btn small ok", "Allow");
  const answer = async (ok) => {
    box.remove();
    card.classList.remove("approval");
    card.querySelector(".tool-state").textContent = ok ? "Running" : "Denied";
    try { await post("/api/approve", { id: ev.id, allow: ok }); } catch (e) { showError(e.message); }
  };
  deny.onclick = () => answer(false);
  allow.onclick = () => answer(true);
  row.append(deny, allow);
  box.appendChild(row);
  card.appendChild(box);
  chat.scrollTop = chat.scrollHeight;
  allow.focus();
}

/** A unified diff as rows: the line's number in the file, a + / − mark, the line (Claude's edit view); the file
 *  headers dropped, each hunk a thin "⋯" row between. Returns {html, added, removed}. */
function diffView(diff) {
  let oldN = 0, newN = 0, added = 0, removed = 0;
  const rows = [];
  for (const l of diff.split("\n")) {
    if (l.startsWith("+++") || l.startsWith("---")) continue;
    const h = l.match(/^@@ -(\d+)(?:,\d+)? \+(\d+)/);
    if (h) {
      oldN = +h[1]; newN = +h[2];
      if (rows.length) rows.push('<div class="dl gap"><span class="dn"></span><span class="dm"></span><span class="dt">⋯</span></div>');
      continue;
    }
    if (l.startsWith("+")) {
      added++;
      rows.push(`<div class="dl add"><span class="dn">${newN++}</span><span class="dm">+</span><span class="dt">${esc(l.slice(1)) || " "}</span></div>`);
    } else if (l.startsWith("-")) {
      removed++;
      rows.push(`<div class="dl del"><span class="dn">${oldN++}</span><span class="dm">−</span><span class="dt">${esc(l.slice(1)) || " "}</span></div>`);
    } else if (l.startsWith(" ") || (l === "" && rows.length)) {
      rows.push(`<div class="dl"><span class="dn">${newN}</span><span class="dm"></span><span class="dt">${esc(l.slice(1)) || " "}</span></div>`);
      oldN++; newN++;
    }
  }
  return { html: rows.join(""), added, removed };
}
function diffHtml(diff) { return diffView(diff).html; }

function toolResult(ev) {
  const card = cards.get(ev.id);
  if (!card) return;
  card.classList.remove("running", "approval");
  card.classList.add(ev.ok ? "ok" : "fail");
  card.querySelector(".approval-box")?.remove();
  const state = card.querySelector(".tool-state");
  if (state.textContent !== "Denied") state.textContent = ev.ok ? "✓ Done" : "✗ Failed";
  const body = card.querySelector(".tool-body");
  body.innerHTML = `<div class="tool-summary">${esc(ev.summary || "")}</div>`;
  if (ev.diff) {  // Claude's edit view: "Edited index.html  +12 −3", the changed lines with their numbers
    const d = diffView(ev.diff);
    card.classList.add("edit");
    const title = card.querySelector(".tool-title");
    const file = ev.path || card.querySelector(".tool-title .arg")?.textContent || "";
    title.innerHTML = `<b>${card.dataset.tool === "write_file" ? "Wrote" : "Edited"}</b><span class="arg">${esc(file)}</span>` +
      `<span class="dc add">+${d.added}</span><span class="dc del">−${d.removed}</span>`;
    body.innerHTML = "";
    body.appendChild(make("div", "diff", d.html));
    if (ev.summary) body.appendChild(make("div", "tool-summary", esc(ev.summary)));
    if (d.added + d.removed <= 40) card.classList.add("open");
  } else if (ev.output !== undefined && ev.output !== null) {
    const pre = make("pre");
    pre.textContent = ev.output || "(no output)";
    body.appendChild(pre);
    if (!QUIET_TOOLS.has(card.dataset.tool)) card.classList.add("open");
  } else if (!ev.ok) {
    card.classList.add("open");
  }
  if (ev.changed && !replaying) refreshTree(ev.path);
  if (nearBottom()) chat.scrollTop = chat.scrollHeight;
}

function showError(msg) { finishAssistant(); append(make("div", "error", esc(msg))); }
function showNote(msg) { append(make("div", "note", esc(msg))); }

/** 🧠 "Was this edit right?" after every edit: only a yes is learned; a no, or no answer, keeps nothing (the user,
 *  2026-11-16). A no points at ↶ Undo. */
function askEdit(ev) {
  const box = append(make("div", "note lesson-ask",
    `✏ Did M42 do this edit right? <span class="lesson-q">(${esc(ev.understood || "")})</span>`));
  const row = make("span", "lesson-btns");
  const answer = async (right) => {
    row.querySelectorAll("button").forEach((b) => (b.disabled = true));
    try {
      const d = await post("/api/learn/edit", { id: ev.id, right });
      row.innerHTML = right ? (d.learned ? "✓ Right: remembered for the next edits" : "✓ Right") : "✕ Not right: nothing learned (↶ Undo puts it back)";
    } catch (e) { showError(e.message); row.querySelectorAll("button").forEach((b) => (b.disabled = false)); }
  };
  const yes = make("button", "btn small primary", "✓ Right"), no = make("button", "btn small ghost", "✕ Not right");
  yes.type = no.type = "button";
  yes.onclick = () => answer(true); no.onclick = () => answer(false);
  row.append(yes, no);
  box.appendChild(row);
}

/** 🧠 A rule M42 learned, kept PENDING: used for the next pages only after the user says yes (the user, 2026-11-16:
 *  "it learned before I confirmed the change was right"). */
function askLesson(ev) {
  const box = append(make("div", "note lesson-ask",
    `🧠 M42 would remember this for ${esc(ev.for || "the next pages")}: <b>${esc(ev.rule || "")}</b> ` +
    `<span class="lesson-q">Was the change right? Remember it?</span>`));
  const row = make("span", "lesson-btns");
  const answer = async (keep) => {
    row.querySelectorAll("button").forEach((b) => (b.disabled = true));
    try {
      await post("/api/learn/confirm", { kind: ev.kind, id: ev.id, keep });
      row.innerHTML = keep ? "✓ Remembered" : "✕ Forgotten";
    } catch (e) { showError(e.message); row.querySelectorAll("button").forEach((b) => (b.disabled = false)); }
  };
  const yes = make("button", "btn small primary", "✓ Yes, remember"), no = make("button", "btn small ghost", "✕ No");
  yes.type = no.type = "button";
  yes.onclick = () => answer(true); no.onclick = () => answer(false);
  row.append(yes, no);
  box.appendChild(row);
}

/** One live line per long step (planning): its text is replaced as the step moves on, with a running
 *  seconds counter so a minute of silent reading doesn't look like a hang. */
const progressLines = new Map();
function showProgress(ev) {
  let p = progressLines.get(ev.id);
  if (!p) {
    p = { el: append(make("div", "note progress")), start: Date.now(), timer: null };
    progressLines.set(ev.id, p);
    if (!replaying) p.timer = setInterval(() => drawProgress(p), 1000);
  }
  p.text = ev.text;
  if (ev.done) {
    clearInterval(p.timer);
    p.el.textContent = ev.text + (replaying ? "" : ` · ${Math.round((Date.now() - p.start) / 1000)}s`);
    progressLines.delete(ev.id);
  } else drawProgress(p);
}
function drawProgress(p) {
  p.el.textContent = replaying ? p.text : `${p.text} · ${Math.round((Date.now() - p.start) / 1000)}s`;
}

/** Build mode plan: tick the features you want, add notes, then Build. */
function showPlan(plan) {
  const card = make("div", "plan-card");
  const steps = plan.steps.map((s, i) => {
    const feats = plan.features.map((f, j) => ({ f, j })).filter(({ f }) => f.step === i + 1);
    if (!feats.length) return "";
    return `<div class="plan-step"><div class="plan-step-title">Step ${i + 1}: ${esc(s.title)}` +
      (s.files.length ? ` <span class="mono">${esc(s.files.join(", "))}</span>` : "") + `</div>` +
      feats.map(({ f, j }) => `<label class="plan-feat"><input type="checkbox" class="feat-box" data-i="${j}"${f.selected ? " checked" : ""}>` +
        `<span><b>${esc(f.name)}</b>${f.from_web ? ' <span class="tag">🌐 from the web: added by M42</span>'
          : f.essential ? "" : ' <span class="tag">extra</span>'}` +
        `<span class="sub">${esc(f.detail)}</span></span></label>`).join("") + `</div>`;
  }).join("");
  // Facts the plan follows: from the web (with sources), or the user's own. Untick wrong ones, add missing
  // ones, then "↻ Re-plan" plans again from exactly this list.
  const factList = plan.facts || [];
  const hosts = [...new Set((plan.sources || []).map((u) => { try { return new URL(u).hostname; } catch { return ""; } }))];
  const facts = `<div class="plan-step"><div class="plan-step-title">` +
      (factList.length ? `🌐 What M42 found on the web` + (plan.sources || []).map((u, i) =>
        ` <a href="${esc(u)}" target="_blank" rel="noopener">${esc(hosts[i] || u)}</a>`).join(",") : "📌 Facts the plan must follow") +
      `</div>` +
      factList.map((f, i) => `<label class="plan-feat${(plan.uncovered || []).includes(f) ? " uncovered" : ""}">` +
        `<input type="checkbox" class="fact-box" data-f="${i}" checked><span>${esc(f)}` +
        `${(plan.uncovered || []).includes(f) ? ' <span class="tag">⚠ the planner skipped this: added as a step below</span>' : ""}` +
        `</span></label>`).join("") +
      ((plan.dropped_facts || []).length ? `<div class="sub">Left out (not found on those pages): ${esc(plan.dropped_facts.join("; "))}</div>` : "") +
      `<textarea class="plan-addfacts" rows="2" placeholder="Wrong or missing? Untick facts above, or add your own, one per line (e.g. camera munnadi mattum scroll aagum)"></textarea>` +
      `<div class="plan-replan-row"><button class="btn small plan-replan">↻ Re-plan with these facts</button></div></div>`;
  // the steps as a flow diagram, made here from the plan (no model time); drawn when opened
  const shown = plan.steps.map((s, i) => ({ s, i })).filter(({ i }) => plan.features.some((f) => f.step === i + 1));
  const q = (t) => String(t).replace(/"/g, "'").slice(0, 70);
  const flow = `flowchart ${shown.length > 4 ? "TD" : "LR"}\n` +
    shown.map(({ s, i }) => `  s${i}["Step ${i + 1}: ${q(s.title)}` + (s.files.length ? `\n${q(s.files.join(", "))}` : "") + `"]`).join("\n") +
    "\n" + shown.slice(1).map(({ i }, k) => `  s${shown[k].i} --> s${i}`).join("\n");
  const diagram = shown.length > 1 ? `<details class="plan-diagram"><summary>🗺 Plan as a diagram</summary>` +
    `<div class="diagram" data-code="${encodeURIComponent(flow)}"><pre><code>${esc(flow)}</code></pre></div></details>` : "";
  // pictures of the game M42 found while researching it: "is this what you mean?" before anything is built
  const refs = (plan.ref_images || []).length ? `<div class="plan-step"><div class="plan-step-title">🖼 Is this the game ` +
    `you mean? (pictures from the pages M42 read)</div><div class="ref-row">` +
    plan.ref_images.map((r) => `<a href="${esc(r.page)}" target="_blank" rel="noopener"><img src="${mediaUrl(r.path)}" ` +
      `alt="reference"></a>`).join("") +
    `</div><div class="sub">Not this one? Send your own picture with "itha mathiri venum" and M42 plans from it.</div></div>` : "";
  card.innerHTML = `<div class="plan-head">🏗 <b>${esc(plan.title)}</b><div class="sub">${esc(plan.summary)}</div></div>` +
    refs + facts + steps + diagram + `<textarea class="plan-notes" rows="2" placeholder="Anything to add or change? (optional)"></textarea>` +
    `<div class="plan-foot"><span class="plan-est"></span><button class="btn primary plan-build">▶ Build</button></div>`;
  const details = card.querySelector("details.plan-diagram");
  if (details) details.ontoggle = () => { if (details.open) renderDiagrams(details); };
  const boxes = [...card.querySelectorAll("input.feat-box")];
  const est = () => {
    const n = new Set(boxes.filter((b) => b.checked).map((b) => plan.features[b.dataset.i].step)).size;
    card.querySelector(".plan-est").textContent =
      `${n} step${n === 1 ? "" : "s"} · about ${n * 3}–${n * 5} min on this PC · each step is checked in a browser`;
    card.querySelector(".plan-build").disabled = !n;
  };
  boxes.forEach((b) => (b.onchange = est));
  est();
  card.querySelector(".plan-build").onclick = () => {
    if (busy) return;
    const chosen = { ...plan, notes: card.querySelector(".plan-notes").value,
      features: plan.features.map((f, j) => ({ ...f, selected: boxes.find((b) => +b.dataset.i === j)?.checked ?? false })) };
    card.querySelectorAll("input, textarea, button").forEach((el) => (el.disabled = true));
    send("Build " + plan.title, { endpoint: "/api/build", body: { plan: chosen }, shown: "▶ Build: " + plan.title });
  };
  card.querySelector(".plan-replan").onclick = () => {
    if (busy) return;
    const kept = [...card.querySelectorAll("input.fact-box")].filter((b) => b.checked).map((b) => factList[+b.dataset.f]);
    const added = card.querySelector(".plan-addfacts").value.split(/\r?\n/).map((s) => s.trim()).filter(Boolean);
    const all = [...kept, ...added];
    if (!all.length) { showNote("Tick or add at least one fact to plan from."); return; }
    card.querySelectorAll("input, textarea, button").forEach((el) => (el.disabled = true));
    send("Re-plan", { endpoint: "/api/plan", body: { message: plan.request || plan.title, facts: all },
                      shown: `↻ Re-plan with ${all.length} facts` + (added.length ? ` (${added.length} added by you)` : "") });
  };
  append(card);
}
let switchNote = null;
function showModelSwitch(ev) {
  const why = ev.kind === "code" ? "for code" : ev.kind === "vision"
    ? "to read the picture (the model with eyes: only it has the image file)" : "for chat / research";
  if (ev.state === "start") {
    switchNote = append(make("div", "note", `🔀 Switching to <b>${esc(shortModel(ev.to))}</b> ${why}…`));
  } else if (switchNote) {
    switchNote.innerHTML = `🔀 Using <b>${esc(shortModel(ev.to))}</b> ${why} (switched in ${ev.secs}s)`;
    switchNote = null;
  }
}
function addVerifyButton() {
  // (M42 UI builds web pages: a web search of the answer adds nothing there and only took time; the user,
  // 2026-11-12: "verify online needed irukka?". The button is gone; the server's verify path stays for main M42.)
}
/** search_papers results as a table, drawn instantly instead of having the model re-type them. */
function showPapers(ev) {
  finishAssistant();
  const link = (r) => r.doi || r.oa_url || "";
  const rows = ev.rows.map((r, i) => {
    const authors = r.authors.join(", ") + (r.more_authors ? " et al." : "");
    const title = link(r) ? `<a href="${esc(link(r))}" target="_blank" rel="noopener">${esc(r.title)}</a>` : esc(r.title);
    const q = r.quartile || (ev.verified ? "—" : "?");
    return `<tr><td>${i + 1}</td><td>${title}<div class="sub">${esc(authors)}</div></td>` +
      `<td>${esc(r.journal)}<div class="sub">${esc(r.publisher || "")}${r.citedness != null ? ` · cited/yr ${r.citedness.toFixed(1)}` : ""}</div></td>` +
      `<td>${r.year || ""}</td><td class="num">${r.citations}</td><td class="q">${esc(q)}</td>` +
      `<td><button class="icon-btn add-lib" data-i="${i}" title="Add to this project's paper library">📥</button></td></tr>`;
  }).join("");
  const box = make("div", "papers",
    `<div class="papers-head"><span>🎓 <b>${ev.rows.length} papers</b> · ${esc(ev.query)}` +
    `${ev.quartile ? ` · ${esc(ev.quartile)}` : ""} · since ${ev.from_year} · OpenAlex</span></div>` +
    `<div class="papers-scroll"><table><thead><tr><th>#</th><th>Paper</th><th>Journal</th><th>Year</th>` +
    `<th>Cites</th><th title="Scimago quartile">Q</th><th title="Add to library">📥</th></tr></thead>` +
    `<tbody>${rows}</tbody></table></div>` +
    `<div class="papers-note">${ev.verified ? "Quartiles: Scimago (SJR)." :
      "⚠️ Quartile (Q1–Q4) not verified: add the Scimago file (see README). “?” = unknown."}</div>`);
  const copy = make("button", "btn small ghost", "📋 Copy list");
  copy.onclick = async () => {
    const text = ev.rows.map((r, i) => `${i + 1}. ${r.authors.join(", ")}${r.more_authors ? " et al." : ""} ` +
      `(${r.year}). ${r.title}. ${r.journal}. ${link(r)}`).join("\n");
    try { await navigator.clipboard.writeText(text); copy.textContent = "✓ Copied"; }
    catch (e) { copy.textContent = "Copy failed"; }
  };
  const addAll = make("button", "btn small ghost", "📥 Add all to library");
  addAll.title = "Save these papers in this project's library (full text when open access, else abstract)";
  addAll.onclick = async () => {
    addAll.disabled = true;
    for (const b of box.querySelectorAll(".add-lib")) {
      if (!(await addToLibrary(ev.rows[b.dataset.i], b))) break;  // stop on "no project" etc.
    }
    addAll.textContent = "✓ Added";
  };
  box.querySelectorAll(".add-lib").forEach((b) => (b.onclick = () => addToLibrary(ev.rows[b.dataset.i], b)));
  const bib = make("button", "btn small ghost", "🔖 Copy BibTeX");
  bib.title = "Official BibTeX for all these papers (from Crossref / DataCite)";
  bib.onclick = async () => {
    bib.textContent = "⏳ BibTeX…";
    try {
      const r = await post("/api/bibtex", { dois: ev.rows.map((x) => x.doi).filter(Boolean) });
      await navigator.clipboard.writeText(r.bibtex);
      bib.textContent = `✓ Copied ${r.bibtex.split("@").length - 1} entries`;
      if (r.errors.length) bib.title = r.errors.join("\n");
    } catch (e) { bib.textContent = "⚠ BibTeX failed"; bib.title = e.message; }
  };
  const head = box.querySelector(".papers-head");
  head.appendChild(addAll);
  head.appendChild(bib);
  head.appendChild(copy);
  append(box);
}

const LIB_ICON = { pdf: "📄", fulltext: "📄", abstract: "📝", exists: "✓" };
/** Add one paper to the open chat's project library. Returns false when it can't work at all. */
async function addToLibrary(row, btn) {
  if (!row.doi) { btn.textContent = "—"; btn.title = "No DOI, can't add"; return true; }
  if (["📄", "📝", "✓"].includes(btn.textContent)) return true;
  btn.textContent = "⏳";
  try {
    const r = await post("/api/library/add", { doi: row.doi });
    btn.textContent = LIB_ICON[r.status] || "✓";
    btn.title = r.message;
    return true;
  } catch (e) {
    btn.textContent = "⚠";
    btn.title = e.message;
    if (e.message.startsWith("Open a chat inside a project")) { alert(e.message); return false; }
    return true;
  }
}

/** Reference check report: one row per .bib entry, problems first. */
function showRefCheck(ev) {
  finishAssistant();
  const icon = { ok: "✅", warn: "⚠️", bad: "❌" };
  const order = { bad: 0, warn: 1, ok: 2 };
  const rows = [...ev.results].sort((a, b) => order[a.status] - order[b.status]).map((r) =>
    `<tr class="rc-${r.status}"><td>${icon[r.status]}</td><td class="mono">${esc(r.key)}</td>` +
    `<td>${esc(r.title.slice(0, 110))}<div class="sub">${esc(r.issues.join("; ") || "verified: DOI and title match")}` +
    `</div></td></tr>`).join("");
  const c = ev.counts;
  const extra = (ev.missing_keys.length ? `<div class="papers-note">❌ \\cite keys missing from ${esc(ev.bib)}: ` +
      `<span class="mono">${esc(ev.missing_keys.join(", "))}</span></div>` : "") +
    (ev.uncited.length ? `<div class="papers-note">ℹ️ In ${esc(ev.bib)} but never cited: ` +
      `<span class="mono">${esc(ev.uncited.join(", "))}</span></div>` : "");
  append(make("div", "papers",
    `<div class="papers-head"><span>📑 <b>Reference check</b> · ${esc(ev.bib)} · ✅ ${c.ok} · ⚠️ ${c.warn} · ❌ ${c.bad}` +
    `</span></div><div class="papers-scroll"><table><tbody>${rows}</tbody></table></div>${extra}` +
    `<div class="papers-note">✅ = DOI exists and its registered title matches. Checked against Crossref / DataCite.</div>`));
}

/** Library excerpts the answer cites as [1], [2]... */
function showLibrary(ev) {
  finishAssistant();
  const items = ev.results.map((r) => {
    const title = r.doi ? `<a href="https://doi.org/${esc(r.doi)}" target="_blank" rel="noopener">${esc(r.title)}</a>` : esc(r.title);
    return `<div class="lib-item"><span class="lib-n">[${r.n}]</span> <b>${esc(r.who)} (${r.year || "n.d."})</b>, ` +
      `${esc(r.where)} · ${title}<details><summary>excerpt</summary><div class="lib-text">${esc(r.text)}</div></details></div>`;
  }).join("");
  append(make("div", "papers library-card",
    `<div class="papers-head"><span>📚 <b>Library excerpts</b> · ${esc(ev.query)}</span></div>${items}`));
}

function showSources(urls) {
  const links = urls.map((u) => `<a href="${esc(u)}" target="_blank" rel="noopener">${esc(u)}</a>`).join("<br>");
  append(make("div", "sources", `<b>Sources</b> <span class="hint">(pages M42 read)</span><br>${links}`));
}

function showStats(ev) {
  const parts = [];
  if (ev.model) parts.push(shortModel(ev.model) + (ev.label && ev.label !== "answer" ? ` (${ev.label})` : ""));
  if (ev.first_token_s != null) parts.push(`first token ${ev.first_token_s}s`);
  if (ev.tokens) parts.push(`${ev.tokens.toLocaleString()} tokens`);
  if (ev.tok_per_s) parts.push(`${ev.tok_per_s} tok/s`);
  if (ev.prompt_tokens) parts.push(`read ${ev.prompt_tokens.toLocaleString()} tok` + (ev.prompt_per_s ? ` @ ${ev.prompt_per_s}/s` : ""));
  if (ev.ctx_used && ev.ctx_size) {  // like Claude Code's context meter: how much of the model's memory is used
    const pct = Math.round(100 * ev.ctx_used / ev.ctx_size);
    parts.push(`context ${(ev.ctx_used / 1000).toFixed(1)}k/${Math.round(ev.ctx_size / 1000)}k (${pct}%)`
               + (pct >= 80 ? " ⚠ older turns get summarised" : ""));
  }
  $("stats").textContent = parts.join(" · ");
}
function showRequestDone(ev) {
  const parts = [`⏱ ${clock(ev.started)} → ${clock(ev.finished)}`, duration(ev.secs)];
  if (ev.tokens) parts.push(`${ev.tokens.toLocaleString()} tokens written` + (ev.calls > 1 ? ` in ${ev.calls} model calls` : ""));
  if (ev.tok_per_s) parts.push(`avg ${ev.tok_per_s} tok/s`);
  append(make("div", "req-time", esc(parts.join(" · "))));
}

function handle(ev) {
  switch (ev.type) {
    case "assistant_start": startAssistant(); break;
    case "delta": if (current) { current.raw += ev.text; renderAssistant(); } break;
    case "assistant_text": if (current) current.raw = ev.text; break;
    case "reading": {  // llama-server reading a long prompt (e.g. an attached document)
      const t = current && !current.raw && current.body.querySelector(".thinking");
      if (t) t.textContent = `📖 Reading ${ev.done.toLocaleString()} / ${ev.total.toLocaleString()} tokens` +
        (ev.eta != null ? ` (~${ev.eta} s left)` : "") + "…";
      break;
    }
    case "stats": showStats(ev); finishAssistant(); break;
    case "request_done": finishAssistant(); showRequestDone(ev); previewNewPage(); break;
    case "undo_point": undoBar(ev); break;
    case "page_preview": if (!replaying) { pagesShown = countPages(); showPreview(ev); } break;  // a site in the folder
    case "tool_start": toolCard(ev); break;
    case "approval": approvalCard(ev); break;
    case "tool_result": toolResult(ev); break;
    case "sources": showSources(ev.urls); break;
    case "image": finishAssistant(); showImage(ev); break;
    case "elements": finishAssistant(); showElements(ev); break;
    case "papers": showPapers(ev); break;
    case "library": showLibrary(ev); break;
    case "model_switch": showModelSwitch(ev); break;
    case "refcheck": showRefCheck(ev); break;
    case "check": finishAssistant(); append(make("div", "check-note", `✅ <b>Requirement check:</b> ${esc(ev.message)}`)); break;
    case "stopped": finishAssistant(); showNote("Stopped."); break;
    case "error": showError(ev.message); break;
    case "done": finishAssistant(); if (!ev.no_verify) addVerifyButton(); break;
    case "note": finishAssistant(); showNote(ev.message); break;
    case "lesson_ask": finishAssistant(); askLesson(ev); break;
    case "edit_ask": finishAssistant(); askEdit(ev); break;
    case "file_link": {  // a document check result (report / humanized .docx), opened in its own app
      finishAssistant();
      const b = make("button", "btn small file-link", esc(ev.label || "📄 Open"));
      b.title = ev.path;
      b.onclick = () => post("/api/doc/open", { path: ev.path }).catch((e) => showError(e.message));
      append(b);
      break;
    }
    case "progress": finishAssistant(); showProgress(ev); break;
    case "plan": finishAssistant(); showPlan(ev.plan); break;
    case "build_step": finishAssistant(); append(make("div", "build-step" + (ev.skipped ? " skipped" : ""), ev.skipped
      ? `⏭ <b>Step ${ev.index}/${ev.total}: ${esc(ev.title)}</b><span>already in the code: ${esc((ev.features || []).join(" · "))}</span>`
      : `🏗 <b>Step ${ev.index}/${ev.total}: ${esc(ev.title)}</b><span>${esc((ev.features || []).join(" · "))}</span>`)); break;
    case "build_done": finishAssistant(); append(make("div", "build-step done", ev.failed?.length
      ? `⚠️ <b>Build finished</b><span>${ev.steps} steps; still failing the browser check: ${esc(ev.failed.join(", "))}</span>`
      : `✅ <b>Build finished</b><span>${ev.steps} steps, each checked in a browser. Open index.html to play.</span>`));
      showNote("🐞 Found something wrong while testing? Just describe it here (e.g. \"goomba mela jump panna saganum\"): M42 finds the file it belongs to and fixes only that part.");
      break;
  }
}

// ---------------------------------------------------------------- sending

function setBusy(v) {
  busy = v;
  $("sendBtn").hidden = v;
  $("stopBtn").hidden = !v;
  $("newChat").disabled = v;
  $("newProject").disabled = v;
  $("modelSelect").disabled = v;
}

async function send(text, opts = {}) {
  text = text.trim();
  if (busy || !text) return;
  document.querySelectorAll(".verify-btn").forEach((b) => b.remove());
  lastAnswer = null;
  addUser(opts.shown || text, Date.now() / 1000, opts.images, opts.shown && opts.shown !== text ? (opts.body?.message ?? text) : text);
  setBusy(true);
  const ctl = new AbortController();
  streamCtl = ctl;
  let left = false;  // the window went to another chat: the request goes on there, followed by watchRun
  try {
    const res = await fetch(opts.endpoint || "/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-M42-Token": TOKEN },
      body: JSON.stringify(opts.body || { message: text, verify: !!opts.verify }),
      signal: ctl.signal,
    });
    if (!res.ok) {
      const d = await res.json().catch(() => ({}));
      throw new Error(d.error || res.statusText);
    }
    const reader = res.body.getReader();
    const dec = new TextDecoder();
    let buf = "";
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += dec.decode(value, { stream: true });
      let i;
      while ((i = buf.indexOf("\n")) >= 0) {
        const line = buf.slice(0, i);
        buf = buf.slice(i + 1);
        if (line.trim()) handle(JSON.parse(line));
      }
    }
  } catch (e) {
    if (ctl.signal.aborted) left = true;
    else showError(e.message);
  } finally {
    if (streamCtl === ctl) streamCtl = null;
    progressLines.forEach((p) => clearInterval(p.timer));  // stream ended: no more ticking
    progressLines.clear();
    if (left) {
      watchRun(null);  // still busy: followed by polling until it ends (and shown live when its chat is open)
    } else {
      finishAssistant();
      setBusy(false);
      refreshTree();
      refreshSidebar();
    }
  }
}

// ---------------------------------------------------------------- 📡 a request that runs while the window is elsewhere
// (the user, 2026-11-15: "another chat and back, it was cut; the app closed by mistake, it started over"): the request
// goes on in M42; the window follows it by its chat's events (/api/session/live), shown live when that chat is open.
let streamCtl = null;
const live = { id: null, from: 0, timer: null, attached: false };
function watchRun(attach) {
  // attach: {id, from} when the running chat is on screen (its events from `from` on are drawn); null: elsewhere
  if (attach) { live.id = attach.id; live.from = attach.from; live.attached = true; }
  else live.attached = false;
  if (live.timer) return;
  live.timer = setInterval(async () => {
    let d;
    try { d = await api(`/api/session/live?id=${encodeURIComponent(live.id || "")}&from=${live.from}`); } catch (e) { return; }
    if (!live.id) live.id = d.running_id;
    if (live.attached && live.id === currentSessionId) {
      for (const ev of d.events || []) {
        if (ev.type === "user") addUser(ev.text, ev.time); else handle(ev);
      }
      live.from += (d.events || []).length;
      if ((d.events || []).length) chat.scrollTop = chat.scrollHeight;
    } else {
      live.from = d.total || live.from;
    }
    if (!d.running_id) {  // (no request runs any more: the last events above were its end)
      clearInterval(live.timer); live.timer = null;
      progressLines.forEach((p) => clearInterval(p.timer));
      progressLines.clear();
      if (live.attached && live.id === currentSessionId) finishAssistant();
      live.id = null; live.attached = false;
      setBusy(false);
      refreshTree();
      refreshSidebar();
    }
  }, 800);
}

// ---------------------------------------------------------------- sessions

let currentSessionId = null;
let currentProjectId = null;   // project of the open chat (null = general chat)
let viewedProjectId = null;    // project page on screen (null = chat view)

function showView(which) {
  const projectPage = which === "project";
  $("projectView").hidden = !projectPage;
  for (const id of ["contextBar", "chat", "composer"]) $(id).hidden = projectPage;
  if (!projectPage) viewedProjectId = null;
}

/** The line above the chat: which project + folders this chat works in. */
function renderContext(s) {
  const bar = $("contextBar");
  if (!s.project) {
    bar.innerHTML = "📂 <b>No folder open</b> · open a folder: M42 UI builds the pages in it and changes them there.";
    return;
  }
  const chips = s.folders.length
    ? s.folders.map((f) => `<span class="folder-chip" title="${esc(f.path)}">📂 ${esc(f.alias)}</span>`).join(" ")
    : '<span class="hint">no folders yet: add them on the project page</span>';
  bar.innerHTML = `<span class="proj-link" title="Open the project page">📁 ${esc(s.project.name)}</span> ${chips}`;
  bar.querySelector(".proj-link").onclick = () => openProjectView(s.project.id);
}

/** Show a chat: clear the chat area and replay its saved UI events. */
function renderSession(s) {
  showView("chat");
  currentSessionId = s.id;
  currentProjectId = s.project ? s.project.id : null;
  current = null;
  lastAnswer = null;
  cards.clear();
  chat.innerHTML = s.ui && s.ui.length ? "" : EMPTY_HTML;
  chat.querySelectorAll(".chip").forEach((c) => (c.onclick = () => send(c.textContent)));
  replaying = true;
  try {
    for (const ev of s.ui || []) {
      if (ev.type === "user") addUser(ev.text, ev.time);
      else handle(ev);
    }
    finishAssistant();
  } finally {
    replaying = false;
  }
  pagesShown = countPages();  // only pages made from now on open their preview by themselves
  // A chat saved mid-run (stopped / closed) can leave tool cards that never got a result.
  if (!s.live) chat.querySelectorAll(".tool.running").forEach((c) => {
    c.classList.remove("running");
    c.querySelector(".tool-state").textContent = "Interrupted";
  });
  if (s.live) {  // 📡 its request is still running (the window came back to it, or was opened again): followed live
    setBusy(true);
    watchRun({ id: s.id, from: (s.ui || []).length });
  } else if (s.running_id) {  // another chat runs a request: this one is only shown
    setBusy(true);
    watchRun(null);
    append(make("div", "build-step interrupted", "⏳ <b>M42 is working in another chat</b><span>It goes on there; open " +
      "that chat to follow it live. You can send here when it finishes.</span>"));
  }
  if (s.interrupted) {  // a build cut off by a power cut / closed app: offer to finish it
    append(make("div", "build-step interrupted", `⚠ <b>The build "${esc(s.interrupted.title || "")}" stopped at step ` +
      `${s.interrupted.step}/${s.interrupted.total}</b><span>Say "continue" (or "thodaru") to finish it: ` +
      `M42 checks the files already written and builds only what's missing.</span>`));
  } else if (s.cut_off) {  // a chat request cut off midway (power cut / app closed)
    const box = make("div", "build-step interrupted", `⚠ <b>This request was cut off before it finished</b>` +
      `<span>"${esc((s.cut_off.text || "").slice(0, 120))}" · ` + (s.resumable
        ? "M42 kept the steps it had finished: Continue goes on from where it stopped, not from the start.</span>"
        : `Say "continue" (or "thodaru") and M42 picks it up from the files already changed.</span>`));
    const go = make("button", "btn small primary", "▶ Continue from where it stopped");
    go.type = "button";
    go.onclick = () => { box.remove(); send("continue", { shown: `▶ Continue: ${(s.cut_off.text || "").slice(0, 80)}` }); };
    box.appendChild(go);
    append(box);
  }
  if (!s.ui || !s.ui.length) {  // welcome text for this kind of chat
    $("emptyTitle").textContent = s.project ? `New chat in ${s.project.name}` : "What should we build?";
    $("emptyHint").textContent = s.project
      ? `Folders: ${s.folders.map((f) => f.alias).join(", ") || "none yet (add them on the project page)"}`
      : "Open a folder (📂 Open folder), then describe the web page or site you want, or attach a design picture.";
  }
  renderContext(s);
  chat.scrollTop = chat.scrollHeight;
  $("stats").textContent = "";
  refreshTree();
  refreshSidebar();
  autosize();
  $("input").focus();
}

function timeAgo(t) {
  const s = Date.now() / 1000 - t;
  if (s < 60) return "now";
  if (s < 3600) return `${Math.floor(s / 60)}m`;
  if (s < 86400) return `${Math.floor(s / 3600)}h`;
  return `${Math.floor(s / 86400)}d`;
}
function refreshSidebar() { drawSidebarLists(); }
// (the old names: other code calls them after a change)
function refreshProjects() { return drawSidebarLists(); }
function refreshSessions() { return drawSidebarLists(); }

/** Projects with their chats under them, as in Claude's sidebar (the user, 2026-11-12): a ▸ / ▾ arrow beside each
 *  project opens its recent chats; the project in use opens by itself; chats outside any project under "Chats". */
let openFolders = new Set();
try { openFolders = new Set(JSON.parse(localStorage.getItem("m42.openProjects") || "[]")); } catch { /* */ }
const keepOpenFolders = () => { try { localStorage.setItem("m42.openProjects", JSON.stringify([...openFolders])); } catch { /* */ } };
let sidebarDrawing = null, sidebarAgain = false;
function drawSidebarLists() {
  if (sidebarDrawing) { sidebarAgain = true; return sidebarDrawing; }  // (asked again while drawing: once more after)
  sidebarDrawing = (async () => {
    try {
      let projs, sess;
      try { [projs, sess] = await Promise.all([api("/api/projects"), api("/api/sessions")]); } catch (e) { return; }
      const box = $("projectList"), loose = $("sessions");
      box.innerHTML = "";
      loose.innerHTML = "";
      const byProject = new Map();
      for (const s of sess.sessions) {
        if (!byProject.has(s.project_id || "")) byProject.set(s.project_id || "", []);
        byProject.get(s.project_id || "").push(s);
      }
      const chatRow = (s) => {
        const item = make("div", "chat-item" + (s.id === sess.current && !viewedProjectId ? " active" : ""),
          `<span class="t">${esc(s.title)}</span>`);
        item.title = `${s.title}\n${timeAgo(s.updated)} ago · double-click to rename`;
        const del = make("button", "icon-btn del", "✕");
        del.title = "Delete this chat";
        del.onclick = (e) => { e.stopPropagation(); deleteSession(s); };
        item.appendChild(del);
        item.onclick = () => openSession(s.id);
        item.ondblclick = (e) => { e.stopPropagation(); renameSession(s); };
        return item;
      };
      if (!projs.projects.length) box.appendChild(make("div", "note", "No folders yet: Open folder"));
      for (const p of projs.projects) {
        const active = viewedProjectId ? p.id === viewedProjectId : p.id === currentProjectId;
        const chats = byProject.get(p.id) || [];
        const open = openFolders.has(p.id) || (p.id === currentProjectId && !openFolders.has("-" + p.id));
        const group = make("div", "proj-group" + (open ? " open" : ""));
        const row = make("div", "proj-item" + (active ? " active" : ""),
          `<button type="button" class="proj-arrow" aria-label="${open ? "Hide" : "Show"} its chats" aria-expanded="${open}">` +
          '<svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 6l6 6-6 6"/></svg></button>' +
          `<span class="t">${esc(p.name)}</span>` + (chats.length ? `<span class="n">${chats.length}</span>` : ""));
        row.title = p.folders.join("\n") || "No folders yet";
        row.onclick = () => openProjectView(p.id);
        const more = make("button", "proj-more",  // ⋯ on hover: open, rename, delete (as in Claude)
          '<svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true" fill="currentColor"><circle cx="5" cy="12" r="1.6"/><circle cx="12" cy="12" r="1.6"/><circle cx="19" cy="12" r="1.6"/></svg>');
        more.type = "button";
        more.title = "More";
        more.setAttribute("aria-label", `More for ${p.name}`);
        more.onclick = (e) => { e.stopPropagation(); projectMenu(p, more); };
        row.appendChild(more);
        row.querySelector(".proj-arrow").onclick = (e) => {
          e.stopPropagation();
          const now = !group.classList.contains("open");
          group.classList.toggle("open", now);
          e.currentTarget.setAttribute("aria-expanded", String(now));
          openFolders.delete(now ? "-" + p.id : p.id);  // ("-id": the user closed the project in use)
          openFolders.add(now ? p.id : "-" + p.id);
          keepOpenFolders();
        };
        const list = make("div", "proj-chats");
        chats.slice(0, 20).forEach((s) => list.appendChild(chatRow(s)));
        if (!chats.length) list.appendChild(make("div", "note", "No chats yet"));
        group.append(row, list);
        box.appendChild(group);
      }
      const others = byProject.get("") || [];
      $("chatsTitle").hidden = !others.length;
      others.slice(0, 30).forEach((s) => loose.appendChild(chatRow(s)));
    } finally {
      sidebarDrawing = null;
      if (sidebarAgain) { sidebarAgain = false; drawSidebarLists(); }
    }
  })();
  return sidebarDrawing;
}

async function openSession(id) {
  if (id === currentSessionId && streamCtl) { showView("chat"); refreshSidebar(); return; }  // (its stream is still drawing it)
  try {
    // Re-opening the current chat (e.g. from the project page) just switches back to it.
    const s = id === currentSessionId && !busy ? await api("/api/session") : await post("/api/sessions/open", { id });
    if (streamCtl && id !== currentSessionId) streamCtl.abort();  // (the request goes on: watchRun follows it)
    renderSession(s);
  } catch (e) { showError(e.message); }
}

// ---------------------------------------------------------------- project page

async function openProjectView(id) {
  try {
    const p = await api(`/api/project?id=${encodeURIComponent(id)}`);
    renderProjectView(p);
    showView("project");
    viewedProjectId = id;
    if (window.files) syncFilesPane(id);  // 📁 this project's files, by themselves
    refreshSidebar();
  } catch (e) { alert(e.message); }
}

function renderProjectView(p) {
  $("pvName").value = p.name;
  if (document.activeElement !== $("pvInstructions")) $("pvInstructions").value = p.instructions || "";
  const folders = $("pvFolders");
  folders.innerHTML = "";
  if (!p.folders.length) folders.appendChild(make("div", "note", "No folders yet. Add one below."));
  for (const path of p.folders) {
    const missing = p.missing.includes(path) ? ' <span class="missing">(not found)</span>' : "";
    const row = make("div", "pv-folder", `<span>📂</span><span class="p">${esc(path)}${missing}</span>`);
    const rm = make("button", "icon-btn", "✕");
    rm.title = "Remove from this project (the folder and its files are not deleted)";
    rm.onclick = () => projectAction("remove_folder", { path },
      `Remove this folder from the project?\n\n${path}\n\nThe folder and its files are NOT deleted.`);
    row.appendChild(rm);
    folders.appendChild(row);
  }
  const chats = $("pvChats");
  chats.innerHTML = "";
  if (!p.chats.length) chats.appendChild(make("div", "note", "No chats yet."));
  for (const s of p.chats) {
    const row = make("div", "pv-chat", `<span>${esc(s.title)}</span><span class="hint">${timeAgo(s.updated)}</span>`);
    row.onclick = () => openSession(s.id);
    chats.appendChild(row);
  }
}

/** Run a project change on the server, then refresh everything that shows it. */
async function projectAction(action, extra = {}, confirmText = null) {
  if (confirmText && !confirm(confirmText)) return null;
  const id = viewedProjectId;
  try {
    const p = await post(`/api/projects/${action}`, { id, ...extra });
    if (action !== "delete") renderProjectView(p);
    refreshSidebar();
    if (id === currentProjectId) {  // the open chat belongs to this project: update its folders/context
      const s = await api("/api/session");
      renderContext(s);
      refreshTree();
    }
    return p;
  } catch (e) {
    alert(e.message);
    return null;
  }
}

const LIB_STATUS = { pdf: (n) => `PDF · ${n} pages`, fulltext: (n) => `full text · ${n} sections`,
  abstract: () => "abstract only" };

async function loadLibrary(projectId) {
  const box = $("pvLibrary");
  let data;
  try { data = await api(`/api/library?project_id=${encodeURIComponent(projectId)}`); }
  catch (e) { box.textContent = e.message; return; }
  $("pvLibCount").textContent = data.papers.length ? `· ${data.papers.length} papers` : "";
  $("pvLibHint").textContent = data.papers_dir
    ? `Add papers with 📥 in a 🎓 papers table, or save PDFs (e.g. downloaded with your university login) into ` +
      `${data.papers_dir} and click Scan. Then ask questions in a project chat: answers cite [1], [2].`
    : "Add a folder to this project first: PDFs are stored in its papers\\ subfolder.";
  $("pvScan").disabled = !data.papers_dir;
  box.innerHTML = "";
  if (!data.papers.length) box.appendChild(make("div", "note", "No papers yet."));
  for (const p of data.papers) {
    const authors = p.authors.length ? `${p.authors[0].split(" ").pop()}${p.authors.length > 1 ? " et al." : ""} · ` : "";
    const row = make("div", "pv-folder lib-row",
      `<span>${p.status === "abstract" ? "📝" : "📄"}</span><span class="p">${esc(p.title)}` +
      `<span class="sub">${esc(authors)}${p.year || ""}${p.journal ? " · " + esc(p.journal) : ""} · ` +
      `${(LIB_STATUS[p.status] || (() => p.status))(p.pages)}</span></span>`);
    const rm = make("button", "icon-btn", "✕");
    rm.title = "Remove from the library (a saved PDF file stays in the folder)";
    rm.onclick = async () => {
      if (!confirm(`Remove from the library?\n\n${p.title}`)) return;
      try { await post("/api/library/remove", { project_id: projectId, paper_id: p.id }); loadLibrary(projectId); }
      catch (e) { alert(e.message); }
    };
    row.appendChild(rm);
    box.appendChild(row);
  }
}

$("pvScan").onclick = async () => {
  const id = viewedProjectId;
  $("pvScan").disabled = true;
  $("pvScan").textContent = "⏳ Scanning…";
  try {
    const r = await post("/api/library/scan", { project_id: id });
    alert(`Added ${r.added.length} PDF(s).` + (r.failed.length ? `\n\nCould not read:\n${r.failed.join("\n")}` : ""));
  } catch (e) { alert(e.message); }
  $("pvScan").textContent = "🔄 Scan papers folder";
  $("pvScan").disabled = false;
  loadLibrary(id);
};

// ---------------------------------------------------------------- literature matrix & gaps

let matrixTimer = null;
const NOVELTY = { similar_exists: ["⚠️", "a very similar paper already exists"], close: ["🟡", "related work exists"],
  no_close_match: ["🟢", "no close match found on OpenAlex (not a guarantee)"], unknown: ["⚪", "not checked"] };

async function loadMatrix(projectId) {
  clearTimeout(matrixTimer);
  let d;
  try { d = await api(`/api/matrix?project_id=${encodeURIComponent(projectId)}`); } catch (e) { return; }
  if (viewedProjectId !== projectId) return;
  const job = d.job;
  const running = job && job.state === "running";
  $("mxBuild").disabled = running || !d.papers;
  $("mxGaps").disabled = running || d.rows.length < 3;
  $("mxStop").hidden = !running;
  const missing = d.papers - d.rows.length;
  $("mxBuild").textContent = d.rows.length && !missing ? "🧮 Rebuild matrix" : `🧮 Build matrix${missing ? ` (${missing} papers)` : ""}`;
  let status = !d.papers ? "Add papers to the library first." :
    `${d.rows.length} of ${d.papers} papers in the matrix.` + (d.xlsx ? ` Excel: ${d.xlsx}` : "");
  if (running) {
    const mins = Math.round((Date.now() / 1000 - job.started) / 6) / 10;
    status = job.kind === "matrix"
      ? `⏳ Building… ${job.done}/${job.total} papers (${mins} min). Now: ${job.current || "starting"}. ` +
        "About 30–60 s per paper on this PC. Chat waits until it finishes."
      : `⏳ ${job.current || "Finding gaps…"} (${mins} min)`;
  } else if (job && job.state === "error") status = `⚠ ${job.error}`;
  else if (job && job.errors && job.errors.length) status += ` ⚠ ${job.errors.length} paper(s) failed: ${job.errors.join("; ")}`;
  $("mxStatus").textContent = status;

  $("mxTable").innerHTML = d.rows.length ? `<table class="mx"><thead><tr><th>#</th><th>Paper</th><th>Method</th>` +
    `<th>Dataset</th><th>Results</th><th>Limitations</th><th>Future work</th></tr></thead><tbody>` +
    d.rows.map((r) => `<tr><td class="mono">${r.pid}</td><td>${esc(r.title.slice(0, 80))}<div class="sub">${r.year || ""} · ` +
      `${r.status === "abstract" ? "abstract only" : "full text"}</div></td>` +
      ["method", "dataset", "results", "limitations", "future_work"].map((k) =>
        `<td class="${r[k] === "not stated" ? "ns" : ""}">${esc(r[k])}</td>`).join("") + "</tr>").join("") +
    "</tbody></table>" : "";

  const g = d.gaps;
  $("mxGapsOut").innerHTML = !g ? "" :
    `<h4>Research gaps <span class="hint">(from ${g.papers} papers; each cites the papers whose limitations / future work support it)</span></h4><ol>` +
    g.gaps.map((x) => `<li><b>${esc(x.gap)}</b> ${x.supported ? x.evidence.map((e) => `<span class="chip-p">${e}</span>`).join("") :
      '<span class="chip-p bad">unsupported</span>'}<div class="sub">${esc(x.why)}</div></li>`).join("") +
    `</ol><h4>Candidate titles</h4><ul class="titles">` +
    g.titles.map((t) => {
      const [icon, label] = NOVELTY[t.novelty.status] || NOVELTY.unknown;
      const close = t.novelty.closest[0];
      return `<li><b>${esc(t.title)}</b> ${t.gap ? `<span class="chip-p">G${t.gap}</span>` : ""}<div class="sub">${esc(t.contribution)}</div>` +
        `<div class="sub">${icon} ${label}${close ? `: closest “${esc(close.title || "")}” (${close.year}, similarity ${close.similarity})` : ""}</div></li>`;
    }).join("") + `</ul><div class="hint">Starting points for your own judgement: check novelty yourself before committing. ` +
    `Saved as research_gaps.md and in the Excel file.</div>`;

  if (running) matrixTimer = setTimeout(() => loadMatrix(projectId), 3000);
}

async function matrixAction(path, extra = {}) {
  try { await post(path, { project_id: viewedProjectId, ...extra }); }
  catch (e) { alert(e.message); }
  loadMatrix(viewedProjectId);
}
$("mxBuild").onclick = () => {
  const rebuild = $("mxBuild").textContent.includes("Rebuild");
  if (rebuild && !confirm("Rebuild the matrix for all papers? This takes about a minute per paper.")) return;
  matrixAction("/api/matrix/start", { force: rebuild });
};
$("mxGaps").onclick = () => matrixAction("/api/matrix/gaps");
$("mxStop").onclick = () => matrixAction("/api/matrix/stop");

// ---------------------------------------------------------------- document check (plagiarism · humanize)

let docTimer = null;
const DOC_KIND = { copied: "copied", "partly copied": "partly", paraphrased: "para", quoted: "quoted" };

async function loadDocs(projectId, select) {
  clearTimeout(docTimer);
  let d;
  try { d = await api(`/api/doc?project_id=${encodeURIComponent(projectId)}`); } catch (e) { return; }
  if (viewedProjectId !== projectId) return;
  const pick = $("docPick");
  const keep = select || pick.value;
  pick.innerHTML = d.docs.length ? d.docs.map((n) => `<option>${esc(n)}</option>`).join("") : "<option value=''>no documents yet</option>";
  if (keep && d.docs.includes(keep)) pick.value = keep;
  const job = d.job;
  const running = job && job.state === "running";
  for (const id of ["docPlag", "docHuman", "docFile"]) $(id).disabled = running || !!d.error;
  $("docStop").hidden = !running;
  let status = d.error || (!d.model ? "⏳ The bge-m3 model is not downloaded yet: the buttons work once it is in models\\bge-m3." :
    `Documents and reports are saved in ${d.folder}.`);
  if (running) {
    const mins = Math.round((Date.now() / 1000 - job.started) / 6) / 10;
    status = `⏳ ${job.kind === "plagiarism" ? "Checking" : "Humanizing"} ${esc(job.doc)}… ` +
      (job.total ? `${job.done}/${job.total} ${job.kind === "plagiarism" ? "sentences" : "paragraphs"} · ` : "") +
      `${mins} min. ${job.current || ""}`;
  } else if (job && job.state === "error") status = `⚠ ${job.error}`;
  $("docStatus").textContent = status;
  $("docOut").innerHTML = "";
  if (job && job.result && !running) showDocResult(job, projectId);
  if (running) docTimer = setTimeout(() => loadDocs(projectId), 2000);
}

function openDocFile(projectId, path) {
  post("/api/doc/open", { project_id: projectId, path }).catch((e) => alert(e.message));
}

function showDocResult(job, projectId) {
  const r = job.result;
  const box = $("docOut");
  if (job.kind === "plagiarism") {
    const p = r.percent;
    const level = r.score >= 25 ? "bad" : r.score >= 10 ? "mid" : "good";
    box.appendChild(make("div", `doc-score ${level}`,
      `<b>${r.score}%</b> similarity <span class="sub">· copied ${p.copied}% · partly copied ${p["partly copied"]}% · ` +
      `paraphrased ${p.paraphrased}% · quoted ${p.quoted}% · ${r.words} words · checked ${r.checked.web_pages} web pages ` +
      `and ${r.checked.library_papers} library papers</span>`));
    for (const n of r.notes || []) box.appendChild(make("div", "hint", `⚠ ${esc(n)}. Wikipedia and OpenAlex were still searched.`));
    if (r.sources.length) {
      box.appendChild(make("div", "doc-sources", "<b>Sources</b><ol>" + r.sources.map((s) =>
        `<li value="${s.id + 1}">${esc(s.title)} · ${s.share}%` +
        (s.url ? ` <a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.url.slice(0, 70))}</a>` : "") + "</li>").join("") + "</ol>"));
    }
    const flagged = r.sentences.filter((s) => DOC_KIND[s.kind] && s.kind !== "quoted");
    if (flagged.length) {
      box.appendChild(make("div", "doc-list", flagged.slice(0, 40).map((s) =>
        `<div class="doc-sent ${DOC_KIND[s.kind]}"><span class="chip-p">${s.kind}${s.source !== null ? ` [${s.source + 1}]` : ""}</span> ${esc(s.text)}` +
        (s.match ? `<div class="sub">source: “${esc(s.match.slice(0, 220))}”</div>` : "") + "</div>").join("") +
        (flagged.length > 40 ? `<div class="sub">…and ${flagged.length - 40} more in the full report</div>` : "")));
    } else box.appendChild(make("div", "note", "No copied or paraphrased sentences found in the sources checked."));
    const open = make("button", "btn small", "📄 Open full report");
    open.onclick = () => openDocFile(projectId, r.report);
    box.appendChild(open);
    box.appendChild(make("div", "hint", "Only the open web and this project's paper library were searched, not paywalled papers or " +
      "other people's submissions: a low score is not a guarantee."));
  } else {
    box.appendChild(make("div", "doc-score good", `<b>${r.rewritten}</b> paragraphs rewritten · <b>${r.kept}</b> kept as they were ` +
      `<span class="sub">(the rewrite changed the meaning or lost a citation / number)</span>`));
    const changed = r.paragraphs.filter((p) => p.status !== "skipped").slice(0, 6);
    box.appendChild(make("div", "doc-list", changed.map((p) =>
      `<div class="doc-pair"><div class="sub">${p.status === "rewritten" ? `before · meaning kept ${p.similarity}` : `kept: ${esc(p.why || "")}`}</div>` +
      `<div class="doc-before">${esc(p.orig)}</div>` + (p.status === "rewritten" ? `<div class="sub">after</div><div class="doc-after">${esc(p.new)}</div>` : "") +
      "</div>").join("")));
    const open = make("button", "btn small", "📄 Open humanized .docx");
    open.onclick = () => openDocFile(projectId, r.docx);
    box.appendChild(open);
    box.appendChild(make("div", "hint", "Read it through before using it: you are the author, and the rewrite is a suggestion."));
  }
}

$("docFile").onchange = async () => {
  const f = $("docFile").files[0];
  if (!f) return;
  const id = viewedProjectId;
  $("docStatus").textContent = `⏳ Uploading ${f.name}…`;
  try {
    const buf = new Uint8Array(await f.arrayBuffer());
    let bin = "";
    for (let i = 0; i < buf.length; i += 32768) bin += String.fromCharCode.apply(null, buf.subarray(i, i + 32768));
    const r = await post("/api/doc/upload", { project_id: id, name: f.name, data: btoa(bin) });
    $("docFile").value = "";
    loadDocs(id, r.doc);
  } catch (e) { $("docStatus").textContent = `⚠ ${e.message}`; }
};

async function startDoc(kind) {
  const id = viewedProjectId;
  try {
    let doc = $("docPick").value;
    const text = $("docText").value.trim();
    if (text) {  // pasted text wins: saved as a .txt document first
      doc = (await post("/api/doc/upload", { project_id: id, text })).doc;
      $("docText").value = "";
    }
    if (!doc) { alert("Upload a document or paste text first."); return; }
    await post("/api/doc/start", { project_id: id, kind, doc });
    loadDocs(id, doc);
  } catch (e) { alert(e.message); }
}
$("docPlag").onclick = () => startDoc("plagiarism");
$("docHuman").onclick = () => startDoc("humanize");
$("docStop").onclick = () => post("/api/doc/stop", { project_id: viewedProjectId }).then(() => loadDocs(viewedProjectId));

$("pvExportBib").onclick = async () => {
  const btn = $("pvExportBib");
  btn.disabled = true;
  btn.textContent = "⏳ Getting BibTeX…";
  try {
    const r = await post("/api/library/export_bib", { project_id: viewedProjectId });
    alert(`${r.path}\n\nAdded ${r.added.length} entries` +
      (r.skipped.length ? `, ${r.skipped.length} were already there` : "") +
      (r.no_doi ? `.\n${r.no_doi} paper(s) have no DOI and were skipped` : ".") +
      (r.errors.length ? `\n\nErrors:\n${r.errors.join("\n")}` : ""));
  } catch (e) { alert(e.message); }
  btn.textContent = "⬇ Export references.bib";
  btn.disabled = false;
};

let instructionsTimer = null;
function saveInstructionsSoon() {
  $("pvSaved").textContent = "editing…";
  clearTimeout(instructionsTimer);
  instructionsTimer = setTimeout(async () => {
    const p = await projectAction("update", { instructions: $("pvInstructions").value });
    if (p) $("pvSaved").textContent = "saved ✓";
  }, 700);
}

async function deleteSession(s) {
  if (busy || !confirm(`Delete the chat "${s.title}"? This cannot be undone.`)) return;
  try {
    await post("/api/sessions/delete", { id: s.id });
    if (s.id === currentSessionId) renderSession(await api("/api/session"));
    else refreshSessions();
  } catch (e) { showError(e.message); }
}

/** The ⋯ menu of a project in the sidebar: open, rename, delete (the folder on disk is never touched). */
function projectMenu(p, anchor) {
  document.querySelector(".sb-menu")?.remove();
  const menu = make("div", "sb-menu");
  menu.setAttribute("role", "menu");
  const item = (label, icon, fn, danger) => {
    const b = make("button", "sb-menu-item" + (danger ? " danger" : ""),
      `<svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">${icon}</svg><span>${label}</span>`);
    b.type = "button";
    b.setAttribute("role", "menuitem");
    b.onclick = (e) => { e.stopPropagation(); menu.remove(); fn(); };
    menu.appendChild(b);
  };
  item("New chat", '<path d="M12 5v14M5 12h14"/>', () => newChatIn(p));  // a new chat in this project (its folder)
  item("Open", '<path d="M3.5 7.5A1.5 1.5 0 0 1 5 6h4l2 2h8a1.5 1.5 0 0 1 1.5 1.5v8A1.5 1.5 0 0 1 19 19H5a1.5 1.5 0 0 1-1.5-1.5z"/>', () => openProjectView(p.id));
  item("Rename", '<path d="M4 20h4L19 9a2.1 2.1 0 0 0-3-3L5 17z"/><path d="M14 7l3 3"/>', () => renameProject(p));
  item("Delete", '<path d="M4 7h16M10 11v6M14 11v6M6 7l1 12a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2l1-12M9 7V4h6v3"/>', () => deleteProject(p), true);
  document.body.appendChild(menu);
  const r = anchor.getBoundingClientRect();
  menu.style.top = Math.min(window.innerHeight - menu.offsetHeight - 8, r.bottom + 4) + "px";
  menu.style.left = Math.max(8, r.right - menu.offsetWidth) + "px";
  setTimeout(() => document.addEventListener("click", () => menu.remove(), { once: true }));
  document.addEventListener("keydown", function esc(e) { if (e.key === "Escape") { menu.remove(); document.removeEventListener("keydown", esc); } });
  menu.querySelector("button")?.focus();
}
async function newChatIn(p) {
  if (busy) { showError("M42 is working on a request: wait for it to finish."); return; }
  try {
    renderSession(await post("/api/sessions/new", { project_id: p.id }));
    openFolders.add(p.id); openFolders.delete("-" + p.id); keepOpenFolders();  // (its chats shown under it)
    refreshSidebar();
    $("input").focus();
  } catch (e) { showError(e.message); }
}
async function renameProject(p) {
  const name = prompt("Rename project", p.name);
  if (!name || name.trim() === p.name) return;
  try { await post("/api/projects/update", { id: p.id, name: name.trim() }); refreshSidebar(); }
  catch (e) { showError(e.message); }
}
async function deleteProject(p) {
  if (busy || !confirm(`Remove the project "${p.name}" from M42 UI?\nIts folder and files on disk are not touched; its chats stay as general chats.`)) return;
  try {
    await post("/api/projects/delete", { id: p.id });
    if (viewedProjectId === p.id && currentSessionId) await openSession(currentSessionId);
    refreshSidebar();
  } catch (e) { showError(e.message); }
}

/** ✓ Keep / ↶ Undo under a change (the user, 2026-11-12: "a correction done wrong: undo goes back to the old code"). */
function undoBar(ev) {
  // ↶ Undo beside "✓ Done" on this change's edit card(s) (the user, 2026-11-12), else a small bar of its own; only the
  // newest change can be undone (an older one would take the newer back with it)
  document.querySelectorAll(".ub-inline:not(.settled), .undo-bar:not(.settled)").forEach((b) => b.remove());
  const cards = [...chat.querySelectorAll(".tool.edit")].slice(-Math.max(1, ev.files.length));
  const make1 = () => {
    const b = make("button", "ub-inline", "↶ Undo");
    b.type = "button";
    b.title = "Put " + (ev.files.join(", ") || "the page") + " back as it was before this change";
    return b;
  };
  const buttons = [];
  const settle = (html) => buttons.forEach((b) => { b.classList.add("settled"); b.disabled = true; b.innerHTML = html; });
  async function doUndo(e) {
    e.stopPropagation();
    buttons.forEach((b) => (b.disabled = true));
    try {
      const d = await post("/api/undo", { id: ev.id });
      settle("↶ Undone");
      showNote(`↶ Undone: ${d.restored.filter((f) => !f.startsWith(".m42")).join(", ")} back as they were`);
      if (d.url) showPreview(d);
      if (!replaying) refreshTree();
    } catch (err) {
      buttons.forEach((b) => (b.disabled = false));
      showError(err.message);
    }
  }
  if (cards.length) {
    for (const c of cards) {
      const state = c.querySelector(".tool-state");
      const b = make1();
      b.onclick = doUndo;
      state.parentNode.insertBefore(b, state);
      buttons.push(b);
    }
  } else {
    const bar = make("div", "undo-bar", `<span class="ub-text">Changed ${ev.files.map((f) => `<code>${esc(f)}</code>`).join(", ") || "the page"}</span>`);
    const b = make1();
    b.onclick = doUndo;
    bar.appendChild(b);
    buttons.push(b);
    append(bar);
  }
}

async function renameSession(s) {
  const title = prompt("Rename chat", s.title);
  if (!title || title === s.title) return;
  try { await post("/api/sessions/rename", { id: s.id, title }); refreshSidebar(); }
  catch (e) { showError(e.message); }
}

// ---------------------------------------------------------------- sidebar

async function refreshTree(highlight) {
  if (window.files && files.open) syncFilesPane(viewedProjectId || null);  // 📁 the files of the chat / project on screen
  try {
    const data = await api("/api/tree");
    $("workspaceName").textContent = data.folders.length ? `· ${data.folders.map((f) => f.alias).join(", ")}` : "";
    const tree = $("tree");
    tree.innerHTML = "";
    if (!data.folders.length) tree.appendChild(make("div", "note", "No folder open"));
    else if (!data.items.length) tree.appendChild(make("div", "note", "Empty folder"));
    for (const it of data.items) {
      const row = make("div", "tree-item" + (it.dir ? " dir" : "") + (it.root ? " root" : ""));
      row.style.paddingLeft = `${6 + it.level * 14}px`;
      row.textContent = it.root ? `📂 ${it.name}` : `${it.dir ? "▸ " : ""}${it.name}`;
      row.title = it.root ? data.folders.find((f) => f.alias === it.name)?.path || it.path : it.path;
      if (!it.dir) row.onclick = () => viewFile(it.path);
      if (highlight && it.path === highlight) {
        row.classList.add("flash");
        requestAnimationFrame(() => row.scrollIntoView({ block: "nearest" }));
      }
      tree.appendChild(row);
    }
  } catch (e) { /* server may be shutting down */ }
}

/** A project file in the viewer: pictures and PDFs drawn, Word as a page, SVG as a picture (code one click
 * away), everything else as text. */
async function viewFile(path) {
  try {
    const d = await api(`/api/file?path=${encodeURIComponent(path)}`);
    const body = $("viewerBody"), tools = $("viewerTools");
    $("viewerTitle").textContent = d.path;
    body.innerHTML = "";
    tools.innerHTML = "";
    body.className = "viewer-body" + (d.kind ? ` view-${d.kind}` : "");
    const pre = (text) => { const p = make("pre", "viewer-text"); p.textContent = text; return p; };
    const img = () => { const i = make("img", "viewer-img"); i.alt = d.path; i.src = mediaUrl(d.abs); return i; };
    if (d.kind === "image") body.appendChild(img());
    else if (d.kind === "pdf") {
      const f = make("iframe", "viewer-pdf");
      f.src = mediaUrl(d.abs);
      f.title = d.path;
      body.appendChild(f);
    } else if (d.kind === "svg") {
      const picture = img(), code = pre(d.content || "");
      code.hidden = true;
      const toggle = make("button", "btn small ghost", "&lt;/&gt; Code");
      toggle.onclick = () => {
        picture.hidden = !picture.hidden;
        code.hidden = !code.hidden;
        toggle.innerHTML = code.hidden ? "&lt;/&gt; Code" : "🖼 Picture";
      };
      tools.appendChild(toggle);
      body.append(picture, code);
    } else if (d.kind === "docx") {
      if (d.error) body.appendChild(make("div", "hint", esc(d.error)));
      else body.innerHTML = d.html;  // built by docview.py: every text escaped, pictures as data: URLs
    } else body.appendChild(pre(d.binary ? "(binary file: no preview for this type)" : d.content));
    if (d.kind) {
      const open = make("button", "btn small ghost", "↗ Open in app");
      open.title = "Open with its usual program (Photos, Edge, Word…)";
      open.onclick = () => post("/api/doc/open", { path: d.abs }).catch((e) => showError(e.message));
      tools.appendChild(open);
    }
    $("viewer").showModal();
  } catch (e) { showError(e.message); }
}

/** 🧩 Models: new Hugging Face models that fit this PC (chat / code), downloads with progress, and "⚙ Custom". */
let hubTimer = null;
async function showModels(refresh = false) {
  const body = $("viewerBody"), tools = $("viewerTools");
  $("viewerTitle").textContent = "🧩 Models for this PC";
  body.className = "viewer-body learned hub";
  if (!$("viewer").open) {
    body.innerHTML = `<p class="learned-empty">${refresh ? "Checking Hugging Face…" : "Loading…"}</p>`;
    $("viewer").showModal();
  }
  tools.innerHTML = "";
  const again = make("button", "btn small ghost", "🔄 Check Hugging Face");
  again.onclick = () => { body.innerHTML = `<p class="learned-empty">Checking Hugging Face… (about 15 s)</p>`; showModels(true); };
  tools.appendChild(again);
  let d;
  try { d = await api(`/api/models/hub${refresh ? "?refresh=1" : ""}`); } catch (e) { body.innerHTML = ""; showError(e.message); return; }
  const hw = d.hardware || {}, jobs = d.jobs || {};
  const installedByFile = Object.fromEntries((d.installed || []).map((m) => [m.file, m]));
  body.innerHTML = "";
  body.appendChild(make("div", "hint", `💻 This PC: <b>${hw.ram_gb} GB RAM</b> (usable) · ${hw.cpus} CPU threads · ` +
    `${esc(hw.folder || "")}: ${hw.free_gb} GB free → models up to <b>${hw.max_file_gb} GB</b>. Speed is an estimate ` +
    `(RAM bandwidth ÷ size; measured here: q35-4b 11, q35-9b 6, coder-7b 12 tok/s). Downloads go to D: and appear in the model list.`));
  if (d.error) body.appendChild(make("div", "hint", "⚠ " + esc(d.error)));
  // ⚙ Combos: the user's named chat + code pairs, each with Use / Edit (name and models) / Delete
  const combos = d.combos || [];
  const auto = make("div", "learned-item own", `<div class="what"><b>⚙ Combos (a chat model + a code model, with a name)</b>` +
    `<span class="hint">${combos.length ? "M42 switches between the two of a combo by itself, like Auto. Each one is in the model list."
      : "Name a chat + code pair (e.g. “Tamil”, “Fast code”): it joins the model list."}</span></div>`);
  const add = make("button", "btn small", "➕ New combo");
  add.onclick = () => { pickerFrom = "models"; pickerEdit = ""; pickCustom(); };
  auto.appendChild(add);
  for (const c of combos) {
    const inUse = c.id === currentModel;
    const row = make("div", "own-card", `<div class="hint"><b>⚙ ${esc(c.name)}</b>${inUse ? " · in use" : ""} · ` +
      `💬 chat ${esc(shortModel(c.chat))} ↔ 💻 code ${esc(shortModel(c.code))}</div>`);
    const use = make("button", "btn small", inUse ? "In use" : "Use");
    use.disabled = inUse;
    use.onclick = async () => {
      try { await post("/api/config", { model: c.id }); showNote(`⚙ ${c.name} on: the next message loads it.`); await checkStatus(); showModels(); }
      catch (e) { showError(e.message); }
    };
    const edit = make("button", "btn small ghost", "✏ Edit name / models");
    edit.onclick = () => { pickerFrom = "models"; pickerEdit = c.id; pickCustom(); };
    const del = make("button", "btn small ghost", "Delete");
    del.onclick = async () => {
      if (!confirm(`Delete the combo “${c.name}”?\n(Only the pair is removed: both models stay on this PC.)`)) return;
      try { await post("/api/models/combo/delete", { id: c.id }); await checkStatus(); showModels(); } catch (e) { showError(e.message); }
    };
    row.append(use, edit, del);
    auto.appendChild(row);
  }
  body.appendChild(auto);
  body.appendChild(ownModelBox(hw));
  if (d.plugins) body.appendChild(pluginsBox(d));  // (M42 UI has no plugins)
  const busy = (j) => ["downloading", "copying", "moving"].includes(j.state);
  const running = Object.values(jobs).filter((j) => j.state !== "done");
  if (running.length) {  // every download, also the ones started from a search, and your own file being moved in
    body.appendChild(make("h3", "", "⬇ Downloads and moves"));
    for (const j of running) {
      const pct = j.total ? Math.floor(100 * j.done / j.total) : 0;
      const verb = { downloading: "⬇", copying: "📋 copying", moving: "📦 moving" }[j.state];
      const row = make("div", "learned-item", `<div class="what"><b>${esc(j.file)}</b><span class="hint">` +
        `${esc(j.repo)} · ${busy(j) ? `${verb} ${pct}% (${(j.done / 2 ** 30).toFixed(1)} / ` +
        `${(j.total / 2 ** 30).toFixed(1)} GB)` : `⚠ ${esc(j.state)} ${esc(j.error || "")}`}</span></div>`);
      if (busy(j)) {
        const stop = make("button", "btn small ghost", "Stop");
        stop.onclick = () => post("/api/models/cancel", { file: j.file }).then(() => showModels()).catch((e) => showError(e.message));
        row.appendChild(stop);
      }
      body.appendChild(row);
    }
  }
  body.appendChild(hubSearchBox(() => showModels()));
  const useButtons = (row, model) => {
    for (const kind of ["chat", "code"]) {
      const b = make("button", "btn small ghost", `Use for ${kind}`);
      b.onclick = async () => {
        try { await post("/api/models/use", { model, kind }); showModels(); } catch (e) { showError(e.message); }
      };
      row.appendChild(b);
    }
  };
  const card = (p, kind) => {
    const job = jobs[p.file];
    const meta = [`released ${p.released}`, `${p.size_gb} GB ${p.quant}`,
      `~${p.tok_s} tok/s ${p.fit === "good" ? "✅" : "⚠ " + p.fit}`, p.license && `licence ${p.license}`,
      p.vision && "👁 can read images"].filter(Boolean).join(" · ");
    const row = make("div", "learned-item", `<div class="what"><b>${p.new ? "🆕 " : ""}${esc(p.repo.split("/")[1].replace(/-GGUF$/i, ""))}</b>` +
      `<span class="hint">${esc(meta)}</span><span class="hint"><a href="https://huggingface.co/${esc(p.repo)}" ` +
      `target="_blank" rel="noopener">${esc(p.repo)}</a></span></div>`);
    const inst = installedByFile[p.file];
    if (inst) useButtons(row, inst.key);
    else if (job && job.state === "downloading") {
      const pct = job.total ? Math.floor(100 * job.done / job.total) : 0;
      row.appendChild(make("span", "hint", `⬇ ${pct}% (${(job.done / 2 ** 30).toFixed(1)} / ${(job.total / 2 ** 30).toFixed(1)} GB)`));
      const stop = make("button", "btn small ghost", "Stop");
      stop.onclick = () => post("/api/models/cancel", { file: p.file }).then(() => showModels()).catch((e) => showError(e.message));
      row.appendChild(stop);
    } else {
      if (job && job.state === "error") row.querySelector(".what").appendChild(make("span", "hint", "⚠ " + esc(job.error)));
      const dl = make("button", "btn small", job && job.state !== "done" ? "⬇ Resume" : "⬇ Download");
      dl.onclick = async () => {
        if (!confirm(`Download ${p.file}\n${p.size_gb} GB from huggingface.co/${p.repo}\ninto ${hw.folder}?`)) return;
        try { await post("/api/models/download", { repo: p.repo, file: p.file, bytes: p.bytes, sha256: p.sha256, kind }); showModels(); }
        catch (e) { showError(e.message); }
      };
      row.appendChild(dl);
    }
    return row;
  };
  const section = (title, items, kind, empty) => {
    body.appendChild(make("h3", "", `${title} (${items.length})`));
    if (!items.length) body.appendChild(make("p", "learned-empty", empty));
    for (const p of items) body.appendChild(card(p, kind));
  };
  section("💬 Chat models that fit", d.chat || [], "chat", "None found: press 🔄 Check Hugging Face.");
  section("💻 Code models that fit", d.code || [], "code", "No new code-only model fits this PC's RAM right now (they " +
    "are 18 GB+). coder-7b is still the best fit; a chat model above can also be used for code.");
  const own = d.installed || [];
  body.appendChild(make("h3", "", `📦 Downloaded here (${own.length})`));
  if (!own.length) body.appendChild(make("p", "learned-empty", "Nothing downloaded from this page yet."));
  for (const m of own) {
    const row = make("div", "learned-item", `<div class="what"><b>${esc(shortModel(m.key))}</b><span class="hint">` +
      `${esc(m.file)} · from ${esc(m.repo || "")}</span></div>`);
    useButtons(row, m.key);
    body.appendChild(row);
  }
  const big = [...((d.big || {}).chat || []), ...((d.big || {}).code || [])];
  if (big.length) {
    body.appendChild(make("h3", "", "🔭 Newer models that need more RAM (for a future upgrade)"));
    for (const p of big) body.appendChild(make("div", "learned-item", `<div class="what"><b>${esc(p.repo.split("/")[1].replace(/-GGUF$/i, ""))}</b>` +
      `<span class="hint">released ${esc(p.released)} · about ${p.size_gb} GB → needs ~${p.needs_ram_gb} GB RAM · ` +
      `<a href="https://huggingface.co/${esc(p.repo)}" target="_blank" rel="noopener">${esc(p.repo)}</a></span></div>`));
  }
  clearTimeout(hubTimer);
  if (Object.values(jobs).some(busy)) {
    hubTimer = setTimeout(() => { if ($("viewer").open && $("viewerTitle").textContent.startsWith("🧩")) showModels(); }, 2000);
  }
}

/** 📁 Your own model: choose a .gguf anywhere on this PC, see what it is, move or copy it into M42's models
 * folder and use it for chat or code (⚙ Custom). */
function ownModelBox(hw) {
  const box = make("div", "learned-item own", `<div class="what"><b>📁 Your own model (.gguf)</b><span class="hint">` +
    `A model you made or got elsewhere: M42 checks the file, moves or copies it into ${esc(hw.folder || "models")} ` +
    `and uses it for chat or code.</span></div>`);
  const pick = make("button", "btn small", "Choose .gguf file…");
  box.appendChild(pick);
  pick.onclick = async () => {
    let d;
    try { d = await post("/api/models/pick_local", {}); } catch (e) { showError(e.message); return; }
    if (d.cancelled) return;
    const i = d.info;
    box.querySelector(".own-card")?.remove();
    const meta = [`${i.size_gb} GB`, i.arch, i.context && `context ${i.context}`, `~${i.tok_s} tok/s (estimate)`,
      i.chat_template ? "chat template ✅" : null].filter(Boolean).join(" · ");
    const projName = i.mmproj ? i.mmproj.split(/[\\/]/).pop() : "";
    const card = make("div", "own-card", `<div class="hint"><b>${esc(i.name)}</b> · ${esc(meta)}</div>` +
      `<div class="hint">${esc(i.path)}</div>` +
      (i.mmproj ? `<div class="hint">👁 Its vision part goes with it: ${esc(projName)} (${i.mmproj_gb} GB): this model will read pictures too</div>`
        : `<div class="hint">No vision part (…mmproj….gguf with the same model name) next to it: text only</div>`) + i.warnings.map((w) => `<div class="hint">⚠ ${esc(w)}</div>`).join(""));
    const kind = make("select", "");
    kind.innerHTML = `<option value="chat">Use for chat</option><option value="code">Use for code</option>`;
    card.appendChild(kind);
    const go = async (mode) => {
      const where = d.folder;
      const pair = i.mmproj ? `\n+ its vision part ${projName} (${i.mmproj_gb} GB)` : "";
      const gb = (i.size_gb + (i.mmproj_gb || 0)).toFixed(2);
      const msg = i.in_folder ? `Add ${i.file}${pair}\n(already in ${where}) to M42's models for ${kind.value}?`
        : mode === "move" ? `Move ${i.file} (${i.size_gb} GB)${pair}\nfrom ${i.path}\nto ${where}?\n\nThey will no longer be at their old place.` +
          (i.same_drive ? "" : `\n(Another drive: copied first, the old files are removed only after full copies.)`)
          : `Copy ${i.file} (${i.size_gb} GB)${pair}\nfrom ${i.path}\nto ${where}?\n\nThe originals stay where they are (uses ${gb} GB more).`;
      if (!confirm(msg)) return;
      try {
        const job = await post("/api/models/import", { path: i.path, kind: kind.value, mode });
        if (job.state === "done") showNote(`📁 ${shortModel(job.key)} is ready for ${kind.value} in ⚙ Custom` +
          (job.vision ? " (👁 it reads pictures too)" : "") + `: press “Use Custom now”.`);
        showModels();
      } catch (e) { showError(e.message); }
    };
    if (i.in_folder) {
      const add = make("button", "btn small", "Add to M42");
      add.onclick = () => go("copy");
      card.appendChild(add);
    } else {
      const mv = make("button", "btn small", "📦 Move into M42");
      mv.onclick = () => go("move");
      const cp = make("button", "btn small ghost", "📋 Copy instead");
      cp.onclick = () => go("copy");
      card.append(mv, cp);
    }
    box.appendChild(card);
  };
  return box;
}

const TAKES = { image: "a picture", text: "text", audio: "an audio file" };
const readAsDataUrl = (file) => new Promise((ok, bad) => {
  const r = new FileReader(); r.onload = () => ok(r.result); r.onerror = bad; r.readAsDataURL(file);
});

/** 🔌 Plugins: any small model (upscaler, classifier, speech, embeddings…) added and tried here, or with
 * "@name" in the chat. Each runs in its own process on the CPU. */
function pluginsBox(d) {
  const box = make("div", "learned-item own", `<div class="what"><b>🔌 Plugins: try any model</b><span class="hint">` +
    `.onnx, .safetensors, .pth or a Hugging Face folder: M42 checks what it is, keeps it in ${esc(d.plugins_dir || "plugins")}, ` +
    `and you try it here or in the chat with <code>@name</code>. Chat / code models (.gguf) go in 📁 Your own model.</span></div>`);
  const addFile = make("button", "btn small", "Add model file…");
  const addFolder = make("button", "btn small ghost", "Add model folder…");
  box.append(addFile, addFolder);
  const choose = async (folder) => {
    box.querySelector(".own-card.pick")?.remove();
    const wait = make("div", "own-card pick", `<div class="hint">Checking the model (it is loaded once, on the CPU)…</div>`);
    let r;
    try { r = await post("/api/plugins/pick", { folder }); } catch (e) { showError(e.message); return; }
    if (r.cancelled) return;
    box.appendChild(wait);
    const i = r.info;
    const meta = [i.runtime, i.arch, i.task, i.purpose, i.scale && `x${i.scale}`, i.size_mb != null && `${i.size_mb} MB`,
      i.takes && `takes ${TAKES[i.takes] || i.takes}`, i.seconds != null && `checked in ${i.seconds} s`,
      i.ram_mb && `${i.ram_mb} MB RAM`].filter(Boolean).join(" · ");
    wait.innerHTML = `<div class="hint"><b>${esc(i.name)}</b> · ${esc(meta)}</div><div class="hint">${esc(i.path)}</div>` +
      (i.ok ? "" : `<div class="hint">⚠ M42 can't run it: ${esc(i.why || i.error || "unknown")}</div>`);
    if (!i.ok) return;
    const name = make("input", "");
    name.placeholder = "name for @ (optional)";
    const go = async (mode) => {
      const msg = mode === "move" ? `Move ${i.name}\nfrom ${i.path}\nto ${r.folder}?\n\nIt will no longer be at its old place.`
        : `Copy ${i.name}\nfrom ${i.path}\nto ${r.folder}?\n\nThe original stays where it is.`;
      if (!confirm(msg)) return;
      try {
        const job = await post("/api/plugins/add", { path: i.path, mode, name: name.value.trim() });
        if (job.state === "done") showNote(`🔌 @${job.key} is ready: try it on the Models page or type “@${job.key}” in the chat.`);
        showModels();
      } catch (e) { showError(e.message); }
    };
    const mv = make("button", "btn small", "📦 Move into M42");
    mv.onclick = () => go("move");
    const cp = make("button", "btn small ghost", "📋 Copy instead");
    cp.onclick = () => go("copy");
    wait.append(name, mv, cp);
  };
  addFile.onclick = () => choose(false);
  addFolder.onclick = () => choose(true);
  for (const p of d.plugins || []) {
    const row = make("div", "own-card", `<div class="hint"><b>@${esc(p.key)}</b> · ${esc([p.task, p.arch,
      p.size_mb != null && `${p.size_mb} MB`, `takes ${TAKES[p.takes] || p.takes}`].filter(Boolean).join(" · "))}</div>`);
    const tryBtn = make("button", "btn small", "▶ Try");
    const rm = make("button", "btn small ghost", "Remove");
    rm.onclick = async () => {
      if (!confirm(`Remove @${p.key} from M42?\nIts files are kept in plugins\\_removed (nothing is deleted).`)) return;
      try { await post("/api/plugins/remove", { key: p.key }); showModels(); } catch (e) { showError(e.message); }
    };
    tryBtn.onclick = () => {
      if (row.querySelector(".plugin-try")) return;
      const t = make("div", "plugin-try");
      const text = make("textarea", "");
      text.rows = 2;
      text.placeholder = p.task === "question-answering" ? "question, then the text on the next lines" :
        p.task === "text-to-image" ? "what to draw (optional: steps=20 size=512x512 seed=42 cfg=7 neg=\"blurry\")" : "text";
      const file = make("input", "");
      file.type = "file";
      file.accept = p.takes === "audio" ? "audio/*" : "image/png,image/jpeg,image/webp";
      const run = make("button", "btn small", "Run");
      const outBox = make("div", "plugin-out");
      if (p.takes === "text") t.append(text); else t.append(file);
      t.append(run, outBox);
      run.onclick = async () => {
        outBox.innerHTML = `<div class="hint">Running on the CPU…</div>`;
        const body = { key: p.key, text: text.value };
        try {
          if (file.files[0]) body[p.takes === "audio" ? "audio" : "image"] = await readAsDataUrl(file.files[0]);
          const res = await post("/api/plugins/run", body);
          const stats = `${res.seconds ?? "?"} s` + (res.ram_mb ? ` · ${res.ram_mb} MB RAM` : "");
          if (!res.ok) { outBox.innerHTML = `<div class="hint">⚠ ${esc(res.error || "failed")} (${stats})</div>`; return; }
          outBox.innerHTML = `<div class="hint">✅ ${esc(stats)}</div>` +
            (res.text ? `<pre>${esc(res.text)}</pre>` : "") +
            (res.labels || []).map((l) => `<div class="hint">${esc(l.label)}: ${(100 * l.score).toFixed(1)}%</div>`).join("") +
            (res.notes || []).map((n) => `<div class="hint">ℹ ${esc(n)}</div>`).join("") +
            (res.image ? `<a href="${mediaUrl(res.image)}" target="_blank"><img src="${mediaUrl(res.image)}" alt="result"></a>` : "");
        } catch (e) { outBox.innerHTML = ""; showError(e.message); }
      };
      row.appendChild(t);
    };
    row.append(tryBtn, rm);
    box.appendChild(row);
  }
  return box;
}

/** 🧠 Learned: what M42 kept while it was used, each with a Forget button. */
async function showLearned() {
  try {
    const d = await api("/api/learned");
    const body = $("viewerBody");
    $("viewerTitle").textContent = "🧠 What M42 learned (kept on this PC)";
    $("viewerTools").innerHTML = "";
    body.className = "viewer-body learned";
    body.innerHTML = "";
    const groups = [["design", "🎨 Design rules it learned by looking at its own pages"], ["lessons", "📝 Lessons from your corrections"], ["facts", "🌐 Answers it looked up on the web"],
      ["skills", "💻 Code that worked (skill library)"], ["tools", "🧰 Tools it made"]];
    for (const [kind, title] of groups) {
      const items = d[kind] || [];
      body.appendChild(make("h3", "", `${esc(title)} (${items.length})`));
      if (!items.length) body.appendChild(make("p", "learned-empty", "Nothing yet."));
      for (const it of items) {
        const when = new Date(it.created * 1000).toLocaleDateString();
        const row = make("div", "learned-item", `<div class="what"><b>${esc(it.title)}</b>` +
          `<span class="hint">${esc(when)} · used ${it.used}×</span><pre>${esc(it.detail || "")}</pre></div>`);
        const forget = make("button", "btn small ghost", "Forget");
        forget.onclick = async () => {
          try { await post("/api/learned/forget", { kind, id: it.id }); row.remove(); } catch (e) { showError(e.message); }
        };
        row.appendChild(forget);
        body.appendChild(row);
      }
    }
    $("viewer").showModal();
  } catch (e) { showError(e.message); }
}

/* 🎤 Speech to text in the prompt box (like Claude's mic): the browser records 16 kHz mono WAV (no format a
 * Python library might not read), the speech plugin writes the words, they go in at the cursor to edit or send. */
let speechPlugin = null, mic = null, speechEngines = [], speechEngine = "";

function wavFrom(chunks, rate) {
  const n = chunks.reduce((a, c) => a + c.length, 0), buf = new ArrayBuffer(44 + n * 2), v = new DataView(buf);
  const str = (o, s) => [...s].forEach((ch, i) => v.setUint8(o + i, ch.charCodeAt(0)));
  str(0, "RIFF"); v.setUint32(4, 36 + n * 2, true); str(8, "WAVE"); str(12, "fmt "); v.setUint32(16, 16, true);
  v.setUint16(20, 1, true); v.setUint16(22, 1, true); v.setUint32(24, rate, true); v.setUint32(28, rate * 2, true);
  v.setUint16(32, 2, true); v.setUint16(34, 16, true); str(36, "data"); v.setUint32(40, n * 2, true);
  let o = 44;
  for (const c of chunks) for (const x of c) { v.setInt16(o, Math.max(-1, Math.min(1, x)) * 0x7fff, true); o += 2; }
  return new Blob([buf], { type: "audio/wav" });
}

const MIC_ICON = '<svg viewBox="0 0 24 24" width="19" height="19" aria-hidden="true"><rect x="9" y="3.5" width="6" height="10.5" rx="3" fill="none" stroke="currentColor" stroke-width="1.75"/><path d="M5.75 11.25a6.25 6.25 0 0 0 12.5 0M12 17.5v3" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round"/></svg>';

/* Live typing (as in Claude: the words come into the box while you speak; the user, 2026-11-13): the voice is cut
 * into phrases at short pauses; each finished phrase is written for good, the phrase still being spoken is written
 * now and then as a grey draft that its final words replace. One request to the speech model at a time. */
const SPEECH_PAUSE = 0.8, SPEECH_MAX = 20, SPEECH_DRAFT_EVERY = 700;  // a pause (s), the longest phrase (s), drafts at most this often (ms)

function micShow(m) {
  const input = $("input"), words = [m.done, m.draft].filter(Boolean).join(" ");
  const glue = m.before && words && !/\s$/.test(m.before) ? " " : "";
  input.value = m.before + glue + words + m.after;
  input.selectionStart = input.selectionEnd = (m.before + glue + words).length;
  input.dispatchEvent(new Event("input"));  // the box grows to fit, the send button turns ready
  input.scrollTop = input.scrollHeight;
}

async function micWords(m, chunks, final) {
  const audio = await readAsDataUrl(wavFrom(chunks, m.rate));
  const t = Date.now();
  // the words already said go with it (Whisper's context), and a finished phrase is read more carefully than a draft
  const res = await post("/api/speech", { audio, prompt: (m.done || "").slice(-200), final: !!final });  // Whisper / IndicConformer on this PC
  // the next draft no sooner than one takes (IndicConformer ~0.2 s, Whisper Tanglish ~0.6 s, Whisper small ~3.5 s): the
  // last few averaged, so one slow first run (a model warming up) does not hold the drafts back
  m.costs = [...(m.costs || []), Date.now() - t].slice(-3);
  m.cost = m.costs.length > 1 ? Math.min(...m.costs.slice(1)) * 0.5 + (m.costs.reduce((a, b) => a + b, 0) / m.costs.length) * 0.5 : 0;
  if (!res.ok) throw new Error(res.error || "no words heard");
  m.engine = res.engine || m.engine;
  return (res.text || "").trim();
}

// the speech model's queue: finished phrases first (in order), then a draft of the phrase being spoken
async function micPump(m) {
  if (m.busy) return;
  m.busy = true;
  try {
    while (m.finals.length || (m.wantDraft && !m.closed)) {
      if (m.finals.length) {
        const text = await micWords(m, m.finals.shift(), true);
        if (text) m.done = [m.done, text].filter(Boolean).join(" ");
        micShow(m);
      } else {
        m.wantDraft = false;
        const from = m.segStart, seg = m.chunks.slice(from);
        const text = seg.length ? await micWords(m, seg) : "";
        if (!m.closed && m.segStart === from) { m.draft = text; micShow(m); }  // (not when its phrase has ended meanwhile)
      }
    }
  } catch (e) { showError("🎤 " + e.message); m.finals = []; m.stats.errors++; }
  finally { m.busy = false; if (m.drained && !m.finals.length) m.drained(); }
}

async function startMic() {
  post("/api/speech/warm").catch(() => {});  // (the speech model loads while the user speaks)
  let stream;
  try {
    stream = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true } });
  } catch (e) { showError(`Microphone: ${e.message} (allow the microphone for M42 in Windows settings / the browser)`); return; }
  const ctx = new AudioContext({ sampleRate: 16000 });
  const src = ctx.createMediaStreamSource(stream), node = ctx.createScriptProcessor(4096, 1, 1), chunks = [];
  const input = $("input"), at = input.selectionStart ?? input.value.length;
  const m = { ctx, stream, src, node, chunks, rate: ctx.sampleRate, before: input.value.slice(0, at),
              after: input.value.slice(input.selectionEnd ?? at), done: "", draft: "", finals: [], segStart: 0,
              spoke: false, quiet: 0, floor: null, lastDraft: Date.now(), busy: false, closed: false, engine: "",
              stats: { n: 0, max: 0, loud: 0, finals: 0, drafts: 0, errors: 0 } };
  // each block of sound (~0.26 s): its loudness against the room's own quiet (a noisy fan, a quiet room) says
  // speech or pause; a pause after speech ends the phrase, which goes to the speech model at once
  node.onaudioprocess = (e) => {
    const x = new Float32Array(e.inputBuffer.getChannelData(0));
    chunks.push(x);
    let sum = 0;
    for (const v of x) sum += v * v;
    const rms = Math.sqrt(sum / x.length), secs = x.length / m.rate;
    // the room's quiet: the lowest level lately (drops at once, rises slowly); speech is well above it, however
    // loud the mic is (a fixed 0.012 never heard a quiet laptop mic: nothing was written, 2026-11-13)
    m.floor = m.floor === null ? rms : Math.min(rms, m.floor * 1.02 + 1e-6);  // (a silent start is 0: a level too)
    const loud = rms > Math.max(0.0015, m.floor * 2.5);
    m.stats.n++; m.stats.max = Math.max(m.stats.max, rms); if (loud) m.stats.loud++;
    if (loud) { m.spoke = true; m.quiet = 0; } else m.quiet += secs;
    const segSecs = (chunks.length - m.segStart) * secs;
    if (m.spoke && (m.quiet >= SPEECH_PAUSE || segSecs >= SPEECH_MAX)) {  // a phrase finished
      m.finals.push(chunks.slice(m.segStart));
      m.stats.finals++;
      m.segStart = chunks.length;
      m.spoke = false;
      m.draft = "";
      micPump(m);
    } else if (!m.spoke && m.quiet >= SPEECH_PAUSE) {
      m.segStart = Math.max(m.segStart, chunks.length - 2);  // silence before speech: not sent (Whisper makes up words in it)
    } else if (m.spoke && Date.now() - m.lastDraft > Math.max(SPEECH_DRAFT_EVERY, m.cost || 0) && !m.busy) {
      m.lastDraft = Date.now();
      m.wantDraft = true;
      m.stats.drafts++;
      micPump(m);
    }
  };
  src.connect(node); node.connect(ctx.destination);
  const btn = $("micBtn"), started = Date.now();
  // the voice as a moving wave in the message box (as in Claude): bars that rise with the voice, small dots in the
  // quiet, scrolling from the right; the mic button a plain stop square (the user, 2026-11-12: no red recording blink)
  const analyser = ctx.createAnalyser();
  analyser.fftSize = 512;
  src.connect(analyser);
  const wave = $("micWave"), cv = wave.querySelector("canvas"), time = wave.querySelector(".mw-time");
  $("composer").classList.add("is-recording");
  wave.hidden = false;
  const levels = [], buf = new Float32Array(analyser.fftSize);
  let raf = 0, last = 0;
  const draw = (now) => {
    raf = requestAnimationFrame(draw);
    const dpr = window.devicePixelRatio || 1, W = cv.clientWidth, H = cv.clientHeight;
    if (cv.width !== Math.round(W * dpr)) { cv.width = Math.round(W * dpr); cv.height = Math.round(H * dpr); }
    if (now - last > 55) {  // one bar every ~55 ms
      last = now;
      analyser.getFloatTimeDomainData(buf);
      let sum = 0;
      for (const v of buf) sum += v * v;
      levels.push(Math.min(1, Math.sqrt(sum / buf.length) * 6));
      if (levels.length > 400) levels.shift();
      const s = Math.floor((Date.now() - started) / 1000);
      time.textContent = `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
    }
    const c = cv.getContext("2d"), step = 6 * dpr, bw = 3 * dpr, mid = cv.height / 2;
    c.clearRect(0, 0, cv.width, cv.height);
    c.fillStyle = getComputedStyle(cv).color;
    const n = Math.floor(cv.width / step);
    for (let i = 0; i < n; i++) {
      const lv = levels[levels.length - n + i];
      const x = cv.width - (n - i) * step;
      const h = lv === undefined ? 0 : Math.max(bw, lv * (cv.height - 4 * dpr));  // quiet: a dot
      if (lv === undefined) continue;
      c.beginPath();
      if (c.roundRect) c.roundRect(x, mid - h / 2, bw, h, bw / 2); else c.rect(x, mid - h / 2, bw, h);
      c.fill();
    }
  };
  raf = requestAnimationFrame(draw);
  m.raf = raf;
  m.stopWave = () => { cancelAnimationFrame(raf); wave.hidden = true; $("composer").classList.remove("is-recording");
                       if (m.placeholder !== undefined) $("input").placeholder = m.placeholder; };
  m.placeholder = input.placeholder;
  input.placeholder = "Listening… the words come here as you speak";
  mic = m;
  btn.classList.add("recording");
  btn.innerHTML = '<svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true"><rect x="5" y="5" width="14" height="14" rx="3" fill="currentColor"/></svg>';
  btn.title = "Stop (Esc cancels). The words come into the box as you speak; Send sends at once";
}

// stop listening; keep: the last phrase is written too, and this waits until every phrase is in the box
async function stopMic(keep = true) {
  const m = mic, btn = $("micBtn");
  if (!m) return;
  mic = null;
  if (m.stopWave) m.stopWave();
  m.node.onaudioprocess = null;
  m.node.disconnect(); m.src.disconnect(); m.stream.getTracks().forEach((t) => t.stop());
  m.ctx.close().catch(() => {});
  btn.classList.remove("recording");
  btn.innerHTML = MIC_ICON;
  btn.title = "Speak";
  m.closed = true;
  if (!keep) {  // Esc: what was said is taken out of the box
    m.finals = [];
    m.done = m.draft = "";
    micShow(m);
    return;
  }
  if (m.spoke && m.chunks.length - m.segStart > 1) { m.finals.push(m.chunks.slice(m.segStart)); m.stats.finals++; }
  else if (!m.stats.finals && !m.done && m.chunks.length > 3) { m.finals.push(m.chunks.slice(0)); m.stats.finals++; }  // nothing heard as speech: all of it, as before
  post("/api/speech/diag", { ...m.stats, floor: m.floor, secs: m.chunks.length * 4096 / m.rate }).catch(() => {});  // (in logs/app.log)
  if (!m.finals.length && !m.busy) { m.draft = ""; micShow(m); return; }
  btn.disabled = true;
  btn.innerHTML = '<span class="mic-spin" aria-hidden="true"></span>';
  await new Promise((ok) => { m.drained = ok; micPump(m); });
  btn.disabled = false;
  btn.innerHTML = MIC_ICON;
  m.draft = "";
  micShow(m);
  $("input").focus();
}

$("micBtn").innerHTML = MIC_ICON;
$("micBtn").addEventListener("click", () => {
  if (!mic && !speechPlugin) {
    showNote("🎤 Speech to text is not set up in M42 UI yet (it needs an offline speech model on this PC). Type your request for now.");
    return;
  }
  return mic ? stopMic(true) : startMic();
});
document.addEventListener("keydown", (e) => { if (e.key === "Escape" && mic) { e.preventDefault(); stopMic(false); } });

async function checkStatus() {
  const box = $("status");
  try {
    const s = await api("/api/status");
    lastModels = s.models || [];
    lastLocal = s.local_models || [];
    lastCustom = s.custom || null;
    lastCombos = s.combos || {};
    currentModel = s.model;
    // new models found on Hugging Face since the Models page was last opened (checked at app start)
    $("openModels").textContent = s.models_new ? `🧩 Models · ${s.models_new} new` : "🧩 Models";
    $("openModels").classList.toggle("has-new", !!s.models_new);
    fillModelSelect(s.model);
    showUpdate(s.update);  // ⬆ a newer M42 UI on GitHub (updater.py)
    speechPlugin = s.speech_plugin || null;  // 🎤 only when a speech-to-text plugin is installed
    speechEngines = s.speech_engines || [];
    speechEngine = s.speech_engine || (speechEngines[0] || {}).id || "";
    $("micModel").hidden = speechEngines.length < 2;
    $("micBtn").hidden = false;  // (always in the box, as in Claude's; without a speech plugin it says how to get one)
    if (speechPlugin) $("micBtn").title = `Speak: press, talk, press again (Esc cancels). @${speechPlugin} writes it here, on this PC`;
    const w = s.warm || {};
    const label = (s.model || "").startsWith("llama.cpp/auto")
      ? `${lastCombos[s.model] ? `⚙ ${lastCombos[s.model].name}` : `🔀 ${s.model.endsWith("-fast") ? "Auto fast"
        : s.model.endsWith("-quality") ? "Auto quality" : "Auto"}`} ` +
        `(now: ${shortModel(s.active_model)})` : modelLabel(s.model);
    let pending = false;
    const su = s.setup || {};
    if (su.state === "running") {  // a new PC: the model and llama-server are downloading (firstrun.py)
      const pct = su.total ? Math.floor(su.done * 100 / su.total) : 0;
      const mb = (n) => (n / 1048576).toFixed(0);
      box.className = "status";
      $("statusText").textContent = `⬇ First run: ${su.step || "getting ready"} · ${pct}% (${mb(su.done)} of ${mb(su.total)} MB)`;
      if (!window._m42SetupNoted) {
        window._m42SetupNoted = true;
        alertNote(`M42 UI is downloading what it needs for the first time (about ${su.gb || 3.3} GB). ` +
                  "Nothing more to do: it continues by itself and is ready when the bar says so.");
      }
      clearTimeout(statusTimer); statusTimer = setTimeout(checkStatus, 1500);
      return;
    }
    if ((su.state === "needs_consent" || su.state === "error") && (su.missing || []).length) {
      // ⬇ a new PC: what is missing, its size, and the user's yes before anything downloads (firstrun.py)
      if (!document.querySelector(".m42-setup-ask")) {
        const g = su.groups || {};
        const part = (k, name) => g[k] ? `${name} ${g[k] < 1 ? Math.round(g[k] * 1024) + " MB" : g[k].toFixed(1) + " GB"}` : "";
        const n = document.createElement("div");
        n.className = "m42-setup-note m42-setup-ask";
        n.innerHTML = `<b>M42 UI needs to download ${su.gb} GB for this PC</b><span>` +
          [part("model", `AI model (${su.tier_label})`), part("runner", "its runner (llama.cpp)"), part("speech", "speech models (IndicConformer Tamil + Whisper small)")]
            .filter(Boolean).join(" · ") + ". From Hugging Face and GitHub; nothing else is sent.</span>" +
          (su.state === "error" ? `<span>The last download stopped: ${esc(su.error || "")}. It resumes where it stopped.</span>` : "");
        const go = document.createElement("button");
        go.type = "button"; go.textContent = su.state === "error" ? "Resume download" : "Download";
        go.onclick = async () => { n.remove(); await post("/api/setup/start").catch((e) => showError(e.message)); checkStatus(); };
        const later = document.createElement("button");
        later.type = "button"; later.textContent = "Not now"; later.className = "ghost"; later.onclick = () => n.remove();
        n.append(go, later);
        document.body.appendChild(n);
      }
      box.className = "status bad";
      $("statusText").textContent = `First run: ${su.gb} GB to download (press Download)`;
      return;
    }
    if (su.state === "error") {
      box.className = "status bad";
      $("statusText").textContent = `First-run download stopped: ${su.error} (restart M42 UI to resume)`;
      return;
    }
    if (s.backend_state === "loading" || w.state === "loading") {
      box.className = "status";
      $("statusText").textContent = `Loading ${label}…`;
      pending = true;
    } else if (!s.ok) {
      box.className = "status bad";
      $("statusText").textContent = `Model server offline — ${s.error}`;
    } else if (!s.model_found) {
      box.className = "status bad";
      $("statusText").textContent = `Model "${s.model}" not found. Pick another one below.`;
    } else if (w.state === "warming") {
      box.className = "status";
      $("statusText").textContent = `${label} · preparing prompt cache…`;
      pending = true;
    } else {
      box.className = "status ok";
      $("statusText").textContent = `${label} · ready` + (w.seconds ? ` (warmed up in ${w.seconds}s)` : "");
    }
    clearTimeout(statusTimer);
    if (pending) statusTimer = setTimeout(checkStatus, 2000);
  } catch (e) {
    box.className = "status bad";
    $("statusText").textContent = `App server unreachable: ${e.message}`;
  }
}

function alertNote(text) {  // a one-time note at the top of the window
  const n = document.createElement("div");
  n.className = "m42-setup-note";
  n.textContent = text;
  const close = document.createElement("button");
  close.type = "button"; close.textContent = "OK"; close.onclick = () => n.remove();
  n.appendChild(close);
  document.body.appendChild(n);
}

function modelLabel(m) {
  if (m === "llama.cpp/auto") return "🔀 Auto: Qwen3.5 4B (plans, pictures and code)";
  if (lastCombos[m]) {  // the user's named chat + code pairs
    const c = lastCombos[m];
    return `⚙ ${c.name}: chat ${shortModel(c.chat)} ↔ code ${shortModel(c.code)}`;
  }
  if (m === "llama.cpp/auto-my") return lastCustom
    ? `⚙ Custom: chat ${shortModel(lastCustom.chat)} ↔ code ${shortModel(lastCustom.code)}` : "⚙ Custom";
  return m && m.startsWith("llama.cpp/") ? `⚡ ${m.slice(10)} (llama.cpp)` : m;
}
const shortModel = (m) => (m || "").replace("llama.cpp/", "");
const CUSTOM_PICK = "__custom__";
let lastCustom = null;  // {chat, code} of ⚙ Custom, from /api/status
let lastCombos = {};  // {"llama.cpp/auto-my-tamil": {id, name, chat, code}}: every named pair

/** 🔎 Search Hugging Face (Models page and Custom picker): any model name; fit, speed here, download. */
let searchTimer = null;
function hubSearchBox(onDownloaded) {
  const box = make("div", "hub-search", `<div class="hub-search-row"><input type="search" class="hub-q" ` +
    `placeholder="🔎 Search Hugging Face: e.g. qwen coder, gemma 4, granite, phi"><button class="btn small">Search</button></div>` +
    `<div class="hub-results"></div>`);
  const input = box.querySelector(".hub-q"), out = box.querySelector(".hub-results");
  const run = async () => {
    const q = input.value.trim();
    if (q.length < 2) return;
    out.innerHTML = `<p class="learned-empty">Searching Hugging Face for “${esc(q)}”…</p>`;
    let d;
    try { d = await api(`/api/models/search?q=${encodeURIComponent(q)}`); } catch (e) { out.innerHTML = ""; showError(e.message); return; }
    out.innerHTML = "";
    if (d.error) out.appendChild(make("p", "hint", "⚠ " + esc(d.error)));
    if (!d.results.length && !d.error) out.appendChild(make("p", "learned-empty", `No chat / code (GGUF) model named like “${esc(q)}” from the ` +
      "usual uploaders (unsloth, bartowski, lmstudio, ggml-org) or the labs themselves."));
    for (const p of d.results) {
      const meta = [p.kind === "code" ? "💻 code" : "💬 chat", p.file ? `${p.size_gb} GB ${p.quant}` : `about ${p.size_gb} GB`,
        p.fits ? `~${p.tok_s} tok/s ${p.fit === "good" ? "✅" : "⚠ " + p.fit}` : `❌ too big: needs ~${p.needs_ram_gb} GB RAM`,
        p.license && `licence ${p.license}`, p.vision && "👁"].filter(Boolean).join(" · ");
      const row = make("div", "learned-item", `<div class="what"><b>${esc(p.repo.split("/")[1].replace(/-GGUF$/i, ""))}</b>` +
        `<span class="hint">${esc(meta)}</span><span class="hint"><a href="https://huggingface.co/${esc(p.repo)}" ` +
        `target="_blank" rel="noopener">${esc(p.repo)}</a> · ${p.downloads ?? 0} downloads</span></div>`);
      const job = (d.jobs || {})[p.file];
      if (p.installed) row.appendChild(make("span", "hint", "✅ on this PC"));
      else if (job && job.state === "downloading") row.appendChild(make("span", "hint", `⬇ ${Math.floor(100 * job.done / job.total)}%`));
      else if (p.fits && p.file) {
        const dl = make("button", "btn small", "⬇ Download");
        dl.onclick = async () => {
          if (!confirm(`Download ${p.file}\n${p.size_gb} GB from huggingface.co/${p.repo}\ninto ${d.hardware.folder}?`)) return;
          try {
            await post("/api/models/download", { repo: p.repo, file: p.file, bytes: p.bytes, sha256: p.sha256, kind: p.kind });
            dl.replaceWith(make("span", "hint download-state", "⬇ starting…"));
            watchDownload(p.file, row, onDownloaded);
          } catch (e) { showError(e.message); }
        };
        row.appendChild(dl);
      }
      out.appendChild(row);
    }
    // (M42 UI: no plugin models)
  };
  box.querySelector("button").onclick = run;
  input.addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); run(); } });
  return box;
}

/** The same search for 🔌 plugin models (ONNX, transformers, upscalers): what each does, how it would run here,
 * its licence, and Download (into plugins/, checked, then ready for ▶ Try and @name). */
async function pluginResults(q, out, onDownloaded) {
  const head = make("h3", "", "🔌 Plugin models (run on the CPU)");
  const wait = make("p", "learned-empty", `Looking for models that do “${esc(q)}”…`);
  out.append(head, wait);
  let d;
  try { d = await api(`/api/plugins/search?q=${encodeURIComponent(q)}`); } catch (e) { wait.textContent = "⚠ " + e.message; return; }
  wait.remove();
  if (d.error) out.appendChild(make("p", "hint", "⚠ " + esc(d.error)));
  if (!d.results.length && !d.error) out.appendChild(make("p", "learned-empty", "No plugin model found for these words."));
  for (const p of d.results) {
    const meta = [p.task, p.runtime && `runs as ${p.runtime}`, p.size_mb != null && `${p.size_mb} MB`,
      p.license && `licence ${p.license}`, `${p.downloads ?? 0} downloads`].filter(Boolean).join(" · ");
    const row = make("div", "learned-item", `<div class="what"><b>${esc(p.repo.split("/")[1])}</b><span class="hint">${esc(meta)}</span>` +
      (p.copy_of ? `<span class="hint">↳ a copy of ${esc(p.copy_of)} that runs here</span>` : "") +
      (p.why ? `<span class="hint">⚠ can't run here: ${esc(p.why)}</span>` : "") +
      (p.needs_base ? `<span class="hint">🎨 a LoRA: it draws on a ${esc(p.needs_base)} model, download one too</span>` : "") +
      (p.runtime_download ? `<span class="hint">🎨 comes with stable-diffusion.cpp ${esc(p.runtime_download.tag || "")} ` +
        `(${(p.runtime_download.size / 2 ** 20).toFixed(0)} MB, github.com/leejet)</span>` : "") +
      (p.alt ? `<span class="hint">✅ runs as its copy <a href="#" class="go-alt">${esc(p.alt)} ↑ show it</a></span>` : "") +
      `<span class="hint"><a href="https://huggingface.co/${esc(p.repo)}" target="_blank" rel="noopener">${esc(p.repo)}</a></span></div>`);
    if (p.installed) row.appendChild(make("span", "hint", "✅ a plugin already"));
    else if (!p.why) {
      const dl = make("button", "btn small", "⬇ Download");
      dl.onclick = async () => {
        const rt = p.runtime_download;
        const files = (p.files || []).map((f) => `  ${f[0]} (${(f[1] / 2 ** 20).toFixed(1)} MB)`).join("\n") +
          (rt ? `\n  + ${rt.name} (${(rt.size / 2 ** 20).toFixed(1)} MB) from github.com/leejet/stable-diffusion.cpp, the program that draws` : "");
        if (!confirm(`Download ${p.repo} (${p.size_mb} MB) from huggingface.co\ninto ${d.folder}?\n\n${files}` +
          (p.license && !/^(mit|apache-2\.0|bsd)/i.test(p.license) ? `\n\nLicence: ${p.license}: check its terms on the model page.` : ""))) return;
        try {
          const job = await post("/api/plugins/download", { repo: p.repo });
          dl.replaceWith(make("span", "hint download-state", "⬇ starting…"));
          watchDownload(job.file, row, onDownloaded);
        } catch (e) { showError(e.message); }
      };
      row.appendChild(dl);
    }
    row.dataset.repo = p.repo;
    row.querySelector(".go-alt")?.addEventListener("click", (e) => {
      e.preventDefault();
      const target = [...out.querySelectorAll(".learned-item")].find((r) => r.dataset.repo === p.alt);
      if (!target) return;
      target.scrollIntoView({ behavior: "smooth", block: "center" });
      target.classList.add("flash");
      setTimeout(() => target.classList.remove("flash"), 1600);
    });
    out.appendChild(row);
  }
}

/** A download's progress in its search row; when done, `onDone` (e.g. reload the Custom lists). */
function watchDownload(file, row, onDone) {
  clearTimeout(searchTimer);
  const tick = async () => {
    let jobs = {};
    try { jobs = (await api("/api/models/hub?jobs_only=1")).jobs || {}; } catch (e) { return; }
    const j = jobs[file], label = row.querySelector(".download-state");
    if (!j || !label) return;
    if (j.state === "downloading") {
      const mb = j.total < 2 ** 30, unit = mb ? 2 ** 20 : 2 ** 30;  // a plugin is often MBs, not GBs
      label.textContent = `⬇ ${Math.floor(100 * j.done / j.total)}% (${(j.done / unit).toFixed(mb ? 0 : 1)} / ` +
        `${(j.total / unit).toFixed(mb ? 0 : 1)} ${mb ? "MB" : "GB"})`;
      searchTimer = setTimeout(tick, 2000);
    } else if (j.state === "done") {
      label.textContent = "✅ downloaded: now in the lists";
      checkStatus();
      if (onDone) onDone();
    } else label.textContent = `⚠ ${j.state}: ${j.error || ""}`;
  };
  searchTimer = setTimeout(tick, 1000);
}

/** ⚙ Custom: two lists of the models on this PC (size and estimated speed), saved as the chat + code pair.
 * from: "models" when opened from the Models page (Back returns there). */
let pickerFrom = null;
let pickerEdit = null;  // the combo being edited ("" = a new one, null = not chosen yet)
let currentModel = null;  // the model / Auto / combo in use, from /api/status
async function pickCustom(from) {
  if (from !== undefined) { pickerFrom = from; pickerEdit = null; }
  let d;
  try { d = await api("/api/models/local"); } catch (e) { showError(e.message); return; }
  const combos = d.combos || [];
  const editing = combos.find((c) => c.id === pickerEdit) || null;  // "Edit" on a combo fills the form with it
  const now = editing || (pickerEdit === "" ? {} : d.custom || d.auto || {});
  const label = (m) => `${shortModel(m.model)} · ${m.size_gb} GB · ${m.measured ? "" : "~"}${m.tok_s} tok/s` +
    `${m.measured ? " (measured)" : ""}${m.vision ? " · 👁" : ""}` +
    (m.draft ? " · +draft" : "");
  const list = (kind) => `<select class="custom-pick" data-kind="${kind}">` + d.models.map((m) =>
    `<option value="${esc(m.model)}"${m.model === now[kind] ? " selected" : ""}>${esc(label(m))}</option>`).join("") + "</select>";
  const body = $("viewerBody");
  $("viewerTitle").textContent = "⚙ Combos: a chat model + a code model, with a name";
  $("viewerTools").innerHTML = "";
  const back = make("button", "btn small ghost", pickerFrom === "models" ? "← Back to Models" : "← Back");
  back.onclick = () => (pickerFrom === "models" ? showModels() : $("viewer").close());
  $("viewerTools").appendChild(back);
  body.className = "viewer-body learned";
  body.innerHTML = "";
  // the saved combos: use, edit, delete
  body.appendChild(make("h3", "", `Your combos (${combos.length})`));
  if (!combos.length) body.appendChild(make("p", "learned-empty", "None yet: name your first pair below."));
  for (const c of combos) {
    const inUse = c.id === currentModel;
    const row = make("div", "learned-item", `<div class="what"><b>⚙ ${esc(c.name)}${inUse ? " · in use" : ""}</b>` +
      `<span class="hint">💬 chat ${esc(shortModel(c.chat))} ↔ 💻 code ${esc(shortModel(c.code))}</span></div>`);
    const use = make("button", "btn small", inUse ? "In use" : "Use");
    use.disabled = inUse;
    use.onclick = async () => {
      try { await post("/api/config", { model: c.id }); $("viewer").close(); showNote(`⚙ ${c.name} on: the next message loads it.`); checkStatus(); }
      catch (e) { showError(e.message); }
    };
    const edit = make("button", "btn small ghost", "Edit");
    edit.onclick = () => { pickerEdit = c.id; pickCustom(); };
    const del = make("button", "btn small ghost", "Delete");
    del.onclick = async () => {
      if (!confirm(`Delete the combo “${c.name}”?\n(Only the pair is removed: both models stay on this PC.)`)) return;
      try { await post("/api/models/combo/delete", { id: c.id }); if (pickerEdit === c.id) pickerEdit = ""; pickCustom(); checkStatus(); }
      catch (e) { showError(e.message); }
    };
    row.append(use, edit, del);
    body.appendChild(row);
  }
  // the form: a new combo, or the one being edited
  body.appendChild(make("h3", "", editing ? `✏ Edit “${esc(editing.name)}”` : "➕ New combo"));
  body.appendChild(make("p", "hint", `From the models on this PC (📂 ${esc(String(d.models.length))} found; more on the ` +
    "🧩 Models page). M42 switches between the two by itself, like Auto. Speeds are estimates for this PC."));
  const name = make("input", "custom-pick combo-name");
  name.placeholder = "Name, e.g. Tamil, Fast code, ESP32";
  name.maxLength = 30;
  name.value = editing ? editing.name : "";
  body.appendChild(name);
  body.insertAdjacentHTML("beforeend", `<h3>💬 Chat, research, documents</h3>${list("chat")}<h3>💻 Code, web pages, firmware</h3>${list("code")}`);
  const save = make("button", "btn primary", editing ? "Save and use" : "Save and use");
  save.style.marginTop = "14px";
  save.onclick = async () => {
    const pick = Object.fromEntries([...body.querySelectorAll("select.custom-pick")].map((s) => [s.dataset.kind, s.value]));
    if (!name.value.trim()) { name.focus(); showError("Give the combo a name"); return; }
    try {
      const r = await post("/api/models/custom", { ...pick, name: name.value.trim(), id: editing ? editing.id : "" });
      await post("/api/config", { model: r.model });
      lastCustom = r.custom;
      pickerEdit = null;
      $("viewer").close();
      showNote(`⚙ ${name.value.trim()} on: chat ${shortModel(pick.chat)} ↔ code ${shortModel(pick.code)}. The next message loads them.`);
      checkStatus();
    } catch (e) { showError(e.message); }
  };
  body.appendChild(save);
  if (editing) {
    const cancel = make("button", "btn ghost", "New combo instead");
    cancel.style.margin = "14px 0 0 8px";
    cancel.onclick = () => { pickerEdit = ""; pickCustom(); };
    body.appendChild(cancel);
  }
  // a model that isn't here yet: search Hugging Face, download, and it joins the lists above
  body.appendChild(make("h3", "", "🔎 Not in the lists? Search Hugging Face"));
  body.appendChild(hubSearchBox(() => pickCustom()));
  if (!$("viewer").open) $("viewer").showModal();
}

let pendingSelect = null;  // a rebuild that waited while the list was open

function fillModelSelect(current) {
  const sel = $("modelSelect");
  // don't rebuild while the user has it open, unless it has no real list yet: it was built before the first
  // status (one "⚙ Custom" option) and, with the focus kept on it, never got the list
  if (sel.matches(":focus") && sel.options.length > 2) { pendingSelect = current; return; }
  pendingSelect = null;
  if (!lastLocal.length && !lastModels.length) {  // the first status hasn't come yet
    sel.innerHTML = `<option value="${esc(current || "")}" selected>Loading models…</option>`;
    return;
  }
  const opt = (m) => `<option value="${esc(m)}"${m === current ? " selected" : ""}>${esc(modelLabel(m))}</option>`;
  const remote = [...new Set([...lastModels, ...(current && !current.startsWith("llama.cpp/") ? [current] : [])])].sort();
  let html = "";
  // ⚙ Custom…: pick any two models on this PC (one for chat, one for code); the pair is "llama.cpp/auto-my"
  const custom = `<option value="${CUSTOM_PICK}">⚙ Combos… (name a chat + code pair, edit, delete)</option>`;
  // only the pairs (the 3 Autos and the user's ⚙ combos): M42 works as chat ↔ code. A single model is used through
  // a combo; it is listed only while it is the one in use (chosen before this list changed)
  const pairs = lastLocal.filter((m) => m.startsWith("llama.cpp/auto") || m === current);
  if (lastLocal.length) html += `<optgroup label="Chat ↔ code combos (llama.cpp)">${pairs.map(opt).join("")}${custom}</optgroup>`;
  if (remote.length) html += `<optgroup label="Ollama / other server">${remote.map(opt).join("")}</optgroup>`;
  sel.innerHTML = html || opt(current);
}

// ---------------------------------------------------------------- settings

async function openSettings() {
  const cfg = await api("/api/config");
  const f = $("settingsForm");
  // 🎤 the speech models here, from the status already read (asking for it again here made the first click on
  // Settings wait for the whole status: the dialog seemed not to open, the user, 2026-11-13)
  $("speechEngine").innerHTML = speechEngines.map((e) => `<option value="${esc(e.id)}">${esc(e.label)}</option>`).join("")
    || '<option value="">No speech model installed</option>';
  for (const el of f.elements) {
    if (!el.name || !(el.name in cfg)) continue;
    if (el.type === "checkbox") el.checked = !!cfg[el.name];
    else el.value = cfg[el.name];
  }
  $("preset").value = "";
  $("modelList").innerHTML = [...lastLocal, ...lastModels].map((m) => `<option value="${esc(m)}">`).join("");
  $("settings").showModal();
}

async function saveSettings() {
  const f = $("settingsForm");
  const out = {};
  for (const el of f.elements) {
    if (!el.name) continue;
    if (el.type === "checkbox") out[el.name] = el.checked;
    else if (el.type === "number") out[el.name] = Number(el.value);
    else out[el.name] = el.value.trim();
  }
  await post("/api/config", out);
  checkStatus();
}

// ---------------------------------------------------------------- ⬆ M42 UI updates (updater.py)
// A newer release on GitHub: a note with what is new and an Update button; the download and the new files go in
// while the note shows how far it is; then "Restart now". Models, chats, projects and settings stay.

let updateTimer = null;
const UPDATE_RUNNING = ["downloading", "installing", "packages"];

function showUpdate(u) {
  if (!u) return;
  const v = $("appVersion");
  if (v) v.textContent = `This is M42 UI ${u.current}` + (u.git ? " (a git checkout: update it with git pull)"
    : u.available ? ` · ${u.latest} is out` : u.checked && !u.error ? " · the latest version" : u.error ? ` · ${u.error}` : "");
  const job = u.job || {};
  const running = UPDATE_RUNNING.includes(job.state);
  const finished = ["done", "rolled_back", "error"].includes(job.state);
  let later = "";
  try { later = localStorage.getItem("m42-update-later") || ""; } catch { /* (no storage: the note shows again) */ }
  let n = document.querySelector(".m42-update-note");
  if (!running && !finished && (!u.available || u.git || later === u.latest)) { if (n) n.remove(); return; }
  if (!n) {
    n = document.createElement("div");
    n.className = "m42-setup-note m42-update-note";
    document.body.appendChild(n);
  }
  n.innerHTML = "";
  const words = document.createElement("div");
  const title = document.createElement("b");
  const text = document.createElement("span");
  const buttons = document.createElement("div");
  words.className = "upd-text"; buttons.className = "upd-btns";
  words.append(title, text);
  n.append(words, buttons);
  const button = (label, ghost, fn) => {
    const b = document.createElement("button");
    b.type = "button"; b.textContent = label; if (ghost) b.className = "ghost"; b.onclick = fn;
    buttons.append(b);
  };
  if (running) {
    const pct = job.total ? Math.floor(job.done * 100 / job.total) : 0;
    title.textContent = `Updating M42 UI to ${u.latest || "the new version"}`;
    text.textContent = job.state === "downloading" ? `Downloading… ${pct}%`
      : job.state === "packages" ? "Installing the new Python packages…" : "Putting the new files in place…";
    clearTimeout(updateTimer);
    updateTimer = setTimeout(pollUpdate, 1000);
  } else if (job.state === "done" || job.state === "rolled_back") {
    title.textContent = job.state === "done" ? `M42 UI ${job.to} is installed` : `Back to M42 UI ${job.to}`;
    text.textContent = "Restart M42 UI to use it. Your chats, projects, models and settings are as they were." +
      (String(job.packages || "").startsWith("error") ? " The new Python packages did not install: run the installer again after the restart." : "");
    button("Restart now", false, restartForUpdate);
  } else if (job.state === "error") {
    title.textContent = "The update stopped";
    text.textContent = `${job.error || ""} Nothing of yours is lost; you can try again.`;
    button("Try again", false, startUpdate);
    button("Close", true, () => n.remove());
  } else {
    title.textContent = `M42 UI ${u.latest} is available (you have ${u.current})`;
    text.textContent = (u.notes || "").split("\n").filter((l) => !/^\s*#/.test(l))  // (headings left out)
      .map((l) => l.replace(/^[*\-\s]+/, "").trim()).filter(Boolean)
      .slice(0, 3).join(" · ").slice(0, 280) || "A newer version is on GitHub.";
    button("Update", false, startUpdate);
    if (u.url) button("What's new", true, () => window.open(u.url, "_blank", "noopener"));
    button("Later", true, () => { try { localStorage.setItem("m42-update-later", u.latest); } catch { /* */ } n.remove(); });
  }
}

async function pollUpdate() {
  try { showUpdate(await api("/api/update")); } catch { /* (the app restarting: the new window takes over) */ }
}

async function startUpdate() {
  try { await post("/api/update/apply"); } catch (e) { return showError(e.message); }
  pollUpdate();
}

async function restartForUpdate() {
  try { await post("/api/update/restart"); } catch (e) { return showError(e.message); }
  const n = document.querySelector(".m42-update-note");
  if (n) n.innerHTML = "<b>Restarting M42 UI…</b><span>A new window opens in a few seconds; this one closes.</span>";
  setTimeout(() => window.close(), 2500);
}

$("checkUpdate").addEventListener("click", async () => {
  $("appVersion").textContent = "Looking for a newer M42 UI on GitHub…";
  try { localStorage.removeItem("m42-update-later"); } catch { /* */ }
  await post("/api/update/check").catch((e) => showError(e.message));
  setTimeout(pollUpdate, 2500);
});
$("undoUpdate").addEventListener("click", async () => {
  if (!confirm("Go back to the M42 UI version before the last update? Your chats, projects and models stay.")) return;
  try { showUpdate(Object.assign(await api("/api/update"), { job: await post("/api/update/rollback") })); }
  catch (e) { showError(e.message); }
});

// ---------------------------------------------------------------- wiring

function autosize() {
  const t = $("input");
  // the send arrow lights up when there is something to send (words or a picture), as in Claude's box
  $("composer").classList.toggle("ready", !!t.value.trim() || !$("attachments").hidden);
  if (!t.value) { t.style.height = ""; return; }  // empty: back to one line (also when it was hidden)
  t.style.height = "auto";
  t.style.height = Math.min(t.scrollHeight, 220) + "px";
}

// ---------------------------------------------------------------- screenshots (📎 / Ctrl+V / drop)
// Shrunk to at most 1280 px before sending: the vision model reads images on the CPU, and a full-size
// screenshot only costs time.
let pendingImages = [];
const imgMeta = new Map();  // picture -> {own: a 📷 of the page itself, crop: the part the user marked}
function addImageFile(file) {
  if (!file || !/^image\/(png|jpeg|webp)$/.test(file.type) || pendingImages.length >= 3) return;
  const img = new Image();
  img.onload = () => {
    const scale = Math.min(1, 1280 / Math.max(img.width, img.height));
    const c = document.createElement("canvas");
    c.width = Math.round(img.width * scale);
    c.height = Math.round(img.height * scale);
    c.getContext("2d").drawImage(img, 0, 0, c.width, c.height);
    pendingImages.push(c.toDataURL("image/jpeg", 0.85));
    URL.revokeObjectURL(img.src);
    renderAttachments();
  };
  img.src = URL.createObjectURL(file);
}
// documents (PDF / Word / text): sent with the message; "plagiarism check" / "humanize" / any question
let pendingDocs = [];
let pendingPick = null;  // 🎯 the block of the page the user clicked on the preview: the message is a change to it
const INPUT_PLACEHOLDER = $("input").placeholder;
const DOC_EXT = /\.(pdf|docx|txt|md)$/i;
async function addDocFile(file) {
  if (!file || !DOC_EXT.test(file.name) || pendingDocs.length >= 3) return;
  if (file.size > 40e6) { showError(`${file.name} is larger than 40 MB`); return; }
  const buf = new Uint8Array(await file.arrayBuffer());
  let bin = "";
  for (let i = 0; i < buf.length; i += 32768) bin += String.fromCharCode.apply(null, buf.subarray(i, i + 32768));
  pendingDocs.push({ name: file.name, data: btoa(bin), size: file.size });
  renderAttachments();
  if (!$("input").value.trim()) $("input").placeholder = "Ask about the document, or type \"plagiarism check\" / \"humanize\"…";
}
function addFile(file) {
  if (!file) return;
  if (DOC_EXT.test(file.name)) addDocFile(file);
  else addImageFile(file);
}
function renderAttachments() {
  const box = $("attachments");
  box.hidden = !pendingImages.length && !pendingDocs.length && !pendingPick;
  autosize();  // (the send arrow: ready with a picture alone)
  box.innerHTML = "";
  if (pendingPick) {
    const item = make("div", "attachment pick", `🎯 <span>&lt;${esc(pendingPick.tag)}&gt; ${esc((pendingPick.words || "").slice(0, 50))}</span>`);
    item.title = "The part you clicked on the page: what you write now is changed in it";
    const x = make("button", "attachment-x", "✕");
    x.type = "button";
    x.title = "Remove";
    x.onclick = () => { pendingPick = null; renderAttachments(); };
    item.appendChild(x);
    box.appendChild(item);
  }
  pendingDocs.forEach((d, i) => {
    const item = make("div", "attachment doc", `📄 <span>${esc(d.name)}</span><small>${Math.max(1, Math.round(d.size / 1024))} KB</small>`);
    const x = make("button", "attachment-x", "✕");
    x.type = "button";
    x.title = "Remove";
    x.onclick = () => { pendingDocs.splice(i, 1); renderAttachments(); };
    item.appendChild(x);
    box.appendChild(item);
  });
  pendingImages.forEach((url, i) => {
    const marked = !!(imgMeta.get(url) || {}).crop;
    const item = make("div", "attachment" + (marked ? " marked" : ""), `<img src="${url}" alt="screenshot ${i + 1}">` +
      (marked ? '<span class="att-mark">marked</span>' : ""));
    item.title = "Click to see it large and mark the part to look at";
    item.querySelector("img").onclick = () => openMarker(i);
    const x = make("button", "attachment-x", "✕");
    x.type = "button";
    x.title = "Remove";
    x.onclick = () => { imgMeta.delete(url); pendingImages.splice(i, 1); renderAttachments(); };
    item.appendChild(x);
    box.appendChild(item);
  });
}
$("attachBtn").onclick = () => $("attachInput").click();
$("attachInput").onchange = (e) => { [...e.target.files].forEach(addFile); e.target.value = ""; };
$("input").addEventListener("paste", (e) => {
  const files = [...(e.clipboardData?.items || [])].filter((it) => it.kind === "file").map((it) => it.getAsFile());
  if (files.some((f) => f && f.type.startsWith("image/"))) { e.preventDefault(); files.forEach(addImageFile); }
});
// drop files anywhere in the chat (not on the project page, which has its own document card)
let dragDepth = 0;
const dropOk = (e) => [...(e.dataTransfer?.types || [])].includes("Files") && $("projectView").hidden;
document.addEventListener("dragenter", (e) => { if (dropOk(e)) { dragDepth++; document.body.classList.add("dropping"); } });
document.addEventListener("dragleave", () => { if (--dragDepth <= 0) { dragDepth = 0; document.body.classList.remove("dropping"); } });
document.addEventListener("dragover", (e) => { if (dropOk(e)) e.preventDefault(); });
document.addEventListener("drop", (e) => {
  dragDepth = 0;
  document.body.classList.remove("dropping");
  if (!dropOk(e)) return;
  e.preventDefault();
  [...e.dataTransfer.files].forEach(addFile);
});

$("composer").addEventListener("submit", (e) => {
  e.preventDefault();
  if (mic) {  // Send while the mic listens: the last words written, then sent (the user, 2026-11-13: no Stop first)
    if (!busy) stopMic(true).then(() => $("composer").requestSubmit());
    return;
  }
  const t = $("input");
  const text = t.value;
  if (window.files && files.sel && $("lineChip") && !$("lineChip").hidden) {  // ✏ lines chosen in a file: the words are for them
    if (busy || !text.trim()) return;
    const sel = files.sel, ask = text.trim();
    if (files.dirty && files.path === sel.path) { fpSave().then((ok) => ok && $("composer").requestSubmit()); return; }  // (typed changes first)
    t.value = ""; autosize();
    const shown = `✏ ${sel.path} · ${sel.start === sel.end ? `line ${sel.start}` : `lines ${sel.start}–${sel.end}`}: ${ask}`;
    clearLines();
    files.editing = true;
    send(ask, { shown, body: { message: ask, lines: { path: sel.path, start: sel.start, end: sel.end } } })
      .finally(() => { files.editing = false; if (files.open && files.path === sel.path) openCodeFile(sel.path, true); });
    return;
  }
  if (busy || (!text.trim() && !pendingImages.length && !pendingDocs.length)) return;
  t.value = "";
  autosize();
  if (pendingDocs.length) {  // documents (screenshots in the same message wait for the next one)
    const docs = pendingDocs.map((d) => ({ name: d.name, data: d.data }));
    pendingDocs = [];
    renderAttachments();
    $("input").placeholder = INPUT_PLACEHOLDER;
    send(text || "(document)", { body: { message: text.trim(), docs },
                                 shown: (text.trim() || "(document)") + "  📄 " + docs.map((d) => d.name).join(", ") });
  } else if (pendingImages.length) {  // a report with screenshots: the vision model reads them, then the fix
    const shownImgs = pendingImages;
    const metas = shownImgs.map((u) => imgMeta.get(u) || {});
    const images = shownImgs.map((u, k) => metas[k].crop || u);  // a marked picture: only the part marked
    const shots = metas.map((m) => !!m.own), marked = metas.map((m) => !!m.crop);
    const marks = metas.map((m) => (m.crop && m.shot ? { box: m.box, size: m.size, ...m.shot } : null));  // (where on the page)
    const pick = pendingPick;  // 🎯 a part clicked on the page goes with the pictures too
    pendingPick = null;
    pendingImages = [];
    imgMeta.clear();
    renderAttachments();
    send(text || "(screenshot)", { body: { message: text.trim(), images, shots, marked, marks, pick }, images: shownImgs,
                                   shown: (text.trim() || "(screenshot)") + `  🖼×${images.length}` + (pick ? `  🎯 <${pick.tag}>` : "") });
  } else if (pendingPick && text.trim()) {  // 🎯 a change to the part clicked on the page
    const pick = pendingPick;
    pendingPick = null;
    renderAttachments();
    send(text, { body: { message: text.trim(), pick }, shown: `🎯 <${pick.tag}> ${(pick.words || "").slice(0, 40)} · ${text.trim()}` });
  } else send(text);  // answer / code / build plan / circuit / picture: M42 decides from the message
});
$("input").addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey && !e.isComposing) {
    e.preventDefault();
    $("composer").requestSubmit();
  }
});
$("input").addEventListener("input", autosize);
$("stopBtn").onclick = () => post("/api/stop").catch((e) => showError(e.message));
$("newChat").onclick = async () => {  // M42 UI: a chat always belongs to a folder (no general chat)
  if (busy) return;
  if (!currentProjectId) return $("newProject").onclick();
  try { renderSession(await post("/api/sessions/new", { project_id: currentProjectId })); } catch (e) { showError(e.message); }
};
$("newProject").onclick = async () => {  // pick a folder -> project -> new chat in it
  if (busy) return;
  const btn = $("newProject");
  btn.disabled = true;
  btn.textContent = "📂 Choose a folder…";
  try {
    const r = await post("/api/projects/new", { pick: true });
    if (!r.cancelled) renderSession(r);
  } catch (e) { alert(e.message); }
  finally {
    btn.disabled = false;
    btn.textContent = "📂 Open folder";
  }
};
$("pvNewChat").onclick = async () => {
  if (busy) return;
  try { renderSession(await post("/api/sessions/new", { project_id: viewedProjectId })); }
  catch (e) { alert(e.message); }
};
$("pvAddFolder").onclick = () => projectAction("add_folder", { pick: true });
$("pvCreateFolder").onclick = () => {
  const name = prompt("New folder name\n(created inside the app's projects folder)", "");
  if (name) projectAction("add_folder", { create: name });
};
$("pvName").addEventListener("change", (e) => projectAction("update", { name: e.target.value }));
$("pvName").addEventListener("keydown", (e) => { if (e.key === "Enter") e.target.blur(); });
$("pvInstructions").addEventListener("input", saveInstructionsSoon);
$("pvDelete").onclick = async () => {
  const name = $("pvName").value;
  const ok = await projectAction("delete", {},
    `Delete the project "${name}"?\n\nIts chats are kept as general chats. Folders and files are NOT deleted.`);
  if (ok) renderSession(await api("/api/session"));
};
$("refreshTree").onclick = () => refreshTree();
$("openSettings").onclick = () => openSettings().catch((e) => showError(e.message));
$("openLearned").onclick = () => showLearned();
$("openModels").onclick = () => showModels();
$("settingsForm").addEventListener("submit", (e) => {
  if (e.submitter?.value === "save") saveSettings().catch((err) => showError(err.message));
});
$("preset").onchange = (e) => {
  if (e.target.value) $("settingsForm").elements.base_url.value = e.target.value;
};
$("modelSelect").onchange = async (e) => {
  if (e.target.value === CUSTOM_PICK) {  // not a model: open the picker, keep showing the current choice
    e.target.blur();
    fillModelSelect((await api("/api/config").catch(() => ({}))).model);
    pickCustom(null);
    return;
  }
  try {
    await post("/api/config", { model: e.target.value });
    e.target.blur();
    checkStatus();
  } catch (err) { showError(err.message); }
};
$("modelSelect").addEventListener("blur", () => { if (pendingSelect !== null) fillModelSelect(pendingSelect); });
$("modelSelect").addEventListener("mousedown", () => { if ($("modelSelect").options.length <= 2) checkStatus(); });
$("closeViewer").onclick = () => $("viewer").close();
window.addEventListener("pagehide", () => navigator.sendBeacon(`/api/bye?t=${encodeURIComponent(TOKEN)}`));

(async function init() {
  try {
    const cfg = await api("/api/config");
    fillModelSelect(cfg.model);
  } catch (e) { /* shown by status */ }
  try { renderSession(await api("/api/session")); } catch (e) { showError(e.message); }
  checkStatus();
  setInterval(() => { if (!busy) checkStatus(); }, 15000);
  $("input").focus();
})();

// ---------------------------------------------------------------- an app, not a web page (the user, 2026-11-12):
// no browser right-click menu (Inspect, View source...) and no developer-tools keys; the text boxes keep their own
// menu (copy / paste)
document.addEventListener("contextmenu", (e) => {
  if (e.target.closest("textarea, input, [contenteditable='true']")) return;
  e.preventDefault();
});
document.addEventListener("keydown", (e) => {
  const k = e.key.toLowerCase();
  if (e.key === "F12" || (e.ctrlKey && e.shiftKey && ["i", "j", "c"].includes(k)) || (e.ctrlKey && k === "u")) e.preventDefault();
});

// ---------------------------------------------------------------- ✏ mark a picture (the user, 2026-11-12: "a marker:
// the place I circle or tick is the only place to look at"): pen and box in red; Done keeps the marks on the picture
// and the part marked (with room round it) is what is sent
function openMarker(i) {
  const src = pendingImages[i];
  if (!src) return;
  const meta = imgMeta.get(src) || {};
  const img = new Image();
  img.onload = () => {
    const W = img.naturalWidth, H = img.naturalHeight;
    const wrap = make("div", "mk-overlay");
    wrap.innerHTML = `<div class="mk-box" role="dialog" aria-label="Mark the picture">
      <div class="mk-bar">
        <div class="mk-tools" role="group" aria-label="Tool">
          <button type="button" class="mk-tool on" data-t="pen" title="Pen: circle or tick the place">✏ Pen</button>
          <button type="button" class="mk-tool" data-t="box" title="Box: drag a rectangle round the place">▭ Box</button>
        </div>
        <button type="button" class="mk-btn" data-a="undo" title="Take back the last mark">↶</button>
        <button type="button" class="mk-btn" data-a="clear">Clear</button>
        <span class="mk-hint">Circle, tick or box the part M42 should look at</span>
        <button type="button" class="mk-btn" data-a="cancel">Cancel</button>
        <button type="button" class="mk-btn mk-done" data-a="done">Done</button>
      </div>
      <div class="mk-stage"><canvas class="mk-canvas"></canvas></div>
    </div>`;
    document.body.appendChild(wrap);
    const cv = wrap.querySelector(".mk-canvas"), stage = wrap.querySelector(".mk-stage");
    // (measured from the window: the stage has no size yet in the moment it is added)
    const room = [Math.max(200, stage.clientWidth || Math.min(1200, innerWidth - 48)) - 12,
                  Math.max(160, stage.clientHeight || Math.min(820, innerHeight - 48) - 64) - 12];
    const scale = Math.min(room[0] / W, room[1] / H, 1);
    cv.width = Math.round(W * scale); cv.height = Math.round(H * scale);
    const ctx = cv.getContext("2d");
    const marks = [];  // in the picture's own pixels: {t: "pen", pts: [[x, y]...]} / {t: "box", a: [x, y], b: [x, y]}
    let tool = "pen", cur = null;
    const lw = Math.max(3, Math.round(Math.max(W, H) / 220));
    function paint(c, k, list) {
      c.drawImage(img, 0, 0, W * k, H * k);
      c.strokeStyle = "#ef4444"; c.lineWidth = lw * k; c.lineCap = "round"; c.lineJoin = "round";
      for (const m of list) {
        c.beginPath();
        if (m.t === "pen") { m.pts.forEach(([x, y], n) => (n ? c.lineTo(x * k, y * k) : c.moveTo(x * k, y * k))); }
        else c.rect(Math.min(m.a[0], m.b[0]) * k, Math.min(m.a[1], m.b[1]) * k, Math.abs(m.b[0] - m.a[0]) * k, Math.abs(m.b[1] - m.a[1]) * k);
        c.stroke();
      }
    }
    const draw = () => paint(ctx, scale, cur ? [...marks, cur] : marks);
    draw();
    const at = (e) => { const r = cv.getBoundingClientRect(); return [(e.clientX - r.left) / scale, (e.clientY - r.top) / scale]; };
    cv.addEventListener("pointerdown", (e) => {
      cv.setPointerCapture(e.pointerId);
      const p = at(e);
      cur = tool === "pen" ? { t: "pen", pts: [p] } : { t: "box", a: p, b: p };
      draw();
    });
    cv.addEventListener("pointermove", (e) => {
      if (!cur) return;
      const p = at(e);
      if (cur.t === "pen") cur.pts.push(p); else cur.b = p;
      draw();
    });
    cv.addEventListener("pointerup", () => {
      if (cur && (cur.t === "pen" ? cur.pts.length > 1 : Math.abs(cur.b[0] - cur.a[0]) + Math.abs(cur.b[1] - cur.a[1]) > 6)) marks.push(cur);
      cur = null; draw();
    });
    const close = () => { wrap.remove(); document.removeEventListener("keydown", onKey); };
    function onKey(e) { if (e.key === "Escape") close(); }
    document.addEventListener("keydown", onKey);
    wrap.querySelectorAll(".mk-tool").forEach((b) => (b.onclick = () => {
      tool = b.dataset.t;
      wrap.querySelectorAll(".mk-tool").forEach((x) => x.classList.toggle("on", x === b));
    }));
    wrap.querySelector(".mk-bar").addEventListener("click", (e) => {
      const a = e.target.closest("[data-a]")?.dataset.a;
      if (a === "undo") { marks.pop(); draw(); }
      else if (a === "clear") { marks.length = 0; draw(); }
      else if (a === "cancel") close();
      else if (a === "done") {
        if (!marks.length) { close(); return; }
        const full = document.createElement("canvas");
        full.width = W; full.height = H;
        paint(full.getContext("2d"), 1, marks);
        const xs = [], ys = [];  // the part marked, with room round it (a fifth of the picture, at least)
        for (const m of marks) (m.t === "pen" ? m.pts : [m.a, m.b]).forEach(([x, y]) => { xs.push(x); ys.push(y); });
        const padX = Math.max(W * 0.1, (Math.max(...xs) - Math.min(...xs)) * 0.25);
        const padY = Math.max(H * 0.1, (Math.max(...ys) - Math.min(...ys)) * 0.25);
        const x0 = Math.max(0, Math.min(...xs) - padX), y0 = Math.max(0, Math.min(...ys) - padY);
        const x1 = Math.min(W, Math.max(...xs) + padX), y1 = Math.min(H, Math.max(...ys) + padY);
        const part = document.createElement("canvas");
        part.width = Math.round(x1 - x0); part.height = Math.round(y1 - y0);
        part.getContext("2d").drawImage(full, x0, y0, x1 - x0, y1 - y0, 0, 0, part.width, part.height);
        const annotated = full.toDataURL("image/jpeg", 0.88);
        imgMeta.delete(src);
        imgMeta.set(annotated, { own: !!meta.own, shot: meta.shot, crop: part.toDataURL("image/jpeg", 0.9),
                                 box: [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)], size: [W, H] });
        pendingImages[i] = annotated;
        renderAttachments();
        close();
        $("input").focus();
      }
    });
  };
  img.src = src;
}

// 🎤 ⌄ the speech model, chosen beside the mic (the user, 2026-11-13: "small and neat, a choice, not an icon")
$("micModel").onclick = (e) => {
  e.stopPropagation();
  document.querySelector(".sb-menu")?.remove();
  const menu = make("div", "sb-menu mic-menu");
  menu.setAttribute("role", "menu");
  menu.appendChild(make("div", "mic-menu-title", "Speech model"));
  for (const en of speechEngines) {
    const [name, about] = en.label.split(":");
    const b = make("button", "sb-menu-item" + (en.id === speechEngine ? " on" : ""),
      `<span class="mm-check">${en.id === speechEngine ? "✓" : ""}</span><span><b>${esc(name)}</b><small>${esc((about || "").trim())}</small></span>`);
    b.type = "button";
    b.setAttribute("role", "menuitemradio");
    b.setAttribute("aria-checked", String(en.id === speechEngine));
    b.onclick = async (ev) => {
      ev.stopPropagation();
      menu.remove();
      speechEngine = en.id;
      try { await post("/api/config", { speech_engine: en.id }); post("/api/speech/warm").catch(() => {}); }
      catch (err) { showError(err.message); }
    };
    menu.appendChild(b);
  }
  document.body.appendChild(menu);
  const r = $("micModel").getBoundingClientRect();
  menu.style.left = Math.max(8, Math.min(window.innerWidth - menu.offsetWidth - 8, r.right - menu.offsetWidth)) + "px";
  menu.style.top = Math.max(8, r.top - menu.offsetHeight - 6) + "px";
  setTimeout(() => document.addEventListener("click", () => menu.remove(), { once: true }));
};

/* 📁 Files beside the chat (the user, 2026-11-13: "a file manager: open a file, select from this line to that line, and
 * a prompt for just those lines, in a card"; "the files of the project I click come by themselves; folder icons, as
 * in Claude"). The project's files (the open chat's project, or the project page on screen); a file opened with its
 * line numbers; lines chosen by selecting them (or a line number, Shift + another); a small box under them asks what
 * should change; M42 writes only those lines again (agent.edit_lines), with Undo as for any change. */
var files = { open: false, path: "", sel: null, previewWasOpen: false, opened: new Set(), project: null, rootKey: "", filter: "" };

const FP_ICON = {
  chev: '<svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 6l6 6-6 6"/></svg>',
  folder: '<svg viewBox="0 0 24 24" width="17" height="17" aria-hidden="true"><path d="M3 7.2A1.7 1.7 0 0 1 4.7 5.5h4.1l2 2.2h8.5A1.7 1.7 0 0 1 21 9.4v8.4a1.7 1.7 0 0 1-1.7 1.7H4.7A1.7 1.7 0 0 1 3 17.8z" fill="currentColor" opacity=".9"/></svg>',
  folderOpen: '<svg viewBox="0 0 24 24" width="17" height="17" aria-hidden="true"><path d="M3 7.2A1.7 1.7 0 0 1 4.7 5.5h4.1l2 2.2h8.5A1.7 1.7 0 0 1 21 9.4V11H7.4a2 2 0 0 0-1.9 1.4L3 19.2z" fill="currentColor" opacity=".55"/><path d="M5.6 12.6A1.6 1.6 0 0 1 7.1 11.5h14a1 1 0 0 1 .95 1.3l-1.9 5.6a1.6 1.6 0 0 1-1.5 1.1H3.4z" fill="currentColor"/></svg>',
  file: '<svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"><path d="M6.5 3.5h7l4 4v12a1 1 0 0 1-1 1h-10a1 1 0 0 1-1-1v-15a1 1 0 0 1 1-1z"/><path d="M13.5 3.5v4h4"/></svg>',
  image: '<svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><rect x="3.5" y="4.5" width="17" height="15" rx="2"/><circle cx="9" cy="10" r="1.6"/><path d="M20.5 16l-5-5-8.5 8.5"/></svg>',
  search: '<svg viewBox="0 0 24 24" width="15" height="15" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><circle cx="11" cy="11" r="6"/><path d="M20 20l-4.2-4.2"/></svg>',
};
// each kind of file: a small coloured mark, as an editor's file list shows them
const FP_KINDS = [
  [/\.html?$/i, "html", "&lt;&gt;"], [/\.css$/i, "css", "#"], [/\.(m?js|jsx)$/i, "js", "JS"], [/\.(ts|tsx)$/i, "ts", "TS"],
  [/\.json$/i, "json", "{ }"], [/\.py$/i, "py", "PY"], [/\.(md|txt)$/i, "txt", null], [/\.(png|jpe?g|webp|gif|svg|ico|bmp)$/i, "img", null],
  [/\.(woff2?|ttf|otf)$/i, "font", "Aa"],
];
function fpFileIcon(name) {
  const k = FP_KINDS.find(([rx]) => rx.test(name));
  if (!k) return `<span class="fp-ic file">${FP_ICON.file}</span>`;
  if (k[1] === "img") return `<span class="fp-ic img">${FP_ICON.image}</span>`;
  if (!k[2]) return `<span class="fp-ic ${k[1]}">${FP_ICON.file}</span>`;
  return `<span class="fp-ic badge ${k[1]}">${k[2]}</span>`;
}
const fpQuery = (extra = "") => (files.project ? `project=${encodeURIComponent(files.project)}` + (extra ? "&" : "") : "") + extra;

function showFilesPane() {
  const app = document.querySelector(".app");
  files.previewWasOpen = !$("previewPane").hidden;
  $("previewPane").hidden = true;
  $("filesPane").hidden = false;
  app.classList.add("has-preview");
  files.open = true;
  $("filesBtn").classList.add("on");
  if (files.path) openCodeFile(files.path, true); else loadFilesTree();
}
function hideFilesPane() {
  $("filesPane").hidden = true;
  files.open = false;
  $("filesBtn").classList.remove("on");
  if (files.previewWasOpen && lastPreview) $("previewPane").hidden = false;
  else document.querySelector(".app").classList.remove("has-preview");
}

/** Another chat or project on screen: its files, by themselves (a file being read stays, if it is still the same
 * project's). project: the project page on screen (null: the open chat's). */
function syncFilesPane(project = null) {
  if (project !== undefined) files.project = project && project !== currentProjectId ? project : null;
  if (!files.open) return;
  loadFilesTree(true);
}

async function loadFilesTree(keepFile = false) {
  const body = $("fpBody");
  let data;
  try { data = await api(`/api/tree${files.project ? "?" + fpQuery() : ""}`); }
  catch (e) { body.innerHTML = `<p class="fp-note">${esc(e.message)}</p>`; return; }
  const key = (files.project || "") + "|" + data.folders.map((f) => f.path).join(";");
  const changed = key !== files.rootKey;
  files.rootKey = key;
  files.folders = data.folders;
  files.items = data.items;
  if (keepFile && files.path && !changed) return;  // the same project: the file being read stays
  files.path = ""; clearLines();
  $("fpBack").hidden = true;
  fpCrumbs();
  body.className = "fp-body";
  body.innerHTML = "";
  if (!data.folders.length) {
    body.appendChild(make("div", "fp-empty", `<span class="fp-empty-ic">${FP_ICON.folder}</span><b>No folder open</b>` +
      "<span>Open a folder (📂 Open folder), or a chat in a project: its files come here.</span>"));
    return;
  }
  const find = make("label", "fp-find", `${FP_ICON.search}<input type="search" placeholder="Filter files" aria-label="Filter files">`);
  const inp = find.querySelector("input");
  inp.value = files.filter;
  inp.oninput = () => { files.filter = inp.value; drawFileRows(list); };
  const list = make("div", "fp-tree");
  body.append(find, list);
  if (!data.items.length) { list.appendChild(make("p", "fp-note", "This folder is empty.")); return; }
  drawFileRows(list);
}

function drawFileRows(list) {
  list.innerHTML = "";
  const q = files.filter.trim().toLowerCase();
  let hideBelow = Infinity;  // inside a closed folder: its rows are not shown
  for (const it of files.items || []) {
    if (q) {  // filtering: the files whose path has the words, in a flat list
      if (it.dir || !it.path.toLowerCase().includes(q)) continue;
    } else {
      if (it.level > hideBelow) continue;
      hideBelow = Infinity;
    }
    const open = it.dir && (it.root || files.opened.has(it.path));
    const row = make("button", "fp-row" + (it.dir ? " dir" : "") + (it.path === files.path ? " on" : ""));
    row.type = "button";
    row.style.paddingLeft = `${8 + (q ? 0 : it.level) * 14}px`;
    row.title = it.path;
    row.innerHTML = (it.dir ? `<span class="fp-chev${open ? " open" : ""}">${FP_ICON.chev}</span><span class="fp-ic folder">${open ? FP_ICON.folderOpen : FP_ICON.folder}</span>`
                            : `<span class="fp-chev blank"></span>${fpFileIcon(it.name)}`) +
      `<span class="fp-name">${esc(q ? it.path : it.name)}</span>`;
    if (it.dir) {
      row.onclick = () => { if (open) files.opened.delete(it.path); else files.opened.add(it.path); drawFileRows(list); };
      if (!open) hideBelow = it.level;
    } else row.onclick = () => openCodeFile(it.path);
    list.appendChild(row);
  }
  if (!list.children.length) list.appendChild(make("p", "fp-note", q ? "No file has those words." : "This folder is empty."));
}

/** The bar's title: the project's folder, then the file's path, each part a step back. */
function fpCrumbs() {
  const t = $("fpTitle");
  t.innerHTML = "";
  const root = make("button", "fp-crumb root", `<span class="fp-ic folder">${FP_ICON.folder}</span>${esc((files.folders || []).map((f) => f.alias).join(", ") || "Files")}`);
  root.type = "button";
  root.onclick = () => { if (files.path) { clearLines(); files.path = ""; loadFilesTree(); } };
  t.appendChild(root);
  if (!files.path) return;
  const parts = files.path.split("/");
  parts.forEach((p, i) => {
    t.appendChild(make("span", "fp-sep", "›"));
    t.appendChild(make("span", "fp-crumb" + (i === parts.length - 1 ? " here" : ""), esc(p)));
  });
}

async function openCodeFile(path, keepScroll = false) {
  if (files.dirty && path !== files.path && !(await fpLeave())) return;
  const body = $("fpBody"), top = keepScroll ? body.scrollTop : 0;
  let d;
  try { d = await api(`/api/file?${fpQuery(`path=${encodeURIComponent(path)}`)}`); } catch (e) { showError(e.message); return; }
  files.path = d.path || path;
  files.dirty = false;
  $("fpBack").hidden = false;
  fpCrumbs();
  body.innerHTML = "";
  body.className = "fp-body code";
  const name = files.path.split("/").pop();
  if (d.kind || d.binary || typeof d.content !== "string") {
    const box = make("div", "fp-empty", `${fpFileIcon(name)}<b>${esc(name)}</b><span>${d.binary ? "A binary file: no text to change here." : "Not a text file: it opens in the viewer."}</span>`);
    if (d.kind) { const b = make("button", "btn small", "Open"); b.onclick = () => viewFile(path); box.appendChild(b); }
    body.appendChild(box);
    return;
  }
  // ✍ the file can be typed into, as in an editor (the user, 2026-11-13: "edit it with the keyboard like Notepad,
  // Ctrl+S or a Save button"): a see-through text box over the coloured lines, the same letters in the same places;
  // the colours and line numbers follow what is typed
  const text = d.content.replace(/\r\n?/g, "\n");
  files.crlf = /\r\n/.test(d.content);
  const head = make("div", "fp-filehead", `${fpFileIcon(name)}<b>${esc(name)}</b><span class="fp-count"></span>` +
    `<span class="fp-dirty" hidden>● Unsaved</span><button type="button" class="fp-save" disabled title="Save (Ctrl+S)">Save</button>`);
  body.appendChild(head);
  const code = make("div", "fp-code");
  const rows = make("div", "fp-rows");
  const ta = make("textarea", "fp-edit");
  ta.value = text.endsWith("\n") ? text.slice(0, -1) : text;
  files.endsNl = text.endsWith("\n");
  ta.spellcheck = false; ta.setAttribute("autocapitalize", "off"); ta.setAttribute("autocomplete", "off");
  ta.setAttribute("aria-label", `${name}: edit, Ctrl+S saves`);
  code.append(rows, ta);
  body.appendChild(code);
  const draw = () => {
    const src = ta.value, lines = src.split("\n"), coloured = HL(name, src);
    const frag = document.createDocumentFragment();
    lines.forEach((t, i) => {
      const row = make("div", "fp-line");
      row.dataset.n = i + 1;
      const ln = make("span", "fp-ln", String(i + 1)), lc = make("span", "fp-lc");
      if (coloured && coloured[i]) lc.innerHTML = coloured[i]; else lc.textContent = t || " ";
      row.append(ln, lc);
      frag.appendChild(row);
    });
    rows.replaceChildren(frag);
    head.querySelector(".fp-count").textContent = `${lines.length} lines · ${(src.length / 1024).toFixed(1)} KB`;
    if (files.sel && files.sel.path === files.path)
      rows.querySelectorAll(".fp-line").forEach((r) => r.classList.toggle("sel", +r.dataset.n >= files.sel.start && +r.dataset.n <= files.sel.end));
  };
  draw();
  let timer = 0;
  const dirty = (on) => {
    files.dirty = on;
    head.querySelector(".fp-dirty").hidden = !on;
    head.querySelector(".fp-save").disabled = !on;
  };
  ta.addEventListener("input", () => { dirty(true); clearTimeout(timer); timer = setTimeout(draw, ta.value.length > 60000 ? 250 : 60); });
  ta.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "s") { e.preventDefault(); fpSave(); }
    else if (e.key === "Tab" && !e.ctrlKey && !e.altKey) {  // two spaces, not the next button
      e.preventDefault();
      const a = ta.selectionStart, b = ta.selectionEnd;
      ta.setRangeText("  ", a, b, "end");
      ta.dispatchEvent(new Event("input"));
    }
  });
  head.querySelector(".fp-save").onclick = fpSave;
  files.editor = { ta, draw, dirty, name };
  body.scrollTop = top;
  if (files.sel && files.sel.path === files.path) markLines(files.sel.start, files.sel.end);
  else { files.sel = null; $("fpAsk").hidden = true; }
}

/** 💾 The file as typed, saved (Ctrl+S / Save); the preview of that page shown again. */
async function fpSave() {
  const ed = files.editor;
  if (!ed || !files.dirty) return true;
  let content = ed.ta.value + (files.endsNl ? "\n" : "");
  if (files.crlf) content = content.replace(/\n/g, "\r\n");
  try {
    await post("/api/file/save", { path: files.path, content, project: files.project || "" });
  } catch (e) { showError("Not saved: " + e.message); return false; }
  ed.dirty(false);
  showNote(`💾 Saved ${files.path}`);
  if (lastPreview && /\.(html?|css|js)$/i.test(files.path)) lastPreview.url && ($("ppFrame").src = lastPreview.url.split("?")[0] + "?r=" + Date.now());
  return true;
}

/** Leaving a file with changes not saved: save them, or let them go. */
async function fpLeave() {
  if (!files.dirty) return true;
  if (confirm(`${files.path} has changes that are not saved.\n\nOK: save them · Cancel: let them go`)) return fpSave();
  files.dirty = false;
  return true;
}

function markLines(a, b) {
  if (files.project) {  // a project's page on screen, no chat: a new chat in that project, then these lines (the user,
    // 2026-11-13: "Add prompt was greyed out: why can't I pick a line?"); the file stays open
    const pid = files.project;
    files.project = null;
    files.rootKey = "|" + (files.folders || []).map((f) => f.path).join(";");  // (the same folders: the file is kept)
    newChatIn({ id: pid }).then(() => markLines(a, b));
    return;
  }
  const start = Math.min(a, b), end = Math.max(a, b);
  files.sel = { path: files.path, start, end };
  document.querySelectorAll("#fpBody .fp-line").forEach((r) => r.classList.toggle("sel", +r.dataset.n >= start && +r.dataset.n <= end));
  // the ask goes in the message box itself, the lines as a chip over it (the user, 2026-11-13: "not a box of its own
  // under the file: our own box asks what should change in these lines")
  const span = start === end ? `line ${start}` : `lines ${start}–${end}`;
  let chip = $("lineChip");
  if (!chip) {
    chip = make("div", "line-chip");
    chip.id = "lineChip";
    $("composer").insertBefore(chip, $("composer").firstChild);
  }
  chip.innerHTML = `<svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M4 20h4L19 9l-4-4L4 16z"/><path d="M13.5 6.5l4 4"/></svg>` +
    `<span><b>${esc(files.path)}</b> · ${span}</span><button type="button" class="line-chip-x" title="Not these lines (Esc)" aria-label="Remove">✕</button>`;
  chip.querySelector("button").onclick = clearLines;
  chip.hidden = false;
  $("fpAsk").hidden = true;
  const input = $("input");
  input.placeholder = `What should change in ${span} of ${files.path.split("/").pop()}?`;
  input.focus();
}
function clearLines() {
  files.sel = null;
  document.querySelectorAll("#fpBody .fp-line.sel").forEach((r) => r.classList.remove("sel"));
  $("fpAsk").hidden = true;
  if ($("lineChip")) $("lineChip").hidden = true;
  $("input").placeholder = INPUT_PLACEHOLDER;
}

(function filesPaneTools() {
  $("filesBtn").onclick = () => (files.open ? hideFilesPane() : showFilesPane());
  $("fpClose").onclick = hideFilesPane;
  $("fpBack").onclick = async () => { if (!(await fpLeave())) return; clearLines(); files.path = ""; loadFilesTree(); };
  $("fpRefresh").onclick = () => (files.path ? openCodeFile(files.path, true) : (files.rootKey = "", loadFilesTree()));
  $("fpAskClose").onclick = clearLines;
  let anchor = null;
  // a line number: that line; Shift + another number: the lines between
  $("fpBody").addEventListener("click", (e) => {
    const ln = e.target.closest(".fp-ln");
    if (!ln) return;
    const n = +ln.parentElement.dataset.n;
    if (e.shiftKey && anchor) markLines(anchor, n); else { anchor = n; markLines(n, n); }
  });
  // lines selected with the mouse: the selection stays as it is (the user, 2026-11-13: "it vanished when I let go
  // of the mouse"), its lines lightly marked; a right-click on it asks "Add prompt" (as in Claude)
  const line = (node) => (node && node.nodeType === 1 ? node : node && node.parentElement)?.closest?.(".fp-line");
  const picked = () => {  // the lines the text selection starts and ends in, or null
    const ta = files.editor && files.editor.ta;
    if (ta && document.activeElement === ta && ta.selectionStart !== ta.selectionEnd) {  // (typed-in text box)
      const v = ta.value, a = ta.selectionStart, b = ta.selectionEnd;
      const end = v.slice(0, b).split("\n").length - (v[b - 1] === "\n" ? 1 : 0);
      const start = v.slice(0, a).split("\n").length;
      return { start, end: Math.max(end, start), text: v.slice(a, b) };
    }
    const s = window.getSelection();
    if (!s || s.isCollapsed) return null;
    const a = line(s.anchorNode), b = line(s.focusNode);
    if (!a || !b || !$("fpBody").contains(a) || !$("fpBody").contains(b)) return null;
    return { start: Math.min(+a.dataset.n, +b.dataset.n), end: Math.max(+a.dataset.n, +b.dataset.n), text: s.toString() };
  };
  const hint = (r) => document.querySelectorAll("#fpBody .fp-line").forEach((el) =>
    el.classList.toggle("picked", !!r && +el.dataset.n >= r.start && +el.dataset.n <= r.end));
  $("fpBody").addEventListener("mouseup", () => setTimeout(() => {
    const r = picked();
    files.picked = r;
    hint(r);
  }));
  $("fpBody").addEventListener("contextmenu", (e) => {
    const r = picked() || files.picked || (files.sel ? { ...files.sel, text: "" } : null);
    const ln = line(e.target);
    if (!ln && !r) return;
    e.preventDefault();
    e.stopPropagation();
    const at = r || { start: +ln.dataset.n, end: +ln.dataset.n, text: "" };
    const span = at.start === at.end ? `line ${at.start}` : `lines ${at.start}–${at.end}`;
    document.querySelector(".sb-menu")?.remove();
    const menu = make("div", "sb-menu fp-menu");
    menu.setAttribute("role", "menu");
    const item = (label, icon, fn, off) => {
      const b = make("button", "sb-menu-item", `<svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">${icon}</svg><span>${label}</span>`);
      b.type = "button"; b.setAttribute("role", "menuitem");
      if (off) { b.disabled = true; b.title = off; }
      b.onclick = (ev) => { ev.stopPropagation(); menu.remove(); fn(); };
      menu.appendChild(b);
    };
    item(`Add prompt · ${span}`, '<path d="M4 20h4L19 9l-4-4L4 16z"/><path d="M13.5 6.5l4 4"/>', () => { anchor = at.start; hint(null); markLines(at.start, at.end); });
    item("Copy", '<rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V6a2 2 0 0 1 2-2h9"/>', () => {
      const text = at.text || [...document.querySelectorAll("#fpBody .fp-line")].filter((el) => +el.dataset.n >= at.start && +el.dataset.n <= at.end)
        .map((el) => el.querySelector(".fp-lc").textContent).join("\n");
      navigator.clipboard?.writeText(text).then(() => showNote("Copied")).catch(() => {});
    });
    document.body.appendChild(menu);
    menu.style.left = Math.min(window.innerWidth - menu.offsetWidth - 8, e.clientX) + "px";
    menu.style.top = Math.min(window.innerHeight - menu.offsetHeight - 8, e.clientY) + "px";
    setTimeout(() => document.addEventListener("click", () => menu.remove(), { once: true }));
    document.addEventListener("keydown", function esc(ev) { if (ev.key === "Escape") { menu.remove(); document.removeEventListener("keydown", esc); } });
  });
  const input = $("fpAskInput");
  input.addEventListener("input", () => { input.style.height = "auto"; input.style.height = Math.min(input.scrollHeight, 160) + "px"; });
  const go = async () => {
    const ask = input.value.trim(), sel = files.sel;
    if (!ask || !sel) { input.focus(); return; }
    if (busy) { showError("M42 is working on a request: wait for it, then send."); return; }
    input.value = ""; input.style.height = "auto";
    $("fpAsk").hidden = true;
    const shown = `✏ ${sel.path} · ${sel.start === sel.end ? `line ${sel.start}` : `lines ${sel.start}–${sel.end}`}: ${ask}`;
    files.editing = true;
    try { await send(ask, { shown, body: { message: ask, lines: { path: sel.path, start: sel.start, end: sel.end } } }); }
    finally { files.editing = false; }
    if (files.open && files.path === sel.path) { files.sel = null; openCodeFile(sel.path, true); }
  };
  $("fpAskSend").onclick = go;
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); go(); }
    else if (e.key === "Escape") { e.preventDefault(); clearLines(); }
  });
})();

/* 🎨 Code in colour in the files panel (the user, 2026-11-13: "as Claude shows code: each kind of word its colour,
 * not one plain block"): HTML (with its <style> as CSS and its <script> as JS), CSS, JS, JSON and Python, read here
 * with no library (offline). Tokens [kind, text]; the file's lines as HTML, each piece in its span. */
const HL = (() => {
  const JS_KW = new Set(("break case catch class const continue debugger default delete do else export extends finally for " +
    "function if import in instanceof let new of return static super switch throw try typeof var void while with yield " +
    "async await get set from as").split(" "));
  const JS_LIT = new Set("true false null undefined NaN Infinity this".split(" "));
  const PY_KW = new Set(("and as assert async await break class continue def del elif else except finally for from global if " +
    "import in is lambda nonlocal not or pass raise return try while with yield").split(" "));
  const PY_LIT = new Set("True False None self cls".split(" "));
  const nextChar = (src, i) => { while (i < src.length && (src[i] === " " || src[i] === "\t")) i++; return src[i]; };

  function js(src) {
    const rx = /(\/\/[^\n]*|\/\*[\s\S]*?(?:\*\/|$))|(`(?:\\[\s\S]|[^`\\])*`?|"(?:\\.|[^"\\\n])*"?|'(?:\\.|[^'\\\n])*'?)|(\b0x[\da-fA-F]+\b|\b\d[\d_]*(?:\.\d+)?(?:[eE][+-]?\d+)?\b)|([A-Za-z_$][\w$]*)|(\s+)|([\s\S])/gy;
    const out = [];
    let m, prev = "";
    rx.lastIndex = 0;
    while ((m = rx.exec(src))) {
      const t = m[0];
      if (m[1]) out.push(["com", t]);
      else if (m[2]) out.push([nextChar(src, rx.lastIndex) === ":" && prev !== "?" ? "prop" : "str", t]);
      else if (m[3]) out.push(["num", t]);
      else if (m[4]) {
        const after = nextChar(src, rx.lastIndex);
        const kind = JS_KW.has(t) ? "kw" : JS_LIT.has(t) ? "lit" : after === "(" ? "fn" : prev === "." ? "prop"
          : /^[A-Z]/.test(t) ? "type" : after === ":" && prev !== "?" ? "prop" : "";
        out.push([kind, t]);
      } else out.push(["", t]);
      if (!m[5]) prev = t;
    }
    return out;
  }

  function css(src) {
    const rx = /(\/\*[\s\S]*?(?:\*\/|$))|("(?:\\.|[^"\\\n])*"?|'(?:\\.|[^'\\\n])*'?)|(@[\w-]+)|(#[\da-fA-F]{3,8}\b)|(-?\d*\.?\d+(?:%|[a-zA-Z]+)?)|(!important)|(-?-?[A-Za-z_][\w-]*)|([{};:,()])|(\s+)|([\s\S])/gy;
    const out = [];
    let m, depth = 0, last = "{";  // last: the last { ; : seen (a name after { or ; is a property)
    while ((m = rx.exec(src))) {
      const t = m[0];
      if (m[1]) out.push(["com", t]);
      else if (m[2]) out.push(["str", t]);
      else if (m[3]) out.push(["kw", t]);
      else if (m[4]) out.push([depth && last === ":" ? "num" : "sel", t]);
      else if (m[5]) out.push([depth && last === ":" ? "num" : "", t]);
      else if (m[6]) out.push(["kw", t]);
      else if (m[7]) {
        const after = nextChar(src, rx.lastIndex);
        if (!depth || (after !== ":" && last !== ":" && after !== "(" && /[{,]/.test(nextChar(src, rx.lastIndex) || ""))) out.push(["sel", t]);
        else if (after === "(") out.push(["fn", t]);
        else if (last !== ":" && after === ":") out.push(["prop", t]);
        else if (last === ":") out.push(["val", t]);
        else out.push(["sel", t]);
      } else if (m[8]) {
        if (t === "{") { depth++; last = "{"; } else if (t === "}") { depth = Math.max(0, depth - 1); last = "{"; }
        else if (t === ";") last = ";"; else if (t === ":" && depth) last = ":";
        out.push(["punc", t]);
      } else out.push([depth ? "" : "sel", t]);
    }
    return out;
  }

  function html(src) {
    const out = [];
    let i = 0;
    while (i < src.length) {
      if (src.startsWith("<!--", i)) {
        const e = src.indexOf("-->", i);
        const j = e < 0 ? src.length : e + 3;
        out.push(["com", src.slice(i, j)]); i = j; continue;
      }
      const open = /^<(\/?)([A-Za-z!][\w:-]*)/.exec(src.slice(i, i + 64));
      if (open) {
        out.push(["punc", "<" + open[1]]);
        out.push(["tag", open[2]]);
        i += open[0].length;
        const name = open[2].toLowerCase();
        // its attributes, up to > or />
        const rx = /(\s+)|([^\s=>\/"']+)|(=)|("[^"]*"?|'[^']*'?)|(\/?>)|([\s\S])/gy;
        rx.lastIndex = i;
        let m;
        while ((m = rx.exec(src))) {
          if (m[5]) { out.push(["punc", m[5]]); break; }
          out.push([m[2] ? "attr" : m[4] ? "str" : m[3] ? "punc" : "", m[0]]);
        }
        i = rx.lastIndex || src.length;
        if (!open[1] && (name === "style" || name === "script")) {  // the code inside, in its own colours
          const close = src.toLowerCase().indexOf(`</${name}`, i);
          const end = close < 0 ? src.length : close;
          out.push(...(name === "style" ? css : js)(src.slice(i, end)));
          i = end;
        }
        continue;
      }
      const ent = /^&[#\w]+;/.exec(src.slice(i, i + 12));
      if (ent) { out.push(["lit", ent[0]]); i += ent[0].length; continue; }
      let j = i + 1;
      while (j < src.length && src[j] !== "<" && src[j] !== "&") j++;
      out.push(["text", src.slice(i, j)]);
      i = j;
    }
    return out;
  }

  function py(src) {
    const rx = /(#[^\n]*)|("""[\s\S]*?(?:"""|$)|'''[\s\S]*?(?:'''|$)|[rbfu]{0,2}"(?:\\.|[^"\\\n])*"?|[rbfu]{0,2}'(?:\\.|[^'\\\n])*'?)|(@[\w.]+)|(\b\d[\d_]*(?:\.\d+)?\b)|([A-Za-z_]\w*)|(\s+)|([\s\S])/gy;
    const out = [];
    let m, prev = "";
    while ((m = rx.exec(src))) {
      const t = m[0];
      if (m[1]) out.push(["com", t]);
      else if (m[2]) out.push(["str", t]);
      else if (m[3]) out.push(["fn", t]);
      else if (m[4]) out.push(["num", t]);
      else if (m[5]) {
        const after = nextChar(src, rx.lastIndex);
        out.push([PY_KW.has(t) ? "kw" : PY_LIT.has(t) ? "lit" : (prev === "def" || prev === "class" || after === "(") ? "fn"
          : prev === "." ? "prop" : "", t]);
      } else out.push(["", t]);
      if (!m[6]) prev = t;
    }
    return out;
  }

  const LANGS = { html, htm: html, css, js, mjs: js, jsx: js, ts: js, json: js, py };
  /** The file's lines as HTML (each token in its colour), or null for a kind of file read as plain text. */
  return function lines(name, text) {
    const lang = LANGS[(name.split(".").pop() || "").toLowerCase()];
    if (!lang || text.length > 400000) return null;
    const rows = [""];
    for (const [kind, t] of lang(text.replace(/\r\n?/g, "\n"))) {
      t.split("\n").forEach((piece, k) => {
        if (k) rows.push("");
        if (piece) rows[rows.length - 1] += kind && kind !== "text" ? `<span class="tk-${kind}">${esc(piece)}</span>` : esc(piece);
      });
    }
    return rows;
  };
})();
// Esc in the message box: the chosen lines let go (the box asks for a message again)
$("input").addEventListener("keydown", (e) => {
  if (e.key === "Escape" && !mic && window.files && files.sel && $("lineChip") && !$("lineChip").hidden) { e.preventDefault(); clearLines(); }
});
