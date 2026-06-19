# Système de Pets — Phase 1 : Modèle de données + bonus passifs — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Poser le **cœur données** des pets (10 pets / 5 raretés) et brancher leurs **bonus passifs « stat de capture »** sur la boucle de production, exactement comme les Amélios — sans shop, sans errance, sans UI (phases suivantes).

**Architecture :** Deux nouveaux **configs purs** (`PetRarities`, `Pets`) : `Pets` porte les 10 défs **et** l'agrégation pure des bonus des pets équipés (`applyPetStats(block, data)`, `sellBonus(data)`, `bonusValue(data, kind)`) — même pattern que `Upgrades.applyAccountStats` (lisible, testable, sans dépendance service). Un nouveau service **`PetService`** porte les **mutations** (octroi, équip/déséquip, fusion, vente, achat de slot) + les remotes `Net`. `CatchService.effectiveStats` ajoute une ligne `Pets.applyPetStats(block, data)` ; `InventoryService.sellStack` ajoute `+ Pets.sellBonus(d)`. Les pets sont stockés dans `data.pets` (clé uid → `{defId, level, locked}`), équipés via `data.equippedPets` (liste d'uid ≤ `data.petSlots`).

**Tech Stack :** Roblox Luau · ModuleScripts dans `ReplicatedStorage.Shared` · services serveur auto-chargés (`ServerScriptService.Server.Services`) · édition + test via le MCP Roblox Studio.

**Spec :** `docs/superpowers/specs/2026-06-17-pet-system-design.md` (§A, §B partiel, §E, §F, §G phase 1).

---

## Notes d'environnement (lire avant de commencer)

- **Pas de framework de test ni de git.** Deux façons de tester selon la nature du code :
  - **Helpers PURS** (`Pets.applyPetStats`/`sellBonus`/`sellValue`) → snippet `execute_luau` en **Edit** qui `require(module:Clone())` et `assert`. **Toujours** cloner : en Edit, `require` met en cache la 1ʳᵉ version (memory `roblox-studio-mcp-gotchas`). Les modules requièrent leurs dépendances en **chemin absolu** (`game:GetService("ReplicatedStorage")…`) → le clone résout bien (pas de `script.Parent`).
  - **Mutations `PetService` / intégration live** (besoin du Registry peuplé) → **⚠️ CORRIGÉ EN COURS D'EXÉCUTION : `execute_luau(datamodel_type="Server")` tourne dans une VM ISOLÉE dont le `Registry` est VIDE** — il ne voit PAS les services du vrai serveur. Pour exécuter dans la **vraie** VM serveur : créer un `Script` temporaire sous `ServerScriptService` (il démarre au lancement du Play) qui fait le test, `print("TAG: ...")` le résultat (lu via `get_console_output`), **puis le supprimer** (`execute_luau` Edit : `game.ServerScriptService:FindFirstChild("...")::Destroy()`). Un joueur solo est présent automatiquement en Play. (Les fonctions PURES de `Config.Pets` restent testables directement en Edit via `:Clone()`.)
- **Mode Studio :** `get_studio_state`. Édition des modules en **Edit**. Tests purs en **Edit**. Test `PetService` en **Play** (Server). Si l'état n'est pas le bon, `start_stop_play`. ⚠️ Studio peut repasser en Play tout seul — re-vérifier l'état avant chaque édition serveur.
- **Édition :** modules existants → `multi_edit` (diff ciblé). **Après CHAQUE édition, relire (`script_read`) pour confirmer** (`multi_edit` peut silencieusement no-op, memory). Nouveaux modules → `multi_edit` avec `className="ModuleScript"` et premier edit `old_string=""` (crée à `file_path`).
- **Persistance :** les éditions vivent dans le DataModel Edit ; écrites dans `build.rbxlx` seulement au **Ctrl+S** de l'utilisateur. Chaque checkpoint = un point où prévenir l'utilisateur qu'il peut sauvegarder.

---

## File Structure

| Fichier (chemin DataModel) | Rôle | Action |
|---|---|---|
| `ReplicatedStorage.Shared.Types` | types `PetRarityDef`/`PetDef`/`OwnedPet` + champs `PlayerData` | Modifier |
| `ReplicatedStorage.Shared.Config.PetRarities` | échelle de rareté des pets (5) | **Créer** |
| `ReplicatedStorage.Shared.Config.Pets` | 10 défs + agrégation pure des bonus | **Créer** |
| `ReplicatedStorage.Shared.Config.GameConfig` | `PROFILE_TEMPLATE` (+ pets/equippedPets/petSlots) | Modifier (ligne 51) |
| `ServerScriptService.Server.Services.PetService` | mutations (grant/équip/fusion/vente/slot) + remotes | **Créer** |
| `ServerScriptService.Server.Services.CatchService` | `effectiveStats` → `Pets.applyPetStats` | Modifier (require + ligne 52) |
| `ServerScriptService.Server.Services.InventoryService` | `sellStack` → `+ Pets.sellBonus` | Modifier (require + ligne 68) |
| `ServerScriptService.AdminService` | commandes test `givePet`/`allPets` | Modifier |

Hors-périmètre Phase 1 (→ phases suivantes, cf. Roadmap) : passifs `crit`/`yield`/`magnet`/`offline` (consommés ailleurs), capacités **actives**, config `Eggs` + shop, errance, UI, assets Blender. Les défs de pets portent déjà `active` (inerte en Phase 1).

---

## Task 1 : Types des pets

**Files:**
- Modify: `ReplicatedStorage.Shared.Types` (après `UpgradeDef`, et champs `PlayerData`)

- [ ] **Step 1 : Ajouter les types pets** (`multi_edit` sur `ReplicatedStorage.Shared.Types`, `datamodel_type="Edit"`)

