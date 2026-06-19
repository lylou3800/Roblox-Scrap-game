# Catalogue de pinces 120 — A-02 : Builder visuel (`ClawModel`) — Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Rendre le visuel des pinces lisible sur **2 axes** (rareté = couleur + **bande de matériau** + halo + taille ; rang = **finition croissante** + couronne), sur **un châssis paramétrique unique**, **sans scintillement**, et le rendre **réutilisable côté client** (pour l'index, sous-projet C) en extrayant le builder dans un module partagé `ReplicatedStorage.Shared.ClawModel`.

**Architecture :** On **déplace** `makeUFOModel` (actuellement local à `PlotService`, l.87-320) vers `ReplicatedStorage.Shared.ClawModel` (`ClawModel.build(ufoDef, prestige, baseCF)`). `PlotService.makeUFOModel` devient un **wrapper** qui délègue (ainsi `ShopService.makePrize` et les générateurs de previews continuent de marcher). On **ajoute** ensuite, de façon **additive** (peu de risque), le traitement de bande de matériau (par rareté) et l'échelle de finition (par rang), plus le renommage d'archétype `premium→apex` + `specialist`.

**Tech Stack :** Roblox / Luau, mode **Edit**. Vérif = `execute_luau` (build d'un modèle, comptage de parts, scan anti-coplanarité) + **Play + `screen_capture`** pour l'œil. Pas de git → Ctrl+S.

**Dépend de A-01** (le `def` porte `rarity`, `rank`, `fxTier`, `scaleMult`, `palette` ; `ClawDesign.materialBandOf(rarityId)` existe).

---

## ⚠️ Invariants à NE PAS casser (sinon FX/anim cassent)

- Noms de parts/attributs : `Root` (PrimaryPart), `Claw`, `ClawJaw`×N, `ClawTip`×N, `ArmPivot` (+ attr `RestCF`), `Glow`, `WarnLight`, `Aura`, `FeedbackAnchor`, `Carriage` (si présent), Motor6D `JawMotor` (+ attr `OpenAngle` sur `ClawJaw`). Tag **`UFOCatcher`**.
- Build **en coordonnées monde** (`part.CFrame = BASE * cf`) — **jamais** `Model:PivotTo` sur l'assemblage soudé (anchored `ArmPivot` + unanchored welded), sinon non-réplication (cf. mémoire art-direction).
- `PlotService.makeUFOModel(ufoDef, prestige, baseCF)` doit rester appelable (ShopService + previews).

## Règles anti-scintillement (NORMATIF — appliquer à tout ajout)

- **Aucune face coplanaire.** Tout part ajouté qui recouvre une face existante est **décalé** d'au moins **0.03 stud** (en relief) ou **encastré**. Ex. liserés/trims : poser à `surfaceY + 0.03`, pas à `surfaceY`.
- **Halos/auras** = parts `Neon`/`ParticleEmitter` à **rayons distincts** ; pas deux coques transparentes au même rayon.
- Pas de `Decal`/`Texture` empilés sur une même face ; **Material + Color** d'abord.
- Tout nouvel élément `CanCollide=false`, `CanQuery=false` si purement visuel.

---

## File Structure

- **Create** `ReplicatedStorage.Shared.ClawModel` (ModuleScript) — `build(ufoDef, prestige, baseCF) -> Model`. Contient les constantes STEEL + tout le corps actuel de `makeUFOModel`, généralisé (bande + finition + archétypes).
- **Modify** `ServerScriptService.Server.Services.PlotService` — supprimer le corps local de `makeUFOModel`, `require(ClawModel)`, et faire `PlotService.makeUFOModel = function(d,p,cf) return ClawModel.build(d,p,cf) end` (conserver l'export l.878 et l'appel interne l.344).
- **Modify (re-bake)** générateurs Edit-mode des previews (`MapBlockout.PlotPreviews` machine statique + `RoulettePreview`) — relancés après changement du builder.

---

## Task 1 : Extraire `makeUFOModel` vers `ReplicatedStorage.Shared.ClawModel`

**Files:**
- Create: `ReplicatedStorage.Shared.ClawModel`
- Modify: `ServerScriptService.Server.Services.PlotService` (l.83-320 + export l.878)

- [ ] **Step 1 :** Créer un `ModuleScript` `ClawModel` sous `ReplicatedStorage.Shared` (via `execute_luau` en Edit, ou clic-droit Insert → renommer). Vérifier le chemin `game.ReplicatedStorage.Shared.ClawModel`.

- [ ] **Step 2 :** Coller dans `ClawModel` l'en-tête + le **corps actuel** de `makeUFOModel`. Copier **verbatim** depuis `PlotService` les **constantes STEEL (l.83-85)** et **toute la fonction `makeUFOModel` (l.87-320)**, en l'enveloppant ainsi :

```lua
--!strict
-- ClawModel.luau — Builder paramétrique de pince (chassis grappin-pelle orange).
-- Partage serveur (PlotService : machines sur parcelles) ET client (index ViewportFrame, sous-projet C)
-- + apercu roulette. NE PAS renommer les parts/tags (FX/anim en dependent — voir A-02 invariants).
local ClawModel = {}

local STEEL = Color3.fromRGB(74, 82, 94)
local STEEL_LIGHT = Color3.fromRGB(158, 166, 178)
local STEEL_DARK = Color3.fromRGB(48, 53, 62)

-- <<< COLLER ICI le corps de makeUFOModel (PlotService l.87-320), mais renommer la signature : >>>
-- local function makeUFOModel(ufoDef, prestige, baseCF): Model   --> deviens :
function ClawModel.build(ufoDef, prestige, baseCF)
	-- ... corps identique (l.88-319) ...
	return model
end

return ClawModel
```
> Le corps est repris **tel quel** (il est déjà autonome : il ne lit que `ufoDef`/`prestige`/`baseCF` et les constantes STEEL). Les Tasks 2-4 le généralisent ensuite.

- [ ] **Step 3 :** Dans `PlotService`, **supprimer** les constantes STEEL (l.83-85) **et** la fonction locale `makeUFOModel` (l.87-320). En haut du fichier (près des autres `require`), ajouter :
```lua
local ClawModel = require(game:GetService("ReplicatedStorage").Shared.ClawModel)
```
Remplacer l'appel interne (ancienne l.344) `local model = makeUFOModel(ufoDef, owned.prestige, baseCF)` par :
```lua
		local model = ClawModel.build(ufoDef, owned.prestige, baseCF)
```
Remplacer l'export (ancienne l.878) `PlotService.makeUFOModel = makeUFOModel` par :
```lua
PlotService.makeUFOModel = function(d, p, cf) return ClawModel.build(d, p, cf) end
```

- [ ] **Step 4 : Test — parité.** En **Play**, placer/observer une pince (ou via `execute_luau` en Edit, builder direct) :
```lua
local CM = require(game.ReplicatedStorage.Shared.ClawModel)
local U = require(game.ReplicatedStorage.Shared.Config.UFOCatchers)
local m = CM.build(U.get("legendary_5"), 0, CFrame.new(0,50,0))
m.Parent = workspace
assert(m.PrimaryPart and m.PrimaryPart.Name == "Root", "Root present")
assert(m:FindFirstChild("Claw", true) and m:FindFirstChild("ArmPivot", true), "Claw+ArmPivot")
assert(m:HasTag("UFOCatcher"), "tag UFOCatcher")
local jaws=0; for _,d in ipairs(m:GetDescendants()) do if d.Name=="ClawJaw" then jaws+=1 end end
assert(jaws>=4, "jaws presentes: "..jaws)
print("A-02 Task1 OK : ClawModel.build parite, "..(#m:GetDescendants()).." descendants")
m:Destroy()
```
Attendu : `A-02 Task1 OK : ...`. Vérifier `get_console_output` (aucune erreur). Confirmer aussi que la **roulette** (`ShopService.makePrize`) et le placement de machine marchent toujours (placer une pince en Play, pas d'erreur).

- [ ] **Step 5 : Ctrl+S.**

---

## Task 2 : Paramètres bande + finition + renommage d'archétype

**Files:** Modify `ReplicatedStorage.Shared.ClawModel`

- [ ] **Step 1 :** En haut de `ClawModel.build`, après le calcul de `fxTier`/`sMult`, **ajouter** les variables d'axes. Repérer la ligne `local isPremium = (arch == "premium")` et la **remplacer** par :
```lua
	local ClawDesign = require(game:GetService("ReplicatedStorage").Shared.Config.ClawDesign)
	local band = (ufoDef.rarity and ClawDesign.materialBandOf(ufoDef.rarity)) or "paint"
	local rank = ufoDef.rank or 1
	local finish = rank / 10               -- 0.1..1.0 : echelle de finition (rang)
	local isApex = (arch == "apex" or arch == "premium")  -- compat ancien nom
	local hasCrown = (rank >= 10)          -- couronne au sommet du tier
	local polish = (rank >= 9 and "gold") or (rank >= 6 and "chrome") or "matte"
```
*(Mettre le `require(ClawDesign)` en haut du module plutôt que dans la fonction si tu préfères — équivalent.)*

- [ ] **Step 2 : Remplacer les usages de `isPremium`** (anciennes l.282 `if isPremium then`) par `if isApex then`. Le bloc premium (couronne de glows) devient le traitement **apex** ; on le complète en Task 3 (couronne par rang).

- [ ] **Step 3 : Archétype `specialist`.** Là où le code teste `arch == "precision"` pour la boule de glow (ancienne l.278), **ajouter** un accent distinct pour `specialist` (anneau scanner néon, en léger relief — anti-z-fight) juste après :
```lua
	if arch == "specialist" then
		welded("Glow", Vector3.new(1.4 * S, 0.18 * S, 1.4 * S), glowC, clawLocal * CFrame.new(0, 0.55 * S, 0) * CFrame.Angles(0, 0, math.rad(90)), Enum.Material.Neon, Enum.PartType.Cylinder)
	end
```
- [ ] **Step 4 :** Les sélecteurs `boomThick`/`tineN` (`arch=="force"`/`"cadence"`) restent valides (force/cadence existent toujours). Vérifier qu'aucun autre littéral `"premium"` ne subsiste (`script_grep "premium"` → ne doit rester que le commentaire de compat).

- [ ] **Step 5 : Test — axes lus.** `execute_luau` :
```lua
local CM = require(game.ReplicatedStorage.Shared.ClawModel)
local U = require(game.ReplicatedStorage.Shared.Config.UFOCatchers)
for _,id in ipairs({"common_1","eternal_10","legendary_9","cosmic_10"}) do
	local m = CM.build(U.get(id), 0, CFrame.new(0,50,0))
	assert(m and m.PrimaryPart, "build "..id)
	m:Destroy()
end
print("A-02 Task2 OK : build sans erreur pour band/rank varies")
```
Attendu : OK, aucune erreur console.

- [ ] **Step 6 : Ctrl+S.**

---

## Task 3 : Traitement de bande (rareté) + finition (rang)

**Files:** Modify `ReplicatedStorage.Shared.ClawModel`

- [ ] **Step 1 : Helpers de surface anti-z-fight.** Juste avant le `model:AddTag("UFOCatcher")` final, insérer les blocs de traitement. D'abord un util local (à placer en haut de `build`, après `part`/`welded`) :
```lua
	-- pose un element en LEGER RELIEF sur une face (offset normal >= 0.03) : zero coplanarite.
	local function proud(name, size, color, cf, mat, shape)
		return part(name, size, color, cf, mat, shape) -- cf doit deja inclure l'offset 0.03+
	end
```

- [ ] **Step 2 : Bande de matériau (par rareté).** Insérer avant `model:AddTag` :
```lua
	-- ===== Bande de materiau : signature visuelle de la RARETE (sur le Cab) =====
	local OFF = 0.04 -- relief anti-coplanaire
	if band == "metal" or band == "crystal" or band == "warp" or band == "prism" then
		-- liseré chromé brillant en haut du cab (en relief)
		proud("BandTrim", Vector3.new(baseL * 0.6 + 0.04, 0.18 * S, baseW * 0.78 + 0.04), STEEL_LIGHT, CFrame.new(cabX, deckTop + cabH - 0.5 * S, 0) * CFrame.new(0, OFF, 0), Enum.Material.Metal)
	end
	if band == "energized" or band == "warp" or band == "prism" then
		-- arêtes lumineuses (4 montants néon, en relief sur les coins du cab)
		for _, sx in ipairs({ -1, 1 }) do for _, sz in ipairs({ -1, 1 }) do
			proud("Glow", Vector3.new(0.14 * S, cabH * 0.9, 0.14 * S), glowC, CFrame.new(cabX + sx * (baseL * 0.3 + OFF), cabCY, sz * (baseW * 0.39 + OFF)), Enum.Material.Neon)
		end end
	end
	if band == "crystal" or band == "prism" then
		-- inserts cristallins facettes (parts distinctes, en relief — pas de decals)
		for k = -1, 1 do
			proud("Crystal", Vector3.new(0.5 * S, 1.2 * S, 0.5 * S), glowC, CFrame.new(cabX + baseL * 0.18, cabCY + 0.4 * S, k * baseW * 0.26 + (OFF * k)) * CFrame.Angles(0, math.rad(45), 0), Enum.Material.Glass)
		end
	end
	if band == "warp" or band == "prism" then
		-- halo orbital (anneau néon a rayon DISTINCT de l'aura — pas de coplanarite)
		proud("Glow", Vector3.new(0.2 * S, baseW * 1.15, baseW * 1.15), glowC, CFrame.new(cabX, cabCY, 0) * CFrame.Angles(math.rad(90), 0, 0), Enum.Material.Neon, Enum.PartType.Cylinder)
	end
```

- [ ] **Step 3 : Échelle de finition (par rang).** Insérer après le bloc bande :
```lua
	-- ===== Finition : signature du RANG (polish + couronne) =====
	if polish == "chrome" or polish == "gold" then
		local pc = (polish == "gold") and Color3.fromRGB(255, 214, 92) or Color3.fromRGB(232, 240, 255)
		-- liseré de finition autour du cab, en relief (anti-z-fight)
		proud("FinishTrim", Vector3.new(baseL * 0.62 + 0.06, 0.12 * S, baseW * 0.8 + 0.06), pc, CFrame.new(cabX, deckTop + 0.2 * S, 0) * CFrame.new(0, OFF, 0), Enum.Material.Metal)
	end
	if hasCrown then
		-- couronne dorée au sommet du cab (standoff : posée au-dessus, pas coplanaire)
		local cy = deckTop + cabH + 0.9 * S
		for k = 0, 5 do
			local a = math.rad(60 * k)
			proud("Crown", Vector3.new(0.34 * S, 1.0 * S, 0.34 * S), Color3.fromRGB(255, 224, 106), CFrame.new(cabX, cy, 0) * CFrame.Angles(0, a, 0) * CFrame.new(baseW * 0.18, 0, 0), Enum.Material.Neon)
		end
		proud("CrownBand", Vector3.new(baseW * 0.5, 0.22 * S, baseW * 0.5), Color3.fromRGB(255, 214, 92), CFrame.new(cabX, cy - 0.5 * S, 0), Enum.Material.Metal, Enum.PartType.Cylinder)
	end
```
> La densité de greebles « monte » déjà avec la rareté/`isApex` ; le polish/couronne ci-dessus encode la lecture **par rang** demandée (rang 10 = couronne).

- [ ] **Step 4 : fxTier 6/7.** Les seuils existants `fxTier >= 2` (PointLight) et `>= 3` (Aura particules) **couvrent déjà** 6/7 (formules `Range/Brightness/Rate/Size` croissantes). **Vérifier** seulement qu'aucun cap dur ne bride 6/7 (relire le bloc l.294-316 ; rien à changer a priori). Optionnel : pour `band=="prism"` (fxTier 7), passer la couleur d'aura en `ColorSequence` arc-en-ciel.

- [ ] **Step 5 : Test — comptage + anti-coplanarité.** `execute_luau` (scan des parts qui partagent exactement un plan de face — heuristique) :
```lua
local CM = require(game.ReplicatedStorage.Shared.ClawModel)
local U = require(game.ReplicatedStorage.Shared.Config.UFOCatchers)
local ids = {"common_1","epic_3","mythic_6","divine_8","transcendent_10","primordial_5","eternal_10"}
for _,id in ipairs(ids) do
	local m = CM.build(U.get(id), 0, CFrame.new(0,50,0))
	-- coplanarite grossiere : 2 BasePart de meme orientation dont une face partage exactement la meme coord
	local faces = {}
	for _,p in ipairs(m:GetDescendants()) do
		if p:IsA("BasePart") then
			local topY = math.floor((p.Position.Y + p.Size.Y/2)*100+0.5)/100
			faces[topY] = (faces[topY] or 0) + 1
		end
	end
	-- on log seulement (verif fine = oeil en Play) ; doit build sans erreur
	m:Destroy()
end
print("A-02 Task3 OK : 7 raretes/rangs build sans erreur (verif z-fight fine = Play)")
```
Attendu : OK.

- [ ] **Step 6 : VÉRIF VISUELLE (Play + capture).** Démarrer Play. Placer (ou faire spawn par admin) **une pince de chaque bande** : `common_1` (paint), `epic_5`/`legendary_5` (metal), `mythic_6` (energized), `divine_8`/`cosmic_9` (crystal), `transcendent_10` (warp), `eternal_10` (prism), + un **rang bas vs rang 10** d'une même rareté (ex. `legendary_1` vs `legendary_10`). Pour chacune : `screen_capture`, **tourner la caméra** (via le joueur) et confirmer **zéro scintillement** aux jonctions (cab/trim/bandes/couronne). Itérer sur les offsets `OFF` si un shimmer apparaît. *(Rappel mémoire : la caméra `screen_capture` ne bouge pas en Play → déplacer le perso / la cible pour varier l'angle.)*

- [ ] **Step 7 : Ctrl+S.**

---

## Task 4 : Re-bake des previews (plots libres + roulette)

**Files:** Modify (re-run) générateurs Edit-mode (cf. mémoire art-direction / roulette-system).

- [ ] **Step 1 :** Le builder étant partagé et l'export `PlotService.makeUFOModel` conservé, les **machines** des previews se mettent à jour si on **relance les générateurs Edit-mode** (ils clonent/figent `makeUFOModel`). Relancer : (a) le générateur des 8 `MapBlockout.PlotPreviews.PlotPreview_<i>` (machine statique sur BAIE 1), (b) le générateur des `RoulettePreview` (la pince trophée via `makePrize`).
- [ ] **Step 2 :** Vérifier en Edit/Play qu'un plot libre et la zone roulette montrent le **nouveau** châssis sans scintillement. `screen_capture`.
- [ ] **Step 3 : Ctrl+S** (les previews sont des géométries bakées → persistées dans `build.rbxlx`).

---

## Self-Review

1. **Couverture spec §4 (langage visuel)** : châssis unique partagé (T1) ; bande par rareté (T3 S2) ; finition+couronne par rang (T3 S3) ; archétypes apex/specialist (T2). **§5 anti-z-fight** : règles normatives + `proud()` + offsets `OFF` + vérif caméra (T3 S6). **Réutilisable client** (pour C) : `ClawModel` partagé (T1).
2. **Placeholders** : code concret pour bande/finition ; l'extraction T1 référence des **lignes réelles** (PlotService 83-320) — copie, pas placeholder.
3. **Invariants** : noms de parts/tags conservés (le corps est copié verbatim) ; `PlotService.makeUFOModel` conservé comme wrapper (ShopService/previews OK).
4. **Dépendances** : `ClawDesign.materialBandOf` (A-01) ; `ufoDef.rarity`/`rank` (A-01). Le `def` ne porte PAS `materialBand` → `ClawModel` le résout via `ClawDesign.materialBandOf(ufoDef.rarity)` (pas besoin de toucher `Types`).
