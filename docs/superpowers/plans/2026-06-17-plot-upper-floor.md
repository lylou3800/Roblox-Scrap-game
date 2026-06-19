# Étage supérieur du plot — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ajouter **un (1) étage** au plot joueur — 8 nouveaux slots de griffes (`f1..f8`) déverrouillables un par un —, achetable via un **panneau cliquable** une fois les 8 baies du rez-de-chaussée (RDC) débloquées, accessible par une **échelle escaladable** (TrussPart) et un **bouton HUD haut-centre** qui téléporte haut↔bas.

**Architecture :** Map de slots **unifiée** : `f1..f8` vivent dans `data.plot.slots` et `PlotLayout.slots` (chaque def gagne `floor=0|1`), donc tous les systèmes qui bouclent sur `data.plot.slots` (catch loop, `refreshSlot`, placement, admin) fonctionnent **sans modification**. La géométrie de l'étage ne se construit que si `data.plot.floor2Unlocked == true`. Le RDC et l'étage partagent un helper `buildBay` extrait (même code = même style). Le panneau d'achat est un **ClickDetector** dont le `MouseClick` est connecté côté serveur (patron du billboard de `ShopService`). Le bouton HUD est créé à l'exécution dans `UIController`, visible selon `st.plot.floor2Unlocked`, et téléporte en posant `HumanoidRootPart.CFrame` (patron `SellBtn`).

**Tech Stack :** Roblox Luau · ModuleScripts (`ReplicatedStorage.Shared`, `ServerScriptService.Server.Services`) · GUI runtime · édition + test via le **MCP Roblox Studio**.

**Spec :** `docs/superpowers/specs/2026-06-17-plot-upper-floor-design.md`

## Global Constraints

- **1 seul étage** (pas de N étages — YAGNI ; ne pas généraliser la structure).
- **Monnaie unique `$` = `scrap`** ; dépenses via `Registry.get("EconomyService").spend(player, { scrap = cost })`.
- **Sol monde à `y=0`** ; tout est construit relativement à `info.origin` (CFrame qui encode position + rotation de rangée).
- **Numérotation des baies continue** : RDC = « BAIE 1..8 », étage = « BAIE 9..16 ».
- **Serveur-autoritaire** : tout achat/déblocage re-validé serveur, jamais de confiance client.
- **Rétro-compatibilité** : ajout de champs au `PROFILE_TEMPLATE` uniquement (couvert par `ProfileStore:Reconcile()`).

---

## Notes d'environnement (lire avant de commencer)

- **Pas de framework de test ni de git.** Persistance = **Ctrl+S** de l'utilisateur (écrit le DataModel Edit dans `build.rbxlx`). Chaque tâche finit par un checkpoint « prévenir l'utilisateur qu'il peut sauvegarder ».
- **Édition :** modules existants → `multi_edit` (`datamodel_type="Edit"`). **Après CHAQUE édition, relire (`script_read`) pour confirmer** — `multi_edit` peut silencieusement no-op (memory `roblox-studio-mcp-gotchas`).
- **Test code PUR** (configs `PlotLayout`/`GameConfig`/`Types`) → `execute_luau` en **Edit** qui `require(module:Clone())` puis `assert`. **Toujours cloner** : en Edit, `require` met en cache la 1ʳᵉ version.
- **Test LIVE** (géométrie/服務 `PlotService`, HUD) → en **Play**. La VM `execute_luau(datamodel_type="Server")` est **ISOLÉE** (Registry vide) : pour tourner dans la vraie VM serveur, créer un `Script` temporaire sous `ServerScriptService`, `print("TAG: …")` (lu via `get_console_output`), **puis le supprimer**. Un joueur solo est présent en Play. Visuel → `start_stop_play` + `screen_capture`.
- ⚠️ Studio peut repasser en Play tout seul ; re-vérifier `get_studio_state` avant chaque édition Edit. Play juste après une édition peut compiler un snapshot périmé → ré-éditer puis re-Play.
- **Registry depuis un Script temporaire :** `local Registry = require(game:GetService("ServerScriptService").Server.Registry)` (les services sont sous `ServerScriptService.Server.Services`, le Registry sous `ServerScriptService.Server.Registry`). Si le chemin diffère, le résoudre via `get_studio_state`/recherche d'arbre.

