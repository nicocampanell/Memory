#!/usr/bin/env python3
"""Measure the sound kit and write kit/AUDIO.md + kit/beats.png.

  python3 studio/measure_audio.py kit/audio            # music in kit/audio/music/, effects in kit/audio/sfx/

Every file is first converted to WAV in kit/audio/wav/ (MP3s carry encoder delay;
measure and mix the WAVs). Optional kit/audio/SOURCES.json maps a filename to
{"source": url, "license": text} for the table.

It measures. It does not listen. Play the track before you build on it.
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).parent))
import audio  # noqa: E402

SR = audio.SR
EXTS = {".wav", ".mp3", ".m4a", ".aac", ".ogg", ".flac", ".aif", ".aiff"}


def to_wav(src, wav_dir):
    dst = wav_dir / (src.stem + ".wav")
    if not dst.exists() or dst.stat().st_mtime < src.stat().st_mtime:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-ar", str(SR), "-ac", "2", "-c:a", "pcm_s24le", str(dst)], check=True)
    return dst


def onset_envelope(x, hop=512, n_fft=2048):
    m = x.mean(axis=1)
    frames = 1 + (len(m) - n_fft) // hop
    win = np.hanning(n_fft).astype(np.float32)
    idx = np.arange(n_fft)[None, :] + hop * np.arange(frames)[:, None]
    spec = np.abs(np.fft.rfft(m[idx] * win, axis=1))
    logspec = np.log1p(100 * spec)
    flux = np.maximum(0, np.diff(logspec, axis=0)).sum(axis=1)
    flux = np.concatenate([[0], flux])
    flux -= np.convolve(flux, np.ones(16) / 16, mode="same")  # remove slow trend
    return np.maximum(flux, 0), hop / SR, spec


def tempo(env, dt, lo=70, hi=180):
    ac = np.correlate(env, env, mode="full")[len(env) - 1:]
    lags = np.arange(len(ac)) * dt
    ok = (lags >= 60 / hi) & (lags <= 60 / lo)
    # weight towards 100-130 BPM, where most launch tracks live, to avoid half/double errors
    bpm_at = 60 / np.maximum(lags, 1e-9)
    w = np.exp(-0.5 * (np.log2(bpm_at / 118) / 0.6) ** 2)
    score = np.where(ok, ac * w, -np.inf)
    lag = int(np.argmax(score))
    # parabolic refinement
    if 0 < lag < len(ac) - 1:
        a, b, c = ac[lag - 1], ac[lag], ac[lag + 1]
        lag = lag + 0.5 * (a - c) / (a - 2 * b + c + 1e-12)
    return 60 / (lag * dt)


def beat_phase(env, dt, bpm):
    """Offset of the beat grid that best lines up with onsets."""
    period = 60 / bpm
    phases = np.linspace(0, period, 200, endpoint=False)
    t = np.arange(len(env)) * dt
    best, best_s = 0.0, -1
    for ph in phases:
        grid = np.arange(ph, t[-1], period)
        s = env[np.clip(np.rint(grid / dt).astype(int), 0, len(env) - 1)].sum()
        if s > best_s:
            best, best_s = ph, s
    return best


def refine_grid(x, bpm, phase, length):
    """Sample-accurate grid: find each beat's real onset in the waveform, then fit
    time = phase + k * period by least squares. Removes STFT frame lag and tempo drift."""
    m = audio.mono(x)
    period = 60 / bpm
    for _ in range(2):
        ks, ts = [], []
        k = 0
        while phase + k * period < length - 0.1:
            b = phase + k * period
            a0, a1 = int(max(0, b - 0.06) * SR), int(min(length, b + 0.06) * SR)
            seg = m[a0:a1]
            if seg.size and seg.max() > 0.15 * m.max():
                ks.append(k)
                ts.append(a0 / SR + audio.onset_time(seg[:, None] if seg.ndim == 1 else seg))
            k += 1
        if len(ks) < 8:
            resid = np.array([np.nan])
            break
        A = np.vstack([np.ones(len(ks)), ks]).T
        (phase, period), *_ = np.linalg.lstsq(A, np.array(ts), rcond=None)
        # throw out outliers (off-beat hits) and refit once
        resid = np.abs(A @ [phase, period] - ts)
        keep = resid < max(0.01, 3 * np.median(resid))
        (phase, period), *_ = np.linalg.lstsq(A[keep], np.array(ts)[keep], rcond=None)
    phase %= period  # earliest beat in the file
    fit_ms = float(np.median(resid) * 1000) if len(ks) >= 8 else None
    return 60 / period, phase, fit_ms


def downbeat(env, dt, bpm, phase, low_energy):
    """Which of the 4 beat positions is beat 1: the one with the most low-end energy."""
    period = 60 / bpm
    grid = np.arange(phase, len(env) * dt, period)
    idx = np.clip(np.rint(grid / dt).astype(int), 0, len(low_energy) - 1)
    scores = [low_energy[idx[k::4]].mean() for k in range(4)]
    k = int(np.argmax(scores))
    return grid[k], grid


def find_drop(low_energy, dt, bpm):
    """The drop: the biggest jump in low-end energy, comparing the bar after with the two bars before."""
    bar = int(round(4 * 60 / bpm / dt))
    best, best_t = 0, None
    for i in range(2 * bar, len(low_energy) - bar):
        before = low_energy[i - 2 * bar: i].mean() + 1e-9
        after = low_energy[i: i + bar].mean()
        if after / before > best:
            best, best_t = after / before, i * dt
    return best_t, best


def measure_music(path):
    x = audio.decode(path)
    env, dt, spec = onset_envelope(x)
    freqs = np.fft.rfftfreq(2048, 1 / SR)
    low = spec[:, freqs < 150].sum(axis=1)
    low = np.convolve(low, np.ones(4) / 4, mode="same")
    bpm = tempo(env, dt)
    phase = beat_phase(env, dt, bpm) + 1024 / SR  # STFT frames are stamped at their start
    bpm, phase, fit_ms = refine_grid(x, bpm, phase, len(x) / SR)
    first_down, grid = downbeat(env, dt, bpm, phase, low)
    drop, ratio = find_drop(low, dt, bpm)
    if drop is not None:  # snap the drop to the nearest beat
        drop = round(float(grid[np.argmin(np.abs(grid - drop))]), 4)
    return {"file": path, "length": len(x) / SR, "bpm": round(float(bpm), 3), "first_downbeat": round(float(first_down), 4),
            "beats": [round(float(b), 4) for b in grid], "drop": drop, "drop_ratio": round(float(ratio), 2),
            "fit_ms": None if fit_ms is None else round(fit_ms, 2), "x": x}


def measure_sfx(path):
    x = audio.decode(path)
    m = audio.mono(x)
    return {"file": path, "length": len(x) / SR, "peak_ms": round(audio.peak_time(x) * 1000, 1),
            "onset_ms": round(audio.onset_time(x) * 1000, 1), "peak_db": round(float(20 * np.log10(m.max() + 1e-12)), 1),
            # a second hit within 30% of the loudest one (e.g. press + release) makes 'max' ambiguous
            "ambiguous": bool(_second_hit(m))}


def _second_hit(m, gap_ms=40):
    i = int(np.argmax(m))
    g = int(gap_ms * SR / 1000)
    rest = np.concatenate([m[: max(0, i - g)], m[i + g:]])
    return rest.size and rest.max() >= 0.7 * m.max()


def beats_png(music, path):
    x = audio.mono(music["x"])
    W, H = 2400, 360
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    n = len(x)
    cols = np.array_split(x, W)
    for i, c in enumerate(cols):
        v = float(c.max()) if c.size else 0
        d.line([(i, H / 2 - v * H * 0.45), (i, H / 2 + v * H * 0.45)], fill=(150, 160, 155))
    sec = W / (n / SR)
    k0 = int(np.argmin(np.abs(np.array(music["beats"]) - music["first_downbeat"])))
    for k, b in enumerate(music["beats"]):
        is_down = (k - k0) % 4 == 0
        d.line([(b * sec, 0), (b * sec, H)], fill=(11, 143, 99) if is_down else (205, 215, 210), width=2 if is_down else 1)
    if music["drop"] is not None:
        xd = music["drop"] * sec
        d.line([(xd, 0), (xd, H)], fill=(194, 74, 27), width=4)
        d.text((xd + 6, 6), f"drop {music['drop']:.2f}s", fill=(194, 74, 27))
    d.text((6, 6), f"{Path(music['file']).name}  {music['bpm']} BPM  first downbeat {music['first_downbeat']:.3f}s  (green = bar lines)", fill="black")
    img.save(path)


def main():
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "kit/audio")
    kit = root.parent
    wav = root / "wav"
    wav.mkdir(exist_ok=True)
    sources = json.loads((root / "SOURCES.json").read_text()) if (root / "SOURCES.json").exists() else {}
    files = lambda d: sorted(p for p in (root / d).glob("*") if p.suffix.lower() in EXTS) if (root / d).exists() else []

    music = [measure_music(to_wav(p, wav)) for p in files("music")]
    sfx = [(p, measure_sfx(to_wav(p, wav))) for p in files("sfx")]

    rel = lambda p: Path(p).resolve().relative_to(kit.resolve().parent).as_posix()
    lines = ["# Sound kit", "", "Measured by `studio/measure_audio.py`. Mix from the WAVs in `kit/audio/wav/`.",
             "It measured these files. It did not listen to them. Play them before you build on them.", "",
             "## Effects", "", "Sync point = where the effect lands on its event. Use `align: \"onset\"` (default) or `\"max\"`.", "",
             "| File (wav) | Source | License | Length | Onset | Loudest peak | Peak dB | Note |",
             "|---|---|---|---|---|---|---|---|"]
    for p, s in sfx:
        src = sources.get(p.name, {})
        note = "two hits of similar loudness: sync on onset, not max" if s["ambiguous"] else ""
        if s["length"] > 3:
            note = (note + "; " if note else "") + "long file: trim it, or check which hit you want"
        lines.append(f"| `{rel(s['file'])}` | {src.get('source', '?')} | {src.get('license', '?')} | {s['length']:.3f}s | "
                     f"{s['onset_ms']} ms | {s['peak_ms']} ms | {s['peak_db']} | {note} |")
    for m in music:
        name = Path(m["file"]).name
        src = sources.get(Path(m["file"]).stem + ".mp3", sources.get(name, {}))
        spb = 60 / m["bpm"]
        lines += ["", f"## Music: `{rel(m['file'])}`", "",
                  f"- Source: {src.get('source', '?')}  License: {src.get('license', '?')}",
                  f"- Length: {m['length']:.2f}s",
                  f"- Tempo: **{m['bpm']} BPM** (one beat = {spb:.4f}s, one bar = {4 * spb:.4f}s; "
                  f"median onset off the grid: {m['fit_ms']} ms)",
                  f"- First downbeat: **{m['first_downbeat']:.4f}s**",
                  f"- Drop: **{m['drop']:.4f}s** (low end jumps {m['drop_ratio']}x)" if m["drop"] else "- Drop: none found",
                  "", "Beat grid (s): " + ", ".join(f"{b:.3f}" for b in m["beats"][:64]) + (" …" if len(m["beats"]) > 64 else "")]
        beats_png(m, kit / ("beats.png" if len(music) == 1 else f"beats-{Path(m['file']).stem}.png"))
    (kit / "AUDIO.md").write_text("\n".join(lines) + "\n")
    print(f"wrote {kit / 'AUDIO.md'}: {len(music)} music, {len(sfx)} effects")
    for m in music:
        print(f"  {Path(m['file']).name}: {m['bpm']} BPM, downbeat {m['first_downbeat']}s, drop {m['drop']}s")


if __name__ == "__main__":
    main()
