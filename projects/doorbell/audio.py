#!/usr/bin/env python3
"""Doorbell: dry Kokoro narration (two voices) + original synthesized sound design: phone pings, muffled footsteps overhead, porch wind and crickets,
camera hiss, a detuning music box that stops when the voice behind the door speaks, a heartbeat, a knob ratchet and a latch, then a hard gated silence
and the buzz that loops the video. Free end to end (numpy). usage: python3 -I projects/doorbell/audio.py -> projects/doorbell/out/doorbell-mix.m4a
"""
import os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "engine")); sys.path.insert(0, HERE)
import sfx
from sfx import SR, _ma, rng, env_exp
import scenes
from scenes import at, TOTAL, CUTS, SEND_T, REPLY_T, SECOND_T, THUMPS, C_BLACK, C_END, C_CAM, C_CAM2, C_RUN, C_KNOB, C_DOOR


def _lp(x, k): return _ma(x.astype(np.float32), k)


def notif(vol=1.0):
    """phone notification: a vibration burr under a two-note ping"""
    n = int(SR * 0.7); t = np.arange(n) / SR
    s = np.sin(2 * np.pi * 1175 * t) * np.exp(-t / 0.16)
    t2 = np.clip(t - 0.11, 0, None); s += np.sin(2 * np.pi * 1568 * t2) * np.exp(-t2 / 0.22) * (t >= 0.11)
    s += 0.25 * np.sin(2 * np.pi * 2350 * t2) * np.exp(-t2 / 0.08) * (t >= 0.11)
    v = (np.sign(np.sin(2 * np.pi * 96 * t)) * 0.3 + np.sin(2 * np.pi * 144 * t) * 0.25) * np.where(t < 0.3, 1.0, 0.0) * np.exp(-t / 0.2)
    return ((s * 0.55 + v) * (1 - np.exp(-t / 0.002)) * vol).astype(np.float32)


def recv(vol=1.0):
    n = int(SR * 0.45); t = np.arange(n) / SR
    s = (np.sin(2 * np.pi * 1568 * t) + 0.4 * np.sin(2 * np.pi * 2093 * t)) * np.exp(-t / 0.09)
    return (s * (1 - np.exp(-t / 0.002)) * vol).astype(np.float32)


def thump_up(vol=1.0):
    """something heavy, one floor up: muffled thud, a little ceiling rattle"""
    n = int(SR * 0.9); t = np.arange(n) / SR
    body = np.sin(2 * np.pi * np.cumsum(58 + 50 * np.exp(-t / 0.05)) / SR) * np.exp(-t / 0.16)
    nz = _lp(rng.standard_normal(n), 18) * np.exp(-t / 0.22) * 2.2
    r = np.random.RandomState(3); rat = np.zeros(n)
    for _ in range(6):
        i0 = int(SR * r.uniform(0.05, 0.6)); m = int(SR * 0.03)
        z = r.standard_normal(m); z = (z - _ma(z.astype(np.float32), 6)) * np.exp(-np.arange(m) / (SR * 0.008)) * r.uniform(0.06, 0.16); rat[i0:i0 + m] += z
    return ((body + nz * 0.5 + rat) * vol).astype(np.float32)


def step_s(vol=1.0):
    n = int(SR * 0.35); t = np.arange(n) / SR
    s = np.sin(2 * np.pi * np.cumsum(70 + 40 * np.exp(-t / 0.03)) / SR) * np.exp(-t / 0.07) + _lp(rng.standard_normal(n), 10) * np.exp(-t / 0.05) * 1.5
    return (s * vol).astype(np.float32)


def creak_s(vol=1.0): return (sfx.creak(0.42, 1.0) * vol).astype(np.float32)


