"""MOTION DETECTED: animated horror short told through a home-camera app. Custom project, everything drawn in code.

Shots: LOCK1 (alert on the lock screen) -> KITCHEN (I live alone) -> APP loading -> BEDROOM FEED (something sits on the bed,
       turns, smiles) -> LOCK2 (alerts: stairs, hallway, kitchen) -> CAMERA GRID (only three cameras) -> CAM 4 reveal -> black.
"""
import math, random
import numpy as np
import skia
import eng, kit, sfx
from eng import (W, H, paint, C, rgb, mix_hex, cl, lerp, prog, e_out, e_io, e_back, line, circ, oval, poly, pulse, decay)
from kit import STATE, _norm

FULL = skia.Rect(0, 0, W, H)
FD = "/usr/share/fonts/truetype/google-fonts/"
_TF = {k: skia.Typeface.MakeFromFile(FD + v) for k, v in dict(light="Poppins-Light.ttf", reg="Poppins-Regular.ttf", med="Poppins-Medium.ttf", bold="Poppins-Bold.ttf").items()}
_TF["mono"] = skia.Typeface.MakeFromFile("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf")
_fc = {}


def fnt(kind, sz):
    k = (kind, int(round(sz)))
    if k not in _fc:
        f = skia.Font(_TF[kind], k[1]); f.setSubpixel(True); _fc[k] = f
    return _fc[k]


def txt(c, s, x, y, kind, sz, col="#ffffff", a=1.0, al="l"):
    f = fnt(kind, sz); w = f.measureText(s)
    x0 = x if al == "l" else (x - w / 2 if al == "c" else x - w)
    c.drawString(s, x0, y, f, paint(col, a))
    return w


def N(tok, approx, end=False):
    best = None
    for w in STATE["words"]:
        if _norm(w[0]) == _norm(tok) and (best is None or abs(w[1] - approx) < abs(best[1] - approx)): best = w
    if best is None: raise KeyError(tok)
    return best[2] if end else best[1]


# ------------------------------------------------------------------ story clock (anchored to the spoken words)
T_BUZZ1 = N("buzzed.", 1.84)
T_BEDROOM = N("Bedroom.", 4.63)
CUT_K = N("I", 6.32) - 0.10
T_KITCHEN = N("kitchen.", 8.69)
T_OPENED = N("opened", 10.42)
T_APPEND = N("app.", 10.97)
T_EMPTY = N("empty.", 12.37)
T_SOMETHING = N("something", 14.55)
T_STILL = N("still.", 16.57)
T_WALL = N("wall.", 17.96)
T_TURNED = N("turned", 19.89)
T_SLOWLY = N("Slowly.", 21.18)
T_UNTIL = N("Until", 22.25)
T_CAMERA = N("camera.", 23.91)
T_SMILED = N("smiled.", 25.74)
T_TOO = N("Too", 26.70)
T_WIDE = N("wide.", 26.91)
CUT_L2 = T_WIDE + 1.15
T_BUZZ2 = N("buzzed", 29.32)
T_STAIRS = N("Stairs.", 31.85)
T_BUZZ3 = N("Motion", 33.39) - 0.08
T_HALL = N("Hallway.", 35.03)
T_BUZZ4 = N("One", 36.81)
T_KIT2 = N("Kitchen.", 39.58)
CUT_GRID = T_KIT2 + 1.05
T_ONLY = N("only", 41.42)
T_THREE = N("three", 42.34)
T_CAMS = N("cameras.", 42.60)
CUT_CAM4 = T_CAMS + 0.42
T_FINAL = CUT_CAM4 + 1.25
TOTAL = T_FINAL + 1.0
T_APP_IN = T_OPENED - 0.05
T_FEED = T_APPEND + 0.6


def keyed(keys, T):
    if T <= keys[0][0]: return keys[0][1]
    for (t0, v0), (t1, v1) in zip(keys, keys[1:]):
        if T < t1: return lerp(v0, v1, e_io(prog(T, t0, t1)))
    return keys[-1][1]


def hsh(i, seed=0):
    x = math.sin(i * 12.9898 + seed * 78.233) * 43758.5453
    return x - math.floor(x)


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


def hgrad_path(c, path, x0, x1, cols, pos=None, a=1.0):
    n = len(cols); pos = pos or [i / (n - 1) for i in range(n)]
    cc = []
    for h in cols:
        R, G, B = rgb(h); cc.append(skia.ColorSetARGB(int(255 * a), R, G, B))
    p = skia.Paint(); p.setAntiAlias(True); p.setShader(skia.GradientShader.MakeLinear([(x0, 0), (x1, 0)], cc, pos))
    c.drawPath(path, p)


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


def rr(c, x0, y0, x1, y1, r, col, a=1.0, stroke=None):
    c.drawRoundRect(skia.Rect(x0, y0, x1, y1), r, r, paint(col, a, stroke) if stroke else paint(col, a))


def pathpts(pts, close=True):
    p = skia.Path(); p.moveTo(*pts[0])
    for q in pts[1:]: p.lineTo(*q)
    if close: p.close()
    return p


# ------------------------------------------------------------------ night-vision palette
NV0, NV1, NV2, NV3, NV4, NV5, NV6, NV7 = "#050a06", "#0d160f", "#18271b", "#2a4130", "#4d6e54", "#8fb095", "#c9e2cb", "#effcef"

_NZ = []


def noise_img(T):
    if not _NZ:
        rs = np.random.RandomState(7)
        for _ in range(8):
            g = rs.randint(0, 255, (240, 135), dtype=np.uint8)
            _NZ.append(skia.Image.fromarray(np.dstack([g, g, g, np.full_like(g, 255)]), skia.kBGRA_8888_ColorType, skia.kUnpremul_AlphaType))
    return _NZ[int(T * 30) % 8]


def static_fill(c, T, a):
    if a <= 0.01: return
    p = skia.Paint(); p.setAlphaf(cl(a))
    c.drawImageRect(noise_img(T), FULL, skia.SamplingOptions(skia.FilterMode.kNearest), p)


def scanlines(c, a=0.16, step=5):
    p = paint("#000000", a)
    for y in range(0, H, step): c.drawRect(skia.Rect(0, y, W, y + 2), p)


def vignette(c, a=0.85, cy=900, r=1250):
    p = skia.Paint(); p.setShader(radial(540, cy, r, "#000000", 0.0, a, mid=(0.45, 0.0))); c.drawRect(FULL, p)


def tear(c, T, amt, seed=0):
    """analogue/digital tear: bright horizontal slivers + cyan/magenta offsets"""
    if amt <= 0.01: return
    n = int(3 + 7 * amt)
    for i in range(n):
        k = int(T * 30) * 17 + i * 31 + seed
        y = hsh(k, 1) * H; hh = 6 + hsh(k, 2) * 60 * amt
        col = ("#00ffd5", "#ff2bd6", "#ffffff", "#7aff9a")[int(hsh(k, 3) * 4) % 4]
        c.drawRect(skia.Rect(0, y, W, y + hh), paint(col, 0.10 + 0.22 * amt * hsh(k, 4)))
        x0 = hsh(k, 5) * W * 0.6; c.drawRect(skia.Rect(x0, y + hh * 0.3, x0 + 200 + hsh(k, 6) * 380, y + hh * 0.55), paint("#ffffff", 0.18 * amt))


def glitch_amt(T, events):
    """events: [(t, dur, strength)] -> current glitch strength 0..1"""
    g = 0.0
    for (t, d, s) in events:
        if t <= T < t + d: g = max(g, s * (1 - (T - t) / d) ** 0.5)
    return g


def stamp_time(T):
    s = 41 + int(T); mm = 12 + s // 60; ss = s % 60
    return "03:%02d:%02d" % (mm, ss)


