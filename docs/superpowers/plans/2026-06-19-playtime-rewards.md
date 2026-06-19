# Récompenses de temps de jeu — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. NOTE: code lives inside a connected Roblox Studio instance (MCP), edited SEQUENTIALLY against one DataModel — do NOT parallelize across worktrees. "Tests" = `execute_luau` (edit VM, for pure config) / temp-Script-in-Play + `get_console_output` (for live services) / Play-mode visual + `inspect_instance`. "Commit" = Studio save (Ctrl+S) milestone; git tracks docs only.

**Goal:** Add a session-only "Playtime Rewards" menu (sidebar button → premium Theme popup, 12 time-gated reward cards) with a new timed-boost system, server-authoritative claims, zero persistence.

**Architecture:** Two new server services (`BoostService`, `PlaytimeRewardsService`) + one config (`PlaytimeRewards`) + two client controllers (`PlaytimeRewardsController`, `BoostHUDController`). Boosts are ADDITIVE, read by `CatchService`/`InventoryService` via `BoostService` accessors. Reward unlock = client-side countdown from a server-sent session origin; claim validated server-side. Cash is FIXED & small (farm-safe by size); loot/egg/pet rewards are stage-indexed at grant time.

**Tech Stack:** Luau, Roblox; existing patterns — `Registry` service locator, `Net` wrapper (3 remotes), `DataService.onReady/onRemoving`, `Theme` UI module, auto-boot of `Server.Services` and `Client.Controllers`.

## Global Constraints

- **Zero persistence**: session state only (`sess[player]`, `active[player]`), init in `DataService.onReady`, cleared in `DataService.onRemoving`. Nothing written to `DataService`/ProfileStore.
- **No new RemoteEvents**: reuse `Net` (events `playtimeInit`, `boostsChanged`; requests `getPlaytimeState`, `claimPlaytimeReward`).
- **Server authoritative**: claims validated server-side (`elapsed >= unlock` against server `joinedAt`, `not claimed[tier]`). Anti-double-claim via `claimed[tier]`.
- **Currency id** = `"scrap"` (the `$`). Grants only via `EconomyService.add` / `InventoryService.addItem` / `PetService.grant` / `eggsInv`+`replicate` / `CollectibleService.prizeRain`.
- **Boosts ADDITIVE** (never literal ×2): cash `+1.0` into sellMult sum; yield `+0.30`; speed `grabSpeed/1.25`; luck `+max(0.6, 0.25·luck)`. Never shorten an active boost; sweep expiry on Heartbeat.
- **Sibling services resolved lazily** via `Registry.services.X` (nil-safe) or `Registry.get("X")` — never top-of-file require of sibling services.
- **MCP gotcha**: after every script create/edit, verify by `script_read`/`inspect_instance` read-back; don't trust silent success.

## File Structure

| Path (Studio dot-notation) | Responsibility |
|---|---|
| `ReplicatedStorage.Shared.Config.PlaytimeRewards` (new ModuleScript) | The 12-tier reward table + `client()` view + `get(tier)`. Single source of truth for amounts/durations. |
| `ServerScriptService.Server.Services.BoostService` (new ModuleScript) | Timed session buffs: `grant`, accessors (`cashAdd/yieldAdd/speedFactor/luckAdd`), `getActive`, Heartbeat expiry sweep, push `boostsChanged`. |
| `ServerScriptService.Server.Services.CatchService` (edit) | Read boost accessors: luck (after `effectiveStats`), yield (`yieldChance`), cash (crit `sellMultTotal`), speed (`grabSpeed` scheduling). |
| `ServerScriptService.Server.Services.InventoryService` (edit) | Read cash boost into `sellStack` sellMult sum. |
| `ServerScriptService.Server.Services.PlaytimeRewardsService` (new ModuleScript) | Session timer state, `getPlaytimeState`/`claimPlaytimeReward` handlers, grant dispatch + stage-indexing helpers. |
| `StarterPlayer.StarterPlayerScripts.Client.Controllers.PlaytimeRewardsController` (new ModuleScript) | The popup (Theme.Panel + 12 cards), local countdowns, claim FX, sidebar button clone + ready-badge. |
| `StarterPlayer.StarterPlayerScripts.Client.Controllers.BoostHUDController` (new ModuleScript) | Active-boost pills on the HUD (countdown, pulse <10s). |

No edit to `UIController` or `StarterGui` (the sidebar button is cloned at runtime by the controller → no static-tree MCP edit, persists across respawns via re-clone guard).

---

### Task 1: Config `PlaytimeRewards`

**Files:** Create `ReplicatedStorage.Shared.Config.PlaytimeRewards` (ModuleScript).

**Interfaces:**
- Produces: `PlaytimeRewards.tiers` (array of 12), `PlaytimeRewards.client()` → client-safe array, `PlaytimeRewards.get(tier)` → entry.
- Entry fields: `tier, unlock, type, visual, name, icon, desc?, cash?, boostKind?, boostKinds?, boostDur?, lootOffset?, lootCount?, rainFloor?`.

- [ ] **Step 1: Create the ModuleScript with this exact source**