def kclick(vol=1.0):
    """tiny metal ratchet click from the knob mechanism"""
    n = int(SR * 0.09); t = np.arange(n) / SR
    s = (np.sin(2 * np.pi * 2650 * t) * 0.5 + np.sin(2 * np.pi * 3720 * t) * 0.35) * np.exp(-t / 0.012)
    nz = rng.standard_normal(n).astype(np.float32); s += (nz - _ma(nz, 5)) * np.exp(-t / 0.004) * 0.7
    return (s * vol).astype(np.float32)


def latch(vol=1.0):
    out = np.zeros(int(SR * 0.4), dtype=np.float32)
    a = kclick(1.0) * 1.3; out[: len(a)] += a
    d = int(SR * 0.055); b = thud(0.2, 0.8); out[d:d + len(b)] += b
    return (out * vol).astype(np.float32)


def thud(dur, vol): return sfx.thud(dur, vol)


def hit(vol=1.0):
    """the door swings open: one short heavy hit that ends exactly on the black cut"""
    n = int(SR * 0.17); t = np.arange(n) / SR
    s = np.sin(2 * np.pi * np.cumsum(40 + 90 * np.exp(-t / 0.04)) / SR) * np.exp(-t / 0.12) + rng.standard_normal(n) * np.exp(-t / 0.03) * 0.55
    s *= np.clip((0.17 - t) / 0.02, 0, 1)
    return (np.tanh(1.8 * s) / np.tanh(1.8) * vol).astype(np.float32)


def boom(vol=1.0):
    n = int(SR * 1.2); t = np.arange(n) / SR
    s = np.sin(2 * np.pi * np.cumsum(34 + 70 * np.exp(-t / 0.07)) / SR) * np.exp(-t / 0.4) + rng.standard_normal(n) * np.exp(-t / 0.05) * 0.3
    return (s * vol).astype(np.float32)


def _gate(t, a, b, fi=0.4, fo=0.4):
    return np.clip(np.minimum((t - a) / fi, (b - t) / fo), 0, 1).astype(np.float32)


def bed(mix, total, add):
    N = int(SR * total); t = np.arange(N) / SR
    cut = np.clip((C_BLACK - t) / 0.03, 0, 1).astype(np.float32)               # everything dies on the black cut, and stays dead
    ramp = (0.5 + 0.5 * np.clip(t / 31.0, 0, 1)).astype(np.float32)
    drone = np.sin(2 * np.pi * 55.0 * t) + 0.9 * np.sin(2 * np.pi * 55.7 * t) + 0.5 * np.sin(2 * np.pi * 82.4 * t + 0.4 * np.sin(2 * np.pi * 0.1 * t))
    room = _ma(rng.standard_normal(N).astype(np.float32), 260) * 6.0
    # porch: wind + crickets + camera hiss while the doorbell camera is on screen
    cam = np.maximum(_gate(t, 7.85, C_CAM + 0.1), _gate(t, C_CAM2 - 0.05, C_RUN + 0.5, 0.2, 0.2))
    nz = rng.standard_normal(N).astype(np.float32)
    wind = _lp(nz, 60) * (3.2 + 2.0 * np.sin(2 * np.pi * 0.23 * t + 1.0)) * cam
    hiss = (nz - _ma(nz, 6)) * 0.07 * cam
    cr = np.zeros(N, dtype=np.float32)
    for k in range(4):
        cr += (np.sin(2 * np.pi * (4300 + 130 * k) * t) * (np.sin(2 * np.pi * (31 + 2 * k) * t) > 0.3) * (np.sin(2 * np.pi * (2.2 + 0.3 * k) * t + k) > 0.6)).astype(np.float32)
    crick = cr * cam * 0.35
    beds = (drone * 0.05).astype(np.float32) * ramp + room * 0.35 + wind * 0.05 + hiss + crick * 0.05
    add((beds * cut).astype(np.float32), 0.0, 1.0)
    # music box lullaby, detuning, from the lock screen until the voice behind the door speaks
    fig = [69, 72, 76, 72, 69, 71, 68, 64]; beat = 60.0 / 54; k = 0; tt_ = 3.45
    stop = at("honey") - 0.05
    while tt_ < stop:
        drift = 1 - 0.0016 * k
        f = 440.0 * 2 ** ((fig[k % 8] - 69) / 12.0) * drift
        add(sfx.mbox(f, 1.0), tt_, 0.07 * (1.3 if k % 8 == 0 else 1.0) * float(np.clip((stop - tt_) / 0.6 + 0.4, 0, 1)))
        tt_ += beat * (0.5 if k % 8 in (1, 2, 4, 5) else 1.0); k += 1


