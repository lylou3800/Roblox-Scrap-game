--!strict
-- BoostService.luau
-- Buffs tempores de SESSION (jamais persistes). Lus par CatchService/InventoryService.
-- Identite si inactif : 0 (additif cash/luck/yield), 1.0 (multiplicatif speed).

local RunService = game:GetService("RunService")
local Shared = game:GetService("ReplicatedStorage"):WaitForChild("Shared")
local ServerRoot = script.Parent.Parent
local Registry = require(ServerRoot.Registry)
local Net = require(Shared.Net.Net)

local BoostService = {}

local CASH_ADD = 1.0       -- +100% additif dans la somme sellMult
local YIELD_ADD = 0.30     -- +0.30 yieldChance
local SPEED_FACTOR = 1.25  -- grabSpeed / 1.25 (+25% cadence)
-- luck : additif scale = max(0.6, 0.25 * luck courante)

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
