# Why do airplane windows have a tiny hole? Side-on cross-section of the three panes (outside on the left, cabin on the right).
from kit import *
import math

OUTER, MID, INNER = "#5AA9FF", "#FFD83D", "#FFB38A"
TOP, XO, XM, XI, PW = 470, 490, 640, 790, 58
BOT_O, BOT_M, BOT_I = 1010, 1010, 900
H0, H1, HY = 925, 965, 945                       # the bleed hole in the middle pane
NX, NY, NS = 250, 1325, 0.9


def window_layer(T0, x, y, s, ring_at=None):
    def fn(c, T):
        if T < T0: return
        k = max(e_back(prog(T, T0, T0 + 0.4), 1.6), 0.01)
        c.save(); c.translate(x, y); c.scale(s * k, s * k)
        rrect(c, 0, 0, 400, 520, 170, fill="#F5F5F5", line=BLACK, lw=14)
        rrect(c, 0, 0, 290, 410, 120, fill="#9AD0FF", line=BLACK, lw=10)
        for cx_, cy_, r_ in ((-45, -90, 40), (5, -112, 50), (55, -85, 36), (-5, -62, 36)): c.drawCircle(cx_, cy_, r_, paint(WHITE, 0.9))
        circ(c, 0, 150, 9, fill=BLACK, line=None)
        if ring_at is not None and T >= ring_at:
            circ(c, 0, 150, 42 + 6 * math.sin((T - ring_at) * 9), fill=None, line=RED, lw=10)
        c.restore()
    return Custom(fn, cues=[("pop_hi", T0)] + ([("bell", ring_at)] if ring_at is not None else []))


def pane(c, x, y0, y1, fill, a=1.0, dy=0.0, dx=0.0):
    rrect(c, x + dx, (y0 + y1) / 2 + dy, PW, y1 - y0, 10, fill=fill, line=BLACK, lw=8, alpha=a)


def xsec(appear=(None, None, None), glow=None, crack=None, gap_t=None, fog=None):
    """appear: when each pane (outer, middle, inner) slides in (None = already there)
    glow: (t0, t1) halo behind the middle pane; crack: time the outer pane cracks; gap_t: time cabin air starts filling the gap
    fog: (t_on, t_clear) white haze in the gap that clears"""
    def fn(c, T):
        rrect(c, 640, TOP - 28, 440, 56, 14, fill="#C9CED6", line=BLACK, lw=8); rrect(c, 640, BOT_O + 28, 440, 56, 14, fill="#C9CED6", line=BLACK, lw=8)
        # air filling the gap between outer and middle pane
        if gap_t is not None and T >= gap_t + 0.9:
            top = lerp(HY, TOP + 6, e_out(prog(T, gap_t + 0.9, gap_t + 2.0)))
            c.drawRect(skia.Rect(XO + PW / 2 + 3, top, XM - PW / 2 - 3, H0 - 2), paint(WHITE, 0.85))
        if fog is not None and T >= fog[0]:
            a = 0.62 * prog(T, fog[0], fog[0] + 0.4) * (1 - prog(T, fog[1], fog[1] + 1.4))
            c.drawRect(skia.Rect(XO + PW / 2 + 3, TOP + 6, XM - PW / 2 - 3, H0 - 2), paint("#FFFFFF", a))
        if glow is not None and T >= glow[0] and (glow[1] is None or T < glow[1]):
            pu = 0.65 + 0.35 * math.sin((T - glow[0]) * 9)
            rrect(c, XM, (TOP + BOT_M) / 2, PW + 46, BOT_M - TOP + 34, 26, fill=WHITE, line=None, alpha=0.85 * pu * prog(T, glow[0], glow[0] + 0.2))
        broke = crack is not None and T >= crack
        specs = [(XO, [(TOP, BOT_O)], OUTER, appear[0]), (XM, [(TOP, H0), (H1, BOT_M)], MID, appear[1]), (XI, [(TOP, BOT_I)], INNER, appear[2])]
        for i, (x, segs, col, t0) in enumerate(specs):
            a, dy = 1.0, 0.0
            if t0 is not None:
                if T < t0: continue
                dy = -(1 - e_back(prog(T, t0, t0 + 0.45), 1.4)) * 760; a = prog(T, t0, t0 + 0.12)
            dx = 0.0
            if i == 0 and broke: col = "#3D7FCC"; dx = 7 * math.exp(-9 * (T - crack)) * math.sin((T - crack) * 80)
            for (y0, y1) in segs: pane(c, x, y0, y1, col, a, dy, dx)
        if broke:
            pts = [(XO, 570), (XO - 15, 625), (XO + 14, 680), (XO - 14, 735), (XO + 13, 790), (XO - 8, 840)]
            n = min(len(pts), 2 + int(prog(T, crack, crack + 0.2) * (len(pts) - 1)))
            p = skia.Path(); p.moveTo(*pts[0])
            for q in pts[1:n]: p.lineTo(*q)
            c.drawPath(p, paint(BLACK, 1.0, 10)); c.drawPath(p, paint(WHITE, 1.0, 4))
    cues = [("whoosh", t) for t in appear if t is not None] + ([("crack", crack)] if crack is not None else [])
    return Custom(fn, cues=cues, punch=[(crack, 0.07)] if crack is not None else [])