# ------------------------------------------------------------------ the head (a real sphere projection: it can turn)
def head_draw(c, hx, hy, rx, ry, psi, roll=0.0, smile=0.0, wide=0.0, eyes=1.0, T=0.0, skin=NV5, shade=NV3, hair_len=2.35, sway=0.0):
    """psi: 0 = facing away from the camera, 180 = looking into the lens. Long black hair hangs down its back."""
    c.save(); c.translate(hx, hy); c.rotate(roll)
    cosp = math.cos(math.radians(psi)); sinp = math.sin(math.radians(psi))
    v = cl((cosp + 0.25) / 1.25)                                   # 1 = back of the head to us, 0 = face to us
    HAIR, HAIR_RIM = "#020503", NV2
    # ---- hair mass hanging behind the head (down its back, over the shoulders)
    wt = rx * 1.17; wb = rx * (1.02 + 0.40 * v); top = -ry * 1.12; bot = ry * hair_len
    hp = skia.Path(); hp.moveTo(-wt, -ry * 0.25)
    hp.cubicTo(-wt * 1.14, -ry * 1.55, wt * 1.14, -ry * 1.55, wt, -ry * 0.25)
    for k in range(1, 9): t = k / 8.0; hp.lineTo(lerp(wt, wb, t) + sway * t, lerp(-ry * 0.25, bot, t) + (hsh(k, 1) - 0.5) * ry * 0.10 * (k > 3))
    for j in range(1, 8): t = j / 8.0; hp.lineTo(lerp(wb, -wb, t) + sway, bot + ry * 0.16 * (1 if j % 2 else -1) * (0.6 + hsh(j, 3) * 0.7))
    for k in range(8, 0, -1): t = k / 8.0; hp.lineTo(-lerp(wt, wb, t) + sway * t, lerp(-ry * 0.25, bot, t) + (hsh(k, 5) - 0.5) * ry * 0.10 * (k > 3))
    hp.close(); c.drawPath(hp, paint(HAIR))
    for k in range(9):
        x = lerp(-wt * 0.86, wt * 0.86, k / 8.0); line(c, x, -ry * 0.15, x * 1.07 + sway, bot * 0.93, 2.6, NV3, 0.16 + 0.12 * hsh(k, 9))
    # ---- the skull
    p = skia.Paint(); p.setAntiAlias(True)
    p.setShader(skia.GradientShader.MakeRadial((-rx * 0.22, -ry * 0.28), ry * 1.25, [C(skin), C(shade)], [0.0, 1.0]))
    c.drawOval(skia.Rect(-rx, -ry, rx, ry), p)

    def pr(a_deg, lat_deg):
        a = math.radians(a_deg); la = math.radians(lat_deg)
        return -math.sin(a) * math.cos(la) * rx, -math.sin(la) * ry, -math.cos(a) * math.cos(la)

    if v > 0.02:                                                   # back of the head is hair
        c.save(); hp = skia.Path(); hp.addOval(skia.Rect(-rx, -ry, rx, ry)); c.clipPath(hp, skia.ClipOp.kIntersect, True)
        xb = sinp * rx * 0.95; rad = rx * (0.30 + 1.05 * v)
        oval(c, xb, -ry * 0.10, rad, ry * 1.2, fill=HAIR, line=None)
        for k in range(6): line(c, xb - rad * 0.7 + k * rad * 0.28, -ry * 0.9, xb - rad * 0.7 + k * rad * 0.28 + 6, ry * 0.8, 2.4, NV3, 0.16)
        c.restore()
    # ---- face
    for dl in (-27, 27):                                           # hollow eyes
        x, y, d = pr(psi + dl, 8)
        if d > 0.05:
            ew = 5.5 + 11.5 * d; eh = 8 + 6.5 * d + 5 * wide
            oval(c, x, y + 3, ew * 2.1, eh * 2.1, fill="#000000", line=None, alpha=0.30 * cl(d * 1.6))
            oval(c, x, y, ew, eh, fill="#010201", line=None, alpha=cl(d * 3))
            if eyes > 0:
                fl = 0.72 + 0.28 * math.sin(T * 23 + dl)
                glow(c, x + 1, y - 1, 12 + 9 * wide, NV7, 0.50 * eyes * fl * cl(d * 2))
                oval(c, x + 1, y - 1, 2.6 * d + 1.0, 2.6 * d + 1.0, fill=NV7, line=None, alpha=eyes * fl * cl(d * 2.5))
    x0, y0, d0 = pr(psi, 4); x1, y1, d1 = pr(psi, -20)             # nose shadow
    if d0 > 0.15: line(c, x0, y0, x1, y1, 4 * d0 + 1, "#0a140c", 0.40 * cl(d0))
    if smile > 0.01:
        half = smile * 80.0; steps = 36
        up, lo = [], []
        for k in range(steps + 1):
            u = -half + 2 * half * k / steps; uu = u / max(half, 1.0)
            lat_u = -31 + 15 * uu * uu
            lat_l = lat_u - (1.6 + 6.5 * wide) * max(0.0, 1 - uu * uu) ** 0.9 - 0.3
            up.append(pr(psi + u, lat_u)); lo.append(pr(psi + u, lat_l))
        k = 0
        while k <= steps:
            if up[k][2] > 0.03:
                j = k
                while j + 1 <= steps and up[j + 1][2] > 0.03: j += 1
                if j - k >= 1:
                    poly(c, [(q[0], q[1]) for q in up[k:j + 1]] + [(q[0], q[1]) for q in lo[k:j + 1][::-1]], fill="#010201", line_c=None)
                    if wide > 0.25:
                        for m in range(k, j + 1, 3):
                            qa, qb = up[m], lo[m]
                            line(c, qa[0], qa[1] + 0.5, qa[0] + (qb[0] - qa[0]) * 0.45, qa[1] + (qb[1] - qa[1]) * 0.45, 2.2, NV7, 0.38 * cl(qa[2] * 2) * cl((wide - 0.25) * 2))
                    for end in (k, j):
                        qe = up[end]
                        if qe[2] > 0.25: line(c, qe[0], qe[1], qe[0] + (8 if end == j else -8), qe[1] - 9, 2.6, "#0a140c", 0.55)     # cheek creases
                k = j + 1
            else: k += 1
    # ---- hair falling forward over the face as it turns toward us
    fa = (1 - v) * 0.95
    if fa > 0.02:
        for sg in (-1, 1):
            pts = [(sg * rx * 1.02, -ry * 0.92), (sg * rx * 0.66, -ry * 0.74), (sg * rx * 0.60, ry * 0.10), (sg * rx * 0.52, ry * 1.1), (sg * rx * 0.82, ry * 1.65), (sg * rx * 1.14, ry * 0.7)]
            poly(c, pts, fill=HAIR, line_c=None, alpha=fa)
            for k in range(4): line(c, sg * (rx * (0.95 - 0.1 * k)), -ry * 0.7, sg * (rx * (0.78 - 0.08 * k)), ry * 1.35, 2.2, NV3, 0.20 * fa)
    c.restore()


