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

