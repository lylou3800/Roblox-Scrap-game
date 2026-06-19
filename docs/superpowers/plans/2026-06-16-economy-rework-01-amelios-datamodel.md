# Économie Rework — Phase 1 : Modèle de données Amélios + stats simples — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remplacer les 2 améliorations de compte par le **catalogue complet de 14 améliorations globales** (5 familles) et câbler les **7 effets « stats simples »** (chance, qualité, modificateurs, capacité, multi-prise, vitesse, revente) dans la boucle de capture et la vente.

**Architecture :** Le module config `Upgrades` devient la source unique : il porte les 14 défs (famille, courbe, `effectKind`, `perLevel`, `params`) **et** une fonction pure `applyAccountStats(stats, levels)` qui applique les 6 effets de capture à un bloc de stats, plus `sellBonus(levels)` pour la revente. `CatchService.effectiveStats` et `InventoryService.sellStack` délèguent à ces helpers (DRY, testable). Les 7 effets « mécaniques » (crit, rendement, aimant, recycleur pro, coffre, hors-ligne, vente-en-lot) ont leurs défs présentes dès maintenant mais sont **ignorées** par `applyAccountStats` — elles seront consommées par leurs services dans les phases 2-3.

**Tech Stack :** Roblox Luau · ModuleScripts dans `ReplicatedStorage.Shared` · services serveur · édition + test via le MCP Roblox Studio.

**Spec :** `docs/superpowers/specs/2026-06-16-economy-progression-rework-design.md` (§B, §F, §I).

---

## Notes d'environnement (lire avant de commencer)

- **Pas de framework de test ni de git.** « Test » = un snippet `execute_luau` qui *require une copie fraîche* du module et `assert`. **Toujours** requérir `module:Clone()` : en Edit, `require` met en cache la 1ʳᵉ version et l'`execute_luau` du MCP réutilise ce cache entre appels (cf. memory `roblox-studio-mcp-gotchas`).
- **Mode Studio :** être en **Edit** (single datamodel) pour lire/éditer les services serveur. `get_studio_state` doit montrer `Edit`. Si Play, `start_stop_play(false)`.
- **Édition de Source :** pour une réécriture complète d'un module → `execute_luau` qui fait `script.Source = [==[ ... ]==]`. Pour un diff ciblé → l'outil MCP `multi_edit`. **Après CHAQUE édition, relire (`script_read`) pour confirmer** : `multi_edit` peut silencieusement no-op (memory).
- **Persistance :** les éditions vivent dans le DataModel Edit ; elles ne sont écrites dans `build.rbxlx` que quand **l'utilisateur sauvegarde (Ctrl+S)**. Il n'y a pas de commit git — chaque « checkpoint » du plan = un point où prévenir l'utilisateur qu'il peut sauvegarder.
- **Tester un service serveur :** `effectiveStats`/`sellStack` sont des fonctions locales non exportées, et le `Registry` de l'`execute_luau` MCP est isolé du vrai serveur (memory). Donc on les vérifie en **live** : `start_stop_play(true)` → console propre + flux client réel `Net.request(...)` (admin `lylou38000` pour `ReplicatedStorage.AdminEvent:FireServer("scrap", n)`).

---

## File Structure

| Fichier (chemin DataModel) | Rôle | Action |
|---|---|---|
| `ReplicatedStorage.Shared.Types` | type `UpgradeDef` (+ `UpgradeFamily`) | Modifier (lignes 91-100) |
| `ReplicatedStorage.Shared.Config.Upgrades` | catalogue 14 défs + helpers purs | **Réécriture complète** |
| `ReplicatedStorage.Shared.Config.GameConfig` | `PROFILE_TEMPLATE.upgrades` (14 ids) | Modifier (ligne 56) |
| `ServerScriptService.Server.Services.CatchService` | `effectiveStats` → `applyAccountStats` | Modifier (lignes ~38-58) |
| `ServerScriptService.Server.Services.InventoryService` | `sellStack` → `+ sellBonus` | Modifier (require + ligne 67) |

L'UI Amélios **n'est pas touchée en Phase 1** : `UIController.populate("Ameliorations")` itère déjà `Upgrades.list` → les 14 améliorations s'afficheront automatiquement en liste plate (fonctionnel mais non groupé ; le rendu par famille = Phase 5).

---

## Task 1 : Étendre le type `UpgradeDef`

