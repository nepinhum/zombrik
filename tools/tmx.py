#!/usr/bin/env python3
# Tiled maps (orthogonal, CSV, finite or infinite) to Zombrik content.
# Animated tiles use their first frame; output is upscaled with nearest filtering.
#
#   tools/tmx.py flatten map.tmx out.png [--scale N] [--skip Layer,Layer]
#       One PNG of every visible tile layer.
#
#   tools/tmx.py compile map.tmx MOD_DIR [--scale N]
#       Builds a map mod: MOD_DIR/map.luau plus MOD_DIR/assets/. Everything is
#       configured in Tiled:
#         tile layers         flattened into one backdrop; a layer with a bool
#                             property `solid` also becomes static boxes where its
#                             cells are at least `coverage` (default 0.5) opaque
#         image objects       props: a sprite whose collider is its opaque bounds;
#                             small ones are decor unless the image's tile sets
#                             `solid`
#         point objects       entities: {class, x, y, ...custom properties}
#         map properties      emitted as `env`
import argparse
import pathlib
import xml.etree.ElementTree as ET

from PIL import Image

FLIP_H, FLIP_V, FLIP_D = 0x80000000, 0x40000000, 0x20000000
GID = ~(FLIP_H | FLIP_V | FLIP_D) & 0xFFFFFFFF
TEXELS_PER_UNIT = 2  # embrik SPRITE_TEXELS_PER_UNIT
DECOR_BELOW = 20  # source px; smaller props get no collider by default


def properties(node) -> dict:
    out = {}
    props = node.find("properties")
    for p in props.findall("property") if props is not None else []:
        kind, value = p.get("type", "string"), p.get("value", p.text or "")
        if kind == "bool":
            out[p.get("name")] = value == "true"
        elif kind in ("int", "float"):
            out[p.get("name")] = float(value)
        elif kind == "color":
            # Tiled writes #AARRGGBB.
            v = value.lstrip("#")[-6:]
            out[p.get("name")] = {c: int(v[i : i + 2], 16) / 255 for c, i in (("r", 0), ("g", 2), ("b", 4))}
        else:
            out[p.get("name")] = value
    return out


