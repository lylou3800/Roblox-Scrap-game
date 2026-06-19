## Task 4 : `buildFloor2` (dalle + garde-corps + trémie + échelle + 8 baies)

**Files:**
- Modify: `ServerScriptService.Server.Services.PlotService` (nouvelle fonction module-local `buildFloor2` ; appel conditionnel dans `assignPlot`)

**Interfaces:**
- Consumes : `makePart`, `styleParts`, `buildBay`, `PlotLayout.floor2`, `PlotLayout.plotSize`, `info.padBySlot`.
- Produces : `buildFloor2(info: PlotInfo)` — idempotent (no-op si `info.model.Floor2` existe). Construit la dalle (3 parts laissant une trémie au bord avant), les garde-corps, l'échelle `TrussPart` `Floor2Ladder`, l'éclairage sous-dalle, un marqueur `Floor2` (Configuration), puis les 8 baies `f*` via `buildBay` (en **mutant** `info.padBySlot`).

- [ ] **Step 1 : Ajouter `buildFloor2`** (`multi_edit` sur `PlotService`)

Insérer **juste après** la fonction `buildBay` (avant `buildPlot`) :
```luau
-- Construit l'étage au-dessus du plot : dalle pleine emprise (avec trémie au bord avant),
-- garde-corps anti-chute, échelle escaladable (TrussPart), éclairage sous-dalle, 8 baies f*.
-- Idempotent. Mute info.padBySlot pour les baies f* (refreshSlot les retrouvera ensuite).
local function buildFloor2(info: PlotInfo)
	local model = info.model
	local origin = info.origin
	if model:FindFirstChild("Floor2") then
		return
	end
	local F = PlotLayout.floor2
	local half = PlotLayout.plotSize.X / 2 -- emprise carrée 128 -> half = 64
	local t = F.deckThickness
	local topY = F.height - 0.3 -- surface haute de la dalle (les baies f* posent dessus)
	local cy = topY - t / 2
	local nH = F.notchHalfW
	local nD = F.notchDepth
	local DECK = Color3.fromRGB(96, 100, 110)
	local RAIL = Color3.fromRGB(54, 59, 70)

	local function dpart(nm, size, color, cf, mat, coll)
		local p = makePart(nm, size, color, cf, model)
		p.Material = mat or Enum.Material.DiamondPlate
		p.CanCollide = (coll ~= false)
		p.TopSurface = Enum.SurfaceType.Smooth
		p.BottomSurface = Enum.SurfaceType.Smooth
		return p
	end

	-- Dalle : grande dalle arrière + 2 bandes avant, laissant une trémie centrale au bord avant
	-- (x in [-nH, nH], z in [-half, -half+nD]) pour le passage de l'échelle.
	local backLen = 2 * half - nD
	dpart("Floor2Deck", Vector3.new(2 * half, t, backLen), DECK, origin * CFrame.new(0, cy, (-half + nD + half) / 2), Enum.Material.DiamondPlate)
	local sideLen = half - nH
	dpart("Floor2Deck", Vector3.new(sideLen, t, nD), DECK, origin * CFrame.new(-(nH + sideLen / 2), cy, -half + nD / 2), Enum.Material.DiamondPlate)
	dpart("Floor2Deck", Vector3.new(sideLen, t, nD), DECK, origin * CFrame.new((nH + sideLen / 2), cy, -half + nD / 2), Enum.Material.DiamondPlate)

	-- Garde-corps périmétriques (anti-chute), bord avant scindé autour de la trémie.
	local railY = topY + F.railHeight / 2
	dpart("Floor2Rail", Vector3.new(2 * half, F.railHeight, 0.5), RAIL, origin * CFrame.new(0, railY, half), Enum.Material.Metal)
	dpart("Floor2Rail", Vector3.new(0.5, F.railHeight, 2 * half), RAIL, origin * CFrame.new(-half, railY, 0), Enum.Material.Metal)
	dpart("Floor2Rail", Vector3.new(0.5, F.railHeight, 2 * half), RAIL, origin * CFrame.new(half, railY, 0), Enum.Material.Metal)
	local fSeg = half - nH
	dpart("Floor2Rail", Vector3.new(fSeg, F.railHeight, 0.5), RAIL, origin * CFrame.new(-(nH + fSeg / 2), railY, -half), Enum.Material.Metal)
	dpart("Floor2Rail", Vector3.new(fSeg, F.railHeight, 0.5), RAIL, origin * CFrame.new((nH + fSeg / 2), railY, -half), Enum.Material.Metal)
	-- Côtés de la trémie (qu'on ne tombe pas dedans depuis la dalle).
	dpart("Floor2Rail", Vector3.new(0.5, F.railHeight, nD), RAIL, origin * CFrame.new(-nH, railY, -half + nD / 2), Enum.Material.Metal)
	dpart("Floor2Rail", Vector3.new(0.5, F.railHeight, nD), RAIL, origin * CFrame.new(nH, railY, -half + nD / 2), Enum.Material.Metal)
	-- Liserés hazard sur la lisse haute (cohérence cartoon).
	dpart("Floor2RailTrim", Vector3.new(2 * half, 0.4, 0.55), HAZ, origin * CFrame.new(0, topY + F.railHeight, half), Enum.Material.SmoothPlastic)

	-- Échelle escaladable : TrussPart (climb natif), base au sol (y=0), sommet à la dalle.
	local truss = Instance.new("TrussPart")
	truss.Name = "Floor2Ladder"
	truss.Anchored = true
	truss.Size = Vector3.new(2, F.height, 2)
	truss.CFrame = origin * CFrame.new(0, F.height / 2, -half + F.ladderInset)
	truss.Color = Color3.fromRGB(224, 182, 44)
	truss.Material = Enum.Material.Metal
	truss.Parent = model

	-- Éclairage sous-dalle (le RDC ne doit pas s'assombrir).
	for _, lx in ipairs({ -32, 0, 32 }) do
		for _, lz in ipairs({ -32, 0, 32 }) do
			local lp = makePart("Floor2Light", Vector3.new(3, 0.3, 3), Color3.fromRGB(255, 250, 230), origin * CFrame.new(lx, topY - t - 0.2, lz), model)
			lp.Material = Enum.Material.Neon
			lp.CanCollide = false
			local sl = Instance.new("SurfaceLight")
			sl.Face = Enum.NormalId.Bottom
			sl.Brightness = 2
			sl.Range = 26
			sl.Angle = 90
			sl.Parent = lp
		end
	end

	-- Marqueur (détection idempotente + repère).
	local marker = Instance.new("Configuration")
	marker.Name = "Floor2"
	marker.Parent = model

	-- Baies de l'étage (floor 1). displayNum = index ipairs (9..16 -> "BAIE 9..16").
	for i, slotDef in ipairs(PlotLayout.slots) do
		if slotDef.floor == 1 then
			info.padBySlot[slotDef.id] = buildBay(model, origin, slotDef, i)
		end
	end

	-- Applique la librairie de matériaux aux baies (mêmes préfixes que le RDC) ; idempotent.
	styleParts(model)
end
```

