#!/usr/bin/env python3
"""Render preview/gameplay.gif from the game's own sprites and physics:
sky, ground texture, obstacles at speed 1 (1 px per 16 ms frame) and the
dino's jump arc, with the dino auto-jumping in the middle of each obstacle's
clear window. No HUD text (that comes from the bar's fonts).

    python3 test/preview_gif.py
"""
import os, sys
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import sprites as S
import build_assets as B
from shots import led

N = 400                                   # frames (shown at 20 ms: GIF's finest step)
SCRIPT = [(0, "s1"), (95, "bh"), (175, "l2"), (270, "bl"), (345, "s2")]
STAND, HS = B.mask_rows(S.DINO_HIT_STAND), B.jump_heights()
TYPES = S.obstacle_types()


def obst_x(spawn, f):
    return B.W - (f - spawn)


def clear_jump(spawn, name):
    art, top, hit = TYPES[name]
    hm, w = B.mask_rows(hit), len(art[0][0])
    run_ok = all(not B.collides(STAND, 6, hm, top, obst_x(spawn, f) - B.DINO_X)
                 for f in range(spawn, spawn + B.W + w + 1))
    if run_ok:
        return None
    good = []
    for j in range(spawn, spawn + B.W + w):
        ok = True
        for f in range(spawn, spawn + B.W + w + 1):
            i = f - j
            h = HS[i - 1] if 1 <= i <= B.JUMP_N else 0
            if B.collides(STAND, 6 - h, hm, top, obst_x(spawn, f) - B.DINO_X):
                ok = False
                break
        if ok:
            good.append(j)
    return good[len(good) // 2]


jumps = [j for j in (clear_jump(s, n) for s, n in SCRIPT) if j is not None]
tex = B.ground_texture()
tex2 = [r + r for r in tex]
frames = []
for f in range(N):
    im = Image.new("RGBA", (B.W, B.H), (0, 0, 0, 255))
    for (x, y, ph) in B.STARS:
        k = (f * 2 * 4 // (B.CLOUD_P * B.CLOUD_DIV) + ph) % 4
        im.putpixel((x, y), B.rgba(S.PAL["S"] if k == 0 else S.PAL["s"]))
    off = f // B.CLOUD_DIV
    for cx0, cy in ((10, 3), (70, 6), (112, 2)):
        for rep in (-B.CLOUD_P, 0, B.CLOUD_P):
            B.blit(im, B.CLOUD, cx0 - off + rep, cy)
    go = f % B.GROUND_P
    B.blit(im, [r[go:go + B.W] for r in tex2], 0, 13)
    for spawn, name in SCRIPT:
        if f >= spawn:
            art = TYPES[name][0]
            B.blit(im, art[((f - spawn) // B.FLAP) % len(art)], obst_x(spawn, f), TYPES[name][1])
    h = 0
    for j in jumps:
        if 1 <= f - j <= B.JUMP_N:
            h = HS[f - j - 1]
    spr = S.DINO_JUMP if h else S.DINO_RUN[(f // 6) % 2]
    B.blit(im, spr, B.DINO_X, 14 - len(spr) - h)
    b = im.convert("RGB").tobytes()
    px = [tuple(b[i:i + 3]) for i in range(0, len(b), 3)]
    frames.append(led(px).resize((72 * 6, 16 * 6), Image.LANCZOS))
out = os.path.join(HERE, "..", "preview", "gameplay.gif")
frames[0].save(out, save_all=True, append_images=frames[1:], duration=20, loop=0, optimize=True)
print("preview/gameplay.gif %d frames %.0f KB" % (len(frames), os.path.getsize(out) / 1024))
