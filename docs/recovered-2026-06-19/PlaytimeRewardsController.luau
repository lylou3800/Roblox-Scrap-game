-- PlaytimeRewardsController.luau
-- Menu "Recompenses de temps de jeu" : panneau Theme + grille 12 cartes, timers locaux,
-- claim valide serveur. Bouton clone dans MainHUD.Sidebar + badge de recompenses pretes.

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

local schedule = nil
local origin = nil
local claimedSet = {}
local cards = {}
local gui = nil
local isOpen = false
local badge = nil
local scaleObj = nil

local function tierColor(v)
	if v == "premium" then return P.Gold elseif v == "rare" then return P.Purple else return P.Cyan end
end

local function fmtTime(s)
	s = math.max(0, math.floor(s))
	local m = math.floor(s / 60); local sec = s % 60
	if m >= 60 then local h = math.floor(m / 60); m = m % 60; return string.format("%d:%02d:%02d", h, m, sec) end
	return string.format("%02d:%02d", m, sec)
end

local function fmtCash(n)
	local s = tostring(math.floor(n)); local out = ""; local c = 0
	for i = #s, 1, -1 do out = s:sub(i, i) .. out; c += 1; if c % 3 == 0 and i > 1 then out = "," .. out end end
	return "$" .. out
end

local function elapsed()
	return origin and (os.clock() - origin) or 0
end

local function buildIcon(holder, t, color)
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

local function buildCard(t)
	local color = tierColor(t.visual)
	local root = Instance.new("Frame")
	root.Size = UDim2.fromScale(1, 1); root.BackgroundColor3 = P.PanelInner; root.BorderSizePixel = 0
	Theme.Corner(root, UDim.new(0, 14))
	local stroke = Theme.Stroke(root, color, t.visual == "premium" and 3 or 2)

	local top = Instance.new("TextLabel")
	top.BackgroundTransparency = 1; top.Size = UDim2.new(1, -10, 0, 22); top.Position = UDim2.fromOffset(5, 6)
	top.Font = Theme.Font.Title; top.TextScaled = true
	top.TextColor3 = (t.type == "cash" or t.type == "prize_rain") and P.Confirm or P.White
	top.Text = (t.cash and (t.type == "cash" or t.type == "prize_rain")) and fmtCash(t.cash) or t.name
	top.Parent = root; Theme.TextStroke(top, 2)
	local tc = Instance.new("UITextSizeConstraint"); tc.MaxTextSize = 18; tc.Parent = top

	local plate = Instance.new("Frame")
	plate.AnchorPoint = Vector2.new(0.5, 0); plate.Position = UDim2.new(0.5, 0, 0, 32)
	plate.Size = UDim2.fromOffset(62, 62); plate.BackgroundTransparency = 1; plate.Parent = root
	buildIcon(plate, t, color)
	if t.lootCount then
		local q = Instance.new("TextLabel")
		q.AnchorPoint = Vector2.new(1, 1); q.Position = UDim2.new(1, -1, 1, -1); q.Size = UDim2.fromOffset(24, 16)
		q.BackgroundTransparency = 1; q.Font = Theme.Font.Title; q.Text = "x" .. t.lootCount
		q.TextColor3 = P.White; q.TextScaled = true; q.ZIndex = 5; q.Parent = plate; Theme.TextStroke(q, 2)
	end

	local subText = (t.cash and (t.type == "cash" or t.type == "prize_rain")) and t.name or (t.desc or "")
	local nameLbl = Instance.new("TextLabel")
	nameLbl.BackgroundTransparency = 1; nameLbl.Size = UDim2.new(1, -10, 0, 28); nameLbl.Position = UDim2.fromOffset(5, 96)
	nameLbl.Font = Theme.Font.Body; nameLbl.Text = subText; nameLbl.TextColor3 = P.Muted; nameLbl.TextScaled = true
	nameLbl.TextWrapped = true; nameLbl.TextTruncate = Enum.TextTruncate.AtEnd; nameLbl.Parent = root; Theme.TextStroke(nameLbl, 1)
	local nc = Instance.new("UITextSizeConstraint"); nc.MaxTextSize = 12; nc.Parent = nameLbl

	local bottom = Instance.new("Frame")
	bottom.AnchorPoint = Vector2.new(0.5, 1); bottom.Position = UDim2.new(0.5, 0, 1, -8)
	bottom.Size = UDim2.new(1, -12, 0, 30); bottom.BackgroundTransparency = 1; bottom.Parent = root

	local timer = Instance.new("TextLabel")
	timer.BackgroundTransparency = 1; timer.Size = UDim2.fromScale(1, 1); timer.Font = Theme.Font.Title
	timer.Text = "--:--"; timer.TextColor3 = P.White; timer.TextScaled = true; timer.Parent = bottom; Theme.TextStroke(timer, 2)
	local tcc = Instance.new("UITextSizeConstraint"); tcc.MaxTextSize = 20; tcc.Parent = timer

	local claimBtn = Theme.Button({ parent = bottom, text = "Reclamer", color = P.Confirm, size = UDim2.fromScale(1, 1), maxTextSize = 16 })
	claimBtn.Parent.Visible = false

	local stamp = Instance.new("TextLabel")
	stamp.BackgroundTransparency = 1; stamp.Size = UDim2.fromScale(1, 1); stamp.Font = Theme.Font.Title
	stamp.Text = "RECLAME"; stamp.TextColor3 = P.Muted; stamp.TextScaled = true; stamp.Visible = false; stamp.Parent = bottom
	Theme.TextStroke(stamp, 2)
	local scc = Instance.new("UITextSizeConstraint"); scc.MaxTextSize = 16; scc.Parent = stamp

	local state = ""
	local function setVisual(s)
		if state == s then return end
		state = s
		timer.Visible = (s == "locked")
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
				local us = Instance.new("UIScale"); us.Parent = root
				TweenService:Create(us, TweenInfo.new(0.12, Enum.EasingStyle.Back, Enum.EasingDirection.Out), { Scale = 1.12 }):Play()
				task.wait(0.12)
				TweenService:Create(us, TweenInfo.new(0.12), { Scale = 1 }):Play()
				setVisual("claimed")
			end
		end)
	end)

	local function update(now)
		if claimedSet[t.tier] then setVisual("claimed"); return end
		local remain = t.unlock - now
		if remain <= 0 then
			setVisual("ready")
		else
			timer.Text = fmtTime(remain)
			setVisual("locked")
		end
	end

	return { root = root, update = update }
