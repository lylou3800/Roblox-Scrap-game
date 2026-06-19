## Task 5 : Panneau d'achat + `tryUnlockFloor` (serveur)

**Files:**
- Modify: `ServerScriptService.Server.Services.PlotService` (helpers compteur RDC, `buildFloorPanel`, `updateFloorPanel`, `PlotService.tryUnlockFloor`, appels dans `assignPlot` + `handleUnlock`, champ `floorPanel` sur `PlotInfo`)

**Interfaces:**
- Consumes : `EconomyService.spend`, `DataService.get/replicate`, `Net.sendEvent`, `AnalyticsService.Track`, `buildFloor2`, `refreshSlot`, `PlotLayout.floor2`.
- Produces :
  - `PlotService.tryUnlockFloor(player)` — public (appelé par le ClickDetector du panneau ; réutilisable admin/Net). Valide « 8/8 RDC » + coût, sinon `notify` warn.
  - panneau world-fixed `FloorPanel` (SurfaceGui + ClickDetector) bâti pour tout plot ; `updateFloorPanel(player)` rafraîchit son texte selon l'état.

- [ ] **Step 1 : Ajouter `floorPanel` au type `PlotInfo`** (`multi_edit` sur `PlotService`)

Remplacer exactement :
```luau
type PlotInfo = {
	index: number,
	model: Model,
	origin: CFrame,
	padBySlot: { [string]: BasePart },
	spawnCF: CFrame,
	charConn: RBXScriptConnection?,
}
```
par :
```luau
type PlotInfo = {
	index: number,
	model: Model,
	origin: CFrame,
	padBySlot: { [string]: BasePart },
	spawnCF: CFrame,
	charConn: RBXScriptConnection?,
	floorPanel: BasePart?,
}
```

- [ ] **Step 2 : Ajouter les helpers compteur + panneau + `updateFloorPanel`** (`multi_edit` sur `PlotService`)

