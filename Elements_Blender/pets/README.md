# Pets — Blender models (10 arcade-industrial mascots)

Procedural Blender build of the 10 UFO-Catchers pets. Built **one object per color zone** so each
zone uploads as its own Roblox `MeshPart` (the validated Blender→Roblox pipeline, same as `../claw_rig`).

## Files
- `pets_build.py` — the build script. Helpers (`sphere/box/cyl/cone/torus/place/rot/scale/squash`,
  `C()`, `assemble()`) + one `@builder("<id>")` per pet. Run inside Blender:
  ```python
  exec(open(r"<path>/pets_build.py").read())
  build_all()        # builds all 10 in named collections, laid out in a grid
  build_one("holo_fox")
  save_blend(r"<path>/pets.blend")
  ```
- `pets.blend` — saved scene: 10 collections, one per pet id, each containing its color-zone meshes
  named `<id>_z0, <id>_z1, …`. Front faces +X, up is +Z (Roblox Y).
- `pets_contact.png` — preview contact sheet (colors are richer in-engine with real materials/neon).
- `asset_ids.json` — Roblox MODEL asset ids, **null until uploaded**.

## Roster (ids == `ReplicatedStorage.Shared.Config.Pets[*].model`)
`bunny_plush, bolt_bot, foam_cube, windup_duck, neon_kitten, magnet_drone, golden_teddy, mini_clawbot, holo_fox, ufo_mascot`

## Import later (when the Roblox upload plugin is connected)
1. Open `pets.blend` in Blender with the official **"Upload to Roblox"** addon, logged in (creator lylou38000).
2. Per pet, upload its color-zone objects as a **MODEL** asset (or each mesh, then group). Write the
   returned id into `asset_ids.json` under that pet's name.
3. In Studio, `InsertService:LoadAsset(id)`, assemble/scale, and place the resulting Model under
   `ReplicatedStorage.Assets.PetMeshes.<id>` (replacing the procedural placeholder of the same name).
   Roblox recenters MeshParts on their bbox, so reposition zones to reassemble the creature.
4. `PetController` already **prefers** `Assets.PetMeshes[<id>]` over the procedural fallback — no code
   change needed once the hero models are in place.

Notes: keep each pet ~3 studs tall for consistency; `assemble()` already seats feet to z=0 and centers
X/Y. Emissive zones (neon/glow/glass) are tagged via `mats` in each builder — set the Roblox
`MeshPart` material/Neon + color accordingly at import.
