"""NIGHT LIGHT: animated horror short. Custom project (frame, TOTAL, CUES, MUSIC, VOICE_FX), all drawn in code.

Shots: A exterior push-in -> B me at my window waving -> C it creeps closer -> D it points -> pan to my bedroom
       -> F the open door -> G its window is empty -> H the hallway light turns on.
"""
import math, random
import numpy as np
import skia
import eng, kit, sfx
from eng import (W, H, paint, C, rgb, mix_hex, cl, lerp, prog, e_out, e_io, e_back, line, circ, oval, poly, ik2, pulse, decay, build_chunks)
from kit import STATE, _norm

TOTAL = STATE["total"]
FULL = skia.Rect(0, 0, W, H)
INK = "#020307"
FRAME = "#1b140f"
MOON = "#cfd8ff"
WARM = "#ffb347"
RED = "#e0262b"
ANTON = skia.Typeface.MakeFromFile("/usr/share/fonts/truetype/google-fonts/ofl/anton/Anton-Regular.ttf")
_af = {}


def afont(sz):
    sz = int(round(sz))
    if sz not in _af:
        f = skia.Font(ANTON, sz); f.setSubpixel(True); _af[sz] = f
    return _af[sz]


def N(tok, approx, end=False):
    """time of the occurrence of word `tok` closest to `approx` seconds"""
    best = None
    for w in STATE["words"]:
        if _norm(w[0]) == _norm(tok) and (best is None or abs(w[1] - approx) < abs(best[1] - approx)): best = w
    if best is None: raise KeyError(tok)
    return best[2] if end else best[1]


# ------------------------------------------------------------------ story clock (all anchored to the spoken words)
T_EMPTY = N("empty", 2.4)
T_3AM = N("3 AM,", 5.6)
LAMP_ON = N("light", 6.85)
T_TALL = N("tall", 9.7)
T_THERE = N("there.", 10.9)
T_WAVES = N("waves.", 11.7)
CUT_B = N("first,", 13.3) - 0.14
T_WAVED = N("waved", 13.9)
T_POLITE = N("polite.", 15.6)
CUT_C = N("Then", 16.9) - 0.06
T_CLOSER1 = N("closer", 18.4)
T_EVERY = N("Every", 20.2)
T_CLOSER2 = N("closer.", 21.4)
CUT_D = N("Last", 22.8) - 0.03
T_STOPPED = N("stopped", 23.5)
T_LIFTED = N("lifted", 25.0)
T_POINTED = N("pointed.", 26.5)
T_NOT = N("Not", 27.4)
T_BEHIND = N("Behind", 28.5)
PAN0 = N("turned", 30.2) - 0.08
PAN1 = N("My", 32.0)
T_OPEN = N("open.", 33.2)
T_CLOSEIT = N("always", 34.0)
CUT_G = N("Then", 35.9) - 0.04
LAMP_OFF = N("out.", 37.67)
CUT_H = N("And", 38.4) - 0.06
T_HALL = N("hallway...", 39.3)
T_TURNED = N("turned", 40.2)
T_ON = N("on.", 40.48)
T_END = T_ON + 0.62


def keyed(keys, T):
    """keys: [(t, v)] -> eased interpolation (smoothstep between keys)"""
    if T <= keys[0][0]: return keys[0][1]
    for (t0, v0), (t1, v1) in zip(keys, keys[1:]):
        if T < t1: return lerp(v0, v1, e_io(prog(T, t0, t1)))
    return keys[-1][1]


def keyedN(keys, T):
    """vector version"""
    if T <= keys[0][0]: return keys[0][1:]
    for a, b in zip(keys, keys[1:]):
        if T < b[0]:
            k = e_io(prog(T, a[0], b[0])); return tuple(lerp(x, y, k) for x, y in zip(a[1:], b[1:]))
    return keys[-1][1:]


def hsh(i, seed=0):
    x = math.sin(i * 12.9898 + seed * 78.233) * 43758.5453
    return x - math.floor(x)


def lamp(T):
    """attic lamp level 0..1: flickers on at LAMP_ON, flickers out at LAMP_OFF"""
    if T < LAMP_ON or T >= LAMP_OFF: return 0.0
    dt = T - LAMP_ON
    if dt < 0.75: return 1.0 if hsh(int(dt * 28), 3) > 0.42 else 0.12
    if LAMP_OFF - T < 0.32: return 1.0 if hsh(int(T * 30), 9) > 0.5 else 0.1
    return 0.93 + 0.07 * math.sin(T * 17.0) * math.sin(T * 3.3)


# ------------------------------------------------------------------ drawing helpers
def radial(cx, cy, r, col, a0, a1=0.0, mid=None):
    R, G, B = rgb(col)
    cols = [skia.ColorSetARGB(int(255 * cl(a0)), R, G, B)]; pos = [0.0]
    if mid: cols.append(skia.ColorSetARGB(int(255 * cl(mid[1])), R, G, B)); pos.append(mid[0])
    cols.append(skia.ColorSetARGB(int(255 * cl(a1)), R, G, B)); pos.append(1.0)
    return skia.GradientShader.MakeRadial((cx, cy), r, cols, pos)


def glow(c, cx, cy, r, col, a, add=True, sy=1.0, mid=None):
    if a <= 0.003: return
    p = skia.Paint(); p.setAntiAlias(True); p.setShader(radial(0, 0, r, col, a, 0.0, mid))
    if add: p.setBlendMode(skia.BlendMode.kPlus)
    c.save(); c.translate(cx, cy); c.scale(1.0, sy); c.drawCircle(0, 0, r, p); c.restore()