# ------------------------------------------------------------------ BEDROOM (night vision)
def bedroom_view(c, T, fig=True, psi=0.0, roll=0.0, smile=0.0, wide=0.0, hd=0.0, jit=0.0):
    vgrad(c, -60, -60, W + 60, 1120, NV1, NV3)
    glow(c, 540, 640, 1000, NV5, 0.18, add=True, sy=1.0)                                  # IR illuminator hot spot
    rect(c, -60, -60, W + 60, 150, NV0, 0.65)
    rect(c, 110, 250, 440, 770, NV0); rect(c, 126, 266, 424, 754, NV2)
    vgrad(c, 126, 266, 424, 754, NV3, NV2, 0.8, 0.8)
    line(c, 275, 266, 275, 754, 8, NV0); line(c, 126, 500, 424, 500, 8, NV0)
    for xx, sg in ((96, 1), (454, -1)):
        pth = skia.Path(); pth.moveTo(xx, 230)
        for j in range(8): pth.lineTo(xx + sg * (24 + 30 * math.sin(j * 1.3 + 1)) * 1.0 - sg * 6, 230 + j * 80)
        pth.lineTo(xx, 800); pth.close(); c.drawPath(pth, paint(NV1, 0.95))
    rect(c, 690, 330, 930, 560, NV0); rect(c, 704, 344, 916, 546, NV2)
    poly(c, [(704, 546), (760, 450), (810, 500), (860, 420), (916, 546)], fill=NV1, line_c=None, alpha=0.9)
    rect(c, 790, 860, 1000, 1110, NV1, 0.95)
    poly(c, [(770, 1010), (800, 880), (860, 850), (930, 880), (985, 960), (1000, 1100), (790, 1110)], fill=NV2, line_c=None)
    line(c, 800, 1110, 790, 1180, 12, NV0); line(c, 990, 1110, 1000, 1180, 12, NV0)
    glow(c, 880, 900, 130, NV5, 0.08)
    oval(c, 250, 1105, 190, 62, fill=NV3, line=None); oval(c, 250, 1090, 180, 48, fill=NV4, line=None, alpha=0.7)
    oval(c, 830, 1105, 170, 58, fill=NV3, line=None); oval(c, 830, 1092, 160, 44, fill=NV4, line=None, alpha=0.6)
    vgrad(c, -60, 1120, W + 60, 2000, NV3, NV2)
    if fig:
        hy = 676 - 40 * hd
        # pale thin neck
        line(c, 520, 760 - 18 * hd, 520, 850, 40, NV2); line(c, 520, 760 - 18 * hd, 520, 850, 30, NV5)
        # torso: a thin dark gown, bony shoulders catching the IR light
        t = skia.Path(); t.moveTo(478, 822); t.quadTo(420, 836, 360, 894); t.quadTo(342, 990, 386, 1196); t.lineTo(662, 1196); t.quadTo(700, 990, 680, 894); t.quadTo(620, 836, 562, 822); t.close()
        hgrad_path(c, t, 350, 690, [NV1, NV2, NV2, NV1], [0, 0.35, 0.65, 1])
        tp = skia.Path(); tp.moveTo(360, 894); tp.quadTo(420, 836, 478, 822); tp.moveTo(562, 822); tp.quadTo(620, 836, 680, 894)
        c.drawPath(tp, paint(NV5, 0.55, 5))
        for k in range(5):
            xk = 430 + k * 40; pth = skia.Path(); pth.moveTo(xk, 900 + 10 * (k % 2)); pth.quadTo(xk + 14 * (k - 2), 1030, xk + 6 * (k - 2), 1190); c.drawPath(pth, paint(NV3, 0.30, 4))
        line(c, 520, 832, 520, 1180, 3, NV3, 0.35)
        head_draw(c, 520 + 1.3 * jit * math.sin(T * 61), hy, 72, 98, psi, roll, smile, wide, 1.0, T, sway=3 * math.sin(T * 0.8))
    bl = skia.Path(); bl.moveTo(-60, 1190)
    for i in range(0, 13): bl.lineTo(-60 + i * 100, 1176 + 22 * math.sin(i * 1.7) + (14 if 4 <= i <= 8 else 0))
    bl.lineTo(W + 60, 2000); bl.lineTo(-60, 2000); bl.close()
    p = skia.Paint(); p.setShader(skia.GradientShader.MakeLinear([(0, 1170), (0, 1700)], [C(NV4), C(NV2)], [0, 1])); c.drawPath(bl, p)
    for k in range(7):
        x0 = 40 + k * 160; pth = skia.Path(); pth.moveTo(x0, 1230); pth.quadTo(x0 + 70, 1290 + 14 * k % 5, x0 + 40 + 20 * (k % 3), 1420); c.drawPath(pth, paint(NV1, 0.4, 7))
        pth = skia.Path(); pth.moveTo(x0 + 18, 1226); pth.quadTo(x0 + 88, 1285, x0 + 60 + 20 * (k % 3), 1410); c.drawPath(pth, paint(NV6, 0.10, 5))
    if fig:                                                                               # arms: dark sleeves, long pale forearms and fingers on the blanket
        for sx in (-1, 1):
            sh = (520 + sx * 146, 896); el = (520 + sx * 200, 1050); wr = (520 + sx * 154, 1236)
            p1 = skia.Path(); p1.moveTo(*sh); p1.lineTo(*el)
            c.drawPath(p1, paint(NV0, 1.0, 46)); c.drawPath(p1, paint(NV2, 1.0, 38))
            p2 = skia.Path(); p2.moveTo(*el); p2.lineTo(*wr)
            c.drawPath(p2, paint(NV1, 1.0, 36)); c.drawPath(p2, paint(NV5, 1.0, 27)); c.drawPath(p2, paint(NV6, 0.3, 9))
            oval(c, wr[0], wr[1] + 6, 22, 28, fill=NV5, line=None)
            for fa, fl in ((-0.55, 78), (-0.25, 100), (0.05, 108), (0.34, 98), (0.62, 74)):
                ang = math.pi / 2 + fa * sx
                ex2, ey2 = wr[0] + math.cos(ang) * fl * 0.65, wr[1] + 12 + math.sin(ang) * fl
                line(c, wr[0], wr[1] + 12, ex2, ey2, 8.5, NV1); line(c, wr[0], wr[1] + 12, ex2, ey2, 6, NV5)


# ------------------------------------------------------------------ STAIRS + HALLWAY + KITCHEN-CAM views
def stand_figure(c, x, y, hgt, psi=180.0, roll=0.0, smile=0.0, wide=0.0, T=0.0, lean=0.0, reach=0.0):
    """tall, thin, in a dark gown, long black hair. Design units: 1000 tall, origin at the feet."""
    s = hgt / 1000.0
    c.save(); c.translate(x, y); c.scale(s, s)
    for sx in (-1, 1):
        line(c, sx * 26, -230, sx * 30, -6, 28, NV1); line(c, sx * 26, -230, sx * 30, -6, 19, NV5)
    gown = skia.Path(); gown.moveTo(-64, -800); gown.quadTo(-72, -600, -96, -250); gown.lineTo(-126, -190); gown.lineTo(126, -190); gown.lineTo(96, -250); gown.quadTo(72, -600, 64, -800); gown.close()
    hgrad_path(c, gown, -126, 126, [NV0, NV2, NV0], [0, 0.5, 1])
    line(c, -64, -800, -92, -300, 4, NV5, 0.35); line(c, 64, -800, 92, -300, 4, NV5, 0.35)
    for sx in (-1, 1):
        sh = (sx * 66, -780); el = (sx * (98 + 20 * reach), -520); wr = (sx * (92 + 36 * reach), -150 + 60 * reach)
        p1 = skia.Path(); p1.moveTo(*sh); p1.lineTo(*el); c.drawPath(p1, paint(NV0, 1.0, 34)); c.drawPath(p1, paint(NV2, 1.0, 25))
        p2 = skia.Path(); p2.moveTo(*el); p2.lineTo(*wr); c.drawPath(p2, paint(NV1, 1.0, 28)); c.drawPath(p2, paint(NV5, 1.0, 19))
        for fa in (-0.4, -0.12, 0.14, 0.4):
            line(c, wr[0], wr[1], wr[0] + fa * 60 * sx, wr[1] + 100, 8, NV1); line(c, wr[0], wr[1], wr[0] + fa * 60 * sx, wr[1] + 100, 5, NV5)
    line(c, 0, -790 + 6 * lean, 0, -850, 26, NV1); line(c, 0, -790, 0, -850, 17, NV5)
    head_draw(c, 6 * lean, -925, 46, 63, psi, roll, smile, wide, 1.0, T, hair_len=2.1)
    c.restore()