Insérer **juste après** `buildFloor2` :
```luau
-- Nombre de baies RDC (floor 0) débloquées + total RDC (pour la condition de prérequis).
local function groundUnlocked(data): (number, number)
	local n, total = 0, 0
	for _, sd in ipairs(PlotLayout.slots) do
		if sd.floor == 0 then
			total += 1
			local s = data.plot.slots[sd.id]
			if s and s.unlocked then
				n += 1
			end
		end
	end
	return n, total
end

-- Rafraîchit le texte/état du panneau d'achat de l'étage.
local function updateFloorPanel(player: Player)
	local info = plots[player]
	local data = Registry.get("DataService").get(player)
	local panel = info and info.floorPanel
	if not info or not data or not panel or not panel.Parent then
		return
	end
	local sg = panel:FindFirstChildOfClass("SurfaceGui")
	local frame = sg and sg:FindFirstChild("Body")
	local status = frame and frame:FindFirstChild("Status")
	if not (status and status:IsA("TextLabel")) then
		return
	end
	local F = PlotLayout.floor2
	if data.plot.floor2Unlocked then
		status.Text = "\u{2713} ÉTAGE DÉBLOQUÉ"
		status.TextColor3 = Color3.fromRGB(150, 240, 150)
	else
		local n, total = groundUnlocked(data)
		if n < total then
			status.Text = string.format("Débloque les %d baies du RDC\n%d / %d", total, n, total)
			status.TextColor3 = Color3.fromRGB(240, 196, 40)
		else
			status.Text = string.format("CONSTRUIRE L'ÉTAGE\n%s $", tostring(F.cost))
			status.TextColor3 = Color3.fromRGB(150, 240, 150)
		end
	end
end

-- Panneau world-fixed (avant-centre, près de l'échelle), cliquable via ClickDetector (serveur).
local function buildFloorPanel(player: Player, info: PlotInfo)
	local origin = info.origin
	local F = PlotLayout.floor2
	local post = makePart("FloorPanelPost", Vector3.new(0.8, 6, 0.8), Color3.fromRGB(54, 59, 70), origin * CFrame.new(F.panelOffset + Vector3.new(0, 3, 0)), info.model)
	post.Material = Enum.Material.Metal; post.CanCollide = false
	local panel = makePart("FloorPanel", Vector3.new(8, 4.4, 0.5), Color3.fromRGB(28, 30, 40), origin * CFrame.new(F.panelOffset + Vector3.new(0, 7, 0)) * CFrame.Angles(0, math.rad(180), 0), info.model)
	panel.Material = Enum.Material.Metal; panel.CanCollide = false
	local sg = Instance.new("SurfaceGui"); sg.Face = Enum.NormalId.Front; sg.CanvasSize = Vector2.new(400, 220); sg.PixelsPerStud = 50; sg.Parent = panel
	local body = Instance.new("Frame"); body.Name = "Body"; body.Size = UDim2.fromScale(1, 1); body.BackgroundColor3 = Color3.fromRGB(28, 30, 40); body.BorderSizePixel = 0; body.Parent = sg
	local bs = Instance.new("UIStroke"); bs.Color = Color3.fromRGB(95, 190, 235); bs.Thickness = 5; bs.Parent = body
	local title = Instance.new("TextLabel"); title.Size = UDim2.new(1, 0, 0.4, 0); title.BackgroundTransparency = 1; title.Font = Enum.Font.LuckiestGuy; title.Text = "ÉTAGE 2"; title.TextColor3 = Color3.fromRGB(255, 220, 120); title.TextStrokeColor3 = Color3.fromRGB(0, 0, 0); title.TextStrokeTransparency = 0.4; title.TextScaled = true; title.Parent = body
	local status = Instance.new("TextLabel"); status.Name = "Status"; status.Position = UDim2.new(0, 0, 0.42, 0); status.Size = UDim2.new(1, 0, 0.55, 0); status.BackgroundTransparency = 1; status.Font = Enum.Font.GothamBlack; status.Text = "…"; status.TextColor3 = Color3.fromRGB(240, 196, 40); status.TextScaled = true; status.Parent = body
	local sc = Instance.new("UITextSizeConstraint"); sc.MaxTextSize = 34; sc.Parent = status
	local cd = Instance.new("ClickDetector"); cd.MaxActivationDistance = 22; cd.Parent = panel
	cd.MouseClick:Connect(function(plr)
		if plr == player then
			PlotService.tryUnlockFloor(player)
		end
	end)
	info.floorPanel = panel
end
```
> ⚠️ `buildFloorPanel` référence `PlotService.tryUnlockFloor` (défini Step 4) ; OK car appelé seulement au clic, après chargement complet du module.

- [ ] **Step 3 : Bâtir le panneau + l'init dans `assignPlot`** (`multi_edit` sur `PlotService`)

Remplacer exactement (le bloc modifié en Task 4 Step 2) :
```luau
	-- Joueur de retour avec l'étage déjà acheté : le reconstruire avant de rafraîchir les slots f*.
	if data.plot.floor2Unlocked then
		buildFloor2(info)
	end

	for slotId in pairs(data.plot.slots) do
		refreshSlot(player, slotId) -- f* no-op tant que leur pad n'existe pas (pad nil -> return)
	end
```
par :
```luau
	-- Panneau d'achat de l'étage (toujours présent). Joueur de retour déjà acheté -> reconstruire.
	buildFloorPanel(player, info)
	if data.plot.floor2Unlocked then
		buildFloor2(info)
	end

	for slotId in pairs(data.plot.slots) do
		refreshSlot(player, slotId) -- f* no-op tant que leur pad n'existe pas (pad nil -> return)
	end
	updateFloorPanel(player)
```

- [ ] **Step 4 : Ajouter `PlotService.tryUnlockFloor`** (`multi_edit` sur `PlotService`)

