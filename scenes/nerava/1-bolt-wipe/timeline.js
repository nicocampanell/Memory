// Bolt wipe. Beats at a nominal 120 bpm (no music yet; kit/audio is empty), so a track
// can be dropped in later by changing bpm/offset here.
const CLOCK = M.clock({ bpm: 120, offset: 0 });
const B = CLOCK.at;
const T = {
  strike: B(0.5),    // bolt strikes on, top to bottom, at 1.5x in frame centre
  pulse: B(1.2),     // one charge pulse
  ant: B(1.8),       // anticipation: a small pull back to the left
  go: B(2.2),        // bolt travels to its place; the wordmark slides out from behind it
  land: B(3.0),      // bolt brightens once as it settles
  end: B(7),
};