def stairs_view(c, T, fig=True, prox=0.0):
    vgrad(c, -60, -60, W + 60, 2000, NV0, NV2)
    # walls converging
    poly(c, [(-60, -60), (400, 540), (400, 1080), (-60, 2000)], fill=NV1, line_c=None)
    poly(c, [(W + 60, -60), (680, 540), (680, 1080), (W + 60, 2000)], fill=NV1, line_c=None)
    rect(c, 400, 540, 680, 800, NV0)                                                       # dark landing above
    glow(c, 540, 720, 150, NV4, 0.22)
    # steps (far to near)
    for i in range(9, -1, -1):
        f0 = 1.0 / (1 + 0.52 * i); f1 = 1.0 / (1 + 0.52 * (i + 1))
        y0 = 760 + 1050 * f0 - 70; y1 = 760 + 1050 * f1 - 70
        wx = 330 + 330 * f0
        c.drawRect(skia.Rect(540 - wx, y1, 540 + wx, y0), paint(mix_hex(NV2, NV4, f0 * 0.8), 1.0))
        c.drawRect(skia.Rect(540 - wx, y1, 540 + wx, y1 + 7 + 8 * f0), paint(NV5, 0.35 + 0.3 * f0))
        c.drawRect(skia.Rect(540 - wx, y0 - 4, 540 + wx, y0), paint(NV0, 0.6))
    # banister
    line(c, 60, 1760, 420, 820, 16, NV0); line(c, 60, 1740, 420, 800, 8, NV5, 0.6)
    for k in range(7):
        t = k / 6.0; xx = lerp(120, 400, t ** 0.9); yb = lerp(1850, 880, t ** 0.9); yt = lerp(1690, 810, t ** 0.9)
        line(c, xx, yb, xx, yt, lerp(14, 6, t), NV0); line(c, xx, yb, xx, yt, lerp(6, 3, t), NV4, 0.7)
    if fig: stand_figure(c, 540, 860, 330 + 210 * prox, 180, 7.0, 0.0, 0.0, T)


def hall_view(c, T, fig=True, prox=0.0, smile=0.7):
    vgrad(c, -60, -60, W + 60, 2000, NV0, NV2)
    poly(c, [(-60, -60), (470, 760), (610, 760), (W + 60, -60)], fill=NV1, line_c=None)    # ceiling
    poly(c, [(-60, 2000), (470, 880), (610, 880), (W + 60, 2000)], fill=NV3, line_c=None)  # floor
    poly(c, [(-60, -60), (470, 760), (470, 880), (-60, 2000)], fill=NV2, line_c=None)      # left wall
    poly(c, [(W + 60, -60), (610, 760), (610, 880), (W + 60, 2000)], fill=NV2, line_c=None)
    rect(c, 470, 760, 610, 880, NV0); glow(c, 540, 820, 130, NV5, 0.30)                    # far window glow
    for sx in (-1, 1):                                                                      # doors on each wall
        for (a0, a1) in ((0.18, 0.40), (0.55, 0.74)):
            def P(t): return 540 + sx * lerp(620, 70, t)
            xa, xb = P(a0), P(a1)
            ya0 = lerp(160, 745, a0); ya1 = lerp(160, 745, a1); yb0 = lerp(1700, 880, a0); yb1 = lerp(1700, 880, a1)
            poly(c, [(xa, ya0 + 40), (xb, ya1 + 40), (xb, yb1), (xa, yb0)], fill=NV1, line_c=None)
            line(c, xa, ya0 + 40, xa, yb0, 5, NV4, 0.5)
    for k in range(6):
        t = k / 6.0; y = lerp(1880, 900, t ** 0.7); line(c, lerp(-60, 470, t ** 0.7), y, lerp(W + 60, 610, t ** 0.7), y, 2, NV1, 0.55)
    if fig: stand_figure(c, 540, 1500 - 150 * (1 - prox), 900 + 260 * prox, 178, -9.0, smile, 0.2, T, lean=1.0, reach=0.6)


def kitchen_cam_view(c, T, lean=0.0):
    """CAM 4: high corner, looking at me from the front. Something tall stands behind me."""
    vgrad(c, -60, -60, W + 60, 1140, NV1, NV3)
    glow(c, 540, 700, 1100, NV5, 0.16)
    rect(c, 640, 250, 960, 660, NV0); rect(c, 656, 266, 944, 644, NV2); line(c, 800, 266, 800, 644, 8, NV0)     # window
    poly(c, [(668, 640), (740, 500), (800, 560), (860, 470), (936, 640)], fill=NV1, line_c=None, alpha=0.85)
    rect(c, 60, 420, 360, 760, NV1); rect(c, 60, 760, 380, 780, NV0)                                           # cabinets
    rect(c, 40, 880, 440, 1160, NV2); rect(c, 40, 870, 440, 900, NV4)
    vgrad(c, -60, 1130, W + 60, 2000, NV2, NV0)
    # the tall thing behind me: dark gown, long black hair, head bowed over my shoulder
    lx = 690 - 30 * lean; ly = 690 + 34 * lean
    tor = skia.Path(); tor.moveTo(lx - 190, 1060); tor.quadTo(lx - 160, 840, lx - 70, 800); tor.lineTo(lx + 70, 800); tor.quadTo(lx + 160, 840, lx + 190, 1060); tor.lineTo(lx + 170, 1600); tor.lineTo(lx - 170, 1600); tor.close()
    hgrad_path(c, tor, lx - 190, lx + 190, [NV0, NV2, NV0])
    line(c, lx - 74, 802, lx - 190, 1050, 4, NV5, 0.4); line(c, lx + 74, 802, lx + 190, 1050, 4, NV5, 0.4)
    line(c, lx, ly + 90, lx, 812, 38, NV2); line(c, lx, ly + 90, lx, 812, 28, NV5)
    head_draw(c, lx, ly, 78, 106, 180.0 + 3 * math.sin(T * 0.9), -15 - 9 * lean, 1.0, 0.9, 1.0, T, hair_len=2.1, sway=4 * math.sin(T * 1.1))
    hx, hy2 = lx - 330 + 14 * lean, 1030 + 26 * lean                                                           # one long arm reaching over my shoulder
    pth = skia.Path(); pth.moveTo(lx - 160, 900); pth.quadTo(lx - 330, 940, hx, hy2)
    c.drawPath(pth, paint(NV0, 1.0, 40)); c.drawPath(pth, paint(NV5, 1.0, 29)); c.drawPath(pth, paint(NV6, 0.3, 9))
    oval(c, hx, hy2, 24, 30, fill=NV5, line=None)
    for fa, fl in ((-0.5, 84), (-0.2, 112), (0.1, 118), (0.38, 100)):
        ex2 = hx + math.sin(fa) * fl * 0.8; ey2 = hy2 + math.cos(fa) * fl
        line(c, hx, hy2 + 8, ex2, ey2, 9, NV0); line(c, hx, hy2 + 8, ex2, ey2, 6, NV5)
    # me, from the front, head bowed to the phone, lit from below
    hd = 1.0 + 0.003 * math.sin(T * 1.6)
    c.save(); c.translate(430, 1100); c.scale(hd * 1.1, hd * 1.1)
    body = skia.Path(); body.moveTo(-180, 0); body.quadTo(-160, -150, -80, -180); body.lineTo(80, -180); body.quadTo(160, -150, 180, 0); body.lineTo(180, 900); body.lineTo(-180, 900); body.close()
    c.drawPath(body, paint(NV1)); c.drawPath(body, paint(NV4, 0.5, 5))
    line(c, -92, -20, -134, 160, 56, NV1); line(c, 92, -20, 128, 160, 56, NV1)
    line(c, 0, -200, 0, -150, 56, NV3)
    oval(c, 0, -264, 66, 80, fill=NV4, line=None)
    glow(c, 0, -20, 210, NV7, 0.55, add=True); glow(c, 0, -236, 150, NV7, 0.40)
    oval(c, 0, -250, 56, 68, fill=NV6, line=None, alpha=0.82)
    poly(c, [(-68, -296), (-44, -352), (40, -352), (68, -296), (62, -326), (0, -360), (-62, -326)], fill=NV1, line_c=None)
    for sx in (-1, 1): oval(c, sx * 22, -254, 10, 5, fill=NV0, line=None, alpha=0.95)
    line(c, -16, -208, 16, -208, 4, NV3, 0.8)
    rr(c, -36, -40, 36, 34, 8, NV7, 0.95); rr(c, -30, -34, 30, 28, 6, NV6, 0.95)
    c.restore()


