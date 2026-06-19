## Task 6 Report — Bouton HUD haut-centre (téléport haut↔bas)

### Status
**COMPLETE**

---

### Module touched
`game.StarterPlayer.StarterPlayerScripts.UIController` (LocalScript)

Full Studio path: `StarterPlayer.StarterPlayerScripts.UIController`

---

### Edits applied (2 via `multi_edit`, datamodel_type=Edit)

**Step 1 — require PlotLayout (line 15):**
Added `local PlotLayout=require(RS.Shared.Config.PlotLayout)` immediately after the existing `Pricing` require.

**Step 2 — FloorBtn block (after BuildBtn, lines 194–247):**
Injected the full floor-button code verbatim from the brief:
- `FloorBtn` TextButton parented to `hud`, anchored top-centre (AnchorPoint 0.5,0 / Position 0.5,0,0,12 / Size 220×46)
- `P.Purple` background, `Theme.Corner/Stroke/TextStroke` styling, `UITextSizeConstraint` max 20
- `onUpperFloor()` checks `hrp.Y > FLOOR_H/2` (FLOOR_H=24, threshold=12)
- `updateFloorLabel()` toggles "▲ Monter à l'étage" / "▼ Descendre"
- `MouseButton1Click` teleports via `base.CFrame * CFrame.new(0, FLOOR_H+4, -50)` (up) or `CFrame.new(0, 4, -54)` (down)
- `refreshFloorBtn(st)` gates visibility on `st.plot.floor2Unlocked == true`
- `StateController.onChanged(refreshFloorBtn)` + `refreshFloorBtn(StateController.get())` on init
- `task.spawn` loop refreshing label every 0.5s while visible

**Re-read confirmation:** `script_read` of lines 14–15 confirmed `PlotLayout` require present; lines 194–247 confirmed full FloorBtn block with `floorBtn`, `refreshFloorBtn`, `StateController.onChanged(refreshFloorBtn)`.

---

### Live verification (Play mode)

**Step 1 — No button at spawn (floor not unlocked):**
`screen_capture` at game start: no top-centre floor button visible. ✓

**Unlock method used:**
DataStore API unavailable in Studio → ProfileStore.Mock; `DS.isReady(player)` never returned true during execute_luau calls. Workaround: created a temp `Script` (`ServerScriptService.Task6TestUnlockFloor`) using `DS.onReady(fn)` callback which fired reliably, set `data.plot.floor2Unlocked=true`, called `DS.replicate(player)`. Console confirmed: `[TASK6_TEST] floor2Unlocked=true replicated for lylou38000`.

**Step 2 — Button visible after unlock:**
`screen_capture` confirmed "▲ Monter à l'étage" button in purple at top-centre of HUD. ✓

**Step 3 — Click → teleport up, label → "▼ Descendre":**
- Pre-click: `HRP Y=3.4` (ground floor)
- `user_mouse_input` click on `LocalPlayer.PlayerGui.MainHUD.FloorBtn`
- Post-click: `HRP Y=26.8`, `FloorBtn.Text='▼ Descendre'` (above FLOOR_H=24)
- `screen_capture` confirmed "▼ Descendre" button at top-centre, player on upper deck. ✓

**Step 4 — Re-click → teleport down, label → "▲ Monter à l'étage":**
- Second click: `HRP Y=3.4`, `FloorBtn.Text='▲ Monter à l'étage'`
- `screen_capture` confirmed. ✓

**Step 5 — Label refresh loop:**
Not tested via ladder (no ladder interaction available in MCP). Behaviour is code-verified: `task.spawn` loop checks every 0.5s while `floorBtn.Visible`, calling `updateFloorLabel()` which re-evaluates `hrp.Y > FLOOR_H/2`.

---

### Cleanup
- Temp script `ServerScriptService.Task6TestUnlockFloor` deleted via `execute_luau` (Edit mode `Destroy()`).
- Studio confirmed in **Edit** mode after `start_stop_play{is_start:false}`.
- No other temp scripts left.

---

### Concerns / Notes

1. **DataStore in Studio:** `DS.isReady(player)` never returned true during inline `execute_luau` waits (up to 20s). `ProfileStore.Mock` + `StartSessionAsync` appears not to complete within `execute_luau` execution context. Using a proper `Script` in `ServerScriptService` with `DS.onReady` worked perfectly. This is not a bug in Task 6 — it's a known Studio execute_luau isolation gotcha.

2. **Y coordinate concern:** The "ground floor" return target `base.CFrame * CFrame.new(0, 4, -54)` puts the player at Y ≈ 3.8. This lands them near the plot road/entrance area. If plots are at different Y elevations, the offset may need adjustment — but it matched the existing `SellBtn` pattern and worked correctly in test.

3. **`task.spawn` loop is unbounded:** The `while true do` loop runs indefinitely. This is intentional per the brief (keeps label fresh when player uses ladder). It is guarded by `if floorBtn.Visible` so it only does work when relevant.

4. **Ctrl+S reminder:** The brief designates this as "pending Ctrl+S" — user should save the place file.
