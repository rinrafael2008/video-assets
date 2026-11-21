# Why are manhole covers round? Calipers demo: a shape turns between two parallel lines; the gap is its "width".
from kit import *
import math

GREY, DGREY = "#9AA3AD", "#69727D"
NX, NY, NS = 250, 1325, 0.9          # narrator parked bottom-left so the demo owns the middle


def manhole_prop(c, x, y, s=1.0, rot=0, alpha=1.0, r=150):
    c.save(); c.translate(x, y); c.rotate(rot); c.scale(s, s)
    circ(c, 0, 0, r, fill=GREY, line=BLACK, lw=12, alpha=alpha)
    circ(c, 0, 0, r * 0.84, fill=None, line=DGREY, lw=9, alpha=alpha)
    for i in range(12):
        a = i * math.pi / 6
        line(c, math.cos(a) * r * 0.30, math.sin(a) * r * 0.30, math.cos(a) * r * 0.70, math.sin(a) * r * 0.70, 9, DGREY, alpha)
    circ(c, 0, 0, r * 0.2, fill=DGREY, line=BLACK, lw=7, alpha=alpha)
    for sg in (-1, 1): oval(c, sg * r * 0.58, 0, r * 0.10, r * 0.045, fill=BLACK, alpha=alpha)   # pick holes
    c.restore()