---

## File Structure

| Fichier (chemin DataModel) | Rôle | Action |
|---|---|---|
| `ReplicatedStorage.Shared.Types` | type `plot` (+ `floor2Unlocked`) | Modifier (ligne ≈602660) |
| `ReplicatedStorage.Shared.Config.GameConfig` | `PROFILE_TEMPLATE.plot` (+ `floor2Unlocked`, `f1..f8`) | Modifier (≈600888) |
| `ReplicatedStorage.Shared.Config.PlotLayout` | `floor` sur slots, `floor2` consts, defs `f1..f8` | Modifier (≈601122) |
| `ServerScriptService.Server.Services.PlotService` | `buildBay` extrait, `buildFloor2`, panneau + `tryUnlockFloor`, hooks | Modifier (≈630700) |
| `StarterPlayer…Controllers` via `UIController` | bouton HUD haut-centre (runtime) | Modifier (`UIController` ≈592945) |

---

## Task 1 : Données + types (champ `floor2Unlocked` + slots `f1..f8`)

**Files:**
- Modify: `ReplicatedStorage.Shared.Types` (≈ligne 602660)
- Modify: `ReplicatedStorage.Shared.Config.GameConfig` (`PROFILE_TEMPLATE.plot`, ≈600888–600900)

**Interfaces:**
- Produces: `data.plot.floor2Unlocked: boolean` (défaut `false`) ; `data.plot.slots.f1..f8 = { unlocked=false, ufoUid=nil }`.

- [ ] **Step 1 : Étendre le type `plot`** (`multi_edit` sur `ReplicatedStorage.Shared.Types`, `datamodel_type="Edit"`)

Remplacer exactement :
```luau
	plot: { expansionLevel: number, slots: { [string]: PlotSlotData } },
```
par :
```luau
	plot: { expansionLevel: number, floor2Unlocked: boolean, slots: { [string]: PlotSlotData } },
```

- [ ] **Step 2 : Relire pour confirmer** — `script_read` sur `ReplicatedStorage.Shared.Types`, vérifier que la ligne contient `floor2Unlocked: boolean`.

- [ ] **Step 3 : Étendre `PROFILE_TEMPLATE.plot`** (`multi_edit` sur `ReplicatedStorage.Shared.Config.GameConfig`, `datamodel_type="Edit"`)

Remplacer exactement :
```luau
	plot = {
		expansionLevel = 1,
		slots = {
			s1 = { unlocked = true, ufoUid = nil },
			s2 = { unlocked = true, ufoUid = nil },
			s3 = { unlocked = false, ufoUid = nil },
			s4 = { unlocked = false, ufoUid = nil },
			s5 = { unlocked = false, ufoUid = nil },
			s6 = { unlocked = false, ufoUid = nil },
			s7 = { unlocked = false, ufoUid = nil },
			s8 = { unlocked = false, ufoUid = nil },
		},
	},
```
par :
```luau
	plot = {
		expansionLevel = 1,
		floor2Unlocked = false, -- étage acheté ? (cf. PlotService.tryUnlockFloor)
		slots = {
			s1 = { unlocked = true, ufoUid = nil },
			s2 = { unlocked = true, ufoUid = nil },
			s3 = { unlocked = false, ufoUid = nil },
			s4 = { unlocked = false, ufoUid = nil },
			s5 = { unlocked = false, ufoUid = nil },
			s6 = { unlocked = false, ufoUid = nil },
			s7 = { unlocked = false, ufoUid = nil },
			s8 = { unlocked = false, ufoUid = nil },
			-- Étage (floor 1) : verrouillés, géométrie bâtie seulement si floor2Unlocked.
			f1 = { unlocked = false, ufoUid = nil },
			f2 = { unlocked = false, ufoUid = nil },
			f3 = { unlocked = false, ufoUid = nil },
			f4 = { unlocked = false, ufoUid = nil },
			f5 = { unlocked = false, ufoUid = nil },
			f6 = { unlocked = false, ufoUid = nil },
			f7 = { unlocked = false, ufoUid = nil },
			f8 = { unlocked = false, ufoUid = nil },
		},
	},
```

