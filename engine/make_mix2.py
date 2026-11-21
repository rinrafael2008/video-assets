import subprocess
import numpy as np
import soundfile as sf

SR = 44100
TOTAL = 32.0
N = int(SR * TOTAL)
rng = np.random.default_rng(11)

# narration -> 44.1k mono float
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", "/home/claude/work/engine/narration.mp3",
                "-ar", str(SR), "-ac", "1", "/tmp/narr44.wav"], check=True)
narr, _ = sf.read("/tmp/narr44.wav", dtype="float32")
out = np.zeros(N, dtype=np.float32)
out[: len(narr)] += narr[: N] * 0.95


def add(sig, t0, gain=1.0):
    i0 = int(t0 * SR)
    if i0 >= N:
        return
    seg = sig[: N - i0]
    mix[i0:i0 + len(seg)] += seg * gain


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

mix = np.zeros(N, dtype=np.float32)

# ---- music bed: bright pluck arpeggio, C - G - Am - F, 112 bpm ----
bpm = 112; beat = 60.0 / bpm
chords = [[60, 64, 67, 72], [55, 59, 62, 67], [57, 60, 64, 69], [53, 57, 60, 65]]
t = 0.0; step = 0
while t < TOTAL:
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
fade = np.ones(N, dtype=np.float32); fi = int(SR * 0.5); fo = int(SR * 1.3)
fade[:fi] = np.linspace(0, 1, fi); fade[-fo:] = np.linspace(1, 0, fo); mix *= fade

# ---- sfx cues (global seconds) ----
B = [1.75, 7.45, 10.9, 12.85, 14.95, 24.8, 28.9]
for b in B: add(whoosh(), b - 0.2, 0.55)
for tc in [0.28, 16.34, 17.76, 18.14]: add(crack(), tc, 0.9)
add(crack(0.9), 6.45, 0.9); add(pop(1000, 380, 0.2, 0.8), 6.45, 0.6)             # POP
add(stamp(), 1.05, 0.55); add(pop(), 0.0, 0.0)                                      # X over bone
add(whoosh(0.18, 0.5), 3.11, 0.7); add(thud(), 3.13, 0.5)                           # joint snap
add(pop(900, 500, 0.12, 0.5), 4.95, 0.6)                                            # cavity
for tp in [1.93, 2.19, 4.35, 5.59, 9.4, 13.26, 17.1, 17.76, 19.0, 21.85, 23.32, 23.95, 25.0, 26.75, 30.0, 30.68]: add(pop(), tp, 0.45)
for k in range(15): add(tick(), 8.22 + k * 0.04, 0.35 + 0.02 * k)                    # 2015 counter
add(pop(1200, 600, 0.12, 0.6), 8.22, 0.5); add(pop(1400, 700, 0.1, 0.5), 10.14, 0.5)  # MRI flash
for j, tp in enumerate([11.45, 11.6, 11.75, 11.88]): add(bloop(450 + 90 * j, 850 + 90 * j), tp, 0.7)
add(stamp(), 11.82, 0.7); add(buzz(), 11.82, 0.4)                                   # ARTHRITIS?
for k in range(9): add(step_thump(), 12.88 + k * 0.105 * 2, 0.5)                    # doctor steps
add(pop(1000, 500, 0.12, 0.5), 14.2, 0.55)
for k in range(17): add(tick(), 15.48 + k * 0.04, 0.35 + 0.015 * k)                 # 60 counter
add(stamp(), 19.94, 0.95); add(thud(), 19.94, 0.7)                                  # CONTROL
add(bell(1568), 21.8, 0.6); add(bell(1976), 21.95, 0.6)                             # checks
add(whoosh(0.5, 0.45), 22.85, 0.6)                                                  # trophy rises
add(bell(1046, 0.5, 1.6), 23.32, 0.9); add(bell(1318, 0.45, 1.6), 23.4, 0.7); add(bell(1568, 0.45, 1.6), 23.48, 0.7)
for k in range(8): add(pop(900 + 120 * (k % 4), 500, 0.08, 0.4), 23.34 + k * 0.05, 0.4)  # confetti
for k in range(36): add(tick(), 25.75 + k * 0.025, 0.3 + 0.01 * k)                  # grid pops
add(stamp(), 27.7, 0.95); add(bell(1318, 0.5, 1.4), 27.72, 0.8)                     # NO LINK
for k in range(6): add(pop(900 + 100 * k, 500, 0.08, 0.4), 27.72 + k * 0.05, 0.35)
add(bloop(380, 220, 0.5), 31.1, 0.7)                                                # HMPH

# duck music under narration
env = np.abs(out); win = int(SR * 0.12)
env = np.convolve(env, np.ones(win) / win, mode="same")
duck = 1.0 - 0.6 * np.clip(env / 0.12, 0, 1)
mix *= duck.astype(np.float32)
final = out + mix * 0.9
final = final / np.max(np.abs(final)) * 0.93
sf.write("/tmp/mix2.wav", final, SR)
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", "/tmp/mix2.wav", "-codec:a", "libmp3lame", "-q:a", "4", "/home/claude/work/engine/knuckle-mix-v1.mp3"], check=True)
print("mix done", len(final) / SR)
