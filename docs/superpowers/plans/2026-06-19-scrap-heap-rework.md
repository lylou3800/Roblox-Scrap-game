# Scrap-Heap Rework ("Contained Feed Mound") Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the per-bay procedural debris pile with a richer, mesh-based "Contained Feed Mound" that is themed by the placed machine's rarity and built dynamically in `refreshSlot`.

**Architecture:** A new `ReplicatedStorage.Shared.ScrapHeapBuilder` module (mirror of `ClawModel`) clones a curated `ReplicatedStorage.Assets.ScrapKit` of untextured MeshParts, recolours/finishes them per `ClawDesign.RARITIES`, and composes them as a contained mound. `refreshSlot` builds/clears `Heap_<slotId>` alongside the machine; `buildPreviewPlot` bakes a neutral variant; the old `buildBay` generator and the already-baked `DebrisPile_*`/`DebrisBit_*` instances are removed by re-running the preview baker.

**Tech Stack:** Roblox Studio (Luau), Roblox Studio MCP (`script_read`/`multi_edit`/`execute_luau`/`insert_asset`/`search_asset`/`screen_capture`/`inspect_instance`/`search_game_tree`/`get_console_output`/`start_stop_play`), Blender MCP (gap meshes), Creator Store, git (40 MB binary `build.rbxlx`).

**Spec:** `docs/superpowers/specs/2026-06-19-scrap-heap-rework-design.md`

## Global Constraints

- **Studio target:** all Studio work targets **`build.rbxlx` in Edit mode** — NOT `recovery.rbxl`. Confirm via `list_roblox_studios` + `set_active_studio` before every Studio mutation. NEVER save `recovery.rbxl` over `build.rbxlx`.
- **Layout reality:** 16 bays/plot (`s1..s8` floor 0 + `f1..f8` floor 1). `MAX_PLOTS = 8`.
- **Module:** `ReplicatedStorage.Shared.ScrapHeapBuilder`; requires ONLY `ReplicatedStorage.Shared.Config.ClawDesign` (acyclic).
- **Kit:** `ReplicatedStorage.Assets.ScrapKit`; all debris are **MeshParts with NO SurfaceAppearance / NO TextureID** (recolour via `BasePart.Color` only).
- **Heap instances:** named `Heap_<slotId>`, `Anchored=true`, `CanCollide=false`, attribute `Rarity` = rarity id or `"neutral"`, attribute `SlotId`.
- **Budget:** ≤ 18 instances/heap (hard cap 20): `Container 1 + Base 3 + Mid 4 + Small 3 + Hero 1` = 12, + ≤ 4 FX/accent + ≤ 2 Rubble. Neutral ≈ 8 (no FX).
- **FX caps:** Neon accent parts ≤ 2/heap, only `fxTier ≥ 2`. Particles only `fxTier ≥ 3`, `Rate ≤ 6`, `MaxParticles ≤ 15`, ≤ 1 emitter/heap.
- **Seed:** `heapSeed(slotId) = Σ byte(slotId,i)*i` (deterministic; identical runtime + preview).
- **heapCF (origin space, NOT pad-yaw):** `outer=(slotDef.offset.X<0) and -1 or 1`; `innerX=-outer`; `heapCF = origin * CFrame.new(slotDef.offset + Vector3.new(innerX*D, baseY, frontZ))`, `D≈10–12`, `frontZ≈0`, `baseY` so the bin floor rests on the ZoneFloor/ZoneInset. Validate BOTH rows (`offset.X>0` and `<0`).
- **Height ≤ 4.5 studs** (keep the machine body the hero).
- **Anti-float pass is BLOCKING** (hard fail, not log). Coplanar faces offset ≥ 0.04.
- **Rollback:** `build.rbxlx` is binary (`.gitattributes: *.rbxlx -text -diff`) → whole-file revert only. Commit/snapshot before the preview re-bake.
- **MCP gotchas:** `multi_edit` can silently no-op → always `script_read` back to confirm. `execute_luau` Server VM is isolated → test ReplicatedStorage modules directly, but test server services (`refreshSlot`) live via Play + a temp Script or game inspection. Play compiles a stale snapshot right after an edit → verify edits before Play.

---

### Task 0: Safe working state + rollback snapshot

**Files:**
- Modify: none (Studio + git state only)

**Interfaces:**
- Produces: a confirmed active `build.rbxlx` Edit session and a git rollback point.

- [ ] **Step 1: Confirm the correct Studio is open**

Run MCP `list_roblox_studios`. Expected: an entry whose `name` is `build.rbxlx` (or the real game), NOT only `recovery.rbxl`.
If only `recovery.rbxl` appears, STOP and ask the user to open `build.rbxlx` in Edit mode (and not save `recovery.rbxl` over it).

- [ ] **Step 2: Make build.rbxlx the active instance**

Run MCP `set_active_studio` with the `build.rbxlx` instance id. Then `get_studio_state`.
Expected: `Current Studio Mode: Edit` (if it says `Play`, ask the user to Stop, or call `start_stop_play` to stop).

- [ ] **Step 3: Confirm it is the full game (sanity)**

Run MCP `script_grep` with query `refreshSlot`. Expected: matches inside the plot-builder script body (not just a PlotLayout comment). This proves the active place is the complete `build.rbxlx`, not the partial recovery file.

- [ ] **Step 4: Rollback snapshot (git)**

Ask the user to confirm `build.rbxlx` is saved (Ctrl+S) at its current state, then:

```bash
git add build.rbxlx && git commit -m "chore(scrap-heap): snapshot build.rbxlx before scrap-heap rework"
```
Expected: a commit containing `build.rbxlx`. This is the revert point.

---

### Task 1: Asset research & selection (Creator Store) — Spec §4 Phases 1–2