- [ ] **Step 4 : Relire pour confirmer** — `script_read` sur `GameConfig`, vérifier `floor2Unlocked = false` + `f1..f8` présents.

- [ ] **Step 5 : Test pur (Edit)** — `execute_luau`, `datamodel_type="Edit"` :
```luau
local GC = require(game:GetService("ReplicatedStorage").Shared.Config.GameConfig:Clone())
local p = GC.PROFILE_TEMPLATE.plot
assert(p.floor2Unlocked == false, "floor2Unlocked défaut faux")
local n = 0 ; for k in pairs(p.slots) do n += 1 end
assert(n == 16, "16 slots attendus, got "..n)
for i = 1, 8 do assert(p.slots["f"..i], "slot f"..i.." manquant") ; assert(p.slots["f"..i].unlocked == false, "f"..i.." doit être verrouillé") end
return "OK floor2Unlocked + f1..f8"
```
Attendu : `"OK floor2Unlocked + f1..f8"`.

- [ ] **Step 6 : Checkpoint** — prévenir l'utilisateur qu'il peut sauvegarder (Ctrl+S).

---

## Task 2 : Config `PlotLayout` (champ `floor`, consts `floor2`, defs `f1..f8`)

**Files:**
- Modify: `ReplicatedStorage.Shared.Config.PlotLayout` (≈601122–601151)

**Interfaces:**
- Consumes: rien.
- Produces :
  - chaque entrée de `PlotLayout.slots` porte `floor = 0|1` ;
  - `PlotLayout.slots` contient 16 entrées (s1..s8 floor 0, f1..f8 floor 1) ; les offsets `f*` ont leur `Y = PlotLayout.floor2.height` (relevés au chargement) ;
  - `PlotLayout.floor2 = { height, deckThickness, railHeight, notchHalfW, notchDepth, cost, currency, panelOffset, ladderInset }` ;
  - `PlotLayout.slotById` inclut `f1..f8` (boucle existante inchangée).

- [ ] **Step 1 : Ajouter `floor=0` aux slots RDC + ajouter `f1..f8` + consts `floor2`** (`multi_edit` sur `PlotLayout`, `datamodel_type="Edit"`)

