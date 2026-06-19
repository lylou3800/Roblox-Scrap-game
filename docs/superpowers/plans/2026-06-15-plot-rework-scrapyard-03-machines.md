# Plot Rework « Scrapyard » — Plan 03 : Zones machines (pioche + feedback par machine)

**Série :** 3/6 · **Dépend de :** Plan 01 (géométrie). **Exécution :** inline Studio (MCP).

**Goal:** Donner vie aux 8 zones — un **tas de débris par zone** que la pince **fouille**, un **chunk** attrapé qui remonte, et tout le **feedback de prise déplacé AU-DESSUS de chaque machine** (fini le `Tray` central).

## Changements

### `ServerScriptService.Server.Services.PlotService` (`buildPlot`, boucle slots)
- Après le pad de slot : ajouter `DebrisPile_<id>` (mound `Ball` 7.5×3×7.5, `Slate`, CanCollide false) au centre de la zone + 4 `DebrisBit_<id>` (`CorrodedMetal`) autour. La pince (placée par `refreshSlot`) surplombe le tas et y plonge à la prise.

### `StarterPlayer.StarterPlayerScripts.Client.Controllers.CatchFXController`
- `floatingText` / `comboText` / `burst` : prennent désormais une **CFrame** (`atCF`) au lieu d'un `BasePart` (seuls appelants = `onCatch`).
- Nouveau `aboveModel(model, extra)` → CFrame au-dessus de la bounding box du rig.
- Nouveau `spawnGrabChunk(slotId, color)` → petit chunk qui remonte de la pince (~0.22s après le dip) puis fade.
- `onCatch` : ancre le feedback sur la **machine** (`getUFO(slotId)`) via `aboveModel`, sons sur `ufo.PrimaryPart` ; plus de dépendance au `Tray`. La pioche (`animateClaw` dip -3) plonge maintenant dans le tas présent.

## Vérif (Play)
- Console propre.
- Chaque prise : feedback (nom/rareté/valeur, combo, burst) **au-dessus de la pince qui a attrapé** ; chunk qui remonte ; pince qui plonge dans le tas.
- `DebrisPile_*` présents (8) et dans les zones (pas de débordement).
