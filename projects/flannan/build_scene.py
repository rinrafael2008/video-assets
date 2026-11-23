#!/usr/bin/env python3
"""Flannan Isles: write scene.json (Picsart scene document, 1080x1920 @30).
Real stock footage (Pexels, server-fetched by Picsart), cut on the spoken words, cold grade, kinetic text beats,
word-timed captions, the original audio mix. usage: python3 -I projects/flannan/build_scene.py [mix_url]
"""
import json, os, sys, re
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from story import WORDS, SHOTS, CLIPS, TOTAL, at

MIX_URL = sys.argv[1] if len(sys.argv) > 1 else \
    "https://raw.githubusercontent.com/rinrafael2008/video-assets/main/projects/flannan/mix.m4a"
FONT_URL = "https://pastatic.picsart.com/63211336242695272495.ttf"   # Poppins Black
FONT = "poppins_black"
W, H, FPS = 1080, 1920, 30
RED, AMBER, WHITE = "#E5383B", "#FFC857", "#FFFFFF"
fr = lambda t: round(round(t * FPS) / FPS, 10)      # snap to the frame grid (exact)

GRADE = {
    "cold": [{"id": "adjust", "params": {"saturation": -0.40, "contrast": 0.18, "temperature": -0.30, "exposure": -0.25, "shadows": -0.1}}],
    "dark": [{"id": "adjust", "params": {"saturation": -0.55, "contrast": 0.28, "temperature": -0.22, "exposure": -0.65, "shadows": -0.15}}],
    "warm": [{"id": "adjust", "params": {"saturation": -0.30, "contrast": 0.22, "temperature": 0.14, "exposure": -0.50, "shadows": -0.1}}],
}

assets = {FONT: {"type": "font", "uri": FONT_URL}, "mix": {"type": "audio", "uri": MIX_URL, "duration": TOTAL}}
for k, (url, dur, _) in CLIPS.items():
    assets[k.lower()] = {"type": "video", "uri": url, "duration": dur}

layers = []

# ---- footage: real camera motion (push / pan / handheld shake) + a punch and RGB glitch on every cut ----
import random
STATIC = {"HALL", "CANDLE", "BOOK", "BOOK2", "PIER", "LH"}      # clips with little motion of their own: move the camera more
for i, (t0, key, tin, grade) in enumerate(SHOTS):
    t1 = SHOTS[i + 1][0] if i + 1 < len(SHOTS) else TOTAL
    t0f, t1f = fr(t0), fr(t1)
    dur = round(t1f - t0f, 10)
    clip_dur = CLIPS[key][1]
    assert tin + dur <= clip_dur + 0.01, (i, key, tin, dur, clip_dur)
    rnd = random.Random(100 + i)
    if key == "HALL":   z0, z1 = 1.06, 1.44                       # walking down the corridor
    elif i % 2 == 0:    z0, z1 = 1.08, 1.34 if key in STATIC else 1.26
    else:               z0, z1 = (1.34 if key in STATIC else 1.26), 1.08
    landscape = CLIPS[key][0].find("1440_2560") < 0 and CLIPS[key][0].find("1080_1920") < 0 and CLIPS[key][0].find("1440_2730") < 0
    ax = 70 if landscape else 18                                  # landscape clips are cropped wide: lots of room to pan sideways
    ay = 16
    sx, sy = rnd.choice((-1, 1)), rnd.choice((-1, 1))
    p0 = (W / 2 - sx * ax, H / 2 - sy * ay); p1 = (W / 2 + sx * ax, H / 2 + sy * ay)
    pos, t = [], 0.0
    while t < dur - 1e-6:                                         # drift line + handheld shake every 0.1 s
        u = t / dur
        pos.append({"time": round(t, 3), "value": [round(p0[0] + (p1[0] - p0[0]) * u + rnd.uniform(-5, 5), 1),
                                                     round(p0[1] + (p1[1] - p0[1]) * u + rnd.uniform(-5, 5), 1)], "easing": "linear"})
        t += 0.1
    pos.append({"time": dur, "value": [round(p1[0], 1), round(p1[1], 1)]})
    layers.append({
        "id": f"shot{i:02d}", "start": t0f, "duration": dur, "timeMode": "layer",
        "content": {"kind": "media", "assetId": key.lower(), "fit": "cover", "muted": True,
                    "trim": {"in": tin, "out": round(tin + dur, 10)}},
        "animations": {
            "scale": {"keyframes": [{"time": 0, "value": [round(z0 * 1.12, 3)] * 2, "easing": "ease_out"},
                                     {"time": 0.18, "value": [z0, z0], "easing": "linear"},
                                     {"time": dur, "value": [z1, z1]}]},
            "position": {"keyframes": pos}},
        "effects": GRADE[grade] + [{"id": "channel_shift", "params": {
            "horizontal": {"keyframes": [{"time": 0, "value": 26, "easing": "ease_out"}, {"time": 0.22, "value": 0}]},
            "vertical": 0}}],
    })

