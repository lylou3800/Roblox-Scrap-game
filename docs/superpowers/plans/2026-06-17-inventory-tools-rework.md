# Inventaire à base de Tools — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use `- [ ]` checkboxes. NO git/test-framework — edits are applied LIVE in Roblox Studio via MCP (Edit DM), persisted by Ctrl+S.

**Goal:** Turn every inventory item (pinces + ferraille) into real Roblox `Tool`s in the Backpack, replace the custom inventory/hotbar with a Tool-driven styled backpack (categories), and place a claw by equipping its Tool and pressing E at a slot (placed → Tool removed; retrieve → Tool returns).

**Architecture:** Server `ToolService` reconciles Backpack Tools to mirror `data` (unplaced pinces + ferraille stacks), hooked into `DataService.replicate` + `CharacterAdded`. Client `BackpackController` (replaces `HotbarController`+`InventoryController`) renders/equips those Tools with category tabs. `PlacementController` reads the equipped Tool instead of a custom selection. Reuses `ClawPreview`, the `placeUFO` remote, prompt `Kind`/`SlotId` attrs, and `SLOT_PROMPT_DIST=18`.

**Tech Stack:** Roblox Luau, Tools/Backpack/Humanoid, `ReplicatedStorage.UI.Theme`, `ReplicatedStorage.Shared.ClawModel`/`Config.*`, `Net`.

## Global Constraints

- **Editing workflow:** ALL edits via Roblox Studio MCP in the **Edit** DataModel (`multi_edit`/`execute_luau datamodel:"Edit"`). `build.rbxlx` persisted by **Ctrl+S** (Studio owns the file). NO git, NO commits, NO tests. Verify via `execute_luau`/Play/`get_console_output`.
- `multi_edit` may silently no-op — re-verify with `script_grep`/`script_read`. `script_grep` treats `(` `"` as Lua-pattern specials → use plain identifier queries. Large `script_read` dumps to a temp file → Read it in chunks.
- **`execute_luau` runs in an ISOLATED VM** where `Registry.controllers`/`Registry.services` are EMPTY and module upvalues are fresh — verify via real instances (`player.Backpack`, `PlayerGui`, `Character` Tools) and shared remotes (`Net`), NOT by calling controller/service methods.
- Play uses a stale snapshot right after an edit; `multi_edit` needs Edit mode (Stop play first).
- **Style:** `ReplicatedStorage.UI.Theme` only. **Controllers** under `StarterPlayer.StarterPlayerScripts.Client.Controllers` (auto-required, `Registry.controllers[name]`, optional `:Init()`/`:Start()`). **Services** under the server services folder (find an existing one's path via `script_grep "function PlotService.refreshClaw"` → siblings).
- Data: `data.ufos[uid]={defId,level,prestige}`; `data.inventory[key]={defId,rarity,modifier,count,locked}`; slot link `data.plot.slots[slotId].ufoUid`. Value = `Pricing.valueOf(defId,rarity,modifier)`.
- Tool attribute contract (exact): pince → `Kind="pince"`, `UfoUid`, `DefId`, `Prestige`; ferraille → `Kind="ferraille"`, `ItemKey`, `DefId`, `Rarity`, `Count`.
- `TOGGLE_KEY = Enum.KeyCode.Tab`; `HOTBAR_SLOTS = 10`.

---

### Task 1: Remove the old custom inventory + hotbar

Removes `HotbarController` + `InventoryController` so they don't conflict with the new Tool system. (After this, the native CoreGui backpack re-enables by default — that's intended; we use it to test Tasks 2-3 before building the styled GUI in Task 4. `PlacementController` still references the now-absent `HotbarController` but its calls are nil-guarded, so placement is simply inert until Task 3 — no errors.)

**Files:**
- Delete (Studio): `StarterPlayer.StarterPlayerScripts.Client.Controllers.HotbarController`, `...Controllers.InventoryController`.

**Interfaces:** none produced.