def push_arrows(T0, xs=(995, 835), ys=(650, 770, 890), color=RED, T1=None, w=22, head=48):
    def fn(c, T):
        if T1 is not None and T >= T1: return
        for i, y in enumerate(ys):
            t0 = T0 + i * 0.15
            if T < t0: continue
            a = prog(T, t0, t0 + 0.2); nudge = 14 * math.sin((T - t0) * 8)
            arrow(c, xs[0] - nudge, y, xs[1] - nudge, y, w, color, head, alpha=a)
    return Custom(fn, cues=[("pop", T0 + i * 0.15) for i in range(len(ys))])


def air_flow(T0, T1):
    """cabin air dots sliding under the inner pane and through the hole into the gap"""
    x0, x1, sp, gap = 960, 560, 560, 0.26
    def fn(c, T):
        if T < T0 or T > T1: return
        i = 0
        while True:
            t0 = T0 + i * gap
            if t0 > T: break
            x = x0 - sp * (T - t0)
            if x > x1:
                a = prog(T, t0, t0 + 0.1); line(c, x + 14, HY, x + 70, HY, 8, WHITE, 0.6 * a); circ(c, x, HY, 15, fill=WHITE, line=BLACK, lw=6, alpha=a)
            i += 1
    return Custom(fn, cues=[("tick", T0 + i * gap) for i in range(8)])


def drops(T0, Te):
    """moisture beads in the gap; they slide down and out through the hole"""
    ys = [520 + i * 55 for i in range(7)]
    def fn(c, T):
        for i, y0 in enumerate(ys):
            tp = T0 + i * 0.12
            if T < tp: continue
            x0 = 565 + 14 * math.sin(i * 2.1); k = max(e_back(prog(T, tp, tp + 0.25), 2.0), 0.01); x, y, a = x0, y0, 1.0
            te = Te + i * 0.12
            if T >= te:
                p = prog(T, te, te + 0.9)
                if p < 0.5: y = lerp(y0, HY, e_in(p * 2))
                else: y = HY; x = lerp(x0, 745, e_out((p - 0.5) * 2))
                a = 1 - prog(p, 0.85, 1.0)
            c.save(); c.translate(x, y); c.scale(k, k)
            poly(c, [(0, -38), (-17, -6), (17, -6)], fill="#7CC6FF", line_c=BLACK, lw=5, alpha=a); circ(c, 0, 6, 18, fill="#7CC6FF", line=BLACK, lw=6, alpha=a); c.restore()
    return Custom(fn, cues=[("bloop", T0 + i * 0.12) for i in range(7)] + [("whoosh", Te)])


