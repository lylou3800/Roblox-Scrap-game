# Plot Rework « Scrapyard » — Plan 06 : Nettoyage, économie, migration

**Série :** 6/6 · **Dépend de :** 01-05. **Exécution :** inline Studio.

**Goal:** Finaliser « vente physique uniquement », retirer le recycleur, nettoyer le Tray, donner un look « éteint » aux zones verrouillées (power-on à l'unlock), et migrer les sauvegardes — sans toucher au gros `UIController` (approche serveur).

## Changements

### `ServerScriptService.Server.Services.InventoryService` (vente physique-only)
- Remotes `sellStack` + `sellAllJunk` → **rejet** + notif « Vente par menu desactivee - ramasse au tas et vends au robot ! ». Les **fonctions** `sellStack`/`sellFiltered` restent (utilisées par `ScrapyardService`). Les boutons menu deviennent inertes proprement (pas de crash).

### `ServerScriptService.Server.Services.MachineService` (retrait recycleur)
- `onReady` : `data.machines = {}` (clear → aucun recycleur ne se construit/tourne ; migration des saves).
- Remote `buildMachine` → rejet + notif « Le recycleur a ete retire ».

### `ServerScriptService.Server.Services.PlotService`
- Retrait du `Tray` central (feedback désormais par machine).
- `refreshSlot` : anneau de slot **éteint/gris** si verrouillé, **néon cyan** si déverrouillé → power-on visuel à l'achat.

### Migration (automatique)
- `PROFILE_TEMPLATE` a déjà `s5..s8` (Plan 01) + `sellFilter` (Plan 05) → `ProfileStore:Reconcile()` propage aux saves. `data.machines` vidé au load.

## Économie (déjà en place)
- Déblocage 8 zones via `PlotLayout.slots.unlockCost` (300/900/2.5k/6k/15k/40k) — Plan 01.

## Reporté (follow-up, non bloquant)
- Cacher visuellement les boutons de vente/recycleur dans `UIController` (actuellement neutralisés côté serveur).
- Retrait des controllers dormants `InventoryUIController`/`ShopUIController` (laissés en place, sans risque).
- Régénérer les `PlotPreviews` (Edit) au nouveau layout.

## Vérif (Play)
- Console propre.
- Menu « VENDRE TOUT » → notif « desactivee » (pas de crédit) ; vente uniquement via robot.
- Aucun recycleur sur le plot ; `buildMachine` rejeté.
- Plus de `Tray` ; zones verrouillées avec anneau éteint.
