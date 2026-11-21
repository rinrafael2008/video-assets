"""Scene kit: build a video from layers anchored to spoken words.

A project's scenes.py defines build(kit) -> [Scene, ...]. Times come from kit.at("word") (absolute seconds), so cues follow the
narration automatically. Layers register sound cues, camera punches and captions come for free.

    from kit import *
    def build():
        return [Scene(at("that"), bg=YEL, layers=[Narrator(pose="hands_up"), Headline("THAT CRACK ISN'T", at("that"), y=175),
                                                  Headline("YOUR BONES", at("bones"), y=300, fill=RED), Burst(at("bones"), 540, 700)]),
                Scene(at("pull"), bg=PINK, layers=[...])]
"""
import math, json, os
import skia
from eng import *
import eng

STATE = {"words": [], "chunks": [], "total": 0.0}


def load(proj, narration_len=None):
    words = [tuple(w) for w in json.load(open(os.path.join(proj, "words.json")))]
    STATE["words"] = words; STATE["chunks"] = build_chunks(words)
    eng.NODS[:] = [w[1] for w in words]
    eng.load_assets(os.path.join(proj, "narration.wav"), os.path.join(proj, "mouth.npz") if os.path.exists(os.path.join(proj, "mouth.npz")) else None)
    STATE["total"] = max((narration_len or 0) + 0.4, words[-1][2] + 0.5)


def _norm(w):
    return "".join(ch for ch in w.lower() if ch.isalnum() or ch == "'")


def at(phrase, n=0, end=False, off=0.0):
    """absolute time (s) when `phrase` (one or more words) is spoken; n = which occurrence; end=True -> when it ends"""
    toks = [_norm(x) for x in phrase.split()]; ws = STATE["words"]; hits = 0
    for i in range(len(ws) - len(toks) + 1):
        if [_norm(w[0]) for w in ws[i:i + len(toks)]] == toks:
            if hits == n: return (ws[i + len(toks) - 1][2] if end else ws[i][1]) + off
            hits += 1
    raise KeyError(f"word(s) '{phrase}' (occurrence {n}) not found in the transcript")


# ------------------------------------------------------------------ narrator
def breathe(T, a=3.0): return a * math.sin(T * 3.1)

POSES = {
    "idle": dict(hl=(-62, -232), hr=(62, -232)),
    "hands_up": dict(hl=(-135, -345), hr=(135, -345)),          # shrug / surprise
    "wide": dict(hl=(-170, -300), hr=(170, -300)),
    "cheer": dict(hl=(-120, -440), hr=(120, -440)),
    "worry": dict(hl=(-30, -420), hr=(60, -350)),               # hand at the head
    "point": dict(hl=(-62, -232), hr=(150, -390)),
}


def narr(c, x, y, s, T, **kw):
    if "mouth" not in kw:
        o, wd, th = mouth_params(T); kw["mouth"] = o; kw.setdefault("mwide", wd); kw.setdefault("teeth", th); kw["mouth_talk"] = True
    kw.setdefault("eyes", blink_at(T))
    hip = kw.pop("hip", (0, 0)); kw["hip"] = (hip[0], hip[1] + breathe(T) + nod_at(T))
    stick(c, x, y, s, **kw)


class Layer:
    cues = ()          # [(sfx_kind, seconds)]
    punch = ()         # [(seconds, amplitude)] camera punches
    def draw(self, c, T): pass


