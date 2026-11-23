"""Peephole: timeline, overlays, captions. All cues anchored on word times (words.json)."""
import json, os, re, math, random
from dark import *

HERE = os.path.dirname(os.path.abspath(__file__))
WORDS = json.load(open(os.path.join(HERE, "words.json")))
TOTAL = 51.5


def _n(w): return re.sub(r"[^a-z0-9:']", "", w.lower())
def at(word, n=0, end=False, off=0.0):
    k = 0
    for w, s, e in WORDS:
        if _n(w) == _n(word):
            if k == n: return (e if end else s) + off
            k += 1
    raise KeyError((word, n))


K1, K2, K3 = at("three", 0), at("slow", 0), at("knocks", 1)           # the first three knocks
R1, R2, R3 = at("three", 1), at("knocks", 2), at("knocks", 2) + 0.62      # the second three (nothing moves at the door)
CK = [R3 + 0.0, at("coming") + 0.05, at("coming") + 0.70, at("closet.") + 0.02]
CUTS = [8.0, 10.46, 13.18, 16.15, 33.97, 38.38, 43.55, 48.42, 50.35]


# ---------------------------------------------------------------- shared effects
def kick(t, times, k=9.0): return sum(decay(t, tk, k) for tk in times)


def burst_on(t, s, e):
    """flicker burst: stuttering on/off, then dark just before the relight at e"""
    if not (s <= t < e): return None
    u = (t - s) / (e - s); fr = int(t * FPS)
    if u > 0.82: return 0.0
    return 1.0 if ((fr * 7 + 3) % 5) in (0, 1) else 0.04


BURSTS = [(18.48, 19.40), (22.80, 23.35), (24.20, 24.42), (25.95, 26.30), (27.05, 27.36), (33.35, 33.95), (44.95, 45.30)]


def lamp_flick(t):
    for s, e in BURSTS:
        r = burst_on(t, s, e)
        if r is not None: return r
    return 0.93 + 0.07 * math.sin(t * 31.0) * math.sin(t * 3.1 + 1.0)


def fig_state(t):
    """(z, head, arm_up) of the thing in the hall, switched only while the lights are out"""
    if t < 19.40: return None
    if t < 23.35: return (32.0, "up", 0.0)
    if t < 24.42: return (18.0, "up", 0.0)
    if t < 26.30: return (9.5, "up", 0.0)
    if t < 27.36: return (3.4, "up", 0.0)
    if t < 34.0: return (2.4, "bent" if t >= 28.7 else "up", 0.0)
    if t < 45.30: return (2.6, "up", 0.0)
    return (1.9, "up", e_io(prog(t, 46.9, 48.3)))


def pitch_of(t):
    if t < 28.5: return 0.0
    if t < 29.5: return 400 * e_io(prog(t, 28.5, 29.5))
    if t < 30.9: return 400.0
    if t < 31.9: return lerp(400, -340, e_io(prog(t, 30.9, 31.9)))
    if t < 33.4: return -340.0
    return lerp(-340, 0, e_io(prog(t, 33.4, 33.9)))


# ---------------------------------------------------------------- overlays
def slam(c, t, t0, t1, s, x, y, size, rgb=(255, 255, 255), stroke=14, rot=0.0, glowb=0):
    if not (t0 <= t < t1): return
    u = t - t0
    sc = 1.0 + 1.1 * (1 - e_out(prog(u, 0, 0.16)))
    a = min(1.0, u / 0.05) * (1 - prog(t, t1 - 0.14, t1))
    dx = 7 * math.sin(u * 90) * decay(u, 0, 9) ; dy = 6 * math.cos(u * 77) * decay(u, 0, 9)
    text(c, s, x + dx, y + dy, size, rgb, a, stroke=stroke, scale=sc, rot=rot, blur_glow=glowb)


def chunks_of(words, maxc=16):
    out, cur = [], []
    for w in words:
        cand = " ".join([x[0].upper() for x in cur] + [w[0].upper()])
        if cur and len(cand) > maxc: out.append(cur); cur = []
        cur.append(w)
        if w[0][-1] in ".?!,": out.append(cur); cur = []
    if cur: out.append(cur)
    return out
