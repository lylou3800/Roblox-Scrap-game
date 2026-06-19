## Task 3 : Refactor — extraire `buildBay` (aucun changement visuel RDC)

**Files:**
- Modify: `ServerScriptService.Server.Services.PlotService` (consts bay ≈631241–631251 → module scope ; boucle ≈631262–631332 → `buildBay`)

**Interfaces:**
- Produces (module-local) : `buildBay(model: Model, origin: CFrame, slotDef, displayNum: number) -> BasePart` (retourne le pad `Slot_<id>`). Construit une baie complète (ZoneFloor/Inset/Curb/Posts/Wall/placard « BAIE <displayNum> »/ring/pad/tas) à `origin * CFrame.new(slotDef.offset)`.
- Consumes : `makePart`, `PlotLayout`, constantes bay (relevées au scope module).

But du refactor : `buildBay` doit produire **exactement** la même géométrie qu'aujourd'hui pour le RDC (même noms de parts, mêmes tailles/couleurs/seed). Seul changement : le numéro de baie affiché devient un paramètre `displayNum` (au lieu de l'index `i`), et la seed du tas devient `displayNum * 7 + 13` (identique pour le RDC car `displayNum == i`).

- [ ] **Step 1 : Lever les constantes de baie au scope module** (`multi_edit` sur `PlotService`, `datamodel_type="Edit"`)

Insérer **juste avant** `local function buildPlot(player: Player, index: number): PlotInfo` (≈631163) le bloc suivant. (Ces couleurs étaient locales à `buildPlot` ; `HAZ` reste utilisé par la section « Sorter PC » de `buildPlot` après l'extraction, d'où le passage au scope module.)
```luau
-- ===== palette des baies (partagée RDC + étage via buildBay) =====
local BAY_CONCRETE = Color3.fromRGB(86, 90, 100)
local BAY_CONCRETE_D = Color3.fromRGB(58, 61, 70)
local STEEL_BAY = Color3.fromRGB(104, 112, 126)
local STEEL_BAY_D = Color3.fromRGB(54, 59, 70)
local HAZ = Color3.fromRGB(240, 196, 40)
local CYAN = Color3.fromRGB(95, 190, 235)
local SCRAP_COLORS = {
	Color3.fromRGB(206, 78, 70), Color3.fromRGB(74, 142, 214), Color3.fromRGB(232, 188, 70),
	Color3.fromRGB(96, 178, 110), Color3.fromRGB(150, 158, 170), Color3.fromRGB(208, 124, 60),
	Color3.fromRGB(120, 132, 150), Color3.fromRGB(196, 202, 212),
}

-- Construit UNE baie complète (pit industriel + tas + placard + ring + pad) à slotDef.offset.
-- displayNum = numéro affiché ("BAIE n") ET seed du tas (n*7+13). Retourne le pad Slot_<id>.
local function buildBay(model: Model, origin: CFrame, slotDef, displayNum: number): BasePart
	local function bayPart(nm, size, color, cf, mat, shape)
		local p = makePart(nm, size, color, cf, model)
		p.Material = mat or Enum.Material.Metal
		p.CanCollide = false
		if shape then p.Shape = shape end
		p.TopSurface = Enum.SurfaceType.Smooth
		p.BottomSurface = Enum.SurfaceType.Smooth
		return p
	end
	local zc = slotDef.offset
	local zs = PlotLayout.zoneSize
	local wh = PlotLayout.zoneWallHeight
	local outer = (zc.X < 0) and -1 or 1
	local innerX = -outer

	bayPart("ZoneFloor_" .. slotDef.id, Vector3.new(zs.X, 0.6, zs.Z), BAY_CONCRETE, origin * CFrame.new(zc), Enum.Material.Concrete)
	bayPart("ZoneInset_" .. slotDef.id, Vector3.new(zs.X - 4, 0.6, zs.Z - 4), BAY_CONCRETE_D, origin * CFrame.new(zc + Vector3.new(0, 0.08, 0)), Enum.Material.DiamondPlate)
	bayPart("ZoneCurb_" .. slotDef.id, Vector3.new(zs.X, 0.8, 0.8), STEEL_BAY_D, origin * CFrame.new(zc + Vector3.new(0, 0.4, zs.Z / 2)), Enum.Material.Metal)
	bayPart("ZoneCurb_" .. slotDef.id, Vector3.new(zs.X, 0.8, 0.8), STEEL_BAY_D, origin * CFrame.new(zc + Vector3.new(0, 0.4, -zs.Z / 2)), Enum.Material.Metal)
	bayPart("ZoneCurbHaz_" .. slotDef.id, Vector3.new(0.8, 0.85, zs.Z), HAZ, origin * CFrame.new(zc + Vector3.new(innerX * (zs.X / 2), 0.42, 0)), Enum.Material.SmoothPlastic)
	for _, sx in ipairs({ -1, 1 }) do
		for _, sz in ipairs({ -1, 1 }) do
			bayPart("ZonePost_" .. slotDef.id, Vector3.new(1.1, wh, 1.1), STEEL_BAY, origin * CFrame.new(zc + Vector3.new(sx * (zs.X / 2 - 0.7), wh / 2 + 0.3, sz * (zs.Z / 2 - 0.7))), Enum.Material.Metal)
			bayPart("ZonePostCap_" .. slotDef.id, Vector3.new(1.3, 0.5, 1.3), HAZ, origin * CFrame.new(zc + Vector3.new(sx * (zs.X / 2 - 0.7), wh + 0.3, sz * (zs.Z / 2 - 0.7))), Enum.Material.SmoothPlastic)
		end
	end
	bayPart("ZoneWall_" .. slotDef.id, Vector3.new(1.0, wh + 1, zs.Z - 1.4), STEEL_BAY, origin * CFrame.new(zc + Vector3.new(outer * (zs.X / 2 - 0.5), (wh + 1) / 2 + 0.3, 0)), Enum.Material.Metal)
	bayPart("ZoneWallTrim_" .. slotDef.id, Vector3.new(1.05, 0.6, zs.Z - 1.4), HAZ, origin * CFrame.new(zc + Vector3.new(outer * (zs.X / 2 - 0.5), wh + 0.6, 0)), Enum.Material.SmoothPlastic)

	local signX = innerX * (zs.X / 2 - 0.8)
	local signZ = -(zs.Z / 2 - 0.8)
	local spost = makePart("ZonePostSign_" .. slotDef.id, Vector3.new(0.55, 3.4, 0.55), STEEL_BAY, origin * CFrame.new(zc + Vector3.new(signX, 1.7, signZ)), model)
	spost.Material = Enum.Material.Metal; spost.CanCollide = false
	local board = makePart("ZoneSign_" .. slotDef.id, Vector3.new(3.6, 1.7, 0.22), Color3.fromRGB(26, 28, 36), origin * CFrame.new(zc + Vector3.new(signX, 4.25, signZ)) * CFrame.Angles(0, innerX > 0 and math.rad(-90) or math.rad(90), 0), model)
	board.Material = Enum.Material.SmoothPlastic; board.CanCollide = false
	local bsg = Instance.new("SurfaceGui"); bsg.Face = Enum.NormalId.Front; bsg.CanvasSize = Vector2.new(360, 170); bsg.PixelsPerStud = 50; bsg.Parent = board
	local bf = Instance.new("Frame"); bf.Size = UDim2.fromScale(1, 1); bf.BackgroundColor3 = Color3.fromRGB(26, 28, 36); bf.BorderSizePixel = 0; bf.Parent = bsg
	local bfs = Instance.new("UIStroke"); bfs.Color = CYAN; bfs.Thickness = 4; bfs.Parent = bf
	local btl = Instance.new("TextLabel"); btl.Size = UDim2.fromScale(1, 1); btl.BackgroundTransparency = 1; btl.TextScaled = true; btl.Font = Enum.Font.GothamBlack; btl.Text = "BAIE " .. displayNum; btl.TextColor3 = Color3.fromRGB(255, 220, 120); btl.TextStrokeColor3 = Color3.fromRGB(0, 0, 0); btl.TextStrokeTransparency = 0.4; btl.Parent = bf

	local ring = makePart("SlotRing_" .. slotDef.id, Vector3.new(0.4, 7.6, 7.6), CYAN, origin * CFrame.new(slotDef.offset + Vector3.new(0, 0.42, 0)) * CFrame.Angles(0, 0, math.rad(90)), model)
	ring.Shape = Enum.PartType.Cylinder; ring.Material = Enum.Material.Neon; ring.CanCollide = false
	local pad = makePart("Slot_" .. slotDef.id, Vector3.new(7, 1, 7), PlotLayout.lockedSlotColor, origin * CFrame.new(slotDef.offset + Vector3.new(0, 0.55, 0)), model)
	pad.Material = Enum.Material.DiamondPlate; pad.CanCollide = false
	pad:SetAttribute("SlotId", slotDef.id)

	local pileC = zc + Vector3.new(-outer * 12.5, 0, 0)
	bayPart("DebrisPile_" .. slotDef.id, Vector3.new(12, 4.6, 13.5), Color3.fromRGB(78, 84, 96), origin * CFrame.new(pileC + Vector3.new(0, 1.0, 0)), Enum.Material.Slate, Enum.PartType.Ball)
	local rng = Random.new(displayNum * 7 + 13)
	local function scrap(sz, col, mat, shape, hx, hy, hz, rx, ry, rz)
		bayPart("DebrisBit_" .. slotDef.id, sz, col, origin * CFrame.new(pileC + Vector3.new(hx, hy, hz)) * CFrame.Angles(rx, ry, rz), mat, shape)
	end
	for b = 1, 22 do
		local ang = rng:NextNumber(0, math.pi * 2)
		local rad = rng:NextNumber(0.3, 5.3)
		local hx, hz = math.cos(ang) * rad, math.sin(ang) * rad * 1.1
		local hy = rng:NextNumber(0.5, 3.4)
		local col = SCRAP_COLORS[rng:NextInteger(1, #SCRAP_COLORS)]
		local rx, ry, rz = rng:NextNumber(0, 3), rng:NextNumber(0, 3), rng:NextNumber(0, 3)
		local kind = rng:NextInteger(1, 6)
		if kind <= 2 then
			local s = rng:NextNumber(1.2, 2.6)
			scrap(Vector3.new(s, s * rng:NextNumber(0.5, 0.9), s), col, Enum.Material.SmoothPlastic, nil, hx, hy, hz, rx, ry, rz)
		elseif kind == 3 then
			scrap(Vector3.new(rng:NextNumber(1.6, 2.4), 1.5, 1.5), col, Enum.Material.Metal, Enum.PartType.Cylinder, hx, hy, hz, rx, ry, rz)
		elseif kind == 4 then
			scrap(Vector3.new(rng:NextNumber(2.6, 4.2), 0.8, 0.8), Color3.fromRGB(150, 158, 170), Enum.Material.Metal, Enum.PartType.Cylinder, hx, hy, hz, rx, ry, rz)
		elseif kind == 5 then
			scrap(Vector3.new(0.75, 2.0, 2.0), Color3.fromRGB(34, 34, 40), Enum.Material.SmoothPlastic, Enum.PartType.Cylinder, hx, hy, hz, rx, ry, rz)
		else
			scrap(Vector3.new(rng:NextNumber(2.0, 3.4), 0.35, rng:NextNumber(1.6, 2.6)), (rng:NextInteger(1, 2) == 1) and col or Color3.fromRGB(150, 158, 170), Enum.Material.DiamondPlate, nil, hx, hy * 0.6 + 0.3, hz, rx * 0.2, ry, rz * 0.2)
		end
	end
	scrap(Vector3.new(1.0, 1.0, 1.0), Color3.fromRGB(130, 245, 190), Enum.Material.Neon, nil, rng:NextNumber(-2, 2), 3.3, rng:NextNumber(-2, 2), 0.4, 0.8, 0.2)

	return pad
end
```

- [ ] **Step 2 : Remplacer la boucle de baies inline de `buildPlot` par des appels `buildBay`** (`multi_edit` sur `PlotService`)

Remplacer exactement le bloc allant de :
```luau
	-- Slot bays: clean industrial pit + a big stylized scrap pile the grapple digs into.
	local CONCRETE = Color3.fromRGB(86, 90, 100)
```
… jusqu'à la fin de la boucle (la ligne `padBySlot[slotDef.id] = pad` puis le `end` de boucle, ≈631331–631332) par :
```luau
	-- Slot bays (RDC = floor 0 ; l'étage est bâti à part par buildFloor2). Voir buildBay.
	local padBySlot: { [string]: BasePart } = {}
	for i, slotDef in ipairs(PlotLayout.slots) do
		if slotDef.floor == 0 then
			padBySlot[slotDef.id] = buildBay(model, origin, slotDef, i)
		end
	end
```
> ⚠️ Ce remplacement supprime les déclarations locales `CONCRETE/CONCRETE_D/STEEL_BAY/STEEL_BAY_D/HAZ/CYAN/SCRAP_COLORS`, la closure `bayPart`, l'ancien `local padBySlot = {}` (≈631261) et tout le corps de boucle. La section « Sorter PC » qui suit utilise `HAZ` → désormais résolu au scope module (Step 1). Vérifier qu'**aucune** autre référence locale à ces noms ne subsiste dans `buildPlot`.

- [ ] **Step 3 : Relire pour confirmer** — `script_read` sur `PlotService` autour de `buildBay` et de la nouvelle boucle ; vérifier que `HAZ` n'est plus déclaré localement dans `buildPlot` et que la section Sorter (`SorterPCHaz`, `HAZ`) compile.

- [ ] **Step 4 : Vérif live — le RDC est inchangé** — `start_stop_play`, attendre le spawn, puis `screen_capture`. Comparer visuellement : 8 baies « BAIE 1..8 », placards/tas/anneaux identiques. Puis Script temporaire (vraie VM serveur) :
```luau
local plr = game:GetService("Players"):GetPlayers()[1]
local model = workspace:FindFirstChild("Plot_"..plr.UserId)
local ok = model ~= nil
for i = 1, 8 do ok = ok and (model:FindFirstChild("Slot_s"..i) ~= nil) end
local f1 = model and model:FindFirstChild("Slot_f1")
print("TAG_BAY: model="..tostring(ok).." f1_absent="..tostring(f1 == nil))
```
Lire via `get_console_output`. Attendu : `TAG_BAY: model=true f1_absent=true` (les baies RDC existent, aucune baie étage tant que non débloqué). Supprimer le Script temporaire.

- [ ] **Step 5 : Checkpoint** — prévenir l'utilisateur qu'il peut sauvegarder (Ctrl+S).

---

