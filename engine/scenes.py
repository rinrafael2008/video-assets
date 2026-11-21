import math, json, random
import skia
from eng import *
import eng

WORDS = [tuple(w) for w in json.load(open("/home/claude/work/engine/words.json"))]
CHUNKS = build_chunks(WORDS)
B = [0, 1.75, 7.45, 10.9, 12.85, 14.95, 24.8, 28.9, 31.85]
TOTAL = B[-1]
Y_FEET = 1290


def breathe(T, a=3.0): return a * math.sin(T * 3.1)


def narr(c, x, y, s, T, **kw):
    kw.setdefault("mouth", mouth_at(T)); kw.setdefault("eyes", blink_at(T))
    hip = kw.pop("hip", (0, 0)); kw["hip"] = (hip[0], hip[1] + breathe(T))
    stick(c, x, y, s, **kw)


# ------------------------------------------------------------------ props
def bone_shape(c, x1, y, x2, thick=84, bulb=46, left_end=True, right_end=True, fill=WHITE, lw=12, alpha=1.0):
    """horizontal bone; outline pass then fill pass so the union has one outline"""
    for pas in (0, 1):
        col = BLACK if pas == 0 else fill; grow = lw if pas == 0 else 0
        line(c, x1, y, x2, y, thick + grow * 2, col, alpha)
        for (ex, on) in ((x1, left_end), (x2, right_end)):
            if on:
                for sg in (-1, 1): c.drawCircle(ex, y + sg * thick * 0.42, bulb + grow, paint(col, alpha))

def bone_icon(c, x, y, s=1.0, rotd=0.0, alpha=1.0):
    c.save(); c.translate(x, y); c.rotate(rotd); c.scale(s, s)
    bone_shape(c, -150, 0, 150, thick=46, bulb=30, alpha=alpha, lw=10); c.restore()

def trophy(c, x, y, s=1.0, alpha=1.0):
    gold, dark = "#FFC93C", "#E3A008"
    c.save(); c.translate(x, y); c.scale(s, s)
    rrect(c, 0, 170, 250, 46, 14, fill=dark, line=BLACK, lw=10, alpha=alpha)
    rrect(c, 0, 118, 60, 80, 8, fill=gold, line=BLACK, lw=10, alpha=alpha)
    rrect(c, 0, 70, 150, 30, 10, fill=dark, line=BLACK, lw=10, alpha=alpha)
    for sg in (-1, 1):
        p = skia.Path(); p.moveTo(sg * 118, -80); p.cubicTo(sg * 220, -90, sg * 210, 40, sg * 80, 40)
        c.drawPath(p, paint(BLACK, alpha, 34)); c.drawPath(p, paint(gold, alpha, 16))
    p = skia.Path(); p.moveTo(-130, -140); p.lineTo(130, -140); p.cubicTo(130, 20, 70, 70, 0, 70); p.cubicTo(-70, 70, -130, 20, -130, -140); p.close()
    c.drawPath(p, paint(gold, alpha)); c.drawPath(p, paint(BLACK, alpha, 11))
    poly(c, star_pts(0, -40, 44, 18, 5, -math.pi / 2), fill=WHITE, line_c=BLACK, lw=6, alpha=alpha)
    c.restore()

def tiny_person(c, x, y, s, alpha=1.0, bob=0.0, head=WHITE):
    c.save(); c.translate(x, y + bob); c.scale(s, s)
    p = skia.Path(); p.moveTo(0, -26); p.lineTo(0, 4); p.moveTo(0, 4); p.lineTo(-8, 22); p.moveTo(0, 4); p.lineTo(8, 22)
    p.moveTo(-10, -18); p.lineTo(10, -18)
    c.drawPath(p, paint(BLACK, alpha, 5)); circ(c, 0, -38, 11, fill=head, line=BLACK, lw=5, alpha=alpha); c.restore()

def arrow(c, x1, y1, x2, y2, w=14, color=BLACK, head=34, alpha=1.0):
    a = math.atan2(y2 - y1, x2 - x1)
    line(c, x1, y1, x2 - math.cos(a) * head * 0.6, y2 - math.sin(a) * head * 0.6, w, color, alpha)
    poly(c, [(x2, y2), (x2 - head * math.cos(a - 0.5), y2 - head * math.sin(a - 0.5)),
             (x2 - head * math.cos(a + 0.5), y2 - head * math.sin(a + 0.5))], fill=color, line_c=color, lw=4, alpha=alpha)