def vgrad(c, x0, y0, x1, y1, top, bot, a0=1.0, a1=1.0):
    R0, G0, B0 = rgb(top); R1, G1, B1 = rgb(bot)
    p = skia.Paint()
    p.setShader(skia.GradientShader.MakeLinear([(0, y0), (0, y1)], [skia.ColorSetARGB(int(255 * a0), R0, G0, B0), skia.ColorSetARGB(int(255 * a1), R1, G1, B1)], [0, 1]))
    c.drawRect(skia.Rect(x0, y0, x1, y1), p)


def lgrad_poly(c, pts, p0, p1, col0, col1, a0, a1, add=False):
    R0, G0, B0 = rgb(col0); R1, G1, B1 = rgb(col1)
    p = skia.Paint(); p.setAntiAlias(True)
    p.setShader(skia.GradientShader.MakeLinear([p0, p1], [skia.ColorSetARGB(int(255 * cl(a0)), R0, G0, B0), skia.ColorSetARGB(int(255 * cl(a1)), R1, G1, B1)], [0, 1]))
    if add: p.setBlendMode(skia.BlendMode.kPlus)
    path = skia.Path(); path.moveTo(*pts[0])
    for q in pts[1:]: path.lineTo(*q)
    path.close(); c.drawPath(path, p)


def rect(c, x0, y0, x1, y1, col, a=1.0):
    c.drawRect(skia.Rect(x0, y0, x1, y1), paint(col, a))


def spaced(c, s, cx, y, font, pa, track=0.0):
    ws = [font.measureText(ch) for ch in s]; tot = sum(ws) + track * (len(s) - 1); x = cx - tot / 2
    for ch, w in zip(s, ws):
        c.drawString(ch, x, y, font, pa); x += w + track


def sway(T, a=1.0, f=1.0, ph=0.0):
    return a * (math.sin(T * f + ph) + 0.5 * math.sin(T * f * 2.3 + ph * 1.7)) / 1.5


# ------------------------------------------------------------------ the night world (street + haunted house)
_stars_rng = random.Random(11)
_STARS = [(_stars_rng.random() * 1500 - 210, _stars_rng.random() * 1050 - 160, 1.2 + _stars_rng.random() * 2.2, _stars_rng.random() * 6.3) for _ in range(90)]


def branch(c, x, y, a, L, w, d, T, seed):
    if d <= 0 or L < 7: return
    a2 = a + 0.035 * math.sin(T * 0.8 + d * 0.9 + seed * 0.3)
    x2, y2 = x + L * math.cos(a2), y + L * math.sin(a2)
    line(c, x, y, x2, y2, w, INK)
    r = random.Random(seed * 7919 + d)
    n = 2 if r.random() < 0.8 else 3
    for k in range(n):
        da = (k - (n - 1) / 2.0) * (0.55 + 0.35 * r.random()) + (r.random() - 0.5) * 0.25
        branch(c, x2, y2, a2 + da, L * (0.66 + 0.14 * r.random()), w * 0.66, d - 1, T, seed * 3 + k + 1)


def house(c, T, L):
    rim = "#4a5a9a"
    # tower (left)
    poly(c, [(120, 1262), (120, 640), (275, 640), (275, 1262)], fill="#06070e", line_c=None)
    poly(c, [(96, 650), (198, 380), (300, 650)], fill=INK, line_c=None)
    line(c, 198, 380, 300, 650, 4, rim, 0.45); line(c, 198, 380, 198, 330, 5, INK)
    # main body + roof
    poly(c, [(255, 1262), (255, 735), (825, 735), (825, 1262)], fill="#07080f", line_c=None)
    poly(c, [(215, 742), (540, 420), (865, 742), (825, 742), (540, 468), (255, 742)], fill=INK, line_c=None)
    poly(c, [(255, 742), (540, 468), (825, 742)], fill="#080a14", line_c=None)           # gable face
    line(c, 540, 420, 865, 742, 5, rim, 0.55); line(c, 825, 735, 825, 1262, 4, rim, 0.35)
    poly(c, [(690, 560), (690, 440), (748, 440), (748, 612)], fill=INK, line_c=None)       # chimney
    line(c, 748, 440, 748, 612, 3, rim, 0.4)
    # siding
    for yy in range(760, 1262, 17): line(c, 256, yy, 824, yy, 1.6, "#1a2244", 0.5)
    for yy in range(660, 1262, 17): line(c, 121, yy, 274, yy, 1.4, "#1a2244", 0.4)
    # windows (dead)
    for (wx, wy, ww, wh) in ((330, 800, 92, 140), (630, 800, 92, 140), (330, 1010, 92, 130), (650, 1010, 92, 130), (170, 760, 62, 100), (170, 930, 62, 100)):
        rect(c, wx - ww / 2, wy - wh / 2, wx + ww / 2, wy + wh / 2, "#02030a")
        c.drawRect(skia.Rect(wx - ww / 2, wy - wh / 2, wx + ww / 2, wy + wh / 2), paint("#2b3768", 0.85, 4))
        line(c, wx, wy - wh / 2, wx, wy + wh / 2, 3, "#2b3768", 0.8); line(c, wx - ww / 2, wy, wx + ww / 2, wy, 3, "#2b3768", 0.8)
    for (wx, wy) in ((330, 1010), (170, 930)):                                             # boarded windows
        line(c, wx - 52, wy - 30, wx + 52, wy + 24, 11, "#14100d"); line(c, wx - 52, wy + 20, wx + 52, wy - 34, 11, "#120e0b")
    poly(c, [(262, 770), (292, 770), (286, 905), (258, 900)], fill="#05060c", line_c=None)  # crooked shutter
    poly(c, [(738, 770), (706, 773), (712, 900)], fill="#05060c", line_c=None)
    # door + porch
    rect(c, 490, 1070, 590, 1262, "#03040a"); c.drawRect(skia.Rect(490, 1070, 590, 1262), paint("#2b3768", 0.8, 4))
    rect(c, 455, 1236, 625, 1262, "#0a0b14"); rect(c, 440, 1252, 640, 1275, "#0d0e18")
    poly(c, [(440, 1070), (540, 1000), (640, 1070)], fill=INK, line_c=None)
    # attic window
    attic(c, T, L)


