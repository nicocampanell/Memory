// App splash: option 2 (charge fill) on a phone screen, ending in a blue gradient ring.
// Beats at a nominal 120 bpm (no music yet; kit/audio is empty).
const CLOCK = M.clock({ bpm: 120, offset: 0 });
const B = CLOCK.at;
const T = {
  draw: B(0.3),       // outlines draw on, glyph by glyph
  charge: B(1.9),     // blue front sweeps through the letters, cooling to ink behind it
  chargeDur: 1.1,     // seconds for the front to cross the logo
  // FIRE (bolt fires) is solved from the sweep in splash.js, about 1.9 s
  ringDelay: 0.12,    // the ring blooms this long after the bolt fires
  end: B(9),
};
