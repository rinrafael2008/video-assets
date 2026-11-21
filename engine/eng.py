"""Tiny 2D animation engine on Skia: easing, camera, IK stickman, fists, particles, captions, motion-blur render."""
import math, json, random, subprocess, sys
import numpy as np
import skia
import soundfile as sf

W, H, FPS = 1080, 1920, 30
FONT_PATH = "/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf"
TF = skia.Typeface.MakeFromFile(FONT_PATH)
_fonts = {}

BLACK = "#111111"; WHITE = "#FFFFFF"; RED = "#FF4D5A"; BLUE = "#3A86FF"; YEL = "#FFD83D"
GREEN = "#06D6A0"; PINK = "#FF8FA3"; ORANGE = "#FF9F1C"; PURPLE = "#7B5CFF"


# ---------------------------------------------------------------- basics
def cl(x, a=0.0, b=1.0): return a if x < a else b if x > b else x
def lerp(a, b, k): return a + (b - a) * k
def prog(t, a, b): return cl((t - a) / (b - a)) if b != a else (1.0 if t >= a else 0.0)
def e_out(x): return 1 - (1 - x) ** 3
def e_out5(x): return 1 - (1 - x) ** 5
def e_in(x): return x ** 3
def e_io(x): return x * x * x * (x * (x * 6 - 15) + 10)
def e_back(x, s=1.9):
    c3 = s + 1
    return 1 + c3 * (x - 1) ** 3 + s * (x - 1) ** 2
def e_elastic(x):
    if x <= 0: return 0.0
    if x >= 1: return 1.0
    return 2 ** (-9 * x) * math.sin((x * 10 - 0.75) * (2 * math.pi) / 3) + 1
def pulse(t, t0, dur=0.25):
    """0->1->0 bump starting at t0"""
    x = prog(t, t0, t0 + dur)
    return math.sin(math.pi * x) if 0 < x < 1 else 0.0
def decay(t, t0, k=7.0):
    return math.exp(-k * (t - t0)) if t >= t0 else 0.0


def rgb(h):
    h = h.lstrip("#"); return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
def mix_hex(a, b, k):
    ra, ga, ba = rgb(a); rb, gb, bb = rgb(b)
    return "#%02x%02x%02x" % (int(lerp(ra, rb, k)), int(lerp(ga, gb, k)), int(lerp(ba, bb, k)))
def C(h, a=1.0):
    r, g, b = rgb(h); return skia.ColorSetARGB(int(255 * cl(a)), r, g, b)

def paint(color=BLACK, alpha=1.0, stroke=None, cap=True):
    p = skia.Paint(); p.setAntiAlias(True); p.setColor(C(color, alpha))
    if stroke:
        p.setStyle(skia.Paint.kStroke_Style); p.setStrokeWidth(stroke)
        if cap: p.setStrokeCap(skia.Paint.kRound_Cap); p.setStrokeJoin(skia.Paint.kRound_Join)
    return p

def font(sz):
    sz = int(round(sz))
    f = _fonts.get(sz)
    if f is None:
        f = skia.Font(TF, sz); f.setSubpixel(True); _fonts[sz] = f
    return f


# ---------------------------------------------------------------- drawing helpers
def circ(c, x, y, r, fill=WHITE, line=BLACK, lw=12, alpha=1.0):
    if r <= 0: return
    if fill: c.drawCircle(x, y, r, paint(fill, alpha))
    if line and lw: c.drawCircle(x, y, r, paint(line, alpha, lw))

def oval(c, x, y, rx, ry, fill=WHITE, line=None, lw=10, alpha=1.0):
    if rx <= 0 or ry <= 0: return
    r = skia.Rect(x - rx, y - ry, x + rx, y + ry)
    if fill: c.drawOval(r, paint(fill, alpha))
    if line: c.drawOval(r, paint(line, alpha, lw))

