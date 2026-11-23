"""Dark-horror procedural renderer on Skia + numpy (no stock footage, no credits).
3D one-point-perspective corridor with lamps/doors/figure, 2D door-room, apartment tower, fisheye peephole, film post.
"""
import math, random
import numpy as np
import skia
import cv2

W, H, FPS = 1080, 1920, 30


# ------------------------------------------------------------------ small helpers
def cl(x, a=0.0, b=1.0): return a if x < a else b if x > b else x
def lerp(a, b, k): return a + (b - a) * k
def prog(t, a, b): return cl((t - a) / (b - a)) if b != a else (1.0 if t >= a else 0.0)
def smooth(x): x = cl(x); return x * x * (3 - 2 * x)
def e_out(x): return 1 - (1 - cl(x)) ** 3
def e_io(x): x = cl(x); return x * x * x * (x * (x * 6 - 15) + 10)
def e_back(x, s=1.7):
    x = cl(x); c3 = s + 1
    return 1 + c3 * (x - 1) ** 3 + s * (x - 1) ** 2
def decay(t, t0, k=8.0): return math.exp(-k * (t - t0)) if t >= t0 else 0.0
def mixc(a, b, k): return tuple(lerp(x, y, k) for x, y in zip(a, b))


def ci(r, g, b, a=1.0):
    return skia.ColorSetARGB(int(255 * cl(a)), int(cl(r, 0, 255)), int(cl(g, 0, 255)), int(cl(b, 0, 255)))


def paint(rgb=(0, 0, 0), a=1.0, stroke=None, blur=0.0, blend=None, shader=None, round_=True):
    p = skia.Paint(AntiAlias=True)
    if shader is not None: p.setShader(shader)
    else: p.setColor(ci(*rgb, a))
    if stroke:
        p.setStyle(skia.Paint.kStroke_Style); p.setStrokeWidth(stroke)
        if round_: p.setStrokeCap(skia.Paint.kRound_Cap); p.setStrokeJoin(skia.Paint.kRound_Join)
    if blur: p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
    if blend is not None: p.setBlendMode(blend)
    return p


_PATH = skia.Path()
def quad(c, pts, rgb, a=1.0, **kw):
    _PATH.reset(); _PATH.moveTo(*pts[0])
    for q in pts[1:]: _PATH.lineTo(*q)
    _PATH.close(); c.drawPath(_PATH, paint(rgb, a, **kw))


def glow(c, x, y, r, rgb, a=0.5, blend=skia.BlendMode.kPlus):
    if r < 1 or a <= 0.003: return
    sh = skia.GradientShader.MakeRadial((x, y), r, [ci(*rgb, a), ci(*rgb, a * 0.35), ci(*rgb, 0)], [0, 0.35, 1])
    c.drawCircle(x, y, r, paint(shader=sh, blend=blend))


def vgrad(c, x0, y0, x1, y1, top, bot, a_top=1.0, a_bot=1.0):
    sh = skia.GradientShader.MakeLinear([(0, y0), (0, y1)], [ci(*top, a_top), ci(*bot, a_bot)])
    c.drawRect(skia.Rect(x0, y0, x1, y1), paint(shader=sh))


_fonts = {}
def font(path, size):
    key = (path, int(size))
    if key not in _fonts:
        f = skia.Font(skia.Typeface.MakeFromFile(path), int(size)); f.setSubpixel(True); _fonts[key] = f
    return _fonts[key]

ANTON = "/usr/share/fonts/truetype/google-fonts/ofl/anton/Anton-Regular.ttf"
POP = "/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf"


def text(c, s, x, y, size, rgb=(255, 255, 255), a=1.0, stroke=0, scale=1.0, rot=0.0, fnt=ANTON, shadow=True, lead=1.02, blur_glow=0):
    """centred multi-line text, (x,y) = block centre"""
    if a <= 0.004 or scale <= 0.001: return
    f = font(fnt, size); lines = s.split("\n")
    c.save(); c.translate(x, y); c.rotate(rot); c.scale(scale, scale)
    tot = (len(lines) - 1) * size * lead
    for i, ln in enumerate(lines):
        w = f.measureText(ln); yy = -tot / 2 + i * size * lead + size * 0.36
        if blur_glow: c.drawString(ln, -w / 2, yy, f, paint(rgb, a * 0.7, blur=blur_glow))
        if shadow: c.drawString(ln, -w / 2 + 4, yy + 10, f, paint((0, 0, 0), 0.45 * a))
        if stroke: c.drawString(ln, -w / 2, yy, f, paint((0, 0, 0), a, stroke=stroke))
        c.drawString(ln, -w / 2, yy, f, paint(rgb, a))
    c.restore()