# ------------------------------------------------------------------ S1  hook (0 - 1.75)
def cam1(t, T):
    z = 1 + 0.10 * decay(t, 0.28, 6) + 0.05 * decay(t, 0.95, 7)
    sx, sy = shake(t, 0.28, 12); sx2, sy2 = shake(t, 0.95, 8)
    return Cam(z, 540, 900, 0.0, sx + sx2, sy + sy2)

def s1(c, t, T):
    sc, fx = 1.6, 540
    kin = prog(t, 0.0, 0.26); kth = e_back(prog(t, 0.26, 0.40), 2.4)
    sep = lerp(26, 150, kth) if t >= 0.26 else lerp(60, 26, e_io(kin))
    hy = lerp(-330, -318, kth) if t >= 0.26 else -330
    sq = 0.08 * pulse(t, 0.26, 0.36) - 0.03 * pulse(t, 0.0, 0.26)
    tilt = 0.1 * math.sin(t * 24) * decay(t, 0.3, 5) + (0.08 * math.sin((t - 0.95) * 22) * decay(t, 0.95, 5))
    brow = 0.5 * prog(t, 0.89, 1.0)
    cx_ = fx; ground = 1335
    narr(c, cx_, ground, sc, T, hl=(-sep, hy), hr=(sep, hy), fists=True, squash=sq, tilt=tilt, brow=brow, smile=0.7 if t > 0.6 else 0.3, look=(0, 0))
    # headline text
    pop_text(c, "THAT CRACK ISN'T", 540, 175, 92, t, -0.3, fill=WHITE, sw=13)
    pop_text(c, "YOUR BONES", 540, 300, 126, t, 0.89, fill=RED, sw=15)
    # bone with X
    k = prog(t, 1.0, 1.25)
    if t >= 0.95:
        sp = max(e_back(prog(t, 0.95, 1.2), 2.4), 0.01)
        bone_icon(c, 850, 560, 0.95 * sp, 24)
        if t >= 1.05:
            cross(c, 850, 560, 1.7 * max(e_back(prog(t, 1.05, 1.28), 3.0), 0.01))
    # crack FX
    fxp = (540, ground - 320 * sc)
    rays(c, t, 0.28, fxp[0], fxp[1], 16, 110, 480, 0.35, 16, WHITE)
    ring(c, t, 0.28, fxp[0], fxp[1], 380, 0.4, 20, WHITE)
    burst(c, t, 0.28, fxp[0], fxp[1], 14, 620, 0.65, 18, (YEL, WHITE, ORANGE), 700, 3, "star")
    starburst(c, "CRACK!", 820, 760, 190, t, 0.3, hold=0.55)
    flash(c, t, 0.28, 0.45, 0.14)
    ring(c, t, 0.98, 850, 560, 320, 0.4, 18, RED, 0.9)


# ------------------------------------------------------------------ S2  joint diagram (1.75 - 7.45)
def joint_gap(t):
    tension = 12 * prog(t, 0.2, 1.35) + 2.5 * math.sin(t * 50) * (1 if 0.3 < t < 1.35 else 0)
    snap = e_back(prog(t, 1.36, 1.62), 2.6)
    return 96 + tension + 142 * snap

def cam2(t, T):
    z = lerp(0.95, 1.0, e_out(prog(t, 0, 1.4))); z = lerp(z, 1.2, e_io(prog(t, 2.2, 3.3)))
    z += 0.08 * decay(t, 4.7, 6) + 0.05 * decay(t, 1.36, 8)
    g = joint_gap(t); sx, sy = shake(t, 4.7, 14); sx2, sy2 = shake(t, 1.36, 9)
    return Cam(z, 430 + g / 2 + 10, 800, 0.02 * math.sin(t * 1.5), sx + sx2, sy + sy2)

