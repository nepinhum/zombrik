# zombrik

>**NOTICE!**
> Development is available at "dev" branch.

Top-down multiplayer zombie survival, built as a Luau mod for
[embrik](https://github.com/schphe/embrik). Quick play: join, shoot zombies, get
turned. Inspired by Brotato and 20 Minutes Till Dawn.

Early work in progress: there is a map, a survivor you can walk and aim with
and nothing to shoot yet. :D

## Build and run

Needs the engine's toolchain ([xmake](https://xmake.io)) and Python 3 with
Pillow for the map tools.

```sh
git clone --recurse-submodules <this repo>
cd embrik && xmake && cd ..

./dev.sh --server --port 5000      # dedicated server
./dev.sh --connect 127.0.0.1:5000  # client
./dev.sh                           # client with the engine menu
```

`dev.sh` runs the engine from a scratch `run/` directory and links `mod/` and
each map into the engine's `mods/`, so the submodule and repo root stay clean.

## Layout

```text
mod/        the game mode: map registry, spawning, chat commands
maps/       one mod per map, Counter-Strike style
asset/      source art; see each pack's NOTICE.md
tools/      Tiled map compiler and asset helpers
embrik/     the engine as a submodule
```

The server runs one map at a time. `/maps` lists what is installed, `/map <name>`
switches and the rotation's first entry in `mod/commands.luau` is the default.

## Maps

A map is its own mod (`maps/zm_street/`) authored in [Tiled](https://mapeditor.org).
Everything is configured in the map itself:

* tile layers are the ground; a `solid` property makes one collide
* image objects from the `props` tileset are props, colliding over their sprite
* point objects are entities: `player_spawn`, `zombie_spawn`, `light`
* map properties set the ambiance: `ambient`, `ambient_color`, `background`,
  `vignette`, `saturation`

Edit `maps/<name>/src/<name>.tmx`, then rebuild and restart the server:

```sh
./tools/build_maps.sh
```

## Assets

Every pack under `asset/` carries a `NOTICE.md`. Everything here is free to use
and redistribute, CC0 or equivalent.
