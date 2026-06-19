# Scrap Kit — Creator Store selection (Task 1 result)

**Date:** 2026-06-19
**Method:** searched Creator Store (free, scope=creator_store) across themes; staged 12 candidates next to a 7×7 pad-sized scale reference at y=400; programmatically measured size + part count + **texture/SurfaceAppearance status** (the recolour gate); screen-captured and judged visually.

## Verdict

The free Store has **few clean, recolourable, stylised single-mesh industrial pieces**. Most candidates are one of: huge textured "scene" dumps (100s of parts), high-part-count primitive assemblies, or PBR-textured/realistic (which breaks `BasePart.Color` recolour). Good *feature* meshes exist (barrels, a gear, low-poly crystals); clean *structural* meshes (pipe/plate/beam/canister/container) essentially do not.

→ **Final kit = Store feature meshes (recolourable) + procedural structural pieces generated in `ScrapHeapBuilder`** (the pattern `ClawModel` already uses: primitive parts + cloned feature meshes). Blender is connected, but simple box/cylinder structural shapes don't benefit from sculpting and the Open-Cloud upload adds risk; reserving authored effort. (Blender-sculpted hero/structural meshes remain an optional future upgrade, consistent with the project's deferred "Blender hero meshes" elsewhere.)

## KEPT — Store feature meshes (recolourable, passed rubric)

| kit role | asset name | assetId | parts | size (studs) | textured | notes |
|---|---|---|---|---|---|---|
| `Barrel` (Base/Mid) | Rusty Metal Drum | **90663282345344** | 1 MeshPart | 4.2×4.0×4.2 | no | cleanest single-mesh barrel; recolour ✓ |
| `Barrel2` (variant) | Metal Barrel/Drum | **9628901253** | 5 parts | 4.9×3.9×4.9 | no | ribbed barrel; recolour ✓ (optional 2nd variant) |
| `Gear` (Mid) | Metal Gear (Cog) | **712422213** | 1 (Union) | 16.9×1×16.9 | no | flat cog; scale down; recolour ✓ |
| `Hero` (crown) | Low Poly Crystal Shard Gem | **112174159152905** | 2 MeshParts | 6.1×8.3×6.2 | no | faceted crystal cluster; recolour per-rarity glow ✓✓ |
| `Hero`/feature (alt) | Low Poly Ore Pack | 130594866462739 | 44 meshes | pack | no | gem-studded rocks; clean but reads "mining" not "scrap" — held in reserve |

## REJECTED (with reason)

| asset | assetId | reason |
|---|---|---|
| Industrial Clutter Junk Scrap Pile | 132797525489587 | 235 parts, **textured**, 170 studs — whole factory scene; too heavy/large/realistic |
| Scrap Metal Junk Pile (B) / Parts (C) | 75660418733089 / 130910668584076 | identical pre-composed crushed-barrel+pallet mini-scenes (24 parts), grungy/realistic, not composable |
| Industrial Gear Cog (giant) | 100863587474349 | 238 parts, 66 studs — giant steampunk scaffold |
| Pipe Kit | 73864105432070 | **textured** (camo/realistic) → `Color` recolour inoperative |
| Suez Dumpster Skip | 129386537356298 | 270 parts, multi-bin colourful set — too heavy & simplistic for a single container |
| Metal Block mesh | 9553036761 | **textured**, 295×210×295 studs — unusable |
| tanks / engines | (various) | military tanks / realistic car engines — wrong subject, realistic |

## Structural pieces → procedural (generated in `ScrapHeapBuilder`)

Clean primitives, recoloured per rarity, kept to 1 part each where possible:
- `Container` skip: low open-top steel box (floor + back + 2 sides + low front) — ~5 parts, the only multi-part role.
- `Mid`/`Base` structural: pipe (Cylinder), bent panel/plate (Block), I-beam offcut (Block), canister (Cylinder).
- `Small` accents: bolt/cog nub (small Cylinder/Block), crumpled sheet (Wedge).

These read clearly as industrial machine scrap, recolour cleanly via `Color`, and keep the per-heap instance budget at ≤ 18.
