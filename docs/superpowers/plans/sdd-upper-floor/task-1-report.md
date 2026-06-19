# Task 1 Report — Données + types (`floor2Unlocked` + slots `f1..f8`)

**Date:** 2026-06-17  
**Status:** DONE

---

## Changes applied

### 1. `ReplicatedStorage.Shared.Types` — line 122

**Replacement applied:**

Old:
```luau
	plot: { expansionLevel: number, slots: { [string]: PlotSlotData } },
```

New:
```luau
	plot: { expansionLevel: number, floor2Unlocked: boolean, slots: { [string]: PlotSlotData } },
```

**Confirmed by re-read:** `script_grep` for `floor2Unlocked` returned `Types | Line: 122 | ...floor2Unlocked: boolean...` ✓

---

### 2. `ReplicatedStorage.Shared.Config.GameConfig` — `PROFILE_TEMPLATE.plot`

**Replacement applied:** Added `floor2Unlocked = false` field and 8 upper-floor slots `f1..f8` (all `unlocked = false, ufoUid = nil`) under a comment marking them as floor-1 slots.

**Confirmed by re-read:** `script_read` lines 38–60 showed the full new block with `floor2Unlocked = false` at line 40, comment at line 50, and `f1..f8` at lines 51–58 ✓

---

## Verification (execute_luau, Edit mode)

Command run (exact snippet from brief Step 5):
```luau
local GC = require(game:GetService("ReplicatedStorage").Shared.Config.GameConfig:Clone())
local p = GC.PROFILE_TEMPLATE.plot
assert(p.floor2Unlocked == false, "floor2Unlocked défaut faux")
local n = 0 ; for k in pairs(p.slots) do n += 1 end
assert(n == 16, "16 slots attendus, got "..n)
for i = 1, 8 do assert(p.slots["f"..i], "slot f"..i.." manquant") ; assert(p.slots["f"..i].unlocked == false, "f"..i.." doit être verrouillé") end
return "OK floor2Unlocked + f1..f8"
```

**Returned:** `"OK floor2Unlocked + f1..f8"` ✓ (matches expected)

---

## Concerns

None. Both edits landed cleanly on first attempt, verification passed with no assertion errors.

---

## Next step

The user can now save (Ctrl+S) to persist to `build.rbxlx`. Task 2 may proceed.
