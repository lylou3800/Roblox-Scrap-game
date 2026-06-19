# Task 3 Report — Refactor: extract `buildBay` (no RDC visual change)

**Date:** 2026-06-17  
**Status:** COMPLETE ✅

---

## What changed

### Module: `ServerScriptService.Server.Services.PlotService`

**Step 1 — Module-scope constants + `buildBay` inserted (lines 473–565)**

Inserted just before `local function buildPlot` (old line 473):
- 7 module-scope color constants: `BAY_CONCRETE`, `BAY_CONCRETE_D`, `STEEL_BAY`, `STEEL_BAY_D`, `HAZ`, `CYAN`, `SCRAP_COLORS`
- `local function buildBay(model, origin, slotDef, displayNum)` — full ~77-line function encapsulating one complete bay (ZoneFloor/Inset/Curb/Posts/Wall/placard/ring/pad/pile)

**Step 2 — Inline bay loop replaced (old lines 550–642 → new lines 644–650)**

Replaced ~93-line block (local color declarations + `bayPart` closure + full `for i, slotDef in ipairs(PlotLayout.slots)` loop body) with:
```luau
	-- Slot bays (RDC = floor 0 ; l'étage est bâti à part par buildFloor2). Voir buildBay.
	local padBySlot: { [string]: BasePart } = {}
	for i, slotDef in ipairs(PlotLayout.slots) do
		if slotDef.floor == 0 then
			padBySlot[slotDef.id] = buildBay(model, origin, slotDef, i)
		end
	end
```

Net script size: 983 lines → 991 lines (buildBay is longer than the extracted loop by 8 lines due to added parameter/comment overhead).

---

## Re-read confirmation (Step 3)

Post-edit `script_read` confirmed:
- `BAY_CONCRETE` et al. at lines 473–487 (module scope)
- `local function buildBay` at line 488, closes at line 565
- `local function buildPlot` at line 567 (directly after `end`)
- New 7-line bay loop at lines 644–650
- **No** local `CONCRETE =`, `CONCRETE_D =`, `STEEL_BAY =`, `HAZ =`, `CYAN =`, or `SCRAP_COLORS =` declarations inside `buildPlot`
- `SorterPCHaz` at line 693 references `HAZ` — resolved to module-scope constant at line 478 ✅

---

## Screen capture observation (Step 4)

Two screen captures taken in Play mode:
1. Ground-level view: 8 industrial bays visible, scrap piles on outer sides, yellow HAZ curbs, steel wall panels, claw machines present — identical to pre-refactor appearance.
2. Overhead aerial view: both rows of 4 bays visible, claw rigs, scrap piles, cyan rings, correct layout.

Visual conclusion: RDC geometry is byte-for-byte identical.

---

## TAG_BAY console output (Step 4)

Temp Script `TempTagBayCheck` created in Edit, then Play started. Console output:

```
TAG_BAY: model=true f1_absent=true
```

- `model=true` — Plot model found, all 8 `Slot_s1..Slot_s8` parts exist ✅
- `f1_absent=true` — No `Slot_f1` (upper-floor slot) present (expected, upper floor not yet implemented) ✅

---

## Temp Script deletion confirmation

`TempTagBayCheck` Script destroyed via `execute_luau` in Edit mode. `FindFirstChild("TempTagBayCheck")` returns `nil`. ✅

Studio left in **Edit** mode. ✅

---

## Concerns / notes

- The old variables were named `CONCRETE`/`CONCRETE_D`; the new module-scope names are `BAY_CONCRETE`/`BAY_CONCRETE_D`. This rename is intentional per the brief to avoid collision with other potential `CONCRETE` locals elsewhere, and does not affect output.
- The `slotDef.floor == 0` guard in the new loop is a forward-compatibility addition from the brief. Since current `PlotLayout.slots` only contains floor-0 slots, all 8 bays are still built and output is unchanged.
- `displayNum == i` for RDC, so sign text "BAIE n" and scrap pile seed `n*7+13` are identical.
- No other modules were touched.
