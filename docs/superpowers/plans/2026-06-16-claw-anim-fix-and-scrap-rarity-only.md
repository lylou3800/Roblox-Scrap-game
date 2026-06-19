# Claw Animation Fix + Scrap Rarity-Only Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the reversed/stuck claw grab animation, and remove scrap families/themes entirely so rarity is the only classifier (data, server logic, and UI all re-cabled to rarity).

**Architecture:** Roblox game; source of truth is `build.rbxlx`, edited in Studio via the MCP. Two workstreams: (A) collapse the claw's three conflicting animation sources into one (server builder writes correct `RestCF` + closed-jaw `C1`; client drives open/close from closed baseline); (B) delete the `theme` and `family` dimensions across data/server/UI and re-key crafting, claw bonus, drop-gating, and recycler onto rarity.

**Tech Stack:** Luau, Roblox Studio, Studio MCP tools (`script_read`, `script_search`, `script_grep`, `multi_edit`, `inspect_instance`, `search_game_tree`, `get_console_output`, `start_stop_play`, `get_studio_state`).

**Spec:** `docs/superpowers/specs/2026-06-16-claw-anim-fix-and-scrap-rarity-only-design.md`

---

## Environment & verification conventions

- **No git, no unit tests.** "Done" = edit applied + read-back confirms it + Play-test/console confirms behavior.
- **MCP gotchas (from project memory):** `multi_edit` can silently no-op → always read back the edited region. Play compiles a *stale* snapshot if started immediately after an edit → after editing, confirm via a fresh `script_read`/`inspect_instance` before `start_stop_play`, and confirm `Mode=Play` via `get_studio_state` before trusting console. `screen_capture` camera doesn't follow in Play.
- **Two client mirrors:** edit the `StarterPlayer.StarterPlayerScripts…` source; the `Players.lylou38000.PlayerScripts…` copy is a runtime clone (do not edit it as the fix; it regenerates from the source at Play).
- **Server builder & services** live in `build.rbxlx` and are only editable in **Edit mode** (not visible in Play). Confirm `Mode=Edit` via `get_studio_state` before editing them.
- **All scrap config edits are mutually dependent** — the game will not run cleanly between Part B tasks. Do NOT Play-test mid-Part-B; the Part B integration Play-test is Task 18.

---

# PART A — Claw grab animation fix

## Task A1: Locate the server plot builder and capture current claw build code

**Files:**
- Investigate: `build.rbxlx` server builder (likely `ServerScriptService`/`ServerStorage` `PlotService` or similar)

- [ ] **Step 1: Confirm Edit mode**

Run `get_studio_state`. Expected: `Mode = Edit`. If `Play`, stop play with `start_stop_play` and re-confirm.

- [ ] **Step 2: Find the builder that creates the claw model**

Run `script_grep` for `ArmPivot` and separately for `JawMotor` and `RestCF` across the place. Expected: hits in a single server module that builds `UFO_s*` / `Plot_`. Record the script path.

- [ ] **Step 3: Read the claw-build region**

`script_read` the section that creates `ArmPivot`, the `Claw`, the 5 `ClawJaw`/`ClawTip`, and the 5 `JawMotor` (Part0/Part1, C0, C1, and any `:SetAttribute("RestCF", …)` / `:SetAttribute("OpenAngle", …)`). Quote the exact current code into the task notes (needed verbatim for A2/A3).

- [ ] **Step 4: Inspect a live-built claw for ground-truth values**

`inspect_instance` on `Workspace.Plot_<userId>.UFO_s1.ArmPivot` (read `CFrame` and attribute `RestCF`) and on one `JawMotor` (read `C0`, `C1`, `CurrentAngle`) and one `ClawJaw` (read attribute `OpenAngle`).
Expected (confirming the bug): `ArmPivot.CFrame` rotation ≈ −27° Z, but `RestCF` attribute rotation ≈ identity (0°); `JawMotor.C1` carries a ~+32° Z spread; `ClawJaw.OpenAngle` ≈ 0.5.
Record the **real** `ArmPivot` build CFrame expression used by the builder (from Step 3) — that is what `RestCF` must equal.

