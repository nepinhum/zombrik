local map = require("zombrik/map")

-- Map rotation, first entry is the default. Maps not installed are skipped.
local MAPCYCLE = { "zm_street" }

command.register("map", {
    description = "Change the map",
    run = function(ctx, name: string)
        if map.change(name) then
            world.broadcast("§7Map changed to §f" .. name)
        else
            ctx:reply("§cNo map named " .. name .. ". §7Installed: " .. table.concat(map.names(), ", "))
        end
    end,
})

command.register("maps", {
    description = "List installed maps",
    run = function(ctx)
        ctx:reply("§7Maps: §f" .. table.concat(map.names(), ", ") .. " §7(current: " .. (map.current() or "none") .. ")")
    end,
})

-- The commands stage runs after every mod's runtime stage, so map mods, which
-- depend on this one and load after it, have all registered by now.
local start = nil
for _, name in MAPCYCLE do
    if table.find(map.names(), name) then
        start = name
        break
    end
end
start = start or map.names()[1]
if start then
    map.change(start)
else
    log("map: no maps installed")
end