def s2(c, t, T):
    xL, y = 430, 800; g = joint_gap(t); xR = xL + g
    rrect(c, 540, y, 1700, 300, 150, fill="#FFE0C7", line=BLACK, lw=12)
    # fluid
    wob = 8 * math.sin(t * 5)
    fl_alpha = 0.92
    rrect(c, xL + g / 2, y, g + 360 + wob, 270 + wob, 120, fill="#7CC6FF", line="#2F7BD9", lw=10, alpha=fl_alpha)
    for i in range(6):  # drifting droplets in the fluid
        dx = (i * 83 + t * 40 * (1 + i % 3)) % (g + 300) - (g + 300) / 2
        circ(c, xL + g / 2 + dx, y - 92 + (i % 3) * 90 + 6 * math.sin(t * 3 + i), 9 + (i % 2) * 5, fill="#CFEAFF", line=None, alpha=0.8)
    # bones
    bone_shape(c, -200, y, xL, left_end=False, right_end=True)
    bone_shape(c, xR, y, 1350 + 0 * t, left_end=True, right_end=False)
    # cavity
    if t >= 3.2:
        rr = 74 * max(e_back(prog(t, 3.2, 3.6), 1.6), 0.0) * (1 + 0.04 * math.sin(t * 18))
        circ(c, xL + g / 2, y, rr, fill="#F4FBFF", line="#2F7BD9", lw=8)
        if rr > 20:
            p = skia.Path(); p.addArc(skia.Rect(xL + g / 2 - rr * 0.62, y - rr * 0.62, xL + g / 2 + rr * 0.62, y + rr * 0.62), 200, 60)
            c.drawPath(p, paint(WHITE, 1, 9))
    # pull arrow (right side)
    if 0.18 <= t < 1.5:
        k = e_out(prog(t, 0.18, 0.5)); sh_ = 14 * math.sin(t * 40) * (t > 0.5)
        arrow(c, 760, y - 190, 900 + sh_, y - 190, 20, BLACK, 46, alpha=k)
        pop_text(c, "PULL", 830, y - 270, 66, t, 0.18, fill=WHITE, sw=11)
    # tags
    tag(c, "KNUCKLE JOINT", 540, 320, 72, t, 0.44, fill=WHITE)
    if 2.6 <= t < 4.45:
        tag(c, "TINY GAP", xL + g / 2, y - 330, 58, t, 2.6, fill=YEL)
        arrow(c, xL + g / 2, y - 268, xL + g / 2, y - 130, 12, BLACK, 30, alpha=prog(t, 2.7, 2.9))
    if t >= 3.84:
        tag(c, "JOINT FLUID", xL + g / 2, y + 262, 58, t, 3.84, fill="#7CC6FF")
        arrow(c, xL + g / 2, y + 206, xL + g / 2 + 40, y + 140, 12, BLACK, 30, alpha=prog(t, 3.9, 4.1))
    # snap + pop FX
    ring(c, t, 1.36, xL + g / 2, y, 330, 0.4, 16, WHITE)
    rays(c, t, 1.36, xL + g / 2, y, 14, 100, 380, 0.3, 12, WHITE)
    ring(c, t, 3.2, xL + g / 2, y, 200, 0.4, 14, WHITE)
    rays(c, t, 4.7, xL + g / 2, y, 20, 130, 560, 0.4, 16, WHITE)
    ring(c, t, 4.7, xL + g / 2, y, 440, 0.5, 20, WHITE)
    burst(c, t, 4.7, xL + g / 2, y, 16, 640, 0.7, 18, (YEL, WHITE, "#7CC6FF"), 600, 5, "star")
    starburst(c, "POP!", xL + g / 2 + 340, y - 190, 175, t, 4.7, hold=0.9)
    flash(c, t, 4.7, 0.5, 0.15)


# ------------------------------------------------------------------ S3  MRI (7.45 - 10.9)
def cam3(t, T):
    z = lerp(0.96, 1.1, e_io(prog(t, 0, 3.4))) + 0.04 * decay(t, 2.69, 8)
    return Cam(z, 540, 830, 0.025 * math.sin(t * 1.3), *shake(t, 2.69, 8))

