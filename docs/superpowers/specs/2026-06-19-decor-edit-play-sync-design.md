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

> **Note :** le schéma ci-dessous décrit l'intention initiale (module partagé + ctx).
> Voir « Découverte en phase de planification » plus bas : l'implémentation retenue est
> plus simple — extraction de fonctions de géométrie pures + un module baker, **sans**
> objet ctx, **sans** guard de boot, **sans** ServerStorage.

```
Extraction de fonctions de géométrie PURES (réutilisées par runtime ET baker) :
  PlotService      assemblePlot(model, origin)  ← cœur extrait de buildPlot
                   buildPreviewPlot(index)      ← export baker
                   applyUnlockedSlotVisual(model, slotDef)
  ShopService      buildRouletteGeometry(hub, O, platformCount)  ← extrait de buildGeometry
                   buildPreviewRoulette(model, origin)           ← export baker
                   buildMachine(hub, MO)  ← scindé : géométrie seule (levier-prompt déplacé)
  ScrapyardService buildVendor(model, anchor)  ← DÉJÀ exporté, pur
  MachineService   inchangé (aucune machine en preview)

EditPreviewBaker (ServerScriptService.Tools.EditPreviewBaker, run() re-runnable)
  pour index 0..7 :
    model = PlotService.buildPreviewPlot(index)
    applyUnlockedSlotVisual + ScrapyardService.buildVendor + ShopService.buildPreviewRoulette
    strip prompts/clickers/scripts ; Anchored=true
  → Workspace.MapBlockout.PlotPreviews.PlotPreview_<index>   (in-place, idempotent)
```

Le baker **ne touche pas** à `assignPlot` (occupied, teleport, replicate, callbacks
restent live-only) : il compose les fonctions de géométrie extraites.

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

## Découverte en phase de planification (révision majeure)

L'inspection du jeu a révélé que les `PlotPreviews` actuelles **ne sont pas des
maquettes simples** : ce sont déjà **8 répliques complètes** (`PlotPreview_0..7`,
~327 parts chacune) incluant coque, bays, stand vendeur + modèle `Vendor` bakés, et un
`PreviewMachine`. Elles n'ont **ni `ProximityPrompt` ni `Humanoid`** (le vendeur est un
assemblage de `Part` ancrées, pas un NPC animé).

Conséquences qui **simplifient le design** :

1. **Le mécanisme guard + ServerStorage est inutile.** La coexistence Édit/live est
   **déjà** résolue par le design existant : previews statiques nommées `PlotPreview_N`,
   détruites par `assignPlot` à la réclamation. On **re-bake les 8 previews en place**.
2. **La prémisse du choix « Édit Studio seulement » (Q4 : coût perf des coques/NPC en
   live) ne s'applique pas** : ces coques complètes sont **déjà** dans le fichier et
   **déjà** affichées en live sur les plots non réclamés. Un re-bake fidèle n'ajoute
   aucun coût (mécanisme identique ; seule la géométrie est corrigée).
3. **Vrais écarts Édit↔Play** : les previews **n'ont pas la zone Roulette** (absente),
   contiennent un **`PreviewMachine`** non désiré (état « coque vide »), et ont
   **dérivé** de la géométrie actuelle des builders.
4. `ScrapyardService.buildVendor(plotModel, anchor)` est **déjà exporté** « pour le
   générateur Edit-mode » → terrain préparé.

La table « BuildContext » ci-dessus est conservée comme **intention** ; en pratique
l'unique dépendance données est le **nombre de plateformes roulette** (passé en
argument) et le **cosmétique slot débloqué** (appliqué par le baker). Pas besoin d'un
objet `ctx` élaboré : on **extrait les fonctions de géométrie pures** et le baker les
compose. Anti-dérive identique (géométrie partagée en un seul endroit).

## Le baker — `EditPreviewBaker`

Module stocké dans le place (`ServerScriptService.Tools.EditPreviewBaker`), re-runnable
via `require(...).run()`. Pour chaque `index` 0..7 :

1. `model = PlotService.buildPreviewPlot(index)` — coque, rim, dépôt ferraille, bays
   (réutilise le cœur géométrique extrait `assemblePlot(model, origin)`)