```lua
--!strict
-- PlaytimeRewards.luau
-- Config des récompenses de temps de jeu (SESSION-only, zéro persistance).
-- Cash FIXE (non farmable par sa taille). Boosts additifs. Objets indexés à l'attribution (serveur).

local PlaytimeRewards = {}

local BOOST_CASH_DUR = 300    -- 5 min
local BOOST_LUCK_DUR = 480    -- 8 min
local BOOST_DOUBLE_DUR = 480  -- 8 min

-- type ∈ "cash" | "boost" | "boost_double" | "prize_rain" | "loot" | "egg" | "pet_jackpot"
-- visual ∈ "normal" | "rare" | "premium"
PlaytimeRewards.tiers = {
	{ tier = 1,  unlock = 60,   type = "cash",         visual = "normal",  cash = 1000,   name = "Première Prime",     icon = "cash" },
	{ tier = 2,  unlock = 180,  type = "boost",        visual = "normal",  boostKind = "cash", boostDur = BOOST_CASH_DUR, name = "Boost ×2 Cash",  icon = "boost_cash",   desc = "x2 Cash - 5 min" },
	{ tier = 3,  unlock = 360,  type = "cash",         visual = "normal",  cash = 5000,   name = "Prime de Ferraille", icon = "cash" },
	{ tier = 4,  unlock = 660,  type = "loot",         visual = "rare",    lootOffset = 1, lootCount = 3, name = "Cache Rare",     icon = "loot" },
	{ tier = 5,  unlock = 1020, type = "boost",        visual = "rare",    boostKind = "luck", boostDur = BOOST_LUCK_DUR, name = "Boost Chance",  icon = "boost_luck",   desc = "+Chance - 8 min" },
	{ tier = 6,  unlock = 1440, type = "prize_rain",   visual = "rare",    rainFloor = 6000, name = "Pluie de Lots",    icon = "cash" },
	{ tier = 7,  unlock = 1980, type = "cash",         visual = "rare",    cash = 75000,  name = "Jackpot Ferrailleur", icon = "cash" },
	{ tier = 8,  unlock = 2580, type = "egg",          visual = "premium", name = "Œuf Mystère",        icon = "egg" },
	{ tier = 9,  unlock = 3300, type = "boost_double", visual = "premium", boostKinds = {"yield","speed"}, boostDur = BOOST_DOUBLE_DUR, name = "Double Boost", icon = "boost_double", desc = "Rendement +30% & Vitesse +25% - 8 min" },
	{ tier = 10, unlock = 4020, type = "cash",         visual = "premium", cash = 250000, name = "Gros Lot Premium",   icon = "cash" },
	{ tier = 11, unlock = 4740, type = "loot",         visual = "premium", lootOffset = 2, lootCount = 2, name = "Coffre Légendaire", icon = "loot" },
	{ tier = 12, unlock = 5400, type = "pet_jackpot",  visual = "premium", cash = 500000, name = "JACKPOT FINAL",      icon = "pet",          desc = "Pet + Magot" },
}

function PlaytimeRewards.client()
	local out = {}
	for _, t in ipairs(PlaytimeRewards.tiers) do
		out[#out + 1] = {
			tier = t.tier, unlock = t.unlock, type = t.type, visual = t.visual,
			name = t.name, icon = t.icon, desc = t.desc, cash = t.cash, lootCount = t.lootCount,
		}
	end
	return out
end

function PlaytimeRewards.get(tier: number)
	return PlaytimeRewards.tiers[tier]
end

return PlaytimeRewards
```

- [ ] **Step 2: Verify it exists & loads** — `inspect_instance game.ReplicatedStorage.Shared.Config.PlaytimeRewards`; then `execute_luau` (edit VM): `local M = require(game.ReplicatedStorage.Shared.Config.PlaytimeRewards); assert(#M.tiers==12); assert(M.get(12).cash==500000); assert(#M.client()==12); print("OK", M.get(1).name)`. Expected: `OK Première Prime`.

- [ ] **Step 3: Save (Ctrl+S milestone).**

---

### Task 2: `BoostService`

**Files:** Create `ServerScriptService.Server.Services.BoostService` (ModuleScript).

**Interfaces:**
- Consumes: `Registry.get("DataService")` (`onReady`/`onRemoving`), `Net.sendEvent`.
- Produces: `BoostService.grant(player, kind, durationSec)`, `BoostService.cashAdd(player)→0|1.0`, `BoostService.yieldAdd(player)→0|0.30`, `BoostService.speedFactor(player)→1.0|1.25`, `BoostService.luckAdd(player, baseLuck)→0|max(0.6,0.25·baseLuck)`, `BoostService.getActive(player)→{{kind,remaining}}`. `kind ∈ "cash"|"luck"|"yield"|"speed"`.

- [ ] **Step 1: Create the ModuleScript with this exact source**

```lua
--!strict
-- BoostService.luau
-- Buffs temporés de SESSION (jamais persistés). Lus par CatchService/InventoryService.
-- Identité si inactif : 0 (additif cash/luck/yield), 1.0 (multiplicatif speed).

local RunService = game:GetService("RunService")
local Shared = game:GetService("ReplicatedStorage"):WaitForChild("Shared")
local ServerRoot = script.Parent.Parent
local Registry = require(ServerRoot.Registry)
local Net = require(Shared.Net.Net)

local BoostService = {}

local CASH_ADD = 1.0       -- +100% additif dans la somme sellMult
local YIELD_ADD = 0.30     -- +0.30 yieldChance
local SPEED_FACTOR = 1.25  -- grabSpeed / 1.25 (+25% cadence)
-- luck : additif scalé = max(0.6, 0.25 * luck courante)

local active: { [Player]: { [string]: number } } = {}

local function clk() return os.clock() end
local function isActive(player: Player, kind: string): boolean
	local a = active[player]
	return a ~= nil and a[kind] ~= nil and a[kind] > clk()
end

function BoostService.push(player: Player)
	Net.sendEvent(player, "boostsChanged", BoostService.getActive(player))
end

function BoostService.grant(player: Player, kind: string, durationSec: number)
	local a = active[player]
	if not a then a = {}; active[player] = a end
	local expiry = clk() + durationSec
	local cur = a[kind]
	a[kind] = (cur and cur > expiry) and cur or expiry  -- ne raccourcit jamais
	BoostService.push(player)
end

function BoostService.cashAdd(player: Player): number
	return isActive(player, "cash") and CASH_ADD or 0
end
function BoostService.yieldAdd(player: Player): number
	return isActive(player, "yield") and YIELD_ADD or 0
end
function BoostService.speedFactor(player: Player): number
	return isActive(player, "speed") and SPEED_FACTOR or 1.0
end
function BoostService.luckAdd(player: Player, baseLuck: number): number
	return isActive(player, "luck") and math.max(0.6, 0.25 * baseLuck) or 0
end

function BoostService.getActive(player: Player)
	local out = {}
	local a = active[player]
	if a then
		local t = clk()
		for kind, exp in pairs(a) do
			if exp > t then out[#out + 1] = { kind = kind, remaining = math.floor(exp - t + 0.5) } end
		end
	end
	return out
end

function BoostService:Start()
	local DataService = Registry.get("DataService")
	DataService.onReady(function(player)
		active[player] = {}
		BoostService.push(player)
	end)
	DataService.onRemoving(function(player)
		active[player] = nil
	end)
	local accum = 0
	RunService.Heartbeat:Connect(function(dt)
		accum += dt
		if accum < 1 then return end
		accum = 0
		local t = clk()
		for player, a in pairs(active) do
			local changed = false
			for kind, exp in pairs(a) do
				if exp <= t then a[kind] = nil; changed = true end
			end
			if changed then pcall(BoostService.push, player) end
		end
	end)
end

return BoostService
```

