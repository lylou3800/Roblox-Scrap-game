# Plot Rework « Scrapyard » — Plan 04 : Tapis convoyeurs

**Série :** 4/6 · **Dépend de :** 01 (géométrie), 03 (machines/chunk). **Exécution :** inline Studio.

**Goal:** Des tapis visibles amènent le scrap des machines au gros tas avant-gauche, en réutilisant `ConveyorDriver` (parts taggées `"Conveyor"` + attribut `Vel` → `AssemblyLinearVelocity`).

## Changements

### `ServerScriptService.Server.Services.PlotService` (`buildPlot`, après la boucle slots)
- Helper `makeBelt(nm, lcenter, lsize, ldir)` : top `DiamondPlate` taggé `"Conveyor"` + attribut `Vel = origin:VectorToWorldSpace(ldir)` + 2 rails.
- 3 belts : `ConveyorL` (x=13, z 54→-38, Vel -Z), `ConveyorR` (x=-13, idem), `ConveyorCross` (z=-42, x -13→40, Vel +X) qui rejoint le tas (x=40).

### `StarterPlayer.StarterPlayerScripts.Client.Controllers.CatchFXController`
- `require(Shared.Config.PlotLayout)` ajouté.
- `spawnGrabChunk` (du Plan 03) → le chunk **voyage** : claw → entrée du belt de sa colonne (x=±13, z du slot) → avant du belt (z=-38) → cross-belt (x=38) → sommet du tas (40,3,-48), puis **plop** (`burst`) et destroy. Origine plot calculée depuis `Base.CFrame`, waypoints en `PointToWorldSpace` (gère la rotation 180° des plots sud).

## Vérif (Play)
- Console propre.
- `ConveyorL/R/Cross` présents + taggés `Conveyor` (Vel non nul).
- À chaque prise, le chunk suit visiblement le tapis jusqu'au tas (pas de dépendance physique : tween client, robuste).