end

local function readyCount()
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
	local b = Instance.new("TextLabel")
	b.Name = "ReadyBadge"; b.AnchorPoint = Vector2.new(1, 0); b.Position = UDim2.new(1, -2, 0, -2)
	b.Size = UDim2.fromOffset(22, 22); b.BackgroundColor3 = P.Danger; b.Font = Theme.Font.Title
	b.Text = "0"; b.TextColor3 = P.White; b.TextScaled = true; b.ZIndex = 10; b.Visible = false
	b.Parent = btn
	Theme.Corner(b, UDim.new(1, 0)); Theme.Stroke(b, P.Outline, 2); Theme.TextStroke(b, 2)
	badge = b
	btn.Parent = sidebar
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

	local parts = Theme.Panel({ parent = g, title = "RECOMPENSES DE TEMPS DE JEU", size = UDim2.fromOffset(720, 600) })
	Theme.Gradient(parts.titleBar, { P.Purple, P.Pink }, 0)
	parts.close.MouseButton1Click:Connect(function() Controller.close() end)
	scaleObj = Instance.new("UIScale"); scaleObj.Scale = 0.7; scaleObj.Parent = parts.card

	local sub = Instance.new("TextLabel")
	sub.BackgroundTransparency = 1; sub.Size = UDim2.new(1, -20, 0, 20); sub.Position = UDim2.fromOffset(4, 2)
	sub.Font = Theme.Font.Body; sub.Text = "Reste connecte pour debloquer des recompenses - reinitialise a la deconnexion."
	sub.TextColor3 = P.Muted; sub.TextScaled = true; sub.TextXAlignment = Enum.TextXAlignment.Left; sub.Parent = parts.content
	local sc = Instance.new("UITextSizeConstraint"); sc.MaxTextSize = 14; sc.Parent = sub

	local scroll = Instance.new("ScrollingFrame")
	scroll.BackgroundTransparency = 1; scroll.BorderSizePixel = 0
	scroll.Position = UDim2.fromOffset(0, 26); scroll.Size = UDim2.new(1, 0, 1, -26)
	scroll.CanvasSize = UDim2.new(); scroll.AutomaticCanvasSize = Enum.AutomaticSize.Y
	scroll.ScrollBarThickness = 8; scroll.Parent = parts.content
	local grid = Instance.new("UIGridLayout")
	grid.CellSize = UDim2.fromOffset(160, 172); grid.CellPadding = UDim2.fromOffset(12, 12)
	grid.HorizontalAlignment = Enum.HorizontalAlignment.Center
	grid.SortOrder = Enum.SortOrder.LayoutOrder; grid.Parent = scroll
	local gpad = Instance.new("UIPadding"); gpad.PaddingTop = UDim.new(0, 6); gpad.PaddingBottom = UDim.new(0, 6); gpad.Parent = scroll

	cards = {}
	for _, t in ipairs(schedule) do
		local card = buildCard(t)
		card.root.LayoutOrder = t.tier; card.root.Parent = scroll
		cards[t.tier] = card
	end
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
	if scaleObj then
		scaleObj.Scale = 0.7
		TweenService:Create(scaleObj, TweenInfo.new(0.2, Enum.EasingStyle.Back, Enum.EasingDirection.Out), { Scale = 1 }):Play()
	end
end

function Controller.close()
	isOpen = false
	if gui and scaleObj then
		local tw = TweenService:Create(scaleObj, TweenInfo.new(0.12), { Scale = 0.7 })
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
	Net.onEvent("playtimeInit", function(st) applyState(st) end)
	task.spawn(function()
		task.wait(1)
		if not schedule then
			local res; pcall(function() res = Net.request("getPlaytimeState") end)
			if res and res.ok then applyState(res.data) end
		end
	end)
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