def s3(c, t, T):
    cx, cy = 540, 820
    rrect(c, cx, cy, 840, 800, 130, fill=WHITE, line=BLACK, lw=14)
    rrect(c, cx - 300, cy - 330, 80, 26, 13, fill="#C9D6E8", line=BLACK, lw=6)
    circ(c, cx, cy, 310, fill=BLUE, line=BLACK, lw=14)
    circ(c, cx, cy, 262, fill="#12163A", line=BLACK, lw=10)
    c.save(); pth = skia.Path(); pth.addCircle(cx, cy, 258); c.clipPath(pth, True)
    for i in range(4): circ(c, cx, cy, 250 - i * 55, fill=None, line="#1F2A6B", lw=5)
    sy = cy + 190 * math.sin(t * 3.0)
    for k in range(5): line(c, cx - 260, sy - k * 12, cx + 260, sy - k * 12, 8 - k, "#5CF2FF", 0.55 - k * 0.1)
    # finger entering from the bottom
    capsule(c, cx, cy + 300, cx, cy - 70, 78, fill="#FFE8D6", line_c=BLACK, lw=9)
    for jy in (cy + 40, cy + 150): line(c, cx - 30, jy, cx + 30, jy, 6, BLACK)
    glow = pulse(t, 2.69, 0.5)
    if glow > 0:
        circ(c, cx, cy + 40, 70 * glow, fill="#FFFFFF", line=None, alpha=0.9)
    c.restore()
    rrect(c, cx, cy + 395, 560, 46, 23, fill="#DDE6F0", line=BLACK, lw=9)
    # year counter
    n = int(2015 * e_out(prog(t, 0.77, 1.35))) if t >= 0.77 else 0
    if t >= 0.2:
        k = max(e_back(prog(t, 0.2, 0.5)), 0.01)
        txt = "%d" % n if t >= 0.77 else "????"
        text(c, txt, 540, 250, 190, fill=WHITE, sw=18, scale=k * (1 + 0.1 * pulse(t, 1.3, 0.3)))
    tag(c, "MRI", 835, 420, 78, t, 1.95, fill=YEL, rot=8)
    if t >= 2.69:
        on = int((t - 2.69) * 3) % 2 == 0
        circ(c, 430, 650, 17, fill=RED if on else "#7A1F28", line=None, lw=0)
        text(c, "REC", 505, 650, 44, fill=WHITE, sw=0, shadow=False)
    ring(c, t, 2.69, cx, cy + 40, 330, 0.5, 14, WHITE)
    ring(c, t, 0.77, 540, 250, 380, 0.5, 14, WHITE)


# ------------------------------------------------------------------ S4  question (10.9 - 12.85)
def cam4(t, T):
    z = lerp(1.0, 1.16, e_io(prog(t, 0, 1.9))) + 0.05 * decay(t, 0.92, 7)
    return Cam(z, 540, 925, 0.035 * math.sin(t * 2.0) * prog(t, 0.9, 1.2), *shake(t, 0.92, 12))

def s4(c, t, T):
    sc = 1.6
    br = -0.8 * prog(t, 0.0, 0.5)
    lk = (-0.6, 0.6) if t < 0.9 else (0.2, 0)
    narr(c, 540, 1320, sc, T, hl=(-30, -420), hr=(60, -350), fists=True, brow=br, browup=0.8, smile=-0.3,
         eyes=min(blink_at(T), 1.0), look=lk, sweat=0.5 + 0.5 * math.sin(T * 4), tilt=0.07 * math.sin(T * 2), mouth=0.0 if t < 0.5 else mouth_at(T) * 0.8)
    for i, (qx, qy, q0, rr) in enumerate(((220, 560, 0.55, -14), (860, 500, 0.7, 12), (140, 880, 0.85, -8), (930, 820, 0.95, 10))):
        if t >= q0:
            k = max(e_back(prog(t, q0, q0 + 0.3)), 0.01)
            bob = 12 * math.sin(T * 5 + i)
            text(c, "?", qx, qy + bob, 170 + 20 * (i % 2), fill=YEL, sw=14, scale=k, rot=rr + 5 * math.sin(T * 4 + i))
    pop_text(c, "ARTHRITIS?", 540, 265, 150, t, 0.92, fill=RED, sw=16, rot=-3)
    ring(c, t, 0.92, 540, 265, 420, 0.4, 14, WHITE)
    burst(c, t, 0.92, 540, 265, 10, 500, 0.6, 14, (YEL, WHITE), 500, 8, "star")