GW, GH = 62, 92


def attic(c, T, L):
    c.save(); c.translate(540, 640)
    rect(c, -73, -103, 73, 103, FRAME)
    c.drawRect(skia.Rect(-73, -103, 73, 103), paint("#3b2c22", 0.9, 3))
    rect(c, -GW, -GH, GW, GH, "#04060d")
    c.save(); c.clipRect(skia.Rect(-GW, -GH, GW, GH), skia.ClipOp.kIntersect, True)
    if L > 0.01:
        vgrad(c, -GW, -GH, GW, GH, "#ffe3a0", "#e98f2a", L, L)
        glow(c, 0, -30, 100, "#fff4cf", 0.55 * L)
        fp = fig_pose(T)
        for sgn in (-1, 1):                                                                 # tattered curtains
            p = skia.Path(); p.moveTo(sgn * GW, -GH)
            for j in range(9):
                yy = -GH + j * (2 * GH / 8); p.lineTo(sgn * (GW - (13 + 8 * j / 8.0 + 3.0 * math.sin(yy * 0.07 + T * 1.1 + sgn))), yy)
            p.lineTo(sgn * GW, GH); p.close(); c.drawPath(p, paint("#190707", 0.95))
        if fp is not None: figure(c, T, **fp)
        vp = skia.Paint(); vp.setShader(radial(0, 0, 118, "#2a1200", 0.0, 0.6 * L, mid=(0.5, 0.0))); c.drawRect(skia.Rect(-GW, -GH, GW, GH), vp)   # dirty-glass vignette
        for k in range(7):
            x0 = -60 + k * 21 + 8 * math.sin(k * 2.1); line(c, x0, -GH, x0 + 40, GH, 1.6, "#ffffff", 0.045)
    else:
        lgrad_poly(c, [(-GW, -GH), (-10, -GH), (GW, 30), (GW, GH), (10, GH), (-GW, -30)], (-GW, -GH), (GW, GH), "#6f86d6", "#0a1030", 0.16, 0.02)
    c.restore()
    fq = fig_pose(T) if L > 0.01 else None
    if fq is not None and fq["out"]:                                                       # the long arm reaches out past the frame
        c.save(); c.translate(fq["dx"], fq["dy"]); c.scale(fq["s"] * 0.95, fq["s"] * 1.1); arm_draw(c, fq["arm"], 112, 124); c.restore()
    rect(c, -2.5, -GH, 2.5, GH, FRAME); rect(c, -GW, -13, GW, -6, FRAME)                    # mullions
    for (x0, y0, x1, y1) in ((-44, 66, -26, 50), (-44, 66, -52, 40), (-44, 66, -34, 84), (-44, 66, -22, 72), (-44, 66, -54, 82)):
        line(c, x0, y0, x1, y1, 1.2, "#ffffff", 0.35)                                       # cracked pane
    rect(c, -82, 103, 82, 118, "#241a14"); line(c, -82, 103, 82, 103, 2, "#5568a8", 0.5)
    c.restore()


def fig_pose(T):
    if T < T_TALL or T >= PAN1: return None
    rise = 1 - e_out(prog(T, T_TALL, T_THERE))
    steps = [(0, 0.80), (CUT_C, 0.80), (T_CLOSER1 - 0.3, 0.96), (T_EVERY, 1.14), (T_CLOSER2, 1.38)]
    s = steps[0][1]
    for i in range(1, len(steps)):
        if T >= steps[i][0]: s = lerp(steps[i - 1][1], steps[i][1], e_out(prog(T, steps[i][0], steps[i][0] + 0.18)))
    s += 0.012 * max(0.0, T - CUT_C)
    if T >= CUT_D: s = max(s, 1.40) + 0.004 * (T - CUT_D)
    # arm keys: (t, hx, hy, angle_deg, spread)
    wv = (T_WAVES - 0.1, 0.0)
    keys = [(0, 52, 150, 90, 0.0), (T_WAVES - 0.15, 52, 150, 90, 0.0), (T_WAVES + 0.55, 40, -84, -90, 1.0), (T_STOPPED - 0.1, 40, -84, -90, 1.0),
            (T_STOPPED + 0.9, 52, 150, 90, 0.0), (T_LIFTED - 0.1, 52, 150, 90, 0.0), (T_POINTED - 0.1, 42, -60, 130, 0.0),
            (T_BEHIND - 0.4, 42, -60, 130, 0.0), (T_BEHIND + 0.4, 42, -60, -38, 0.0), (999, 42, -60, -38, 0.0)]
    hx, hy, ang, spread = keyedN(keys, T)
    out = False
    if T_WAVES + 0.4 < T < T_STOPPED:
        amp = min(1.0, (T - T_WAVES - 0.4) / 0.5) * min(1.0, (T_STOPPED - T) / 0.4)
        hx += 15 * amp * math.sin(2 * math.pi * 1.7 * (T - T_WAVES)); ang += 12 * amp * math.sin(2 * math.pi * 1.7 * (T - T_WAVES) + 1.0)
    if T_NOT < T < T_NOT + 0.5: hx += 4 * math.sin((T - T_NOT) * 60) * (1 - (T - T_NOT) / 0.5)          # finger twitch
    eyes = prog(T, T_CLOSER1, T_CLOSER1 + 0.6) * (0.8 + 0.2 * math.sin(T * 5.0))
    return dict(s=s, dy=300 * rise, tilt=0.10 + 0.07 * math.sin(T * 0.7) + (0.12 if T > T_POINTED else 0), arm=(hx, hy, ang, spread), eyes=eyes, dx=sway(T, 2.5, 0.8), out=out)


