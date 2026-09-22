#!/usr/bin/env python3
# Embrik's angle 0 faces +x, but the overhead sprites in asset/packs/survivors are drawn
# facing up. Writes copies turned 90° clockwise into mod/assets/characters/,
# which the game serves as zombrik/characters/<name>.png.
import pathlib
from PIL import Image

root = pathlib.Path(__file__).resolve().parent.parent
src = root / "asset" / "packs" / "survivors"
dst = root / "mod" / "assets" / "characters"
dst.mkdir(parents=True, exist_ok=True)
for name in ["survivor_unarmed", "survivor_pistol", "survivor_rifle", "survivor_shotgun", "survivor_smg", "zombie"]:
    Image.open(src / f"{name}.png").rotate(-90).save(dst / f"{name}.png")
