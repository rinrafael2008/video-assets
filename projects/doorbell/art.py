"""Doorbell: everything drawn in code. Phone chat UI + lock screen, the doorbell-camera feed (porch, woman), the bedroom door.
Skia + numpy + cv2 only. Reuses helpers/post-FX from projects/peephole/dark.py.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "peephole"))
from dark import *          # noqa: W, H, FPS, cl, lerp, prog, e_out, e_io, e_back, decay, paint, quad, glow, vgrad, font, text, ANTON, POP, post, skia, np, cv2, math, random
import dark

PM = "/usr/share/fonts/truetype/google-fonts/Poppins-Medium.ttf"
PB = POP


def rrect(c, x0, y0, x1, y1, r, rgb, a=1.0, **kw):
    c.drawRoundRect(skia.Rect(x0, y0, x1, y1), r, r, paint(rgb, a, **kw))


def tl(c, s, x, y, size, rgb=(255, 255, 255), a=1.0, fnt=PM):      # left aligned, y = visual centre
    c.drawString(s, x, y + size * 0.36, font(fnt, size), paint(rgb, a))


def tr(c, s, x, y, size, rgb=(255, 255, 255), a=1.0, fnt=PM):      # right aligned
    f = font(fnt, size); c.drawString(s, x - f.measureText(s), y + size * 0.36, f, paint(rgb, a))


def tc(c, s, x, y, size, rgb=(255, 255, 255), a=1.0, fnt=PM):
    f = font(fnt, size); c.drawString(s, x - f.measureText(s) / 2, y + size * 0.36, f, paint(rgb, a))


# =============================================================== phone UI
def status_bar(c, clock="2:14", batt=0.11, tint=(255, 255, 255)):
    tl(c, clock, 66, 62, 38, tint, 1.0, PB)
    for i, hh in enumerate((10, 16, 22, 28)):                       # signal bars
        c.drawRect(skia.Rect(780 + i * 14, 76 - hh, 780 + i * 14 + 9, 76), paint(tint, 0.9 if i < 3 else 0.35))
    rrect(c, 900, 46, 968, 80, 9, tint, 0.9, stroke=3)
    rrect(c, 906, 52, 906 + 56 * batt, 74, 5, (235, 60, 60), 1.0)
    c.drawRect(skia.Rect(970, 55, 975, 71), paint(tint, 0.9))
    tr(c, f"{int(batt * 100)}%", 886, 62, 32, (235, 60, 60), 1.0, PB)


def draw_lock(c, t, shake=0.0, n2=0.0, ring=0.0):
    ox = shake * math.sin(t * 95); oy = shake * 0.6 * math.cos(t * 83)
    c.save(); c.translate(ox, oy)
    vgrad(c, -40, -40, W + 40, H + 40, (14, 20, 42), (3, 4, 10))
    glow(c, 820, 360, 620, (60, 90, 190), 0.18); glow(c, 160, 1500, 760, (90, 60, 160), 0.10)
    for i in range(14):                                              # soft bokeh
        gr = random.Random(i * 7 + 3)
        c.drawCircle(gr.random() * W, 300 + gr.random() * 1300, 40 + gr.random() * 90, paint((120, 150, 255), 0.025 + 0.02 * gr.random()))
    status_bar(c, "2:14", 0.11)
    tc(c, "2:14", W / 2, 420, 250, (240, 244, 255), 0.96, PB)
    # notification card
    y0, y1 = 700, 1010
    rrect(c, 56, y0, W - 56, y1, 54, (38, 40, 56), 0.88)
    rrect(c, 56, y0, W - 56, y1, 54, (255, 255, 255), 0.22, stroke=3)
    c.drawCircle(150, y0 + 100, 52, paint((236, 118, 142)))
    tc(c, "M", 150, y0 + 100, 56, (255, 255, 255), 1.0, PB)
    tl(c, "Mom", 232, y0 + 72, 50, (255, 255, 255), 1.0, PB)
    tr(c, "now", W - 100, y0 + 72, 34, (190, 196, 220), 0.9)
    tl(c, "I'm outside.", 232, y0 + 150, 52, (255, 255, 255), 1.0, PM)
    tl(c, "Open the door.", 232, y0 + 218, 52, (255, 255, 255), 1.0, PM)
    if ring > 0: rrect(c, 46, y0 - 10, W - 46, y1 + 10, 62, (255, 214, 90), ring * (0.6 + 0.4 * math.sin(t * 10)), stroke=8)
    if n2 > 0:
        yy = 1050 + (1 - e_back(n2, 1.4)) * 80
        rrect(c, 56, yy, W - 56, yy + 210, 54, (38, 40, 56), 0.88 * n2); rrect(c, 56, yy, W - 56, yy + 210, 54, (255, 255, 255), 0.22 * n2, stroke=3)
        c.drawCircle(150, yy + 70, 46, paint((236, 118, 142), n2)); tc(c, 'M', 150, yy + 70, 50, (255, 255, 255), n2, PB)
        tl(c, 'Mom', 232, yy + 52, 46, (255, 255, 255), n2, PB); tl(c, "Hurry up, it's freezing!", 232, yy + 128, 50, (255, 255, 255), n2, PM)
    for x, ic in ((120, "flash"), (W - 120, "cam")):                  # lock-screen shortcuts
        c.drawCircle(x, 1700, 62, paint((255, 255, 255), 0.13))
    rrect(c, W / 2 - 180, 1840, W / 2 + 180, 1850, 5, (255, 255, 255), 0.5)
    c.restore()


class M:
    def __init__(self, side, text, t, ts=""):
        self.side, self.text, self.t, self.ts = side, text, t, ts
        self.lines = _wrap(text, 50, 660)
        f = font(PM, 50)
        self.w = max(f.measureText(l) for l in self.lines) + 66
        self.h = len(self.lines) * 66 + 44


def _wrap(s, size, maxw):
    f = font(PM, size); words = s.split(" "); out = []; cur = ""
    for w in words:
        tst = (cur + " " + w).strip()
        if f.measureText(tst) <= maxw or not cur: cur = tst
        else: out.append(cur); cur = w
    if cur: out.append(cur)
    return out


CH_BG = ((17, 18, 25), (9, 10, 14)); RECV = (44, 46, 58); SENT = (58, 110, 242)
BASE = 1285


def draw_chat(c, t, msgs, dots=(), typed="", cursor=True, send_k=0.0, hl=None, hl_k=0.0, shake=0.0, dim=0.0):
    ox = shake * math.sin(t * 95); oy = shake * 0.6 * math.cos(t * 83)
    c.save(); c.translate(ox, oy)
    vgrad(c, -40, -40, W + 40, H + 40, CH_BG[0], CH_BG[1])
    # stack (bottom aligned, earlier messages are pushed up smoothly)
    items = []
    for m in sorted(msgs, key=lambda m: m.t): items.append(("m", m, e_out(prog(t, m.t, m.t + 0.26)), m.t))
    for (a, b) in dots:
        if a <= t < b: items.append(("d", None, e_out(prog(t, a, a + 0.2)), a))
    items.sort(key=lambda x: x[3])
    ycur = BASE
    for kind, m, pr, _ in reversed(items):
        if pr <= 0.001: continue
        h = (m.h if kind == "m" else 100); GAP = 36
        yb = ycur; yt = yb - h
        ycur -= (h + GAP) * pr
        yt_d = yt + (1 - pr) * 40
        side = m.side if kind == "m" else "r"
        w = m.w if kind == "m" else 190
        x0 = 48 if side == "r" else W - 48 - w
        c.save(); c.translate((x0 + w / 2), (yt_d + h / 2)); sc = 0.88 + 0.12 * pr; c.scale(sc, sc); c.translate(-(x0 + w / 2), -(yt_d + h / 2))
        col = RECV if side == "r" else SENT
        rrect(c, x0, yt_d, x0 + w, yt_d + h, 44, col, pr)
        if kind == "m":
            if hl is m and hl_k > 0:
                rrect(c, x0 - 8, yt_d - 8, x0 + w + 8, yt_d + h + 8, 50, (255, 214, 90), hl_k * (0.55 + 0.45 * math.sin(t * 9)), stroke=7)
            for i, ln in enumerate(m.lines): tl(c, ln, x0 + 33, yt_d + 22 + 33 + i * 66, 50, (255, 255, 255), pr)
            if m.ts: tl(c, m.ts, x0 + (6 if side == "r" else w - 6 - font(PM, 26).measureText(m.ts)), yt_d + h + 22, 26, (135, 141, 165), pr * 0.9)
        else:
            for i in range(3):
                ph = (t * 3.2 - i * 0.28)
                dy = -14 * max(0.0, math.sin(ph * math.pi)) if ph > 0 else 0
                c.drawCircle(x0 + 52 + i * 43, yt_d + h / 2 + dy, 12, paint((190, 196, 220), 0.55 + 0.4 * (i == int(t * 3.2) % 3)))
        c.restore()
    # header
    c.drawRect(skia.Rect(-40, -40, W + 40, 270), paint((24, 25, 34)))
    c.drawRect(skia.Rect(-40, 268, W + 40, 272), paint((0, 0, 0), 0.35))
    status_bar(c, "2:14", 0.11)
    p = skia.Path(); p.moveTo(94, 152); p.lineTo(62, 190); p.lineTo(94, 228)
    c.drawPath(p, paint((120, 160, 255), 1.0, stroke=9))
    c.drawCircle(190, 190, 46, paint((236, 118, 142))); tc(c, "M", 190, 190, 52, (255, 255, 255), 1.0, PB)
    tl(c, "Mom", 258, 172, 50, (255, 255, 255), 1.0, PB)
    tl(c, "Messages", 258, 220, 30, (150, 156, 180), 1.0)
    # input bar
    rrect(c, 28, 1332, W - 28, 1434, 51, (30, 31, 41), 1.0)
    if typed:
        tl(c, typed + ("|" if cursor and int(t * 2.6) % 2 == 0 else ""), 70, 1383, 44, (255, 255, 255), 1.0)
    else: tl(c, "Message", 70, 1383, 44, (110, 116, 140), 1.0)
    c.drawCircle(W - 90, 1383, 36, paint((58, 110, 242) if (typed or send_k > 0) else (50, 54, 72)))
    q = skia.Path(); q.moveTo(W - 104, 1396); q.lineTo(W - 90, 1366); q.lineTo(W - 76, 1396)
    c.drawPath(q, paint((255, 255, 255), 0.95, stroke=7))
    if dim > 0: c.drawRect(skia.Rect(-40, -40, W + 40, H + 40), paint((0, 0, 0), dim))
    c.restore()


# =============================================================== doorbell camera: porch + woman
FW, FH = 540, 960
_FSURF = skia.Surface(FW, FH)
_u, _v = np.meshgrid(np.arange(FW, dtype=np.float32), np.arange(FH, dtype=np.float32))
_cx, _cy = FW / 2, FH / 2; _R = math.hypot(_cx, _cy)
_dx, _dy = (_u - _cx) / _R, (_v - _cy) / _R
_k = 0.30; _r2 = _dx * _dx + _dy * _dy
_MAPX = (_cx + _dx * _R / (1 + _k * _r2)).astype(np.float32); _MAPY = (_cy + _dy * _R / (1 + _k * _r2)).astype(np.float32)


def _skin_shader(y0, y1, a, b):
    return skia.GradientShader.MakeLinear([(0, y0), (0, y1)], [ci(*a), ci(*b)])


def draw_woman(c, t, x, y, sc, smile=0.0, scare=0.0, mouth=None, wave=0.0, breath=0.0):
    """(x,y) = base of the neck, sc = scale. mouth = (w, h, teeth) overrides the smile (lip-sync of RUN)."""
    c.save(); c.translate(x, y + math.sin(t * 2.0) * 1.5 * (1 + 3 * breath)); c.scale(sc, sc)
    HAIR = (34, 26, 26); SK0 = (236, 218, 206); SK1 = (184, 156, 144)
    # hair behind head and shoulders
    p = skia.Path(); p.moveTo(-104, -130); p.cubicTo(-114, -262, -60, -314, 0, -316); p.cubicTo(60, -314, 114, -262, 104, -130); p.cubicTo(114, -70, 122, -10, 134, 30); p.cubicTo(90, 46, -90, 46, -134, 30); p.cubicTo(-122, -10, -114, -70, -104, -130); p.close()
    c.drawPath(p, paint(HAIR))
    # robe
    r = skia.Path(); r.moveTo(-270, 700); r.cubicTo(-270, 170, -150, 44, -42, 12); r.lineTo(42, 12); r.cubicTo(150, 44, 270, 170, 270, 700); r.close()
    c.drawPath(r, paint(shader=skia.GradientShader.MakeLinear([(0, 0), (0, 500)], [ci(150, 154, 162), ci(78, 82, 90)])))
    c.drawPath(r, paint((255, 255, 255), 0.18, stroke=4))
    # neck + chest
    c.drawRect(skia.Rect(-27, -50, 27, 22), paint((158, 134, 122)))
    v = skia.Path(); v.moveTo(-60, 14); v.lineTo(0, 150); v.lineTo(60, 14); v.close(); c.drawPath(v, paint((190, 164, 150)))
    for sx in (-1, 1):
        l = skia.Path(); l.moveTo(sx * 40, 8); l.lineTo(0, 164); l.lineTo(sx * 18, 168); l.lineTo(sx * 92, 20); l.close()
        c.drawPath(l, paint((190, 194, 202))); c.drawPath(l, paint((60, 64, 72), 0.5, stroke=3))
    c.drawRoundRect(skia.Rect(-80, 168, 80, 190), 10, 10, paint((70, 74, 84), 0.55))
    # face
    face = skia.Rect(-74, -228, 74, -34)
    c.drawOval(face, paint(shader=_skin_shader(-228, -34, SK0, SK1)))
    c.save(); c.clipRRect(skia.RRect.MakeOval(face))
    c.drawOval(skia.Rect(-160, -120, -50, 40), paint((60, 40, 36), 0.30, blur=18)); c.drawOval(skia.Rect(50, -120, 160, 40), paint((60, 40, 36), 0.30, blur=18))
    vgrad(c, -80, -100, 80, -30, (0, 0, 0), (30, 12, 10), 0.0, 0.42)
    c.restore()
    c.drawOval(skia.Rect(-62, -52, 62, -16), paint((40, 24, 22), 0.30, blur=10))     # jaw shadow on the neck
    # fringe
    f = skia.Path(); f.moveTo(-84, -140); f.cubicTo(-90, -272, 90, -272, 84, -140); f.cubicTo(72, -204, 30, -224, -10, -226); f.cubicTo(-44, -226, -72, -194, -84, -140); f.close()
    c.drawPath(f, paint(HAIR))
    for sx in (-1, 1):
        s = skia.Path(); s.moveTo(sx * 90, -150); s.cubicTo(sx * 124, -92, sx * 132, -20, sx * 130, 30); s.lineTo(sx * 86, 30); s.cubicTo(sx * 88, -28, sx * 80, -70, sx * 74, -120); s.close()
        c.drawPath(s, paint(HAIR)); c.drawPath(s, paint((90, 80, 80), 0.35, stroke=3))
    # eyes
    open_h = 15 + 12 * scare - 4 * smile
    for sx in (-1, 1):
        ex, ey = sx * 31, -138
        c.drawOval(skia.Rect(ex - 18, ey - open_h / 2 - 1, ex + 18, ey + open_h / 2 + 1), paint((242, 238, 234)))
        c.drawCircle(ex, ey, 8.6 + 1.2 * scare, paint((40, 32, 30))); c.drawCircle(ex, ey, 4.2, paint((4, 4, 4)))
        c.drawCircle(ex - 3, ey - 3, 2.2, paint((255, 255, 255)))
        lid = skia.Path(); lid.moveTo(ex - 19, ey + 1); lid.quadTo(ex, ey - open_h / 2 - 8, ex + 19, ey + 1)
        c.drawPath(lid, paint((46, 30, 28), 1.0, stroke=3.4))
        low = skia.Path(); low.moveTo(ex - 16, ey + open_h / 2 + 1); low.quadTo(ex, ey + open_h / 2 + 5, ex + 16, ey + open_h / 2 + 1)
        c.drawPath(low, paint((120, 90, 84), 0.5, stroke=2))
        by = -171 - 7 * scare
        br = skia.Path(); br.moveTo(ex + sx * 23, by + 7 + 2 * scare); br.quadTo(ex, by - 5 - 3 * scare, ex - sx * 20, by + 4 - 18 * scare)
        c.drawPath(br, paint((44, 30, 28), 1.0, stroke=6.5))
    # nose
    c.drawPath(skia.Path().moveTo(-3, -150).lineTo(-5, -98), paint((255, 246, 236), 0.22, stroke=7))
    c.drawPath(skia.Path().moveTo(8, -140).lineTo(10, -98), paint((110, 80, 70), 0.30, stroke=6))
    c.drawOval(skia.Rect(-16, -97, -5, -90), paint((92, 62, 56), 0.75)); c.drawOval(skia.Rect(5, -97, 16, -90), paint((92, 62, 56), 0.75))
    # mouth
    my = -64
    if mouth is None:
        a0 = -70 - 6 * smile
        m = skia.Path(); m.moveTo(-31, a0); m.quadTo(0, -70 + 38 * smile + 3, 31, a0); m.quadTo(0, -66 + 6 * smile, -31, a0); m.close()
        c.drawPath(m, paint((62, 22, 26)))
        if smile > 0.35:
            c.save(); c.clipPath(m); c.drawRect(skia.Rect(-31, a0 - 2, 31, a0 + 12 * smile + 2), paint((240, 234, 226))); c.restore()
        c.drawPath(m, paint((140, 70, 72), 0.9, stroke=3.6))
        for sx in (-1, 1): c.drawPath(skia.Path().moveTo(sx * 31, a0).lineTo(sx * 36, a0 - 6 * smile), paint((110, 70, 64), 0.7, stroke=3))
    else:
        w, h, teeth = mouth
        c.drawOval(skia.Rect(-w / 2, my - h / 2, w / 2, my + h / 2), paint((50, 14, 18)))
        if teeth > 0:
            c.save(); c.clipRRect(skia.RRect.MakeOval(skia.Rect(-w / 2, my - h / 2, w / 2, my + h / 2)))
            c.drawRect(skia.Rect(-w / 2, my - h / 2, w / 2, my - h / 2 + max(5, h * 0.36 * teeth)), paint((240, 234, 226))); c.restore()
        c.drawOval(skia.Rect(-w / 2, my - h / 2, w / 2, my + h / 2), paint((150, 76, 78), 1.0, stroke=5))
    # raised hand (waving); slides down out of frame when wave = 0
    if wave > 0.002:
        c.save(); c.translate(0, (1 - e_out(wave)) * 520)
        c.drawPath(skia.Path().moveTo(205, 330).lineTo(220, 60), paint((140, 144, 152), 1.0, stroke=96))
        c.drawPath(skia.Path().moveTo(205, 330).lineTo(220, 60), paint((255, 255, 255), 0.25, stroke=5))
        c.save(); c.translate(222, 40); c.rotate(math.sin(t * 13.0) * 0.28)
        c.drawPath(skia.Path().moveTo(0, 0).lineTo(0, -48), paint((206, 182, 168), 1.0, stroke=40))
        c.drawOval(skia.Rect(-38, -140, 38, -36), paint((222, 200, 186)))
        for i, (fx, ln, ang) in enumerate(((-26, 62, -0.30), (-9, 76, -0.10), (9, 72, 0.08), (26, 56, 0.26), (-44, 46, -0.95))):
            bx, by = (fx, -122) if i < 4 else (-30, -70)
            ex_, ey_ = bx + math.sin(ang) * ln, by - math.cos(ang) * ln
            c.drawPath(skia.Path().moveTo(bx, by).lineTo(ex_, ey_), paint((222, 200, 186), 1.0, stroke=19))
            c.drawPath(skia.Path().moveTo(bx - 3, by).lineTo(ex_ - 3, ey_), paint((255, 244, 234), 0.22, stroke=4))
        c.restore(); c.restore()
    c.restore()


def draw_porch(c, t, st):
    z = st.get("zoom", 1.0); zc = st.get("zc", (270, 330))
    c.save(); c.translate(zc[0], zc[1]); c.scale(z, z); c.translate(-zc[0], -zc[1])
    c.translate(st.get("shx", 0), st.get("shy", 0))
    vgrad(c, -200, -200, FW + 200, 470, (34, 40, 54), (16, 20, 28))
    for i, (x, r) in enumerate(((20, 90), (110, 70), (200, 100), (330, 80), (420, 110), (520, 90))):
        c.drawCircle(x, 440, r, paint((9, 12, 12)))
    c.drawRect(skia.Rect(380, 392, 540, 452), paint((16, 18, 22)))                 # neighbour house
    c.drawRect(skia.Rect(404, 408, 430, 432), paint((255, 206, 120), 0.9)); glow(c, 417, 420, 50, (255, 190, 100), 0.35)
    glow(c, 470, 372, 200, (255, 220, 150), 0.30)                                  # street lamp
    c.drawRect(skia.Rect(467, 372, 473, 452), paint((10, 12, 14)))
    c.drawRoundRect(skia.Rect(20, 420, 150, 458), 14, 14, paint((8, 10, 12)))     # parked car
    c.drawRoundRect(skia.Rect(46, 402, 124, 432), 10, 10, paint((8, 10, 12)))
    vgrad(c, -200, 452, FW + 200, 566, (26, 34, 30), (38, 46, 40))                  # lawn
    # porch floor with perspective planks
    vgrad(c, -200, 560, FW + 200, FH + 200, (84, 70, 56), (140, 116, 90))
    vp = (270, 462)
    for i in range(-14, 16):
        xb = 270 + i * 74
        c.drawPath(skia.Path().moveTo(vp[0] + (xb - 270) * 0.06, 566).lineTo(xb, FH + 200), paint((20, 14, 10), 0.55, stroke=3, round_=False))
    c.drawRect(skia.Rect(-200, 556, FW + 200, 568), paint((178, 150, 118), 0.55))
    # railing posts (near the camera)
    for x0, x1 in ((-30, 46), (494, 570)):
        c.drawRect(skia.Rect(x0, 300, x1, 760), paint((52, 44, 38))); c.drawRect(skia.Rect(x0, 300, x1, 308), paint((200, 180, 150), 0.5))
    c.drawRect(skia.Rect(46, 520, 494, 536), paint((60, 52, 44), 0.9))
    # porch lamp: hot disc + big cone of light
    sh = skia.GradientShader.MakeRadial((250, -6), 760, [ci(255, 240, 200, 0.42), ci(255, 240, 200, 0.14), ci(255, 240, 200, 0)], [0, 0.45, 1])
    c.drawCircle(250, -6, 760, paint(shader=sh, blend=skia.BlendMode.kPlus))
    glow(c, 250, 4, 120, (255, 248, 220), 0.85)
    c.restore()
    wm = st.get("woman")
    if wm:
        c.save(); c.translate(zc[0], zc[1]); c.scale(z, z); c.translate(-zc[0], -zc[1]); c.translate(st.get("shx", 0), st.get("shy", 0))
        draw_woman(c, t, **wm)
        c.restore()


def draw_feed(c, t, st):
    tq = math.floor(t * 12.0) / 12.0
    fc = _FSURF.getCanvas(); fc.clear(skia.ColorBLACK)
    draw_porch(fc, tq, st)
    a = _FSURF.makeImageSnapshot().toarray()[..., :3].astype(np.float32)
    g = a.mean(axis=2, keepdims=True)
    rs = np.random.RandomState(int(tq * 12) % 4096)
    a = g * np.array([0.84, 1.0, 0.90], dtype=np.float32) * 1.12 + rs.standard_normal((FH, FW, 1)).astype(np.float32) * 10.0
    a[::2] *= 0.94
    a = cv2.remap(np.clip(a, 0, 255).astype(np.uint8), _MAPX, _MAPY, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    ok, enc = cv2.imencode(".jpg", a, [cv2.IMWRITE_JPEG_QUALITY, 30]); a = cv2.imdecode(enc, 1)
    a = cv2.resize(a, (W, H), interpolation=cv2.INTER_CUBIC)
    bgra = np.dstack([a, np.full((H, W, 1), 255, np.uint8)])
    c.drawImage(skia.Image.fromarray(np.ascontiguousarray(bgra), colorType=skia.kBGRA_8888_ColorType, alphaType=skia.kPremul_AlphaType), 0, 0)


def cam_ui(c, t, connecting=0.0):
    vgrad(c, 0, 0, W, 300, (0, 0, 0), (0, 0, 0), 0.72, 0.0)
    vgrad(c, 0, 1400, W, H, (0, 0, 0), (0, 0, 0), 0.0, 0.7)
    status_bar(c, "2:14", 0.11)
    p = skia.Path(); p.moveTo(86, 150); p.lineTo(58, 182); p.lineTo(86, 214); c.drawPath(p, paint((255, 255, 255), 0.9, stroke=8))
    tl(c, "Front Door", 120, 182, 46, (255, 255, 255), 1.0, PB)
    on = int(t * 1.6) % 2 == 0
    c.drawCircle(W - 250, 182, 12, paint((235, 50, 50), 1.0 if on else 0.35)); tl(c, "LIVE", W - 226, 182, 36, (255, 255, 255), 1.0, PB)
    tl(c, "02:14:%02d AM" % (int(t) % 60), 50, 1440, 40, (255, 255, 255), 0.9, PB)
    for x, lab in ((200, "Talk"), (540, "Light"), (880, "Siren")):
        c.drawCircle(x, 1700, 62, paint((255, 255, 255), 0.16)); c.drawCircle(x, 1700, 62, paint((255, 255, 255), 0.35, stroke=3))
        tc(c, lab, x, 1810, 32, (230, 232, 240), 0.9)
    if connecting > 0:
        c.drawRect(skia.Rect(0, 0, W, H), paint((6, 8, 12), connecting))
        a = t * 6.0
        for i in range(10):
            ang = a + i * 0.628; r0, r1 = 52, 84
            c.drawLine(W / 2 + math.cos(ang) * r0, 900 + math.sin(ang) * r0, W / 2 + math.cos(ang) * r1, 900 + math.sin(ang) * r1, paint((255, 255, 255), connecting * (0.12 + 0.88 * (i / 10.0)), stroke=9))
        tc(c, "Connecting to Front Door...", W / 2, 1050, 40, (200, 206, 224), connecting)


# =============================================================== bedroom door (seen from the bed)
def draw_bdoor(c, t, cam_y=900.0, zoom=1.0, cx=540.0, under=1.0, feet=0.0, feet_xs=(440, 640), knob=0.0, ajar=0.0, glowk=0.6, dust=(), sway=0.0, roll=0.0):
    c.save(); c.translate(W / 2, H / 2); c.rotate(roll); c.scale(zoom, zoom); c.translate(-cx, -cam_y)
    vgrad(c, -900, -1500, 2000, 1500, (24, 32, 46), (11, 15, 22))
    for i in range(-14, 30):                                                         # faint wallpaper
        if i % 2 == 0: c.drawRect(skia.Rect(i * 60, 262, i * 60 + 30, 1450), paint((255, 255, 255), 0.018))
    glow(c, 80, 700, 700, (70, 100, 170), 0.10)                                      # moonlight from the left
    # ceiling
    vgrad(c, -900, -1500, 2000, 262, (16, 22, 32), (30, 40, 56))
    c.drawRect(skia.Rect(-900, 256, 2000, 272), paint((50, 60, 78), 0.55))
    rs = random.Random(9)
    for i in range(90): c.drawCircle(-300 + rs.random() * 1700, -600 + rs.random() * 850, 1.5 + rs.random() * 2.5, paint((255, 255, 255), 0.03))
    c.drawPath(skia.Path().moveTo(300, 250).lineTo(340, 120).lineTo(310, 40).lineTo(380, -90), paint((0, 0, 0), 0.7, stroke=3))     # crack
    c.save(); c.translate(540, -330); c.rotate(sway * math.sin(t * 5) * 0.05)
    c.drawLine(0, 0, 0, -120, paint((18, 20, 24), 1.0, stroke=6))
    c.drawOval(skia.Rect(-110, 0, 110, 70), paint((52, 58, 70))); c.drawOval(skia.Rect(-80, 12, 80, 50), paint((120, 130, 150), 0.7))
    c.restore()
    # floor + baseboard
    c.drawRect(skia.Rect(-900, 1420, 2000, 1460), paint((8, 10, 14)))
    c.drawRect(skia.Rect(-900, 1418, 2000, 1423), paint((70, 86, 100), 0.35))
    vgrad(c, -900, 1460, 2000, 3000, (22, 17, 14), (5, 4, 4))
    if under > 0.01:                                                                 # light fan from the hall
        sh = skia.GradientShader.MakeLinear([(0, 1424), (0, 2300)], [ci(200, 232, 215, 0.55 * under), ci(200, 232, 215, 0.0)])
        pth = skia.Path(); pth.moveTo(300, 1424); pth.lineTo(780, 1424); pth.lineTo(1160, 2300); pth.lineTo(-80, 2300); pth.close()
        c.drawPath(pth, paint(shader=sh))
    # door + frame
    c.drawRect(skia.Rect(236, 262, 844, 1424), paint((10, 9, 9)))
    c.drawRect(skia.Rect(270, 296, 810, 1424), paint((40, 54, 64)))
    vgrad(c, 270, 296, 810, 1424, (66, 86, 98), (26, 36, 44), 0.30, 0.55)
    for (x0, y0, x1, y1) in ((314, 342, 500, 760), (580, 342, 766, 760), (314, 820, 500, 1160), (580, 820, 766, 1160), (314, 1210, 500, 1380), (580, 1210, 766, 1380)):
        c.drawRect(skia.Rect(x0, y0, x1, y1), paint((8, 12, 16), 0.55)); c.drawRect(skia.Rect(x0 + 6, y0 + 6, x1 - 6, y1 - 6), paint((52, 68, 78), 0.6))
        c.drawRect(skia.Rect(x0 + 6, y0 + 6, x1 - 6, y0 + 10), paint((140, 170, 180), 0.28))
    # knob (rotating highlight + latch tab)
    kx, ky = 742, 900
    rrect(c, kx - 34, ky - 80, kx + 34, ky + 80, 18, (110, 92, 58), 0.9)
    c.drawCircle(kx, ky, 40, paint((8, 8, 8), 0.7, blur=6))
    c.drawCircle(kx, ky, 34, paint((150, 126, 78)))
    c.drawCircle(kx, ky, 34, paint((255, 232, 170), 0.25, stroke=3))
    a_ = knob * 0.9
    c.drawCircle(kx + math.cos(-2.2 + a_) * 17, ky + math.sin(-2.2 + a_) * 17, 9, paint((255, 245, 205), 0.75))
    c.save(); c.translate(kx, ky); c.rotate(a_); c.drawRoundRect(skia.Rect(-30, -4, 30, 4), 4, 4, paint((72, 56, 30), 0.9)); c.restore()
    if ajar > 0.001:                                                                 # the latch lets go: light floods round the edge
        sh2 = skia.GradientShader.MakeLinear([(810, 0), (810 + 90 * ajar, 0)], [ci(230, 250, 235, 0.95 * ajar), ci(230, 250, 235, 0)])
        c.drawRect(skia.Rect(804, 296, 810 + 90 * ajar, 1424), paint(shader=sh2))
        c.drawRect(skia.Rect(806, 296, 806 + 9 * ajar, 1424), paint((255, 255, 255), min(1.0, ajar * 1.4)))
    # gap under the door: light + shadows of feet
    c.drawRect(skia.Rect(290, 1414, 790, 1426), paint((205, 240, 222), 0.9 * under))
    if feet > 0.01:
        for fx in feet_xs: c.drawOval(skia.Rect(fx - 54, 1408, fx + 54, 1430), paint((2, 3, 4), feet))
    # dust falling from the ceiling after each thump upstairs
    for td in dust:
        if 0 <= t - td < 1.6:
            gr = random.Random(int(td * 100))
            for i in range(26):
                px = 120 + gr.random() * 840; py = 270 + (t - td) * (90 + gr.random() * 240) - 140; a = 0.7 * (1 - (t - td) / 1.6)
                c.drawCircle(px, py, 1.5 + gr.random() * 2.5, paint((210, 220, 225), a))
    c.restore()
    if glowk > 0:                                                                    # the phone in my hand lights the foreground
        glow(c, W / 2, H + 120, 1100, (170, 195, 255), 0.35 * glowk)
        pth = skia.Path(); pth.moveTo(-60, H); pth.cubicTo(120, H - 210, 420, H - 260, 640, H - 190); pth.cubicTo(860, H - 120, 1000, H - 80, 1180, H); pth.close()
        c.drawPath(pth, paint((5, 6, 9), 0.92)); c.drawPath(pth, paint((140, 170, 255), 0.18 * glowk, stroke=4))