**Files:**
- Create: `docs/superpowers/specs/2026-06-19-scrap-kit-selection.md` (the documented kept-set)
- Modify: Studio `Workspace` (a temporary `_ScrapStaging` folder, deleted at task end)

**Interfaces:**
- Produces: `docs/superpowers/specs/2026-06-19-scrap-kit-selection.md` listing, per kit role (`Container`, `Base`, `Mid`, `Small`, `Hero`), the chosen Creator Store asset IDs (or "GAP → Blender") with scores; this drives Tasks 2–3.

- [ ] **Step 1: Search the store across all themes**

Run MCP `search_asset` once per theme keyword and collect candidates: `scrap metal`, `industrial debris`, `broken pipe`, `gear cog`, `oil barrel drum`, `metal canister`, `I-beam girder`, `dumpster skip bin`, `wooden pallet`, `bolt nut`, `spring coil`, `crumpled metal sheet`, `engine block`.
Record for each candidate: assetId, name, creator. Prefer stylised low/mid-poly, cohesive sets, clean silhouettes.

- [ ] **Step 2: Stage the top candidates next to a real machine**

Create a staging folder and insert the top ~3 candidates per role:

```lua
-- execute_luau (Edit)
local Workspace = game:GetService("Workspace")
local f = Workspace:FindFirstChild("_ScrapStaging") or Instance.new("Folder")
f.Name = "_ScrapStaging"; f.Parent = Workspace
return f:GetFullName()
```
Then `insert_asset` each candidate assetId into `Workspace._ScrapStaging`, lay them in a row near an existing bay's pad for scale reference.

- [ ] **Step 3: Capture and score**

Run MCP `screen_capture` framing the staged candidates beside a machine. Score EACH against the rubric (Spec §4 Phase 2): style fit · **recolourable = untextured** · proportions · silhouette legible at distance · enriches not confuses · premium>cheap · scale fit · marries with machine · poly cost. Reject any that fail style or that ship a `SurfaceAppearance`/`TextureID` (verify with `inspect_instance` — `TextureID` must be empty and no `SurfaceAppearance` child).

- [ ] **Step 4: Identify gaps**

For any role with no acceptable untextured Store mesh, mark it `GAP → Blender` (the `Container` and the `Hero` set are the most likely gaps).

- [ ] **Step 5: Write the kept-set doc**

Write `docs/superpowers/specs/2026-06-19-scrap-kit-selection.md`: a table of `role → {assetId | GAP} → score → notes`. This is the contract Task 2/3 consume.

- [ ] **Step 6: Clean up staging**

```lua
-- execute_luau (Edit)
local s = game.Workspace:FindFirstChild("_ScrapStaging")
if s then s:Destroy() end
return "cleared"
```

- [ ] **Step 7: Commit the selection doc**

```bash
git add docs/superpowers/specs/2026-06-19-scrap-kit-selection.md
git commit -m "docs(scrap-heap): documented Creator Store kit selection (roles + asset IDs)"
```

---

### Task 2: Build `ReplicatedStorage.Assets.ScrapKit` from Store meshes — Spec §3.2

**Files:**
- Modify: Studio `ReplicatedStorage.Assets` (new `ScrapKit` folder of MeshParts)

**Interfaces:**
- Consumes: kept-set doc from Task 1.
- Produces: `ReplicatedStorage.Assets.ScrapKit` folder containing untextured MeshParts named EXACTLY `Container_1[..n]`, `Base_1..Base_k`, `Mid_1..Mid_k`, `Small_1..Small_k` (Hero added in Task 3). Each MeshPart: `Anchored=true`, `CanCollide=false`, `TextureID=""`, no `SurfaceAppearance` child. Consumed by `ScrapHeapBuilder` via `FindFirstChild`-by-role (Task 4).

- [ ] **Step 1: Create the kit folder**

```lua
-- execute_luau (Edit)
local RS = game:GetService("ReplicatedStorage")
local assets = RS.Assets
local kit = assets:FindFirstChild("ScrapKit") or Instance.new("Folder")
kit.Name = "ScrapKit"; kit.Parent = assets
return kit:GetFullName()
```
Expected: `ReplicatedStorage.Assets.ScrapKit`.

- [ ] **Step 2: Insert each selected Store mesh into the kit and rename by role**

For each kept assetId, `insert_asset` into `ReplicatedStorage.Assets.ScrapKit`, then rename to its role name (`Base_1`, `Mid_1`, …). If an insert yields a Model, extract the single MeshPart and discard the wrapper.

- [ ] **Step 3: Normalise each mesh (untextured, single MeshPart, flags)**

```lua
-- execute_luau (Edit)
local kit = game.ReplicatedStorage.Assets.ScrapKit
local bad = {}
for _, p in ipairs(kit:GetDescendants()) do
    if p:IsA("MeshPart") then
        p.Anchored = true; p.CanCollide = false
        p.TextureID = ""
        local sa = p:FindFirstChildWhichIsA("SurfaceAppearance")
        if sa then table.insert(bad, p.Name); end -- textured -> must be replaced
    end
end
return #bad == 0 and "all untextured OK" or ("TEXTURED (reject): " .. table.concat(bad, ", "))
```
Expected: `all untextured OK`. Any listed name must be swapped for an untextured alternative (back to Task 1) — recolour-by-Color will not work otherwise.

- [ ] **Step 4: Verify recolour works (the core assumption)**

```lua
-- execute_luau (Edit) — clone one base mesh, set Color, confirm it took
local kit = game.ReplicatedStorage.Assets.ScrapKit
local m = kit:FindFirstChild("Base_1"):Clone()
m.Color = Color3.fromRGB(255, 0, 0)
m.Parent = workspace
local ok = (m.Color == Color3.fromRGB(255, 0, 0))
m:Destroy()
return ok and "recolour OK" or "recolour FAILED"
```
Expected: `recolour OK`.