- [ ] **Step 1: Delete both ModuleScripts** via `execute_luau` (datamodel `Edit`):
```lua
local c = game.StarterPlayer.StarterPlayerScripts.Client.Controllers
local a = c:FindFirstChild("HotbarController"); if a then a:Destroy() end
local b = c:FindFirstChild("InventoryController"); if b then b:Destroy() end
return ("hotbar=%s inventory=%s"):format(a and "gone" or "absent", b and "gone" or "absent")
```
- [ ] **Step 2: Verify** `script_grep "HotbarController"` and `script_grep "InventoryController"` → only the (nil-guarded) reference inside `PlacementController` may remain; no other. Start Play, `get_console_output` → `[Client] ready (N controllers)` (N = previous − 2), NO errors. The native Roblox backpack should now be visible (CoreGui re-enabled). Stop play.
- [ ] **Step 3: Persist** — Ctrl+S.

---

### Task 2: Server `ToolService` — mirror data as Backpack Tools

**Files:**
- Create (Studio): a server ModuleScript `ToolService` in the same folder as `PlotService` (find via `script_grep "function PlotService.refreshClaw"` → use its parent path, e.g. `ServerScriptService.Server.Services.ToolService`).
- Modify (Studio): `DataService` (find via `script_grep "function DataService.replicate"`) — add a reconcile hook at the end of `replicate`.

**Interfaces:**
- Consumes: `Registry.get("DataService").get(player)`; `Shared.Config.{UFOCatchers,LootTable,Rarities}`.
- Produces: `ToolService.reconcile(player)`; Backpack Tools with the attribute contract.

- [ ] **Step 1: Create `ToolService`** (`className="ModuleScript"`). Confirm the require path for the server `Registry` by reading the top of `PlotService` (e.g. `local Registry = require(script.Parent.Parent.Registry)` — match it). Full source:

```lua
-- ToolService.luau (server) — mirror data (unplaced pinces + ferraille stacks) as Backpack Tools.
local Players = game:GetService("Players")
local RS = game:GetService("ReplicatedStorage")

local ServerRoot = script.Parent.Parent
local Registry = require(ServerRoot.Registry)
local UFOCatchers = require(RS.Shared.Config.UFOCatchers)
local LootTable = require(RS.Shared.Config.LootTable)
local Rarities = require(RS.Shared.Config.Rarities)

local ToolService = {}

local function rarityColor(rar: string): Color3
	local rd = Rarities.get(rar)
	return rd and Color3.new(rd.color[1], rd.color[2], rd.color[3]) or Color3.fromRGB(200, 205, 215)
end

local function makeHandle(color: Color3): Part
	local h = Instance.new("Part")
	h.Name = "Handle"; h.Size = Vector3.new(1.2, 1.2, 1.2); h.Color = color
	h.Material = Enum.Material.SmoothPlastic; h.CanCollide = false; h.Massless = true
	h.TopSurface = Enum.SurfaceType.Smooth; h.BottomSurface = Enum.SurfaceType.Smooth
	return h
end

local function makePinceTool(uid: string, rec): Tool
	local def = UFOCatchers.get(rec.defId)
	local tool = Instance.new("Tool")
	tool.Name = (def and def.name) or rec.defId
	tool.RequiresHandle = true; tool.CanBeDropped = false
	tool.ToolTip = "Pince — équipe puis E sur un emplacement"
	makeHandle(rarityColor(def and def.rarity or "common")).Parent = tool
	tool:SetAttribute("Kind", "pince")
	tool:SetAttribute("UfoUid", uid)
	tool:SetAttribute("DefId", rec.defId)
	tool:SetAttribute("Prestige", rec.prestige or 0)
	return tool
end

local function makeFerrailleTool(key: string, stack): Tool
	local def = LootTable.get(stack.defId)
	local tool = Instance.new("Tool")
	tool.Name = ((def and def.name) or stack.defId) .. " ×" .. tostring(stack.count)
	tool.RequiresHandle = true; tool.CanBeDropped = false
	tool.ToolTip = "Ferraille"
	makeHandle(rarityColor(stack.rarity)).Parent = tool
	tool:SetAttribute("Kind", "ferraille")
	tool:SetAttribute("ItemKey", key)
	tool:SetAttribute("DefId", stack.defId)
	tool:SetAttribute("Rarity", stack.rarity)
	tool:SetAttribute("Count", stack.count)
	return tool
end

local function existingTools(player: Player): { [string]: Tool }
	local out = {}
	local function scan(container)
		if not container then return end
		for _, ch in ipairs(container:GetChildren()) do
			if ch:IsA("Tool") then
				local kind = ch:GetAttribute("Kind")
				if kind == "pince" then out["p:" .. tostring(ch:GetAttribute("UfoUid"))] = ch
				elseif kind == "ferraille" then out["f:" .. tostring(ch:GetAttribute("ItemKey"))] = ch end
			end
		end
	end
	scan(player:FindFirstChildOfClass("Backpack"))
	scan(player.Character)
	return out
end

function ToolService.reconcile(player: Player)
	local data = Registry.get("DataService").get(player)
	if not data then return end
	local backpack = player:FindFirstChildOfClass("Backpack")
	if not backpack then return end

	local placed = {}
	for _, sd in pairs(data.plot.slots) do if sd.ufoUid then placed[sd.ufoUid] = true end end
	local desired = {}
	for uid, rec in pairs(data.ufos) do
		if not placed[uid] then desired["p:" .. uid] = { kind = "pince", uid = uid, rec = rec } end
	end
	for key, stack in pairs(data.inventory) do
		if (stack.count or 0) > 0 then desired["f:" .. key] = { kind = "ferraille", key = key, stack = stack } end
	end

	local existing = existingTools(player)
	for id, tool in pairs(existing) do
		if not desired[id] then tool:Destroy() end
	end
	for id, d in pairs(desired) do
		local tool = existing[id]
		if not tool then
			if d.kind == "pince" then makePinceTool(d.uid, d.rec).Parent = backpack
			else makeFerrailleTool(d.key, d.stack).Parent = backpack end
		elseif d.kind == "ferraille" then
			local def = LootTable.get(d.stack.defId)
			local newName = ((def and def.name) or d.stack.defId) .. " ×" .. tostring(d.stack.count)
			if tool.Name ~= newName then tool.Name = newName end
			if tool:GetAttribute("Count") ~= d.stack.count then tool:SetAttribute("Count", d.stack.count) end
		else
			if tool:GetAttribute("Prestige") ~= (d.rec.prestige or 0) then tool:SetAttribute("Prestige", d.rec.prestige or 0) end
		end
	end
end

function ToolService:Start()
	local function hook(p: Player)
		p.CharacterAdded:Connect(function()
			task.wait(0.3)
			ToolService.reconcile(p)
		end)
		if p.Character then ToolService.reconcile(p) end
	end
	for _, p in ipairs(Players:GetPlayers()) do hook(p) end
	Players.PlayerAdded:Connect(hook)
end

return ToolService
```