Remplacer exactement :
```luau
	slots = {
		{ id = "s1", offset = Vector3.new(34, 0, -18), tier = 1, unlockCurrency = "scrap", unlockCost = 0 },
		{ id = "s2", offset = Vector3.new(34, 0, 4), tier = 1, unlockCurrency = "scrap", unlockCost = 0 },
		{ id = "s3", offset = Vector3.new(34, 0, 26), tier = 2, unlockCurrency = "scrap", unlockCost = 200 },
		{ id = "s4", offset = Vector3.new(34, 0, 48), tier = 3, unlockCurrency = "scrap", unlockCost = 600 },
		{ id = "s5", offset = Vector3.new(-34, 0, -18), tier = 2, unlockCurrency = "scrap", unlockCost = 1800 },
		{ id = "s6", offset = Vector3.new(-34, 0, 4), tier = 3, unlockCurrency = "scrap", unlockCost = 5000 },
		{ id = "s7", offset = Vector3.new(-34, 0, 26), tier = 4, unlockCurrency = "scrap", unlockCost = 14000 },
		{ id = "s8", offset = Vector3.new(-34, 0, 48), tier = 5, unlockCurrency = "scrap", unlockCost = 40000 },
	},
```
par :
```luau
	-- Étage supérieur : géométrie/échelle/baies bâties seulement si data.plot.floor2Unlocked.
	floor2 = {
		height = 24,          -- hauteur de la dalle (studs) au-dessus du RDC (y=0)
		deckThickness = 1.4,
		railHeight = 4,       -- garde-corps anti-chute
		notchHalfW = 3,       -- demi-largeur de la trémie (ouverture d'échelle, bord avant)
		notchDepth = 12,      -- profondeur de la trémie depuis le bord avant
		ladderInset = 1.2,    -- recul du truss depuis le bord avant
		cost = 100000,        -- prix unique d'achat de l'étage ($/scrap)
		currency = "scrap",
		panelOffset = Vector3.new(12, 0, -56), -- panneau d'achat, avant-centre, près de l'échelle
	},
	slots = {
		{ id = "s1", offset = Vector3.new(34, 0, -18), tier = 1, floor = 0, unlockCurrency = "scrap", unlockCost = 0 },
		{ id = "s2", offset = Vector3.new(34, 0, 4), tier = 1, floor = 0, unlockCurrency = "scrap", unlockCost = 0 },
		{ id = "s3", offset = Vector3.new(34, 0, 26), tier = 2, floor = 0, unlockCurrency = "scrap", unlockCost = 200 },
		{ id = "s4", offset = Vector3.new(34, 0, 48), tier = 3, floor = 0, unlockCurrency = "scrap", unlockCost = 600 },
		{ id = "s5", offset = Vector3.new(-34, 0, -18), tier = 2, floor = 0, unlockCurrency = "scrap", unlockCost = 1800 },
		{ id = "s6", offset = Vector3.new(-34, 0, 4), tier = 3, floor = 0, unlockCurrency = "scrap", unlockCost = 5000 },
		{ id = "s7", offset = Vector3.new(-34, 0, 26), tier = 4, floor = 0, unlockCurrency = "scrap", unlockCost = 14000 },
		{ id = "s8", offset = Vector3.new(-34, 0, 48), tier = 5, floor = 0, unlockCurrency = "scrap", unlockCost = 40000 },
		-- Étage (floor 1) : mêmes X/Z que s1..s8 (colonnes miroir) ; le Y est relevé à floor2.height
		-- juste après cette table. Coûts en continuité de courbe (≈ ×2 par cran depuis s8).
		{ id = "f1", offset = Vector3.new(34, 0, -18), tier = 5, floor = 1, unlockCurrency = "scrap", unlockCost = 120000 },
		{ id = "f2", offset = Vector3.new(34, 0, 4), tier = 6, floor = 1, unlockCurrency = "scrap", unlockCost = 250000 },
		{ id = "f3", offset = Vector3.new(34, 0, 26), tier = 6, floor = 1, unlockCurrency = "scrap", unlockCost = 500000 },
		{ id = "f4", offset = Vector3.new(34, 0, 48), tier = 7, floor = 1, unlockCurrency = "scrap", unlockCost = 1000000 },
		{ id = "f5", offset = Vector3.new(-34, 0, -18), tier = 7, floor = 1, unlockCurrency = "scrap", unlockCost = 2000000 },
		{ id = "f6", offset = Vector3.new(-34, 0, 4), tier = 8, floor = 1, unlockCurrency = "scrap", unlockCost = 4000000 },
		{ id = "f7", offset = Vector3.new(-34, 0, 26), tier = 8, floor = 1, unlockCurrency = "scrap", unlockCost = 8000000 },
		{ id = "f8", offset = Vector3.new(-34, 0, 48), tier = 9, floor = 1, unlockCurrency = "scrap", unlockCost = 16000000 },
	},
```

- [ ] **Step 2 : Relever le Y des slots de l'étage à `floor2.height`** (`multi_edit` sur `PlotLayout`)

