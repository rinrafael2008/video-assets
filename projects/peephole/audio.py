#!/usr/bin/env python3
"""Peephole: dry Kokoro narration + original synthesized sound design (knocks, lamp hum that follows the real flicker, rain, drone,
detuned music box, heartbeat, stings). Free end to end (numpy). usage: python3 -I projects/peephole/audio.py -> out/peephole-mix.m4a
"""
import os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "engine")); sys.path.insert(0, HERE)
import sfx
from sfx import SR, _ma, rng, env_exp
import scenes
from scenes import at, TOTAL, CUTS, K1, K2, K3, R1, R2, R3, CK, BURSTS, lamp_flick


def knock(pitch=92.0, vol=1.0):
    n = int(SR * 0.5); t = np.arange(n) / SR
    body = np.sin(2 * np.pi * np.cumsum(pitch + 55 * np.exp(-t / 0.018)) / SR) * np.exp(-t / 0.085)
    wood = (np.sin(2 * np.pi * 215 * t) * 0.5 + np.sin(2 * np.pi * 470 * t) * 0.3 + np.sin(2 * np.pi * 790 * t) * 0.15) * np.exp(-t / 0.035)
    nz = rng.standard_normal(n).astype(np.float32); click = (nz - _ma(nz, 8)) * np.exp(-t / 0.004)
    s = body + wood * 0.55 + click * 0.6
    s *= (1 - np.exp(-t / 0.0007))
    return (s / (np.max(np.abs(s)) + 1e-9) * vol).astype(np.float32)


def cknock(vol=1.0):
    """hollow louvered closet door: lower, boxy, with rattling slats"""
    n = int(SR * 0.7); t = np.arange(n) / SR
    s = knock(138.0, 1.0)[:n].astype(np.float64)
    s = np.pad(s, (0, n - len(s)))
    s += np.sin(2 * np.pi * 312 * t) * np.exp(-t / 0.12) * 0.35
    r = np.random.RandomState(5)
    for _ in range(9):
        t0 = int(SR * r.uniform(0.01, 0.34)); m = int(SR * 0.025)
        nz = r.standard_normal(m); nz = nz - _ma(nz.astype(np.float32), 4)
        s[t0:t0 + m] += nz * np.exp(-np.arange(m) / (SR * 0.006)) * r.uniform(0.1, 0.3)
    return (s / (np.max(np.abs(s)) + 1e-9) * vol).astype(np.float32)


def relight(vol=1.0):
    n = int(SR * 0.5); t = np.arange(n) / SR
    hum = (np.sin(2 * np.pi * 100 * t) + 0.5 * np.sin(2 * np.pi * 200 * t) + 0.25 * np.sin(2 * np.pi * 300 * t)) * np.exp(-t / 0.18) * 0.35
    s = hum.astype(np.float32); c = sfx.click(1.0); s[:len(c)] += c
    s[: int(SR * 0.012)] += rng.standard_normal(int(SR * 0.012)).astype(np.float32) * 0.5
    return (s * vol).astype(np.float32)


def boom(vol=1.0):
    n = int(SR * 1.4); t = np.arange(n) / SR
    s = np.sin(2 * np.pi * np.cumsum(34 + 70 * np.exp(-t / 0.07)) / SR) * np.exp(-t / 0.45)
    s += (rng.standard_normal(n) * np.exp(-t / 0.05)) * 0.3
    return (s * vol).astype(np.float32)


def hum_env(t):
    if 10.46 <= t < 13.18: return 0.8 + 0.2 * math_sin(t)
    if 16.15 <= t < 33.97 or 43.55 <= t < 48.42: return float(np.clip(lamp_flick(t), 0, 1))
    return 0.0


def math_sin(t): return float(np.sin(t * 31.0) * np.sin(t * 3.1))