# ------------------------------------------------------------------ S5  doctor (12.85 - 14.95)
def cam5(t, T):
    return Cam(lerp(1.0, 1.08, e_io(prog(t, 0, 2.1))) + 0.04 * decay(t, 1.35, 8), 540, 900, 0, *shake(t, 1.35, 8))

def s5(c, t, T):
    sc = 1.55
    xdoc = lerp(-150, 540, e_out(prog(t, 0.0, 0.95)))
    walking = t < 0.98
    ph = 2 * math.pi * (xdoc + 150) / (4 * 62 * sc * 0.82)
    if walking:
        kw = walk_kw(ph, stride=62, lift=46, bob=12)
    else:
        kk = e_back(prog(t, 1.2, 1.4), 2.0)
        kw = dict(hl=lerp(-60, -34, kk) and (lerp(-62, -34, kk), lerp(-232 + 0 * kk, -330, kk)),
                  hr=(lerp(62, 34, kk), lerp(-232, -330, kk)), lean=0.0, hip=(0, 4 * math.sin(T * 4)))
        kw["hl"] = (lerp(-62, -36, kk), lerp(-232, -318, kk)); kw["hr"] = (lerp(62, 36, kk), lerp(-232, -318, kk))
    sq = 0.07 * pulse(t, 1.35, 0.3)
    narr(c, xdoc, 1320, sc, T, outfit="doc", fists=True, smile=0.8, squash=sq, brow=0.0, tilt=0.12 * prog(t, 1.35, 1.6), cheeks=0.0, **kw)
    tag(c, "DR. DONALD UNGER", 540, 330, 66, t, 0.41, fill=WHITE, rot=-3)
    if t >= 1.35:
        rays(c, t, 1.35, 540, 880, 14, 260, 520, 0.35, 12, WHITE)
        burst(c, t, 1.35, 540, 880, 12, 480, 0.6, 14, (YEL, WHITE, PINK), 600, 11, "star")


# ------------------------------------------------------------------ S6  hands (14.95 - 24.8)
def bg6(T):
    return mix_hex("#FFD166", "#B8F2C9", e_io(prog(T - B[5], 6.0, 6.6)))

def cam6(t, T):
    # wide -> right fist (3.8) -> wide (6.0) -> trophy
    z, cx, cy = 1.0, 540, 800
    k = e_io(prog(t, 3.8, 4.45)); z = lerp(z, 1.55, k); cx = lerp(cx, 790, k); cy = lerp(cy, 780, k)
    k2 = e_io(prog(t, 6.0, 6.6)); z = lerp(z, 1.0, k2); cx = lerp(cx, 540, k2); cy = lerp(cy, 800, k2)
    z += 0.05 * decay(t, 4.99, 7) + 0.03 * decay(t, 1.39, 9) + 0.03 * decay(t, 2.81, 9) + 0.03 * decay(t, 3.19, 9)
    sx = sy = 0.0
    for t0, a in ((1.39, 9), (2.81, 9), (3.19, 9), (4.99, 14)):
        a_, b_ = shake(t, t0, a); sx += a_; sy += b_
    return Cam(z, cx, cy, 0.0, sx, sy)

