// Motion library for seek(t) scenes. Every function here is a pure function
// of its inputs: no timers, no requestAnimationFrame, no state between frames.
// Load with a classic <script> tag; everything hangs off window.M.
(function () {
  const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
  const lerp = (a, b, p) => a + (b - a) * p;
  const inv = (a, b, x) => (b === a ? 0 : (x - a) / (b - a));

  // Eases take p in [0,1] and return [0,1].
  const ease = {
    linear: (p) => p,
    inOut: (p) => (p < 0.5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2),
    out: (p) => 1 - Math.pow(1 - p, 3),
    in: (p) => p * p * p,
    outExpo: (p) => (p >= 1 ? 1 : 1 - Math.pow(2, -10 * p)),
    inOutExpo: (p) =>
      p <= 0 ? 0 : p >= 1 ? 1 : p < 0.5 ? Math.pow(2, 20 * p - 10) / 2 : (2 - Math.pow(2, -20 * p + 10)) / 2,
  };

  // Progress of t through [t0, t1], eased.
  const prog = (t, t0, t1, e = ease.inOut) => e(clamp(inv(t0, t1, t)));

  // Closed-form damped spring from 0 to 1, started at t0.
  // freq is the natural frequency in Hz; damping < 1 gives overshoot
  // (0.75 ≈ 3% overshoot, 0.6 ≈ 9%). Returns 0 before t0.
  function spring(t, t0, { freq = 2.2, damping = 0.75 } = {}) {
    const x = t - t0;
    if (x <= 0) return 0;
    const w = 2 * Math.PI * freq;
    if (damping >= 1) return 1 - Math.exp(-w * x) * (1 + w * x);
    const wd = w * Math.sqrt(1 - damping * damping);
    const e = Math.exp(-damping * w * x);
    return 1 - e * (Math.cos(wd * x) + ((damping * w) / wd) * Math.sin(wd * x));
  }

  // A value that changes target more than once is a sum of springs.
  // keys: [{t, v, freq?, damping?}, ...] sorted by t; the first v is the start.
  function springs(t, keys, opts) {
    let v = keys[0].v;
    for (let i = 1; i < keys.length; i++) {
      const k = keys[i];
      v += (k.v - keys[i - 1].v) * spring(t, k.t, { ...opts, ...k });
    }
    return v;
  }

  // Eased keyframes. keys: [{t, v, e?}] where e eases the segment ending at that key.
  function keys(t, ks) {
    if (t <= ks[0].t) return ks[0].v;
    for (let i = 1; i < ks.length; i++) {
      if (t <= ks[i].t) {
        const p = (ks[i].e || ease.inOut)(inv(ks[i - 1].t, ks[i].t, t));
        return lerp(ks[i - 1].v, ks[i].v, p);
      }
    }
    return ks[ks.length - 1].v;
  }

  // Camera: keyframes of {t, x, y, zoom}. Position is eased linearly,
  // zoom is interpolated in log space so 1x→2x feels as fast as 2x→4x.
  // (x, y) is the canvas point placed at the centre of the frame.
  function camera(t, ks) {
    const x = keys(t, ks.map((k) => ({ t: k.t, v: k.x, e: k.e })));
    const y = keys(t, ks.map((k) => ({ t: k.t, v: k.y, e: k.e })));
    const z = Math.exp(keys(t, ks.map((k) => ({ t: k.t, v: Math.log(k.zoom), e: k.e }))));
    return { x, y, zoom: z };
  }
  function applyCamera(el, cam, W = 1920, H = 1080) {
    el.style.transformOrigin = '0 0';
    el.style.transform =
      `translate(${W / 2}px, ${H / 2}px) scale(${cam.zoom}) translate(${-cam.x}px, ${-cam.y}px)`;
  }

  // Beat clock. Build once from the tempo in kit/AUDIO.md.
  function clock({ bpm, offset = 0 }) {
    const spb = 60 / bpm;
    return {
      bpm,
      spb,
      at: (beat) => offset + beat * spb, // beat number -> seconds
      beat: (t) => (t - offset) / spb, // seconds -> beat number
    };
  }

  // Mask rise: returns translateY in px for a word rising from behind a line.
  const rise = (t, t0, h, opts = { freq: 2.4, damping: 0.8 }) => (1 - spring(t, t0, opts)) * h;

  // Count from a to b without ever showing a value outside [min(a,b), max(a,b)].
  // Rounds toward the target so a countdown never reads one unit low.
  function count(t, t0, t1, a, b, step = 1) {
    const v = lerp(a, b, prog(t, t0, t1, ease.out));
    const q = b < a ? Math.ceil(v / step) * step : Math.floor(v / step) * step;
    return Math.min(Math.max(a, b), Math.max(Math.min(a, b), q)) + 0; // +0 kills -0
  }

  // The frame a subframe sample belongs to. Drive readable values (counters, text)
  // from frameT(t) so motion blur never shows two numbers on top of each other.
  const frameT = (t, fps = 60) => Math.round(t * fps) / fps;

  window.M = { frameT, clamp, lerp, inv, ease, prog, spring, springs, keys, camera, applyCamera, clock, rise, count };
})();