def rrect(c, x, y, w, h, rad, fill=WHITE, line=BLACK, lw=12, alpha=1.0):
    """x,y = center"""
    r = skia.Rect(x - w / 2, y - h / 2, x + w / 2, y + h / 2)
    if fill: c.drawRoundRect(r, rad, rad, paint(fill, alpha))
    if line and lw: c.drawRoundRect(r, rad, rad, paint(line, alpha, lw))

def line(c, x1, y1, x2, y2, w=14, color=BLACK, alpha=1.0):
    c.drawLine(x1, y1, x2, y2, paint(color, alpha, w))

def poly(c, pts, fill=None, line_c=BLACK, lw=10, close=True, alpha=1.0):
    p = skia.Path(); p.moveTo(*pts[0])
    for q in pts[1:]: p.lineTo(*q)
    if close: p.close()
    if fill: c.drawPath(p, paint(fill, alpha))
    if line_c: c.drawPath(p, paint(line_c, alpha, lw))

def capsule(c, x1, y1, x2, y2, w, fill=WHITE, line_c=BLACK, lw=12, alpha=1.0):
    if line_c: line(c, x1, y1, x2, y2, w + lw * 2, line_c, alpha)
    line(c, x1, y1, x2, y2, w, fill, alpha)

def star_pts(cx, cy, r1, r2, n, rot=0.0):
    pts = []
    for i in range(n * 2):
        a = rot + math.pi * i / n; r = r1 if i % 2 == 0 else r2
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts

def check(c, x, y, s=1.0, color=GREEN, lw=26, alpha=1.0, outline=True):
    pts = [(x - 46 * s, y + 2 * s), (x - 12 * s, y + 38 * s), (x + 52 * s, y - 40 * s)]
    p = skia.Path(); p.moveTo(*pts[0]); p.lineTo(*pts[1]); p.lineTo(*pts[2])
    if outline: c.drawPath(p, paint(BLACK, alpha, lw + 14))
    c.drawPath(p, paint(color, alpha, lw))

def cross(c, x, y, s=1.0, color=RED, lw=26, alpha=1.0):
    p = skia.Path(); p.moveTo(x - 42 * s, y - 42 * s); p.lineTo(x + 42 * s, y + 42 * s)
    p.moveTo(x + 42 * s, y - 42 * s); p.lineTo(x - 42 * s, y + 42 * s)
    c.drawPath(p, paint(BLACK, alpha, lw + 14)); c.drawPath(p, paint(color, alpha, lw))

def text(c, s, x, y, size, fill=WHITE, stroke=BLACK, sw=0, scale=1.0, rot=0.0, alpha=1.0,
         shadow=True, lead=1.12):
    """centered multi-line text, (x,y) = center of block"""
    if alpha <= 0 or scale <= 0: return
    lines_ = s.split("\n"); f = font(size)
    c.save(); c.translate(x, y); c.rotate(rot); c.scale(scale, scale)
    total = (len(lines_) - 1) * size * lead
    for i, ln in enumerate(lines_):
        w = f.measureText(ln); yy = -total / 2 + i * size * lead + size * 0.36
        if shadow: c.drawString(ln, -w / 2 + 3, yy + 9, f, paint(BLACK, 0.28 * alpha))
        if sw:
            c.drawString(ln, -w / 2, yy, f, paint(stroke, alpha, sw))
        c.drawString(ln, -w / 2, yy, f, paint(fill, alpha))
    c.restore()

def pop_text(c, s, x, y, size, t, t0, **kw):
    k = prog(t, t0, t0 + 0.3)
    if t < t0: return
    text(c, s, x, y, size, scale=max(e_back(k), 0.01), **kw)

def tag(c, s, x, y, size, t, t0, fill=YEL, fg=BLACK, rot=0.0, padx=34, pady=18):
    """pill label that pops in"""
    if t < t0: return
    k = max(e_back(prog(t, t0, t0 + 0.3)), 0.01)
    f = font(size); w = f.measureText(s) + padx * 2; h = size + pady * 2
    c.save(); c.translate(x, y); c.rotate(rot); c.scale(k, k)
    rrect(c, 4, 8, w, h, h / 2, fill=BLACK, line=None, alpha=0.25)
    rrect(c, 0, 0, w, h, h / 2, fill=fill, line=BLACK, lw=8)
    c.drawString(s, -f.measureText(s) / 2, size * 0.36, f, paint(fg))
    c.restore()


