#!/usr/bin/env python3
"""Sleeper: Kokoro narration (voice + two whispers) + original synthesized sound design: phone pings, a heart monitor that speeds up, the flat-line tone for Sleeper 2,
mic hiss under the sleep-talking clip, a music box that detunes, cloth rustle as the second sleeper sits up, then a hard gated silence and the ping that loops the video.
Free end to end (numpy). usage: python3 -I projects/sleeper/audio.py -> projects/sleeper/out/sleeper-mix.m4a
"""
import os, sys, subprocess
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "..", "engine"))
import sfx
from sfx import SR, _ma, rng, env_exp
import scenes
from scenes import at, TOTAL, CUTS, BEATS, C_LIVE, C_NIGHT, C_CLIP, C_LIVE2, C_ALERT, C_BED, C_BLACK, C_END, T_PAN, T_RISE0, T_RISE1


def _lp(x, k): return _ma(x.astype(np.float32), k)


def notif(vol=1.0):
    n = int(SR * 0.7); t = np.arange(n) / SR
    s = np.sin(2 * np.pi * 1175 * t) * np.exp(-t / 0.16)
    t2 = np.clip(t - 0.11, 0, None); s += np.sin(2 * np.pi * 1568 * t2) * np.exp(-t2 / 0.22) * (t >= 0.11)
    s += 0.25 * np.sin(2 * np.pi * 2350 * t2) * np.exp(-t2 / 0.08) * (t >= 0.11)
    v = (np.sign(np.sin(2 * np.pi * 96 * t)) * 0.3 + np.sin(2 * np.pi * 144 * t) * 0.25) * np.where(t < 0.3, 1.0, 0.0) * np.exp(-t / 0.2)
    return ((s * 0.55 + v) * (1 - np.exp(-t / 0.002)) * vol).astype(np.float32)


def alarm(vol=1.0):
    """the 'Guest detected' alert: two low-high urgent chirps"""
    n = int(SR * 0.6); t = np.arange(n) / SR; s = np.zeros(n)
    for t0 in (0.0, 0.2):
        u = np.clip(t - t0, 0, None); s += (np.sin(2 * np.pi * 880 * u) + 0.4 * np.sin(2 * np.pi * 1320 * u)) * np.exp(-u / 0.07) * (t >= t0)
    return (s * (1 - np.exp(-t / 0.002)) * vol).astype(np.float32)


def hmon(vol=1.0):
    """heart-monitor blip"""
    n = int(SR * 0.16); t = np.arange(n) / SR
    return (np.sin(2 * np.pi * 1000 * t) * np.exp(-t / 0.05) * (1 - np.exp(-t / 0.001)) * vol).astype(np.float32)


def rustle(dur=1.8, vol=1.0):
    """bedclothes sliding: band-limited noise in slow bursts"""
    n = int(SR * dur); t = np.arange(n) / SR
    nz = rng.standard_normal(n).astype(np.float32); nz = _ma(nz, 5) - _ma(nz, 90)
    am = np.clip(np.sin(2 * np.pi * 2.3 * t) * 0.6 + np.sin(2 * np.pi * 5.1 * t + 1.2) * 0.4 + 0.45, 0, 1) ** 1.5
    g = np.clip(np.minimum(t / 0.25, (dur - t) / 0.4), 0, 1)
    return (nz * am * g * 5.5 * vol).astype(np.float32)


def breath(dur=1.4, vol=1.0):
    n = int(SR * dur); t = np.arange(n) / SR
    nz = _ma(rng.standard_normal(n).astype(np.float32), 14) * 7.0
    e = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 2
    return (nz * e * vol).astype(np.float32)


def hit(vol=1.0):
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


def box_run(add, t0, stop, drift0=0.0, gain=0.07):
    fig = [69, 72, 76, 72, 69, 71, 68, 64]; beat = 60.0 / 54; k = 0; tt = t0
    while tt < stop:
        drift = 1 - drift0 - 0.0016 * k
        f = 440.0 * 2 ** ((fig[k % 8] - 69) / 12.0) * drift
        add(sfx.mbox(f, 1.0), tt, gain * (1.3 if k % 8 == 0 else 1.0) * float(np.clip((stop - tt) / 0.5 + 0.2, 0, 1)))
        tt += beat * (0.5 if k % 8 in (1, 2, 4, 5) else 1.0); k += 1