- [ ] **Step 2 : Construire l'étage au build du plot si déjà acheté** (`multi_edit` sur `PlotService`, dans `assignPlot`)

Remplacer exactement :
```luau
	local info = buildPlot(player, index)
	plots[player] = info

	for slotId in pairs(data.plot.slots) do
		refreshSlot(player, slotId)
	end
```
par :
```luau
	local info = buildPlot(player, index)
	plots[player] = info

	-- Joueur de retour avec l'étage déjà acheté : le reconstruire avant de rafraîchir les slots f*.
	if data.plot.floor2Unlocked then
		buildFloor2(info)
	end

	for slotId in pairs(data.plot.slots) do
		refreshSlot(player, slotId) -- f* no-op tant que leur pad n'existe pas (pad nil -> return)
	end
```

- [ ] **Step 3 : Relire pour confirmer** — `script_read` sur `PlotService` : `buildFloor2` présent, appel conditionnel dans `assignPlot`.

- [ ] **Step 4 : Vérif live — forcer l'étage et le voir** — `buildFloor2` est module-local (pas encore d'API publique avant Task 5). Pour le déclencher via la lifecycle `assignPlot → buildFloor2` : en Play, Script temporaire (vraie VM serveur) qui pose le flag puis relance l'assignation du plot —
```luau
local Registry = require(game:GetService("ServerScriptService").Server.Registry)
local DataService = Registry.get("DataService")
local plr = game:GetService("Players"):GetPlayers()[1]
DataService.get(plr).plot.floor2Unlocked = true
```
Puis `start_stop_play` (stop) et re-Play : à la re-connexion, `assignPlot` voit `floor2Unlocked=true` et bâtit l'étage. Après respawn, `screen_capture` : dalle + garde-corps + échelle jaune + 8 baies « BAIE 9..16 ». Puis Script temporaire de contrôle :
```luau
local plr = game:GetService("Players"):GetPlayers()[1]
local m = workspace:FindFirstChild("Plot_"..plr.UserId)
local hasDeck = m and m:FindFirstChild("Floor2") ~= nil
local hasLadder = m and m:FindFirstChild("Floor2Ladder") ~= nil
local f = 0 ; if m then for i = 1, 8 do if m:FindFirstChild("Slot_f"..i) then f += 1 end end end
print("TAG_F2: deck="..tostring(hasDeck).." ladder="..tostring(hasLadder).." fbays="..f)
```
Attendu : `TAG_F2: deck=true ladder=true fbays=8`. Vérifier en jeu que l'échelle est **escaladable** (monter dessus). Supprimer le Script temporaire.

- [ ] **Step 5 : Checkpoint** — prévenir l'utilisateur qu'il peut sauvegarder (Ctrl+S).

---