def reuleaux(n, width, steps=36):
    """outline of a Reuleaux n-gon (odd n) of constant width, centred on its centroid"""
    d_over_R = 2 * math.sin(math.pi * (n - 1) / (2 * n)); R = width / d_over_R
    V = [(R * math.cos(-math.pi / 2 + 2 * math.pi * k / n), R * math.sin(-math.pi / 2 + 2 * math.pi * k / n)) for k in range(n)]
    pts = []
    for k in range(n):
        a_, b_ = V[(k + (n - 1) // 2) % n], V[(k + (n + 1) // 2) % n]
        a1 = math.atan2(a_[1] - V[k][1], a_[0] - V[k][0]); a2 = math.atan2(b_[1] - V[k][1], b_[0] - V[k][0])
        diff = (a2 - a1 + math.pi) % (2 * math.pi) - math.pi
        for j in range(steps):
            a = a1 + diff * j / steps; pts.append((V[k][0] + width * math.cos(a), V[k][1] + width * math.sin(a)))
    return pts


def rot_pts(pts, phi):
    ca, sa = math.cos(phi), math.sin(phi); return [(x * ca - y * sa, x * sa + y * ca) for x, y in pts]


def demo(T0, kind, cx=610, cy=700, W0=300, omega=1.3, drop_at=None, fill=YEL, ok=GREEN, T1=None):
    """shape spinning between two parallel lines; the readout shows the gap between them"""
    base = {"square": [(-W0 / 2, -W0 / 2), (W0 / 2, -W0 / 2), (W0 / 2, W0 / 2), (-W0 / 2, W0 / 2)],
            "reuleaux": reuleaux(3, W0)}.get(kind)

    def fn(c, T):
        if T < T0 or (T1 is not None and T >= T1): return
        k = max(e_back(prog(T, T0, T0 + 0.35)), 0.01); t = T - T0
        fall = drop_at is not None and T >= drop_at; dt = max(0.0, T - drop_at) if fall else 0.0
        phi = omega * t + (0.0 if kind == "square" else 0.4) + 2.0 * dt
        if kind == "circle": ymin, ymax = -W0 / 2, W0 / 2
        else:
            pts = rot_pts(base, phi); ys = [p[1] for p in pts]; ymin, ymax = min(ys), max(ys)
        wm = ymax - ymin; col = ok if kind != "square" else RED
        if not fall:
            a = prog(T, T0 + 0.25, T0 + 0.5)
            for yy in (ymin, ymax): line(c, cx - 290, cy + yy, cx + 290, cy + yy, 9, BLACK, a)
            bx = cx + 345; mid = (ymin + ymax) / 2
            arrow(c, bx, cy + mid, bx, cy + ymin, 11, col, 30, a); arrow(c, bx, cy + mid, bx, cy + ymax, 11, col, 30, a)
            text(c, "WIDTH", cx, 968, 44, fill=WHITE, sw=8, alpha=a)
            text(c, str(int(round(wm))), cx, 1056, 112, fill=col, sw=14, alpha=a)
        dy = 1900 * dt * dt
        if kind == "circle": manhole_prop(c, cx, cy, k, math.degrees(phi), 1.0, W0 / 2)
        else:
            P = [(cx + x * k, cy + y * k + dy) for x, y in (rot_pts(base, phi))]
            poly(c, P, fill=fill, line_c=BLACK, lw=12)
            P2 = [(cx + x * 0.78 * k, cy + y * 0.78 * k + dy) for x, y in rot_pts(base, phi)]
            poly(c, P2, fill=None, line_c=mix_hex(fill, "#000000", 0.35), lw=7)
    cues = [("pop_hi", T0)] + ([("whoosh_big", drop_at)] if drop_at else [])
    return Custom(fn, cues=cues)


def spinner(T0, x, y, s, spin=35, r=150):
    def fn(c, T):
        if T < T0: return
        k = max(e_back(prog(T, T0, T0 + 0.4), 2.0), 0.01); manhole_prop(c, x, y, s * k, spin * (T - T0), 1.0, r)
    return Custom(fn, cues=[("pop_hi", T0)])


def trio(T0, T_hi, y=640, w=230):
    specs = [("circle", 200, "#B8F2C9", 0), ("r3", 540, YEL, 3), ("r5", 880, PINK, 5)]

    def fn(c, T):
        for i, (kind, x, fill, n) in enumerate(specs):
            t0 = T0 + i * 0.22
            if T < t0: continue
            k = max(e_back(prog(T, t0, t0 + 0.35)), 0.01); ang = 1.5 * (T - t0) + i
            hi = T >= T_hi; dim = 0.35 if (hi and kind != "r3") else 1.0
            if hi and kind == "r3": k *= 1 + 0.2 * pulse(T, T_hi, 0.5)
            if kind == "circle":
                circ(c, x, y, w / 2 * k, fill=fill, line=BLACK, lw=12, alpha=dim)
                line(c, x, y, x + w / 2 * k * math.cos(ang), y + w / 2 * k * math.sin(ang), 9, BLACK, dim)
            else:
                P = [(x + px * k, y + py * k) for px, py in rot_pts(reuleaux(n, w), ang)]
                poly(c, P, fill=fill, line_c=BLACK, lw=12, alpha=dim)
                c.drawCircle(x, y, 8 * k, paint(BLACK, dim))
    return Custom(fn, cues=[("bloop", T0), ("bloop", T0 + 0.22), ("bloop", T0 + 0.44)])


def press(T0, T1, x=760, y0=480, yh=730):
    """cartoon stamping press: slams once, a finished cover pops out"""
    def fn(c, T):
        if T < T0 - 0.05 or T >= T1: return
        out = 1 - prog(T, T1 - 0.25, T1); dt = T - T0
        yb = lerp(y0, yh, e_in(prog(T, T0, T0 + 0.18))) if dt < 0.3 else lerp(yh, y0, e_out(prog(T, T0 + 0.35, T0 + 1.0)))
        c.save(); c.translate(x, 900); c.scale(out, out); c.translate(-x, -900)
        rrect(c, x, 1055, 460, 54, 18, fill=DGREY, line=BLACK, lw=10)
        if T >= T0 + 0.18: manhole_prop(c, x, 905, max(e_back(prog(T, T0 + 0.18, T0 + 0.5), 2.2), 0.01), 0, 1.0, 120)
        line(c, x, 410, x, yb, 38, DGREY); line(c, x, 410, x, yb, 12, BLACK, 0.25)
        rrect(c, x, yb, 360, 120, 24, fill=GREY, line=BLACK, lw=10)
        c.restore()
    return Custom(fn, cues=[("whoosh", T0), ("thud", T0 + 0.18)], punch=[(T0 + 0.18, 0.06)])


def roller(T0, T1, y=600, r=130, x0=-200, x1=1280):
    def fn(c, T):
        if T < T0 or T > T1 + 0.05: return
        k = prog(T, T0, T1); x = lerp(x0, x1, k); ang = (x - x0) / r * 180 / math.pi
        for i in range(4): line(c, x - r - 40 - i * 90, y - 50 + i * 36, x - r - 120 - i * 90, y - 50 + i * 36, 12, WHITE, 0.55)
        manhole_prop(c, x, y, 1.0, ang, 1.0, r)
    return Custom(fn, cues=[("whoosh_big", T0)])


def build():
    N = lambda **kw: Narrator(x=NX, y=NY, s=NS, **kw)
    return [
        Scene(0, bg=YEL, trans="auto", layers=[
            N(pose="wide", smile=0.7),
            Headline("WHY ARE MANHOLE", at("why"), y=190, size=96), Headline("COVERS ROUND?", at("covers"), y=325, size=112, fill=RED),
            spinner(0.1, 640, 790, 1.35), QMarks(at("manhole", off=0.1), spots=((170, 600), (1000, 560), (980, 1010)))]),
        Scene(at("tip"), bg="#BDE0FE", trans="auto", layers=[
            N(pose="point"),
            Headline("SQUARE", at("square"), y=190, size=140, fill=RED),
            demo(at("square"), "square", drop_at=at("slips")),
            Tag("DIAGONAL IS LONGER", at("diagonally"), x=610, y=385, size=52, fill=WHITE),
            Stamp("FALLS IN!", at("slips"), 700, 1195, color=RED, fill=WHITE, w=560, h=170, size=100, rot=-8)]),
        Scene(at("a circle"), bg="#B8F2C9", trans="auto", layers=[
            N(pose="hands_up", smile=0.8),
            Headline("CIRCLE", at("circle"), y=190, size=140, fill=WHITE),
            demo(at("circle"), "circle"),
            Tag("SAME WIDTH EVERYWHERE", at("same"), x=590, y=385, size=48, fill=YEL),
            Stamp("CAN'T FALL IN", at("never"), 665, 1205, color=GREEN, fill=WHITE, w=590, h=150, size=74, rot=-6)]),
        Scene(at("but"), bg="#CDB4DB", trans="auto", layers=[
            N(pose="wide", smile=0.6),
            Headline("CIRCLES AREN'T", at("but"), y=185, size=92), Headline("SPECIAL", at("special"), y=310, size=126, fill=RED),
            Tag("INFINITE SHAPES", at("infinitely"), x=540, y=445, size=60, fill=WHITE),
            trio(at("many"), at("curved")), Burst(at("curved"), 540, 640, 0.7),
            Tag("CURVED TRIANGLE", at("curved"), x=650, y=905, size=56, fill=YEL, rot=-3)]),
        Scene(at("round just"), bg="#FFD166", trans="auto", layers=[
            N(pose="wide", smile=0.8),
            Headline("ROUND WINS", at("round just"), y=190, size=130, fill=WHITE),
            Tag("EASY TO MAKE", at("easy"), x=540, y=330, size=58, fill=WHITE, T1=at("lid", off=-0.1)),
            press(at("easy"), at("lid", off=-0.1)),
            Tag("ROLLS LIKE A WHEEL", at("rolls"), x=540, y=330, size=54, fill=WHITE),
            roller(at("lid", off=-0.1), at("wheel", end=True, off=0.25))]),
        Scene(at("microsoft"), bg="#FF8FA3", trans="auto", layers=[
            Narrator(y=1320, s=1.45, pose="worry", brow=-0.5, sweat=0.8, smile=-0.3), QMarks(at("famous")),
            Headline("MICROSOFT", at("microsoft"), y=200, size=126, fill=WHITE), Tag("JOB INTERVIEW", at("job"), y=340, size=62, fill=YEL)]),
        Scene(at("the shortest"), bg=YEL, trans="auto", layers=[
            Narrator(y=1320, s=1.3, pose="hands_up", smile=0.9),
            Headline("MANHOLES ARE ROUND", at("manholes"), y=220, size=74), Headline("BECAUSE", at("because"), y=340, size=66, fill=RED),
            Headline("MANHOLES ARE ROUND", at("manholes", 1), y=455, size=74), Burst(at("round", 5), 540, 330, 1.1, colors=(YEL, PINK, BLUE, GREEN, WHITE))]),
    ]