# ------------------------------------------------------------------ THE KITCHEN (shot 2)
def drip_phase(T, t0=0.0):
    x = ((T - t0) % 1.75) / 1.75
    return x


def kitchen_scene(c, T):
    z = 1.0 + 0.11 * prog(T, CUT_K, T_OPENED)
    c.save(); c.translate(540, 900); c.scale(z, z); c.translate(-540 + 14 * prog(T, CUT_K, T_OPENED), -900)
    vgrad(c, -200, -200, 1300, 1130, "#060a13", "#101b2e")
    vgrad(c, -200, 1130, 1300, 2300, "#0b121e", "#04060b")
    rect(c, -200, 1124, 1300, 1136, "#1b2a40", 0.9)
    # window + moon
    rect(c, 80, 290, 480, 880, "#050810")
    vgrad(c, 98, 308, 462, 862, "#223a66", "#0d1730")
    glow(c, 330, 440, 150, "#9db8ff", 0.35); circ(c, 330, 440, 46, fill="#dfe8ff", line=None)
    for k in range(5): line(c, 98 + 30 * k, 862, 150 + 60 * k, 700 - 30 * (k % 2), 7, "#050810", 0.9)
    line(c, 280, 308, 280, 862, 9, "#050810"); line(c, 98, 585, 462, 585, 9, "#050810")
    rect(c, 64, 876, 496, 896, "#16233a")
    lgrad_poly(c, [(98, 862), (462, 862), (860, 1500), (330, 1700)], (280, 862), (560, 1600), "#8fb0ff", "#8fb0ff", 0.10, 0.0, add=True)
    # cabinets, counter, microwave, sink
    rect(c, 520, 280, 780, 640, "#0a101c"); rect(c, 522, 282, 778, 638, "#0e1626", 0.9); line(c, 650, 282, 650, 638, 4, "#050810")
    rect(c, 60, 932, 790, 984, "#1b2940"); rect(c, 60, 984, 790, 1130, "#0a101b")
    for xx in (60, 300, 540): line(c, xx, 990, xx, 1128, 4, "#04070d")
    rect(c, 560, 770, 770, 932, "#0b121f"); rect(c, 574, 784, 690, 918, "#05080f")
    txt(c, "3:12", 604, 868, "mono", 40, "#35ff7a", 0.55 + 0.4 * (0.5 + 0.5 * math.sin(T * 2.0)), "l")
    glow(c, 640, 850, 120, "#35ff7a", 0.10)
    rr(c, 200, 892, 252, 934, 10, "#0f1828"); line(c, 252, 905, 270, 922, 6, "#0f1828")  # mug
    rect(c, 330, 926, 470, 936, "#05080f")                                                  # sink
    pf = skia.Path(); pf.moveTo(395, 930); pf.lineTo(395, 840); pf.quadTo(395, 800, 440, 800); pf.lineTo(470, 800); pf.lineTo(470, 830)
    c.drawPath(pf, paint("#26344f", 1.0, 14))
    dp = drip_phase(T)
    if dp < 0.45: oval(c, 470, 842 + 80 * (dp / 0.45) ** 2, 4, 6 + 5 * (dp / 0.45), fill="#9db8ff", line=None, alpha=0.9)
    # fridge
    rect(c, 800, 270, 1040, 1130, "#0b1220"); rect(c, 800, 270, 812, 1130, "#1a2842"); rect(c, 800, 600, 1040, 612, "#040711")
    rr(c, 980, 380, 992, 520, 4, "#26344f"); rr(c, 980, 650, 992, 800, 4, "#26344f")
    circ(c, 835, 330, 5, fill="#6fb2ff", line=None, alpha=0.6 + 0.4 * math.sin(T * 3)); glow(c, 835, 330, 40, "#6fb2ff", 0.25 * (0.6 + 0.4 * math.sin(T * 3)))
    vgrad(c, 812, 280, 1040, 1130, "#9db8ff", "#9db8ff", 0.05, 0.0)
    # me, from behind, lit by the phone
    sw = 1.0 + 0.005 * math.sin(T * 1.3)
    c.save(); c.translate(470, 1290); c.scale(1.0, sw); c.translate(-470, -1290)
    glow(c, 470, 985, 310, "#7fb8ff", 0.34)
    body = skia.Path(); body.moveTo(300, 1290); body.quadTo(290, 980, 340, 890); body.quadTo(470, 830, 600, 890); body.quadTo(650, 980, 640, 1290); body.close()
    c.drawPath(body, paint("#04060b")); c.drawPath(body, paint("#27406e", 0.55, 4))
    oval(c, 470, 770, 66, 78, fill="#04060b", line=None); c.drawOval(skia.Rect(404, 692, 536, 848), paint("#27406e", 0.5, 3))
    for sx in (-1, 1):
        pth = skia.Path(); pth.moveTo(470 + sx * 150, 930); pth.quadTo(470 + sx * 215, 1020, 470 + sx * 95, 1075)
        c.drawPath(pth, paint("#04060b", 1.0, 62)); c.drawPath(pth, paint("#2b4a86", 0.45, 3))
    glow(c, 470, 1085, 150, "#bfe0ff", 0.55); rr(c, 428, 1050, 512, 1118, 9, "#cfe6ff", 0.9)
    c.restore()
    # dust
    for i in range(26):
        x = (hsh(i, 2) * 1080 + 14 * math.sin(T * 0.4 + i)) % 1080; y = (hsh(i, 5) * 1400 + 600 - T * (6 + 8 * hsh(i, 7))) % 1400 + 300
        circ(c, x, y, 1.6 + 1.6 * hsh(i, 9), fill="#9db8ff", line=None, alpha=0.18 + 0.2 * hsh(i, 4))
    c.restore()
    vignette(c, 0.88, 900, 1200)
    p = skia.Paint(); p.setAlphaf(0.07); c.drawImageRect(noise_img(T), FULL, skia.SamplingOptions(skia.FilterMode.kLinear), p)


# ------------------------------------------------------------------ THE PHONE: lock screen + banners + camera app
def battery(c, x, y, lvl, col="#ffffff"):
    rr(c, x, y, x + 58, y + 28, 8, col, 0.6, 2.5); rr(c, x + 4, y + 4, x + 4 + 50 * lvl, y + 24, 5, "#ff4a4a" if lvl < 0.2 else col, 0.95); rect(c, x + 60, y + 9, x + 64, y + 19, col, 0.6)


def status_bar(c, T, time_str=None, col="#ffffff"):
    if time_str: txt(c, time_str, 70, 84, "bold", 36, col, 0.95)
    for k in range(4): rr(c, 800 + k * 18, 82 - 8 - k * 6, 800 + k * 18 + 11, 82, 3, col, 0.9 if k < 3 else 0.35)
    battery(c, 936, 58, 0.14)


def app_icon(c, x, y, s):
    p = skia.Paint(); p.setAntiAlias(True)
    p.setShader(skia.GradientShader.MakeLinear([(x, y), (x + s, y + s)], [C("#ff6a3d"), C("#d3112b")], [0, 1]))
    c.drawRoundRect(skia.Rect(x, y, x + s, y + s), s * 0.24, s * 0.24, p)
    rr(c, x + s * 0.2, y + s * 0.32, x + s * 0.8, y + s * 0.68, s * 0.08, "#ffffff", 0.97)
    circ(c, x + s * 0.5, y + s * 0.5, s * 0.1, fill="#d3112b", line=None)


