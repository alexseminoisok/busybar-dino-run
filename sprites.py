"""Pixel art for Dino Run (72x16 front display).

Sprites are lists of strings; "." is transparent, any other char is a palette
key. Bit masks for collisions are derived from the "#" pixels (body), so
decorative pixels (eye, highlights) can use other keys and still count via
COLLIDE below.
"""

# Palette: Chrome's dark-mode look, tuned for LEDs (black = off).
PAL = {
    "#": (172, 172, 172),   # sprites (dino, birds)
    "v": (140, 205, 140),   # cacti (pale green)
    "e": (0, 0, 0),         # dino eye (a hole in the head)
    "E": (230, 230, 230),   # dead dino's wide eye
    "g": (150, 150, 150),   # ground line
    "p": (70, 70, 70),      # ground pebbles
    "c": (52, 52, 58),      # clouds
    "s": (60, 60, 72),      # dim star
    "S": (130, 130, 150),   # bright star
}
COLLIDE = set("#eEv")        # pixels that count for collisions

# ── Dino (feet on the bottom row) ───────────────────────────
DINO_W = 11                 # sprite canvas width (duck pose is the widest)

DINO_RUN = [
    ["....#####..",
     "....#e####.",
     "....######.",
     "#..####....",
     "##.######..",
     ".######....",
     "..#..#.....",
     "..##......."],
    ["....#####..",
     "....#e####.",
     "....######.",
     "#..####....",
     "##.######..",
     ".######....",
     "..#..#.....",
     ".....##...."],
]
DINO_STAND = [
    "....#####..",
    "....#e####.",
    "....######.",
    "#..####....",
    "##.######..",
    ".######....",
    "..#..#.....",
    "..##.##....",
]
DINO_BLINK = [
    "....#####..",
    "....######.",
    "....######.",
    "#..####....",
    "##.######..",
    ".######....",
    "..#..#.....",
    "..##.##....",
]
DINO_JUMP = DINO_STAND
DINO_DEAD = [
    "....#####..",
    "....#E####.",
    "....######.",
    "#..###.....",
    "##.######..",
    ".######....",
    "..#..#.....",
    "..##.##....",
]
DINO_DUCK = [
    ["...........",
     "...........",
     "...........",
     ".......####",
     "#.....##e##",
     "##########.",
     ".#######...",
     "..#..##...."],
    ["...........",
     "...........",
     "...........",
     ".......####",
     "#.....##e##",
     "##########.",
     ".#######...",
     ".##...#...."],
]

# Collision masks: the art minus a forgiving pixel or two (tail tip, snout).
DINO_HIT_STAND = [
    "...........",
    ".....###...",
    ".....####..",
    "...####....",
    "...#####...",
    ".######....",
    "..#..#.....",
    "..##.##....",
]
DINO_HIT_DUCK = [
    "...........",
    "...........",
    "...........",
    "........##.",
    "......####.",
    ".#########.",
    ".#######...",
    "..#..##....",
]

# ── Obstacles (bottom row sits on the ground) ───────────────
CACTUS_S = [
    "..v..",
    "v.v.v",
    "vvvvv",
    "..v..",
]
CACTUS_L = [
    "..v..",
    "v.v..",
    "v.v.v",
    "vvvvv",
    "..v..",
]
# Hitboxes without the outer arm tips: brushing an arm doesn't count.
CACTUS_S_HIT = [
    "..v..",
    "..v..",
    ".vvv.",
    "..v..",
]
CACTUS_L_HIT = [
    "..v..",
    "..v..",
    "..v..",
    ".vvv.",
    "..v..",
]
BIRD = [  # two flap frames, 8x5, flying left (beak on the left)
    ["....#...",
     "....##..",
     ".#..###.",
     "########",
     "....###."],
    ["........",
     "........",
     ".#......",
     "########",
     "...####."],
]
BIRD_HIT = ["........",
            "........",
            ".#......",
            ".######.",
            "........"]


def hstack(sprite, n, gap=1):
    """n copies side by side (cactus clusters)."""
    pad = "." * gap
    return [pad.join([row] * n) for row in sprite]


# name -> (frames, top_row, hit_mask). top_row is where the sprite's first
# row is drawn on the 72x16 screen (ground line is row 14, so things standing
# on it end at row 13).
def obstacle_types():
    t = {}
    for n in (1, 2, 3):
        s = hstack(CACTUS_S, n)
        t["s%d" % n] = ([s], 14 - len(s), hstack(CACTUS_S_HIT, n))
        l = hstack(CACTUS_L, n)
        t["l%d" % n] = ([l], 14 - len(l), hstack(CACTUS_L_HIT, n))
    t["bl"] = (BIRD, 9, BIRD_HIT)      # low: jump it
    t["bm"] = (BIRD, 4, BIRD_HIT)      # mid: duck under it
    t["bh"] = (BIRD, 0, BIRD_HIT)      # high: just keep running
    return t
