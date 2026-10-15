// Charge-up fill. Beats at a nominal 120 bpm (no music yet; kit/audio is empty).
const CLOCK = M.clock({ bpm: 120, offset: 0 });
const B = CLOCK.at;
const T = {
  draw: B(0.4),       // outlines draw on, glyph by glyph
  charge: B(2.2),     // a blue front sweeps left to right through the letters, cooling to ink behind it
  chargeDur: 1.2,     // seconds for the front to cross the logo
  // the bolt fires the moment the front reaches it (solved from the sweep in index.html)
  end: B(8),
};