# ---------------------------------------------------------------- effects (analytic in t)
def burst(c, t, t0, x, y, n=16, speed=560, life=0.7, size=15, colors=(YEL, WHITE, ORANGE), g=900, seed=1,
          shape="circle", spread=(0, 2 * math.pi)):
    dt = t - t0
    if dt < 0 or dt > life: return
    rng = random.Random(seed)
    for i in range(n):
        a = lerp(spread[0], spread[1], rng.random()); sp = speed * (0.35 + 0.65 * rng.random())
        px = x + math.cos(a) * sp * dt; py = y + math.sin(a) * sp * dt + 0.5 * g * dt * dt
        k = 1 - dt / life; col = colors[i % len(colors)]
        r = size * (0.5 + 0.5 * rng.random()) * (0.4 + 0.6 * k)
        if shape == "circle":
            c.drawCircle(px, py, r, paint(col, k))
        elif shape == "rect":
            c.save(); c.translate(px, py); c.rotate((rng.random() * 360) + dt * 360 * (rng.random() - 0.5) * 2)
            c.drawRect(skia.Rect(-r, -r * 0.55, r, r * 0.55), paint(col, k)); c.restore()
        elif shape == "star":
            poly(c, star_pts(px, py, r * 1.4, r * 0.55, 4, dt * 6), fill=col, line_c=None, alpha=k)

def ring(c, t, t0, x, y, r1=300, dur=0.45, w=18, color=WHITE, alpha=0.9):
    dt = t - t0
    if dt < 0 or dt > dur: return
    k = dt / dur; r = r1 * e_out(k)
    c.drawCircle(x, y, r, paint(color, alpha * (1 - k), w * (1 - 0.6 * k)))

def rays(c, t, t0, x, y, n=18, r1=120, r2=520, dur=0.4, w=16, color=WHITE, alpha=0.9, rot=0.0):
    dt = t - t0
    if dt < 0 or dt > dur: return
    k = dt / dur
    for i in range(n):
        a = rot + 2 * math.pi * i / n; ra = lerp(r1, r2, e_out(k)); rb = lerp(r1, r2, e_out(cl(k * 1.4)))
        rb = max(rb, ra * 0.5)
        c.drawLine(x + math.cos(a) * min(ra, rb), y + math.sin(a) * min(ra, rb),
                   x + math.cos(a) * max(ra, rb), y + math.sin(a) * max(ra, rb), paint(color, alpha * (1 - k), w))

def flash(c, t, t0, alpha=0.7, dur=0.18, color=WHITE):
    dt = t - t0
    if 0 <= dt < dur:
        c.drawRect(skia.Rect(0, 0, W, H), paint(color, alpha * (1 - dt / dur)))

def starburst(c, s, x, y, size, t, t0, fill=YEL, fg=BLACK, rot=-8, hold=0.8):
    """comic CRACK! style spiky bubble"""
    dt = t - t0
    if dt < 0: return
    k = max(e_back(prog(t, t0, t0 + 0.22), 2.6), 0.01)
    out = 1 - prog(t, t0 + hold, t0 + hold + 0.18)
    if out <= 0: return
    wob = 1 + 0.03 * math.sin(dt * 40)
    c.save(); c.translate(x, y); c.rotate(rot); c.scale(k * out * wob, k * out * wob)
    poly(c, star_pts(0, 0, size * 1.05, size * 0.62, 11, 0.2), fill=BLACK, line_c=None)
    poly(c, star_pts(-4, -4, size, size * 0.6, 11, 0.2), fill=fill, line_c=BLACK, lw=9)
    f = font(size * 0.36); w = f.measureText(s)
    c.drawString(s, -w / 2, size * 0.13, f, paint(fg)); c.restore()