- [ ] **Step 2: Verify** — `inspect_instance game.ServerScriptService.Server.Services.BoostService`; confirm source via `script_read`. (Behavior is tested end-to-end in Task 7.)

- [ ] **Step 3: Save (Ctrl+S).**

---

### Task 3: Boost read-hooks in `CatchService` + `InventoryService`

**Files:** Edit `ServerScriptService.Server.Services.InventoryService` (line 69), `ServerScriptService.Server.Services.CatchService` (after 152, line 174, line 196, line 242).

**Interfaces:** Consumes `Registry.services.BoostService` (nil-safe) accessors from Task 2.

- [ ] **Step 1: InventoryService.sellStack — add cash boost into the sellMult sum.**
Read `InventoryService` around line 69 to confirm exact text, then replace the single `earned` line:
```lua
	local earned = math.floor(unit * n * (1 + Crafts.bonus(d, "sellMult") + Upgrades.sellBonus(d.upgrades) + Pets.sellBonus(d)) + 0.5) -- Fonderie craft + Prix de Revente (Amélios) + pets
```
with:
```lua
	local boostCash = (Registry.services.BoostService and Registry.services.BoostService.cashAdd(player)) or 0
	local earned = math.floor(unit * n * (1 + Crafts.bonus(d, "sellMult") + Upgrades.sellBonus(d.upgrades) + Pets.sellBonus(d) + boostCash) + 0.5) -- + Boost Cash (temporé)
```

- [ ] **Step 2: CatchService crit (line ~196) — add cash boost into `sellMultTotal`.** Replace:
```lua
		local sellMultTotal = 1 + Crafts.bonus(data, "sellMult") + Upgrades.sellBonus(data.upgrades) + Pets.sellBonus(data)
```
with:
```lua
		local boostCash = (Registry.services.BoostService and Registry.services.BoostService.cashAdd(player)) or 0
		local sellMultTotal = 1 + Crafts.bonus(data, "sellMult") + Upgrades.sellBonus(data.upgrades) + Pets.sellBonus(data) + boostCash
```

- [ ] **Step 3: CatchService doGrab (after line 152) — luck boost.** After:
```lua
	local stats = effectiveStats(data, ufoDef, level, prestige)
```
insert:
```lua
	do local _bs = Registry.services.BoostService; if _bs then stats.luck = stats.luck + _bs.luckAdd(player, stats.luck) end end
```

- [ ] **Step 4: CatchService doGrab (line ~174) — yield boost.** Replace:
```lua
	local yieldChance = 0.03 * ((data.upgrades and data.upgrades.yield) or 0) + Pets.bonusValue(data, "yield")
```
with:
```lua
	local yieldChance = 0.03 * ((data.upgrades and data.upgrades.yield) or 0) + Pets.bonusValue(data, "yield")
		+ ((Registry.services.BoostService and Registry.services.BoostService.yieldAdd(player)) or 0)
```

- [ ] **Step 5: CatchService tick (line ~242) — speed boost on cadence.** Replace:
```lua
							schedule[slotId] = now + stats.grabSpeed
```
with:
```lua
							local _sf = (Registry.services.BoostService and Registry.services.BoostService.speedFactor(player)) or 1
							schedule[slotId] = now + stats.grabSpeed / _sf
```

- [ ] **Step 6: Verify** — `script_read` each edited region back to confirm the 5 insertions are present and not duplicated/no-opped (MCP gotcha). Confirm no syntax error (check `get_console_output` after a Play start in Task 7).

- [ ] **Step 7: Save (Ctrl+S).**

---

### Task 4: `PlaytimeRewardsService`

**Files:** Create `ServerScriptService.Server.Services.PlaytimeRewardsService` (ModuleScript).

**Interfaces:**
- Consumes: `PlaytimeRewards` config; `Registry.get("DataService"/"EconomyService"/"BoostService"/"CollectibleService"/"InventoryService"/"PetService")`; configs `UFOCatchers`, `Rarities`, `Eggs`, `PetRarities`, `Pets`; `Id.new()`. Events/requests via `Net`.
- Produces: server handlers `getPlaytimeState`, `claimPlaytimeReward`; event `playtimeInit`.

- [ ] **Step 1: Create the ModuleScript with this exact source**

