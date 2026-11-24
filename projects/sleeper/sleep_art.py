"""Sleeper: everything drawn in code. Lock screen, live sleep-tracker app, sleep-talking clip screen, alert modal, and the bedroom (a 2-screen-wide world we pan across).
Skia + numpy only. Reuses helpers/post-FX from projects/peephole/dark.py.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(HERE, "..", "peephole"))
from dark import *          # noqa: W, H, FPS, cl, lerp, prog, e_out, e_io, e_back, decay, paint, quad, glow, vgrad, font, text, ANTON, POP, post, skia, np, cv2, math, random, ci
import soundfile as sf

PM = "/usr/share/fonts/truetype/google-fonts/Poppins-Medium.ttf"
PB = POP
TEAL = (86, 224, 204); CORAL = (255, 92, 112); LAV = (160, 148, 255); CARD = (22, 26, 54); INK = (236, 240, 255); DIM = (140, 148, 182)


def rrect(c, x0, y0, x1, y1, r, rgb, a=1.0, **kw):
    c.drawRoundRect(skia.Rect(x0, y0, x1, y1), r, r, paint(rgb, a, **kw))


def tl(c, s, x, y, size, rgb=(255, 255, 255), a=1.0, fnt=PM):      # left aligned, y = visual centre
    c.drawString(s, x, y + size * 0.36, font(fnt, size), paint(rgb, a))


def tr(c, s, x, y, size, rgb=(255, 255, 255), a=1.0, fnt=PM):      # right aligned
    f = font(fnt, size); c.drawString(s, x - f.measureText(s), y + size * 0.36, f, paint(rgb, a))


def tc(c, s, x, y, size, rgb=(255, 255, 255), a=1.0, fnt=PM):
    f = font(fnt, size); c.drawString(s, x - f.measureText(s) / 2, y + size * 0.36, f, paint(rgb, a))


def tw(s, size, fnt=PM): return font(fnt, size).measureText(s)


def status_bar(c, clock="11:52", batt=0.34, tint=(255, 255, 255)):
    tl(c, clock, 66, 62, 38, tint, 1.0, PB)
    for i, hh in enumerate((10, 16, 22, 28)):
        c.drawRect(skia.Rect(780 + i * 14, 76 - hh, 780 + i * 14 + 9, 76), paint(tint, 0.9 if i < 3 else 0.35))
    rrect(c, 900, 46, 968, 80, 9, tint, 0.9, stroke=3)
    col = (235, 60, 60) if batt < 0.2 else tint
    rrect(c, 906, 52, 906 + 56 * batt, 74, 5, col, 1.0)
    c.drawRect(skia.Rect(970, 55, 975, 71), paint(tint, 0.9))


def app_bg(c, dim=0.0):
    vgrad(c, -40, -40, W + 40, H + 40, (13, 15, 36), (5, 6, 16))
    glow(c, 900, 300, 700, (90, 80, 210), 0.10); glow(c, 120, 1500, 800, (60, 90, 190), 0.07)
    if dim > 0: c.drawRect(skia.Rect(-40, -40, W + 40, H + 40), paint((0, 0, 0), dim))


def moon(c, x, y, r, rgb=LAV, a=1.0):
    p = skia.Path(); p.addCircle(x, y, r)
    q = skia.Path(); q.addCircle(x + r * 0.5, y - r * 0.28, r * 0.86)
    res = skia.Op(p, q, skia.PathOp.kDifference_PathOp)
    c.drawPath(res, paint(rgb, a))


# =============================================================== lock screen (the hook, and the loop)
def draw_lock(c, t, t_on=0.0, shake=0.0, ring=0.0, n2=0.0):
    ox = shake * math.sin(t * 95); oy = shake * 0.6 * math.cos(t * 83)
    c.save(); c.translate(ox, oy)
    vgrad(c, -40, -40, W + 40, H + 40, (16, 18, 44), (3, 4, 10))
    glow(c, 820, 420, 640, (90, 80, 210), 0.18); glow(c, 160, 1500, 760, (60, 90, 190), 0.10)
    for i in range(14):
        gr = random.Random(i * 7 + 3)
        c.drawCircle(gr.random() * W, 400 + gr.random() * 1200, 40 + gr.random() * 90, paint((140, 130, 255), 0.02 + 0.02 * gr.random()))
    status_bar(c, "6:58", 0.34)
    tc(c, "Wednesday, November 25", W / 2, 400, 40, (210, 216, 240), 0.85)
    tc(c, "6:58", W / 2, 560, 250, (240, 244, 255), 0.96, PB)
    y0, y1 = 790, 1090
    rrect(c, 56, y0, W - 56, y1, 54, (38, 40, 70), 0.9); rrect(c, 56, y0, W - 56, y1, 54, (255, 255, 255), 0.22, stroke=3)
    c.drawCircle(150, y0 + 96, 52, paint((70, 60, 150))); moon(c, 150, y0 + 96, 28)
    tl(c, "Sleep", 232, y0 + 70, 46, (255, 255, 255), 1.0, PB); tr(c, "now", W - 100, y0 + 70, 34, (190, 196, 220), 0.9)
    tl(c, "Good morning! Sleep score: 91", 232, y0 + 146, 40, (255, 255, 255), 1.0, PM)
    tl(c, "2 sleepers detected.", 232, y0 + 214, 46, (255, 120, 140), 1.0, PB)
    if ring > 0: rrect(c, 46, y0 - 10, W - 46, y1 + 10, 62, (255, 214, 90), ring * (0.6 + 0.4 * math.sin(t * 10)), stroke=8)
    if n2 > 0:
        yy = 1130 + (1 - e_back(n2, 1.4)) * 80
        rrect(c, 56, yy, W - 56, yy + 200, 54, (38, 40, 70), 0.9 * n2); rrect(c, 56, yy, W - 56, yy + 200, 54, (255, 255, 255), 0.22 * n2, stroke=3)
        c.drawCircle(150, yy + 70, 46, paint((70, 60, 150), n2)); moon(c, 150, yy + 70, 24, LAV, n2)
        tl(c, "Sleep", 232, yy + 52, 42, (255, 255, 255), n2, PB); tl(c, "Sleeper 2 · heart rate: 0 bpm", 232, yy + 128, 40, (255, 255, 255), n2, PM)
    for x in (120, W - 120): c.drawCircle(x, 1700, 62, paint((255, 255, 255), 0.13))
    rrect(c, W / 2 - 180, 1840, W / 2 + 180, 1850, 5, (255, 255, 255), 0.5)
    c.restore()


# =============================================================== live sleep-tracker screen
SPEED = 300.0                                                            # px per second of ECG scroll
def _bpm_table(bpm_fn, T=40.0, dt=1.0 / 300):
    n = int(T / dt) + 2; ph = np.zeros(n); acc = 0.0
    for i in range(1, n): acc += bpm_fn(i * dt) / 60.0 * dt; ph[i] = acc
    return ph, dt


def _ecg(f):
    g = lambda m, s: math.exp(-((f - m) / s) ** 2)
    return 0.13 * g(0.15, 0.04) - 0.12 * g(0.285, 0.012) + 1.0 * g(0.30, 0.012) - 0.24 * g(0.318, 0.014) + 0.30 * g(0.56, 0.06)


class Live:
    """live screen state: bpm_fn(t) is the heart rate of Sleeper 1; the table integrates it into beat phase so the ECG, the heart icon and the audio stay locked."""
    def __init__(self, bpm_fn): self.bpm = bpm_fn; self.ph, self.dt = _bpm_table(bpm_fn)
    def phase(self, t): i = max(0, min(len(self.ph) - 2, int(t / self.dt))); return self.ph[i] + (self.ph[i + 1] - self.ph[i]) * (t / self.dt - i)
    def beat_times(self, t0, t1):
        """times of the R peak of every beat in [t0, t1]"""
        out = []; k = int(self.phase(t0))
        while True:
            k += 1; i = int(np.searchsorted(self.ph, k + 0.30))
            if i >= len(self.ph) - 1: break
            tt = i * self.dt
            if tt > t1: break
            if tt >= t0: out.append(round(tt, 3))
        return out


def chip(c, x, y, label, rgb, a=1.0, size=40, icon=None, pop=0.0):
    w = tw(label, size, PB) + 56 + (46 if icon else 0)
    c.save(); c.translate(x + w / 2, y); sc = 1.0 + 0.16 * pop; c.scale(sc, sc); c.translate(-(x + w / 2), -y)
    rrect(c, x, y - 36, x + w, y + 36, 36, rgb, 0.20 * a); rrect(c, x, y - 36, x + w, y + 36, 36, rgb, 0.8 * a, stroke=3)
    xx = x + 28
    if icon == "person":
        c.drawCircle(xx + 12, y - 8, 8, paint(rgb, a)); c.drawPath(skia.Path().moveTo(xx, y + 18).quadTo(xx + 12, y - 6, xx + 24, y + 18), paint(rgb, a, stroke=7)); xx += 46
    tl(c, label, xx, y, size, rgb, a, PB)
    c.restore(); return w


def heart_icon(c, x, y, s, rgb, a=1.0):
    p = skia.Path(); p.moveTo(x, y + 0.9 * s); p.cubicTo(x - 1.6 * s, y - 0.1 * s, x - 0.9 * s, y - 1.1 * s, x, y - 0.4 * s)
    p.cubicTo(x + 0.9 * s, y - 1.1 * s, x + 1.6 * s, y - 0.1 * s, x, y + 0.9 * s); p.close(); c.drawPath(p, paint(rgb, a))


def draw_card(c, t, y0, y1, who, st):
    """one sleeper card. st: name, name2, flip (0..1 crossfade to name2), col, bpm (text), live(ECG on), glowk, flat, pop"""
    col = st["col"]
    rrect(c, 48, y0, W - 48, y1, 52, CARD, 1.0); rrect(c, 48, y0, W - 48, y1, 52, (255, 255, 255), 0.08, stroke=3)
    if st.get("glowk", 0) > 0: rrect(c, 44, y0 - 4, W - 44, y1 + 4, 56, col, st["glowk"] * (0.6 + 0.4 * math.sin(t * 9)), stroke=7)
    fl = st.get("flip", 0.0); cy = y0 + 76
    if fl < 0.5: chip(c, 90, cy, st["name"], col, 1 - fl * 2, 38, None, st.get("pop", 0.0))
    else: chip(c, 90, cy, st["name2"], st.get("col2", col), (fl - 0.5) * 2, 38, "person", st.get("pop", 0.0))
    tr(c, st["sub"], W - 92, cy, 32, DIM, 1.0)
    # big number + bpm label
    bx = 96; by = y0 + 255
    f = font(PB, 220); s = st["bpm"]
    c.drawString(s, bx + 3, by + 220 * 0.36 + 8, f, paint((0, 0, 0), 0.5)); c.drawString(s, bx, by + 220 * 0.36, f, paint(INK))
    nw = f.measureText(s)
    tl(c, "bpm", bx + nw + 24, by + 52, 48, DIM, 1.0, PM)
    heart_icon(c, W - 180, by - 6, 44 * (1.0 + 0.16 * st.get("beatk", 0.0)), col, 0.95 if st.get("live") else 0.25)


def draw_trace(c, t, x0, x1, ybase, amp, col, live, flat, phase_fn=None, label=None):
    # ECG: sample x -> time -> beat phase
    pth = skia.Path(); first = True
    xs = np.arange(x0, x1 + 1, 3.0)
    for x in xs:
        tx = t - (x1 - x) / SPEED
        if flat:
            y = ybase + 1.6 * math.sin(tx * 17.0) * 0.4 + (0.9 if int(tx * 40) % 7 == 0 else 0.0)
        else:
            y = ybase - amp * _ecg(phase_fn(tx) % 1.0) if tx > 0 else ybase
        if first: pth.moveTo(x, y); first = False
        else: pth.lineTo(x, y)
    c.drawPath(pth, paint(col, 0.45, stroke=14, blur=10)); c.drawPath(pth, paint(col, 1.0, stroke=5))
    c.drawCircle(x1, ybase if flat else ybase - amp * _ecg(phase_fn(t) % 1.0), 9, paint((255, 255, 255)))


def live_header(c, t, title="Live", sub="Bedroom · bed sensor"):
    status_bar(c, "11:52", 0.34)
    p = skia.Path(); p.moveTo(86, 150); p.lineTo(58, 182); p.lineTo(86, 214); c.drawPath(p, paint((190, 180, 255), 0.95, stroke=8))
    tl(c, title, 120, 172, 52, INK, 1.0, PB); tl(c, sub, 120, 224, 32, DIM, 1.0)
    on = int(t * 1.6) % 2 == 0
    c.drawCircle(W - 250, 182, 12, paint((235, 50, 50), 1.0 if on else 0.35)); tl(c, "LIVE", W - 226, 182, 36, INK, 1.0, PB)


def draw_live(c, t, L, s1, s2, shake=0.0, dim=0.0, banner=None, modal=None, foot="Bed sensor · 2 people present"):
    ox = shake * math.sin(t * 95); oy = shake * 0.6 * math.cos(t * 83)
    c.save(); c.translate(ox, oy)
    app_bg(c)
    live_header(c, t)
    ph = L.phase
    # card A: sleeper 1 (live ECG)
    draw_card(c, t, 330, 850, 1, s1)
    c.save(); c.clipRect(skia.Rect(90, 640, W - 90, 830))
    draw_trace(c, t, 96, W - 96, 740, 70, s1["col"], True, False, ph)
    c.restore()
    # card B: sleeper 2 (flat)
    draw_card(c, t, 890, 1410, 2, s2)
    c.save(); c.clipRect(skia.Rect(90, 1200, W - 90, 1390))
    draw_trace(c, t, 96, W - 96, 1300, 0, s2["col"], False, True)
    c.restore()
    if s2.get("tag", 0) > 0:
        a = s2["tag"] * (0.55 + 0.45 * (int(t * 3) % 2))
        chip(c, 468, 1148, "NO PULSE", CORAL, a, 32)
    tc(c, foot, W / 2, 1640, 36, DIM, 1.0)
    for i in range(2): c.drawCircle(W / 2 - 22 + i * 44, 1700, 9, paint(LAV if i == 0 else DIM, 0.9))
    if dim > 0: c.drawRect(skia.Rect(-40, -40, W + 40, H + 40), paint((0, 0, 0), dim))
    if banner: draw_banner(c, t, **banner)
    if modal: draw_modal(c, t, **modal)
    c.restore()


def draw_banner(c, t, k, title, body, sub):
    if k <= 0: return
    y = -260 + 400 * e_back(k, 1.2)
    rrect(c, 40, y, W - 40, y + 250, 54, (44, 46, 82), 0.98); rrect(c, 40, y, W - 40, y + 250, 54, (255, 255, 255), 0.25, stroke=3)
    c.drawCircle(130, y + 84, 46, paint((70, 60, 150))); moon(c, 130, y + 84, 24)
    tl(c, "Sleep", 206, y + 62, 38, (255, 255, 255), 1.0, PB); tr(c, "now", W - 90, y + 62, 30, (190, 196, 220), 0.9)
    tl(c, title, 206, y + 126, 46, (255, 150, 164), 1.0, PB); tl(c, sub, 206, y + 188, 34, (210, 216, 240), 0.95, PM)


def draw_modal(c, t, k, done=0.0):
    if k <= 0: return
    c.drawRect(skia.Rect(-40, -40, W + 40, H + 40), paint((0, 0, 0), 0.62 * k))
    sc = 0.85 + 0.15 * e_back(k, 1.6)
    c.save(); c.translate(W / 2, 800); c.scale(sc, sc); c.translate(-W / 2, -800)
    rrect(c, 90, 520, W - 90, 1090, 60, (30, 22, 40), min(1.0, k * 1.5))
    rrect(c, 90, 520, W - 90, 1090, 60, CORAL, 0.55 + 0.35 * math.sin(t * 8), stroke=6)
    p = skia.Path(); p.moveTo(W / 2, 590); p.lineTo(W / 2 + 74, 726); p.lineTo(W / 2 - 74, 726); p.close()
    c.drawPath(p, paint(CORAL, 0.25)); c.drawPath(p, paint(CORAL, 1.0, stroke=9))
    tc(c, "!", W / 2, 678, 70, CORAL, 1.0, PB)
    tc(c, "Guest detected", W / 2, 810, 70, (255, 255, 255), 1.0, PB)
    tc(c, "in your home", W / 2, 880, 40, (200, 206, 230), 1.0)
    # status row: spinner -> check
    yy = 990
    if done < 0.5:
        a = t * 7.0
        for i in range(10):
            ang = a + i * 0.628
            c.drawLine(W / 2 - 150 + math.cos(ang) * 14, yy + math.sin(ang) * 14, W / 2 - 150 + math.cos(ang) * 28, yy + math.sin(ang) * 28, paint((255, 255, 255), 0.12 + 0.88 * (i / 10.0), stroke=6))
        tl(c, "Notifying owner…", W / 2 - 110, yy, 42, (255, 255, 255), 1.0, PM)
    else:
        kk = e_back(prog(done, 0.5, 0.9), 1.8)
        c.save(); c.translate(W / 2 - 170, yy); c.scale(kk, kk)
        c.drawCircle(0, 0, 30, paint(TEAL, 0.25)); c.drawPath(skia.Path().moveTo(-14, 0).lineTo(-3, 12).lineTo(16, -12), paint(TEAL, 1.0, stroke=8)); c.restore()
        tl(c, "Owner notified", W / 2 - 110, yy, 46, (255, 255, 255), 1.0, PB)
    c.restore()


# =============================================================== sleep-talking clip screen
_NARR = None
def narr_env(t0, t1, n):
    global _NARR
    if _NARR is None: _NARR = sf.read(os.path.join(HERE, "narration.wav"), dtype="float32")
    y, sr = _NARR
    seg = np.abs(y[int(t0 * sr):int(t1 * sr)]); m = len(seg) // n
    e = np.array([np.sqrt(np.mean(seg[i * m:(i + 1) * m] ** 2)) for i in range(n)])
    return e / (e.max() + 1e-9)


def draw_clip(c, t, T0, T1, env, bubbles, match, summary, shake=0.0, playing=True):
    """bubbles: [(speaker, text_shown, show_chip_k)]; match: appear 0..1; summary: 0..1 (the '2 speakers' card)"""
    ox = shake * math.sin(t * 95); oy = shake * 0.6 * math.cos(t * 83)
    c.save(); c.translate(ox, oy)
    app_bg(c)
    status_bar(c, "6:58", 0.34)
    p = skia.Path(); p.moveTo(86, 150); p.lineTo(58, 182); p.lineTo(86, 214); c.drawPath(p, paint((190, 180, 255), 0.95, stroke=8))
    tl(c, "Sleep talking", 120, 172, 52, INK, 1.0, PB); tl(c, "Last night · 3:12 AM · clip 1 of 3", 120, 224, 32, DIM, 1.0)
    # waveform card
    rrect(c, 48, 300, W - 48, 640, 52, CARD, 1.0); rrect(c, 48, 300, W - 48, 640, 52, (255, 255, 255), 0.08, stroke=3)
    n = len(env); bw = (W - 2 * 48 - 80) / n; u = cl((t - T0) / (T1 - T0)) if playing else 0.0
    for i, e in enumerate(env):
        x = 88 + i * bw + bw / 2; h = 10 + 190 * e
        played = (i + 0.5) / n <= u
        c.drawLine(x, 470 - h / 2, x, 470 + h / 2, paint(LAV if played else (90, 96, 150), 1.0 if played else 0.7, stroke=bw * 0.56))
    xp = 88 + (W - 2 * 48 - 80) * u
    c.drawLine(xp, 370, xp, 570, paint((255, 255, 255), 0.95, stroke=4))
    tl(c, "0:%02d" % int(u * 14), 96, 600, 30, DIM, 1.0); tr(c, "0:14", W - 96, 600, 30, DIM, 1.0)
    # transcript bubbles
    ys = [690, 960]
    for (spk, txt, ck), y in zip(bubbles, ys):
        if not txt: continue
        a = 1.0
        h = 250
        rrect(c, 48, y, W - 48, y + h, 44, (36, 40, 76), a); rrect(c, 48, y, W - 48, y + h, 44, (255, 255, 255), 0.10, stroke=3)
        tl(c, spk, 96, y + 44, 30, DIM, 1.0)
        tl(c, txt, 96, y + 112, 58, INK, 1.0, PB)
        if ck > 0:
            kk = e_out(ck)
            chip(c, 96, y + 196, "Voice match: Daniel 99%", TEAL, kk, 30)
    # the reveal
    if summary > 0:
        k = e_back(summary, 1.4)
        c.save(); c.translate(W / 2, 1340); c.scale(0.9 + 0.1 * k, 0.9 + 0.1 * k); c.translate(-W / 2, -1340)
        rrect(c, 48, 1255, W - 48, 1425, 50, (60, 24, 40), 0.95 * summary); rrect(c, 48, 1255, W - 48, 1425, 50, CORAL, (0.55 + 0.35 * math.sin(t * 8)) * summary, stroke=6)
        tc(c, "2 speakers · 1 voice", W / 2, 1305, 60, (255, 255, 255), summary, PB)
        tc(c, "Both match: Daniel (you)", W / 2, 1379, 38, (255, 170, 184), summary, PM)
        c.restore()
    c.restore()


# =============================================================== the bedroom: a world two screens wide
WW = 2160


def draw_window(c, x0, y0, x1, y1, k=1.0):
    vgrad(c, x0, y0, x1, y1, (78, 98, 150), (30, 42, 78), 0.95 * k, 0.95 * k)
    glow(c, (x0 + x1) / 2, y0 + 140, 460, (140, 170, 240), 0.14 * k)
    c.drawRect(skia.Rect((x0 + x1) / 2 - 8, y0, (x0 + x1) / 2 + 8, y1), paint((18, 22, 34)))
    c.drawRect(skia.Rect(x0, (y0 + y1) / 2 - 8, x1, (y0 + y1) / 2 + 8), paint((18, 22, 34)))
    c.drawRect(skia.Rect(x0 - 14, y0 - 14, x1 + 14, y0 + 4), paint((14, 18, 28))); c.drawRect(skia.Rect(x0 - 14, y1 - 4, x1 + 14, y1 + 18), paint((14, 18, 28)))
    c.drawRect(skia.Rect(x0 - 14, y0 - 14, x0 + 4, y1 + 18), paint((14, 18, 28))); c.drawRect(skia.Rect(x1 - 4, y0 - 14, x1 + 14, y1 + 18), paint((14, 18, 28)))
    rs = random.Random(5)
    for i in range(26): c.drawCircle(x0 + 20 + rs.random() * (x1 - x0 - 40), y0 + 20 + rs.random() * (y1 - y0 - 40), 1.4 + rs.random() * 1.6, paint((255, 255, 255), 0.5))


def draw_figure(c, t, fig):
    """the second sleeper: a lump under the covers, then a silhouette that sits up and tilts its head toward us"""
    a = fig.get("alpha", 1.0)
    if a <= 0.01: return
    rise = e_io(fig.get("rise", 0.0)); tilt = fig.get("tilt", 0.0)
    cx = 1650
    # covers: long lump with the shoulders under it
    cov = skia.Path(); cov.moveTo(1290, 1500); cov.cubicTo(1300, 1360, 1420, 1330, 1520, 1340); cov.cubicTo(1580, 1250 - 150 * rise, 1740, 1250 - 150 * rise, 1800, 1340)
    cov.cubicTo(1900, 1340, 2010, 1370, 2040, 1500); cov.lineTo(2040, 1700); cov.lineTo(1290, 1700); cov.close()
    # body silhouette (sits up): torso + neck + head
    hy = lerp(1250, 620, rise); sy = lerp(1330, 900, rise)
    c.save(); c.translate(cx, 0)
    body = skia.Path(); body.moveTo(-270, 1500); body.cubicTo(-260, sy + 80, -210, sy - 4, -110, sy - 20)
    body.cubicTo(-60, sy - 30, -52, sy - 60, -52, hy + 150); body.lineTo(52, hy + 150)
    body.cubicTo(52, sy - 60, 60, sy - 30, 110, sy - 20); body.cubicTo(210, sy - 4, 260, sy + 80, 270, 1500); body.close()
    head_w, head_h = 92, 118
    c.save(); c.translate(0, hy); c.rotate(tilt * -11.0)
    head = skia.Rect(-head_w, -head_h, head_w, head_h)
    c.drawOval(skia.Rect(-head_w - 16, -head_h - 12, head_w + 16, head_h + 6), paint((140, 175, 255), 0.22 * a * rise, blur=16))      # rim light spill
    c.restore()
    c.drawPath(body, paint((2, 3, 6), a))
    c.save(); c.translate(0, hy); c.rotate(tilt * -11.0)
    c.drawOval(head, paint((2, 3, 6), a))
    hair = skia.Path(); hair.moveTo(-head_w - 4, 10); hair.cubicTo(-head_w - 14, -head_h - 40, head_w + 14, -head_h - 40, head_w + 4, 10); hair.cubicTo(head_w - 20, -50, -head_w + 20, -50, -head_w - 4, 10); hair.close()
    c.drawPath(hair, paint((1, 1, 3), a))
    c.drawPath(skia.Path().moveTo(-head_w + 8, -head_h * 0.55).cubicTo(-head_w * 0.4, -head_h - 4, head_w * 0.5, -head_h - 6, head_w - 2, -head_h * 0.5), paint((170, 200, 255), 0.35 * a * rise, stroke=4, blur=3))
    c.restore()
    c.restore()
    c.drawPath(cov, paint((14, 18, 30), a)); c.drawPath(cov, paint((120, 150, 230), 0.20 * a, stroke=4))
    for i in range(7):                                                                                # folds
        x = 1380 + i * 95; c.drawPath(skia.Path().moveTo(x, 1440 + 18 * math.sin(i)).quadTo(x + 30, 1500, x + 10, 1640), paint((0, 0, 0), 0.35 * a, stroke=10, blur=4))


def draw_bedroom(c, t, ox=0.0, fig=None, glowk=0.7, phone_glow=1.0, sway=0.0, zoom=1.0, dust=0.0):
    c.save(); c.translate(W / 2, H / 2); c.scale(zoom, zoom); c.translate(-W / 2, -H / 2)
    c.translate(-ox + 5 * math.sin(t * 1.3) * (1 + sway), 4 * math.sin(t * 1.9))
    # ---- wall
    vgrad(c, -200, -400, WW + 200, 1300, (22, 28, 44), (9, 12, 20))
    for i in range(-4, 40):
        if i % 2 == 0: c.drawRect(skia.Rect(i * 60, 0, i * 60 + 30, 1300), paint((255, 255, 255), 0.016))
    # left: a framed photo and a shelf, lit by the phone
    c.drawRect(skia.Rect(250, 380, 470, 640), paint((6, 8, 12))); c.drawRect(skia.Rect(262, 392, 458, 628), paint((30, 40, 58)))
    c.drawRect(skia.Rect(700, 760, 940, 776), paint((6, 8, 12)))
    # bedside table, a glass of water and the clock (11:52), all lit by the phone
    c.drawRect(skia.Rect(560, 1180, 1010, 1420), paint((22, 28, 42))); c.drawRect(skia.Rect(560, 1180, 1010, 1190), paint((140, 160, 210), 0.30))
    c.drawRect(skia.Rect(580, 1196, 990, 1420), paint((10, 13, 20), 0.5))
    rrect(c, 650, 1070, 880, 1180, 14, (8, 10, 14), 1.0); rrect(c, 650, 1070, 880, 1180, 14, (120, 140, 190), 0.25, stroke=3)
    tc(c, "11:52", 765, 1126, 62, (255, 70, 70), 0.95, PB); glow(c, 765, 1126, 190, (255, 60, 60), 0.30)
    c.drawRoundRect(skia.Rect(910, 1090, 970, 1180), 8, 8, paint((150, 180, 230), 0.22)); c.drawRoundRect(skia.Rect(910, 1124, 970, 1180), 8, 8, paint((150, 190, 240), 0.22))
    # right: the window, curtains, light on the bed
    draw_window(c, 1420, 250, 1820, 940)
    c.drawRect(skia.Rect(1180, 1010, 2100, 1340), paint((16, 19, 30))); c.drawRect(skia.Rect(1180, 1010, 2100, 1018), paint((120, 140, 190), 0.22))
    c.drawRect(skia.Rect(1180, 1010, 1200, 1340), paint((8, 10, 16)))
    for sx, w in ((1150, 200), (1880, 230)):
        cur = skia.Path(); cur.moveTo(sx, 0); cur.lineTo(sx + w, 0); cur.cubicTo(sx + w - 40, 600, sx + w + 30, 1000, sx + w - 20, 1330); cur.lineTo(sx, 1330); cur.close()
        c.drawPath(cur, paint(shader=skia.GradientShader.MakeLinear([(sx, 0), (sx + w, 0)], [ci(18, 22, 36), ci(32, 40, 62)])))
        for k in range(5): c.drawLine(sx + 18 + k * (w / 5), 40, sx + 4 + k * (w / 5), 1300, paint((0, 0, 0), 0.35, stroke=8, blur=5))
    # light fan from the window falling across the bed
    fan = skia.Path(); fan.moveTo(1420, 940); fan.lineTo(1820, 940); fan.lineTo(2300, 1900); fan.lineTo(1000, 1900); fan.close()
    c.drawPath(fan, paint(shader=skia.GradientShader.MakeLinear([(0, 940), (0, 1900)], [ci(120, 150, 230, 0.16), ci(120, 150, 230, 0.02)])))
    # ---- bed: mattress top, sheets, pillows
    vgrad(c, -200, 1300, WW + 200, 2100, (30, 36, 56), (14, 17, 28))
    c.drawRect(skia.Rect(-200, 1296, WW + 200, 1306), paint((130, 150, 200), 0.18))
    rrect(c, 1380, 1170, 1930, 1370, 80, (44, 52, 80), 1.0); rrect(c, 1380, 1170, 1930, 1370, 80, (150, 170, 230), 0.16, stroke=4)
    if fig is not None: draw_figure(c, t, fig)
    # ---- my side (left): big pillow near the camera + the phone's glow
    pil = skia.Path(); pil.moveTo(-80, 1560); pil.cubicTo(60, 1380, 700, 1340, 1100, 1480); pil.lineTo(1100, 2100); pil.lineTo(-80, 2100); pil.close()
    c.drawPath(pil, paint(shader=skia.GradientShader.MakeLinear([(0, 1380), (0, 2000)], [ci(60, 70, 104), ci(20, 24, 38)])))
    c.drawPath(pil, paint((170, 190, 255), 0.14, stroke=4))
    if phone_glow > 0:
        glow(c, 560, 1900, 1200, (150, 175, 255), 0.42 * glowk * phone_glow)
        glow(c, 640, 1150, 1000, (150, 175, 255), 0.26 * glowk * phone_glow)
        pth = skia.Path(); pth.moveTo(-60, 1920); pth.cubicTo(100, 1740, 360, 1690, 560, 1760); pth.cubicTo(760, 1690, 940, 1780, 1140, 1920); pth.close()
        c.drawPath(pth, paint((4, 5, 8), 0.94 * phone_glow)); c.drawPath(pth, paint((150, 175, 255), 0.30 * glowk * phone_glow, stroke=5))
        c.drawRoundRect(skia.Rect(420, 1760, 700, 1790), 14, 14, paint((200, 220, 255), 0.55 * glowk * phone_glow))       # lit edge of the phone
    if dust > 0:
        rs = random.Random(3)
        for i in range(40): c.drawCircle(1100 + rs.random() * 900, 300 + rs.random() * 900 + 30 * math.sin(t * 0.7 + i), 1.5 + rs.random() * 2, paint((190, 210, 255), 0.18 * dust))
    c.restore()
