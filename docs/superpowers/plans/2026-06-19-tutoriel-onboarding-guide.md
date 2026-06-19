# Tutoriel d'onboarding guidé — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax. This is live Roblox-Studio MCP work: "tests" = read-back verification, deterministic `execute_luau` checks, and screenshots (Play mode for runtime UI, Edit for static). The user saves with **Ctrl+S** at the end to persist into `build.rbxlx`.

**Goal:** A premium, opt-in, server-authoritative onboarding tutorial that drops a brand-new player straight into the core loop — place your pince → watch it catch → sell at the vendor → buy an upgrade — guided entirely by world/screen visual indicators, ending with a guaranteed-rare pince reward.

**Architecture:** A client step-machine (`TutorialController`) advances by observing the player's *real* actions via the existing server `meta.funnelFlags` (replicated through `StateController`). A reusable visual toolkit (`GuideFX`) draws the arrows/rings/highlights/spotlights. A new server `TutorialService` owns the persisted `meta.tutorialDone` gate, the skip path (auto-places the starter), and the grant-once reward (validated against the funnel flags = anti-cheat). The existing `PlotService.grantStarterIfNeeded` is gated so the starter is **granted but not auto-placed** while the tutorial is pending.

**Tech Stack:** Roblox Studio MCP (`script_read`, `multi_edit`, `execute_luau`, `inspect_instance`, `start_stop_play`, `screen_capture`), Luau. No external test runner — verification is in-engine.

## Global Constraints

- **Source of truth** = `build.rbxlx`; edits are applied to the live Edit/Play DataModel via MCP, then the user runs **Ctrl+S**. `multi_edit` can silently no-op → **always re-read** the script after editing to confirm. The `execute_luau` **Server VM is isolated** → to exercise server services, inject a temporary `Script` into `ServerScriptService`, not the execute sandbox.
- **Server services** live at **`ServerScriptService.Server.Services`** (20 ModuleScripts incl. `PlotService`, `DataService`, `UpgradeService`, `InventoryService`, `ToolService`, `AnalyticsService`, `EconomyService`); the bootstrap `ServerScriptService.Server` (`init.server`) folder-scans them and runs `:Init()` then `:Start()`. `TutorialService` goes in this folder and is auto-loaded. (If a session momentarily shows `ServerScriptService` empty, it caught Studio mid-load — re-inspect.)
- **Client controllers** auto-load: every `ModuleScript` under `StarterPlayer.StarterPlayerScripts.Client.Controllers` is required, registered by `Name` in `Registry.controllers`, then `:Init()` then `:Start()` are called (see `Client` LocalScript). New controllers just need a `Name` and an `Init`/`Start`.
- **Net contract** — server: `Net.onRequest(action, handler(player,payload) -> data | (false, err))`, `Net.sendEvent(player, name, data)`. client: `Net.request(action, payload) -> {ok, err?, data?}`, `Net.onState(fn)`, `Net.onEvent(name, fn)`. (`ReplicatedStorage.Shared.Net.Net`.)
- **Funnel flags** (set server-side by the real services, read client-side at `state.meta.funnelFlags`): `first_ufo_placed` (set in `PlotService.placeUFO`), `first_item_caught` (`CatchService`/`InventoryService.addItem`), `first_item_sold` (`InventoryService.sell*` via the vendor `"Vendre tout"` prompt), `first_upgrade_bought` (`UpgradeService.buy` via `buyUpgrade`). The tutorial **must not invent new flags** for step completion — it reads these.
- **Server helper APIs** (all via `Registry.get("X")` on the server): `DataService.get(player) -> data`, `DataService.onReady(fn(player))`, `DataService.onRemoving(fn)`, `DataService.replicate(player)` (fires `ToolService.reconcile` + pushes state); `EconomyService.add(player, "scrap", n)`; `AnalyticsService.TrackOnce(player, flag, event, props?)`, `AnalyticsService.Track(player, event, props)`; `Id.new()` (`Shared.Util.Id`). Currency key is `"scrap"` (displayed as `$`).
- **Client lookup APIs**: `Registry.get("PlotController")` → `.getPlot()`, `.waitForPlot(t)`, `.getUFO(slotId)`; `Registry.get("StateController")` → `.onChanged(fn(state))`, `.get()`; `Registry.controllers["ClawPreview"].make(defId, prestige, parent) -> ViewportFrame`. Plot model = `Workspace` child with attribute `OwnerUserId == player.UserId` (also named `Plot_<UserId>`); slot pad = `plot:FindFirstChild("Slot_<slotId>")`; vendor stand = `plot:FindFirstChild("SellPad")`; machine = `plot:FindFirstChild("UFO_<slotId>")`.
- **UI kit** = `ReplicatedStorage.UI.Theme` (require as `Theme`, `P = Theme.Palette`): `Theme.Panel({parent,title,size}) -> {card, content, close}`, `Theme.Button({parent,text,color,size,position,anchor,maxTextSize}) -> TextButton`, `Theme.SectionHeader({text,position,size,parent})`, `Theme.Pill({...})`, `Theme.Corner(inst, UDim)`, `Theme.Stroke(inst, color, thick)`, `Theme.TextStroke(inst, n)`, `Theme.darken(color, amt)`, `Theme.Dims.{Corner,Stroke,StrokeThin}`, `Theme.Font.{Title,Body}`. Palette keys used: `P.PanelBg, P.PanelInner, P.Outline, P.Gold, P.White, P.Confirm` (green), `P.Danger, P.Purple, P.Cyan, P.Muted, P.TitleBar`. **Guidance green = `P.Confirm`; reward gold = `P.Gold`.** Fonts already cartoon-premium (LuckiestGuy/Fredoka).
- **FX kit** = `Client.FXKit`: `FXKit.burst(atCF,color,order,jackpot?)`, `.shockwave(atCF,color)`, `.lightBeam(atCF,color)`, `.explode(atCF,color)`, `.flash(atCF,color,maxSize?)`, `.shake(mag,dur)`, `.playSound(id,anchor?,vol?)`, `.SOUNDS`.
- **Reward** = `UFOCatchers.get("rare_1")` (defId scheme `<rarity>_<rank>`; `rare` = tier 3, clear jump above `common_1`). Both `s1` and `s2` are unlocked by default (`GameConfig.PROFILE_TEMPLATE.plot.slots`), so no slot-unlock is needed for machine #2.
- **All new tutorial GUIs**: `ResetOnSpawn=false`, `IgnoreGuiInset=true`, a high `DisplayOrder` (≥ 80, above Menus=10/Backpack=8/Cashout=60), parented to `PlayerGui`. All `GuideFX` world parts: `Anchored=true, CanCollide=false, CanQuery=false`, attribute `GuideFX=true` (sweepable).
- **FR copy only** (match the game). Edits live in the DataModel → **pending Ctrl+S**.

---

### Task 1: Restore server scripts + add the `tutorialDone` data field

**Files:**
- Verify/restore: server services tree (currently absent from live DM).
- Modify: `ReplicatedStorage.Shared.Config.GameConfig` (`PROFILE_TEMPLATE.meta`).
- Modify: `ReplicatedStorage.Shared.Types` (the `meta` type, ~line 121).

