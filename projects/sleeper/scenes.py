"""Sleeper: the timeline. frame(c, t) draws one frame and returns the post-FX dict."""
import os, re, sys, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from sleep_art import *            # noqa

WORDS = json.load(open(os.path.join(HERE, "words.json")))
_n = lambda w: re.sub(r"[^a-z0-9']", "", w.lower())


def at(word, n=0, end=False, off=0.0):
    k = 0
    for w, s, e in WORDS:
        if _n(w) == _n(word):
            if k == n: return (e if end else s) + off
            k += 1
    raise KeyError((word, n))


TOTAL = 36.6
# ---- cut points (anchored on the spoken words)
C_ALONE = 3.30                       # lock screen -> the empty bedroom ("I live alone")
C_NIGHT = at("so") - 0.06            # tonight: me in bed, phone glow
C_LIVE = at("sleeper", 0) - 0.10     # the live sleep-tracker screen
C_CLIP = 14.45                       # the sleep-talking clip
C_LIVE2 = 20.52                      # back to the live screen: the names
C_ALERT = at("new") - 0.08           # the Guest-detected modal
C_BED = at("something") - 0.14       # the bedroom again
C_BLACK, C_END = 34.35, 35.45
CUTS = [C_ALONE, C_NIGHT, C_LIVE, C_CLIP, C_LIVE2, C_ALERT, C_BED, C_BLACK, C_END]
T_PAN = at("beside") - 0.10
T_RISE0, T_RISE1 = at("sat") - 0.05, 34.10


def bpm_fn(t):
    g, nw = at("guest"), at("new")
    if t < g: return 78.0 + 0.3 * math.sin(t * 0.9)
    if t < nw: return lerp(78, 98, e_io(prog(t, g, nw)))
    return lerp(98, 128, prog(t, nw, C_BED))


L = Live(bpm_fn)
BEATS = L.beat_times(C_LIVE, C_BED + 0.2)
HITS = [(0.0, 14), (2.0, 10), (at("zero"), 22), (at("pinged"), 10), (C_CLIP, 6), (at("daniel"), 12), (at("guest"), 16), (at("new"), 18), (at("sat"), 10), (C_END, 14)]


def kick(t): return sum(a * decay(t, t0, 7.0) for t0, a in HITS)


def slam(c, t, t0, t1, s, x, y, size, rgb=(255, 255, 255), stroke=14, rot=0.0, glowb=0):
    if not (t0 <= t < t1): return
    u = t - t0
    sc = 1.0 + 1.1 * (1 - e_out(prog(u, 0, 0.16)))
    a = min(1.0, u / 0.05) * (1 - prog(t, t1 - 0.14, t1))
    dx = 7 * math.sin(u * 90) * decay(u, 0, 9); dy = 6 * math.cos(u * 77) * decay(u, 0, 9)
    text(c, s, x + dx, y + dy, size, rgb, a, stroke=stroke, scale=sc, rot=rot, blur_glow=glowb)


# ---- captions (word timed, active word amber)
def _chunks(words, maxc=13):
    out, cur, n = [], [], 0
    for w, s, e in words:
        cur.append((w, s, e)); n += len(w) + 1
        if n >= maxc or w[-1] in ".?!" or (w[-1] == "," and n >= 8): out.append(cur); cur = []; n = 0
    if cur: out.append(cur)
    return out


CHUNKS = _chunks(WORDS)


def captions(c, t, y=1510, size=78):
    for i, ch in enumerate(CHUNKS):
        t0 = ch[0][1]; t1 = CHUNKS[i + 1][0][1] if i + 1 < len(CHUNKS) else ch[-1][2] + 0.4
        t1 = min(t1, ch[-1][2] + 0.5)
        if i + 1 < len(CHUNKS) and CHUNKS[i + 1][0][1] - ch[-1][2] < 0.5: t1 = CHUNKS[i + 1][0][1] - 0.02
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


# ---- scenes
def s_lock(c, t, t_on=0.0):
    first = t_on == 0.0
    draw_lock(c, t, shake=(14 * decay(t, t_on, 6.0) + (10 * decay(t, 2.0, 6.0) if first else 0.0)),
              n2=(prog(t, 2.0, 2.4) if first else 0.0), ring=(prog(t, at("two") - 0.05, at("two") + 0.1) * (1 - prog(t, 3.0, 3.3)) if first else 0.0))


def s_alone(c, t):
    draw_bedroom(c, t, ox=1080, fig=dict(alpha=0.0), phone_glow=0.0, zoom=1.0 + 0.07 * prog(t, C_ALONE, C_NIGHT), dust=1.0)