- [ ] **Step 5: Confirm the role inventory is complete (pools non-empty)**

```lua
-- execute_luau (Edit)
local kit = game.ReplicatedStorage.Assets.ScrapKit
local counts = {Container=0, Base=0, Mid=0, Small=0}
for _, p in ipairs(kit:GetChildren()) do
    local role = p.Name:match("^(%a+)_")
    if role and counts[role] ~= nil then counts[role] += 1 end
end
return ("Container=%d Base=%d Mid=%d Small=%d"):format(counts.Container, counts.Base, counts.Mid, counts.Small)
```
Expected: `Container>=1 Base>=4 Mid>=5 Small>=4` (per Spec §3.2 variant pools). If any pool is short, add more variants (Store or Blender) before proceeding.

- [ ] **Step 6: Save + commit**

Ask the user to Ctrl+S, then:
```bash
git add build.rbxlx && git commit -m "feat(scrap-heap): add ScrapKit Store meshes (Container/Base/Mid/Small, untextured)"
```

---

### Task 3: Author gap meshes in Blender (Container + Hero set) — Spec §4 Phase 3

**Files:**
- Modify: Studio `ReplicatedStorage.Assets.ScrapKit` (add `Container_*` if gap, and `Hero_paint`, `Hero_metal`, `Hero_energized`, `Hero_crystal`, `Hero_warp`, `Hero_prism`)

**Interfaces:**
- Consumes: gaps marked in Task 1.
- Produces: kit MeshParts `Container_1` (low open-top steel skip) and one `Hero_<band>` per material band in {`paint`,`metal`,`energized`,`crystal`,`warp`,`prism`}, untextured, in `ScrapKit`. Consumed by `ScrapHeapBuilder` (Hero chosen by `materialBand`).

- [ ] **Step 1: Model the skip container in Blender**

Via Blender MCP `execute_blender_code`: a low open-top rectangular steel skip (~9 × 3.5 × 9 studs in Roblox scale), front wall ~40% height so the mound shows, separate objects per colour zone (body / rim), **no texture** (flat materials). Frame `get_viewport_screenshot` to confirm.

- [ ] **Step 2: Model the 6 hero crown pieces**

Via Blender: `paint`=scrap nugget (rounded chunk), `metal`=polished ingot, `energized`=cell with seam, `crystal`=faceted crystal, `warp`=twisted shard, `prism`=multi-facet prism. Each ~1.5–2.5 studs, single object, untextured. These are recoloured per-tier at runtime; geometry only here.

- [ ] **Step 3: Upload + insert into the kit**

Use the proven pipeline (Open Cloud "Upload to Roblox" → MODEL asset), then `insert_asset` each into `ReplicatedStorage.Assets.ScrapKit`, rename to `Container_1` / `Hero_<band>`, run Task 2 Step 3 normalisation on them (untextured, Anchored, CanCollide=false).

- [ ] **Step 4: Verify hero coverage**

```lua
-- execute_luau (Edit)
local kit = game.ReplicatedStorage.Assets.ScrapKit
local need = {"paint","metal","energized","crystal","warp","prism"}
local missing = {}
for _, b in ipairs(need) do
    if not kit:FindFirstChild("Hero_" .. b) then table.insert(missing, b) end
end
local hasContainer = kit:FindFirstChild("Container_1") ~= nil
return ("Container=%s; missingHero=[%s]"):format(tostring(hasContainer), table.concat(missing, ","))
```
Expected: `Container=true; missingHero=[]`.

- [ ] **Step 5: Save + commit**

Ask the user to Ctrl+S, then:
```bash
git add build.rbxlx && git commit -m "feat(scrap-heap): add Blender Container + Hero_<band> kit meshes"
```

---

### Task 4: `ScrapHeapBuilder` module (core builder, tested in isolation) — Spec §3.1, §5, §6

**Files:**
- Create: Studio `ReplicatedStorage.Shared.ScrapHeapBuilder` (ModuleScript)

**Interfaces:**
- Consumes: `ReplicatedStorage.Assets.ScrapKit` (Tasks 2–3); `ReplicatedStorage.Shared.Config.ClawDesign`.
- Produces:
  - `ScrapHeapBuilder.build(ufoDef: {rarity: string}?, seed: number, baseCF: CFrame): Model`
  - `ScrapHeapBuilder.heapSeed(slotId: string): number`
  - `ScrapHeapBuilder.heapCF(origin: CFrame, slotDef: {offset: Vector3}): CFrame`
  Returned Model: `Anchored` children, attribute `Rarity`, named by caller. Consumed by Task 5/6.

- [ ] **Step 1: Write the module**

Create ModuleScript `ReplicatedStorage.Shared.ScrapHeapBuilder` (via `multi_edit` on a new instance, or create instance then set Source). Full source:

```lua
--!strict
-- ScrapHeapBuilder.luau
-- Builds a "Contained Feed Mound" scrap heap from ReplicatedStorage.Assets.ScrapKit,
-- recoloured/finished by the placed machine's rarity (ClawDesign.RARITIES).
-- Mirror of ClawModel: requires ONLY Config.ClawDesign (acyclic). Pure builder, no runtime script.

local ReplicatedStorage = game:GetService("ReplicatedStorage")
local ClawDesign = require(ReplicatedStorage.Shared.Config.ClawDesign)
local KIT = ReplicatedStorage.Assets.ScrapKit

local ScrapHeapBuilder = {}

local D_DEFAULT = 11      -- inner offset magnitude (tune in Studio, 10..12)
local FRONT_Z = 0
local BASE_Y = 0.4        -- bin floor rests on ZoneInset top (tune ±0.3 in Studio)
local EMBED = 0.3         -- how far a piece sinks into its support, for a settled look
local HEIGHT_CAP = 4.5

-- neutral "tier 0" greys
local NEUTRAL = {
    trim = Color3.fromRGB(96, 100, 110),
    core = Color3.fromRGB(120, 126, 138),
    glow = Color3.fromRGB(150, 158, 170),
}

-- Fixed layer layout. pos is relative to baseCF (studs); each entry seats on `support`
-- ("floor" = bin floor, or an earlier entry index). tilt in degrees.
local LAYOUT = {
    { role = "Container", pos = Vector3.new(0, 0, 0),       tilt = Vector3.new(0, 0, 0),    support = "floor" },
    { role = "Base",      pos = Vector3.new(-2.2, 0, 0.8),  tilt = Vector3.new(6, 15, -4),  support = "floor" },
    { role = "Base",      pos = Vector3.new(2.0, 0, -0.6),  tilt = Vector3.new(-5, -25, 6), support = "floor" },
    { role = "Base",      pos = Vector3.new(0.2, 0, 2.0),   tilt = Vector3.new(8, 5, -8),   support = "floor" },
    { role = "Mid",       pos = Vector3.new(-1.4, 0, -0.2), tilt = Vector3.new(12, 40, -10),support = 2 },
    { role = "Mid",       pos = Vector3.new(1.2, 0, 0.6),   tilt = Vector3.new(-14, -20, 8),support = 3 },
    { role = "Mid",       pos = Vector3.new(0.0, 0, -1.2),  tilt = Vector3.new(10, 0, -16),  support = 4 },
    { role = "Mid",       pos = Vector3.new(-0.4, 0, 1.0),  tilt = Vector3.new(-8, 25, 10),  support = 2 },
    { role = "Small",     pos = Vector3.new(-0.8, 0, -0.4), tilt = Vector3.new(18, 30, -12), support = 5 },
    { role = "Small",     pos = Vector3.new(0.8, 0, 0.2),   tilt = Vector3.new(-16, -10, 14),support = 6 },
    { role = "Small",     pos = Vector3.new(0.2, 0, 0.8),   tilt = Vector3.new(15, 50, -8),  support = 8 },
    { role = "Hero",      pos = Vector3.new(0.0, 0, -0.3),  tilt = Vector3.new(-6, 12, 6),   support = 7 },
}

-- neutral heaps use only the cheap subset (no Hero/FX): first 8 entries
local NEUTRAL_COUNT = 8

local function c3(t: { number }): Color3
    return Color3.new(t[1], t[2], t[3])
end

local function materialForBand(band: string?): Enum.Material
    if band == "metal" then return Enum.Material.Metal
    elseif band == "energized" then return Enum.Material.Metal
    elseif band == "crystal" then return Enum.Material.Glass
    elseif band == "warp" then return Enum.Material.Foil
    elseif band == "prism" then return Enum.Material.Glass
    else return Enum.Material.SmoothPlastic end -- paint / neutral
end

local function colorForRole(role: string, pal): Color3
    if role == "Hero" then return c3(pal.glow)
    elseif role == "Small" then return c3(pal.core)
    elseif role == "Mid" then return c3(pal.trim):Lerp(c3(pal.core), 0.5)
    else return c3(pal.trim) end -- Base / Container
end

-- pool of variant MeshParts for a role, e.g. {Base_1, Base_2, ...}
local function poolFor(role: string): { MeshPart }
    local out = {}
    for _, p in ipairs(KIT:GetChildren()) do
        if p:IsA("MeshPart") and p.Name:match("^" .. role .. "_") then
            table.insert(out, p)
        end
    end
    return out
end

local function heroFor(band: string): MeshPart?
    return KIT:FindFirstChild("Hero_" .. band) :: MeshPart?
end

function ScrapHeapBuilder.heapSeed(slotId: string): number
    local n = 0
    for i = 1, #slotId do
        n += string.byte(slotId, i) * i
    end
    return n
end

function ScrapHeapBuilder.heapCF(origin: CFrame, slotDef: { offset: Vector3 }): CFrame
    local outer = (slotDef.offset.X < 0) and -1 or 1
    local innerX = -outer
    return origin * CFrame.new(slotDef.offset + Vector3.new(innerX * D_DEFAULT, BASE_Y, FRONT_Z))
end

function ScrapHeapBuilder.build(ufoDef: { rarity: string }?, seed: number, baseCF: CFrame): Model
    local rarity = ufoDef and ClawDesign.getRarity(ufoDef.rarity) or nil
    local pal = rarity and rarity.palette or NEUTRAL
    local band = rarity and rarity.materialBand or "paint"
    local fxTier = rarity and rarity.fxTier or 0
    local rng = Random.new(seed)

    local model = Instance.new("Model")
    model.Name = "Heap"
    model:SetAttribute("Rarity", ufoDef and ufoDef.rarity or "neutral")

    -- placed pieces, for support lookup (index -> {part, topY})
    local placed: { { part: BasePart, topY: number } } = {}
    local count = rarity and #LAYOUT or NEUTRAL_COUNT

    for i = 1, count do
        local entry = LAYOUT[i]
        local mesh: MeshPart?
        if entry.role == "Hero" then
            mesh = heroFor(band)
        else
            local pool = poolFor(entry.role)
            if #pool > 0 then
                mesh = pool[rng:NextInteger(1, #pool)]
            end
        end
        if mesh then
            local clone = mesh:Clone()
            clone.Anchored = true
            clone.CanCollide = false
            clone.Color = colorForRole(entry.role, pal)
            clone.Material = (entry.role == "Container") and Enum.Material.Metal or materialForBand(band)

            -- seat: support top + half height - embed
            local supportTopY = BASE_Y
            if type(entry.support) == "number" then
                local s = placed[entry.support]
                if s then supportTopY = s.topY end
            end
            local halfH = clone.Size.Y / 2
            local jitter = Vector3.new(
                (rng:NextNumber() - 0.5) * 0.4, 0, (rng:NextNumber() - 0.5) * 0.4
            )
            local localPos = entry.pos + jitter + Vector3.new(0, supportTopY + halfH - EMBED, 0)
            local cf = baseCF
                * CFrame.new(localPos)
                * CFrame.Angles(math.rad(entry.tilt.X), math.rad(entry.tilt.Y), math.rad(entry.tilt.Z))
            clone.CFrame = cf
            clone.Parent = model

            placed[i] = { part = clone, topY = localPos.Y + halfH }
        end
    end

    -- FX accents (capped): Neon bits at fxTier>=2, one sparkle emitter at fxTier>=3
    if fxTier >= 2 then
        for k = 1, math.min(2, fxTier - 1) do
            local neon = Instance.new("Part")
            neon.Shape = Enum.PartType.Ball
            neon.Size = Vector3.new(0.5, 0.5, 0.5)
            neon.Material = Enum.Material.Neon
            neon.Color = c3(pal.glow)
            neon.Anchored = true; neon.CanCollide = false
            local top = placed[#placed] or placed[1]
            if top then
                neon.CFrame = top.part.CFrame
                    * CFrame.new((rng:NextNumber() - 0.5) * 1.6, 0.6 + k * 0.4, (rng:NextNumber() - 0.5) * 1.6)
            else
                neon.CFrame = baseCF * CFrame.new(0, 2.5 + k * 0.4, 0)
            end
            neon.Name = "HeapNeon"
            neon.Parent = model
        end
    end
    if fxTier >= 3 then
        local emitterHost = (placed[#placed] and placed[#placed].part) or model:FindFirstChildWhichIsA("BasePart")
        if emitterHost then
            local pe = Instance.new("ParticleEmitter")
            pe.Rate = 6
            pe.Lifetime = NumberRange.new(0.6, 1.0)
            pe.Speed = NumberRange.new(0.4, 0.9)
            pe.Color = ColorSequence.new(c3(pal.glow))
            pe.Texture = "rbxasset://textures/particles/sparkles_main.dds"
            pe.LightEmission = 1
            pe.Rotation = NumberRange.new(0, 360)
            pe.Parent = emitterHost
        end
    end

    -- pick a PrimaryPart for safe parenting/cleanup
    model.PrimaryPart = (placed[1] and placed[1].part) or model:FindFirstChildWhichIsA("BasePart")
    return model
end

return ScrapHeapBuilder
```

