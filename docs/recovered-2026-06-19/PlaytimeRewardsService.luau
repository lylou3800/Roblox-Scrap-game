--!strict
-- PlaytimeRewardsService.luau
-- Recompenses de temps de jeu : etat de session (joinedAt/claimed), claim autoritaire,
-- attribution + indexation par stade. ZERO persistance.

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
