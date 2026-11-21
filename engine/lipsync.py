"""Viseme lip-sync track from word timings + espeak phonemes (+ audio envelope).
usage: python3 -I lipsync.py words.json narration.wav out.npz
words.json: [[word, start, end], ...]   SPOKEN maps display words that are spoken differently (digits, acronyms).
"""
import sys, json, re, os
import numpy as np
import soundfile as sf

RATE = 240.0
SPOKEN = {"2015": "twenty fifteen", "MRI": "M R I", "60": "sixty", "215": "two hundred fifteen", "Ig": "ig"}

# viseme: (open 0..1, width factor, teeth 0..1)
V = {
    "AA": (0.95, 1.00, 0.2), "AE": (0.80, 1.15, 0.5), "EH": (0.50, 1.05, 0.5), "IH": (0.30, 1.25, 0.7),
    "AO": (0.70, 0.70, 0.0), "UW": (0.28, 0.50, 0.0), "M": (0.0, 0.95, 0.0), "FV": (0.14, 1.10, 1.0),
    "W": (0.25, 0.50, 0.0), "R": (0.26, 0.70, 0.0), "S": (0.12, 1.20, 1.0), "SH": (0.20, 0.60, 0.3),
    "TH": (0.16, 1.00, 0.9), "T": (0.20, 1.00, 0.5), "Y": (0.22, 1.20, 0.5), "H": (0.30, 1.00, 0.0),
}
VOW = {"ɑ": "AA", "a": "AA", "ɐ": "AA", "ʌ": "AA", "ɒ": "AA", "æ": "AE", "ɛ": "EH", "e": "EH", "ə": "EH", "ɜ": "EH", "ɚ": "EH",
       "ɪ": "IH", "i": "IH", "ɨ": "IH", "ᵻ": "IH", "ɔ": "AO", "o": "UW", "ʊ": "UW", "u": "UW", "ɯ": "UW"}
CON = {"m": "M", "b": "M", "p": "M", "f": "FV", "v": "FV", "w": "W", "ɹ": "R", "r": "R", "s": "S", "z": "S", "ʃ": "SH", "ʒ": "SH",
       "θ": "TH", "ð": "TH", "j": "Y", "h": "H", "t": "T", "d": "T", "n": "T", "l": "T", "k": "T", "g": "T", "ŋ": "T", "ɡ": "T", "ɾ": "T", "ʔ": "T"}
DIPH = {"aɪ": ("AA", "IH"), "aʊ": ("AA", "UW"), "ɔɪ": ("AO", "IH"), "eɪ": ("EH", "IH"), "oʊ": ("UW", "UW")}
AFFR = {"dʒ": "SH", "tʃ": "SH"}


def tokenize(ipa):
    ipa = re.sub(r"[ˈˌ\s,.!?;:\-]", "", ipa)
    out = []; i = 0
    while i < len(ipa):
        two = ipa[i:i + 2]
        if two in DIPH: out.append((DIPH[two][0], 2.2)); out.append((DIPH[two][1], 1.6)); i += 2; continue
        if two in AFFR: out.append((AFFR[two], 1.3)); i += 2; continue
        ch = ipa[i]; long_ = i + 1 < len(ipa) and ipa[i + 1] == "ː"
        if ch in VOW: out.append((VOW[ch], 3.2 if long_ else 2.6))
        elif ch in CON: out.append((CON[ch], 0.9 if CON[ch] in ("M", "T") else 1.2))
        elif ch == "ː": pass
        else: out.append(("T", 0.8))
        i += 2 if long_ else 1
    return out


def build(words, wav, out):
    from kokoro_onnx import Kokoro
    k = Kokoro(os.path.join(os.environ.get("KOKORO_DIR", "/home/claude/work"), "kokoro-v1.0.onnx"), os.path.join(os.environ.get("KOKORO_DIR", "/home/claude/work"), "voices-v1.0.bin"))
    y, sr = sf.read(wav, dtype="float32")
    if y.ndim > 1: y = y.mean(1)
    dur = len(y) / sr + 0.5
    n = int(dur * RATE)
    tgt = np.zeros((n, 3), np.float32); tgt[:, 1] = 1.0           # rest = closed, normal width
    for w, s, e in words:
        raw = re.sub(r"[^\w']", "", w)
        spoken = SPOKEN.get(raw, raw)
        ipa = k.tokenizer.phonemize(spoken, "en-us")
        toks = tokenize(ipa)
        if not toks: continue
        tot = sum(d for _, d in toks); t = s
        for vis, d in toks:
            seg = (e - s) * d / tot
            i0, i1 = int(t * RATE), max(int((t + seg) * RATE), int(t * RATE) + 1)
            tgt[i0:i1] = V[vis]; t += seg
    # amplitude gate / scale from audio energy
    hop = int(sr / RATE)
    m = len(y) // hop
    rms = np.sqrt((y[:m * hop].reshape(m, hop) ** 2).mean(1))
    rms = rms / (np.percentile(rms, 95) + 1e-6)
    rms = np.pad(rms, (0, max(0, n - len(rms))))[:n]
    tgt[:, 0] *= np.clip(0.55 + 0.6 * rms, 0.0, 1.15)
    tgt[rms < 0.04, 0] = 0.0
    # smooth: fast closing, slower opening, then lead the audio by 25 ms
    sm = np.zeros_like(tgt); v = tgt[0].copy()
    ao, ac = 1 - np.exp(-1 / (RATE * 0.030)), 1 - np.exp(-1 / (RATE * 0.018))
    for i in range(n):
        a = np.where(tgt[i] > v, ao, ac)
        a[1:] = 1 - np.exp(-1 / (RATE * 0.035))
        v = v + (tgt[i] - v) * a; sm[i] = v
    lead = int(0.025 * RATE)
    sm = np.concatenate([sm[lead:], np.repeat(sm[-1:], lead, 0)])
    np.savez(out, open=sm[:, 0], wide=sm[:, 1], teeth=sm[:, 2], rate=RATE)
    return sm


if __name__ == "__main__":
    words = json.load(open(sys.argv[1]))
    build(words, sys.argv[2], sys.argv[3]); print("lipsync track saved", sys.argv[3])
