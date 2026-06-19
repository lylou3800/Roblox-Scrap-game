# Visuels des récompenses + HUD des boosts actifs — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remplacer les icônes de récompense « cheap » du menu CADEAUX par des visuels premium glossy-3D (image IA Higgsfield + secours construit + ViewportFrame 3D pour œuf/pet), reconstruire le HUD des boosts actifs en bas à droite (badges icône empilés, hiérarchie, timer dessous), et retirer une phrase d'onboarding obsolète.

**Architecture :** Pipeline hybride. Un nouveau module partagé `ReplicatedStorage.Shared.RewardIcons` est la **source unique** d'icônes : il résout chaque clé d'icône vers (1) une image IA uploadée si son asset-id est renseigné, (2) un `ViewportFrame` du vrai mesh pour œuf/pet, sinon (3) un emblème construit. Les deux consommateurs (carte CADEAUX + badge HUD) passent par ce module, ce qui garantit qu'aucune icône n'est jamais vide même avant la modération Roblox des images. Une retouche serveur minimale expose `duration` pour la barre de progression des badges. Aucune logique gameplay touchée.

**Tech Stack :** Luau / Roblox ; édition via le **Roblox Studio MCP** (le code vit dans `build.rbxlx`, ouvert dans Studio) ; `ReplicatedStorage.UI.Theme` (style) ; `ReplicatedStorage.Shared.ScrapIcons` (vecteurs) ; meshes `ReplicatedStorage.Assets.EggMeshes` / `.PetMeshes` ; CLI Higgsfield (`@higgsfield/cli`) pour la génération d'images.

## Modèle de test (adapté Roblox/MCP)

Ce dépôt n'a **pas** de harnais de tests unitaires (pas de pytest). Le « cycle de test » de chaque tâche est :
1. **Éditer** le script via le MCP (`mcp__Roblox_Studio__multi_edit` / création de script / `execute_luau` pour créer une instance).
2. **Relire** (`mcp__Roblox_Studio__script_read` / `script_grep`) pour **confirmer que l'édition a bien pris** — `multi_edit` peut no-op silencieusement (cf. [[roblox-studio-mcp-gotchas]]).
3. **Booter** (`mcp__Roblox_Studio__start_stop_play`) puis `get_console_output` : zéro erreur, compteurs services/contrôleurs inchangés.
4. **Vérifier le rendu** (`screen_capture` / `inspect_instance`) quand la tâche est visuelle.
5. **Persister + commit** : demander à l'utilisateur de **Ctrl+S** dans Studio (écrit `build.rbxlx`), puis `git commit`.

> Avant la 1ʳᵉ tâche : confirmer la connexion Studio avec `mcp__Roblox_Studio__list_roblox_studios` puis `set_active_studio`. `execute_luau` (VM serveur) est **isolé** des handlers de remotes live — ne pas s'en servir pour « tester » un claim de bout en bout ; s'en servir pour créer des instances / lire l'arbre / vérifier des valeurs.

## Global Constraints