**Files:**
- Modify: `ReplicatedStorage.Shared.Types:91-100`

- [ ] **Step 1 : Appliquer l'édition** (outil MCP `multi_edit` sur `ReplicatedStorage.Shared.Types`)

Remplacer exactement :
```luau
export type UpgradeDef = {
	id: string,
	name: string,
	stat: string, -- which UFO stat / system value it boosts
	maxLevel: number,
	baseCost: number,
	costGrowth: number, -- multiplicative cost growth per level
	perLevel: number, -- additive effect per level
	currency: string,
}
```
par :
```luau
export type UpgradeFamily = { id: string, name: string, color: { number }, icon: string }

export type UpgradeDef = {
	id: string,
	name: string,
	family: string, -- chance|cadence|valeur|auto|meta
	icon: string, -- icon key for the Amélios card
	maxLevel: number,
	baseCost: number,
	costGrowth: number, -- multiplicative cost growth per level
	effectKind: string, -- luckAdd|qualityAdd|modifierAdd|weightMult|multiAdd|speedMult|sellMult|crit|yield|bulkBonus|magnet|recyclerPro|vault|offline
	perLevel: number, -- per-level magnitude (sense depends on effectKind)
	currency: string,
	params: { [string]: number }?, -- extra knobs (crit mult ladder, magnet timing, vault cap...)
	descTemplate: string?,
}
```

- [ ] **Step 2 : Relire pour confirmer**