Edit 1 — insérer les nouveaux types avant le commentaire `-- ProfileStore-backed player data shape`. Remplacer exactement :
```luau
-- ProfileStore-backed player data shape (see GameConfig.PROFILE_TEMPLATE).
export type PlotSlotData = { unlocked: boolean, ufoUid: string? }
```
par :
```luau
-- Pets (compagnons d'usine, voir Config.PetRarities / Config.Pets).
export type PetRarityDef = {
	id: string,
	name: string,
	color: { number }, -- {r,g,b} 0..1
	order: number, -- 1 = plus commun
	sellBase: number, -- valeur de revente d'un pet niv 1 de ce palier
}

export type PetPassive = { kind: string, value: number } -- kind = vocabulaire effectKind ; value = magnitude niv 1
export type PetActive = { kind: string, baseCooldown: number, params: { [string]: number }? } -- capacité active (Phase 2)

export type PetDef = {
	id: string,
	name: string,
	rarity: string, -- id PetRarityDef
	icon: string,
	model: string, -- clé dans ReplicatedStorage.Assets.PetMeshes (placeholder tant que le mesh Blender n'est pas uploadé)
	passive: { PetPassive },
	active: PetActive?,
}

export type OwnedPet = { defId: string, level: number, locked: boolean }

-- ProfileStore-backed player data shape (see GameConfig.PROFILE_TEMPLATE).
export type PlotSlotData = { unlocked: boolean, ufoUid: string? }
```

Edit 2 — ajouter les champs pets à `PlayerData`. Remplacer exactement :
```luau
	upgrades: { [string]: number },
	shop: { [string]: number },
	stats: { [string]: number },
}
```
par :
```luau
	upgrades: { [string]: number },
	shop: { [string]: number },
	stats: { [string]: number },
	pets: { [string]: OwnedPet }, -- [uid] = pet possédé
	equippedPets: { string }, -- liste d'uid équipés (≤ petSlots)
	petSlots: number, -- slots de pets équipés (3 → 6)
}
```

- [ ] **Step 2 : Relire pour confirmer**

`script_read` `ReplicatedStorage.Shared.Types` (lignes ~106-145). Vérifier que `PetRarityDef`, `PetPassive`, `PetActive`, `PetDef`, `OwnedPet` existent et que `PlayerData` porte `pets`/`equippedPets`/`petSlots`. (Types effacés au runtime : validation réelle via les tests des tasks suivantes.)

---

## Task 2 : Config `PetRarities`

**Files:**
- Create: `ReplicatedStorage.Shared.Config.PetRarities`
- Test: snippet `execute_luau` (Edit)

- [ ] **Step 1 : Écrire le test (qui doit échouer)**

`execute_luau` (`datamodel_type="Edit"`) :
```luau
local node = game.ReplicatedStorage.Shared.Config:FindFirstChild("PetRarities")
if not node then return "FAIL: PetRarities module manquant" end
local R = require(node:Clone())
local errs = {}
local function ck(c,m) if not c then table.insert(errs,m) end end
ck(#R.list == 5, "attendu 5 raretés, eu "..tostring(#R.list))
ck(R.get("commun") ~= nil and R.get("legendaire") ~= nil, "ids commun/legendaire manquants")
ck(R.get("rare").sellBase == 60000, "rare.sellBase != 60000")
ck(R.get("legendaire").order == 5, "legendaire.order != 5")
if #errs>0 then return "FAIL:\n"..table.concat(errs,"\n") end
return "PASS: PetRarities (5 paliers, sellBase, order)"
```

- [ ] **Step 2 : Lancer → attendu FAIL** (`PetRarities module manquant`).

- [ ] **Step 3 : Créer le module** (`multi_edit`, `file_path="ReplicatedStorage.Shared.Config.PetRarities"`, `className="ModuleScript"`, `datamodel_type="Edit"`, premier edit `old_string=""` avec ce `new_string`) :
```luau
--!strict
-- PetRarities.luau
-- Échelle de rareté des pets (5 paliers). sellBase = valeur de revente d'un pet niv 1 de ce palier.
local Types = require(game:GetService("ReplicatedStorage").Shared.Types)

local PetRarities: { Types.PetRarityDef } = {
	{ id = "commun",     name = "Commun",     color = { 0.78, 0.78, 0.80 }, order = 1, sellBase = 1000 },
	{ id = "peu_commun", name = "Peu commun", color = { 0.40, 0.85, 0.45 }, order = 2, sellBase = 8000 },
	{ id = "rare",       name = "Rare",       color = { 0.30, 0.60, 1.00 }, order = 3, sellBase = 60000 },
	{ id = "epique",     name = "Épique",     color = { 0.70, 0.35, 1.00 }, order = 4, sellBase = 500000 },
	{ id = "legendaire", name = "Légendaire", color = { 1.00, 0.70, 0.15 }, order = 5, sellBase = 5000000 },
}

local byId: { [string]: Types.PetRarityDef } = {}
for _, r in ipairs(PetRarities) do
	byId[r.id] = r
end

return {
	list = PetRarities,
	byId = byId,
	get = function(id: string): Types.PetRarityDef?
		return byId[id]
	end,
}
```

- [ ] **Step 4 : Relire** `script_read` `ReplicatedStorage.Shared.Config.PetRarities` (entier) — 1ʳᵉ ligne `--!strict`, 5 entrées.

- [ ] **Step 5 : Relancer le test → attendu PASS.**

---

## Task 3 : Config `Pets` (défs + agrégation pure)

**Files:**
- Create: `ReplicatedStorage.Shared.Config.Pets`
- Test: snippet `execute_luau` (Edit)

- [ ] **Step 1 : Écrire le test (qui doit échouer)**

