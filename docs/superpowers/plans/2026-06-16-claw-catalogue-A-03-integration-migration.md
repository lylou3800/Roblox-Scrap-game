# Catalogue de pinces 120 — A-03 : Intégration & migration — Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Boucler le sous-projet A : **migration sans perte** des sauvegardes (ancien rang 5 → nouveau rang 10) + réservation du champ `stars`, et **vérifier** que les consommateurs du catalogue (CatchService, ShopService, FX) tournent correctement sur la plage étendue (12 tiers × 10 rangs, fxTier 0-7).

**Architecture :** L'essentiel des consommateurs est **déjà compatible** (vérifié en Edit) : `CatchService.rollLoot` consomme déjà `specialEfficiency.rarity` et son rarity-gate `clamp(clawTier+1,1,10)` borne déjà les tiers 11/12 ; `ShopService.priceOf` reste fini/raisonnable. La **seule vraie addition de code** est une **migration one-shot** dans `DataService` (gate `meta.clawSchema`).

**Tech Stack :** Roblox / Luau, mode **Edit**. Tests `execute_luau` + Play. Pas de git → Ctrl+S.

**Dépend de A-01** (catalogue 120, `get()` tolérant) **et A-02** (visuel). Peut se faire après A-01 seul si A-02 n'est pas prêt (la migration ne touche pas au visuel).

---

## Task 1 : Migration one-shot des sauvegardes (`DataService`)

**Files:** Modify `ServerScriptService.Server.Services.DataService` (insérer après le bloc legacy-remap, l.95)