class Narrator(Layer):
    """Talking stickman. pose: name from POSES, dict of stick() kwargs, or callable(T)->dict. walk=(x0, x1, T0, T1) walks in."""
    def __init__(self, x=540, y=1290, s=1.6, pose="idle", outfit=None, flip=1, talk=True, walk=None, **kw):
        self.x, self.y, self.s, self.pose, self.outfit, self.flip, self.talk, self.walk, self.kw = x, y, s, pose, outfit, flip, talk, walk, kw
        if walk: self.cues = [("step", walk[2] + 0.1 + k * 0.21) for k in range(int((walk[3] - walk[2]) / 0.21))]

    def draw(self, c, T):
        p = self.pose(T) if callable(self.pose) else (POSES[self.pose] if isinstance(self.pose, str) else self.pose)
        kw = dict(p); kw.update(self.kw); x = self.x
        if self.walk:
            x0, x1, T0, T1 = self.walk; k = e_out(prog(T, T0, T1))
            x = lerp(x0, x1, k)
            if T < T1:
                kw.update(walk_kw(2 * math.pi * (x - x0) / (4 * 62 * self.s * 0.82), stride=62, lift=46, bob=12))
        if self.outfit: kw["outfit"] = self.outfit
        if self.flip != 1: kw["flip"] = self.flip
        kw.setdefault("fists", True)
        if self.talk: narr(c, x, self.y, self.s, T, **kw)
        else: stick(c, x, self.y, self.s, eyes=blink_at(T), **kw)


# ------------------------------------------------------------------ text + labels
class Headline(Layer):
    def __init__(self, s, T0, x=540, y=250, size=110, fill=WHITE, sw=14, rot=0, T1=None, sfx="pop"):
        self.a = (s, x, y, size); self.T0, self.T1, self.kw = T0, T1, dict(fill=fill, sw=sw, rot=rot)
        self.cues = [(sfx, T0)] if sfx else []
    def draw(self, c, T):
        if self.T1 is not None and T >= self.T1: return
        s, x, y, size = self.a; pop_text(c, s, x, y, size, T, self.T0, **self.kw)


class Tag(Layer):
    def __init__(self, s, T0, x=540, y=330, size=62, fill=YEL, rot=0, T1=None, sfx="pop"):
        self.a = (s, x, y, size); self.T0, self.T1, self.kw = T0, T1, dict(fill=fill, rot=rot)
        self.cues = [(sfx, T0)] if sfx else []
    def draw(self, c, T):
        if self.T1 is not None and T >= self.T1: return
        s, x, y, size = self.a; tag(c, s, x, y, size, T, self.T0, **self.kw)


class BigNumber(Layer):
    """counts up to `value` between T0 and T0+dur, then holds (fmt like '{:,} PEOPLE')"""
    def __init__(self, value, T0, fmt="{}", x=540, y=250, size=130, dur=0.7, fill=WHITE, sw=16, T1=None):
        self.v, self.T0, self.fmt, self.x, self.y, self.size, self.dur, self.fill, self.sw, self.T1 = value, T0, fmt, x, y, size, dur, fill, sw, T1
        self.cues = [("pop_hi", T0)] + [("tick", T0 + 0.03 + k * 0.04) for k in range(min(int(dur / 0.04), 24))]
    def draw(self, c, T):
        if T < self.T0 or (self.T1 is not None and T >= self.T1): return
        n = int(self.v * e_out(prog(T, self.T0, self.T0 + self.dur)))
        k = max(e_back(prog(T, self.T0, self.T0 + 0.28)), 0.01)
        text(c, self.fmt.format(n), self.x, self.y, self.size, fill=self.fill, sw=self.sw, scale=k * (1 + 0.08 * pulse(T, self.T0 + self.dur, 0.3)))
        ring(c, T, self.T0 + self.dur, self.x, self.y, 380, 0.5, 14, WHITE)


class Stamp(Layer):
    """slammed rubber stamp, e.g. Stamp('NO LINK', at('no link'), color=GREEN)"""
    def __init__(self, s, T0, x=540, y=830, color=RED, w=620, h=190, size=130, rot=-9, fill=None, T1=None):
        self.a = (s, x, y, color, w, h, size, rot, fill); self.T0, self.T1 = T0, T1
        self.cues = [("stamp", T0)]; self.punch = [(T0, 0.06)]
    def draw(self, c, T):
        s, x, y, color, w, h, size, rot, fill = self.a
        if T < self.T0 or (self.T1 is not None and T >= self.T1): return
        k = prog(T, self.T0, self.T0 + 0.15); sc_ = lerp(2.7, 1.0, e_out5(k)) if k < 1 else 1.0
        c.save(); c.translate(x, y); c.rotate(rot); c.scale(sc_, sc_)
        rrect(c, 0, 0, w, h, h * 0.16, fill=fill, line=color, lw=15, alpha=min(1.0, k * 1.7))
        text(c, s, 0, 0, size, fill=color, stroke=WHITE, sw=0, shadow=False, alpha=min(1.0, k * 1.7)); c.restore()
        ring(c, T, self.T0 + 0.12, x, y, w * 0.6, 0.4, 16, WHITE)