`script_read` `ReplicatedStorage.Shared.Types` lignes 88-108. Vérifier que `UpgradeFamily` existe, que `stat` a disparu et que `effectKind`/`params`/`descTemplate`/`family`/`icon` sont présents. (Les types sont effacés à l'exécution : la validation runtime vient du Task 2.)

---

## Task 2 : Réécrire le module `Upgrades`

**Files:**
- Modify: `ReplicatedStorage.Shared.Config.Upgrades` (réécriture complète)
- Test: snippet `execute_luau` (ci-dessous)

- [ ] **Step 1 : Écrire le test (qui doit échouer)**

`execute_luau` (datamodel **Edit**) :
```luau
local mod = game.ReplicatedStorage.Shared.Config.Upgrades:Clone()
local U = require(mod)
local errs = {}
local function check(c, m) if not c then table.insert(errs, m) end end
check(#U.list == 14, "expected 14 upgrades, got " .. tostring(#U.list))
check(U.FAMILIES and #U.FAMILIES == 5, "expected 5 families")
for _, id in ipairs({"luck","quality","modifiers","crit_master","grab_speed","multi_grab","weight_cap","sell_mult","yield","bulk_bonus","magnet","recycler_pro","vault","offline"}) do
	check(U.get(id) ~= nil, "missing def: " .. id)
end
check(U.costFor(U.get("luck"), 0) == 150, "luck L0 should be 150, got " .. tostring(U.costFor(U.get("luck"), 0)))
check(U.costFor(U.get("sell_mult"), 9) == 7689, "sell_mult L9 should be 7689, got " .. tostring(U.costFor(U.get("sell_mult"), 9)))
local blk = { luck = 1, grabSpeed = 2, qualityBias = 0, modifierChance = 0, weightCap = 10, multiGrab = 0 }
U.applyAccountStats(blk, { luck = 10, grab_speed = 10, weight_cap = 5, multi_grab = 4, quality = 3, modifiers = 2 })
check(math.abs(blk.luck - 1.8) < 1e-6, "luck applied wrong: " .. blk.luck)
check(math.abs(blk.grabSpeed - (2 * 0.97 ^ 10)) < 1e-6, "speed applied wrong: " .. blk.grabSpeed)
check(math.abs(blk.weightCap - (10 * 1.06 ^ 5)) < 1e-6, "weight applied wrong: " .. blk.weightCap)
check(math.abs(blk.qualityBias - 0.18) < 1e-6, "quality applied wrong: " .. blk.qualityBias)
check(math.abs(blk.modifierChance - 0.08) < 1e-6, "modifier applied wrong: " .. blk.modifierChance)
check(math.abs(blk.multiGrab - 0.06) < 1e-6, "multi applied wrong: " .. blk.multiGrab)
check(math.abs(U.sellBonus({ sell_mult = 5 }) - 0.20) < 1e-6, "sellBonus wrong: " .. U.sellBonus({ sell_mult = 5 }))
local blk2 = { luck = 0, grabSpeed = 1, weightCap = 1, multiGrab = 0 }
U.applyAccountStats(blk2, { crit_master = 10, yield = 10, magnet = 10, vault = 10, offline = 10, recycler_pro = 10, bulk_bonus = 10 })
check(blk2.luck == 0 and blk2.grabSpeed == 1, "bespoke upgrades must NOT change catch stats")
if #errs > 0 then return "FAIL:\n" .. table.concat(errs, "\n") end
return "PASS: 14 upgrades, families, costs, applyAccountStats (simple only), sellBonus"
```

- [ ] **Step 2 : Lancer le test → attendu FAIL**

Attendu : `FAIL:` avec `expected 14 upgrades, got 2` (+ défs manquantes). Confirme qu'on teste bien l'ancien module.

- [ ] **Step 3 : Réécrire le module** (`execute_luau` Edit : `script.Source = [==[ ... ]==]`)

Mettre `ReplicatedStorage.Shared.Config.Upgrades.Source` à exactement :
```luau
--!strict
-- Upgrades.luau
-- Améliorations globales de compte — l'onglet Amélios ("Centre de Commande de l'Usine").
-- 14 améliorations en 5 familles. Coût géométrique : cost(level) = round(baseCost * costGrowth^level).
-- effectKind dit aux consommateurs comment appliquer l'effet :
--   stats de capture simples (appliquées ici par applyAccountStats) :
--     luckAdd, qualityAdd, modifierAdd, weightMult, multiAdd, speedMult
--   sellMult : lu par InventoryService (Upgrades.sellBonus)
--   mécaniques sur-mesure (consommées par leurs services, PAS appliquées ici) :
--     crit, yield, magnet, recyclerPro, vault, offline, bulkBonus
-- perLevel = magnitude par niveau (sens selon effectKind). params = boutons de réglage en plus.

local Types = require(game:GetService("ReplicatedStorage").Shared.Types)

local FAMILIES: { Types.UpgradeFamily } = {
	{ id = "chance",  name = "Chance & Rareté",       color = { 1.00, 0.78, 0.20 }, icon = "luck" },
	{ id = "cadence", name = "Cadence & Débit",        color = { 0.35, 0.80, 1.00 }, icon = "speed" },
	{ id = "valeur",  name = "Valeur & Revente",       color = { 0.40, 0.90, 0.45 }, icon = "cash" },
	{ id = "auto",    name = "Automatisation & Récup", color = { 0.70, 0.55, 1.00 }, icon = "magnet" },
	{ id = "meta",    name = "Méta & Passif",          color = { 1.00, 0.55, 0.75 }, icon = "vault" },
}

local Upgrades: { Types.UpgradeDef } = {
	-- 🍀 CHANCE & RARETÉ
	{ id = "luck", name = "Chance", family = "chance", icon = "luck",
		maxLevel = 20, baseCost = 150, costGrowth = 1.45, currency = "scrap",
		effectKind = "luckAdd", perLevel = 0.08, descTemplate = "+{e} chance (toutes les pinces)" },
	{ id = "quality", name = "Œil Expert", family = "chance", icon = "eye",
		maxLevel = 15, baseCost = 220, costGrowth = 1.5, currency = "scrap",
		effectKind = "qualityAdd", perLevel = 0.06, descTemplate = "+{e} qualité (biaise la rareté)" },
	{ id = "modifiers", name = "Modificateurs", family = "chance", icon = "spark",
		maxLevel = 15, baseCost = 260, costGrowth = 1.5, currency = "scrap",
		effectKind = "modifierAdd", perLevel = 0.04, descTemplate = "+{e} chance de modificateur" },
	{ id = "crit_master", name = "Coup de Maître", family = "chance", icon = "crit",
		maxLevel = 12, baseCost = 500, costGrowth = 1.7, currency = "scrap",
		effectKind = "crit", perLevel = 0.004, params = { multBase = 10, multPerLevel = 3.6 },
		descTemplate = "{e}% de coup critique (×{m} valeur)" },

	-- ⚡ CADENCE & DÉBIT
	{ id = "grab_speed", name = "Vitesse de Pince", family = "cadence", icon = "speed",
		maxLevel = 20, baseCost = 180, costGrowth = 1.45, currency = "scrap",
		effectKind = "speedMult", perLevel = 0.03, descTemplate = "−{e}% temps de capture" },
	{ id = "multi_grab", name = "Multi-Prise", family = "cadence", icon = "combo",
		maxLevel = 15, baseCost = 300, costGrowth = 1.5, currency = "scrap",
		effectKind = "multiAdd", perLevel = 0.015, descTemplate = "+{e} multi-prise (combos)" },
	{ id = "weight_cap", name = "Capacité de Charge", family = "cadence", icon = "weight",
		maxLevel = 15, baseCost = 240, costGrowth = 1.5, currency = "scrap",
		effectKind = "weightMult", perLevel = 0.06, descTemplate = "+{e}% capacité de charge" },

	-- 💰 VALEUR & REVENTE
	{ id = "sell_mult", name = "Prix de Revente", family = "valeur", icon = "cash",
		maxLevel = 20, baseCost = 200, costGrowth = 1.5, currency = "scrap",
		effectKind = "sellMult", perLevel = 0.04, descTemplate = "+{e}% à la revente" },
	{ id = "yield", name = "Rendement des Scraps", family = "valeur", icon = "yield",
		maxLevel = 15, baseCost = 280, costGrowth = 1.5, currency = "scrap",
		effectKind = "yield", perLevel = 0.03, descTemplate = "+{e}% butin bonus par capture" },
	{ id = "bulk_bonus", name = "Vente en Lot", family = "valeur", icon = "bulk",
		maxLevel = 10, baseCost = 400, costGrowth = 1.6, currency = "scrap",
		effectKind = "bulkBonus", perLevel = 0.03, params = { threshold = 50 },
		descTemplate = "+{e}% si vente de {t}+ items d'un coup" },

	-- 🧲 AUTOMATISATION & RÉCUP
	{ id = "magnet", name = "Aimant Récupérateur", family = "auto", icon = "magnet",
		maxLevel = 15, baseCost = 300, costGrowth = 1.5, currency = "scrap",
		effectKind = "magnet", perLevel = 1,
		params = { baseInterval = 12, intervalPerLevel = 0.6, minInterval = 3, baseFraction = 0.2, fractionPerLevel = 0.06 },
		descTemplate = "auto-récupère le tas (niveau {lvl})" },
	{ id = "recycler_pro", name = "Recycleur Pro", family = "auto", icon = "recycler",
		maxLevel = 12, baseCost = 350, costGrowth = 1.5, currency = "scrap",
		effectKind = "recyclerPro", perLevel = 1, params = { ratePerLevel = 0.15, yieldPerLevel = 0.10 },
		descTemplate = "+débit / +rendement recycleur (niveau {lvl})" },

	-- 🏦 MÉTA & PASSIF
	{ id = "vault", name = "Coffre / Intérêts", family = "meta", icon = "vault",
		maxLevel = 10, baseCost = 1000, costGrowth = 1.7, currency = "scrap",
		effectKind = "vault", perLevel = 0.001, params = { capPerLevel = 50000 },
		descTemplate = "+{e}%/min sur le $ détenu (plafonné)" },
	{ id = "offline", name = "Gains Hors-Ligne", family = "meta", icon = "offline",
		maxLevel = 8, baseCost = 2000, costGrowth = 1.8, currency = "scrap",
		effectKind = "offline", perLevel = 0.07, params = { basePct = 0.20, baseHours = 4, hoursPerLevel = 1 },
		descTemplate = "{e}% du taux en hors-ligne" },
}

local byId: { [string]: Types.UpgradeDef } = {}
for _, u in ipairs(Upgrades) do byId[u.id] = u end

local function costFor(def: Types.UpgradeDef, level: number): number
	return math.floor(def.baseCost * (def.costGrowth ^ level) + 0.5)
end

local function effectFor(def: Types.UpgradeDef, level: number): number
	return def.perLevel * level
end

-- Applique les améliorations « stat de capture simple » à un bloc de stats (mute + retourne).
-- `levels` = data.upgrades (id -> niveau). Les mécaniques sur-mesure sont volontairement ignorées.
local function applyAccountStats(stats: any, levels: any): any
	levels = levels or {}
	for _, def in ipairs(Upgrades) do
		local n = levels[def.id] or 0
		if n > 0 then
			local k = def.effectKind
			if k == "luckAdd" then
				stats.luck = (stats.luck or 0) + def.perLevel * n
			elseif k == "qualityAdd" then
				stats.qualityBias = (stats.qualityBias or 0) + def.perLevel * n
			elseif k == "modifierAdd" then
				stats.modifierChance = (stats.modifierChance or 0) + def.perLevel * n
			elseif k == "weightMult" then
				stats.weightCap = (stats.weightCap or 0) * ((1 + def.perLevel) ^ n)
			elseif k == "multiAdd" then
				stats.multiGrab = math.min(0.95, (stats.multiGrab or 0) + def.perLevel * n)
			elseif k == "speedMult" then
				stats.grabSpeed = math.max(0.2, (stats.grabSpeed or 1) * ((1 - def.perLevel) ^ n))
			end
		end
	end
	return stats
end

-- Bonus additif de valeur de revente issu de "Prix de Revente" (lu par InventoryService).
local function sellBonus(levels: any): number
	local def = byId["sell_mult"]
	local n = (levels and levels.sell_mult) or 0
	return (def and def.perLevel * n) or 0
end

return {
	list = Upgrades,
	byId = byId,
	FAMILIES = FAMILIES,
	get = function(id: string): Types.UpgradeDef?
		return byId[id]
	end,
	costFor = costFor,
	effectFor = effectFor,
	applyAccountStats = applyAccountStats,
	sellBonus = sellBonus,
}
```

- [ ] **Step 4 : Relire pour confirmer l'écriture**

`script_read` `ReplicatedStorage.Shared.Config.Upgrades` (entier). Vérifier que la 1ʳᵉ ligne est `--!strict`, que `FAMILIES` a 5 entrées et qu'on voit les 14 ids. (Si la Source n'a pas changé → l'édition a no-op, recommencer.)

- [ ] **Step 5 : Relancer le test → attendu PASS**

Réexécuter le snippet du Step 1. Attendu : `PASS: 14 upgrades, families, costs, applyAccountStats (simple only), sellBonus`.

---

## Task 3 : Compléter `PROFILE_TEMPLATE.upgrades`

**Files:**
- Modify: `ReplicatedStorage.Shared.Config.GameConfig:56`
- Test: snippet `execute_luau`

- [ ] **Step 1 : Écrire le test (qui doit échouer)**

`execute_luau` (Edit) :
```luau
local gc = require(game.ReplicatedStorage.Shared.Config.GameConfig:Clone())
local up = gc.PROFILE_TEMPLATE.upgrades
local ids = {"luck","quality","modifiers","crit_master","grab_speed","multi_grab","weight_cap","sell_mult","yield","bulk_bonus","magnet","recycler_pro","vault","offline"}
local errs = {}
for _, id in ipairs(ids) do
	if up[id] ~= 0 then table.insert(errs, "missing/non-zero template upgrade: " .. id) end
end
local n = 0 for _ in pairs(up) do n += 1 end
if n ~= 14 then table.insert(errs, "expected 14 template upgrade keys, got " .. n) end
if #errs > 0 then return "FAIL:\n" .. table.concat(errs, "\n") end
return "PASS: PROFILE_TEMPLATE.upgrades has all 14 ids at 0"
```

- [ ] **Step 2 : Lancer → attendu FAIL** (`expected 14 ... got 2`).

- [ ] **Step 3 : Éditer** (`multi_edit`) — remplacer exactement :
```luau
	upgrades = { luck = 0, grab_speed = 0 },
```
par :
```luau
	upgrades = {
		luck = 0, quality = 0, modifiers = 0, crit_master = 0,
		grab_speed = 0, multi_grab = 0, weight_cap = 0,
		sell_mult = 0, yield = 0, bulk_bonus = 0,
		magnet = 0, recycler_pro = 0, vault = 0, offline = 0,
	},
```

- [ ] **Step 4 : Relire** `GameConfig` lignes 56-64 pour confirmer.

- [ ] **Step 5 : Relancer → attendu PASS.**

---

## Task 4 : Câbler `CatchService.effectiveStats`

**Files:**
- Modify: `ServerScriptService.Server.Services.CatchService:38-58`

`Upgrades` est déjà requis dans `CatchService` (haut du fichier). Pas de nouveau require.

- [ ] **Step 1 : Éditer** (`multi_edit`) — remplacer exactement :
```luau
	local s = ufoDef.stats
	local luckDef = Upgrades.get("luck")
	local speedDef = Upgrades.get("grab_speed")

	local bonusLuck = luckDef and Upgrades.effectFor(luckDef, data.upgrades.luck or 0) or 0
	local speedReduction = speedDef and Upgrades.effectFor(speedDef, data.upgrades.grab_speed or 0) or 0
	local speedFactor = math.max(0.2, 1 - speedReduction)

	-- Base + account upgrades, then per-claw level scaling (Parts-funded, see ClawUpgrade).
	local eff = ClawUpgrade.apply({
		grabSpeed = s.grabSpeed * speedFactor,
		luck = s.luck + bonusLuck,
		qualityBias = s.qualityBias,
		modifierChance = s.modifierChance,
		weightCap = s.weightCap,
		stability = s.stability or 1,
		multiGrab = s.multiGrab or 0,
		specialEfficiency = s.specialEfficiency,
	}, level or 1, prestige or 0)
```
par :
```luau
	local s = ufoDef.stats

	-- Bloc de stats de base -> améliorations globales (Amélios) -> niveau/prestige par pince -> crafts.
	local block = {
		grabSpeed = s.grabSpeed,
		luck = s.luck,
		qualityBias = s.qualityBias,
		modifierChance = s.modifierChance,
		weightCap = s.weightCap,
		stability = s.stability or 1,
		multiGrab = s.multiGrab or 0,
		specialEfficiency = s.specialEfficiency,
	}
	Upgrades.applyAccountStats(block, data.upgrades)
	local eff = ClawUpgrade.apply(block, level or 1, prestige or 0)
```

- [ ] **Step 2 : Relire** `CatchService` lignes 36-62 pour confirmer (plus aucune référence à `luckDef`/`speedDef`/`speedFactor`).

- [ ] **Step 3 : Boot propre** — `start_stop_play(true)`, puis `get_console_output`. Attendu : aucune erreur `[CatchService]` ni de compilation. (Puis on reste en Play pour le Step 4.)

- [ ] **Step 4 : Smoke test live de l'effet vitesse** — depuis le datamodel **Client** :
```luau
-- compte les catches sur ~6 s, achète 10 niv de vitesse, recompte.
local Net = require(game.ReplicatedStorage.Shared.Net.Net)
game.ReplicatedStorage.AdminEvent:FireServer("scrap", 1e9) -- admin lylou38000
-- (s'assurer qu'une pince est placée en s1 ; sinon en placer une via l'UI/admin)
return "manual: observe inventory growth before/after buying grab_speed via UI"
```
Vérification manuelle acceptable : acheter plusieurs niveaux de **Vitesse de Pince** dans l'onglet Amélios (liste plate) et constater que les captures s'enchaînent plus vite (le tas grossit plus vite). L'exactitude de la formule est déjà couverte par le test unitaire du Task 2.

- [ ] **Step 5 : Repasser en Edit** — `start_stop_play(false)` (pour la suite des éditions serveur).

---

## Task 5 : Câbler le bonus de revente dans `InventoryService.sellStack`

**Files:**
- Modify: `ServerScriptService.Server.Services.InventoryService` (require + ligne 67)

- [ ] **Step 1 : Ajouter le require** (`multi_edit`) — remplacer exactement :
```luau
local Pricing = require(Shared.Config.Pricing)
local Crafts = require(Shared.Config.Crafts)
```
par :
```luau
local Pricing = require(Shared.Config.Pricing)
local Crafts = require(Shared.Config.Crafts)
local Upgrades = require(Shared.Config.Upgrades)
```

- [ ] **Step 2 : Modifier le calcul du gain** (`multi_edit`) — remplacer exactement :
```luau
	local earned = math.floor(unit * n * (1 + Crafts.bonus(d, "sellMult")) + 0.5) -- Fonderie craft boosts sell value
```
par :
```luau
	local earned = math.floor(unit * n * (1 + Crafts.bonus(d, "sellMult") + Upgrades.sellBonus(d.upgrades)) + 0.5) -- Fonderie craft + Prix de Revente (Amélios)
```

- [ ] **Step 3 : Relire** `InventoryService` (require en tête + ligne ~67) pour confirmer.

- [ ] **Step 4 : Boot propre + smoke vente** — `start_stop_play(true)`, `get_console_output` (aucune erreur `InventoryService`). Puis, côté Client : se faire créditer du scrap admin, acheter quelques niveaux de **Prix de Revente**, remplir le tas (`AdminEvent:FireServer("fillJunk")`), vendre au robot, et constater un gain plus élevé qu'au niveau 0 (chaque niveau = +4 %). Repasser en Edit (`start_stop_play(false)`).

---

## Task 6 : Checkpoint d'intégration + persistance

- [ ] **Step 1 : Vérification d'ensemble** — `start_stop_play(true)`, `get_console_output` : démarrage propre (services/contrôleurs OK, 0 erreur). Ouvrir l'onglet **Amélios** → les **14 améliorations** s'affichent (liste plate) et le bouton `AMÉLIORER $coût` débite et incrémente le niveau pour chacune (tester au moins `luck`, `grab_speed`, `sell_mult`, plus une « mécanique » non encore câblée comme `crit_master` — l'achat doit marcher même si l'effet n'est pas encore actif). Repasser en Edit.

