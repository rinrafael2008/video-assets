#!/usr/bin/env python3
"""preview: python3 -I projects/sleeper/sheet.py out.png t1 t2 t3 ... (renders those frames at 1080x1920 -> 360x640 tiles)"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import numpy as np, skia
from PIL import Image
from sleep_art import W, H, FPS, post
import scenes
out = sys.argv[1]; times = [float(x) for x in sys.argv[2:]]
surf = skia.Surface(W, H); cv = surf.getCanvas(); tiles = []
for t in times:
    cv.clear(skia.ColorBLACK); fx = scenes.frame(cv, t)
    a = post(surf.makeImageSnapshot().toarray(), fx, int(t * FPS))[..., ::-1]
    tiles.append(Image.fromarray(np.ascontiguousarray(a)).resize((360, 640), Image.LANCZOS))
cols = min(4, len(tiles)); rows = (len(tiles) + cols - 1) // cols
sh = Image.new("RGB", (360 * cols, 640 * rows), "white")
for i, im in enumerate(tiles): sh.paste(im, ((i % cols) * 360, (i // cols) * 640))
sh.save(out); print("ok", out)