CHUNKS = chunks_of(WORDS)


def captions(c, t, y=1510, size=78):
    for i, ch in enumerate(CHUNKS):
        t0 = ch[0][1]; t1 = CHUNKS[i + 1][0][1] if i + 1 < len(CHUNKS) else ch[-1][2] + 0.4
        t1 = min(t1, ch[-1][2] + 0.5)
        if not (t0 - 0.02 <= t < t1): continue
        f = font(POP, size); txt = [w[0].upper() for w in ch]
        sp = f.measureText(" ") + 8; ws = [f.measureText(x) for x in txt]; tot = sum(ws) + sp * (len(ws) - 1)
        k = e_back(prog(t, t0 - 0.02, t0 + 0.14), 1.4)
        c.save(); c.translate(W / 2, y); c.scale(0.86 + 0.14 * k, 0.86 + 0.14 * k)
        xx = -tot / 2
        for j, (w, wd) in enumerate(zip(ch, ws)):
            nxt = ch[j + 1][1] if j + 1 < len(ch) else t1
            act = w[1] - 0.02 <= t < nxt
            col = (255, 206, 80) if act else (255, 255, 255)
            sc = 1.0 + (0.09 * math.sin(math.pi * prog(t, w[1], w[1] + 0.16)) if act else 0)
            c.save(); c.translate(xx + wd / 2, 0); c.scale(sc, sc)
            c.drawString(txt[j], -wd / 2 + 3, size * 0.36 + 8, f, paint((0, 0, 0), 0.5))
            c.drawString(txt[j], -wd / 2, size * 0.36, f, paint((0, 0, 0), 1.0, stroke=13))
            c.drawString(txt[j], -wd / 2, size * 0.36, f, paint(col))
            c.restore(); xx += wd + sp
        c.restore()


# ---------------------------------------------------------------- scenes
def s_door(c, t):
    p = e_io(prog(t, 0, 8.0))
    zoom = lerp(1.0, 1.20, p) + 0.035 * kick(t, [K1, K2, K3], 11)
    under = 0.82 + 0.10 * math.sin(t * 2.3) - 0.55 * kick(t, [K1, K2, K3], 22)
    draw_room(c, t, cx=540 + 18 * math.sin(t * 0.6), cy=880, zoom=zoom, roll=0.4 * math.sin(t * 0.8), knocks=[K1, K2, K3], under=cl(under, 0.05, 1.0),
              coat=0.5 + 3 * kick(t, [K1, K2, K3], 4), peep_glow=cl(under, 0, 1))
    return dict(ab=14 * kick(t, [K1, K2, K3], 18), bloom=1.0)


def s_tower(c, t):
    scroll = lerp(1.0, 14.0, e_io(prog(t, 8.0, 9.85)))
    zoom = lerp(1.0, 1.9, e_io(prog(t, 9.85, 10.44)))
    draw_tower(c, t, scroll, zoom=zoom, zc=(432, 873))
    mv = abs(scroll - lerp(1.0, 14.0, e_io(prog(t + 0.033, 8.0, 9.85)))) * FLOOR_H * 30
    return dict(vblur=cl(mv / 45, 0, 60), ab=3)


def s_hall(c, t):
    u = t - 10.46
    cam = Cam3(lerp(0.0, 3.6, u / 2.72), 0.0, 1.55 + 0.012 * math.sin(t * 5.1), f=1250, cx=540 + 5 * math.sin(t * 3.0), cy=900)
    draw_corridor(c, cam, flick=0.9 + 0.1 * math.sin(t * 40) * math.sin(t * 2.3), t=t)
    return dict(ab=2)


def s_peepdoor(c, t):
    u = prog(t, 13.18, 15.95)
    r = 60 * (490 / 60) ** e_io(u)
    draw_door_surface(c, t, cx=540, cy=880, ring_r=r)
    gl = e_io(prog(t, 15.1, 16.1))
    glow(c, 540, 880, r * 0.8, (170, 235, 185), 0.5 * gl)
    return dict(ab=2 + 6 * gl, bloom=1.0 + gl)


