# Task 4 Report — `buildFloor2` (dalle + garde-corps + trémie + échelle + 8 baies)

**Date:** 2026-06-17  
**Status:** COMPLETE

---

## What landed

### Step 1 — `buildFloor2` inserted

- Inserted verbatim from the brief at line ~567 (just after `buildBay`'s closing `end`, before `buildPlot`).
- `script_grep` for `buildFloor2` → 3 hits confirmed:
  - Line 518: `local function buildFloor2(info: PlotInfo)` (definition)
  - Line 668: comment in `buildPlot` referencing it
  - Line 884: `buildFloor2(info)` call in `assignPlot`
- `script_grep` for `Floor2Ladder` → Line 563 confirmed.
- `script_grep` for `Floor2Deck` → Lines 544/546/547 confirmed (3 deck parts).

### Step 2 — `assignPlot` wired

- Replaced the exact block (`local info = buildPlot ... for slotId in pairs(data.plot.slots) do refreshSlot ...`) with the conditional `if data.plot.floor2Unlocked then buildFloor2(info) end` block plus the refreshSlot loop with comment.
- Verified at lines 965–975 in the post-edit read.

---

## Live verification

**Method:** Temporarily set `GameConfig.PROFILE_TEMPLATE.plot.floor2Unlocked = true` (Edit mode), started Play, let `assignPlot` run with the flag active.

**execute_luau Server check (TAG_F2):**
```
TAG_F2: deck=true ladder=true fbays=8 deckParts=3
```
- `deck=true` → `Floor2` Configuration marker exists under the plot model.
- `ladder=true` → `Floor2Ladder` TrussPart exists.
- `fbays=8` → Slots `f1..f8` all present under the model.
- `deckParts=3` → 3 Floor2Deck parts (large rear slab + 2 side strips flanking the trémie).

**screen_capture observation:**
- Upper deck clearly visible elevated above ground floor (~24 studs up).
- Yellow hazard trim (HAZ) visible on rear guardrail top edge.
- 8 upper bays visible on the deck surface with scrap debris piles.
- Ground floor bays visible underneath the deck.
- "lylou38000's Scrapyard" label visible at the mid-level transition.
- Yellow TrussPart ladder visible in the initial player-view capture.

---

## Cleanup

- TempSetFloor2 Script: deleted (confirmed `script_grep` → no matches).
- GameConfig `floor2Unlocked`: restored to `false` (confirmed `script_grep`).
- Studio mode: Edit (confirmed `get_studio_state`).
- No temp scripts remain.

---

## Concerns / Notes

1. **ProfileStore.Mock reset:** In Studio, ProfileStore uses Mock mode (no persistence), so `floor2Unlocked` always defaults to template value on each session. The "returning player" path (stop → restart with flag=true from real datastore) can only be tested in a live game. The workaround used (temporarily setting default=true in the template) correctly exercises the `assignPlot → buildFloor2` code path.

2. **Ladder climbability:** The TrussPart (`Floor2Ladder`) is `Anchored=true` with `Material=Metal` — Roblox TrussParts are natively climbable when a character touches them (via the `Climb` state on Humanoid). No additional scripts needed. Could not test player climbing in screen_capture (camera doesn't follow player in Play mode), but the TrussPart type guarantees native climb behavior.

3. **Slot numbering:** The brief uses `for i, slotDef in ipairs(PlotLayout.slots) do if slotDef.floor == 1 then ... buildBay(..., i) end` — meaning `displayNum` = the ipairs index (not 9..16 explicitly). Whether these resolve to "BAIE 9..16" depends on floor-1 slots being at positions 9..16 in `PlotLayout.slots`. This matches the PlotLayout design where floor=0 slots are s1..s8 (indices 1..8) and floor=1 slots are f1..f8 (indices 9..16).

4. **Ready to save:** Ctrl+S in Studio will persist both the PlotService edit and the restored GameConfig.
