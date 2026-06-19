# ToolService Tweaks — Implementation Report

**Status: DONE — both changes applied and verified live (2026-06-17)**

---

## Changes Made

### Change A — Ferraille removed from reconcile

Deleted the ferraille desired-set loop:
```lua
-- REMOVED:
for key, stack in pairs(data.inventory) do
    if (stack.count or 0) > 0 then desired["f:" .. key] = { kind = "ferraille", key = key, stack = stack } end
end
```

Also cleaned the `for id, d in pairs(desired)` apply block — the `elseif d.kind == "ferraille"` branch (name/count sync) was removed since no ferraille will ever appear in `desired`. The pince branch remains intact. `makeFerrailleTool` was left in the file (harmless — unused).

Existing ferraille Tools in backpacks are auto-destroyed by reconcile (they no longer appear in `desired`).

### Change B — Held textured machine on equip

Added to top requires:
- `local ServerStorage = game:GetService("ServerStorage")`
- `local ClawModel = require(RS.Shared.ClawModel)`

Added (placed between `makeFerrailleTool` and `existingTools`):
- `HELD_SCALE = 0.13`
- `heldCache` — per-defId+prestige template cache stored in ServerStorage
- `heldTemplate()` — builds + caches a scaled-down model (all parts non-collidable, massless)
- `ToolService._buildHeld(tool)` — clones template, pivots to Handle, welds every part to Handle
- `ToolService._clearHeld(tool)` — destroys HeldModel child

In `makePinceTool`, after handle creation:
- Handle made transparent + shrunk to 0.4³ (invisible grip anchor)
- `tool.Equipped:Connect` → `_buildHeld`
- `tool.Unequipped:Connect` → `_clearHeld`

---

## Verification Outputs

**Check 1 — No errors at startup:** `get_console_output` returned empty (no errors). Server and client started cleanly.

**Check 2 — Ferraille gone:**
```
after giveUFO: pinces=1 ferraille=0
```
→ ferraille=0 confirmed. Pince tool created correctly.

**Check 3 — HeldModel on equip:**
```
equipped=true HeldModel=Y parts=48
```
→ HeldModel appears in the equipped tool with 48 BasePart descendants (full claw machine at 0.13 scale).

---

## Concerns / Notes

- **Scale/orientation**: `0.13` scale places the machine in-hand but pivot origin is at the Handle CFrame (which is at the player's hand attachment point). The machine model's internal pivot is its bbox center — this may offset it slightly high or to the side depending on the machine archetype. No visual review was performed (screen_capture is unreliable in Play). If the model floats away from the hand, `clone:PivotTo(handle.CFrame * CFrame.new(0, 0.2, 0))` can be tweaked.
- **`makeFerrailleTool` unused**: Left in file. Safe to delete in a later cleanup pass.
- **`existingTools` still tracks ferraille keys** (the `elseif kind == "ferraille"` scan branch): harmless — it will simply never find any ferraille Tools once reconcile stops creating them. Can be removed in cleanup.
- **heldCache persists across the session** in ServerStorage — if a claw's definition changes mid-session (e.g., prestige upgrade), the cache key changes automatically (`defId|prestige`) so a fresh template is built.
- **No Ctrl+S performed** — edits live in the DM, pending manual save.