class Burst(Layer):
    """impact: ring + rays + particles (+ flash). sfx 'crack' | 'pop' | None"""
    def __init__(self, T0, x, y, size=1.0, colors=(YEL, WHITE, ORANGE), sfx="pop", flash_=True, punch=0.05):
        self.T0, self.x, self.y, self.size, self.colors, self.flash = T0, x, y, size, colors, flash_
        self.cues = [(sfx, T0)] if sfx else []; self.punch = [(T0, punch)] if punch else []
    def draw(self, c, T):
        t0, x, y, s = self.T0, self.x, self.y, self.size
        rays(c, T, t0, x, y, 16, 110 * s, 480 * s, 0.35, 16, WHITE); ring(c, T, t0, x, y, 380 * s, 0.4, 20, WHITE)
        burst(c, T, t0, x, y, 14, 620 * s, 0.65, 18, self.colors, 700, int(t0 * 10) % 97, "star")
        if self.flash: flash(c, T, t0, 0.14 + 0.0, 0.45)


class Starburst(Layer):
    def __init__(self, s, T0, x, y, size=170, hold=0.6, rot=-8, fill=YEL, sfx="crack"):
        self.a, self.T0 = (s, x, y, size, hold, rot, fill), T0
        self.cues = [(sfx, T0)] if sfx else []
    def draw(self, c, T):
        s, x, y, size, hold, rot, fill = self.a; starburst(c, s, x, y, size, T, self.T0, fill=fill, hold=hold, rot=rot)


class Prop(Layer):
    """pops in a prop drawn by fn(c, x, y, scale, rotd, alpha). enter='pop' or 'rise' (from below)."""
    def __init__(self, fn, T0, x, y, s=1.0, rot=0, T1=None, enter="pop", sfx="pop"):
        self.fn, self.T0, self.x, self.y, self.s, self.rot, self.T1, self.enter = fn, T0, x, y, s, rot, T1, enter
        self.cues = [(sfx, T0)] if sfx else []
    def draw(self, c, T):
        if T < self.T0 or (self.T1 is not None and T >= self.T1): return
        if self.enter == "rise":
            k = e_back(prog(T, self.T0, self.T0 + 0.55), 1.4); self.fn(c, self.x, lerp(self.y + 600, self.y, k), self.s, self.rot, 1.0)
        else:
            k = max(e_back(prog(T, self.T0, self.T0 + 0.3), 2.2), 0.01); self.fn(c, self.x, self.y, self.s * k, self.rot, 1.0)


class Mark(Layer):
    """check mark or cross that pops in"""
    def __init__(self, kind, T0, x, y, s=2.0, sfx="bell"):
        self.kind, self.T0, self.x, self.y, self.s = kind, T0, x, y, s; self.cues = [(sfx, T0)] if sfx else []
    def draw(self, c, T):
        if T < self.T0: return
        k = max(e_back(prog(T, self.T0, self.T0 + 0.3), 2.4), 0.01)
        (check if self.kind == "check" else cross)(c, self.x, self.y, self.s * k)
        ring(c, T, self.T0, self.x, self.y, 300, 0.4, 14, WHITE)


