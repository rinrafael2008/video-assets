"""Doorbell: the timeline. frame(c, t) draws one frame and returns the post-FX dict."""
import os, re, sys, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from art import *            # noqa

WORDS = json.load(open(os.path.join(HERE, "words.json")))
_n = lambda w: re.sub(r"[^a-z0-9']", "", w.lower())


def at(word, n=0, end=False, off=0.0):
    k = 0
    for w, s, e in WORDS:
        if _n(w) == _n(word):
            if k == n: return (e if end else s) + off
            k += 1
    raise KeyError((word, n))


TOTAL = 36.9
# ---- cut points (all anchored on the spoken words)
C_LOCK, C_BED, C_HIST, C_CAM = 3.40, 5.45, 7.85, 13.40
C_CHAT1, C_CUT, C_CHAT2 = C_CAM, at("disappeared"), at("appeared", 1)
C_DOOR, C_CAM2, C_RUN = 23.40, 26.45, at("run") - 0.10
C_KNOB, C_BLACK, C_END = at("my", 1) - 0.1, 34.35, 35.30
CUTS = [C_LOCK, C_BED, C_HIST, C_CAM, C_CUT, C_CHAT2, C_DOOR, C_CAM2, C_RUN, C_KNOB, C_BLACK, C_END]

SEND_T = at("name") + 0.50            # I send "what's my middle name?"
REPLY_T = at("got")                   # Mom answers
SECOND_T = at("text")                 # the second text lands
MSGS = [M("r", "Did you eat dinner?", -12, "6:41 PM"), M("s", "yes mom", -11, "6:43 PM"), M("r", "Good. Lock up when you go to bed.", -10, "6:44 PM"), M("r", "Goodnight sweetie. Don't stay up too late.", -9, "1:12 AM"), M("s", "night mom. love you", -8, "1:13 AM"), M("r", "I'm outside. Open the door.", -7, "2:14 AM"), M("r", "Hurry up, it's freezing!", -6, "2:14 AM"),
        M("s", "what's my middle name?", SEND_T, "2:14 AM"), M("r", "Jonathan.", REPLY_T, "2:14 AM"), M("r", "Whatever is upstairs, do not answer it.", SECOND_T, "2:14 AM")]
DOTS = [(at("appeared", 0) - 0.02, at("disappeared")), (at("appeared", 1), REPLY_T)]
GOODNIGHT = next(m for m in MSGS if m.text.startswith('Goodnight'))
TYPED = "what's my middle name?"
THUMPS = [4.15, 4.55]
HITS = [(0.0, 14), (2.2, 10), (REPLY_T, 8), (SECOND_T, 16), (C_DOOR, 12), (C_RUN, 34), (at("run") + 0.9, 10), (33.95, 14), (C_END, 14), (THUMPS[0], 7), (THUMPS[1], 7), (at("honey"), 6)]


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
    draw_lock(c, t, shake=14 * decay(t, t_on, 6.0) + (10 * decay(t, 2.2, 6.0) if t_on == 0.0 else 0.0), n2=(prog(t, 2.2, 2.6) if t_on == 0.0 else 0.0),
              ring=(prog(t, at('outside') - 0.05, at('outside') + 0.1) * (1 - prog(t, 3.0, 3.3)) if t_on == 0.0 else 0.0))


def s_bed(c, t):
    u = prog(t, 4.0, 4.8)
    cam_y = lerp(900, -90, e_io(u)) + 8 * math.sin(t * 1.3)
    sway = decay(t, THUMPS[0], 1.2) + decay(t, THUMPS[1], 1.2)
    draw_bdoor(c, t, cam_y=cam_y, zoom=1.0 + 0.05 * prog(t, C_LOCK, C_BED), under=0.8 + 0.2 * math.sin(t * 3), glowk=0.55 * (1 - u), dust=THUMPS, sway=sway * 6)


def s_hist(c, t):
    z = 1.0 + 0.05 * prog(t, C_BED, C_HIST)
    c.save(); c.translate(W / 2, H / 2); c.scale(z, z); c.translate(-W / 2, -H / 2)
    hk = prog(t, at("goodnight") - 0.05, at("goodnight") + 0.12) * (1 - prog(t, 7.25, 7.45))
    draw_chat(c, t, [m for m in MSGS if m.t < 0], (), "", True, 0.0, GOODNIGHT, hk)
    c.restore()