def shake(t, t0, amp=18, k=9.0):
    dt = t - t0
    if dt < 0: return 0.0, 0.0
    a = amp * math.exp(-k * dt)
    return a * math.sin(dt * 91.0 + 1.0), a * math.sin(dt * 77.0)


# ---------------------------------------------------------------- audio envelope (lip sync)
class Env:
    def __init__(self, wav):
        y, sr = sf.read(wav, dtype="float32")
        if y.ndim > 1: y = y.mean(1)
        hop = sr // 120; n = len(y) // hop
        rms = np.sqrt(np.convolve(y[:n * hop].reshape(n, hop).__pow__(2).mean(1), np.ones(3) / 3, mode="same"))
        rms = rms / (np.percentile(rms, 95) + 1e-6)
        out = np.zeros_like(rms); v = 0.0
        for i, r in enumerate(rms):  # attack/release smoothing
            v = v + (r - v) * (0.65 if r > v else 0.22); out[i] = v
        self.e = np.clip(out, 0, 1.2); self.rate = 120.0
    def __call__(self, t):
        x = t * self.rate
        if x < 0 or x >= len(self.e) - 1: return 0.0
        i = int(x); f = x - i
        return float(self.e[i] * (1 - f) + self.e[i + 1] * f)

ENV = None
CAPT = None
def mouth_at(t):
    e = ENV(t) if ENV else 0.0
    return cl((e - 0.12) * 1.5, 0, 1)


def blink_at(t, period=2.9, off=0.6):
    x = (t + off) % period
    d = 0.16
    return 1.0 - (math.sin(math.pi * x / d) if x < d else 0.0)


# ---------------------------------------------------------------- IK stickman
def ik2(ax, ay, tx, ty, l1, l2, bend):
    dx, dy = tx - ax, ty - ay
    d = math.hypot(dx, dy) or 1e-6
    dc = cl(d, abs(l1 - l2) + 1e-3, l1 + l2 - 1e-3)
    ux, uy = dx / d, dy / d
    a = (l1 * l1 - l2 * l2 + dc * dc) / (2 * dc)
    h = math.sqrt(max(l1 * l1 - a * a, 0))
    px, py = ax + ux * a, ay + uy * a
    return (px - uy * h * bend, py + ux * h * bend), (ax + ux * dc, ay + uy * dc)

def rot(p, a):
    ca, sa = math.cos(a), math.sin(a); return (p[0] * ca - p[1] * sa, p[0] * sa + p[1] * ca)