**Interfaces:**
- Produces: `data.meta.tutorialDone: boolean` (default `false`) present on every profile via `ProfileStore:Reconcile`.

- [ ] **Step 1: Confirm server services are loaded.** `inspect_instance` on `ServerScriptService.Server.Services`. **CONFIRMED (2026-06-19):** 20 services present (`PlotService`, `DataService`, `UpgradeService`, `InventoryService`, `ToolService`, `AnalyticsService`, `EconomyService`, …); bootstrap = `ServerScriptService.Server` (`init.server`) folder-scans + `Init`/`Start`. `TutorialService` (Task 3) goes in `ServerScriptService.Server.Services`. (If `ServerScriptService` shows 0 children, Studio was mid-load — re-inspect; do not have the user reopen unless it persists.)

- [ ] **Step 2: Add `tutorialDone` to the profile template.** In `GameConfig`, change the `meta` line of `PROFILE_TEMPLATE`:

```lua
	meta = { version = 1, firstJoinAt = 0, lastSeenAt = 0, funnelFlags = {}, tutorialDone = false },
```

- [ ] **Step 3: Add it to the `meta` type.** In `Shared.Types`, the `meta` field becomes:

```lua
	meta: { version: number, firstJoinAt: number, lastSeenAt: number, funnelFlags: { [string]: boolean }, tutorialDone: boolean },
```

- [ ] **Step 4: Verify (read-back).** `script_read` both edits to confirm they applied (multi_edit no-op guard). Confirm `GameConfig` line now contains `tutorialDone = false`.

- [ ] **Step 5: Commit.**

