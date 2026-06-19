# EggShop Visual Polish — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. This is live Roblox-Studio MCP work: "tests" = read-back verification, deterministic Luau checks, and screenshots (captured in **Edit** mode).

**Goal:** Polish `Workspace.Environment.EggShop` to a premium look (surface depth, signage, corbels, egg display, NPC visibility) without changing its identity or breaking shop logic.

**Architecture:** The shop is static baked geometry in `build.rbxlx`. All edits are applied to the live Edit DataModel via **one idempotent Luau script** run through `execute_luau`. Idempotency = every added decor part gets attribute `Polish=true`; the script first destroys all descendants with `Polish=true`, then rebuilds — safe to re-run. 3 "hero" accents come from Blender meshes (with native fallbacks). User saves with Ctrl+S afterward.

**Tech Stack:** Roblox Studio MCP (`execute_luau`, `inspect_instance`, `screen_capture`, `insert_asset`), Blender MCP (`execute_blender_code`, upload addon), Luau.

## Global Constraints

- **Faces +X**, wide along **Z (±15)**, up = **Y**. Shop pivot (-379, 0.5, 0).
- **CounterTop top must stay Y≈5.35** (eggs are placed by script at `Y=5.4+h/2`, i.e. on the counter). Do not move Egg X/Z.
- **Never rename/delete** bound nodes: `Pedestal1..6` → `Egg` → `Visual`/`Info`(`EggName`,`EggPrice`,`EggOdds`)/`BuyPrompt`; `Countdown`→`CountdownGui`→`Time`.
- **Never parent decor inside `Egg` or `Visual`** (Visual is replaced at runtime). Decor goes on `Pedestal*` or the shop model.
- **Anti z-fighting**: offset every trim/molding/cap **≥0.04 studs**; no coplanar same-facing faces. Run detector at the end.
- **All added decor**: `Anchored=true`, `CanCollide=false`, `CanQuery=false`, attribute `Polish=true`, neutral names (`Holder`,`GemBtn`,`Corbel`,`Batten`,`RidgeCap`,`Molding`,`SignRig`,`Emblem`,`Cartouche`,`NpcRiser`).
- **Palette (Color3.fromRGB)**: orange `196,108,42`; orange-dark `150,78,28`; brun `120,72,36` / `100,58,28`; doré `240,196,70`; doré-dark `196,150,40`; rouge `225,70,64`; cream `248,244,238`; bois sombre `70,46,30`; gem rouge `200,40,40`.
- Edits live in the DataModel → **pending Ctrl+S** by the user.

---

### Task 1: Hero accents — Blender meshes (with native fallback)

**Files:** Blender scene (procedural) → uploaded MODEL assets; or native fallback in the polish script.

**Interfaces:**
- Produces: a table `HERO = { emblem=<assetId or "fallback">, corbel=<assetId or "fallback">, cartouche=<assetId or "fallback"> }` used by Tasks 4 & 5. Asset IDs load via `InsertService:LoadAsset(id)`.

- [ ] **Step 1: Probe pipeline availability**
  - `get_scene_info` (Blender) to confirm Blender MCP is live.
  - Confirm the "Upload to Roblox" addon / Open Cloud key is configured (try a minimal upload, or check addon presence). If unavailable, mark all three as `"fallback"` and skip to Task 2 — fallbacks are good enough and must not block the polish.

- [ ] **Step 2: Build 3 low-poly procedural meshes in Blender** (one object per color zone, smooth-shaded, < ~400 tris each):
  - **Egg emblem**: a cartoon egg (UV-sphere scaled Y, slight taper), optional shallow crack groove. Cream body.
  - **Corbel**: a quarter-round/ogee bracket (curved profile extruded) — the curve a wedge can't do. Dark wood.
  - **Cartouche**: a flat plaque frame, rounded corners + slight outer bevel, hollow center (the sign face shows through). Dark wood.

- [ ] **Step 3: Upload via addon → record asset IDs** into `HERO`. Verify each returns a valid numeric asset id.