- [ ] **Step 2: Verify the module compiles & required cleanly (no cycle)**

```lua
-- execute_luau (Edit)
local ok, mod = pcall(require, game.ReplicatedStorage.Shared.ScrapHeapBuilder)
if not ok then return "REQUIRE FAILED: " .. tostring(mod) end
return ("OK fns: build=%s heapSeed=%s heapCF=%s"):format(
    type(mod.build), type(mod.heapSeed), type(mod.heapCF))
```
Expected: `OK fns: build=function heapSeed=function heapCF=function`.

- [ ] **Step 3: Verify the neutral build (structure + anchored + budget)**

```lua
-- execute_luau (Edit)
local SHB = require(game.ReplicatedStorage.Shared.ScrapHeapBuilder)
local m = SHB.build(nil, SHB.heapSeed("s1"), CFrame.new(0, 50, 0))
m.Parent = workspace
local parts, anchored = 0, true
for _, p in ipairs(m:GetDescendants()) do
    if p:IsA("BasePart") then parts += 1; if not p.Anchored then anchored = false end end
end
local rarity = m:GetAttribute("Rarity")
m:Destroy()
return ("neutral: parts=%d anchored=%s rarity=%s"):format(parts, tostring(anchored), tostring(rarity))
```
Expected: `parts` between 6 and 9, `anchored=true`, `rarity=neutral`.

- [ ] **Step 4: Verify a rarity build (colour/material/FX + budget + height)**

```lua
-- execute_luau (Edit)
local SHB = require(game.ReplicatedStorage.Shared.ScrapHeapBuilder)
local m = SHB.build({rarity = "mythic"}, SHB.heapSeed("s3"), CFrame.new(0, 50, 0))
m.Parent = workspace
local parts, neon, minY, maxY = 0, 0, math.huge, -math.huge
for _, p in ipairs(m:GetDescendants()) do
    if p:IsA("BasePart") then
        parts += 1
        if p.Material == Enum.Material.Neon then neon += 1 end
        minY = math.min(minY, p.Position.Y - p.Size.Y/2)
        maxY = math.max(maxY, p.Position.Y + p.Size.Y/2)
    end
end
local rarity = m:GetAttribute("Rarity")
m:Destroy()
return ("mythic: parts=%d neon=%d height=%.1f rarity=%s"):format(parts, neon, maxY - minY, rarity)
```
Expected: `parts` ≤ 20, `neon` ≤ 2 (mythic fxTier=3 → 2), `height` ≤ ~6 (the 50-Y base + mound; the relative span should be ≤ ~5), `rarity=mythic`.

- [ ] **Step 5: Anti-float self-check (every piece supported)**

