/*! M42 UI kit | MIT License | Copyright (c) 2026 Muthupandi (M42 TECH) | https://github.com/M42TECHY/M42-UI
 *  This file is MIT even though the M42 UI app is AGPL-3.0: a page built with M42 UI is yours to use under any licence. */
/* M42 3D (MIT, part of M42 UI): a 3D scene in a page's hero, made from a small JSON spec the page's planner (the 4B)
 * writes, with no model file needed: objects drawn in code from families of shapes (vessels, boxes, rounds, rings,
 * tubes, nature, tech, food, school, health...), a story that moves them (fill, pour, build up, assemble, orbit...),
 * extras around them (steam, sparkles, confetti...) and a card over the scene. Runs on three.js r128 (lib/three.min.js).
 *
 *   <div class="m42-3d" data-m42-3d='{"objects":["cup","coffee_beans"],"story":"pour","liquid":"coffee",
 *        "extras":["steam"],"card":{"title":"Your cappuccino","states":["Brewing","Enjoy"],"detail":"92°C · 180 ml"}}'></div>
 *
 * The page's own colours (--m42-accent, --m42-accent-2, --m42-accent-3) colour the scene. A user's model file:
 * "model": "models/statue.glb" (needs lib/GLTFLoader.js) or ".stl" (lib/STLLoader.js).
 */