- [ ] **Step 4: Verify** — insert each asset once into a temp folder via `insert_asset`/`LoadAsset`, screenshot, confirm it loads and looks right; delete temp. If any fails → set that entry to `"fallback"`.

  **Fallbacks (native, used when `HERO.x=="fallback"`):**
  - emblem → clone existing egg mesh from `ReplicatedStorage.Assets.EggMeshes` (game's own egg), cream-tinted.
  - corbel → `WedgePart` (triangular bracket), dark wood.
  - cartouche → frame from 4 thin parts + cylinder corner caps (fakes rounded corners), dark wood.

---

### Task 2: Surface depth & materials (S1 — walls, roof, posts/beams)

**Files:** polish script (Edit DM).

**Interfaces:**
- Consumes: nothing. Produces: `Polish`-tagged battens/ridge cap; recolored base parts.

- [ ] **Step 1: Establish idempotency + helpers** at script top:

```lua
local shop = workspace.Environment.EggShop
-- sweep previous polish
for _,d in ipairs(shop:GetDescendants()) do if d:GetAttribute("Polish") then d:Destroy() end end
local function mk(name, size, cf, color, mat, parent)
  local p = Instance.new("Part")
  p.Name=name; p.Size=size; p.CFrame=cf; p.Color=color; p.Material=mat or Enum.Material.SmoothPlastic
  p.Anchored=true; p.CanCollide=false; p.CanQuery=false; p:SetAttribute("Polish", true)
  p.Parent=parent or shop; return p
end
local function tex(part, faces, id, sx, sy, color, alpha)
  for _,f in ipairs(faces) do
    local t=Instance.new("Texture"); t.Face=f; t.Texture=id; t.StudsPerTileU=sx; t.StudsPerTileV=sy
    if color then t.Color3=color end; t.Transparency=alpha or 0.6; t:SetAttribute("Polish",true); t.Parent=part
  end
end
```

- [ ] **Step 2: Walls** — add a tiling `Texture` (use a built-in studs/woodgrain asset, low alpha, orange-tinted darker) on BackWall +X face and add 4–6 thin vertical **Batten** parts (size ~0.3 × 14 × 0.6) across BackWall, offset 0.05 in +X, color orange-dark. Same light treatment on the canopy underside if visible.

- [ ] **Step 3: Roof** — set `Canopy.Material=WoodPlanks`; add **RidgeCap** part along the top ridge (full Z length, ~1.2 × 0.8 × 36, color orange-dark, offset above canopy +0.05) and a thin front overhang lip.

- [ ] **Step 4: Posts/beams** — set posts & beams `Material=WoodPlanks`; add a thin darker band part near the base of each PostFront (faux AO), offset 0.05.

- [ ] **Step 5: Verify** — `screen_capture` front + angle; confirm walls/roof read with depth and palette unchanged. Re-read a couple parts to confirm material/texture applied (MCP no-op guard).

---

### Task 3: Counter polish (S1 — molding, grooves, gem buttons)

**Files:** polish script.

- [ ] **Step 1: Rim molding** — thin **Molding** frame around CounterTop outer edge (4 bars hugging the rim, top at ~Y5.4, color doré-dark, offset 0.05 outward). Must stay at the rim — **not** over the center where eggs sit (eggs at X=-371, center).

- [ ] **Step 2: Base grooves** — 5–7 thin vertical recessed **Groove** strips (dark, ~0.15 × 3.6 × 0.2) on CounterBase front face (X≈-368.5, +0.04), evenly spaced in Z.

- [ ] **Step 3: Gem buttons** — along CounterBase front, between grooves, add **GemBtn**: a small Metal mount (0.5³) + a `Shape=Ball` Neon-soft red half-gem (~0.7) proud of the face (X≈-368.3), at Y≈2.4, ~6 across Z. Matches reference.

- [ ] **Step 4: Verify** — screenshot front; confirm gems/grooves read, counter top unchanged (re-read `CounterTop` size/pos = 6.4,0.9,29 @ -371,4.9,0).

---

### Task 4: Signage rework (S2 — order, layout, cartouches, emblem, text)

**Files:** polish script; edits to `Countdown`/`CountdownGui`, `EggsSign`/`EggsSignGui`, frames.

**Interfaces:** Consumes `HERO.cartouche`, `HERO.emblem`.

- [ ] **Step 1: Fix countdown label order** — in `CountdownGui` (UIListLayout), set `LayoutOrder` so render is Title `Marchand d'œufs` → Sub `Réapprovisionnement dans` → `Time` `MM:SS`. Do **not** rename labels. Confirm `Time` still exists (controller writes it).

- [ ] **Step 2: Reposition signs (réf layout: Marchand gauche / Œufs droite)** — set positions so both hang at the **same Y** on the façade band just under BeamFront, symmetric about Z=0, flush front (X≈-367.6), not overlapping interior. Marchand sign at Z<0 side (customer-left = +Z? confirm handedness from screenshot: in front view customer-left = +Z). Place Œufs opposite. Keep them clear of the egg row (eggs Y≈5.9 region; signs up at Y≈16–18).
  - Add a short **SignRig** hanger (2 thin bars/chains) from BeamFront to each sign.

- [ ] **Step 3: Cartouche frames** — destroy/hide flat `EggsSignFrame`/`CountdownFrame` (or set transparent) and place `HERO.cartouche` (or fallback frame) sized behind each sign face, dark wood, offset behind the GUI face (anti z-fight). Tag `Polish`.

- [ ] **Step 4: Egg emblem** — place `HERO.emblem` (or fallback egg mesh) centered on the top edge of the Œufs sign, cream, ~2–2.5 studs, anchored, `CanQuery=false`.

- [ ] **Step 5: Text style** — ensure sign `TextLabel`s use a bold display font (LuckiestGuy/GothamBlack), white, `TextStrokeTransparency≈0.3`, `TextScaled`, add `UIPadding`. Don't change `.Text` of dynamic labels.

- [ ] **Step 6: Verify** — screenshot front: timer order correct, Marchand-left/Œufs-right, equal height, centered, cartouches + emblem read, text crisp. Confirm names: `Countdown.CountdownGui.Time`, `EggsSign.EggsSignGui.L` still present.

---

### Task 5: Corbels (S3 — Blender hero #2)

**Files:** polish script. Consumes `HERO.corbel`.

- [ ] **Step 1: Place corbels** at the 2 PostFront→BeamFront joints (both ±Z ends), mirrored, snug under the beam against the post (X≈-369). Use `HERO.corbel` (or `WedgePart` fallback), dark wood, `Polish`-tagged, `CanQuery=false`. Optional: small corbels under each sign rig.

- [ ] **Step 2: Verify** — angle screenshot; corbels seated at joints, mirrored, no z-fight with post/beam (offset ≥0.04).

---

### Task 6: Eggs & holders + placement integrity (S4)

**Files:** polish script; edit `Pedestal6.Egg`.

- [ ] **Step 1: Fix Pedestal6 egg Y** — set `Pedestal6.Egg` Y to 5.9 (match Pedestal1..5). Keep X/Z.

- [ ] **Step 2: Holders** — under each `Pedestal*`, add `Holder`: a dark disc/puck (`Shape=Cylinder` or thin box, ~2.2 dia × 0.3 h) top at Y≈5.4 (on counter), centered at the pedestal X/Z, + a thin colored rim. `CanQuery=false`, `CanCollide=false`, parented to the `Pedestal*` part. Must not rise above 5.45 (egg base) and must not block the prompt.

- [ ] **Step 3: Deterministic placement check** (execute_luau, return text):

```lua
local s = workspace.Environment.EggShop
local out = {}
local ct = s.CounterTop; table.insert(out, ("CounterTopTop=%.3f"):format(ct.Position.Y+ct.Size.Y/2))
for i=1,6 do local e=s["Pedestal"..i].Egg
  table.insert(out, ("Egg%d y=%.3f x=%.3f z=%.3f"):format(i,e.Position.Y,e.Position.X,e.Position.Z)) end
return table.concat(out,"\n")
```
  Expected: CounterTopTop ≈ 5.35; all 6 Egg y equal (≈5.9), x = -371, z = {-12.5..12.5} step 5.

- [ ] **Step 4: Verify** — screenshot front: 6 eggs centered, on holders, none floating/sinking, prices aligned.

---

### Task 7: NPC merchant (S5)

**Files:** polish script; reposition `NPC.shopkeeper`, `NPC.NamePlate`.

- [ ] **Step 1: Raise/advance NPC** — `PivotTo` the `shopkeeper` model so torso/head clear the counter top (head visible above Y≈5.35), slightly forward toward the counter. Add a hidden **NpcRiser** platform under its feet (anchored, `CanQuery=false`). Keep R6 parts/clothing/hat.

- [ ] **Step 2: NamePlate** — raise `NamePlate.StudsOffset` (or part pos) so the label floats above the head, not over the eggs.

- [ ] **Step 3: Verify** — screenshot front: merchant visible (head+torso), nameplate above head, not clipping eggs.

---

### Task 8: Final verification & optimization (S6)

- [ ] **Step 1: CanQuery sweep** — confirm every `Polish`-tagged part has `CanQuery=false`, `Anchored=true`. Re-read counts.

- [ ] **Step 2: Coplanar / z-fighting detector** (execute_luau): for all BaseParts in the shop, flag pairs whose faces are coplanar (same plane within 0.02) AND same outward normal AND overlapping in the other two axes. Return the list; fix any flagged pair by nudging the added part ≥0.04. Re-run until clean.

- [ ] **Step 3: Bindings name check** (execute_luau): assert presence of `Pedestal1..6/Egg/Visual/Info(EggName,EggPrice)/BuyPrompt`, `Countdown/CountdownGui/Time`, `EggsSign/EggsSignGui`. Return PASS/FAIL list. Expected: all PASS.

- [ ] **Step 4: Final screenshots** front + angle (Edit). Compare against Task-0 baseline; confirm acceptance criteria 1–8 in the spec.

- [ ] **Step 5: Report** — summarize changes, list any fallbacks used, remind the user to **Ctrl+S** in Studio to persist into `build.rbxlx`. Offer to commit the spec + plan docs.

---

## Self-Review

- **Spec coverage:** S1→T2/T3, S2→T4, S3→T5, S4→T6, S5→T7, S6→T1(meshes)/T8. Acceptance criteria 1–8 covered by T8 verify + per-task screenshots. ✓
- **Placeholders:** none — concrete sizes/positions/colors given; code shown for idempotency, placement check, and detectors.
- **Type consistency:** `HERO` table keys (`emblem`/`corbel`/`cartouche`) consistent across T1/T4/T5. Names (`Polish`, `Holder`, `GemBtn`, `Corbel`, etc.) consistent with Global Constraints.
