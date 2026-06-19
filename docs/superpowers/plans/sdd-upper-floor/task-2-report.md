# Task 2 Report — Config `PlotLayout` (floor field, floor2 consts, f1..f8)

## Status
DONE

## Module touched
`ReplicatedStorage.Shared.Config.PlotLayout`

## What landed (confirmed by script_read)

### Step 1 — slots table + `floor2` consts
- Added `floor2` table (lines 15–26) with all 9 fields: `height=24`, `deckThickness=1.4`, `railHeight=4`, `notchHalfW=3`, `notchDepth=12`, `ladderInset=1.2`, `cost=100000`, `currency="scrap"`, `panelOffset=Vector3.new(12,0,-56)`.
- Added `floor = 0` field to all 8 ground-floor slots (s1..s8); X/Z offsets and costs unchanged.
- Added 8 upper-floor slot defs f1..f8 (floor=1, Y=0 in the table literal, tiers 5–9, costs 120 000 → 16 000 000 scrap).

### Step 2 — Y-raise loop
- Added loop before `slotById` construction (lines 64–70): iterates slots, adds `Vector3.new(0, PlotLayout.floor2.height, 0)` to any slot with `floor == 1`.
- `slotById` loop and `return PlotLayout` remain unchanged.

## Verification

### execute_luau command (Edit datamodel, :Clone() pattern)
```luau
local PL = require(game:GetService("ReplicatedStorage").Shared.Config.PlotLayout:Clone())
assert(PL.floor2 and PL.floor2.height == 24, "floor2.height")
local g, f = 0, 0
for _, s in ipairs(PL.slots) do
    assert(s.floor == 0 or s.floor == 1, "floor manquant sur "..s.id)
    if s.floor == 0 then g += 1 else f += 1 ; assert(s.offset.Y == PL.floor2.height, s.id.." Y non relevé ("..s.offset.Y..")") end
end
assert(g == 8 and f == 8, "attendu 8 RDC + 8 étage, got "..g.."/"..f)
assert(PL.slotById.f8 and PL.slotById.f8.unlockCost == 16000000, "slotById.f8")
assert(PL.slotById.s1.offset.Y == 0, "s1 Y doit rester 0")
return "OK PlotLayout floor/floor2/f1..f8"
```

### Returned value
`"OK PlotLayout floor/floor2/f1..f8"`

All assertions passed: floor2.height==24, 8 ground slots (Y==0), 8 upper slots (Y==24), slotById.f8.unlockCost==16000000, s1.offset.Y==0.

## Concerns
None. Studio left in Edit mode. User should Ctrl+S to persist to build.rbxlx.
