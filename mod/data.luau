-- Runs once at load: declares components and prototypes.

export type Health = Replicated<{ current: number, max: number }>