```bash
git add docs/superpowers/plans/2026-06-19-tutoriel-onboarding-guide.md
git commit -m "feat(tutorial): add meta.tutorialDone profile field"
```
(Code lives in `build.rbxlx`, persisted by the user's Ctrl+S; commit the plan/doc progress.)

---

### Task 2: Gate the starter auto-place on tutorial completion

**Files:**
- Modify: `PlotService` → `grantStarterIfNeeded(player, data)` (in `build.rbxlx` ~line 1092194).

**Interfaces:**
- Consumes: `data.meta.tutorialDone` (Task 1).
- Produces: when a fresh profile joins with `tutorialDone == false`, the starter pince is in `data.ufos` but **`data.plot.slots.s1.ufoUid` stays `nil`** (so `ToolService` surfaces it as a backpack Tool and the tutorial can teach placement). When `tutorialDone == true`, legacy behavior (auto-place) is preserved.

- [ ] **Step 1: Replace the function body.** Current:

```lua
local function grantStarterIfNeeded(player: Player, data)
	if next(data.ufos) ~= nil then
		return -- already has UFOs
	end
	local uid = Id.new()
	data.ufos[uid] = { defId = GameConfig.STARTING.starterUFO, level = 1, prestige = 0 }
	local startSlot = GameConfig.STARTING.starterSlotForUFO
	if data.plot.slots[startSlot] and data.plot.slots[startSlot].unlocked then
		data.plot.slots[startSlot].ufoUid = uid
	end
end
```

New (the only change is gating the auto-place on `tutorialDone`):

```lua
local function grantStarterIfNeeded(player: Player, data)
	if next(data.ufos) ~= nil then
		return -- already has UFOs
	end
	local uid = Id.new()
	data.ufos[uid] = { defId = GameConfig.STARTING.starterUFO, level = 1, prestige = 0 }
	local startSlot = GameConfig.STARTING.starterSlotForUFO
	-- Onboarding: leave the starter UNPLACED so the tutorial can teach placement.
	-- Once the tutorial is done/skipped (TutorialService), the starter is auto-placed
	-- (legacy behavior, also covers profiles that never run the tutorial).
	if data.meta.tutorialDone and data.plot.slots[startSlot] and data.plot.slots[startSlot].unlocked then
		data.plot.slots[startSlot].ufoUid = uid
	end
end
```

- [ ] **Step 2: Verify (read-back).** `script_read` `PlotService` around `grantStarterIfNeeded`; confirm the `data.meta.tutorialDone and` guard is present.

- [ ] **Step 3: Deterministic check (temp server Script).** Inject a temp `Script` into `ServerScriptService` that builds a fake `data` from `GameConfig.PROFILE_TEMPLATE` (deep-copy), sets `meta.tutorialDone=false`, calls the grant logic path indirectly is hard in isolation — instead assert the *intent*: read `GameConfig.PROFILE_TEMPLATE.plot.slots.s1.unlocked == true` and `.s2.unlocked == true`, and `meta.tutorialDone == false`. Print PASS/FAIL. (Full behavior is verified end-to-end in Task 8.) Remove the temp Script.

- [ ] **Step 4: Commit** (`git commit -m "feat(tutorial): don't auto-place starter while tutorial pending"`).

---

### Task 3: Server `TutorialService` (status / skip / finish + reward + anti-cheat)

**Files:**
- Create: `TutorialService` ModuleScript, sibling of `PlotService` in the server services folder (path from Task 1). Auto-loaded by the server bootstrap.

**Interfaces:**
- Consumes: `DataService`, `EconomyService`(unused here but available), `AnalyticsService`, `Net`, `Id`, `UFOCatchers`, `GameConfig`.
- Produces three remotes:
  - `tutorialStatus` → `{ shouldOffer: boolean }` (`= not data.meta.tutorialDone`).
  - `tutorialSkip` → marks done + auto-places the starter in `s1`. Returns `{ ok = true }`.
  - `tutorialFinish` → validates the 4 funnel flags, grants `rare_1`, marks done. Returns `{ rewardDefId = "rare_1" }` (or `(false, err)`). Also fires `Net.sendEvent(player, "tutorialReward", { defId = "rare_1" })`.

- [ ] **Step 1: Write the module.**

```lua
--!strict
-- TutorialService.luau
-- Server-authoritative gate + reward for the onboarding tutorial. The CLIENT
-- (TutorialController) drives the visuals; the server owns persistence and the grant-once
-- reward, validated against the real funnel flags (anti-cheat).

local Shared = game:GetService("ReplicatedStorage"):WaitForChild("Shared")
local ServerRoot = script.Parent.Parent
local Registry = require(ServerRoot.Registry)

local Net = require(Shared.Net.Net)
local Id = require(Shared.Util.Id)
local GameConfig = require(Shared.Config.GameConfig)
local UFOCatchers = require(Shared.Config.UFOCatchers)

local TutorialService = {}

local REWARD_DEFID = "rare_1" -- guaranteed-rare pince (clear jump above common_1 starter)
local REQUIRED_FLAGS = { "first_ufo_placed", "first_item_caught", "first_item_sold", "first_upgrade_bought" }

-- Find the player's starter pince uid that is NOT placed in any slot.
local function findUnplacedUfo(data): string?
	local placed: { [string]: boolean } = {}
	for _, slot in pairs(data.plot.slots) do
		if slot.ufoUid then placed[slot.ufoUid] = true end
	end
	for uid in pairs(data.ufos) do
		if not placed[uid] then return uid end
	end
	return nil
end

local function autoPlaceStarter(data)
	local startSlot = GameConfig.STARTING.starterSlotForUFO
	local slot = data.plot.slots[startSlot]
	if not slot or not slot.unlocked or slot.ufoUid then return end
	local uid = findUnplacedUfo(data)
	if uid then slot.ufoUid = uid end
end

function TutorialService.skip(player: Player): boolean
	local data = Registry.get("DataService").get(player)
	if not data then return false end
	if not data.meta.tutorialDone then
		data.meta.tutorialDone = true
		autoPlaceStarter(data) -- player stays operational
		Registry.get("DataService").replicate(player)
		Registry.get("AnalyticsService").TrackOnce(player, "tutorial_skipped", "tutorial_skipped")
	end
	return true
end

function TutorialService.finish(player: Player): (boolean, any)
	local data = Registry.get("DataService").get(player)
	if not data then return false, "not_ready" end
	if data.meta.tutorialDone then
		return { rewardDefId = REWARD_DEFID, alreadyDone = true } -- idempotent, no double-grant
	end
	-- Anti-cheat: the funnel flags are only set by the real services. Require all four.
	for _, flag in ipairs(REQUIRED_FLAGS) do
		if not data.meta.funnelFlags[flag] then
			return false, "incomplete:" .. flag
		end
	end
	-- Grant the guaranteed-rare pince (surfaces as a backpack Tool via ToolService on replicate).
	if UFOCatchers.get(REWARD_DEFID) then
		data.ufos[Id.new()] = { defId = REWARD_DEFID, level = 1, prestige = 0 }
	end
	data.meta.tutorialDone = true
	Registry.get("DataService").replicate(player)
	Registry.get("AnalyticsService").TrackOnce(player, "tutorial_completed", "tutorial_completed")
	Net.sendEvent(player, "tutorialReward", { defId = REWARD_DEFID })
	return { rewardDefId = REWARD_DEFID }
end

function TutorialService:Start()
	Net.onRequest("tutorialStatus", function(player)
		local data = Registry.get("DataService").get(player)
		return { shouldOffer = (data ~= nil) and (not data.meta.tutorialDone) }
	end)
	Net.onRequest("tutorialSkip", function(player)
		return { ok = TutorialService.skip(player) }
	end)
	Net.onRequest("tutorialFinish", function(player)
		return TutorialService.finish(player)
	end)
end

return TutorialService
```

- [ ] **Step 2: Verify it loads.** `inspect_instance` the services folder → `TutorialService` present. Enter Play (`start_stop_play`), then `get_console_output` → no `TutorialService` require/Start errors. (If the bootstrap requires an explicit registration list rather than folder-scan, add `TutorialService` to it — discovered in Task 1.)

- [ ] **Step 3: Deterministic anti-cheat check (temp server Script in `ServerScriptService`).** While in Play, inject a Script that, for the local player's `data`: (a) calls `TutorialService.finish` with no flags set → expect `(false, "incomplete:first_ufo_placed")`; (b) sets all 4 flags, calls again → expect a table with `rewardDefId == "rare_1"` and `data.meta.tutorialDone == true` and exactly one extra `rare_1` in `data.ufos`; (c) calls again → `alreadyDone == true`, no second `rare_1`. Print PASS/FAIL per case. Remove the Script. Stop Play.

- [ ] **Step 4: Commit** (`git commit -m "feat(tutorial): server TutorialService (status/skip/finish + rare_1 reward)"`).

---

### Task 4: Client `GuideFX` module (the reusable visual-guidance toolkit)

**Files:**
- Create: `StarterPlayer.StarterPlayerScripts.Client.GuideFX` (ModuleScript at the **client root**, a sibling of `UIUtil`/`FXKit` — NOT under `Controllers/`, so the loader ignores it; controllers `require` it by relative path).

**Interfaces:**
- Produces a toolkit. Every constructor returns a **handle** `{ Destroy = function() end }` and is auto-tracked; `GuideFX.clearAll()` destroys all live handles. Default color = `Theme.Palette.Confirm` (guidance green).
  - `GuideFX.highlight(instance: Instance, color?: Color3) -> handle`
  - `GuideFX.worldArrow(adornee: BasePart, color?: Color3) -> handle`
  - `GuideFX.groundRing(target: BasePart | CFrame, color?: Color3) -> handle`
  - `GuideFX.offscreenIndicator(getPos: () -> Vector3?, color?: Color3) -> handle`
  - `GuideFX.screenPointer(gui: GuiObject, color?: Color3) -> handle`
  - `GuideFX.spotlight(gui: GuiObject) -> handle`
  - `GuideFX.pulse(gui: GuiObject) -> handle`
  - `GuideFX.clearAll()`

- [ ] **Step 1: Write the module.**

```lua
--!strict
-- GuideFX.luau (client)
-- Reusable onboarding/quest guidance primitives: world arrows, ground rings, highlights,
-- off-screen edge indicators, on-screen pointers, spotlight scrims, button pulses. Premium,
-- tweened, green=guidance. Every constructor returns a handle with :Destroy(); clearAll() purges.

local RunService = game:GetService("RunService")
local TweenService = game:GetService("TweenService")
local Players = game:GetService("Players")
local RS = game:GetService("ReplicatedStorage")

local Theme = require(RS.UI.Theme)
local P = Theme.Palette

local GuideFX = {}
local GREEN = P.Confirm
local player = Players.LocalPlayer

local active: { [any]: boolean } = {}
local function track(handle)
	active[handle] = true
	local realDestroy = handle.Destroy
	handle.Destroy = function()
		active[handle] = nil
		if realDestroy then realDestroy() end
	end
	return handle
end

function GuideFX.clearAll()
	for h in pairs(active) do
		pcall(function() h:Destroy() end)
	end
	active = {}
end

-- ===== world: highlight (breathing outline + soft fill) =====
function GuideFX.highlight(instance: Instance, color: Color3?): any
	local hl = Instance.new("Highlight")
	hl.Adornee = instance
	hl.DepthMode = Enum.HighlightDepthMode.AlwaysOnTop
	hl.OutlineColor = color or GREEN
	hl.FillColor = color or GREEN
	hl.OutlineTransparency = 0
	hl.FillTransparency = 0.75
	hl.Parent = instance
	local tw = TweenService:Create(hl, TweenInfo.new(0.7, Enum.EasingStyle.Sine, Enum.EasingDirection.InOut, -1, true), { FillTransparency = 0.95 })
	tw:Play()
	return track({ Destroy = function() tw:Cancel(); hl:Destroy() end })
end

-- ===== world: bobbing downward chevron above a part =====
function GuideFX.worldArrow(adornee: BasePart, color: Color3?): any
	local bb = Instance.new("BillboardGui")
	bb.Name = "GuideArrow"
	bb.Adornee = adornee
	bb.Size = UDim2.fromOffset(64, 64)
	bb.StudsOffsetWorldSpace = Vector3.new(0, (adornee.Size.Y / 2) + 4, 0)
	bb.AlwaysOnTop = true
	bb.Parent = adornee
	local lbl = Instance.new("TextLabel")
	lbl.BackgroundTransparency = 1
	lbl.Size = UDim2.fromScale(1, 1)
	lbl.Font = Enum.Font.LuckiestGuy
	lbl.Text = "▼"
	lbl.TextScaled = true
	lbl.TextColor3 = color or GREEN
	lbl.TextStrokeColor3 = Color3.fromRGB(20, 30, 16)
	lbl.TextStrokeTransparency = 0
	lbl.Parent = bb
	local t0 = os.clock()
	local conn = RunService.RenderStepped:Connect(function()
		local b = math.sin((os.clock() - t0) * 5) * 3
		bb.StudsOffsetWorldSpace = Vector3.new(0, (adornee.Size.Y / 2) + 4 + b * 0.15, 0)
	end)
	return track({ Destroy = function() conn:Disconnect(); bb:Destroy() end })
end

-- ===== world: pulsing neon ring on the ground =====
function GuideFX.groundRing(target: any, color: Color3?): any
	local cf: CFrame = (typeof(target) == "Instance") and (target :: BasePart).CFrame or target
	local ring = Instance.new("Part")
	ring.Name = "GuideRing"
	ring.Anchored = true; ring.CanCollide = false; ring.CanQuery = false
	ring.Shape = Enum.PartType.Cylinder
	ring.Material = Enum.Material.Neon
	ring.Color = color or GREEN
	ring.Transparency = 0.25
	ring.Size = Vector3.new(0.4, 7, 7)
	ring.CFrame = (cf - cf.Position + Vector3.new(cf.X, cf.Position.Y - 1.4, cf.Z)) * CFrame.Angles(0, 0, math.rad(90))
	ring:SetAttribute("GuideFX", true)
	ring.Parent = workspace
	local tw = TweenService:Create(ring, TweenInfo.new(0.9, Enum.EasingStyle.Sine, Enum.EasingDirection.InOut, -1, true), { Size = Vector3.new(0.4, 10, 10), Transparency = 0.55 })
	tw:Play()
	return track({ Destroy = function() tw:Cancel(); ring:Destroy() end })
end

-- ===== screen: edge arrow pointing toward an off-screen world target =====
function GuideFX.offscreenIndicator(getPos: () -> Vector3?, color: Color3?): any
	local gui = Instance.new("ScreenGui")
	gui.Name = "GuideOffscreen"; gui.ResetOnSpawn = false; gui.IgnoreGuiInset = true; gui.DisplayOrder = 82
	gui.Parent = player:WaitForChild("PlayerGui")
	local arrow = Instance.new("TextLabel")
	arrow.AnchorPoint = Vector2.new(0.5, 0.5)
	arrow.Size = UDim2.fromOffset(56, 56)
	arrow.BackgroundTransparency = 1
	arrow.Font = Enum.Font.LuckiestGuy
	arrow.Text = "➤"
	arrow.TextScaled = true
	arrow.TextColor3 = color or GREEN
	arrow.TextStrokeColor3 = Color3.fromRGB(20, 30, 16)
	arrow.TextStrokeTransparency = 0
	arrow.Parent = gui
	local conn = RunService.RenderStepped:Connect(function()
		local cam = workspace.CurrentCamera
		local pos = getPos()
		if not cam or not pos then arrow.Visible = false; return end
		local sp, onScreen = cam:WorldToViewportPoint(pos)
		local vp = cam.ViewportSize
		if onScreen and sp.Z > 0 then
			arrow.Visible = false -- target visible: world arrow handles it
			return
		end
		arrow.Visible = true
		-- direction from screen center to the (possibly behind) target
		local dir = Vector2.new(sp.X - vp.X / 2, sp.Y - vp.Y / 2)
		if sp.Z < 0 then dir = -dir end
		if dir.Magnitude < 1 then dir = Vector2.new(0, -1) end
		dir = dir.Unit
		local margin = 70
		local cx, cy = vp.X / 2, vp.Y / 2
		local px = math.clamp(cx + dir.X * cx * 2, margin, vp.X - margin)
		local py = math.clamp(cy + dir.Y * cy * 2, margin, vp.Y - margin)
		arrow.Position = UDim2.fromOffset(px, py)
		arrow.Rotation = math.deg(math.atan2(dir.Y, dir.X))
	end)
	return track({ Destroy = function() conn:Disconnect(); gui:Destroy() end })
end

-- ===== screen: pointer (arrow + halo) tracking a GUI button =====
function GuideFX.screenPointer(targetGui: GuiObject, color: Color3?): any
	local gui = Instance.new("ScreenGui")
	gui.Name = "GuidePointer"; gui.ResetOnSpawn = false; gui.IgnoreGuiInset = true; gui.DisplayOrder = 83
	gui.Parent = player:WaitForChild("PlayerGui")
	local halo = Instance.new("ImageLabel")
	halo.BackgroundTransparency = 1
	halo.Image = "rbxasset://textures/ui/common/glow.png" -- soft radial; fallback below if missing
	halo.ImageColor3 = color or GREEN
	halo.ImageTransparency = 0.2
	halo.AnchorPoint = Vector2.new(0.5, 0.5)
	halo.Parent = gui
	local arrow = Instance.new("TextLabel")
	arrow.BackgroundTransparency = 1; arrow.AnchorPoint = Vector2.new(0.5, 0.5)
	arrow.Size = UDim2.fromOffset(48, 48); arrow.Font = Enum.Font.LuckiestGuy; arrow.Text = "➤"
	arrow.TextScaled = true; arrow.TextColor3 = color or GREEN
	arrow.TextStrokeColor3 = Color3.fromRGB(20, 30, 16); arrow.TextStrokeTransparency = 0; arrow.Rotation = 90
	arrow.Parent = gui
	local t0 = os.clock()
	local conn = RunService.RenderStepped:Connect(function()
		if not targetGui.Parent or not targetGui.Visible then halo.Visible = false; arrow.Visible = false; return end
		halo.Visible = true; arrow.Visible = true
		local ap, az = targetGui.AbsolutePosition, targetGui.AbsoluteSize
		local cx, cy = ap.X + az.X / 2, ap.Y + az.Y / 2
		local pulse = 1 + 0.12 * math.sin((os.clock() - t0) * 6)
		halo.Size = UDim2.fromOffset(az.X * 2.0 * pulse, az.Y * 2.0 * pulse)
		halo.Position = UDim2.fromOffset(cx, cy)
		arrow.Position = UDim2.fromOffset(cx, ap.Y - 30 + 4 * math.sin((os.clock() - t0) * 6))
	end)
	return track({ Destroy = function() conn:Disconnect(); gui:Destroy() end })
end

-- ===== screen: spotlight scrim (dims everything except the target rect) =====
function GuideFX.spotlight(targetGui: GuiObject): any
	local gui = Instance.new("ScreenGui")
	gui.Name = "GuideSpotlight"; gui.ResetOnSpawn = false; gui.IgnoreGuiInset = true; gui.DisplayOrder = 81
	gui.Parent = player:WaitForChild("PlayerGui")
	local function mkPanel()
		local f = Instance.new("Frame"); f.BackgroundColor3 = Color3.new(0, 0, 0)
		f.BackgroundTransparency = 0.4; f.BorderSizePixel = 0; f.Parent = gui; return f
	end
	local top, bottom, left, right = mkPanel(), mkPanel(), mkPanel(), mkPanel()
	local pad = 8
	local conn = RunService.RenderStepped:Connect(function()
		if not targetGui.Parent or not targetGui.Visible then return end
		local cam = workspace.CurrentCamera; if not cam then return end
		local vp = cam.ViewportSize
		local ap, az = targetGui.AbsolutePosition, targetGui.AbsoluteSize
		local x0, y0 = ap.X - pad, ap.Y - pad
		local x1, y1 = ap.X + az.X + pad, ap.Y + az.Y + pad
		top.Position = UDim2.fromOffset(0, 0); top.Size = UDim2.fromOffset(vp.X, math.max(0, y0))
		bottom.Position = UDim2.fromOffset(0, y1); bottom.Size = UDim2.fromOffset(vp.X, math.max(0, vp.Y - y1))
		left.Position = UDim2.fromOffset(0, y0); left.Size = UDim2.fromOffset(math.max(0, x0), math.max(0, y1 - y0))
		right.Position = UDim2.fromOffset(x1, y0); right.Size = UDim2.fromOffset(math.max(0, vp.X - x1), math.max(0, y1 - y0))
	end)
	return track({ Destroy = function() conn:Disconnect(); gui:Destroy() end })
end

-- ===== screen: subtle breathe on a button itself =====
function GuideFX.pulse(targetGui: GuiObject): any
	local scale = targetGui:FindFirstChildOfClass("UIScale") or Instance.new("UIScale")
	scale.Parent = targetGui
	local tw = TweenService:Create(scale, TweenInfo.new(0.55, Enum.EasingStyle.Sine, Enum.EasingDirection.InOut, -1, true), { Scale = 1.08 })
	tw:Play()
	return track({ Destroy = function() tw:Cancel(); scale.Scale = 1 end })
end

return GuideFX
```

- [ ] **Step 2: Smoke-test each primitive (temp client Script via `execute_luau` client OR a temp LocalScript).** In Play, run a snippet that requires `GuideFX` and, against the local player's character HumanoidRootPart, creates `highlight`, `worldArrow`, `groundRing` (on HRP), and a `screenPointer`/`spotlight`/`pulse` on a temp Frame; `screen_capture`; then `GuideFX.clearAll()` and confirm everything is gone (`inspect_instance` PlayerGui has no `Guide*` ScreenGuis, workspace has no `GuideRing`). If `rbxasset://textures/ui/common/glow.png` doesn't render, replace `halo.Image` with `"rbxassetid://5028857084"` (the same soft shadow asset `UIUtil.shadow` uses).

- [ ] **Step 3: Commit** (`git commit -m "feat(tutorial): GuideFX visual-guidance toolkit"`).

---

### Task 5: `TutorialController` — proposal popup + step-card UI shell

**Files:**
- Create: `StarterPlayer.StarterPlayerScripts.Client.Controllers.TutorialController` (auto-loaded).
- Delete (later, Task 6 Step 5): `Controllers.OnboardingController`.

**Interfaces:**
- Consumes: `Registry`, `GuideFX` (Task 4), `Theme`, `Net`, `StateController`, `PlotController`, `FXKit`.
- Produces (internal): `showProposal()`, `mountCard()`, `setCard(title, stepIndex)`, `celebrate(defId)`. Step logic added in Task 6.

- [ ] **Step 1: Write the controller shell (proposal + card; no step wiring yet).**

```lua
--!strict
-- TutorialController.luau
-- Premium opt-in onboarding. Drives a 4-step "learn by doing" flow with GuideFX visual guidance,
-- gated server-side (TutorialService). Replaces the abandoned OnboardingController.

local Players = game:GetService("Players")
local TweenService = game:GetService("TweenService")
local RS = game:GetService("ReplicatedStorage")
local Shared = RS:WaitForChild("Shared")

local ClientRoot = script.Parent.Parent
local Registry = require(ClientRoot.Registry)
local GuideFX = require(ClientRoot.GuideFX)
local FXKit = require(ClientRoot.FXKit)
local Theme = require(RS.UI.Theme)
local P = Theme.Palette
local Net = require(Shared.Net.Net)

local TutorialController = {}
local player = Players.LocalPlayer
local gui, card, cardTitle, cardPips
local active = false

local TOTAL_STEPS = 4

-- ===== proposal popup =====
local function showProposal(onStart, onSkip)
	local pg = player:WaitForChild("PlayerGui")
	local sg = Instance.new("ScreenGui")
	sg.Name = "TutorialProposal"; sg.ResetOnSpawn = false; sg.IgnoreGuiInset = true; sg.DisplayOrder = 90
	sg.Parent = pg
	local overlay = Instance.new("TextButton")
	overlay.Size = UDim2.fromScale(1, 1); overlay.BackgroundColor3 = Color3.new(0, 0, 0)
	overlay.BackgroundTransparency = 0.4; overlay.AutoButtonColor = false; overlay.Text = ""; overlay.Parent = sg
	local parts = Theme.Panel({ parent = sg, title = "🎓 BIENVENUE !", size = UDim2.fromOffset(460, 300) })
	local content = parts.content
	local body = Instance.new("TextLabel")
	body.BackgroundTransparency = 1; body.Size = UDim2.new(1, 0, 0, 120); body.Position = UDim2.fromOffset(0, 0)
	body.Font = Theme.Font.Body; body.TextScaled = true; body.TextColor3 = P.White; body.TextWrapped = true
	body.Text = "Tour express (~60s) pour bien démarrer.\nFinis-le et gagne une PINCE RARE ✨"
	body.Parent = content
	local bc = Instance.new("UITextSizeConstraint"); bc.MaxTextSize = 22; bc.Parent = body
	Theme.TextStroke(body, 1.5)
	local startBtn = Theme.Button({ parent = content, text = "▶ C'EST PARTI", color = P.Confirm,
		size = UDim2.new(1, 0, 0, 56), position = UDim2.fromOffset(0, 132), maxTextSize = 26 })
	local skipBtn = Theme.Button({ parent = content, text = "Passer", color = P.PanelInner,
		size = UDim2.new(1, 0, 0, 40), position = UDim2.fromOffset(0, 198), maxTextSize = 18 })
	local function done() sg:Destroy() end
	startBtn.MouseButton1Click:Connect(function() done(); onStart() end)
	skipBtn.MouseButton1Click:Connect(function() done(); onSkip() end)
	-- pop-in
	local sc = parts.card:FindFirstChildOfClass("UIScale") or Instance.new("UIScale")
	sc.Parent = parts.card; sc.Scale = 0.7
	TweenService:Create(sc, TweenInfo.new(0.22, Enum.EasingStyle.Back, Enum.EasingDirection.Out), { Scale = 1 }):Play()
end

-- ===== step card (bottom-center) =====
local function mountCard()
	gui = Instance.new("ScreenGui")
	gui.Name = "TutorialCard"; gui.ResetOnSpawn = false; gui.IgnoreGuiInset = true; gui.DisplayOrder = 85
	gui.Parent = player:WaitForChild("PlayerGui")
	card = Instance.new("Frame")
	card.AnchorPoint = Vector2.new(0.5, 1); card.Position = UDim2.new(0.5, 0, 1, -92)
	card.Size = UDim2.fromOffset(560, 64); card.BackgroundColor3 = P.PanelBg; card.BorderSizePixel = 0
	card.Visible = false; card.Parent = gui
	Theme.Corner(card, UDim.new(0, 14)); Theme.Stroke(card, P.Confirm, 3)
	cardTitle = Instance.new("TextLabel")
	cardTitle.BackgroundTransparency = 1; cardTitle.Position = UDim2.fromOffset(16, 6)
	cardTitle.Size = UDim2.new(1, -32, 0, 34); cardTitle.Font = Theme.Font.Title; cardTitle.Text = ""
	cardTitle.TextColor3 = P.White; cardTitle.TextScaled = true; cardTitle.TextXAlignment = Enum.TextXAlignment.Left
	cardTitle.Parent = card; Theme.TextStroke(cardTitle, 2)
	local tc = Instance.new("UITextSizeConstraint"); tc.MaxTextSize = 24; tc.Parent = cardTitle
	cardPips = Instance.new("Frame"); cardPips.BackgroundTransparency = 1; cardPips.AnchorPoint = Vector2.new(0, 1)
	cardPips.Position = UDim2.new(0, 16, 1, -8); cardPips.Size = UDim2.fromOffset(200, 12); cardPips.Parent = card
	local pl = Instance.new("UIListLayout"); pl.FillDirection = Enum.FillDirection.Horizontal
	pl.Padding = UDim.new(0, 6); pl.Parent = cardPips
	for i = 1, TOTAL_STEPS do
		local dot = Instance.new("Frame"); dot.Name = "Pip" .. i; dot.Size = UDim2.fromOffset(28, 8)
		dot.BackgroundColor3 = P.PanelInner; dot.BorderSizePixel = 0; dot.LayoutOrder = i; dot.Parent = cardPips
		Theme.Corner(dot, UDim.new(1, 0))
	end
	local skip = Instance.new("TextButton")
	skip.AnchorPoint = Vector2.new(1, 1); skip.Position = UDim2.new(1, -12, 1, -8); skip.Size = UDim2.fromOffset(80, 22)
	skip.BackgroundTransparency = 1; skip.Font = Theme.Font.Body; skip.Text = "Passer ✕"; skip.TextColor3 = P.Muted
	skip.TextScaled = true; skip.Parent = card
	TutorialController._skipBtn = skip
end

local function setCard(title: string, stepIndex: number)
	cardTitle.Text = title
	for i = 1, TOTAL_STEPS do
		local dot = cardPips:FindFirstChild("Pip" .. i)
		if dot then dot.BackgroundColor3 = (i < stepIndex) and P.Confirm or (i == stepIndex and P.Gold or P.PanelInner) end
	end
	if not card.Visible then
		card.Visible = true
		card.Position = UDim2.new(0.5, 0, 1, 20)
		TweenService:Create(card, TweenInfo.new(0.3, Enum.EasingStyle.Back, Enum.EasingDirection.Out), { Position = UDim2.new(0.5, 0, 1, -92) }):Play()
	end
	FXKit.playSound(FXKit.SOUNDS.ding, nil, 0.4)
end

TutorialController._showProposal = showProposal
TutorialController._mountCard = mountCard
TutorialController._setCard = setCard

function TutorialController:Start()
	-- Step machine wired in Task 6.
end

return TutorialController
```

- [ ] **Step 2: Verify render.** Temporarily call `TutorialController._mountCard()` + `_setCard("Test objectif", 2)` + `_showProposal(function() end, function() end)` from a temp client snippet in Play; `screen_capture`; confirm the centered proposal panel (title, body, two buttons) and the bottom card with 4 pips (pip 1 green, pip 2 gold) render in the cartoon Theme. Confirm `Theme.Panel`/`Theme.Button` returns match the field names used (`parts.content`, `parts.card`, button `MouseButton1Click`). Clean up the temp GUIs.

- [ ] **Step 3: Commit** (`git commit -m "feat(tutorial): TutorialController proposal popup + step card shell"`).

---

### Task 6: `TutorialController` — step machine wiring (the 4 actions)

**Files:**
- Modify: `Controllers.TutorialController` (add the step machine + `Start` logic).
- Delete: `Controllers.OnboardingController`.

**Interfaces:**
- Consumes: `tutorialStatus`/`tutorialSkip`/`tutorialFinish` remotes (Task 3); `state.meta.funnelFlags`; `GuideFX`; `PlotController`.
- Produces: a running tutorial. On all-flags-complete → calls `tutorialFinish` → triggers Task 7 celebration.

- [ ] **Step 1: Add the step definitions + helpers** (insert above `function TutorialController:Start()`):

```lua
local StateController = Registry.controllers["StateController"]
local PlotController = Registry.controllers["PlotController"]

local currentGuides: { any } = {}
local function clearGuides()
	GuideFX.clearAll()
	currentGuides = {}
end
local function keep(h) table.insert(currentGuides, h); return h end

-- Equip the starter pince so the player only needs to walk + press E (hero moment, no fumbling).
local function equipPince()
	local char = player.Character
	local hum = char and char:FindFirstChildOfClass("Humanoid")
	if not hum then return end
	if char:FindFirstChildOfClass("Tool") then return end -- already holding something
	local bp = player:FindFirstChildOfClass("Backpack")
	if not bp then return end
	for _, t in ipairs(bp:GetChildren()) do
		if t:IsA("Tool") and t:GetAttribute("Kind") == "pince" then hum:EquipTool(t); return end
	end
end

local function slotPart()
	local plot = PlotController.getPlot()
	return plot and plot:FindFirstChild("Slot_s1")
end
local function machinePart()
	local m = PlotController.getUFO("s1")
	return m and (m.PrimaryPart or m:FindFirstChildWhichIsA("BasePart"))
end
local function sellPad()
	local plot = PlotController.getPlot()
	return plot and plot:FindFirstChild("SellPad")
end
local function ameliosBtn()
	local hud = player:WaitForChild("PlayerGui"):FindFirstChild("MainHUD")
	local sidebar = hud and hud:FindFirstChild("Sidebar")
	return sidebar and sidebar:FindFirstChild("AmeliosBtn")
end

-- Each step: flag = the funnel flag that marks it done; begin() draws the guidance.
local STEPS = {
	{
		flag = "first_ufo_placed",
		title = "🦾 Pose ta pince : va au socle qui brille et appuie sur E",
		begin = function()
			equipPince()
			local p = slotPart()
			if p then keep(GuideFX.highlight(p)); keep(GuideFX.worldArrow(p)); keep(GuideFX.groundRing(p)) end
			keep(GuideFX.offscreenIndicator(function() local s = slotPart(); return s and s.Position end))
		end,
	},
	{
		flag = "first_item_caught",
		title = "✨ Ta pince ramasse la ferraille toute seule — regarde !",
		begin = function()
			local p = machinePart()
			if p then keep(GuideFX.highlight(p)); keep(GuideFX.worldArrow(p)) end
		end,
	},
	{
		flag = "first_item_sold",
		title = "💰 Va voir le vendeur et vends ta ferraille (tout)",
		begin = function()
			local p = sellPad()
			if p then keep(GuideFX.worldArrow(p)); keep(GuideFX.groundRing(p)) end
			keep(GuideFX.offscreenIndicator(function() local s = sellPad(); return s and s.Position end))
		end,
	},
	{
		flag = "first_upgrade_bought",
		title = "⚡ Ouvre Améliorations et booste ta pince",
		begin = function()
			local b = ameliosBtn()
			if b then keep(GuideFX.spotlight(b)); keep(GuideFX.screenPointer(b)); keep(GuideFX.pulse(b)) end
		end,
	},
}

local function flagsOf(state)
	return (state and state.meta and state.meta.funnelFlags) or {}
end
-- index of the first incomplete step (1..4), or 5 when all done.
local function stepIndexFor(flags)
	for i, s in ipairs(STEPS) do
		if not flags[s.flag] then return i end
	end
	return TOTAL_STEPS + 1
end
```

- [ ] **Step 2: Add the run loop in `Start`** (replace the placeholder `Start`):

```lua
function TutorialController:Start()
	-- Wait for state + ask the server whether to offer the tutorial.
	task.spawn(function()
		PlotController.waitForPlot(30)
		local res = Net.request("tutorialStatus")
		if not (res and res.ok and res.data and res.data.shouldOffer) then
			return -- already done/skipped: stay silent
		end
		showProposal(function() -- C'est parti
			active = true
			mountCard()
			TutorialController._run()
		end, function() -- Passer
			Net.request("tutorialSkip")
		end)
	end)

	-- Celebration handler (Task 7 fills celebrate()).
	Net.onEvent("tutorialReward", function(data)
		TutorialController._celebrate(data and data.defId or "rare_1")
	end)
end

local lastIndex = 0
local finishing = false
function TutorialController._run()
	if not active then return end
	-- wire the card skip button
	if TutorialController._skipBtn then
		TutorialController._skipBtn.MouseButton1Click:Connect(function()
			active = false; clearGuides(); if gui then gui:Destroy() end
			Net.request("tutorialSkip")
		end)
	end
	local function refresh(state)
		if not active then return end
		local flags = flagsOf(state)
		local idx = stepIndexFor(flags)
		if idx > TOTAL_STEPS then
			-- all 4 done → finish once
			if not finishing then
				finishing = true
				clearGuides()
				card.Visible = false
				task.spawn(function() Net.request("tutorialFinish") end) -- server fires "tutorialReward"
			end
			return
		end
		if idx ~= lastIndex then
			lastIndex = idx
			clearGuides()
			-- success burst for the step we just finished (if any), at the player
			if idx > 1 then
				local hrp = player.Character and player.Character:FindFirstChild("HumanoidRootPart")
				if hrp then FXKit.burst(hrp.CFrame, P.Confirm, 2, false); FXKit.playSound(FXKit.SOUNDS.clamp, hrp, 0.5) end
			end
			setCard(STEPS[idx].title, idx)
			STEPS[idx].begin()
		end
	end
	StateController.onChanged(refresh)
	refresh(StateController.get())
end
```

- [ ] **Step 3: Add a temporary stub for `_celebrate`** (replaced in Task 7) so Task 6 runs standalone:

```lua
function TutorialController._celebrate(defId)
	active = false
	clearGuides()
	if gui then gui:Destroy() end
end
```

- [ ] **Step 4: Verify the edits applied** — `script_read` `TutorialController`; confirm `STEPS` has 4 entries with the exact flags `first_ufo_placed`/`first_item_caught`/`first_item_sold`/`first_upgrade_bought`, and `Start` calls `tutorialStatus`.

- [ ] **Step 5: Delete `OnboardingController`.** `inspect_instance` to confirm path `...Controllers.OnboardingController`, then remove it (via `multi_edit` delete or `execute_luau`: `game.StarterPlayer.StarterPlayerScripts.Client.Controllers.OnboardingController:Destroy()`). Re-inspect to confirm it's gone (so the loader no longer mounts the old hint line).

- [ ] **Step 6: Play-test the spine (manual).** Reopen as a fresh profile is hard in Studio (data persists); instead use a temp server Script to reset the local player's `data.meta.tutorialDone=false`, clear the 4 funnel flags, unplace `s1`, and `DataService.replicate`. Enter Play → the proposal appears → click "C'est parti" → step 1 card + slot guidance show. Walk to the socket, press E → step 1 burst, card advances to step 2 → watch a catch → advances → walk to vendor, sell → advances → open Améliorations, buy → card hides + `tutorialFinish` called (console shows reward grant). `screen_capture` at 2–3 steps. (Full celebration in Task 7.)

- [ ] **Step 7: Commit** (`git commit -m "feat(tutorial): step machine wiring + remove OnboardingController"`).

---

### Task 7: Conclusion — celebration + rare pince reveal + place-machine-#2 hand-off

**Files:**
- Modify: `Controllers.TutorialController` (replace `_celebrate`).

**Interfaces:**
- Consumes: `ClawPreview.make(defId, prestige, parent)`, `FXKit`, `GuideFX`, `Theme`, `PlotController`.

- [ ] **Step 1: Replace `_celebrate`** with the full conclusion:

```lua
function TutorialController._celebrate(defId)
	clearGuides()
	if card then card.Visible = false end
	local pg = player:WaitForChild("PlayerGui")
	local sg = Instance.new("ScreenGui")
	sg.Name = "TutorialReward"; sg.ResetOnSpawn = false; sg.IgnoreGuiInset = true; sg.DisplayOrder = 95
	sg.Parent = pg
	local overlay = Instance.new("Frame")
	overlay.Size = UDim2.fromScale(1, 1); overlay.BackgroundColor3 = Color3.new(0, 0, 0)
	overlay.BackgroundTransparency = 0.35; overlay.BorderSizePixel = 0; overlay.Parent = sg
	local parts = Theme.Panel({ parent = sg, title = "🏆 PINCE RARE DÉBLOQUÉE !", size = UDim2.fromOffset(420, 420) })
	local content = parts.content
	-- 3D preview of the reward pince
	local holder = Instance.new("Frame"); holder.BackgroundColor3 = P.PanelInner; holder.BorderSizePixel = 0
	holder.Size = UDim2.fromOffset(240, 240); holder.Position = UDim2.new(0.5, -120, 0, 6); holder.Parent = content
	Theme.Corner(holder, UDim.new(0, 12)); Theme.Stroke(holder, P.Gold, 3)
	local ok, preview = pcall(function() return Registry.controllers["ClawPreview"].make(defId, 0, holder) end)
	local sub = Instance.new("TextLabel"); sub.BackgroundTransparency = 1; sub.Position = UDim2.fromOffset(0, 256)
	sub.Size = UDim2.new(1, 0, 0, 56); sub.Font = Theme.Font.Body; sub.TextColor3 = P.White; sub.TextScaled = true
	sub.TextWrapped = true; sub.Text = "Elle est dans ton sac. Pose-la dans un 2e socle et fais grossir ton atelier !"
	sub.Parent = content
	local sc = Instance.new("UITextSizeConstraint"); sc.MaxTextSize = 20; sc.Parent = sub
	local go = Theme.Button({ parent = content, text = "À MOI DE JOUER !", color = P.Confirm,
		size = UDim2.new(1, 0, 0, 54), position = UDim2.fromOffset(0, 318), maxTextSize = 24 })

	-- juice
	local hrp = player.Character and player.Character:FindFirstChild("HumanoidRootPart")
	if hrp then FXKit.explode(hrp.CFrame + Vector3.new(0, 3, 0), P.Gold); FXKit.shake(0.5, 0.5) end
	FXKit.playSound(FXKit.SOUNDS.jackpot, nil, 0.9)
	local cardScale = parts.card:FindFirstChildOfClass("UIScale") or Instance.new("UIScale")
	cardScale.Parent = parts.card; cardScale.Scale = 0.6
	TweenService:Create(cardScale, TweenInfo.new(0.3, Enum.EasingStyle.Back, Enum.EasingDirection.Out), { Scale = 1 }):Play()

	local function finishUp()
		sg:Destroy()
		active = false
		if gui then gui:Destroy() end
		-- soft hand-off: point at the free 2nd slot for a few seconds, then release.
		local plot = PlotController.getPlot()
		local s2 = plot and plot:FindFirstChild("Slot_s2")
		if s2 then
			local h1 = GuideFX.worldArrow(s2, P.Gold)
			local h2 = GuideFX.groundRing(s2, P.Gold)
			task.delay(12, function() pcall(function() h1:Destroy() end); pcall(function() h2:Destroy() end) end)
		end
	end
	go.MouseButton1Click:Connect(finishUp)
	task.delay(8, function() if sg.Parent then finishUp() end end) -- auto-release safeguard
end
```

- [ ] **Step 2: Verify reward reveal.** Continue the Play session from Task 6 (or re-trigger): on buying the upgrade, the reward panel appears with the spinning `rare_1` pince in the `ClawPreview` ViewportFrame, gold framing, confetti/explode FX, "À MOI DE JOUER!" button. Click it → panel closes, a gold arrow+ring appears on `Slot_s2` for ~12s, then clears. `screen_capture` the reveal. Confirm the pince Tool `rare_1` is now in the Backpack (`inspect_instance` `player.Backpack`).

- [ ] **Step 3: Commit** (`git commit -m "feat(tutorial): celebration + rare pince reveal + place-#2 hand-off"`).

---

### Task 8: End-to-end verification, edge cases, optimization & Ctrl+S

**Files:** none (verification only) + any fixes found.

- [ ] **Step 1: Full happy-path playthrough.** Temp server Script resets the local profile (`tutorialDone=false`, clear the 4 flags, unplace `s1`, replicate). Play from spawn: proposal → place (E) → catch → sell → upgrade → reward → place #2. Confirm each step's guidance appears/clears correctly and the card pips advance (green=done, gold=current). Capture 4–5 screenshots.

- [ ] **Step 2: Skip path.** Reset profile again; Play; click **Passer** on the proposal. Confirm: the starter is auto-placed in `s1` (machine appears + starts catching), `data.meta.tutorialDone == true` (temp Script read-back), and no proposal on a second Play.

- [ ] **Step 3: Anti-cheat.** In Play with `tutorialDone=false` and flags cleared, call `Net.request("tutorialFinish")` from a temp client snippet → expect `{ok=false, err="incomplete:first_ufo_placed"}` and **no** `rare_1` in `data.ufos`.

- [ ] **Step 4: Rejoin/idempotency.** With `tutorialDone=true`, Play → no proposal; `tutorialStatus` returns `shouldOffer=false`. Confirm `grantStarterIfNeeded` would auto-place for such a profile (the starter is placed, not floating in the bag).

- [ ] **Step 5: Cleanup sweep.** Confirm `GuideFX.clearAll()` leaves zero residue: `inspect_instance` `PlayerGui` (no `Guide*`, `Tutorial*` ScreenGuis after completion) and `workspace` (no `GuideRing` parts). Confirm no `RenderStepped` leak (the handles disconnect on Destroy).

- [ ] **Step 6: Mobile/perf sanity.** Confirm only a small number of `Highlight`s exist at once (≤ 2), `BillboardGui`s are `AlwaysOnTop` with bounded count, and the spotlight scrim uses 4 frames (not a per-pixel mask). No errors in `get_console_output` across a full run.

- [ ] **Step 7: Final screenshots + report.** Capture the proposal, two mid-steps (world + screen guidance), and the reward reveal. Summarize what shipped; **remind the user to press Ctrl+S** in Studio to persist all of it into `build.rbxlx`. Offer to update the auto-memory (`playtime-rewards-system`-style note) and commit the plan progress.

- [ ] **Step 8: Commit** (`git commit -m "test(tutorial): end-to-end + edge-case verification"`).

---

## Self-Review

- **Spec coverage:**
  - Proposal opt-in + announces reward + skippable → Task 5 (`showProposal`) + Task 6 `Start`/skip + Task 3 `tutorialSkip`. ✓
  - Hero "place your own pince" first → Task 2 (gate auto-place) + Task 6 step 1 (`equipPince` + slot guidance). ✓
  - 4 action steps gated on real funnel flags → Task 6 `STEPS`. ✓
  - Visual guidance (arrows/rings/highlights/offscreen/spotlight/pointer/pulse) → Task 4 `GuideFX`, used per step in Task 6. ✓
  - Per-step feedback + progression pops + final celebration → Task 6 (`setCard`/burst) + Task 7 (`_celebrate`). ✓
  - Reward = guaranteed-rare pince + place machine #2 (`s2` free) → Task 3 (`rare_1` grant) + Task 7 (reveal + `Slot_s2` hand-off). ✓
  - Server-authoritative, grant-once, persisted, anti-cheat → Task 3 (`tutorialFinish` validates flags + `tutorialDone`). ✓
  - Non-replayable, auto first-join only → Task 6 (`tutorialStatus.shouldOffer`); no replay button built. ✓
  - Replace abandoned OnboardingController → Task 6 Step 5. ✓
  - Edge: disconnect mid-tutorial re-offers (flags persist, step machine derives index) → Task 6 `stepIndexFor`. ✓
  - Env caveat (server scripts absent) → Task 1 Step 1. ✓
- **Placeholder scan:** none. `_celebrate` has a deliberate stub in Task 6 Step 3 that is fully replaced in Task 7 (flagged as such). All FX/UI/world targets are real symbols.
- **Type/name consistency:** flags match across Tasks 3 & 6 (`first_ufo_placed`/`first_item_caught`/`first_item_sold`/`first_upgrade_bought`); `tutorialStatus`/`tutorialSkip`/`tutorialFinish` + `tutorialReward` event consistent Task 3 ↔ Task 6; `GuideFX` method names (`highlight`/`worldArrow`/`groundRing`/`offscreenIndicator`/`screenPointer`/`spotlight`/`pulse`/`clearAll`) consistent Task 4 ↔ Task 6/7; reward `rare_1` consistent Task 3 ↔ Task 7; Theme/Palette keys (`P.Confirm`, `P.Gold`, `Theme.Panel/Button`) match the verified `UIController`/`ScrapyardController` usage.
- **Risk note:** `Theme.Panel` return fields (`card`/`content`/`close`) and `Theme.Button` are used per observed call-sites; Task 5 Step 2 verifies them live before deeper UI work, so a mismatch is caught early.
