# Synchronisation des décors Édit ↔ Joueur — Design

**Date :** 2026-06-19
**Statut :** Spec validée, en attente de plan d'implémentation
**Source de vérité :** `build.rbxlx`

## Problème

En mode **Édit** (Studio, aucune partie lancée), le map ne contient que du décor
**statique** : `MapBlockout` (Hub, Walls, Backdrop, FactoryDecor, AvenueLights,
**PlotPreviews** = 8 maquettes des plots) + `Environment` (route, EggShop, convoyeurs…).

En mode **Joueur**, quand un joueur rejoint, plusieurs services **construisent le
décor en temps réel** par-plot, parenté à `plot.model` ancré à `plot.origin` :

1. `PlotService.buildPlot` — coque, rim, dépôt de ferraille, bays, panneau d'étage
2. `ScrapyardService` (`onPlotReady`) — NPC vendeur
3. `ShopService.buildGeometry` (`onPlotReady`) — zone Roulette (pad, arche, machine, plateformes)
4. `MachineService` (`onPlotReady`) — machines (seulement quand une pince est posée)

`PlotService.assignPlot` détruit la `PlotPreview_N` de la case réclamée puis appelle
`buildPlot`. Résultat : en Édit on ne voit que des maquettes simplifiées ; en Joueur
on voit les plots complets.

**Racine du problème :** les `PlotPreviews` sont des approximations **bakées à la
main** qui **dérivent** à chaque modification des builders (confirmé par l'historique :
« 8 PlotPreviews re-baked », « rotated to match »). D'où des décors « pas placés pareil ».

## Objectif

Que le mode Édit reflète fidèlement le rendu runtime, **sans dérive future**, en
modifiant le côté sans-joueur. Décisions de cadrage validées :

| Décision | Choix retenu |
|---|---|
| Périmètre | **Tout le décor runtime per-plot** (plots + NPC vendeur + zone roulette) |
| État représenté | **Coque vide débloquée** : structure complète, tous slots débloqués, **0 machine posée** |
| Robustesse | **Baker réutilisable anti-dérive** (source unique de géométrie) |
| Portée | **Édit Studio uniquement** — zéro impact gameplay/perf en live |
| Coexistence Édit/live | **Guard au boot** (previews simples générées au boot, `EditPreview` détruit en live) |

Hors scope : Floor 2 (on bake Floor 1 uniquement), machines posées, décor déjà
statique (EggShop, Environment, Hub, Walls…).

## Approche retenue — Injection de contexte (Approche 1)

On extrait la **géométrie/cosmétique** des builders en helpers purs paramétrés par un
petit état, appelés à la fois par le chemin **runtime** (état = données joueur) et par
le **baker** (état = « coque vide débloquée » synthétique). Runtime et baker traversent
le **même code géométrie** → fidélité **par construction**.

Approches écartées :
- **Capture de snapshot live** — c'est un snapshot qui re-dérive à chaque modif de builder.
- **Bake « faux joueur » headless** — simule tout l'environnement de service (Player,
  DataService, Net, prompts) ; fragile, effets de bord.

## Architecture

```
ReplicatedStorage/Shared
  └─ PlotBuild  (nouveau ModuleScript partagé)
       • PlotBuildContext : { ownerId, name, getSlot(slotId)->{unlocked,ufoUid}, shopLevel, … }
       • RuntimeContext(player) → lit DataService            (comportement actuel)
       • PreviewContext(index)  → défauts « coque vide débloquée »
       • helpers cosmétiques purs : applySlotVisual(pad, ring, state), …

Services refactorés pour passer par un ctx :
  PlotService      (buildPlot, refreshSlot)
  ShopService      (buildGeometry → nb plateformes via ctx.shopLevel)
  ScrapyardService (vendor NPC → builder pur (model, origin))
  MachineService   (inchangé : aucune machine en preview)

EditPreview baker (script Édit, lancé via MCP execute_luau)
  pour index 1..8 : buildPreviewPlot(index) → modèle ancré, prompts/scripts retirés
  → Workspace.MapBlockout.EditPreview.EditPreview_<index>

EditPreviewGuard (Script de boot)
  à RunService:IsRunning() : détruit EditPreview, génère les maquettes simples
```

Le baker **ne touche pas** à `assignPlot` (occupied, teleport, replicate, callbacks
restent live-only) : il appelle un nouvel orchestrateur léger `buildPreviewPlot(index)`
qui réutilise les builders via `PreviewContext`.

## Interface `BuildContext` et points de refactor

Seul changement dans les builders : remplacer les accès directs
`Registry.get("DataService")` / `player` par un `ctx`.

| Builder | Accès donnée actuel | Devient (via ctx) | En PreviewContext |
|---|---|---|---|
| `buildPlot(player, index)` | `player.UserId` (nom + attr `OwnerUserId`) | `ctx.ownerId`, `ctx.name` | `ownerId=0`, `name="EditPreview_N"` |
| `refreshSlot` → cosmétique | `slotData.unlocked` | `ctx.getSlot(id).unlocked` via helper `applySlotVisual` | `unlocked=true` |
| `refreshSlot` → machine | `slotData.ufoUid` | `ctx.getSlot(id).ufoUid` | `nil` → aucune machine |
| `ShopService.buildGeometry` | `data.shop.slotsLevel` | `ctx.shopLevel` | `0` → 1 plateforme |
| `ScrapyardService` vendor | NPC au point d'ancrage `IsVendor` | builder pur `(model, origin)` | identique |