# ---- global finish: grain + vignette on everything under the text ------------
layers.append({"id": "finish", "start": 0, "duration": TOTAL, "adjustmentLayer": True,
               "content": {"kind": "color", "color": "#00000000"},
               "effects": [{"id": "vignette", "params": {"fade": 25, "size": 75}},
                           {"id": "film_grain", "params": {"intensity": 0.16, "size": 2, "color": 0.3}}]})

# ---- bottom shade for the caption band ---------------------------------------
layers.append({"id": "shade", "start": 0, "duration": TOTAL,
               "transform": {"position": [W / 2, 1470]},
               "content": {"kind": "shape", "items": [
                   {"type": "rect", "size": [W, 900], "position": [0, 0]},
                   {"type": "gradientFill", "startPoint": [0, -450], "endPoint": [0, 450],
                    "colorStops": [{"offset": 0, "color": "#000000"}, {"offset": 1, "color": "#000000"}],
                    "alphaStops": [{"offset": 0, "alpha": 0.0}, {"offset": 1, "alpha": 0.78}]}]}})

# ---- impact flashes ----------------------------------------------------------
for name, t in (("flash_fake", at("Fake.")), ("flash_fiction", at("Fiction.")), ("flash_never", at("never"))):
    layers.append({"id": name, "start": fr(t), "duration": 0.3, "timeMode": "layer",
                   "content": {"kind": "color", "color": "#FFFFFF"},
                   "animations": {"opacity": {"keyframes": [{"time": 0, "value": 0.75, "easing": "ease_out"}, {"time": 0.28, "value": 0}]}}})