- **Style** : tout passe par `ReplicatedStorage.UI.Theme` (Palette/Font/Corner/Stroke/TextStroke/Gradient/darken/Panel/Button/Pill). Ne **pas** utiliser `UIUtil`. Palette utile : `Confirm 5FD41A`, `Gold F2C019`, `Purple 8B4FE0`, `Cyan 29C7E0`, `Pink EF3F6F`, `Danger E8433C`, `White FFFFFF`, `Muted CBB89F`, `PanelBg 241A12`, `PanelInner 3A2A1C`, `Outline 0E0905`. Police : `Title = LuckiestGuy`, `Body = FredokaOne`.
- **Chaînes affichées = ASCII pur** (pas d'accents bruts dans le texte transporté par le MCP ; les échappements `\u{...}` dans la source Luau sont OK car ASCII).
- **Aucune nouvelle RemoteEvent** : réutiliser l'event `boostsChanged` (wrapper `Net`).
- **Aucun changement de logique gameplay** (économie, catch, sell, grant). Seule modif serveur autorisée : exposer `duration` depuis `BoostService.getActive`.
- **Garantie anti-vide** : toute carte/badge doit rendre une icône correcte **immédiatement** avec le secours construit ; l'image IA ne fait que se substituer plus tard.
- **Vérifier chaque édition par relecture** (multi_edit peut no-op) ; **Play compile un snapshot** — relire avant de conclure.
- **Cibles d'icônes** (clés canoniques) : `cash`, `x2_cash`, `chance`, `yield`, `speed`, `double_boost`, `cache_rare`, `chest`, `prize_rain`, `egg`, `pet`.

---

## Task 1: Retirer la phrase d'onboarding

**Files:**
- Modify: `StarterPlayer.StarterPlayerScripts...OnboardingController` (fonction `nextHint`, branche `first_item_sold`). Dans `build.rbxlx` ~ ligne 857886-857887.

**Interfaces:**
- Consumes: rien.
- Produces: rien (suppression pure ; la chaîne `if/elseif` retombe sur la branche suivante).

- [ ] **Step 1 : Localiser la branche**

Via le MCP : `mcp__Roblox_Studio__script_grep` motif `Sell junk for Scrap` (ou `script_read` sur `OnboardingController`). Confirmer la présence exacte de :

```lua
	elseif not flags["first_item_sold"] and hasInventory then
		return "Open your Inventory and Sell junk for Scrap."
```

- [ ] **Step 2 : Supprimer les deux lignes**

`mcp__Roblox_Studio__multi_edit` sur `OnboardingController` — remplacer

```lua
	elseif not flags["first_item_caught"] then
		return "Your UFO is scanning the scrapyard… watch it grab some junk!"
	elseif not flags["first_item_sold"] and hasInventory then
		return "Open your Inventory and Sell junk for Scrap."
	elseif not flags["first_item_kept"] and hasInventory then
```

par

```lua
	elseif not flags["first_item_caught"] then
		return "Your UFO is scanning the scrapyard… watch it grab some junk!"
	elseif not flags["first_item_kept"] and hasInventory then
```

(Le flag `first_item_sold` reste utilisé ailleurs dans le funnel ; seul son hint disparaît.)

- [ ] **Step 3 : Relire pour confirmer l'édition**

`mcp__Roblox_Studio__script_grep` motif `Sell junk for Scrap` → **0 résultat**. `script_grep` motif `first_item_kept` → toujours présent (branche suivante intacte).

- [ ] **Step 4 : Booter et vérifier**

`start_stop_play` puis `get_console_output` : aucune erreur de compilation d'`OnboardingController`. Mode = Play confirmé.

- [ ] **Step 5 : Persister + commit**

Demander Ctrl+S dans Studio, puis :

```bash
git add build.rbxlx
git commit -m "fix(hud): retire le hint onboarding 'Sell junk for Scrap'"
```

---

## Task 2: Exposer `duration` depuis `BoostService.getActive` (serveur)

Permet aux badges du HUD d'afficher une barre de progression exacte. Restructure le stockage interne de `expiry:number` vers `{ exp:number, dur:number }` par kind.

**Files:**
- Modify (réécriture complète) : `ServerScriptService.Server.Services.BoostService` (copie texte : `docs/recovered-2026-06-19/BoostService.luau`).

**Interfaces:**
- Consumes: `Registry.get("DataService")` (`onReady`/`onRemoving`), `Net.sendEvent`.
- Produces: `BoostService.getActive(player) -> { { kind:string, remaining:number, duration:number }, ... }` (ajoute `duration`). Inchangés et toujours valides : `grant(player, kind, durationSec)`, `cashAdd`, `yieldAdd`, `speedFactor`, `luckAdd`, `push`. `boostsChanged` porte désormais `duration` par entrée (rétro-compatible : le client lisait `remaining`).

- [ ] **Step 1 : Remplacer la source de BoostService**

Via le MCP, écrire la Source de `BoostService` exactement :

```lua
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

-- active[player][kind] = { exp = os.clock_expiry, dur = duree_totale_sec }
local active: { [Player]: { [string]: { exp: number, dur: number } } } = {}

local function clk() return os.clock() end
local function isActive(player: Player, kind: string): boolean
	local a = active[player]
	return a ~= nil and a[kind] ~= nil and a[kind].exp > clk()
end

function BoostService.push(player: Player)
	Net.sendEvent(player, "boostsChanged", BoostService.getActive(player))
end

function BoostService.grant(player: Player, kind: string, durationSec: number)
	local a = active[player]
	if not a then a = {}; active[player] = a end
	local expiry = clk() + durationSec
	local cur = a[kind]
	if cur and cur.exp > expiry then
		-- ne raccourcit jamais : garde l'existant plus long (et sa duree)
	else
		a[kind] = { exp = expiry, dur = durationSec }
	end
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
		for kind, v in pairs(a) do
			if v.exp > t then
				out[#out + 1] = { kind = kind, remaining = math.floor(v.exp - t + 0.5), duration = v.dur }
			end
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
			for kind, v in pairs(a) do
				if v.exp <= t then a[kind] = nil; changed = true end
			end
			if changed then pcall(BoostService.push, player) end
		end
	end)
end

return BoostService
```

- [ ] **Step 2 : Relire pour confirmer**

`script_grep` sur `BoostService` motif `duration = v.dur` → présent. Motif `a%[kind%].exp` → présent (toutes les lectures pointent bien la nouvelle forme `.exp`). Aucune occurrence résiduelle de `a[kind] > clk()` (ancienne forme numérique).

- [ ] **Step 3 : Booter et vérifier**

`start_stop_play` + `get_console_output` : `BoostService` compile, boot propre (compteur de services inchangé, aucune erreur `attempt to index number`).

- [ ] **Step 4 : Vérifier la forme de getActive**

Via un Script serveur temporaire (ou `execute_luau` côté serveur) : appeler `Registry.get("BoostService").grant(plr, "cash", 30)` sur un joueur de test puis logger `getActive(plr)` ; attendu : une entrée `{ kind="cash", remaining≈30, duration=30 }`.

- [ ] **Step 5 : Persister + commit**

Ctrl+S, puis :

```bash
git add build.rbxlx docs/recovered-2026-06-19/BoostService.luau
git commit -m "feat(boost): expose duration dans getActive pour la barre de progression HUD"
```

(Mettre à jour la copie texte `docs/recovered-2026-06-19/BoostService.luau` avec la nouvelle source pour un diff lisible.)

---

## Task 3: Module partagé `RewardIcons` (source unique d'icônes)

**Files:**
- Create: `ReplicatedStorage.Shared.RewardIcons` (ModuleScript) + copie texte `docs/recovered-2026-06-19/RewardIcons.luau`.

**Interfaces:**
- Consumes: `ReplicatedStorage.UI.Theme`, `ReplicatedStorage.Shared.ScrapIcons` (lazy), meshes `ReplicatedStorage.Assets.EggMeshes` / `.PetMeshes`.
- Produces:
  - `RewardIcons.ASSETS : { [key:string]: number }` — asset-ids des images IA (0 = pas encore dispo).
  - `RewardIcons.emblem(holder: GuiObject, key: string, color: Color3)` — emblème construit seul (pas de plate, pas de viewport). **Utilisé par le HUD.**
  - `RewardIcons.build(holder: GuiObject, key: string, color: Color3)` — plate teintée + (image IA | ViewportFrame œuf/pet | emblème). **Utilisé par les cartes.**
  - `RewardIcons.viewportEgg(holder)` / `RewardIcons.viewportPet(holder)` — ViewportFrame d'un mesh représentatif.

- [ ] **Step 1 : Créer le ModuleScript et écrire la Source**

Via le MCP, créer un `ModuleScript` nommé `RewardIcons` sous `ReplicatedStorage.Shared` (p. ex. `execute_luau` : `local m=Instance.new("ModuleScript"); m.Name="RewardIcons"; m.Parent=game.ReplicatedStorage.Shared`), puis définir sa Source exactement :

```lua
-- RewardIcons.luau
-- Source unique d'icones de recompense (cartes CADEAUX + HUD boosts).
-- Resout par cle : (1) image IA uploadee si ASSETS[key]~=0, (2) ViewportFrame pour oeuf/pet,
-- (3) emblème construit. Garantit qu'aucune icone n'est jamais vide (moderation-safe).

local RS = game:GetService("ReplicatedStorage")
local Theme = require(RS.UI.Theme)
local P = Theme.Palette

local RewardIcons = {}

-- Asset-ids des images IA detourees (remplies apres upload+moderation, Task 6). 0 => fallback construit.
RewardIcons.ASSETS = {
	cash = 0, x2_cash = 0, chance = 0, yield = 0, speed = 0,
	double_boost = 0, cache_rare = 0, chest = 0, prize_rain = 0,
}

-- ---------- helpers construits ----------
local function plate(holder, color)
	local bg = Instance.new("Frame")
	bg.Size = UDim2.fromScale(1, 1); bg.BackgroundColor3 = Theme.darken(color, 0.5)
	bg.BorderSizePixel = 0; bg.ZIndex = 1; bg.Parent = holder
	Theme.Corner(bg, UDim.new(0, 10))
	Theme.Gradient(bg, { color, Theme.darken(color, 0.6) }, 90)
	local hi = Instance.new("Frame")  -- reflet superieur (look glossy)
	hi.Size = UDim2.new(1, -10, 0, 7); hi.Position = UDim2.fromOffset(5, 5)
	hi.BackgroundColor3 = P.White; hi.BackgroundTransparency = 0.72; hi.BorderSizePixel = 0
	hi.ZIndex = 2; hi.Parent = bg
	Theme.Corner(hi, UDim.new(0, 5))
	return bg
end

local function symbol(holder, text)
	local g = Instance.new("TextLabel")
	g.BackgroundTransparency = 1; g.Size = UDim2.fromScale(1, 1)
	g.Font = Theme.Font.Title; g.Text = text; g.TextColor3 = P.White; g.TextScaled = true
	g.ZIndex = 3; g.Parent = holder
	Theme.TextStroke(g, 2)
	local cc = Instance.new("UITextSizeConstraint"); cc.MaxTextSize = 40; cc.Parent = g
	return g
end

local function clover(holder, color)  -- trefle porte-bonheur (4 disques)
	for _, off in ipairs({ {0.5, 0.36}, {0.36, 0.52}, {0.64, 0.52}, {0.5, 0.66} }) do
		local d = Instance.new("Frame"); d.AnchorPoint = Vector2.new(0.5, 0.5)
		d.Position = UDim2.fromScale(off[1], off[2]); d.Size = UDim2.fromScale(0.36, 0.36)
		d.BackgroundColor3 = color; d.BorderSizePixel = 0; d.ZIndex = 3; d.Parent = holder
		Theme.Corner(d, UDim.new(1, 0)); Theme.Stroke(d, Theme.darken(color, 0.5), 2)
	end
end

local function scrap(holder, itemId, color)  -- vecteur ScrapIcons centre
	local h = Instance.new("Frame"); h.AnchorPoint = Vector2.new(0.5, 0.5)
	h.Position = UDim2.fromScale(0.5, 0.5); h.Size = UDim2.fromScale(0.72, 0.72)
	h.BackgroundTransparency = 1; h.ZIndex = 3; h.Parent = holder
	pcall(function() require(RS.Shared.ScrapIcons).build(h, itemId, color) end)
end

local function imageIcon(holder, assetId)
	local img = Instance.new("ImageLabel")
	img.Size = UDim2.fromScale(0.92, 0.92); img.AnchorPoint = Vector2.new(0.5, 0.5)
	img.Position = UDim2.fromScale(0.5, 0.5); img.BackgroundTransparency = 1
	img.Image = "rbxassetid://" .. tostring(assetId); img.ScaleType = Enum.ScaleType.Fit
	img.ZIndex = 3; img.Parent = holder
	return img
end

-- ---------- ViewportFrame (calque ClawPreview/makePetPreview) ----------
local function pickMesh(folderName)
	local assets = RS:FindFirstChild("Assets")
	local folder = assets and assets:FindFirstChild(folderName)
	if not folder then return nil end
	local models = {}
	for _, c in ipairs(folder:GetChildren()) do if c:IsA("Model") then models[#models + 1] = c end end
	if #models == 0 then return nil end
	table.sort(models, function(a, b) return a.Name < b.Name end)
	return models[math.clamp(math.ceil(#models / 2), 1, #models)]  -- un mesh "milieu de gamme"
end

local function viewport(holder, src)
	local vp = Instance.new("ViewportFrame")
	vp.Size = UDim2.fromScale(1, 1); vp.BackgroundTransparency = 1; vp.ZIndex = 3
	vp.Ambient = Color3.fromRGB(210, 210, 218); vp.LightColor = Color3.fromRGB(255, 255, 255)
	vp.LightDirection = Vector3.new(-0.4, -1, -0.6); vp.Parent = holder
	if not src then return vp end
	local clone = src:Clone()
	for _, p in ipairs(clone:GetDescendants()) do if p:IsA("BasePart") then p.Anchored = true end end
	clone:PivotTo(CFrame.new()); clone.Parent = vp
	local cf, size = clone:GetBoundingBox()
	local radius = size.Magnitude / 2
	local cam = Instance.new("Camera"); local dist = math.max(radius * 2.2, 5)
	cam.CFrame = CFrame.lookAt(cf.Position + Vector3.new(0.6, 0.4, 1).Unit * dist, cf.Position)
	cam.FieldOfView = 35; vp.CurrentCamera = cam; cam.Parent = vp
	return vp
end

local eggSrc, petSrc
function RewardIcons.viewportEgg(holder)
	if eggSrc == nil then eggSrc = pickMesh("EggMeshes") or false end
	return viewport(holder, eggSrc or nil)
end
function RewardIcons.viewportPet(holder)
	if petSrc == nil then petSrc = pickMesh("PetMeshes") or false end
	return viewport(holder, petSrc or nil)
end

-- ---------- API publique ----------
function RewardIcons.emblem(holder, key, color)
	if key == "cash" then symbol(holder, "$")
	elseif key == "x2_cash" then symbol(holder, "x2")
	elseif key == "yield" then symbol(holder, "+%")
	elseif key == "speed" then symbol(holder, ">>")
	elseif key == "double_boost" then symbol(holder, ">>")
	elseif key == "prize_rain" then symbol(holder, "$$$")
	elseif key == "chance" then clover(holder, color)
	elseif key == "cache_rare" then scrap(holder, "ufo_core", color)
	elseif key == "chest" then scrap(holder, "alien_alloy", color)
	elseif key == "egg" then symbol(holder, "O")
	elseif key == "pet" then symbol(holder, "<3")
	else symbol(holder, "$") end
end

function RewardIcons.build(holder, key, color)
	plate(holder, color)
	local asset = RewardIcons.ASSETS[key]
	if asset and asset ~= 0 then imageIcon(holder, asset)
	elseif key == "egg" then RewardIcons.viewportEgg(holder)
	elseif key == "pet" then RewardIcons.viewportPet(holder)
	else RewardIcons.emblem(holder, key, color) end
end

return RewardIcons
```

- [ ] **Step 2 : Relire pour confirmer**

`script_read` sur `ReplicatedStorage.Shared.RewardIcons` : la Source correspond, le module retourne `RewardIcons`. `inspect_instance` confirme qu'il existe bien comme ModuleScript sous `Shared`.

- [ ] **Step 3 : Test de fumée du module**

Via un LocalScript temporaire (ou la console client) :

```lua
local RewardIcons = require(game.ReplicatedStorage.Shared.RewardIcons)
local pg = game.Players.LocalPlayer.PlayerGui
local sg = Instance.new("ScreenGui"); sg.Name = "RI_TEST"; sg.Parent = pg
local function cell(i, key, color)
	local f = Instance.new("Frame"); f.Size = UDim2.fromOffset(80,80)
	f.Position = UDim2.fromOffset(10 + (i%8)*88, 10 + math.floor(i/8)*88)
	f.BackgroundColor3 = Color3.fromRGB(30,24,18); f.Parent = sg
	RewardIcons.build(f, key, color)
end
local keys = {"cash","x2_cash","chance","yield","speed","double_boost","cache_rare","chest","prize_rain","egg","pet"}
for i,k in ipairs(keys) do cell(i-1, k, Color3.fromRGB(120,200,90)) end
```

`screen_capture` : les 11 cellules montrent un emblème lisible chacune ; `egg` et `pet` montrent un **ViewportFrame 3D** (mesh visible, pas vide). Détruire `RI_TEST` ensuite.

- [ ] **Step 4 : Booter et vérifier**

`start_stop_play` + `get_console_output` : aucune erreur de require (`RS.UI.Theme`, `RS.Shared.ScrapIcons`, `Assets.EggMeshes/PetMeshes` résolus ou pcall-protégés).

- [ ] **Step 5 : Persister + commit**

Ctrl+S, puis :

```bash
git add build.rbxlx docs/recovered-2026-06-19/RewardIcons.luau
git commit -m "feat(ui): module RewardIcons (image IA / ViewportFrame oeuf-pet / emblème de secours)"
```

---

## Task 4: Cartes CADEAUX — icônes via `RewardIcons` + sheen premium

**Files:**
- Modify: `StarterPlayer.StarterPlayerScripts.Client.Controllers.PlaytimeRewardsController` (fonctions `buildIcon` et `buildCard` ; copie texte `docs/recovered-2026-06-19/PlaytimeRewardsController.luau`).

**Interfaces:**
- Consumes: `RewardIcons.build(holder, key, color)` (Task 3).
- Produces: cartes au visuel premium ; aucune signature publique modifiée (`Controller.open/close`, `Controller:Start` inchangés).

- [ ] **Step 1 : Importer RewardIcons et ajouter le résolveur de clé**

En tête de `PlaytimeRewardsController`, après `local ScrapIcons = require(RS.Shared.ScrapIcons)`, ajouter :

```lua
local RewardIcons = require(RS.Shared.RewardIcons)
```

Puis, juste avant `local function buildIcon(holder, t, color)`, ajouter le résolveur :

```lua
local function iconKeyFor(t)
	if t.type == "cash" then return "cash"
	elseif t.type == "prize_rain" then return "prize_rain"
	elseif t.type == "boost_double" then return "double_boost"
	elseif t.type == "boost" then
		return (t.icon == "boost_luck") and "chance" or "x2_cash"
	elseif t.type == "loot" then
		return (t.visual == "premium") and "chest" or "cache_rare"
	elseif t.type == "egg" then return "egg"
	elseif t.type == "pet_jackpot" then return "pet"
	end
	return "cash"
end
```

- [ ] **Step 2 : Remplacer le corps de `buildIcon` par une délégation à RewardIcons**

Remplacer toute la fonction `buildIcon` actuelle (le bloc qui crée `bg`, gère `t.type == "loot"` via ScrapIcons et sinon le glyphe texte `sym`) par :

```lua
local function buildIcon(holder, t, color)
	RewardIcons.build(holder, iconKeyFor(t), color)
end
```

- [ ] **Step 3 : Ajouter le sheen premium aux cartes premium**

Dans `buildCard(t)`, juste après la création de `stroke` (`local stroke = Theme.Stroke(root, color, ...)`), ajouter un reflet diagonal animé pour le tier premium :

```lua
	if t.visual == "premium" then
		local sheen = Instance.new("Frame")
		sheen.Name = "Sheen"; sheen.BackgroundColor3 = P.White; sheen.BackgroundTransparency = 1
		sheen.Size = UDim2.fromScale(1, 1); sheen.BorderSizePixel = 0; sheen.ZIndex = 6; sheen.Parent = root
		Theme.Corner(sheen, UDim.new(0, 14))
		local sg = Instance.new("UIGradient")
		sg.Color = ColorSequence.new(P.White)
		sg.Transparency = NumberSequence.new({
			NumberSequenceKeypoint.new(0, 1), NumberSequenceKeypoint.new(0.45, 1),
			NumberSequenceKeypoint.new(0.5, 0.78), NumberSequenceKeypoint.new(0.55, 1),
			NumberSequenceKeypoint.new(1, 1),
		})
		sg.Rotation = 25; sg.Offset = Vector2.new(-1, 0); sg.Parent = sheen
		task.spawn(function()
			while sheen.Parent do
				sg.Offset = Vector2.new(-1, 0)
				TweenService:Create(sg, TweenInfo.new(1.6, Enum.EasingStyle.Linear), { Offset = Vector2.new(1, 0) }):Play()
				task.wait(3.2)
			end
		end)
	end
```

(`TweenService` est déjà requis en tête du contrôleur ; `P` = `Theme.Palette` déjà aliasé.)

- [ ] **Step 4 : Relire pour confirmer**

`script_grep` sur `PlaytimeRewardsController` : motif `RewardIcons.build` → présent ; motif `iconKeyFor` → présent ; l'ancien glyphe `sym = "x2"` → **absent** (corps de buildIcon bien remplacé). `script_read` pour confirmer que `buildCard` contient le bloc `Sheen` sous le tier premium.

- [ ] **Step 5 : Booter et capturer le menu**

`start_stop_play`. En jeu, ouvrir le menu : cliquer le bouton `MainHUD.Sidebar.RewardsBtn` (« CADEAUX ») via `user_mouse_input`, **ou** forcer l'ouverture par LocalScript temporaire `require(...PlaytimeRewardsController).open()` après injection du schedule de test. `screen_capture` : les 12 cartes montrent les nouvelles icônes ; T8 = œuf 3D, T12 = pet 3D, premium = sheen visible, plates glossy. `get_console_output` : aucune erreur.

> Note env : `user_mouse_input` peut crasher en Play (cf. [[roblox-studio-mcp-gotchas]]) ; préférer l'ouverture par script de test pour la capture.

- [ ] **Step 6 : Persister + commit**

Ctrl+S, puis :

```bash
git add build.rbxlx docs/recovered-2026-06-19/PlaytimeRewardsController.luau
git commit -m "feat(rewards): cartes CADEAUX en icones premium (RewardIcons + ViewportFrame oeuf/pet + sheen premium)"
```

---

## Task 5: HUD des boosts actifs — pile de badges bas-droite (réécriture)

**Files:**
- Modify (réécriture complète) : `StarterPlayer.StarterPlayerScripts.Client.Controllers.BoostHUDController` (copie texte `docs/recovered-2026-06-19/BoostHUDController.luau`).

**Interfaces:**
- Consumes: event `boostsChanged` → liste `{ kind, remaining, duration }` (Task 2) ; `RewardIcons.emblem` (Task 3) ; `Theme`.
- Produces: `Controller:Start()` (auto-booté par le bootstrap des contrôleurs, inchangé côté boot).

- [ ] **Step 1 : Remplacer la source de BoostHUDController**

Écrire la Source de `BoostHUDController` exactement :

```lua
-- BoostHUDController.luau
-- HUD des boosts actifs : pile verticale de badges (icone + barre + timer dessous), BAS A DROITE.
-- Hierarchie par taille/glow (cash = majeur). Pilote par l'event boostsChanged.

local Players = game:GetService("Players")
local RunService = game:GetService("RunService")
local TweenService = game:GetService("TweenService")
local UserInputService = game:GetService("UserInputService")
local RS = game:GetService("ReplicatedStorage")
local Theme = require(RS.UI.Theme)
local P = Theme.Palette
local Net = require(RS.Shared.Net.Net)
local RewardIcons = require(RS.Shared.RewardIcons)

local player = Players.LocalPlayer
local Controller = {}

local KIND = {
	cash  = { label = "x2 Cash",   color = P.Gold,   iconKey = "x2_cash", major = true },
	luck  = { label = "Chance",    color = P.Purple, iconKey = "chance",  major = false },
	yield = { label = "Rendement", color = P.Gold,   iconKey = "yield",   major = false },
	speed = { label = "Vitesse",   color = P.Cyan,   iconKey = "speed",   major = false },
}
local ORDER = { cash = 1, yield = 2, speed = 3, luck = 4 }
local SIZE_MAJOR, SIZE_STD = 78, 60

local container = nil
local badges = {}   -- kind -> rec
local expAt = {}    -- kind -> os.clock expiry
local durOf = {}    -- kind -> duration (sec)

local function ensureContainer()
	if container then return end
	local pg = player:FindFirstChildOfClass("PlayerGui"); if not pg then return end
	local g = Instance.new("ScreenGui")
	g.Name = "BoostHUD"; g.ResetOnSpawn = false; g.IgnoreGuiInset = true
	g.ZIndexBehavior = Enum.ZIndexBehavior.Sibling; g.DisplayOrder = 20; g.Parent = pg
	local f = Instance.new("Frame")
	f.Name = "Stack"; f.AnchorPoint = Vector2.new(1, 1)
	local bottomInset = UserInputService.TouchEnabled and 150 or 16  -- evite le bouton saut mobile
	f.Position = UDim2.new(1, -16, 1, -bottomInset)
	f.Size = UDim2.fromOffset(SIZE_MAJOR + 12, 10); f.AutomaticSize = Enum.AutomaticSize.Y
	f.BackgroundTransparency = 1; f.Parent = g
	local list = Instance.new("UIListLayout")
	list.FillDirection = Enum.FillDirection.Vertical
	list.VerticalAlignment = Enum.VerticalAlignment.Bottom
	list.HorizontalAlignment = Enum.HorizontalAlignment.Right
	list.Padding = UDim.new(0, 10); list.SortOrder = Enum.SortOrder.LayoutOrder; list.Parent = f
	container = f
end

local function makeBadge(kind)
	local meta = KIND[kind] or { label = kind, color = P.Cyan, iconKey = "cash", major = false }
	local sz = meta.major and SIZE_MAJOR or SIZE_STD

	local entry = Instance.new("Frame")
	entry.Name = kind; entry.BackgroundTransparency = 1
	entry.Size = UDim2.fromOffset(SIZE_MAJOR + 12, sz + 22)
	entry.LayoutOrder = ORDER[kind] or 9
	local col = Instance.new("UIListLayout")
	col.FillDirection = Enum.FillDirection.Vertical; col.HorizontalAlignment = Enum.HorizontalAlignment.Center
	col.VerticalAlignment = Enum.VerticalAlignment.Bottom
	col.Padding = UDim.new(0, 2); col.SortOrder = Enum.SortOrder.LayoutOrder; col.Parent = entry

	-- conteneur badge+halo (centre le halo qui deborde)
	local box = Instance.new("Frame")
	box.Name = "Box"; box.LayoutOrder = 1; box.BackgroundTransparency = 1; box.Size = UDim2.fromOffset(sz, sz)
	box.Parent = entry

	local halo = Instance.new("Frame")
	halo.AnchorPoint = Vector2.new(0.5, 0.5); halo.Position = UDim2.fromScale(0.5, 0.5)
	halo.Size = UDim2.fromOffset(sz + 14, sz + 14); halo.BackgroundColor3 = meta.color
	halo.BackgroundTransparency = meta.major and 0.5 or 0.76; halo.BorderSizePixel = 0; halo.ZIndex = 0
	halo.Parent = box
	Theme.Corner(halo, UDim.new(0, 18))

	local badge = Instance.new("Frame")
	badge.AnchorPoint = Vector2.new(0.5, 0.5); badge.Position = UDim2.fromScale(0.5, 0.5)
	badge.Size = UDim2.fromOffset(sz, sz); badge.BackgroundColor3 = P.PanelInner; badge.BorderSizePixel = 0
	badge.ZIndex = 1; badge.Parent = box
	Theme.Corner(badge, UDim.new(0, 14))
	Theme.Gradient(badge, { Theme.darken(meta.color, 0.15), Theme.darken(meta.color, 0.55) }, 90)
	Theme.Stroke(badge, meta.color, meta.major and 3 or 2)

	local iconHolder = Instance.new("Frame")
	iconHolder.AnchorPoint = Vector2.new(0.5, 0.5); iconHolder.Position = UDim2.fromScale(0.5, 0.42)
	iconHolder.Size = UDim2.fromScale(0.7, 0.6); iconHolder.BackgroundTransparency = 1; iconHolder.ZIndex = 2
	iconHolder.Parent = badge
	RewardIcons.emblem(iconHolder, meta.iconKey, meta.color)  -- emblème construit net en petit

	local barBg = Instance.new("Frame")
	barBg.AnchorPoint = Vector2.new(0.5, 1); barBg.Position = UDim2.new(0.5, 0, 1, -6)
	barBg.Size = UDim2.new(1, -12, 0, 6); barBg.BackgroundColor3 = Theme.darken(meta.color, 0.7)
	barBg.BorderSizePixel = 0; barBg.ZIndex = 3; barBg.Parent = badge
	Theme.Corner(barBg, UDim.new(1, 0))
	local barFill = Instance.new("Frame")
	barFill.Size = UDim2.fromScale(1, 1); barFill.BackgroundColor3 = meta.color
	barFill.BorderSizePixel = 0; barFill.ZIndex = 4; barFill.Parent = barBg
	Theme.Corner(barFill, UDim.new(1, 0))

	local timer = Instance.new("TextLabel")
	timer.LayoutOrder = 2; timer.BackgroundTransparency = 1; timer.Size = UDim2.fromOffset(sz, 18)
	timer.Font = Theme.Font.Title; timer.Text = "00:00"; timer.TextColor3 = P.White; timer.TextScaled = true
	timer.Parent = entry; Theme.TextStroke(timer, 2)
	local tcc = Instance.new("UITextSizeConstraint"); tcc.MaxTextSize = 16; tcc.Parent = timer

	local us = Instance.new("UIScale"); us.Scale = 0; us.Parent = entry  -- pop-in
	TweenService:Create(us, TweenInfo.new(0.22, Enum.EasingStyle.Back, Enum.EasingDirection.Out), { Scale = 1 }):Play()

	entry.Parent = container
	return { entry = entry, badge = badge, halo = halo, barFill = barFill, timer = timer,
		color = meta.color, baseBadge = Theme.darken(meta.color, 0.15), scale = us, major = meta.major }
end

local function removeBadge(kind)
	local rec = badges[kind]; if not rec then return end
	badges[kind] = nil; expAt[kind] = nil; durOf[kind] = nil
	local tw = TweenService:Create(rec.scale, TweenInfo.new(0.18), { Scale = 0 })
	tw:Play(); tw.Completed:Once(function() if rec.entry then rec.entry:Destroy() end end)
end

function Controller:Start()
	Net.onEvent("boostsChanged", function(list)
		ensureContainer(); if not container then return end
		local seen = {}
		for _, b in ipairs(list or {}) do
			seen[b.kind] = true
			expAt[b.kind] = os.clock() + (b.remaining or 0)
			durOf[b.kind] = math.max(1, b.duration or b.remaining or 1)
			if not badges[b.kind] then badges[b.kind] = makeBadge(b.kind) end
		end
		for kind in pairs(badges) do
			if not seen[kind] then removeBadge(kind) end
		end
	end)

	RunService.Heartbeat:Connect(function()
		local now = os.clock()
		for kind, rec in pairs(badges) do
			local remain = math.max(0, (expAt[kind] or 0) - now)
			local total = durOf[kind] or 1
			rec.barFill.Size = UDim2.fromScale(math.clamp(remain / total, 0, 1), 1)
			local r = math.floor(remain + 0.5)
			rec.timer.Text = string.format("%02d:%02d", math.floor(r / 60), r % 60)
			if remain <= 10 and remain > 0 then  -- urgence : pulse
				local a = 0.5 + 0.5 * math.abs(math.sin(now * 4))
				rec.halo.BackgroundTransparency = (rec.major and 0.5 or 0.76) - 0.3 * a
				rec.badge.BackgroundColor3 = rec.baseBadge:Lerp(P.White, a * 0.25)
			elseif rec.badge.BackgroundColor3 ~= rec.baseBadge then
				rec.badge.BackgroundColor3 = rec.baseBadge
			end
			if remain <= 0 then removeBadge(kind) end
		end
	end)
end

return Controller
```

- [ ] **Step 2 : Relire pour confirmer**

`script_grep` sur `BoostHUDController` : motif `AnchorPoint = Vector2.new(1, 1)` → présent (bas-droite) ; motif `RewardIcons.emblem` → présent ; motif `b.duration` → présent ; ancien motif `Theme.Pill` → **absent** (réécriture effective). `script_grep` motif `VerticalAlignment = Enum.VerticalAlignment.Bottom` → présent.

- [ ] **Step 3 : Booter et tester le rendu avec des boosts simulés**

`start_stop_play`. Injecter un test client (LocalScript temporaire) qui simule l'event sans toucher au serveur :

```lua
local Net = require(game.ReplicatedStorage.Shared.Net.Net)
-- selon l'API Net locale ; sinon appeler directement le handler via un BindableEvent de test.
-- Cible attendue par le controleur : liste d'entrees {kind, remaining, duration}
local fake = {
	{ kind = "cash",  remaining = 300, duration = 300 },
	{ kind = "speed", remaining = 18,  duration = 480 },
	{ kind = "luck",  remaining = 9,   duration = 480 },
}
Net.fireEvent and Net.fireEvent("boostsChanged", fake)  -- adapter au shim Net local de simulation
```

> Si `Net.onEvent` ne peut être déclenché localement, valider plutôt en jeu réel : réclamer le palier T2 (boost cash) dans CADEAUX après 3 min de session, ou via l'outil admin si dispo. La vérif clé : les badges apparaissent **en bas à droite**, empilés, `cash` plus grand + halo plus fort, barre qui se vide, timer dessous, pulse < 10 s sur `luck`.

`screen_capture` : confirmer placement bas-droite, hiérarchie de taille, barres + timers. `get_console_output` : aucune erreur.

- [ ] **Step 4 : Vérifier l'inset mobile (lecture de code)**

Confirmer par relecture que `bottomInset = UserInputService.TouchEnabled and 150 or 16` (la pile remonte au-dessus du bouton saut sur mobile). Pas de test device requis.

- [ ] **Step 5 : Persister + commit**

Ctrl+S, puis :

```bash
git add build.rbxlx docs/recovered-2026-06-19/BoostHUDController.luau
git commit -m "feat(hud): boosts actifs en pile de badges bas-droite (icone + barre + timer, hierarchie cash)"
```

---

## Task 6: Génération Higgsfield + upload + câblage des asset-ids

Remplit `RewardIcons.ASSETS` avec les vraies images IA. Le secours construit reste actif tant qu'un asset vaut `0` → aucune régression si une icône échoue ou attend la modération.

**Files:**
- Modify: `ReplicatedStorage.Shared.RewardIcons` (table `ASSETS` uniquement) + copie texte.
- Create (hors-jeu): `assets/reward-icons/<key>.png` (sources générées, pour archive/retouche).

**Interfaces:**
- Consumes: CLI Higgsfield (génération) ; `mcp__Roblox_Studio__upload_image` (upload → assetId).
- Produces: `RewardIcons.ASSETS[key] = <assetId>` pour chaque icône validée.

- [ ] **Step 1 : Setup Higgsfield (HUMAIN, interactif)**

Demander à l'utilisateur d'exécuter dans le terminal de session :

```
! npm install -g @higgsfield/cli
! higgsfield auth login
! npx skills add higgsfield-ai/skills
```

Confirmer l'auth : `! higgsfield whoami` (ou `higgsfield --help` pour repérer la sous-commande de génération exacte du skill installé). **Repérer aussi la liste des modèles** (`higgsfield models` / `--help`) pour identifier le **moins cher**.

- [ ] **Step 2 : Générer le set d'icônes**

**Modèle : utiliser le modèle / tier le MOINS CHER proposé par Higgsfield** (préférence utilisateur explicite — une icône simple centrée n'exige pas le modèle premium ; on monte en gamme uniquement si une clé refuse obstinément le style au Step 3). Passer le flag de modèle éco repéré au Step 1 à chaque appel.

Pour chaque clé, lancer la génération (sous-commande confirmée au Step 1) avec un prompt commun + sujet, fond **plat neutre** (détourage facile), objet **centré** :

> Base : *« glossy stylized 3D game reward icon, chunky cartoon, soft rim light, glossy highlights, thick dark outline, vivid saturated colors, single centered object, flat neutral background, mobile gacha UI, high contrast »* + sujet :

| key | sujet |
|-----|-------|
| `cash` | green cash stack / money bag |
| `x2_cash` | golden "x2" multiplier coin token |
| `chance` | lucky four-leaf clover / horseshoe charm |
| `yield` | upward green arrow / output boost |
| `speed` | yellow lightning bolt |
| `double_boost` | upward arrow combined with a lightning bolt |
| `cache_rare` | rugged metal scrap crate, purple rarity glow |
| `chest` | premium golden treasure chest overflowing |
| `prize_rain` | burst of falling gold coins |

Sauver chaque rendu retenu en `assets/reward-icons/<key>.png`. (`egg`/`pet` ne sont **pas** générés — ViewportFrame.)

- [ ] **Step 3 : Curation stricte**

Pour chaque clé, ne garder qu'**un** rendu on-style (glossy 3D, silhouette claire, lisible réduit à ~64px). Rejeter réaliste/cheap/bruité/hors-thème. Si aucune variante n'est bonne → laisser `ASSETS[key] = 0` (le secours construit reste) et le noter.

- [ ] **Step 4 : Détourage (fond transparent)**

Retirer le fond plat → PNG transparent à silhouette nette. (Si l'outil de génération propose un export cutout/transparent, l'utiliser ; sinon détourage par suppression de fond uni.)

- [ ] **Step 5 : Upload Roblox**

Pour chaque PNG retenu : `mcp__Roblox_Studio__upload_image` → récupérer l'`assetId`. Noter le mapping `key -> assetId`.

- [ ] **Step 6 : Câbler les asset-ids dans RewardIcons.ASSETS**

Éditer la table `RewardIcons.ASSETS` (Task 3) en remplaçant les `0` par les assetIds obtenus, p. ex. :

```lua
RewardIcons.ASSETS = {
	cash = 0, x2_cash = 0, chance = 0, yield = 0, speed = 0,
	double_boost = 0, cache_rare = 0, chest = 0, prize_rain = 0,
}
```

→ remplacer chaque `0` câblé par son `<assetId>` (laisser à `0` toute icône non validée/non modérée).

- [ ] **Step 7 : Vérifier le rendu (après modération)**

`start_stop_play`, ouvrir CADEAUX, `screen_capture` : les cartes dont l'asset est câblé montrent l'image IA ; les autres gardent le secours. Si une image apparaît grise/manquante → modération non terminée : re-tester plus tard ; le secours couvre l'attente. `get_console_output` : aucune erreur d'`Image`.

- [ ] **Step 8 : Persister + commit**

Ctrl+S, puis :

```bash
git add build.rbxlx docs/recovered-2026-06-19/RewardIcons.luau assets/reward-icons
git commit -m "feat(rewards): images IA Higgsfield cablees dans RewardIcons.ASSETS (secours construit conserve)"
```

> Risques acceptés (cf. spec §10) : délai de modération Roblox (secours couvre) ; sous-commande CLI Higgsfield à confirmer au Step 1 ; toute icône non validée reste sur secours construit.

---

## Task 7: QA d'intégration finale

**Files:**
- Aucune modif de code ; vérification d'ensemble + commit de clôture si besoin.

**Interfaces:**
- Consumes: tout ce qui précède.
- Produces: validation des critères d'acceptation de la spec.

- [ ] **Step 1 : Boot propre**

`start_stop_play` + `get_console_output` : zéro erreur ; les contrôleurs `PlaytimeRewardsController` et `BoostHUDController` et le service `BoostService` démarrent ; compteurs services/contrôleurs cohérents avec l'avant-chantier.

- [ ] **Step 2 : Menu CADEAUX**

Ouvrir CADEAUX, `screen_capture` : 12 cartes avec icônes premium (T8 œuf 3D, T12 pet 3D, premium = sheen + glow or), états corrects (verrouillé/prêt/réclamé), aucune carte vide. Cohérence `Theme` avec les autres menus.

- [ ] **Step 3 : HUD boosts**

Avec ≥1 boost actif (claim réel d'un palier boost ou simulation Step 5 de la Task 5), `screen_capture` : badges **bas-droite**, empilés, `cash` majeur, barre + timer dessous, pulse < 10 s. Aucun chevauchement avec le reste du HUD.

- [ ] **Step 4 : Phrase**

Confirmer (jeu réel, joueur neuf, ou lecture) que le hint « Open your Inventory and Sell junk for Scrap. » n'apparaît **plus** et que les autres hints s'enchaînent normalement.

- [ ] **Step 5 : Commit de clôture (si Ctrl+S en attente)**

```bash
git add build.rbxlx
git commit -m "chore(rewards): QA finale visuels recompenses + HUD boosts"
```

---

## Couverture spec (auto-revue)

- Spec §4 (cartes icônes premium) → Tasks 3, 4, 6. ✔
- Spec §5 (HUD bas-droite badges + hiérarchie + timer dessous + barre + anims + inset mobile) → Tasks 2, 5. ✔
- Spec §6 (`duration` via getActive pour barre exacte) → Task 2. ✔
- Spec §7 (pipeline Higgsfield → curation → détourage → upload → swap, secours, modération) → Tasks 3, 6. ✔
- Spec §8 (module `RewardIcons` source unique, ViewportFrame œuf/pet, Theme/ScrapIcons réutilisés) → Task 3. ✔
- Spec §9 (retrait phrase, fall-through propre) → Task 1. ✔
- Spec §11 critères d'acceptation 1-7 → Task 7 (QA). ✔
- ViewportFrame œuf/pet (vrais meshes, pas d'IA) → Task 3 (`viewportEgg`/`viewportPet`). ✔
- Garantie anti-vide (secours construit immédiat) → Task 3 (`emblem`/`build`), maintenue Task 6. ✔
