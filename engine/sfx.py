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


# ---------------------------------------------------------------- horror kit
def _ma(x, k):
    """fast moving-average low-pass"""
    cs = np.cumsum(np.concatenate([np.zeros(k, dtype=np.float64), x.astype(np.float64)]))
    out = (cs[k:] - cs[:-k]) / k
    return out.astype(np.float32)


def creak(dur=1.6, vol=0.5):
    n = int(SR * dur); t = np.arange(n) / SR
    f = 150 + 55 * np.sin(2 * np.pi * 3.1 * t) + 35 * np.sin(2 * np.pi * 7.3 * t + 1) + 90 * (t / dur)
    ph = 2 * np.pi * np.cumsum(f) / SR
    saw = 2 * ((ph / (2 * np.pi)) % 1) - 1
    gate = (0.5 + 0.5 * np.sin(2 * np.pi * 11 * t + 2 * np.sin(2 * np.pi * 2.3 * t))) ** 2
    s = _ma(saw * gate, 7)
    env = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 0.7
    return (s * env * vol).astype(np.float32)


def click(vol=0.6):
    n = int(SR * 0.09); t = np.arange(n) / SR
    s = rng.standard_normal(n).astype(np.float32) * env_exp(n, 0.003) + np.sin(2 * np.pi * 1500 * t) * env_exp(n, 0.012) * 0.6
    s += np.sin(2 * np.pi * 110 * t) * env_exp(n, 0.03) * 0.5
    return (s * vol).astype(np.float32)


def bulb_on(vol=0.5):
    """switch clunk + flickering electric hum"""
    dur = 1.3; n = int(SR * dur); t = np.arange(n) / SR
    hum = sum(np.sin(2 * np.pi * f * t) * a for f, a in ((100, 1.0), (200, 0.6), (300, 0.35), (500, 0.15)))
    gate = np.ones(n, dtype=np.float32); g = np.random.RandomState(3).rand(int(dur * 40)) > 0.45
    for i, on in enumerate(g):
        if i / 40.0 < 0.55 and not on: gate[int(i / 40.0 * SR):int((i + 1) / 40.0 * SR)] = 0.05
    s = hum * gate * np.exp(-np.maximum(t - 0.55, 0) / 0.5) * 0.22
    s = s.astype(np.float32); s[: int(SR * 0.09)] += click(1.0)[: int(SR * 0.09)]
    return (s * vol).astype(np.float32)


