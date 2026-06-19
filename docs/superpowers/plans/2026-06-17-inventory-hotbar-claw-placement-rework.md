# Inventaire + Hotbar + Rework pose des pinces — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the menu-based inventory with a Grow-a-Garden-style inventory (sidebar tabs + search + grid), add an always-visible claw hotbar, and rework claw placement so the player selects a claw in the hotbar and places it into a machine slot with E.

**Architecture:** Three new client controllers (`ClawPreview` util, `HotbarController`, `InventoryController`) + one new client controller for placement (`PlacementController`), plus server changes in `PlotService` (new `placeUFO` remote, prompt attributes, longer distances) and removal of the legacy inventory UI. The server stays authoritative for placement; the client only supplies the selected `uid`.

**Tech Stack:** Roblox Luau, `ReplicatedStorage.UI.Theme` (cartoon UI helpers), `ReplicatedStorage.Shared.ClawModel` (claw model builder), the `Net` request/event layer, `StateController` replication.

## Global Constraints

- **Editing workflow:** ALL edits are applied inside Roblox Studio via the MCP tools in the **Edit** DataModel (`multi_edit` / `execute_luau datamodel_type:"Edit"`). `build.rbxlx` is the source of truth and is persisted by **Ctrl+S** in Studio (there is a `build.rbxlx.lock` → Studio owns the file). There is **no git** and **no test framework** — "verify" steps use `execute_luau`, Play + `get_console_output`, and `screen_capture`.
- **`multi_edit` may silently no-op** — after every edit, verify with `script_grep` / `script_read` before moving on.
- **Play uses a stale snapshot right after an edit** — always Stop → Start fresh before runtime verification, and `multi_edit` requires Stop (Edit mode).
- **Style:** use `ReplicatedStorage.UI.Theme` only (Palette, `Font.Title`=LuckiestGuy / `Font.Body`=FredokaOne, helpers `Corner/Stroke/TextStroke/Pill/Panel/Button/Gradient/SectionHeader`). Do NOT use the legacy `UIUtil` theme.
- **Controller pattern:** new ModuleScripts go under `StarterPlayer.StarterPlayerScripts.Client.Controllers`; they are auto-required and registered as `Registry.controllers[name]`; expose optional `:Init()` then `:Start()`. Cross-controller access via `Registry.get("X")` or `Registry.controllers["X"]`.
- **Single currency** `$` (scrap). **Rarity is the sole classifier.**
- **Toggle key constant:** `TOGGLE_KEY = Enum.KeyCode.Tab` (top of `InventoryController`; never 1-0, reserved for hotbar).
- **Slot prompt distance constant:** `SLOT_PROMPT_DIST = 18` (top of `PlotService`).
- Data shapes (verbatim): `inventory[key] = {defId, rarity, modifier, count, locked}`; `ufos[uid] = {defId, level, prestige}`; slot link = `data.plot.slots[slotId].ufoUid`. Item value is computed: `Pricing.valueOf(defId, rarity, modifier)`.

---

### Task 1: `ClawPreview` util module (shared ViewportFrame builder)

A small reusable module that renders an owned claw as a ViewportFrame thumbnail (used by hotbar + inventory Pinces cards). Caches by `defId|prestige`.

**Files:**
- Create (Studio): `StarterPlayer.StarterPlayerScripts.Client.Controllers.ClawPreview` (ModuleScript)

**Interfaces:**
- Consumes: `ReplicatedStorage.Shared.ClawModel` → `ClawModel.build(ufoDef, prestige, baseCF) -> Model`; `ReplicatedStorage.Shared.Config.UFOCatchers` → `UFOCatchers.get(defId) -> ufoDef`.
- Produces: `ClawPreview.make(defId: string, prestige: number?, parent: GuiObject) -> ViewportFrame` (parents a fresh transparent ViewportFrame filling the parent, returns it).

- [ ] **Step 1: Create the module via `multi_edit`** (Edit DM, `className="ModuleScript"`, first edit empty `old_string`):

```lua
-- ClawPreview.luau — renders an owned claw as a ViewportFrame thumbnail (hotbar + inventory).
local RS = game:GetService("ReplicatedStorage")
local ClawModel = require(RS.Shared.ClawModel)
local UFOCatchers = require(RS.Shared.Config.UFOCatchers)

local ClawPreview = {}

-- Build a model once per (defId|prestige) and clone it into each viewport.
local modelCache: { [string]: Model } = {}

local function cachedModel(defId: string, prestige: number): Model?
	local key = defId .. "|" .. tostring(prestige)
	local m = modelCache[key]
	if m then return m end
	local def = UFOCatchers.get(defId)
	if not def then return nil end
	local ok, built = pcall(function()
		return ClawModel.build(def, prestige, CFrame.new())
	end)
	if not ok or not built then return nil end
	-- Park it centered at origin, anchored, so clones drop straight into a viewport.
	built:PivotTo(CFrame.new())
	for _, p in ipairs(built:GetDescendants()) do
		if p:IsA("BasePart") then p.Anchored = true end
	end
	modelCache[key] = built
	return built
end

function ClawPreview.make(defId: string, prestige: number?, parent: GuiObject): ViewportFrame
	local vp = Instance.new("ViewportFrame")
	vp.Name = "Preview"
	vp.Size = UDim2.fromScale(1, 1)
	vp.BackgroundTransparency = 1
	vp.Ambient = Color3.fromRGB(200, 200, 200)
	vp.LightColor = Color3.fromRGB(255, 255, 255)
	vp.LightDirection = Vector3.new(-0.4, -1, -0.6)
	vp.Parent = parent

	local src = cachedModel(defId, prestige or 0)
	if not src then return vp end
	local clone = src:Clone()
	clone.Parent = vp

	-- Frame the model: camera distance from bounding sphere.
	local cf, size = clone:GetBoundingBox()
	local radius = size.Magnitude / 2
	local cam = Instance.new("Camera")
	local dist = math.max(radius * 2.2, 6)
	cam.CFrame = CFrame.lookAt(cf.Position + Vector3.new(0.7, 0.5, 1).Unit * dist, cf.Position)
	cam.FieldOfView = 35
	vp.CurrentCamera = cam
	cam.Parent = vp
	return vp
end

return ClawPreview
```