_POV_CACHE = {}
def s_pov(c, t, tstart, fig_override=None):
    fl = lamp_flick(t)
    fs = fig_state(t)
    pitch = pitch_of(t)
    breath = 1.0 + 0.010 * math.sin(t * 0.9)
    jx = 3.5 * math.sin(t * 1.7) + 1.5 * math.sin(t * 7.3); jy = 3.0 * math.sin(t * 1.3 + 1)
    fz = fs

    def drawfn(cc, src):
        cam = Cam3(0.0, 0.0 + 0.004 * math.sin(t * 2.1), 1.55, f=1100 * breath, cx=src / 2 + jx, cy=src / 2 + pitch + jy)
        fig = None
        if fz is not None:
            z, head, arm = fz
            fig = dict(z=z, head=head, arm_up=arm, lit=min(fl, 1.0), glints=1.0 if fl > 0.3 else 0.0)
        draw_corridor(cc, cam, flick=fl, t=t, figure=fig, width=src, height=src)
    c.drawRect(skia.Rect(0, 0, W, H), paint((0, 0, 0)))
    img = peephole_image(drawfn, src=1200, out=980, k=0.85)
    c.drawImage(img, (W - 980) / 2, 880 - 490)
    draw_ring(c, 540, 880, 492)
    hit = kick(t, [b[1] for b in BURSTS], 12)
    return dict(ab=3 + 12 * hit + (6 if (fz and fz[0] < 3 and fl > 0.5) else 0), bloom=1.0, flash=0.0)


def s_room_back(c, t):
    # 33.97 -> 38.38 : pull back from the door, feet under it, then the knocks that do not move the door, then whip to the closet
    p = e_io(prog(t, 33.97, 36.9))
    zoom = lerp(1.65, 1.0, p) + 0.04 * kick(t, [R1, R2], 11)
    cx = lerp(600, 540, p)
    whip = prog(t, 37.95, 38.40)
    cx2 = lerp(cx, -290, e_io(whip)); zoom2 = lerp(zoom, 1.25, e_io(whip))
    feet = 1.0 if t < 36.85 else 0.0
    under = 0.55 - 0.35 * kick(t, [R1, R2], 20) + (0.2 if int(t * 12) % 7 == 0 and t < 36.8 else 0)
    draw_room(c, t, cx=cx2 + 8 * math.sin(t * 40) * kick(t, [R1, R2], 14), cy=880, zoom=zoom2, roll=0.8 * math.sin(t * 1.3), knocks=[], cknocks=[R3 - 0.0], feet=feet,
              under=cl(under, 0.05, 1.0), coat=1.5, peep_glow=0.2, closet_open=0.0)
    spd = abs(e_io(prog(t + 0.033, 37.95, 38.40)) - e_io(whip)) * 1000 * 30 * 0.4
    return dict(ab=10 * kick(t, [R1, R2, R3], 16), whip=cl(spd, 0, 120), bloom=1.0)


def s_closet(c, t):
    p = prog(t, 38.38, 43.55)
    zoom = lerp(1.25, 1.55, e_io(p)) + 0.035 * kick(t, CK, 11)
    op = 0.03 + 0.07 * p
    draw_room(c, t, cx=-290, cy=870, zoom=zoom, roll=1.0 * math.sin(t * 1.1), cknocks=CK, under=0.1, closet_open=op, eyes=0.9 * kick(t, CK[1:], 13), coat=0.5)
    return dict(ab=12 * kick(t, CK, 16), bloom=1.0)


def s_reveal(c, t):
    u = t - 48.42
    op = 0.10 + 0.55 * e_out(prog(t, at("wasn't"), at("alone", 1, end=True) + 0.5))
    eyes = e_out(prog(t, at("alone", 1), at("alone", 1) + 0.12))
    fing = e_out(prog(t, at("alone", 1) + 0.35, at("alone", 1) + 1.1))
    zoom = lerp(1.55, 1.85, e_io(prog(t, 48.42, 50.3)))
    draw_room(c, t, cx=-290 + 10 * math.sin(t * 50) * eyes * 0.3, cy=870, zoom=zoom, cknocks=[], under=0.1, closet_open=op, eyes=eyes, fingers=fing, coat=0.5)
    return dict(ab=18 * decay(t, at("alone", 1), 6), flash=0.35 * decay(t, at("alone", 1), 14), bloom=1.2)