def s_cam(c, t):
    k = e_io(prog(t, 9.55, 10.65))
    wm = None
    if t >= 9.55:
        wm = dict(x=lerp(420, 270, k), y=lerp(502, 462, k) - 6 * (1 - k) * abs(math.sin(t * 9)), sc=lerp(0.42, 1.0, k),
                  smile=e_out(prog(t, at("smiling") - 0.1, at("smiling") + 0.4)), wave=prog(t, at("waving") - 0.1, at("waving") + 0.25) * (1 - prog(t, 12.5, 12.85)))
    pz = e_io(prog(t, 12.3, 13.3))
    draw_feed(c, t, dict(woman=wm, zoom=1.0 + 0.6 * pz, zc=(270, 340)))
    cam_ui(c, t, connecting=1 - prog(t, 8.45, 8.95) if t < 9 else 0.0)


def _chat(c, t, t_a, t_b, push=0.04, dim=0.0):
    z = 1.0 + push * prog(t, t_a, t_b)
    c.save(); c.translate(W / 2, H / 2); c.scale(z, z); c.translate(-W / 2, -H / 2)
    typed = TYPED[:int(len(TYPED) * prog(t, 13.68, 15.15))] if t < SEND_T else ""
    sk = 12 * decay(t, REPLY_T, 7.0) + 16 * decay(t, SECOND_T, 6.0)
    draw_chat(c, t, [m for m in MSGS if m.t > -1 or m.t < 0], DOTS, typed, True, 1.0 if t >= SEND_T - 0.05 else 0.0, None, 0.0, shake=sk, dim=dim)
    c.restore()


def s_cut(c, t):
    u = prog(t, C_CUT, C_CHAT2)
    draw_bdoor(c, t, cam_y=1060, zoom=1.12, under=0.65 + 0.35 * (int(t * 22) % 2), feet=1.0, feet_xs=(lerp(250, 770, u),), glowk=0.45)


def s_door(c, t):
    u = prog(t, C_DOOR, C_CAM2)
    flick = 1.0 if (t % 2.2) < 2.0 else 0.55
    draw_bdoor(c, t, cam_y=lerp(1000, 1130, e_io(u)), zoom=lerp(1.0, 1.38, e_io(u)), under=flick, feet=1.0, glowk=0.5 * (1 - 0.8 * u), roll=0.4 * math.sin(t * 0.8))


MOUTHS = [(30, 26, 0.0), (22, 30, 0.0), (54, 16, 1.0), (44, 6, 0.0)]


def _mouth(t, t0):
    ph = (t - t0) / 0.2
    if ph < 0: return None
    i = int(ph) % 4; f = e_io(ph - int(ph)); a, b = MOUTHS[i], MOUTHS[(i + 1) % 4]
    return tuple(lerp(x, y, f) for x, y in zip(a, b))


def s_cam2(c, t):
    stop = at("stopped")
    sm = 1 - prog(t, stop + 0.02, stop + 0.45)
    scare = e_out(prog(t, stop + 0.15, stop + 0.9))
    t_m = at("mouthed") - 0.05
    mouth = _mouth(t, t_m) if t >= t_m else ((40, 10 + 12 * scare, 0.4) if t > stop + 0.55 else None)
    wave = 1 - prog(t, stop - 0.05, stop + 0.3)
    jit = prog(t, 28.6, 31.0)
    shx = 4 * math.sin(t * 61) * jit; shy = 4 * math.cos(t * 47) * jit
    z = 1.28 + 0.55 * e_io(prog(t, 26.45, 31.1))
    wm = dict(x=270, y=462, sc=1.0, smile=sm, scare=scare, mouth=mouth, wave=wave, breath=jit)
    draw_feed(c, t, dict(woman=wm, zoom=z, zc=(270, 330), shx=shx, shy=shy))
    cam_ui(c, t)