`execute_luau` (`datamodel_type="Edit"`) :
```luau
local node = game.ReplicatedStorage.Shared.Config:FindFirstChild("Pets")
if not node then return "FAIL: Pets module manquant" end
local P = require(node:Clone())
local errs = {}
local function ck(c,m) if not c then table.insert(errs,m) end end
local function near(a,b) return math.abs(a-b) < 1e-6 end

ck(#P.list == 10, "attendu 10 pets, eu "..tostring(#P.list))
ck(P.MAX_LEVEL == 10, "MAX_LEVEL != 10")
for _,id in ipairs({"bunny_plush","bolt_bot","foam_cube","windup_duck","neon_kitten","magnet_drone","golden_teddy","mini_clawbot","holo_fox","ufo_mascot"}) do
	ck(P.get(id) ~= nil, "def manquante: "..id)
end

-- Données de test : a/b/c équipés ; d (ufo) NON équipé -> ne doit RIEN apporter.
local data = {
	pets = {
		a = { defId = "foam_cube",   level = 1, locked = false }, -- luckAdd 0.10 -> 0.10
		b = { defId = "bunny_plush", level = 3, locked = false }, -- speedMult 0.02*(1+0.15*2)=0.026
		c = { defId = "golden_teddy",level = 2, locked = false }, -- sellMult 0.06*(1.15)=0.069
		d = { defId = "ufo_mascot",  level = 1, locked = false }, -- non équipé
	},
	equippedPets = { "a", "b", "c" },
}

local block = { luck = 1, grabSpeed = 2, qualityBias = 0, modifierChance = 0, weightCap = 10, multiGrab = 0 }
P.applyPetStats(block, data)
ck(near(block.luck, 1.10), "luck attendu 1.10, eu "..block.luck)
ck(near(block.grabSpeed, 1.948), "grabSpeed attendu 1.948, eu "..block.grabSpeed)
ck(near(block.weightCap, 10), "weightCap ne doit pas bouger")
ck(near(block.multiGrab, 0), "multiGrab ne doit pas bouger")

-- sellBonus = seulement le teddy équipé (0.069) ; PAS l'ufo non équipé (0.05).
ck(near(P.sellBonus(data), 0.069), "sellBonus attendu 0.069, eu "..P.sellBonus(data))
-- bonusValue générique
ck(near(P.bonusValue(data, "luckAdd"), 0.10), "bonusValue luckAdd attendu 0.10")
ck(near(P.bonusValue(data, "crit"), 0), "bonusValue crit attendu 0 (pas de fox équipé)")

-- sellValue : commun L1=1000 ; rare L2=floor(60000*1.5)=90000 ; legendaire L1=5000000
ck(P.sellValue(P.get("foam_cube"), 1) == 1000, "sellValue foam_cube L1 != 1000")
ck(P.sellValue(P.get("golden_teddy"), 2) == 90000, "sellValue golden_teddy L2 != 90000")
ck(P.sellValue(P.get("ufo_mascot"), 1) == 5000000, "sellValue ufo L1 != 5000000")

-- cooldownAt : teddy 180*(1-0.03)=174.6 ; pet sans active -> huge
ck(near(P.cooldownAt(P.get("golden_teddy"), 2), 174.6), "cooldown teddy L2 != 174.6")
ck(P.cooldownAt(P.get("foam_cube"), 1) == math.huge, "cooldown pet sans active != huge")

if #errs>0 then return "FAIL:\n"..table.concat(errs,"\n") end
return "PASS: Pets (10 défs, applyPetStats, sellBonus équipés-seuls, bonusValue, sellValue, cooldown)"
```

- [ ] **Step 2 : Lancer → attendu FAIL** (`Pets module manquant`).

