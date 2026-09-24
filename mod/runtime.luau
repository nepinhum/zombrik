local map = require("zombrik/map")
local combat = require("zombrik/combat")

local SPRITES = "zombrik/characters/"

-- Static zombies to test for development. They belong to the
-- map's scene, so a map change clears them.
-- TODO : There can be 2 types of zombies: AI & controllable (not sure about AI one)
map.on_change(function()
    for _, s in map.entities("zombie_spawn") do
        map.spawn({
            Position = { x = s.x, y = s.y },
            Rotation = { angle = math.atan2(-s.y, -s.x) },
            RenderDepth = { y_sort = true },
            Replicated = {},
        }):sprite({ { tex = SPRITES .. "zombie.png", nearest = true } })
    end
end)

events.on(function(e: EventHit)
    combat.hit(e)
end)

events.on(function(e: EventTick)
    combat.tick(e.tick)
end)

events.on(function(e: EventPlayerJoin)
    local p = map.spawn_point()
    local body = world.spawn{
        Position = { x = p.x, y = p.y },
        Rotation = { angle = 0 },
        CollisionBox = { width = 18, height = 18 },
        RenderDepth = { y_sort = true },
        Controller = { scheme = ControlScheme.TopDown },
        Dynamic = {},
        HitBox = {},
        -- Flashlight: a cone light follows the body's rotation, i.e. the aim.
        Light = { r = 1, g = 0.92, b = 0.75, radius = 420, intensity = 1.3, cone = 0.45, softness = 0.6, shadows = true },
    }
    e.player:control(body)
    -- The head sits behind canvas center; pivot on it so aiming turns in place.
    body:sprite({ { tex = SPRITES .. "survivor_pistol.png", nearest = true, pivot = { 0.36, 0.5 } } })
    body.Camera = { zoom = 2 }
    combat.arm(body)
    map.dress(body)
end)