2. cosmétique **slot débloqué** appliqué (pad bleu, ring visible), **sans prompt**
3. `ScrapyardService.buildVendor(model, findVendorAnchor(model))` — stand vendeur (parts)
4. `ShopService.buildPreviewRoulette(model, PlotService.originForIndex(index))` — zone
   roulette (pad, arche, machine **sans levier-prompt**, 1 plateforme, décor)
5. **Nettoyage** : retirer tout `ProximityPrompt` / `ClickDetector` / `Script` /
   `LocalScript` résiduel ; `Anchored = true` partout ; **pas** de `PreviewMachine`/`UFO`
6. parenter sous `Workspace.MapBlockout.PlotPreviews` en `PlotPreview_<index>`

**Idempotent** : le dossier `PlotPreviews` est détruit puis reconstruit à chaque run
(pattern « Edit-mode generator » déjà utilisé). Relançable sans accumulation.

## Coexistence Édit / live

**Aucun mécanisme supplémentaire requis.** Les previews re-bakées restent des décors
statiques nommés `PlotPreview_N` dans `Workspace.MapBlockout.PlotPreviews`, exactement
comme aujourd'hui :

- **Édit** : les 8 previews fidèles sont visibles dans le viewport.
- **Live** : `PlotService.assignPlot` détruit `PlotPreview_<index>` à la réclamation
  (code inchangé, lignes 1306-1312) puis `buildPlot` construit le plot du joueur.
- Plots non réclamés en live → affichent la preview fidèle (comme aujourd'hui, à
  géométrie corrigée près).

## Déclenchement & workflow

- Le baker est lancé en mode Édit via le MCP Roblox Studio
  (`execute_luau`/`run_script` → `require(game.ServerScriptService.Tools.EditPreviewBaker).run()`),
  ou via un Script temporaire si la VM `execute_luau` ne persiste pas les mutations.
- **Workflow type** : modifier un builder → relancer le baker → `PlotPreviews` re-bake
  fidèlement → sauvegarder (Ctrl+S).

## Edge cases

| Cas | Traitement |
|---|---|
| Re-run du baker | détruit `PlotPreviews` d'abord (idempotent) |
| Vendeur en Édit | déjà un assemblage de `Part` ancrées (aucun `Humanoid`) |
| Prompts/clickers/scripts résiduels | strippés à l'étape 5 du baker |
| Drift futur d'un builder | la géométrie vit en un seul endroit (fonctions partagées) ; sinon re-run baker |
| Floor 2 | hors scope (bake Floor 1 uniquement) |
| Machines posées (`PreviewMachine`/`UFO`) | aucune (état coque vide) |
| Régression runtime des builders | le chemin live appelle les mêmes fonctions extraites → vérifié en Play |

## Validation

1. **Bake** → `inspect_instance` sur `Workspace.MapBlockout.PlotPreviews` en Édit :
   8 `PlotPreview_N`, chacun avec un enfant `Roulette`, un enfant `Vendor`,
   **aucun `ProximityPrompt`**, **aucun `PreviewMachine`/`UFO_*`**.
2. **Comparer** le `WorldPivot`/`Base.CFrame` de chaque preview à `originForIndex(index)`.
3. **Play** une fois → vérifier la non-régression : claim d'un plot détruit sa preview et
   construit le plot live ; le plot live (zone roulette, bays, vendeur) est
   géométriquement identique à la preview bakée.

## Fichiers impactés (prévision)

- **Nouveau** `ServerScriptService.Tools.EditPreviewBaker` — module générateur re-runnable
- **Modifié** `PlotService` — extraire `assemblePlot(model, origin)` de `buildPlot` ;
  ajouter exports `buildPreviewPlot(index)`, `originForIndex` ; helper
  `applyUnlockedSlotVisual(model, slotDef)`
- **Modifié** `ShopService` — scinder `buildMachine` (géométrie / levier-prompt) ;
  extraire `buildRouletteGeometry(hub, O, platformCount)` ; ajouter export
  `buildPreviewRoulette(model, origin)`
- `ScrapyardService` — `buildVendor` **déjà exporté** (aucun changement, ou exposer
  `findPart` si besoin)
- `MachineService` — inchangé
- **Aucun** guard de boot, **aucun** usage de `ServerStorage` (mécanisme abandonné)
