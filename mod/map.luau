-- Maps are separate mods (maps/zm_*) and the server runs one
-- at a time inside a scene, so changing maps unloads everything
-- the last onespawned. Map data comes from Tiled via tools/tmx.py compile.
local M = {}

local FLOOR_PLANE = -20000
local BOUNDS_THICKNESS = 64

local maps = {}
local order: { string } = {}
local current = nil -- { name, scene, data }
local listeners: { () -> () } = {}

function M.register(name: string, data)
    if maps[name] == nil then
        table.insert(order, name)
    end
    maps[name] = data
end

function M.names(): { string }
    return table.clone(order)
end

function M.current(): string?
    return current and current.name
end

-- Runs after every map change, inside the new map's scene.
function M.on_change(fn: () -> ())
    table.insert(listeners, fn)
end

function M.spawn(def): Entity
    return current.scene:spawn(def)
end

function M.entities(class: string)
    local out = {}
    for _, e in current.data.entities do
        if e.class == class then
            table.insert(out, e)
        end
    end
    return out
end

function M.spawn_point(): Vec
    local points = M.entities("player_spawn")
    if #points == 0 then
        return { x = 0, y = 0 }
    end
    local p = points[math.random(#points)]
    return { x = p.x, y = p.y }
end

-- Applies the map's ambiance to a player's body; the renderer reads Vision and
-- PostStack from the local player's entity.
function M.dress(body: Entity)
    local env = current.data.env
    local ambient = env.ambient_color or { r = 1, g = 1, b = 1 }
    body.Vision = { kind = VisionKind.None, ambient = env.ambient or 1, ambient_r = ambient.r, ambient_g = ambient.g, ambient_b = ambient.b }
    body.PostStack = { vignette = env.vignette or 0, saturation = env.saturation or 1, distortion = 1, flash_fade = 1 }
end

local function build(data)
    M.spawn({
        Position = { x = 0, y = 0 },
        Rotation = { angle = 0 },
        RenderDepth = { plane = FLOOR_PLANE },
        Replicated = {},
    }):sprite({ { tex = data.backdrop, nearest = true } })

    -- Props sort by their base and, unless the compiler marked them decor, collide
    -- and cast shadows there.
    for _, p in data.props do
        local def = {
            Position = { x = p.x, y = p.y },
            Rotation = { angle = 0 },
            RenderDepth = { y_sort = true },
            Replicated = {},
        }
        if p.solid then
            def.CollisionBox = { width = p.box[1], height = p.box[2] }
            def.Occluder = { half_x = p.box[1] / 2, half_y = p.box[2] / 2, opacity = 0.8 }
            def.Static = {}
        end
        M.spawn(def):sprite({ { tex = p.tex, nearest = true, pivot = p.pivot } })
    end

    -- Colliders are Replicated so client prediction collides with them too.
    local function wall(x: number, y: number, w: number, h: number)
        M.spawn({
            Position = { x = x, y = y },
            Rotation = { angle = 0 },
            CollisionBox = { width = w, height = h },
            Static = {},
            Replicated = {},
        })
    end
    for _, w in data.walls do
        wall(w.x, w.y, w.w, w.h)
    end
    local hw, hh, t = data.size[1] / 2, data.size[2] / 2, BOUNDS_THICKNESS
    wall(0, -hh - t / 2, data.size[1] + 2 * t, t)
    wall(0, hh + t / 2, data.size[1] + 2 * t, t)
    wall(-hw - t / 2, 0, t, data.size[2])
    wall(hw + t / 2, 0, t, data.size[2])

    for _, l in M.entities("light") do
        local c = l.color or { r = 1, g = 1, b = 1 }
        M.spawn({
            Position = { x = l.x, y = l.y },
            Light = { r = c.r, g = c.g, b = c.b, radius = l.radius or 220, intensity = l.intensity or 1,
                      flicker = l.flicker or 0, softness = 0.5, shadows = true },
            Replicated = {},
        })
    end
end

function M.change(name: string): boolean
    local data = maps[name]
    if data == nil then
        return false
    end
    if current then
        current.scene:unload()
    end
    current = { name = name, scene = world.scene("map/" .. name), data = data }
    local bg = data.env.background or { r = 0, g = 0, b = 0 }
    world.background({ r = bg.r, g = bg.g, b = bg.b })
    current.scene:load(function()
        build(data)
        for _, fn in listeners do
            fn()
        end
    end)
    for _, player in world.players() do
        local body = player:entity()
        if body then
            local p = M.spawn_point()
            body:teleport(p.x, p.y)
            M.dress(body)
        end
    end
    log("map: " .. name)
    return true
end

return M