- [ ] **Step 2: Verify the module compiles and renders** — Stop play if running, then run `execute_luau` (datamodel `Edit`) is not enough (controllers don't run in Edit). Instead start Play and run (datamodel `Client`):

```lua
local RS = game:GetService("ReplicatedStorage")
local Registry = require(game.Players.LocalPlayer.PlayerScripts.Client.Registry)
local CP = Registry.controllers["ClawPreview"]
local sg = Instance.new("ScreenGui"); sg.Parent = game.Players.LocalPlayer.PlayerGui
local f = Instance.new("Frame"); f.Size = UDim2.fromOffset(120,120); f.Parent = sg
-- pick the player's first owned claw
local st = Registry.get("StateController").get()
local defId, prestige
for _, u in pairs(st.ufos or {}) do defId = u.defId; prestige = u.prestige; break end
local vp = CP.make(defId or "ufo_basic", prestige or 0, f)
return ("vp=%s children=%d defId=%s"):format(vp.ClassName, #vp:GetChildren(), tostring(defId))
```

Expected: returns `vp=ViewportFrame children>=1`, console has no error. (Then `screen_capture` to eyeball the thumbnail; the temp ScreenGui can be ignored — it vanishes on next Play.)

- [ ] **Step 3: Persist** — Stop play, **Ctrl+S** in Studio.

---

### Task 2: Server — `placeUFO` remote, prompt attributes, distances (`PlotService`)

Make placement client-driven (the player's selected `uid`), expose place/upgrade prompt identity to the client via attributes, and widen interaction distance.

**Files:**
- Modify (Studio): `<server>.Services.PlotService` (the server-loaded `PlotService` ModuleScript; locate via `script_search "function PlotService.refreshClaw"`). Disk anchors: refreshSlot prompt blocks ~630837-630902, `handlePlace` 631266-631285, `PromptTriggered` 631384-631398, `:Start()` ends 631399.

**Interfaces:**
- Consumes: existing `data.plot.slots`, `data.ufos`, `refreshSlot`, `Registry.get("DataService")`, `Net.onRequest`.
- Produces: server remote `Net.onRequest("placeUFO", {slotId:string, uid:string})`; ProximityPrompt attributes `Kind` ("place"/"unlock"/"unequip"/"upgrade") and `SlotId` on every slot prompt (read by `PlacementController`).

- [ ] **Step 1: Add the distance constant.** Find the top-of-file locals block (near `local MAX_PLOTS`). Add via `multi_edit`:
  - old: `local MAX_PLOTS = 8`
  - new: `local MAX_PLOTS = 8\nlocal SLOT_PROMPT_DIST = 18 -- place / unlock / unequip / upgrade reach (was 10)`

- [ ] **Step 2: Bump distances + tag prompts with attributes** in `refreshSlot`. Apply these `multi_edit` edits (each `MaxActivationDistance = 10` line is identical, so include enough surrounding context to make each unique). Replace the four prompt definitions:

  Unlock prompt (anchor 630838-630846):
  - old:
    ```
    		prompt.Style = Enum.ProximityPromptStyle.Custom
    		prompt.MaxActivationDistance = 10
    		prompt.RequiresLineOfSight = false
    		prompt.Parent = pad
    		promptActions[prompt] = { owner = player, kind = "unlock", slotId = slotId }
    ```
  - new:
    ```
    		prompt.Style = Enum.ProximityPromptStyle.Custom
    		prompt.MaxActivationDistance = SLOT_PROMPT_DIST
    		prompt.RequiresLineOfSight = false
    		prompt:SetAttribute("Kind", "unlock")
    		prompt:SetAttribute("SlotId", slotId)
    		prompt.Parent = pad
    		promptActions[prompt] = { owner = player, kind = "unlock", slotId = slotId }
    ```

  Unequip prompt (anchor 630866-630877):
  - old:
    ```
    			prompt.HoldDuration = 0.5
    			prompt.MaxActivationDistance = 10
    			prompt.RequiresLineOfSight = false
    			prompt.Parent = pad
    			promptActions[prompt] = { owner = player, kind = "unequip", slotId = slotId }
    ```
  - new:
    ```
    			prompt.HoldDuration = 0.5
    			prompt.MaxActivationDistance = SLOT_PROMPT_DIST
    			prompt.RequiresLineOfSight = false
    			prompt:SetAttribute("Kind", "unequip")
    			prompt:SetAttribute("SlotId", slotId)
    			prompt.Parent = pad
    			promptActions[prompt] = { owner = player, kind = "unequip", slotId = slotId }
    ```

  Upgrade prompt (anchor 630879-630890):
  - old:
    ```
    			up.HoldDuration = 0.2
    			up.MaxActivationDistance = 10
    			up.RequiresLineOfSight = false
    			up.Parent = pad
    			promptActions[up] = { owner = player, kind = "upgrade", slotId = slotId }
    ```
  - new:
    ```
    			up.HoldDuration = 0.2
    			up.MaxActivationDistance = SLOT_PROMPT_DIST
    			up.RequiresLineOfSight = false
    			up:SetAttribute("Kind", "upgrade")
    			up:SetAttribute("SlotId", slotId)
    			up.Parent = pad
    			promptActions[up] = { owner = player, kind = "upgrade", slotId = slotId }
    ```

  Place prompt (anchor 630893-630901):
  - old:
    ```
    		local prompt = Instance.new("ProximityPrompt")
    		prompt.ActionText = "Place UFO"
    		prompt.ObjectText = "Empty Slot"
    		prompt.HoldDuration = 0.3
    		prompt.Style = Enum.ProximityPromptStyle.Custom
    		prompt.MaxActivationDistance = 10
    		prompt.RequiresLineOfSight = false
    		prompt.Parent = pad
    		promptActions[prompt] = { owner = player, kind = "place", slotId = slotId }
    ```
  - new:
    ```
    		local prompt = Instance.new("ProximityPrompt")
    		prompt.ActionText = "Placer la pince"
    		prompt.ObjectText = "Emplacement vide"
    		prompt.HoldDuration = 0.3
    		prompt.Style = Enum.ProximityPromptStyle.Custom
    		prompt.MaxActivationDistance = SLOT_PROMPT_DIST
    		prompt.RequiresLineOfSight = false
    		prompt:SetAttribute("Kind", "place")
    		prompt:SetAttribute("SlotId", slotId)
    		prompt.Parent = pad
    		promptActions[prompt] = { owner = player, kind = "place", slotId = slotId }
    ```

- [ ] **Step 3: Make placement client-driven.** Replace `handlePlace` (631266-631285) with a uid-taking version, and make the server `PromptTriggered` ignore `place` (the client handles it). Two edits:

  Edit A — replace `handlePlace`:
  - old: the whole `local function handlePlace(player: Player, slotId: string) ... end` block (631266-631285).
  - new:
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

  Edit B — drop the `place` branch in `PromptTriggered` (631391-631392):
  - old:
    ```
    		if action.kind == "unlock" then
    			handleUnlock(player, action.slotId)
    		elseif action.kind == "place" then
    			handlePlace(player, action.slotId)
    		elseif action.kind == "unequip" then
    ```
  - new:
    ```
    		if action.kind == "unlock" then
    			handleUnlock(player, action.slotId)
    		elseif action.kind == "unequip" then
    ```

  `findFreeUFO` (631207) becomes unused — leave it (harmless lint warning) or delete its block; do not delete `grantStarterIfNeeded` which still uses direct assignment.

- [ ] **Step 4: Register the `placeUFO` remote** inside `PlotService:Start()`, right after the `ProximityPromptService.PromptTriggered:Connect(...)` block (before the closing `end` at 631399). Insert via `multi_edit` (anchor on the unique end of that connect):
  - old:
    ```
    		elseif action.kind == "upgrade" then
    			handleUpgrade(player, action.slotId)
    		end
    	end)
    end
    ```
  - new:
    ```
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

- [ ] **Step 5: Verify server compiles + remote exists.** `script_grep "placeUFO"` → expect matches in PlotService (`placeUFO` function + `Net.onRequest`). `script_grep "SetAttribute(\"Kind\""` → expect 4 matches in PlotService. Start Play, `get_console_output` → no `PlotService` errors, plot builds, `[Client] ready`.

- [ ] **Step 6: Persist** — Stop, **Ctrl+S**.

---

### Task 3: `HotbarController` — bottom bar + selection + disable Roblox backpack

**Files:**
- Create (Studio): `StarterPlayer.StarterPlayerScripts.Client.Controllers.HotbarController` (ModuleScript)

**Interfaces:**
- Consumes: `Registry.get("StateController")` (`.get()/.onChanged(fn)`), `ReplicatedStorage.UI.Theme`, `ReplicatedStorage.Shared.Config.{UFOCatchers,Rarities}`, `Registry.controllers["ClawPreview"]` (`.make`).
- Produces: `HotbarController.getSelected() -> string?` (selected uid, nil if placed/none), `HotbarController.select(uid: string)` (select + highlight, ignored if uid not owned).

- [ ] **Step 1: Create the module** (`className="ModuleScript"`):

```lua
-- HotbarController.luau — always-visible bottom bar of owned claws; pick one to place with E.
local Players = game:GetService("Players")
local UIS = game:GetService("UserInputService")
local StarterGui = game:GetService("StarterGui")
local RS = game:GetService("ReplicatedStorage")

local ClientRoot = script.Parent.Parent
local Registry = require(ClientRoot.Registry)
local Theme = require(RS.UI.Theme)
local P = Theme.Palette
local UFOCatchers = require(RS.Shared.Config.UFOCatchers)
local Rarities = require(RS.Shared.Config.Rarities)

local HotbarController = {}

local SLOTS = 10 -- slots 1..0
local selectedUid: string? = nil
local cellByIndex: { [number]: any } = {}
local uidByIndex: { [number]: string? } = {}
local placedSet: { [string]: boolean } = {}

local function rarityColor(rar: string): Color3
	local rd = Rarities.get(rar)
	return rd and Color3.new(rd.color[1], rd.color[2], rd.color[3]) or P.Cyan
end

local function disableDefaultBackpack()
	for _ = 1, 8 do
		local ok = pcall(function()
			StarterGui:SetCoreGuiEnabled(Enum.CoreGuiType.Backpack, false)
		end)
		if ok then return end
		task.wait(0.25)
	end
end

local gui, bar
local function buildGui()
	local pg = Players.LocalPlayer:WaitForChild("PlayerGui")
	gui = Instance.new("ScreenGui")
	gui.Name = "Hotbar"
	gui.ResetOnSpawn = false
	gui.IgnoreGuiInset = true
	gui.DisplayOrder = 8
	gui.Parent = pg

	bar = Instance.new("Frame")
	bar.Name = "Bar"
	bar.AnchorPoint = Vector2.new(0.5, 1)
	bar.Position = UDim2.new(0.5, 0, 1, -10)
	bar.Size = UDim2.fromOffset(SLOTS * 78, 78)
	bar.BackgroundTransparency = 1
	bar.Parent = gui
	local layout = Instance.new("UIListLayout")
	layout.FillDirection = Enum.FillDirection.Horizontal
	layout.HorizontalAlignment = Enum.HorizontalAlignment.Center
	layout.VerticalAlignment = Enum.VerticalAlignment.Bottom
	layout.Padding = UDim.new(0, 6)
	layout.SortOrder = Enum.SortOrder.LayoutOrder
	layout.Parent = bar

	for i = 1, SLOTS do
		local cell = Instance.new("TextButton")
		cell.Name = "Cell" .. i
		cell.AutoButtonColor = false
		cell.Text = ""
		cell.Size = UDim2.fromOffset(72, 72)
		cell.BackgroundColor3 = P.PanelBg
		cell.LayoutOrder = i
		cell.Parent = bar
		Theme.Corner(cell, UDim.new(0, 10))
		local stroke = Theme.Stroke(cell, P.Outline, Theme.Dims.StrokeThin)

		local num = Instance.new("TextLabel")
		num.Name = "Num"; num.BackgroundTransparency = 1; num.Size = UDim2.fromOffset(16, 16)
		num.Position = UDim2.fromOffset(3, 1); num.Font = Theme.Font.Title
		num.Text = tostring(i % 10); num.TextColor3 = P.White; num.TextScaled = true
		num.ZIndex = 5; num.Parent = cell
		Theme.TextStroke(num, 1)

		local holder = Instance.new("Frame")
		holder.Name = "Holder"; holder.BackgroundTransparency = 1
		holder.Size = UDim2.new(1, -8, 1, -8); holder.Position = UDim2.fromOffset(4, 4); holder.Parent = cell

		local nameL = Instance.new("TextLabel")
		nameL.Name = "Nom"; nameL.BackgroundTransparency = 1; nameL.Size = UDim2.new(1, -4, 0, 14)
		nameL.AnchorPoint = Vector2.new(0.5, 1); nameL.Position = UDim2.new(0.5, 0, 1, -2)
		nameL.Font = Theme.Font.Body; nameL.Text = ""; nameL.TextColor3 = P.White
		nameL.TextScaled = true; nameL.ZIndex = 6; nameL.Parent = cell
		Theme.TextStroke(nameL, 1)
		local nc = Instance.new("UITextSizeConstraint"); nc.MaxTextSize = 11; nc.Parent = nameL

		local badge = Instance.new("TextLabel")
		badge.Name = "Placed"; badge.BackgroundColor3 = P.Outline; badge.BackgroundTransparency = 0.25
		badge.Size = UDim2.new(1, 0, 0, 14); badge.AnchorPoint = Vector2.new(0.5, 0.5)
		badge.Position = UDim2.fromScale(0.5, 0.5); badge.Font = Theme.Font.Title
		badge.Text = "POSÉE"; badge.TextColor3 = P.Gold; badge.TextScaled = true
		badge.Visible = false; badge.ZIndex = 7; badge.Parent = cell
		local bc = Instance.new("UITextSizeConstraint"); bc.MaxTextSize = 11; bc.Parent = badge

		cell:SetAttribute("Index", i)
		cell.Activated:Connect(function() HotbarController.selectIndex(i) end)
		cellByIndex[i] = { cell = cell, stroke = stroke, holder = holder, nameL = nameL, badge = badge }
	end
end

local function refresh()
	local st = Registry.get("StateController").get()
	if not st then return end
	placedSet = {}
	for _, sd in pairs((st.plot and st.plot.slots) or {}) do
		if sd.ufoUid then placedSet[sd.ufoUid] = true end
	end
	-- stable ordering: collect uids sorted by tier desc then uid
	local uids = {}
	for uid, rec in pairs(st.ufos or {}) do
		local def = UFOCatchers.get(rec.defId)
		table.insert(uids, { uid = uid, rec = rec, tier = (def and def.tier) or 0 })
	end
	table.sort(uids, function(a, b)
		if a.tier ~= b.tier then return a.tier > b.tier end
		return a.uid < b.uid
	end)

	for i = 1, SLOTS do
		local c = cellByIndex[i]
		local entry = uids[i]
		uidByIndex[i] = entry and entry.uid or nil
		for _, ch in ipairs(c.holder:GetChildren()) do ch:Destroy() end
		if entry then
			local def = UFOCatchers.get(entry.rec.defId)
			Registry.controllers["ClawPreview"].make(entry.rec.defId, entry.rec.prestige, c.holder)
			c.nameL.Text = (def and def.name) or entry.rec.defId
			c.stroke.Color = rarityColor(def and def.rarity or "common")
			local placed = placedSet[entry.uid] == true
			c.badge.Visible = placed
			for _, ch in ipairs(c.holder:GetDescendants()) do
				if ch:IsA("GuiObject") then ch.Transparency = placed and 0.55 or 0 end
			end
		else
			c.nameL.Text = ""
			c.stroke.Color = P.Outline
			c.badge.Visible = false
		end
		-- selection highlight
		local isSel = entry and selectedUid == entry.uid
		c.stroke.Thickness = isSel and 4 or Theme.Dims.StrokeThin
		if isSel then c.stroke.Color = P.Gold end
	end
end

function HotbarController.selectIndex(i: number)
	local uid = uidByIndex[i]
	if uid and not placedSet[uid] then
		selectedUid = uid
		refresh()
	end
end

function HotbarController.select(uid: string)
	-- only if owned and not placed
	for i, u in pairs(uidByIndex) do
		if u == uid and not placedSet[uid] then selectedUid = uid; refresh(); return end
	end
end

function HotbarController.getSelected(): string?
	if selectedUid and not placedSet[selectedUid] then return selectedUid end
	return nil
end

function HotbarController:Start()
	task.spawn(disableDefaultBackpack)
	buildGui()
	refresh()
	Registry.get("StateController").onChanged(refresh)
	UIS.InputBegan:Connect(function(input, gp)
		if gp then return end
		local map = {
			[Enum.KeyCode.One]=1,[Enum.KeyCode.Two]=2,[Enum.KeyCode.Three]=3,[Enum.KeyCode.Four]=4,
			[Enum.KeyCode.Five]=5,[Enum.KeyCode.Six]=6,[Enum.KeyCode.Seven]=7,[Enum.KeyCode.Eight]=8,
			[Enum.KeyCode.Nine]=9,[Enum.KeyCode.Zero]=10,
		}
		local idx = map[input.KeyCode]
		if idx then HotbarController.selectIndex(idx) end
	end)
end

return HotbarController
```

- [ ] **Step 2: Verify hotbar builds + backpack disabled.** Start Play, `get_console_output` → no error. Run `execute_luau` (Client):

```lua
local Players = game:GetService("Players")
local sg = game:GetService("StarterGui")
local hb = Players.LocalPlayer.PlayerGui:FindFirstChild("Hotbar")
local cells = hb and hb.Bar:GetChildren() or {}
return ("Hotbar=%s cells=%d backpackEnabled=%s"):format(hb and "Y" or "N", #cells, tostring(sg:GetCoreGuiEnabled(Enum.CoreGuiType.Backpack)))
```

Expected: `Hotbar=Y`, cells ≥ 10 (incl. UIListLayout), `backpackEnabled=false`. `screen_capture` → bottom hotbar visible with the starter claw thumbnail in slot 1; pressing 1 highlights it gold.

- [ ] **Step 3: Persist** — Stop, **Ctrl+S**.

---

### Task 4: `PlacementController` — client place trigger via hotbar selection

**Files:**
- Create (Studio): `StarterPlayer.StarterPlayerScripts.Client.Controllers.PlacementController` (ModuleScript)

**Interfaces:**
- Consumes: `ProximityPromptService.PromptTriggered`/`PromptShown`, prompt attributes `Kind`/`SlotId` (Task 2), `Registry.controllers["HotbarController"].getSelected()`, `Net.request("placeUFO", {...})`, `Registry.get("StateController")`, `UFOCatchers.get`.
- Produces: nothing consumed by others.

- [ ] **Step 1: Create the module:**

```lua
-- PlacementController.luau — E on an empty slot places the hotbar-selected claw (server validates).
local PPS = game:GetService("ProximityPromptService")
local RS = game:GetService("ReplicatedStorage")

local ClientRoot = script.Parent.Parent
local Registry = require(ClientRoot.Registry)
local Net = require(RS.Shared.Net.Net)
local UFOCatchers = require(RS.Shared.Config.UFOCatchers)

local PlacementController = {}

local function selectedName(): string?
	local hb = Registry.controllers["HotbarController"]
	local uid = hb and hb.getSelected()
	if not uid then return nil end
	local st = Registry.get("StateController").get()
	local rec = st and st.ufos and st.ufos[uid]
	local def = rec and UFOCatchers.get(rec.defId)
	return def and def.name or "Pince"
end

function PlacementController:Start()
	-- Keep the place prompt's ObjectText showing the selected claw.
	PPS.PromptShown:Connect(function(prompt)
		if prompt:GetAttribute("Kind") ~= "place" then return end
		local nm = selectedName()
		prompt.ObjectText = nm and ("Pince : " .. nm) or "Sélectionne une pince"
	end)

	PPS.PromptTriggered:Connect(function(prompt)
		if prompt:GetAttribute("Kind") ~= "place" then return end
		local slotId = prompt:GetAttribute("SlotId")
		local hb = Registry.controllers["HotbarController"]
		local uid = hb and hb.getSelected()
		if not uid then
			Net.sendEvent_local = nil -- noop guard
			Registry.get("StateController") -- ensure loaded
			Net.fireNotify = nil
			return PlacementController._notify("Sélectionne une pince dans la barre (1-0).")
		end
		Net.request("placeUFO", { slotId = slotId, uid = uid })
	end)
end

-- Minimal local toast via the existing notify event path if present; else print.
function PlacementController._notify(text: string)
	local ok = pcall(function() Net.sendEvent_to_self("notify", { text = text, kind = "warn" }) end)
	if not ok then print("[Placement] " .. text) end
end

return PlacementController
```

  NOTE: the `_notify` fallback above is defensive; if the project exposes a client toast (check `script_search "notify"` for a client handler), call it directly instead and delete the `_notify` stub. Replace the `if not uid then ... end` body with the real toast call once identified. **Before implementing, run `script_grep "onEvent(\"notify\""` to find the client notify renderer and use it; do not ship the `Net.sendEvent_local`/`fireNotify` noop lines — they are placeholders to be replaced by the real toast call.** Minimal acceptable version if no toast helper is found:

```lua
		if not uid then return end
		Net.request("placeUFO", { slotId = slotId, uid = uid })
```

- [ ] **Step 2: Verify placement end-to-end.** Start Play. Run `execute_luau` (Client) to confirm a free claw + empty slot exist, then simulate the request the prompt would send:

```lua
local RS = game:GetService("ReplicatedStorage")
local Registry = require(game.Players.LocalPlayer.PlayerScripts.Client.Registry)
local Net = require(RS.Shared.Net.Net)
local st = Registry.get("StateController").get()
-- find a free uid + an empty unlocked slot
local placed = {}
for _, sd in pairs(st.plot.slots) do if sd.ufoUid then placed[sd.ufoUid]=true end end
local freeUid; for uid in pairs(st.ufos) do if not placed[uid] then freeUid=uid break end end
local emptySlot; for sid, sd in pairs(st.plot.slots) do if sd.unlocked and not sd.ufoUid then emptySlot=sid break end end
Registry.controllers["HotbarController"].select(freeUid)
local res = Net.request("placeUFO", { slotId = emptySlot, uid = freeUid })
task.wait(0.4)
local st2 = Registry.get("StateController").get()
return ("placed uid=%s into %s -> slot now=%s"):format(tostring(freeUid), tostring(emptySlot), tostring(st2.plot.slots[emptySlot].ufoUid))
```

Expected: `slot now=<freeUid>` (placement succeeded), no console error. Then physically: select a claw (1-0), walk to an empty slot, confirm the prompt reads "Pince : <name>" and holding E places it; verify distance feels ~18 studs (activates farther than before). `screen_capture` for the prompt text.

- [ ] **Step 3: Persist** — Stop, **Ctrl+S**.

---

### Task 5: `InventoryController` — panel (Tout / Ferraille / Pinces + search + grid)

**Files:**
- Create (Studio): `StarterPlayer.StarterPlayerScripts.Client.Controllers.InventoryController` (ModuleScript)

**Interfaces:**
- Consumes: `Theme`, `StateController`, `Registry.controllers["ClawPreview"]`/`["HotbarController"]`, `Shared.Config.{LootTable,UFOCatchers,Rarities,Pricing}`.
- Produces: `InventoryController.toggle()` / `.open()` / `.close()` (for an optional HUD button rebind).

- [ ] **Step 1: Create the module.** Uses `Theme.Panel` for the shell, a left sidebar, a search box, and a `ScrollingFrame` + `UIGridLayout` grid. Render functions per tab.

```lua
-- InventoryController.luau — Grow-a-Garden-style inventory: sidebar tabs + search + grid.
local Players = game:GetService("Players")
local UIS = game:GetService("UserInputService")
local RS = game:GetService("ReplicatedStorage")

local ClientRoot = script.Parent.Parent
local Registry = require(ClientRoot.Registry)
local Theme = require(RS.UI.Theme)
local P = Theme.Palette
local LootTable = require(RS.Shared.Config.LootTable)
local UFOCatchers = require(RS.Shared.Config.UFOCatchers)
local Rarities = require(RS.Shared.Config.Rarities)
local Pricing = require(RS.Shared.Config.Pricing)

local TOGGLE_KEY = Enum.KeyCode.Tab

local InventoryController = {}
local gui, panel, grid, searchBox, sidebarBtns
local currentTab = "Tout"
local rarityFilter = "all"
local searchText = ""
local visible = false

local TABS = { "Tout", "Ferraille", "Pinces" }

local function norm(s: string): string
	return string.lower(s or "")
end
local function rarityColor(rar: string): Color3
	local rd = Rarities.get(rar)
	return rd and Color3.new(rd.color[1], rd.color[2], rd.color[3]) or P.Cyan
end

-- ----- card builders -----
local function scrapCard(stack)
	local def = LootTable.get(stack.defId)
	local card = Instance.new("Frame")
	card.Size = UDim2.fromOffset(112, 112)
	card.BackgroundColor3 = Theme.darken(rarityColor(stack.rarity), 0.45)
	Theme.Corner(card, UDim.new(0, 10)); Theme.Stroke(card, rarityColor(stack.rarity), Theme.Dims.StrokeThin)
	local rd = Rarities.get(stack.rarity)
	local emoji = Instance.new("TextLabel")
	emoji.BackgroundTransparency = 1; emoji.Size = UDim2.new(1,0,0.45,0); emoji.Position = UDim2.fromScale(0,0.06)
	emoji.Font = Enum.Font.SourceSansBold; emoji.Text = (rd and rd.icon) or "⬛"; emoji.TextScaled = true; emoji.Parent = card
	local nameL = Instance.new("TextLabel")
	nameL.BackgroundTransparency = 1; nameL.Size = UDim2.new(1,-8,0,18); nameL.Position = UDim2.fromScale(0.5,0.56)
	nameL.AnchorPoint = Vector2.new(0.5,0); nameL.Font = Theme.Font.Body; nameL.Text = (def and def.name) or stack.defId
	nameL.TextColor3 = P.White; nameL.TextScaled = true; nameL.Parent = card
	Theme.TextStroke(nameL, 1)
	local nc = Instance.new("UITextSizeConstraint"); nc.MaxTextSize = 13; nc.Parent = nameL
	local val = Instance.new("TextLabel")
	val.BackgroundTransparency = 1; val.Size = UDim2.new(1,-8,0,16); val.AnchorPoint = Vector2.new(0.5,1)
	val.Position = UDim2.new(0.5,0,1,-3); val.Font = Theme.Font.Title
	val.Text = "$" .. tostring(Pricing.valueOf(stack.defId, stack.rarity, stack.modifier) * stack.count)
	val.TextColor3 = P.Gold; val.TextScaled = true; val.Parent = card
	Theme.TextStroke(val, 1)
	local vc = Instance.new("UITextSizeConstraint"); vc.MaxTextSize = 15; vc.Parent = val
	local count = Instance.new("TextLabel")
	count.BackgroundColor3 = P.Outline; count.BackgroundTransparency = 0.2; count.Size = UDim2.fromOffset(34,18)
	count.AnchorPoint = Vector2.new(1,0); count.Position = UDim2.new(1,-3,0,3); count.Font = Theme.Font.Title
	count.Text = "x" .. tostring(stack.count); count.TextColor3 = P.White; count.TextScaled = true; count.Parent = count.Parent
	count.Parent = card; Theme.Corner(count, UDim.new(1,0))
	if stack.locked then
		local lock = Instance.new("TextLabel"); lock.BackgroundTransparency = 1; lock.Size = UDim2.fromOffset(18,18)
		lock.Position = UDim2.fromOffset(3,3); lock.Font = Enum.Font.SourceSansBold; lock.Text = "🔒"; lock.TextScaled = true; lock.Parent = card
	end
	return card
end

local function clawCard(uid, rec, placedBy)
	local def = UFOCatchers.get(rec.defId)
	local card = Instance.new("TextButton")
	card.AutoButtonColor = false; card.Text = ""
	card.Size = UDim2.fromOffset(112, 112); card.BackgroundColor3 = P.PanelBg
	Theme.Corner(card, UDim.new(0,10)); Theme.Stroke(card, rarityColor(def and def.rarity or "common"), Theme.Dims.StrokeThin)
	local holder = Instance.new("Frame"); holder.BackgroundTransparency = 1
	holder.Size = UDim2.new(1,-8,0.62,0); holder.Position = UDim2.fromOffset(4,4); holder.Parent = card
	Registry.controllers["ClawPreview"].make(rec.defId, rec.prestige, holder)
	local nameL = Instance.new("TextLabel"); nameL.BackgroundTransparency = 1
	nameL.Size = UDim2.new(1,-6,0,16); nameL.Position = UDim2.fromScale(0.5,0.64); nameL.AnchorPoint = Vector2.new(0.5,0)
	nameL.Font = Theme.Font.Body; nameL.Text = (def and def.name) or rec.defId; nameL.TextColor3 = P.White
	nameL.TextScaled = true; nameL.Parent = card; Theme.TextStroke(nameL,1)
	local nc = Instance.new("UITextSizeConstraint"); nc.MaxTextSize = 12; nc.Parent = nameL
	local rankL = Instance.new("TextLabel"); rankL.BackgroundColor3 = P.Gold; rankL.Size = UDim2.fromOffset(48,16)
	rankL.AnchorPoint = Vector2.new(0.5,1); rankL.Position = UDim2.new(0.5,0,1,-3); rankL.Font = Theme.Font.Title
	rankL.Text = "RANG " .. ((def and def.roman) or "I"); rankL.TextColor3 = Theme.darken(P.Gold,0.72)
	rankL.TextScaled = true; rankL.Parent = card; Theme.Corner(rankL, UDim.new(0,6))
	local rc = Instance.new("UITextSizeConstraint"); rc.MaxTextSize = 10; rc.Parent = rankL
	if placedBy then
		local b = Instance.new("TextLabel"); b.BackgroundColor3 = P.Outline; b.BackgroundTransparency = 0.25
		b.Size = UDim2.new(1,0,0,16); b.AnchorPoint = Vector2.new(0.5,0); b.Position = UDim2.fromOffset(0,3)
		b.Font = Theme.Font.Title; b.Text = "POSÉE"; b.TextColor3 = P.Gold; b.TextScaled = true; b.ZIndex=5; b.Parent = card
		local bc = Instance.new("UITextSizeConstraint"); bc.MaxTextSize=10; bc.Parent=b
	end
	card.Activated:Connect(function()
		Registry.controllers["HotbarController"].select(uid)
	end)
	return card
end
```

  (continue the module in Step 2 — the render/layout half)

- [ ] **Step 2: Add the shell, tabs, search, render, toggle** (second `multi_edit` appending before `return InventoryController`; or include in Step 1's single create). Append:

```lua
local function clearGrid()
	for _, ch in ipairs(grid:GetChildren()) do
		if ch:IsA("GuiObject") then ch:Destroy() end
	end
end

local function passSearch(name: string): boolean
	return searchText == "" or string.find(norm(name), norm(searchText), 1, true) ~= nil
end

local function render()
	clearGrid()
	local st = Registry.get("StateController").get(); if not st then return end
	local placedBy = {}
	for sid, sd in pairs(st.plot.slots or {}) do if sd.ufoUid then placedBy[sd.ufoUid] = sid end end

	if currentTab == "Pinces" or currentTab == "Tout" then
		for uid, rec in pairs(st.ufos or {}) do
			local def = UFOCatchers.get(rec.defId)
			local nm = (def and def.name) or rec.defId
			local okRar = (rarityFilter == "all") or (def and def.rarity == rarityFilter)
			if passSearch(nm) and okRar then clawCard(uid, rec, placedBy[uid]).Parent = grid end
		end
	end
	if currentTab == "Ferraille" or currentTab == "Tout" then
		for _, stack in pairs(st.inventory or {}) do
			local def = LootTable.get(stack.defId)
			local nm = (def and def.name) or stack.defId
			local okRar = (rarityFilter == "all") or (stack.rarity == rarityFilter)
			if passSearch(nm) and okRar then scrapCard(stack).Parent = grid end
		end
	end
end

local function setTab(t)
	currentTab = t
	for name, btn in pairs(sidebarBtns) do
		btn.BackgroundColor3 = (name == t) and P.TitleBar or P.PanelInner
	end
	render()
end

local function buildGui()
	local pg = Players.LocalPlayer:WaitForChild("PlayerGui")
	gui = Instance.new("ScreenGui")
	gui.Name = "InventoryPanel"; gui.ResetOnSpawn = false; gui.IgnoreGuiInset = true
	gui.DisplayOrder = 9; gui.Enabled = false; gui.Parent = pg

	local overlay = Instance.new("TextButton")
	overlay.Text = ""; overlay.AutoButtonColor = false; overlay.Size = UDim2.fromScale(1,1)
	overlay.BackgroundColor3 = Color3.new(0,0,0); overlay.BackgroundTransparency = 0.45; overlay.Parent = gui
	overlay.Activated:Connect(function() InventoryController.close() end)

	panel = Instance.new("Frame")
	panel.AnchorPoint = Vector2.new(0.5,0.5); panel.Position = UDim2.fromScale(0.5,0.5)
	panel.Size = UDim2.fromScale(0.74, 0.74); panel.BackgroundColor3 = P.PanelBg; panel.Parent = gui
	Theme.Corner(panel, Theme.Dims.Corner); Theme.Stroke(panel, P.Outline, Theme.Dims.Stroke)

	-- sidebar
	sidebarBtns = {}
	local side = Instance.new("Frame"); side.BackgroundTransparency = 1
	side.Size = UDim2.new(0, 150, 1, -20); side.Position = UDim2.fromOffset(10,10); side.Parent = panel
	local sl = Instance.new("UIListLayout"); sl.Padding = UDim.new(0,8); sl.Parent = side
	for _, t in ipairs(TABS) do
		local b = Instance.new("TextButton"); b.AutoButtonColor = false; b.Size = UDim2.new(1,0,0,64)
		b.BackgroundColor3 = P.PanelInner; b.Font = Theme.Font.Title; b.Text = t
		b.TextColor3 = P.White; b.TextScaled = true; b.Parent = side
		Theme.Corner(b, UDim.new(0,10)); Theme.Stroke(b, P.Outline, Theme.Dims.StrokeThin); Theme.TextStroke(b,2)
		local tc = Instance.new("UITextSizeConstraint"); tc.MaxTextSize = 20; tc.Parent = b
		b.Activated:Connect(function() setTab(t) end)
		sidebarBtns[t] = b
	end

	-- search box (top-right of content)
	searchBox = Instance.new("TextBox")
	searchBox.Size = UDim2.new(0, 260, 0, 36); searchBox.AnchorPoint = Vector2.new(1,0)
	searchBox.Position = UDim2.new(1,-16,0,12); searchBox.BackgroundColor3 = P.PanelInner
	searchBox.Font = Theme.Font.Body; searchBox.PlaceholderText = "Rechercher…"; searchBox.Text = ""
	searchBox.TextColor3 = P.White; searchBox.TextScaled = true; searchBox.ClearTextOnFocus = false; searchBox.Parent = panel
	Theme.Corner(searchBox, UDim.new(0,10)); Theme.Stroke(searchBox, P.Outline, Theme.Dims.StrokeThin)
	searchBox:GetPropertyChangedSignal("Text"):Connect(function() searchText = searchBox.Text; render() end)

	-- rarity filter row (only meaningful on Tout; visible always, simple)
	local filterRow = Instance.new("Frame"); filterRow.BackgroundTransparency = 1
	filterRow.Size = UDim2.new(1, -440, 0, 28); filterRow.Position = UDim2.fromOffset(170, 16); filterRow.Parent = panel
	local fl = Instance.new("UIListLayout"); fl.FillDirection = Enum.FillDirection.Horizontal
	fl.Padding = UDim.new(0,4); fl.Parent = filterRow
	local function chip(label, key)
		local c = Instance.new("TextButton"); c.AutoButtonColor=false; c.Size = UDim2.fromOffset(58,26)
		c.BackgroundColor3 = (key=="all") and P.TitleBar or rarityColor(key); c.Font = Theme.Font.Body
		c.Text = label; c.TextColor3 = P.White; c.TextScaled = true; c.Parent = filterRow
		Theme.Corner(c, UDim.new(0,8)); local cc=Instance.new("UITextSizeConstraint"); cc.MaxTextSize=11; cc.Parent=c
		c.Activated:Connect(function() rarityFilter = key; render() end)
	end
	chip("TOUT","all")
	for _, rd in ipairs(Rarities.list) do chip(string.upper(string.sub(rd.name,1,4)), rd.id) end

	-- grid
	local scroll = Instance.new("ScrollingFrame")
	scroll.BackgroundTransparency = 1; scroll.BorderSizePixel = 0; scroll.ScrollBarThickness = 8
	scroll.Size = UDim2.new(1, -170, 1, -64); scroll.Position = UDim2.fromOffset(160, 56)
	scroll.CanvasSize = UDim2.new(); scroll.AutomaticCanvasSize = Enum.AutomaticSize.Y; scroll.Parent = panel
	local g = Instance.new("UIGridLayout"); g.CellSize = UDim2.fromOffset(112,112)
	g.CellPadding = UDim2.fromOffset(10,10); g.SortOrder = Enum.SortOrder.LayoutOrder; g.Parent = scroll
	local gp = Instance.new("UIPadding"); gp.PaddingLeft = UDim.new(0,12); gp.PaddingTop = UDim.new(0,12); gp.Parent = scroll
	grid = scroll
end

function InventoryController.open()
	visible = true; gui.Enabled = true; setTab(currentTab)
end
function InventoryController.close()
	visible = false; gui.Enabled = false
end
function InventoryController.toggle()
	if visible then InventoryController.close() else InventoryController.open() end
end

function InventoryController:Start()
	buildGui()
	Registry.get("StateController").onChanged(function() if visible then render() end end)
	UIS.InputBegan:Connect(function(input, gp)
		if gp then return end
		if input.KeyCode == TOGGLE_KEY then InventoryController.toggle()
		elseif input.KeyCode == Enum.KeyCode.Escape and visible then InventoryController.close() end
	end)
end

return InventoryController
```

  NOTE on the `scrapCard` count label: the line `count.Parent = count.Parent` in Task-5 Step-1 is a typo guard — when implementing, create the `count` TextLabel, then set `count.Parent = card` once (remove the self-assignment line). Verify the final card has exactly one count badge.

- [ ] **Step 3: Verify panel.** Start Play. Run `execute_luau` (Client):

```lua
local Registry = require(game.Players.LocalPlayer.PlayerScripts.Client.Registry)
local inv = Registry.controllers["InventoryController"]
inv.open()
task.wait(0.2)
local gui = game.Players.LocalPlayer.PlayerGui:FindFirstChild("InventoryPanel")
local grid = gui and gui:FindFirstChildWhichIsA("Frame") -- panel
return ("panel=%s enabled=%s"):format(gui and "Y" or "N", tostring(gui and gui.Enabled))
```

Expected: `panel=Y enabled=true`. `screen_capture` → sidebar (Tout/Ferraille/Pinces), search top-right, grid of cards (claw thumbnails + scrap cards). Click each tab + type in search; press Tab/Escape to toggle.

- [ ] **Step 4: Persist** — Stop, **Ctrl+S**.

---

### Task 6: Remove the old inventory UI

**Files:**
- Modify (Studio): `StarterGui.MainHUD.UIController` (LocalScript) — remove `populateInventory` + `InventaireBtn` wiring; hide the INVENT. button.
- Delete (Studio): `StarterPlayer.StarterPlayerScripts.Client.Controllers.InventoryUIController` (legacy ModuleScript).

**Interfaces:** none produced.

- [ ] **Step 1: Unwire + hide the old button.** In `UIController`, find `wire("InventaireBtn", function() open("Inventaire") end)` and the INVENT. button. Replace the wire line to hide the button instead (so the sidebar slot disappears) — edit:
  - old: `	wire("InventaireBtn", function() open("Inventaire") end)`
  - new: `	do local b = sidebar and sidebar:FindFirstChild("InventaireBtn"); if b then b.Visible = false end end`

  (Locate the exact `sidebar` reference name first with `script_read`; if the button is reached differently, hide it via its actual path. Confirm with `script_grep "InventaireBtn"` afterward → only the hide line remains.)

- [ ] **Step 2: Remove the `populateInventory` body.** Find `local function populateInventory()` … its matching `end`, and the dispatch that calls it (in `populate(name)`). Replace the function body with a no-op and drop the `Inventaire` case from `populate` so it is never opened:
  - In `populate(name)`, remove/!skip the `elseif name == "Inventaire" then populateInventory()` branch.
  - Replace `local function populateInventory() … end` with `local function populateInventory() end` (empty), OR delete it and its call. Verify `script_grep "populateInventory"` shows no remaining caller.

- [ ] **Step 3: Delete the legacy controller.** Remove the `InventoryUIController` ModuleScript so the bootstrap no longer loads it:

```lua
-- run in execute_luau datamodel "Edit"
local m = game.StarterPlayer.StarterPlayerScripts.Client.Controllers:FindFirstChild("InventoryUIController")
if m then m:Destroy() end
return m and "destroyed" or "not found"
```

- [ ] **Step 4: Verify no regressions.** Start Play, `get_console_output` → `[Client] ready (N controllers)` with no error and N reflecting the removed legacy + 4 new controllers. Confirm the old INVENT. menu no longer opens (the button is hidden); the new panel opens via Tab; hotbar + placement still work. `script_grep "Inventaire\b"` → no opener remains besides inert leftovers.

- [ ] **Step 5: Persist** — Stop, **Ctrl+S**.

---

## Self-Review

**Spec coverage:**
- A. InventoryController (tabs/search/grid) → Task 5. ✓
- B. HotbarController (bottom bar, 1-0 select, disable backpack) → Task 3. ✓
- C. Placement rework (placeUFO remote, client-driven, ObjectText) → Tasks 2 + 4. ✓
- D. Distances 10→18 → Task 2. ✓
- E. Cleanup (menu inventory, INVENT. button, legacy controller) → Task 6. ✓
- Shared claw thumbnails → Task 1 (ClawPreview), consumed by Tasks 3 & 5. ✓

**Placeholder scan:** The only soft spots are the `PlacementController` notify fallback (Task 4 Step 1) — flagged explicitly with a concrete minimal replacement (`if not uid then return end`) and an instruction to use the real notify handler found via `script_grep`. No other TBD/TODO. The `scrapCard` count self-assignment + `populateInventory` exact line are called out as implementer notes with the corrective action.

**Type consistency:** `HotbarController.getSelected()/select(uid)/selectIndex(i)` used consistently across Tasks 3/4/5. `ClawPreview.make(defId, prestige, parent)` consistent in Tasks 1/3/5. `Net.request("placeUFO", {slotId, uid})` matches the server handler payload guard in Task 2. Prompt attributes `Kind`/`SlotId` written in Task 2, read in Task 4. `Pricing.valueOf(defId, rarity, modifier)`, `LootTable.get`, `UFOCatchers.get`, `Rarities.get/.list` match the explored APIs.

## Verification (full feature)
1. Play, no console errors; `[Client] ready` lists the 4 new controllers, no legacy.
2. Hotbar bottom-visible, Roblox backpack gone; 1-0 + click select (gold highlight); placed claws greyed + "POSÉE".
3. Tab opens the panel; Tout/Ferraille/Pinces + rarity chips + search filter correctly; claw thumbnails + scrap cards render; clicking a Pince card selects it in the hotbar.
4. Select a claw → empty slot prompt reads "Pince : <name>" → E places that exact claw (server `slotData.ufoUid` set); E on filled retrieves; works at ~18 studs; R upgrade unchanged.
5. `screen_capture` comparisons to the reference for panel + hotbar.
6. **Ctrl+S** to persist `build.rbxlx`.