def spinner(c, cx, cy, r, T, col="#ffffff"):
    for k in range(12):
        a = 2 * math.pi * k / 12 - math.pi / 2; ph = ((T * 10 - k) % 12) / 12.0
        line(c, cx + math.cos(a) * r * 0.55, cy + math.sin(a) * r * 0.55, cx + math.cos(a) * r, cy + math.sin(a) * r, r * 0.16, col, 0.12 + 0.88 * (1 - ph))


BN = [(T_BUZZ1, "Bedroom camera", "bed"), (T_BUZZ2, "Stairs camera", "stairs"), (T_BUZZ3, "Hallway camera", "hall"), (T_BUZZ4, "Camera 4  ·  Kitchen", "cam4")]
HE, HC = 640, 168


def snap_view(c, T, kind, x, y, w, h):
    """a snapshot thumbnail (night-vision still) of one camera, cropped around its subject"""
    c.save(); c.clipRRect(skia.RRect.MakeRectXY(skia.Rect(x, y, x + w, y + h), 22, 22), skia.ClipOp.kIntersect, True)
    focus = {"bed": (540, 880, 0.86), "stairs": (540, 700, 1.0), "hall": (540, 560, 0.95)}[kind]
    c.translate(x + w / 2, y + h / 2); c.scale(focus[2], focus[2]); c.translate(-focus[0], -focus[1])
    if kind == "bed": bedroom_view(c, 0.0, fig=False)
    elif kind == "stairs": stairs_view(c, T, True, 0.0)
    else: hall_view(c, T, True, 0.55)
    c.restore()
    c.save(); c.clipRRect(skia.RRect.MakeRectXY(skia.Rect(x, y, x + w, y + h), 22, 22), skia.ClipOp.kIntersect, True)
    p = skia.Paint(); p.setAlphaf(0.10); c.drawImageRect(noise_img(T * 0.3), skia.Rect(x, y, x + w, y + h), skia.SamplingOptions(skia.FilterMode.kLinear), p)
    for yy in range(int(y), int(y + h), 5): c.drawRect(skia.Rect(x, yy, x + w, yy + 2), paint("#000000", 0.18))
    txt(c, "03:12:%02d" % (41 + int(T) % 18), x + 18, y + h - 16, "mono", 26, NV6, 0.9)
    rr(c, x + w - 140, y + 14, x + w - 16, y + 52, 10, "#e0252b", 0.92); txt(c, "MOTION", x + w - 78, y + 42, "bold", 22, "#ffffff", 1.0, "c")
    c.restore()


def banner(c, T, i, y, h, expand, app):
    x0, x1 = 60, 1020; a = cl(app * 2.5)
    rr(c, x0, y, x1, y + h, 46, "#1d1f26", 0.93 * a); rr(c, x0, y, x1, y + h, 46, "#ffffff", 0.07 * a, 2)
    app_icon(c, x0 + 28, y + 26, 66)
    txt(c, "HOMEEYE", x0 + 120, y + 70, "med", 29, "#9ea3b0", a)
    txt(c, "now", x1 - 34, y + 70, "reg", 29, "#9ea3b0", a, "r")
    t_s = BN[i][0]
    txt(c, "Motion detected", x0 + 30, y + 128, "bold", 45, "#ffffff", a)
    sub = BN[i][1]; txt(c, sub, x0 + 30, y + 168 - 4 * (1 - expand), "reg", 36, "#c4c8d4", a)
    if expand > 0.04 and h > 330:
        sy = y + 196; sh = h - 196 - 26; sx = x0 + 26; sw = (x1 - x0) - 52
        c.save(); c.saveLayerAlpha(None, int(255 * cl(expand * a))) if False else None
        if BN[i][2] == "cam4":
            rr(c, sx, sy, sx + sw, sy + sh, 22, "#2a2d36", a)
            spinner(c, sx + sw / 2, sy + sh / 2 - 10, 34, T, "#cfd3de"); txt(c, "Loading snapshot…", sx + sw / 2, sy + sh / 2 + 80, "med", 28, "#9ea3b0", a, "c")
        else: snap_view(c, T, BN[i][2], sx, sy, sw, sh)
        c.restore()
        if expand < 0.98: rr(c, x0 + 6, y + 190, x1 - 6, y + h, 40, "#1d1f26", 0.93 * (1 - expand) * a)


def lock_screen(c, T):
    vgrad(c, 0, 0, W, H, "#06070d", "#0c1020")
    glow(c, 540, 1100, 900, "#2b3f78", 0.16, add=False)
    nb = sum(1 for b in BN if T >= b[0])
    clk = e_io(prog(T, BN[1][0], BN[1][0] + 0.65)) if T > CUT_L2 - 0.5 else 0.0
    cy = lerp(385, 235, clk); sz = lerp(260, 150, clk)
    date_y = lerp(235, 135, clk)
    status_bar(c, T)
    txt(c, "Sunday, November 22", 540, date_y, "med", lerp(44, 34, clk), "#ffffff", 0.8, "c")
    flick = 1.0 if T > 0.6 else (0.55 if hsh(int(T * 30), 6) > 0.45 else 1.0)
    mins = 12 if T < 20 else 13
    s = "3:%02d" % mins; f = fnt("light", sz); wd = f.measureText(s)
    if T < 0.9:
        c.drawString(s, 540 - wd / 2 - 7, cy + sz * 0.36, f, paint("#00ffe0", 0.30 * (1 - T / 0.9)))
        c.drawString(s, 540 - wd / 2 + 7, cy + sz * 0.36, f, paint("#ff2b6a", 0.30 * (1 - T / 0.9)))
    c.drawString(s, 540 - wd / 2, cy + sz * 0.36, f, paint("#ffffff", 0.93 * flick))
    # notification stack
    Ytop = lerp(570, 330, clk)
    vis = [i for i, b in enumerate(BN) if T >= b[0] - 0.01][::-1][:3]
    y = Ytop
    for idx, i in enumerate(vis):
        t_i = BN[i][0]; app = e_out(prog(T, t_i, t_i + 0.45))
        newer = BN[i + 1][0] if i + 1 < len(BN) else None
        col = e_io(prog(T, newer, newer + 0.5)) if newer is not None else 0.0
        hh = lerp(HE, HC, col)
        off = -(hh + 220) * (1 - app) if idx == 0 else 0.0
        banner(c, T, i, y + off, hh, 1 - col, app)
        y += (hh + 16) * (app if idx == 0 else 1.0)
    # bottom of lock screen
    circ(c, 150, 1720, 52, fill="#ffffff", line=None, alpha=0.10); circ(c, 930, 1720, 52, fill="#ffffff", line=None, alpha=0.10)


def camera_chrome(c, T, label, live=True, cam="CAM 1"):
    p = skia.Paint(); p.setShader(skia.GradientShader.MakeLinear([(0, 0), (0, 250)], [C("#000000", 0.85), C("#000000", 0.0)], [0, 1])); c.drawRect(skia.Rect(0, 0, W, 250), p)
    status_bar(c, T, "3:%02d" % (12 + (1 if T > 19 else 0)))
    txt(c, "‹", 62, 188, "med", 74, "#ffffff", 0.95); txt(c, label, 130, 182, "bold", 46, "#ffffff", 0.97)
    if live:
        rr(c, 790, 144, 1010, 200, 28, "#000000", 0.55); circ(c, 828, 172, 9, fill="#ff2b2b", line=None, alpha=0.6 + 0.4 * (1 if int(T * 1.6) % 2 == 0 else 0))
        txt(c, "LIVE", 852, 186, "bold", 36, "#ffffff", 0.97)
    txt(c, cam + "  ·  " + label.upper(), 56, 1262, "mono", 32, NV7, 0.9)
    txt(c, "11-22-2026   " + stamp_time(T), 1030, 1262, "mono", 32, NV7, 0.9, "r")
    circ(c, 70, 292, 11, fill="#ff2b2b", line=None, alpha=1.0 if int(T * 1.4) % 2 == 0 else 0.15); txt(c, "REC", 96, 304, "mono", 30, "#ff6b6b", 0.9)