def figure(c, T, s=1.0, dy=0.0, tilt=0.0, arm=(52, 150, 90, 0.0), eyes=0.0, dx=0.0, out=False):
    """the tall shadow: long neck, coat-hanger shoulders, thin long arms. origin = middle of the window."""
    c.save(); c.translate(dx, dy); c.scale(s * 0.95, s * 1.1)
    body = skia.Path(); body.moveTo(-9, 28); body.lineTo(-54, 44); body.quadTo(-50, 120, -44, 200); body.lineTo(-40, 300); body.lineTo(-46, 400); body.lineTo(46, 400); body.lineTo(40, 300); body.quadTo(50, 120, 54, 44); body.lineTo(9, 28); body.close()
    c.drawPath(body, paint(INK))
    line(c, -50, 46, -66, 128, 10, INK); line(c, -66, 128, -58, 210, 9.5, INK)
    line(c, 0, -16, 0, 30, 10, INK)
    if not out: arm_draw(c, arm, 92, 102)
    c.save(); c.translate(0, -14); c.rotate(math.degrees(tilt))
    oval(c, 0, -33, 20.5, 33, fill=INK, line=None)
    if eyes > 0.02:
        for sgn in (-1, 1):
            glow(c, sgn * 9, -38, 15, "#ffffff", 0.34 * eyes)
            c.save(); c.translate(sgn * 9, -38); c.rotate(-sgn * 9); oval(c, 0, 0, 6.4, 2.5, fill="#ffffff", alpha=cl(eyes)); c.restore()
    c.restore()
    c.restore()


def arm_draw(c, arm, l1, l2):
    hx, hy, ang, spread = arm
    k, hnd = ik2(50, 46, hx, hy, l1, l2, -1)
    pth = skia.Path(); pth.moveTo(50, 46); pth.lineTo(*k); pth.lineTo(*hnd)
    c.drawPath(pth, paint("#2e3046", 1.0, 14.5)); c.drawPath(pth, paint(INK, 1.0, 10))      # faint rim so the arm reads against the body
    hand(c, hnd[0], hnd[1], ang, spread)


def hand(c, x, y, ang_deg, spread):
    a = math.radians(ang_deg)
    for col, g in (("#2e3046", 3.0), (INK, 0.0)):
        oval(c, x, y, 13 + g / 2, 15 + g / 2, fill=col, line=None)
        if spread > 0.5:
            for da, ln in ((-0.66, 38), (-0.24, 52), (0.16, 50), (0.56, 38)):
                line(c, x, y, x + math.cos(a + da * spread) * (ln + 12), y + math.sin(a + da * spread) * (ln + 12), 4.4 + g, col)
        else:
            line(c, x, y, x + math.cos(a) * 74, y + math.sin(a) * 74, 7.5 + g, col)               # one long pointing finger
            for da in (-1.0, 1.0): circ(c, x + math.cos(a + da) * 9, y + math.sin(a + da) * 9, 6 + g / 2, fill=col, line=None)


def world(c, T, zoom, cx, cy, L=None):
    L = lamp(T) if L is None else L
    c.save(); c.translate(W / 2, H / 2); c.scale(zoom, zoom); c.translate(-cx, -cy)
    vgrad(c, -900, -900, 2000, 700, "#02030a", "#0d1634"); vgrad(c, -900, 700, 2000, 1262, "#0d1634", "#27386d")
    for (x, y, r, ph) in _STARS: c.drawCircle(x, y, r, paint("#ffffff", 0.35 + 0.45 * (0.5 + 0.5 * math.sin(T * 1.6 + ph))))
    glow(c, 860, 300, 420, "#7088e0", 0.30); circ(c, 860, 300, 72, fill=MOON, line=None)
    for (dx_, dy_, rr) in ((-22, -14, 16), (20, 12, 12), (-6, 26, 10), (26, -26, 8)): circ(c, 860 + dx_, 300 + dy_, rr, fill="#aab6e6", line=None, alpha=0.5)
    for i in range(4):                                                                       # clouds drifting over the moon
        xx = (T * (9 + 3 * i) + i * 430) % 1900 - 380; yy = 250 + i * 70 + 12 * math.sin(T * 0.2 + i)
        for k in range(4): oval(c, xx + k * 95, yy + (k % 2) * 14, 150 - k * 14, 30 + k % 2 * 8, fill="#0a1030", line=None, alpha=0.42)
    # far hills + trees
    poly(c, [(-900, 1262), (-900, 1150), (-200, 1120), (60, 1170), (400, 1130), (1000, 1160), (1500, 1110), (2000, 1160), (2000, 1262)], fill="#05060e", line_c=None)
    house(c, T, L)
    glow(c, 540, 640, 460, WARM, 0.34 * L); glow(c, 540, 640, 150, "#ffd98a", 0.3 * L)
    # fence
    rect(c, 60, 1292, 1020, 1300, "#04050b")
    for i in range(34):
        x = 70 + i * 28.5; hgt = 62 - (24 if i in (5, 11, 12, 19, 26) else 0) + 4 * hsh(i)
        poly(c, [(x - 8, 1330), (x - 8, 1268 + (62 - hgt)), (x, 1256 + (62 - hgt)), (x + 8, 1268 + (62 - hgt)), (x + 8, 1330)], fill="#04050b", line_c=None)
    # street
    vgrad(c, -900, 1330, 2000, 2300, "#0b1020", "#020308")
    glow(c, 540, 1450, 700, "#4a5a9a", 0.12, add=False, sy=0.3)
    if L > 0.02:
        lgrad_poly(c, [(500, 1335), (580, 1335), (700, 2200), (380, 2200)], (0, 1335), (0, 1900), WARM, WARM, 0.22 * L, 0.0, add=True)
    # near tree (left) + mailbox
    branch(c, 100, 1330, -math.pi / 2 - 0.05, 300, 38, 7, T, 4)
    branch(c, 100, 760, -math.pi / 2 + 0.55, 190, 16, 5, T, 8); branch(c, 112, 900, -math.pi / 2 + 0.9, 170, 14, 4, T, 2)
    poly(c, [(930, 1330), (936, 1180), (952, 1180), (958, 1330)], fill=INK, line_c=None); rect(c, 905, 1150, 985, 1190, INK)
    # fog banks (world space)
    for i in range(7):
        x = (i * 300 + T * (14 + i * 3) + i * 91) % 2300 - 600; yy = 1290 + 40 * math.sin(T * 0.3 + i) + (i % 3) * 42
        glow(c, x, yy, 430, "#8fa0d0", 0.17, add=False, sy=0.26)
    glow(c, 540, 1230, 900, "#6f80b8", 0.14, add=False, sy=0.22)
    c.restore()