def build():
    N = lambda **kw: Narrator(x=NX, y=NY, s=NS, **kw)
    sides = lambda t: [Tag("OUTSIDE", t, x=265, y=530, size=40, fill=WHITE, sfx=None), Tag("CABIN", t, x=905, y=530, size=40, fill=WHITE, sfx=None)]
    return [
        Scene(0, bg="#FF8FA3", trans="auto", layers=[
            N(pose="wide", smile=0.7),
            Headline("WHY DO AIRPLANE", at("why"), y=170, size=84), Headline("WINDOWS HAVE", at("windows"), y=265, size=84),
            Headline("A TINY HOLE?", at("tiny"), y=385, size=118, fill=YEL),
            window_layer(0.1, 640, 790, 0.9, ring_at=0.6), QMarks(at("have"), spots=((150, 600), (1010, 620), (990, 1040)))]),
        Scene(at("it's not"), bg="#FFD166", trans="auto", layers=[
            N(pose="point", smile=0.8),
            Headline("NOT A MISTAKE", at("not"), y=190, size=100), Headline("BLEED HOLE", at("bleed"), y=315, size=126, fill=RED),
            window_layer(at("it's not"), 640, 830, 0.85, ring_at=at("it's not")), Burst(at("bleed"), 640, 940, 0.8)]),
        Scene(at("your window"), bg="#CDB4DB", trans="auto", layers=[
            N(pose="point"), *sides(at("your")),
            Headline("YOUR WINDOW", at("your"), y=190, size=100), Headline("3 PANES", at("three"), y=315, size=126, fill=RED),
            xsec(appear=(at("really"), at("three"), at("panes"))),
            Tag("OUTER", at("really", off=0.3), x=470, y=1105, size=38, fill=OUTER), Tag("MIDDLE", at("three", off=0.3), x=640, y=1180, size=38, fill=MID),
            Tag("INNER", at("panes", off=0.3), x=810, y=1105, size=38, fill=INNER)]),
        Scene(at("at cruising"), bg="#B8F2C9", trans="auto", layers=[
            N(pose="worry", brow=-0.4, smile=0.1), *sides(at("at cruising")),
            Headline("CRUISING ALTITUDE", at("cruising"), y=190, size=78), Headline("PRESSURE!", at("pressurized"), y=310, size=126, fill=RED),
            xsec(), push_arrows(at("pressurized")), Burst(at("hard"), 830, 720, 0.7)]),
        Scene(at("the hole"), bg="#BDE0FE", trans="auto", layers=[
            N(pose="point"), *sides(at("the hole")),
            Headline("OUTER PANE", at("outer"), y=190, size=100), Headline("TAKES THE LOAD", at("takes"), y=305, size=84, fill=RED),
            xsec(gap_t=at("lets")), air_flow(at("lets"), at("outer")),
            push_arrows(at("takes"), xs=(602, 534), ys=(560, 700, 840), w=16, head=34),
            Mark("check", at("load", off=0.35), 905, 770, s=1.8)]),
        Scene(at("the middle"), bg="#CDB4DB", trans="auto", layers=[
            N(pose="hands_up"), *sides(at("the middle")),
            Headline("MIDDLE PANE", at("middle"), y=190, size=100), Headline("BACKUP", at("backup"), y=315, size=130, fill=YEL),
            xsec(glow=(at("middle"), at("outer", 1)), crack=at("compromised")),
            Stamp("IT HOLDS!", at("compromised", off=0.5), 690, 1200, color=GREEN, fill=WHITE, w=500, h=150, size=84, rot=-7)]),
        Scene(at("the hole also"), bg="#B8F2C9", trans="auto", layers=[
            N(pose="wide", smile=0.7), *sides(at("the hole also")),
            Headline("MOISTURE OUT", at("moisture"), y=190, size=100), Headline("NO FOG", at("fog"), y=315, size=126, fill=WHITE),
            xsec(fog=(at("also"), at("escape"))), drops(at("moisture"), at("escape")),
            Mark("check", at("fog", off=0.4), 905, 770, s=1.8)]),
        Scene(at("so that"), bg="#FF8FA3", trans="auto", layers=[
            N(pose="hands_up", smile=0.8),
            Headline("THAT DOT?", at("dot"), y=190, size=130), Headline("SAFETY FEATURE", at("safety"), y=315, size=84, fill=YEL),
            window_layer(at("so that"), 640, 800, 0.9, ring_at=at("dot")),
            Burst(at("feature"), 640, 600, 1.0, colors=(YEL, WHITE, BLUE, GREEN, PINK))]),
    ]