Remplacer exactement :
```luau
local slotById = {}
for _, s in ipairs(PlotLayout.slots) do slotById[s.id] = s end
PlotLayout.slotById = slotById
return PlotLayout
```
par :
```luau
-- Les baies de l'étage partagent les X/Z du RDC ; on relève leur Y une fois ici (DRY :
-- suit floor2.height). buildBay et refreshSlot lisent slotDef.offset tel quel ensuite.
for _, s in ipairs(PlotLayout.slots) do
	if s.floor == 1 then
		s.offset = s.offset + Vector3.new(0, PlotLayout.floor2.height, 0)
	end
end
local slotById = {}
for _, s in ipairs(PlotLayout.slots) do slotById[s.id] = s end
PlotLayout.slotById = slotById
return PlotLayout
```

- [ ] **Step 3 : Relire pour confirmer** — `script_read` sur `PlotLayout` : `floor2` présent, 16 slots avec `floor`, boucle de relevage présente.

- [ ] **Step 4 : Test pur (Edit)** — `execute_luau`, `datamodel_type="Edit"` :
```luau
local PL = require(game:GetService("ReplicatedStorage").Shared.Config.PlotLayout:Clone())
assert(PL.floor2 and PL.floor2.height == 24, "floor2.height")
local g, f = 0, 0
for _, s in ipairs(PL.slots) do
	assert(s.floor == 0 or s.floor == 1, "floor manquant sur "..s.id)
	if s.floor == 0 then g += 1 else f += 1 ; assert(s.offset.Y == PL.floor2.height, s.id.." Y non relevé ("..s.offset.Y..")") end
end
assert(g == 8 and f == 8, "attendu 8 RDC + 8 étage, got "..g.."/"..f)
assert(PL.slotById.f8 and PL.slotById.f8.unlockCost == 16000000, "slotById.f8")
assert(PL.slotById.s1.offset.Y == 0, "s1 Y doit rester 0")
return "OK PlotLayout floor/floor2/f1..f8"
```
Attendu : `"OK PlotLayout floor/floor2/f1..f8"`.

- [ ] **Step 5 : Checkpoint** — prévenir l'utilisateur qu'il peut sauvegarder (Ctrl+S).

---

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

## Task 6 : Bouton HUD haut-centre (téléport haut↔bas)

**Files:**
- Modify: `UIController` (LocalScript, ≈592945–593203) — créer le bouton à l'exécution + le câbler

**Interfaces:**
- Consumes : `hud` (MainHUD), `StateController.get()/onChanged`, `PlotLayout.floor2.height`, `Theme`.
- Produces : un `TextButton` `FloorBtn` parenté à `hud`, ancré haut-centre, visible ssi `st.plot.floor2Unlocked`, label basculant selon la hauteur Y du personnage, téléportant via `HumanoidRootPart.CFrame`.

- [ ] **Step 1 : Require `PlotLayout` côté client** (`multi_edit` sur `UIController`)

Remplacer exactement :
```luau
local Pricing=require(RS.Shared.Config.Pricing)
```
par :
```luau
local Pricing=require(RS.Shared.Config.Pricing)
local PlotLayout=require(RS.Shared.Config.PlotLayout)
```

- [ ] **Step 2 : Créer + câbler le bouton d'étage** (`multi_edit` sur `UIController`)