def s_night(c, t):
    draw_bedroom(c, t, ox=0, fig=None, phone_glow=1.0, glowk=0.9, zoom=1.0 + 0.09 * prog(t, C_NIGHT, C_LIVE))


def bpm_text(t):
    t7 = at("78")
    if t < t7: return "--"
    u = t - t7
    if u < 0.55: return str(int(lerp(41, 78, e_out(u / 0.55)) + 2 * math.sin(u * 40) * (1 - u / 0.55)))
    return str(int(round(bpm_fn(t) + 0.2 * math.sin(t * 2.3) + 0.15 * math.sin(t * 5.1))))


def s_live(c, t, banner=False, modal=False):
    ph = L.phase(t); frac = ph % 1.0
    beatk = math.exp(-7.0 * ((frac - 0.30) % 1.0))
    g, d = at("guest"), at("daniel")
    s1 = dict(name="Sleeper 1", name2="Guest", flip=prog(t, g - 0.02, g + 0.14), col=TEAL, col2=(255, 196, 90), bpm=bpm_text(t), live=True, beatk=beatk, pop=decay(t, g, 6.0),
              sub="Breathing 14/min", glowk=max(0.9 * prog(t, at("sleeper", 0) - 0.05, at("sleeper", 0) + 0.1) * (1 - prog(t, at("sleeper", 1) - 0.1, at("sleeper", 1) + 0.1)),
                                               0.9 * prog(t, g - 0.05, g + 0.1) * (1 - prog(t, at("that") - 0.1, at("that") + 0.1))))
    s2 = dict(name="Sleeper 2", name2="Daniel (you)", flip=prog(t, d - 0.02, d + 0.14), col=CORAL, col2=(200, 190, 255), bpm="0", live=False, pop=decay(t, d, 6.0),
              sub="Breathing —", tag=prog(t, at("zero"), at("zero") + 0.2),
              glowk=max(0.9 * prog(t, at("sleeper", 1) - 0.05, at("sleeper", 1) + 0.1) * (1 - prog(t, at("pinged") + 0.4, at("pinged") + 0.8)),
                        0.9 * prog(t, d - 0.05, d + 0.1) * (1 - prog(t, at("sleeper", 3) - 0.1, at("sleeper", 3) + 0.1))))
    ban = None
    if banner:
        k = prog(t, at("pinged") - 0.15, at("pinged") + 0.2) * (1 - prog(t, C_CLIP - 0.16, C_CLIP - 0.04))
        ban = dict(k=k, title="Sleep talking detected", body="", sub="3:12 AM · 14 s · tap to play")
    mod = None
    if modal:
        dn = 0.0 if t < at("notified") - 0.02 else 0.5 + 0.5 * prog(t, at("notified") - 0.02, at("notified") + 0.35)
        mod = dict(k=prog(t, C_ALERT, C_ALERT + 0.18), done=dn)
    z = 1.0 + 0.035 * prog(t, C_LIVE, C_CLIP) if t < C_CLIP else 1.0 + 0.03 * prog(t, C_LIVE2, C_ALERT)
    c.save(); c.translate(W / 2, H / 2); c.scale(z, z); c.translate(-W / 2, -H / 2)
    draw_live(c, t, L, s1, s2, shake=(10 * decay(t, at("new"), 5.0) if modal else 0.0), dim=(0.15 if modal else 0.0), banner=ban, modal=mod)
    c.restore()


def _typed(words, t):
    out = [w for w, ts in words if t >= ts]
    return " ".join(out)


A1 = [("Is", at("is")), ("he", at("he")), ("asleep?", at("asleep"))]
A2 = [("Not", at("not")), ("yet.", at("yet")), ("Keep", at("keep")), ("still.", at("still"))]
CT0, CT1 = 14.55, 18.35
ENV = narr_env(CT0, CT1, 64)


def s_clip(c, t):
    b1 = ("Speaker 1", _typed(A1, t), prog(t, at("asleep") + 0.40, at("asleep") + 0.70))
    b2 = ("Speaker 2", _typed(A2, t), prog(t, at("still") + 0.30, at("still") + 0.60))
    summ = prog(t, at("both") - 0.05, at("both") + 0.28)
    z = 1.0 + 0.03 * prog(t, C_CLIP, C_LIVE2)
    c.save(); c.translate(W / 2, H / 2); c.scale(z, z); c.translate(-W / 2, -H / 2)
    draw_clip(c, t, CT0, CT1, ENV, [b1, b2], 1.0, summ, shake=6 * decay(t, at("not"), 8.0) + 6 * decay(t, at("is"), 8.0))
    c.restore()