def mist(c, T, a=0.10):
    """screen-space drifting mist, keeps close-ups alive"""
    for i in range(5):
        x = (i * 330 - T * (22 + i * 7)) % 1700 - 300; y = 300 + i * 330 + 60 * math.sin(T * 0.25 + i * 1.7)
        glow(c, x, y, 360, "#9fb0e0", a, add=False, sy=0.45)


# ------------------------------------------------------------------ shots
CAM_A = [(0.0, 1.00, 540, 960), (4.6, 1.20, 540, 870), (LAMP_ON, 1.40, 540, 800), (8.7, 2.3, 540, 700), (T_TALL, 3.5, 540, 655), (CUT_B, 4.4, 540, 646)]


def cam_smooth(keys, T, w=0.5):
    acc = np.zeros(3)
    for k in range(-3, 4):
        z, x, y = keyedN(keys, min(max(T + k * w / 3.0, 0), 1e3)); acc += (math.log(z), x, y)
    acc /= 7; return math.exp(acc[0]), acc[1], acc[2]


def handheld(T, a=1.0):
    return a * (3.0 * math.sin(T * 1.7) + 1.6 * math.sin(T * 4.3 + 1)), a * (2.4 * math.sin(T * 1.3 + 2) + 1.2 * math.sin(T * 3.7))


def shot_A(c, T):
    z, x, y = cam_smooth(CAM_A, T); hx, hy = handheld(T, 0.6)
    world(c, T, z, x + hx / z, y + hy / z)


def shot_B(c, T):
    z = 1.34 + 0.012 * (T - CUT_B); world(c, T, z, 540, 835)
    draw_me(c, T)


def draw_me(c, T):
    """foreground: my window, curtains, and me from behind, rim-lit by the moon, waving at the house"""
    sill = 1332
    rect(c, 0, 0, 44, H, "#05060b"); rect(c, W - 44, 0, W, H, "#05060b"); rect(c, 0, 0, W, 70, "#05060b")
    c.drawRect(skia.Rect(44, 70, W - 44, sill), paint("#2a3366", 0.6, 4)); line(c, 540, 70, 540, sill, 4, "#2a3366", 0.5)
    for sgn, x0 in ((1, 44), (-1, W - 44)):                                                 # curtains with lit folds
        p = skia.Path(); p.moveTo(x0, 0)
        for k in range(0, 9): p.lineTo(x0 + sgn * (96 + 22 * math.sin(k * 1.9 + T * 0.7 + sgn)), k * 170)
        p.lineTo(x0, H); p.close(); c.drawPath(p, paint("#140a1c", 0.98))
        for k in range(3): line(c, x0 + sgn * (26 + k * 28), 0, x0 + sgn * (34 + k * 28 + 8 * math.sin(T + k)), H, 3, "#33224a", 0.7)
    rect(c, 0, sill, W, H, "#080c1c"); rect(c, 0, sill, W, sill + 8, "#2a3568")
    wob = 0.010 * math.sin(T * 0.9)
    amt = prog(T, T_WAVED - 0.35, T_WAVED - 0.05) * (1 - prog(T, T_POLITE + 0.25, T_POLITE + 0.75))
    wv = math.sin(2 * math.pi * 1.9 * (T - T_WAVED))

    def shapes(col):
        c.save(); c.translate(380, 1500); c.rotate(wob)
        sh = skia.Path(); sh.moveTo(-290, 520); sh.quadTo(-300, 130, -210, 66); sh.quadTo(-90, 14, -40, -30); sh.lineTo(40, -30); sh.quadTo(90, 14, 210, 66); sh.quadTo(300, 130, 290, 520); sh.close()
        c.drawPath(sh, paint(col)); line(c, 0, -30, 0, -90, 58, col)
        oval(c, 0, -178, 86, 100, fill=col, line=None)
        hx = 250 + 46 * wv * amt; hy = lerp(300, -440, e_out(prog(T, T_WAVED - 0.35, T_WAVED + 0.2))) * amt + 360 * (1 - amt)
        k, hn = ik2(170, 70, hx, hy, 250, 270, -1)
        pth = skia.Path(); pth.moveTo(170, 70); pth.lineTo(*k); pth.lineTo(*hn); c.drawPath(pth, paint(col, 1.0, 58))
        circ(c, hn[0], hn[1], 48, fill=col, line=None)
        for da in (-0.7, -0.25, 0.2, 0.65): line(c, hn[0], hn[1], hn[0] + math.sin(da + wv * 0.4) * 88, hn[1] - math.cos(da) * 88, 18, col)
        c.restore()
    c.save(); c.translate(9, 0); shapes("#7a8fe0"); c.restore()                              # moon rim light (right edge)
    shapes("#04060e")


