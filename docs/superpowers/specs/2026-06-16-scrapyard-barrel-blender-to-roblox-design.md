# Scrapyard Barrel — Blender → Roblox pipeline test

**Date:** 2026-06-16
**Goal:** Prove the Blender → Roblox import pipeline by producing one optimized scrapyard
barrel decoration and placing it in-game near the spawn for visual verification.

## Reference
User screenshot: a stubby metal drum — rust/dark-orange body, dark anthracite domed lid
with ~8 light-grey rivets in a ring, yellow hazard bands on the body rings.

## Decisions
- **3D method:** Procedural modeling via Blender Python script (clean, optimized, controllable).
- **Coloring:** Option B — a small assembly of a few MeshParts colored by zone
  (body / lid / rings / rivets). Robust, crisp colors, no dependency on texture upload.
- **Detail level:** Stylized-optimized decor prop (rich visual detail, controlled geometry).
- **Placement:** Near spawn / hub, in clear view for inspection.

## Build spec (Blender)
- Body: 24-segment cylinder, radius ~0.45 m, height ~0.6 m, slight mid bulge.
- Three raised rings (top / middle / bottom) — flattened tori inset into the body.
- Domed dark lid with 8 rivets (small cylinders) in a ring.
- Target geometry: ~1.5–2.5k tris total across the assembly, clean normals, UVs.
- Separate objects by color zone so each can export as its own MeshPart:
  - `Barrel_Body` (rust orange)
  - `Barrel_Lid` (anthracite)
  - `Barrel_Rings` (steel grey, two of them painted hazard yellow)
  - `Barrel_Rivets` (light grey)
  - `Barrel_HazardBands` (yellow)

## Export / Import
- Export each zone as `.obj` to `assets/barrel/` in the project.
- Import into Studio as MeshParts, weld/group into a `ScrapBarrel` Model.
- Scale to ~3.6 studs tall, place near spawn, anchored.
- Apply zone colors via Color3 + matte material (cartoon look, no glossy PBR).

## Success criteria
Barrel appears near spawn, recognizable vs reference (rust + hazard + riveted lid),
optimized geometry, crisp colors, no broken textures.
