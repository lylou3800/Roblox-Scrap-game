# BackpackController Tweak Report
**Date:** 2026-06-17  
**Status:** DONE — all 5 changes applied and verified live.

---

## Summary

Single atomic `multi_edit` on `StarterPlayer.StarterPlayerScripts.Client.Controllers.BackpackController` replaced the entire file with the reworked version. First attempt failed (Studio was in Play mode); stopped play, re-applied successfully.

---

## Changes Applied

### Change 1 — Pinces only + no count badge
- `collectTools`: filter `add` now requires `t:GetAttribute("Kind") == "pince"` (was any Kind).
- Sort simplified to alphabetical only (no kind sort needed).
- `refresh`: removed `local kind = tool:GetAttribute("Kind")` and ferraille count logic; `c.cnt.Text` always `""`.
- Hotbar stroke color now uses `rarityColor(tool:GetAttribute("Rarity") or "common")` directly.

### Change 2 — `togglePanel()` shared function
- Added `local togglePanel, renderPanel` forward declarations at line 19.
- Assigned `togglePanel = function() ... end` at line 57 (after upvalue declarations, before `buildHotbar`).
- `renderPanel` similarly assigned as upvalue so `clearGrid` can call it before `buildPanel` runs.

### Change 3 — Backpack icon button on hotbar
- Hotbar width widened: `(HOTBAR_SLOTS + 1) * 70` (770 instead of 700).
- Drawn bag button (`BackpackBtn`, LayoutOrder=999) added inline at end of `buildHotbar`:
  - Gold `UIStroke` border, brown `P.Soil` body, flap, loop strap, front pocket, gold buckle.
  - `btn.Activated` calls `togglePanel()`.

### Change 4 — Panel restructured (no sidebar)
- Removed: `TABS`, `setTab`, `sidebarBtns`, `currentTab`, sidebar `Frame`.
- `buildPanel`: title label "SAC A DOS" top-left (gold, Theme.Font.Title, maxSize 24), search box top-right (unchanged), full-width `ScrollingFrame` grid `Size = UDim2.new(1,-32,1,-64)` at `Position = UDim2.fromOffset(16,52)`. Panel height 380 (was 360).
- `renderPanel`: no tab filter — only search filter. Card stroke uses `rarityColor(rarity or "common")`.
- `:Start` no longer calls `setTab("Pinces")`.

### Change 5 — Keys
- `UIS.InputBegan`: `if input.KeyCode == TOGGLE_KEY or input.KeyCode == Enum.KeyCode.Backquote then togglePanel(); return end`.

---

## Verification

**Console:** `[Client] ready (18 controllers)` — no errors.

**execute_luau result:**
```
BackpackGui=Y backpackBtn=Y panel=Y panelDesc=3
```
(`panelDesc=3` = title label + search box + scroll frame; grid empty at start because no pince tools have been granted yet — correct.)

**Screenshot (BpTweak):** Confirmed visually:
- 10 hotbar slots + orange/brown bag icon button at right end, gold stroke.
- Panel open showing "SAC A DOS" title gold top-left, "Rechercher..." search box top-right, dark empty grid area (no pinces yet).
- No sidebar tabs present.

---

## Concerns

1. **`P.Soil` color key**: The button uses `P.Soil` for the bag body. If `Theme.Palette` does not define `Soil`, the bag frames will error or render black. Should be confirmed — the claw system memory notes mention `P.Soil` as used in prior roulette code, so likely fine.
2. **`fillIcon` always calls `ClawPreview.make`**: If a tool somehow has `Kind == "pince"` but no `DefId`/`Prestige` attributes, `ClawPreview.make` may error. This is the same risk as before; no regression introduced.
3. **Title text**: Uses ASCII `"SAC A DOS"` (not `"SAC À DOS"` with accent) to avoid encoding issues in the MCP channel. Visually acceptable; can be fixed to the accented version in Studio directly if desired.
