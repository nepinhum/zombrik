-- Runs once at load: declares components and weapons.

-- Clients draw health bars, it replicates; damage stays server side.
export type Health = Replicated<{ current: number, max: number }>

-- What the body is holding. The engine fires the shot and tracks ammo; the mod
-- only needs to know what a hit from this body is worth.
export type Weapon = Component<{ damage: number }>

export type GunProto = Prototype<{ ProjectileWeapon: ProjectileWeapon, Ammo: Ammo, Weapon: Weapon }>

-- cooldown is in ticks (60/s), speed and muzzle in world units, a tile is 32.
GunProto:define("pistol", {
    ProjectileWeapon = { cooldown = 16, speed = 620, muzzle = 16, life = 1.4 },
    Ammo = { mag = 12, reserve = 72, mag_size = 12, reload_time = 1.4 },
    Weapon = { damage = 26 },
})