- [ ] **Step 3 : Créer le module** (`multi_edit`, `file_path="ReplicatedStorage.Shared.Config.Pets"`, `className="ModuleScript"`, `datamodel_type="Edit"`, premier edit `old_string=""`) :
```luau
--!strict
-- Pets.luau
-- Compagnons d'usine : 10 pets sur 5 raretés. Bonus PASSIFS (cumulables) branchés sur le même
-- vocabulaire effectKind que les Amélios. Module PUR (ne lit que `data`) : l'agrégation des bonus
-- des pets ÉQUIPÉS vit ici (testable, sans service), comme Upgrades.applyAccountStats. Les MUTATIONS
-- (octroi/équip/fusion/vente) vivent dans PetService.
--
-- passive = { {kind, value}... } ; kind ∈ luckAdd|speedMult|sellMult|multiAdd|qualityAdd|modifierAdd|
--   weightMult|crit|yield|magnet|offline. value = magnitude au niveau 1.
-- Magnitude effective = value * (1 + LEVEL_SCALE*(level-1)). `active` = capacité Phase 2 (def présente, inerte ici).

local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Types = require(ReplicatedStorage.Shared.Types)
local PetRarities = require(ReplicatedStorage.Shared.Config.PetRarities)

local LEVEL_SCALE = 0.15 -- +15% de l'effet par niveau (niv 10 ≈ ×2.35)
local MAX_LEVEL = 10

local Pets: { Types.PetDef } = {
	-- 🩶 COMMUN
	{ id = "bunny_plush", name = "Lapin en Peluche", rarity = "commun", icon = "🐰", model = "bunny_plush",
		passive = { { kind = "speedMult", value = 0.02 } } },
	{ id = "bolt_bot", name = "Boulon-Bot", rarity = "commun", icon = "🔩", model = "bolt_bot",
		passive = { { kind = "sellMult", value = 0.03 } } },
	{ id = "foam_cube", name = "Cube Mousse", rarity = "commun", icon = "🧊", model = "foam_cube",
		passive = { { kind = "luckAdd", value = 0.10 } } },

	-- 💚 PEU COMMUN
	{ id = "windup_duck", name = "Canard Mécanique", rarity = "peu_commun", icon = "🦆", model = "windup_duck",
		passive = { { kind = "offline", value = 0.05 } } },
	{ id = "neon_kitten", name = "Chaton Néon", rarity = "peu_commun", icon = "🐱", model = "neon_kitten",
		passive = { { kind = "luckAdd", value = 0.12 }, { kind = "yield", value = 0.02 } } },

	-- 💙 RARE
	{ id = "magnet_drone", name = "Drone Aimanté", rarity = "rare", icon = "🛸", model = "magnet_drone",
		passive = { { kind = "magnet", value = 0.10 } },
		active = { kind = "autosell", baseCooldown = 180, params = { fraction = 0.5 } } },
	{ id = "golden_teddy", name = "Ourson Doré", rarity = "rare", icon = "🧸", model = "golden_teddy",
		passive = { { kind = "sellMult", value = 0.06 } },
		active = { kind = "guaranteed_crit", baseCooldown = 180, params = { mult = 12 } } },

	-- 💜 ÉPIQUE
	{ id = "mini_clawbot", name = "Mini Claw-Bot", rarity = "epique", icon = "🤖", model = "mini_clawbot",
		passive = { { kind = "multiAdd", value = 0.03 } },
		active = { kind = "double_grab", baseCooldown = 150, params = { duration = 8 } } },
	{ id = "holo_fox", name = "Renard Holo-Arcade", rarity = "epique", icon = "🦊", model = "holo_fox",
		passive = { { kind = "crit", value = 0.005 } },
		active = { kind = "jackpot", baseCooldown = 150, params = { mult = 20 } } },

	-- 🧡 LÉGENDAIRE
	{ id = "ufo_mascot", name = "OVNI Mascotte", rarity = "legendaire", icon = "👽", model = "ufo_mascot",
		passive = { { kind = "luckAdd", value = 0.15 }, { kind = "speedMult", value = 0.03 }, { kind = "sellMult", value = 0.05 } },
		active = { kind = "prize_rain", baseCooldown = 120, params = { copies = 8 } } },
}

local byId: { [string]: Types.PetDef } = {}
for _, p in ipairs(Pets) do
	byId[p.id] = p
end

local function effOf(value: number, level: number): number
	return value * (1 + LEVEL_SCALE * ((level or 1) - 1))
end

-- Itère les pets ÉQUIPÉS -> (def, level). Tolère uid/def manquants.
local function forEachEquipped(data: any, fn: (Types.PetDef, number) -> ())
	local pets = data and data.pets
	local equipped = data and data.equippedPets
	if not pets or not equipped then
		return
	end
	for _, uid in ipairs(equipped) do
		local owned = pets[uid]
		local def = owned and byId[owned.defId]
		if def then
			fn(def, owned.level or 1)
		end
	end
end

-- Applique les passifs « stat de capture » des pets équipés au bloc de stats (mute + retourne).
-- Mêmes sémantiques que Upgrades.applyAccountStats. sellMult/crit/yield/magnet/offline NON appliqués ici
-- (lus respectivement par InventoryService et, en Phase 2, doGrab/AutomationService/DataService).
local function applyPetStats(stats: any, data: any): any
	forEachEquipped(data, function(def, level)
		for _, pas in ipairs(def.passive) do
			local e = effOf(pas.value, level)
			local k = pas.kind
			if k == "luckAdd" then
				stats.luck = (stats.luck or 0) + e
			elseif k == "qualityAdd" then
				stats.qualityBias = (stats.qualityBias or 0) + e
			elseif k == "modifierAdd" then
				stats.modifierChance = (stats.modifierChance or 0) + e
			elseif k == "weightMult" then
				stats.weightCap = (stats.weightCap or 0) * (1 + e)
			elseif k == "multiAdd" then
				stats.multiGrab = math.min(0.95, (stats.multiGrab or 0) + e)
			elseif k == "speedMult" then
				stats.grabSpeed = math.max(0.2, (stats.grabSpeed or 1) * (1 - e))
			end
		end
	end)
	return stats
end

-- Somme additive d'un `kind` sur les pets équipés (pour sellMult, crit, yield, magnet, offline).
local function bonusValue(data: any, kind: string): number
	local total = 0
	forEachEquipped(data, function(def, level)
		for _, pas in ipairs(def.passive) do
			if pas.kind == kind then
				total += effOf(pas.value, level)
			end
		end
	end)
	return total
end

-- Bonus de revente additif issu des pets équipés (lu par InventoryService.sellStack).
local function sellBonus(data: any): number
	return bonusValue(data, "sellMult")
end

-- Valeur de revente d'UN pet (menu) = sellBase rareté * (1 + 0.5*(level-1)).
local function sellValue(def: Types.PetDef, level: number): number
	local r = PetRarities.get(def.rarity)
	local base = (r and r.sellBase) or 0
	return math.floor(base * (1 + 0.5 * ((level or 1) - 1)) + 0.5)
end

-- Cooldown effectif d'une capacité active (Phase 2) = baseCooldown * (1 - 0.03*(level-1)), plancher 30 s.
local function cooldownAt(def: Types.PetDef, level: number): number
	if not def.active then
		return math.huge
	end
	return math.max(30, def.active.baseCooldown * (1 - 0.03 * ((level or 1) - 1)))
end

return {
	list = Pets,
	byId = byId,
	MAX_LEVEL = MAX_LEVEL,
	LEVEL_SCALE = LEVEL_SCALE,
	get = function(id: string): Types.PetDef?
		return byId[id]
	end,
	effOf = effOf,
	applyPetStats = applyPetStats,
	bonusValue = bonusValue,
	sellBonus = sellBonus,
	sellValue = sellValue,
	cooldownAt = cooldownAt,
}
```

- [ ] **Step 4 : Relire** `script_read` `ReplicatedStorage.Shared.Config.Pets` (entier). Vérifier 1ʳᵉ ligne `--!strict`, les 10 ids, et la présence de `applyPetStats`/`sellBonus`/`sellValue`/`cooldownAt`.

- [ ] **Step 5 : Relancer le test → attendu PASS.**

---

## Task 4 : `PROFILE_TEMPLATE` (pets / equippedPets / petSlots)

**Files:**
- Modify: `ReplicatedStorage.Shared.Config.GameConfig:51`
- Test: snippet `execute_luau` (Edit)

- [ ] **Step 1 : Écrire le test (qui doit échouer)**

`execute_luau` (`datamodel_type="Edit"`) :
```luau
local gc = require(game.ReplicatedStorage.Shared.Config.GameConfig:Clone())
local t = gc.PROFILE_TEMPLATE
local errs = {}
local function ck(c,m) if not c then table.insert(errs,m) end end
ck(type(t.pets) == "table", "pets manquant")
ck(type(t.equippedPets) == "table", "equippedPets manquant")
ck(t.petSlots == 3, "petSlots attendu 3, eu "..tostring(t.petSlots))
if #errs>0 then return "FAIL:\n"..table.concat(errs,"\n") end
return "PASS: PROFILE_TEMPLATE pets/equippedPets/petSlots"
```

