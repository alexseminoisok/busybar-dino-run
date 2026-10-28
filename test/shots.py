#!/usr/bin/env python3
"""test/shots/*.raw (base64 72x16 BGR from /api/screen) -> LED-style PNGs.

    python3 test/shots.py                 # contact sheet -> test/shots/sheet.png
    python3 test/shots.py a.raw b.raw ... # stack those -> preview/device.png
"""
import base64, os, sys
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
S, GAP = 8, 1                       # px per LED, dark gap between LEDs


def load(path):
    raw = open(path, "rb").read()
    try:
        px = base64.b64decode(raw, validate=True)
    except Exception:
        px = raw
    if len(px) != 72 * 16 * 3:
        raise ValueError("%s: %d bytes" % (path, len(px)))
    return [(px[i + 2], px[i + 1], px[i]) for i in range(0, len(px), 3)]


def led(pixels):
    im = Image.new("RGB", (72 * S, 16 * S), (6, 6, 6))
    d = ImageDraw.Draw(im)
    for i, c in enumerate(pixels):
        x, y = i % 72, i // 72
        d.rectangle([x * S, y * S, x * S + S - 1 - GAP, y * S + S - 1 - GAP],
                    fill=tuple(max(v, 16) for v in c))
    return im


def stack(ims, pad=10):
    w = max(i.width for i in ims)
    out = Image.new("RGB", (w + 2 * pad, sum(i.height for i in ims) + pad * (len(ims) + 1)), (0, 0, 0))
    y = pad
    for i in ims:
        out.paste(i, (pad, y))
        y += i.height + pad
    return out


if __name__ == "__main__":
    shots = os.path.join(HERE, "shots")
    if len(sys.argv) > 1:
        stack([led(load(os.path.join(shots, a))) for a in sys.argv[1:]]).save(
            os.path.join(HERE, "..", "preview", "device.png"))
        print("preview/device.png")
    else:
        names = sorted(n for n in os.listdir(shots) if n.endswith(".raw"))
        stack([led(load(os.path.join(shots, n))) for n in names], 4).save(os.path.join(shots, "sheet.png"))
        print("test/shots/sheet.png:", ", ".join(names))
