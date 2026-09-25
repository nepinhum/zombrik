#!/usr/bin/env python3
# Draws the small effect sprites the mod needs and that no pack provides, into
# mod/assets/fx/. Sizes are in source pixels; the game draws 2 of them per world
# unit, same as the character art.
import pathlib

from PIL import Image

CORE = (255, 241, 194, 255)
EDGE = (255, 176, 64, 255)
TRAIL = (255, 138, 32, 140)

out = pathlib.Path(__file__).resolve().parent.parent / "mod" / "assets" / "fx"
out.mkdir(parents=True, exist_ok=True)

# Bullet: a bright core with a short warm trail, pointing +x like everything else.
bullet = Image.new("RGBA", (8, 3))
for x in range(8):
    bullet.putpixel((x, 1), CORE if x >= 5 else (EDGE if x >= 3 else TRAIL))
bullet.putpixel((6, 0), EDGE)
bullet.putpixel((6, 2), EDGE)
bullet.save(out / "bullet.png")
print(out / "bullet.png")