- [ ] **Step 2 : Lancer → attendu FAIL** (`pets manquant`).

- [ ] **Step 3 : Éditer** (`multi_edit` sur `ReplicatedStorage.Shared.Config.GameConfig`, `datamodel_type="Edit"`) — remplacer exactement :
```luau
	ufos = {}, -- [uid] = { defId, level, stars } ; stars = niveau de fusion (sous-projet B), defaut 1
```
par :
```luau
	ufos = {}, -- [uid] = { defId, level, stars } ; stars = niveau de fusion (sous-projet B), defaut 1
	pets = {}, -- [uid] = { defId, level, locked } (compagnons d'usine)
	equippedPets = {}, -- liste d'uid équipés (≤ petSlots)
	petSlots = 3, -- slots de pets équipés (achetables jusqu'à 6)
```

- [ ] **Step 4 : Relire** `GameConfig` lignes 50-55 pour confirmer.

- [ ] **Step 5 : Relancer → attendu PASS.** (Les saves existantes reçoivent ces 3 clés à 0/`{}`/3 via `ProfileStore:Reconcile`, aucune migration manuelle.)

---

## Task 5 : `PetService` (mutations) + commandes admin de test

**Files:**
- Create: `ServerScriptService.Server.Services.PetService`
- Modify: `ServerScriptService.AdminService` (require + commandes `givePet`/`allPets`)
- Test: snippet `execute_luau` (Play, Server)

- [ ] **Step 1 : Créer le service** (`multi_edit`, `file_path="ServerScriptService.Server.Services.PetService"`, `className="ModuleScript"`, `datamodel_type="Edit"`, premier edit `old_string=""`) :
```luau
--!strict
-- PetService.luau
-- Mutations server-authoritative sur l'inventaire de pets : octroi, équip/déséquip, fusion, vente,
-- achat de slot. L'AGRÉGATION des bonus passifs est PURE dans Config.Pets (lue par CatchService /
-- InventoryService). Les capacités ACTIVES (tick) arrivent en Phase 2.

local Shared = game:GetService("ReplicatedStorage"):WaitForChild("Shared")
local ServerRoot = script.Parent.Parent
local Registry = require(ServerRoot.Registry)

local Pets = require(Shared.Config.Pets)
local Id = require(Shared.Util.Id)
local Net = require(Shared.Net.Net)

local PetService = {}

local MAX_SLOTS = 6
-- Coût d'achat du slot n (en $). Slots 1-3 offerts.
local SLOT_COST: { [number]: number } = { [4] = 250000, [5] = 5000000, [6] = 80000000 }

local function data(player: Player)
	return Registry.get("DataService").get(player)
end

local function isEquipped(d, uid: string): boolean
	for _, u in ipairs(d.equippedPets) do
		if u == uid then
			return true
		end
	end
	return false
end

-- Octroi d'un pet (éclosion EggShopService en Phase 3, et admin en test). Retourne l'uid.
function PetService.grant(player: Player, defId: string, level: number?): string?
	local d = data(player)
	if not d or not Pets.get(defId) then
		return nil
	end
	local uid = Id.new()
	d.pets[uid] = { defId = defId, level = level or 1, locked = false }
	Registry.get("DataService").replicate(player)
	return uid
end

function PetService.equip(player: Player, uid: string): boolean
	local d = data(player)
	if not d or not d.pets[uid] then
		return false
	end
	if isEquipped(d, uid) then
		return false
	end
	if #d.equippedPets >= (d.petSlots or 3) then
		return false
	end
	table.insert(d.equippedPets, uid)
	Registry.get("DataService").replicate(player)
	return true
end

function PetService.unequip(player: Player, uid: string): boolean
	local d = data(player)
	if not d then
		return false
	end
	for i, u in ipairs(d.equippedPets) do
		if u == uid then
			table.remove(d.equippedPets, i)
			Registry.get("DataService").replicate(player)
			return true
		end
	end
	return false
end

-- Fusion : 3 pets identiques (même defId + même level), non équipés et non verrouillés -> 1 pet level+1.
function PetService.fuse(player: Player, defId: string, level: number): string?
	local d = data(player)
	if not d or level >= Pets.MAX_LEVEL then
		return nil
	end
	local found: { string } = {}
	for uid, owned in pairs(d.pets) do
		if owned.defId == defId and owned.level == level and not owned.locked and not isEquipped(d, uid) then
			table.insert(found, uid)
			if #found == 3 then
				break
			end
		end
	end
	if #found < 3 then
		return nil
	end
	for _, uid in ipairs(found) do
		d.pets[uid] = nil
	end
	return PetService.grant(player, defId, level + 1)
end

-- Vente d'un pet (non équipé, non verrouillé). Crédite du $ et retourne la valeur (0 si refus).
function PetService.sell(player: Player, uid: string): number
	local d = data(player)
	if not d then
		return 0
	end
	local owned = d.pets[uid]
	if not owned or owned.locked or isEquipped(d, uid) then
		return 0
	end
	local def = Pets.get(owned.defId)
	if not def then
		return 0
	end
	local value = Pets.sellValue(def, owned.level)
	d.pets[uid] = nil
	Registry.get("EconomyService").add(player, "scrap", value) -- replicates
	return value
end

-- Achat du prochain slot de pet. Retourne true si acheté.
function PetService.buySlot(player: Player): boolean
	local d = data(player)
	if not d then
		return false
	end
	local cur = d.petSlots or 3
	if cur >= MAX_SLOTS then
		return false
	end
	local cost = SLOT_COST[cur + 1]
	if not cost then
		return false
	end
	if not Registry.get("EconomyService").spend(player, { scrap = cost }) then
		return false
	end
	d.petSlots = cur + 1
	Registry.get("DataService").replicate(player)
	return true
end

function PetService:Start()
	Net.onRequest("equipPet", function(player, payload)
		if typeof(payload) ~= "table" or typeof(payload.uid) ~= "string" then
			return false, "bad_payload"
		end
		return { ok = PetService.equip(player, payload.uid) }
	end)
	Net.onRequest("unequipPet", function(player, payload)
		if typeof(payload) ~= "table" or typeof(payload.uid) ~= "string" then
			return false, "bad_payload"
		end
		return { ok = PetService.unequip(player, payload.uid) }
	end)
	Net.onRequest("fusePet", function(player, payload)
		if typeof(payload) ~= "table" or typeof(payload.defId) ~= "string" or typeof(payload.level) ~= "number" then
			return false, "bad_payload"
		end
		local uid = PetService.fuse(player, payload.defId, payload.level)
		if not uid then
			return false, "cannot_fuse"
		end
		return { uid = uid }
	end)
	Net.onRequest("sellPet", function(player, payload)
		if typeof(payload) ~= "table" or typeof(payload.uid) ~= "string" then
			return false, "bad_payload"
		end
		local v = PetService.sell(player, payload.uid)
		if v <= 0 then
			return false, "cannot_sell"
		end
		return { value = v }
	end)
	Net.onRequest("buyPetSlot", function(player)
		if not PetService.buySlot(player) then
			return false, "cannot_buy"
		end
		local d = data(player)
		return { slots = d and d.petSlots or 3 }
	end)
end

return PetService
```

