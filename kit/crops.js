// Positions of every crop used by scenes, measured on the real screenshots in kit/shots.
// One entry per UI element: the source shot and its box in that shot's pixels.
// Scenes read these instead of hard-coding positions, so a re-shot page is a one-file fix.
window.CROPS = {
  // example:
  // newPaymentButton: { shot: 'dashboard.png', x: 1184, y: 96, w: 212, h: 56, radius: 12 },
};
