#!/usr/bin/env python3
"""Checks that make the video watch itself.

  python3 studio/checks.py determinism scenes/x --frame 90
  python3 studio/checks.py contact film.mp4 --bpm 120 [--offset 0] [--out contact.png]
  python3 studio/checks.py pops film.mp4
  python3 studio/checks.py sync film.mp4 --event 1.0 [--window 0.25]
  python3 studio/checks.py loop clip.mp4
  python3 studio/checks.py loudness film.mp4
  python3 studio/checks.py phone film.mp4
"""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).parent))
import audio  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def probe(path):
    p = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames", "-show_entries",
                        "stream=width,height,r_frame_rate,nb_read_frames", "-of", "json", str(path)],
                       capture_output=True, text=True, check=True)
    s = json.loads(p.stdout)["streams"][0]
    num, den = map(int, s["r_frame_rate"].split("/"))
    return {"w": s["width"], "h": s["height"], "fps": num / den, "frames": int(s["nb_read_frames"])}


def frames(path, w, h, pix="rgb24"):
    """Yield decoded frames as arrays at w x h."""
    ch = 3 if pix == "rgb24" else 1
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", str(path), "-vf", f"scale={w}:{h}:flags=area",
                          "-f", "rawvideo", "-pix_fmt", pix, "-"], stdout=subprocess.PIPE)
    size = w * h * ch
    while True:
        b = p.stdout.read(size)
        if len(b) < size:
            break
        yield np.frombuffer(b, np.uint8).reshape(h, w, ch)
    p.wait()


def frame_at(path, t, w=None, h=None):
    vf = ["-vf", f"scale={w}:{h}"] if w else []
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.4f}", "-i", str(path), "-frames:v", "1", *vf,
                          "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True, check=True).stdout
    import io
    return Image.open(io.BytesIO(raw)).convert("RGB")