Remplacer exactement :
```luau
qbtn("SellBtn", function()
	-- Amene le joueur DEVANT l'echoppe du vendeur (et non sur la dalle/dedans), face au comptoir.
	local plot=workspace:FindFirstChild("Plot_"..player.UserId)
	local pad=plot and plot:FindFirstChild("SellPad")
	local char=player.Character; local hrp=char and char:FindFirstChild("HumanoidRootPart")
	if pad and hrp then hrp.CFrame=pad.CFrame*CFrame.new(0,3.5,-12)*CFrame.Angles(0,math.pi,0) end
end)
qbtn("BuildBtn",function() req("buildMachine",{defId="recycler"}) end)
```
par :
```luau
qbtn("SellBtn", function()
	-- Amene le joueur DEVANT l'echoppe du vendeur (et non sur la dalle/dedans), face au comptoir.
	local plot=workspace:FindFirstChild("Plot_"..player.UserId)
	local pad=plot and plot:FindFirstChild("SellPad")
	local char=player.Character; local hrp=char and char:FindFirstChild("HumanoidRootPart")
	if pad and hrp then hrp.CFrame=pad.CFrame*CFrame.new(0,3.5,-12)*CFrame.Angles(0,math.pi,0) end
end)
qbtn("BuildBtn",function() req("buildMachine",{defId="recycler"}) end)

-- ===== Bouton d'étage (haut-centre) : apparait quand l'étage est débloque, telep. haut<->bas =====
local FLOOR_H=PlotLayout.floor2.height
local floorBtn=Instance.new("TextButton")
floorBtn.Name="FloorBtn"
floorBtn.AnchorPoint=Vector2.new(0.5,0)
floorBtn.Position=UDim2.new(0.5,0,0,12)
floorBtn.Size=UDim2.fromOffset(220,46)
floorBtn.AutoButtonColor=true
floorBtn.BackgroundColor3=P.Purple
floorBtn.Font=Theme.Font.Body
floorBtn.Text="\u{25B2} Monter à l'étage"
floorBtn.TextColor3=P.White
floorBtn.TextScaled=true
floorBtn.Visible=false
floorBtn.Parent=hud
Theme.Corner(floorBtn,UDim.new(0,12))
Theme.Stroke(floorBtn,P.Outline,2.5)
Theme.TextStroke(floorBtn,2)
local fbc=Instance.new("UITextSizeConstraint");fbc.MaxTextSize=20;fbc.Parent=floorBtn

local function onUpperFloor()
	local char=player.Character; local hrp=char and char:FindFirstChild("HumanoidRootPart")
	return hrp ~= nil and hrp.Position.Y > (FLOOR_H/2)
end
local function updateFloorLabel()
	floorBtn.Text=onUpperFloor() and "\u{25BC} Descendre" or "\u{25B2} Monter à l'étage"
end
floorBtn.MouseButton1Click:Connect(function()
	local plot=workspace:FindFirstChild("Plot_"..player.UserId)
	local base=plot and plot:FindFirstChild("Base")
	local char=player.Character; local hrp=char and char:FindFirstChild("HumanoidRootPart")
	if not (base and hrp) then return end
	if onUpperFloor() then
		hrp.CFrame=base.CFrame*CFrame.new(0,4,-54) -- retour au RDC (zone de spawn)
	else
		hrp.CFrame=base.CFrame*CFrame.new(0,FLOOR_H+4,-50) -- arrivee sur la dalle, pres de la tremie
	end
	task.wait(0.1)
	updateFloorLabel()
end)
local function refreshFloorBtn(st)
	local unlocked=st and st.plot and st.plot.floor2Unlocked==true
	floorBtn.Visible=unlocked
	if unlocked then updateFloorLabel() end
end
StateController.onChanged(refreshFloorBtn)
refreshFloorBtn(StateController.get())
-- Met a jour le label si le joueur change d'etage par l'echelle (sans cliquer le bouton).
task.spawn(function()
	while true do
		task.wait(0.5)
		if floorBtn.Visible then updateFloorLabel() end
	end
end)
```

- [ ] **Step 3 : Relire pour confirmer** — `script_read` sur `UIController` : `floorBtn` créé, `StateController.onChanged(refreshFloorBtn)`, require `PlotLayout`.

- [ ] **Step 4 : Vérif live — visibilité + téléport** — en Play :
  1. Au spawn (étage non débloqué) → `screen_capture` : **pas** de bouton haut-centre.
  2. Script temporaire serveur (réutiliser Task 5 Step 7 §2) pour débloquer l'étage → après `replicate`, `screen_capture` : bouton « ▲ Monter à l'étage » visible haut-centre.
  3. `user_mouse_input` clic sur le bouton (ou téléport manuel) → vérifier que le perso monte sur la dalle ; `screen_capture` : label devient « ▼ Descendre ».
  4. Re-clic → retour RDC ; label « ▲ Monter à l'étage ».
  5. Monter par l'échelle (sans cliquer) puis attendre ~0.6s → label « ▼ Descendre » (boucle de rafraîchissement).