def shot_C(c, T):
    z = lerp(3.1, 5.0, e_io(prog(T, CUT_C, CUT_D))); hx, hy = handheld(T, 1.0)
    world(c, T, z, 540 + hx / z, 640 + hy / z)
    # night counter
    tags = [(CUT_C, "NIGHT 1"), (T_CLOSER1 - 0.05, "NIGHT 6"), (T_EVERY, "NIGHT 11"), (T_CLOSER2 - 0.03, "NIGHT 14"), (CUT_D, None)]
    for (t0, s), (t1, _) in zip(tags, tags[1:]):
        if t0 <= T < t1: night_tag(c, s, T, t0)
    mist(c, T, 0.07)


def night_tag(c, s, T, t0):
    dt = T - t0; a = 1.0 if dt > 0.3 else (1.0 if hsh(int(dt * 40), 2) > 0.4 else 0.2)
    f = afont(96); pa = paint("#e9ecff", 0.92 * a); pa2 = paint(RED, 0.85 * a)
    jx = 5 * math.sin(T * 70) if dt < 0.3 else 0
    spaced(c, s, 540 + jx + 4, 262, f, pa2, 8); spaced(c, s, 540 + jx, 258, f, pa, 8)


def shot_D(c, T):
    z = lerp(5.2, 6.5, e_io(prog(T, CUT_D, PAN0))); hx, hy = handheld(T, 1.3)
    sx, sy = 0, 0
    for tt, amp in ((T_POINTED, 7), (T_BEHIND, 9)):
        a, b = eng.shake(T, tt, amp, 8.0); sx += a; sy += b
    world(c, T, z, 540 + (hx + sx) / z, 640 + (hy + sy) / z)
    if T < CUT_D + 1.8: night_tag(c, "LAST NIGHT", T, CUT_D)
    mist(c, T, 0.06)


# ------------------------------------------------------------------ the bedroom
DX0, DX1, DY0, DY1 = 345, 735, 385, 1400


def door_theta(T):
    th = 38 + 3.0 * prog(T, PAN1, T_CLOSEIT) + 5.0 * prog(T, T_CLOSEIT, T_CLOSEIT + 1.7) + 1.2 * prog(T, CUT_H, T_ON)
    th = 38 + (th - 38)
    if T >= T_ON: th = lerp(th, 88, e_out(prog(T, T_ON, T_ON + 0.14)))
    return th


def hall_light(T):
    if T < T_TURNED: return 0.0
    dt = T - T_TURNED
    if dt < 0.22: return 1.0 if hsh(int(dt * 40), 5) > 0.35 else 0.0
    return 1.0


def draw_room(c, T):
    th = door_theta(T); sn, cs = math.sin(math.radians(th)), math.cos(math.radians(th)); HL = hall_light(T)
    # wall + floor
    vgrad(c, -200, -200, W + 200, 1400, "#151a35", "#090b18"); vgrad(c, -200, 1400, W + 200, 2200, "#0b0a12", "#030308")
    lgrad_poly(c, [(0, 250), (330, 430), (250, 1330), (0, 1090)], (0, 300), (330, 900), "#7d94e8", "#7d94e8", 0.14, 0.04, add=True)   # moonlight patch
    lgrad_poly(c, [(0, 1100), (250, 1340), (150, 1920), (0, 1920)], (0, 1200), (200, 1800), "#7d94e8", "#7d94e8", 0.10, 0.0, add=True)
    rect(c, 0, 1372, W, 1404, "#161220")                                                    # baseboard
    # picture on the wall (hangs a little crooked)
    c.save(); c.translate(150, 690); c.rotate(-4 + 1.2 * math.sin(T * 0.4)); rect(c, -60, -80, 60, 80, "#1b130f"); rect(c, -48, -68, 48, 68, "#0a0d1c"); c.restore()
    # frame + hallway
    rect(c, DX0 - 28, DY0 - 28, DX1 + 28, DY1, "#1f1612"); c.drawRect(skia.Rect(DX0 - 28, DY0 - 28, DX1 + 28, DY1), paint("#4a3a30", 0.5, 3))
    c.save(); c.clipRect(skia.Rect(DX0, DY0, DX1, DY1), skia.ClipOp.kIntersect, True)
    rect(c, DX0, DY0, DX1, DY1, "#010103")
    if HL > 0:
        vgrad(c, DX0, DY0, DX1, DY1, "#ffe6a8", "#b8742c", HL, HL)
        for k in range(6): rect(c, DX0, 520 + k * 160, DX1, 524 + k * 160, "#6a4220", 0.25 * HL)
        rect(c, DX0, 1250, DX1, DY1, "#4b2d12", 0.8 * HL)
        glow(c, 600, 700, 360, "#fff4cf", 0.5 * HL)
    # the shadow in the hallway
    fx = lerp(660, 560, e_out(prog(T, T_ON, T_ON + 0.25)))
    if T >= T_HALL - 0.1:
        eye_a = prog(T, T_HALL - 0.1, T_HALL + 0.5) * (0.7 + 0.15 * math.sin(T * 6))
        if T >= T_TURNED: eye_a = 1.0
        wv = math.sin(2 * math.pi * 1.9 * (T - T_TURNED))
        arm = (36 + 14 * wv, -78, -90 + 12 * wv, 1.0)
        c.save(); c.translate(fx, 800 + (1 - HL) * 0); c.scale(1.0, 1.0)
        if HL > 0 or T >= T_HALL:
            if HL > 0: figure(c, T, s=3.2, dy=0, tilt=0.20, arm=arm, eyes=eye_a, dx=0)
            else:
                c.save(); c.scale(3.2, 3.2)
                for sgn in (-1, 1): glow(c, sgn * 11, -61, 26, "#ffffff", 0.5 * eye_a); oval(c, sgn * 11, -61, 7.5, 3.4, fill="#ffffff", alpha=eye_a)
                c.restore()
        c.restore()
    c.restore()
    if HL > 0:                                                                              # spill on the floor
        lgrad_poly(c, [(DX0 + 40, 1400), (DX1, 1400), (DX1 + 380, 1920), (DX0 - 280, 1920)], (0, 1400), (0, 1920), "#ffc86a", "#ffc86a", 0.34 * HL, 0.05, add=True)
    # door leaf (swings toward me)
    wl = (DX1 - DX0) * cs

    def lp(u, v):
        xt = DX0 + u * wl; yt = DY0 - 52 * sn * u; yb = DY1 + 110 * sn * u
        return (xt, yt + v * (yb - yt))
    poly(c, [lp(0, 0), lp(1, 0), lp(1, 1), lp(0, 1)], fill="#2b1e18", line_c=None)
    for (u0, u1, v0, v1) in ((0.12, 0.88, 0.06, 0.44), (0.12, 0.88, 0.52, 0.94)):
        poly(c, [lp(u0, v0), lp(u1, v0), lp(u1, v1), lp(u0, v1)], fill="#21160f", line_c="#3d2c22", lw=3)
    poly(c, [lp(0.93, 0), lp(1, 0), lp(1, 1), lp(0.93, 1)], fill="#3a2a22", line_c=None)
    kx, ky = lp(0.86, 0.52); circ(c, kx, ky, 17 * (1 + 0.3 * sn), fill="#a98c52", line="#3b2d18", lw=3); circ(c, kx - 5, ky - 6, 5, fill="#f5e3a8", line=None, alpha=0.7)
    # furniture silhouettes: bed (left), chair with a jacket (right)
    c.save(); oval(c, 60, 1500, 230, 260, fill="#06070f", line=None); oval(c, 120, 1330, 140, 70, fill="#0b0d1c", line=None); c.restore()
    rect(c, 830, 1200, 846, 1560, "#06070d"); rect(c, 960, 1200, 976, 1560, "#06070d"); rect(c, 830, 1380, 976, 1400, "#06070d")
    jk = skia.Path(); jk.moveTo(836, 1215); jk.quadTo(900, 1190, 972, 1215); jk.quadTo(990, 1330, 960, 1440); jk.quadTo(900, 1460, 846, 1440); jk.quadTo(818, 1320, 836, 1215); c.drawPath(jk, paint("#04050a"))
    oval(c, 904, 1186, 30, 34, fill="#04050a", line=None)