Insérer **juste avant** `return PlotService` (≈631680) :
```luau
-- Achat de l'étage. Re-validé serveur : prérequis (8/8 RDC) + coût. Appelé par le ClickDetector
-- du panneau (et réutilisable admin/Net). Construit l'étage et débloque le bouton HUD via replicate.
function PlotService.tryUnlockFloor(player: Player)
	local data = Registry.get("DataService").get(player)
	local info = plots[player]
	if not data or not info then
		return
	end
	if data.plot.floor2Unlocked then
		return
	end
	local n, total = groundUnlocked(data)
	if n < total then
		Net.sendEvent(player, "notify", { text = "Débloque d'abord les " .. total .. " baies du rez-de-chaussée !", kind = "warn" })
		return
	end
	local F = PlotLayout.floor2
	if not Registry.get("EconomyService").spend(player, { [F.currency] = F.cost }) then
		Net.sendEvent(player, "notify", { text = "Pas assez de " .. F.currency .. " !", kind = "warn" })
		return
	end
	data.plot.floor2Unlocked = true
	buildFloor2(info)
	for _, sd in ipairs(PlotLayout.slots) do
		if sd.floor == 1 then
			refreshSlot(player, sd.id)
		end
	end
	updateFloorPanel(player)
	Registry.get("DataService").replicate(player)
	Net.sendEvent(player, "notify", { text = "Étage débloqué ! Monte par l'échelle.", kind = "reward" })
	Registry.get("AnalyticsService").Track(player, "floor_unlocked", {})
end
```

- [ ] **Step 5 : Faire progresser le panneau quand une baie RDC se débloque** (`multi_edit` sur `PlotService`, dans `handleUnlock`)

Remplacer exactement :
```luau
	slotData.unlocked = true
	refreshSlot(player, slotId)
	Net.sendEvent(player, "notify", { text = "Slot unlocked!", kind = "reward" })
	Registry.get("DataService").replicate(player)
	Registry.get("AnalyticsService").Track(player, "slot_unlocked", { slot = slotId })
```
par :
```luau
	slotData.unlocked = true
	refreshSlot(player, slotId)
	updateFloorPanel(player) -- fait avancer le compteur "X/8" du panneau d'étage
	Net.sendEvent(player, "notify", { text = "Slot unlocked!", kind = "reward" })
	Registry.get("DataService").replicate(player)
	Registry.get("AnalyticsService").Track(player, "slot_unlocked", { slot = slotId })
```

- [ ] **Step 6 : Relire pour confirmer** — `script_read` sur `PlotService` : `tryUnlockFloor`, `buildFloorPanel`, `updateFloorPanel`, `groundUnlocked` présents ; appels dans `assignPlot` + `handleUnlock`.

- [ ] **Step 7 : Vérif live — flux d'achat complet** — en Play, Script temporaire (vraie VM serveur) :
```luau
local Registry = require(game:GetService("ServerScriptService").Server.Registry)
local PlotService, DataService = Registry.get("PlotService"), Registry.get("DataService")
local plr = game:GetService("Players"):GetPlayers()[1]
local data = DataService.get(plr)

-- 1) Sans prérequis : refus attendu.
PlotService.tryUnlockFloor(plr)
local m = workspace:FindFirstChild("Plot_"..plr.UserId)
print("TAG_A no_prereq deck="..tostring(m:FindFirstChild("Floor2") ~= nil)) -- attendu false

-- 2) Débloque les 8 RDC + argent, puis achète.
for i = 1, 8 do data.plot.slots["s"..i].unlocked = true end
data.currency.scrap = (data.currency.scrap or 0) + 200000
DataService.replicate(plr)
PlotService.tryUnlockFloor(plr)
print("TAG_B bought floor2="..tostring(data.plot.floor2Unlocked).." deck="..tostring(m:FindFirstChild("Floor2") ~= nil))

-- 3) Double achat : pas de re-débit.
local before = data.currency.scrap
PlotService.tryUnlockFloor(plr)
print("TAG_C no_double_charge="..tostring(data.currency.scrap == before))
```
Attendu : `TAG_A no_prereq deck=false` · `TAG_B bought floor2=true deck=true` · `TAG_C no_double_charge=true`. Vérifier le solde scrap débité de 100000 entre les étapes. Supprimer le Script temporaire. (Optionnel : en jeu, débloquer les 8 baies via prompts puis **cliquer le panneau** pour valider le clic réel.)

- [ ] **Step 8 : Checkpoint** — prévenir l'utilisateur qu'il peut sauvegarder (Ctrl+S).

---

