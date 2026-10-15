// Nerava app splash. Shared by the full-screen portrait render (index.html) and the
// phone-frame showcase (../5-app-splash-device). Defines window.seek for one screen.
// Option 2's motion, plus a soft blue gradient ring that blooms around the logo at the end.
function nervaSplash(host, { w = 1080, h = 1920, scale = 1.0, ringD = 900 } = {}) {
  host.style.cssText = `position:absolute;left:0;top:0;width:${w}px;height:${h}px;overflow:hidden;background:${NV.C.bg}`;
  const cam = document.createElement('div');
  host.appendChild(cam);

  // --- ring layers (CSS), centred on the logo, behind it
  const ringBox = document.createElement('div');
  ringBox.style.cssText = `position:absolute;left:${w / 2 - ringD / 2}px;top:${h / 2 - ringD / 2}px;width:${ringD}px;height:${ringD}px`;
  const layer = (css) => { const d = document.createElement('div'); d.style.cssText = 'position:absolute;inset:0;border-radius:50%;' + css; ringBox.appendChild(d); return d; };
  const BLUES = '#2563EB, #3B82F6, #60A5FA, #A5C8FF, #38BDF8, #3B82F6, #4F7BF7, #2563EB';
  const wash = layer(`background:radial-gradient(circle, rgba(59,130,246,0.05) 0%, rgba(59,130,246,0.025) 40%, rgba(59,130,246,0) 70%)`);
  const glow = layer(`-webkit-mask:radial-gradient(circle closest-side, transparent 62%, #000 86%, transparent 100%);filter:blur(30px)`);
  const ring = layer(`-webkit-mask:radial-gradient(circle closest-side, transparent 80%, #000 89%, #000 92%, transparent 99%);filter:blur(6px)`);
  cam.appendChild(ringBox);

  const S = NV.build(Object.assign(document.createElement('div'), {}), { w, h, scale });
  cam.appendChild(S.svg.parentNode);
  const { bolt, letters } = S;
  const glyphs = [...letters, bolt];
  const X0 = 100, X1 = 780, TAIL = 110, BOLT_X = 590, BCX = 615, BCY = 140;

  const front = (t) => M.lerp(X0, X1, M.prog(t, T.charge, T.charge + T.chargeDur, M.ease.inOut));
  let lo = T.charge, hi = T.charge + T.chargeDur;
  for (let i = 0; i < 40; i++) { const m = (lo + hi) / 2; if (front(m) < BOLT_X) lo = m; else hi = m; }
  const FIRE = hi, RING = FIRE + T.ringDelay;

  const grad = S.el('linearGradient', { id: 'charge', gradientUnits: 'userSpaceOnUse', x1: X0, y1: 0, x2: X1, y2: 0,
    gradientTransform: `translate(0 140) skewX(${-Math.atan(NV.SLANT) * 180 / Math.PI}) translate(0 -140)` }, S.defs);
  const stops = [0, 1, 2, 3].map(() => S.el('stop', {}, grad));
  glyphs.forEach((g) => {
    g.len = g.path.getTotalLength();
    g.path.setAttribute('stroke', NV.C.ink);
    g.path.setAttribute('stroke-dasharray', `${g.len} ${g.len}`);
  });
  letters.forEach((L) => L.path.setAttribute('fill', 'url(#charge)'));

  function mix(a, b, k) {
    const hx = (s, i) => parseInt(s.slice(1 + 2 * i, 3 + 2 * i), 16);
    return '#' + [0, 1, 2].map((i) => Math.round(M.lerp(hx(a, i), hx(b, i), k)).toString(16).padStart(2, '0')).join('');
  }

  const seek = (t) => {
    // outlines draw on, then fade once filled (stroke a touch heavier: the logo is smaller here)
    glyphs.forEach((g, i) => {
      const p = M.prog(t, T.draw + i * 0.07, T.draw + i * 0.07 + 0.8, M.ease.inOut);
      g.path.setAttribute('stroke-dashoffset', g.len * (1 - p));
      const fade = g === bolt ? M.prog(t, FIRE, FIRE + 0.15) : M.prog(t, T.charge + T.chargeDur - 0.2, T.charge + T.chargeDur + 0.3);
      g.path.setAttribute('stroke-opacity', 0.34 * (1 - fade));
      g.path.setAttribute('stroke-width', fade >= 1 ? 0 : 1.4);
    });
    // charge front
    const f = front(t), ink = f - TAIL;
    const off = (x) => M.clamp((x - X0) / (X1 - X0));
    const set = (s, x, c, o) => { s.setAttribute('offset', off(x)); s.setAttribute('stop-color', c); s.setAttribute('stop-opacity', o); };
    set(stops[0], ink, NV.C.ink, 1); set(stops[1], f - 6, NV.C.blue, 1); set(stops[2], f, NV.C.blue, 1); set(stops[3], f + 0.01, NV.C.blue, 0);
    // bolt fires
    const on = t >= FIRE;
    bolt.path.setAttribute('fill-opacity', on ? 1 : 0);
    const pop = 0.2 * (M.spring(t, FIRE, { freq: 5, damping: 0.6 }) - M.spring(t, FIRE + 0.06, { freq: 2.6, damping: 0.62 }));
    const twist = on ? -7 * (1 - M.spring(t, FIRE, { freq: 2.4, damping: 0.55 })) : 0;
    bolt.inner.setAttribute('transform', NV.tr({ s: 1 + pop, r: twist, ox: BCX, oy: BCY }));
    bolt.path.setAttribute('fill', mix(NV.C.blue, '#DCEBFF', on ? 0.8 * Math.exp(-(t - FIRE) * 7) : 0));
    const kick = -3.5 * (M.spring(t, FIRE, { freq: 7, damping: 0.7 }) - M.spring(t, FIRE + 0.05, { freq: 2.8, damping: 0.7 }));
    S.lettersG.setAttribute('transform', NV.tr({ x: kick }));

    // ring: blooms out from just inside its final size, the colours turning slowly
    const rs = M.spring(t, RING, { freq: 1.1, damping: 0.82 });
    const ro = M.prog(t, RING, RING + 0.7, M.ease.out);
    const spin = 200 + 26 * Math.max(0, t - RING) + 90 * rs;                // degrees; drifts forever
    const cg = `conic-gradient(from ${spin}deg, ${BLUES})`;
    ring.style.background = cg; glow.style.background = cg;
    ringBox.style.transform = `scale(${0.62 + 0.38 * rs})`;
    ring.style.opacity = ro; glow.style.opacity = 0.4 * ro;
    wash.style.opacity = ro;

    // camera: one slow push in that lands as the bolt settles
    const c = M.camera(t, [{ t: 0, x: w / 2, y: h / 2, zoom: 0.93 }, { t: FIRE + 0.5, x: w / 2, y: h / 2, zoom: 1, e: M.ease.inOut }]);
    M.applyCamera(cam, c, w, h);
  };
  return { seek, FIRE, RING };
}