# ---- text beats ----------------------------------------------------------------
cut = lambda i: SHOTS[i][0]
BEATS = [
    # start, end, text, max size, colour, y (px from top), slam
    (0.0, cut(1), "SCOTLAND\n1900", 190, WHITE, 760, False),
    (cut(1), cut(3), "3 KEEPERS\nVANISHED", 170, WHITE, 760, False),
    (cut(3), at("Fake.", off=-0.12), "THE STORY\nYOU KNOW?", 150, WHITE, 760, False),
    (at("Fake.", off=-0.12), cut(5), "FAKE.", 340, RED, 760, True),
    (cut(5), cut(6), "11 DAYS\nLATER", 190, WHITE, 760, False),
    (cut(6), cut(7), "NOBODY ON\nTHE DOCK", 150, WHITE, 760, False),
    (cut(7), cut(8), "DOOR\nSHUT", 230, WHITE, 760, False),
    (cut(8), cut(9), "BEDS\nUNMADE", 220, WHITE, 760, False),
    (cut(9), cut(10), "2 RAINCOATS\nGONE", 150, WHITE, 760, False),
    (cut(10), cut(11), "1 STILL ON\nITS PEG", 150, WHITE, 760, False),
    (cut(11), cut(12), "NO HALF-EATEN\nDINNER", 130, WHITE, 760, False),
    (cut(12), cut(13), "NO OVERTURNED\nCHAIR", 130, WHITE, 760, False),
    (cut(13), cut(14), "FROM A\nPOEM", 220, WHITE, 760, False),
    (cut(14), cut(15), "1912", 340, AMBER, 760, True),
    (cut(15), cut(17), "THE LOGBOOK\nENTRIES", 150, WHITE, 760, False),
    (cut(17), cut(18), "FIRST IN PRINT\n1965", 150, AMBER, 760, False),
    (cut(18), cut(19), "FICTION.", 270, RED, 760, True),
    (cut(19), cut(20), "THE ROCKS\nDON'T LIE", 160, WHITE, 760, False),
    (cut(20), cut(21), "OVER 1 TON\nMOVED", 160, WHITE, 760, False),
    (cut(21), cut(22), "100+ FT UP\nTHE CLIFF", 160, WHITE, 760, False),
    (cut(22), cut(24), "A FREAK\nWAVE?", 200, WHITE, 760, False),
    (cut(24), cut(25), "NEVER\nFOUND.", 250, RED, 760, True),
    (cut(25), at("men", off=-0.08), "THE LEGEND\nIS FICTION.", 150, WHITE, 760, False),
]
SHADOW = [{"id": "drop_shadow", "params": {"offset": [0, 8], "blur": 18, "color": "#000000cc"}}]
for j, (s, e, text, size, color, y, slam) in enumerate(BEATS):
    s, e = fr(s), fr(e)
    dur = round(e - s, 10)
    lines = text.split("\n")
    widest = max(len(l) for l in lines)
    fs = int(min(size, 960 / (widest * 0.80)))
    lh = round(fs * 1.04)
    rnd = random.Random(500 + j)
    for k, line in enumerate(lines):
        d = round(0.07 * k, 3)                                    # stagger the lines
        ks = fr(s + d); kd = round(e - ks, 10)                    # this line's own start / duration, on the frame grid
        cy = y + (k - (len(lines) - 1) / 2) * lh
        pos = [{"time": 0, "value": [W / 2, cy + 46], "easing": "ease_out"}]
        if slam:                                                  # impact shake, decaying over 0.5 s
            tt = 0.14
            while tt < 0.55:
                amp = 16 * (1 - (tt - 0.14) / 0.41)
                pos.append({"time": round(tt, 2), "value": [round(W / 2 + rnd.uniform(-amp, amp), 1), round(cy + rnd.uniform(-amp, amp), 1)], "easing": "linear"})
                tt += 0.04
            pos.append({"time": 0.55, "value": [W / 2, cy]})
        else:
            pos.append({"time": 0.2, "value": [W / 2, cy]})
        pos.append({"time": max(kd, 0.7), "value": [W / 2, cy - 26]})          # then keep floating up
        kf_scale = ([{"time": 0, "value": [2.0, 2.0], "easing": "ease_out"}, {"time": 0.12, "value": [0.94, 0.94], "easing": "ease_out"}, {"time": 0.22, "value": [1, 1], "easing": "linear"}]
                    if slam else
                    [{"time": 0, "value": [1.4, 1.4], "easing": "ease_out"}, {"time": 0.16, "value": [1, 1], "easing": "linear"}])
        kf_scale.append({"time": max(kd, 0.7), "value": [1.07, 1.07]})
        layers.append({
            "id": f"beat{j:02d}_{k}", "start": ks, "duration": kd, "timeMode": "layer",
            "content": {"kind": "text", "text": line, "font": {"family": FONT, "size": fs}, "color": color,
                        "alignment": "center", "wrapWidth": 1040, "letterSpacing": 1,
                        "stroke": {"width": max(8, fs // 12), "color": "#000000", "order": "stroke-over-fill"}},
            "animations": {"scale": {"keyframes": kf_scale}, "position": {"keyframes": pos},
                           "opacity": {"keyframes": [{"time": 0, "value": 1 if (j == 0 and k == 0) else 0}, {"time": 0.06, "value": 1}]}},
            "effects": SHADOW,
        })

# last beat: the men are still GONE.
s = fr(at("men", off=-0.08)); dur = round(fr(TOTAL) - s, 10)
layers.append({"id": "beat_men", "start": s, "duration": dur, "timeMode": "layer",
               "transform": {"position": [W / 2, 560]},
               "content": {"kind": "text", "text": "THE MEN ARE", "font": {"family": FONT, "size": 110}, "color": WHITE,
                           "alignment": "center", "wrapWidth": 980,
                           "stroke": {"width": 9, "color": "#000000", "order": "stroke-over-fill"}},
               "animations": {"opacity": {"keyframes": [{"time": 0, "value": 0}, {"time": 0.08, "value": 1}]}},
               "effects": [{"id": "drop_shadow", "params": {"offset": [0, 8], "blur": 18, "color": "#000000cc"}}]})
layers.append({"id": "beat_gone", "start": s, "duration": dur, "timeMode": "layer",
               "transform": {"position": [W / 2, 860]},
               "content": {"kind": "text", "text": "STILL\nGONE.", "font": {"family": FONT, "size": 210}, "color": RED, "lineHeight": 214,
                           "alignment": "center", "wrapWidth": 1000,
                           "stroke": {"width": 14, "color": "#000000", "order": "stroke-over-fill"}},
               "animations": {"scale": {"keyframes": [{"time": 0, "value": [1.5, 1.5], "easing": "ease_out"}, {"time": 0.25, "value": [1, 1]}]},
                              "opacity": {"keyframes": [{"time": 0, "value": 0}, {"time": 0.08, "value": 1}]}},
               "effects": [{"id": "drop_shadow", "params": {"offset": [0, 8], "blur": 18, "color": "#000000cc"}}]})

# small location tag (top safe band)
layers.append({"id": "tag", "start": 0.0, "duration": fr(cut(3)), "timeMode": "layer",
               "transform": {"position": [W / 2, 400]},
               "content": {"kind": "text", "text": "FLANNAN ISLES · OUTER HEBRIDES", "font": {"family": FONT, "size": 42}, "color": AMBER,
                           "alignment": "center", "wrapWidth": 1000, "letterSpacing": 5,
                           "stroke": {"width": 4, "color": "#000000", "order": "stroke-over-fill"}},
               "animations": {"opacity": {"keyframes": [{"time": 0, "value": 1}, {"time": 0.3, "value": 1}]}}})

# ---- captions (word-timed) -----------------------------------------------------
words = []
for text, s, e in WORDS:
    parts = text.split()
    if len(parts) == 1:
        words.append((text, s, e))
    else:
        step = (e - s) / len(parts)
        for k, p in enumerate(parts):
            words.append((p, s + k * step, s + (k + 1) * step))

chunks, cur = [], []
for w in words:
    tentative = " ".join(x[0] for x in cur + [w])
    if cur and (len(tentative) > 17 or re.search(r"[.?!,]$", cur[-1][0])):
        chunks.append(cur); cur = []
    cur.append(w)
if cur: chunks.append(cur)

segments = []
for i, ch in enumerate(chunks):
    s = ch[0][1]
    last_end = ch[-1][2]
    nxt = chunks[i + 1][0][1] if i + 1 < len(chunks) else TOTAL
    e = max(last_end, min(nxt - 0.01, last_end + 0.35))
    segments.append({"start": round(s, 3), "end": round(e, 3), "text": " ".join(x[0] for x in ch),
                     "words": [{"text": x[0], "start": round(x[1], 3), "end": round(x[2], 3)} for x in ch]})

DUP = {"fake.", "fiction.", "never found."}   # a giant beat already says it
segments = [g for g in segments if g["text"].lower() not in DUP or g["start"] > 50]
for i in range(len(segments) - 1):          # alignment can overlap a word with the next chunk: clamp
    nxt = segments[i + 1]["start"]
    if segments[i]["end"] > nxt:
        segments[i]["end"] = nxt
        for w in segments[i]["words"]:
            w["end"] = min(w["end"], nxt)
            w["start"] = min(w["start"], round(nxt - 0.001, 3))

layers.append({"id": "captions", "start": 0, "duration": TOTAL,
               "content": {"kind": "captions",
                           "style": {"font": {"family": FONT, "size": 72}, "color": WHITE, "alignment": "center",
                                     "wrapWidth": 1000, "offset": [0, 470], "textCase": "upper", "animationPivot": "word",
                                     "animation": [
                                         {"transform": {"kind": "scale", "value": {"keyframes": [{"t": 0, "v": 0.7, "easing": "ease_out"}, {"t": 0.13, "v": 1.08, "easing": "ease_out"}, {"t": 0.22, "v": 1}]}},
                                          "selector": {"basedOn": "word", "start": 0, "end": 1, "shape": "square"}},
                                         {"transform": {"kind": "opacity", "value": {"keyframes": [{"t": 0, "v": 0}, {"t": 0.06, "v": 1}]}},
                                          "selector": {"basedOn": "word", "start": 0, "end": 1, "shape": "square"}}],
                                     "effects": [{"id": "stroke", "params": {"width": 9, "color": "#000000ff"}}],
                                     "decorations": [{"target": "highlighted", "place": "text", "color": AMBER, "window": "active"}]},
                           "transcript": {"segments": segments}}})

# ---- audio ---------------------------------------------------------------------
layers.append({"id": "mix", "start": 0, "content": {"kind": "audio", "assetId": "mix", "trim": {"in": 0, "out": TOTAL}}})

scene = {"version": "1.0",
         "composition": {"width": W, "height": H, "fps": FPS, "duration": TOTAL, "background": "#000000"},
         "assets": assets, "layers": layers}
out = os.path.join(HERE, "scene.json")
json.dump(scene, open(out, "w"), indent=1)
print("wrote", out, len(layers), "layers", len(segments), "caption segments", round(os.path.getsize(out) / 1024), "KB")