```lua
--!strict
-- PlaytimeRewardsService.luau
-- Récompenses de temps de jeu : état de session (joinedAt/claimed), claim autoritaire,
-- attribution + indexation par stade. ZÉRO persistance.

local Shared = game:GetService("ReplicatedStorage"):WaitForChild("Shared")
local ServerRoot = script.Parent.Parent
local Registry = require(ServerRoot.Registry)
local Net = require(Shared.Net.Net)

local PlaytimeRewards = require(Shared.Config.PlaytimeRewards)
local UFOCatchers = require(Shared.Config.UFOCatchers)
local Rarities = require(Shared.Config.Rarities)
local Eggs = require(Shared.Config.Eggs)
local PetRarities = require(Shared.Config.PetRarities)
local Pets = require(Shared.Config.Pets)
local Id = require(Shared.Util.Id)

local PlaytimeRewardsService = {}

local sess: { [Player]: { joinedAt: number, claimed: { [number]: boolean } } } = {}

local function data(player: Player) return Registry.get("DataService").get(player) end

local function bestClawTier(d): number
	local best = 1
	for _, owned in pairs(d.ufos) do
		local def = UFOCatchers.get(owned.defId)
		if def and def.tier and def.tier > best then best = def.tier end
	end
	return best
end
local function lootRarityId(d, offset: number): string
	local order = math.clamp(math.min(bestClawTier(d), 10) + offset, 1, 10)
	return Rarities.list[order].id
end
local function eggIdFor(d): string
	local idx = math.clamp(bestClawTier(d) - 1, 1, #Eggs.list)
	return Eggs.list[idx].id
end
local function petDefFor(d): string?
	local bestOrder = 0
	for _, owned in pairs(d.pets) do
		local pdef = Pets.get and Pets.get(owned.defId)
		local r = pdef and pdef.rarity and PetRarities.get(pdef.rarity)
		if r and r.order and r.order > bestOrder then bestOrder = r.order end
	end
	local target = PetRarities.list[math.clamp(bestOrder + 1, 1, #PetRarities.list)].id
	if Pets.list then
		for _, pdef in ipairs(Pets.list) do
			if pdef.rarity == target then return pdef.id end
		end
		return Pets.list[1] and Pets.list[1].id or nil
	end
	return nil
end

local function grantReward(player: Player, d, t)
	if t.type == "cash" then
		Registry.get("EconomyService").add(player, "scrap", t.cash)
		return { kind = "cash", amount = t.cash }
	elseif t.type == "boost" then
		Registry.get("BoostService").grant(player, t.boostKind, t.boostDur)
		return { kind = "boost", boostKind = t.boostKind }
	elseif t.type == "boost_double" then
		for _, k in ipairs(t.boostKinds) do
			Registry.get("BoostService").grant(player, k, t.boostDur)
		end
		return { kind = "boost_double" }
	elseif t.type == "prize_rain" then
		local n = Registry.get("CollectibleService").prizeRain(player, 0, t.rainFloor)
		if not n then Registry.get("EconomyService").add(player, "scrap", t.rainFloor * 5) end
		return { kind = "prize_rain" }
	elseif t.type == "loot" then
		local rarity = lootRarityId(d, t.lootOffset)
		local Inv = Registry.get("InventoryService")
		for _ = 1, t.lootCount do
			Inv.addItem(player, { defId = "ufo_core", rarity = rarity, modifier = "none", value = 0, weight = 0, oddsHit = 0 })
		end
		return { kind = "loot", rarity = rarity, count = t.lootCount }
	elseif t.type == "egg" then
		local eggId = eggIdFor(d)
		d.eggsInv[Id.new()] = { eggId = eggId }
		Registry.get("DataService").replicate(player)
		return { kind = "egg", eggId = eggId }
	elseif t.type == "pet_jackpot" then
		local petDef = petDefFor(d)
		if petDef then Registry.get("PetService").grant(player, petDef) end
		Registry.get("EconomyService").add(player, "scrap", t.cash)
		return { kind = "pet_jackpot", petDef = petDef, amount = t.cash }
	end
	return { kind = "unknown" }
end

function PlaytimeRewardsService:Start()
	local DataService = Registry.get("DataService")
	DataService.onReady(function(player)
		sess[player] = { joinedAt = os.clock(), claimed = {} }
		Net.sendEvent(player, "playtimeInit", { schedule = PlaytimeRewards.client(), elapsed = 0 })
	end)
	DataService.onRemoving(function(player)
		sess[player] = nil
	end)

	Net.onRequest("getPlaytimeState", function(player)
		local s = sess[player]
		if not s then return false, "not_ready" end
		local claimed = {}
		for tier in pairs(s.claimed) do claimed[#claimed + 1] = tier end
		return { schedule = PlaytimeRewards.client(), elapsed = os.clock() - s.joinedAt, claimed = claimed }
	end)

	Net.onRequest("claimPlaytimeReward", function(player, payload)
		if typeof(payload) ~= "table" or typeof(payload.tier) ~= "number" then return false, "bad_payload" end
		local s = sess[player]
		if not s then return false, "not_ready" end
		local t = PlaytimeRewards.get(payload.tier)
		if not t then return false, "bad_tier" end
		if s.claimed[t.tier] then return false, "already" end
		if os.clock() - s.joinedAt < t.unlock then return false, "locked" end
		local d = data(player)
		if not d then return false, "no_data" end
		s.claimed[t.tier] = true
		local ok, granted = pcall(grantReward, player, d, t)
		if not ok then
			s.claimed[t.tier] = nil
			return false, "grant_failed"
		end
		return { ok = true, granted = granted }
	end)
end

return PlaytimeRewardsService
```

- [ ] **Step 2: Verify config shapes used by indexing.** `script_read game.ReplicatedStorage.Shared.Config.Pets` — confirm `Pets.list` (array of defs with `.id`,`.rarity`) and `Pets.get(defId).rarity` exist; if the shape differs, adapt `petDefFor` accordingly (fallback already returns nil-safe). Confirm `Eggs.list[i].id`, `Rarities.list[i].id`, `PetRarities.list[i].id`/`.order`, `UFOCatchers.get(defId).tier`.

- [ ] **Step 3: Verify service exists** — `inspect_instance game.ServerScriptService.Server.Services.PlaytimeRewardsService`. (Behavior tested in Task 7.)

- [ ] **Step 4: Save (Ctrl+S).**

---

### Task 5: `PlaytimeRewardsController` (menu UI + button + badge)

**Files:** Create `StarterPlayer.StarterPlayerScripts.Client.Controllers.PlaytimeRewardsController` (ModuleScript).

**Interfaces:**
- Consumes: `Theme`, `ScrapIcons`, `Net` (`onEvent "playtimeInit"`, `request "getPlaytimeState"`/`"claimPlaytimeReward"`), `PlayerGui.MainHUD.Sidebar.IndexBtn` (clone source).
- Produces: `PlaytimeRewardsController.open()/close()`.

- [ ] **Step 1: Create the ModuleScript with this exact source**