def room_cam(c, T, zoom, sx=0.0, sy=0.0):
    c.translate(540 + sx, 880 + sy); c.scale(zoom, zoom); c.translate(-540, -880)


def shot_F(c, T):
    z = 1.0 + 0.07 * prog(T, PAN1, CUT_G); hx, hy = handheld(T, 0.8)
    c.save(); room_cam(c, T, z, hx, hy); draw_room(c, T); c.restore()


def shot_G(c, T):
    z = 1.28 + 0.03 * (T - CUT_G); world(c, T, z, 540, 790)
    mist(c, T, 0.05)


def shot_H(c, T):
    z = 1.04 + 0.12 * e_io(prog(T, CUT_H, T_ON))
    sx = sy = 0.0
    if T >= T_ON:
        a, b = eng.shake(T, T_ON, 34, 5.5); sx, sy = a, b
        z = 1.2 + 0.55 * e_io(prog(T, T_ON, T_END)) + 0.15 * e_out(prog(T, T_ON, T_ON + 0.08))
    elif T >= T_TURNED:
        a, b = eng.shake(T, T_TURNED, 6, 9.0); sx, sy = a, b
    c.save(); room_cam(c, T, z, sx, sy); draw_room(c, T); c.restore()


def pan(c, T):
    p = e_io(prog(T, PAN0, PAN1))
    c.save(); c.translate(-p * W, 0); shot_D(c, T); c.restore()
    c.save(); c.translate((1 - p) * W, 0); shot_F(c, T); c.restore()


# ------------------------------------------------------------------ overlays: vignette, grain, ui text, captions
_GR = []


def grain(T):
    if not _GR:
        rs = np.random.RandomState(5)
        for _ in range(6):
            g = rs.randint(0, 255, (320, 180), dtype=np.uint8)
            _GR.append(skia.Image.fromarray(np.dstack([g, g, g, np.full_like(g, 22)]), skia.kBGRA_8888_ColorType, skia.kUnpremul_AlphaType))
    return _GR[int(T * 24) % 6]


def hb(T):
    """heartbeat pulse 0..1 (starts at the last night, speeds up)"""
    if T < CUT_D: return 0.0
    bpm = lerp(66, 118, prog(T, CUT_D, T_TURNED)); per = 60.0 / bpm; x = (T - CUT_D) % per
    return max(math.exp(-x * 14), 0.8 * math.exp(-max(x - per * 0.28, 0) * 14) if x > per * 0.28 else 0)


def overlays(c, T):
    h = hb(T) if T < PAN1 or T > CUT_H else 0.5 * hb(T)
    # vignette (throbs with the heart late in the story)
    p = skia.Paint(); p.setShader(radial(540, 900, 1250, "#000000", 0.0, 0.88, mid=(0.5, 0.0))); c.drawRect(FULL, p)
    if h > 0.01 and T > CUT_D:
        q = skia.Paint(); q.setShader(radial(540, 900, 1150, "#7a0000", 0.0, 0.42 * h, mid=(0.6, 0.0))); c.drawRect(FULL, q)
    # film grain
    g = grain(T); c.drawImageRect(g, FULL, skia.SamplingOptions(skia.FilterMode.kLinear), None)
    # hook title + clock
    if T < T_EMPTY + 1.3: hook_title(c, T)
    if T_3AM - 0.05 <= T < T_TALL + 0.1: clock(c, T)
    # hallway flash on the scare
    if T_ON <= T < T_ON + 0.16: c.drawRect(FULL, paint("#ffffff", 0.85 * (1 - (T - T_ON) / 0.16)))
    # black dips on hard cuts
    for tc in (CUT_B, CUT_C, CUT_D, CUT_G, CUT_H):
        dt = T - tc
        if -0.0 <= dt < 0.09: c.drawRect(FULL, paint("#000000", 1.0 - dt / 0.09))
    if T >= T_END: c.drawRect(FULL, paint("#000000", 1.0))
    elif T > T_END - 0.12: c.drawRect(FULL, paint("#000000", prog(T, T_END - 0.12, T_END)))
    caps(c, T)