class QMarks(Layer):
    """floating question marks popping in one after another"""
    def __init__(self, T0, spots=((220, 560), (860, 500), (140, 880), (930, 820)), gap=0.15):
        self.T0, self.spots, self.gap = T0, spots, gap; self.cues = [("bloop", T0 + i * gap) for i in range(len(spots))]
    def draw(self, c, T):
        for i, (qx, qy) in enumerate(self.spots):
            q0 = self.T0 + i * self.gap
            if T >= q0:
                k = max(e_back(prog(T, q0, q0 + 0.3)), 0.01)
                text(c, "?", qx, qy + 12 * math.sin(T * 5 + i), 170 + 20 * (i % 2), fill=YEL, sw=14, scale=k, rot=(-14 if i % 2 == 0 else 12) + 5 * math.sin(T * 4 + i))


class Crowd(Layer):
    """grid of tiny people appearing over `dur` (the 'N people' shot)"""
    def __init__(self, T0, n=100, cols=12, x0=None, y0=372, spx=70, spy=84, dur=1.0, s=0.9, dim_at=None):
        self.T0, self.n, self.cols, self.y0, self.spx, self.spy, self.dur, self.s, self.dim_at = T0, n, cols, y0, spx, spy, dur, s, dim_at
        self.x0 = x0 if x0 is not None else 540 - (cols - 1) * spx / 2
        self.cues = [("tick", T0 + i * 0.025) for i in range(min(36, n // 4))]
    def draw(self, c, T):
        heads = [PINK, YEL, "#BDE0FE", "#B8F2C9", WHITE, "#FFB38A"]
        dim = 1.0 - (0.55 * prog(T, self.dim_at, self.dim_at + 0.2) if self.dim_at else 0)
        for i in range(self.n):
            r, col = divmod(i, self.cols); t0 = self.T0 + self.dur * i / self.n
            if T < t0: continue
            k = max(e_back(prog(T, t0, t0 + 0.22), 2.0), 0.01); wave = 3.5 * math.sin(T * 4 - (r + col) * 0.5) if T > self.T0 + self.dur else 0
            tiny_person(c, self.x0 + col * self.spx, self.y0 + r * self.spy, self.s * k, alpha=dim, bob=wave, head=heads[(i * 7 + r) % 6])


class Arrow(Layer):
    def __init__(self, T0, x1, y1, x2, y2, w=16, head=40, T1=None, color=BLACK):
        self.a, self.T0, self.T1 = (x1, y1, x2, y2, w, head, color), T0, T1
    def draw(self, c, T):
        if T < self.T0 or (self.T1 is not None and T >= self.T1): return
        x1, y1, x2, y2, w, head, color = self.a; arrow(c, x1, y1, x2, y2, w, color, head, alpha=prog(T, self.T0, self.T0 + 0.2))


class Custom(Layer):
    def __init__(self, fn, cues=(), punch=()): self.fn, self.cues, self.punch = fn, list(cues), list(punch)
    def draw(self, c, T): self.fn(c, T)


# ------------------------------------------------------------------ props
def arrow(c, x1, y1, x2, y2, w=14, color=BLACK, head=34, alpha=1.0):
    a = math.atan2(y2 - y1, x2 - x1)
    line(c, x1, y1, x2 - math.cos(a) * head * 0.6, y2 - math.sin(a) * head * 0.6, w, color, alpha)
    poly(c, [(x2, y2), (x2 - head * math.cos(a - 0.5), y2 - head * math.sin(a - 0.5)),
             (x2 - head * math.cos(a + 0.5), y2 - head * math.sin(a + 0.5))], fill=color, line_c=color, lw=4, alpha=alpha)

def tiny_person(c, x, y, s, alpha=1.0, bob=0.0, head=WHITE):
    c.save(); c.translate(x, y + bob); c.scale(s, s)
    p = skia.Path(); p.moveTo(0, -26); p.lineTo(0, 4); p.moveTo(0, 4); p.lineTo(-8, 22); p.moveTo(0, 4); p.lineTo(8, 22)
    p.moveTo(-10, -18); p.lineTo(10, -18)
    c.drawPath(p, paint(BLACK, alpha, 5)); circ(c, 0, -38, 11, fill=head, line=BLACK, lw=5, alpha=alpha); c.restore()

def trophy_prop(c, x, y, s=1.0, rot=0, alpha=1.0):
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

def bone_prop(c, x, y, s=1.0, rot=0, alpha=1.0):
    c.save(); c.translate(x, y); c.rotate(rot); c.scale(s, s)
    for pas in (0, 1):
        col = BLACK if pas == 0 else WHITE; grow = 10 if pas == 0 else 0
        line(c, -150, 0, 150, 0, 46 + grow * 2, col, alpha)
        for ex in (-150, 150):
            for sg in (-1, 1): c.drawCircle(ex, sg * 19, 30 + grow, paint(col, alpha))
    c.restore()

def emoji_circle(c, x, y, s=1.0, rot=0, alpha=1.0, label="?", fill=YEL):
    circ(c, x, y, 90 * s, fill=fill, line=BLACK, lw=10 * s, alpha=alpha); text(c, label, x, y, 120 * s, fill=BLACK, sw=0, shadow=False)


# ------------------------------------------------------------------ timeline
class Scene:
    def __init__(self, start, layers, bg="#FFD166", trans="iris", push=0.08, center=(540, 960), cam=None):
        self.start, self.layers, self.bg, self.trans, self.push, self.center, self.cam_fn = start, layers, bg, trans, push, center, cam
        self.end = None

    def cam(self, T):
        dur = max(self.end - self.start, 0.1); t = T - self.start
        z = 1.0 + self.push * e_io(prog(t, 0, dur)); sx = sy = 0.0
        for L in self.layers:
            for (tp, amp) in L.punch:
                z += amp * decay(T, tp, 7); a_, b_ = shake(T, tp, 14 * amp / 0.05 * 0.8, 9); sx += a_; sy += b_
        if self.cam_fn: return self.cam_fn(t, T, z, sx, sy)
        return Cam(z, self.center[0], self.center[1], 0.0, sx, sy)

    def draw(self, c, T):
        draw_bg(c, T, self.bg, seed=int(self.start * 7) % 50)
        c.save(); self.cam(T).apply(c)
        for L in self.layers: L.draw(c, T)
        c.restore()


HW = 0.13
TRANS_CYCLE = ["iris", "up", "left", "diag"]


def wipe_path(kind, p):
    e = e_io(p); pth = skia.Path()
    if kind == "iris": pth.addCircle(W / 2, H / 2 - 100, e * 1500)
    elif kind == "up": pth.addRect(skia.Rect(0, H * (1 - e), W, H))
    elif kind == "left": pth.addRect(skia.Rect(W * (1 - e), 0, W, H))
    else: pth.moveTo(0, 0); pth.lineTo(W * 2 * e, 0); pth.lineTo(W * 2 * e - H * 0.6, H); pth.lineTo(0, H); pth.close()
    return pth


class Timeline:
    def __init__(self, scenes, total):
        self.scenes, self.total = scenes, total
        scenes[0].start = 0.0
        for i, s in enumerate(scenes): s.end = scenes[i + 1].start if i + 1 < len(scenes) else total
        self.B = [s.start for s in scenes] + [total]
        for i, s in enumerate(scenes[:-1]):
            if s.trans == "auto": s.trans = TRANS_CYCLE[i % 4]

    def cues(self):
        out = [("whoosh", b - 0.2) for b in self.B[1:-1]]
        for s in self.scenes:
            for L in s.layers: out += list(L.cues)
        return out

    def frame(self, c, T):
        T = max(0.0, min(T, self.total - 0.001)); B = self.B; k = None
        for j in range(1, len(B) - 1):
            if abs(T - B[j]) <= HW: k = j
        if k is None:
            i = max(j for j in range(len(self.scenes)) if B[j] <= T); self.scenes[i].draw(c, T)
        else:
            p = (T - (B[k] - HW)) / (2 * HW)
            self.scenes[k - 1].draw(c, T)
            c.save(); c.clipPath(wipe_path(self.scenes[k - 1].trans, p), skia.ClipOp.kIntersect, True)
            self.scenes[k].draw(c, T); c.restore()
        draw_captions(c, eng.CAPT if eng.CAPT is not None else T, STATE["chunks"])