```lua
--!strict
-- PlaytimeRewardsController.luau
-- Menu "Récompenses de temps de jeu" : panneau Theme + grille 12 cartes, timers locaux,
-- claim validé serveur. Bouton cloné dans MainHUD.Sidebar + badge de récompenses prêtes.

local Players = game:GetService("Players")
local RunService = game:GetService("RunService")
local TweenService = game:GetService("TweenService")
local RS = game:GetService("ReplicatedStorage")

local Theme = require(RS.UI.Theme)
local P = Theme.Palette
local ScrapIcons = require(RS.Shared.ScrapIcons)
local Net = require(RS.Shared.Net.Net)

local player = Players.LocalPlayer

local Controller = {}

local schedule: any = nil          -- liste config client
local origin: number? = nil        -- os.clock() au début de session (horloge locale)
local claimedSet: { [number]: boolean } = {}
local cards: { [number]: any } = {} -- [tier] = { update = fn, setReady = fn, setClaimed = fn }
local gui: ScreenGui? = nil
local isOpen = false
local badge: TextLabel? = nil

local function tierColor(v: string): Color3
	if v == "premium" then return P.Gold elseif v == "rare" then return P.Purple else return P.Cyan end
end

local function fmtTime(s: number): string
	s = math.max(0, math.floor(s))
	local m = math.floor(s / 60); local sec = s % 60
	if m >= 60 then local h = math.floor(m / 60); m = m % 60; return string.format("%d:%02d:%02d", h, m, sec) end
	return string.format("%02d:%02d", m, sec)
end

local function fmtCash(n: number): string
	local s = tostring(math.floor(n)); local out = ""; local c = 0
	for i = #s, 1, -1 do out = s:sub(i, i) .. out; c += 1; if c % 3 == 0 and i > 1 then out = "," .. out end end
	return "$" .. out
end

local function elapsed(): number
	return origin and (os.clock() - origin) or 0
end

-- ICÔNE : plate teintée + glyphe (loot via ScrapIcons)
local function buildIcon(holder: Instance, t: any, color: Color3)
	local bg = Instance.new("Frame")
	bg.Size = UDim2.fromScale(1, 1); bg.BackgroundColor3 = Theme.darken(color, 0.5)
	bg.BorderSizePixel = 0; bg.Parent = holder
	Theme.Corner(bg, UDim.new(0, 10))
	Theme.Gradient(bg, { color, Theme.darken(color, 0.55) }, 90)
	if t.type == "loot" then
		local h = Instance.new("Frame")
		h.AnchorPoint = Vector2.new(0.5, 0.5); h.Position = UDim2.fromScale(0.5, 0.5)
		h.Size = UDim2.fromScale(0.72, 0.72); h.BackgroundTransparency = 1; h.Parent = holder
		pcall(ScrapIcons.build, h, "ufo_core", color)
	else
		local sym = "$"
		if t.icon == "boost_cash" then sym = "x2"
		elseif t.icon == "boost_luck" then sym = "+%"
		elseif t.icon == "boost_double" then sym = ">>"
		elseif t.icon == "egg" then sym = "O"
		elseif t.icon == "pet" then sym = "<3" end
		local g = Instance.new("TextLabel")
		g.BackgroundTransparency = 1; g.Size = UDim2.fromScale(1, 1)
		g.Font = Theme.Font.Title; g.Text = sym; g.TextColor3 = P.White; g.TextScaled = true; g.Parent = holder
		Theme.TextStroke(g, 2)
		local cc = Instance.new("UITextSizeConstraint"); cc.MaxTextSize = 40; cc.Parent = g
	end
end

-- Une carte. Retourne { root, update(now), setClaimed() }
local function buildCard(t: any)
	local color = tierColor(t.visual)
	local root = Instance.new("Frame")
	root.Size = UDim2.fromScale(1, 1); root.BackgroundColor3 = P.PanelInner
	root.BorderSizePixel = 0
	Theme.Corner(root, UDim.new(0, 14))
	local stroke = Theme.Stroke(root, color, t.visual == "premium" and 3 or 2)
	-- ombre
	local shadow = Instance.new("Frame")
	shadow.AnchorPoint = Vector2.new(0.5, 0.5); shadow.Position = UDim2.new(0.5, 0, 0.5, 6)
	shadow.Size = UDim2.fromScale(1, 1); shadow.BackgroundColor3 = P.Outline
	shadow.BackgroundTransparency = 0.5; shadow.BorderSizePixel = 0; shadow.ZIndex = root.ZIndex - 1
	shadow.Parent = root; Theme.Corner(shadow, UDim.new(0, 14))

	-- haut : montant (cash) ou nom
	local top = Instance.new("TextLabel")
	top.BackgroundTransparency = 1; top.Size = UDim2.new(1, -10, 0, 22)
	top.Position = UDim2.fromOffset(5, 6); top.Font = Theme.Font.Title
	top.TextScaled = true; top.TextColor3 = (t.type == "cash" or t.type == "prize_rain") and P.Confirm or P.White
	top.Text = (t.cash and (t.type == "cash" or t.type == "prize_rain")) and fmtCash(t.cash) or t.name
	top.Parent = root; Theme.TextStroke(top, 2)
	local tc = Instance.new("UITextSizeConstraint"); tc.MaxTextSize = 18; tc.Parent = top

	-- plate icône
	local plate = Instance.new("Frame")
	plate.AnchorPoint = Vector2.new(0.5, 0); plate.Position = UDim2.new(0.5, 0, 0, 30)
	plate.Size = UDim2.fromOffset(64, 64); plate.BackgroundTransparency = 1; plate.Parent = root
	buildIcon(plate, t, color)
	-- badge quantité
	if t.lootCount then
		local q = Instance.new("TextLabel")
		q.AnchorPoint = Vector2.new(1, 1); q.Position = UDim2.new(1, -2, 1, -2)
		q.Size = UDim2.fromOffset(24, 16); q.BackgroundTransparency = 1; q.Font = Theme.Font.Title
		q.Text = "x" .. t.lootCount; q.TextColor3 = P.White; q.TextScaled = true; q.ZIndex = 5; q.Parent = plate
		Theme.TextStroke(q, 2)
	end

	-- bas : zone d'état (timer / bouton / stamp)
	local bottom = Instance.new("Frame")
	bottom.AnchorPoint = Vector2.new(0.5, 1); bottom.Position = UDim2.new(0.5, 0, 1, -8)
	bottom.Size = UDim2.new(1, -12, 0, 30); bottom.BackgroundTransparency = 1; bottom.Parent = root

	local timer = Instance.new("TextLabel")
	timer.BackgroundTransparency = 1; timer.Size = UDim2.fromScale(1, 1); timer.Font = Theme.Font.Title
	timer.Text = "--:--"; timer.TextColor3 = P.White; timer.TextScaled = true; timer.Parent = bottom
	Theme.TextStroke(timer, 2)
	local tcc = Instance.new("UITextSizeConstraint"); tcc.MaxTextSize = 20; tcc.Parent = timer

	local claimBtn = Theme.Button({ parent = bottom, text = "Réclamer", color = P.Confirm, size = UDim2.fromScale(1, 1), maxTextSize = 16 })
	claimBtn.Parent.Visible = false  -- Theme.Button returns Face; its parent is the container

	local stamp = Instance.new("TextLabel")
	stamp.BackgroundTransparency = 1; stamp.Size = UDim2.fromScale(1, 1); stamp.Font = Theme.Font.Title
	stamp.Text = "RÉCLAMÉ"; stamp.TextColor3 = P.Muted; stamp.TextScaled = true; stamp.Visible = false; stamp.Parent = bottom
	Theme.TextStroke(stamp, 2)
	local scc = Instance.new("UITextSizeConstraint"); scc.MaxTextSize = 16; scc.Parent = stamp

	local state = "locked"
	local function setVisual(s: string)
		state = s
		timer.Visible = (s == "locked" or s == "next")
		claimBtn.Parent.Visible = (s == "ready")
		stamp.Visible = (s == "claimed")
		if s == "claimed" then
			root.BackgroundColor3 = Theme.darken(P.PanelInner, 0.25); stroke.Color = P.Muted; stroke.Transparency = 0.3
		elseif s == "ready" then
			stroke.Color = P.Confirm; stroke.Thickness = 3; stroke.Transparency = 0
		else
			stroke.Color = color; stroke.Transparency = 0
		end
	end

	claimBtn.MouseButton1Click:Connect(function()
		if state ~= "ready" then return end
		task.spawn(function()
			local res
			pcall(function() res = Net.request("claimPlaytimeReward", { tier = t.tier }) end)
			if res and res.ok then
				claimedSet[t.tier] = true
				-- FX : punch
				local us = Instance.new("UIScale"); us.Parent = root
				TweenService:Create(us, TweenInfo.new(0.12, Enum.EasingStyle.Back, Enum.EasingDirection.Out), { Scale = 1.12 }):Play()
				task.wait(0.12)
				TweenService:Create(us, TweenInfo.new(0.12), { Scale = 1 }):Play()
				setVisual("claimed")
			end
		end)
	end)

	local function update(now: number)
		if claimedSet[t.tier] then if state ~= "claimed" then setVisual("claimed") end return end
		local remain = t.unlock - now
		if remain <= 0 then
			if state ~= "ready" then setVisual("ready") end
		else
			timer.Text = fmtTime(remain)
			-- "prochaine" = le 1er verrouillé
			setVisual(state == "claimed" and "claimed" or "locked")
			timer.Visible = true
		end
	end

	return { root = root, update = update, tier = t.tier, color = color, visual = t.visual,
		pulse = function() end }
end

-- compteur de récompenses prêtes (badge)
local function readyCount(): number
	local n = 0
	if schedule then
		local now = elapsed()
		for _, t in ipairs(schedule) do
			if not claimedSet[t.tier] and now >= t.unlock then n += 1 end
		end
	end
	return n
end

local function ensureButton()
	local pg = player:FindFirstChildOfClass("PlayerGui"); if not pg then return end
	local hud = pg:FindFirstChild("MainHUD"); if not hud then return end
	local sidebar = hud:FindFirstChild("Sidebar"); if not sidebar then return end
	if sidebar:FindFirstChild("RewardsBtn") then return end
	local src = sidebar:FindFirstChild("IndexBtn"); if not src then return end
	local btn = src:Clone()
	btn.Name = "RewardsBtn"; btn.LayoutOrder = 5
	local face = btn:FindFirstChild("Face")
	if face then
		face.BackgroundColor3 = P.Gold
		local lbl = face:FindFirstChild("Label"); if lbl then lbl.Text = "CADEAUX" end
	end
	local base = btn:FindFirstChild("Base"); if base then base.BackgroundColor3 = Theme.darken(P.Gold, 0.45) end
	-- badge
	local b = Instance.new("TextLabel")
	b.Name = "ReadyBadge"; b.AnchorPoint = Vector2.new(1, 0); b.Position = UDim2.new(1, -2, 0, -2)
	b.Size = UDim2.fromOffset(22, 22); b.BackgroundColor3 = P.Danger; b.Font = Theme.Font.Title
	b.Text = "0"; b.TextColor3 = P.White; b.TextScaled = true; b.ZIndex = 10; b.Visible = false; b.Parent = btn
	Theme.Corner(b, UDim.new(1, 0)); Theme.Stroke(b, P.Outline, 2); Theme.TextStroke(b, 2)
	badge = b
	if face then face.MouseButton1Click:Connect(function() Controller.open() end) end
end

local function buildGui()
	if gui then return end
	local pg = player:FindFirstChildOfClass("PlayerGui"); if not pg then return end
	local g = Instance.new("ScreenGui")
	g.Name = "PlaytimeRewards"; g.ResetOnSpawn = false; g.IgnoreGuiInset = true
	g.ZIndexBehavior = Enum.ZIndexBehavior.Sibling; g.DisplayOrder = 46; g.Enabled = false; g.Parent = pg
	gui = g

	local overlay = Instance.new("TextButton")
	overlay.Size = UDim2.fromScale(1, 1); overlay.BackgroundColor3 = Color3.new(0, 0, 0)
	overlay.BackgroundTransparency = 0.45; overlay.AutoButtonColor = false; overlay.Text = ""
	overlay.ZIndex = 0; overlay.Parent = g
	overlay.MouseButton1Click:Connect(function() Controller.close() end)

	local parts = Theme.Panel({ parent = g, title = "RÉCOMPENSES DE TEMPS DE JEU", size = UDim2.fromOffset(720, 560) })
	Theme.Gradient(parts.titleBar, { P.Purple, P.Pink }, 0)
	parts.close.MouseButton1Click:Connect(function() Controller.close() end)
	local us = Instance.new("UIScale"); us.Scale = 0.7; us.Parent = parts.card
	g:SetAttribute("uiscale", true)
	gui:SetAttribute("ready", true)

	-- sous-titre
	local sub = Instance.new("TextLabel")
	sub.BackgroundTransparency = 1; sub.Size = UDim2.new(1, -20, 0, 20); sub.Position = UDim2.fromOffset(4, 2)
	sub.Font = Theme.Font.Body; sub.Text = "Reste connecté pour débloquer des récompenses — réinitialisé à la déconnexion."
	sub.TextColor3 = P.Muted; sub.TextScaled = true; sub.TextXAlignment = Enum.TextXAlignment.Left; sub.Parent = parts.content
	local sc = Instance.new("UITextSizeConstraint"); sc.MaxTextSize = 14; sc.Parent = sub

	-- grille
	local scroll = Instance.new("ScrollingFrame")
	scroll.BackgroundTransparency = 1; scroll.BorderSizePixel = 0
	scroll.Position = UDim2.fromOffset(0, 26); scroll.Size = UDim2.new(1, 0, 1, -26)
	scroll.CanvasSize = UDim2.new(); scroll.AutomaticCanvasSize = Enum.AutomaticSize.Y
	scroll.ScrollBarThickness = 8; scroll.Parent = parts.content
	local grid = Instance.new("UIGridLayout")
	grid.CellSize = UDim2.fromOffset(160, 172); grid.CellPadding = UDim2.fromOffset(12, 12)
	grid.HorizontalAlignment = Enum.HorizontalAlignment.Center
	grid.SortOrder = Enum.SortOrder.LayoutOrder; grid.Parent = scroll

	for _, t in ipairs(schedule) do
		local card = buildCard(t)
		card.root.LayoutOrder = t.tier; card.root.Parent = scroll
		cards[t.tier] = card
	end

	-- store refs for open/close tween
	g:SetAttribute("built", true)
	g.AncestryChanged:Connect(function() end)
	Controller._scale = us
end

local function refresh()
	local now = elapsed()
	for _, card in pairs(cards) do card.update(now) end
	local rc = readyCount()
	if badge then badge.Text = tostring(rc); badge.Visible = rc > 0 end
end

function Controller.open()
	if not schedule then return end
	if not gui then buildGui() end
	if not gui then return end
	isOpen = true
	gui.Enabled = true
	refresh()
	if Controller._scale then
		Controller._scale.Scale = 0.7
		TweenService:Create(Controller._scale, TweenInfo.new(0.2, Enum.EasingStyle.Back, Enum.EasingDirection.Out), { Scale = 1 }):Play()
	end
end

function Controller.close()
	isOpen = false
	if gui and Controller._scale then
		local tw = TweenService:Create(Controller._scale, TweenInfo.new(0.12), { Scale = 0.7 })
		tw:Play()
		tw.Completed:Once(function() if not isOpen and gui then gui.Enabled = false end end)
	elseif gui then gui.Enabled = false end
end

local function applyState(st)
	if not st then return end
	schedule = st.schedule
	origin = os.clock() - (st.elapsed or 0)
	if st.claimed then for _, tier in ipairs(st.claimed) do claimedSet[tier] = true end end
end

function Controller:Start()
	-- état initial : event poussé + fallback request
	Net.onEvent("playtimeInit", function(st)
		applyState(st)
	end)
	task.spawn(function()
		task.wait(1)
		if not schedule then
			local res; pcall(function() res = Net.request("getPlaytimeState") end)
			if res and res.ok then applyState(res.data) end
		end
	end)
	-- bouton + boucle 1s
	task.spawn(function()
		while true do
			ensureButton()
			if schedule then refresh() end
			task.wait(1)
		end
	end)
	player.CharacterAdded:Connect(function() task.wait(0.5); ensureButton() end)
end

return Controller
```