def s_run(c, t):
    u = t - C_RUN
    mouth = _mouth(t, C_RUN - 0.2)
    wm = dict(x=270, y=462, sc=1.0, smile=0.0, scare=1.0, mouth=mouth, wave=0.0, breath=1.0)
    draw_feed(c, t, dict(woman=wm, zoom=2.45 + 0.25 * prog(u, 0, 1.2), zc=(270, 318), shx=6 * math.sin(t * 70), shy=6 * math.cos(t * 55)))
    c.drawRect(skia.Rect(0, 0, W, H), paint((220, 0, 0), 0.20))
    vgrad(c, 0, 0, W, 300, (0, 0, 0), (0, 0, 0), 0.6, 0.0)
    tl(c, "Front Door", 120, 182, 46, (255, 255, 255), 1.0, PB)
    c.drawCircle(W - 250, 182, 12, paint((235, 50, 50))); tl(c, "LIVE", W - 226, 182, 36, (255, 255, 255), 1.0, PB)


def s_knob(c, t):
    u = prog(t, C_KNOB, 33.7)
    k = e_io(u)
    kn = e_io(prog(t, C_KNOB + 0.25, 33.85)) + 0.05 * math.sin(t * 40) * prog(t, C_KNOB + 0.25, 33.85)
    draw_bdoor(c, t, cam_y=lerp(980, 900, k), cx=lerp(540, 742, k), zoom=lerp(1.0, 2.9, k), under=1.0, feet=1.0, feet_xs=(560, 700), knob=kn, ajar=prog(t, 33.95, 34.28), glowk=0.0,
               roll=1.0 * math.sin(t * 30) * prog(t, 33.6, 34.3))


def frame(c, t):
    fx = {"bloom": 1.0}
    c.clear(skia.ColorBLACK)
    k = kick(t)
    c.save(); c.translate(3.0 * k * math.sin(t * 91), 2.2 * k * math.cos(t * 77))
    if t < C_LOCK: s_lock(c, t)
    elif t < C_BED: s_bed(c, t)
    elif t < C_HIST: s_hist(c, t)
    elif t < C_CAM: s_cam(c, t)
    elif t < C_CUT: _chat(c, t, C_CHAT1, C_CUT)
    elif t < C_CHAT2: s_cut(c, t)
    elif t < C_DOOR: _chat(c, t, C_CHAT2, C_DOOR, dim=0.55 * prog(t, 21.95, 22.25) + 0.25 * prog(t, 22.9, 23.35))
    elif t < C_CAM2: s_door(c, t)
    elif t < C_RUN: s_cam2(c, t)
    elif t < C_KNOB: s_run(c, t)
    elif t < C_BLACK: s_knob(c, t)
    elif t < C_END: pass
    else: s_lock(c, t, C_END); fx["fade"] = prog(t, C_END, C_END + 0.12)
    c.restore()
    # ---- overlays
    slam(c, t, 0.0, 3.3, "MOM TEXTED ME", W / 2, 205, 128, (255, 255, 255), 14)
    slam(c, t, at("mom", 1), C_BED - 0.1, "MOM WAS", W / 2, 520, 120, (255, 255, 255), 12)
    slam(c, t, at("upstairs", 0), C_BED - 0.1, "UPSTAIRS", W / 2, 720, 210, (255, 60, 60), 14, glowb=20)
    slam(c, t, at("hour"), C_HIST - 0.1, "1 HOUR AGO", W / 2, 520, 150, (255, 255, 255), 14)
    slam(c, t, at("mom", 2), C_CAM - 0.05, "IT WAS MOM.", W / 2, 1180, 140, (255, 255, 255), 14)
    slam(c, t, at("do"), C_DOOR - 0.05, "DO NOT\nANSWER IT", W / 2, 560, 150, (255, 60, 60), 14, glowb=18)
    slam(c, t, C_RUN + 0.02, C_KNOB - 0.1, "RUN.", W / 2, 400, 360, (255, 40, 40), 18, glowb=30)
    QUIET = ((at('mom', 2) - 0.02, C_CAM), (at('do') - 0.02, C_DOOR), (C_RUN, C_KNOB - 0.1))
    if t < C_BLACK and not any(a <= t < b for a, b in QUIET): captions(c, t)
    for tc_ in CUTS: fx["ab"] = fx.get("ab", 0) + 5 * decay(t, tc_, 14.0)
    fx["flash"] = 0.55 * decay(t, C_RUN, 12.0) + 0.9 * prog(t, 34.18, 34.34) * (t < C_BLACK)
    return fx
