#!/bin/sh
# Compiles every map mod's Tiled source (maps/<name>/src/<name>.tmx) into its
# map.luau and assets/. Run after editing a map in Tiled.
set -eu
cd "$(dirname "$0")/.."

for tmx in maps/*/src/*.tmx; do
    mod=$(dirname "$(dirname "$tmx")")
    rm -rf "$mod/assets"
    python3 tools/tmx.py compile "$tmx" "$mod"
done