def cues():
    c = [("notif", 0.0), ("notif", 2.2)]
    for t in CUTS[:-2]: c.append(("whoosh", t - 0.06))
    c += [("thump_up", THUMPS[0]), ("thump_up", THUMPS[1]), ("creak", 4.3), ("creak_s", 5.0)]
    c += [("beep", 7.95), ("beep", 8.82)]
    # typing, send, the dots, her answer, the second text
    for i in range(21): c.append(("tick", 13.72 + i * 0.068))
    c += [("whoosh", SEND_T), ("pop_hi", SEND_T + 0.06), ("pop_lo", 16.13), ("tick", 16.72), ("pop_lo", 17.30)]
    c += [("recv", REPLY_T), ("notif", SECOND_T)]
    # someone on the stairs, then outside the bedroom door
    c += [("step_s", 22.95), ("step_s", 23.22), ("creak_s", 23.55), ("step_s", 24.05), ("creak_s", 25.2)]
    c += [("riser", C_RUN - 1.6), ("sting", C_RUN + 0.0), ("boom", C_RUN + 0.0)]
    tt = 18.6; gap = 1.0
    while tt < 33.75:
        c.append(("heart", tt)); tt += gap; gap = max(gap - 0.035, 0.55)
    # the knob: ratchet, ratchet, ratchet, latch, hinge, and the door swings open into black
    for tk in (32.62, 32.9, 33.12, 33.34, 33.52, 33.70): c.append(("kclick", tk))
    c += [("latch", 33.93), ("creak_s", 34.0), ("hit", 34.18)]
    c += [("notif", C_END)]
    return c


def main():
    out_dir = os.path.join(HERE, "out"); os.makedirs(out_dir, exist_ok=True)
    sfx.LIB.update({"notif": lambda: notif(), "recv": lambda: recv(), "thump_up": lambda: thump_up(), "step_s": lambda: step_s(), "creak_s": lambda: creak_s(),
                    "kclick": lambda: kclick(), "latch": lambda: latch(), "hit": lambda: hit(), "boom": lambda: boom()})
    sfx.GAIN.update({"notif": 0.55, "recv": 0.4, "thump_up": 0.7, "step_s": 0.5, "creak_s": 0.3, "creak": 0.28, "kclick": 0.5, "latch": 0.85, "hit": 0.9, "boom": 0.7,
                     "whoosh": 0.14, "tick": 0.2, "beep": 0.25, "pop_hi": 0.3, "pop_lo": 0.3, "heart": 0.55, "riser": 0.36, "sting": 0.75})
    sfx.DRY.update({"notif", "recv", "boom", "sting", "hit", "latch"})
    wav = os.path.join(HERE, "narration.wav")
    aac = os.path.join(out_dir, "doorbell-mix.m4a")
    sfx.mix_from_cues(wav, TOTAL, cues(), aac, workdir=out_dir, music_fn=bed, voice_fx=lambda v: (v / (np.max(np.abs(v)) + 1e-9) * 0.95).astype(np.float32))
    tmp = os.path.join(out_dir, "_safe.m4a")                                       # true-peak safety: AAC can overshoot the sample-peak limiter by about 1 dB
    import subprocess
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", aac, "-af", "alimiter=limit=0.78:level=false", "-ar", "48000", "-c:a", "aac", "-b:a", "192k", tmp], check=True)
    os.replace(tmp, aac)
    print("wrote", aac)


if __name__ == "__main__":
    main()