- [ ] **Step 1 :** Juste après le bloc `do ... end` de remap legacy (qui se termine à l'actuelle **l.95**, avant `profile.OnSessionEnd:Connect`), **insérer** :
```lua
	-- Migration one-shot vers le catalogue 120 (12x10) : l'ancien "rang 5 = meilleur du tier"
	-- devient le nouveau "rang 10 = meilleur" ; rangs 1..4 repartis. Gate par meta.clawSchema
	-- (absent/0 = ancien schema "5 rangs"). NE PAS mettre clawSchema dans le PROFILE_TEMPLATE :
	-- Reconcile le remplirait et on sauterait la migration a tort. La passe est idempotente
	-- (s'execute une seule fois par profil) donc les pinces neuves rang 1..5 ne sont jamais retouchees.
	do
		local d = profile.Data
		local CLAW_SCHEMA = 2
		if (d.meta.clawSchema or 0) < CLAW_SCHEMA then
			local RANK_REMAP_5_TO_10 = { [1] = 1, [2] = 3, [3] = 5, [4] = 7, [5] = 10 }
			if d.ufos then
				for _, owned in pairs(d.ufos) do
					local rarityId, rankStr = string.match(owned.defId or "", "^(.+)_(%d+)$")
					local rank = rankStr and tonumber(rankStr)
					if rarityId and rank and RANK_REMAP_5_TO_10[rank] then
						owned.defId = rarityId .. "_" .. RANK_REMAP_5_TO_10[rank]
					end
					owned.stars = owned.stars or 1 -- reserve la fusion (sous-projet B)
				end
			end
			d.meta.clawSchema = CLAW_SCHEMA
		end
	end
```

- [ ] **Step 2 : Relire** `DataService` autour de l'insertion (`script_read`) pour confirmer l'ordre : Reconcile (l.80) → legacy-remap → **migration clawSchema** → OnSessionEnd.

- [ ] **Step 3 : Test — migration idempotente** (`execute_luau`, simulate une donnée joueur) :
```lua
local function migrate(d)
	local CLAW_SCHEMA = 2
	if (d.meta.clawSchema or 0) < CLAW_SCHEMA then
		local R = { [1]=1,[2]=3,[3]=5,[4]=7,[5]=10 }
		for _, owned in pairs(d.ufos) do
			local rarityId, rankStr = string.match(owned.defId or "", "^(.+)_(%d+)$")
			local rank = rankStr and tonumber(rankStr)
			if rarityId and rank and R[rank] then owned.defId = rarityId.."_"..R[rank] end
			owned.stars = owned.stars or 1
		end
		d.meta.clawSchema = CLAW_SCHEMA
	end
end
local d = { meta = {}, ufos = { a={defId="legendary_5",level=1}, b={defId="common_1",level=1}, c={defId="rare_4",level=1} } }
migrate(d)
assert(d.ufos.a.defId == "legendary_10", "ancien rang 5 -> 10, got "..d.ufos.a.defId)
assert(d.ufos.b.defId == "common_1", "rang 1 inchange")
assert(d.ufos.c.defId == "rare_7", "rang 4 -> 7, got "..d.ufos.c.defId)
assert(d.ufos.a.stars == 1 and d.meta.clawSchema == 2, "stars + flag")
-- idempotence : un 2e passage ne doit RIEN changer (une pince neuve rang 3 reste rang 3)
d.ufos.x = { defId = "epic_3", level = 1 }
migrate(d)
assert(d.ufos.a.defId == "legendary_10" and d.ufos.x.defId == "epic_3", "2e passage no-op (gate)")
print("A-03 Task1 OK : migration rang 5->10, stars, idempotente")
```
Attendu : `A-03 Task1 OK : ...`.

- [ ] **Step 4 :** En Studio (Mock ProfileStore), pour valider de bout en bout : si possible, injecter un profil de test avec `ufos = { u1 = { defId="legendary_5", level=1 } }` **avant** chargement, rejoindre, puis vérifier que la pince est devenue `legendary_10` et placée correctement. (Sinon, le test unitaire Step 3 couvre la logique.)

- [ ] **Step 5 : Ctrl+S.**

---

## Task 2 : Réservation `stars` dans le template + commentaire

**Files:** Modify `ReplicatedStorage.Shared.Config.GameConfig`

- [ ] **Step 1 :** Mettre à jour le commentaire de `ufos` dans `PROFILE_TEMPLATE` (l.51) pour documenter `stars` :
Remplacer :
```lua
	ufos = {}, -- [uid] = { defId, level }
```
par :
```lua
	ufos = {}, -- [uid] = { defId, level, stars } ; stars = niveau de fusion (sous-projet B), defaut 1
```
*(Pas de défaut par-uid à ajouter : `ufos` démarre vide ; `stars` est posé au grant et par la migration A-03 Task1.)*

- [ ] **Step 2 : Ctrl+S.**

---

## Task 3 : Vérifier `CatchService` (specialEfficiency + rarity-gate) — lecture seule

**Files:** (vérification, aucune modification attendue) `ServerScriptService.Server.Services.CatchService`

- [ ] **Step 1 :** Relire `CatchService` l.100-125 : confirmer que `rollLoot` lit `stats.specialEfficiency` et teste `se.rarity == "all" or Rarities.get(se.rarity)` (déjà le cas). **Aucune modification** : la forme `{rarity,mult}` produite par A-01 est consommée correctement.
- [ ] **Step 2 :** Confirmer le rarity-gate `rarityPoolFor` : `maxOrder = math.clamp(clawTier + 1, 1, 10)`. Pour les tiers 11/12 (raretés primordial/eternal), `clamp` → 10 → accès à **toutes** les raretés loot. OK (comportement voulu, pas de crash).
- [ ] **Step 2b :** Si — et seulement si — une incohérence est trouvée (p.ex. un `se.family` résiduel quelque part), l'aligner sur `.rarity`. Sinon, ne rien toucher.
- [ ] **Step 3 : Test — effectiveStats propage specialEfficiency** (`execute_luau`) :
```lua
local U = require(game.ReplicatedStorage.Shared.Config.UFOCatchers)
local apex = U.get("transcendent_10")
assert(apex.stats.specialEfficiency and apex.stats.specialEfficiency.rarity == "all", "apex universel")
local spec = U.get("legendary_9")
assert(spec.stats.specialEfficiency and spec.stats.specialEfficiency.rarity == "divine", "specialist -> divine")
local plain = U.get("common_1")
assert(plain.stats.specialEfficiency == nil, "rang 1 sans specialEfficiency")
print("A-03 Task3 OK : specialEfficiency {rarity} present sur les bons rangs")
```
Attendu : OK.

---

## Task 4 : Vérifier `ShopService.priceOf` sur la plage étendue — lecture seule

**Files:** (vérification) `ServerScriptService.Server.Services.ShopService`

- [ ] **Step 1 : Test — prix finis & croissants** (`execute_luau`, réplique de la formule l.55-59) :
```lua
local U = require(game.ReplicatedStorage.Shared.Config.UFOCatchers)
local function priceOf(def) local t=def.tier or 1; local r=def.rank or 1; return math.floor(100*(t^2)*(1+0.3*(r-1))+0.5) end
local pmin = priceOf(U.get("common_1"))
local pmax = priceOf(U.get("eternal_10"))
assert(pmin == 100, "common_1 = 100$")
assert(pmax < 1e7 and pmax > 0, "eternal_10 prix fini raisonnable: "..pmax) -- ~53 280
-- croissance par rang au sein d'une rarete
assert(priceOf(U.get("legendary_10")) > priceOf(U.get("legendary_1")), "prix monte avec le rang")
print("A-03 Task4 OK : prix min "..pmin.." max "..pmax.." (finis, croissants)")
```
Attendu : `A-03 Task4 OK : prix min 100 max 53280 ...`.
- [ ] **Step 2 :** Décision tunable : si le prix max (~53k$) est jugé trop bas/haut vs l'économie, ajuster la constante de `priceOf` (l.58) — **optionnel**, à valider avec l'utilisateur. Par défaut : **ne pas changer**.

---

## Task 5 : Vérifier les FX `fxTier` 6/7 — Play

**Files:** (vérification) `CatchFXController` + rendu `ClawModel` (A-02)

- [ ] **Step 1 :** En Play, faire apparaître/placer une pince `primordial_*` (fxTier 6) et `eternal_*` (fxTier 7). Confirmer que l'aura/particules (gérées par `ClawModel` via les formules `fxTier >= 3`) rendent **plus intensément** sans erreur, et que `CatchFXController.animateWorld` (spin WarnLight / pulse Glow) tourne. `screen_capture`.
- [ ] **Step 2 :** Déclencher un **catch** avec une de ces pinces : confirmer que les FX de catch (`CatchFXController`) ne plantent pas (ils sont keyés par rareté/intensité de loot, indépendants de `fxTier` — donc rien à changer, juste vérifier). `get_console_output` propre.

---

## Task 6 : Vérification d'intégration A (bout en bout)

**Files:** aucun (Play).

- [ ] **Step 1 :** En Play, via l'admin (lylou38000) / la roulette : **roll** plusieurs fois et confirmer l'obtention d'ids valides sur les **12 raretés** (forcer si besoin via `getByRarityRank`), la bannière « NOUVELLE PINCE ! », et l'affichage roulette (mini-preview `makePrize`) avec le **nouveau visuel**.
- [ ] **Step 2 :** Placer des pinces de divers (rareté, rang) sur les slots ; confirmer catch + hologramme + jaws (Motor6D) OK, **zéro scintillement** caméra qui tourne.
- [ ] **Step 3 :** Ouvrir l'**index** actuel (`IndexBtn`) : il liste désormais 120 pinces (toggle scrap/ufo marche encore) — sans erreur. *(Le rework visuel de l'index = sous-projet C.)*
- [ ] **Step 4 : `get_console_output`** : aucune erreur. **Ctrl+S** final → sous-projet A terminé.

---

## Self-Review

1. **Couverture spec §7 (migration, stars)** : migration one-shot gate `clawSchema` (T1) + `stars` réservé (T1/T2). **§8 (intégration)** : CatchService (T3, vérif), ShopService (T4, vérif), FX 6/7 (T5), index/roulette (T6). 
2. **Placeholders** : code de migration complet + tests à sortie attendue ; les tâches « lecture seule » sont explicitement des vérifs (le code est déjà conforme, vérifié en Edit).
3. **Cohérence** : `clawSchema = 2` partout ; `RANK_REMAP_5_TO_10 = {1,3,5,7,10}` identique au test et à la tolérance `get()` de A-01 ; `stars` défaut 1 cohérent avec Types (A-01) + template (T2).
4. **Risque** : la migration ne s'exécute qu'une fois (gate) → pas de double-remap des pinces neuves rang 1..5. Vérifié par le test d'idempotence (T1 S3).
