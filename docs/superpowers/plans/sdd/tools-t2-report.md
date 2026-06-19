# T2 ToolService — Implementation Report
**Date:** 2026-06-17  
**Status:** COMPLETE — all checks green

---

## Paths Used

- **ToolService created:** `ServerScriptService.Server.Services.ToolService` (ModuleScript, sibling of PlotService)
- **DataService modified:** `ServerScriptService.Server.Services.DataService`
- **Plan source:** `C:\Users\farhi\Documents\Projet\UFO_Catchers\docs\superpowers\plans\2026-06-17-inventory-tools-rework.md` — Task 2

---

## Step A — Path Discovery

- `script_grep "function PlotService.refreshClaw"` → `ServerScriptService.Server.Services.PlotService` line 1022
- PlotService top: `local ServerRoot = script.Parent.Parent` then `local Registry = require(ServerRoot.Registry)` — ToolService uses identical pattern
- `script_grep "function DataService.replicate"` → `ServerScriptService.Server.Services.DataService` line 179 (original)
- DataService did NOT have `local Registry = require(...)` — needed to add it

---

## Step B — ToolService Created

Full source from plan used verbatim, with Registry require path matching PlotService siblings:
```lua
local ServerRoot = script.Parent.Parent
local Registry = require(ServerRoot.Registry)
```
ToolService at line 64 defines `ToolService.reconcile(player)`.
`ToolService:Start()` hooks `CharacterAdded` + runs reconcile for already-present players.

---

## Step C — DataService.replicate Hook

### Two edits applied:

**Edit 1 — Add Registry require near top (line 22):**
```lua
-- OLD (line 22 was ProfileStore):
local ProfileStore = require(ServerRoot.Packages.ProfileStore)

-- NEW:
local Registry = require(ServerRoot.Registry)
local ProfileStore = require(ServerRoot.Packages.ProfileStore)
```

**Edit 2 — Insert reconcile hook at end of replicate function:**
```lua
-- OLD (tail of replicate):
	Net.pushState(player, TableUtil.deepCopy(profile.Data))
end

-- NEW:
	Net.pushState(player, TableUtil.deepCopy(profile.Data))
	-- mirror inventory/pinces into the player's Backpack as Tools
	local ToolService = Registry.services and Registry.services["ToolService"]
	if ToolService then ToolService.reconcile(player) end
end
```

**Verification:** `script_grep "ToolService.reconcile"` confirmed match at `DataService` line 188.

---

## Verification Results

### Console output (Play, ~3s after start):
```
[Server] ready (17 services).
[Client] ready (17 controllers) for lylou38000.
Infinite yield possible on 'Players.lylou38000.PlayerGui:WaitForChild("MainHUD")'  ← PRE-EXISTING, unrelated to T2
```
No new errors. ToolService loaded as one of the 17 services.

### Backpack Tool check (execute_luau Client):
```
backpack pinces=0 ferraille=10 total=10
```
- `ferraille=10` — all 10 scrap stacks mirrored as Tools ✓
- `pinces=0` — starter pince is placed in slot s1, correctly has NO Tool ✓
- `total=10` — only managed Tools in Backpack ✓

### Placed-pince state check (execute_luau Client):
```
starter placed in s1 uid=50992a3b-f214-4c3b-8654-41dfc336001a (should have NO pince Tool while placed)
```
- Confirms the slot→uid link is present and reconcile correctly excludes it from the Backpack ✓

Note: `Net.request("getState")` returns `{ok, data}` (not flat) — the initial execute_luau attempt used `st.plot.slots` directly; fixed to `st.data.plot.slots`.

---

## Concerns

1. **UIController infinite yield** (`WaitForChild("MainHUD")`) is pre-existing and unrelated to T2 — exists before this task.
2. **Registry.services timing:** The hook in `DataService.replicate` guards with `Registry.services and Registry.services["ToolService"]` — if replicate fires before ToolService:Start() registers it (boot ordering), reconcile is skipped for that call. The `CharacterAdded` hook in `ToolService:Start()` covers the character-spawn case independently, so in practice there is no gap. No fix needed for T2 scope.
3. **Ctrl+S** must be done manually in Studio to persist to `build.rbxlx`.
