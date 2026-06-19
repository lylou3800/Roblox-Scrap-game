# Pet System Completion — Implementation Plan

> **For agentic workers:** Implement task-by-task. Steps use `- [ ]` checkboxes. This is a **Roblox place** (`build.rbxlx`) edited via the `Roblox_Studio` MCP — there is **no filesystem source, no pytest, no git**. "Files" = ModuleScript paths (`game.…`). "Verify" = read-back via `script_read`/`inspect_instance` + temp-`Script` `execute_luau` (the Server VM in `execute_luau` is ISOLATED — test live services by creating a temporary `Script` under ServerScriptService, never inline). After edits the user saves with **Ctrl+S** (note "PENDING Ctrl+S"). `multi_edit` can silently no-op → **always read back** what you changed.

**Goal:** Complete the pet system — 6 egg-slot shop ($-unlocked), egg-item→hold→click-hatch flow, plot roaming, money upgrade (no fusion), improved NPC/decor, roulette placeholder removed, billboards near-only, and 10 Blender animal models.

**Architecture:** Reuse the existing `effectKind` bonus pipeline and Tool-based inventory. Config-driven (deterministic time-bucket lineup). Server-authoritative buys/hatches. Pets are data records that render + roam client-side; eggs are real Backpack Tools.

**Tech Stack:** Roblox Luau, `Registry`/`Net` framework, `ProfileStore` (Mock in Studio), `Theme` UI module, Blender (MCP) for assets.

**Spec:** `docs/superpowers/specs/2026-06-17-pet-system-completion-design.md`

---

## File map (paths in the place)

**Configs** (`game.ReplicatedStorage.Shared.Config.*`): `Eggs`, `Pets`, `GameConfig`, `Types`.
**Services** (`game.ServerScriptService.Server.Services.*`): `EggShopService`, `PetService`, `ToolService`, `DataService`, `CatchService`, `InventoryService`, `AutomationService`.
**Controllers** (`game.StarterPlayer.StarterPlayerScripts.Client.Controllers.*`): `EggShopController`, `PetController`, `PetMenuController`, `BackpackController`.
**3D** (`game.Workspace.Environment.*`): `EggShop` (+ `NPC`, `Pedestal1..6`), remove `RoulettePad/Post/Sign`.
**Blender**: `Elements_Blender/pets/` (filesystem — Write tool + Blender MCP).

> The mirror copies under `game.Players.lylou38000.PlayerScripts.Client.Controllers.*` are runtime clones of `StarterPlayer…` — **edit the `StarterPlayer` originals only**.

---

## Phase 1 — Config & data

### Task 1.1: Expand `Eggs` config (12 eggs, tiers, 6-slot lineup, slot costs)

**Files:** Modify `game.ReplicatedStorage.Shared.Config.Eggs`

- [ ] **Step 1:** `script_read` the whole `Eggs` module; note exact current shape of `Eggs` list, `lineupFor`, `currentBucket`, `nextRefreshAt`, `rollPet`, `petsByRarity`, and `LINEUP_SIZE`.
- [ ] **Step 2:** Replace the egg list with the 12 defs (keep old ids `common_egg`/`industrial_egg`/`neon_egg`/`legendary_egg`/`mystery_egg`, add `picnic_egg`/`scrap_egg`/`arcade_egg`/`voltaic_egg`/`prism_egg`/`cosmic_egg`/`ufo_egg`). Each `{ id, name, price, tier, model="egg", weights={commun,peu_commun,rare,epique,legendaire} }`. Drop the `unlock` field. Values per spec §A.1.
- [ ] **Step 3:** Set `LINEUP_SIZE = 6`. Add `EGG_SLOT_COST = { [2]=150000, [3]=3000000, [4]=60000000, [5]=600000000, [6]=6000000000 }` and export it (`Eggs.SLOT_COST = EGG_SLOT_COST`, plus `Eggs.MAX_SLOTS = 6`).
- [ ] **Step 4:** Rewrite `lineupFor(bucket)` to be **tiered** — one egg per tier 1..6, alternating variants by bucket:

