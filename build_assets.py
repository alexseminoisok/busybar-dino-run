#!/usr/bin/env python3
"""Build Dino Run's native assets + game data.

Everything that moves is a native .anim the bar plays by itself, so motion is
exactly one step per display refresh (16 ms, 62.5 fps) no matter how slow
the JS is. JS only starts/switches sections and does the collision maths.

Measured on fw 27.14 (r1030): an .anim whose header says 76 fps (lv_timer
period 13 ms) advances exactly once per 16 ms display refresh. 60 fps gives
20 ms, 50 gives 24 ms, so 76 it is.

Layers (z): sky (clouds/stars) < ground < obstacles < dino < HUD.
Speeds are px per frame: 1, 1.25, 1.5, 1.75, 2 (62.5 .. 125 px/s). The
ground texture period (210 px) is a whole number of frames at every speed,
so each speed's section loops seamlessly and every section starts at
texture offset 0 — switching speed with await_previous_end is seamless.

"Still" sections (one frame each, pointing into the 1 px/frame sections)
freeze a layer at any position for the game-over screen.

    python3 build_assets.py            # -> community.dino_run/{anims,sounds,appmeta}
                                        #    + scripts/main.js (data injected)
"""
import json, math, os, random, struct, sys, tempfile
from pathlib import Path
from PIL import Image

import sprites as S

HERE = os.path.dirname(os.path.abspath(__file__))
APP_ID = "community.dino_run"
PKG = os.path.join(HERE, APP_ID)
FW = os.environ.get("BSB_FW", os.path.join(HERE, "..", "busybar-fw-jerryscript"))
sys.path.insert(0, os.path.join(FW, "scripts"))
from seq2anim import BSBAnimConverter  # noqa: E402

FPS_HDR = 76                 # -> 16 ms per frame on the bar (see above)
W, H = 72, 16
GROUND_Y = 14                # ground line row
TIERS = [1.0, 1.25, 1.5, 1.75, 2.0]
GROUND_P = 210               # texture period, px (210 / every tier speed is whole)
DINO_X = 3
DINO_W, DINO_H = S.DINO_W, 14  # dino element covers rows 0..13
JUMP_N = 36                  # frames in the air (0.58 s)
JUMP_H = 6                   # apex, px
CLOUD_P = 144                # sky loop width, px
CLOUD_DIV = 4                # clouds move 1 px every 4 frames
OBST_H = 14                  # obstacle element rows 0..13


def rgba(c, a=255):
    return c + (a,)


def blit(im, spr, x, y, sub=None):
    for j, row in enumerate(spr):
        yy = y + j
        if yy < 0 or yy >= im.height:
            continue
        for i, c in enumerate(row):
            xx = x + i
            if c == "." or xx < 0 or xx >= im.width:
                continue
            if sub:
                c = sub.get(c, c)
            im.putpixel((xx, yy), rgba(S.PAL[c]))


def write_anim(frames, sections, path, mode="argb8888"):
    with tempfile.TemporaryDirectory(prefix="dino-") as t:
        for i, im in enumerate(frames):
            im.save(os.path.join(t, "frame_%d.png" % i))
        with open(os.path.join(t, "meta.json"), "w") as f:
            json.dump({"fps": FPS_HDR, "color_mode": mode, "sections": sections}, f)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        BSBAnimConverter().convert_dir(Path(t), Path(path))
    print("  %-22s %4d frames %4d sections %7.1f KB" % (
        os.path.basename(path), len(frames), len(sections), os.path.getsize(path) / 1024))


def blank(w, h, mode="argb8888"):
    return Image.new("RGBA", (w, h), (0, 0, 0, 0 if mode == "argb8888" else 255))


# ── Sky ─────────────────────────────────────────────────────
CLOUD = ["..ccc....",
         ".cc..cc..",
         "ccccccccc"]
# Stars stay out of the text areas (title rows 1-5 / 8-11 across the middle,
# score top right), or they show through between the letters.
STARS = [(6, 2, 0), (15, 5, 1), (2, 9, 2), (17, 11, 3), (25, 7, 0), (40, 6, 2),
         (52, 7, 1), (30, 12, 3), (45, 12, 0), (58, 12, 2), (10, 0, 1), (63, 6, 3)]


