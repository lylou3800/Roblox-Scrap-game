# Plot Rework « Scrapyard » — Plan 02 : Matériaux réutilisables (look usine)

**Série :** 2/6 (exécuté en dernier) · **Exécution :** inline Studio.

**Goal:** Introduire la **bibliothèque de matériaux réutilisable** que le joueur a demandée (« enregistrer pour réutiliser ») et appliquer un look scrapyard cohérent.

> **Permission `generate_material` non activée** → livré en **repli stylisé** (matériaux Roblox intégrés : CorrodedMetal/rouille, DiamondPlate/tôle, Concrete sale, Slate). L'architecture est prête pour le **vrai PBR** : générer des `MaterialVariant` dans `MaterialService` puis ajouter `variant = "<Nom>"` à une entrée de `Materials.byName` — `styleParts` applique `part.MaterialVariant` automatiquement. Aucun autre changement de code requis.

## Changements

### NOUVEAU `ReplicatedStorage.Shared.Config.YardPalette`
- Palette 3D centrale (steel, rust, concrete, scrap, hazardYellow, accentCyan, gold…).

### NOUVEAU `ReplicatedStorage.Shared.Config.Materials`
- `byName` : logique → `{ material, color, [variant] }` (RustySteel, ScratchedMetal, Tread, DirtyConcrete, ScrapHeap).
- `prefixMap` : nom de part → matériau logique (plus long préfixe gagnant).
- `forPart(name)`, `get(name)`, `apply(part, name)` (pose `Material`/`Color`/`MaterialVariant`).

### `ServerScriptService.Server.Services.PlotService`
- `require(Materials)` + `styleParts(model)` (post-pass par préfixe) appelé en fin de `buildPlot` → murs/poteaux = rouille, sols/tapis = tôle, base = béton sale, tas = slate. Sélectif (n'altère pas néons/anneaux/signs).

## Vérif (Play)
- Console propre ; murs/poteaux en CorrodedMetal (rouille), base béton sale, tapis tôle.
- `Materials.forPart("BaseRim")` = ScratchedMetal (longest-prefix), `"ZoneWall_s1"` = RustySteel.

## Follow-up (avec permission)
- Activer `generate_material`, générer ~6-10 MaterialVariants PBR, ajouter `variant=` à `Materials.byName`, re-bake. Optionnel : re-styliser les rigs de pince (`makeUFOModel`).