def hook_title(c, T):
    a = 1.0 if T < T_EMPTY else cl(1 - (T - T_EMPTY) / 1.2)
    if a <= 0: return
    jit = 6 if (hsh(int(T * 18), 1) > 0.86) else 0
    f = afont(215)
    for i, (s, y) in enumerate((("NEVER", 540), ("WAVE BACK", 760))):
        spaced(c, s, 540 + 7 + jit, y + 5, f, paint(RED, 0.9 * a), 4)
        spaced(c, s, 540 - 3, y + 1, f, paint("#33ffff", 0.25 * a * (1 if jit else 0)), 4)
        spaced(c, s, 540, y, f, paint("#f2f4ff", a), 4)


def clock(c, T):
    a = prog(T, T_3AM - 0.05, T_3AM + 0.15) * (1 - prog(T, T_TALL - 0.3, T_TALL + 0.1))
    if a <= 0: return
    jit = 4 * math.sin(T * 90) if (T - T_3AM) < 0.4 else 0
    f = afont(210)
    glow(c, 540 + jit, 292, 330, RED, 0.35 * a)
    spaced(c, "3:00", 540 + jit, 330, f, paint("#ff2a2a", a), 6)
    spaced(c, "AM", 540 + jit + 330, 270, afont(80), paint("#ff2a2a", a), 6)


_CH = None


def caps(c, T):
    global _CH
    if _CH is None: _CH = STATE["chunks"]
    t = eng.CAPT if eng.CAPT is not None else T
    vgrad(c, 0, 1290, W, 1700, "#000000", "#000000", 0.0, 0.62)
    f = eng.font(84)
    for i, ch in enumerate(_CH):
        t0 = ch[0][1]; t1 = _CH[i + 1][0][1] if i + 1 < len(_CH) else ch[-1][2] + 0.3
        t1 = min(t1, ch[-1][2] + 0.45)
        if not (t0 - 0.02 <= t < t1 - 0.02): continue
        texts = [w[0].upper() for w in ch]; sp = f.measureText(" ") + 10; ws = [f.measureText(x) for x in texts]
        tot = sum(ws) + sp * (len(ws) - 1); kin = max(e_back(prog(t, t0 - 0.02, t0 + 0.16), 1.2), 0.0)
        c.save(); c.translate(W / 2, 1450); c.scale(0.92 + 0.08 * kin, 0.92 + 0.08 * kin)
        xx = -tot / 2
        for j, (w, wd) in enumerate(zip(ch, ws)):
            nxt = ch[j + 1][1] if j + 1 < len(ch) else t1
            active = w[1] - 0.02 <= t < nxt
            sc = 1.0 + (0.09 * math.sin(math.pi * prog(t, w[1], w[1] + 0.16)) if active else 0)
            c.save(); c.translate(xx + wd / 2, 0); c.scale(sc, sc)
            c.drawString(texts[j], -wd / 2, 84 * 0.36, f, paint("#000000", 1.0, 13))
            c.drawString(texts[j], -wd / 2, 84 * 0.36, f, paint("#ff3b3b" if active else "#f4f4fb"))
            c.restore(); xx += wd + sp
        c.restore()


# ------------------------------------------------------------------ master frame
def frame(c, T):
    T = max(0.0, min(T, TOTAL - 0.001))
    c.drawRect(FULL, paint("#000000"))
    if T < CUT_B: shot_A(c, T)
    elif T < CUT_C: shot_B(c, T)
    elif T < CUT_D: shot_C(c, T)
    elif T < PAN0: shot_D(c, T)
    elif T < PAN1: pan(c, T)
    elif T < CUT_G: shot_F(c, T)
    elif T < CUT_H: shot_G(c, T)
    else: shot_H(c, T)
    overlays(c, T)


# ------------------------------------------------------------------ sound design
CUES = [("beep", T_3AM), ("bulb_on", LAMP_ON), ("thud_lo", T_TALL + 0.1),
        ("tap", CUT_C + 0.05), ("tap", CUT_C + 0.35), ("tap", T_CLOSER1), ("tap", T_CLOSER1 + 0.3), ("tap", T_EVERY), ("tap", T_EVERY + 0.28), ("tap", T_CLOSER2), ("tap", T_CLOSER2 + 0.25),
        ("thud", CUT_B), ("thud", CUT_C), ("thud_lo", CUT_D), ("thud_lo", T_BEHIND), ("whoosh", PAN0 + 0.05),
        ("creak", T_CLOSEIT - 0.1), ("bulb_off", LAMP_OFF - 0.08), ("riser_s", CUT_H + 0.15),
        ("click", T_TURNED + 0.01), ("bulb_on", T_TURNED + 0.02), ("sting", T_ON - 0.01), ("thud_lo", T_ON), ("thud_lo", T_ON + 0.03)]
_t = CUT_D
while _t < T_TURNED - 0.3:
    _bpm = lerp(66, 118, prog(_t, CUT_D, T_TURNED)); CUES.append(("heart", _t)); _t += 60.0 / _bpm


def MUSIC(mix, total, add):
    sfx.music_horror(mix, total, add, stop=LAMP_OFF, start=T_EMPTY + 1.6)


def VOICE_FX(v):
    return sfx.reverb(v, wet=0.2, rt=1.2)


RENDER = dict(nsub=3, shutter=0.5, crf=23)

MASTER = dict(pre="acompressor=threshold=0.25:ratio=2:attack=20:release=250:makeup=1", I=-17.0, TP=-1.5)
