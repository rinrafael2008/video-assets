"""SFX synthesis + auto music bed + mixing with ducking (numpy only, no downloads, no credits).
Scene layers register cues like ("pop", T); mix_from_cues() renders them under the narration.
"""
import subprocess
import numpy as np
import soundfile as sf

SR = 44100
rng = np.random.default_rng(11)


def env_exp(n, tau):
    t = np.arange(n) / SR
    return np.exp(-t / tau)


def pop(f0=900, f1=320, dur=0.16, vol=0.5):
    n = int(SR * dur)
    t = np.arange(n) / SR
    f = f1 + (f0 - f1) * np.exp(-t / (dur * 0.35))
    ph = 2 * np.pi * np.cumsum(f) / SR
    return (np.sin(ph) * env_exp(n, dur * 0.4) * vol).astype(np.float32)


def thud(dur=0.35, vol=0.7):
    n = int(SR * dur)
    t = np.arange(n) / SR
    f = 45 + 90 * np.exp(-t / 0.05)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return (np.sin(ph) * env_exp(n, 0.12) * vol).astype(np.float32)


def whoosh(dur=0.34, vol=0.35):
    n = int(SR * dur)
    noise = rng.standard_normal(n).astype(np.float32)
    # moving band via cumulative smoothing of different widths
    t = np.linspace(0, 1, n)
    out_s = np.zeros(n, dtype=np.float32)
    k = 40
    sm = np.convolve(noise, np.ones(k) / k, mode="same")
    hp = noise - sm
    out_s = (0.6 * hp + 0.4 * sm * 3)
    env = np.sin(np.pi * t) ** 1.5
    return (out_s * env * vol).astype(np.float32)


def tick(vol=0.35):
    n = int(SR * 0.05)
    t = np.arange(n) / SR
    return (np.sin(2 * np.pi * 1800 * t) * env_exp(n, 0.012) * vol).astype(np.float32)


def boing(vol=0.45):
    n = int(SR * 0.45)
    t = np.arange(n) / SR
    f = 300 + 250 * np.sin(2 * np.pi * 6 * t) * np.exp(-t / 0.2) + 200 * (t / 0.45)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return (np.sin(ph) * env_exp(n, 0.25) * vol).astype(np.float32)


def buzz(vol=0.3):
    n = int(SR * 0.28)
    t = np.arange(n) / SR
    s = np.sign(np.sin(2 * np.pi * 110 * t)) * 0.5 + np.sin(2 * np.pi * 165 * t) * 0.3
    return (s * env_exp(n, 0.18) * vol).astype(np.float32)


def ding(vol=0.4):
    n = int(SR * 0.8)
    t = np.arange(n) / SR
    s = np.sin(2 * np.pi * 1318 * t) + 0.5 * np.sin(2 * np.pi * 1976 * t)
    return (s * env_exp(n, 0.3) * vol * 0.6).astype(np.float32)



def crack(vol=0.8):
    n = int(SR * 0.12)
    t = np.arange(n) / SR
    s = rng.standard_normal(n).astype(np.float32) * env_exp(n, 0.004)
    s += np.sin(2 * np.pi * 950 * t) * env_exp(n, 0.02) * 0.8
    s2 = np.zeros(n, dtype=np.float32); d = int(SR * 0.03)
    s2[d:] = (rng.standard_normal(n - d).astype(np.float32) * env_exp(n - d, 0.003)) * 0.7 + np.sin(2 * np.pi * 1300 * t[: n - d]) * env_exp(n - d, 0.015) * 0.5
    return ((s + s2) * vol).astype(np.float32)

def stamp(vol=0.9):
    n = int(SR * 0.4)
    t = np.arange(n) / SR
    f = 60 + 120 * np.exp(-t / 0.03)
    ph = 2 * np.pi * np.cumsum(f) / SR
    s = np.sin(ph) * env_exp(n, 0.1) + rng.standard_normal(n).astype(np.float32) * env_exp(n, 0.01) * 0.5
    return (s * vol).astype(np.float32)

def bell(freq=1568, vol=0.4, dur=1.2):
    n = int(SR * dur)
    t = np.arange(n) / SR
    s = np.sin(2 * np.pi * freq * t) + 0.45 * np.sin(2 * np.pi * freq * 2.76 * t) * np.exp(-t / 0.2) + 0.25 * np.sin(2 * np.pi * freq * 5.4 * t) * np.exp(-t / 0.08)
    return (s * env_exp(n, 0.4) * vol * 0.6).astype(np.float32)

def step_thump(vol=0.35):
    n = int(SR * 0.09)
    t = np.arange(n) / SR
    return (np.sin(2 * np.pi * (110 + 60 * np.exp(-t / 0.02)) * t) * env_exp(n, 0.03) * vol).astype(np.float32)

def hat(vol=0.5):
    n = int(SR * 0.04)
    x = rng.standard_normal(n).astype(np.float32)
    x = x - np.convolve(x, np.ones(6) / 6, mode="same")
    return (x * env_exp(n, 0.008) * vol).astype(np.float32)