Les **prompts** (unlock/place/upgrade) ne sont créés que par le chemin runtime de
`refreshSlot` ; le baker ne les génère pas (et les strippe par sécurité). La
géométrie/cosmétique est extraite en helpers purs pour **éviter toute duplication =
zéro dérive**.

Note d'implémentation : `buildPlot` et `buildBay` sont déjà quasi purs (géométrie
seule) ; `player` n'y sert qu'au nom et à l'attribut `OwnerUserId`. La dépendance aux
données est concentrée dans `refreshSlot` (cosmétique débloqué/verrouillé + machine) et
dans les 2 callbacks `onPlotReady` (roulette, NPC).

## Le baker — `buildPreviewPlot(index)`

1. `origin = originForIndex(index)`
2. `model = buildPlot(PreviewContext(index), index)` — coque, rim, dépôt ferraille, bays
3. pour chaque slot : `applySlotVisual` en état **débloqué** (pad bleu, ring visible),
   **sans prompt**
4. `ShopService.buildPreviewGeometry(ctx, model, origin)` — zone roulette (pad, arche,
   machine, 1 plateforme)
5. `ScrapyardService.buildPreviewVendor(model, origin)` — NPC vendeur figé (sans IA)
6. **Nettoyage** : retirer tout `ProximityPrompt`, `Script`/`LocalScript` ; désactiver
   le `Humanoid` (display-only) ; `Anchored = true` partout
7. parenter sous `Workspace.MapBlockout.EditPreview` en `EditPreview_<index>`

**Idempotent** : `EditPreview` est détruit puis reconstruit à chaque run (pattern
« Edit-mode generator » déjà utilisé pour les paths/PlotPreviews). Relançable sans
accumulation.

## Coexistence Édit / live — Guard au boot

Le `.rbxlx` est partagé entre Édit et live. Pour obtenir **plein en Édit / inchangé en
live / sans chevauchement** depuis un fichier unique :

- Les `PlotPreviews` simples actuelles **deviennent générées au boot** par un
  `EditPreviewGuard` (Script) : à `RunService:IsRunning()` (vrai en Play/live), il
  **détruit `EditPreview`** puis **construit les maquettes simples** via une fonction
  `buildSimplePreview(index)` (la géométrie statique actuelle déplacée en code).
- En **Édit** (aucun script ne tourne) : seul `EditPreview` existe → coques pleines,
  **aucun chevauchement**.
- En **live** : guard détruit `EditPreview` → maquettes simples identiques à
  aujourd'hui ; `PlotService.assignPlot` les détruit à la réclamation comme avant.

**Seul changement live** : les maquettes simples sont bâties au boot au lieu d'être
statiques — rendu **identique**, perf négligeable (8 petits modèles, une fois au boot).
C'est le prix minimal pour satisfaire « plein en Édit / zéro chevauchement / live
inchangé » depuis un fichier unique.

## Déclenchement & workflow

- Le baker est un **script Édit** lancé via le MCP Roblox Studio (`execute_luau` sur le
  DataModel d'édition), pas un service de jeu. Il vit dans le repo comme un script de
  génération réutilisable.
- **Workflow type** : modifier un builder → relancer le baker → `EditPreview` re-bake
  fidèlement → sauvegarder (Ctrl+S).

## Edge cases

| Cas | Traitement |
|---|---|
| Re-run du baker | détruit `EditPreview` d'abord (idempotent) |
| `Humanoid` du NPC qui tombe en Édit | `Anchored`, état figé, scripts retirés |
| Prompts/scripts inertes baked | strippés à l'étape 6 du baker |
| Drift futur d'un builder | impossible par construction (helpers partagés) ; sinon re-run baker |
| Floor 2 | hors scope (bake Floor 1 uniquement) |
| Machines posées | aucune (état coque vide) |

## Validation

1. **Bake** → inspecter `Workspace.MapBlockout.EditPreview` en Édit : 8 coques + NPC +
   zone roulette par plot.
2. **Comparer** les CFrames baked vs `originForIndex(index)` (mêmes origines/rotations
   que le runtime).
3. **Play** une fois → vérifier que `EditPreviewGuard` détruit `EditPreview`, génère les
   maquettes simples, et que le flux de réclamation de plot est non-régressé (plot
   réclamé == coque baked aux mêmes CFrames).

## Fichiers impactés (prévision)

- **Nouveau** `ReplicatedStorage/Shared/PlotBuild` — contexts + helpers cosmétiques partagés
- **Nouveau** baker Édit (script de génération, repo)
- **Nouveau** `EditPreviewGuard` (Script de boot) + `buildSimplePreview`
- **Modifié** `PlotService` (`buildPlot`, `refreshSlot` → via ctx)
- **Modifié** `ShopService` (`buildGeometry` + `buildPreviewGeometry`)
- **Modifié** `ScrapyardService` (vendor → builder pur `buildPreviewVendor`)
- `MachineService` — inchangé