```lua
-- execute_luau (Edit) — each non-container part must have something within EMBED+tol below it
local SHB = require(game.ReplicatedStorage.Shared.ScrapHeapBuilder)
local m = SHB.build({rarity = "legendary"}, SHB.heapSeed("f5"), CFrame.new(0, 50, 0))
m.Parent = workspace
local Workspace = workspace
local params = RaycastParams.new()
params.FilterType = Enum.RaycastFilterType.Include
local filt = {}
for _, p in ipairs(m:GetDescendants()) do if p:IsA("BasePart") then table.insert(filt, p) end end
params.FilterDescendantsInstances = filt
local floating = {}
for _, p in ipairs(filt) do
    local bottom = p.Position - Vector3.new(0, p.Size.Y/2, 0)
    local hit = Workspace:Raycast(bottom + Vector3.new(0, 0.2, 0), Vector3.new(0, -2.0, 0), params)
    -- a piece is "supported" if something (another piece or the implied floor plane) is within 2 studs below
    if not hit and (p.Position.Y - p.Size.Y/2) > 50 + 0.6 then table.insert(floating, p.Name) end
end
m:Destroy()
return #floating == 0 and "no float OK" or ("FLOATING: " .. table.concat(floating, ", "))
```
Expected: `no float OK`. If pieces float, tune `LAYOUT` `support`/`pos` (Step 1) and re-run — this gate is BLOCKING.

- [ ] **Step 6: Save + commit**

Ask the user to Ctrl+S, then:
```bash
git add build.rbxlx && git commit -m "feat(scrap-heap): ScrapHeapBuilder module (rarity-themed feed mound, anti-float verified)"
```

---

### Task 5: Wire `refreshSlot` — dynamic heap follows the machine — Spec §3.3

**Files:**
- Modify: Studio plot-builder script — `refreshSlot` (`build.rbxlx ≈ :1091338`), add `require` of `ScrapHeapBuilder` near the existing `ClawModel` require (`:1091064`), add a `clearHeap` helper near `clearSlotVisual` (`:1091317`).

**Interfaces:**
- Consumes: `ScrapHeapBuilder.build/heapSeed/heapCF` (Task 4); `info.origin`, `info.model`, `slotDef`, `slotData`, `ufoDef`, `owned` (existing in `refreshSlot`).
- Produces: live `Heap_<slotId>` instances under `info.model` for occupied + unlocked-empty slots.

- [ ] **Step 1: Read the current refreshSlot region to anchor edits**

`script_read` the plot-builder script lines ~1091060–1091070 (requires block), ~1091315–1091325 (`clearSlotVisual`), ~1091336–1091440 (`refreshSlot`). Confirm exact current text before editing (multi_edit needs exact matches).

- [ ] **Step 2: Add the ScrapHeapBuilder require**

`multi_edit` the requires block: add next to the `ClawModel` require line:
```lua
local ScrapHeapBuilder = require(game:GetService("ReplicatedStorage").Shared.ScrapHeapBuilder)
```

- [ ] **Step 3: Add a `clearHeap` helper (mirror clearSlotVisual)**

`multi_edit` to insert after `clearSlotVisual`:
```lua
local function clearHeap(info, slotId: string)
	local h = info.model:FindFirstChild("Heap_" .. slotId)
	if h then h:Destroy() end
end
```

- [ ] **Step 4: Call clearHeap unconditionally + build per branch**

`multi_edit` `refreshSlot`:
1. Right after the existing `clearSlotVisual(info, slotId)` call (~:1091363), add:
```lua
	clearHeap(info, slotId)
	local heapCF = ScrapHeapBuilder.heapCF(info.origin, slotDef)
	local heapSeed = ScrapHeapBuilder.heapSeed(slotId)
```
2. In the occupied branch, right after `model.Parent = info.model` (~:1091392), add:
```lua
				local heap = ScrapHeapBuilder.build(ufoDef, heapSeed, heapCF)
				heap.Name = "Heap_" .. slotId
				heap:SetAttribute("SlotId", slotId)
				heap.Parent = info.model
```
3. In the unlocked-empty `else` branch (the "Placer la pince" block, ~:1091426), before creating the prompt, add:
```lua
		local heap = ScrapHeapBuilder.build(nil, heapSeed, heapCF)
		heap.Name = "Heap_" .. slotId
		heap:SetAttribute("SlotId", slotId)
		heap.Parent = info.model
```
(The locked branch returns earlier and builds nothing — `clearHeap` already ran, so no stale heap survives.)

- [ ] **Step 5: Read back to confirm the edits applied (multi_edit can no-op)**

`script_read` the same regions. Confirm `clearHeap`, the `ScrapHeapBuilder.heapCF`/`heapSeed` lines, and the two `ScrapHeapBuilder.build` calls are present and correctly placed.

- [ ] **Step 6: Live verify in Play (occupied + empty + lock)**