(function () {
  "use strict";
  if (typeof THREE === "undefined") return;
  const T = THREE;
  const TAU = Math.PI * 2;

  // ---------------------------------------------------------------- colours and materials
  function cssColor(name) {
    // the colour a CSS variable really is (--m42-accent is often var(--bs-primary, ...)): read through a probe
    const raw = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    if (!raw) return "";
    const pr = document.createElement("i"); pr.style.cssText = "display:none;color:" + `var(${name})`;
    document.body.appendChild(pr); const c = getComputedStyle(pr).color; pr.remove();
    const m = c && c.match(/rgba?\(\s*(\d+)[,\s]+(\d+)[,\s]+(\d+)/);
    return m ? "#" + [m[1], m[2], m[3]].map((x) => (+x).toString(16).padStart(2, "0")).join("") : "";
  }
  function hsl(c) { const o = {}; new T.Color(c).getHSL(o); return o; }
  // a colour the scene can wear: not near black, white or grey (a page whose accent is #18181b gave a grey scene)
  const vivid = (c) => { if (!c) return false; const o = hsl(c); return o.s > 0.3 && o.l > 0.22 && o.l < 0.78; };
  const hueGap = (a, b) => { const d = Math.abs(hsl(a).h - hsl(b).h); return Math.min(d, 1 - d); };
  function lightPage() {
    for (const n of [document.querySelector(".m42-hero"), document.body, document.documentElement]) {
      if (!n) continue; const m = getComputedStyle(n).backgroundColor.match(/rgba?\(\s*(\d+)[,\s]+(\d+)[,\s]+(\d+)(?:[,\s/]+([\d.]+))?/);
      if (m && (m[4] === undefined || +m[4] > 0.5)) return (0.2126 * m[1] + 0.7152 * m[2] + 0.0722 * m[3]) / 255 > 0.55;
    }
    return true;
  }
  // the page's own dark brand colour (a navy #2c3e50, a bottle green) for the dark parts; else the accent made deep
  function deepOf(given, accent) {
    const own = given.find((c) => { if (!c) return false; const o = hsl(c); return o.s > 0.15 && o.l > 0.08 && o.l < 0.4; });
    return own ? new T.Color(own) : new T.Color().setHSL(hsl(accent).h, Math.min(0.7, hsl(accent).s), 0.16);
  }
  function palette(spec) {
    const given = ((spec && spec.colors) || []).concat(["--m42-accent", "--m42-accent-2", "--m42-accent-3", "--bs-primary"].map(cssColor));
    const picks = [];
    for (const c of given) if (vivid(c) && picks.every((x) => hueGap(x, c) > 0.06)) picks.push(c);
    // too few of its own: harmonious ones from the first (a warm one beside a cool one, then a third between)
    const base = picks[0] || "#5b5bf0";
    const shift = (c, dh, l) => { const o = hsl(c); return "#" + new T.Color().setHSL((o.h + dh + 1) % 1, Math.max(0.55, Math.min(0.85, o.s)), l ?? Math.min(0.62, Math.max(0.48, o.l))).getHexString(); };
    const accent = base;
    const accent2 = picks[1] || shift(base, hsl(base).h > 0.45 && hsl(base).h < 0.8 ? 0.45 : 0.5, 0.6);
    const accent3 = picks[2] || shift(base, -0.12, 0.5);
    return {
      main: new T.Color(accent), second: new T.Color(accent2), third: new T.Color(accent3),
      light: new T.Color("#fbf8f3"), white: new T.Color("#ffffff"), dark: new T.Color("#23262d"), ink: new T.Color("#33363d"),
      wood: new T.Color("#c99a68"), woodDark: new T.Color("#8a5a36"), metal: new T.Color("#c9ced6"), steel: new T.Color("#8d949e"),
      gold: new T.Color("#e5b54a"), silver: new T.Color("#d9dde3"), copper: new T.Color("#c8794a"), glass: new T.Color("#dff3ff"),
      green: new T.Color("#5fb35a"), leaf: new T.Color("#4f9d4a"), grass: new T.Color("#7cc56b"), soil: new T.Color("#7a5232"),
      sky: new T.Color("#8fd0ff"), water: new T.Color("#4db6e8"), red: new T.Color("#e5484d"), orange: new T.Color("#f08a3c"),
      yellow: new T.Color("#f5c84b"), pink: new T.Color("#f48fb1"), purple: new T.Color("#9b7bf0"), brown: new T.Color("#7b4a2a"),
      deep: deepOf(given, accent), lightBg: lightPage(), cream: new T.Color("#f3e3c8"), chocolate: new T.Color("#4a2a18"), rubber: new T.Color("#2b2d31"), skin: new T.Color("#e9b994"),
    };
  }
  const LIQUIDS = { coffee: "#3b2314", tea: "#a8642a", milk: "#f7f2ea", juice: "#f5a524", orange: "#f5a524", water: "#7fc8f0",
    wine: "#7a1430", honey: "#e0a020", paint: null, soup: "#d07a2a", chocolate: "#4a2a18", lemonade: "#f3e27a", milkshake: "#f4b6c8",
    oil: "#d9b23a", potion: "#8e5cf0", fuel: "#e0b030", beer: "#e9a32a", soda: "#5a2a1a", smoothie: "#e46a8a" };

  function makeMats(p) {
    const cache = new Map();
    return function mat(color, o = {}) {
      const col = (color instanceof T.Color ? color.clone() : new T.Color(color)).convertSRGBToLinear();
      const key = col.getHexString() + JSON.stringify(o);
      if (cache.has(key)) return cache.get(key);
      const m = new T.MeshPhysicalMaterial({
        color: col, roughness: o.rough ?? 0.42, metalness: o.metal ?? 0.05, clearcoat: o.clear ?? 0.25, clearcoatRoughness: 0.4,
        transparent: !!o.opacity && o.opacity < 1, opacity: o.opacity ?? 1, side: o.side ?? T.FrontSide,
        emissive: o.glow ? col : new T.Color(0), emissiveIntensity: o.glow || 0, map: o.map || null,
        transmission: o.glass ? 0.6 : 0, flatShading: !!o.flat,
      });
      if (o.map) m.color = new T.Color("#ffffff");
      if (o.envI !== undefined) m.envMapIntensity = o.envI;
      cache.set(key, m);
      return m;
    };
  }

  // ---------------------------------------------------------------- geometry helpers
  const V2 = (x, y) => new T.Vector2(x, y);
  const V3 = (x, y, z) => new T.Vector3(x, y, z);
  function smooth2(pts, n = 40) {  // a profile through these points, sampled finely (no dents)
    if (pts.length < 3) return pts.map(([x, y]) => V2(x, y));
    return new T.SplineCurve(pts.map(([x, y]) => V2(x, y))).getPoints(n);
  }
  function lathe(pts, m, seg = 72, sm = true) {
    const g = new T.LatheGeometry(sm ? smooth2(pts, Math.max(24, pts.length * 8)) : pts.map(([x, y]) => V2(x, y)), seg);
    return mesh(g, m);
  }
  function mesh(g, m) { const x = new T.Mesh(g, m); x.castShadow = true; x.receiveShadow = true; return x; }
  function rbox(w, h, d, r, m) {  // a rounded box: a rounded rectangle pushed out with rounded edges
    r = Math.min(r, w / 2 - 1e-3, h / 2 - 1e-3, d / 2 - 1e-3);
    const s = new T.Shape(), x = -w / 2 + r, y = -h / 2 + r, W = w - 2 * r, H = h - 2 * r;
    s.moveTo(x, y - r); s.lineTo(x + W, y - r); s.quadraticCurveTo(x + W + r, y - r, x + W + r, y);
    s.lineTo(x + W + r, y + H); s.quadraticCurveTo(x + W + r, y + H + r, x + W, y + H + r);
    s.lineTo(x, y + H + r); s.quadraticCurveTo(x - r, y + H + r, x - r, y + H); s.lineTo(x - r, y); s.quadraticCurveTo(x - r, y - r, x, y - r);
    const g = new T.ExtrudeGeometry(s, { depth: Math.max(1e-3, d - 2 * r), bevelEnabled: r > 0.001, bevelSize: r * 0.9, bevelThickness: r,
      bevelSegments: 4, curveSegments: 8 });
    g.translate(0, 0, -(d - 2 * r) / 2);
    return mesh(g, m);
  }
  const box = (w, h, d, m) => mesh(new T.BoxGeometry(w, h, d), m);
  const cyl = (rt, rb, h, m, seg = 48) => mesh(new T.CylinderGeometry(rt, rb, h, seg), m);
  const sph = (r, m, ws = 48, hs = 32) => mesh(new T.SphereGeometry(r, ws, hs), m);
  const tor = (R, r, m, arc = TAU, ts = 24, rs = 72) => mesh(new T.TorusGeometry(R, r, ts, rs, arc), m);
  const cone = (r, h, m, seg = 48) => mesh(new T.ConeGeometry(r, h, seg), m);
  function tube(pts, r, m, closed = false, seg = 96, rs = 16) {
    const c = new T.CatmullRomCurve3(pts.map(([x, y, z]) => V3(x, y, z || 0)), closed);
    return mesh(new T.TubeGeometry(c, seg, r, rs, closed), m);
  }
  function extrude(shape, depth, m, bevel = 0.02) {
    const g = new T.ExtrudeGeometry(shape, { depth, bevelEnabled: bevel > 0, bevelSize: bevel, bevelThickness: bevel, bevelSegments: 3,
      curveSegments: 24 });
    g.translate(0, 0, -depth / 2);
    return mesh(g, m);
  }
  function at(o, x = 0, y = 0, z = 0, rx = 0, ry = 0, rz = 0, s = 1) {
    o.position.set(x, y, z); o.rotation.set(rx, ry, rz); if (s !== 1) o.scale.setScalar(s); return o;
  }
  function group(...kids) { const g = new T.Group(); kids.flat().forEach((k) => k && g.add(k)); return g; }
  function canvasTex(draw, w = 256, h = 256) {
    const c = document.createElement("canvas"); c.width = w; c.height = h; draw(c.getContext("2d"), w, h);
    const t = new T.CanvasTexture(c); t.encoding = T.sRGBEncoding; t.anisotropy = 4; return t;
  }
  function textTex(text, bg, fg, w = 512, h = 256, font = "700 120px Segoe UI, sans-serif") {
    return canvasTex((g) => {
      g.fillStyle = bg; g.fillRect(0, 0, w, h); g.fillStyle = fg; g.textAlign = "center"; g.textBaseline = "middle";
      let size = parseInt(font.match(/(\d+)px/)[1], 10);
      do { g.font = font.replace(/\d+px/, size + "px"); size -= 4; } while (g.measureText(text).width > w * 0.86 && size > 20);
      g.fillText(text, w / 2, h / 2 + 4);
    }, w, h);
  }
  const hexStr = (c) => "#" + c.getHexString();

  // ---------------------------------------------------------------- vessels: turned shapes that can hold a liquid
  // [outer profile (r, y) from the bottom up], wall, extras. The inside follows the outside, "wall" in; fill: true
  const VESSELS = {
    cup: { p: [[0, 0.1], [0.5, 0.1], [0.55, 0.3], [0.68, 0.75], [0.78, 1.05]], wall: 0.05, handle: "side", saucer: true, band: true },
    mug: { p: [[0, 0], [0.62, 0], [0.64, 0.4], [0.65, 1.0], [0.66, 1.25]], wall: 0.06, handle: "big", band: true },
    tea_glass: { p: [[0, 0], [0.4, 0], [0.42, 0.3], [0.5, 0.9], [0.56, 1.25]], wall: 0.03, glass: true },
    glass: { p: [[0, 0], [0.48, 0], [0.5, 0.5], [0.56, 1.4]], wall: 0.03, glass: true },
    wine_glass: { p: [[0, 0], [0.45, 0], [0.42, 0.04], [0.05, 0.1], [0.05, 0.7], [0.3, 0.8], [0.48, 1.1], [0.42, 1.5]], wall: 0.025, glass: true, fillFrom: 0.78 },
    cocktail_glass: { p: [[0, 0], [0.4, 0], [0.05, 0.06], [0.05, 0.75], [0.7, 1.3]], wall: 0.02, glass: true, fillFrom: 0.78 },
    bottle: { p: [[0, 0], [0.42, 0], [0.45, 0.1], [0.45, 1.05], [0.38, 1.3], [0.16, 1.55], [0.15, 1.95], [0.17, 2.0]], wall: 0.03, glass: true, cap: true, label: true },
    wine_bottle: { p: [[0, 0], [0.38, 0], [0.4, 0.1], [0.4, 1.3], [0.32, 1.55], [0.13, 1.75], [0.12, 2.25]], wall: 0.03, dark: true, cap: true, label: true },
    milk_bottle: { p: [[0, 0], [0.45, 0], [0.48, 0.15], [0.48, 1.0], [0.3, 1.35], [0.27, 1.6], [0.29, 1.65]], wall: 0.03, glass: true, cap: true },
    jar: { p: [[0, 0], [0.55, 0], [0.6, 0.1], [0.62, 0.9], [0.5, 1.05], [0.5, 1.15]], wall: 0.03, glass: true, lid: true, label: true },
    honey_jar: { p: [[0, 0], [0.5, 0], [0.62, 0.35], [0.6, 0.85], [0.42, 1.0], [0.42, 1.1]], wall: 0.03, glass: true, lid: true, liquid: "honey" },
    vase: { p: [[0, 0], [0.32, 0], [0.55, 0.45], [0.48, 0.95], [0.26, 1.35], [0.3, 1.7], [0.38, 1.85]], wall: 0.04 },
    bowl: { p: [[0, 0], [0.4, 0], [0.62, 0.15], [0.85, 0.5], [0.95, 0.62]], wall: 0.05 },
    plant_pot: { p: [[0, 0], [0.5, 0], [0.56, 0.08], [0.7, 0.85], [0.78, 0.9], [0.78, 1.02]], wall: 0.05, soil: true },
    pot: { p: [[0, 0], [0.75, 0], [0.8, 0.08], [0.82, 0.85], [0.86, 0.9]], wall: 0.05, handles: true },
    bucket: { p: [[0, 0], [0.55, 0], [0.62, 0.1], [0.78, 1.15]], wall: 0.03, handle: "bail", metal: true },
    paint_can: { p: [[0, 0], [0.62, 0], [0.62, 1.05], [0.6, 1.1]], wall: 0.03, handle: "bail", metal: true, label: true, liquid: "paint" },
    tank: { p: [[0, 0], [0.9, 0], [0.95, 0.1], [0.95, 1.6], [0.7, 1.85], [0.2, 1.9]], wall: 0.04, glass: true, liquid: "water" },
    beaker: { p: [[0, 0], [0.5, 0], [0.52, 0.05], [0.52, 1.3], [0.58, 1.35]], wall: 0.025, glass: true, marks: true, liquid: "potion" },
    flask: { p: [[0, 0], [0.62, 0], [0.66, 0.12], [0.5, 0.65], [0.16, 1.1], [0.16, 1.55], [0.2, 1.6]], wall: 0.025, glass: true, liquid: "potion" },
    test_tube: { p: [[0, 0], [0.08, 0.01], [0.14, 0.08], [0.15, 0.2], [0.15, 1.5]], wall: 0.012, glass: true, liquid: "potion" },
    perfume: { p: [[0, 0], [0.55, 0], [0.6, 0.08], [0.6, 0.85], [0.45, 1.0], [0.12, 1.05], [0.12, 1.15]], wall: 0.04, glass: true, cap: "cube", liquid: "honey" },
    soda_can: { p: [[0, 0], [0.38, 0], [0.45, 0.08], [0.46, 1.2], [0.38, 1.32], [0.36, 1.34]], wall: 0.02, metal: true, label: true, closed: true },
    shaker: { p: [[0, 0], [0.45, 0], [0.5, 0.1], [0.55, 1.1], [0.5, 1.25], [0.3, 1.5], [0.2, 1.6]], wall: 0.03, metal: true, closed: true },
    blender: { p: [[0, 0.55], [0.38, 0.55], [0.45, 0.9], [0.62, 1.9], [0.62, 2.0]], wall: 0.03, glass: true, base: true, liquid: "smoothie" },
    ice_bucket: { p: [[0, 0], [0.6, 0], [0.72, 0.9], [0.78, 1.0]], wall: 0.03, metal: true },
    candle_jar: { p: [[0, 0], [0.5, 0], [0.52, 0.9], [0.5, 0.95]], wall: 0.03, glass: true, liquid: "cream", flame: true },
    cauldron: { p: [[0, 0.15], [0.3, 0.05], [0.8, 0.35], [0.88, 0.75], [0.7, 1.05], [0.74, 1.12]], wall: 0.05, dark: true, liquid: "potion" },
  };
  function buildVessel(name, p, mat, spec) {
    const v = VESSELS[name];
    const outer = v.p;
    const glassy = v.glass, metal = v.metal;
    const body = glassy ? mat(p.glass, { rough: 0.05, opacity: 0.32, side: T.DoubleSide, clear: 1 })
      : metal ? mat(p.metal, { rough: 0.25, metal: 0.85, side: T.DoubleSide })
        : v.dark ? mat(p.dark, { rough: 0.3, side: T.DoubleSide }) : mat(p.light, { rough: 0.32, side: T.DoubleSide, clear: 0.6 });
    const top = outer[outer.length - 1][1];
    const rAt = (y) => {  // the outside's radius at a height (straight lines between the points)
      for (let i = 1; i < outer.length; i++) {
        const [r0, y0] = outer[i - 1], [r1, y1] = outer[i];
        if (y <= y1 || i === outer.length - 1) return y1 === y0 ? r1 : r0 + (r1 - r0) * Math.max(0, Math.min(1, (y - y0) / (y1 - y0)));
      }
      return outer[outer.length - 1][0];
    };
    const base = v.fillFrom ?? (outer[0][1] + v.wall * 1.5);
    const inner = [];
    for (let i = 0; i <= 24; i++) { const y = base + (top - base) * i / 24; inner.push([Math.max(0.01, rAt(y) - v.wall), y]); }
    const prof = [...outer, ...inner.slice().reverse().filter((q, i) => i > 0), [0, base]];
    const g = group(lathe(v.closed ? [...outer, [0, top]] : prof, body, 72, false));
    g.userData.parts = [g.children[0]];
    const add = (o) => { g.add(o); g.userData.parts.push(o); return o; };
    const R = outer.reduce((a, q) => Math.max(a, q[0]), 0);
    if (v.band) add(lathe([[rAt(top * 0.62) + 0.006, top * 0.62], [rAt(top * 0.74) + 0.006, top * 0.74]], mat(p.main, { side: T.DoubleSide }), 72, false));
    if (v.handle === "side" || v.handle === "big") {
      const big = v.handle === "big";
      add(at(tor(big ? 0.34 : 0.28, big ? 0.07 : 0.055, body, Math.PI * 1.15), rAt(top * 0.6) * 0.93, top * 0.58, 0, 0, 0, -Math.PI * 0.57));
    }
    if (v.handle === "bail") add(at(tor(R * 0.98, 0.02, mat(p.steel, { metal: 0.9, rough: 0.3 }), Math.PI), 0, top, 0, 0, 0, 0));
    if (v.handles) for (const s of [-1, 1]) add(at(tor(0.16, 0.05, body, Math.PI), s * (R + 0.1), top * 0.8, 0, 0, 0, s * Math.PI / 2));
    if (v.saucer) add(lathe([[0, 0.0], [0.9, 0.0], [1.35, 0.08], [1.42, 0.14], [1.36, 0.15], [0.92, 0.08], [0, 0.08]], mat(p.light, { rough: 0.3, clear: 0.6 })));
    if (v.cap) {
      const r = rAt(top) + 0.015;
      add(v.cap === "cube" ? at(rbox(r * 2.6, 0.35, r * 2.6, 0.06, mat(p.gold, { metal: 0.8, rough: 0.25 })), 0, top + 0.17)
        : at(cyl(r, r, 0.16, mat(p.main, { rough: 0.35 })), 0, top + 0.06));
    }
    if (v.lid) add(at(cyl(rAt(top) + 0.04, rAt(top) + 0.04, 0.16, mat(p.main, { rough: 0.35 })), 0, top + 0.06));
    if (v.label) {
      const y0 = top * 0.3, y1 = top * 0.62, r = rAt((y0 + y1) / 2) + 0.008;
      const tex = textTex(spec.label || spec.brand || "", hexStr(p.main), "#ffffff", 512, 256);
      const lab = mesh(new T.CylinderGeometry(r, r, y1 - y0, 64, 1, true, -Math.PI * 0.55, Math.PI * 1.1), mat("#ffffff", { map: tex, rough: 0.5 }));
      add(at(lab, 0, (y0 + y1) / 2));
    }
    if (v.marks) for (let i = 1; i < 5; i++) add(at(tor(rAt(top * i / 5) + 0.004, 0.006, mat(p.white, { rough: 0.4 }), Math.PI / 3), 0, top * i / 5, 0, Math.PI / 2, 0, Math.PI * 0.85));
    if (v.base) add(at(rbox(1.05, 0.55, 1.05, 0.12, mat(p.dark, { rough: 0.35 })), 0, 0.27));
    if (v.soil) add(at(cyl(rAt(top * 0.9) - v.wall, rAt(top * 0.9) - v.wall, 0.04, mat(p.soil, { rough: 0.9 })), 0, top * 0.9));
    if (v.flame) add(flame(p, mat, 0, top * 0.95, 0));
    g.userData.vessel = { inner: (y) => Math.max(0.01, rAt(y) - v.wall - 0.004), bottom: base, top: top - 0.04, liquid: v.liquid };
    g.userData.top = top;
    return g;
  }
  function flame(p, mat, x, y, z) {
    const f = lathe([[0, 0], [0.06, 0.06], [0.07, 0.14], [0.03, 0.28], [0, 0.34]], mat(p.yellow, { glow: 1.3, rough: 0.6 }), 24);
    f.userData.flicker = true; return at(f, x, y, z);
  }

  // ---------------------------------------------------------------- the catalog: every object by name (families below)
  const MAKERS = {};
  const family = (names, make) => names.forEach((n) => { MAKERS[n] = (p, mat, spec) => make(n, p, mat, spec); });
  family(Object.keys(VESSELS), buildVessel);

  window.M42_3D_INTERNAL = { T, palette, makeMats, lathe, mesh, rbox, box, cyl, sph, tor, cone, tube, extrude, at, group, canvasTex,
    textTex, hexStr, family, MAKERS, LIQUIDS, flame, V2, V3, smooth2 };
})();

/* ---- families: boxes, devices, buildings, furniture, school and office things ---- */
(function () {
  "use strict";
  const K = window.M42_3D_INTERNAL; if (!K) return;
  const { T, rbox, box, cyl, sph, tor, cone, tube, extrude, at, group, canvasTex, textTex, hexStr, family, lathe } = K;
  const TAU = Math.PI * 2;
  const parts = (g) => { g.userData.parts = g.children.slice(); return g; };
  const screenTex = (p, kind = "app") => canvasTex((g, w, h) => {
    const grd = g.createLinearGradient(0, 0, w, h); grd.addColorStop(0, hexStr(p.main)); grd.addColorStop(1, hexStr(p.second));
    g.fillStyle = grd; g.fillRect(0, 0, w, h);
    g.fillStyle = "rgba(255,255,255,.9)";
    if (kind === "chart") { for (let i = 0; i < 6; i++) { const bh = 30 + ((i * 53) % 90); g.fillRect(30 + i * 36, h - 30 - bh, 22, bh); } }
    else { g.globalAlpha = .9; g.fillRect(24, 28, w - 48, 26); g.globalAlpha = .55; for (let i = 0; i < 4; i++) g.fillRect(24, 74 + i * 34, (w - 48) * (0.5 + 0.12 * i), 18); }
  }, 256, 320);

  // books: a cover, pages, a spine colour; stack / open book
  function book(p, mat, col, w = 1.3, h = 0.22, d = 0.95) {
    const g = group(
      at(rbox(w, h, d, 0.03, mat(col, { rough: 0.5 })), 0, h / 2),
      at(box(w - 0.08, h - 0.07, d - 0.03, mat(p.cream, { rough: 0.8 })), 0.03, h / 2)
    );
    return g;
  }
  family(["book"], (n, p, mat) => parts(group(at(book(p, mat, p.main), 0, 0, 0, 0, 0.2, 0))));
  family(["book_stack", "books"], (n, p, mat) => {
    const cols = [p.main, p.second, p.third, p.red, p.main];
    const g = group(); let y = 0;
    cols.forEach((c, i) => { const b = book(p, mat, c, 1.3 - i * 0.06, 0.2 + (i % 2) * 0.05, 0.95 - i * 0.03); at(b, (i % 2 ? 0.06 : -0.05), y, 0, 0, (i - 2) * 0.12, 0); y += 0.21 + (i % 2) * 0.05; g.add(b); });
    return parts(g);
  });
  family(["open_book", "notebook"], (n, p, mat) => {
    const page = (sgn) => { const g = new T.Group(); for (let i = 0; i < 3; i++) g.add(at(rbox(1.05, 0.03, 1.4, 0.01, mat(p.cream, { rough: 0.85 })), sgn * 0.54, 0.09 + i * 0.03, 0, 0, 0, sgn * (0.1 - i * 0.025))); return g; };
    return parts(group(at(rbox(2.3, 0.06, 1.5, 0.03, mat(p.main, { rough: 0.5 })), 0, 0.03), page(-1), page(1),
      at(box(0.82, 0.005, 0.05, mat(p.ink)), -0.55, 0.2, -0.3), at(box(0.7, 0.005, 0.05, mat(p.ink)), -0.6, 0.2, -0.1), at(box(0.8, 0.005, 0.05, mat(p.ink)), 0.55, 0.2, -0.3)));
  });
  family(["phone", "smartphone", "app"], (n, p, mat) => parts(group(
    at(rbox(0.9, 1.8, 0.1, 0.12, mat(p.dark, { rough: 0.2, metal: 0.4 })), 0, 0.9),
    at(K.mesh(new T.PlaneGeometry(0.8, 1.68), mat("#fff", { map: screenTex(p), rough: 0.25 })), 0, 0.9, 0.052),
  )));
  family(["tablet"], (n, p, mat) => parts(group(
    at(rbox(1.5, 2.0, 0.08, 0.1, mat(p.silver, { metal: 0.6, rough: 0.3 })), 0, 1.0),
    at(K.mesh(new T.PlaneGeometry(1.38, 1.86), mat("#fff", { map: screenTex(p, "chart") })), 0, 1.0, 0.042))));
  family(["laptop"], (n, p, mat) => {
    const lid = group(at(rbox(2.0, 1.3, 0.05, 0.05, mat(p.silver, { metal: 0.6, rough: 0.3 })), 0, 0.65),
      at(K.mesh(new T.PlaneGeometry(1.86, 1.16), mat("#fff", { map: screenTex(p, "chart") })), 0, 0.65, 0.027));
    at(lid, 0, 0.05, -0.62, -0.25, 0, 0);
    return parts(group(at(rbox(2.0, 0.08, 1.3, 0.05, mat(p.silver, { metal: 0.6, rough: 0.3 })), 0, 0.04), at(box(1.6, 0.01, 0.7, mat(p.dark)), 0, 0.085, 0.05), lid));
  });
  family(["monitor", "computer", "tv"], (n, p, mat) => parts(group(
    at(rbox(2.4, 1.45, 0.08, 0.05, mat(p.dark, { rough: 0.3 })), 0, 1.25),
    at(K.mesh(new T.PlaneGeometry(2.28, 1.33), mat("#fff", { map: screenTex(p, n === "tv" ? "app" : "chart") })), 0, 1.25, 0.042),
    at(cyl(0.06, 0.08, 0.5, mat(p.steel, { metal: 0.8 })), 0, 0.3), at(rbox(0.8, 0.06, 0.5, 0.03, mat(p.steel, { metal: 0.8 })), 0, 0.03))));
  family(["speaker"], (n, p, mat) => parts(group(at(rbox(0.9, 1.4, 0.8, 0.12, mat(p.dark)), 0, 0.7),
    at(cyl(0.3, 0.3, 0.05, mat(p.ink, { rough: 0.6 })), 0, 0.5, 0.41, Math.PI / 2), at(cyl(0.14, 0.14, 0.05, mat(p.ink)), 0, 1.05, 0.41, Math.PI / 2))));
  family(["headphones"], (n, p, mat) => parts(group(at(tor(0.75, 0.07, mat(p.dark), Math.PI), 0, 0.85),
    ...[-1, 1].map((s) => at(rbox(0.32, 0.55, 0.3, 0.12, mat(p.main)), s * 0.75, 0.6, 0)))));
  family(["camera"], (n, p, mat) => parts(group(at(rbox(1.5, 0.95, 0.7, 0.12, mat(p.dark)), 0, 0.5),
    at(cyl(0.34, 0.38, 0.45, mat(p.ink, { rough: 0.3 })), 0, 0.48, 0.5, Math.PI / 2), at(cyl(0.25, 0.25, 0.05, mat(p.sky, { rough: 0.05, clear: 1 })), 0, 0.48, 0.73, Math.PI / 2),
    at(rbox(0.4, 0.18, 0.3, 0.05, mat(p.main)), -0.45, 1.0, 0))));
  family(["game_controller"], (n, p, mat) => parts(group(at(rbox(1.6, 0.35, 0.9, 0.17, mat(p.dark)), 0, 0.2),
    ...[-1, 1].map((s) => at(sph(0.32, mat(p.dark)), s * 0.62, 0.15, 0.25)), at(sph(0.09, mat(p.red)), 0.42, 0.4, -0.05), at(sph(0.09, mat(p.green)), 0.6, 0.4, 0.08),
    at(rbox(0.32, 0.08, 0.1, 0.03, mat(p.steel)), -0.5, 0.4, 0), at(rbox(0.1, 0.08, 0.32, 0.03, mat(p.steel)), -0.5, 0.4, 0))));
  family(["chip", "cpu", "processor"], (n, p, mat) => {
    const g = group(at(rbox(1.4, 0.18, 1.4, 0.04, mat(p.dark)), 0, 0.09), at(rbox(0.8, 0.08, 0.8, 0.03, mat(p.silver, { metal: 0.8 })), 0, 0.22));
    for (let i = 0; i < 6; i++) for (const s of [-1, 1]) { g.add(at(box(0.08, 0.04, 0.25, mat(p.gold, { metal: 0.9 })), -0.55 + i * 0.22, 0.06, s * 0.8)); g.add(at(box(0.25, 0.04, 0.08, mat(p.gold, { metal: 0.9 })), s * 0.8, 0.06, -0.55 + i * 0.22)); }
    return parts(g);
  });
  family(["server", "server_rack", "database"], (n, p, mat) => {
    const g = group();
    for (let i = 0; i < 4; i++) { g.add(at(rbox(1.3, 0.42, 1.0, 0.06, mat(p.dark)), 0, 0.22 + i * 0.46)); g.add(at(sph(0.04, mat(i % 2 ? p.green : p.main, { glow: 1.5 }), 12, 8), 0.5, 0.22 + i * 0.46, 0.51)); }
    return parts(g);
  });
  family(["router", "wifi"], (n, p, mat) => parts(group(at(rbox(1.4, 0.3, 0.9, 0.1, mat(p.white)), 0, 0.15),
    ...[-0.45, 0, 0.45].map((x) => at(cyl(0.04, 0.04, 0.8, mat(p.dark)), x, 0.65, -0.35, -0.15)),
    ...[0, 1, 2].map((i) => at(tor(0.18 + i * 0.16, 0.025, mat(p.main, { glow: 0.4 }), Math.PI / 2), 0, 0.9, 0, 0, 0, Math.PI / 4)))));
  family(["battery"], (n, p, mat) => parts(group(at(rbox(0.8, 1.4, 0.8, 0.14, mat(p.dark)), 0, 0.7), at(cyl(0.12, 0.12, 0.12, mat(p.metal, { metal: 0.9 })), 0, 1.45),
    ...[0, 1, 2].map((i) => at(rbox(0.6, 0.32, 0.05, 0.05, mat(p.green, { glow: 0.5 })), 0, 0.3 + i * 0.4, 0.4)))));
  family(["solar_panel"], (n, p, mat) => {
    const g = group(at(box(0.08, 0.9, 0.08, mat(p.steel, { metal: 0.8 })), 0, 0.45));
    const panel = group(at(rbox(2.0, 0.06, 1.3, 0.02, mat(p.silver, { metal: 0.7 })), 0, 0));
    for (let i = 0; i < 4; i++) for (let j = 0; j < 3; j++) panel.add(at(box(0.44, 0.02, 0.38, mat("#1d3a7a", { rough: 0.15, clear: 1 })), -0.72 + i * 0.48, 0.04, -0.42 + j * 0.42));
    g.add(at(panel, 0, 0.95, 0, -0.5)); return parts(g);
  });
  family(["robot"], (n, p, mat) => parts(group(at(rbox(1.0, 1.0, 0.8, 0.2, mat(p.white)), 0, 0.85), at(rbox(0.8, 0.6, 0.7, 0.18, mat(p.white)), 0, 1.75),
    at(rbox(0.6, 0.3, 0.05, 0.1, mat(p.dark)), 0, 1.78, 0.35), ...[-0.13, 0.13].map((x) => at(sph(0.06, mat(p.main, { glow: 1.2 })), x, 1.78, 0.39)),
    at(cyl(0.02, 0.02, 0.3, mat(p.steel)), 0, 2.2), at(sph(0.07, mat(p.second, { glow: 0.8 })), 0, 2.38),
    ...[-1, 1].map((s) => at(rbox(0.2, 0.7, 0.25, 0.08, mat(p.main)), s * 0.65, 0.85, 0, 0, 0, s * 0.15)),
    ...[-0.25, 0.25].map((x) => at(rbox(0.28, 0.4, 0.3, 0.08, mat(p.dark)), x, 0.2, 0)))));
  // buildings
  function windows(g, mat, p, w, h, d, rows, cols, y0 = 0.25) {
    const glassM = mat(p.sky, { rough: 0.1, clear: 1 });
    for (let r = 0; r < rows; r++) for (let c = 0; c < cols; c++) g.add(at(box(w / cols * 0.55, h / rows * 0.5, 0.02, glassM), -w / 2 + (c + 0.5) * w / cols, y0 + r * h / rows, d / 2 + 0.01));
  }
  family(["building", "office", "apartment", "tower", "skyscraper", "hotel", "hospital", "bank", "school_building", "college", "factory"], (n, p, mat) => {
    const tall = { tower: 4, skyscraper: 4.6, building: 3, office: 3.2, apartment: 2.8, hotel: 3.4, hospital: 2.4, bank: 1.7, school_building: 1.7, college: 2.0, factory: 1.5 }[n];
    const wide = ["school_building", "college", "bank", "factory", "hospital"].includes(n) ? 2.6 : 1.5;
    const g = group();
    const floors = Math.max(2, Math.round(tall / 0.45));
    for (let i = 0; i < floors; i++) g.add(at(rbox(wide, tall / floors - 0.02, 1.2, 0.04, mat(i % 2 ? p.light : p.white, { rough: 0.6 })), 0, (i + 0.5) * tall / floors));
    windows(g, mat, p, wide, tall, 1.2, floors, wide > 2 ? 6 : 3);
    if (n === "bank") for (let i = 0; i < 5; i++) g.add(at(cyl(0.08, 0.09, 1.3, mat(p.white)), -1 + i * 0.5, 0.7, 0.7));
    if (n === "bank" || n === "school_building" || n === "college") g.add(at(cone(1.7, 0.6, mat(p.main), 4), 0, tall + 0.3, 0, 0, Math.PI / 4));
    if (n === "school_building" || n === "college") { g.add(at(cyl(0.02, 0.02, 0.8, mat(p.steel)), 0.9, tall + 0.5, 0.4)); g.add(at(box(0.4, 0.25, 0.02, mat(p.second)), 1.11, tall + 0.75, 0.4)); g.add(at(cyl(0.25, 0.25, 0.04, mat("#fff")), 0, tall - 0.3, 0.62, Math.PI / 2)); }
    if (n === "hospital") { g.add(at(box(0.5, 0.15, 0.03, mat(p.red)), 0, tall - 0.4, 0.62)); g.add(at(box(0.15, 0.5, 0.03, mat(p.red)), 0, tall - 0.4, 0.62)); }
    if (n === "factory") { g.add(at(cyl(0.18, 0.22, 1.5, mat(p.steel, { metal: 0.6 })), 0.8, tall + 0.6, -0.3)); }
    if (n === "tower" || n === "skyscraper") g.add(at(cyl(0.03, 0.03, 0.7, mat(p.steel)), 0, tall + 0.35));
    g.add(at(rbox(0.45, 0.55, 0.05, 0.03, mat(p.main)), 0, 0.28, 0.61));
    return parts(g);
  });
  family(["house", "home", "villa", "cottage"], (n, p, mat) => {
    const roofShape = new T.Shape(); roofShape.moveTo(-1.15, 0); roofShape.lineTo(0, 0.9); roofShape.lineTo(1.15, 0); roofShape.lineTo(-1.15, 0);
    const g = group(at(rbox(1.9, 1.2, 1.5, 0.05, mat(p.light, { rough: 0.6 })), 0, 0.6),
      at(extrude(roofShape, 1.7, mat(p.main, { rough: 0.5 }), 0.03), 0, 1.2),
      at(rbox(0.38, 0.65, 0.05, 0.03, mat(p.woodDark)), 0, 0.33, 0.76),
      ...[-0.6, 0.6].map((x) => at(rbox(0.36, 0.36, 0.04, 0.03, mat(p.sky, { rough: 0.1 })), x, 0.75, 0.76)),
      at(box(0.25, 0.6, 0.25, mat(p.brown)), 0.6, 1.75, -0.3));
    return parts(g);
  });
  family(["shop", "store", "cafe", "bakery_shop", "restaurant"], (n, p, mat) => {
    const g = group(at(rbox(2.2, 1.4, 1.4, 0.05, mat(p.light)), 0, 0.7), at(rbox(1.6, 0.8, 0.05, 0.03, mat(p.sky, { rough: 0.1, opacity: 0.7 })), 0, 0.6, 0.71),
      at(rbox(2.3, 0.3, 0.1, 0.04, mat(p.second)), 0, 1.25, 0.72));
    for (let i = 0; i < 6; i++) g.add(at(box(0.38, 0.06, 0.45, mat(i % 2 ? p.main : p.white)), -0.95 + i * 0.38, 1.05, 0.9, 0.5));
    return parts(g);
  });
  // furniture and home
  family(["chair"], (n, p, mat) => parts(group(at(rbox(0.9, 0.12, 0.9, 0.05, mat(p.main)), 0, 0.6), at(rbox(0.9, 0.9, 0.1, 0.05, mat(p.main)), 0, 1.05, -0.4),
    ...[[-1, -1], [1, -1], [-1, 1], [1, 1]].map(([a, b]) => at(cyl(0.04, 0.04, 0.6, mat(p.wood)), a * 0.38, 0.3, b * 0.38)))));
  family(["table", "desk"], (n, p, mat) => parts(group(at(rbox(2.2, 0.1, 1.2, 0.04, mat(p.wood)), 0, 0.95),
    ...[[-1, -1], [1, -1], [-1, 1], [1, 1]].map(([a, b]) => at(cyl(0.05, 0.04, 0.9, mat(p.dark)), a * 0.95, 0.45, b * 0.48)))));
  family(["sofa", "couch"], (n, p, mat) => parts(group(at(rbox(2.4, 0.45, 1.0, 0.15, mat(p.main)), 0, 0.4), at(rbox(2.4, 0.8, 0.3, 0.15, mat(p.main)), 0, 0.8, -0.38),
    ...[-1, 1].map((s) => at(rbox(0.3, 0.6, 1.0, 0.13, mat(p.main)), s * 1.2, 0.55, 0)),
    ...[-0.55, 0.55].map((x) => at(rbox(1.05, 0.2, 0.8, 0.1, mat(p.light)), x, 0.7, 0.05)))));
  family(["bed"], (n, p, mat) => parts(group(at(rbox(1.8, 0.4, 2.4, 0.06, mat(p.wood)), 0, 0.2), at(rbox(1.7, 0.25, 2.3, 0.12, mat(p.white)), 0, 0.52),
    at(rbox(1.8, 1.0, 0.12, 0.05, mat(p.wood)), 0, 0.7, -1.15), ...[-0.42, 0.42].map((x) => at(rbox(0.7, 0.16, 0.4, 0.08, mat(p.light)), x, 0.72, -0.85)),
    at(rbox(1.72, 0.08, 1.3, 0.04, mat(p.main)), 0, 0.68, 0.45))));
  family(["lamp"], (n, p, mat) => parts(group(at(cyl(0.35, 0.4, 0.08, mat(p.dark)), 0, 0.04), at(cyl(0.03, 0.03, 1.4, mat(p.gold, { metal: 0.8 })), 0, 0.75),
    at(lathe([[0.2, 1.45], [0.5, 1.95]], mat(p.cream, { side: T.DoubleSide, glow: 0.2 }), 48, false), 0, 0), at(sph(0.1, mat(p.yellow, { glow: 2 })), 0, 1.6))));
  family(["shelf", "bookshelf"], (n, p, mat) => {
    const g = group(); const cols = [p.main, p.second, p.third, p.red, p.yellow, p.purple];
    for (let i = 0; i < 4; i++) g.add(at(box(2.0, 0.06, 0.6, mat(p.wood)), 0, 0.05 + i * 0.6));
    for (const s of [-1, 1]) g.add(at(box(0.06, 1.85, 0.6, mat(p.wood)), s, 0.92));
    for (let i = 0; i < 3; i++) for (let j = 0; j < 7; j++) g.add(at(box(0.18, 0.4 + (j % 3) * 0.05, 0.42, mat(cols[(i + j) % cols.length])), -0.75 + j * 0.24, 0.3 + i * 0.6 + (j % 3) * 0.025));
    return parts(g);
  });
  family(["fridge"], (n, p, mat) => parts(group(at(rbox(1.0, 2.2, 0.9, 0.1, mat(p.white)), 0, 1.1), at(box(0.96, 0.02, 0.02, mat(p.steel)), 0, 1.45, 0.46),
    ...[0.9, 1.9].map((y) => at(rbox(0.05, 0.4, 0.05, 0.02, mat(p.steel, { metal: 0.8 })), 0.38, y, 0.48)))));
  family(["oven", "microwave"], (n, p, mat) => parts(group(at(rbox(1.6, 1.0, 1.0, 0.08, mat(p.silver, { metal: 0.5 })), 0, 0.5),
    at(rbox(1.0, 0.7, 0.05, 0.05, mat(p.dark, { rough: 0.1, opacity: 0.85 })), -0.2, 0.5, 0.5),
    ...[0.65, 0.45, 0.25].map((y) => at(cyl(0.06, 0.06, 0.05, mat(p.dark)), 0.6, y + 0.1, 0.52, Math.PI / 2)))));
  family(["washing_machine"], (n, p, mat) => parts(group(at(rbox(1.3, 1.5, 1.2, 0.1, mat(p.white)), 0, 0.75),
    at(tor(0.38, 0.06, mat(p.steel, { metal: 0.8 })), 0, 0.68, 0.61), at(cyl(0.34, 0.34, 0.02, mat(p.sky, { opacity: 0.6, rough: 0.05 })), 0, 0.68, 0.6, Math.PI / 2),
    at(rbox(1.1, 0.2, 0.05, 0.04, mat(p.light)), 0, 1.3, 0.6))));
  family(["door"], (n, p, mat) => parts(group(at(rbox(1.0, 2.0, 0.12, 0.03, mat(p.wood)), 0, 1.0), at(sph(0.05, mat(p.gold, { metal: 0.9 })), 0.38, 1.0, 0.09))));
  family(["key"], (n, p, mat) => parts(group(at(tor(0.25, 0.07, mat(p.gold, { metal: 0.9, rough: 0.25 })), 0, 1.3), at(cyl(0.06, 0.06, 1.0, mat(p.gold, { metal: 0.9 })), 0, 0.55),
    at(box(0.25, 0.1, 0.08, mat(p.gold, { metal: 0.9 })), 0.12, 0.2), at(box(0.18, 0.1, 0.08, mat(p.gold, { metal: 0.9 })), 0.1, 0.4))));
  family(["lock", "padlock", "security"], (n, p, mat) => parts(group(at(rbox(1.1, 0.9, 0.5, 0.12, mat(p.main)), 0, 0.45), at(tor(0.35, 0.08, mat(p.silver, { metal: 0.9, rough: 0.2 }), Math.PI), 0, 0.9),
    ...[-1, 1].map((s) => at(cyl(0.08, 0.08, 0.2, mat(p.silver, { metal: 0.9 })), s * 0.35, 0.92)), at(cyl(0.08, 0.08, 0.05, mat(p.dark)), 0, 0.5, 0.26, Math.PI / 2))));
  family(["shield"], (n, p, mat) => {
    const s = new T.Shape(); s.moveTo(0, 1.2); s.bezierCurveTo(0.5, 1.05, 0.8, 1.1, 0.85, 1.05); s.bezierCurveTo(0.9, 0.4, 0.5, 0.1, 0, -0.15);
    s.bezierCurveTo(-0.5, 0.1, -0.9, 0.4, -0.85, 1.05); s.bezierCurveTo(-0.8, 1.1, -0.5, 1.05, 0, 1.2);
    const tick = tube([[-0.3, 0.55, 0.2], [-0.05, 0.3, 0.2], [0.35, 0.8, 0.2]], 0.07, mat(p.white));
    return parts(group(at(extrude(s, 0.25, mat(p.main), 0.06), 0, 0.2), at(tick, 0, 0.2)));
  });
  family(["briefcase", "suitcase", "bag"], (n, p, mat) => parts(group(at(rbox(1.6, n === "suitcase" ? 1.6 : 1.1, 0.5, 0.12, mat(n === "suitcase" ? p.main : p.brown)), 0, n === "suitcase" ? 0.85 : 0.6),
    at(tor(0.25, 0.05, mat(p.dark), Math.PI), 0, n === "suitcase" ? 1.67 : 1.17), at(box(1.62, 0.08, 0.52, mat(p.gold, { metal: 0.8 })), 0, n === "suitcase" ? 0.9 : 0.75))));
  family(["parcel", "box", "package", "delivery_box"], (n, p, mat) => parts(group(at(rbox(1.3, 1.0, 1.0, 0.04, mat(p.wood, { rough: 0.8 })), 0, 0.5),
    at(box(1.32, 0.02, 0.25, mat(p.cream)), 0, 1.0), at(box(0.3, 0.3, 0.02, mat(p.white)), 0.35, 0.65, 0.51))));
  family(["gift", "present"], (n, p, mat) => parts(group(at(rbox(1.2, 1.0, 1.2, 0.05, mat(p.main)), 0, 0.5), at(rbox(1.3, 0.25, 1.3, 0.05, mat(p.main)), 0, 1.08),
    at(box(0.2, 1.3, 1.32, mat(p.second)), 0, 0.62), at(box(1.32, 1.3, 0.2, mat(p.second)), 0, 0.62),
    ...[-1, 1].map((s) => at(tor(0.2, 0.06, mat(p.second)), s * 0.18, 1.32, 0, 0, s * 0.5, s * 0.6)))));
  family(["card", "credit_card", "bank_card", "id_card", "ticket"], (n, p, mat) => {
    const tex = canvasTex((g, w, h) => { const grd = g.createLinearGradient(0, 0, w, h); grd.addColorStop(0, hexStr(p.main)); grd.addColorStop(1, hexStr(p.second));
      g.fillStyle = grd; g.fillRect(0, 0, w, h); g.fillStyle = "#e9c46a"; g.fillRect(36, 70, 60, 46); g.fillStyle = "rgba(255,255,255,.85)";
      g.font = "600 26px monospace"; g.fillText("4242  ••••  ••••  1234", 36, 170); }, 400, 250);
    return parts(group(at(rbox(1.7, 1.07, 0.04, 0.08, mat("#fff", { map: tex, rough: 0.3, clear: 0.8 })), 0, 0.6)));
  });
  family(["wallet"], (n, p, mat) => parts(group(at(rbox(1.4, 0.95, 0.22, 0.1, mat(p.brown, { rough: 0.6 })), 0, 0.5), at(rbox(0.5, 0.3, 0.06, 0.05, mat(p.woodDark)), 0.48, 0.55, 0.12))));
  family(["coin", "money", "rupee", "dollar"], (n, p, mat) => {
    const sym = n === "dollar" ? "$" : "₹";
    const face = textTex(sym, hexStr(p.gold), "#a87a12", 256, 256, "800 170px Segoe UI, sans-serif");
    const c = K.mesh(new T.CylinderGeometry(0.6, 0.6, 0.12, 64), [mat(p.gold, { metal: 0.9, rough: 0.25 }), mat("#fff", { map: face, metal: 0.6, rough: 0.3 }), mat("#fff", { map: face, metal: 0.6, rough: 0.3 })]);
    return parts(group(at(c, 0, 0.7, 0, Math.PI / 2)));
  });
  family(["calculator"], (n, p, mat) => { const g = group(at(rbox(1.0, 1.4, 0.15, 0.08, mat(p.dark)), 0, 0.7, 0, -0.2), at(box(0.8, 0.3, 0.02, mat(p.green, { glow: 0.3 })), 0, 1.15, 0.03, -0.2));
    for (let i = 0; i < 4; i++) for (let j = 0; j < 4; j++) g.add(at(rbox(0.16, 0.14, 0.05, 0.03, mat(j === 3 ? p.main : p.light)), -0.3 + j * 0.2, 0.85 - i * 0.2 - 0.0, 0.07 - i * 0.04, -0.2));
    return parts(g); });
  family(["calendar"], (n, p, mat) => { const g = group(at(rbox(1.4, 1.4, 0.12, 0.06, mat(p.white)), 0, 0.7), at(rbox(1.4, 0.35, 0.13, 0.06, mat(p.main)), 0, 1.25));
    for (let i = 0; i < 3; i++) for (let j = 0; j < 4; j++) g.add(at(box(0.2, 0.18, 0.02, mat(i === 1 && j === 2 ? p.second : p.light)), -0.45 + j * 0.3, 0.85 - i * 0.28, 0.07));
    return parts(g); });
  family(["clipboard", "checklist", "document", "invoice"], (n, p, mat) => { const g = group(at(rbox(1.2, 1.6, 0.06, 0.06, mat(p.wood)), 0, 0.8), at(box(1.0, 1.35, 0.02, mat(p.white)), 0, 0.75, 0.04),
    at(rbox(0.5, 0.15, 0.08, 0.04, mat(p.steel, { metal: 0.8 })), 0, 1.58, 0.04));
    for (let i = 0; i < 4; i++) { g.add(at(box(0.12, 0.12, 0.02, mat(i < 3 ? p.green : p.light)), -0.32, 1.2 - i * 0.28, 0.06)); g.add(at(box(0.5, 0.06, 0.02, mat(p.light)), 0.12, 1.2 - i * 0.28, 0.06)); }
    return parts(g); });
  family(["envelope", "mail", "email"], (n, p, mat) => { const flap = new T.Shape(); flap.moveTo(-0.8, 0); flap.lineTo(0, -0.55); flap.lineTo(0.8, 0); flap.lineTo(-0.8, 0);
    return parts(group(at(rbox(1.6, 1.0, 0.08, 0.04, mat(p.white)), 0, 0.5), at(extrude(flap, 0.02, mat(p.main), 0.005), 0, 1.0, 0.05))); });
  family(["chat_bubble", "message", "chat"], (n, p, mat) => parts(group(at(rbox(1.5, 1.0, 0.35, 0.3, mat(p.main)), 0, 0.85), at(cone(0.2, 0.4, mat(p.main), 3), -0.45, 0.3, 0, 0, 0, Math.PI * 0.85),
    ...[-0.35, 0, 0.35].map((x) => at(sph(0.09, mat(p.white)), x, 0.85, 0.18)))));
  family(["bell", "notification"], (n, p, mat) => parts(group(at(lathe([[0, 1.3], [0.12, 1.28], [0.3, 1.1], [0.42, 0.6], [0.6, 0.3], [0.62, 0.22], [0, 0.22]], mat(p.gold, { metal: 0.8, rough: 0.25 })), 0, 0),
    at(sph(0.12, mat(p.gold, { metal: 0.8 })), 0, 0.14), at(tor(0.1, 0.03, mat(p.gold, { metal: 0.8 })), 0, 1.38, 0, Math.PI / 2))));
  family(["magnifier", "search", "magnifying_glass"], (n, p, mat) => parts(group(at(tor(0.5, 0.08, mat(p.main)), 0, 1.15, 0, 0, 0, 0), at(cyl(0.48, 0.48, 0.02, mat(p.sky, { opacity: 0.4, rough: 0.05 })), 0, 1.15, 0, Math.PI / 2),
    at(rbox(0.18, 0.8, 0.18, 0.08, mat(p.dark)), 0.55, 0.38, 0, 0, 0, 0.7))));
  family(["trophy", "cup_trophy", "award"], (n, p, mat) => parts(group(at(lathe([[0, 1.0], [0.55, 1.55], [0.6, 1.95], [0.5, 1.95], [0.38, 1.45], [0.06, 1.0]], mat(p.gold, { metal: 0.9, rough: 0.22, side: T.DoubleSide })), 0, 0),
    at(cyl(0.07, 0.1, 0.5, mat(p.gold, { metal: 0.9 })), 0, 0.75), at(rbox(0.8, 0.45, 0.8, 0.05, mat(p.dark)), 0, 0.25),
    ...[-1, 1].map((s) => at(tor(0.22, 0.05, mat(p.gold, { metal: 0.9 }), Math.PI), s * 0.6, 1.62, 0, 0, 0, s * -Math.PI / 2)))));
  family(["medal"], (n, p, mat) => parts(group(at(cyl(0.45, 0.45, 0.08, mat(p.gold, { metal: 0.9, rough: 0.2 })), 0, 0.6, 0, Math.PI / 2), at(box(0.3, 0.8, 0.02, mat(p.main)), -0.15, 1.3, -0.02, 0, 0, 0.3), at(box(0.3, 0.8, 0.02, mat(p.second)), 0.15, 1.3, -0.03, 0, 0, -0.3))));
  family(["lightbulb", "idea", "bulb"], (n, p, mat) => parts(group(at(lathe([[0, 2.0], [0.4, 1.95], [0.62, 1.55], [0.48, 1.05], [0.3, 0.8], [0.28, 0.7], [0, 0.7]], mat(p.yellow, { glow: 0.6, opacity: 0.85, rough: 0.1 })), 0, 0),
    at(cyl(0.28, 0.24, 0.45, mat(p.steel, { metal: 0.85 })), 0, 0.48), at(tube([[-0.12, 0.8], [-0.12, 1.3], [0, 1.45], [0.12, 1.3], [0.12, 0.8]], 0.015, mat(p.orange, { glow: 2 })), 0, 0))));
  family(["rocket", "startup", "launch"], (n, p, mat) => {
    const g = group(at(lathe([[0, 0.2], [0.42, 0.35], [0.5, 1.2], [0.4, 1.9], [0.18, 2.35], [0, 2.5]], mat(p.white)), 0, 0),
      at(lathe([[0, 1.9], [0.4, 1.92], [0.18, 2.35], [0, 2.5]], mat(p.main)), 0, 0.005),
      at(cyl(0.18, 0.18, 0.05, mat(p.sky, { rough: 0.05 })), 0, 1.4, 0.47, Math.PI / 2), at(cone(0.3, 0.3, mat(p.dark)), 0, 0.12, 0, Math.PI));
    const fin = new T.Shape(); fin.moveTo(0, 0); fin.lineTo(0.5, -0.2); fin.lineTo(0.45, 0.4); fin.lineTo(0, 0.7);
    for (let i = 0; i < 3; i++) { const f = extrude(fin, 0.06, mat(p.main), 0.02); f.position.set(Math.cos(i * TAU / 3) * 0.42, 0.25, Math.sin(i * TAU / 3) * 0.42); f.rotation.y = -i * TAU / 3; g.add(f); }
    const fire = lathe([[0, 0], [0.18, -0.1], [0.12, -0.5], [0, -0.75]], mat(p.orange, { glow: 1.6, opacity: 0.9 }), 32); fire.userData.flicker = true; g.add(at(fire, 0, 0.12));
    return parts(g);
  });
  family(["satellite"], (n, p, mat) => parts(group(at(rbox(0.7, 0.9, 0.7, 0.08, mat(p.gold, { metal: 0.8 })), 0, 1),
    ...[-1, 1].map((s) => at(rbox(1.2, 0.04, 0.6, 0.02, mat("#1d3a7a", { rough: 0.15, clear: 1 })), s * 1.05, 1, 0)), at(lathe([[0, 0], [0.35, 0.2]], mat(p.white, { side: T.DoubleSide }), 32, false), 0, 1.45))));
  // school
  family(["graduation_cap", "grad_cap", "mortarboard"], (n, p, mat) => parts(group(at(lathe([[0.42, 0.0], [0.45, 0.4], [0.0, 0.5]], mat(p.deep.clone().multiplyScalar(0.6), { side: T.DoubleSide, rough: 0.75, clear: 0.05, envI: 0.25 }), 48, false), 0, 0.3),
    at(rbox(1.6, 0.06, 1.6, 0.02, mat(p.deep.clone().multiplyScalar(0.6), { rough: 0.75, clear: 0.05, envI: 0.25 })), 0, 0.82, 0, 0, Math.PI / 4), at(sph(0.06, mat(p.gold, { metal: 0.8 })), 0, 0.87),
    at(tube([[0, 0.87, 0], [0.55, 0.85, 0.2], [0.75, 0.6, 0.25], [0.78, 0.35, 0.25]], 0.02, mat(p.gold, { metal: 0.7 })), 0, 0),
    at(cyl(0.05, 0.08, 0.18, mat(p.gold, { metal: 0.7 })), 0.78, 0.27, 0.25))));
  family(["pencil", "pen", "crayon"], (n, p, mat) => parts(group(at(cyl(0.1, 0.1, 1.6, mat(n === "pen" ? p.dark : p.yellow), 6), 0, 1.0),
    at(cone(0.1, 0.3, mat(p.cream), 6), 0, 0.05, 0, Math.PI), at(cone(0.035, 0.1, mat(p.dark), 12), 0, -0.07, 0, Math.PI),
    at(cyl(0.105, 0.105, 0.14, mat(p.silver, { metal: 0.8 })), 0, 1.86), at(cyl(0.1, 0.1, 0.16, mat(p.pink)), 0, 2.01))));
  family(["ruler", "scale"], (n, p, mat) => { const g = group(at(rbox(2.4, 0.06, 0.4, 0.02, mat(p.yellow)), 0, 0.03));
    for (let i = 0; i < 24; i++) g.add(at(box(0.012, 0.01, i % 5 ? 0.08 : 0.15, mat(p.dark)), -1.15 + i * 0.1, 0.065, -0.12)); return parts(g); });
  family(["abacus"], (n, p, mat) => { const cols = [p.red, p.yellow, p.green, p.main, p.purple];
    const g = group(...[-1, 1].map((s) => at(rbox(0.12, 1.6, 0.3, 0.04, mat(p.wood)), s * 1.0, 0.8)), at(rbox(2.1, 0.12, 0.3, 0.04, mat(p.wood)), 0, 1.55), at(rbox(2.1, 0.12, 0.3, 0.04, mat(p.wood)), 0, 0.06));
    for (let r = 0; r < 5; r++) { g.add(at(cyl(0.015, 0.015, 2.0, mat(p.steel)), 0, 0.32 + r * 0.25, 0, 0, 0, Math.PI / 2)); for (let b = 0; b < 6; b++) g.add(at(sph(0.1, mat(cols[r]), 20, 14), -0.75 + b * 0.15 + (b > 2 ? 0.55 : 0), 0.32 + r * 0.25, 0)); }
    return parts(g); });
  family(["atom", "science", "physics"], (n, p, mat) => parts(group(at(sph(0.25, mat(p.main, { glow: 0.4 })), 0, 1.2),
    ...[0, 1, 2].map((i) => at(tor(0.95, 0.02, mat(p.second, { glow: 0.3 })), 0, 1.2, 0, Math.PI / 2 + (i - 1) * 0.9, i * 1.05, 0)),
    ...[0, 1, 2].map((i) => { const e = at(sph(0.08, mat(p.third, { glow: 1 })), 0, 1.2); e.userData.electron = { ring: i, phase: i * 2.1 }; return e; }))));
  family(["microscope"], (n, p, mat) => parts(group(at(rbox(1.0, 0.15, 0.8, 0.05, mat(p.dark)), 0, 0.08), at(tube([[0.3, 0.15, 0], [0.4, 0.8, 0], [0.15, 1.4, 0]], 0.09, mat(p.white)), 0, 0),
    at(cyl(0.12, 0.1, 0.9, mat(p.main)), -0.05, 1.45, 0, 0, 0, 0.45), at(rbox(0.6, 0.06, 0.5, 0.02, mat(p.dark)), -0.1, 0.6), at(cyl(0.05, 0.07, 0.3, mat(p.silver, { metal: 0.8 })), -0.3, 0.8, 0, 0, 0, 0.45))));
  family(["telescope"], (n, p, mat) => parts(group(at(cyl(0.16, 0.22, 2.0, mat(p.main)), 0, 1.4, 0, 0, 0, -0.9), ...[-0.4, 0, 0.4].map((x, i) => at(cyl(0.03, 0.03, 1.3, mat(p.dark)), x * 0.8, 0.6, (i - 1) * 0.3, (i - 1) * 0.3, 0, x * 0.8)))));
  family(["blackboard", "chalkboard", "whiteboard"], (n, p, mat) => { const tex = canvasTex((g, w, h) => { g.fillStyle = n === "whiteboard" ? "#f7f7f5" : "#2f4a3a"; g.fillRect(0, 0, w, h);
      g.strokeStyle = n === "whiteboard" ? hexStr(p.main) : "#f2f2ea"; g.lineWidth = 6; g.font = "600 64px Segoe UI"; g.fillStyle = g.strokeStyle; g.fillText("A + B = C", 40, 110);
      g.beginPath(); g.arc(380, 170, 50, 0, 6.28); g.stroke(); g.fillText("π", 360, 190); }, 512, 256);
    return parts(group(at(rbox(2.6, 1.4, 0.1, 0.04, mat(p.wood)), 0, 1.4), at(K.mesh(new T.PlaneGeometry(2.4, 1.2), mat("#fff", { map: tex, rough: 0.8 })), 0, 1.4, 0.06),
      ...[-1, 1].map((s) => at(cyl(0.04, 0.04, 1.6, mat(p.wood)), s * 1.0, 0.8, -0.1)))); });
  family(["school_bus", "bus"], (n, p, mat) => parts(group(at(rbox(3.0, 1.1, 1.2, 0.15, mat(n === "bus" ? p.main : p.yellow)), 0, 0.85),
    at(box(2.4, 0.35, 1.22, mat(p.sky, { rough: 0.1 })), -0.1, 1.05), at(rbox(0.6, 0.6, 1.22, 0.1, mat(n === "bus" ? p.main : p.yellow)), 1.55, 0.6),
    ...[[-0.9, 1], [-0.9, -1], [1.1, 1], [1.1, -1]].map(([x, s]) => at(cyl(0.28, 0.28, 0.2, mat(p.rubber, { rough: 0.8 })), x, 0.28, s * 0.58, Math.PI / 2)),
    at(box(3.02, 0.06, 1.24, mat(p.dark)), 0, 0.72))));
  family(["backpack", "school_bag"], (n, p, mat) => parts(group(at(rbox(1.1, 1.4, 0.6, 0.25, mat(p.main)), 0, 0.75), at(rbox(0.8, 0.55, 0.25, 0.12, mat(p.second)), 0, 0.5, 0.35),
    at(tor(0.2, 0.05, mat(p.dark), Math.PI), 0, 1.45), ...[-0.3, 0.3].map((x) => at(rbox(0.12, 1.1, 0.06, 0.04, mat(p.dark)), x, 0.75, -0.33)))));
  family(["paint_palette", "palette", "art"], (n, p, mat) => { const s = new T.Shape(); s.absellipse(0, 0, 1.0, 0.75, 0, TAU); const hole = new T.Path(); hole.absellipse(0.5, -0.2, 0.15, 0.12, 0, TAU); s.holes.push(hole);
    const g = group(at(extrude(s, 0.08, mat(p.wood), 0.02), 0, 0.5, 0, -Math.PI / 2 + 0.3)); [p.red, p.yellow, p.main, p.green, p.purple].forEach((c, i) => g.add(at(sph(0.13, mat(c, { rough: 0.2 }), 20, 12), -0.55 + i * 0.25, 0.62 + Math.sin(i) * 0.02, -0.25 + (i % 2) * 0.25)));
    return parts(g); });
  family(["brush", "paint_brush"], (n, p, mat) => parts(group(at(cyl(0.06, 0.04, 1.4, mat(p.wood)), 0, 0.7), at(cyl(0.08, 0.06, 0.2, mat(p.silver, { metal: 0.8 })), 0, 1.5), at(cone(0.09, 0.35, mat(p.main)), 0, 1.78))));
  K.parts = parts;
})();

/* ---- families: rounds, rings, food, nature, vehicles, tools, fashion, health, sports, symbols, text ---- */
(function () {
  "use strict";
  const K = window.M42_3D_INTERNAL; if (!K) return;
  const { T, rbox, box, cyl, sph, tor, cone, tube, extrude, at, group, canvasTex, textTex, hexStr, family, lathe, parts } = K;
  const TAU = Math.PI * 2;

  // globe / planets
  const earthTex = (p) => canvasTex((g, w, h) => {
    g.fillStyle = hexStr(p.water); g.fillRect(0, 0, w, h); g.fillStyle = hexStr(p.grass);
    const blobs = [[60, 70, 50, 34], [120, 150, 40, 60], [250, 80, 70, 40], [290, 160, 50, 46], [400, 100, 60, 40], [440, 190, 34, 24], [200, 210, 30, 16]];
    blobs.forEach(([x, y, a, b]) => { g.beginPath(); g.ellipse(x, y, a, b, 0.4, 0, TAU); g.fill(); });
    g.fillStyle = "#fff"; g.fillRect(0, 0, w, 12); g.fillRect(0, h - 12, w, 12);
  }, 512, 256);
  family(["globe", "earth", "world"], (n, p, mat) => parts(group(at(sph(0.9, mat("#fff", { map: earthTex(p), rough: 0.5 }), 64, 48), 0, 1.4, 0, 0, 0, 0.41),
    ...(n === "globe" ? [at(tor(1.02, 0.03, mat(p.gold, { metal: 0.8 }), Math.PI), 0, 1.4, 0, 0, 0, 0.41), at(cyl(0.05, 0.05, 0.5, mat(p.gold, { metal: 0.8 })), 0, 0.3), at(cyl(0.45, 0.55, 0.1, mat(p.dark)), 0, 0.05)] : []))));
  family(["planet", "saturn"], (n, p, mat) => parts(group(at(sph(0.8, mat(p.orange, { rough: 0.6 })), 0, 1.3), at(tor(1.25, 0.12, mat(p.cream, { rough: 0.5 }), TAU, 6, 96), 0, 1.3, 0, Math.PI / 2 - 0.4, 0, 0.2))));
  family(["sun"], (n, p, mat) => { const g = group(at(sph(0.7, mat(p.yellow, { glow: 0.35 })), 0, 1.3)); for (let i = 0; i < 12; i++) g.add(at(cone(0.1, 0.35, mat(p.orange, { glow: 0.6 })), Math.cos(i * TAU / 12) * 0.95, 1.3 + Math.sin(i * TAU / 12) * 0.95, 0, 0, 0, i * TAU / 12 - Math.PI / 2)); return parts(g); });
  family(["moon"], (n, p, mat) => parts(group(at(sph(0.8, mat("#d9dce3", { rough: 0.9 })), 0, 1.2), ...[[0.3, 0.3], [-0.2, -0.1], [0.1, -0.4]].map(([x, y]) => at(sph(0.15, mat("#b7bcc6", { rough: 0.9 })), x, 1.2 + y, 0.7)))));
  // balls
  family(["ball", "football", "soccer_ball", "basketball", "tennis_ball", "cricket_ball", "volleyball"], (n, p, mat) => {
    const col = { basketball: p.orange, tennis_ball: "#d4e83a", cricket_ball: p.red, volleyball: p.white, football: p.white, soccer_ball: p.white, ball: p.main }[n];
    const g = group(at(sph(0.7, mat(col, { rough: n === "tennis_ball" ? 0.9 : 0.4 })), 0, 0.7));
    const seam = mat(n === "basketball" ? p.dark : n === "cricket_ball" ? p.white : n === "tennis_ball" ? p.white : p.dark);
    if (n === "basketball" || n === "volleyball") [0, 1, 2].forEach((i) => g.add(at(tor(0.705, 0.012, seam), 0, 0.7, 0, (i * Math.PI) / 3, i, 0)));
    else if (n === "cricket_ball") g.add(at(tor(0.705, 0.02, seam), 0, 0.7, 0, Math.PI / 2));
    else if (n === "tennis_ball") g.add(at(tor(0.705, 0.015, seam), 0, 0.7, 0, 1.0, 0.6));
    else if (n !== "ball") for (let i = 0; i < 12; i++) { const ph = Math.acos(1 - 2 * (i + 0.5) / 12), th = Math.PI * (1 + Math.sqrt(5)) * i;
      const patch = at(cyl(0.18, 0.18, 0.02, mat(p.dark), 5), Math.sin(ph) * Math.cos(th) * 0.69, 0.7 + Math.cos(ph) * 0.69, Math.sin(ph) * Math.sin(th) * 0.69);
      patch.lookAt(0, 0.7, 0); patch.rotateX(Math.PI / 2); g.add(patch); }
    return parts(g);
  });
  // rings and round things
  family(["ring", "engagement_ring", "jewellery", "jewelry"], (n, p, mat) => parts(group(at(tor(0.55, 0.08, mat(p.gold, { metal: 1, rough: 0.15 }), TAU, 32, 96), 0, 0.65, 0, 0, 0, 0),
    at(cyl(0.12, 0.07, 0.1, mat(p.gold, { metal: 1, rough: 0.15 }), 6), 0, 1.25), at(mesh_gem(mat, p, 0.2), 0, 1.38))));
  function mesh_gem(mat, p, r) { const g = K.mesh(new T.OctahedronGeometry(r, 0), mat("#e8f6ff", { rough: 0.02, metal: 0.1, clear: 1, flat: true, glow: 0.15 })); g.scale.y = 1.2; return g; }
  family(["diamond", "gem", "crystal"], (n, p, mat) => parts(group(at(lathe([[0, 0], [0.7, 0.7], [0.55, 0.95], [0, 1.0]], mat("#e8f6ff", { rough: 0.02, clear: 1, flat: true, glow: 0.1 }), 10, false), 0, 0.2))));
  family(["bracelet", "bangle"], (n, p, mat) => parts(group(at(tor(0.6, 0.09, mat(p.gold, { metal: 1, rough: 0.2 }), TAU, 24, 96), 0, 0.7, 0, 1.2))));
  family(["necklace", "chain"], (n, p, mat) => { const g = group(); for (let i = 0; i < 40; i++) { const a = Math.PI * 0.15 + (i / 39) * Math.PI * 0.7;
    g.add(at(tor(0.05, 0.015, mat(p.gold, { metal: 1, rough: 0.2 }), TAU, 8, 16), Math.cos(a) * 0.9, 1.6 - Math.sin(a) * 1.2, 0, 0, i % 2 ? Math.PI / 2 : 0)); }
    g.add(at(mesh_gem(mat, p, 0.18), 0, 0.3)); return parts(g); });
  family(["watch", "smartwatch", "clock"], (n, p, mat) => {
    if (n === "clock") { const tex = canvasTex((g, w, h) => { g.fillStyle = "#fff"; g.fillRect(0, 0, w, h); g.fillStyle = "#333"; for (let i = 0; i < 12; i++) { const a = i * TAU / 12; g.fillRect(w / 2 + Math.cos(a) * 100 - 4, h / 2 + Math.sin(a) * 100 - 4, 8, 8); } });
      const g = group(at(tor(0.8, 0.1, mat(p.main)), 0, 1.0), at(cyl(0.8, 0.8, 0.05, mat("#fff", { map: tex })), 0, 1.0, 0, Math.PI / 2));
      const hh = at(box(0.05, 0.45, 0.03, mat(p.dark)), 0, 1.2, 0.05), mm = at(box(0.04, 0.65, 0.03, mat(p.dark)), 0, 1.3, 0.06); hh.userData.hand = { speed: 0.1, pivot: 1.0 }; mm.userData.hand = { speed: 1.2, pivot: 1.0 };
      g.add(hh, mm); return parts(g); }
    return parts(group(at(rbox(0.9, 1.0, 0.25, n === "smartwatch" ? 0.2 : 0.45, mat(n === "smartwatch" ? p.dark : p.gold, { metal: 0.8, rough: 0.2 })), 0, 1.0),
      at(rbox(0.75, 0.85, 0.05, 0.18, mat(n === "smartwatch" ? p.main : p.white, { glow: n === "smartwatch" ? 0.3 : 0 })), 0, 1.0, 0.13),
      at(rbox(0.6, 1.6, 0.1, 0.08, mat(p.brown, { rough: 0.6 })), 0, 1.0, -0.1)));
  });
  family(["tyre", "tire", "wheel"], (n, p, mat) => parts(group(at(tor(0.7, 0.28, mat(p.rubber, { rough: 0.85 }), TAU, 24, 64), 0, 1.0), at(cyl(0.45, 0.45, 0.3, mat(p.silver, { metal: 0.9, rough: 0.25 })), 0, 1.0, 0, Math.PI / 2))));
  family(["life_ring", "lifebuoy"], (n, p, mat) => { const g = group(); for (let i = 0; i < 8; i++) g.add(at(tor(0.7, 0.2, mat(i % 2 ? p.red : p.white), TAU / 8, 20, 12), 0, 1.0, 0, 0, 0, i * TAU / 8)); return parts(g); });
  // food
  family(["donut", "doughnut"], (n, p, mat) => { const icing = at(tor(0.5, 0.27, mat(p.pink, { rough: 0.3 })), 0, 0.42, 0, Math.PI / 2); icing.scale.set(1, 1, 0.55);
    const g = group(at(tor(0.5, 0.26, mat(p.wood, { rough: 0.7 })), 0, 0.3, 0, Math.PI / 2), icing); const cols = [p.yellow, p.main, p.white, p.green];
    for (let i = 0; i < 26; i++) { const a = Math.random() * TAU, r = 0.32 + Math.random() * 0.36; g.add(at(cyl(0.015, 0.015, 0.08, mat(cols[i % 4])), Math.cos(a) * r, 0.57, Math.sin(a) * r, Math.PI / 2, a, 0)); }
    return parts(g); });
  family(["cake", "birthday_cake", "wedding_cake"], (n, p, mat) => { const tiers = n === "wedding_cake" ? 3 : 2; const g = group(at(cyl(1.25, 1.25, 0.06, mat(p.white)), 0, 0.03)); let y = 0.06;
    for (let i = 0; i < tiers; i++) { const r = 1.0 - i * 0.28, h = 0.55; g.add(at(cyl(r, r, h, mat(i % 2 ? p.cream : p.pink, { rough: 0.6 })), 0, y + h / 2)); g.add(at(tor(r, 0.06, mat(p.white)), 0, y + h, 0, Math.PI / 2)); y += h; }
    if (n !== "wedding_cake") for (let i = 0; i < 5; i++) { const a = i * TAU / 5; g.add(at(cyl(0.035, 0.035, 0.35, mat([p.main, p.second, p.third][i % 3])), Math.cos(a) * 0.4, y + 0.17, Math.sin(a) * 0.4)); g.add(K.flame(p, mat, Math.cos(a) * 0.4, y + 0.35, Math.sin(a) * 0.4)); }
    else g.add(at(sph(0.18, mat(p.red)), 0, y + 0.15));
    return parts(g); });
  family(["cupcake", "muffin"], (n, p, mat) => parts(group(at(lathe([[0, 0], [0.45, 0], [0.6, 0.6], [0, 0.6]], mat(p.main, { rough: 0.6 }), 16, false), 0, 0),
    at(lathe([[0.62, 0.6], [0.65, 0.75], [0.5, 0.95], [0.32, 1.15], [0.15, 1.3], [0, 1.36]], mat(p.pink, { rough: 0.35 })), 0, 0), at(sph(0.12, mat(p.red)), 0, 1.42))));
  family(["ice_cream", "ice_cream_cone"], (n, p, mat) => parts(group(at(cone(0.38, 1.2, mat(p.wood, { rough: 0.7 }), 24), 0, 0.6, 0, Math.PI), at(sph(0.42, mat(p.pink, { rough: 0.4 })), 0, 1.3), at(sph(0.36, mat(p.cream, { rough: 0.4 })), 0, 1.7), at(sph(0.08, mat(p.red)), 0, 2.08))));
  family(["burger", "hamburger", "sandwich"], (n, p, mat) => { const g = group(); let y = 0.1;
    const layer = (c, r, h, kind) => { const m = kind === "dome" ? at(lathe([[0, 0], [r, 0], [r, h * 0.4], [r * 0.6, h], [0, h * 1.05]], mat(c, { rough: 0.5 })), 0, y) : at(cyl(r, r, h, mat(c, { rough: 0.6 })), 0, y + h / 2); g.add(m); y += h; };
    layer(p.wood, 0.95, 0.25); layer(p.chocolate, 1.0, 0.22); layer(p.yellow, 1.04, 0.05); layer(p.green, 1.06, 0.06); layer(p.red, 0.95, 0.08); layer(p.wood, 0.95, 0.55, "dome");
    for (let i = 0; i < 14; i++) { const a = Math.random() * TAU, r = Math.random() * 0.6; g.add(at(sph(0.035, mat(p.cream), 8, 6), Math.cos(a) * r, y - 0.05 + Math.random() * 0.02, Math.sin(a) * r)); }
    return parts(g); });
  family(["pizza"], (n, p, mat) => { const g = group(at(cyl(1.1, 1.1, 0.1, mat(p.wood, { rough: 0.7 })), 0, 0.05), at(cyl(1.0, 1.0, 0.04, mat(p.red, { rough: 0.6 })), 0, 0.11), at(cyl(0.95, 0.95, 0.03, mat(p.yellow, { rough: 0.5 })), 0, 0.14));
    for (let i = 0; i < 9; i++) { const a = i * 2.4, r = 0.25 + (i % 3) * 0.22; g.add(at(cyl(0.11, 0.11, 0.03, mat("#b23a2a")), Math.cos(a) * r, 0.17, Math.sin(a) * r)); }
    return parts(g); });
  family(["coffee_beans", "coffee_bean", "bean"], (n, p, mat) => { const g = group(); const bean = () => { const s = sph(0.16, mat(p.brown, { rough: 0.45 }), 24, 16); s.scale.set(1, 0.6, 1.4); return s; };
    for (let i = 0; i < (n === "coffee_bean" ? 1 : 9); i++) g.add(at(bean(), (i % 3 - 1) * 0.35, 0.12 + Math.floor(i / 3) * 0.05, (Math.floor(i / 3) - 1) * 0.35, 0, i, 0)); return parts(g); });
  family(["croissant"], (n, p, mat) => parts(group(at(tor(0.55, 0.22, mat(p.wood, { rough: 0.6 }), Math.PI * 1.1, 20, 40), 0, 0.25, 0, Math.PI / 2, 0, -Math.PI * 0.05))));
  family(["bread", "loaf"], (n, p, mat) => { const top = sph(0.5, mat(p.wood, { rough: 0.7 })); top.scale.set(1.6, 0.55, 0.9);
    return parts(group(at(rbox(1.6, 0.6, 0.9, 0.25, mat(p.wood, { rough: 0.7 })), 0, 0.3), at(top, 0, 0.6))); });
  family(["cookie", "biscuit"], (n, p, mat) => { const g = group(at(cyl(0.8, 0.82, 0.16, mat(p.wood, { rough: 0.8 })), 0, 0.08)); for (let i = 0; i < 8; i++) { const a = i * 2.3, r = 0.2 + (i % 3) * 0.2; g.add(at(sph(0.08, mat(p.chocolate), 10, 8), Math.cos(a) * r, 0.17, Math.sin(a) * r)); } return parts(g); });
  family(["apple", "fruit"], (n, p, mat) => { const leaf = at(sph(0.14, mat(p.leaf), 16, 10), 0.18, 1.08, 0); leaf.scale.set(1.4, 0.3, 0.8);
    return parts(group(at(lathe([[0, 0.05], [0.35, 0.0], [0.6, 0.3], [0.62, 0.65], [0.42, 0.95], [0.1, 0.92], [0, 0.85]], mat(p.red, { rough: 0.3, clear: 0.8 })), 0, 0),
      at(cyl(0.025, 0.03, 0.3, mat(p.brown)), 0.02, 1.0, 0, 0, 0, -0.2), leaf)); });
  family(["orange_fruit", "lemon", "tomato", "cherry", "grapes", "strawberry", "watermelon"], (n, p, mat) => {
    if (n === "grapes") { const g = group(); for (let i = 0; i < 16; i++) { const lvl = Math.floor(Math.sqrt(i)), a = i * 2.4; g.add(at(sph(0.17, mat(p.purple, { rough: 0.25 }), 20, 14), Math.cos(a) * 0.08 * lvl, 1.4 - lvl * 0.28, Math.sin(a) * 0.08 * lvl)); } return parts(g); }
    if (n === "watermelon") { const sl = at(cyl(1.0, 1.0, 0.25, mat(p.red), 48), 0, 0.6, 0, Math.PI / 2); return parts(group(sl, at(tor(1.0, 0.08, mat(p.green), Math.PI), 0, 0.6, 0, 0, 0, Math.PI))); }
    const col = { orange_fruit: p.orange, lemon: p.yellow, tomato: p.red, cherry: p.red, strawberry: p.red }[n];
    const s = sph(n === "cherry" ? 0.3 : 0.55, mat(col, { rough: 0.35, clear: 0.6 })); if (n === "lemon") s.scale.set(1, 0.8, 0.8); if (n === "strawberry") s.scale.set(1, 1.2, 1);
    return parts(group(at(s, 0, n === "cherry" ? 0.35 : 0.6), at(cyl(0.02, 0.02, 0.3, mat(p.leaf)), 0, n === "cherry" ? 0.8 : 1.2, 0, 0, 0, 0.3)));
  });
  family(["sushi", "sushi_roll"], (n, p, mat) => parts(group(at(cyl(0.5, 0.5, 0.5, mat(p.dark)), 0, 0.25), at(cyl(0.44, 0.44, 0.52, mat(p.white, { rough: 0.8 })), 0, 0.25), at(cyl(0.18, 0.18, 0.54, mat(p.orange)), 0, 0.25))));
  family(["noodles", "ramen", "soup_bowl"], (n, p, mat) => { const b = K.MAKERS.bowl(p, mat, {}); const g = group(b, at(cyl(0.88, 0.88, 0.04, mat(p.yellow, { rough: 0.4 })), 0, 0.52));
    for (let i = 0; i < 6; i++) g.add(at(tor(0.15 + i * 0.1, 0.02, mat(p.cream), TAU * 0.6), 0, 0.55, 0, Math.PI / 2, 0, i)); g.add(at(cyl(0.02, 0.02, 1.6, mat(p.wood)), 0.3, 0.9, 0, 0, 0, 0.6)); return parts(g); });
  family(["fries"], (n, p, mat) => { const g = group(at(lathe([[0, 0], [0.45, 0], [0.6, 0.9], [0, 0.9]], mat(p.red), 4, false), 0, 0, 0, 0, Math.PI / 4)); for (let i = 0; i < 14; i++) g.add(at(box(0.08, 0.7, 0.08, mat(p.yellow)), (i % 5 - 2) * 0.14, 1.05 + (i % 3) * 0.05, (Math.floor(i / 5) - 1) * 0.14, (i % 3 - 1) * 0.12, 0, (i % 4 - 1.5) * 0.08)); return parts(g); });
  family(["teapot"], (n, p, mat) => parts(group(at(lathe([[0, 0], [0.55, 0], [0.75, 0.35], [0.7, 0.75], [0.45, 1.0], [0.2, 1.05], [0, 1.1]], mat(p.light, { clear: 0.6 })), 0, 0),
    at(sph(0.08, mat(p.main)), 0, 1.15), at(tube([[0.6, 0.35], [0.95, 0.5], [1.1, 0.85]], 0.07, mat(p.light)), 0, 0), at(tor(0.3, 0.05, mat(p.light), Math.PI), -0.75, 0.55, 0, 0, 0, Math.PI / 2))));
  family(["kettle", "gooseneck_kettle"], (n, p, mat) => {
    const matte = mat(p.dark, { rough: 0.4, metal: 0.35, clear: 0.6 }), wood = mat(p.wood, { rough: 0.55 });
    const body = lathe([[0, 0], [0.5, 0.0], [0.6, 0.06], [0.62, 0.22], [0.58, 0.42], [0.47, 0.6], [0.33, 0.7], [0.2, 0.73], [0, 0.735]], matte, 96);
    const neck = tube([[0.5, 0.12], [0.72, 0.1], [0.86, 0.22], [0.95, 0.45], [1.05, 0.66], [1.2, 0.78]], 0.04, matte);
    const g = group(body, at(lathe([[0, 0.73], [0.2, 0.73], [0.21, 0.75], [0.17, 0.79], [0, 0.8]], matte, 48), 0, 0), at(sph(0.06, wood), 0, 0.85), neck,
      tube([[-0.5, 0.58], [-0.78, 0.66], [-0.9, 0.42], [-0.74, 0.16], [-0.56, 0.14]], 0.055, wood));
    g.userData.spout = new T.Vector3(1.2, 0.78, 0); return parts(g);
  });
  // nature
  family(["tree", "pine", "pine_tree", "palm", "palm_tree"], (n, p, mat) => {
    if (n.startsWith("pine")) { const g = group(at(cyl(0.12, 0.16, 0.6, mat(p.brown)), 0, 0.3)); for (let i = 0; i < 3; i++) g.add(at(cone(0.9 - i * 0.22, 0.9, mat(p.leaf, { flat: true, rough: 0.7 }), 8), 0, 0.85 + i * 0.5)); return parts(g); }
    if (n.startsWith("palm")) { const g = group(tube([[0, 0], [0.1, 0.8], [0.3, 1.6], [0.5, 2.2]], 0.1, mat(p.brown))); for (let i = 0; i < 6; i++) { const a = i * TAU / 6; g.add(tube([[0.5, 2.2], [0.5 + Math.cos(a) * 0.6, 2.45, Math.sin(a) * 0.6], [0.5 + Math.cos(a) * 1.0, 2.1, Math.sin(a) * 1.0]], 0.07, mat(p.leaf))); } return parts(g); }
    const g = group(at(cyl(0.14, 0.2, 1.0, mat(p.brown)), 0, 0.5)); [[0, 1.45, 0, 0.7], [0.4, 1.2, 0.2, 0.5], [-0.35, 1.25, -0.15, 0.5], [0.05, 1.85, 0.05, 0.5]].forEach(([x, y, z, r]) => g.add(at(K.mesh(new T.IcosahedronGeometry(r, 1), mat(p.leaf, { flat: true, rough: 0.7 })), x, y, z)));
    return parts(g);
  });
  family(["leaf", "eco", "plant_leaf"], (n, p, mat) => { const s = new T.Shape(); s.moveTo(0, 0); s.bezierCurveTo(0.6, 0.3, 0.6, 1.0, 0, 1.5); s.bezierCurveTo(-0.6, 1.0, -0.6, 0.3, 0, 0);
    return parts(group(at(extrude(s, 0.04, mat(p.leaf, { rough: 0.4 }), 0.02), 0, 0.2, 0, 0, 0, 0.2), at(tube([[0, 0.2], [0.05, 0.9], [0.0, 1.6]], 0.025, mat(p.green)), 0, 0, 0.04, 0, 0, 0.2))); });
  family(["flower", "rose", "tulip", "bouquet", "sunflower"], (n, p, mat) => {
    const make = (x, z, c, h) => { const g = group(at(tube([[0, 0], [0.05, h * 0.5], [0, h]], 0.03, mat(p.leaf)), x, 0, z)); const pc = n === "sunflower" ? p.yellow : c;
      for (let i = 0; i < (n === "tulip" ? 5 : 8); i++) { const pe = sph(n === "sunflower" ? 0.2 : 0.18, mat(pc, { rough: 0.4 }), 16, 12); pe.scale.set(0.6, n === "tulip" ? 1.6 : 0.3, 1.2); g.add(at(pe, x + Math.cos(i * TAU / 8) * 0.17, h + (n === "tulip" ? 0.15 : 0), z + Math.sin(i * TAU / 8) * 0.17, 0, -i * TAU / 8, n === "tulip" ? 0.2 : 0.4)); }
      g.add(at(sph(0.1, mat(n === "sunflower" ? p.brown : p.yellow)), x, h + 0.05, z)); return g; };
    if (n === "bouquet") return parts(group(make(0, 0, p.pink, 1.4), make(0.3, 0.1, p.red, 1.2), make(-0.3, 0.1, p.purple, 1.25), make(0.05, -0.3, p.main, 1.3)));
    return parts(group(make(0, 0, n === "rose" ? p.red : p.pink, 1.4)));
  });
  family(["cactus"], (n, p, mat) => parts(group(K.MAKERS.plant_pot(p, mat, {}), at(cyl(0.28, 0.3, 1.1, mat(p.green, { rough: 0.6 }), 12), 0, 1.4), at(sph(0.28, mat(p.green, { rough: 0.6 }), 12, 8), 0, 1.95),
    at(cyl(0.14, 0.14, 0.5, mat(p.green, { rough: 0.6 }), 10), 0.4, 1.6, 0, 0, 0, 0), at(cyl(0.14, 0.14, 0.3, mat(p.green, { rough: 0.6 }), 10), 0.28, 1.35, 0, 0, 0, Math.PI / 2))));
  family(["mountain", "mountains", "hill"], (n, p, mat) => parts(group(at(cone(1.2, 2.0, mat(p.steel, { flat: true, rough: 0.8 }), 6), 0, 1.0), at(cone(0.45, 0.6, mat(p.white, { flat: true }), 6), 0, 1.72),
    at(cone(0.9, 1.4, mat(p.leaf, { flat: true, rough: 0.8 }), 6), 1.1, 0.7, 0.3), at(cone(0.8, 1.2, mat(p.green, { flat: true, rough: 0.8 }), 6), -1.0, 0.6, 0.4))));
  family(["cloud", "cloud_storage"], (n, p, mat) => parts(group(...[[0, 1.3, 0.55], [0.55, 1.2, 0.42], [-0.55, 1.18, 0.4], [0.25, 1.6, 0.42], [-0.25, 1.55, 0.36]].map(([x, y, r]) => at(sph(r, mat(p.white, { rough: 0.6 })), x, y, 0)))));
  family(["rock", "stone"], (n, p, mat) => parts(group(at(K.mesh(new T.DodecahedronGeometry(0.7, 0), mat(p.steel, { flat: true, rough: 0.9 })), 0, 0.5, 0, 0.3, 0.5))));
  family(["island"], (n, p, mat) => parts(group(at(cyl(1.4, 0.4, 0.8, mat(p.soil, { flat: true }), 8), 0, 0.4), at(cyl(1.42, 1.42, 0.12, mat(p.grass)), 0, 0.82), at(K.MAKERS.tree(p, mat, {}), 0.3, 0.88, 0, 0, 0, 0, 0.7),
    at(K.MAKERS.house(p, mat, {}), -0.6, 0.88, 0.2, 0, 0.4, 0, 0.45))));
  family(["water_drop", "drop"], (n, p, mat) => parts(group(at(lathe([[0, 0], [0.45, 0.25], [0.55, 0.6], [0.35, 1.05], [0, 1.6]], mat(p.water, { rough: 0.05, clear: 1, opacity: 0.85 })), 0, 0.1))));
  family(["fire", "flame_big"], (n, p, mat) => { const f = lathe([[0, 0], [0.5, 0.25], [0.45, 0.8], [0.15, 1.4], [0, 1.8]], mat(p.red.clone().lerp(p.orange, 0.5), { glow: 0.12, opacity: 0.95 })); f.userData.flicker = true;
    const f2 = lathe([[0, 0], [0.3, 0.2], [0.25, 0.6], [0, 1.1]], mat(p.yellow, { glow: 0.6 })); f2.userData.flicker = true; return parts(group(f, at(f2, 0, 0.05, 0.1))); });
  // vehicles
  family(["car", "taxi", "electric_car"], (n, p, mat) => parts(group(at(rbox(2.6, 0.65, 1.2, 0.25, mat(n === "taxi" ? p.yellow : p.main, { rough: 0.2, clear: 1 })), 0, 0.6),
    at(rbox(1.5, 0.55, 1.1, 0.25, mat(n === "taxi" ? p.yellow : p.main, { rough: 0.2, clear: 1 })), -0.15, 1.1), at(rbox(1.35, 0.42, 1.12, 0.18, mat(p.dark, { rough: 0.05 })), -0.15, 1.12),
    ...[[-0.85, 1], [-0.85, -1], [0.85, 1], [0.85, -1]].map(([x, s]) => at(cyl(0.3, 0.3, 0.22, mat(p.rubber, { rough: 0.8 })), x, 0.32, s * 0.55, Math.PI / 2)),
    ...[-0.38, 0.38].map((z) => at(sph(0.08, mat(p.yellow, { glow: 1.5 })), 1.3, 0.7, z)))));
  family(["bike", "bicycle", "scooter", "motorbike"], (n, p, mat) => parts(group(...[-0.8, 0.8].map((x) => at(tor(0.45, 0.05, mat(p.rubber)), x, 0.45)),
    tube([[-0.8, 0.45], [-0.1, 0.45], [0.35, 1.1], [-0.35, 1.1], [-0.1, 0.45]], 0.04, mat(p.main)), tube([[0.35, 1.1], [0.8, 0.45]], 0.04, mat(p.main)),
    at(rbox(0.35, 0.08, 0.15, 0.04, mat(p.dark)), -0.4, 1.2), tube([[0.3, 1.1], [0.35, 1.35], [0.15, 1.4]], 0.03, mat(p.dark)))));
  family(["plane", "airplane", "flight", "travel"], (n, p, mat) => parts(group(at(lathe([[0, -1.3], [0.25, -1.0], [0.3, 0.6], [0.2, 1.1], [0, 1.4]], mat(p.white)), 0, 1.0, 0, Math.PI / 2, 0, Math.PI / 2),
    at(rbox(0.6, 0.06, 2.8, 0.03, mat(p.white)), 0.1, 1.0), at(rbox(0.35, 0.05, 1.0, 0.02, mat(p.main)), -1.05, 1.05), at(rbox(0.4, 0.5, 0.05, 0.02, mat(p.main)), -1.1, 1.3),
    ...[-0.7, 0.7].map((z) => at(cyl(0.12, 0.12, 0.4, mat(p.steel, { metal: 0.7 })), 0.25, 0.85, z, 0, 0, Math.PI / 2)))));
  family(["boat", "ship", "sailboat"], (n, p, mat) => { const hull = new T.Shape(); hull.moveTo(-1.3, 0.4); hull.lineTo(1.3, 0.4); hull.lineTo(0.9, -0.1); hull.lineTo(-1.0, -0.1); hull.lineTo(-1.3, 0.4);
    const sail = new T.Shape(); sail.moveTo(0, 0); sail.lineTo(0, 1.6); sail.lineTo(1.0, 0.1); sail.lineTo(0, 0);
    return parts(group(at(extrude(hull, 0.8, mat(p.main), 0.05), 0, 0.3), at(cyl(0.03, 0.03, 1.8, mat(p.wood)), 0, 1.6), at(extrude(sail, 0.02, mat(p.white, { side: T.DoubleSide }), 0.005), 0.05, 0.8))); });
  family(["drone"], (n, p, mat) => { const g = group(at(rbox(0.7, 0.2, 0.7, 0.08, mat(p.dark)), 0, 1.0)); for (const [x, z] of [[1, 1], [1, -1], [-1, 1], [-1, -1]]) {
      g.add(at(box(0.7, 0.05, 0.06, mat(p.dark)), x * 0.35, 1.0, z * 0.35, 0, Math.atan2(z, x) * -1 + 0, 0)); const prop = at(box(0.6, 0.01, 0.06, mat(p.main)), x * 0.62, 1.12, z * 0.62); prop.userData.propeller = true; g.add(prop); g.add(at(cyl(0.05, 0.05, 0.1, mat(p.steel)), x * 0.62, 1.06, z * 0.62)); }
    g.add(at(sph(0.1, mat(p.sky, { rough: 0.05 })), 0, 0.9, 0.3)); return parts(g); });
  family(["truck", "delivery_truck", "van"], (n, p, mat) => parts(group(at(rbox(1.9, 1.4, 1.3, 0.08, mat(p.white)), -0.45, 1.05), at(rbox(0.9, 1.0, 1.25, 0.15, mat(p.main)), 1.0, 0.85),
    at(rbox(0.5, 0.45, 1.27, 0.08, mat(p.dark, { rough: 0.05 })), 1.15, 1.1), ...[[-1, 1], [-1, -1], [1, 1], [1, -1]].map(([x, s]) => at(cyl(0.3, 0.3, 0.22, mat(p.rubber)), x * 0.85, 0.3, s * 0.6, Math.PI / 2)))));
  family(["train", "metro"], (n, p, mat) => parts(group(at(rbox(3.0, 1.2, 1.1, 0.25, mat(p.main)), 0, 0.85), at(box(2.4, 0.35, 1.12, mat(p.sky, { rough: 0.05 })), 0, 1.0),
    ...[-1, -0.35, 0.35, 1].map((x) => at(cyl(0.18, 0.18, 1.15, mat(p.dark)), x, 0.22, 0, Math.PI / 2)))));
  // tools and craft
  family(["gear", "gears", "settings", "engineering"], (n, p, mat) => {
    const gearShape = (R, teeth, r0) => { const s = new T.Shape(); for (let i = 0; i <= teeth * 2; i++) { const a = i * Math.PI / teeth, rr = i % 2 ? R : R * 0.82; const x = Math.cos(a) * rr, y = Math.sin(a) * rr; i ? s.lineTo(x, y) : s.moveTo(x, y); }
      const h = new T.Path(); h.absarc(0, 0, r0, 0, TAU, true); s.holes.push(h); return s; };
    const g1 = at(extrude(gearShape(0.8, 12, 0.25), 0.25, mat(p.main, { metal: 0.4, rough: 0.35 }), 0.03), 0, 1.0); g1.userData.spinZ = 0.5;
    if (n !== "gears" && n !== "engineering") return parts(group(g1));
    const g2 = at(extrude(gearShape(0.5, 8, 0.15), 0.25, mat(p.second, { metal: 0.4, rough: 0.35 }), 0.03), 1.2, 1.55); g2.userData.spinZ = -0.8;
    return parts(group(g1, g2));
  });
  family(["wrench", "spanner", "tools", "repair"], (n, p, mat) => { const s = new T.Shape(); s.absarc(0, 0, 0.35, 0.6, TAU - 0.6, false); s.lineTo(0.1, -0.12); s.lineTo(0.1, 0.12);
    return parts(group(at(extrude(s, 0.12, mat(p.silver, { metal: 0.9, rough: 0.25 }), 0.02), 0, 2.0, 0, 0, 0, -Math.PI / 2), at(rbox(0.22, 1.6, 0.12, 0.06, mat(p.silver, { metal: 0.9, rough: 0.25 })), 0, 0.95), at(rbox(0.28, 0.6, 0.16, 0.08, mat(p.main)), 0, 0.4))); });
  family(["hammer"], (n, p, mat) => parts(group(at(cyl(0.07, 0.08, 1.8, mat(p.wood)), 0, 0.9), at(rbox(0.9, 0.3, 0.3, 0.06, mat(p.steel, { metal: 0.9 })), 0.15, 1.85))));
  family(["screwdriver"], (n, p, mat) => parts(group(at(cyl(0.16, 0.18, 0.7, mat(p.main), 8), 0, 0.35), at(cyl(0.04, 0.04, 1.0, mat(p.silver, { metal: 0.9 })), 0, 1.2))));
  family(["printer_3d", "3d_printer"], (n, p, mat) => { const m = mat(p.main, { rough: 0.35 }), g = group();
    for (const [x, z] of [[-1, -1], [1, -1], [-1, 1], [1, 1]]) g.add(at(box(0.1, 2.2, 0.1, m), x * 1.0, 1.1, z * 1.0));
    for (const y of [0.05, 2.15]) for (const [w, d, x, z] of [[2.1, 0.1, 0, -1], [2.1, 0.1, 0, 1], [0.1, 2.1, -1, 0], [0.1, 2.1, 1, 0]]) g.add(at(box(w, 0.1, d, m), x, y, z));
    g.add(at(box(1.8, 0.08, 1.8, mat(p.dark, { rough: 0.6 })), 0, 0.35)); const head = group(at(box(2.0, 0.08, 0.08, mat(p.steel, { metal: 0.8 })), 0, 0), at(rbox(0.3, 0.3, 0.3, 0.05, mat(p.dark)), 0, -0.1), at(cone(0.06, 0.15, mat(p.copper, { metal: 0.8 })), 0, -0.32, 0, Math.PI));
    head.userData.printhead = true; g.add(at(head, 0, 1.4)); g.add(at(cyl(0.3, 0.3, 0.2, mat(p.second)), 0.6, 2.4, 0, Math.PI / 2)); return parts(g); });
  family(["scissors"], (n, p, mat) => parts(group(...[-1, 1].map((s) => group(at(tor(0.22, 0.05, mat(p.main)), s * 0.25, 0.4), at(rbox(0.08, 1.2, 0.04, 0.03, mat(p.silver, { metal: 0.9 })), s * 0.05, 1.1, 0.03 * s, 0, 0, s * 0.18))))));
  family(["sewing_machine", "thread", "spool"], (n, p, mat) => parts(group(at(cyl(0.45, 0.45, 0.1, mat(p.wood)), 0, 0.05), at(cyl(0.3, 0.3, 0.9, mat(p.main, { rough: 0.7 })), 0, 0.55), at(cyl(0.45, 0.45, 0.1, mat(p.wood)), 0, 1.05))));
  // fashion and beauty
  family(["glasses", "sunglasses", "spectacles"], (n, p, mat) => parts(group(...[-0.45, 0.45].map((x) => at(tor(0.32, 0.04, mat(p.dark)), x, 1.0)), ...[-0.45, 0.45].map((x) => at(cyl(0.3, 0.3, 0.02, mat(n === "sunglasses" ? p.dark : p.sky, { opacity: 0.6, rough: 0.05 })), x, 1.0, 0, Math.PI / 2)),
    at(tor(0.13, 0.03, mat(p.dark), Math.PI), 0, 1.02), ...[-1, 1].map((s) => at(box(0.05, 0.05, 1.0, mat(p.dark)), s * 0.78, 1.05, -0.5)))));
  family(["cap", "hat", "baseball_cap"], (n, p, mat) => parts(group(at(lathe([[0.75, 0], [0.72, 0.3], [0.5, 0.6], [0, 0.7]], mat(p.main, { side: T.DoubleSide })), 0, 0.3), at(cyl(0.55, 0.6, 0.05, mat(p.main)), 0.55, 0.32, 0, 0, 0, 0.12), at(sph(0.06, mat(p.main)), 0, 1.0))));
  family(["shoe", "sneaker"], (n, p, mat) => parts(group(at(rbox(2.0, 0.22, 0.8, 0.1, mat(p.white)), 0, 0.11), at(rbox(1.6, 0.55, 0.75, 0.25, mat(p.main)), -0.15, 0.45), at(rbox(0.8, 0.45, 0.7, 0.22, mat(p.main)), -0.55, 0.85),
    ...[0, 1, 2].map((i) => at(box(0.05, 0.03, 0.55, mat(p.white)), 0.05 + i * 0.18, 0.75 - i * 0.03, 0)))));
  family(["tshirt", "shirt", "clothes"], (n, p, mat) => { const s = new T.Shape(); s.moveTo(-0.5, 0); s.lineTo(0.5, 0); s.lineTo(0.5, 0.9); s.lineTo(0.85, 0.75); s.lineTo(1.05, 1.05); s.lineTo(0.55, 1.35); s.lineTo(0.2, 1.35);
    s.quadraticCurveTo(0, 1.15, -0.2, 1.35); s.lineTo(-0.55, 1.35); s.lineTo(-1.05, 1.05); s.lineTo(-0.85, 0.75); s.lineTo(-0.5, 0.9); s.lineTo(-0.5, 0);
    return parts(group(at(extrude(s, 0.18, mat(p.main, { rough: 0.8 }), 0.05), 0, 0.3))); });
  family(["handbag", "purse"], (n, p, mat) => parts(group(at(rbox(1.4, 1.0, 0.55, 0.18, mat(p.main, { rough: 0.45 })), 0, 0.5), at(tor(0.45, 0.05, mat(p.dark), Math.PI), 0, 1.0), at(rbox(0.25, 0.15, 0.05, 0.04, mat(p.gold, { metal: 0.9 })), 0, 0.75, 0.29))));
  family(["lipstick", "makeup", "cosmetics"], (n, p, mat) => parts(group(at(cyl(0.25, 0.25, 0.8, mat(p.gold, { metal: 0.9, rough: 0.2 })), 0, 0.4), at(cyl(0.2, 0.2, 0.5, mat(p.red, { rough: 0.3 })), 0, 1.05), at(lathe([[0.2, 1.3], [0.2, 1.45], [0, 1.6]], mat(p.red, { rough: 0.3 })), 0, 0))));
  family(["crown", "king", "premium"], (n, p, mat) => { const g = group(at(cyl(0.7, 0.7, 0.4, mat(p.gold, { metal: 0.95, rough: 0.2, side: T.DoubleSide }), 64), 0, 0.4));
    for (let i = 0; i < 8; i++) { const a = i * TAU / 8; g.add(at(cone(0.16, 0.5, mat(p.gold, { metal: 0.95, rough: 0.2 })), Math.cos(a) * 0.62, 0.85, Math.sin(a) * 0.62)); g.add(at(sph(0.06, mat(i % 2 ? p.red : p.main, { rough: 0.1 })), Math.cos(a) * 0.71, 0.45, Math.sin(a) * 0.71)); }
    return parts(g); });
  family(["umbrella"], (n, p, mat) => { const g = group(at(cyl(0.03, 0.03, 1.8, mat(p.dark)), 0, 0.9), at(tor(0.12, 0.03, mat(p.dark), Math.PI), 0.12, 0.05, 0, 0, 0, Math.PI));
    for (let i = 0; i < 8; i++) g.add(at(K.mesh(new T.SphereGeometry(1.1, 12, 8, i * TAU / 8, TAU / 8, 0, Math.PI / 2.4), mat(i % 2 ? p.main : p.white, { side: T.DoubleSide })), 0, 1.3));
    return parts(g); });
  // health
  family(["pill", "capsule", "medicine", "tablet_pill"], (n, p, mat) => { const half = (c, s) => at(lathe([[0, 0], [0.22, 0.04], [0.25, 0.25], [0.25, 0.5]], mat(c, { rough: 0.2, clear: 1 }), 48), 0, 0, 0, s > 0 ? 0 : Math.PI);
    return parts(group(at(group(half(p.main, 1), half(p.white, -1)), 0, 0.8, 0, 0, 0, 0.9))); });
  family(["syringe", "vaccine", "injection"], (n, p, mat) => parts(group(at(group(
      at(cyl(0.2, 0.2, 1.3, mat(p.white, { opacity: 0.45, rough: 0.05, clear: 1 })), 0, 0.85), at(cyl(0.17, 0.17, 0.8, mat(p.main, { opacity: 0.9 })), 0, 0.62),
      at(cyl(0.05, 0.05, 0.7, mat(p.white)), 0, 1.75), at(cyl(0.28, 0.28, 0.05, mat(p.white)), 0, 2.1), at(cyl(0.32, 0.32, 0.05, mat(p.white)), 0, 1.5),
      at(cone(0.12, 0.2, mat(p.white)), 0, 0.12, 0, Math.PI), at(cyl(0.012, 0.012, 0.6, mat(p.silver, { metal: 0.9 })), 0, -0.25)), 0, 0.5, 0, 0, 0, 0.7))));
  family(["heart", "love", "health", "cardiology"], (n, p, mat) => { const s = new T.Shape(); s.moveTo(0, -0.5); s.bezierCurveTo(-0.9, 0.1, -0.6, 0.9, 0, 0.45); s.bezierCurveTo(0.6, 0.9, 0.9, 0.1, 0, -0.5);
    return parts(group(at(extrude(s, 0.35, mat(n === "health" ? p.main : p.red, { rough: 0.25, clear: 1 }), 0.12), 0, 1.0))); });
  family(["first_aid", "medical_kit", "medical"], (n, p, mat) => parts(group(at(rbox(1.5, 1.1, 0.6, 0.15, mat(p.white)), 0, 0.55), at(box(0.55, 0.16, 0.02, mat(p.red)), 0, 0.55, 0.31), at(box(0.16, 0.55, 0.02, mat(p.red)), 0, 0.55, 0.31), at(tor(0.25, 0.05, mat(p.dark), Math.PI), 0, 1.1))));
  family(["stethoscope", "doctor"], (n, p, mat) => parts(group(tube([[-0.4, 1.8], [-0.45, 1.2], [0, 0.8], [0.45, 1.2], [0.4, 1.8]], 0.04, mat(p.dark)), tube([[0, 0.8], [0.1, 0.4], [0.5, 0.25]], 0.04, mat(p.dark)), at(cyl(0.18, 0.18, 0.1, mat(p.silver, { metal: 0.9 })), 0.55, 0.22, 0, 0, 0, Math.PI / 2))));
  family(["tooth", "dental", "dentist"], (n, p, mat) => parts(group(at(lathe([[0, 1.6], [0.45, 1.55], [0.6, 1.2], [0.5, 0.85], [0.25, 0.55]], mat(p.white, { rough: 0.2, clear: 1 })), 0, 0), ...[-0.2, 0.2].map((x) => at(cone(0.16, 0.7, mat(p.white, { rough: 0.2 })), x, 0.45, 0, Math.PI)))));
  family(["dna", "genetics", "biotech"], (n, p, mat) => { const g = group(); for (let i = 0; i < 24; i++) { const a = i * 0.45, y = 0.2 + i * 0.09;
      g.add(at(sph(0.07, mat(p.main), 12, 8), Math.cos(a) * 0.45, y, Math.sin(a) * 0.45)); g.add(at(sph(0.07, mat(p.second), 12, 8), -Math.cos(a) * 0.45, y, -Math.sin(a) * 0.45));
      if (i % 2) g.add(at(cyl(0.02, 0.02, 0.9, mat(p.white)), 0, y, 0, 0, -a, Math.PI / 2)); } return parts(g); });
  family(["thermometer"], (n, p, mat) => parts(group(at(cyl(0.12, 0.12, 1.6, mat(p.white, { opacity: 0.7 })), 0, 1.1), at(sph(0.22, mat(p.red)), 0, 0.25), at(cyl(0.05, 0.05, 1.0, mat(p.red)), 0, 0.85))));
  // sports and fitness
  family(["dumbbell", "gym", "fitness"], (n, p, mat) => parts(group(at(cyl(0.06, 0.06, 1.6, mat(p.silver, { metal: 0.9 })), 0, 0.45, 0, 0, 0, Math.PI / 2),
    ...[-0.6, -0.45, 0.45, 0.6].map((x) => at(cyl(x * x > 0.3 ? 0.42 : 0.38, x * x > 0.3 ? 0.42 : 0.38, 0.12, mat(p.dark, { rough: 0.4 })), x, 0.45, 0, 0, 0, Math.PI / 2)))));
  family(["kettlebell"], (n, p, mat) => parts(group(at(sph(0.55, mat(p.dark, { rough: 0.4 })), 0, 0.55), at(tor(0.32, 0.08, mat(p.dark, { rough: 0.4 }), Math.PI), 0, 1.0))));
  family(["yoga_mat", "yoga"], (n, p, mat) => parts(group(at(cyl(0.3, 0.3, 1.6, mat(p.main, { rough: 0.7 })), 0, 0.3, 0, 0, 0, Math.PI / 2), at(rbox(1.6, 0.03, 1.4, 0.01, mat(p.main, { rough: 0.7 })), 0, 0.02, 0.9))));
  family(["bat", "cricket_bat", "racket", "tennis_racket"], (n, p, mat) => n.includes("racket") ? parts(group(at(tor(0.5, 0.05, mat(p.main)), 0, 1.5, 0, 0, 0, 0), at(cyl(0.05, 0.05, 1.0, mat(p.dark)), 0, 0.5)))
    : parts(group(at(rbox(0.45, 1.5, 0.15, 0.06, mat(p.wood)), 0, 1.0), at(cyl(0.06, 0.06, 0.7, mat(p.dark)), 0, 2.05))));
  family(["running_shoe"], (n, p, mat) => K.MAKERS.sneaker(p, mat, {}));
  // symbols and abstract
  family(["star", "rating", "favorite"], (n, p, mat) => { const s = new T.Shape(); for (let i = 0; i <= 10; i++) { const a = Math.PI / 2 + i * Math.PI / 5, r = i % 2 ? 0.35 : 0.8; const x = Math.cos(a) * r, y = Math.sin(a) * r; i ? s.lineTo(x, y) : s.moveTo(x, y); }
    return parts(group(at(extrude(s, 0.25, mat(p.yellow, { rough: 0.25, clear: 1 }), 0.08), 0, 1.0))); });
  family(["lightning", "bolt", "energy", "power"], (n, p, mat) => { const s = new T.Shape(); [[0.1, 1], [-0.45, -0.05], [0.0, -0.05], [-0.15, -1], [0.45, 0.15], [0.0, 0.15], [0.1, 1]].forEach(([x, y], i) => i ? s.lineTo(x, y) : s.moveTo(x, y));
    return parts(group(at(extrude(s, 0.25, mat(p.yellow, { glow: 0.4 }), 0.06), 0, 1.1))); });
  family(["location_pin", "map_pin", "location", "map"], (n, p, mat) => parts(group(at(lathe([[0, 0], [0.12, 0.25], [0.4, 0.75], [0.55, 1.15], [0.45, 1.5], [0, 1.68]], mat(p.red, { rough: 0.25, clear: 1 })), 0, 0.2), at(sph(0.18, mat(p.white)), 0, 1.4, 0.38))));
  family(["check", "tick", "done", "success"], (n, p, mat) => parts(group(at(cyl(0.8, 0.8, 0.25, mat(p.green, { rough: 0.25 })), 0, 1.0, 0, Math.PI / 2), tube([[-0.35, 1.0, 0.15], [-0.08, 0.72, 0.15], [0.4, 1.3, 0.15]], 0.09, mat(p.white)))));
  family(["arrow_up", "growth", "chart_up", "analytics", "chart", "bar_chart"], (n, p, mat) => { const g = group(); [0.6, 1.0, 1.5, 2.1].forEach((h, i) => g.add(at(rbox(0.38, h, 0.38, 0.06, mat(i === 3 ? p.main : p.second, { rough: 0.3 })), -0.7 + i * 0.47, h / 2)));
    g.add(tube([[-0.9, 0.9, 0.3], [-0.3, 1.3, 0.3], [0.2, 1.2, 0.3], [0.9, 2.4, 0.3]], 0.045, mat(p.third))); g.add(at(cone(0.13, 0.3, mat(p.third)), 0.95, 2.5, 0.3, 0, 0, -0.5)); return parts(g); });
  family(["pie_chart", "donut_chart"], (n, p, mat) => { const g = group(); const cuts = [0.4, 0.25, 0.2, 0.15]; let a = 0; const cols = [p.main, p.second, p.third, p.yellow];
    cuts.forEach((c, i) => { g.add(at(K.mesh(new T.CylinderGeometry(1.0, 1.0, 0.3 + i * 0.08, 48, 1, false, a, c * TAU), mat(cols[i], { rough: 0.3 })), 0, 0.2 + i * 0.04)); a += c * TAU; }); return parts(g); });
  family(["question", "help", "faq"], (n, p, mat) => K.MAKERS.chat_bubble(p, mat, {}));
  family(["infinity", "loop"], (n, p, mat) => { const pts = []; for (let i = 0; i < 48; i++) { const t = i / 48 * TAU, d = 1 + Math.sin(t) ** 2; pts.push([Math.cos(t) / d * 1.1, 1.0 + Math.sin(t) * Math.cos(t) / d * 1.1, 0]); }
    return parts(group(tube(pts, 0.12, mat(p.main, { rough: 0.2, clear: 1 }), true, 128))); });
  family(["cube", "block", "blocks", "blockchain"], (n, p, mat) => { const g = group(); const k = n === "cube" ? 1 : 3; for (let i = 0; i < k; i++) for (let j = 0; j < (n === "cube" ? 1 : 2); j++) g.add(at(rbox(0.8, 0.8, 0.8, 0.12, mat([p.main, p.second, p.third][(i + j) % 3], { rough: 0.25, clear: 1 })), (i - (k - 1) / 2) * 0.95, 0.4 + j * 0.9, j * 0.2)); return parts(g); });
  family(["sphere_glass", "orb", "ai", "brain_orb"], (n, p, mat) => parts(group(at(sph(0.9, mat(p.main, { rough: 0.05, clear: 1, opacity: 0.55, glow: 0.25 })), 0, 1.2), at(K.mesh(new T.IcosahedronGeometry(0.5, 1), mat(p.second, { flat: true, glow: 0.5, rough: 0.2 })), 0, 1.2))));
  family(["torus_knot", "abstract"], (n, p, mat) => parts(group(at(K.mesh(new T.TorusKnotGeometry(0.6, 0.18, 160, 24), mat(p.main, { rough: 0.15, clear: 1, metal: 0.2 })), 0, 1.2))));
  // the brand's name in 3D: its letters on a rounded slab (canvas text), standing
  family(["brand_text", "logo", "text", "sign", "signboard", "badge"], (n, p, mat, spec) => {
    const word = String(spec.brand || spec.text || "Brand").slice(0, 24);
    const w = Math.min(4.2, 0.45 + word.length * 0.3);
    const tex = textTex(word, hexStr(p.main), "#ffffff", Math.round(w * 256), 256, "800 150px Segoe UI, sans-serif");
    const slab = rbox(w, 1.0, 0.25, 0.18, [mat(p.main, { rough: 0.3, clear: 1 })][0]);
    const face = K.mesh(new T.PlaneGeometry(w - 0.1, 0.9), mat("#fff", { map: tex, rough: 0.3, clear: 1 }));
    const g = group(at(slab, 0, 0.9), at(face, 0, 0.9, 0.131));
    if (n === "signboard" || n === "sign") g.add(...[-1, 1].map((s) => at(cyl(0.05, 0.05, 0.6, mat(p.dark)), s * (w / 2 - 0.3), 0.2)));
    return parts(g);
  });
})();

/* ---- the runtime: a scene per [data-m42-3d], its story, its extras, its card ---- */
(function () {
  "use strict";
  const K = window.M42_3D_INTERNAL; if (!K) return;
  const { T, MAKERS, LIQUIDS, at, group, lathe, tube, cyl, sph, tor, canvasTex, hexStr } = K;
  const TAU = Math.PI * 2;
  const ease = (x) => (x < 0.5 ? 2 * x * x : 1 - Math.pow(-2 * x + 2, 2) / 2);
  const back = (x) => { const c1 = 1.70158, c3 = c1 + 1; return 1 + c3 * Math.pow(x - 1, 3) + c1 * Math.pow(x - 1, 2); };
  const clamp = (x, a = 0, b = 1) => Math.max(a, Math.min(b, x));
  const STORIES = ["fill", "pour", "build_up", "assemble", "explode", "turntable", "float", "orbit", "stack", "grow", "pop", "scroll_spin",
    "scroll_rise", "swing", "bounce", "spin", "flip", "wave", "rain", "drive", "pulse", "sunrise", "levitate", "reveal"];
  const CAMERAS = ["still", "zoom_in", "pull_back", "rise", "circle"];
  const EXTRAS = ["sweep", "steam", "sparkles", "confetti", "leaves", "petals", "snow", "rain", "sparks", "bubbles", "stars", "dust", "rays", "halo",
    "glow", "grid", "clouds", "smoke", "hearts", "notes", "coins", "pedestal", "labels"];

  // ---------------------------------------------------------------- the CSS of the stage, its card and labels
  if (!document.getElementById("m42-3d-css")) {
    const st = document.createElement("style"); st.id = "m42-3d-css";
    st.textContent = `.m42-3d{position:relative;width:100%;min-height:360px;height:clamp(360px,58vh,600px)}
.m42-3d canvas{position:absolute;inset:0;width:100%!important;height:100%!important;display:block;cursor:grab;touch-action:pan-y}
.m42-3d canvas:active{cursor:grabbing}
.m42-3d-card{position:absolute;left:4%;top:5%;width:min(230px,56%);background:rgba(16,18,28,.78);color:#f5f6fa;
-webkit-backdrop-filter:blur(12px);backdrop-filter:blur(12px);border:1px solid rgba(255,255,255,.12);
border-radius:16px;padding:11px 14px;box-shadow:0 18px 40px -18px rgba(0,0,0,.6);font-size:12.5px;z-index:2}
.m42-3d-card .r{display:flex;justify-content:space-between;align-items:center;font-weight:700;letter-spacing:.04em;font-size:12px}
.m42-3d-card .r b::before{content:"";display:inline-block;width:8px;height:8px;border-radius:50%;background:#e2683c;margin-right:8px;vertical-align:1px}
.m42-3d-card.done .r b::before{background:#2f9e6b}.m42-3d-card.idle .r b::before{animation:m42pulse 1.6s infinite}
@keyframes m42pulse{50%{opacity:.25}}
.m42-3d-card .bar{height:6px;background:rgba(127,127,127,.18);border-radius:99px;margin:9px 0 7px;overflow:hidden}
.m42-3d-card .bar i{display:block;height:100%;width:0;border-radius:99px;background:linear-gradient(90deg,var(--m42-accent-2,#f4a261),var(--m42-accent,#6d5dfc))}
.m42-3d-card small{display:block;line-height:1.35}.m42-3d-card .tt{display:block;font-weight:700;font-size:14px;opacity:1}.m42-3d-card .dt{display:block;opacity:.65;margin-top:2px}
.m42-3d-label{position:absolute;z-index:2;transform:translate(-50%,-120%);background:rgba(16,18,28,.8);color:#f5f6fa;border:1px solid rgba(255,255,255,.12);
font-size:12px;font-weight:600;padding:5px 10px;border-radius:999px;box-shadow:0 8px 20px -10px rgba(0,0,0,.4);white-space:nowrap;pointer-events:none}
.m42-3d-cap{position:absolute;left:50%;bottom:4%;transform:translate(-50%,8px);z-index:2;max-width:86%;text-align:center;font-size:13px;font-weight:600;
letter-spacing:.01em;padding:7px 14px;border-radius:999px;background:rgba(16,18,28,.8);color:#f5f6fa;border:1px solid rgba(255,255,255,.12);box-shadow:0 10px 26px -14px rgba(0,0,0,.45);
opacity:0;transition:opacity .6s,transform .6s;pointer-events:none}.m42-3d-cap.on{opacity:1;transform:translate(-50%,0)}
@media (max-width:768px){.m42-3d{height:340px;min-height:300px}.m42-3d-card{left:3%;top:3%;width:min(210px,62%)}}`;
    document.head.appendChild(st);
  }

  // ---------------------------------------------------------------- a soft studio to reflect (no image file)
  function studio(renderer) {
    const pm = new T.PMREMGenerator(renderer);
    const s = new T.Scene();
    const geo = new T.SphereGeometry(10, 32, 16), cols = [];
    for (let i = 0; i < geo.attributes.position.count; i++) { const y = geo.attributes.position.getY(i) / 10; const c = new T.Color().setHSL(0.6, 0.08, 0.55 + y * 0.4); cols.push(c.r, c.g, c.b); }
    geo.setAttribute("color", new T.Float32BufferAttribute(cols, 3));
    s.add(new T.Mesh(geo, new T.MeshBasicMaterial({ vertexColors: true, side: T.BackSide })));
    for (const [x, y, z, w, h] of [[0, 8, 0, 8, 8], [7, 3, 3, 3, 5], [-7, 2, -2, 3, 4]]) { const m = new T.Mesh(new T.PlaneGeometry(w, h), new T.MeshBasicMaterial({ color: 0xffffff, side: T.DoubleSide })); m.position.set(x, y, z); m.lookAt(0, 0, 0); s.add(m); }
    const env = pm.fromScene(s, 0.04).texture; pm.dispose(); return env;
  }

  // ---------------------------------------------------------------- sizes: every object fits its place
  function fit(o, size) {
    const b = new T.Box3().setFromObject(o), d = b.getSize(new T.Vector3());
    const k = size / Math.max(d.y, Math.max(d.x, d.z) * 0.85, 1e-3);
    o.scale.multiplyScalar(k);
    const b2 = new T.Box3().setFromObject(o), c = b2.getCenter(new T.Vector3());
    o.position.x -= c.x; o.position.z -= c.z; o.position.y -= b2.min.y;
    o.userData.k = k;
    return o;
  }
  function build(name, p, mat, spec) {
    const key = String(name || "").toLowerCase().replace(/[\s-]+/g, "_");
    const make = MAKERS[key] || MAKERS[key.replace(/s$/, "")] || null;
    const file = spec && spec.models && spec.models[key];
    if (!make && file) return libModel(file, key);  // 📦 a bundled model (a person, a pet, a dish, furniture)
    if (!make) return null;
    try { const o = make(p, mat, spec); o.userData.name = key; return o; } catch (e) { console.warn("m42-3d:", key, e); return null; }
  }

  // ---------------------------------------------------------------- particles for the extras (sprites)
  const TEX = {};
  function spriteTex(kind) {
    if (TEX[kind]) return TEX[kind];
    TEX[kind] = canvasTex((g, w, h) => {
      g.clearRect(0, 0, w, h); g.fillStyle = "#fff";
      if (kind === "soft") { const r = g.createRadialGradient(w / 2, h / 2, 1, w / 2, h / 2, w / 2); r.addColorStop(0, "rgba(255,255,255,.9)"); r.addColorStop(1, "rgba(255,255,255,0)"); g.fillStyle = r; g.fillRect(0, 0, w, h); }
      else if (kind === "star") { g.translate(w / 2, h / 2); g.beginPath(); for (let i = 0; i < 8; i++) { const r = i % 2 ? 8 : 30, a = i * Math.PI / 4; g.lineTo(Math.cos(a) * r, Math.sin(a) * r); } g.fill(); }
      else if (kind === "leaf") { g.beginPath(); g.ellipse(w / 2, h / 2, 12, 26, 0.5, 0, TAU); g.fill(); }
      else if (kind === "heart") { g.beginPath(); g.moveTo(32, 52); g.bezierCurveTo(4, 32, 14, 6, 32, 20); g.bezierCurveTo(50, 6, 60, 32, 32, 52); g.fill(); }
      else if (kind === "note") { g.beginPath(); g.ellipse(24, 46, 10, 7, -0.4, 0, TAU); g.fill(); g.fillRect(31, 12, 4, 34); g.fillRect(31, 12, 16, 6); }
      else if (kind === "drop") { g.beginPath(); g.moveTo(32, 6); g.quadraticCurveTo(52, 36, 32, 56); g.quadraticCurveTo(12, 36, 32, 6); g.fill(); }
      else if (kind === "coin") { g.beginPath(); g.arc(32, 32, 26, 0, TAU); g.fill(); }
      else g.fillRect(16, 22, 32, 20);
    }, 64, 64);
    return TEX[kind];
  }
  const PART = {
    steam: { n: 24, tex: "soft", col: ["#ffffff"], move: "rise", size: [0.3, 1.0], op: 0.5, area: "top", speed: 0.18 },
    smoke: { n: 26, tex: "soft", col: ["#9aa0a6"], move: "rise", size: [0.5, 1.5], op: 0.35, area: "top", speed: 0.12 },
    sparkles: { n: 34, tex: "star", col: ["#fff7cf", "#ffffff"], move: "twinkle", size: [0.12, 0.3], op: 1, area: "around" },
    stars: { n: 70, tex: "star", col: ["#ffffff"], move: "twinkle", size: [0.05, 0.14], op: 0.9, area: "back" },
    confetti: { n: 60, tex: "square", col: "palette", move: "fall", size: [0.08, 0.16], op: 1, area: "above", spin: true, speed: 0.35 },
    leaves: { n: 26, tex: "leaf", col: ["#5fb35a", "#8bc34a", "#e0a32a"], move: "fall", size: [0.16, 0.28], op: 1, area: "above", spin: true, speed: 0.22 },
    petals: { n: 30, tex: "leaf", col: ["#f48fb1", "#f8bbd0", "#ffffff"], move: "fall", size: [0.12, 0.22], op: 1, area: "above", spin: true, speed: 0.2 },
    snow: { n: 80, tex: "soft", col: ["#ffffff"], move: "fall", size: [0.06, 0.14], op: 0.9, area: "above", speed: 0.25 },
    rain: { n: 80, tex: "drop", col: ["#9fd3ff"], move: "fall", size: [0.06, 0.12], op: 0.7, area: "above", speed: 1.2 },
    sparks: { n: 40, tex: "soft", col: ["#ffb347", "#ffd27a"], move: "burst", size: [0.05, 0.12], op: 1, area: "top", speed: 1.0 },
    bubbles: { n: 26, tex: "soft", col: ["#bfe9ff"], move: "rise", size: [0.08, 0.22], op: 0.6, area: "around", speed: 0.3 },
    dust: { n: 50, tex: "soft", col: ["#ffffff"], move: "float", size: [0.03, 0.07], op: 0.6, area: "around" },
    hearts: { n: 18, tex: "heart", col: ["#ff5c8a", "#ff8fab"], move: "rise", size: [0.15, 0.3], op: 0.95, area: "around", speed: 0.25 },
    notes: { n: 14, tex: "note", col: "palette", move: "rise", size: [0.2, 0.32], op: 0.95, area: "around", speed: 0.22 },
    coins: { n: 22, tex: "coin", col: ["#e5b54a"], move: "fall", size: [0.14, 0.2], op: 1, area: "above", speed: 0.5, spin: true },
    clouds: { n: 6, tex: "soft", col: ["#ffffff"], move: "drift", size: [0.9, 1.6], op: 0.35, area: "back" },
  };
  function particles(kind, cfg, p, box) {
    const g = new T.Group(); const list = [];
    let cols = cfg.col === "palette" ? [p.main, p.second, p.third, p.yellow, p.pink].map(hexStr) : cfg.col;
    if (p.lightBg && Array.isArray(cols) && cols.every((c) => new T.Color(c).getHSL({}).l > 0.85) && /sparkle|star|sparks|dust/.test(kind))
      cols = [p.main, p.second, p.gold].map(hexStr);  // white stars vanish into a light page (grey outlines)
    const W = box.w, H = box.h, top = box.top;
    for (let i = 0; i < cfg.n; i++) {
      const m = new T.SpriteMaterial({ map: spriteTex(cfg.tex), color: new T.Color(cols[i % cols.length]).convertSRGBToLinear(), transparent: true, depthWrite: false, opacity: cfg.op });
      const s = new T.Sprite(m); const size = cfg.size[0] + Math.random() * (cfg.size[1] - cfg.size[0]); s.scale.setScalar(size);
      s.userData = { seed: Math.random() * 100, u: Math.random(), x: (Math.random() - 0.5) * W * 1.6, z: (Math.random() - 0.5) * W, size, rot: (Math.random() - 0.5) * 4 };
      g.add(s); list.push(s);
    }
    g.userData.update = (t) => {
      for (const s of list) {
        const d = s.userData; const sp = cfg.speed || 0.2; const u = (d.u + t * sp) % 1;
        if (cfg.move === "rise") { s.position.set(d.x * (cfg.area === "top" ? 0.12 : 0.6) + Math.sin(u * 6 + d.seed) * 0.15 * u, (cfg.area === "top" ? top : 0.2) + u * H * 0.9, d.z * 0.12);
          s.scale.setScalar(d.size * (cfg.area === "top" ? 0.6 + u : 1)); s.material.opacity = cfg.op * Math.sin(u * Math.PI); }
        else if (cfg.move === "fall") { s.position.set(d.x + Math.sin(t + d.seed) * 0.3, H * 1.4 - u * H * 1.5, d.z); s.material.opacity = cfg.op * Math.min(1, (1 - u) * 6, u * 10);
          if (cfg.spin) s.material.rotation = d.rot * t; }
        else if (cfg.move === "twinkle") { const a = d.seed, r = cfg.area === "back" ? W * 1.6 : W * 0.75; s.position.set(Math.cos(a) * r * (0.5 + d.u), 0.3 + (d.u * 0.9 + Math.sin(a * 3) * 0.1) * H, cfg.area === "back" ? -W * 1.2 : Math.sin(a) * r * 0.6);
          s.material.opacity = cfg.op * (0.3 + 0.7 * Math.pow(Math.abs(Math.sin(t * 2 + d.seed)), 3)); }
        else if (cfg.move === "burst") { const a = d.seed, uu = (d.u + t * 0.8) % 1; s.position.set(Math.cos(a) * uu * 1.0, top + Math.sin(uu * Math.PI) * 0.6, Math.sin(a) * uu * 1.0); s.material.opacity = cfg.op * (1 - uu); }
        else if (cfg.move === "drift") { s.position.set(((d.u + t * 0.02) % 1 - 0.5) * W * 4, H * (0.6 + d.u * 0.5), -W * 1.4 - d.u * 2); }
        else { s.position.set(d.x + Math.sin(t * 0.3 + d.seed) * 0.4, 0.3 + d.u * H + Math.sin(t * 0.5 + d.seed) * 0.2, d.z); s.material.opacity = cfg.op * (0.4 + 0.6 * Math.abs(Math.sin(t + d.seed))); }
      }
    };
    return g;
  }

  // ---------------------------------------------------------------- one stage: a beat's objects, extras and story on its own group
  function stage(sp, p, mat, host, el, scene, camera) {
    const world = new T.Group(); host.add(world);
    // the objects: the first is the scene's own, the others stand round it
    const names = (sp.objects || []).map((o) => (typeof o === "string" ? o : o && o.name)).filter(Boolean);
    let main = build(names[0], p, mat, sp) || build("brand_text", p, mat, sp);
    fit(main, sp.size || 2.2); world.add(main);
    const props = [];
    names.slice(1, 6).forEach((n, i) => { const o = build(n, p, mat, sp); if (!o) return; fit(o, 0.95); world.add(o); props.push(o); });
    const mb = new T.Box3().setFromObject(main), msize = mb.getSize(new T.Vector3());
    const R = Math.max(msize.x, msize.z) / 2 + 1.0;
    const angles = [-0.95, 0.95, -2.2, 2.2, Math.PI];
    props.forEach((o, i) => { o.position.x += Math.sin(angles[i]) * R; o.position.z += Math.cos(angles[i]) * R * 0.75; o.userData.home = o.position.clone(); o.rotation.y = -angles[i] * 0.4; });
    main.userData.home = main.position.clone();
    const box = { w: Math.max(msize.x, 2), h: Math.max(msize.y, 2), top: msize.y };

    // a user's / an online model: it takes the main object's place when it is loaded
    if (sp.model) loadModel(sp.model, p, mat).then((m) => { if (!m) return; fit(m, sp.size || 2.2); world.remove(main); world.add(m); m.userData.home = m.position.clone(); main = m; ctx.main = m; ctx.story && ctx.story.reset && ctx.story.reset(); }).catch(() => {});

    // extras
    const extras = (sp.extras || []).map(String);
    const ups = [];
    if (extras.includes("pedestal") || sp.pedestal) { const ped = lathe([[0, 0], [R * 0.95, 0], [R, 0.06], [R * 0.95, 0.12], [0, 0.12]], mat(p.light, { rough: 0.35, clear: 0.5 }), 96, false); world.add(ped); world.children.forEach((c) => { if (c !== ped) { c.position.y += 0.12; if (c.userData.home) c.userData.home.y += 0.12; } }); }
    for (const x of extras) {
      if (PART[x]) { const g = particles(x, PART[x], p, box); world.add(g); ups.push(g.userData.update); }
      else if (x === "rays") { const g = new T.Group(); for (let i = 0; i < 9; i++) { const c = new T.Mesh(new T.ConeGeometry(0.5, 7, 16, 1, true), new T.MeshBasicMaterial({ color: p.yellow, transparent: true, opacity: 0.06, depthWrite: false, side: T.DoubleSide }));
          c.position.y = box.h * 0.6; c.rotation.z = Math.PI / 2 + i * TAU / 9; c.translateY(3.5); g.add(c); } g.position.z = -1.5; world.add(g); ups.push((t) => { g.rotation.z = t * 0.08; }); }
      else if (x === "halo") { const g = new T.Group(); for (let i = 0; i < 3; i++) g.add(at(tor(Math.min(R, Math.max(box.w, 1.6) * 0.62) * (0.8 + i * 0.18), 0.012, mat(i % 2 ? p.second : p.main, { glow: 0.8 }), TAU, 8, 128), 0, box.h * 0.5, 0, Math.PI / 2 + (i - 1) * 0.35, 0, 0)); world.add(g); ups.push((t) => g.children.forEach((c, i) => { c.rotation.z = t * (0.3 + i * 0.15) * (i % 2 ? -1 : 1); })); }
      else if (x === "glow") { const d = new T.Mesh(new T.CircleGeometry(R * 0.9, 64), new T.MeshBasicMaterial({ map: spriteTex("soft"), color: p.main, transparent: true, opacity: 0.55, depthWrite: false })); d.rotation.x = -Math.PI / 2; d.position.y = 0.01; world.add(d); ups.push((t) => { d.material.opacity = 0.4 + 0.2 * Math.sin(t * 2); }); }
      else if (x === "sweep") { const sw = new T.Mesh(new T.PlaneGeometry(1.4, Math.max(box.h, 2) * 2.2), new T.MeshBasicMaterial({ map: spriteTex("soft"), color: p.yellow, transparent: true, opacity: 0.55,
          depthWrite: false, blending: T.AdditiveBlending })); sw.rotation.z = 0.35; world.add(sw);
        ups.push((t) => { const u = (t * 0.32) % 1; sw.position.set((u - 0.5) * R * 4, box.h * 0.55, R * 0.6); sw.material.opacity = 0.55 * Math.sin(u * Math.PI); }); }
      else if (x === "grid") { const gh = new T.GridHelper(14, 28, p.main, p.main); gh.material.transparent = true; gh.material.opacity = 0.12; world.add(gh); }
    }
    const ctx = { main, props, world, p, mat, box, scene, camera, el, spec: sp, R };
    ctx.story = makeStory(sp.story || "float", ctx);
    return { world, ctx, ups, get story() { return ctx.story; }, get main() { return ctx.main; }, props, box, R };
  }

  // ---------------------------------------------------------------- one scene
  function mount(el, spec) {
    if (el.__m42_3d) return el.__m42_3d;
    spec = spec || {};
    const p = K.palette(spec), mat = K.makeMats(p);
    const canvas = el.querySelector("canvas") || el.appendChild(document.createElement("canvas"));
    let renderer;
    try { renderer = new T.WebGLRenderer({ canvas, antialias: true, alpha: true, powerPreference: "high-performance" }); }
    catch (e) { el.classList.add("m42-3d-off"); return null; }
    renderer.setPixelRatio(Math.min(1.75, window.devicePixelRatio || 1));
    renderer.outputEncoding = T.sRGBEncoding; renderer.toneMapping = T.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.05;
    renderer.shadowMap.enabled = true; renderer.shadowMap.type = T.PCFSoftShadowMap; renderer.localClippingEnabled = true;
    const scene = new T.Scene(); scene.environment = studio(renderer);
    const camera = new T.PerspectiveCamera(32, 1, 0.1, 200);
    scene.add(new T.HemisphereLight(0xffffff, new T.Color(p.main).lerp(new T.Color("#ffffff"), 0.6), 0.55));
    const key = new T.DirectionalLight(0xffffff, 1.15); key.position.set(4, 8, 5); key.castShadow = true; key.shadow.mapSize.set(1024, 1024);
    Object.assign(key.shadow.camera, { left: -6, right: 6, top: 6, bottom: -6 }); key.shadow.radius = 4; scene.add(key);
    const rim = new T.DirectionalLight(new T.Color(p.second).lerp(new T.Color("#ffffff"), 0.5), 0.6); rim.position.set(-6, 4, -5); scene.add(rim);
    const root = new T.Group(); scene.add(root);
    const floor = new T.Mesh(new T.CircleGeometry(9, 64), new T.ShadowMaterial({ opacity: 0.14 })); floor.rotation.x = -Math.PI / 2; floor.receiveShadow = true; root.add(floor);

    // 🎬 the scene's beats (a story told in steps: the 4B's own story of the business, cut into what the kit can show),
    // each its own objects, story and extras, played one after another; the last one stays. One beat = the old single scene.
    const beats = Array.isArray(spec.beats) && spec.beats.length ? spec.beats.slice(0, 5).map((b) => Object.assign({}, spec, { beats: null, card: null, labels: null, model: null }, b)) : [spec];
    const stages = beats.map((b) => stage(b, p, mat, root, el, scene, camera));
    const starts = []; let total = 0; beats.forEach((b, i) => { starts.push(total); total += i < beats.length - 1 ? Math.max(2, Math.min(9, +b.seconds || 4)) : 0; });
    const lastStage = stages[stages.length - 1];
    let main = lastStage.main; const props = lastStage.props, box = lastStage.box, R = lastStage.R, world = root;
    const ups = stages.length > 1 ? [] : lastStage.ups;
    // a caption per beat (its line of the story), under the scene
    let capEl = null; if (stages.length > 1 && beats.some((b) => b.caption)) { capEl = document.createElement("div"); capEl.className = "m42-3d-cap"; el.appendChild(capEl); }

    // labels near the objects (HTML, they follow them): the last beat's
    const extras = (spec.extras || []).map(String);
    const labelEls = (extras.includes("labels") || spec.labels ? (spec.labels || []) : []).slice(0, 5).map((txt) => { const d = document.createElement("div"); d.className = "m42-3d-label"; d.textContent = txt; el.appendChild(d); return d; });

    // the card
    let card = null;
    if (spec.card) {
      const c = typeof spec.card === "string" ? { title: spec.card } : spec.card;
      card = document.createElement("div"); card.className = "m42-3d-card";
      card.innerHTML = `<div class="r"><b class="st"></b><span class="pc"></span></div><div class="bar"><i></i></div><small><span class="tt"></span><span class="dt"></span></small>`;
      card.querySelector(".tt").textContent = c.title || ""; card.querySelector(".dt").textContent = c.detail || "";
      card.userData = c; el.appendChild(card);
    }

    const ctx = lastStage.ctx;
    const story = lastStage.story;
    // the camera: everything in sight, a little from above
    const fitCam = () => {
      const w = el.clientWidth || 600, h = el.clientHeight || 400;
      renderer.setSize(w, h, false); camera.aspect = w / h;
      // the objects (and how far the story moves them), not the shadow floor or the particles round them
      const bb = new T.Box3();
      stages.forEach((sg) => { const vis = sg.world.visible, sc = sg.world.scale.x; sg.world.visible = true; sg.world.scale.setScalar(1); sg.world.updateMatrixWorld(true);
        [sg.main, ...sg.props].forEach((o) => bb.expandByObject(o)); const st = sg.story;
        if (st.reach) bb.expandByPoint(st.reach);
        if (st.span) { bb.expandByPoint(new T.Vector3(st.span, 0, st.span)); bb.expandByPoint(new T.Vector3(-st.span, 0, -st.span)); }
        sg.world.visible = vis; sg.world.scale.setScalar(sc); });
      bb.expandByScalar(0.15);
      const s = bb.getBoundingSphere(new T.Sphere());
      const fov = camera.fov * Math.PI / 180, fovH = 2 * Math.atan(Math.tan(fov / 2) * camera.aspect);
      const dist = s.radius / Math.sin(Math.min(fov, fovH) / 2) * (spec.zoom ? 1 / spec.zoom : stages.length > 1 ? 0.62 : 0.8);
      const el2 = 0.38, az = 0.0;
      camera.position.set(s.center.x + Math.sin(az) * dist * Math.cos(el2), s.center.y + dist * Math.sin(el2), s.center.z + Math.cos(az) * dist * Math.cos(el2));
      camera.lookAt(s.center); camera.updateProjectionMatrix();
      camBase = { c: s.center.clone(), dist, el: el2 };
    };

    let camBase = null;
    const camMove = (mode, u) => {  // a beat's camera move over its time u (0..1)
      if (!camBase || !mode || mode === "still") return;
      const e2 = ease(clamp(u));
      let d = camBase.dist, el2 = camBase.el, az = 0;
      if (mode === "zoom_in") d *= 1.3 - 0.45 * e2;
      else if (mode === "pull_back") d *= 0.8 + 0.4 * e2;
      else if (mode === "rise") { el2 = 0.2 + 0.32 * e2; d *= 1.15 - 0.15 * e2; }  // (from low and a step back: nothing cut off)
      else if (mode === "circle") az = -0.5 + 1.0 * e2;
      camera.position.set(camBase.c.x + Math.sin(az) * d * Math.cos(el2), camBase.c.y + d * Math.sin(el2), camBase.c.z + Math.cos(az) * d * Math.cos(el2));
      camera.lookAt(camBase.c);
    };
    // turning by hand
    let spin = spec.angle || -0.35, drag = null, idle = 0;
    canvas.addEventListener("pointerdown", (e) => { drag = { x: e.clientX, s: spin }; });
    window.addEventListener("pointermove", (e) => { if (drag) { spin = drag.s + (e.clientX - drag.x) * 0.008; idle = 0; } });
    window.addEventListener("pointerup", () => { drag = null; });

    const still = !!window.M42_STILL || matchMedia("(prefers-reduced-motion: reduce)").matches;  // (M42's own pictures: the scene at rest)
    const clock = new T.Clock();
    let visible = true, raf = 0, last = 0;
    const tick = () => {
      raf = 0;
      const t = still ? (story.cycle || 8) * 0.92 : clock.getElapsedTime(), dt = Math.min(0.05, t - last); last = t;
      idle += dt;
      const T0 = still ? total + (story.cycle || 8) * 0.92 : t;  // (reduced motion: the scene at rest, its last beat)
      let active = lastStage;
      stages.forEach((sg, i) => {
        if (stages.length === 1) { sg.story.update(t, dt); return; }
        const s0 = starts[i], s1 = i < stages.length - 1 ? starts[i + 1] : Infinity, fade = 0.7;
        const k = Math.min(i ? ease(clamp((T0 - (s0 - fade)) / fade)) : ease(clamp(T0 / fade)), i < stages.length - 1 ? 1 - ease(clamp((T0 - (s1 - fade)) / fade)) : 1);
        sg.world.visible = k > 0.002; sg.world.scale.setScalar(Math.max(0.002, k));
        if (sg.world.visible) { sg.story.update(T0 - s0, dt); sg.ups.forEach((f) => f(T0 - s0)); }
        if (T0 >= s0 && T0 < s1) active = sg;
        if (capEl && T0 >= s0 && T0 < s1 && capEl._i !== i) { capEl._i = i; capEl.classList.remove("on"); void capEl.offsetWidth; capEl.textContent = beats[i].caption || ""; if (beats[i].caption) capEl.classList.add("on"); }
      });
      if (stages.length > 1) { const ai = stages.indexOf(active), s0 = starts[ai], s1 = ai < stages.length - 1 ? starts[ai + 1] : s0 + 4;
        camMove(beats[ai].camera, (T0 - s0) / Math.max(1, s1 - s0)); }
      if (!drag && !still && active.story.autoSpin !== false) spin += dt * 0.12;
      root.rotation.y = spin;
      world.traverse((o) => { const u = o.userData;
        if (u.flicker) o.scale.set(1 + Math.sin(t * 23 + o.id) * 0.05, 1 + Math.sin(t * 17 + o.id) * 0.1, 1);
        if (u.spinZ) o.rotation.z = t * u.spinZ;
        if (u.propeller) o.rotation.y = t * 30;
        if (u.printhead) o.position.set(Math.sin(t * 2.3) * 0.6, o.position.y, Math.cos(t * 1.7) * 0.5);
        if (u.electron) { const a = t * 2 + u.electron.phase, rr = 0.95, i = u.electron.ring; const v = new T.Vector3(Math.cos(a) * rr, Math.sin(a) * rr, 0).applyEuler(new T.Euler(Math.PI / 2 + (i - 1) * 0.9, i * 1.05, 0)); o.position.set(v.x, 1.2 + v.y, v.z); }
        if (u.hand) o.rotation.z = -t * u.hand.speed; });
      ups.forEach((f) => f(t));
      if (card) card.style.display = stages.length === 1 || T0 >= starts[stages.length - 1] ? "" : "none";
      if (card) {
        const c = card.userData, pr = story.progress ? story.progress(t) : null, states = c.states || [];
        if (pr === null) { card.classList.add("idle"); card.querySelector(".st").textContent = (states[0] || c.status || "LIVE").toUpperCase(); card.querySelector(".pc").textContent = c.value || ""; card.querySelector(".bar").style.display = "none"; }
        else { const done = pr >= 0.999; card.classList.toggle("done", done); card.querySelector(".st").textContent = ((done ? states[1] : states[0]) || (done ? "Ready" : "In progress")).toUpperCase();
          card.querySelector(".pc").textContent = done ? (c.doneValue || "✓") : Math.round(pr * 100) + "%"; card.querySelector("i").style.width = Math.round(pr * 100) + "%"; }
      }
      const atRest = stages.length === 1 || T0 >= starts[stages.length - 1];
      labelEls.forEach((d, i) => { d.style.display = atRest && d.textContent && (i < props.length || i === 0) ? "" : "none"; });  // (a side thing with no word: no label)
      if (labelEls.length && atRest) { const r = el.getBoundingClientRect(); labelEls.forEach((d, i) => { const o = props[i] || main; const v = new T.Box3().setFromObject(o).getCenter(new T.Vector3()); v.y = new T.Box3().setFromObject(o).max.y; v.project(camera);
        let x = (v.x + 1) / 2 * r.width, y = (1 - v.y) / 2 * r.height; const w = d.offsetWidth + 6, h = d.offsetHeight + 4;
        for (let k = 0; k < i; k++) { const q = labelEls[k]._at; if (q && Math.abs(q.x - x) < (w + q.w) / 2 && Math.abs(q.y - y) < h) y = q.y - h; }
        // (inside the scene's own box: a label beside an object near the edge went past the page, "Soun|", 2026-11-16)
        x = Math.min(Math.max(x, w / 2 + 4), r.width - w / 2 - 4); y = Math.min(Math.max(y, h * 1.2 + 4), r.height - 4);
        d._at = { x, y, w }; d.style.left = x + "px"; d.style.top = y + "px"; }); }
      renderer.render(scene, camera);
      if (visible && !still) raf = requestAnimationFrame(tick);
    };
    fitCam();
    new ResizeObserver(() => { fitCam(); if (!raf) tick(); }).observe(el);
    new IntersectionObserver((es) => { visible = es[0].isIntersecting; if (visible && !raf && !still) raf = requestAnimationFrame(tick); }, { threshold: 0.01 }).observe(el);
    tick();
    const api = { scene, camera, renderer, ctx, story, spec };
    el.__m42_3d = api;
    return api;
  }

  // ---------------------------------------------------------------- stories
  function makeStory(name, c) {
    const { main, props, world, p, mat, box } = c;
    const parts = () => (c.main.userData.parts || c.main.children).filter((o) => o.isObject3D);
    const save = (o) => { if (!o.userData.base) o.userData.base = { p: o.position.clone(), r: o.rotation.clone(), s: o.scale.clone() }; return o.userData.base; };
    const scrollP = () => { const r = c.el.getBoundingClientRect(), vh = innerHeight || 800; return clamp(1 - (r.top + r.height) / (vh + r.height)); };
    const vessel = main.userData.vessel;
    const S = {};
    S.float = { cycle: 6, update(t) { [main, ...props].forEach((o, i) => { const h = o.userData.home; o.position.y = h.y + 0.12 + Math.sin(t * 1.3 + i) * 0.1; o.rotation.z = Math.sin(t * 0.9 + i) * 0.04; }); } };
    S.turntable = { cycle: 8, autoSpin: false, update(t) { main.rotation.y = t * 0.5; props.forEach((o, i) => { o.position.y = o.userData.home.y + 0.08 + Math.sin(t * 1.4 + i) * 0.08; }); c.world.rotation.y = -0.2; } };
    S.levitate = { cycle: 8, update(t) { main.position.y = main.userData.home.y + 0.35 + Math.sin(t * 1.2) * 0.12; main.rotation.y = t * 0.4; props.forEach((o, i) => { o.position.y = o.userData.home.y + 0.1 + Math.sin(t * 1.4 + i) * 0.08; }); } };
    S.orbit = { cycle: 10, span: c.R * 1.1, update(t) { main.rotation.y = t * 0.2; props.forEach((o, i) => { const a = t * 0.5 + i * TAU / Math.max(1, props.length), r = c.R * 1.05;
      o.position.set(Math.cos(a) * r, box.h * (0.35 + 0.25 * Math.sin(a + i)), Math.sin(a) * r * 0.8); o.rotation.y = -a; }); } };
    S.swing = { cycle: 4, update(t) { main.rotation.z = Math.sin(t * 2.2) * 0.25; } };
    S.bounce = { cycle: 1.6, update(t) { const u = (t % 1.2) / 1.2, h = Math.abs(Math.sin(u * Math.PI)); main.position.y = main.userData.home.y + h * 0.9; const sq = h < 0.15 ? 1 - (0.15 - h) : 1; main.scale.set(main.userData.k * (2 - sq), main.userData.k * sq, main.userData.k * (2 - sq)); } };
    S.spin = { cycle: 4, update(t) { const u = t % 4; main.rotation.y = u < 1.2 ? ease(u / 1.2) * TAU * 2 : 0; main.position.y = main.userData.home.y + 0.2 + Math.sin(t * 1.5) * 0.08; } };
    S.flip = { cycle: 5, update(t) { const u = t % 5; main.rotation.x = u < 0.9 ? ease(u / 0.9) * Math.PI * 2 : 0; } };
    S.pulse = { cycle: 1.2, update(t) { const u = t % 1.2, k = 1 + 0.08 * Math.exp(-u * 8) * Math.sin(u * 30) + 0.06 * Math.exp(-Math.max(0, u - 0.25) * 8) * (u > 0.25 ? 1 : 0); main.scale.setScalar(main.userData.k * k); } };
    S.wave = { cycle: 4, update(t) { const all = [main, ...props]; all.forEach((o, i) => { o.position.y = o.userData.home.y + 0.15 + Math.sin(t * 2.4 - i * 0.8) * 0.18; }); } };
    S.scroll_spin = { cycle: 6, autoSpin: false, update(t) { c.world.rotation.y = -0.3 + scrollP() * TAU + Math.sin(t * 0.5) * 0.05; main.position.y = main.userData.home.y + 0.1 + Math.sin(t) * 0.06; } };
    S.scroll_rise = { cycle: 6, update(t) { const s = scrollP(); main.position.y = main.userData.home.y + s * 0.8; main.rotation.y = s * Math.PI; props.forEach((o, i) => { o.position.y = o.userData.home.y + s * (0.4 + i * 0.2); }); } };
    S.grow = { cycle: 7, progress: (t) => clamp((t % 7) / 2.2), update(t) { const u = t % 7; [main, ...props].forEach((o, i) => { const k = o.userData.k, x = clamp((u - i * 0.25) / 0.9);
      const out = u > 6.2 ? 1 - clamp((u - 6.2) / 0.6) : 1; o.scale.setScalar(Math.max(0.001, k * back(x) * out)); }); } };
    S.pop = { cycle: 7, progress: (t) => clamp((t % 7) / (0.6 + props.length * 0.45)), update(t) { const u = t % 7; main.position.y = main.userData.home.y + 0.1 + Math.sin(t) * 0.06;
      props.forEach((o, i) => { const x = clamp((u - 0.4 - i * 0.45) / 0.5), out = u > 6.3 ? 1 - clamp((u - 6.3) / 0.5) : 1; o.scale.setScalar(Math.max(0.001, o.userData.k * back(x) * out)); o.position.y = o.userData.home.y + 0.3 + Math.sin(t * 1.6 + i) * 0.08; }); } };
    S.assemble = { cycle: 8, progress: (t) => clamp((t % 8) / 3.2), update(t) { const u = t % 8, ps = parts();
      ps.forEach((o, i) => { const b = save(o), x = clamp((u - i * (2.2 / Math.max(1, ps.length))) / 1.0), out = u > 7 ? clamp((u - 7) / 0.9) : 0;
        const dir = b.p.clone().sub(new T.Vector3(0, box.h / 2 / (c.main.userData.k || 1), 0)).normalize().multiplyScalar(2.5 / (c.main.userData.k || 1)); dir.y += 1.5 / (c.main.userData.k || 1);
        const k = ease(x) * (1 - out); o.position.copy(b.p.clone().add(dir.multiplyScalar(1 - k))); o.rotation.set(b.r.x + (1 - k) * 1.2, b.r.y + (1 - k) * 2, b.r.z); o.visible = x > 0 || out > 0; }); } };
    S.explode = { cycle: 7, update(t) { const u = 0.5 - 0.5 * Math.cos(t * TAU / 7), ps = parts(); const cy = box.h / 2 / (c.main.userData.k || 1);
      ps.forEach((o) => { const b = save(o), d = b.p.clone().sub(new T.Vector3(0, cy, 0)); if (d.length() < 1e-3) d.set(0, 1, 0); o.position.copy(b.p.clone().add(d.normalize().multiplyScalar(u * 0.9 / (c.main.userData.k || 1)))); }); } };
    S.stack = { cycle: 8, progress: (t) => clamp((t % 8) / 4), update(t) { const u = t % 8, ps = parts().slice().sort((a, b) => save(a).p.y - save(b).p.y);
      ps.forEach((o, i) => { const b = save(o), x = clamp((u - i * (3.6 / Math.max(1, ps.length))) / 0.55), out = u > 7.2 ? clamp((u - 7.2) / 0.6) : 0;
        const fall = (1 - (x < 1 ? x * x : 1)) * 3 / (c.main.userData.k || 1); const bnc = x >= 1 ? Math.max(0, Math.sin(clamp((u - i * (3.6 / ps.length) - 0.55) / 0.3) * Math.PI)) * 0.15 / (c.main.userData.k || 1) : 0;
        o.position.set(b.p.x, b.p.y + fall + bnc + out * 3 / (c.main.userData.k || 1), b.p.z); o.visible = x > 0; }); } };
    S.rain = { cycle: 8, update(t) {
      if (!S.rain.items) { S.rain.items = []; const src = props[0] || null; for (let i = 0; i < 14; i++) { const o = src ? src.clone() : sph(0.15, mat(p.second)); o.scale.multiplyScalar(src ? 0.45 : 1); o.userData = { x: (Math.random() - 0.5) * c.R * 1.8, z: c.R * 0.3 + Math.random() * 0.8, d: Math.random() * 6, r: Math.random() * TAU }; world.add(o); S.rain.items.push(o); } if (src) src.visible = false; }
      S.rain.items.forEach((o) => { const u = ((t + o.userData.d) % 6) / 6; const y = Math.max(0.1, 4 - u * 9); o.position.set(o.userData.x, y, o.userData.z); o.rotation.set(t + o.userData.r, o.userData.r, 0); o.visible = u < 0.95; }); } };
    S.drive = { cycle: 10, autoSpin: false, span: c.R * 1.3, update(t) { if (!S.drive.road) { S.drive.road = at(tor(c.R * 1.25, 0.25, mat(p.dark, { rough: 0.9 }), TAU, 8, 96), 0, 0.02, 0, Math.PI / 2); S.drive.road.scale.z = 0.02; world.add(S.drive.road); }
      const a = t * 0.45, r = c.R * 1.25; main.position.set(Math.cos(a) * r, main.userData.home.y, Math.sin(a) * r); main.rotation.y = -a; c.world.rotation.y = -0.25; } };
    S.sunrise = { cycle: 10, update(t) { if (!S.sunrise.sun) { S.sunrise.sun = sph(0.7, mat(p.yellow, { glow: 1.2 })); world.add(S.sunrise.sun); }
      const u = (t % 10) / 10; S.sunrise.sun.position.set(-c.R * 0.6, -0.6 + ease(clamp(u * 1.6)) * box.h * 1.3, -c.R * 1.4); c.scene.children.forEach((l) => { if (l.isDirectionalLight && l.castShadow) l.color.setHSL(0.1, 0.6, 0.5 + 0.5 * clamp(u * 1.6)); }); } };
    S.reveal = { cycle: 7, progress: (t) => clamp((t % 7) / 2.5), update(t) { const u = t % 7, x = ease(clamp(u / 2.5)), out = u > 6.3 ? clamp((u - 6.3) / 0.6) : 0;
      main.position.y = main.userData.home.y - (1 - x + out) * box.h; if (!S.reveal.plane) { S.reveal.plane = new T.Plane(new T.Vector3(0, 1, 0), 0); c.main.traverse((m) => { if (m.material) { m.material = (Array.isArray(m.material) ? m.material : [m.material]).map((q) => { const n = q.clone(); n.clippingPlanes = [S.reveal.plane]; return n; }); if (m.material.length === 1) m.material = m.material[0]; } }); } } };
    S.build_up = { cycle: 9, progress: (t) => clamp((t % 9) / 7), update(t) {
      if (!S.build_up.plane) { S.build_up.plane = new T.Plane(new T.Vector3(0, -1, 0), 0);
        // a 3D printer among the objects: it stands round the main object, which is printed inside it (bed height)
        const pr = props.find((o) => /printer/.test(o.userData.name || ""));
        if (pr) { const mb2 = new T.Box3().setFromObject(c.main).getSize(new T.Vector3()); const want = Math.max(mb2.x, mb2.z, mb2.y * 0.75) * 1.9;
          const pb = new T.Box3().setFromObject(pr).getSize(new T.Vector3()); pr.scale.multiplyScalar(want / Math.max(pb.x, pb.z)); pr.position.set(0, 0, 0); pr.rotation.y = 0;
          const bed = new T.Box3().setFromObject(pr); c.main.position.y = bed.min.y + (bed.max.y - bed.min.y) * 0.17; c.main.userData.home = c.main.position.clone(); pr.userData.home = pr.position.clone(); }
        c.main.traverse((m) => { if (m.isMesh && m.material) m.material = (Array.isArray(m.material) ? m.material.map((q) => { const n = q.clone(); n.clippingPlanes = [S.build_up.plane]; n.clipShadows = true; return n; }) : (() => { const n = m.material.clone(); n.clippingPlanes = [S.build_up.plane]; n.clipShadows = true; return n; })()); });
        S.build_up.ring = at(tor(Math.max(box.w, 1) * 0.42, 0.015, mat(p.orange, { glow: 2 }), TAU, 8, 96), 0, 0, 0, Math.PI / 2); world.add(S.build_up.ring); }
      const u = t % 9, x = clamp(u / 7), y0 = c.main.position.y, top = box.h + 0.05; S.build_up.plane.constant = y0 + 0.02 + x * top; S.build_up.ring.position.y = y0 + 0.02 + x * top; S.build_up.ring.visible = x < 0.995; S.build_up.ring.material.opacity = 1; } };
    // fill / pour: a liquid rises in the vessel (its inside); pour: a kettle or a bottle tips over it and a stream falls
    const liquidCol = new T.Color(LIQUIDS[c.spec.liquid] || (c.spec.liquid === "paint" ? hexStr(p.main) : (vessel && LIQUIDS[vessel.liquid]) || "#3b2314"));
    function fillStory(pour) {
      if (!vessel) return S.grow;
      const k = c.main.userData.k, liq = new T.Mesh(new T.BufferGeometry(), mat(liquidCol, { rough: 0.15, clear: 1, side: T.DoubleSide }));
      const surfTex = c.spec.liquid === "coffee" || !c.spec.liquid && !vessel.liquid ? canvasTex((g, w, h) => { const r = g.createRadialGradient(w / 2, h / 2, 6, w / 2, h / 2, w / 2);
        r.addColorStop(0, "#d8b48a"); r.addColorStop(0.55, "#b9865a"); r.addColorStop(0.85, "#8a5a36"); r.addColorStop(1, "#5a3620"); g.fillStyle = r; g.fillRect(0, 0, w, h);
        g.fillStyle = "rgba(255,244,228,.85)"; g.beginPath(); g.moveTo(128, 175); g.bezierCurveTo(60, 130, 80, 70, 128, 100); g.bezierCurveTo(176, 70, 196, 130, 128, 175); g.fill(); }) : null;
      const surf = new T.Mesh(new T.CircleGeometry(1, 64), surfTex ? mat("#fff", { map: surfTex, rough: 0.4 }) : mat(liquidCol.clone().offsetHSL(0, 0, 0.08), { rough: 0.1, clear: 1 }));
      surf.rotation.x = -Math.PI / 2; c.main.add(liq); c.main.add(surf);
      const setLevel = (f) => { const top = vessel.bottom + (vessel.top - vessel.bottom) * f, pts = [];
        for (let i = 0; i <= 12; i++) { const y = vessel.bottom + (top - vessel.bottom) * i / 12; pts.push(new T.Vector2(vessel.inner(y), y)); }
        liq.geometry.dispose(); liq.geometry = new T.LatheGeometry(pts, 64); liq.visible = surf.visible = f > 0.01; surf.position.y = top; surf.scale.setScalar(vessel.inner(top)); surf.rotation.z = f * 2.2; };
      let pourer = null, tipPt = null, stream = null;
      if (pour) {
        const kind = c.spec.pourer || (["wine", "juice", "water", "soda", "beer", "lemonade", "oil", "milk"].includes(c.spec.liquid) ? (c.spec.liquid === "wine" ? "wine_bottle" : "bottle") : "kettle");
        pourer = build(kind, p, mat, c.spec); fit(pourer, kind === "kettle" ? 1.1 : 1.3);
        const holder = new T.Group(); holder.add(pourer); world.add(holder); pourer.userData.holder = holder;
        tipPt = new T.Object3D(); (pourer.userData.spout ? pourer : pourer).add(tipPt);
        if (pourer.userData.spout) tipPt.position.copy(pourer.userData.spout); else { const bb = new T.Box3().setFromObject(pourer); tipPt.position.set(0, (bb.max.y - pourer.position.y) / pourer.scale.y, 0); }
        stream = new T.Mesh(new T.CylinderGeometry(0.022, 0.036, 1, 16, 1, true), mat(liquidCol, { rough: 0.08, clear: 1 })); world.add(stream);
      }
      const POUR = 6.5, REST = 3.0;
      return { cycle: POUR + REST, reach: pour ? new T.Vector3(-2.2, box.h + 1.8, 0) : null,
        progress: (t) => { const u = t % (POUR + REST); return u < POUR ? ease(clamp(u / POUR)) : 1; },
        update(t) {
          const u = t % (POUR + REST), on = u < POUR, f = on ? ease(clamp(u / POUR)) : 1; setLevel(f);
          if (!pour) return;
          const h = pourer.userData.holder, tipIn = clamp(u / 0.8), out = on ? 0 : clamp((u - POUR) / 0.8);
          const isK = !!pourer.userData.spout;
          h.position.set(-(c.R * 0.75) - out * 0.6, box.h * (isK ? 1.05 : 1.2) + out * 0.35, 0);
          h.rotation.z = -(isK ? 0.1 + 0.45 * tipIn : 0.6 + 1.3 * tipIn) * (1 - out);
          h.updateMatrixWorld(true);
          const from = tipPt.getWorldPosition(new T.Vector3()); world.worldToLocal(from);
          const sY = c.main.position.y + (vessel.bottom + (vessel.top - vessel.bottom) * f) * k;
          const show = on && u > 0.6 && u < POUR - 0.15; stream.visible = show;
          if (show) { const to = new T.Vector3(c.main.position.x + Math.sin(t * 9) * 0.015, sY, c.main.position.z);
            stream.position.copy(from.clone().add(to).multiplyScalar(0.5)); stream.scale.set(1, from.distanceTo(to), 1);
            stream.quaternion.setFromUnitVectors(new T.Vector3(0, 1, 0), from.clone().sub(to).normalize()); }
        } };
    }
    S.fill = fillStory(false); S.pour = fillStory(true);
    return S[name] || S.float;
  }

  // ---------------------------------------------------------------- a model file (the user's, or one found online)
  // a bundled model: a box of the right size at once (the scene is laid out round it), the model put in when loaded,
  // scaled to that box and stood on the floor
  function libModel(url, key) {
    const g = new T.Group(); g.userData.name = key;
    const stand = new T.Mesh(new T.BoxGeometry(1, 1.6, 1), new T.MeshBasicMaterial({ visible: false })); stand.position.y = 0.8; g.add(stand);
    if (T.GLTFLoader) new T.GLTFLoader().load(url, (gl) => {
      const m = gl.scene; m.traverse((o) => { if (o.isMesh) { o.castShadow = o.receiveShadow = true; if (o.material && o.material.map) o.material.map.encoding = T.sRGBEncoding; } });
      const b = new T.Box3().setFromObject(m), d = b.getSize(new T.Vector3()); const k = 1.6 / Math.max(d.y, Math.max(d.x, d.z) * 0.85, 1e-3);
      m.scale.multiplyScalar(k); const b2 = new T.Box3().setFromObject(m), c = b2.getCenter(new T.Vector3());
      m.position.x -= c.x; m.position.z -= c.z; m.position.y -= b2.min.y; g.remove(stand); g.add(m);
    }, undefined, () => {});
    return g;
  }
  function loadModel(url, p, mat) {
    return new Promise((ok, no) => {
      if (/\.(glb|gltf)(\?|$)/i.test(url) && T.GLTFLoader) new T.GLTFLoader().load(url, (g) => { g.scene.traverse((m) => { if (m.isMesh) { m.castShadow = m.receiveShadow = true; } }); g.scene.userData.parts = g.scene.children.slice(); ok(g.scene); }, undefined, no);
      else if (/\.stl(\?|$)/i.test(url) && T.STLLoader) new T.STLLoader().load(url, (geo) => { geo.computeVertexNormals(); geo.rotateX(-Math.PI / 2); const m = new T.Mesh(geo, mat(p.main, { rough: 0.4 })); m.castShadow = true; ok(group(m)); }, undefined, no);
      else ok(null);
    });
  }

  // ---------------------------------------------------------------- start every scene on the page
  function start() {
    document.querySelectorAll("[data-m42-3d]").forEach((el) => {
      if (el.__m42_3d) return;
      let spec = {}; try { spec = JSON.parse(el.getAttribute("data-m42-3d") || "{}"); } catch (e) { spec = {}; }
      el.classList.add("m42-3d");
      mount(el, spec);
    });
  }
  window.M42_3D = { mount, start, catalog: () => Object.keys(MAKERS).sort(), stories: STORIES.slice(), extras: EXTRAS.slice(), cameras: CAMERAS.slice(), liquids: Object.keys(LIQUIDS) };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start); else start();
})();
