"""Audio helpers: decode, measure, mix and normalise. Everything at 48 kHz stereo float32."""
import json
import re
import subprocess

import numpy as np

SR = 48000


def decode(path, sr=SR):
    """Decode any file ffmpeg can read to a (n, 2) float32 array."""
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-f", "f32le", "-ac", "2", "-ar", str(sr), "-"],
        check=True, capture_output=True,
    ).stdout
    return np.frombuffer(raw, dtype=np.float32).reshape(-1, 2).copy()


def mono(x):
    return np.abs(x).max(axis=1) if x.ndim == 2 else np.abs(x)


def peak_time(x, sr=SR):
    """Seconds from the start of x to its loudest sample."""
    return float(np.argmax(mono(x))) / sr


def onset_time(x, sr=SR, threshold=0.5):
    """Seconds to the first sample at or above threshold * the loudest sample.

    This is the sync point for most effects. A click with a press and a release
    of equal loudness syncs on the press, not whichever happens to be 0.1 dB louder.
    """
    m = mono(x)
    return float(np.argmax(m >= threshold * m.max())) / sr


def sync_point(x, align="onset", sr=SR):
    if isinstance(align, (int, float)):
        return float(align) / 1000.0  # explicit milliseconds
    return peak_time(x, sr) if align == "max" else onset_time(x, sr)


def db(g):
    return 10 ** (g / 20)


def mix(duration, music=None, cues=(), root=".", sr=SR):
    """Build the soundtrack.

    music: {"file", "from": seconds into the file, "at": film time it starts, "gain": dB}
    cues:  [{"t": film time of the event, "file", "gain": dB, "align": "onset"|"max"|ms}]
    Each cue is placed so its sync point lands exactly on t.
    Returns (audio, report) where report lists where every cue landed.
    """
    n = int(round(duration * sr))
    out = np.zeros((n, 2), np.float32)
    report = []
    if music:
        x = decode(f"{root}/{music['file']}", sr)
        x = x[int(round(music.get("from", 0) * sr)):]
        at = int(round(music.get("at", 0) * sr))
        x = x[: max(0, n - at)] * db(music.get("gain", 0))
        out[at: at + len(x)] += x
    cache = {}
    for c in cues:
        if c["file"] not in cache:
            cache[c["file"]] = decode(f"{root}/{c['file']}", sr)
        x = cache[c["file"]]
        sp = sync_point(x, c.get("align", "onset"), sr)
        start = int(round((c["t"] - sp) * sr))
        a, b = max(0, start), min(n, start + len(x))
        if b > a:
            out[a:b] += x[a - start: b - start] * db(c.get("gain", 0))
        report.append({"t": c["t"], "file": c["file"], "sync_ms": round(sp * 1000, 2), "starts_at": round(start / sr, 4)})
    return out, report


def write_wav(path, x, sr=SR):
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ac", "2", "-ar", str(sr), "-i", "-", "-c:a", "pcm_s24le", str(path)],
        input=np.ascontiguousarray(x, np.float32).tobytes(), check=True,
    )


def loudnorm(src, dst, target=-14.0, tp=-1.0):
    """Two-pass linear loudness normalisation (no dynamic processing, timing untouched)."""
    p = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", str(src), "-af", f"loudnorm=I={target}:TP={tp}:LRA=20:print_format=json", "-f", "null", "-"],
        capture_output=True, text=True, check=True,
    )
    m = json.loads(re.findall(r"\{[^{}]*\}", p.stderr)[-1])
    if float(m["input_i"]) == float("-inf") or m["input_i"] == "-inf":
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-c:a", "pcm_s24le", str(dst)], check=True)
        return m
    af = (
        f"loudnorm=I={target}:TP={tp}:LRA=20:linear=true:"
        f"measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}:"
        f"measured_thresh={m['input_thresh']}:offset={m['target_offset']}"
    )
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-af", af, "-ar", str(SR), "-c:a", "pcm_s24le", str(dst)], check=True)
    return m


def integrated_lufs(path):
    p = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af", "ebur128", "-f", "null", "-"],
                       capture_output=True, text=True)
    m = re.findall(r"I:\s+(-?[\d.]+) LUFS", p.stderr)
    return float(m[-1]) if m else None
