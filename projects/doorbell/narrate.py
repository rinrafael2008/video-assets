#!/usr/bin/env python3
"""Doorbell: per-line voices + effects with Kokoro (free). usage: python3 -I projects/doorbell/narrate.py
Line = [text, pause_after, {"voice","speed","fx"}]; fx "door" = muffled, as if heard through a closed bedroom door.
Writes narration.wav/.mp3 + narration_meta.json (same format as engine/tts.py so engine/align.py works unchanged).
"""
import os, sys, json, subprocess
import numpy as np, soundfile as sf
from scipy.signal import butter, sosfilt

HERE = os.path.dirname(os.path.abspath(__file__))


def door_fx(y, sr):
    y = sosfilt(butter(4, 1500, "low", fs=sr, output="sos"), y)          # muffled by the door
    y = sosfilt(butter(2, 140, "high", fs=sr, output="sos"), y)
    # short small-room smear
    n = int(sr * 0.09); ir = np.zeros(n, dtype=np.float32); r = np.random.RandomState(3)
    for d, g in ((0.011, 0.5), (0.023, 0.32), (0.041, 0.2), (0.067, 0.12)): ir[int(d * sr)] = g
    wet = np.convolve(y, ir)[:len(y)]
    return (y * 0.9 + wet * 0.8).astype(np.float32) * 0.62


def main():
    from kokoro_onnx import Kokoro
    sc = json.load(open(os.path.join(HERE, "script.json")))
    d = os.environ.get("KOKORO_DIR", "/home/claude/work")
    k = Kokoro(os.path.join(d, "kokoro-v1.0.onnx"), os.path.join(d, "voices-v1.0.bin"))
    chunks, meta, t, sr_out = [], [], 0.0, 24000
    for text, pause, o in sc["lines"]:
        s, sr = k.create(text, voice=o.get("voice", sc["voice"]), speed=o.get("speed", sc["speed"]), lang="en-us")
        s = np.asarray(s, dtype=np.float32); sr_out = sr
        s = s / max(1e-6, np.max(np.abs(s)))
        if o.get("fx") == "door": s = door_fx(s, sr)
        dur = len(s) / sr
        meta.append({"text": text, "start": round(t, 3), "end": round(t + dur, 3)})
        chunks.append(s); t += dur
        if pause: chunks.append(np.zeros(int(sr * pause), dtype=np.float32)); t += pause
    a = np.concatenate(chunks)
    wav = os.path.join(HERE, "narration.wav"); sf.write(wav, a * 0.95, sr_out)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav, "-codec:a", "libmp3lame", "-q:a", "3", os.path.join(HERE, "narration.mp3")], check=True)
    json.dump({"total": round(t, 3), "lines": meta}, open(os.path.join(HERE, "narration_meta.json"), "w"), indent=1)
    print("narration seconds:", round(t, 2))
    for m in meta: print(f"{m['start']:6.2f}-{m['end']:6.2f}  {m['text']}")


if __name__ == "__main__":
    main()