- [ ] **Step 2: Hook reconcile into `DataService.replicate`.** `script_read` the `function DataService.replicate(player ...)` body to get its exact tail (the line(s) before its closing `end`, e.g. the `Net.pushState(...)` call). Add, immediately after the push/at the end of the function body, a guarded reconcile (use the server Registry accessor that DataService already has — confirm it requires `Registry`; if not, require it). Exact insert (adapt to the real last line):
```lua
	-- mirror inventory/pinces into the player's Backpack as Tools
	local ToolService = Registry.services and Registry.services["ToolService"]
	if ToolService then ToolService.reconcile(player) end
```
If `DataService` does not already `require` the server `Registry`, add `local Registry = require(script.Parent.Parent.Registry)` near its top (match the path used by sibling services). Verify with `script_grep "ToolService.reconcile"` → match inside DataService.

- [ ] **Step 3: Verify Tools mirror data.** Start Play, wait ~3s, `get_console_output` → no errors, `[Server] ready`, `[Client] ready`. Then `execute_luau` (datamodel `Client`) inspecting the real Backpack:
```lua
local p = game.Players.LocalPlayer
local bp = p:FindFirstChildOfClass("Backpack")
local pinces, ferr = 0, 0
for _, t in ipairs(bp:GetChildren()) do
	if t:IsA("Tool") then
		if t:GetAttribute("Kind")=="pince" then pinces+=1 elseif t:GetAttribute("Kind")=="ferraille" then ferr+=1 end
	end
end
return ("backpackTools pinces=%d ferraille=%d total=%d"):format(pinces, ferr, #bp:GetChildren())
```
Expect: `ferraille>=1` (player has scrap from auto-catches); `pinces` = owned-but-unplaced count (the starter is auto-placed in s1 → likely `pinces=0` until you unequip it; that's correct — a placed pince has NO Tool). Confirm: the placed starter has no pince Tool. Stop play.

- [ ] **Step 4: Persist** — Ctrl+S.

---

### Task 3: `PlacementController` — place the EQUIPPED pince

**Files:**
- Modify (Studio): `StarterPlayer.StarterPlayerScripts.Client.Controllers.PlacementController`.

**Interfaces:**
- Consumes: equipped Tool on `player.Character` (attr `Kind`/`UfoUid`), `Net.request("placeUFO", {slotId, uid})`, prompt attrs `Kind`/`SlotId`.
- Produces: none.

- [ ] **Step 1: Rewrite the controller** to read the equipped Tool. `script_read` the current file, then replace its whole body (between the requires and `return PlacementController`) with:
```lua
local Players = game:GetService("Players")
local function equippedPince()
	local char = Players.LocalPlayer.Character
	local tool = char and char:FindFirstChildOfClass("Tool")
	if tool and tool:GetAttribute("Kind") == "pince" then return tool end
	return nil
end

function PlacementController:Start()
	PPS.PromptShown:Connect(function(prompt)
		if prompt:GetAttribute("Kind") ~= "place" then return end
		local t = equippedPince()
		prompt.ObjectText = t and ("Pince : " .. t.Name) or "Équipe une pince"
	end)
	PPS.PromptTriggered:Connect(function(prompt)
		if prompt:GetAttribute("Kind") ~= "place" then return end
		local slotId = prompt:GetAttribute("SlotId")
		local t = equippedPince()
		if not t then return end
		Net.request("placeUFO", { slotId = slotId, uid = t:GetAttribute("UfoUid") })
	end)
end
```
Keep the existing `local PPS = game:GetService("ProximityPromptService")`, `local Net = require(RS.Shared.Net.Net)` (and `RS`) requires at the top — if the old file referenced `Registry`/`UFOCatchers`/`selectedName`, remove those now-unused requires/helpers. Verify with `script_grep "equippedPince"` and ensure NO remaining reference to `HotbarController` or `getSelected` in this file.

- [ ] **Step 2: Verify the full place loop via the NATIVE backpack.** Start Play. The native backpack is active (Task 1). Manually: equip a pince (if the only pince is placed in s1, first walk to s1 and press E to retrieve it → its Tool appears in the backpack → equip it from the hotbar), walk to an empty unlocked slot, confirm the E prompt reads `Pince : <name>`, hold E → the claw is placed and the Tool leaves your hand/backpack. Then verify programmatically with `execute_luau` (Client) that a known free pince can be placed end-to-end:
```lua
local RS = game:GetService("ReplicatedStorage"); local Net = require(RS.Shared.Net.Net)
local st = Net.request("getState")
local placed = {}; for _, sd in pairs(st.plot.slots) do if sd.ufoUid then placed[sd.ufoUid]=true end end
local freeUid; for uid in pairs(st.ufos) do if not placed[uid] then freeUid=uid break end end
local emptySlot; for sid, sd in pairs(st.plot.slots) do if sd.unlocked and not sd.ufoUid then emptySlot=sid break end end
if not (freeUid and emptySlot) then return "need a free pince + empty slot (retrieve starter first): freeUid="..tostring(freeUid).." empty="..tostring(emptySlot) end
Net.request("placeUFO", { slotId = emptySlot, uid = freeUid })
task.wait(0.4)
local st2 = Net.request("getState")
local bp = game.Players.LocalPlayer:FindFirstChildOfClass("Backpack")
local stillHasTool = false
for _, t in ipairs(bp:GetChildren()) do if t:GetAttribute("UfoUid")==freeUid then stillHasTool=true end end
return ("slot now=%s pinceToolGone=%s"):format(tostring(st2.plot.slots[emptySlot].ufoUid), tostring(not stillHasTool))
```
Expect: `slot now=<freeUid> pinceToolGone=true` (placed + its Tool removed by reconcile). Stop play.

- [ ] **Step 3: Persist** — Ctrl+S.

---

### Task 4: `BackpackController` — styled Tool-driven backpack (replaces native)

**Files:**
- Create (Studio): `StarterPlayer.StarterPlayerScripts.Client.Controllers.BackpackController`.

**Interfaces:**
- Consumes: `player.Backpack`/`Character` Tools, `Humanoid:EquipTool/UnequipTools`, `Registry.controllers["ClawPreview"].make`, `Theme`, `Shared.Config.{Rarities,LootTable,Pricing,UFOCatchers}`.
- Produces: none (self-contained UI).

- [ ] **Step 1: Create the module** (full source):
```lua
-- BackpackController.luau — custom backpack replacing CoreGui: hotbar + categorized panel, Tool-driven.
local Players = game:GetService("Players")
local UIS = game:GetService("UserInputService")
local StarterGui = game:GetService("StarterGui")
local RS = game:GetService("ReplicatedStorage")

local ClientRoot = script.Parent.Parent
local Registry = require(ClientRoot.Registry)
local Theme = require(RS.UI.Theme)
local P = Theme.Palette
local Rarities = require(RS.Shared.Config.Rarities)

local TOGGLE_KEY = Enum.KeyCode.Tab
local HOTBAR_SLOTS = 10

local BackpackController = {}
local player = Players.LocalPlayer
local gui, hotbarBar, panel, grid, searchBox, sidebarBtns
local hotCells = {}
local currentTab, searchText, panelOpen = "Pinces", "", false

local function rarityColor(rar)
	local rd = Rarities.get(rar)
	return rd and Color3.new(rd.color[1], rd.color[2], rd.color[3]) or P.Cyan
end

local function disableNative()
	for _ = 1, 8 do
		local ok = pcall(function() StarterGui:SetCoreGuiEnabled(Enum.CoreGuiType.Backpack, false) end)
		if ok then return end
		task.wait(0.25)
	end
end

local function collectTools()
	local list = {}
	local function add(t) if t:IsA("Tool") and t:GetAttribute("Kind") then table.insert(list, t) end end
	local bp = player:FindFirstChildOfClass("Backpack")
	if bp then for _, t in ipairs(bp:GetChildren()) do add(t) end end
	local char = player.Character
	if char then for _, t in ipairs(char:GetChildren()) do add(t) end end
	table.sort(list, function(a, b)
		local ka, kb = a:GetAttribute("Kind"), b:GetAttribute("Kind")
		if ka ~= kb then return ka == "pince" end
		return a.Name < b.Name
	end)
	return list
end

local function equipped()
	local char = player.Character
	return char and char:FindFirstChildOfClass("Tool")
end

local function equip(tool)
	local char = player.Character
	local hum = char and char:FindFirstChildOfClass("Humanoid")
	if not (hum and tool) then return end
	if tool.Parent == char then hum:UnequipTools() else hum:EquipTool(tool) end
end

local function fillIcon(tool, holder)
	for _, c in ipairs(holder:GetChildren()) do if not c:IsA("UICorner") then c:Destroy() end end
	if tool:GetAttribute("Kind") == "pince" then
		Registry.controllers["ClawPreview"].make(tool:GetAttribute("DefId"), tool:GetAttribute("Prestige"), holder)
	else
		local rd = Rarities.get(tool:GetAttribute("Rarity"))
		local em = Instance.new("TextLabel")
		em.BackgroundColor3 = Theme.darken(rarityColor(tool:GetAttribute("Rarity")), 0.4)
		em.Size = UDim2.fromScale(1, 1); em.Font = Enum.Font.SourceSansBold
		em.Text = (rd and rd.icon) or "⬛"; em.TextScaled = true; em.TextColor3 = P.White; em.Parent = holder
		Theme.Corner(em, UDim.new(0, 8))
	end
end

-- ===== hotbar =====
local function buildHotbar()
	hotbarBar = Instance.new("Frame")
	hotbarBar.Name = "Hotbar"; hotbarBar.AnchorPoint = Vector2.new(0.5, 1)
	hotbarBar.Position = UDim2.new(0.5, 0, 1, -8); hotbarBar.Size = UDim2.fromOffset(HOTBAR_SLOTS * 70, 70)
	hotbarBar.BackgroundTransparency = 1; hotbarBar.Parent = gui
	local l = Instance.new("UIListLayout"); l.FillDirection = Enum.FillDirection.Horizontal
	l.HorizontalAlignment = Enum.HorizontalAlignment.Center; l.VerticalAlignment = Enum.VerticalAlignment.Bottom
	l.Padding = UDim.new(0, 5); l.SortOrder = Enum.SortOrder.LayoutOrder; l.Parent = hotbarBar
	for i = 1, HOTBAR_SLOTS do
		local cell = Instance.new("TextButton"); cell.AutoButtonColor = false; cell.Text = ""
		cell.Size = UDim2.fromOffset(64, 64); cell.BackgroundColor3 = P.PanelBg; cell.LayoutOrder = i; cell.Parent = hotbarBar
		Theme.Corner(cell, UDim.new(0, 10)); local stroke = Theme.Stroke(cell, P.Outline, Theme.Dims.StrokeThin)
		local num = Instance.new("TextLabel"); num.BackgroundTransparency = 1; num.Size = UDim2.fromOffset(14, 14)
		num.Position = UDim2.fromOffset(3, 1); num.Font = Theme.Font.Title; num.Text = tostring(i % 10)
		num.TextColor3 = P.White; num.TextScaled = true; num.ZIndex = 6; num.Parent = cell; Theme.TextStroke(num, 1)
		local holder = Instance.new("Frame"); holder.Name = "Holder"; holder.BackgroundTransparency = 1
		holder.Size = UDim2.new(1, -6, 1, -16); holder.Position = UDim2.fromOffset(3, 3); holder.Parent = cell
		Theme.Corner(holder, UDim.new(0, 8))
		local cnt = Instance.new("TextLabel"); cnt.Name = "Count"; cnt.BackgroundTransparency = 1
		cnt.AnchorPoint = Vector2.new(0.5, 1); cnt.Position = UDim2.new(0.5, 0, 1, -1); cnt.Size = UDim2.new(1, -4, 0, 12)
		cnt.Font = Theme.Font.Body; cnt.Text = ""; cnt.TextColor3 = P.White; cnt.TextScaled = true; cnt.ZIndex = 6; cnt.Parent = cell
		Theme.TextStroke(cnt, 1)
		cell.Activated:Connect(function() if hotCells[i].tool then equip(hotCells[i].tool) end end)
		hotCells[i] = { cell = cell, stroke = stroke, holder = holder, cnt = cnt, tool = nil }
	end
end

-- ===== expandable panel =====
local TABS = { "Tout", "Ferraille", "Pinces" }
local function clearGrid() for _, c in ipairs(grid:GetChildren()) do if c:IsA("GuiObject") then c:Destroy() end end end
local function norm(s) return string.lower(s or "") end

local function renderPanel()
	clearGrid()
	for _, tool in ipairs(collectTools()) do
		local kind = tool:GetAttribute("Kind")
		local okTab = currentTab == "Tout" or (currentTab == "Pinces" and kind == "pince") or (currentTab == "Ferraille" and kind == "ferraille")
		local okSearch = searchText == "" or string.find(norm(tool.Name), norm(searchText), 1, true) ~= nil
		if okTab and okSearch then
			local card = Instance.new("TextButton"); card.AutoButtonColor = false; card.Text = ""
			card.Size = UDim2.fromOffset(96, 96); card.BackgroundColor3 = P.PanelBg; card.Parent = grid
			Theme.Corner(card, UDim.new(0, 10))
			local stroke = Theme.Stroke(card, kind == "pince" and rarityColor("common") or P.Outline, Theme.Dims.StrokeThin)
			local holder = Instance.new("Frame"); holder.BackgroundTransparency = 1; holder.Size = UDim2.new(1, -8, 1, -22)
			holder.Position = UDim2.fromOffset(4, 4); holder.Parent = card; Theme.Corner(holder, UDim.new(0, 8))
			fillIcon(tool, holder)
			local nm = Instance.new("TextLabel"); nm.BackgroundTransparency = 1; nm.Size = UDim2.new(1, -6, 0, 16)
			nm.AnchorPoint = Vector2.new(0.5, 1); nm.Position = UDim2.new(0.5, 0, 1, -2); nm.Font = Theme.Font.Body
			nm.Text = tool.Name; nm.TextColor3 = P.White; nm.TextScaled = true; nm.Parent = card; Theme.TextStroke(nm, 1)
			local nc = Instance.new("UITextSizeConstraint"); nc.MaxTextSize = 12; nc.Parent = nm
			if tool == equipped() then stroke.Color = P.Gold; stroke.Thickness = 3 end
			card.Activated:Connect(function() equip(tool) end)
		end
	end
end

local function setTab(t)
	currentTab = t
	for name, b in pairs(sidebarBtns) do b.BackgroundColor3 = (name == t) and P.TitleBar or P.PanelInner end
	renderPanel()
end

local function buildPanel()
	panel = Instance.new("Frame"); panel.Name = "Panel"; panel.AnchorPoint = Vector2.new(0.5, 1)
	panel.Position = UDim2.new(0.5, 0, 1, -84); panel.Size = UDim2.fromOffset(640, 360)
	panel.BackgroundColor3 = P.PanelBg; panel.Visible = false; panel.Parent = gui
	Theme.Corner(panel, Theme.Dims.Corner); Theme.Stroke(panel, P.Outline, Theme.Dims.Stroke)

	sidebarBtns = {}
	local side = Instance.new("Frame"); side.BackgroundTransparency = 1; side.Size = UDim2.new(0, 130, 1, -20)
	side.Position = UDim2.fromOffset(10, 10); side.Parent = panel
	local sl = Instance.new("UIListLayout"); sl.Padding = UDim.new(0, 8); sl.Parent = side
	for _, t in ipairs(TABS) do
		local b = Instance.new("TextButton"); b.AutoButtonColor = false; b.Size = UDim2.new(1, 0, 0, 54)
		b.BackgroundColor3 = P.PanelInner; b.Font = Theme.Font.Title; b.Text = t; b.TextColor3 = P.White
		b.TextScaled = true; b.Parent = side; Theme.Corner(b, UDim.new(0, 10)); Theme.Stroke(b, P.Outline, Theme.Dims.StrokeThin); Theme.TextStroke(b, 2)
		local tc = Instance.new("UITextSizeConstraint"); tc.MaxTextSize = 18; tc.Parent = b
		b.Activated:Connect(function() setTab(t) end)
		sidebarBtns[t] = b
	end

	searchBox = Instance.new("TextBox"); searchBox.Size = UDim2.new(0, 220, 0, 32); searchBox.AnchorPoint = Vector2.new(1, 0)
	searchBox.Position = UDim2.new(1, -14, 0, 12); searchBox.BackgroundColor3 = P.PanelInner; searchBox.Font = Theme.Font.Body
	searchBox.PlaceholderText = "Rechercher…"; searchBox.Text = ""; searchBox.TextColor3 = P.White; searchBox.TextScaled = true
	searchBox.ClearTextOnFocus = false; searchBox.Parent = panel
	Theme.Corner(searchBox, UDim.new(0, 10)); Theme.Stroke(searchBox, P.Outline, Theme.Dims.StrokeThin)
	searchBox:GetPropertyChangedSignal("Text"):Connect(function() searchText = searchBox.Text; renderPanel() end)

	local scroll = Instance.new("ScrollingFrame"); scroll.BackgroundTransparency = 1; scroll.BorderSizePixel = 0
	scroll.ScrollBarThickness = 8; scroll.Size = UDim2.new(1, -160, 1, -60); scroll.Position = UDim2.fromOffset(150, 52)
	scroll.CanvasSize = UDim2.new(); scroll.AutomaticCanvasSize = Enum.AutomaticSize.Y; scroll.Parent = panel
	local g = Instance.new("UIGridLayout"); g.CellSize = UDim2.fromOffset(96, 96); g.CellPadding = UDim2.fromOffset(8, 8)
	g.SortOrder = Enum.SortOrder.LayoutOrder; g.Parent = scroll
	local gp = Instance.new("UIPadding"); gp.PaddingLeft = UDim.new(0, 6); gp.PaddingTop = UDim.new(0, 6); gp.Parent = scroll
	grid = scroll
end

-- ===== refresh =====
local function refresh()
	local tools = collectTools()
	local eq = equipped()
	for i = 1, HOTBAR_SLOTS do
		local c = hotCells[i]; local tool = tools[i]; c.tool = tool
		for _, ch in ipairs(c.holder:GetChildren()) do if not ch:IsA("UICorner") then ch:Destroy() end end
		if tool then
			fillIcon(tool, c.holder)
			local kind = tool:GetAttribute("Kind")
			c.cnt.Text = (kind == "ferraille") and ("×" .. tostring(tool:GetAttribute("Count") or 1)) or ""
			c.stroke.Color = (tool == eq) and P.Gold or (kind == "pince" and rarityColor("common") or P.Outline)
			c.stroke.Thickness = (tool == eq) and 4 or Theme.Dims.StrokeThin
		else
			c.cnt.Text = ""; c.stroke.Color = P.Outline; c.stroke.Thickness = Theme.Dims.StrokeThin
		end
	end
	if panelOpen then renderPanel() end
end

local function bindContainers()
	local function bind(container)
		if not container then return end
		container.ChildAdded:Connect(refresh)
		container.ChildRemoved:Connect(refresh)
	end
	bind(player:FindFirstChildOfClass("Backpack"))
	bind(player.Character)
end

function BackpackController:Start()
	task.spawn(disableNative)
	local pg = player:WaitForChild("PlayerGui")
	gui = Instance.new("ScreenGui"); gui.Name = "BackpackGui"; gui.ResetOnSpawn = false
	gui.IgnoreGuiInset = true; gui.DisplayOrder = 8; gui.Parent = pg
	buildHotbar(); buildPanel(); setTab("Pinces"); refresh(); bindContainers()

	player.CharacterAdded:Connect(function()
		task.wait(0.3); bindContainers(); refresh()
	end)

	UIS.InputBegan:Connect(function(input, gp)
		if gp then return end
		if input.KeyCode == TOGGLE_KEY then
			panelOpen = not panelOpen; panel.Visible = panelOpen; if panelOpen then renderPanel() end
			return
		end
		local map = { [Enum.KeyCode.One]=1,[Enum.KeyCode.Two]=2,[Enum.KeyCode.Three]=3,[Enum.KeyCode.Four]=4,
			[Enum.KeyCode.Five]=5,[Enum.KeyCode.Six]=6,[Enum.KeyCode.Seven]=7,[Enum.KeyCode.Eight]=8,
			[Enum.KeyCode.Nine]=9,[Enum.KeyCode.Zero]=10 }
		local i = map[input.KeyCode]
		if i and hotCells[i] and hotCells[i].tool then equip(hotCells[i].tool) end
	end)
end

return BackpackController
```

- [ ] **Step 2: Verify the styled backpack.** Start Play, wait ~3s, `get_console_output` → no errors, `[Client] ready`. `execute_luau` (Client):
```lua
local pg = game.Players.LocalPlayer.PlayerGui
local g = pg:FindFirstChild("BackpackGui")
local sg = game:GetService("StarterGui")
local cells = g and g:FindFirstChild("Hotbar") and #g.Hotbar:GetChildren() or 0
return ("BackpackGui=%s hotbarCells=%d nativeBackpack=%s"):format(g and "Y" or "N", cells, tostring(sg:GetCoreGuiEnabled(Enum.CoreGuiType.Backpack)))
```
Expect: `BackpackGui=Y`, `hotbarCells>=10`, `nativeBackpack=false`. `screen_capture` (capture_id "Bp") if it works (Play capture is flaky) → bottom hotbar shows your ferraille/pince tools; Tab opens the categorized panel. Physically: press 1-0 to equip (tool appears in hand), Tab to open Tout/Ferraille/Pinces. Stop play.

- [ ] **Step 3: Persist** — Ctrl+S.

---

## Self-Review

**Spec coverage:** A `ToolService` (mirror data → Tools, reconcile, hooks) → Task 2. B `BackpackController` (hotbar + categories + equip, disable native) → Task 4. C `PlacementController` (equipped pince) → Task 3. D removal of old controllers → Task 1. Reuse of `ClawPreview`/`placeUFO`/prompt attrs/dist → unchanged. ✓

**Placeholder scan:** none — every function has a real body.

**Type/name consistency:** Tool attribute contract (`Kind`/`UfoUid`/`DefId`/`Prestige`; `Kind`/`ItemKey`/`DefId`/`Rarity`/`Count`) is written by `ToolService` (Task 2) and read identically by `PlacementController` (Task 3: `Kind`/`UfoUid`) and `BackpackController` (Task 4: `Kind`/`DefId`/`Prestige`/`Rarity`/`Count`). `ToolService.reconcile(player)` defined Task 2, called from `DataService.replicate`. `placeUFO {slotId, uid}` payload matches the existing server handler.

## Verification (full feature)
1. Backpack mirrors data (unplaced pinces + ferraille); placed pince has no Tool; catch updates a ferraille Tool's count without disturbing the equipped one.
2. Equip a pince (1-0/click) → in hand; E at empty slot places THAT pince → its Tool vanishes; E on filled slot → Tool returns.
3. Styled GUI: hotbar + Tab panel (Tout/Ferraille/Pinces + search); native backpack hidden; equipped highlighted gold.
4. No console errors; controller/service counts sane.
5. **Ctrl+S**.