def bulb_off(vol=0.5):
    n = int(SR * 0.5); t = np.arange(n) / SR
    hum = (np.sin(2 * np.pi * 100 * t) + 0.5 * np.sin(2 * np.pi * 200 * t)) * np.exp(-t / 0.07) * 0.25
    gate = (np.random.RandomState(8).rand(n // 600 + 1) > 0.35).astype(np.float32).repeat(600)[:n]
    s = (hum * gate).astype(np.float32); s[:int(SR * 0.09)] += click(0.9)[:int(SR * 0.09)]
    return (s * vol).astype(np.float32)


def heart(vol=0.6):
    n = int(SR * 0.55); out = np.zeros(n, dtype=np.float32)
    a = thud(0.3, 1.0); b = thud(0.26, 0.7)
    out[: len(a)] += a; d = int(SR * 0.21); out[d:d + len(b)] += b[: n - d]
    return (out * vol).astype(np.float32)


def riser(dur=2.0, vol=0.5):
    n = int(SR * dur); t = np.arange(n) / SR
    f = 180 * (11.0 ** (t / dur)); tone = np.sin(2 * np.pi * np.cumsum(f) / SR)
    nz = rng.standard_normal(n).astype(np.float32); nz = nz - _ma(nz, max(2, int(SR / 700)))
    env = (t / dur) ** 2.2
    return ((tone * 0.5 + nz * 0.6) * env * vol).astype(np.float32)


def sting(vol=1.0):
    dur = 2.4; n = int(SR * dur); t = np.arange(n) / SR; s = np.zeros(n, dtype=np.float64)
    for f0, f1 in ((1180, 1250), (1255, 1340), (1760, 1650), (2217, 2330), (880, 820), (1568, 1500)):
        f = f0 + (f1 - f0) * np.minimum(t / 0.7, 1); ph = 2 * np.pi * np.cumsum(f) / SR
        s += 2 * ((ph / (2 * np.pi)) % 1) - 1
    s *= env_exp(n, 0.85) * 0.2
    fb = 36 + 80 * np.exp(-t / 0.06); boom = np.sin(2 * np.pi * np.cumsum(fb) / SR) * env_exp(n, 0.6) * 1.0
    nz = rng.standard_normal(n) * env_exp(n, 0.12) * 0.5
    x = np.tanh(2.4 * (s + boom + nz)) / np.tanh(2.4)          # saturate: denser and louder than the peak suggests
    return (x * vol).astype(np.float32)


def tap(vol=0.5):
    n = int(SR * 0.12); t = np.arange(n) / SR
    return ((np.sin(2 * np.pi * 330 * t) + 0.5 * np.sin(2 * np.pi * 620 * t)) * env_exp(n, 0.02) * vol).astype(np.float32)


def beep(vol=0.4):
    n = int(SR * 0.22); t = np.arange(n) / SR
    s = np.sign(np.sin(2 * np.pi * 1760 * t)) * 0.4 + np.sin(2 * np.pi * 1760 * t) * 0.3
    return (s * np.where(t < 0.18, 1, 0) * vol).astype(np.float32)


def reverb(x, wet=0.18, rt=1.1, seed=4):
    r = np.random.RandomState(seed); n = int(SR * rt); t = np.arange(n) / SR
    ir = r.standard_normal(n).astype(np.float32) * np.exp(-t / (rt * 0.28)); ir = _ma(ir, 5); ir[0] = 0
    ir /= np.sqrt((ir ** 2).sum()) + 1e-9
    L = len(x) + n; N = 1 << (L - 1).bit_length()
    y = np.fft.irfft(np.fft.rfft(x, N) * np.fft.rfft(ir, N), N)[: len(x)].astype(np.float32)
    return x * (1 - wet * 0.4) + y * wet * 1.6


def mbox(f, vol=1.0, dur=1.1):
    n = int(SR * dur); t = np.arange(n) / SR
    s = np.sin(2 * np.pi * f * t) + 0.38 * np.sin(2 * np.pi * f * 3.0 * t) * np.exp(-t / 0.12) + 0.2 * np.sin(2 * np.pi * f * 5.1 * t) * np.exp(-t / 0.05)
    return (s * env_exp(n, 0.22) * (1 - np.exp(-t / 0.002)) * vol).astype(np.float32)


def music_horror(mix, total, add, stop=37.55, stop_fade=0.35, start=4.4):
    """cold drone + wind + a slowly detuning music box; everything dies when the street light goes out (stop)"""
    N = int(SR * total); t = np.arange(N) / SR
    ramp = 0.55 + 0.45 * np.clip(t / max(stop, 1.0), 0, 1)
    d = (np.sin(2 * np.pi * 55 * t) + np.sin(2 * np.pi * 55.7 * t) * 0.9 + 0.5 * np.sin(2 * np.pi * 82.4 * t + 0.4 * np.sin(2 * np.pi * 0.11 * t))
         + 0.35 * np.sin(2 * np.pi * 116.5 * t) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.07 * t)))
    w = rng.standard_normal(N).astype(np.float32)
    w = _ma(w, 220) * 5.0 * (0.55 + 0.45 * np.sin(2 * np.pi * 0.13 * t + 1.0)) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.031 * t))
    bed = ((d * 0.16).astype(np.float32) + (w * 0.5).astype(np.float32)) * ramp.astype(np.float32)
    cut = np.clip((stop - t) / stop_fade, 0, 1).astype(np.float32); bed *= cut
    add(bed.astype(np.float32), 0.0, 1.0)
    # music box: original 8-note figure in A minor with a chromatic sting, 63 bpm, detuning as the story goes on
    beat = 60.0 / 63; fig = [81, 84, 88, 87, 84, 81, 80, 83]; k = 0; tt = start
    while tt < stop - 0.2:
        drift = 1 - 0.0016 * k
        f = 440.0 * 2 ** ((fig[k % 8] - 69) / 12.0) * drift
        g = 0.07 * (1.0 if k % 8 != 0 else 1.3)
        add(mbox(f, 1.0), tt, g)
        tt += beat * (0.5 if k % 8 in (1, 2, 4, 5) else 1.0) * (1.0 + 0.004 * k)
        k += 1