## Task A2: Builder writes the true RestCF

**Files:**
- Modify: server plot builder (path from A1), the line that sets `ArmPivot`'s `RestCF` attribute.

- [ ] **Step 1: Edit RestCF assignment**

In the builder, change the `RestCF` attribute write so it stores the arm's **actual built CFrame** (the same CFrame/orientation expression used to position `ArmPivot`, including its ~−27° rotation), not an identity-rotation CFrame.

Target shape (adapt to the builder's real variable names from A1):
```lua
-- BEFORE (bug): RestCF stored with identity rotation
-- armPivot:SetAttribute("RestCF", CFrame.new(armPivot.Position))
-- AFTER: store the real built CFrame (position AND rotation)
armPivot:SetAttribute("RestCF", armPivot.CFrame)
```

- [ ] **Step 2: Read back the edit**

`script_read` the edited region. Expected: the `RestCF` write now uses the full `armPivot.CFrame` (rotation preserved), not a position-only/identity CFrame.

- [ ] **Step 3: Defer behavior check to A4** (build runs at Play; verified after A3 in the integrated A4 test).

## Task A3: Builder bakes JawMotor.C1 at the closed grip + single open value; client recalibrated

**Files:**
- Modify: server plot builder (JawMotor `C1` setup + `ClawJaw` `OpenAngle` attribute)
- Modify: `StarterPlayer.StarterPlayerScripts.Client.Controllers.CatchFXController` (constants `DIG_ANGLE`/`JAW_OPEN`/`JAW_GRAB` ~286–290, `animateClaw` ~293–361, idle loop ~533–552)

- [ ] **Step 1: Bake C1 at closed pose in builder**

In the builder, set each `JawMotor.C1` so the jaws sit **closed** (radial fan in `C0` kept; remove the ~+32° Z spread that was baked into `C1`). The per-jaw `C0` (0°, ±72°, ±144° fan) stays; only the `C1` Z-spread is removed/zeroed.

Target shape (adapt to real code from A1):
```lua
-- BEFORE: C1 carried a +32deg Z spread (jaws splayed open at rest)
-- jawMotor.C1 = someAnchorCF * CFrame.Angles(0, 0, math.rad(32))
-- AFTER: C1 at closed grip (no Z spread); spread now lives only in client Transform
jawMotor.C1 = someAnchorCF
```

- [ ] **Step 2: Reconcile OpenAngle to the single open value**

Set the `ClawJaw` `OpenAngle` attribute to the chosen open spread in radians (start at `math.rad(28)` ≈ 0.49) so there is ONE source the client reads, OR remove the attribute entirely if the client will hardcode one constant. Pick one and be consistent in Step 3.

```lua
clawJaw:SetAttribute("OpenAngle", math.rad(28)) -- single source of the open spread
```

- [ ] **Step 3: Recalibrate client jaw constants to open-from-closed**

In `CatchFXController`, redefine the jaw values so **closed = `Transform` 0** (matches new C1) and **open = positive** spread. Replace the old `JAW_OPEN=-0.2`/`JAW_GRAB=-0.6`:
```lua
local JAW_CLOSED = 0                 -- C1 is now baked closed → rest/grab is zero transform
local JAW_OPEN   = math.rad(28)      -- positive spread; must match ClawJaw OpenAngle
```
Update every reference accordingly: anywhere `JAW_GRAB` was used (snap-shut at bottom line ~333, idle hold line ~549) → use `JAW_CLOSED`; anywhere `JAW_OPEN` was used (plunge line ~330) keep `JAW_OPEN` (now positive).

- [ ] **Step 4: Verify the dip direction uses the corrected rest**

Confirm `animateClaw` still computes `down = rest * CFrame.Angles(0, 0, -DIG_ANGLE)` and `up = rest * CFrame.Angles(0, 0, math.rad(-12))`, and that the idle loop line ~537 sets `c.CFrame = rest * CFrame.Angles(0,0,sway)`. With `RestCF` now correct (A2), no code change needed here — just confirm these three lines read `rest` from `GetAttribute("RestCF")`.

- [ ] **Step 5: Read back both edits**

`script_read` the builder C1/OpenAngle region and the `CatchFXController` constants + the lines that referenced the old `JAW_GRAB`. Expected: no remaining reference to the deleted `JAW_GRAB` symbol; C1 has no +32° Z; OpenAngle matches `JAW_OPEN`.

## Task A4: Play-test the claw animation

**Files:** none (verification only)

- [ ] **Step 1: Confirm fresh compile**

After A2/A3 edits, `get_studio_state` to confirm Edit; then `start_stop_play`; then `get_studio_state` to confirm `Mode = Play` (avoids stale-snapshot trap).

- [ ] **Step 2: Inspect the live-built arm + jaws**

`inspect_instance` on `Workspace.Plot_<userId>.UFO_s1.ArmPivot` → `RestCF` attribute rotation now ≈ the real build rotation (~−27°, not identity). `inspect_instance` a `JawMotor` → `C1` has no +32° Z spread.

- [ ] **Step 3: Trigger a grab and observe**

Drive a catch at a slot (interact with the machine). Observe: arm dips **downward** (not up), jaws are **visibly closed at rest**, **open** during the plunge, **snap closed** at the bottom, **stay closed** on the way up, **reopen** at rest.

- [ ] **Step 4: Check console**

`get_console_output`. Expected: no errors referencing `CatchFXController`, `RestCF`, `JawMotor`, or nil `JAW_GRAB`.

- [ ] **Step 5: Tune if needed**

If the open spread looks too small/large, adjust `JAW_OPEN` (client) and `OpenAngle` (builder) together to the same value, re-read-back, re-Play. Stop when the open/close reads cleanly.

---

# PART B — Remove families/themes; rarity-only

> Do NOT Play-test until Task 18. Intermediate states won't run cleanly.

## Task B1: Add `icon` to rarities (UI flair source)

**Files:**
- Modify: `ReplicatedStorage.Shared.Types` (`RarityDef`)
- Modify: `ReplicatedStorage.Shared.Config.Rarities` (10 rows)

- [ ] **Step 1: Add icon field to the type**

In `Types`, add to `RarityDef`: `icon: string?,`.

- [ ] **Step 2: Add an emoji to each of the 10 rarities**

In `Rarities`, add an `icon` to each row. Suggested mapping (adjust to taste):
```lua
-- common ⚪, uncommon 🟢, rare 🔵, epic 🟣, legendary 🟠,
-- mythic 🔴, relic 🟤, divine ⚜️, cosmic 🩵, transcendent 🌈
```
Add `icon = "⚪"` (etc.) to each existing row, keeping all other fields intact.

- [ ] **Step 3: Read back**

`script_read` `Rarities`. Expected: all 10 rows have an `icon`, `Rarities.list` ordering unchanged.

## Task B2: Remove family/theme from shared Types

**Files:**
- Modify: `ReplicatedStorage.Shared.Types`

- [ ] **Step 1: Delete type defs and fields**

Remove `export type ItemFamily = …` (line ~25) and `export type ScrapTheme = …` (lines ~38–48). In `LootItemDef`, remove `family: ItemFamily` (~30) and `theme: string?` (~31). In `UFOStats`, change `specialEfficiency: { family: string, mult: number }?` → `specialEfficiency: { rarity: string, mult: number }?` (~69). In `MachineDef`, remove `accepts: { ItemFamily }` (~90).

- [ ] **Step 2: Read back**

`script_read` `Types`. Expected: no remaining `ItemFamily`, `ScrapTheme`, `.family`, `.theme`, or `accepts` references.

## Task B3: Strip family/theme from LootTable

**Files:**
- Modify: `ReplicatedStorage.Shared.Config.LootTable`

- [ ] **Step 1: Remove the two fields from all 31 items**

For each item, delete `family = "…"` and `theme = "…"`, keeping `id, name, baseValue, rarity, dropWeight`. Example:
```lua
-- BEFORE: { id = "soda_can", name = "Canette", family = "monetary", theme = "domestic", baseValue = 3, rarity = "common", dropWeight = … }
-- AFTER:  { id = "soda_can", name = "Canette", baseValue = 3, rarity = "common", dropWeight = … }
```

- [ ] **Step 2: Read back**

`script_grep` for `family` and `theme` within `LootTable`. Expected: zero matches.

## Task B4: Delete ScrapThemes module + all requires

**Files:**
- Delete: `ReplicatedStorage.Shared.Config.ScrapThemes`
- Modify: every script that `require`s it

- [ ] **Step 1: Find all requires**

`script_grep` for `ScrapThemes`. Record every path.

- [ ] **Step 2: Remove each require + downstream usage**

In each hit, delete the `require(... ScrapThemes)` line. Usages of `ScrapThemes.get/list/byId` are removed by the tasks that own those files (CatchService B9, UIController B14/B15, ScrapyardController B13) — for any file not otherwise covered, remove the usage here.

- [ ] **Step 3: Delete the module**

Remove the `ScrapThemes` ModuleScript from `ReplicatedStorage.Shared.Config`.

- [ ] **Step 4: Read back**

`script_grep` for `ScrapThemes`. Expected: zero matches anywhere.

## Task B5: Re-key Crafts recipes to rarity

**Files:**
- Modify: `ReplicatedStorage.Shared.Config.Crafts`

- [ ] **Step 1: Convert each recipe requirement from family to rarity**

Replace `{ family = "…", count = N }` entries with `{ rarity = "…", count = N }`, mapping each old family to a sensible rarity tier (preserve counts; pick tiers that keep difficulty similar). Example:
```lua
-- BEFORE: recipe = { { family = "monetary", count = 40 }, { family = "craft", count = 10 } }
-- AFTER:  recipe = { { rarity = "common",   count = 40 }, { rarity = "rare",  count = 10 } }
```

- [ ] **Step 2: Read back**

`script_grep` `family` in `Crafts`. Expected: zero matches; every requirement has `rarity`.

## Task B6: Re-key ClawDesign rank bonus to rarity

**Files:**
- Modify: `ReplicatedStorage.Shared.Config.ClawDesign` (`RANKS` ~47–53, `genStats` ~88/97–134)

- [ ] **Step 1: Change RANKS family → rarity**

In each rank, replace `family = "<x>"` with `rarity = "<tier>"`, mapping the old fetish family to a target rarity (rank "all" keeps a sentinel `rarity = "all"`). Example:
```lua
-- BEFORE: [3] = { …, family = "monetary" }
-- AFTER:  [3] = { …, rarity = "common" }   -- rank III boosts Common scrap value
```

- [ ] **Step 2: Update genStats**

Change `specialEfficiency = { family = r.family, mult = … }` → `specialEfficiency = { rarity = r.rarity, mult = … }`.

- [ ] **Step 3: Read back**

`script_grep` `family` in `ClawDesign`. Expected: zero matches; `specialEfficiency` built with `rarity`.

## Task B7: Remove recycler `accepts` from Machines

**Files:**
- Modify: `ReplicatedStorage.Shared.Config.Machines` (~13)

- [ ] **Step 1: Delete the accepts field**

Remove `accepts = { "monetary", "utility", "craft" }` from `recycler`.

- [ ] **Step 2: Read back**

`script_read` `Machines`. Expected: no `accepts` field remains.

## Task B8: Drop `themes` from profile template

**Files:**
- Modify: `ReplicatedStorage.Shared.Config.GameConfig` (`PROFILE_TEMPLATE.sellFilter` ~58)

- [ ] **Step 1: Edit the template**

Change `sellFilter = { rarities = {}, themes = {} }` → `sellFilter = { rarities = {} }`.

- [ ] **Step 2: Read back**

`script_read`. Expected: `sellFilter` only has `rarities`.

## Task B9: CatchService — rarity gating + rarity bonus match

**Files:**
- Modify: `CatchService` in `build.rbxlx` (`rollLoot` ~617696–617775)

- [ ] **Step 1: Read current rollLoot**

`script_read` `rollLoot`. Quote the theme `minTier` pool-filter loop (~617701–617714) and the family-bonus block (~617717–617723).

- [ ] **Step 2: Replace theme gating with rarity gating**

Delete the `ScrapThemes.get(def.theme)` / `th.minTier <= clawTier` pool filter. Replace with a rarity gate keyed on `clawTier`: only allow items whose rarity `order` ≤ a cap derived from `clawTier` (so better claws unlock higher rarities). Target shape:
```lua
local Rarities = require(Shared.Config.Rarities)
-- maxOrder unlocked grows with clawTier (tune the mapping to taste; clamp 1..10)
local maxOrder = math.clamp(clawTier + 1, 1, 10)
local pool = {}
for _, def in ipairs(LootTable) do
    local r = Rarities.get(def.rarity)
    if r and r.order <= maxOrder then
        table.insert(pool, def)
    end
end
if #pool == 0 then pool = LootTable end -- safety fallback
```

- [ ] **Step 3: Replace family bonus with rarity bonus**

Change `se.family == "all" or se.family == itemDef.family` → `se.rarity == "all" or se.rarity == itemDef.rarity`.

- [ ] **Step 4: Read back**

`script_grep` `theme` and `family` in `CatchService`. Expected: zero matches; `rollLoot` now references `Rarities`/`def.rarity`.

## Task B10: CraftService — count/consume by rarity

**Files:**
- Modify: `CraftService` in `build.rbxlx` (`familyCount` ~620445–620456, `consume` ~620458–620475, `craft` ~620477–620504)

- [ ] **Step 1: Read current functions**

`script_read` the three functions. Note they iterate inventory matching `def.family` and read `req.family`.

- [ ] **Step 2: Re-key to rarity**

Rename/retarget `familyCount(data, family)` → `rarityCount(data, rarity)` matching `def.rarity`; `consume(data, family, amount)` → `consume(data, rarity, amount)` matching `def.rarity`; in `craft`, check/consume `req.rarity` instead of `req.family`. Keep the same structure, swap the keyed field.

- [ ] **Step 3: Read back**

`script_grep` `family` in `CraftService`. Expected: zero matches.

## Task B11: InventoryService — drop theme filter + byTheme

**Files:**
- Modify: `InventoryService` in `build.rbxlx` (`sellFiltered` ~618353–618371, `sellableInfo` ~618374–618393, `sellableByRarity` ~618445–618469, `holdings` ~618476–618503)

- [ ] **Step 1: Read current functions**

`script_read` all four. Note `filter.themes` reads and the `byTheme` accumulation in `holdings`.

- [ ] **Step 2: Remove theme exclusion in the three sell functions**

In `sellFiltered`, `sellableInfo`, `sellableByRarity`: delete the `filter.themes` lookups and the `def.theme`-based exclusion; keep the `rarities` filter logic intact.

- [ ] **Step 3: Remove byTheme from holdings**

In `holdings`, delete the `byTheme[...]` accumulation and the `thm[theme]` exclusion; stop returning `byTheme`. Keep `byRarity`.

- [ ] **Step 4: Read back**

`script_grep` `theme` in `InventoryService`. Expected: zero matches.

## Task B12: ScrapyardService — drop theme from filter handlers

**Files:**
- Modify: `ScrapyardService` (sell-filter handlers) in `build.rbxlx` (`getFilter` ~620564–620569, `setSellFilter` ~620936–620956, `getPileInfo` ~620967–620976)

- [ ] **Step 1: Read handlers**

`script_read` the three. Note `d.sellFilter.themes` init and the `payload.kind == "theme"` branch.

- [ ] **Step 2: Remove themes**

In `getFilter`: stop initializing/persisting `d.sellFilter.themes`. In `setSellFilter`: delete the `kind == "theme"` branch and any `f.themes` clearing (keep the `rarity`/`rarities` branch). `getPileInfo` returns `holdings()` which no longer includes `byTheme` (from B11) — no change needed beyond confirming it doesn't reference `byTheme`.

- [ ] **Step 3: Read back**

`script_grep` `theme` in `ScrapyardService`. Expected: zero matches.

## Task B13: ScrapyardController (TRI DU TAS) — remove family section

**Files:**
- Modify: `StarterPlayer.StarterPlayerScripts.Client.Controllers.ScrapyardController` (`FAMILY_LABEL` ~35, families build ~36–47, family section ~181–196, `filt`/`themes` refs ~26/201/211/214)

- [ ] **Step 1: Read the controller**

`script_read` the file. Confirm the family chip section and the `setSellFilter{kind="theme"}` requests.

- [ ] **Step 2: Delete family UI + theme requests**

Remove `FAMILY_LABEL` (~35) and the `families` list build (~36–47). Delete the `gridSection("🧰 Garder par famille", …)` block and its chips/requests (~181–196). Remove `themes` from the local `filt` table and any `filt.themes` reads (~26/201/211/214). Keep the rarity keep-section (~171–179) and the rarity inventory breakdown (~217–238) fully intact.

- [ ] **Step 3: Remove the ScrapThemes require** (if not already done in B4).

- [ ] **Step 4: Read back**

`script_grep` `theme`, `famille`, `family`, `ScrapThemes` in `ScrapyardController`. Expected: zero matches.

## Task B14: UIController inventory menu — color/name by rarity

**Files:**
- Modify: `StarterPlayer.StarterPlayerScripts.UIController` (inventory: `invTheme` ~63, theme chip ~83–88, theme resolve ~114, filter test ~115, junk rows ~132–137)

- [ ] **Step 1: Read the inventory menu region**

`script_read` lines ~60–140.

- [ ] **Step 2: Remove the theme filter chip + state**

Delete `local invTheme="all"` (~63) and the "Theme: Tous / Theme <icon>" chip block (~83–88). Remove the `(invTheme=="all" or …)` clause from the filter test (~115), keeping any rarity filter.

- [ ] **Step 3: Recolor/rename junk rows by rarity**

Replace the theme resolve (`local theme = ScrapThemes.get(idef.theme)`, ~114) with `local rar = Rarities.get(idef.rarity)`. In the row render (~132–137): badge color from `Color3.new(unpack(rar.color))`, title prefix from `rar.icon` (added in B1), subtitle uses `rar.name` instead of `it.theme.name`.

- [ ] **Step 4: Read back**

`script_grep` `theme`/`invTheme` in the inventory region. Expected: zero matches; rows use `Rarities`.

## Task B15: UIController index (SCRAPS) — group by rarity

**Files:**
- Modify: `StarterPlayer.StarterPlayerScripts.UIController` (IndexUFO SCRAPS ~184–194)

- [ ] **Step 1: Read the index region**

`script_read` ~180–200.

- [ ] **Step 2: Regroup by rarity**

Replace the per-theme grouping loop with a per-rarity loop over `Rarities.list` (sorted by `order`). For each rarity: header `rar.icon.." "..rar.name.."   (disc/total)"`, list items where `d.rarity == rar.id`, rows colored `Color3.new(unpack(rar.color))` and prefixed with `rar.icon`.
```lua
for _, rar in ipairs(Rarities.list) do
    -- header: rar.icon .. " " .. rar.name .. "   (" .. disc .. "/" .. total .. ")"
    for _, d in ipairs(scrapDefs) do
        if d.rarity == rar.id then
            -- row: prefix rar.icon, color Color3.new(unpack(rar.color))
        end
    end
end
```

- [ ] **Step 3: Read back**

`script_grep` `theme`/`th.icon`/`th.color` in the index region. Expected: zero matches.

## Task B16: UIController crafting menu — requirements by rarity

**Files:**
- Modify: `StarterPlayer.StarterPlayerScripts.UIController` (Ameliorations/craft ~158–169)

- [ ] **Step 1: Read the craft menu region**

`script_read` ~155–172.

- [ ] **Step 2: Switch family counting/display to rarity**

Replace the "paye en scrap par famille" label (~158) with "...par rareté". Replace `fam[d.family]` owned-count accumulation with `rar[d.rarity]`. Render each requirement as `string.format("%s %d/%d", rq.rarity, owned, rq.count)` (~164) using the new `Crafts` `rarity` field. Optionally prefix with the rarity icon/name from `Rarities.get(rq.rarity)`.

- [ ] **Step 3: Read back**

`script_grep` `family`/`fam[` in the craft region. Expected: zero matches.

## Task B17: ClawUpgrade — rarity-keyed specialEfficiency, nil-safe

**Files:**
- Modify: `ReplicatedStorage.Shared.Config.ClawUpgrade` (~46–47)

- [ ] **Step 1: Read the scrapPerSec region**

`script_read` ~40–55. Note `local se = effStats.specialEfficiency; if se and se.mult then rarityFactor *= se.mult end`.

- [ ] **Step 2: Confirm nil-safety**

The guard `if se and se.mult` already handles a missing bonus. Since `specialEfficiency` now carries `rarity` not `family` (B6), no structural change is needed here unless this file reads `se.family` anywhere — `script_grep` `family` in `ClawUpgrade`; if found, remove/retarget to `se.rarity`. Otherwise leave as-is.

- [ ] **Step 3: Read back**

`script_grep` `family` in `ClawUpgrade`. Expected: zero matches.

## Task B18: Full-place sweep for stragglers

**Files:** whole place

- [ ] **Step 1: Grep the entire place for residual references**

`script_grep` each of: `ScrapThemes`, `\.theme`, `\.family`, `byTheme`, `FAMILY_LABEL`, `ItemFamily`, `minTier`, `accepts`, `sellFilter.themes`, `kind == "theme"`, `kind="theme"`.
Expected: only hits are the unrelated UI color palette `ReplicatedStorage.UI.Theme` / `THEME` (cartoon theme module) — NOT scrap. Confirm each remaining hit is the UI palette, not scrap.

- [ ] **Step 2: Fix any straggler**

For any scrap-related hit, apply the matching transformation (rarity) and read back.

## Task 18 (integration): Play-test scrap rarity-only end-to-end

**Files:** none (verification)

- [ ] **Step 1: Fresh compile**

`get_studio_state` (Edit) → `start_stop_play` → `get_studio_state` (confirm `Mode = Play`).

- [ ] **Step 2: Console clean**

`get_console_output`. Expected: no errors about nil `theme`/`family`, `ScrapThemes`, missing module, or `accepts`.

- [ ] **Step 3: Inventory menu**

Open Inventaire. Expected: no theme filter chip; junk rows colored/named by rarity; no theme text.

- [ ] **Step 4: TRI DU TAS terminal**

Interact with the sorting terminal. Expected: only rarity keep-section + rarity breakdown; NO "Garder par famille" section; toggling rarity filters works (server accepts `kind`/`rarity`, no orphaned `theme` request errors in console).

- [ ] **Step 5: Index (SCRAPS)**

Open IndexUFO SCRAPS. Expected: sections grouped by rarity (common→transcendent), each with icon/color; no theme sections.

- [ ] **Step 6: Crafting menu**

Open Ameliorations. Expected: recipe requirements shown by rarity (e.g. "common 12/40"); crafting consumes the right rarity scrap (test a craft if affordable).

- [ ] **Step 7: Drops & bonus**

Catch scrap on a low-tier vs high-tier claw. Expected: low-tier claw only yields lower rarities; higher-tier unlocks higher rarities (rarity gating). Claw rank bonus boosts the targeted rarity's value (spot-check via sell value or $/s display).

- [ ] **Step 8: Recycler**

Use the recycler. Expected: accepts all scrap regardless of former family.

---

## Self-Review notes

- **Spec coverage:** Part A §1–4 → A1–A4. Part B data layer → B1–B8; server logic → B9–B12, B17; UI → B13–B16; edge cases (profile themes B8, client↔server contract B12+B13, byTheme B11, theme.axis removed with ScrapThemes B4, gating B9, index regroup B15, two mirrors B13–B16 on StarterPlayer source, scattered literals B5/B6/B7/B13) → covered; full sweep B18.
- **No mid-Part-B Play-test** is intentional (interdependent config edits).
- **Tuning values** (rarity-gating curve, craft tiers, jaw open angle) are explicitly adjustable in their tasks per the spec's non-objectives.