def bed(mix, total, add):
    N = int(SR * total); t = np.arange(N) / SR
    cut = np.clip((C_BLACK - t) / 0.03, 0, 1).astype(np.float32)               # everything dies on the black cut, and stays dead
    ramp = (0.45 + 0.55 * np.clip(t / 33.0, 0, 1)).astype(np.float32)
    drone = np.sin(2 * np.pi * 55.0 * t) + 0.9 * np.sin(2 * np.pi * 55.7 * t) + 0.5 * np.sin(2 * np.pi * 82.4 * t + 0.4 * np.sin(2 * np.pi * 0.1 * t))
    room = _ma(rng.standard_normal(N).astype(np.float32), 260) * 6.0
    # the sleep-talking clip: tape hiss + a low rumble of the room, gated to that screen only
    clip = _gate(t, C_CLIP - 0.02, C_LIVE2 - 0.25, 0.08, 0.3)
    nz = rng.standard_normal(N).astype(np.float32)
    hiss = (nz - _ma(nz, 6)) * 0.06 * clip
    rumble = _lp(nz, 90) * 2.4 * clip
    # the flat-line tone: Sleeper 2 has no pulse
    fl = _gate(t, at("zero") - 0.02, at("pinged") - 0.30, 0.04, 0.2)
    flat = (np.sin(2 * np.pi * 880.0 * t) * 0.5 + np.sin(2 * np.pi * 1760.0 * t) * 0.06) * fl * 0.10
    beds = (drone * 0.05).astype(np.float32) * ramp + room * 0.30 + hiss + rumble * 0.05 + flat.astype(np.float32)
    add((beds * cut).astype(np.float32), 0.0, 1.0)
    box_run(add, C_NIGHT + 0.05, C_CLIP - 0.15, 0.0, 0.07)                      # lullaby from the dark bedroom until the clip
    box_run(add, C_LIVE2 + 0.1, C_ALERT - 0.05, 0.035, 0.06)                    # it comes back, already out of tune


def cues():
    c = [("notif", 0.0), ("notif", 2.0)]
    for t in CUTS[:-2]: c.append(("whoosh", t - 0.06))
    c += [("creak_s", 5.4), ("creak_s", 6.1)]
    # the heart: Sleeper 1 beats (the monitor blip and the thump), silent while the clip plays
    for tb in BEATS:
        if C_CLIP - 0.05 <= tb < C_LIVE2: continue
        if tb < at("78") - 0.1: continue
        c.append(("heart", tb)); c.append(("hmon", tb + 0.01))
    c += [("notif", at("pinged") - 0.05)]
    c += [("tap", C_CLIP + 0.02), ("pop_lo", at("asleep") + 0.40), ("pop_lo", at("still") + 0.30)]
    c += [("riser_s", at("both") - 0.9), ("thud_lo", at("both") - 0.02)]
    c += [("pop_hi", at("daniel") - 0.02), ("thud_lo", at("daniel") - 0.02), ("pop_hi", at("guest") - 0.02), ("thud_lo", at("guest") - 0.02)]
    c += [("alarm", at("new") - 0.06), ("boom", at("new") - 0.02), ("ding", at("notified") - 0.02)]
    c += [("riser", C_BED - 0.6), ("breath", T_PAN + 0.5), ("rustle", T_RISE0 - 0.05), ("breath", 33.2), ("sting", T_PAN + 0.78)]
    c += [("hit", C_BLACK - 0.18), ("boom", C_BLACK - 0.18)]
    c += [("notif", C_END)]
    return c


def main():
    out_dir = os.path.join(HERE, "out"); os.makedirs(out_dir, exist_ok=True)
    sfx.LIB.update({"notif": lambda: notif(), "alarm": lambda: alarm(), "hmon": lambda: hmon(), "rustle": lambda: rustle(T_RISE1 - T_RISE0 + 0.2), "breath": lambda: breath(),
                    "creak_s": lambda: (sfx.creak(0.42, 1.0)).astype(np.float32), "hit": lambda: hit(), "boom": lambda: boom()})
    sfx.GAIN.update({"notif": 0.55, "alarm": 0.5, "hmon": 0.10, "rustle": 0.55, "breath": 0.5, "creak_s": 0.28, "hit": 0.9, "boom": 0.7, "heart": 0.55, "whoosh": 0.14,
                     "tap": 0.4, "pop_lo": 0.3, "pop_hi": 0.3, "thud_lo": 0.8, "riser": 0.42, "riser_s": 0.35, "sting": 0.7, "ding": 0.35})
    sfx.DRY.update({"notif", "alarm", "boom", "sting", "hit"})
    wav = os.path.join(HERE, "narration.wav")
    aac = os.path.join(out_dir, "sleeper-mix.m4a")
    sfx.mix_from_cues(wav, TOTAL, cues(), aac, workdir=out_dir, music_fn=bed, voice_fx=lambda v: (v / (np.max(np.abs(v)) + 1e-9) * 0.95).astype(np.float32))
    tmp = os.path.join(out_dir, "_safe.m4a")                                       # true-peak safety: AAC can overshoot the sample-peak limiter by about 1 dB
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", aac, "-af", "alimiter=limit=0.78:level=false", "-ar", "48000", "-c:a", "aac", "-b:a", "192k", tmp], check=True)
    os.replace(tmp, aac)
    print("wrote", aac, "beats:", len(BEATS))


if __name__ == "__main__":
    main()
