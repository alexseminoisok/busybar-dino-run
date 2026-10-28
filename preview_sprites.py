#!/usr/bin/env python3
"""Render every sprite onto one scaled-up PNG sheet: preview/sprites.png"""
import os
from PIL import Image, ImageDraw
import sprites as S

HERE = os.path.dirname(os.path.abspath(__file__))
SCALE = 12


def draw(im, spr, x, y):
    for j, row in enumerate(spr):
        for i, c in enumerate(row):
            if c != ".":
                im.putpixel((x + i, y + j), S.PAL[c])


items = [S.DINO_STAND, S.DINO_BLINK, S.DINO_RUN[0], S.DINO_RUN[1], S.DINO_DEAD,
         S.DINO_DUCK[0], S.DINO_DUCK[1], S.DINO_HIT_STAND, S.DINO_HIT_DUCK,
         S.CACTUS_S, S.CACTUS_L, S.hstack(S.CACTUS_S, 3), S.hstack(S.CACTUS_L, 2),
         S.BIRD[0], S.BIRD[1], S.BIRD_HIT]
w = sum(len(s[0]) + 2 for s in items)
im = Image.new("RGB", (w, 10), (20, 20, 40))
x = 1
for s in items:
    draw(im, s, x, 10 - len(s) - 1)
    x += len(s[0]) + 2
os.makedirs(os.path.join(HERE, "preview"), exist_ok=True)
im.resize((w * SCALE, 10 * SCALE), Image.NEAREST).save(os.path.join(HERE, "preview", "sprites.png"))
print("preview/sprites.png")