def frame(c, t):
    """returns the post-processing dict; draws everything for time t"""
    c.save()
    # global camera shake from the hits
    hits = [K1, K2, K3, R1, R2, R3] + CK + [at("alone", 1)] + [x for x in CUTS]
    sh = 0.0
    for tk in hits: sh += decay(t, tk, 14)
    c.translate(7 * sh * math.sin(t * 83), 6 * sh * math.cos(t * 71))
    c.translate(W / 2, H / 2); c.scale(1.04, 1.04); c.translate(-W / 2, -H / 2)
    if t < 8.0: fx = s_door(c, t)
    elif t < 10.46: fx = s_tower(c, t)
    elif t < 13.18: fx = s_hall(c, t)
    elif t < 16.15: fx = s_peepdoor(c, t)
    elif t < 33.97: fx = s_pov(c, t, 16.15)
    elif t < 38.38: fx = s_room_back(c, t)
    elif t < 43.55: fx = s_closet(c, t)
    elif t < 48.42: fx = s_pov(c, t, 43.55)
    elif t < 50.35: fx = s_reveal(c, t)
    else:
        c.drawRect(skia.Rect(0, 0, W, H), paint((0, 0, 0))); fx = dict()
    c.restore()
    # cut pulses
    for tc in CUTS:
        if t >= tc: fx["ab"] = fx.get("ab", 0) + 16 * decay(t, tc, 16)
    # ---- overlays
    clk = 1.0 - prog(t, 1.9, 2.1) if t < 2.2 else 0.0
    if t < 8.0:
        if t < 2.1:
            text(c, "3:07", W / 2, 300, 330, (255, 40, 40), 1.0, stroke=0, fnt=ANTON, shadow=False, blur_glow=26)
            text(c, "EVERY NIGHT AT", W / 2, 120, 84, (255, 255, 255), 1.0, stroke=10, fnt=ANTON)
        slam(c, t, at("something"), at("door.", end=True) + 0.3, "SOMETHING\nKNOCKS", W / 2, 340, 190, (255, 255, 255), stroke=16)
        slam(c, t, K1, 8.0, "THREE", W / 2, 560, 170, (255, 255, 255))
        slam(c, t, K2, 8.0, "SLOW", W / 2, 740, 170, (255, 255, 255))
        slam(c, t, K3, 8.0, "KNOCKS", W / 2, 940, 200, (255, 45, 45), glowb=18)
    slam(c, t, at("alone"), 9.1, "ALONE", W / 2, 300, 230, (255, 45, 45), glowb=14) if t < 10.46 else None
    slam(c, t, at("fourteenth"), 10.4, "14TH FLOOR", W / 2, 300, 170, (255, 255, 255))
    slam(c, t, at("else"), 13.1, "NOBODY\nELSE", W / 2, 330, 190, (255, 255, 255))
    slam(c, t, 19.46, 22.0, "SOMETHING\nTALL", W / 2, 250, 120, (255, 255, 255), stroke=12)
    slam(c, t, at("again", 1), 26.5, "AGAIN.", W / 2, 250, 220, (255, 45, 45), glowb=14)
    slam(c, t, at("right"), 28.5, "RIGHT OUTSIDE", W / 2, 250, 130, (255, 255, 255), stroke=12)
    slam(c, t, at("but"), at("hallway", 1, end=True) + 0.4, "NOT FROM\nTHE HALLWAY", W / 2, 330, 150, (255, 45, 45), glowb=12)
    slam(c, t, at("closet."), at("closet.", end=True) + 1.2, "MY\nCLOSET", W / 2, 330, 210, (255, 255, 255))
    slam(c, t, at("alone", 1), 50.3, "NOT\nALONE", W / 2, 400, 250, (255, 45, 45), glowb=22)
    if t >= 50.35:
        a = e_out(prog(t, 50.5, 50.9))
        text(c, "3:07", W / 2, 900, 330, (255, 40, 40), a, fnt=ANTON, shadow=False, blur_glow=26)
    if t < 50.3: captions(c, t)
    fx["fade"] = 1.0 - 0.0
    if t < 0.25: fx["fade"] = 1.0
    return fx
