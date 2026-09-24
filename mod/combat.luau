-- Health, damage and respawning.
--
-- The engine owns the shot: it spawns the bullet on the fire button, enforces
-- the fire rate, tracks ammo and reloading and resolves the hit against a
-- HitBox with lag compensation. From EventHit on, it is ours.
local map = require("zombrik/map")

local M = {}

local TICKRATE = 60
local RESPAWN_SECONDS = 3
local DEFAULT_GUN = "pistol"
local DEFAULT_HEALTH = 100

-- Bodies waiting to come back: entity id -> the tick they revive on.
local waiting: { [number]: number } = {}
local now = 0

-- Gives the body a gun and the ammo that comes with it. Reequipping refills
-- because the prototype carries the full magazine.
function M.equip(body: Entity, gun: string)
    local def = GunProto:get(gun)
    if def == nil then
        log("combat: no gun named " .. gun)
        return
    end
    body:apply(def)
    body:projectile("zombrik/fx/bullet.png")
end

function M.arm(body: Entity)
    body.Health = { current = DEFAULT_HEALTH, max = DEFAULT_HEALTH }
    M.equip(body, DEFAULT_GUN)
end

-- Dying hides the body and stops its input and firing; the engine would revive
-- it on its own only if `revive` were set, so the timing stays here.
local function kill(body: Entity)
    body:add(Dying)
    waiting[body:id()] = now + RESPAWN_SECONDS * TICKRATE
end

function M.hurt(body: Entity, amount: number)
    local hp = body.Health
    if hp == nil or hp.current <= 0 then
        return
    end
    local left = math.max(hp.current - amount, 0)
    body.Health = { current = left, max = hp.max }
    if left == 0 then
        kill(body)
    end
end

-- `events.on` binds handlers to event types by the order their annotations were
-- parsed and a required module is parsed after the file that requires it.
-- Modules expose plain functions and runtime.luau does the subscribing.
function M.hit(e: EventHit)
    -- No Weapon means the shooter is gone or was never armed: no damage.
    if e.attacker:has(Weapon) then
        M.hurt(e.victim, e.attacker.Weapon.damage)
    end
end

function M.tick(tick: number)
    now = tick
    for id, at in waiting do
        if now >= at then
            waiting[id] = nil
            local body = world.entity(id)
            if body then
                local p = map.spawn_point()
                body:teleport(p.x, p.y)
                M.arm(body)
                body:remove(Dying)
            end
        end
    end
end

return M