def s_bed(c, t):
    ox = lerp(0, 1080, e_io(prog(t, T_PAN, T_PAN + 0.80)))
    rise = prog(t, T_RISE0, T_RISE1)
    tilt = e_io(prog(t, 33.05, 34.10))
    fig = dict(alpha=1.0, rise=rise, tilt=tilt)
    z = 1.0 + 0.10 * e_io(prog(t, T_PAN + 0.8, C_BLACK))
    phone = 1.0 - prog(t, T_PAN, T_PAN + 0.8)
    draw_bedroom(c, t, ox=ox, fig=fig, phone_glow=phone, glowk=0.9, sway=2.0 * prog(t, T_PAN + 0.8, C_BLACK), zoom=z, dust=1.0 if ox > 500 else 0.0)


def frame(c, t):
    fx = {"bloom": 1.0}
    c.clear(skia.ColorBLACK)
    k = kick(t)
    c.save(); c.translate(3.0 * k * math.sin(t * 91), 2.2 * k * math.cos(t * 77))
    if t < C_ALONE: s_lock(c, t)
    elif t < C_NIGHT: s_alone(c, t)
    elif t < C_LIVE: s_night(c, t)
    elif t < C_CLIP: s_live(c, t, banner=True)
    elif t < C_LIVE2: s_clip(c, t)
    elif t < C_ALERT: s_live(c, t)
    elif t < C_BED: s_live(c, t, modal=True)
    elif t < C_BLACK: s_bed(c, t)
    elif t < C_END: pass
    else: s_lock(c, t, C_END); fx["fade"] = prog(t, C_END, C_END + 0.12)
    c.restore()
    # ---- overlays
    top = ((at("zero") - 0.02, at("pinged") - 0.2), (at("both") - 0.02, C_LIVE2 - 0.12), (at("my", 2) - 0.03, C_ALERT - 0.1), (at("owner") - 0.02, C_BED - 0.1))
    if any(a <= t < b for a, b in top): vgrad(c, 0, 0, W, 360, (0, 0, 0), (0, 0, 0), 0.94, 0.0)
    slam(c, t, 0.0, C_ALONE - 0.05, "2 SLEEPERS", W / 2, 180, 132, (255, 255, 255), 14)
    slam(c, t, 0.0, C_ALONE - 0.05, "DETECTED", W / 2, 305, 120, (255, 90, 110), 14, glowb=16)
    slam(c, t, at("live", 0) - 0.02, C_NIGHT - 0.05, "I LIVE ALONE.", W / 2, 215, 150, (255, 70, 80), 14, glowb=24)
    slam(c, t, at("tonight") - 0.03, C_LIVE - 0.06, "TONIGHT", W / 2, 400, 160, (255, 255, 255), 14)
    slam(c, t, at("tonight") + 0.20, C_LIVE - 0.06, "11:52 PM", W / 2, 540, 78, (255, 214, 90), 10)
    slam(c, t, at("zero") - 0.02, at("pinged") - 0.2, "ZERO.", W / 2, 215, 250, (255, 60, 80), 16, glowb=30)
    slam(c, t, at("both") - 0.02, C_LIVE2 - 0.12, "BOTH VOICES\nMATCH ME", W / 2, 205, 112, (255, 255, 255), 12)
    slam(c, t, at("my", 2) - 0.03, at("sleeper", 3) - 0.12, "MY NAME.", W / 2, 215, 190, (255, 255, 255), 14)
    slam(c, t, at("guest") - 0.02, at("that") - 0.08, "GUEST.", W / 2, 215, 230, (255, 196, 90), 16, glowb=22)
    slam(c, t, at("that") - 0.02, C_ALERT - 0.1, "THAT WAS\nME.", W / 2, 205, 150, (255, 255, 255), 14)
    slam(c, t, at("owner") - 0.02, C_BED - 0.1, "OWNER\nNOTIFIED.", W / 2, 205, 130, (255, 70, 90), 14, glowb=20)
    QUIET = ((at("zero") - 0.02, at("pinged") - 0.35),)
    if t < C_BLACK and not any(a <= t < b for a, b in QUIET): captions(c, t)
    for tc_ in CUTS: fx["ab"] = fx.get("ab", 0) + 5 * decay(t, tc_, 14.0)
    fx["flash"] = 0.30 * decay(t, at("zero"), 12.0) + 0.9 * prog(t, C_BLACK - 0.16, C_BLACK - 0.02) * (t < C_BLACK)
    return fx