def feed_fx(c, T, glitch=0.0, nz=0.16):
    vignette(c, 0.80, 800, 1150)
    scanlines(c, 0.16)
    p = skia.Paint(); p.setAlphaf(nz); c.drawImageRect(noise_img(T), FULL, skia.SamplingOptions(skia.FilterMode.kLinear), p)
    c.drawRect(FULL, paint("#33ff66", 0.045))
    tear(c, T, glitch)
    static_fill(c, T, 0.5 * glitch * glitch)


def spin_deg(T):
    """head yaw: stutters (jerky 6 fps) while it turns"""
    q = math.floor(T * 6.0) / 6.0
    keys = [(T_TURNED + 0.35, 0.0), (T_SLOWLY + 0.1, 58.0), (T_UNTIL + 0.15, 66.0), (T_CAMERA - 0.55, 128.0), (T_CAMERA - 0.12, 150.0), (T_CAMERA, 180.0)]
    if T < keys[0][0]: return 0.0
    qt = q if T < T_CAMERA - 0.15 else T
    return keyed(keys, max(qt, keys[0][0]))


def feed_shot(c, T):
    """full-screen bedroom feed: empty bed -> something sitting -> turns -> smiles"""
    # camera glitch events
    gl = glitch_amt(T, [(T_SOMETHING - 0.20, 0.45, 1.0), (T_TURNED - 0.05, 0.12, 0.5), (T_CAMERA - 0.06, 0.40, 1.0), (T_SMILED - 0.02, 0.22, 0.6), (T_WIDE - 0.04, 0.28, 0.6), (T_FEED, 0.35, 0.9), (CUT_L2 - 0.18, 0.2, 1.0)])
    zf = keyed([(T_FEED, 1.0), (T_SOMETHING + 3.0, 1.05), (T_TURNED, 1.08), (T_CAMERA, 1.42), (T_SMILED, 1.50), (T_WIDE + 0.6, 1.86)], T)
    fy = keyed([(T_FEED, 960), (T_TURNED, 880), (T_CAMERA, 740), (T_WIDE + 0.6, 705)], T)
    fig = T >= T_SOMETHING
    psi = spin_deg(T); roll = keyed([(T_TURNED, 0.0), (T_CAMERA, -5.0), (T_WIDE, -13.0)], T)
    smile = keyed([(T_SMILED - 0.1, 0.0), (T_SMILED + 0.7, 0.55), (T_WIDE, 0.62), (T_WIDE + 0.55, 1.0)], T)
    wide = keyed([(T_TOO - 0.05, 0.0), (T_WIDE + 0.6, 1.0)], T)
    hd = keyed([(T_TURNED, 0.0), (T_CAMERA, 0.55), (T_WIDE, 1.0)], T)
    jit = 1.0 if T > T_STILL else 0.0
    sh_x = 0.0
    if gl > 0.3: sh_x = 14 * (hsh(int(T * 30), 3) - 0.5) * gl
    c.save(); c.translate(540 + sh_x, fy); c.scale(zf, zf); c.translate(-540, -fy)
    bedroom_view(c, T, fig=fig, psi=psi, roll=roll, smile=smile, wide=wide, hd=hd, jit=jit)
    c.restore()
    camera_chrome(c, T, "Bedroom", True, "CAM 1")
    feed_fx(c, T, gl, 0.16 + 0.1 * gl)
    if T_FEED - 0.05 < T < T_FEED + 0.5: c.drawRect(FULL, paint("#ffffff", 0.35 * (1 - prog(T, T_FEED, T_FEED + 0.5))))
    if T_SOMETHING - 0.05 < T < T_SOMETHING + 0.07: c.drawRect(FULL, paint(NV7, 0.55))


def app_loading(c, T):
    c.drawRect(FULL, paint("#000000"))
    vgrad(c, 0, 0, W, H, "#05070b", "#0a0f16")
    status_bar(c, T, "3:12")
    txt(c, "‹", 62, 188, "med", 74, "#ffffff", 0.95); txt(c, "Bedroom", 130, 182, "bold", 46, "#ffffff", 0.97)
    spinner(c, 540, 820, 54, T, "#ffffff"); txt(c, "Connecting to camera…", 540, 960, "med", 38, "#aab0bf", 0.9, "c")
    pass
    vignette(c, 0.6, 900, 1300)


def camera_grid(c, T):
    vgrad(c, 0, 0, W, H, "#05070b", "#0a0f16")
    status_bar(c, T, "3:13")
    txt(c, "My cameras", 60, 190, "bold", 60, "#ffffff", 0.97)
    tiles = [("Bedroom", "bed", 250), ("Stairs", "stairs", 538), ("Hallway", "hall", 826)]
    for (nm, kind, y0) in tiles:
        x0, w, h = 60, 960, 272
        c.save(); c.clipRRect(skia.RRect.MakeRectXY(skia.Rect(x0, y0, x0 + w, y0 + h), 26, 26), skia.ClipOp.kIntersect, True)
        focus = {"bed": (540, 900, 0.88), "stairs": (540, 880, 0.88), "hall": (540, 900, 0.88)}[kind]
        c.translate(x0 + w / 2, y0 + h / 2); c.scale(focus[2], focus[2]); c.translate(-focus[0], -focus[1])
        if kind == "bed": bedroom_view(c, T, fig=False)
        elif kind == "stairs": stairs_view(c, T, False)
        else: hall_view(c, T, False)
        c.restore()
        c.save(); c.clipRRect(skia.RRect.MakeRectXY(skia.Rect(x0, y0, x0 + w, y0 + h), 26, 26), skia.ClipOp.kIntersect, True)
        for yy in range(int(y0), int(y0 + h), 5): c.drawRect(skia.Rect(x0, yy, x0 + w, yy + 2), paint("#000000", 0.2))
        c.drawRect(skia.Rect(x0, y0, x0 + w, y0 + h), paint("#000000", 0.25))
        rr(c, x0 + 20, y0 + 20, x0 + 20 + 52 + 20 * len(nm), y0 + 68, 24, "#000000", 0.6); circ(c, x0 + 44, y0 + 44, 7, fill="#7bff8a", line=None)
        txt(c, nm, x0 + 62, y0 + 54, "bold", 28, "#ffffff", 0.95)
        c.restore()
        hit = prog(T, T_THREE - 0.05, T_THREE + 0.25)
        if hit > 0:
            idx = tiles.index((nm, kind, y0)) + 1
            if T >= T_THREE + 0.12 * (idx - 1) - 0.05: circ(c, x0 + w - 48, y0 + 46, 28, fill="#ffffff", line=None, alpha=0.9); txt(c, str(idx), x0 + w - 48, y0 + 58, "bold", 34, "#000000", 1.0, "c")
    # the fourth one
    k = e_out(prog(T, T_CAMS - 0.10, T_CAMS + 0.28))
    if k > 0.01:
        y0 = 1114 + (1 - k) * 700; x0, w, h = 60, 960, 272
        sh = 10 * math.sin(T * 70) * (1 - k) if k < 1 else 3 * math.sin(T * 55)
        c.save(); c.translate(sh, 0); c.clipRRect(skia.RRect.MakeRectXY(skia.Rect(x0, y0, x0 + w, y0 + h), 26, 26), skia.ClipOp.kIntersect, True)
        c.translate(x0 + w / 2, y0 + h / 2 + 60); c.scale(0.86, 0.86); c.translate(-440, -880)
        kitchen_cam_view(c, T, 0.0)
        c.restore()
        c.save(); c.translate(sh, 0)
        rr(c, x0, y0, x0 + w, y0 + h, 26, "#ff2b2b", 0.9, 6)
        rr(c, x0 + 20, y0 + 20, x0 + 20 + 330, y0 + 68, 24, "#e0252b", 0.95); txt(c, "Camera 4  ·  Kitchen", x0 + 38, y0 + 54, "bold", 28, "#ffffff", 1.0)
        c.restore()
    vignette(c, 0.5, 900, 1300)


