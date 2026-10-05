#!/usr/bin/env python3
"""Render a seek(t) scene to MP4.

A scene is an index.html that defines:
  window.SCENE = {
    duration: seconds,
    width: 1920, height: 1080, fps: 60,          // optional
    subframes: 4 | (t) => n,                     // optional, motion blur samples per frame
    music: {file, from, at, gain},               // optional, paths relative to the repo root
    cues: [{t, file, gain, align}],              // optional, sound effects
  }
  window.seek = (t) => { ...draw the exact frame for time t... }   // may return a promise

Usage:
  python3 studio/render.py scenes/c1-hook                     # -> scenes/c1-hook/clip.mp4
  python3 studio/render.py scenes/c1-hook --still 3.5 --out s.png
  python3 studio/render.py scenes/c1-hook --stills-at-beats 2,7,12 --bpm 120
  python3 studio/render.py scenes/c5-end --loop               # first and last frame must match
"""
import argparse
import functools
import hashlib
import http.server
import io
import json
import multiprocessing as mp
import os
import socketserver
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
import audio  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SHUTTER = 0.5  # fraction of a frame the virtual shutter stays open (180 degrees)


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def serve(root):
    handler = functools.partial(QuietHandler, directory=str(root))
    srv = socketserver.ThreadingTCPServer(("127.0.0.1", 0), handler)
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


# After seeking, tear down and rebuild every layout and compositor layer, so each frame is
# rasterised from scratch. Without this Chromium carries state between frames: an element
# that has moved gets promoted to its own layer and anti-aliases differently afterwards,
# and a will-change layer keeps the raster scale it first saw.
RESET_SEEK = """async t => {
  await window.seek(t);
  const b = document.body;
  b.style.display = 'none'; void b.offsetHeight; b.style.display = '';
  void b.offsetHeight;
}"""


class Scene:
    def __init__(self, scene_dir, page):
        self.dir = Path(scene_dir).resolve()
        self.page = page
        rel = self.dir.relative_to(ROOT).as_posix()
        self.url_path = f"/{rel}/index.html"

    def open(self, port):
        self.page.goto(f"http://127.0.0.1:{port}{self.url_path}", wait_until="load")
        self.page.wait_for_function("window.SCENE && typeof window.seek === 'function'")
        self.page.evaluate("document.fonts.ready.then(() => true)")
        self.page.evaluate("Promise.all([...document.images].map(i => i.decode().catch(() => null)))")
        meta = self.page.evaluate(
            """() => {
              const s = window.SCENE;
              return {duration: s.duration, width: s.width || 1920, height: s.height || 1080,
                      fps: s.fps || 60, music: s.music || null, cues: s.cues || [],
                      subframes: typeof s.subframes === 'number' ? s.subframes : null,
                      dynamicSubframes: typeof s.subframes === 'function'}
            }"""
        )
        self.meta = meta
        return meta

    def subframes(self, t, default):
        if self.meta["dynamicSubframes"]:
            return int(self.page.evaluate("t => window.SCENE.subframes(t)", t))
        return self.meta["subframes"] or default

    def shot(self, t):
        self.page.evaluate(RESET_SEEK, t)
        png = self.page.screenshot(type="png", animations="disabled", caret="hide")
        return np.asarray(Image.open(io.BytesIO(png)).convert("RGB"))

    def frame(self, f, fps, n_sub, duration):
        """One output frame: the average of n_sub samples spread over the shutter."""
        t0 = f / fps
        if n_sub <= 1:
            return self.shot(t0)
        acc = None
        for i in range(n_sub):
            t = t0 + SHUTTER * ((i + 0.5) / n_sub - 0.5) / fps
            img = self.shot(min(max(t, 0.0), duration)).astype(np.float32)
            acc = img if acc is None else acc + img
        return np.clip(np.rint(acc / n_sub), 0, 255).astype(np.uint8)


BROWSER_ARGS = ["--font-render-hinting=none", "--disable-lcd-text", "--force-color-profile=srgb"]


def open_scene(p, scene_dir, port):
    browser = p.chromium.launch(args=BROWSER_ARGS)
    rel = Path(scene_dir).resolve().relative_to(ROOT).as_posix()
    probe = browser.new_page()
    probe.goto(f"http://127.0.0.1:{port}/{rel}/index.html")
    probe.wait_for_function("window.SCENE")
    W, H = probe.evaluate("[window.SCENE.width || 1920, window.SCENE.height || 1080]")
    probe.close()
    page = browser.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
    scene = Scene(scene_dir, page)
    scene.open(port)
    return browser, scene