- [ ] **Step 2: Verify** — `inspect_instance` the new controller; `script_read` to confirm full source. Note the `Theme.Button` returns the `Face`; `claimBtn.Parent.Visible` toggles the button container (confirmed by Theme.Button structure: container → Base + Face).

- [ ] **Step 3: Save (Ctrl+S).**

---

### Task 6: `BoostHUDController` (active-boost pills)

**Files:** Create `StarterPlayer.StarterPlayerScripts.Client.Controllers.BoostHUDController` (ModuleScript).

**Interfaces:** Consumes `Net.onEvent("boostsChanged", {{kind,remaining}})`; `Theme`.

- [ ] **Step 1: Create the ModuleScript with this exact source**

```lua
--!strict
-- BoostHUDController.luau
-- Strip de pills de boosts actifs (haut-centre du HUD). Piloté par l'event boostsChanged.

local Players = game:GetService("Players")
local RunService = game:GetService("RunService")
local RS = game:GetService("ReplicatedStorage")
local Theme = require(RS.UI.Theme)
local P = Theme.Palette
local Net = require(RS.Shared.Net.Net)

local player = Players.LocalPlayer
local Controller = {}

local KIND = {
	cash = { label = "x2 Cash", color = P.Confirm },
	luck = { label = "+Chance", color = P.Purple },
	yield = { label = "+Rendement", color = P.Gold },
	speed = { label = "+Vitesse", color = P.Cyan },
}

local container: Frame? = nil
local active: { [string]: number } = {}   -- kind -> expiresAt (os.clock)
local pills: { [string]: any } = {}

local function ensureContainer()
	if container then return end
	local pg = player:FindFirstChildOfClass("PlayerGui"); if not pg then return end
	local g = Instance.new("ScreenGui")
	g.Name = "BoostHUD"; g.ResetOnSpawn = false; g.IgnoreGuiInset = true
	g.ZIndexBehavior = Enum.ZIndexBehavior.Sibling; g.DisplayOrder = 20; g.Parent = pg
	local f = Instance.new("Frame")
	f.AnchorPoint = Vector2.new(0.5, 0); f.Position = UDim2.new(0.5, 0, 0, 8)
	f.Size = UDim2.fromOffset(10, 40); f.AutomaticSize = Enum.AutomaticSize.X
	f.BackgroundTransparency = 1; f.Parent = g
	local list = Instance.new("UIListLayout")
	list.FillDirection = Enum.FillDirection.Horizontal; list.Padding = UDim.new(0, 8)
	list.HorizontalAlignment = Enum.HorizontalAlignment.Center; list.SortOrder = Enum.SortOrder.Name; list.Parent = f
	container = f
end

local function makePill(kind: string)
	local meta = KIND[kind] or { label = kind, color = P.Cyan }
	local pill, label = Theme.Pill({ parent = container, name = kind, size = UDim2.fromOffset(150, 36),
		color = Theme.darken(meta.color, 0.15), text = meta.label .. "  00:00", textColor = P.White,
		font = Theme.Font.Body, maxTextSize = 16 })
	return { pill = pill, label = label, color = meta.color, baseLabel = meta.label }
end

function Controller:Start()
	Net.onEvent("boostsChanged", function(list)
		ensureContainer()
		local seen = {}
		for _, b in ipairs(list or {}) do
			seen[b.kind] = true
			active[b.kind] = os.clock() + (b.remaining or 0)
			if not pills[b.kind] then pills[b.kind] = makePill(b.kind) end
		end
		-- retirer les pills disparues
		for kind, p in pairs(pills) do
			if not seen[kind] then p.pill:Destroy(); pills[kind] = nil; active[kind] = nil end
		end
	end)

	RunService.Heartbeat:Connect(function()
		local now = os.clock()
		for kind, p in pairs(pills) do
			local exp = active[kind] or 0
			local remain = math.max(0, math.floor(exp - now + 0.5))
			local m = math.floor(remain / 60); local s = remain % 60
			p.label.Text = string.format("%s  %02d:%02d", p.baseLabel, m, s)
			-- pulse < 10s
			if remain <= 10 and remain > 0 then
				local a = 0.5 + 0.5 * math.abs(math.sin(now * 4))
				p.pill.BackgroundColor3 = p.color:Lerp(P.White, a * 0.4)
			end
			if remain <= 0 then p.pill:Destroy(); pills[kind] = nil; active[kind] = nil end
		end
	end)
end

return Controller
```