def _install():
    LIB.update({"creak": lambda: creak(), "click": lambda: click(), "bulb_on": lambda: bulb_on(), "bulb_off": lambda: bulb_off(),
                "heart": lambda: heart(), "riser": lambda: riser(), "riser_s": lambda: riser(1.6, 0.6), "sting": lambda: sting(),
                "tap": lambda: tap(), "beep": lambda: beep(), "thud_lo": lambda: thud(0.5, 1.0)})
    GAIN.update({"creak": 0.55, "click": 0.7, "bulb_on": 0.7, "bulb_off": 0.8, "heart": 0.55, "riser": 0.55, "riser_s": 0.5, "sting": 1.0,
                 "tap": 0.5, "beep": 0.5, "thud_lo": 0.8})
DRY = {"sting"}


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


def mix_from_cues(narration_wav, total, cues, out_aac, workdir="/tmp", music_fn=None, voice_fx=None, master=None):
    """cues: [(kind, seconds)]. Writes a loudness-normalised (-14 LUFS) AAC for muxing."""
    N = int(SR * total)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", narration_wav, "-ar", str(SR), "-ac", "1", f"{workdir}/_narr44.wav"], check=True)
    narr, _ = sf.read(f"{workdir}/_narr44.wav", dtype="float32")
    voice = np.zeros(N, dtype=np.float32); voice[: min(len(narr), N)] += narr[:N] * 0.95
    if voice_fx: voice = voice_fx(voice).astype(np.float32)
    dry = np.zeros(N, dtype=np.float32)
    mix = np.zeros(N, dtype=np.float32)

    def add(sig, t0, gain=1.0):
        i0 = int(t0 * SR)
        if i0 < 0 or i0 >= N: return
        seg = sig[: N - i0]; mix[i0:i0 + len(seg)] += seg * gain
    (music_fn or music)(mix, total, add)
    fade = np.ones(N, dtype=np.float32); fi = int(SR * 0.5); fo = int(SR * 1.3)
    fade[:fi] = np.linspace(0, 1, fi); fade[-fo:] = np.linspace(1, 0, fo); mix *= fade
    for kind, t in cues:
        if kind in LIB:
            if kind in DRY:
                sig = LIB[kind]() * GAIN[kind]; i0 = int(t * SR)
                if 0 <= i0 < N: seg = sig[: N - i0]; dry[i0:i0 + len(seg)] += seg
            else: add(LIB[kind](), t, GAIN[kind])
    env = np.abs(voice); win = int(SR * 0.12); env = np.convolve(env, np.ones(win) / win, mode="same")
    mix *= (1.0 - 0.6 * np.clip(env / 0.12, 0, 1)).astype(np.float32)          # duck music under the voice
    final = voice + mix * 0.9 + dry * 1.0; final = final / np.max(np.abs(final)) * 0.93
    sf.write(f"{workdir}/_mix.wav", final, SR)
    # loudness chain that fixed the quiet raw mix (-25 LUFS -> about -14.7): compress, two-pass loudnorm, limit
    mst = dict(pre="acompressor=threshold=0.1:ratio=3:attack=5:release=120:makeup=2", I=-14.0, TP=-1.5); mst.update(master or {})
    pre = mst["pre"]; LU = mst["I"]; TP = mst["TP"]
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", f"{workdir}/_mix.wav", "-af", pre + f",loudnorm=I={LU}:TP={TP}:LRA=11:print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True)
    import json, re
    m = json.loads(re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", r.stderr, re.S).group(0))
    ln = (pre + f",loudnorm=I={LU}:TP={TP}:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}"
          f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true,alimiter=limit=0.89")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", f"{workdir}/_mix.wav", "-af", ln, "-ar", "48000", "-c:a", "aac", "-b:a", "192k", out_aac], check=True)
    return out_aac


_install()