def build_sky():
    n = CLOUD_P * CLOUD_DIV                       # 576 frames
    frames = []
    for f in range(n):
        im = blank(W, H, "rgb888")
        for (x, y, ph) in STARS:                  # each star twinkles twice per loop
            k = (f * 2 * 4 // n + ph) % 4
            col = S.PAL["S"] if k == 0 else S.PAL["s"]
            im.putpixel((x, y), rgba(col))
        off = f // CLOUD_DIV
        for cx0, cy in ((10, 3), (70, 6), (112, 2)):
            for rep in (-CLOUD_P, 0, CLOUD_P):
                blit(im, CLOUD, cx0 - off + rep, cy)
        frames.append(im)
    write_anim(frames, [{"name": "loop", "start": 0, "end": n - 1}],
               os.path.join(PKG, "anims", "sky.anim"), "rgb888")


# ── Ground ──────────────────────────────────────────────────
def ground_texture():
    rnd = random.Random(7)
    rows = [["."] * GROUND_P for _ in range(3)]
    for x in range(GROUND_P):
        rows[1][x] = "g"
    # Single pebbles below the line only: bumps on the feet row and longer
    # dashes blended with the dino's legs.
    for x in range(GROUND_P):
        if rnd.random() < 0.10 and (x == 0 or rows[2][x - 1] == "."):
            rows[2][x] = "p"
    return ["".join(r) for r in rows]


def build_ground():
    tex = ground_texture()
    tex2 = [r + r for r in tex]

    def frame(off):
        im = blank(W, 3)
        blit(im, [r[off:off + W] for r in tex2], 0, 0)
        return im

    frames, sections, tier_frames = [], [], []
    for k, s in enumerate(TIERS):
        n = round(GROUND_P / s)
        assert abs(n * s - GROUND_P) < 1e-9
        start = len(frames)
        for f in range(n):
            frames.append(frame(int(math.floor(s * f)) % GROUND_P))
        sections.append({"name": "t%d" % k, "start": start, "end": len(frames) - 1})
        tier_frames.append(n)
    for o in range(GROUND_P):                   # stills: tier 0 moves 1 px/frame
        sections.append({"name": "g%d" % o, "start": o, "end": o})
    write_anim(frames, sections, os.path.join(PKG, "anims", "ground.anim"))
    return tier_frames


# ── Obstacles ───────────────────────────────────────────────
FLAP = 9                                        # frames per wing position


def obstacle_x(s, f):
    return W - int(math.floor(s * f))


def build_obstacles(types, allowed):
    frames, sections, meta = [], [], {}
    for name, (art, top, hit) in types.items():
        w = len(art[0][0])
        meta[name] = {"w": w, "top": top, "tiers": {}}
        tier0_start = None
        for k, s in enumerate(TIERS):
            if k not in allowed[name] and k != 0:
                continue
            start = len(frames)
            f = 0
            while True:
                x = obstacle_x(s, f)
                im = blank(W, OBST_H)
                blit(im, art[(f // FLAP) % len(art)], x, top)
                frames.append(im)
                if x <= -w:
                    break
                f += 1
            sections.append({"name": "%s_%d" % (name, k), "start": start, "end": len(frames) - 1})
            if k == 0:
                tier0_start = start
            if k in allowed[name]:
                meta[name]["tiers"][k] = len(frames) - start
        for x in range(-w + 1, W):              # stills, from the 1 px/frame section
            fi = tier0_start + (W - x)
            sections.append({"name": "%s@%d" % (name, x), "start": fi, "end": fi})
    write_anim(frames, sections, os.path.join(PKG, "anims", "obst.anim"))
    return meta


# ── Dino ────────────────────────────────────────────────────
def jump_heights():
    return [int(round(4 * JUMP_H * (f / JUMP_N) * (1 - f / JUMP_N))) for f in range(1, JUMP_N + 1)]


def dino_frame(spr, h):
    im = blank(DINO_W, DINO_H)
    blit(im, spr, 0, DINO_H - len(spr) - h)
    return im


def build_dino():
    frames, sections = [], []

    def add(name, ims):
        start = len(frames)
        frames.extend(ims)
        sections.append({"name": name, "start": start, "end": len(frames) - 1})

    idle = [dino_frame(S.DINO_STAND, 0)] * 180 + [dino_frame(S.DINO_BLINK, 0)] * 9 + \
           [dino_frame(S.DINO_STAND, 0)] * 60 + [dino_frame(S.DINO_BLINK, 0)] * 8
    add("idle", idle)
    add("run", [dino_frame(S.DINO_RUN[0], 0)] * 6 + [dino_frame(S.DINO_RUN[1], 0)] * 6)
    add("duck", [dino_frame(S.DINO_DUCK[0], 0)] * 6 + [dino_frame(S.DINO_DUCK[1], 0)] * 6)
    add("jump", [dino_frame(S.DINO_JUMP, h) for h in jump_heights()])
    for h in range(JUMP_H + 1):
        add("dead%d" % h, [dino_frame(S.DINO_DEAD, h)])
    add("deadduck", [dino_frame(S.DINO_DUCK[0], 0)])
    write_anim(frames, sections, os.path.join(PKG, "anims", "dino.anim"))


# ── Collision masks (bit i = column i) ──────────────────────
def mask_rows(spr):
    out = []
    for row in spr:
        m = 0
        for i, c in enumerate(row):
            if c in S.COLLIDE:
                m |= 1 << i
        out.append(m)
    return out


def collides(dmask, dtop, omask, otop, dx):
    """dx = obstacle_x - dino_x."""
    for j, om in enumerate(omask):
        y = otop + j
        dj = y - dtop
        if dj < 0 or dj >= len(dmask) or not om:
            continue
        o = om << dx if dx >= 0 else om >> -dx
        if dmask[dj] & o:
            return True
    return False


def feasibility(types):
    """Which tiers each obstacle can appear at: it must be clearable with a
    comfortable timing window (jumped, ducked or simply run under)."""
    stand = mask_rows(S.DINO_HIT_STAND)
    duck = mask_rows(S.DINO_HIT_DUCK)
    hs = jump_heights()
    allowed, windows = {}, {}
    for name, (art, top, hit) in types.items():
        hm = mask_rows(hit)
        w = len(art[0][0])
        allowed[name], windows[name] = [], {}
        for k, s in enumerate(TIERS):
            life = int(math.ceil((W + w) / s)) + 1

            def hits(dtop_at):
                for f in range(life):
                    dt = dtop_at(f)
                    if dt is None:
                        continue
                    m, t = dt
                    if collides(m, t, hm, top, obstacle_x(s, f) - DINO_X):
                        return True
                return False

            run_ok = not hits(lambda f: (stand, 14 - 8))
            duck_ok = not hits(lambda f: (duck, 14 - 8))
            good = 0
            for j in range(-JUMP_N, life):
                def jt(f, j=j):
                    i = f - j
                    h = hs[i - 1] if 1 <= i <= JUMP_N else 0
                    return (stand, 14 - 8 - h)
                if not hits(jt):
                    good += 1
            windows[name][k] = {"run": run_ok, "duck": duck_ok, "jump": good}
            # run/duck-able birds are fair at any speed; jumps need >= 5 frames (80 ms)
            if run_ok or duck_ok or good >= 5:
                allowed[name].append(k)
    return allowed, windows, stand, duck


# ── Sounds (raw s16le 44.1 kHz mono) ────────────────────────
SR = 44100


def square(freq, dur, amp=0.32, decay=0.0):
    n = int(SR * dur)
    out = []
    for i in range(n):
        t = i / SR
        env = min(1.0, i / 120, (n - i) / 300) * math.exp(-decay * t)
        v = amp * env * (1 if math.sin(2 * math.pi * freq * t) >= 0 else -1)
        out.append(v)
    return out


def sweep(f0, f1, dur, amp=0.3):
    n = int(SR * dur)
    out, ph = [], 0.0
    for i in range(n):
        f = f0 + (f1 - f0) * i / n
        ph += 2 * math.pi * f / SR
        env = min(1.0, i / 120, (n - i) / 400)
        out.append(amp * env * (1 if math.sin(ph) >= 0 else -1))
    return out


def write_snd(name, samples):
    path = os.path.join(PKG, "sounds", name + ".snd")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(struct.pack("<%dh" % len(samples), *[int(max(-1, min(1, v)) * 32767) for v in samples]))


def build_sounds():
    write_snd("jump", sweep(520, 760, 0.07, 0.25))
    write_snd("score", square(1047, 0.07, 0.22) + [0.0] * int(SR * 0.03) + square(1568, 0.11, 0.22, 8))
    write_snd("hit", square(196, 0.09, 0.3) + [0.0] * int(SR * 0.025) + square(147, 0.16, 0.3, 6))


# ── Icons ───────────────────────────────────────────────────
ICON8 = ["...#####",
         "...#e###",
         "...#####",
         "#.###...",
         "######..",
         ".####...",
         "..#.#...",
         "..#.##.."]


def build_icons():
    d = os.path.join(PKG, "appmeta")
    os.makedirs(d, exist_ok=True)
    im = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
    blit(im, ICON8, 0, 0, {"#": "#"})
    im.save(os.path.join(d, "icon_front_8x8.png"))
    im = Image.new("RGBA", (11, 11), (0, 0, 0, 0))
    blit(im, S.DINO_STAND, 0, 1)
    for x in range(11):
        im.putpixel((x, 10), rgba(S.PAL["g"]))
    im.save(os.path.join(d, "icon_back_11x11.png"))


# ── Main ────────────────────────────────────────────────────
def main():
    types = S.obstacle_types()
    allowed, windows, stand, duck = feasibility(types)
    print("obstacle tiers:")
    for n in types:
        print("  %-3s %-16s %s" % (n, allowed[n], {k: v["jump"] for k, v in windows[n].items()}))

    print("anims:")
    build_sky()
    gframes = build_ground()
    ometa = build_obstacles(types, allowed)
    build_dino()
    build_sounds()
    build_icons()

    data = {
        "TIERS": TIERS,
        "GROUND_FRAMES": gframes,
        "GROUND_P": GROUND_P,
        "SKY_FRAMES": CLOUD_P * CLOUD_DIV,
        "JUMP": jump_heights(),
        "DINO_X": DINO_X,
        "HIT_STAND": stand,
        "HIT_DUCK": duck,
        "OBST": {n: {"w": m["w"], "top": m["top"], "hit": mask_rows(types[n][2]),
                     "frames": m["tiers"]}
                 for n, m in ometa.items()},
    }
    src = open(os.path.join(HERE, "main.src.js")).read()
    js = src.replace("/*@DATA@*/null", json.dumps(data, separators=(",", ":"), sort_keys=True))
    os.makedirs(os.path.join(PKG, "scripts"), exist_ok=True)
    with open(os.path.join(PKG, "scripts", "main.js"), "w") as f:
        f.write(js)
    print("scripts/main.js %.1f KB" % (len(js) / 1024))


if __name__ == "__main__":
    main()
