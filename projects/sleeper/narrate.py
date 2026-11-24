#!/usr/bin/env python3
"""Sleeper: per-line voices + effects with Kokoro (free). usage: python3 -I projects/sleeper/narrate.py
Line = [text, pause_after, {"voice","speed","fx"}]; fx "whisper" = random-phase STFT resynthesis (breathy whisper) as heard on a phone mic.
Writes narration.wav/.mp3 + narration_meta.json (same format as engine/tts.py so engine/align.py works unchanged).
"""
import os, sys, json, subprocess
import numpy as np, soundfile as sf
from scipy.signal import butter, sosfilt, stft, istft

HERE = os.path.dirname(os.path.abspath(__file__))


def whisper_fx(y, sr):
    f, t, Z = stft(y, fs=sr, nperseg=1024, noverlap=768)
    r = np.random.RandomState(7)
    Z2 = np.abs(Z) * np.exp(1j * r.uniform(0, 2 * np.pi, Z.shape))                       # keep the spectral envelope, throw the pitch away
    _, w = istft(Z2, fs=sr, nperseg=1024, noverlap=768)
    w = w[:len(y)].astype(np.float32)
    w = sosfilt(butter(2, 180, "high", fs=sr, output="sos"), w)
    w = sosfilt(butter(4, 5200, "low", fs=sr, output="sos"), w)
    hiss = sosfilt(butter(2, 3000, "high", fs=sr, output="sos"), r.standard_normal(len(w)).astype(np.float32))
    env = np.convolve(np.abs(y), np.ones(int(sr * 0.03)) / int(sr * 0.03), mode="same")
    w = w + hiss * env * 0.35                                                            # breath
    n = int(sr * 0.12); ir = np.zeros(n, dtype=np.float32)
    for d, g in ((0.013, 0.35), (0.029, 0.24), (0.051, 0.14), (0.083, 0.08)): ir[int(d * sr)] = g
    w = w + np.convolve(w, ir)[:len(w)] * 0.7                                            # small dark room
    return (w / (np.max(np.abs(w)) + 1e-9) * 0.9).astype(np.float32)


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
        if o.get("fx") == "whisper": s = whisper_fx(s, sr) * 0.8
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
