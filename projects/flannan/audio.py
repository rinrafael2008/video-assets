#!/usr/bin/env python3
"""Flannan Isles: narration + original synthesized sea/drone bed + SFX on the key words -> out/flannan-mix.m4a (-14 LUFS).
Free end to end (numpy only). usage: python3 -I projects/flannan/audio.py
"""
import os, sys, json
import numpy as np
import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "engine"))
sys.path.insert(0, HERE)
import sfx
from sfx import SR, _ma, rng
from story import at, TOTAL, CUTS


def env_exp(n, tau): return np.exp(-(np.arange(n) / SR) / tau)


def long_bell(f=196.0, dur=4.5, vol=1.0):
    n = int(SR * dur); t = np.arange(n) / SR; s = np.zeros(n)
    for ratio, a, tau in ((1.0, 1.0, 2.6), (2.0, 0.55, 1.8), (2.76, 0.45, 1.3), (5.4, 0.25, 0.7), (8.9, 0.12, 0.4)):
        s += a * np.sin(2 * np.pi * f * ratio * t) * np.exp(-t / tau)
    s *= (1 - np.exp(-t / 0.004))
    return (s * vol * 0.5).astype(np.float32)


def foghorn(dur=3.0, vol=1.0):
    n = int(SR * dur); t = np.arange(n) / SR
    f = 82.0 + 4.0 * np.sin(2 * np.pi * 0.7 * t)
    ph = 2 * np.pi * np.cumsum(f) / SR
    saw = 2 * ((ph / (2 * np.pi)) % 1) - 1
    s = _ma(saw, 30) * 1.0 + 0.5 * np.sin(ph * 2)
    env = np.clip(t / 0.7, 0, 1) ** 1.5 * np.exp(-np.maximum(t - 1.4, 0) / 0.6)
    return (s * env * vol * 0.6).astype(np.float32)


def wave_crash(dur=3.2, vol=1.0):
    n = int(SR * dur); t = np.arange(n) / SR
    nz = rng.standard_normal(n).astype(np.float32)
    body = _ma(nz, 24) * 3.0 + (nz - _ma(nz, 6)) * 0.35
    env = np.clip(t / 0.45, 0, 1) ** 2 * np.exp(-np.maximum(t - 0.45, 0) / 0.9)
    sub = np.sin(2 * np.pi * (38 + 40 * np.exp(-t / 0.25)) * t) * np.exp(-t / 0.7) * 0.9
    return ((body * env + sub) * vol * 0.6).astype(np.float32)


def rock_hit(vol=1.0):
    n = int(SR * 0.6); t = np.arange(n) / SR
    s = np.sin(2 * np.pi * (52 + 90 * np.exp(-t / 0.04)) * t) * np.exp(-t / 0.18)
    s += (rng.standard_normal(n) * np.exp(-t / 0.012)) * 0.5
    return (s * vol).astype(np.float32)


def music_flannan(mix, total, add):
    N = int(SR * total); t = np.arange(N) / SR
    # cold drone: A1 / C2 / E2 with slow breathing + a sliding beat note
    d = (np.sin(2 * np.pi * 55.0 * t) + 0.85 * np.sin(2 * np.pi * 55.6 * t)
         + 0.55 * np.sin(2 * np.pi * 65.4 * t + 0.6 * np.sin(2 * np.pi * 0.09 * t))
         + 0.40 * np.sin(2 * np.pi * 82.4 * t) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.06 * t + 1.0)))
    drone = (d * 0.050).astype(np.float32)
    # sea: low rumble + wash, swelling like waves (period ~ 11 s)
    swell = (0.5 + 0.5 * np.sin(2 * np.pi * 0.09 * t - 1.2)) ** 1.6
    nz = rng.standard_normal(N).astype(np.float32)
    rumble = _ma(nz, 420) * 9.0 * swell
    wash = (_ma(nz, 40) - _ma(nz, 400)) * 3.2 * swell
    wind = (_ma(rng.standard_normal(N).astype(np.float32), 70) - _ma(rng.standard_normal(N).astype(np.float32), 500)) * 2.4 * (0.4 + 0.6 * (0.5 + 0.5 * np.sin(2 * np.pi * 0.047 * t + 2.0)))
    bed = drone + (rumble * 0.10 + wash * 0.07 + wind * 0.06).astype(np.float32)
    # tension: the bed thins out on the last line, then dies on "gone."
    gone = at("gone.", 1)
    bed *= np.clip((gone + 0.9 - t) / 1.0, 0, 1).astype(np.float32) ** 0.8
    add(bed.astype(np.float32), 0.0, 1.0)
    # distant buoy bell, sparse
    for tb, f in ((3.2, 196.0), (11.0, 196.0), (19.6, 185.0), (28.2, 196.0), (36.6, 175.0), (46.0, 165.0)):
        add(sfx.reverb(long_bell(f, 5.0, 1.0), wet=0.35, rt=2.2), tb, 0.10)


def voice_fx(v):
    """dry, clean voice: no reverb, no bass boost -- level only"""
    return (v / (np.max(np.abs(v)) + 1e-9) * 0.95).astype(np.float32)


def cues():
    c = []
    for t in CUTS: c.append(("whoosh", t - 0.05))
    # hook: low hit on 1900, riser into FAKE, stamp
    c += [("thud_lo", at("1900.")), ("riser_s", at("Fake.") - 1.55), ("sting", at("Fake.")), ("thud_lo", at("Fake.", off=0.02))]
    c += [("thud", at("11")), ("foghorn", at("arrives.") - 0.9)]
    # door shuts, latch
    c += [("creak", at("door") - 0.55), ("thud", at("shut.", off=0.05)), ("click", at("shut.", off=0.2))]
    c += [("tick", at("unmade.")), ("tick", at("gone.", 0)), ("tick", at("peg."))]
    c += [("thud", at("12", off=0.0)), ("thud", at("1965.")), ("stamp", at("Fiction.", off=0.1))]
    c += [("rock", at("boulder")), ("thud", at("ton,")), ("thud", at("hundred"))]
    c += [("wave", at("freak", off=0.2)), ("thud_lo", at("never")), ("bell_big", at("gone.", 1, off=0.1))]
    # heartbeat under "Their bodies were never found."
    tt = at("Their"); k = 0
    while tt < at("found.", end=True) + 0.6:
        c.append(("heart", tt)); tt += 0.95; k += 1
    return c


def main():
    out_dir = os.path.join(HERE, "out"); os.makedirs(out_dir, exist_ok=True)
    sfx.LIB.update({"foghorn": lambda: foghorn(), "wave": lambda: wave_crash(), "rock": lambda: rock_hit(),
                    "bell_big": lambda: sfx.reverb(long_bell(131.0, 6.0, 1.0), wet=0.3, rt=2.5)})
    sfx.GAIN.update({"foghorn": 0.45, "wave": 0.85, "rock": 0.8, "bell_big": 0.9,
                     "whoosh": 0.16, "sting": 0.5, "thud": 0.5, "thud_lo": 0.55, "creak": 0.35, "click": 0.5, "heart": 0.5,
                     "riser_s": 0.45, "tick": 0.3, "stamp": 0.6})
    wav = os.path.join(HERE, "narration.wav")
    aac = os.path.join(out_dir, "flannan-mix.m4a")
    sfx.mix_from_cues(wav, TOTAL, cues(), aac, workdir=out_dir, music_fn=music_flannan, voice_fx=voice_fx)
    print("wrote", aac)


if __name__ == "__main__":
    main()