def s6(c, t, T):
    # trophy phase first so it sits behind fists leaving
    out = e_io(prog(t, 7.7, 8.15))
    ly, ry = 700, 700
    lx = lerp(290, -320, out); rx = lerp(790, 1400, out)
    # left fist
    crack_l = max(decay(t, 1.39, 12), decay(t, 2.81, 12), decay(t, 3.19, 12))
    sq_l = crack_l * 1.0
    bob = 6 * math.sin(T * 3)
    fist(c, lx, ly + bob, 1.05, rotd=-3 + 4 * crack_l * math.sin(t * 60), crack=crack_l, squeeze=sq_l, arm=900)
    fist(c, rx, ry - bob, 1.05, rotd=3, crack=0, arm=900, mirror=True)
    # labels
    tag(c, "LEFT", 290 if out == 0 else lx, 1010, 62, t, 2.15, fill=YEL, rot=-3)
    tag(c, "RIGHT", 790 if out == 0 else rx, 1010, 62, t, 4.05, fill=WHITE, rot=3)
    if 4.1 <= t < 4.9 and out < 1:
        z_ = pulse(T, 0, 1.0)
        for i in range(3):
            text(c, "z", rx + 150 + i * 36, 480 - i * 70 - 14 * math.sin(T * 2 + i), 56 + i * 14, fill=WHITE, sw=8, alpha=0.9 - i * 0.2, shadow=False)
    # crack FX on left fist
    for t0 in (1.39, 2.81, 3.19):
        ring(c, t, t0, lx + 110, ly - 80, 250, 0.35, 14, WHITE)
        rays(c, t, t0, lx + 110, ly - 80, 12, 80, 300, 0.3, 12, WHITE)
        burst(c, t, t0, lx + 110, ly - 80, 8, 420, 0.5, 14, (YEL, WHITE, ORANGE), 500, int(t0 * 10), "star")
        flash(c, t, t0, 0.18, 0.1)
    starburst(c, "CRACK!", 230, 440, 130, t, 1.39, hold=0.5, rot=-10)
    starburst(c, "CRACK!", 340, 430, 130, t, 2.81, hold=0.28, rot=8)
    starburst(c, "CRACK!", 220, 460, 130, t, 3.19, hold=0.5, rot=-6)
    # counter 60 YEARS
    if 0.5 <= t < 4.0:
        n = int(60 * e_out(prog(t, 0.53, 1.2)))
        k = max(e_back(prog(t, 0.5, 0.8)), 0.01) * (1 - prog(t, 3.7, 3.9))
        s_ = "%d+ YEARS" % n if n >= 60 or t > 1.2 else "%d YEARS" % n
        text(c, s_ if t < 1.2 else "60+ YEARS", 540, 250, 130, fill=WHITE, sw=16, scale=max(k, 0.001) * (1 + 0.08 * pulse(t, 1.2, 0.3)))
    if 2.81 <= t < 4.0:
        tag(c, "2x A DAY", 540, 1160, 66, t, 2.81, fill=WHITE, rot=-2)
    # CONTROL stamp
    if t >= 4.99 and t < 6.4:
        k = prog(t, 4.99, 5.14); sc_ = lerp(2.6, 1.0, e_out5(k)) if k < 1 else 1.0
        c.save(); c.translate(790, 470); c.rotate(-12); c.scale(sc_, sc_)
        rrect(c, 0, 0, 470, 150, 24, fill=None, line=RED, lw=14, alpha=min(1.0, k * 1.6))
        text(c, "CONTROL", 0, 0, 100, fill=RED, stroke=WHITE, sw=0, shadow=False, alpha=min(1.0, k * 1.6))
        c.restore()
        ring(c, t, 5.12, 790, 470, 360, 0.4, 16, WHITE)
    # checks + no arthritis
    if t >= 6.85 and out < 1:
        for (px, t0) in ((lx, 6.85), (rx, 7.0)):
            if t >= t0: check(c, px, 380, 2.0 * max(e_back(prog(t, t0, t0 + 0.3), 2.4), 0.01))
        ring(c, t, 6.85, lx, 380, 300, 0.4, 14, WHITE); ring(c, t, 7.0, rx, 380, 300, 0.4, 14, WHITE)
        pop_text(c, "NO ARTHRITIS", 540, 190, 112, t, 6.9, fill=WHITE, sw=14)
    # trophy
    if t >= 8.0:
        k = e_back(prog(t, 8.0, 8.55), 1.4); ty = lerp(1500, 900, k)
        trophy(c, 540, ty, 1.55)
        pop_text(c, "IG NOBEL", 540, 330, 150, t, 8.37, fill=YEL, sw=16, rot=-2)
        pop_text(c, "PRIZE", 540, 470, 120, t, 9.0, fill=WHITE, sw=14, rot=2)
        if t >= 8.37:
            burst(c, t, 8.37, 540, 760, 70, 950, 1.4, 24, (YEL, PINK, BLUE, GREEN, WHITE), 900, 21, "rect", (math.pi * 1.05, math.pi * 1.95))
            ring(c, t, 8.37, 540, 800, 500, 0.5, 16, WHITE)
            rays(c, t, 8.37, 540, 800, 18, 160, 600, 0.4, 14, WHITE)
        for i in range(4):
            tt = (T * 2.2 + i * 0.7) % 2.0
            if t >= 8.7:
                sp = pulse(tt, 0, 0.6); poly(c, star_pts(300 + i * 160, 700 + 80 * math.sin(i * 2), 26 * sp, 8 * sp, 4), fill=WHITE, line_c=None)