- [ ] **Step 2 : Relire** `script_read` `ServerScriptService.Server.Services.PetService` (entier) — confirme la création (sinon l'édition a no-op, recommencer).

- [ ] **Step 3 : Brancher les commandes admin de test** (`multi_edit` sur `ServerScriptService.AdminService`, `datamodel_type="Edit"`).

Edit 1 — ajouter le require. Remplacer exactement :
```luau
local UFOCatchers=require(RS.Shared.Config.UFOCatchers)
local Upgrades=require(RS.Shared.Config.Upgrades)
```
par :
```luau
local UFOCatchers=require(RS.Shared.Config.UFOCatchers)
local Upgrades=require(RS.Shared.Config.Upgrades)
local Pets=require(RS.Shared.Config.Pets)
```

Edit 2 — ajouter les commandes avant `fillJunk`. Remplacer exactement :
```luau
	elseif cmd=="fillJunk" then
```
par :
```luau
	elseif cmd=="givePet" then if Pets.get(arg) then Registry.get("PetService").grant(player, arg) end
	elseif cmd=="allPets" then for _,p in ipairs(Pets.list) do Registry.get("PetService").grant(player, p.id) end
	elseif cmd=="fillJunk" then
```

- [ ] **Step 4 : Relire** `AdminService` (require en tête + le bloc `elseif`) pour confirmer les deux edits.

- [ ] **Step 5 : Boot propre** — `start_stop_play(true)`, puis `get_console_output`. Attendu : `[Server] ready (N services).` avec N = précédent **+1** (PetService chargé), `[AdminService] pret`, **0 warn/erreur** `PetService`/`AdminService`. (Rester en Play pour le Step 6.)

- [ ] **Step 6 : Test live des mutations** — `execute_luau` (`datamodel_type="Server"`, en Play ; un joueur doit être présent) :
```luau
local Registry = require(game.ServerScriptService.Server.Registry)
local PS = Registry.get("PetService")
local DS = Registry.get("DataService")
local Eco = Registry.get("EconomyService")
local plr = game.Players:GetPlayers()[1]
if not plr then return "FAIL: aucun joueur (lance en solo Play)" end
local d = DS.get(plr); if not d then return "FAIL: data non prête" end
d.pets = {}; d.equippedPets = {}; d.petSlots = 3 -- reset propre pour le test
local errs = {}
local function ck(c,m) if not c then table.insert(errs,m) end end

local a = PS.grant(plr,"foam_cube"); local b = PS.grant(plr,"foam_cube"); local c = PS.grant(plr,"foam_cube")
ck(a and b and c, "grant a renvoyé nil")
ck(PS.equip(plr,a) == true, "equip a échoué")
ck(PS.equip(plr,b) == true, "equip b échoué")
ck(PS.equip(plr,c) == true, "equip c échoué (slot 3)")
ck(#d.equippedPets == 3, "equipped != 3")
local x = PS.grant(plr,"foam_cube")
ck(PS.equip(plr,x) == false, "equip au-delà de petSlots aurait dû échouer")
PS.unequip(plr,a); PS.unequip(plr,b); PS.unequip(plr,c)
ck(#d.equippedPets == 0, "unequip n'a pas vidé")
local fused = PS.fuse(plr,"foam_cube",1) -- consomme 3 des 4 L1 dispo -> 1 L2
ck(fused ~= nil, "fuse échoué")
ck(d.pets[fused] and d.pets[fused].level == 2, "pet fusionné level != 2")
local before = Eco.get(plr,"scrap")
local v = PS.sell(plr,fused) -- commun base 1000, L2 -> floor(1000*1.5)=1500
ck(v == 1500, "valeur de vente != 1500, eu "..tostring(v))
ck(Eco.get(plr,"scrap") == before + 1500, "$ non crédité")
ck(d.pets[fused] == nil, "pet vendu non retiré")
if #errs>0 then return "FAIL:\n"..table.concat(errs,"\n") end
return "PASS: grant/equip/cap-slots/unequip/fuse/sell"
```
Attendu : `PASS: grant/equip/cap-slots/unequip/fuse/sell`.

- [ ] **Step 7 : Repasser en Edit** — `start_stop_play(false)`.

---

## Task 6 : Brancher les passifs dans `CatchService.effectiveStats`

**Files:**
- Modify: `ServerScriptService.Server.Services.CatchService` (require + ligne 52)

- [ ] **Step 1 : Ajouter le require** (`multi_edit`, `datamodel_type="Edit"`) — remplacer exactement :
```luau
local Upgrades = require(Shared.Config.Upgrades)
local ClawUpgrade = require(Shared.Config.ClawUpgrade)
```
par :
```luau
local Upgrades = require(Shared.Config.Upgrades)
local Pets = require(Shared.Config.Pets)
local ClawUpgrade = require(Shared.Config.ClawUpgrade)
```

- [ ] **Step 2 : Appliquer les passifs** (`multi_edit`) — remplacer exactement :
```luau
	Upgrades.applyAccountStats(block, data.upgrades)
	local eff = ClawUpgrade.apply(block, level or 1, prestige or 0)
```
par :
```luau
	Upgrades.applyAccountStats(block, data.upgrades)
	Pets.applyPetStats(block, data) -- bonus passifs des pets équipés (luck/vitesse/multi/qualité/modif/charge)
	local eff = ClawUpgrade.apply(block, level or 1, prestige or 0)
```

- [ ] **Step 3 : Relire** `CatchService` lignes 18-21 (require) et 50-55 (apply) pour confirmer.

- [ ] **Step 4 : Boot propre + vérif d'effet (via Script temporaire dans la vraie VM)** — `start_stop_play(true)`, `get_console_output` : **0 erreur de compilation** et **0 `[CatchService] tick error`** (la pince de départ en s1 grab en continu → `effectiveStats` tourne à chaque grab ; si la ligne pet plantait, l'erreur de tick sortirait tout de suite). Puis créer un Script temporaire `ServerScriptService.PetCatchTest` (className `Script`, créé en Edit) qui prouve que `effectiveStats` consomme `data.pets` — comme `effectiveStats` est local/non exporté, on reproduit son préfixe et on compare avec/sans pet via la fonction PURE déjà câblée :
```luau
local RS = game:GetService("ReplicatedStorage")
local Pets = require(RS.Shared.Config.Pets)
local Registry = require(game.ServerScriptService.Server.Registry)
task.wait(2)
local plr = game.Players:GetPlayers()[1]
local d = plr and Registry.get("DataService").get(plr)
if not d then print("PETCATCH: FAIL no data") return end
d.pets = {}; d.equippedPets = {}; d.petSlots = 3
local PS = Registry.get("PetService")
local u = PS.grant(plr, "foam_cube"); PS.equip(plr, u) -- luckAdd 0.10
local block = { luck = 1, grabSpeed = 2, qualityBias = 0, modifierChance = 0, weightCap = 10, multiGrab = 0 }
Pets.applyPetStats(block, d)
print("PETCATCH: " .. ((math.abs(block.luck - 1.10) < 1e-6) and "PASS luck=1.10" or ("FAIL luck=" .. block.luck)))
```
Démarrer Play, attendre ~3 s, `get_console_output`, repérer `PETCATCH: PASS luck=1.10`. **Nettoyer** : `start_stop_play(false)` puis supprimer le Script temporaire (`execute_luau` Edit : `local s=game.ServerScriptService:FindFirstChild("PetCatchTest"); if s then s:Destroy() end`). (La formule est déjà prouvée par le test pur du Task 3 ; ici on confirme l'intégration réelle.) Rester en Edit.

---

## Task 7 : Brancher le bonus de revente dans `InventoryService.sellStack`

**Files:**
- Modify: `ServerScriptService.Server.Services.InventoryService` (require + ligne 68)

> Si tu reviens d'un Play, repasse en **Edit** (`start_stop_play(false)`) avant d'éditer.

- [ ] **Step 1 : Ajouter le require** (`multi_edit`, `datamodel_type="Edit"`) — remplacer exactement :
```luau
local Upgrades = require(Shared.Config.Upgrades)
local Id = require(Shared.Util.Id)
```
par :
```luau
local Upgrades = require(Shared.Config.Upgrades)
local Pets = require(Shared.Config.Pets)
local Id = require(Shared.Util.Id)
```

- [ ] **Step 2 : Ajouter le bonus pet au gain** (`multi_edit`) — remplacer exactement :
```luau
	local earned = math.floor(unit * n * (1 + Crafts.bonus(d, "sellMult") + Upgrades.sellBonus(d.upgrades)) + 0.5) -- Fonderie craft + Prix de Revente (Amélios)
```
par :
```luau
	local earned = math.floor(unit * n * (1 + Crafts.bonus(d, "sellMult") + Upgrades.sellBonus(d.upgrades) + Pets.sellBonus(d)) + 0.5) -- Fonderie craft + Prix de Revente (Amélios) + pets
```

- [ ] **Step 3 : Relire** `InventoryService` (require en tête + ligne ~68) pour confirmer.

- [ ] **Step 4 : Boot propre + vérif de revente (Script temporaire dans la vraie VM)** — `start_stop_play(true)`, `get_console_output` (0 erreur `InventoryService`). Puis créer un Script temporaire `ServerScriptService.PetSellTest` (className `Script`, créé en Edit ; `InventoryService.sellStack` est public, donc on l'appelle réellement) :
```luau
local Reg = require(game.ServerScriptService.Server.Registry)
task.wait(2)
local DS, PS, Inv = Reg.get("DataService"), Reg.get("PetService"), Reg.get("InventoryService")
local plr = game.Players:GetPlayers()[1]
local d = plr and DS.get(plr)
if not d then print("PETSELL: FAIL no data") return end
d.pets = {}; d.equippedPets = {}; d.petSlots = 3; d.inventory = {}
-- Stack de 100 pour que le bonus +6% dépasse l'arrondi (sur 1 item bon marché il floorerait pareil).
for _ = 1, 100 do Inv.addItem(plr, { defId = "scrap_metal", rarity = "common", modifier = "none" }) end
local base = Inv.sellStack(plr, (next(d.inventory))) -- sans pet
d.inventory = {}
for _ = 1, 100 do Inv.addItem(plr, { defId = "scrap_metal", rarity = "common", modifier = "none" }) end
local g = PS.grant(plr, "golden_teddy"); PS.equip(plr, g) -- sellMult +0.06 (L1)
local withPet = Inv.sellStack(plr, (next(d.inventory)))
print("PETSELL: " .. ((base > 0 and withPet > base) and string.format("PASS base=%d pet=%d", base, withPet) or string.format("FAIL base=%d pet=%d", base, withPet)))
```
Démarrer Play, attendre ~3 s, `get_console_output`, repérer `PETSELL: PASS base=… pet=…` (pet strictement > base). **Nettoyer** : `start_stop_play(false)` puis supprimer le Script (`execute_luau` Edit : `local s=game.ServerScriptService:FindFirstChild("PetSellTest"); if s then s:Destroy() end`).

- [ ] **Step 5 : Repasser en Edit** — `start_stop_play(false)`.

---

## Task 8 : Checkpoint d'intégration + persistance

- [ ] **Step 1 : Vérification d'ensemble** — `start_stop_play(true)`, `get_console_output` : démarrage propre, `[Server] ready` avec PetService compté (15 services), 0 erreur. Refaire le test de mutation du Task 5 **via un Script temporaire** `ServerScriptService.PetCheckTest` (className `Script` ; même contenu que le test de revue Task 5 : grant/equip/cap/unequip/fuse/sell + `print("PETCHECK: PASS/FAIL")`), démarrer Play, `get_console_output` → `PETCHECK: PASS`, puis supprimer le Script. (Rappel : `execute_luau(datamodel_type="Server")` est en VM isolée — toujours passer par un Script temporaire pour toucher le vrai Registry.) Repasser en Edit.

- [ ] **Step 2 : Compat saves** — vérifier (Mock ProfileStore Studio ou save réelle) qu'un profil **existant** se charge sans erreur : `Reconcile` ajoute `pets={}`, `equippedPets={}`, `petSlots=3` ; aucune erreur de shape au join (observer la console).

- [ ] **Step 3 : Persistance** — ⚠️ Prévenir l'utilisateur : *« Phase 1 pets vérifiée — sauvegarde la place (Ctrl+S) pour persister dans build.rbxlx. »* (Pas de commit git dans ce projet.)

---

## Self-Review (rempli)

- **Couverture spec (phase 1)** : roster 10 pets + 5 raretés (Task 2-3, §A) ✓ · niveaux/scaling + fusion + slots + vente (Task 3 `effOf`/`sellValue`/`cooldownAt`, Task 5 `fuse`/`buySlot`/`sell`, §B) ✓ · stockage profil `pets`/`equippedPets`/`petSlots` (Task 1, Task 4, §F) ✓ · agrégation pure + branchement passifs `effectiveStats`/`sellStack` (Task 3, 6, 7, §E) ✓ · types (Task 1) ✓ · outil de test admin (Task 5, §I) ✓. **Reporté (Roadmap)** : passifs `crit`/`yield`/`magnet`/`offline` (présents dans `bonusValue`, consommés en Phase 2), capacités actives, `Eggs`/shop, errance, UI, Blender — conforme au découpage §H.
- **Placeholders** : aucun — chaque étape porte le code/commande exact.
- **Cohérence des noms** : `Pets.applyPetStats`/`sellBonus`/`bonusValue`/`sellValue`/`cooldownAt`/`MAX_LEVEL`/`effOf` · `PetService.grant`/`equip`/`unequip`/`fuse`/`sell`/`buySlot` · remotes `equipPet`/`unequipPet`/`fusePet`/`sellPet`/`buyPetSlot` · champs `pets`/`equippedPets`/`petSlots` · kinds `luckAdd`/`speedMult`/`sellMult`/`multiAdd`/`qualityAdd`/`modifierAdd`/`weightMult`/`crit`/`yield`/`magnet`/`offline` (alignés sur `Upgrades.effectKind`) — identiques entre défs, helpers, service, consommateurs et tests.

---

## Roadmap — phases suivantes (plans à écrire à pleine fidélité au moment venu)

Chaque phase devient un fichier `docs/superpowers/plans/2026-06-17-pet-system-0N-*.md`, détaillé une fois la précédente posée (les hooks exacts dépendent de l'état réel du code).

- **02 — Capacités actives + passifs restants.** Brancher `crit`/`yield` pet dans `CatchService.doGrab` (`chance += Pets.bonusValue(data,"crit")` / `+ ... ,"yield")`), `magnet`/`offline` dans `AutomationService` (`magnetInterval`/`grantOffline` lisent `Pets.bonusValue`), puis le **tick `PetService`** (accumulateur Heartbeat par joueur) qui déclenche les `active` sur cooldown : `autosell` (`InventoryService.sellFiltered` partiel), `guaranteed_crit` (flag consommé dans `doGrab`), `double_grab` (fenêtre lue dans `doGrab`), `jackpot` (grant cash + FX), `prize_rain` (copies du butin). Events `petAbility`.
- **03 — Config `Eggs` + `EggShopService`.** `Eggs` (5 défs + `Eggs.lineupFor(bucket)` global déterministe + garde-fou `common_egg` + `Eggs.rollPet`) ; `EggShopService` (lineup par `bucket=floor(os.time()/900)`, gating par `data.stats.lifetimeEarned`, remote `buyEgg` → `EconomyService.spend` → tirage → `PetService.grant` → event `petHatched`, `getPetShop`, broadcast `petShopRefreshed`). Aucune migration (`lifetimeEarned` existe déjà).
- **04 — Build 3D du shop d'œufs.** Modèle `EggShop` procédural idempotent (générateur Edit-mode, façon `MapBlockout.PlotConnectors`/roulette) dans la zone d'accueil (offset image 3) : 3 piédestaux, arche, SurfaceGui countdown, props `DecorLibrary`.
- **05 — Errance + interaction + menus.** `PetController` (clone `ReplicatedStorage.Assets.PetMeshes[model]` — placeholders parts ; errance waypoints autour de la parcelle ; idle/walk ; `BillboardGui` + `ProximityPrompt` → menu), `PetMenuController` (grille + carte détail `ViewportFrame`, Équiper/Déséquiper/Fusionner/Vendre, achat de slot ; `Net.request` vers les remotes du Task 5), `EggShopController` (countdown + prompts d'achat + FX éclosion réutilisant `RouletteRollController`/`FXKit`).
- **06 — Assets Blender.** 10 pets (1 objet par zone de couleur), riggés idle+marche, upload addon officiel → `Elements_Blender/pets/asset_ids.json` → `ReplicatedStorage.Assets.PetMeshes` ; remplace les placeholders. Fallback procédural si rigging trop lourd.
- **07 — Équilibrage & vérif end-to-end.** Calibrage prix œufs / magnitudes / cooldowns / coûts de slots ; simulation `execute_luau` ; passe finale.
