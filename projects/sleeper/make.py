#!/usr/bin/env python3
"""Render sleeper: frames (2 processes) -> mp4 segments -> mux with out/sleeper-mix.m4a.
usage: python3 -I projects/sleeper/make.py [--frames A B] [--out path]   (--frames renders a clip without audio, for checks)
"""
import os, sys, time, subprocess, multiprocessing as mp
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np, skia
from sleep_art import W, H, FPS, post
import scenes
assert os.path.dirname(os.path.abspath(scenes.__file__)) == HERE, scenes.__file__

OUT = os.path.join(HERE, "out"); os.makedirs(OUT, exist_ok=True)


def render_range(args):
    i, f0, f1 = args
    seg = os.path.join(OUT, f"seg{i}.mp4")
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                           "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart", seg], stdin=subprocess.PIPE)
    surf = skia.Surface(W, H); cv = surf.getCanvas()
    t0 = time.time()
    for f in range(f0, f1):
        t = (f + 0.5) / FPS
        cv.clear(skia.ColorBLACK)
        fx = scenes.frame(cv, t)
        ff.stdin.write(post(surf.makeImageSnapshot().toarray(), fx, f).tobytes())
        if (f - f0) % 90 == 0: print(f"seg{i} frame {f} ({time.time() - t0:.0f}s)", flush=True)
    ff.stdin.close(); ff.wait()
    return seg


def main():
    a = sys.argv[1:]
    n = int(round(scenes.TOTAL * FPS)); f0, f1 = 0, n
    if "--frames" in a: k = a.index("--frames"); f0, f1 = int(a[k + 1]), int(a[k + 2])
    out = a[a.index("--out") + 1] if "--out" in a else os.path.join(OUT, "sleeper.mp4")
    T0 = time.time(); nproc = 2
    bounds = [round(f0 + (f1 - f0) * k / nproc) for k in range(nproc + 1)]
    with mp.get_context("fork").Pool(nproc) as p:
        segs = p.map(render_range, [(i, bounds[i], bounds[i + 1]) for i in range(nproc)])
    print(f"rendered {f1 - f0} frames in {time.time() - T0:.0f}s")
    open(os.path.join(OUT, "list.txt"), "w").write("".join(f"file '{s}'\n" for s in segs))
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", os.path.join(OUT, "list.txt")]
    mix = os.path.join(OUT, "sleeper-mix.m4a")
    if "--frames" not in a and os.path.exists(mix):
        cmd += ["-i", mix, "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "copy", "-shortest"]
    else: cmd += ["-c:v", "copy"]
    subprocess.run(cmd + ["-movflags", "+faststart", out], check=True)
    print("wrote", out)


if __name__ == "__main__":
    main()