def cam4_full(c, T):
    t = T - CUT_CAM4
    zk = e_out(prog(T, CUT_CAM4, CUT_CAM4 + 0.28))
    lean = keyed([(CUT_CAM4, 0.0), (T_FINAL - 0.2, 1.0)], T)
    z = lerp(0.78, 1.0, zk) + 0.05 * prog(T, CUT_CAM4 + 0.3, T_FINAL)
    gl = glitch_amt(T, [(CUT_CAM4, 0.18, 0.8), (T_FINAL - 0.34, 0.34, 1.0)])
    c.save(); c.translate(540, 760); c.scale(z, z); c.translate(-540, -760)
    kitchen_cam_view(c, T, lean)
    c.restore()
    camera_chrome(c, T, "Kitchen", True, "CAM 4")
    feed_fx(c, T, gl, 0.20)
    if T > T_FINAL - 0.02: c.drawRect(FULL, paint(NV7, 0.6 * (1 - prog(T, T_FINAL - 0.02, T_FINAL + 0.1))))


# ------------------------------------------------------------------ captions (same style as the engine's other horror short)
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
def buzz_shake(T):
    for t0 in (T_BUZZ1, T_BUZZ2, T_BUZZ3, T_BUZZ4):
        for off in (0.0, 0.26):
            d = T - (t0 + off)
            if 0 <= d < 0.20: return 9 * math.sin(d * 2 * math.pi * 34) * (1 - d / 0.20)
    return 0.0


def frame(c, T):
    T = max(0.0, min(T, TOTAL - 0.001))
    c.drawRect(FULL, paint("#000000"))
    if T < CUT_K:
        c.save(); c.translate(buzz_shake(T), 0); lock_screen(c, T); c.restore()
    elif T < T_APP_IN:
        kitchen_scene(c, T)
    elif T < T_FEED:
        app_loading(c, T)
    elif T < CUT_L2:
        feed_shot(c, T)
    elif T < CUT_GRID:
        c.save(); c.translate(buzz_shake(T), 0); lock_screen(c, T); c.restore()
    elif T < CUT_CAM4:
        camera_grid(c, T)
    elif T < T_FINAL:
        cam4_full(c, T)
    else:
        c.drawRect(FULL, paint("#000000"))
    # hard-cut dips + final black
    for tc in (CUT_K, T_APP_IN, T_FEED, CUT_L2, CUT_GRID, CUT_CAM4):
        dt = T - tc
        if 0.0 <= dt < 0.08: c.drawRect(FULL, paint("#000000", 1.0 - dt / 0.08))
    if T < T_FINAL: caps(c, T)


# ------------------------------------------------------------------ sound design
def _noise(n): return sfx.rng.standard_normal(n).astype(np.float32)


def buzz_phone(vol=0.8):
    SR = sfx.SR; out = np.zeros(int(SR * 0.62), np.float32)
    for off in (0.0, 0.26):
        n = int(SR * 0.19); t = np.arange(n) / SR
        s = (np.sign(np.sin(2 * np.pi * 148 * t)) * 0.55 + np.sin(2 * np.pi * 148 * t) * 0.6) * (1 - np.exp(-t * 500)) * np.exp(-np.maximum(t - 0.13, 0) * 70)
        s = s + sfx._ma(_noise(n), 24) * 5.0 * np.exp(-t * 14)
        s = s + np.sin(2 * np.pi * 62 * t) * 0.8 * np.exp(-t * 22)
        i0 = int(off * SR); out[i0:i0 + n] += s.astype(np.float32)
    return (out * vol).astype(np.float32)


def static_burst(dur=0.34, vol=0.55):
    SR = sfx.SR; n = int(SR * dur); x = _noise(n)
    gate = np.repeat((np.random.RandomState(5).rand(int(dur * 60) + 2) > 0.32), int(SR / 60) + 1)[:n].astype(np.float32)
    env = np.exp(-np.arange(n) / SR * 4.5); hp = x - sfx._ma(x, 12)
    return (hp * gate * env * vol).astype(np.float32)


def drip(vol=0.5):
    SR = sfx.SR; n = int(SR * 0.3); t = np.arange(n) / SR
    f = 520 + 1500 * np.exp(-t * 20); s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 20)
    return (s * vol).astype(np.float32)


def drone_swell(dur=2.6, vol=0.5):
    SR = sfx.SR; n = int(SR * dur); t = np.arange(n) / SR; k = t / dur
    s = np.sin(2 * np.pi * 55 * t) * 0.8 + np.sin(2 * np.pi * 58.3 * t) * 0.8 + np.sin(2 * np.pi * (110 + 30 * k) * t) * 0.3 * k
    return (s * (k ** 2.2) * np.minimum(1, (dur - t) / 0.05 + 0.0) * vol).astype(np.float32)


sfx.LIB.update({"buzz": lambda: buzz_phone(), "static": lambda: static_burst(), "drip": lambda: drip(), "swell": lambda: drone_swell(), "swell_l": lambda: drone_swell(3.4, 0.55)})
sfx.GAIN.update({"buzz": 0.6, "static": 0.4, "drip": 0.5, "swell": 0.8, "swell_l": 0.8})
sfx.DRY.add("static")

CUES = [("buzz", T_BUZZ1), ("buzz", T_BUZZ2), ("buzz", T_BUZZ3), ("buzz", T_BUZZ4),
        ("thud", CUT_K), ("drip", CUT_K + 0.75), ("drip", CUT_K + 2.5), ("drip", CUT_K + 4.2), ("click", T_OPENED), ("beep", T_FEED - 0.05), ("whoosh", T_APP_IN),
        ("static", T_SOMETHING - 0.2), ("thud_lo", T_SOMETHING), ("riser_s", T_STILL),
        ("creak", T_TURNED + 0.25), ("creak", T_SLOWLY + 0.1), ("creak", T_UNTIL + 0.4),
        ("static", T_CAMERA - 0.06), ("thud_lo", T_CAMERA), ("riser", T_SMILED - 0.3), ("static", T_WIDE - 0.05), ("sting", T_WIDE + 0.02),
        ("thud", CUT_L2), ("click", CUT_GRID),
        ("creak", T_BUZZ2 + 1.1), ("thud_lo", T_BUZZ2 + 1.45), ("creak", T_BUZZ2 + 1.9), ("thud_lo", T_BUZZ2 + 2.35),
        ("creak", T_BUZZ3 + 0.7), ("thud_lo", T_BUZZ3 + 1.05), ("thud_lo", T_BUZZ3 + 1.5), ("thud_lo", T_BUZZ3 + 1.9),
        ("swell_l", CUT_GRID - 0.2), ("whoosh", CUT_CAM4), ("static", CUT_CAM4 - 0.04), ("static", T_FINAL - 0.34), ("sting", T_FINAL - 0.02), ("thud_lo", T_FINAL - 0.02), ("thud_lo", T_FINAL + 0.04)]
_t = T_TURNED - 0.2
while _t < T_WIDE + 0.5:
    _bpm = lerp(58, 112, prog(_t, T_TURNED - 0.2, T_WIDE)); CUES.append(("heart", _t)); _t += 60.0 / _bpm
_t = T_BUZZ4 + 0.9
while _t < T_FINAL - 0.3:
    _bpm = lerp(70, 132, prog(_t, T_BUZZ4, T_FINAL)); CUES.append(("heart", _t)); _t += 60.0 / _bpm


def MUSIC(mix, total, add):
    pass                                                    # the generated score is mixed on afterwards (see the README)


def VOICE_FX(v):
    return sfx.reverb(v, wet=0.17, rt=1.1)


RENDER = dict(nsub=3, shutter=0.5, crf=21)
MASTER = dict(pre="acompressor=threshold=0.25:ratio=2:attack=20:release=250:makeup=1", I=-19.0, TP=-1.5)