`start_stop_play` to Play. `get_console_output` → expect NO errors mentioning ScrapHeapBuilder/refreshSlot. Then `search_game_tree` with `keywords: "Heap_"` under the player's plot model.
Expected: `Heap_<slotId>` exists for any occupied slot and for unlocked-empty slots; none for locked slots. If no occupied slot exists, place one via the existing place flow (or a temp server Script calling the plot service) to confirm the occupied path builds a rarity heap (`inspect_instance` the Heap → attribute `Rarity` matches the placed claw's rarity). `start_stop_play` to stop.

- [ ] **Step 7: Save + commit**

Ask the user to Ctrl+S (in Edit, after stopping Play), then:
```bash
git add build.rbxlx && git commit -m "feat(scrap-heap): refreshSlot builds Heap_<slotId> per placed machine + neutral on empty"
```

---

### Task 6: Remove old `buildBay` heap + add neutral heap to `buildPreviewPlot` — Spec §3.4

**Files:**
- Modify: Studio plot-builder script — `buildBay` heap block (`≈ :1091524–1091551`), `buildPreviewPlot` (`≈ :1092463`).

**Interfaces:**
- Consumes: `ScrapHeapBuilder` (Task 4).
- Produces: `buildBay` no longer emits any `DebrisPile_`/`DebrisBit_`; `buildPreviewPlot` parents a neutral `Heap_<slotId>` per slot into the preview model.

- [ ] **Step 1: Read the buildBay heap block**

`script_read` `≈ :1091523–1091553` (from `local pileC` through the trailing neon `scrap(...)` line and `return pad`). Confirm exact text.

- [ ] **Step 2: Delete the heap generation from buildBay**

`multi_edit` to remove the block from `local pileC = ...` through the final neon `scrap(Vector3.new(1.0,1.0,1.0), ... )` line (keep `return pad`). buildBay now builds the pit/placard/ring/pad but no heap.

- [ ] **Step 3: Read buildPreviewPlot**

`script_read` `≈ :1092460–1092478`. Confirm where `assemblePlot` is called and where slots are iterated (`setSlotVisual` loop).

- [ ] **Step 4: Add neutral heap baking to buildPreviewPlot**

`multi_edit` `buildPreviewPlot`: after the model is assembled and its origin known, iterate the ground-floor (and floor-1 if the preview includes it) slots and bake a neutral heap:
```lua
	for _, slotDef in ipairs(PlotLayout.slots) do
		local heap = ScrapHeapBuilder.build(nil, ScrapHeapBuilder.heapSeed(slotDef.id), ScrapHeapBuilder.heapCF(origin, slotDef))
		heap.Name = "Heap_" .. slotDef.id
		heap.Parent = model
	end
```
(Use the same `origin`/`model` variable names already present in `buildPreviewPlot` — confirm them in Step 3 and match exactly.)

- [ ] **Step 5: Read back to confirm both edits**

`script_read` both regions. Confirm the buildBay heap block is gone and the buildPreviewPlot loop is present with correct variable names.

- [ ] **Step 6: Compile check**

```lua
-- execute_luau (Edit) — re-require nothing server-side; just confirm no syntax error surfaced
return "edits applied; see get_console_output for compile errors"
```
Run `get_console_output`. Expected: no syntax/compile errors for the plot-builder script.

- [ ] **Step 7: Save + commit**

Ask the user to Ctrl+S, then:
```bash
git add build.rbxlx && git commit -m "feat(scrap-heap): remove buildBay debris gen; bake neutral heaps in buildPreviewPlot"
```

---

### Task 7: Re-bake PlotPreviews (drop old debris, bake new heaps) — Spec §3.4, §8

**Files:**
- Modify: Studio `Workspace.MapBlockout.PlotPreviews` (regenerated)

**Interfaces:**
- Consumes: edited `buildBay`/`buildPreviewPlot` (Task 6).
- Produces: regenerated `PlotPreview_0..7` with no `DebrisPile_*`/`DebrisBit_*` and new `Heap_*` neutral heaps.

- [ ] **Step 1: Pre-bake instance count (baseline)**

```lua
-- execute_luau (Edit)
local prev = game.Workspace.MapBlockout.PlotPreviews
local dp, db, hp = 0, 0, 0
for _, p in ipairs(prev:GetDescendants()) do
    if p.Name:match("^DebrisPile_") then dp += 1
    elseif p.Name:match("^DebrisBit_") then db += 1
    elseif p.Name:match("^Heap_") then hp += 1 end
end
return ("before: DebrisPile=%d DebrisBit=%d Heap=%d"):format(dp, db, hp)
```
Expected: `DebrisPile=64 DebrisBit=1473 Heap=0` (approx).

- [ ] **Step 2: Run the preview baker**

Find the baker entry (Spec: `EditPreviewBaker.run()` ≈ `:1095305`). Invoke it via a temp Edit Script or `execute_luau` requiring the same module the baker uses. Per the project's existing baker mechanism (it does `old:Destroy()` on the `PlotPreviews` folder then rebuilds), run it.

```lua
-- execute_luau (Edit) — adapt the require path to the actual baker module
local baker = require(game.ServerScriptService.<...>.EditPreviewBaker) -- confirm path via script_search "EditPreviewBaker"
return baker.run()
```
Expected: the baker's success string (e.g. "PlotPreviews regenerees : 8 modeles").

- [ ] **Step 3: Post-bake instance count (verify swap)**

Re-run Step 1's count.
Expected: `DebrisPile=0 DebrisBit=0 Heap>0` (Heap = number of unlocked slots × 8 previews).

- [ ] **Step 4: Visual spot check**

`screen_capture` framing a couple of `PlotPreview_*`. Confirm neutral heaps present, contained in bins, none floating, old grey lumps gone.

- [ ] **Step 5: Save + commit (this is the big binary change — rollback point matters)**

Ask the user to Ctrl+S, then:
```bash
git add build.rbxlx && git commit -m "feat(scrap-heap): re-bake PlotPreviews with neutral heaps (drop old DebrisPile/Bit)"
```

---

### Task 8: Full verification & polish — Spec §8

**Files:**
- Modify: Studio (tuning of `ScrapHeapBuilder` LAYOUT/`D`/`baseY` constants if needed)

**Interfaces:**
- Consumes: everything above.
- Produces: a verified, committed feature.

- [ ] **Step 1: Both-rows placement check (the heapCF side bug)**

In Play (or via inspection on a live plot), pick one `offset.X>0` slot and one `offset.X<0` slot. `inspect_instance` each `Heap_<slotId>` and the sibling `UFO_<slotId>`/pad: confirm the heap sits on the AISLE (inner) side of BOTH, in front of the machine — not against the outer wall. If one row is wrong, fix `heapCF` (Task 4 Step 1) and re-verify.

- [ ] **Step 2: Coplanar / z-fight pass**

Run the project's coplanar detector over the new heap instances (and the baked previews). Fix any coplanar same-facing faces by offsetting ≥ 0.04 in `ScrapHeapBuilder` LAYOUT positions. Re-run until clean.

- [ ] **Step 3: Anti-float pass on baked + live heaps (BLOCKING)**

```lua
-- execute_luau (Edit) — scan all Heap_* in workspace; report any part with no support within 2 studs below
local function scan(root)
    local bad = {}
    for _, h in ipairs(root:GetDescendants()) do
        if h:IsA("Model") and h.Name:match("^Heap_") then
            local parts = {}
            for _, p in ipairs(h:GetDescendants()) do if p:IsA("BasePart") then table.insert(parts, p) end end
            local params = RaycastParams.new()
            params.FilterType = Enum.RaycastFilterType.Exclude
            params.FilterDescendantsInstances = {} -- hit everything incl. plot floor
            for _, p in ipairs(parts) do
                local origin = p.Position - Vector3.new(0, p.Size.Y/2 - 0.1, 0)
                local hit = workspace:Raycast(origin, Vector3.new(0, -2.5, 0), params)
                if not hit then table.insert(bad, h.Name .. "/" .. p.Name) end
            end
        end
    end
    return bad
end
local bad = scan(workspace)
return #bad == 0 and "ALL ANCHORED OK" or ("FLOATING: " .. table.concat(bad, ", "))
```
Expected: `ALL ANCHORED OK`. Any float → tune LAYOUT and re-bake the affected path. Do not proceed past a non-empty result.

- [ ] **Step 4: Rarity spread visual validation**

Via the place flow / temp Script, materialise heaps for common, a mid tier (e.g. legendary), and eternal; `screen_capture` each from player approach + distance. Confirm: legible, contained, machine still the visual hero (heap ≤ 4.5 high), FX only on high tiers and within caps.

- [ ] **Step 5: Lifecycle sequence test**

On a live plot: place a claw (heap appears, correct rarity) → transform/prestige (heap rebuilds, no duplicate `Heap_<slotId>`) → unequip (heap → neutral) → lock the slot if possible (heap gone) → stop & re-Play / rejoin with an occupied slot (heap present on join). `search_game_tree keywords:"Heap_"` after each step; confirm exactly one heap per non-locked slot, none on locked.

- [ ] **Step 6: Performance sanity**

`execute_luau` count total `Heap_*` parts in workspace and confirm shared MeshIds:
```lua
local heaps, parts, meshids = 0, 0, {}
for _, h in ipairs(workspace:GetDescendants()) do
    if h:IsA("Model") and h.Name:match("^Heap_") then heaps += 1 end
    if h:IsA("MeshPart") and h.Parent and h.Parent.Name:match("^Heap") then
        parts += 1; meshids[h.MeshId] = (meshids[h.MeshId] or 0) + 1
    end
end
local unique = 0; for _ in pairs(meshids) do unique += 1 end
return ("heaps=%d meshparts=%d uniqueMeshIds=%d"):format(heaps, parts, unique)
```
Expected: `uniqueMeshIds` small (≈ 12–16) regardless of heap count → instancing intact.

- [ ] **Step 7: Final save + commit**

Ask the user to Ctrl+S, then:
```bash
git add build.rbxlx && git commit -m "feat(scrap-heap): verify both-rows placement, anti-float, rarity spread, lifecycle"
```

- [ ] **Step 8: Update memory**

Append a memory note (`scrap-system.md` or a new `scrap-heap-decor.md`) recording: the heap is now `ScrapHeapBuilder` (RS.Shared) driven by `refreshSlot`, rarity-themed, `ScrapKit` assets, neutral on empty, 16 bays/plot, pending Ctrl+S status. Update `MEMORY.md` index.

---

## Self-Review

**Spec coverage:**
- §1/§1.1/§1.2 context → Tasks 0, 5, 6 (consume the documented facts). ✓
- §2 decisions → embodied across Tasks 2–6. ✓
- §3.1 module → Task 4. ✓ §3.2 kit + mesh contracts → Tasks 2, 3. ✓ §3.3 lifecycle/clearHeap → Task 5. ✓ §3.4 removal + previews → Tasks 6, 7. ✓
- §4 asset pipeline (Phases 1–4) → Tasks 1 (1–2), 3 (3), 2/3 (binder via Rubble — NOTE: Rubble pool is optional 0–2; the builder LAYOUT does not require it, so no separate task needed; if used, add `Rubble_*` to the kit in Task 2 Step 2). ✓
- §5 composition/anchor/heapCF → Task 4 (LAYOUT, heapCF, anti-float), Task 8 (both-rows, anti-float). ✓
- §6 rarity ladder → Task 4 (colorForRole/materialForBand/FX caps). ✓
- §7 budget → Task 4 Steps 3–4 (counts), Task 8 Step 6 (instancing). ✓
- §8 verification → Tasks 7, 8. ✓
- §9 non-goals → respected (no gameplay/pad/prompt changes). ✓
- §10 risks → mitigations land in Tasks 0 (rollback/Studio), 4 (seed/heapCF/float), 6–7 (removal/re-bake). ✓

**Placeholder scan:** Studio/Blender exploratory steps (Task 1 search, Task 3 modelling) are inherently procedural, but each carries concrete tool calls, the rubric, and verification `execute_luau` with expected output. The one runtime-resolved path is the `EditPreviewBaker` require in Task 7 Step 2 (`script_search "EditPreviewBaker"` to confirm) and `buildPreviewPlot`'s local var names in Task 6 Step 4 (confirmed in the preceding read step) — both are explicit "confirm exact text first" steps, not hidden TODOs. No "TBD"/"add error handling"/"similar to" placeholders.

**Type consistency:** `ScrapHeapBuilder.build(ufoDef?, seed, baseCF)`, `.heapSeed(slotId)`, `.heapCF(origin, slotDef)` are used identically in Tasks 4 (def), 5, 6. Heap instances always `Heap_<slotId>` with attribute `Rarity`. Kit role names (`Container_/Base_/Mid_/Small_/Hero_<band>`) match between Task 2/3 (creation) and Task 4 (`poolFor`/`heroFor` lookups). ✓
