# Task 5 Report — Floor Purchase Panel + `tryUnlockFloor`

## Status
COMPLETE — all 5 steps landed and verified live.

## Module touched
`ServerScriptService.Server.Services.PlotService`

## What landed

### Step 1 — `floorPanel: BasePart?` added to `PlotInfo` type (line 35)
```luau
floorPanel: BasePart?,
```

### Step 2 — Helpers inserted after `buildFloor2` (lines 599–661)
- `groundUnlocked(data)` at line 599 — counts unlocked floor-0 slots vs. total.
- `updateFloorPanel(player)` at line 613 — refreshes SurfaceGui Status label (locked/progress/ready/unlocked states).
- `buildFloorPanel(player, info)` at line 642 — builds the world-fixed post+panel with SurfaceGui + ClickDetector wired to `PlotService.tryUnlockFloor`.

### Step 3 — `assignPlot` block updated (lines ~948–957)
`buildFloorPanel(player, info)` called before the `floor2Unlocked` guard; `updateFloorPanel(player)` called after the slot refresh loop.

### Step 4 — `PlotService.tryUnlockFloor` inserted before `return PlotService` (line 1055)
Server-validated: checks `floor2Unlocked` false, `groundUnlocked` == total (8/8), spends `floor2.cost` scrap via `EconomyService.spend`, sets `data.plot.floor2Unlocked = true`, calls `buildFloor2`, refreshes floor-1 slots, calls `updateFloorPanel` + `replicate` + notify + analytics.

### Step 5 — `updateFloorPanel(player)` inserted in `handleUnlock` (line 964)
After `refreshSlot`, before the "Slot unlocked!" notify — advances the "X/8" counter on the panel whenever a ground bay is purchased.

## Re-read confirmation
`script_grep` results confirmed all symbols present at expected lines:
- `tryUnlockFloor` — lines 658 (ClickDetector call), 1055 (definition)
- `buildFloorPanel` — lines 642 (definition), 950 (assignPlot call)
- `groundUnlocked` — lines 599 (definition), 631 (updateFloorPanel call), 1064 (tryUnlockFloor call)
- `floorPanel` — lines 35 (type), 616, 647, 661, 950, 957 (all usage sites)
- `updateFloorPanel` — lines 613 (definition), 883 (handleUnlock), 957 (assignPlot), 1081 (tryUnlockFloor)

## Live verification — TAG_A / TAG_B / TAG_C

Console output from Play run with TempFloorTest Script:

```
TAG_A no_prereq deck=false
[Analytics] lylou38000 | floor_unlocked |
TAG_B bought floor2=true deck=true
TAG_C no_double_charge=true
```

- **TAG_A** `no_prereq deck=false` — tryUnlockFloor correctly refused (0/8 bays unlocked), no Floor2 model built.
- **TAG_B** `bought floor2=true deck=true` — after unlocking 8 bays + adding 200000 scrap, floor2Unlocked flipped true and Floor2 model appeared in workspace.
- **TAG_C** `no_double_charge=true` — second call was a no-op; scrap balance unchanged.
- Analytics `floor_unlocked` event fired correctly on TAG_B.

## Cleanup
- TempFloorTest Script deleted (confirmed via `script_grep` returning no matches).
- Studio left in **Edit** mode (confirmed via `get_studio_state`).

## Concerns
- `PlotLayout.floor2.panelOffset` must be defined in `PlotLayout` (not added here — assumed provided by an earlier task or pre-existing config). If missing at runtime, `buildFloorPanel` will error on `F.panelOffset + Vector3.new(...)`.
- `PlotLayout.floor2.currency` and `PlotLayout.floor2.cost` are similarly assumed present (the `GameConfig` grep confirmed `floor2Unlocked` is already in the data schema, so the config likely exists).
- No concerns about the purchase flow logic itself — all three validation paths (no prereq / valid purchase / double-buy) behaved as specified.
