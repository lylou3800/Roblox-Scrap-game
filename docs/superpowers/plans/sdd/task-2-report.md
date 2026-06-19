# Task 2 Report — Server: placeUFO remote, prompt attributes, distances

**Status: DONE**
**Date: 2026-06-17**
**File: `ServerScriptService.Server.Services.PlotService`**

---

## Summary

All 4 steps from the plan applied verbatim and verified. PlotService compiles clean, plot assigns, client ready — no errors.

---

## Edits Applied

### Step 1 — Add `SLOT_PROMPT_DIST` constant

- **old:** `local MAX_PLOTS = 8`
- **new:**
  ```lua
  local MAX_PLOTS = 8
  local SLOT_PROMPT_DIST = 18 -- place / unlock / unequip / upgrade reach (was 10)
  ```
- Live line: 26

---

### Step 2 — Bump distances + tag prompts (4 prompt edits)

**Unlock prompt** (was line ~384, now ~345):
- `prompt.MaxActivationDistance = 10` → `= SLOT_PROMPT_DIST`
- Added `prompt:SetAttribute("Kind", "unlock")` + `prompt:SetAttribute("SlotId", slotId)`

**Unequip prompt** (was line ~415, now ~376):
- `prompt.MaxActivationDistance = 10` → `= SLOT_PROMPT_DIST`
- Added `prompt:SetAttribute("Kind", "unequip")` + `prompt:SetAttribute("SlotId", slotId)`

**Upgrade prompt** (was line ~428, now ~390):
- `up.MaxActivationDistance = 10` → `= SLOT_PROMPT_DIST`
- Added `up:SetAttribute("Kind", "upgrade")` + `up:SetAttribute("SlotId", slotId)`

**Place prompt** (was line ~439, now ~403):
- `prompt.ActionText = "Place UFO"` → `"Placer la pince"`
- `prompt.ObjectText = "Empty Slot"` → `"Emplacement vide"`
- `prompt.MaxActivationDistance = 10` → `= SLOT_PROMPT_DIST`
- Added `prompt:SetAttribute("Kind", "place")` + `prompt:SetAttribute("SlotId", slotId)`

---

### Step 3A — Replace `handlePlace` with `placeUFO`

- **old:** entire `local function handlePlace(player: Player, slotId: string) ... end` block (lines 807–826)
- **new:**
  ```lua
  -- Placement is now client-driven: the client sends the selected uid via the "placeUFO" remote.
  local function placeUFO(player: Player, slotId: string, uid: string): (boolean, string?)
      local data = Registry.get("DataService").get(player)
      if not data then return false, "no_data" end
      local slotData = data.plot.slots[slotId]
      if not slotData or not slotData.unlocked or slotData.ufoUid then
          return false, "slot_unavailable"
      end
      if not data.ufos[uid] then return false, "not_owned" end
      -- reject a uid already placed in another slot
      for sid, sd in pairs(data.plot.slots) do
          if sd.ufoUid == uid and sid ~= slotId then return false, "already_placed" end
      end
      slotData.ufoUid = uid
      refreshSlot(player, slotId)
      Net.sendEvent(player, "notify", { text = "Pince posée — elle attrape !", kind = "reward" })
      Registry.get("DataService").replicate(player)
      Registry.get("AnalyticsService").TrackOnce(player, "first_ufo_placed", "first_ufo_placed", { slot = slotId })
      return true
  end
  ```

### Step 3B — Drop `place` branch from `PromptTriggered`

- **old:**
  ```lua
  		if action.kind == "unlock" then
  			handleUnlock(player, action.slotId)
  		elseif action.kind == "place" then
  			handlePlace(player, action.slotId)
  		elseif action.kind == "unequip" then
  ```
- **new:**
  ```lua
  		if action.kind == "unlock" then
  			handleUnlock(player, action.slotId)
  		elseif action.kind == "unequip" then
  ```

---

### Step 4 — Register `Net.onRequest("placeUFO", ...)` in `PlotService:Start()`

Inserted right after the `PromptTriggered:Connect(...)` block, before the closing `end`:

- **old:**
  ```lua
  		elseif action.kind == "upgrade" then
  			handleUpgrade(player, action.slotId)
  		end
  	end)
  end
  ```
- **new:**
  ```lua
  		elseif action.kind == "upgrade" then
  			handleUpgrade(player, action.slotId)
  		end
  	end)

  	Net.onRequest("placeUFO", function(player, payload)
  		if typeof(payload) ~= "table" or typeof(payload.slotId) ~= "string" or typeof(payload.uid) ~= "string" then
  			return false, "bad_payload"
  		end
  		local ok, err = placeUFO(player, payload.slotId, payload.uid)
  		if not ok then return false, err end
  		return true
  	end)
  end
  ```

---

## Verification Output

### script_grep "placeUFO"
```
PlotService | Line: 747 | -- Placement is now client-driven: the client sends the selected uid via the "placeUFO" remote.
PlotService | Line: 748 | local function placeUFO(player: Player, slotId: string, uid: string): (boolean, string?)
PlotService | Line: 865 | 	Net.onRequest("placeUFO", function(player, payload)
PlotService | Line: 869 | 		local ok, err = placeUFO(player, payload.slotId, payload.uid)
```
✓ Function defined + Net.onRequest registered.

### script_grep "SetAttribute" (Kind lines in PlotService)
```
PlotService | Line: 347 | 		prompt:SetAttribute("Kind", "unlock")
PlotService | Line: 378 | 			prompt:SetAttribute("Kind", "unequip")
PlotService | Line: 392 | 			up:SetAttribute("Kind", "upgrade")
PlotService | Line: 405 | 		prompt:SetAttribute("Kind", "place")
```
✓ 4 SetAttribute("Kind", ...) calls — one per slot prompt type.

### script_grep "SLOT_PROMPT_DIST"
```
PlotService | Line: 26  | local SLOT_PROMPT_DIST = 18 -- place / unlock / unequip / upgrade reach (was 10)
PlotService | Line: 345 | 		prompt.MaxActivationDistance = SLOT_PROMPT_DIST
PlotService | Line: 376 | 			prompt.MaxActivationDistance = SLOT_PROMPT_DIST
PlotService | Line: 390 | 			up.MaxActivationDistance = SLOT_PROMPT_DIST
PlotService | Line: 403 | 		prompt.MaxActivationDistance = SLOT_PROMPT_DIST
```
✓ Constant declared + used in all 4 prompts.

### script_grep "MaxActivationDistance = 10"
```
No matches found.
```
✓ 0 occurrences of the old hardcoded distance — all 4 slot prompts updated.

### Play test (start_stop_play → get_console_output)
```
[Server] booting...
[Server] ready (15 services).
[Client] booting...
[Client] ready (14 controllers) for lylou38000.
[Analytics] lylou38000 | plot_assigned | index=0
```
✓ No PlotService errors, plot builds, [Client] ready. Server stopped cleanly.

---

## Concerns

None. All edits matched exactly (no silent no-ops), all verifications passed, runtime clean.

`findFreeUFO` is now unused — left in place per the plan instruction ("leave it, harmless lint warning"). It does not affect runtime.