- [ ] **Step 2: Verify** — `inspect_instance` + `script_read` the new controller.

- [ ] **Step 3: Save (Ctrl+S).**

---

### Task 7: Integration playtest

**Files:** none (verification only). Uses a temporary `Script` in `ServerScriptService` to drive the live services (the `execute_luau` server VM is isolated, so live-service tests must run inside the running game).

- [ ] **Step 1: Start Play.** `start_stop_play` → Play. `get_console_output` → confirm NO errors from `BoostService`, `PlaytimeRewardsService`, `CatchService`, `InventoryService` at boot (syntax/require errors surface here). If a `Server.Services` module errored, the bootstrap warns `[Server] failed to require X` — fix before continuing.

- [ ] **Step 2: Server-side smoke test.** Create a temp `Script` `ServerScriptService.__PT_TEST` with body below, let it run once, read `get_console_output`, then delete it:
```lua
local Players = game:GetService("Players")
local Registry = require(game.ServerScriptService.Server.Registry)
local plr = Players:GetPlayers()[1]
if not plr then warn("PT_TEST: no player"); return end
local d = Registry.get("DataService").get(plr)
-- boost grant + read
Registry.get("BoostService").grant(plr, "cash", 30)
print("PT cashAdd =", Registry.get("BoostService").cashAdd(plr))           -- expect 1
print("PT speedFactor =", Registry.get("BoostService").speedFactor(plr))   -- expect 1 (speed not granted)
-- claim tier 1 too early -> locked
print("PT claim-early =", require(game.ReplicatedStorage.Shared.Config.PlaytimeRewards).get(1).unlock)
```
Expected console: `PT cashAdd = 1`, `PT speedFactor = 1`.