class Map:
    def __init__(self, path: pathlib.Path):
        root = ET.parse(path).getroot()
        self.path = path
        self.tw, self.th = int(root.get("tilewidth")), int(root.get("tileheight"))
        self.properties = properties(root)

        # Grid tilesets: (firstgid, columns, image path); sheets load on first use,
        # so tilesets only hidden layers need may be absent.
        self.grids = []
        # Image collection tilesets: gid -> (image path, tile properties).
        self.images = {}
        for ts in root.findall("tileset"):
            first = int(ts.get("firstgid"))
            image = ts.find("image")
            if image is not None:
                self.grids.append((first, int(ts.get("columns")), path.parent / image.get("source")))
            for tile in ts.findall("tile"):
                timage = tile.find("image")
                if timage is not None:
                    self.images[first + int(tile.get("id"))] = (path.parent / timage.get("source"), properties(tile))
        self.grids.sort(key=lambda t: t[0])
        self.sheets = {}

        # [(name, properties, {(x, y): raw gid})] in draw order; names may repeat.
        self.layers = []
        self.objects = []
        for node in root:
            if node.get("visible") == "0":
                continue
            if node.tag == "layer":
                cells = {}
                data = node.find("data")
                for block in data.findall("chunk") or [data]:
                    bx, by = int(block.get("x", 0)), int(block.get("y", 0))
                    width = int(block.get("width", node.get("width")))
                    values = [int(v) for v in block.text.replace("\n", "").split(",") if v]
                    for i, raw in enumerate(values):
                        if raw:
                            cells[(bx + i % width, by + i // width)] = raw
                self.layers.append((node.get("name"), properties(node), cells))
            elif node.tag == "objectgroup":
                self.objects.extend(node.findall("object"))

        if root.get("infinite") == "1":
            every = [xy for _, _, cells in self.layers for xy in cells]
            self.x0, self.y0 = min(x for x, _ in every), min(y for _, y in every)
            self.w = max(x for x, _ in every) - self.x0 + 1
            self.h = max(y for _, y in every) - self.y0 + 1
        else:
            self.x0 = self.y0 = 0
            self.w, self.h = int(root.get("width")), int(root.get("height"))

    def sheet(self, source: pathlib.Path) -> Image.Image:
        if source not in self.sheets:
            self.sheets[source] = Image.open(source).convert("RGBA")
        return self.sheets[source]

    def tile(self, raw: int) -> Image.Image:
        first, columns, source = next(t for t in reversed(self.grids) if t[0] <= raw & GID)
        i = (raw & GID) - first
        x, y = (i % columns) * self.tw, (i // columns) * self.th
        im = self.sheet(source).crop((x, y, x + self.tw, y + self.th))
        if raw & FLIP_D:
            im = im.transpose(Image.Transpose.TRANSPOSE)
        if raw & FLIP_H:
            im = im.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        if raw & FLIP_V:
            im = im.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
        return im

    def render(self, keep=lambda name: True) -> Image.Image:
        canvas = Image.new("RGBA", (self.w * self.tw, self.h * self.th))
        for name, _, cells in self.layers:
            if keep(name):
                for (x, y), raw in cells.items():
                    canvas.alpha_composite(self.tile(raw), ((x - self.x0) * self.tw, (y - self.y0) * self.th))
        return canvas

    def solid_cells(self) -> set:
        # Wall layers carry faint edge shadows and gate ends over walkable ground;
        # only cells with enough opaque pixels block movement.
        out = set()
        for _, props, cells in self.layers:
            if not props.get("solid"):
                continue
            coverage = props.get("coverage", 0.5)
            for xy, raw in cells.items():
                alpha = self.tile(raw).getchannel("A").tobytes()
                if sum(1 for a in alpha if a) >= coverage * len(alpha):
                    out.add(xy)
        return out


def upscale(im: Image.Image, scale: int) -> Image.Image:
    return im.resize((im.width * scale, im.height * scale), Image.Resampling.NEAREST)


def footprint(im: Image.Image):
    # One rule for every prop: the collider is what you see, the sprite's opaque
    # bounds. Anything else (a tree blocking only at its trunk, say) makes half a
    # prop passable and collisions feel arbitrary. Returns the collider's center
    # and size in image pixels.
    left, top, right, bottom = im.getbbox()
    return (left + right) / 2, (top + bottom) / 2, right - left, bottom - top


def rectangles(cells: set) -> list[tuple[int, int, int, int]]:
    # Greedy: grow each run right, then down while the whole run stays filled.
    left = set(cells)
    out = []
    for y in sorted({y for _, y in cells}):
        for x in sorted(x for x, cy in cells if cy == y):
            if (x, y) not in left:
                continue
            w = 1
            while (x + w, y) in left:
                w += 1
            h = 1
            while all((x + i, y + h) in left for i in range(w)):
                h += 1
            for j in range(h):
                for i in range(w):
                    left.discard((x + i, y + j))
            out.append((x, y, w, h))
    return out


def lua_value(v) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, float):
        return f"{v:g}"
    if isinstance(v, dict):
        return "{ " + ", ".join(f"{k} = {lua_value(x)}" for k, x in v.items()) + " }"
    return '"' + str(v).replace("\\", "\\\\").replace('"', '\\"') + '"'


def flatten(args):
    m = Map(args.map)
    skip = set(filter(None, args.skip.split(",")))
    im = upscale(m.render(lambda name: name not in skip), args.scale)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    im.save(args.out)
    print(f"{args.out}: {im.width}x{im.height}")


def compile_map(args):
    m = Map(args.map)
    s = args.scale
    unit = s / TEXELS_PER_UNIT  # world units per source pixel
    cx, cy = m.w * m.tw / 2, m.h * m.th / 2  # map center in source pixels
    ox, oy = m.x0 * m.tw, m.y0 * m.th  # object coordinates are relative to tile 0,0
    mod = args.mod.name
    assets = args.mod / "assets"
    (assets / "props").mkdir(parents=True, exist_ok=True)

    def world(px: float, py: float) -> str:
        return f"x = {(px - ox - cx) * unit:g}, y = {(py - oy - cy) * unit:g}"

    lua = [f"-- Generated by tools/tmx.py from {args.map.name}. World units, map centered on 0,0.", "return {"]
    lua.append(f"    size = {{ {m.w * m.tw * unit:g}, {m.h * m.th * unit:g} }},")
    lua.append(f"    env = {lua_value(m.properties)},")

    upscale(m.render(), s).save(assets / "backdrop.png")
    lua.append(f'    backdrop = "{mod}/backdrop.png",')

    lua.append("    props = {")
    textures = {}
    props = 0
    for obj in m.objects:
        if obj.get("gid") is None:
            continue
        raw = int(obj.get("gid"))
        source, tile_props = m.images[raw & GID]
        name = source.stem + ("_h" if raw & FLIP_H else "")
        if name not in textures:
            im = Image.open(source).convert("RGBA")
            if raw & FLIP_H:
                im = im.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
            upscale(im, s).save(assets / "props" / f"{name}.png")
            fx, fy, bw, bh = footprint(im)
            solid = tile_props.get("solid", max(im.size) >= DECOR_BELOW)
            textures[name] = (im.size, fx, fy, bw, bh, solid)
        (w, h), fx, fy, bw, bh, solid = textures[name]
        # Tile objects anchor at their bottom-left corner.
        left, top = float(obj.get("x")), float(obj.get("y")) - h
        lua.append(
            f'        {{ tex = "{mod}/props/{name}.png", {world(left + fx, top + fy)}, '
            f"pivot = {{ {fx / w:.4f}, {fy / h:.4f} }}, box = {{ {bw * unit:g}, {bh * unit:g} }}, solid = {lua_value(solid)} }},"
        )
        props += 1
    lua.append("    },")

    lua.append("    entities = {")
    entities = 0
    for obj in m.objects:
        if obj.get("gid") is not None:
            continue
        cls = obj.get("class") or obj.get("type") or obj.get("name") or ""
        extra = "".join(f", {k} = {lua_value(v)}" for k, v in properties(obj).items())
        lua.append(f'        {{ class = "{cls}", {world(float(obj.get("x")), float(obj.get("y")))}{extra} }},')
        entities += 1
    lua.append("    },")

    lua.append("    walls = {")
    boxes = rectangles(m.solid_cells())
    for x, y, w, h in boxes:
        px, py = (x - m.x0) * m.tw + ox, (y - m.y0) * m.th + oy
        lua.append(
            f"        {{ {world(px + w * m.tw / 2, py + h * m.th / 2)}, w = {w * m.tw * unit:g}, h = {h * m.th * unit:g} }},"
        )
    lua.append("    },")
    lua.append("}")

    (args.mod / "map.luau").write_text("\n".join(lua) + "\n")
    print(f"{args.mod / 'map.luau'}: {props} props ({len(textures)} textures), {entities} entities, {len(boxes)} wall boxes")


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(required=True)

    p = sub.add_parser("flatten")
    p.add_argument("map", type=pathlib.Path)
    p.add_argument("out", type=pathlib.Path)
    p.add_argument("--scale", type=int, default=4)
    p.add_argument("--skip", default="")
    p.set_defaults(run=flatten)

    p = sub.add_parser("compile")
    p.add_argument("map", type=pathlib.Path)
    p.add_argument("mod", type=pathlib.Path, help="map mod directory; its name prefixes asset names")
    p.add_argument("--scale", type=int, default=4)
    p.set_defaults(run=compile_map)

    args = parser.parse_args()
    args.run(args)


main()
