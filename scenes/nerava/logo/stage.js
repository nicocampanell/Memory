// Shared stage for the Nerava logo scenes. Builds the traced logo as SVG, one group per
// glyph, laid out so the final frame is the static logo centred at 1920x1080.
// Pure setup: nothing here depends on time. Load after glyphs.js and motion.js.
(function () {
  const C = { bg: '#F7F6F1', ink: '#0B1020', blue: '#3B82F6' }; // sampled from logo/source.png
  const SCALE = 1.75;          // source px -> frame px (logo ~913 px wide)
  const SLANT = 0.378;         // the bolt's left edge: x moves this far left per unit down
  const W = 1920, H = 1080;
  const NS = 'http://www.w3.org/2000/svg';
  const G = window.NERAVA_GLYPHS;
  const [bx0, by0, bx1, by1] = G.bbox;

  const el = (tag, attrs = {}, parent) => {
    const e = document.createElementNS(NS, tag);
    for (const k in attrs) e.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(e);
    return e;
  };

  // translate(x,y), then rotate/scale about the origin (ox, oy). Units are source px.
  function tr({ x = 0, y = 0, s = 1, sx = 1, sy = 1, r = 0, ox = 0, oy = 0 } = {}) {
    return `translate(${x} ${y}) translate(${ox} ${oy}) rotate(${r}) scale(${s * sx} ${s * sy}) translate(${-ox} ${-oy})`;
  }

  // opts: {w, h, scale} for frames other than 1920x1080 (the logo stays centred)
  function build(host, { w = W, h = H, scale = SCALE } = {}) {
    const tx = w / 2 - ((bx0 + bx1) / 2) * scale;
    const ty = h / 2 - ((by0 + by1) / 2) * scale;
    host.style.cssText = `position:absolute;left:0;top:0;width:${w}px;height:${h}px`;
    const svg = el('svg', { width: w, height: h, viewBox: `0 0 ${w} ${h}` }, host);
    const defs = el('defs', {}, svg);
    const world = el('g', { transform: `translate(${tx} ${ty}) scale(${scale})` }, svg);
    const make = (g, parent) => {
      const wrap = el('g', {}, parent);
      const inner = el('g', {}, wrap);
      const path = el('path', { d: g.d, fill: g.id === 'bolt' ? C.blue : C.ink }, inner);
      const bb = path.getBBox();
      return { id: g.id, wrap, inner, path, bb, cx: bb.x + bb.width / 2, cy: bb.y + bb.height / 2 };
    };
    const lettersG = el('g', {}, world);
    const letters = G.glyphs.filter((g) => g.id !== 'bolt').map((g) => make(g, lettersG));
    const bolt = make(G.glyphs.find((g) => g.id === 'bolt'), world);
    return { svg, defs, world, lettersG, letters, bolt, el };
  }

  // Bolt left edge as a line in source px: x at height y.
  const boltEdgeX = (y) => 616 - SLANT * (y - 76);

  window.NV = { C, SCALE, SLANT, W, H, build, tr, el, boltEdgeX };
})();