# ------------------------------------------------------------------ post (numpy): bloom, aberration, grade, grain, vignette
_rs = np.random.RandomState(5)
_GRAIN = [(_rs.standard_normal((H, W, 1)) * 7.0).astype(np.float32) for _ in range(6)]
_yy, _xx = np.mgrid[0:H, 0:W].astype(np.float32)
_VIG = (1.0 - 0.62 * np.clip((((_xx - W / 2) / (W * 0.62)) ** 2 + ((_yy - H / 2) / (H * 0.62)) ** 2), 0, 1) ** 1.25)[..., None].astype(np.float32)


def post(img_bgra, fx, frame):
    a = img_bgra[..., :3].astype(np.float32)                      # BGR 0..255
    if fx.get("whip", 0) > 1:
        k = int(fx["whip"]) | 1
        a = cv2.blur(a, (k, 1))
    if fx.get("vblur", 0) > 1:
        k = int(fx["vblur"]) | 1
        a = cv2.blur(a, (1, k))
    # bloom
    small = cv2.resize(a, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    hl = np.clip(small - 120.0, 0, None) * 1.25
    b1 = cv2.GaussianBlur(hl, (0, 0), 7); b2 = cv2.GaussianBlur(hl, (0, 0), 22)
    bl = cv2.resize(b1 * 0.55 + b2 * 0.65, (W, H), interpolation=cv2.INTER_LINEAR) * fx.get("bloom", 1.0)
    a += bl
    ab = int(round(fx.get("ab", 0)))
    if ab >= 1:
        a[..., 0] = np.roll(a[..., 0], ab, axis=1); a[..., 2] = np.roll(a[..., 2], -ab, axis=1)
    a *= _VIG
    # grade: cold shadows, slightly crushed
    a[..., 0] += 5.0; a[..., 1] += 2.0
    a = (a - 128) * 1.06 + 128 - 6
    if fx.get("flash", 0) > 0.003: a += 255.0 * fx["flash"]
    fd = fx.get("fade", 1.0)
    if fd < 1: a *= fd
    g = _GRAIN[frame % 6]
    sx = (frame * 37) % 97; sy = (frame * 53) % 89
    g = np.roll(np.roll(g, sx, axis=1), sy, axis=0)
    a += g * (0.6 + 0.4 * (1 - np.clip(a.mean(axis=2, keepdims=True) / 200, 0, 1)))
    return np.clip(a, 0, 255).astype(np.uint8)


# ------------------------------------------------------------------ 3D corridor
ZMAX = 50.0
HALF = 1.25; CEIL = 2.55
LAMPS = [(2.5, 0.70), (7.5, 0.45), (12.5, 1.0), (17.5, 0.0), (22.5, 0.75), (27.5, 0.55), (32.5, 0.0), (37.5, 0.75), (42.5, 1.0), (47.0, 1.1)]
LAMP_RGB = (222, 236, 206)
WALL = (100, 100, 90); WAIN = (62, 64, 58); DOOR = (50, 30, 22); FRAME = (82, 76, 62)
FLOOR_S = (46, 28, 30); FLOOR_R = (62, 34, 36); CEILC = (92, 94, 90)


def _light(z, flick, lamps):
    s = 0.0
    for zl, I in lamps: s += I * math.exp(-((z - zl) / 3.3) ** 2)
    return 0.045 + s * flick


def _shade(rgb, L, z, camz):
    k = cl(L, 0, 1.25) ** 1.0
    fog = math.exp(-max(z - camz, 0) / 70.0)
    return tuple(cl(v * k * fog, 0, 255) for v in rgb)


class Cam3:
    def __init__(self, z=0.0, x=0.0, y=1.55, f=1300.0, cx=W / 2, cy=H / 2):
        self.z, self.x, self.y, self.f, self.cx, self.cy = z, x, y, f, cx, cy
    def p(self, x, y, z):
        d = max(z - self.z, 0.05)
        return (self.cx + self.f * (x - self.x) / d, self.cy - self.f * (y - self.y) / d)


def draw_corridor(c, cam, flick=1.0, lamps=None, t=0.0, figure=None, dust=True, width=W, height=H):
    lamps = LAMPS if lamps is None else lamps
    c.drawRect(skia.Rect(0, 0, width, height), paint((3, 4, 6)))
    near = cam.z + 0.35
    dz = 0.5
    n = int((ZMAX - near) / dz) + 1
    doors = [(4.0 + 3.6 * k, k) for k in range(13)]
    fig_drawn = False
    # end wall
    L = _light(ZMAX - 1, flick, lamps)
    quad(c, [cam.p(-HALF, 0, ZMAX), cam.p(HALF, 0, ZMAX), cam.p(HALF, CEIL, ZMAX), cam.p(-HALF, CEIL, ZMAX)], _shade((150, 150, 140), L * 1.2, ZMAX, cam.z))
    # exit sign + end door
    ex = [cam.p(-0.32, 2.38, ZMAX - 0.02), cam.p(0.32, 2.38, ZMAX - 0.02), cam.p(0.32, 2.12, ZMAX - 0.02), cam.p(-0.32, 2.12, ZMAX - 0.02)]
    quad(c, ex, (40, 255, 120), 0.95)
    quad(c, [cam.p(-0.5, 0, ZMAX - 0.02), cam.p(0.5, 0, ZMAX - 0.02), cam.p(0.5, 2.0, ZMAX - 0.02), cam.p(-0.5, 2.0, ZMAX - 0.02)], _shade(DOOR, L * 1.2, ZMAX, cam.z))
    for i in range(n - 1, -1, -1):
        z1 = near + i * dz; z0 = z1 + dz                           # slice [z1, z0], z0 is the far edge
        zm = (z0 + z1) / 2; Lm = _light(zm, flick, lamps)
        # floor: sides + runner
        for xa, xb, base in ((-HALF, -0.55, FLOOR_S), (-0.55, 0.55, FLOOR_R), (0.55, HALF, FLOOR_S)):
            quad(c, [cam.p(xa, 0, z0), cam.p(xb, 0, z0), cam.p(xb, 0, z1), cam.p(xa, 0, z1)], _shade(base, Lm * 1.05, zm, cam.z))
        # ceiling
        quad(c, [cam.p(-HALF, CEIL, z0), cam.p(HALF, CEIL, z0), cam.p(HALF, CEIL, z1), cam.p(-HALF, CEIL, z1)], _shade(CEILC, Lm * 1.25, zm, cam.z))
        for side in (-1, 1):
            x = side * HALF
            in_door = None
            for zd, k in doors:
                if (k % 2 == 0) == (side < 0): zdd = zd
                else: zdd = zd + 1.8
                if zdd - 0.05 <= zm <= zdd + 1.1: in_door = (zdd, zm)
            quad(c, [cam.p(x, 0, z0), cam.p(x, 0, z1), cam.p(x, CEIL, z1), cam.p(x, CEIL, z0)], _shade(WALL, Lm, zm, cam.z))
            quad(c, [cam.p(x, 0, z0), cam.p(x, 0, z1), cam.p(x, 1.05, z1), cam.p(x, 1.05, z0)], _shade(WAIN, Lm, zm, cam.z))
            quad(c, [cam.p(x, 1.03, z0), cam.p(x, 1.03, z1), cam.p(x, 1.09, z1), cam.p(x, 1.09, z0)], _shade(FRAME, Lm * 1.1, zm, cam.z))
            if in_door:
                zdd = in_door[0]; edge = (zm < zdd + 0.12) or (zm > zdd + 0.95)
                col = FRAME if edge else DOOR
                quad(c, [cam.p(x, 0, z0), cam.p(x, 0, z1), cam.p(x, 2.1, z1), cam.p(x, 2.1, z0)], _shade(col, Lm, zm, cam.z))
                if not edge and abs(zm - (zdd + 0.53)) < dz / 2 + 0.01 and (z1 - cam.z) > 1.2:
                    quad(c, [cam.p(x, 1.58, z0), cam.p(x, 1.58, z1), cam.p(x, 1.68, z1), cam.p(x, 1.68, z0)], _shade((200, 170, 90), Lm * 1.4, zm, cam.z))
        # lamp fixtures
        for zl, I in lamps:
            if z1 <= zl < z0:
                on = I * flick
                col = tuple(cl(v * (0.18 + 0.95 * min(on, 1)), 0, 255) for v in LAMP_RGB) if on > 0.02 else (22, 24, 24)
                quad(c, [cam.p(-0.32, CEIL - 0.02, zl + 0.55), cam.p(0.32, CEIL - 0.02, zl + 0.55), cam.p(0.32, CEIL - 0.02, zl - 0.55), cam.p(-0.32, CEIL - 0.02, zl - 0.55)], col)
    for zl, I in lamps:
        if zl > cam.z + 0.6 and I * flick > 0.02:
            sx, sy = cam.p(0, CEIL - 0.05, zl)
            glow(c, sx, sy, cl(cam.f * 1.4 / (zl - cam.z), 24, 800), LAMP_RGB, 0.26 * I * flick)
    vx, vy = cam.p(0, 1.4, ZMAX)
    glow(c, vx, vy, 360, (110, 170, 130), 0.13 * flick)
    if figure is not None:
        draw_figure(c, cam, t=t, **figure)
    if dust:
        rr = random.Random(7)
        for i in range(46):
            zz = cam.z + 0.6 + (rr.random() * 9 + t * 0.15 * (0.5 + rr.random())) % 9
            xx = (rr.random() * 2 - 1) * 1.1 + 0.05 * math.sin(t * 0.7 + i)
            yy = 0.2 + rr.random() * 2.2 + 0.03 * math.sin(t * 1.3 + i * 2)
            sx, sy = cam.p(xx, yy, zz)
            c.drawCircle(sx, sy, cl(cam.f * 0.006 / (zz - cam.z), 0.8, 5), paint((255, 255, 235), 0.22 * min(flick, 1)))


def draw_figure(c, cam, z=30.0, x=0.0, t=0.0, scale=1.15, lean=0.0, head="up", eyes=True, lit=1.0, wiggle=1.0, arm_up=0.0, glints=1.0):
    """tall thin silhouette: tiny tilted head, long neck, arms past the knees, too many finger joints. Feet at y=0."""
    s = scale
    sway = 0.022 * math.sin(t * 1.15) + 0.010 * math.sin(t * 2.9 + 1)
    twitch = 0.025 * (1 if math.sin(t * 9.0) > 0.93 else 0)
    X = x + sway + twitch
    d = max(z - cam.z, 0.1); k = cam.f / d
    def P(px, py): return cam.p(X + px * s + lean * py * 0.10, py * s, z)
    core = (3, 4, 5); rim = (150, 182, 170); lit = lit * (1.0 + 1.1 * cl((6.0 - z) / 5.0))
    def limb(pts, w):
        pp = [P(*q) for q in pts]
        path = skia.Path(); path.moveTo(*pp[0])
        for q in pp[1:]: path.lineTo(*q)
        c.drawPath(path, paint(rim, 0.22 * lit, stroke=max(k * w * s + 3, 2)))
        c.drawPath(path, paint(core, 1.0, stroke=max(k * w * s, 1.4)))
    def poly(pts):
        pp = [P(*q) for q in pts]
        path = skia.Path(); path.moveTo(*pp[0])
        for q in pp[1:]: path.lineTo(*q)
        path.close()
        c.drawPath(path, paint(rim, 0.22 * lit, stroke=3))
        c.drawPath(path, paint(core, 1.0))
    # legs
    limb([(-0.065, 0.0), (-0.06, 0.5), (-0.05, 1.02)], 0.07)
    limb([(0.065, 0.0), (0.06, 0.5), (0.05, 1.02)], 0.07)
    # torso: wide shoulders tapering to a narrow waist
    poly([(-0.20, 1.84), (0.20, 1.84), (0.15, 1.45), (0.10, 1.0), (-0.10, 1.0), (-0.15, 1.45)])
    # long thin neck, head tilted
    hx, hy = (0.0, 2.16) if head == "up" else (0.26, 2.24)
    if head == "up": limb([(0.0, 1.82), (0.0, 1.98), (hx, hy - 0.07)], 0.05)
    else: limb([(0.0, 1.82), (0.03, 2.02), (0.16, 2.16), (hx, hy - 0.04)], 0.055)
    # arms to below the knees, sway
    sw = 0.025 * math.sin(t * 1.3 + 0.5)
    for sd in (-1, 1):
        ha = (sd * 0.27 + sw * sd, 0.55 + 0.5 * arm_up * (1 if sd > 0 else 0))
        limb([(sd * 0.19, 1.80), (sd * 0.26, 1.2), ha], 0.045)
        for j in range(4):
            ang = (j - 1.5) * 0.11 + 0.06 * math.sin(t * 2.2 + j * 1.3 + sd) * wiggle
            f1 = (ha[0] + math.sin(ang) * 0.10, ha[1] - 0.15)
            f2 = (f1[0] + math.sin(ang + 0.25 * math.sin(t * 1.7 + j)) * 0.11 * wiggle, f1[1] - 0.15)
            f3 = (f2[0] + math.sin(ang - 0.3 * math.sin(t * 2.1 + j)) * 0.07 * wiggle, f2[1] - 0.10)
            limb([ha, f1, f2, f3], 0.011)
    # head
    hp = P(hx, hy)
    c.save(); c.translate(*hp); c.rotate(-16 if head == "up" else -62)
    rx, ry = max(k * 0.078 * s, 2), max(k * 0.118 * s, 3)
    c.drawOval(skia.Rect(-rx - 1.5, -ry - 1.5, rx + 1.5, ry + 1.5), paint(rim, 0.20 * lit))
    c.drawOval(skia.Rect(-rx, -ry, rx, ry), paint(core, 1.0))
    if eyes and k * 0.07 * s > 2.4:
        for ex in (-0.38, 0.38):
            glow(c, ex * rx, -0.10 * ry, max(rx * 1.1, 5), (205, 232, 255), 0.5 * glints)
            c.drawCircle(ex * rx, -0.10 * ry, max(rx * 0.14, 1.0), paint((240, 250, 255), 0.95 * glints))
    c.restore()


# ------------------------------------------------------------------ fisheye peephole
_FISH = {}
def _fish_maps(src, out, k):
    key = (src, out, k)
    if key not in _FISH:
        R = out / 2
        u, v = np.meshgrid(np.arange(out, dtype=np.float32), np.arange(out, dtype=np.float32))
        dx, dy = u - R + 0.5, v - R + 0.5
        r = np.sqrt(dx * dx + dy * dy) / R
        rs = r * (1 + k * r * r) / (1 + k) * (src / 2)
        sc = np.where(r > 1e-5, rs / np.maximum(r * R, 1e-5), 1.0)
        mapx = (src / 2 + dx * sc).astype(np.float32); mapy = (src / 2 + dy * sc).astype(np.float32)
        edge = np.clip((1.0 - r) / 0.05, 0, 1)
        dark = (1.0 - 0.55 * np.clip(r, 0, 1) ** 2.2)
        _FISH[key] = (mapx, mapy, (edge * dark).astype(np.float32)[..., None])
    return _FISH[key]


def peephole_image(draw_fn, src=1200, out=980, k=0.85, tint=(0.92, 1.0, 0.95)):
    surf = skia.Surface(src, src)
    draw_fn(surf.getCanvas(), src)
    arr = surf.makeImageSnapshot().toarray()[..., :3]
    mapx, mapy, mask = _fish_maps(src, out, k)
    o = cv2.remap(arr, mapx, mapy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT).astype(np.float32)
    o = o * mask
    o[..., 0] *= tint[2]; o[..., 1] *= tint[1]; o[..., 2] *= tint[0]
    bgra = np.dstack([np.clip(o, 0, 255), np.where(mask[..., 0] > 0.001, 255, 0)[..., None].astype(np.float32) * np.clip(mask[..., :1] * 3, 0, 1)[..., 0:1]]).astype(np.uint8)
    # premultiply for skia
    a = bgra[..., 3:4].astype(np.float32) / 255.0
    bgra[..., :3] = (bgra[..., :3].astype(np.float32) * a).astype(np.uint8)
    return skia.Image.fromarray(np.ascontiguousarray(bgra), colorType=skia.kBGRA_8888_ColorType, alphaType=skia.kPremul_AlphaType)


# ------------------------------------------------------------------ the apartment entry: door, coat, closet (2D, parallax-free, camera moves over it)
def _ring(c, x, y, r, w=14):
    sh = skia.GradientShader.MakeLinear([(x - r, y - r), (x + r, y + r)], [ci(225, 190, 110), ci(120, 85, 40), ci(210, 170, 95)])
    c.drawCircle(x, y, r, paint(shader=sh, stroke=w))


def draw_room(c, t, cx=540, cy=900, zoom=1.0, roll=0.0, knocks=(), cknocks=(), under=1.0, feet=0.0, closet_open=0.0, eyes=0.0, fingers=0.0,
              coat=0.0, peep_glow=0.0, nightlight=0.0):
    c.save(); c.translate(W / 2, H / 2); c.rotate(roll); c.scale(zoom, zoom); c.translate(-cx, -cy)
    # wall + wallpaper stripes
    vgrad(c, -1400, -900, 3000, 1390, (26, 36, 42), (13, 19, 23))
    for i in range(-24, 44):
        if i % 2 == 0: c.drawRect(skia.Rect(i * 60, -900, i * 60 + 30, 1390), paint((255, 255, 255), 0.022))
    glow(c, 540, 1250, 1100, (90, 140, 120), 0.10 * under, blend=skia.BlendMode.kPlus)
    c.drawOval(skia.Rect(-80, 80, 260, 420), paint((0, 0, 0), 0.10, blur=60))       # damp stain
    # baseboard + floor
    c.drawRect(skia.Rect(-1400, 1346, 3000, 1388), paint((9, 11, 13)))
    c.drawRect(skia.Rect(-1400, 1344, 3000, 1349), paint((70, 86, 90), 0.35))
    vgrad(c, -1400, 1388, 3000, 3600, (20, 15, 12), (5, 4, 4))
    for xx in range(-2600, 3600, 240):
        p = skia.Path(); p.moveTo(540 + (xx - 540) * 0.02, 1388); p.lineTo(xx, 3600)
        c.drawPath(p, paint((0, 0, 0), 0.55, stroke=3, round_=False))
    # light fan from under the door
    if under > 0.01:
        sh = skia.GradientShader.MakeLinear([(0, 1388), (0, 2200)], [ci(190, 235, 195, 0.55 * under), ci(190, 235, 195, 0.0)])
        _PATH.reset(); _PATH.moveTo(300, 1388); _PATH.lineTo(780, 1388); _PATH.lineTo(1100, 2200); _PATH.lineTo(-20, 2200); _PATH.close()
        c.drawPath(_PATH, paint(shader=sh))
    # closet (left)
    cw0, cw1 = -500.0, -90.0
    ck = sum(decay(t, tk, 6.0) * math.sin((t - tk) * 64) for tk in cknocks) * 9.0
    c.save(); c.translate(ck, 0)
    c.drawRect(skia.Rect(cw0 - 34, 300, cw1 + 34, 1388), paint((12, 10, 9)))               # frame
    c.drawRect(skia.Rect(cw0, 330, cw1, 1388), paint((2, 2, 3)))                               # void behind the door
    op = closet_open
    xr = cw1 - op * 300.0
    if eyes > 0.01:
        ex, ey = cw1 - 60 - op * 40, 790
        for dx in (-34, 34):
            glow(c, ex + dx, ey, 70, (235, 245, 255), 0.75 * eyes)
            c.drawOval(skia.Rect(ex + dx - 17, ey - 11, ex + dx + 17, ey + 11), paint((248, 252, 255), eyes))
            c.drawCircle(ex + dx + 2, ey, 5, paint((0, 0, 0), eyes))
    if fingers > 0.01:
        for j in range(4):
            base_y = 700 + j * 46
            wig = math.sin(t * 2.3 + j * 1.2) * 8 * fingers
            pts = [(xr + 4, base_y), (xr + 70 * fingers, base_y - 4 + wig), (xr + 140 * fingers, base_y + 26 + wig), (xr + 176 * fingers, base_y + 100 + wig), (xr + 170 * fingers, base_y + 170 + wig)]
            path = skia.Path(); path.moveTo(*pts[0])
            for q in pts[1:]: path.lineTo(*q)
            c.drawPath(path, paint((10, 12, 12), 0.95, stroke=30))
            c.drawPath(path, paint((182, 188, 180), 0.97, stroke=21))
            for q in pts[1:-1]: c.drawCircle(q[0], q[1], 15, paint((140, 146, 138), 0.9))
    # louvered door leaf (hinged left; narrows when open)
    quad(c, [(cw0, 330), (xr, 330 + op * 26), (xr, 1388 - op * 26), (cw0, 1388)], (30, 38, 38))
    for yy in range(350, 1380, 24):
        a0 = yy; quad(c, [(cw0 + 14, a0), (xr - 14, a0 + op * 2), (xr - 14, a0 + 9 + op * 2), (cw0 + 14, a0 + 9)], (10, 14, 15), 0.9)
        quad(c, [(cw0 + 14, a0 + 9), (xr - 14, a0 + 9 + op * 2), (xr - 14, a0 + 12 + op * 2), (cw0 + 14, a0 + 12)], (80, 100, 100), 0.18)
    c.drawCircle(xr - 34 - op * 6, 900, 15, paint((150, 130, 90)))
    c.restore()
    # coat on a hook (looks like somebody standing there)
    c.save(); c.translate(160, 520); c.rotate(coat * 2.0 * math.sin(t * 2.0) + 0.6 * math.sin(t * 0.7))
    path = skia.Path(); path.moveTo(0, 20); path.cubicTo(-52, 40, -70, 130, -60, 250); path.lineTo(-78, 720); path.lineTo(80, 720); path.lineTo(70, 250); path.cubicTo(80, 130, 52, 40, 0, 20); path.close()
    c.drawPath(path, paint((70, 90, 96), 0.40, stroke=5))
    c.drawPath(path, paint((7, 9, 11)))
    c.drawCircle(0, 6, 10, paint((90, 75, 50)))
    c.restore()
    c.drawRect(skia.Rect(160 - 70, 508, 160 + 70, 516), paint((50, 44, 36)))
    # shoes
    for sx, sy, ang in ((860, 1424, -8), (940, 1436, 12)):
        c.save(); c.translate(sx, sy); c.rotate(ang); c.drawOval(skia.Rect(-46, -17, 46, 17), paint((8, 9, 10))); c.restore()
    # door
    dk = sum(decay(t, tk, 7.0) * math.sin((t - tk) * 72) for tk in knocks) * 8.0
    c.save(); c.translate(dk, 0); c.rotate(dk * 0.04)
    c.drawRect(skia.Rect(246, 266, 834, 1388), paint((13, 11, 10)))
    c.drawRect(skia.Rect(280, 300, 800, 1388), paint((38, 52, 58)))
    vgrad(c, 280, 300, 800, 1388, (60, 80, 86), (22, 32, 36), 0.30, 0.55)
    for (x0, y0, x1, y1) in ((322, 346, 498, 760), (582, 346, 758, 760), (322, 820, 498, 1330), (582, 820, 758, 1330)):
        c.drawRect(skia.Rect(x0, y0, x1, y1), paint((10, 14, 16), 0.55))
        c.drawRect(skia.Rect(x0 + 6, y0 + 6, x1 - 6, y1 - 6), paint((46, 62, 68), 0.65))
        c.drawRect(skia.Rect(x0 + 6, y0 + 6, x1 - 6, y0 + 10), paint((120, 150, 155), 0.3))
    # peephole: brass ring + lens (glows when the hall light hits it)
    _ring(c, 540, 600, 30, 9)
    c.drawCircle(540, 600, 22, paint((6, 10, 10)))
    glow(c, 540, 600, 70 + 70 * peep_glow, (180, 240, 190), 0.30 + 0.55 * peep_glow)
    c.drawCircle(540, 600, 5, paint((230, 255, 230), 0.4 + 0.6 * peep_glow))
    # lock, knob, chain
    c.drawRoundRect(skia.Rect(712, 812, 770, 880), 10, 10, paint((130, 110, 70)))
    c.drawCircle(741, 846, 15, paint((20, 18, 14)))
    c.drawCircle(730, 960, 36, paint((150, 125, 80))); c.drawCircle(721, 951, 11, paint((255, 235, 180), 0.45))
    c.drawLine(762, 700, 800, 700, paint((120, 110, 90), 1.0, stroke=5))
    for i in range(7): c.drawCircle(776 + math.sin(t * 1.0 + i) * 0.5 + i * 3.5, 700 + (i % 2) * 5, 4, paint((150, 140, 120), 0.9, stroke=2))
    c.restore()
    for tk in knocks:
        if 0 <= t - tk < 1.4:
            gr = random.Random(int(tk * 100))
            for i in range(16):
                px = 290 + gr.random() * 500; py = 300 + (t - tk) * (160 + gr.random() * 240) ; a = 0.55 * (1 - (t - tk) / 1.4)
                c.drawCircle(px + dk, py, 2 + gr.random() * 2.5, paint((200, 210, 200), a))
    # gap under the door: light + feet
    gl = 0.55 + 0.45 * under
    c.drawRect(skia.Rect(290 + dk, 1380, 790 + dk, 1392), paint((200, 240, 205), 0.85 * under))
    if feet > 0.01:
        for fx in (440, 640):
            c.drawOval(skia.Rect(fx - 50 + dk, 1378, fx + 50 + dk, 1396), paint((2, 3, 3), feet))
    c.restore()


# ------------------------------------------------------------------ apartment tower at night (camera climbs the facade)
FLOOR_H = 300.0
def draw_tower(c, t, scroll, zoom=1.0, lit_floor=14, rain=1.0, zc=(W / 2, H / 2)):
    """scroll: world y of the screen centre, in floors (1 = ground floor). floor n spans y = -(n-1)*FLOOR_H"""
    c.save(); c.translate(*zc); c.scale(zoom, zoom); c.translate(-zc[0], -zc[1])
    vgrad(c, -400, -400, W + 400, H + 400, (6, 9, 18), (22, 30, 46))
    glow(c, 860, 250, 380, (170, 190, 235), 0.25)
    c.drawCircle(860, 250, 54, paint((205, 215, 240), 0.8))
    rr = random.Random(3)
    for i in range(7):                                         # clouds drifting
        x = (rr.random() * 1500 + t * (14 + 10 * rr.random())) % 1700 - 300; y = rr.random() * 700
        c.drawOval(skia.Rect(x - 260, y - 40, x + 260, y + 40), paint((14, 20, 32), 0.55, blur=34))
    off = (scroll - 1) * FLOOR_H
    # far towers
    for k, (bx, bw, bh) in enumerate(((-40, 260, 1900), (230, 200, 1500), (760, 300, 2000), (930, 240, 1650))):
        by = H - 200 + off * 0.35 - bh + 700
        c.drawRect(skia.Rect(bx, by, bx + bw, H + 2000), paint((9, 13, 22)))
        for r in range(0, int(bh / 70)):
            for q in range(int(bw / 60)):
                if (r * 7 + q * 13 + k * 5) % 11 == 0: c.drawRect(skia.Rect(bx + 14 + q * 60, by + 40 + r * 70, bx + 34 + q * 60, by + 60 + r * 70), paint((255, 210, 140), 0.45))
    # facade
    fx0, fx1 = 120, 960
    c.drawRect(skia.Rect(fx0, -4000, fx1, H + 2400), paint((11, 15, 24)))
    c.drawRect(skia.Rect(fx0, -4000, fx0 + 6, H + 2400), paint((90, 110, 150), 0.25))
    c.drawRect(skia.Rect(fx1 - 6, -4000, fx1, H + 2400), paint((90, 110, 150), 0.25))
    for fl in range(1, 40):
        y = H * 0.40 - (fl - 1) * FLOOR_H + off          # top of the window row for this floor
        if y < -300 or y > H + 300: continue
        c.drawRect(skia.Rect(fx0, y + 236, fx1, y + 250), paint((26, 34, 50)))
        for col in range(4):
            x = fx0 + 46 + col * 196
            h = (fl * 31 + col * 17) % 9
            me = (fl == lit_floor and col == 1)
            if me:
                fl_ = 0.8 + 0.2 * math.sin(t * 7.0) * (1 if int(t * 3) % 5 == 0 else 0.3)
                glow(c, x + 70, y + 110, 240, (255, 200, 120), 0.45 * fl_)
                c.drawRect(skia.Rect(x, y, x + 140, y + 210), paint((255, 205, 130), 0.95 * fl_))
                c.drawRect(skia.Rect(x + 66, y, x + 74, y + 210), paint((70, 40, 20)))
                c.drawRect(skia.Rect(x, y + 98, x + 140, y + 106), paint((70, 40, 20)))
            elif h < 2:
                c.drawRect(skia.Rect(x, y, x + 140, y + 210), paint((255, 225, 160), 0.30 + 0.1 * math.sin(t * 0.6 + fl)))
            else:
                c.drawRect(skia.Rect(x, y, x + 140, y + 210), paint((20, 30, 48)))
                c.drawRect(skia.Rect(x, y, x + 140, y + 30), paint((90, 120, 170), 0.10))
        c.drawString(str(fl), 40, y + 140, font(POP, 30), paint((150, 170, 200), 0.35))
    if rain > 0:
        rr = random.Random(9)
        for i in range(170):
            x0 = rr.random() * 1300 - 100; sp = 1500 + rr.random() * 900; y0 = (rr.random() * 2200 + t * sp) % 2200 - 150
            c.drawLine(x0, y0, x0 - 20, y0 + 70, paint((190, 210, 255), 0.22 * rain, stroke=2))
    c.restore()


# ------------------------------------------------------------------ peephole ring (drawn over the fisheye image)
def draw_ring(c, cx, cy, r, shine=1.0):
    sh = skia.GradientShader.MakeLinear([(cx - r, cy - r), (cx + r, cy + r)], [ci(230, 195, 115), ci(90, 62, 28), ci(215, 175, 100)])
    c.drawCircle(cx, cy, r + 14, paint((0, 0, 0), 0.9, stroke=40))
    c.drawCircle(cx, cy, r + 6, paint(shader=sh, stroke=26))
    c.drawCircle(cx, cy, r - 6, paint((255, 255, 255), 0.08 * shine, stroke=6))


def draw_door_surface(c, t, cx=540, cy=880, ring_r=60, zoom_w=1.0):
    """close-up of the door with the brass peephole at (cx, cy); ring_r grows as the camera pushes in"""
    c.drawRect(skia.Rect(0, 0, W, H), paint((16, 22, 26)))
    vgrad(c, 0, 0, W, H, (44, 58, 64), (12, 18, 20), 0.5, 0.9)
    gr = random.Random(2)
    for i in range(46):                                   # faint paint streaks
        x = gr.random() * W; c.drawRect(skia.Rect(x, 0, x + 2 + gr.random() * 5, H), paint((0, 0, 0), 0.07))
    sh = skia.GradientShader.MakeLinear([(cx - ring_r, cy - ring_r), (cx + ring_r, cy + ring_r)], [ci(235, 200, 120), ci(95, 66, 30), ci(220, 180, 105)])
    c.drawCircle(cx, cy, ring_r * 1.18, paint((0, 0, 0), 0.5, blur=ring_r * 0.15))
    c.drawCircle(cx, cy, ring_r, paint(shader=sh))
    c.drawCircle(cx, cy, ring_r * 0.74, paint((4, 7, 7)))
    glow(c, cx, cy, ring_r * 0.9, (170, 235, 185), 0.32)
    c.drawCircle(cx - ring_r * 0.22, cy - ring_r * 0.22, ring_r * 0.10, paint((235, 255, 240), 0.55))