STROKE = 17
def stick(c, x, y, s=1.0, *, hip=(0, 0), lean=0.0, tilt=0.0, hl=None, hr=None, fl=None, fr=None,
          mouth=0.0, smile=0.35, eyes=1.0, look=(0.0, 0.0), brow=0.0, browup=0.0, squash=0.0, flip=1,
          outfit=None, fists=False, alpha=1.0, shadow=True, o_mouth=False, sweat=0.0, head_r=80,
          bend_arm=1, bend_leg=-1, cheeks=0.0, arm_w=None):
    """character origin = ground between feet. units before scale s. hl/hr/fl/fr: targets in local coords."""
    sw = arm_w or STROKE
    c.save(); c.translate(x, y); c.scale(s * flip * (1 + squash), s * (1 - squash))
    if shadow:
        c.drawOval(skia.Rect(-110, -16, 110, 16), paint(BLACK, 0.16 * alpha))
    hipp = (hip[0], -215 + hip[1])
    sh = (hipp[0] + rot((0, -165), lean)[0], hipp[1] + rot((0, -165), lean)[1])
    neck = (sh[0] + rot((0, -22), lean)[0], sh[1] + rot((0, -22), lean)[1])
    hc = (neck[0] + rot((0, -head_r - 6), lean + tilt)[0], neck[1] + rot((0, -head_r - 6), lean + tilt)[1])
    fl = fl or (-46, 0); fr = fr or (46, 0)
    hl = hl or (sh[0] - 62, sh[1] + 150); hr = hr or (sh[0] + 62, sh[1] + 150)
    # legs
    for ft in (fl, fr):
        k, f = ik2(hipp[0], hipp[1], ft[0], ft[1], 112, 112, bend_leg)
        p = skia.Path(); p.moveTo(*hipp); p.lineTo(*k); p.lineTo(*f)
        c.drawPath(p, paint(BLACK, alpha, sw))
        line(c, f[0], f[1], f[0] + 24, f[1], sw * 0.9, BLACK, alpha)  # foot
    # torso
    line(c, hipp[0], hipp[1], sh[0], sh[1], sw, BLACK, alpha)
    if outfit == "doc":
        pts = [(sh[0] - 44, sh[1] + 4), (sh[0] + 44, sh[1] + 4), (hipp[0] + 70, hipp[1] + 78), (hipp[0] - 70, hipp[1] + 78)]
        poly(c, pts, fill=WHITE, line_c=BLACK, lw=9, alpha=alpha)
        line(c, sh[0], sh[1] + 6, hipp[0], hipp[1] + 76, 6, BLACK, alpha)
        # stethoscope
        p = skia.Path(); p.moveTo(sh[0] - 30, sh[1] + 4); p.quadTo(sh[0] - 36, sh[1] + 90, sh[0], sh[1] + 96)
        p.quadTo(sh[0] + 36, sh[1] + 90, sh[0] + 30, sh[1] + 4)
        c.drawPath(p, paint(BLUE, alpha, 8)); circ(c, sh[0], sh[1] + 100, 15, fill=BLUE, line=BLACK, lw=5, alpha=alpha)
    if outfit == "mom":
        pts = [(sh[0] - 30, sh[1] + 20), (sh[0] + 30, sh[1] + 20), (hipp[0] + 64, hipp[1] + 100), (hipp[0] - 64, hipp[1] + 100)]
        poly(c, pts, fill=PINK, line_c=BLACK, lw=8, alpha=alpha)
    # arms
    for tg in (hl, hr):
        k, hnd = ik2(sh[0], sh[1], tg[0], tg[1], 98, 98, bend_arm if tg is hl else -bend_arm)
        p = skia.Path(); p.moveTo(*sh); p.lineTo(*k); p.lineTo(*hnd)
        c.drawPath(p, paint(BLACK, alpha, sw))
        if fists: circ(c, hnd[0], hnd[1], 21, fill=WHITE, line=BLACK, lw=8, alpha=alpha)
    # head
    c.save(); c.translate(*hc); c.rotate(math.degrees(lean + tilt))
    if outfit == "mom":
        circ(c, -6, -head_r - 18, 36, fill="#5A3A2A", line=BLACK, lw=9, alpha=alpha)
    circ(c, 0, 0, head_r, fill=WHITE, line=BLACK, lw=15, alpha=alpha)
    ex, ey = 29, -4
    for sgn in (-1, 1):
        cx_ = sgn * ex + look[0] * 6; cy_ = ey + look[1] * 5
        oval(c, cx_, cy_, 9.5, 13 * max(eyes, 0.08), fill=BLACK, alpha=alpha)
        if eyes > 0.5: circ(c, cx_ + 3, cy_ - 5, 3.2, fill=WHITE, line=None, alpha=alpha)
        # brows (brow>0 angry: inner end lower; brow<0 worried: inner end higher)
        bx, by = sgn * ex, ey - 30 - browup * 12
        dyb = brow * 10
        line(c, bx + sgn * 17, by - dyb, bx - sgn * 17, by + dyb, 7, BLACK, alpha)
    if cheeks > 0:
        for sgn in (-1, 1): oval(c, sgn * 52, 22, 15, 9, fill=PINK, alpha=0.8 * cheeks * alpha)
    my = 36
    if o_mouth:
        oval(c, 0, my + 4, 14, 18, fill=BLACK, alpha=alpha)
    elif mouth > 0.06:
        mw = 24 + 8 * mouth; mh = 5 + 30 * mouth
        oval(c, 0, my + mh * 0.3, mw, mh, fill=BLACK, alpha=alpha)
        if mouth > 0.45: oval(c, 0, my + mh * 0.75, mw * 0.55, mh * 0.35, fill="#FF6B81", alpha=alpha)
    else:
        p = skia.Path(); p.moveTo(-26, my - 2 * smile); p.quadTo(0, my + 26 * smile + 2, 26, my - 2 * smile)
        c.drawPath(p, paint(BLACK, alpha, 8))
    if outfit == "doc":  # glasses
        for sgn in (-1, 1): circ(c, sgn * ex, ey, 24, fill=None, line=BLACK, lw=6, alpha=alpha)
        line(c, -ex + 24, ey, ex - 24, ey, 6, BLACK, alpha)
    if sweat > 0:
        sx, sy = 70, -48 + 26 * sweat
        p = skia.Path(); p.moveTo(sx, sy - 20); p.quadTo(sx + 16, sy + 4, sx, sy + 14); p.quadTo(sx - 16, sy + 4, sx, sy - 20)
        c.drawPath(p, paint("#7CC6FF", alpha)); c.drawPath(p, paint(BLACK, alpha, 4))
    c.restore()
    c.restore()