- [ ] **Step 3: UI smoke test.** In Play, confirm `PlayerGui.MainHUD.Sidebar.RewardsBtn` exists (`inspect_instance`), and `PlayerGui.PlaytimeRewards` ScreenGui is created on first `open()`. Drive open via temp client behavior or click; `screen_capture` the panel. Confirm: panel centered, purple→pink header, 12 cards in 4×3, tier-1 timer counting down from `01:00`.

- [ ] **Step 4: Claim path.** Temporarily lower tier-1 `unlock` to `3` in the config (or wait 60s), let tier-1 become ready, click Réclamer; confirm `$` HUD increments by 1000 and the card stamps "RÉCLAMÉ". Restore `unlock = 60`.

- [ ] **Step 5: Boost effect + HUD.** Grant a cash boost (temp script `BoostService.grant(plr,"cash",60)`); confirm a pill appears in `PlayerGui.BoostHUD` and sells pay more while active. Confirm pill disappears at expiry.

- [ ] **Step 6: Session reset.** Stop Play, Start Play again; confirm timers restart at 0 (sess cleared) and no boosts persist.

- [ ] **Step 7: Stop Play. Save (Ctrl+S).** Update the project memory note.

---

## Self-Review

**Spec coverage:** §4 reward table → Task 1 config (all 12 tiers, exact amounts/durations/offsets). §5.1 boost impl → Task 2 (`BoostService` accessors) + Task 3 (4 hook sites: sellStack/crit cash, luck, yield, speed). §5.2 indexing → Task 4 (`lootRarityId`/`eggIdFor`/`petDefFor`). §6 session behavior → Task 4 (`sess`, onReady/onRemoving, claim validation, anti-double-claim). §7 UI (panel, 4 states, rarity, animations, assets, boost HUD, button) → Task 5 + Task 6. §8 architecture/components → all tasks; §9 component list → File Structure table. §11 acceptance → Task 7 steps map 1:1.

**Placeholder scan:** none — every step has concrete code or a concrete MCP verification command.

**Type consistency:** boost `kind` strings `cash|luck|yield|speed` consistent across `BoostService` (Task 2), hooks (Task 3), config `boostKind`/`boostKinds` (Task 1), service grant (Task 4), HUD `KIND` map (Task 6). `schedule` entry fields produced by `PlaytimeRewards.client()` (Task 1) match consumption in controller `buildCard` (Task 5). Reward `granted.kind` produced by `grantReward` (Task 4) — not consumed for branching by the client (client only checks `res.ok`), so no mismatch. `Net` request names `getPlaytimeState`/`claimPlaytimeReward` and events `playtimeInit`/`boostsChanged` consistent server↔client.

**Known confirm-at-exec items (flagged in steps, not placeholders):** exact line text at the 5 CatchService/InventoryService hook points (read-back before edit); `Pets.list`/`Pets.get` shape for `petDefFor`; `CollectibleService.prizeRain` no-character fallback; MCP instance-creation read-back.
