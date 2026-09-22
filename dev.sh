#!/bin/sh
set -eu

root=$(cd "$(dirname "$0")" && pwd)
bin=${EMBRIK_BIN:-$root/embrik/build/linux/x86_64/release/embrik}

mkdir -p "$root/run/mods"
ln -sfn ../embrik/asset "$root/run/asset"
ln -sfn ../../mod "$root/run/mods/zombrik"
# Map mods load alongside the game, like Counter-Strike maps.
for map in "$root"/maps/*/; do
    name=$(basename "$map")
    ln -sfn "../../maps/$name" "$root/run/mods/$name"
done

cd "$root/run"
exec "$bin" "$@"
