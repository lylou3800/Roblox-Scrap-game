-- BoostHUDController.luau
-- Strip de pills de boosts actifs (haut-centre du HUD). Pilote par l'event boostsChanged.

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

local container = nil
local active = {}
local pills = {}

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

local function makePill(kind)
	local meta = KIND[kind] or { label = kind, color = P.Cyan }
	local pill, label = Theme.Pill({ parent = container, name = kind, size = UDim2.fromOffset(150, 36),
		color = Theme.darken(meta.color, 0.15), text = meta.label .. "  00:00", textColor = P.White,
		font = Theme.Font.Body, maxTextSize = 16 })
	return { pill = pill, label = label, color = meta.color, baseLabel = meta.label }
end

function Controller:Start()
	Net.onEvent("boostsChanged", function(list)
		ensureContainer()
		if not container then return end
		local seen = {}
		for _, b in ipairs(list or {}) do
			seen[b.kind] = true
			active[b.kind] = os.clock() + (b.remaining or 0)
			if not pills[b.kind] then pills[b.kind] = makePill(b.kind) end
		end
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
			if remain <= 10 and remain > 0 then
				local a = 0.5 + 0.5 * math.abs(math.sin(now * 4))
				p.pill.BackgroundColor3 = p.color:Lerp(P.White, a * 0.4)
			end
			if remain <= 0 then p.pill:Destroy(); pills[kind] = nil; active[kind] = nil end
		end
	end)
end

return Controller