def music_peephole(mix, total, add):
    N = int(SR * total); t = np.arange(N) / SR
    cut = np.clip((50.35 - t) / 0.04, 0, 1).astype(np.float32)             # everything dies on the final cut
    ramp = (0.55 + 0.45 * np.clip(t / 48.0, 0, 1)).astype(np.float32)
    drone = (np.sin(2 * np.pi * 55.0 * t) + 0.9 * np.sin(2 * np.pi * 55.8 * t) + 0.5 * np.sin(2 * np.pi * 82.4 * t + 0.4 * np.sin(2 * np.pi * 0.1 * t))
             + 0.30 * np.sin(2 * np.pi * 116.5 * t) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.07 * t)))
    room = _ma(rng.standard_normal(N).astype(np.float32), 260) * 6.0
    # lamp hum that follows the real flicker of the picture
    tt = np.arange(0, total, 0.005); env = np.interp(t, tt, np.array([hum_env(x) for x in tt])).astype(np.float32)
    hum = (np.sin(2 * np.pi * 100 * t) * 0.6 + np.sin(2 * np.pi * 200 * t) * 0.3 + np.sin(2 * np.pi * 300 * t) * 0.15
           + 0.3 * (rng.standard_normal(N).astype(np.float32) - _ma(rng.standard_normal(N).astype(np.float32), 12))) * env
    # rain + wind over the tower shot
    r_env = np.clip(np.minimum((t - 7.8) / 0.4, (10.6 - t) / 0.3), 0, 1).astype(np.float32)
    nz = rng.standard_normal(N).astype(np.float32)
    rain = ((nz - _ma(nz, 10)) * 0.5 + _ma(nz, 30) * 1.5) * r_env
    bed = (drone * 0.055).astype(np.float32) * ramp + room * 0.35 + hum.astype(np.float32) * 0.055 + rain * 0.06
    add((bed * cut).astype(np.float32), 0.0, 1.0)
    # music box lullaby, detuning, only while the narrator is watching (14-33.4) and again under the finger (43.6-48.4)
    fig = [76, 72, 69, 71, 72, 69, 64, 67]; beat = 60.0 / 54
    for t0, t1, g0 in ((14.0, 33.3, 0.075), (43.6, 48.3, 0.06)):
        k = 0; tt_ = t0
        while tt_ < t1:
            drift = 1 - 0.0021 * k - (0.012 if t0 > 40 else 0.0)
            f = 440.0 * 2 ** ((fig[k % 8] - 69) / 12.0) * drift
            add(sfx.mbox(f, 1.0), tt_, g0 * (1.3 if k % 8 == 0 else 1.0))
            tt_ += beat * (0.5 if k % 8 in (1, 2, 4, 5) else 1.0)
            k += 1
    # sparse glassy high notes in the closet scenes
    for tn, f in ((39.9, 1318.5), (42.6, 1244.5), (44.4, 1174.7), (46.4, 1318.5)):
        add(sfx.mbox(f, 1.0, 1.6), tn, 0.03)


def cues():
    c = []
    for t in CUTS: c.append(("whoosh", t - 0.06))
    c += [("knock", K1 + 0.02), ("knock", K2 + 0.02), ("knock", K3 + 0.02)]
    c += [("thud_lo", at("something") - 0.02), ("thud_lo", at("alone")), ("thud_lo", at("fourteenth")), ("whoosh_big", 8.0), ("whoosh_big", 9.8)]
    c += [("riser", 13.2), ("thud_lo", 16.15)]
    for s_, e_ in BURSTS: c += [("bulb_off", s_), ("relight", e_)]
    c += [("boom", 19.40), ("boom", 23.35), ("boom", 24.42), ("riser_s", 24.4), ("boom", 26.30), ("sting", 27.36), ("boom", 27.36)]
    c += [("creak", 28.7), ("creak", 31.2)]
    tt = 23.6; gap = 1.0
    while tt < 33.4:
        c.append(("heart", tt)); tt += gap; gap = max(gap - 0.03, 0.62)
    c += [("thud_lo", 33.97)]
    c += [("knock", R1 + 0.02), ("knock", R2 + 0.02), ("cknock", R3 + 0.02), ("creak", 38.6), ("riser_s", 36.9)]
    c += [("cknock", t + 0.02) for t in CK[1:]]
    c += [("creak", 41.9), ("boom", at("closet.")), ("riser", 46.4)]
    c += [("sting", at("alone", 1)), ("boom", at("alone", 1)), ("creak", 48.55), ("thud_lo", 50.35)]
    c += [("knock_soft", 50.75), ("knock_soft", 51.25)]
    return c


def main():
    out_dir = os.path.join(HERE, "out"); os.makedirs(out_dir, exist_ok=True)
    sfx.LIB.update({"knock": lambda: knock(), "cknock": lambda: cknock(), "knock_soft": lambda: knock(80.0, 0.55), "relight": lambda: relight(), "boom": lambda: boom()})
    sfx.GAIN.update({"knock": 0.95, "cknock": 0.9, "knock_soft": 0.8, "relight": 0.4, "boom": 0.7, "bulb_off": 0.45, "whoosh": 0.14, "whoosh_big": 0.28,
                     "sting": 0.8, "thud_lo": 0.6, "heart": 0.55, "creak": 0.32, "riser_s": 0.38, "riser": 0.36})
    sfx.DRY.update({"knock", "cknock", "knock_soft", "sting", "boom"})
    wav = os.path.join(HERE, "narration.wav")
    aac = os.path.join(out_dir, "peephole-mix.m4a")
    sfx.mix_from_cues(wav, TOTAL, cues(), aac, workdir=out_dir, music_fn=music_peephole, voice_fx=lambda v: (v / (np.max(np.abs(v)) + 1e-9) * 0.95).astype(np.float32))
    print("wrote", aac)


if __name__ == "__main__":
    main()