- [ ] **Step 2 : Compat saves** — vérifier qu'un profil existant (Mock ProfileStore en Studio) se charge sans erreur : `Reconcile` ajoute les 12 nouveaux ids à 0 et conserve `luck`/`grab_speed`. (Observer la console au join ; aucune erreur de shape.)

- [ ] **Step 3 : Persistance** — ⚠️ Prévenir l'utilisateur : *« Phase 1 vérifiée — sauvegarde la place (Ctrl+S) pour persister dans build.rbxlx. »* (Pas de commit git dans ce projet.)

---

## Self-Review (rempli)

- **Couverture spec §B/§F/§I (Phase 1)** : modèle de données `Upgrades` (Task 2) ✓ · `Types.UpgradeDef` (Task 1) ✓ · `PROFILE_TEMPLATE` complet (Task 3) ✓ · stats simples câblées dans `CatchService` (Task 4) ✓ · `sell_mult` dans `InventoryService` (Task 5) ✓ · UI inchangée/liste plate par défaut (noté) ✓. Les 7 mécaniques (crit/yield/magnet/recycler_pro/vault/offline/bulk_bonus) ont leurs défs (Task 2) mais effets reportés → phases 2-3 (roadmap ci-dessous).
- **Placeholders** : aucun — chaque étape porte le code/commande exact.
- **Cohérence des noms** : `applyAccountStats`, `sellBonus`, `costFor`, `effectFor`, `FAMILIES`, `effectKind`, ids `luck/quality/modifiers/crit_master/grab_speed/multi_grab/weight_cap/sell_mult/yield/bulk_bonus/magnet/recycler_pro/vault/offline` — identiques entre la déf (Task 2), le template (Task 3), les consommateurs (Tasks 4-5) et les tests.

