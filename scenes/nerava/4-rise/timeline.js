// Masked letter rise. Beats at a nominal 120 bpm (no music yet).
const CLOCK = M.clock({ bpm: 120, offset: 0 });
const B = CLOCK.at;
const T = {
  rise: B(0.4),      // letters rise out of the baseline, left to right
  stagger: 0.045,
  fall: B(1.1),      // the bolt falls in down its own slant
  fallDur: 0.34,     // impact = fall + fallDur
  end: B(6),
};
