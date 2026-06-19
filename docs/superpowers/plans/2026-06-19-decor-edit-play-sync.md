# Synchronisation décors Édit↔Joueur — Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Re-baker fidèlement les 8 `PlotPreviews` (Workspace.MapBlockout) à partir du code runtime actuel, en état « coque vide débloquée » + zone roulette, pour que le mode Édit (sans joueur) reflète le mode Joueur, sans dérive future.

**Architecture:** Extraire les fonctions de géométrie *pures* déjà presque player-independent (`buildPlot`, `buildBay`, `buildRouletteGeometry`, `buildVendor`), les exporter, puis composer un module `EditPreviewBaker` qui regénère les 8 previews en place. Aucun objet contexte, aucun guard de boot, aucun usage de ServerStorage — la coexistence Édit/live est déjà assurée par le mécanisme existant (`PlotPreview_N` détruites par `assignPlot` à la réclamation).

**Tech Stack:** Roblox Luau ; code édité **dans le place** `build.rbxlx` via les outils Roblox Studio MCP (`script_read`, `multi_edit`, `inspect_instance`, `search_game_tree`, `execute_luau`, `run_script`, `start_stop_play`). Pas de framework de test unitaire — la vérification se fait par inspection MCP + une passe en mode Play.

## Global Constraints

- **Source de vérité** : `build.rbxlx`. Les éditions MCP sont *pending* tant que l'utilisateur n'a pas fait **Ctrl+S** ; un commit git ne capture que l'état sauvegardé.
- **Studio actif** : instance `build.rbxlx` (vérifier via `list_roblox_studios` avant toute mutation ; `set_active_studio` si besoin).
- **Gotchas MCP** (cf. mémoire `roblox-studio-mcp-gotchas`) : `multi_edit` peut silencieusement no-op → **toujours relire** le script après édition pour confirmer ; un Play lancé juste après une édition peut compiler un snapshot périmé ; la VM `execute_luau` Server est **isolée** (tester les services live via un Script temporaire, pas via execute_luau) ; `execute_luau` convient pour la génération de géométrie Edit-mode mais **vérifier la persistance** par `inspect_instance` séparé.
- **État baked cible** : tous slots **débloqués** (cosmétique bleu), **0 machine** (`PreviewMachine`/`UFO_*` exclus), **Floor 1 uniquement** (Floor 2 hors scope), **aucun** `ProximityPrompt`/`ClickDetector`/`Script`, tout `Anchored=true`.
- **Naming** : previews nommées `PlotPreview_<index>` (index 0..7) sous `Workspace.MapBlockout.PlotPreviews` — ne PAS renommer (PlotService les cherche par ce nom, lignes 1308-1309).
- **Anti-dérive** : toute géométrie réutilisée doit vivre en **un seul** endroit appelé par le runtime ET le baker. Ne jamais dupliquer un bloc de géométrie dans le baker.

---

## Task 1 : ShopService — scinder `buildMachine`, extraire `buildRouletteGeometry`, exporter `buildPreviewRoulette`

**Files:**
- Modify: `game.ServerScriptService.Server.Services.ShopService` (buildMachine ~269-288 ; buildGeometry ~329-353 ; ajout exports avant `return ShopService`)