def walk_kw(phase, stride=62, lift=46, bob=12, swing=50, sh_y=-230):
    s, co = math.sin(phase), math.cos(phase)
    fl_ = (stride * s - 20, -lift * max(0.0, co)); fr_ = (-stride * s + 20, -lift * max(0.0, -co))
    return dict(fl=fl_, fr=fr_, hip=(0, bob * (1 - abs(s))),
                hl=(-52 + swing * s, sh_y + 160 - 14 * co), hr=(52 - swing * s, sh_y + 160 + 14 * co), lean=0.06)


# ---------------------------------------------------------------- front-view fist
SKIN = "#FFDDBE"
def fist(c, x, y, s=1.0, rotd=0.0, crack=0.0, alpha=1.0, fill=SKIN, squeeze=0.0, arm=0, mirror=False):
    c.save(); c.translate(x, y); c.rotate(rotd)
    c.scale(s * (1 + 0.05 * squeeze) * (-1 if mirror else 1), s * (1 - 0.06 * squeeze))
    if arm:
        rrect(c, 0, 360 + arm / 2, 214, arm, 46, fill=WHITE, line=BLACK, lw=14, alpha=alpha)   # sleeve
        rrect(c, 0, 220, 150, 300, 56, fill=fill, line=BLACK, lw=12, alpha=alpha)               # forearm
        rrect(c, 0, 352, 232, 44, 18, fill="#EDEDED", line=BLACK, lw=10, alpha=alpha)           # cuff
    rrect(c, 0, 20, 250, 215, 70, fill=fill, line=BLACK, lw=14, alpha=alpha)
    for i in range(1, 4):
        line(c, -125 + i * 62.5, -88, -125 + i * 62.5, 18, 9, BLACK, alpha)
    p = skia.Path(); p.moveTo(-120, 18); p.quadTo(0, 44, 120, 18)
    c.drawPath(p, paint(BLACK, alpha, 9))
    for i in range(4):
        kx = -94 + i * 62.5
        bump = 1.0 + (0.22 * crack if i == 2 else 0)
        oval(c, kx, -92, 28 * bump, 20 * bump, fill=fill, line=BLACK, lw=9, alpha=alpha)
    rrect(c, 128, 48, 70, 120, 32, fill=fill, line=BLACK, lw=12, alpha=alpha)
    c.restore()


# ---------------------------------------------------------------- captions
def build_chunks(words, maxc=17):
    chunks = []; cur = []
    def flush():
        nonlocal cur
        if cur: chunks.append(cur); cur = []
    for w in words:
        txt = w[0].upper()
        cand = " ".join([x[0].upper() for x in cur] + [txt])
        if cur and len(cand) > maxc: flush()
        cur.append(w)
        if w[0][-1] in ".?!,": flush()
    flush()
    # merge tiny orphans (1-2 letter words) into previous when short enough
    return chunks