def render_chunk(job):
    """Worker: render frames [f0, f1) losslessly to a chunk file. Returns (first_hash, last_hash)."""
    from playwright.sync_api import sync_playwright
    scene_dir, port, f0, f1, default_sub, path = job
    with sync_playwright() as p:
        browser, scene = open_scene(p, scene_dir, port)
        m = scene.meta
        W, H, fps = m["width"], m["height"], m["fps"]
        enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                                "-r", str(fps), "-i", "-", "-c:v", "ffv1", "-pix_fmt", "bgr0", str(path)],
                               stdin=subprocess.PIPE)
        hashes = []
        for f in range(f0, f1):
            img = scene.frame(f, fps, scene.subframes(f / fps, default_sub), m["duration"])
            hashes.append(hashlib.sha256(img.tobytes()).hexdigest())
            enc.stdin.write(img.tobytes())
            if (f - f0) % fps == 0:
                print(f"  worker {os.getpid()}: frame {f} ({f0}-{f1})", flush=True)
        enc.stdin.close()
        enc.wait()
        browser.close()
    return hashes[0], hashes[-1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scene")
    ap.add_argument("--out")
    ap.add_argument("--subframes", type=int, default=4, help="default samples per frame if SCENE.subframes is unset")
    ap.add_argument("--still", type=float, help="render one frame at this time to --out (png)")
    ap.add_argument("--stills-at-beats", help="comma list of beats; needs --bpm (and --offset)")
    ap.add_argument("--bpm", type=float)
    ap.add_argument("--offset", type=float, default=0.0)
    ap.add_argument("--start", type=float, default=0.0)
    ap.add_argument("--end", type=float)
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    ap.add_argument("--loop", action="store_true", help="encode so the first and last frames decode identically")
    ap.add_argument("--crf", type=int, default=16)
    ap.add_argument("--no-audio", action="store_true")
    args = ap.parse_args()

    from playwright.sync_api import sync_playwright

    srv = serve(ROOT)
    port = srv.server_address[1]
    scene_dir = Path(args.scene)

    with sync_playwright() as p:
        browser, scene = open_scene(p, scene_dir, port)
        meta = scene.meta
        W, H, fps, dur = meta["width"], meta["height"], meta["fps"], meta["duration"]
        if args.still is not None or args.stills_at_beats:
            times = [args.still] if args.still is not None else [
                args.offset + float(b) * 60 / args.bpm for b in args.stills_at_beats.split(",")]
            outs = [Image.fromarray(scene.frame(int(round(t * fps)), fps, scene.subframes(t, args.subframes), dur))
                    for t in times]
            if args.still is not None:
                path = args.out or scene_dir / f"still-{args.still:.2f}.png"
                outs[0].save(path)
            else:
                path = args.out or scene_dir / "stills.png"
                sheet = Image.new("RGB", (W // 2 * len(outs), H // 2), "white")
                for i, im in enumerate(outs):
                    sheet.paste(im.resize((W // 2, H // 2), Image.LANCZOS), (i * W // 2, 0))
                sheet.save(path)
            print(f"wrote {path}")
            browser.close()
            return
        browser.close()

    f0 = int(round(args.start * fps))
    f1 = int(round((args.end if args.end is not None else dur) * fps))
    n_frames = f1 - f0
    out = Path(args.out) if args.out else scene_dir / "clip.mp4"
    t_start = time.time()

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        n_w = max(1, min(args.workers, n_frames // fps or 1))
        bounds = [f0 + n_frames * i // n_w for i in range(n_w + 1)]
        jobs = [(str(scene_dir), port, bounds[i], bounds[i + 1], args.subframes, tmp / f"chunk{i:03d}.mkv")
                for i in range(n_w)]
        print(f"rendering {n_frames} frames on {n_w} workers")
        with mp.get_context("spawn").Pool(n_w) as pool:
            hashes = pool.map(render_chunk, jobs)
        (tmp / "chunks.txt").write_text("".join(f"file '{j[5]}'\n" for j in jobs))

        mix_path = None
        if not args.no_audio and (meta["music"] or meta["cues"]):
            a, report = audio.mix(dur, meta["music"], meta["cues"], root=ROOT)
            a = a[int(round(args.start * audio.SR)): int(round(f1 / fps * audio.SR))]
            audio.write_wav(tmp / "raw.wav", a)
            mix_path = tmp / "mix.wav"
            audio.loudnorm(tmp / "raw.wav", mix_path)
            (scene_dir / "cues.json").write_text(json.dumps(report, indent=2))

        cmd = ["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(tmp / "chunks.txt")]
        if mix_path:
            cmd += ["-i", str(mix_path)]
        cmd += ["-map", "0:v"] + (["-map", "1:a"] if mix_path else [])
        cmd += ["-vf", "scale=out_color_matrix=bt709:out_range=tv", "-c:v", "libx264", "-preset", "medium",
                "-pix_fmt", "yuv420p", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709"]
        if args.loop:
            # Same QP and an I-frame at both ends, so identical source frames decode identically.
            cmd += ["-qp", str(max(args.crf - 4, 0)), "-force_key_frames", f"0,{(n_frames - 1) / fps:.6f}",
                    "-x264-params", "scenecut=0"]
        else:
            cmd += ["-crf", str(args.crf)]
        if mix_path:
            cmd += ["-c:a", "aac", "-b:a", "256k"]
        cmd += ["-movflags", "+faststart", str(out)]
        subprocess.run(cmd, check=True)

    print(f"rendered {n_frames} frames in {time.time() - t_start:.0f}s -> {out}")
    if args.loop:
        print("source first frame == last frame:", hashes[0][0] == hashes[-1][1])


if __name__ == "__main__":
    main()