**Interfaces:**
- Consumes: helpers existants `buildPad(hub,O)`, `buildArch(hub,O)`, `buildPlatform(hub,c,i)`, `setPlatformActive(plat,active)`, `placeDecor(hub,name,cf,scale)`, constantes `MAX_PLATFORMS`, `GRID`, `ZONE_YAW`, `PlotLayout.rouletteOffset`, `rot()`.
- Produces:
  - `buildMachine(hub, MO)` — **signature changée** : ne crée plus le ProximityPrompt du levier (retourne le `lever` BasePart pour câblage par l'appelant).
  - `buildRouletteGeometry(hub, O, platformCount)` — géométrie pure de la zone roulette (pad+arche+machine-géo+plateformes+décor), aucune dépendance joueur/data.
  - `ShopService.buildPreviewRoulette(plotModel, origin) -> Model` — crée le sous-modèle `Roulette` parenté à `plotModel`, 1 plateforme active, **sans** prompt/billboard-data.

- [ ] **Step 1 : Relire les zones à modifier (confirmer les numéros de ligne courants)**

Via MCP `script_read` sur `game.ServerScriptService.Server.Services.ShopService` lignes 260-360 et la fin du fichier (`return ShopService`). Confirmer que `buildMachine` se termine à la ligne `prompt.Parent=lever;spinPrompts[prompt]=player` et que `buildGeometry` appelle `buildMachine(hub,O*CFrame.new(0,0,12),player)`.

- [ ] **Step 2 : Scinder `buildMachine` — retirer le prompt, retourner le levier**

Remplacer les 4 dernières lignes de `buildMachine` (création + parent du ProximityPrompt) par un simple `return lever`. Code cible des dernières lignes de la fonction :

```lua
	-- levier (cote +Z, face joueur, a droite)
	local lever=part(hub,"Lever",Vector3.new(0.35,2.4,0.35),STEEL_L,MO*CFrame.new(2.6,3,1.6),Enum.Material.Metal)
	local knob=part(hub,"LeverKnob",Vector3.new(0.9,0.9,0.9),RED,MO*CFrame.new(2.6,4.2,1.6),Enum.Material.SmoothPlastic,BALL)
	lever:SetAttribute("RestCF",lever.CFrame); knob:SetAttribute("RestCF",knob.CFrame)
	return lever
end
```

Et changer la signature ligne 269 de `local function buildMachine(hub,MO,player)` → `local function buildMachine(hub,MO)`.

- [ ] **Step 3 : Extraire `buildRouletteGeometry(hub,O,platformCount)`**

Insérer cette nouvelle fonction **juste avant** `buildGeometry` (avant la ligne 329). Elle reprend telles quelles les lignes de géométrie de `buildGeometry` (335-352) en remplaçant le `count` data-driven par le paramètre `platformCount`, et l'appel machine par la version sans prompt :

```lua
-- Géométrie pure de la zone roulette (réutilisée par le runtime ET le baker Edit-mode).
-- platformCount = nombre de plateformes actives (1 = base, sans upgrade).
local function buildRouletteGeometry(hub,O,platformCount)
	buildPad(hub,O)
	buildArch(hub,O)
	buildMachine(hub,O*CFrame.new(0,0,12))
	for i=1,MAX_PLATFORMS do local g=GRID[i]; local plat=buildPlatform(hub,O*CFrame.new(g.x,0,g.z),i); setPlatformActive(plat,i<=platformCount) end
	-- DECO industrielle (DecorLibrary), non-collidable, posee sur le pad (y~0.2)
	placeDecor(hub,"Floodlight",O*CFrame.new(-22,0.2,18)*rot(0,-100,0),0.9)
	placeDecor(hub,"Floodlight",O*CFrame.new(-22,0.2,-19.5)*rot(0,-152,0),0.9)
	placeDecor(hub,"Floodlight",O*CFrame.new(25,0.2,-19.5)*rot(0,-211,0),0.9)
	placeDecor(hub,"Barrel",O*CFrame.new(-19,0.2,12),1)
	placeDecor(hub,"Barrel",O*CFrame.new(-21,0.2,9.5),1)
	placeDecor(hub,"Barrel",O*CFrame.new(-19.5,0.2,7),0.9)
	placeDecor(hub,"CableSpool",O*CFrame.new(23,0.2,14)*rot(0,20,0),1)
	placeDecor(hub,"ScrapHeap",O*CFrame.new(-21,0.2,-13)*rot(0,40,0),0.9)
end
```

- [ ] **Step 4 : Réécrire `buildGeometry(player)` pour réutiliser la géométrie extraite + recâbler le levier-prompt**

Remplacer le corps de `buildGeometry` (329-353) par :

```lua
local function buildGeometry(player)
	local plot=Registry.get("PlotService").getPlot(player); if not plot then return end
	local model=plot.model
	if model:FindFirstChild("Roulette") then return end
	local hub=Instance.new("Model");hub.Name="Roulette";hub.Parent=model
	local O=plot.origin*CFrame.new(PlotLayout.rouletteOffset)*rot(0,ZONE_YAW,0)
	local data=Registry.get("DataService").get(player)
	local count=1+((data and data.shop and data.shop.slotsLevel) or 0)
	buildRouletteGeometry(hub,O,count)
	-- câblage interactif (runtime only) : prompt du levier + billboard data-driven
	local lever=hub:FindFirstChild("Lever")
	if lever then
		local prompt=Instance.new("ProximityPrompt")
		prompt.ActionText="Tirer le levier (GRATUIT)";prompt.ObjectText="ROULETTE";prompt.HoldDuration=0.3;prompt.MaxActivationDistance=14;prompt.RequiresLineOfSight=false
		prompt.Parent=lever;spinPrompts[prompt]=player
	end
	buildBillboard(hub,O,player)
end
```

(Note : `buildBillboard` reste appelé uniquement par le runtime — il lit `data.shop` et câble des ClickDetectors ; le baker ne l'appelle pas.)

- [ ] **Step 5 : Ajouter l'export `ShopService.buildPreviewRoulette`**

Juste avant `return ShopService` (fin de fichier), insérer :

```lua
-- Exporté pour le générateur Edit-mode (EditPreviewBaker) : zone roulette sans joueur,
-- 1 plateforme active, aucun prompt ni billboard data-driven.
function ShopService.buildPreviewRoulette(plotModel, origin)
	if plotModel:FindFirstChild("Roulette") then plotModel.Roulette:Destroy() end
	local hub=Instance.new("Model");hub.Name="Roulette";hub.Parent=plotModel
	local O=origin*CFrame.new(PlotLayout.rouletteOffset)*rot(0,ZONE_YAW,0)
	buildRouletteGeometry(hub,O,1)
	return hub
end
```

- [ ] **Step 6 : Relire le fichier pour confirmer les 3 éditions (multi_edit peut no-op)**

`script_read` ShopService : vérifier (a) `buildMachine(hub,MO)` se termine par `return lever`, (b) `buildRouletteGeometry` existe avant `buildGeometry`, (c) `buildGeometry` appelle `buildRouletteGeometry(hub,O,count)`, (d) `ShopService.buildPreviewRoulette` existe avant `return ShopService`. Si une édition a no-op, la ré-appliquer.

- [ ] **Step 7 : Vérifier la compilation (pas d'erreur de syntaxe)**

Via MCP `execute_luau` : `local ok,err = pcall(function() return require(game.ServerScriptService.Server.Services.ShopService) end); return ok and "OK" or err`
Attendu : `OK` (le require d'un ModuleScript ne démarre pas le service ; il valide juste la syntaxe et les upvalues).

---

## Task 2 : PlotService — extraire `assemblePlot`, exporter `buildPreviewPlot`, `originForIndex`, helper slot débloqué

**Files:**
- Modify: `game.ServerScriptService.Server.Services.PlotService` (buildPlot ~1006-1189 ; refreshSlot cosmétique ~360-367 ; ajout exports avant `return PlotService`)

**Interfaces:**
- Consumes: `originForIndex(index)`, `makePart`, `buildBay`, `PlotLayout`, et tout le corps géométrique existant de `buildPlot`.
- Produces:
  - `assemblePlot(model, origin) -> { [slotId]=padBasePart }` — cœur géométrique pur extrait de `buildPlot` (base, rim, sell-stall, bays). Aucune dépendance joueur.
  - `setSlotVisual(model, slotId, unlocked)` — applique le cosmétique pad/ring (extrait de `refreshSlot`), partagé runtime+baker.
  - `PlotService.buildPreviewPlot(index) -> Model` — modèle non parenté nommé `PlotPreview_<index>`, slots débloqués, **sans** prompt/machine.
  - `PlotService.originForIndex(index) -> CFrame` — export de la fonction locale (pour le baker / la zone roulette).

- [ ] **Step 1 : Relire `buildPlot` en entier pour borner l'extraction**

`script_read` PlotService lignes 1006-1189. Identifier : (a) la portion 100% géométrie à déplacer dans `assemblePlot` (de la création de `base` jusqu'à la fin de la boucle des bays `buildBay`), (b) ce que `buildPlot` retourne en fin (`PlotInfo` avec `model`, `origin`, `padBySlot`, `spawnCF`), (c) la boucle des bays (vers 1082-1090) qui remplit `padBySlot`.

- [ ] **Step 2 : Créer `assemblePlot(model, origin)` au-dessus de `buildPlot`**

Insérer une nouvelle fonction locale **avant** `buildPlot`. Y déplacer **tout le corps géométrique** de `buildPlot` (base, rim, sell-stall via `sp`, boucle bays) en remplaçant les références `player` (uniquement le nom/attr, lignes 1010-1011) — celles-ci RESTENT dans `buildPlot`, pas dans `assemblePlot`. `assemblePlot` ne prend que `(model, origin)` et **retourne `padBySlot`**. Forme :

```lua
-- Cœur géométrique pur d'un plot (réutilisé par le runtime buildPlot ET le baker Edit-mode).
-- Ne touche AUCUNE donnée joueur. Retourne padBySlot = { [slotId] = padBasePart }.
local function assemblePlot(model: Model, origin: CFrame): { [string]: BasePart }
	-- Base pad
	local base = makePart("Base", PlotLayout.plotSize, PlotLayout.baseColor,
		origin * CFrame.new(0, -PlotLayout.plotSize.Y / 2 + 0.3, 0), model)
	base.Material = Enum.Material.Concrete
	base.TopSurface = Enum.SurfaceType.Smooth
	model.PrimaryPart = base
	-- BaseRim
	local rim = makePart("BaseRim", Vector3.new(PlotLayout.plotSize.X + 2.5, 1.4, PlotLayout.plotSize.Z + 2.5),
		Color3.fromRGB(38, 40, 48), origin * CFrame.new(0, -0.5, 0), model)
	rim.Material = Enum.Material.Metal
	-- … (DÉPLACER ICI VERBATIM le reste de la géométrie de buildPlot : sell-stall `sp(...)`,
	--     y compris la part avec l'attribut IsVendor/VendorAnchor, puis la boucle des bays) …
	local padBySlot = {}
	for i, slotDef in ipairs(PlotLayout.slots) do
		padBySlot[slotDef.id] = buildBay(model, origin, slotDef, i)
	end
	return padBySlot
end
```

**Important** : conserver à l'identique l'ordre et les CFrames du sell-stall (incluant la part portant l'attribut `IsVendor`, repérée à l'inspection sous le nom `VendorAnchor`) — le baker s'en sert pour ancrer le vendeur.

- [ ] **Step 3 : Réduire `buildPlot(player,index)` pour déléguer à `assemblePlot`**

`buildPlot` ne garde que : `origin`, création du `model` + nom/attr joueur, appel `assemblePlot`, puis le retour `PlotInfo`. Forme cible :

```lua
local function buildPlot(player: Player, index: number): PlotInfo
	local origin = originForIndex(index)
	local model = Instance.new("Model")
	model.Name = "Plot_" .. player.UserId
	model:SetAttribute("OwnerUserId", player.UserId)
	local padBySlot = assemblePlot(model, origin)
	-- … (CONSERVER VERBATIM le reste original de buildPlot APRÈS la boucle des bays :
	--     calcul spawnCF, construction de la table PlotInfo retournée, etc.) …
end
```

(Si l'original construisait `padBySlot` inline, supprimer ce bloc puisqu'il provient désormais d'`assemblePlot`. Si l'original faisait d'autres choses entre base et bays, tout est déjà dans `assemblePlot`.)

- [ ] **Step 4 : Extraire `setSlotVisual(model, slotId, unlocked)` et l'appeler depuis `refreshSlot`**

Dans `refreshSlot`, les lignes cosmétiques actuelles sont :

```lua
	pad.Color = slotData.unlocked and PlotLayout.slotColor or PlotLayout.lockedSlotColor
	local locked = not slotData.unlocked
	local zring = info.model:FindFirstChild("SlotRing_" .. slotId)
	if zring and zring:IsA("BasePart") then
		zring.Transparency = locked and 0.6 or 0
		zring.Color = locked and Color3.fromRGB(95, 95, 105) or Color3.fromRGB(95, 180, 230)
	end
```

Créer une fonction locale (au-dessus de `refreshSlot`) :

```lua
-- Cosmétique pad/anneau d'un slot (partagé runtime + baker). N'ajoute AUCUN prompt.
local function setSlotVisual(model: Model, slotId: string, unlocked: boolean)
	local pad = model:FindFirstChild("Slot_" .. slotId)
	if pad and pad:IsA("BasePart") then
		pad.Color = unlocked and PlotLayout.slotColor or PlotLayout.lockedSlotColor
	end
	local zring = model:FindFirstChild("SlotRing_" .. slotId)
	if zring and zring:IsA("BasePart") then
		zring.Transparency = unlocked and 0 or 0.6
		zring.Color = unlocked and Color3.fromRGB(95, 180, 230) or Color3.fromRGB(95, 95, 105)
	end
end
```

Puis dans `refreshSlot`, remplacer le bloc cosmétique ci-dessus par : `setSlotVisual(info.model, slotId, slotData.unlocked)` (en gardant la variable `locked`/`pad` si d'autres lignes en aval s'en servent ; sinon ne garder que l'appel). Relire pour confirmer qu'on n'a pas cassé l'usage de `pad` plus bas (le pad sert encore au parentage des prompts → conserver `local pad = info.padBySlot[slotId]`).

- [ ] **Step 5 : Exporter `originForIndex` et `buildPreviewPlot`**

Avant `return PlotService`, insérer :

```lua
-- Exporté pour le baker Edit-mode.
PlotService.originForIndex = originForIndex

-- Construit une preview « coque vide débloquée » d'un plot (Floor 1, tous slots
-- débloqués, AUCUNE machine, AUCUN prompt). Modèle non parenté, nommé PlotPreview_<index>.
function PlotService.buildPreviewPlot(index: number): Model
	local origin = originForIndex(index)
	local model = Instance.new("Model")
	model.Name = "PlotPreview_" .. index
	local _padBySlot = assemblePlot(model, origin)
	for _, slotDef in ipairs(PlotLayout.slots) do
		setSlotVisual(model, slotDef.id, true) -- débloqué
	end
	return model
end
```

- [ ] **Step 6 : Relire PlotService pour confirmer les éditions (anti no-op)**

`script_read` : vérifier que `assemblePlot` existe, que `buildPlot` est réduit et délègue, que `setSlotVisual` existe et est appelé dans `refreshSlot`, et que les deux exports existent avant `return PlotService`.

- [ ] **Step 7 : Vérifier la compilation**

`execute_luau` : `local ok,err=pcall(function() return require(game.ServerScriptService.Server.Services.PlotService) end); return ok and "OK" or err`
Attendu : `OK`.

---

## Task 3 : Module `EditPreviewBaker` + génération

**Files:**
- Create: `game.ServerScriptService.Tools.EditPreviewBaker` (ModuleScript ; créer le dossier `Tools` s'il n'existe pas)

**Interfaces:**
- Consumes: `PlotService.buildPreviewPlot(index)`, `PlotService.originForIndex(index)`, `ScrapyardService.buildVendor(model, anchor)`, `ShopService.buildPreviewRoulette(model, origin)`.
- Produces: `EditPreviewBaker.run()` — regénère `Workspace.MapBlockout.PlotPreviews` (8 modèles).

- [ ] **Step 1 : Créer le dossier `Tools` et le ModuleScript**

Via MCP : s'assurer que `game.ServerScriptService.Tools` existe (sinon le créer), puis créer le ModuleScript `EditPreviewBaker` avec ce contenu complet :

```lua
--!strict
-- EditPreviewBaker — générateur Edit-mode (re-runnable, idempotent).
-- Regénère Workspace.MapBlockout.PlotPreviews à partir des MÊMES fonctions de géométrie
-- que le runtime, en état « coque vide débloquée » + zone roulette. Aucun prompt/machine.
-- Lancer en Édit : require(game.ServerScriptService.Tools.EditPreviewBaker).run()
local Workspace = game:GetService("Workspace")
local SSS = game:GetService("ServerScriptService")

local PlotService = require(SSS.Server.Services.PlotService)
local ShopService = require(SSS.Server.Services.ScrapyardService and SSS.Server.Services.ShopService)
local ScrapyardService = require(SSS.Server.Services.ScrapyardService)

local PLOT_COUNT = 8

local function findByAttr(root: Instance, attr: string): BasePart?
	for _, p in ipairs(root:GetDescendants()) do
		if p:IsA("BasePart") and p:GetAttribute(attr) then
			return p
		end
	end
	return nil
end

-- Strip tout ce qui ne doit pas exister dans une preview statique, et fige le tout.
local function sanitize(model: Instance)
	for _, d in ipairs(model:GetDescendants()) do
		if d:IsA("ProximityPrompt") or d:IsA("ClickDetector")
			or d:IsA("Script") or d:IsA("LocalScript") or d:IsA("ModuleScript")
			or d:IsA("Humanoid") then
			d:Destroy()
		elseif d:IsA("BasePart") then
			d.Anchored = true
		end
	end
end

local EditPreviewBaker = {}

function EditPreviewBaker.run()
	local blockout = Workspace:FindFirstChild("MapBlockout")
	assert(blockout, "MapBlockout introuvable")
	local old = blockout:FindFirstChild("PlotPreviews")
	if old then old:Destroy() end
	local folder = Instance.new("Folder")
	folder.Name = "PlotPreviews"
	folder.Parent = blockout

	for index = 0, PLOT_COUNT - 1 do
		local model = PlotService.buildPreviewPlot(index)
		-- vendeur (stand) au point d'ancrage IsVendor
		local anchor = findByAttr(model, "IsVendor")
		if anchor then
			ScrapyardService.buildVendor(model, anchor)
		end
		-- zone roulette
		ShopService.buildPreviewRoulette(model, PlotService.originForIndex(index))
		-- fige + nettoie
		sanitize(model)
		model.Parent = folder
	end
	return ("PlotPreviews regénérées : %d modèles"):format(PLOT_COUNT)
end

return EditPreviewBaker
```

(Note : `ShopService` est requis directement ; la garde `SSS.Server.Services.ScrapyardService and …` n'a pas de valeur fonctionnelle — la **remplacer** simplement par `require(SSS.Server.Services.ShopService)`.)

- [ ] **Step 2 : Corriger la ligne du require ShopService**

Éditer la ligne `local ShopService = require(SSS.Server.Services.ScrapyardService and SSS.Server.Services.ShopService)` → `local ShopService = require(SSS.Server.Services.ShopService)`.

- [ ] **Step 3 : Lancer le baker en Édit**

Via MCP `execute_luau` (ou `run_script` selon ce qui persiste les mutations sur le DataModel d'édition) :

```lua
return require(game.ServerScriptService.Tools.EditPreviewBaker).run()
```

Attendu : retour `"PlotPreviews regénérées : 8 modèles"`. **Si la VM est isolée** et que rien n'apparaît sous `MapBlockout.PlotPreviews` à l'inspection (Step 4), exécuter à la place via un **Script temporaire** : créer un `Script` dans `ServerScriptService` contenant `require(game.ServerScriptService.Tools.EditPreviewBaker).run()`, déclencher son exécution, puis le supprimer — ou appeler le baker depuis la barre de commande Studio.

- [ ] **Step 4 : Vérifier le résultat par inspection MCP**

`search_game_tree` path `Workspace.MapBlockout.PlotPreviews` max_depth 2 : attendu **8** Models `PlotPreview_0..7`.
`inspect_instance` `Workspace.MapBlockout.PlotPreviews.PlotPreview_0` : attendu un enfant `Roulette` (Model) et un enfant `Vendor` (Model), `PrimaryPart = Base`.
`execute_luau` de contrôle (compte les éléments interdits) :

```lua
local f=game.Workspace.MapBlockout.PlotPreviews
local prompts,machines=0,0
for _,p in ipairs(f:GetDescendants()) do
  if p:IsA("ProximityPrompt") or p:IsA("ClickDetector") then prompts+=1 end
  if p.Name=="PreviewMachine" or p.Name:match("^UFO_") then machines+=1 end
end
return ("prompts=%d machines=%d count=%d"):format(prompts,machines,#f:GetChildren())
```

Attendu : `prompts=0 machines=0 count=8`.

- [ ] **Step 5 : Vérifier l'alignement des origines**

`execute_luau` : comparer le `WorldPivot`/`Base` de chaque preview à `originForIndex` :

```lua
local PS=require(game.ServerScriptService.Server.Services.PlotService)
local f=game.Workspace.MapBlockout.PlotPreviews
local out={}
for i=0,7 do
  local m=f:FindFirstChild("PlotPreview_"..i)
  local base=m and m:FindFirstChild("Base")
  local o=PS.originForIndex(i)
  if base then
    local d=(base.CFrame.Position - (o*CFrame.new(0,-0.2,0)).Position).Magnitude
    out[#out+1]=("%d:%.2f"):format(i,d)
  end
end
return table.concat(out," ")
```

Attendu : tous les écarts proches de 0 (à l'épaisseur de la base près). Un écart important sur un index → l'origine du preview ne correspond pas au runtime (régression à corriger).

---

## Task 4 : Non-régression runtime (Play) + sauvegarde + commit

**Files:** aucun nouveau ; validation comportementale.

- [ ] **Step 1 : Lancer une session Play**

Via MCP `start_stop_play` (start). Attendre l'init serveur. (Rappel gotcha : si une édition vient d'être faite, laisser le temps à la recompilation ; au besoin stop/start.)

- [ ] **Step 2 : Vérifier la réclamation de plot (preview détruite → plot live construit)**

Le joueur local se voit assigner un plot à l'arrivée. Via un **Script temporaire** côté serveur (la VM execute_luau étant isolée pour le live), logguer : nombre de `PlotPreview_*` restants sous `MapBlockout.PlotPreviews` (doit être 7 après assignation d'un plot), et présence d'un `Plot_<userId>` sous Workspace avec ses enfants `Roulette` + `Vendor`.

Attendu : la preview du plot réclamé est détruite ; un `Plot_<userId>` complet existe (coque, bays, zone roulette, vendeur), géométriquement superposable à l'ancienne preview.

- [ ] **Step 3 : Vérifier visuellement la zone roulette + bays + vendeur du plot live**

`screen_capture` (ou inspection) du plot live : confirmer que la zone roulette est présente et identique à celle bakée, que les bays sont débloqués, que le vendeur est en place. Confirmer l'absence de double-construction (un seul `Roulette`, un seul `Vendor`).

- [ ] **Step 4 : Arrêter le Play**

`start_stop_play` (stop).

- [ ] **Step 5 : Sauvegarde + commit**

Demander à l'utilisateur de faire **Ctrl+S** dans Studio (les éditions MCP sont *pending* jusque-là). Une fois `build.rbxlx` réécrit sur disque :

```bash
git add build.rbxlx docs/superpowers/specs/2026-06-19-decor-edit-play-sync-design.md docs/superpowers/plans/2026-06-19-decor-edit-play-sync.md
git commit -m "feat(decor): re-bake fidèle des PlotPreviews (Édit↔Joueur)

Extraction des géométries pures (assemblePlot, buildRouletteGeometry,
buildPreviewRoulette, buildPreviewPlot) + module EditPreviewBaker.
PlotPreviews regénérées en place: coque vide débloquée + zone roulette,
0 machine, 0 prompt. Runtime non-régressé (mêmes fonctions de géométrie).

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Self-Review (effectuée)

**Couverture spec :**
- Périmètre « tout le décor runtime per-plot » → Task 1 (roulette), Task 2 (plot+bays), baker compose + vendeur (`buildVendor` existant) → Task 3. ✔
- État « coque vide débloquée » → `buildPreviewPlot` (slots débloqués via `setSlotVisual(...,true)`, pas de machine) + `buildPreviewRoulette` (1 plateforme). ✔
- Anti-dérive → géométries extraites en un seul endroit (`assemblePlot`, `buildRouletteGeometry`, `setSlotVisual`) appelées par runtime ET baker. ✔
- Édit-only / live inchangé → re-bake en place sous `PlotPreviews`, mécanisme `assignPlot` inchangé (pas de guard/ServerStorage). ✔
- Floor 2 / machines posées hors scope → non générés par `buildPreviewPlot`. ✔

**Placeholders :** les `-- … (DÉPLACER ICI VERBATIM …)` aux Tasks 2.2/2.3 ne sont pas des TODO mais des instructions d'extraction mécanique d'un bloc existant déjà identifié au Step 2.1 (le code source exact est dans le place, à recopier sans modification). Tout code *nouveau* est fourni complet.

**Cohérence des types/noms :** `buildPreviewPlot`, `originForIndex`, `buildPreviewRoulette`, `buildVendor`, `assemblePlot`, `setSlotVisual`, `buildRouletteGeometry` — noms identiques entre producteur et consommateur. `buildMachine(hub,MO)` (2 args) cohérent entre définition (Task 1.2) et appels (Task 1.3 runtime + buildRouletteGeometry). `PlotPreview_<index>` (0..7) cohérent avec la recherche de `assignPlot`. ✔
