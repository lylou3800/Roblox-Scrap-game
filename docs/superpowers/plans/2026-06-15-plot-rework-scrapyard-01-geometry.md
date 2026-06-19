# Plot Rework « Scrapyard » — Plan 01 : Géométrie 8 zones

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task (inline-in-Studio chosen). Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Spec source:** `C:\Users\farhi\.claude\plans\quizzical-scribbling-horizon.md` · **Série :** 1/6 (Géométrie → Matériaux → Machines → Tapis → Boucle physique → Déblocage/migration/nettoyage).

**Goal:** Remplacer la dalle « 4 pinces en rangée + 2 slots machine » par le layout cible **8 zones-machines encadrées** (2 colonnes de 4 le long d'une allée centrale) + ancres avant pour **gros tas (gauche)**, **vendeur (droite)**, **filtre** et **spawn avant-centre** — sans casser les systèmes existants (machines, FX, UI).

**Architecture:** Tout est construit au runtime par `PlotService.buildPlot` à partir de `PlotLayout`. On étend `PlotLayout` à 8 slots + nouveaux offsets, on ajoute la géométrie de cadre par zone + des ancres-placeholder à l'avant dans `buildPlot`, et on étend `PROFILE_TEMPLATE` à 8 slots (`ProfileStore:Reconcile()` propage s5-s8 aux sauvegardes existantes). `refreshSlot` est déjà data-driven (boucle `PlotLayout.slotById` + `data.plot.slots`) → fonctionne pour 8 sans modification.

**Tech Stack:** Roblox / Luau ; source vivante dans `build.rbxlx` (source de vérité) ; édition + build + vérif via MCP Roblox Studio (`script_read`/édition de Source, `execute_luau`, `inspect_instance`, `screen_capture`, `start_stop_play`, `get_console_output`). **Pas de framework de test ni de git** → « tests/commit » = vérif Studio + sauvegarde `.rbxlx`.

> ⚠️ **Toutes les éditions de Source se font en mode Edit** (le mode Play est éphémère, les modifs n'y persistent pas). On bascule en Play seulement pour vérifier le runtime, puis on revient en Edit.

---

## File Structure

| Fichier (chemin game-tree) | Responsabilité | Changement |
|---|---|---|
| `ReplicatedStorage.Shared.Config.PlotLayout` | Constantes de géométrie du plot | **Réécriture** : 8 slots + offsets tas/vendeur/filtre + spawn + tailles de zone + waypoints tapis ; champs hérités marqués DEPRECATED mais conservés |
| `ServerScriptService.Server.Services.PlotService` | Construit le plot au runtime | **`buildPlot`** : cadre de zone par slot (boucle existante), ancres avant (tas/filtre), `SellPad` repositionné = ancre vendeur ; `Tray` conservé |
| `ReplicatedStorage.Shared.Config.GameConfig` | `PROFILE_TEMPLATE` | Ajouter `s5..s8` (verrouillés) à `plot.slots` |

**Repère de coordonnées (local plot)** : `front = -Z` (face au hub), `back = +Z`. Le joueur spawn à l'avant et regarde +Z → **gauche joueur = +X**, **droite joueur = -X** (cohérent avec l'ancien `sellOffset` -X = droite et `rouletteOffset` +X = gauche).

---

## Task 1 : Réécrire `PlotLayout` (8 zones + offsets avant)

**Files:** Modify `ReplicatedStorage.Shared.Config.PlotLayout` (remplacer tout le module)

- [ ] **Step 1 :** Remplacer le Source complet du module par :

```lua
--!strict
-- PlotLayout.luau — geometry config for the player plot (Scrapyard rework: 8 zones).
-- Local convention: front = -Z (faces hub), back = +Z. Player spawns front, faces +Z,
-- so player's LEFT = +X, player's RIGHT = -X.
local PlotLayout = {
	plotSize = Vector3.new(128, 1, 128),
	gridSpacing = 64,
	perRow = 4,
	rowSpacingX = 192,
	rowOffsetZ = 144,

	baseColor = Color3.fromRGB(158, 156, 150),
	slotColor = Color3.fromRGB(120, 200, 240),
	lockedSlotColor = Color3.fromRGB(150, 150, 162),

	aisleHalfWidth = 12,                 -- aisle spans local X in [-12, 12]
	zoneSize = Vector3.new(42, 1, 20),   -- framed bay footprint (around each slot)
	zoneWallHeight = 5,

	-- 8 machine zones: 2 columns x 4. s1-s4 = LEFT (+X), s5-s8 = RIGHT (-X), front -> back.
	slots = {
		{ id = "s1", offset = Vector3.new(34, 0, -18), tier = 1, unlockCurrency = "scrap", unlockCost = 0 },
		{ id = "s2", offset = Vector3.new(34, 0, 4),   tier = 1, unlockCurrency = "scrap", unlockCost = 0 },
		{ id = "s3", offset = Vector3.new(34, 0, 26),  tier = 2, unlockCurrency = "scrap", unlockCost = 300 },
		{ id = "s4", offset = Vector3.new(34, 0, 48),  tier = 3, unlockCurrency = "scrap", unlockCost = 900 },
		{ id = "s5", offset = Vector3.new(-34, 0, -18), tier = 2, unlockCurrency = "scrap", unlockCost = 2500 },
		{ id = "s6", offset = Vector3.new(-34, 0, 4),   tier = 3, unlockCurrency = "scrap", unlockCost = 6000 },
		{ id = "s7", offset = Vector3.new(-34, 0, 26),  tier = 4, unlockCurrency = "scrap", unlockCost = 15000 },
		{ id = "s8", offset = Vector3.new(-34, 0, 48),  tier = 5, unlockCurrency = "scrap", unlockCost = 40000 },
	},

	-- Front-strip fixtures (pile LEFT, vendor RIGHT).
	spawnOffset     = Vector3.new(0, 5, -54),
	pileOffset      = Vector3.new(40, 0, -48),
	vendorOffset    = Vector3.new(-40, 0, -48),
	filterOffset    = Vector3.new(56, 0, -42),
	nameplateOffset = Vector3.new(0, 22, 60),

	-- Conveyor waypoints (local). Consumed in Plan 03; declared here so layout owns them.
	conveyorLeft  = { Vector3.new(13, 0.7, 56), Vector3.new(13, 0.7, -40), Vector3.new(34, 0.7, -46) },
	conveyorRight = { Vector3.new(-13, 0.7, 56), Vector3.new(-13, 0.7, -40), Vector3.new(34, 0.7, -46) },

	-- DEPRECATED (kept so MachineService/CatchFXController/UIController don't break before Plans 03/05):
	machineSlots = {
		{ id = "m1", offset = Vector3.new(-22, 0, 32) },
		{ id = "m2", offset = Vector3.new(22, 0, 32) },
	},
	trayOffset = Vector3.new(0, 0, -44),   -- CatchFXController anchor until Plan 03
	sellOffset = Vector3.new(-40, 0, -48), -- aligned to vendor; UIController until Plan 05
	shopOffset = Vector3.new(56, 0, 12),
	rouletteOffset = Vector3.new(36, 0, -94), -- unchanged (off-slab roulette)
}
local slotById = {}
for _, s in ipairs(PlotLayout.slots) do slotById[s.id] = s end
PlotLayout.slotById = slotById
return PlotLayout
```

- [ ] **Step 2 :** Vérifier qu'il n'y a pas d'erreur de syntaxe — `execute_luau` (Edit) :

```lua
local ok, m = pcall(require, game.ReplicatedStorage.Shared.Config.PlotLayout)
return ok, type(m) == "table" and #m.slots or m
```
Attendu : `true, 8`.

---

## Task 2 : `buildPlot` — cadres de zone (boucle slots)

**Files:** Modify `ServerScriptService.Server.Services.PlotService` (boucle slots actuelle, lignes ~407-431)

- [ ] **Step 1 :** Remplacer le bloc « Slot pads … » (de `-- Slot pads, each on a glowing mount ring …` jusqu'à la fin du `for … ipairs(PlotLayout.slots)`) par la boucle qui ajoute le **cadre de zone** + conserve l'anneau + pad :

```lua
	-- Machine zones: a framed industrial bay per slot (floor + corner posts + back wall + number),
	-- plus the glowing mount ring + Slot pad at the bay centre (the claw stands here).
	local padBySlot: { [string]: BasePart } = {}
	for i, slotDef in ipairs(PlotLayout.slots) do
		local zc = slotDef.offset
		local zs = PlotLayout.zoneSize
		local wh = PlotLayout.zoneWallHeight

		local floor = makePart("ZoneFloor_" .. slotDef.id, Vector3.new(zs.X, 0.4, zs.Z),
			Color3.fromRGB(96, 98, 104), origin * CFrame.new(zc + Vector3.new(0, 0.4, 0)), model)
		floor.Material = Enum.Material.DiamondPlate
		floor.CanCollide = false

		for _, sx in ipairs({ -1, 1 }) do
			for _, sz in ipairs({ -1, 1 }) do
				local post = makePart("ZonePost_" .. slotDef.id, Vector3.new(1.2, wh, 1.2),
					Color3.fromRGB(60, 64, 72),
					origin * CFrame.new(zc + Vector3.new(sx * (zs.X / 2 - 0.6), wh / 2, sz * (zs.Z / 2 - 0.6))),
					model)
				post.Material = Enum.Material.Metal
			end
		end

		local backZ = zs.Z / 2 - 0.4
		local wall = makePart("ZoneWall_" .. slotDef.id, Vector3.new(zs.X, wh, 0.6),
			Color3.fromRGB(72, 76, 84), origin * CFrame.new(zc + Vector3.new(0, wh / 2, backZ)), model)
		wall.Material = Enum.Material.Metal

		local sign = makePart("ZoneSign_" .. slotDef.id, Vector3.new(0.2, 0.2, 0.2), Color3.new(1, 1, 1),
			origin * CFrame.new(zc + Vector3.new(0, wh + 1.2, backZ)), model)
		sign.Transparency = 1; sign.CanCollide = false
		local zbb = Instance.new("BillboardGui"); zbb.Size = UDim2.fromScale(4, 2); zbb.AlwaysOnTop = true; zbb.Parent = sign
		local ztl = Instance.new("TextLabel"); ztl.Size = UDim2.fromScale(1, 1); ztl.BackgroundTransparency = 1
		ztl.TextScaled = true; ztl.Font = Enum.Font.GothamBlack; ztl.Text = "ZONE " .. i
		ztl.TextColor3 = Color3.fromRGB(255, 210, 90); ztl.TextStrokeTransparency = 0.3; ztl.Parent = zbb

		local ring = makePart("SlotRing_" .. slotDef.id, Vector3.new(0.4, 7.6, 7.6),
			Color3.fromRGB(95, 180, 230),
			origin * CFrame.new(zc + Vector3.new(0, 0.48, 0)) * CFrame.Angles(0, 0, math.rad(90)), model)
		ring.Shape = Enum.PartType.Cylinder; ring.Material = Enum.Material.Neon; ring.CanCollide = false

		local pad = makePart("Slot_" .. slotDef.id, Vector3.new(6, 1, 6), PlotLayout.lockedSlotColor,
			origin * CFrame.new(zc + Vector3.new(0, 0.6, 0)), model)
		pad.Material = Enum.Material.Plastic
		pad:SetAttribute("SlotId", slotDef.id)
		padBySlot[slotDef.id] = pad
	end
```

---

## Task 3 : `buildPlot` — ancres avant (tas / filtre) + `SellPad` = vendeur

**Files:** Modify `ServerScriptService.Server.Services.PlotService`

- [ ] **Step 1 :** Dans le bloc `SellPad` (lignes ~391-405), remplacer `PlotLayout.sellOffset` par `PlotLayout.vendorOffset` partout (SellPad, SellGlow, SellSign), et ajouter après la création de `sellPad` : `sellPad:SetAttribute("IsVendor", true)`. (Le `SellPad` devient le marqueur de la zone vendeur ; UIController continue de le trouver. Le robot vendeur le remplacera au Plan 05.)

- [ ] **Step 2 :** Juste avant `-- Owner nameplate.`, ajouter les ancres placeholder (remplacées par la vraie géométrie aux Plans 04/05) :

```lua
	-- Front-strip anchors (placeholders; full geometry in Plans 04/05).
	local pile = makePart("PileAnchor", Vector3.new(16, 1, 16), Color3.fromRGB(120, 110, 90),
		origin * CFrame.new(PlotLayout.pileOffset + Vector3.new(0, 0.6, 0)), model)
	pile.Material = Enum.Material.Slate
	pile:SetAttribute("IsPile", true)

	local filter = makePart("FilterAnchor", Vector3.new(4, 3, 1), Color3.fromRGB(150, 150, 90),
		origin * CFrame.new(PlotLayout.filterOffset + Vector3.new(0, 1.5, 0)), model)
	filter.Material = Enum.Material.Metal
	filter:SetAttribute("IsFilter", true)
```

- [ ] **Step 3 :** Laisser le `Tray` tel quel (déplacé via `trayOffset` mis à jour dans PlotLayout) — CatchFXController s'en sert jusqu'au Plan 03. Ne rien retirer d'autre.

---

## Task 4 : `PROFILE_TEMPLATE` → 8 slots

**Files:** Modify `ReplicatedStorage.Shared.Config.GameConfig` (lignes ~40-45)

- [ ] **Step 1 :** Remplacer la table `slots` de `PROFILE_TEMPLATE.plot` par :

```lua
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
```
(`Reconcile()` ajoutera s5-s8 aux profils existants au prochain chargement.)

---

## Task 5 : Build & vérif runtime dans Studio

- [ ] **Step 1 — Sauver l'Edit :** s'assurer que les 3 éditions sont en mode **Edit**, puis sauvegarder le place (Studio `.rbxlx`).

- [ ] **Step 2 — Lancer le Play :** `start_stop_play` → mode Play (Server+Client). Le joueur local rejoint → `assignPlot` construit `Plot_<UserId>`.

- [ ] **Step 3 — Vérifier la présence des 8 zones :** `inspect_instance` sur `Workspace.Plot_<UserId>` (datamodel Server) → confirmer : `Base`, `BaseRim`, `Tray`, `SellPad`(IsVendor), `PileAnchor`(IsPile), `FilterAnchor`(IsFilter), `Nameplate`, et pour chaque `s1..s8` : `ZoneFloor_*`, `ZonePost_*` (×4), `ZoneWall_*`, `ZoneSign_*`, `SlotRing_*`, `Slot_*`.

- [ ] **Step 4 — Vérifier le non-chevauchement / dans la dalle :** `execute_luau` (Server) qui calcule les bounding boxes locales et vérifie qu'aucune zone ne sort de ±64 ni n'en chevauche une autre :

```lua
local plot
for _, m in ipairs(workspace:GetChildren()) do
	if m:GetAttribute("OwnerUserId") then plot = m break end
end
local origin = plot.PrimaryPart.CFrame * CFrame.new(0, 0.2, 0) -- approx plot origin at y=0
local report = {}
for _, p in ipairs(plot:GetDescendants()) do
	if p:IsA("BasePart") and (p.Name:match("^ZoneFloor_") or p.Name:match("^Slot_")
		or p.Name == "PileAnchor" or p.Name == "VendorAnchor" or p.Name == "SellPad") then
		local lp = origin:PointToObjectSpace(p.Position)
		table.insert(report, string.format("%s  x=%.1f z=%.1f  (sx=%.1f sz=%.1f)",
			p.Name, lp.X, lp.Z, p.Size.X, p.Size.Z))
	end
end
return table.concat(report, "\n")
```
Attendu : chaque `|x| + sx/2 <= 64` et `|z| + sz/2 <= 64` ; les ZoneFloor des 2 colonnes ne se recouvrent pas (gap en X autour de l'allée, gap en Z entre zones).

- [ ] **Step 5 — Vérif visuelle :** `screen_capture` (Client) depuis le spawn → 8 zones encadrées en 2 colonnes, allée centrale dégagée, **tas (gris/slate) à gauche**, **vendeur (vert) à droite**, panneaux « ZONE 1..8 ». Capturer aussi une vue de dessus.

- [ ] **Step 6 — Vérif interactions slots :** confirmer (visuel/prompts) que s1 porte la pince de départ, s2 affiche « Place UFO » (déverrouillé/vide), s3-s8 affichent « Unlock (coût scrap) ».

- [ ] **Step 7 — Console propre :** `get_console_output` → aucune erreur `PlotService`/`PlotLayout`/`Reconcile`.

- [ ] **Step 8 — Revenir en Edit :** `start_stop_play` → Edit. (Les modifs de Source étaient déjà en Edit ; rien à re-sauver côté code.)

- [ ] **Step 9 — Checkpoint utilisateur :** présenter les captures et le rapport bounding-box, valider avant d'enchaîner sur le Plan 02 (Matériaux).

---

## Notes transitionnelles (assumées jusqu'aux plans suivants)

- **Recycleur** (si présent dans une sauvegarde) se construit encore à `machineSlots` m1/m2 → peut chevaucher une zone. Sans incidence sur un **profil neuf** (aucun recycleur). Nettoyé au **Plan 06**.
- **PlotPreviews** (Edit) montrent encore l'ancien layout (détruits au runtime). Régénération optionnelle au Plan 06 ; en attendant, vérifier en **Play**.
- **Tray / SellPad** conservés volontairement (consommés par CatchFXController/UIController) ; remplacés/retirés aux Plans 03/05.

## Self-Review

- **Couverture spec (périmètre Géométrie)** : 8 zones 4/côté ✓ (Task 1/2) ; allée centrale ✓ (offsets x=±34, aisleHalfWidth) ; tas gauche / vendeur droite ✓ (Task 3) ; spawn avant-centre ✓ ; ancre filtre ✓ ; non-chevauchement vérifié ✓ (Task 5 Step 4). Pioche/feedback/tapis/boucle/matériaux = hors périmètre (Plans 02-06).
- **Placeholders** : aucun TODO/TBD ; tout le code des steps est complet (modules entiers ou blocs exacts).
- **Cohérence des noms** : champs `id/offset/tier/unlockCurrency/unlockCost` identiques à l'usage dans `refreshSlot`/`handleUnlock` ; `slotById` reconstruit ; `PROFILE_TEMPLATE` clés `s1..s8` = `PlotLayout.slots` ids ; attributs `IsPile/IsVendor/IsFilter/SlotId` cohérents avec la vérif Task 5.
- **Risque** : le rapport bounding-box utilise `plot.PrimaryPart` (= `Base`) comme proxy d'origine — suffisant pour un contrôle relatif ; les valeurs sont déjà calées dans la dalle par construction.