def draw_captions(c, t, chunks, y=1450, size=86):
    for i, ch in enumerate(chunks):
        t0 = ch[0][1]; t1 = chunks[i + 1][0][1] if i + 1 < len(chunks) else ch[-1][2] + 0.3
        t1 = min(t1, ch[-1][2] + 0.45)
        if not (t0 - 0.02 <= t < t1): continue
        f = font(size); texts = [w[0].upper() for w in ch]
        space = f.measureText(" ") + 10; ws = [f.measureText(x) for x in texts]
        total = sum(ws) + space * (len(ws) - 1)
        kin = max(e_back(prog(t, t0 - 0.02, t0 + 0.16), 1.2), 0.0)
        c.save(); c.translate(W / 2, y); c.scale(0.9 + 0.1 * kin, 0.9 + 0.1 * kin)
        rrect(c, 0, 0, total + 64, size * 1.55, size * 0.7, fill="#000000", line=None, alpha=0.8)
        xx = -total / 2
        for j, (w, wd) in enumerate(zip(ch, ws)):
            nxt = ch[j + 1][1] if j + 1 < len(ch) else t1
            active = w[1] - 0.02 <= t < nxt
            col = YEL if active else WHITE
            sc = 1.0 + (0.08 * math.sin(math.pi * prog(t, w[1], w[1] + 0.16)) if active else 0)
            c.save(); c.translate(xx + wd / 2, 0); c.scale(sc, sc)
            c.drawString(texts[j], -wd / 2, size * 0.36, f, paint("#000000", 1.0, 9))
            c.drawString(texts[j], -wd / 2, size * 0.36, f, paint(col))
            c.restore(); xx += wd + space
        c.restore()


# ---------------------------------------------------------------- background + camera
def draw_bg(c, t, color, seed=0):
    c.drawRect(skia.Rect(0, 0, W, H), paint(color))
    dark = mix_hex(color, "#000000", 0.07); light = mix_hex(color, "#FFFFFF", 0.35)
    rng = random.Random(seed)
    for i in range(7):
        bx = rng.random() * W; by = rng.random() * H; r = 140 + rng.random() * 260
        sp = 14 + rng.random() * 22; ph = rng.random() * 6.28
        px = bx + 40 * math.sin(t * 0.35 + ph); py = (by - t * sp) % (H + 2 * r) - r
        c.drawCircle(px, py, r, paint(light if i % 2 else dark, 0.30))


class Cam:
    def __init__(self, zoom=1.0, cx=W / 2, cy=H / 2, rot=0.0, sx=0.0, sy=0.0):
        self.zoom, self.cx, self.cy, self.rot, self.sx, self.sy = zoom, cx, cy, rot, sx, sy
    def apply(self, c):
        c.translate(W / 2, H / 2); c.rotate(self.rot); c.scale(self.zoom, self.zoom)
        c.translate(-self.cx + self.sx, -self.cy + self.sy)


# ---------------------------------------------------------------- render loop
def render_range(scene_fn, f0, f1, out, nsub=4, shutter=0.55, crf=19):
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", str(crf),
                           "-pix_fmt", "yuv420p", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    surf = skia.Surface(W, H)
    for f in range(f0, f1):
        acc = np.zeros((H, W, 4), np.float32)
        globals()['CAPT'] = (f + 0.5) / FPS
        for s in range(nsub):
            t = (f + (s + 0.5) / nsub * shutter - shutter / 2 + 0.5 * 0) / FPS
            t = max(t, 0.0)
            cv = surf.getCanvas(); cv.save(); scene_fn(cv, t); cv.restore()
            acc += surf.makeImageSnapshot().toarray().astype(np.float32)
        ff.stdin.write((acc / nsub).astype(np.uint8).tobytes())
        if (f - f0) % 60 == 0: print("frame", f, flush=True)
    ff.stdin.close(); ff.wait()


def render_png(scene_fn, t, path):
    surf = skia.Surface(W, H); cv = surf.getCanvas(); scene_fn(cv, t)
    surf.makeImageSnapshot().save(path, skia.kPNG)