def cmd_determinism(a):
    import render
    from playwright.sync_api import sync_playwright
    srv = render.serve(ROOT)
    hashes = []
    with sync_playwright() as p:
        for run in range(2):  # two fresh browsers, so nothing can be remembered between them
            b, s = render.open_scene(p, a.scene, srv.server_address[1])
            m = s.meta
            fps = m["fps"]
            # On the second run, render the whole timeline first, the way the renderer does.
            # This catches state carried between frames, in the page or in Chromium itself
            # (an element promoted to a compositor layer mid-animation rasterises differently).
            if run == 1:
                n = int(m["duration"] * fps)
                for f in range(0, n, max(1, n // 400)):
                    s.frame(f, fps, s.subframes(f / fps, 4), m["duration"])
            img = s.frame(a.frame, fps, s.subframes(a.frame / fps, 4), m["duration"])
            hashes.append(hashlib.sha256(img.tobytes()).hexdigest())
            b.close()
    ok = hashes[0] == hashes[1]
    print(f"determinism frame {a.frame}: {'IDENTICAL' if ok else 'DIFFERENT'}  {hashes[0][:16]} {hashes[1][:16]}")
    return 0 if ok else 1


def cmd_contact(a):
    info = probe(a.video)
    dur = info["frames"] / info["fps"]
    if a.bpm:
        spb = 60 / a.bpm
        times, k = [], 0
        while a.offset + k * spb < dur:
            times.append((k, a.offset + k * spb))
            k += 1
    else:
        times = [(i, i / 2) for i in range(int(dur * 2))]
    cols, tw = 6, 320
    th = int(tw * info["h"] / info["w"])
    rows = (len(times) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tw, rows * (th + 22)), "white")
    d = ImageDraw.Draw(sheet)
    for i, (k, t) in enumerate(times):
        im = frame_at(a.video, min(t, dur - 1 / info["fps"]), tw, th)
        x, y = (i % cols) * tw, (i // cols) * (th + 22)
        sheet.paste(im, (x, y))
        d.text((x + 6, y + th + 4), f"{'beat ' + str(k) if a.bpm else ''}  {t:.2f}s", fill="black")
    out = a.out or str(Path(a.video).with_name("contact.png"))
    sheet.save(out)
    print(f"wrote {out} ({len(times)} frames)")


def cmd_pops(a):
    """Flag single-frame pops: frame n differs from both neighbours far more than they differ from each other."""
    info = probe(a.video)
    w, h = 240, int(240 * info["h"] / info["w"])
    fs = [f.astype(np.int16)[..., 0] for f in frames(a.video, w, h, "gray")]
    flagged = []
    for n in range(1, len(fs) - 1):
        d_prev = np.abs(fs[n] - fs[n - 1]).mean()
        d_next = np.abs(fs[n + 1] - fs[n]).mean()
        d_skip = np.abs(fs[n + 1] - fs[n - 1]).mean()
        # a pop: jumps away and back. Steady motion has d_skip ≈ d_prev + d_next.
        if min(d_prev, d_next) > a.min_diff and d_skip < a.ratio * min(d_prev, d_next):
            flagged.append((n, n / info["fps"], round(float(d_prev), 2), round(float(d_next), 2), round(float(d_skip), 2)))
    # also flag hard jumps far above the local median (cuts or teleports)
    diffs = np.array([np.abs(fs[n] - fs[n - 1]).mean() for n in range(1, len(fs))])
    jumps = []
    for n in range(len(diffs)):
        lo, hi = max(0, n - 15), min(len(diffs), n + 16)
        med = np.median(np.delete(diffs[lo:hi], n - lo)) if hi - lo > 1 else 0
        if diffs[n] > a.min_diff * 4 and diffs[n] > a.jump * (med + 0.05):
            jumps.append((n + 1, (n + 1) / info["fps"], round(float(diffs[n]), 2), round(float(med), 2)))
    print(f"scanned {len(fs)} frames")
    print(f"pops (frame, t, d_prev, d_next, d_skip): {flagged or 'none'}")
    print(f"jumps (frame, t, diff, local median): {jumps or 'none'}")
    return 1 if flagged or jumps else 0


def cmd_sync(a):
    x = audio.decode(a.video)
    sr = audio.SR
    lo, hi = int(max(0, a.event - a.window) * sr), int((a.event + a.window) * sr)
    seg = x[lo:hi]
    t_peak = lo / sr + audio.peak_time(seg)
    t_on = lo / sr + audio.onset_time(seg)
    print(f"event {a.event:.4f}s  onset {t_on:.5f}s ({(t_on - a.event) * 1000:+.2f} ms)  "
          f"peak {t_peak:.5f}s ({(t_peak - a.event) * 1000:+.2f} ms)")


def cmd_loop(a):
    fs = list(frames(a.video, probe(a.video)["w"], probe(a.video)["h"]))
    first, last = fs[0], fs[-1]
    diff = np.abs(first.astype(int) - last.astype(int))
    print(f"loop: first vs last  max diff {diff.max()}  mean {diff.mean():.4f}  -> {'IDENTICAL' if diff.max() == 0 else 'DIFFERENT'}")
    return 0 if diff.max() == 0 else 1


def cmd_loudness(a):
    print(f"integrated loudness: {audio.integrated_lufs(a.video)} LUFS")


def cmd_phone(a):
    base = Path(a.video).with_suffix("")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", a.video, "-vf", "fps=1,scale=360:-1,tile=5x7",
                    "-frames:v", "1", f"{base}-phone.png"], check=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", a.video, "-frames:v", "1", f"{base}-first-frame.png"], check=True)
    print(f"wrote {base}-phone.png and {base}-first-frame.png")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("determinism"); s.add_argument("scene"); s.add_argument("--frame", type=int, default=90)
    s = sub.add_parser("contact"); s.add_argument("video"); s.add_argument("--bpm", type=float)
    s.add_argument("--offset", type=float, default=0.0); s.add_argument("--out")
    s = sub.add_parser("pops"); s.add_argument("video"); s.add_argument("--min-diff", type=float, default=0.6)
    s.add_argument("--ratio", type=float, default=0.5); s.add_argument("--jump", type=float, default=6.0)
    s = sub.add_parser("sync"); s.add_argument("video"); s.add_argument("--event", type=float, required=True)
    s.add_argument("--window", type=float, default=0.25)
    s = sub.add_parser("loop"); s.add_argument("video")
    s = sub.add_parser("loudness"); s.add_argument("video")
    s = sub.add_parser("phone"); s.add_argument("video")
    a = ap.parse_args()
    sys.exit(globals()[f"cmd_{a.cmd}"](a) or 0)


if __name__ == "__main__":
    main()