---

## Roadmap — phases suivantes (plans à écrire à pleine fidélité au moment venu)

Chaque phase devient un fichier `docs/superpowers/plans/2026-06-16-economy-rework-0N-*.md`, à détailler une fois la précédente posée (les hooks exacts dépendent de l'état réel du code).

- **02 — Mécaniques actives** (`crit_master`, `yield`) : dans `CatchService.doGrab` — crit = grant cash instantané `floor(unit·(critMult−1)·(1+sellMultTotal))` + payload `catch.crit` + FX `CatchFXController` ; yield = chance `0.03·level` d'ajouter une copie du butin vedette. Vérif live (crit forcé haut, observer grant + FX).
- **03 — Automatisation & passif** (`magnet`, `vault`, `offline`, `recycler_pro`) : nouveau `AutomationService` (boucle par joueur : aimant = auto-vente d'une fraction du tas selon `params` ; coffre = intérêts /60 s plafonnés) ; `offline` dans `DataService.onReady` + EMA `data.stats.avgIncomePerSec` dans `InventoryService` ; `recycler_pro` lu par `MachineService`.
- **04 — Parts → $** : `Machines.recycler.output = "scrap"` + `MachineService` ; masquer `PartsDisplay` (`UIController.updateCurrency`) ; palier codex `CollectionService` en `$`.
- **05 — Refonte UI Amélios** : rendu groupé par famille (nouveau contrôleur type `IndexController`) + juice ; sous-section crafts conservée.
- **06 — Rééquilibrage + vérif rythme** : `PlotLayout` (unlockCost lissés), `ShopService` (`priceOf` exposant 2.4, `SHOP_LUCK` cap 12) ; script de simulation `execute_luau` confrontant les temps-jusqu'aux-jalons au tableau §A, ajuster bases/growth.
