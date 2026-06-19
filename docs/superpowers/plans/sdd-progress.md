# SDD Progress — Inventory/Hotbar/Placement rework (2026-06-17)

Plan: `docs/superpowers/plans/2026-06-17-inventory-hotbar-claw-placement-rework.md`
Environment: no git; edits applied in Roblox Studio Edit DM via MCP; persist = Ctrl+S.

- Task 1 (ClawPreview util): COMPLETE (runtime-verified vp=ViewportFrame; review clean)
  - CAVEAT for all later verify: execute_luau runs in an ISOLATED context where Registry.controllers is empty. Verify via PlayerGui instance inspection + shared remotes (Net), NOT via Registry.controllers[...] method calls.
- Task 2 (PlotService placeUFO + distances): COMPLETE (placeUFO+validation, 4 prompts tagged Kind/SlotId, dist=18, place branch removed; runtime clean; review clean)
  - NOTE: script_grep treats `(` and `"` as Lua-pattern specials → queries with parens give false negatives; use plain identifier greps.
- Task 3 (HotbarController): COMPLETE (Hotbar=Y cells=11 backpack disabled; review clean). Plan bug fixed: removed invalid `c.holder.GroupTransparency = nil` (CanvasGroup-only). Placed-dimming works via GuiObject.Transparency loop.
- Task 4 (PlacementController): COMPLETE (16 controllers, no errors; placeholder noop lines removed; placeUFO validation proven via bad_payload/already_placed). GAP: happy-path place (empty→uid) not auto-tested (only 1 starter claw in mock) → confirm in final human playtest.
- Task 5 (InventoryController panel): COMPLETE (17 controllers, no errors; shell verified: sidebar/search/chips/grid; count-badge self-assignment fixed). 

## Minor findings (for final review triage)
- [Task 5] Rarity chip row (`filterRow` width `1,-440`) may clip the last 2-3 high rarities (DIVI/COSM/TRAN) at typical widths — needs wrap or narrower chips in a polish pass.
- [Task 5] Populated grid render (cards on tab click) only shell-verified; confirm visually in human playtest (press Tab in game).
- [Task 4] Happy-path placement confirm in human playtest.

## FINAL REVIEW: ready-to-ship, no Critical/Important. 4 Minors all FIXED (one fix wave):
- #1 chip-row clipping → filterRow own line (160,50 / -176,24), chips 46x22, grid down to y=84. FIXED.
- #2 dead locals invType/invRar/invSort in UIController → deleted. FIXED.
- #3 unused findFreeUFO in PlotService → deleted. FIXED.
- #4 placed-claw dim → real scrim Frame overlay (ZIndex 4) replaces ineffective ViewportFrame.Transparency loop. FIXED.
Post-fix boot: [Client] ready (16 controllers), no errors.

## REMAINING (human playtest — MCP can't auto-verify):
1. Press Tab → panel opens, tabs/search/chips/grid populated correctly.
2. Get a 2nd claw (roulette) → select (1-0/click) → empty slot prompt "Pince : <name>" → E places it (happy path).
3. Place/upgrade reach ~18 studs; placed claws show scrim + POSÉE.
## PERSIST: Ctrl+S in Studio (all in Edit DM, unsaved).

# === PIVOT: Tool-based inventory (2026-06-17) ===
Plan: `docs/superpowers/plans/2026-06-17-inventory-tools-rework.md`. Pinces+ferraille become real Roblox Tools; equip=in hand; placed pince Tool disappears; styled backpack replaces native.
- T1 (remove old Hotbar/Inventory controllers): COMPLETE (both deleted; boot clean 17 controllers; native backpack re-enabled; no stale GUIs).
- T2 (ToolService server reconcile + DataService.replicate hook): COMPLETE (ferraille=10 Tools, placed pince has no Tool; DataService given Registry require + reconcile hook; boot clean). WATCH: pre-existing "UIController infinite yield on MainHUD" warning — verify HUD intact at playtest.
- T3 (PlacementController reads equipped pince): COMPLETE (reads Character Tool Kind=pince; old refs gone; boot clean). Happy-path place = composition of proven parts (T2 placed→noTool + placeUFO validation) → confirm in playtest with a 2nd claw.
- T4 (BackpackController styled GUI): COMPLETE (BackpackGui=Y, hotbar 10, panel Tout/Ferraille/Pinces, native off). Minor: × separator → x ASCII (cosmetic).

## TOOLS PIVOT — DONE + happy-path PROVEN at runtime:
- giveUFO (admin) → pince Tool appears → placeUFO → slot set + pince Tool removed (toolAfterPlace=false). Equip-to-place + placed-disappears CONFIRMED.
- MainHUD infinite-yield warning = benign (MainHUD exists, cash label works) — pre-existing, not a regression.
- Minor: hotbar count uses "x" not "×" (cosmetic).
## PERSIST: Ctrl+S in Studio (all Edit DM, unsaved).
- Task 6 (Remove old inventory UI): COMPLETE (16 controllers, no errors; Hotbar+InvPanel present, InventaireBtn hidden; legacy InventoryUIController deleted; populateInventory neutralized). Minor: dead locals invType/invRar/invSort in UIController (StarterPlayer.StarterPlayerScripts.UIController).

## Minor findings (for final review triage)
(none yet)