```lua
local byTier = {}              -- built once at module load
for _, e in ipairs(Eggs) do byTier[e.tier] = byTier[e.tier] or {}; table.insert(byTier[e.tier], e.id) end
for _, v in pairs(byTier) do table.sort(v) end  -- deterministic variant order

local function lineupFor(bucket: number): { string }
	local out = {}
	for tier = 1, LINEUP_SIZE do
		local variants = byTier[tier]
		if variants and #variants > 0 then
			out[tier] = variants[1 + (bucket % #variants)]
		end
	end
	return out
end
```

- [ ] **Step 5:** Keep `rollPet(eggId, rng?)` and `petsByRarity` as-is (verify the new eggs' `weights` keys match pet rarity ids). Add helper `Eggs.tierOfSlot = function(slot) return slot end` is unnecessary — slot==tier; document it in a comment.
- [ ] **Step 6: Verify.** Temp Script: `require(Eggs); print(#Eggs.lineupFor(0), Eggs.lineupFor(0)[1], Eggs.lineupFor(1)[1])` → lineup has 6 entries; slot-1 egg differs between bucket 0 and 1 (picnic/common alternation). Print `Eggs.rollPet("cosmic_egg")` a few times → returns epique/legendaire pet ids.

### Task 1.2: `Pets` — add `upgradeCost`, remove fusion

**Files:** Modify `game.ReplicatedStorage.Shared.Config.Pets`

- [ ] **Step 1:** `script_read` `Pets`; locate `effOf`, `sellValue`, `applyPetStats`, `bonusValue`, `sellBonus`, `cooldownAt`, `MAX_LEVEL`, and any fusion helper.
- [ ] **Step 2:** Add upgrade-cost knobs + function:

```lua
local UPGRADE_BASE_FACTOR = 0.6     -- fraction of sellBase as base unit
local UPGRADE_LEVEL_EXP = 1.9       -- escalates with target level
function Pets.upgradeCost(def, level)        -- cost to go level -> level+1
	if not def or level >= MAX_LEVEL then return math.huge end
	local base = PetRarities.get(def.rarity).sellBase
	return math.floor(base * UPGRADE_BASE_FACTOR * (level ^ UPGRADE_LEVEL_EXP) + 0.5)
end
```

- [ ] **Step 3:** Remove any `Pets.fuse*`/fusion helper (search the module; fusion logic may live only in `PetService` — if so, nothing to remove here).
- [ ] **Step 4: Verify.** Temp Script: print `Pets.upgradeCost(Pets.get("bunny_plush"),1)`, `(…,9)`, `(…,10)` → finite increasing, `huge` at 10.

### Task 1.3: Profile template + Types

**Files:** Modify `game.ReplicatedStorage.Shared.Config.GameConfig`, `game.ReplicatedStorage.Shared.Types`

- [ ] **Step 1:** In `GameConfig.PROFILE_TEMPLATE`: add `deployedPets = {}`, `eggsInv = {}`, `eggSlots = 1`. Keep `pets = {}`. Remove `petSlots` and `equippedPets` from the template (migration handles old saves — Task 1.4).
- [ ] **Step 2:** In `Types`: add `OwnedEgg = { eggId: string }`; update any `OwnedPet`/profile type to include `deployedPets`/`eggsInv`/`eggSlots`; drop `equippedPets`/`petSlots` if typed.
- [ ] **Step 3: Verify.** `script_read` both, confirm fields present/removed.

### Task 1.4: DataService migration

**Files:** Modify `game.ServerScriptService.Server.Services.DataService`

- [ ] **Step 1:** `script_read` DataService; find the `ProfileStore:Reconcile`/onReady path and the `replicate` function (which calls `ToolService.reconcile`).
- [ ] **Step 2:** After Reconcile, run a migration on `profile.Data`:

```lua
local d = profile.Data
d.deployedPets = d.deployedPets or {}
d.eggsInv = d.eggsInv or {}
if d.eggSlots == nil then d.eggSlots = 1 end
if d.equippedPets then                       -- migrate old -> deployed (cap 3)
	for _, uid in ipairs(d.equippedPets) do
		if #d.deployedPets >= 3 then break end
		if d.pets and d.pets[uid] then table.insert(d.deployedPets, uid) end
	end
	d.equippedPets = nil
end
d.petSlots = nil
```

- [ ] **Step 3: Verify.** Temp Script simulating a profile table with `equippedPets={"a","b","c","d"}` + matching pets → after migration `deployedPets` has ≤3 valid uids, `equippedPets`/`petSlots` nil.

---

## Phase 2 — Server core (PetService + consumers)

### Task 2.1: `PetService` — deploy/recall/upgrade, drop fuse/buySlot

**Files:** Modify `game.ServerScriptService.Server.Services.PetService`

- [ ] **Step 1:** `script_read` PetService fully. Map `grant`, `equip`, `unequip`, `fuse`, `sell`, `buySlot`, the active tick, net handlers, and `MAX_SLOTS`/`SLOT_COST`.
- [ ] **Step 2:** Replace `equip`→`deploy(player, uid)`: fail if not owned / already deployed / `#deployedPets >= 3`; else insert into `deployedPets` + `DataService.replicate`. Replace `unequip`→`recall(player, uid)`: remove from `deployedPets`.
- [ ] **Step 3:** Add `upgrade(player, uid)`: read pet; `level < MAX_LEVEL`; `cost = Pets.upgradeCost(def, level)`; `EconomyService.spend(player,{scrap=cost})`; on success `pet.level += 1` + replicate; return new level. Errors `max_level`/`cant_afford`/`not_owned`.
- [ ] **Step 4:** `sell(player, uid)`: if deployed → auto-`recall` first, then proceed (remove old "refuse if equipped"). Keep `Pets.sellValue` + `EconomyService.add`.
- [ ] **Step 5:** Delete `fuse` and `buySlot` and their net handlers (`fusePet`, `buyPetSlot`). Remove `MAX_SLOTS`/`SLOT_COST` if unused.
- [ ] **Step 6:** Net handlers: register `deployPet {uid}`→`{ok}`, `recallPet {uid}`→`{ok}`, `upgradePet {uid}`→`{level}` or `(false,err)`, keep `sellPet {uid}`→`{value}`.
- [ ] **Step 7:** Active tick: change "for each equipped" → "for each **deployed**" pet. Keep cooldowns/flags/effects unchanged.
- [ ] **Step 8: Verify.** Temp Script: admin-grant a pet, `deploy` 4 → 4th fails; `upgrade` debits & raises level; `sell` a deployed pet auto-recalls + pays.

### Task 2.2: Re-point bonus consumers to `deployedPets`

**Files:** Modify `Config.Pets` helpers + `CatchService`, `InventoryService`, `AutomationService`, `DataService` (offline)

- [ ] **Step 1:** In `Pets.applyPetStats`/`bonusValue`/`sellBonus`/the equipped iterator (`forEachEquipped`), change the source list from `data.equippedPets` to `data.deployedPets`. (If these read `equippedPets` directly, this is the single rename point.)
- [ ] **Step 2:** Grep all services for `equippedPets` (`script_grep`) and replace each read with `deployedPets`. Confirm `CatchService.effectiveStats`/`doGrab`, `InventoryService.sellStack`, `AutomationService` (magnet/yield/offline), `DataService` offline all reference deployed.
- [ ] **Step 3: Verify.** Temp Script: deploy a `sellMult` pet, dump `effectiveStats`/`sellBonus` before/after → bonus only counts deployed; recall → bonus drops.

---

## Phase 3 — Egg shop server logic

### Task 3.1: `EggShopService` — 6-slot gating, buy=egg item, buy slot, hatch

**Files:** Modify `game.ServerScriptService.Server.Services.EggShopService`

- [ ] **Step 1:** `script_read` EggShopService. Map `shopStateFor`, `buyEgg`, the `BuyPrompt` handler, refresh broadcast.
- [ ] **Step 2:** `shopStateFor(player)`: return `{ lineup = {...6...}, nextRefreshAt, eggSlots, slotCosts = Eggs.SLOT_COST }`. Each lineup entry `{ slot, id, name, price, model, rarity=<dominant>, owned = slot<=eggSlots, isNextLocked = slot==eggSlots+1 }`.
- [ ] **Step 3:** Rewrite `buyEgg(player, slot)`: validate `slot<=eggSlots`; `eggId = Eggs.lineupFor(currentBucket())[slot]`; if nil → `lineup_changed`; check soft-cap (count of `eggsInv` < 50) else `egg_inventory_full`; `EconomyService.spend{scrap=egg.price}`; on success add `data.eggsInv[Id.new()] = { eggId }` + `DataService.replicate`; return `{ ok=true, eggId }`. **No pet grant here.**
- [ ] **Step 4:** Add `buyEggSlot(player)`: `cur=data.eggSlots or 1`; fail if `cur>=6`; cost `Eggs.SLOT_COST[cur+1]`; spend; `data.eggSlots=cur+1` + replicate; return `{ slots=cur+1 }`.
- [ ] **Step 5:** Add `hatchEgg(player, uid)`: validate `data.eggsInv[uid]`; `defId = Eggs.rollPet(rec.eggId)`; if nil → return `(false,"roll_failed")` **without consuming**; remove `eggsInv[uid]`; `petUid = PetService.grant(player, defId, 1)`; if `#data.deployedPets < 3` → `PetService.deploy(player, petUid)`; replicate; `Net.sendEvent(player,"petHatched",{petUid,defId,rarity,name})`; return `{ defId, petUid }`.
- [ ] **Step 6:** Net handlers: `getPetShop`→`shopStateFor`; `buyEgg {slot}`; `buyEggSlot`; `hatchEgg {uid}`.
- [ ] **Step 7:** `BuyPrompt` handler (3D): read `prompt.Parent:GetAttribute("EggSlot")`; if that slot `<=eggSlots` → `buyEgg(slot)`; if `==eggSlots+1` → `buyEggSlot`; notify on errors (`locked_slot`/`cant_afford`/`lineup_changed`/`egg_inventory_full`).
- [ ] **Step 8: Verify.** Temp Script: buy slot 2 (debits, eggSlots=2); buy egg slot 1 → `eggsInv` grows, **no new pet**; hatch that uid → pet appears, egg gone, auto-deployed; buying locked slot 5 → `locked_slot`.

---

## Phase 4 — Egg-item inventory

### Task 4.1: `ToolService` — egg Tools + non-solid held visual

**Files:** Modify `game.ServerScriptService.Server.Services.ToolService`

- [ ] **Step 1:** `script_read` ToolService. Map `makePinceTool`, `makeHandle`, `existingTools`, `reconcile`, `_buildHeld/_clearHeld`.
- [ ] **Step 2:** Add `makeEggTool(uid, eggId)`: Tool `RequiresHandle=true,CanBeDropped=false`, name = egg def name; Handle = small part `CanCollide=false`, with a SpecialMesh sphere or egg mesh, color = egg rarity color, transparency 0; attrs `Kind="egg"`, `EggUid=uid`, `DefId=eggId`, `Rarity=<dominant>`.
- [ ] **Step 3:** In `existingTools`, also key egg Tools as `"e:"..EggUid`.
- [ ] **Step 4:** In `reconcile`, after the pince `desired` loop, add: `for uid, rec in pairs(data.eggsInv or {}) do desired["e:"..uid] = { kind="egg", uid=uid, eggId=rec.eggId } end`; in the create branch, build `makeEggTool` for egg kind. Keep destroy-diff intact (handles eggs hatched/removed).
- [ ] **Step 5: Verify.** Temp Script: add `data.eggsInv["x"]={eggId="common_egg"}` + `reconcile` → an egg Tool appears in Backpack with `Kind="egg"`, handle `CanCollide=false`; remove + reconcile → Tool destroyed.

### Task 4.2: `BackpackController` — show/equip/activate eggs

**Files:** Modify `game.StarterPlayer.StarterPlayerScripts.Client.Controllers.BackpackController`

- [ ] **Step 1:** `script_read` BackpackController. Map `collectTools` (currently `Kind=="pince"` only), the hotbar render, icon drawing, equip logic.
- [ ] **Step 2:** Extend `collectTools` to also accept `Kind=="egg"`. Render egg cells with an egg icon (drawn or emoji 🥚) tinted by `Rarity`. Eggs appear after pinces in the hotbar / in the panel grid.
- [ ] **Step 3:** Equipping an egg works via the existing equip path (`Humanoid:EquipTool`). Add: on equip of an egg Tool, bind `tool.Activated` → `Net.request("hatchEgg",{uid=tool:GetAttribute("EggUid")})`. (Bind once per Tool; clean up on unequip/removal.)
- [ ] **Step 4: Verify (human playtest flag):** grant an egg, see it in hotbar, equip → held in hand (non-solid), click → hatch request fires. Confirm via console log + pet appears.

---

## Phase 5 — Client shop & pets

### Task 5.1: `EggShopController` — 6 pedestals, gating display, MaxDistance, hatch FX

**Files:** Modify `game.StarterPlayer.StarterPlayerScripts.Client.Controllers.EggShopController`

- [ ] **Step 1:** `script_read` EggShopController. Map `findShop` (`Pedestal1..3`), `refresh`, label writing, countdown, `hatchFX`, egg spin.
- [ ] **Step 2:** `findShop` → `Pedestal1..6`. `refresh` reads `getPetShop` state (lineup + eggSlots): for slot `k`, set egg/label/prompt per spec §A.4 (unlocked=egg+price; next=lock+"Débloquer $"; beyond=dim lock no price). Hide egg mesh + label for slots beyond `eggSlots+1`.
- [ ] **Step 3:** Set `BillboardGui.MaxDistance = 32` on each egg label billboard (create if labels are SurfaceGui — verify type first; current eggs have a BillboardGui child).
- [ ] **Step 4:** Move the **hatch reveal FX to the hatch moment**: keep `hatchFX` on `petHatched`, but it now fires on click-to-hatch (server sends `petHatched` from `hatchEgg`). Keep the reveal panel; optionally add an in-hand crack burst.
- [ ] **Step 5:** Subscribe to `petShopRefreshed` + state changes → `refresh`. Keep countdown loop.
- [ ] **Step 6: Verify (playtest):** with eggSlots=1, only pedestal 1 shows an egg, pedestal 2 shows "Débloquer", 3-6 dim; labels vanish when far; buying slot 2 reveals pedestal 2.

### Task 5.2: `PetController` — plot roaming + right-click menu + MaxDistance

**Files:** Modify `game.StarterPlayer.StarterPlayerScripts.Client.Controllers.PetController`

- [ ] **Step 1:** `script_read` PetController. Map `makePet`, `buildPlaceholder`, roam loop (currently around HumanoidRootPart), ClickDetector.
- [ ] **Step 2:** Render from `state.deployedPets` (was `equippedPets`). Find local plot via `OwnerUserId` attribute (mirror `PlotController`'s lookup). Compute roam center+extents from the plot footprint; pick waypoints **within** the plot (margin from edges). If no plot yet → don't spawn; retry when plot appears.
- [ ] **Step 3:** Set the pet name `BillboardGui.MaxDistance = 40`.
- [ ] **Step 4:** Change interaction to **right-click**: ClickDetector `RightMouseClick` → `PetMenuController.open(uid)`.
- [ ] **Step 5: Verify (playtest):** deployed pets roam inside the plot, name visible only near, right-click opens the menu.

### Task 5.3: `PetMenuController` — upgrade $/deploy/recall/sell, drop fusion, vignettes

**Files:** Modify `game.StarterPlayer.StarterPlayerScripts.Client.Controllers.PetMenuController`

- [ ] **Step 1:** `script_read` PetMenuController. Map grid render, detail render, the fusion/equip/sell/buy-slot buttons.
- [ ] **Step 2:** Grid: list `state.pets`; mark deployed (in `deployedPets`) with an outline; header `"Déployés <#deployedPets>/3"`. Each card uses a `ViewportFrame` of the pet model (per-animal visual) — reuse the `PetMeshes` clone; fallback icon.
- [ ] **Step 3:** Detail: name, rarity, level N/10, passive lines (`effOf`), active+cooldown; buttons: **Déployer/Recall** (`deployPet`/`recallPet`), **Améliorer — $cost** (`upgradePet`, disabled "Niveau max" at 10, shows `Pets.upgradeCost`), **Vendre $** (`sellPet`, confirm for epique+).
- [ ] **Step 4:** Remove the **Fusionner** button and the **Acheter un slot** button entirely.
- [ ] **Step 5: Verify (playtest):** P opens grid with 3D vignettes; upgrade debits + raises level; deploy/recall respect cap 3; no fusion/buy-slot buttons.

---

## Phase 6 — 3D build (Studio MCP)

### Task 6.1: Remove roulette placeholder

**Files:** `game.Workspace.Environment.RoulettePad/RoulettePost/RouletteSign`

- [ ] **Step 1:** Re-confirm zero script refs (`script_grep "RoulettePad"`, `"RouletteSign"`). Then delete the 3 parts via `execute_luau` (Edit) — `workspace.Environment.RoulettePad:Destroy()` etc.
- [ ] **Step 2: Verify.** `search_game_tree` Environment → roulette parts gone; `ShopService`/`plot.Roulette` untouched.

### Task 6.2: EggShop → 6 pedestals, no overlap

**Files:** `game.Workspace.Environment.EggShop`

- [ ] **Step 1:** Read current pedestal transforms (`Pedestal1..3` at x≈-371..-387, z≈-4, pivot (-379,12,5)). Widen the counter/deck and lay out **6 pedestals** evenly along the counter with clear spacing; set `EggSlot=1..6`. Clone the existing `Egg`+`BillboardGui`+`BuyPrompt`+mesh structure onto the new pedestals.
- [ ] **Step 2:** Run a square-overlap scan (per `project-architecture` memory) over EggShop parts + Decor; nudge any intersecting decor.
- [ ] **Step 3: Verify.** `inspect_instance` EggShop → 6 pedestals with `EggSlot` attrs; screen_capture (Edit) to eyeball spacing.

### Task 6.3: Improve NPC

**Files:** `game.Workspace.Environment.EggShop.NPC`

- [ ] **Step 1:** Rebuild the NPC parts into proper Roblox-character proportions (rounded head + cartoon face, torso, arms, legs, apron, hat), `Theme` palette, anchored, `CanCollide=false`. Add a name `BillboardGui` "Marchand d'Œufs" with `MaxDistance=40`.
- [ ] **Step 2:** Add a light client idle anim (small bob/wave) — extend `EggShopController` or a tiny animator; cheap.
- [ ] **Step 3: Verify.** screen_capture (Edit) → recognizable Roblox-style merchant, no parts detached.

---

## Phase 7 — Blender (10 animals, import deferred)

### Task 7.1: Build the 10 pet models in Blender

**Files:** `Elements_Blender/pets/pets_build.py`, `Elements_Blender/pets/*.blend`, previews, `asset_ids.json`

- [ ] **Step 1:** Write `pets_build.py` (style of `claw_rig/claw_rig_build.py`): a function per pet that builds it from primitives, **1 object per color zone**, good proportions, named to match `PetDef.model`. Roster: bunny_plush, bolt_bot, foam_cube, windup_duck, neon_kitten, magnet_drone, golden_teddy, mini_clawbot, holo_fox, ufo_mascot.
- [ ] **Step 2:** Drive Blender via MCP (`execute_blender_code`) per pet: build, frame, render a preview PNG to `Elements_Blender/pets/`, save a `.blend`.
- [ ] **Step 3:** Write `asset_ids.json` with all 10 ids set to null (to fill after the user uploads via the official addon later).
- [ ] **Step 4: Verify.** Each `.blend` + preview exists; viewport screenshots look clean. (No Studio import now — plugin not connected.)

---

## Phase 8 — Balance & end-to-end

### Task 8.1: Calibrate numbers

- [ ] **Step 1:** Sample late-game income (read `stats.avgIncomePerSec`/economy configs; run a short Play if needed) and adjust egg prices, `EGG_SLOT_COST`, `Pets.upgradeCost` so slot 6 ≈ endgame and each tier's eggs are affordable shortly after unlocking its slot.
- [ ] **Step 2:** Adjust `MaxDistance`, soft-cap, roam radius if playtest shows issues.

### Task 8.2: Full verification (spec §H)

- [ ] **Step 1:** Clean boot (no console errors; services start).
- [ ] **Step 2:** Walk all edge cases in spec §F.3 via temp Scripts + a human playtest checklist; record results.
- [ ] **Step 3:** Note "PENDING Ctrl+S" for the user; update memory.

---

## Self-review notes
- **Spec coverage:** A→F all mapped (A→T1.1/3.1/5.1/6.2; B→T3.1/4.1/4.2/5.1; C→T2.1/2.2/5.2/5.3; D→T6.1-6.3; E→T7.1; F→T1.3/1.4 + edge cases T8.2).
- **Type consistency:** `deployedPets` (not equippedPets) used everywhere post-1.3; `Eggs.SLOT_COST`/`MAX_SLOTS`, `Pets.upgradeCost`, net names `deployPet/recallPet/upgradePet/sellPet/buyEgg/buyEggSlot/hatchEgg/getPetShop` consistent across tasks.
- **No placeholders:** key new code shown inline; service edits described concretely against read-back.