def bloop(f0=500, f1=900, vol=0.4):
    n = int(SR * 0.14)
    t = np.arange(n) / SR
    f = f0 + (f1 - f0) * (t / 0.14)
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * env_exp(n, 0.07) * vol).astype(np.float32)


LIB = {
    "pop": lambda: pop(), "pop_hi": lambda: pop(1200, 600, 0.12, 0.6), "pop_lo": lambda: pop(900, 500, 0.12, 0.5),
    "whoosh": lambda: whoosh(), "whoosh_big": lambda: whoosh(0.5, 0.45), "crack": lambda: crack(), "stamp": lambda: stamp(),
    "thud": lambda: thud(), "tick": lambda: tick(), "bell": lambda: bell(1568), "bell_hi": lambda: bell(1976),
    "bell_win": lambda: bell(1046, 0.5, 1.6), "buzz": lambda: buzz(), "bloop": lambda: bloop(450, 850), "bloop_down": lambda: bloop(380, 220, 0.5),
    "step": lambda: step_thump(), "boing": lambda: boing(), "ding": lambda: ding(),
}
GAIN = {"pop": 0.45, "pop_hi": 0.5, "pop_lo": 0.5, "whoosh": 0.55, "whoosh_big": 0.6, "crack": 0.9, "stamp": 0.9, "thud": 0.6, "tick": 0.35,
        "bell": 0.6, "bell_hi": 0.6, "bell_win": 0.8, "buzz": 0.4, "bloop": 0.6, "bloop_down": 0.7, "step": 0.5, "boing": 0.5, "ding": 0.5}


def music(mix, total, add):
    """bright pluck arpeggio C-G-Am-F at 112 bpm + soft hat"""
    bpm = 112; beat = 60.0 / bpm
    chords = [[60, 64, 67, 72], [55, 59, 62, 67], [57, 60, 64, 69], [53, 57, 60, 65]]
    t = 0.0; step = 0
    while t < total:
        chord = chords[(step // 8) % 4]
        note = chord[[0, 1, 2, 3, 2, 1, 3, 2][step % 8]]
        f = 440.0 * 2 ** ((note + 12 - 69) / 12.0)
        n = int(SR * 0.4); tt = np.arange(n) / SR
        s = (np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(2 * np.pi * 2 * f * tt)) * env_exp(n, 0.13)
        add(s.astype(np.float32), t, 0.075)
        if step % 8 == 0:
            fb = 440.0 * 2 ** ((chord[0] - 24 - 69) / 12.0); nb = int(SR * beat * 3.8); tb = np.arange(nb) / SR
            add((np.sin(2 * np.pi * fb * tb) * env_exp(nb, 0.9)).astype(np.float32), t, 0.16)
        if step % 2 == 1: add(hat(), t, 0.05 if step % 4 == 1 else 0.03)
        t += beat / 2; step += 1


def mix_from_cues(narration_wav, total, cues, out_aac, workdir="/tmp"):
    """cues: [(kind, seconds)]. Writes a loudness-normalised (-14 LUFS) AAC for muxing."""
    N = int(SR * total)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", narration_wav, "-ar", str(SR), "-ac", "1", f"{workdir}/_narr44.wav"], check=True)
    narr, _ = sf.read(f"{workdir}/_narr44.wav", dtype="float32")
    voice = np.zeros(N, dtype=np.float32); voice[: min(len(narr), N)] += narr[:N] * 0.95
    mix = np.zeros(N, dtype=np.float32)

    def add(sig, t0, gain=1.0):
        i0 = int(t0 * SR)
        if i0 < 0 or i0 >= N: return
        seg = sig[: N - i0]; mix[i0:i0 + len(seg)] += seg * gain
    music(mix, total, add)
    fade = np.ones(N, dtype=np.float32); fi = int(SR * 0.5); fo = int(SR * 1.3)
    fade[:fi] = np.linspace(0, 1, fi); fade[-fo:] = np.linspace(1, 0, fo); mix *= fade
    for kind, t in cues:
        if kind in LIB: add(LIB[kind](), t, GAIN[kind])
    env = np.abs(voice); win = int(SR * 0.12); env = np.convolve(env, np.ones(win) / win, mode="same")
    mix *= (1.0 - 0.6 * np.clip(env / 0.12, 0, 1)).astype(np.float32)          # duck music under the voice
    final = voice + mix * 0.9; final = final / np.max(np.abs(final)) * 0.93
    sf.write(f"{workdir}/_mix.wav", final, SR)
    # loudness chain that fixed the quiet raw mix (-25 LUFS -> about -14.7): compress, two-pass loudnorm, limit
    pre = "acompressor=threshold=0.1:ratio=3:attack=5:release=120:makeup=2"
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", f"{workdir}/_mix.wav", "-af", pre + ",loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True)
    import json, re
    m = json.loads(re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", r.stderr, re.S).group(0))
    ln = (pre + f",loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}"
          f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true,alimiter=limit=0.89")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", f"{workdir}/_mix.wav", "-af", ln, "-ar", "48000", "-c:a", "aac", "-b:a", "192k", out_aac], check=True)
    return out_aac