# ------------------------------------------------------------------ S7  215 people (24.8 - 28.9)
COLS, N_PEOPLE = 18, 215
def cam7(t, T):
    a = e_io(prog(t, 0.6, 0.95)); k = e_io(prog(t, 1.0, 2.3))
    z = lerp(lerp(1.0, 1.15, a), 1.0, k); cx = 540; cy = lerp(lerp(960, 800, a), 960, k)
    z += 0.04 * decay(t, 2.9, 8)
    return Cam(z, cx, cy, 0, *shake(t, 2.9, 10))

def s7(c, t, T):
    x0, y0, spx, spy = 81, 372, 54, 80
    heads = [PINK, YEL, "#BDE0FE", "#B8F2C9", WHITE, "#FFB38A"]
    dim = 1.0 - 0.55 * prog(t, 2.9, 3.1)
    for i in range(N_PEOPLE):
        r, col = divmod(i, COLS)
        t0 = 0.95 + i * 0.0042 + col * 0.0
        if t < t0: continue
        k = max(e_back(prog(t, t0, t0 + 0.22), 2.0), 0.01)
        wave = 3.5 * math.sin(T * 4 - (r + col) * 0.5) if t > 2.3 else 0
        tiny_person(c, x0 + col * spx, y0 + r * spy, 0.8 * k, alpha=dim, bob=wave, head=heads[(i * 7 + r) % 6])
    # counter
    n = min(N_PEOPLE, int((t - 0.95) / 0.0042)) if t >= 0.95 else 0
    k = max(e_back(prog(t, 0.55, 0.85)), 0.01)
    if t < 0.95: pop_text(c, "A LATER STUDY", 540, 250, 100, t, 0.03, fill=WHITE, sw=14)
    else:
        text(c, "%d PEOPLE" % max(n, 1) if t < 2.0 else "215 PEOPLE", 540, 250, 118, fill=WHITE, sw=14, scale=1.0 + 0.06 * pulse(t, 1.9, 0.3))
    # stamp
    if t >= 2.9:
        k = prog(t, 2.9, 3.05); sc_ = lerp(2.8, 1.0, e_out5(k)) if k < 1 else 1.0
        c.save(); c.translate(540, 830); c.rotate(-9); c.scale(sc_, sc_)
        rrect(c, 0, 0, 700, 230, 34, fill=WHITE, line=GREEN, lw=18, alpha=min(1.0, k * 1.8))
        text(c, "NO LINK", 0, 0, 168, fill=GREEN, stroke=BLACK, sw=0, shadow=False, alpha=min(1.0, k * 1.8))
        c.restore()
        ring(c, t, 3.0, 540, 830, 520, 0.45, 18, WHITE)
        burst(c, t, 3.0, 540, 830, 18, 700, 0.8, 16, (GREEN, WHITE, YEL), 600, 7, "star")


# ------------------------------------------------------------------ S8  finale (28.9 - 31.85)
def cam8(t, T):
    z = lerp(1.0, 1.06, prog(t, 0, 2.9)) + 0.03 * decay(t, 1.78, 8)
    return Cam(z, 540, 900, 0, *shake(t, 1.78, 6))