- [ ] **Step 5 : Checkpoint** — prévenir l'utilisateur qu'il peut sauvegarder (Ctrl+S).

---

## Task 7 : Vérification d'intégration + edge cases

**Files:** aucun (vérification seulement).

- [ ] **Step 1 : Rétro-compat profil existant** — en Play avec un profil pré-existant (ou simuler : Script temporaire qui retire `floor2Unlocked` et `f*` d'un `data.plot` puis appelle `DataService` reconcile/au prochain join). Vérifier via Script temporaire :
```luau
local Registry = require(game:GetService("ServerScriptService").Server.Registry)
local data = Registry.get("DataService").get(game:GetService("Players"):GetPlayers()[1])
local okF = data.plot.floor2Unlocked ~= nil
local okSlots = data.plot.slots.f1 ~= nil and data.plot.slots.f8 ~= nil
print("TAG_RECON: floor2Unlocked="..tostring(okF).." f1="..tostring(okSlots))
```
Attendu : `TAG_RECON: floor2Unlocked=true f1=true` (Reconcile a backfillé). Supprimer le Script.

- [ ] **Step 2 : Catch loop sur les baies de l'étage** — étage débloqué, débloquer une baie `f*` (prompt « Unlock ») puis y poser un UFO (prompt « Place UFO »). Vérifier via Script temporaire que `data.plot.slots.f1.ufoUid` est set et que la production tourne (le compteur scrap augmente, ou `CatchService` traite la baie). Attendu : la baie de l'étage produit comme une baie RDC (la boucle itère `data.plot.slots` génériquement).

- [ ] **Step 3 : Visiteur** — 2e joueur (ou simuler) : monter sur le plot d'un autre via l'échelle truss (doit fonctionner physiquement) ; vérifier que **son** `FloorBtn` est lié à **son** plot (pas celui du proprio visité). Le bouton ne doit pas apparaître/agir sur le plot d'autrui.

- [ ] **Step 4 : Respawn + chute** — à l'étage, se faire respawn (reset) → réapparaître au RDC (`spawnCF`, inchangé). Vérifier que les garde-corps empêchent de tomber de la dalle (faire le tour) et que la trémie est bordée (rails latéraux).

- [ ] **Step 5 : Idempotence** — appeler `PlotService.tryUnlockFloor` une 2e fois (Script temporaire) → pas de dalle dupliquée (garde `Floor2`), pas de re-débit (déjà couvert TAG_C). `screen_capture` : une seule dalle/échelle.

- [ ] **Step 6 : Récap final** — `screen_capture` du plot complet (RDC + étage) ; confirmer le style cohérent (DiamondPlate/métal/néons/placards), l'éclairage sous-dalle (RDC pas trop sombre). Noter tout ajustement de tuning (hauteur dalle, position panneau, recul échelle) à appliquer.

- [ ] **Step 7 : Checkpoint final** — prévenir l'utilisateur qu'il peut sauvegarder (Ctrl+S) et lister ce qui reste éventuellement à tuner.

---

## Notes de tuning (non bloquantes)

- `floor2.height=24` donne le dégagement au-dessus des machines RDC ; ajuster si une machine de rang élevé dépasse.
- `panelOffset (12,0,-56)` / orientation du panneau : à ajuster en Studio pour qu'il fasse face au joueur arrivant du spawn.
- Le **Nameplate** (billboard à `nameplateOffset (0,22,60)`, y=22) peut frôler le bord arrière de la dalle (y≈23.7) ; si chevauchement visuel, remonter le nameplate ou rentrer la dalle de quelques studs au fond.
- L'échelle `TrussPart` (bord avant) doit rester accessible depuis l'allée ; si le climb accroche mal, augmenter légèrement `ladderInset` ou la largeur de trémie `notchHalfW`.
