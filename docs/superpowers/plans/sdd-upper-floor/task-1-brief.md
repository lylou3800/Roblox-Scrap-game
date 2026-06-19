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