def s8(c, t, T):
    sc = 1.45
    # narrator: shakes head 'no', then sheepish
    shy = prog(t, 1.7, 2.0)
    kw = dict(hl=(-62, -232), hr=(62, -232))
    if shy > 0:  # sheepish shrug: both hands up beside the shoulders
        e = e_out(shy)
        kw["hl"] = (lerp(-62, -135, e), lerp(-232, -345 + 8 * math.sin(T * 9), e)); kw["hr"] = (lerp(62, 135, e), lerp(-232, -345 + 8 * math.sin(T * 9 + 1), e))
    tilt = 0.12 * math.sin(t * 8) * (1 - shy) * (1 if 0.2 < t < 1.5 else 0) + 0.1 * shy
    narr(c, 330, Y_FEET, sc, T, fists=True, tilt=tilt, smile=0.6 if shy < 0.5 else -0.1, sweat=shy, look=(-0.6 * shy, 0.2 * shy), brow=-0.5 * shy, **kw)
    # mom
    ft = 12 * max(0.0, math.sin(T * 9))
    narr(c, 770, Y_FEET, sc, T, flip=-1, outfit="mom", hl=(30, -300), hr=(-30, -300), fr=(46, -ft), mouth=0.0, brow=0.8, smile=-0.2,
         eyes=blink_at(T, 3.3, 1.0), tilt=-0.05, fists=False)
    # bubbles / text
    pop_text(c, "NOT YOUR BONES", 540, 250, 108, t, 1.1, fill=WHITE, sw=14, rot=-2) if t < 1.7 else None
    pop_text(c, "SORRY, MOM", 540, 250, 130, t, 1.78, fill=RED, sw=16, rot=2)
    if t >= 2.2:
        k = max(e_back(prog(t, 2.2, 2.5)), 0.01)
        c.save(); c.translate(890, 420); c.scale(k, k)
        poly(c, [(-105, -42), (105, -42), (105, 42), (-105, 42)], fill=WHITE, line_c=BLACK, lw=9)
        poly(c, [(-70, 42), (-96, 96), (-20, 42)], fill=WHITE, line_c=BLACK, lw=9)
        line(c, -66, 40, -26, 40, 14, WHITE)
        text(c, "HMPH.", 0, 0, 48, fill=BLACK, sw=0, shadow=False); c.restore()
    burst(c, t, 1.78, 540, 250, 12, 480, 0.6, 14, (YEL, WHITE, PINK), 500, 4, "star")


# ------------------------------------------------------------------ timeline + transitions
FNS = [s1, s2, s3, s4, s5, s6, s7, s8]
CAMS = [cam1, cam2, cam3, cam4, cam5, cam6, cam7, cam8]
BGC = ["#FFD166", "#CDB4DB", "#B8F2C9", "#FF8FA3", "#BDE0FE", None, "#CDB4DB", "#FFD166"]
TRANS = ["iris", "up", "iris", "left", "diag", "iris", "up"]  # transition into scene i+1
HW = 0.13

def draw_scene(c, i, T):
    t = max(T - B[i], 0.0) if T < B[i] else T - B[i]
    col = BGC[i] if BGC[i] else bg6(T)
    draw_bg(c, T, col, seed=i + 3)
    c.save(); CAMS[i](t, T).apply(c); FNS[i](c, t, T); c.restore()

def wipe_path(kind, p):
    e = e_io(p); pth = skia.Path()
    if kind == "iris": pth.addCircle(W / 2, H / 2 - 100, e * 1500)
    elif kind == "up": pth.addRect(skia.Rect(0, H * (1 - e), W, H))
    elif kind == "left": pth.addRect(skia.Rect(W * (1 - e), 0, W, H))
    else:
        d = e * (W + H + 400) - 200
        pth.moveTo(-200, d - 0); pth.lineTo(W + 200, d - W - 200); pth.lineTo(W + 200, H + 200); pth.lineTo(-200, H + 200); pth.close()
        pth = skia.Path(); pth.moveTo(0, 0); pth.lineTo(W * 2 * e, 0); pth.lineTo(W * 2 * e - W * 0.0 - H * 0.6, H); pth.lineTo(0, H); pth.close()
    return pth

def frame(c, T):
    T = max(0.0, min(T, TOTAL - 0.001))
    k = None
    for j in range(1, len(B) - 1):
        if abs(T - B[j]) <= HW: k = j
    if k is None:
        i = max(j for j in range(len(FNS)) if T >= B[j] - HW - 1e-9) if T > 0 else 0
        for j in range(len(FNS)):
            if B[j] <= T < B[j + 1]: i = j
        draw_scene(c, i, T)
    else:
        p = (T - (B[k] - HW)) / (2 * HW)
        draw_scene(c, k - 1, T)
        c.save(); c.clipPath(wipe_path(TRANS[k - 1], p), skia.ClipOp.kIntersect, True)
        draw_scene(c, k, T); c.restore()
    draw_captions(c, eng.CAPT if eng.CAPT is not None else T, CHUNKS)
    # first-frame hook safety: nothing else
