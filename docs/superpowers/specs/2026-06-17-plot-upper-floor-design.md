# Spec — Étage supérieur du plot joueur (1er étage)

**Date :** 2026-06-17
**Statut :** Validé (design), prêt pour plan d'implémentation
**Fichier source de vérité :** `build.rbxlx` (toute la source Lua/Luau y est intégrée dans des blocs `<ProtectedString name="Source">`).

## 1. Objectif

Les joueurs manquent de slots de machines. On ajoute **un (1) étage supérieur** au-dessus du rez-de-chaussée (RDC) du plot, apportant **8 nouveaux slots de griffes** déverrouillables un par un, dans la continuité du gameplay. L'étage :

- est **achetable une seule fois**, via un **panneau cliquable world-fixed** (style des panneaux d'amélioration du shop roulette), **uniquement** quand les **8 slots du RDC sont déverrouillés** + paiement d'un prix unique ;
- **n'est pas affiché du tout** tant qu'il n'est pas débloqué (aucune géométrie, échelle, ni bouton HUD) ;
- s'accède physiquement par une **échelle escaladable native** (TrussPart habillé industriel), reliant RDC → étage ;
- dispose d'un **bouton HUD haut-centre** (proprio uniquement) qui apparaît une fois l'étage débloqué et **téléporte** le joueur haut↔bas, avec label basculant « Monter à l'étage ↑ » / « Descendre ↓ ».

**Hors périmètre (mises à jour futures) :** plus d'un étage. Le design ne doit pas sur-anticiper N étages (YAGNI), mais ne doit pas non plus bloquer une extension future.

## 2. Contexte technique vérifié

- **Sol monde à `y = 0`** ; plots procéduraux construits relativement à `plot.origin` (CFrame).
- **`PlotService`** (source ≈ lignes 630700–631681 de `build.rbxlx`) :
  - `MAX_PLOTS = 8`, modèle `Plot_<UserId>`, attribut `OwnerUserId`, `PrimaryPart = Base`.
  - `buildPlot(player, index)` (≈631163–631431) construit le RDC ; boucle des baies `for i, slotDef in ipairs(PlotLayout.slots)` (≈631262–631332) : par baie → `ZoneFloor_/ZoneInset_/ZoneCurb_/ZonePost_/ZoneWall_`, `SlotRing_<id>` (néon), `Slot_<id>` (pad 7×1×7 DiamondPlate, attribut `SlotId`), placard SurfaceGui « BAIE i », tas de ferraille `DebrisPile_/DebrisBit_`.
  - `refreshSlot(player, slotId)` (≈631043–631143) : recolore le pad/ring selon `unlocked`, reconstruit les ProximityPrompts (locked→« Unlock (coût) » `handleUnlock` ; unlocked vide→« Place UFO » `handlePlace` ; occupé→« Ranger » `handleUnequip` + « Améliorer » `handleUpgrade`), et bâtit le claw `UFO_<slotId>` si `ufoUid`.
  - `handleUnlock` (≈631484–631504) : `EconomyService.spend(slotDef.unlockCost, slotDef.unlockCurrency)` → `slotData.unlocked=true` → `refreshSlot` → `replicate` → analytics `"slot_unlocked"`.
  - `assignPlot` (≈631543–631597), `teleportToPlot` (≈631433–631443, set `hrp.CFrame = info.spawnCF`).
  - **API publique :** `getPlot(player)→{model,origin}`, `getSlotPad(player,slotId)`, `onPlotReady(fn)` (≈631670–631675, **hook pour builders externes**), `refreshClaw`, `makeUFOModel`.
- **`PlotLayout`** (config, source ≈601108–601152) : `slots` = liste de 8 defs `{ id, offset:Vector3, tier, unlockCurrency="scrap", unlockCost }` ; `slotById` (601150). Colonnes : droite `x=+34` (s1 z=-18 c0, s2 z=4 c0, s3 z=26 c200, s4 z=48 c600) ; gauche `x=-34` (s5 z=-18 c1800, s6 z=4 c5000, s7 z=26 c14000, s8 z=48 c40000). `plotSize=(128,1,128)`, `zoneSize=(42,1,20)`, `zoneWallHeight=5`. `rouletteOffset=(36,0,-94)`.
- **`GameConfig.PROFILE_TEMPLATE`** (source ≈600851–600922, template ≈600885–600920) : `plot = { expansionLevel=1, slots = { s1..s8 = {unlocked, ufoUid} } }` (s1/s2 unlocked=true). `DataService` (ProfileStore `"PlayerData_v1"`) appelle `:Reconcile()` → **ajout de clés rétro-compatible**.
- **Consommateurs de `data.plot.slots`** itèrent tous **génériquement** `pairs(data.plot.slots)` : StateController client (≈590445), UIController `placedBy` (≈593041), CatchService loop (≈629686), refresh/téléport (≈631449), assignPlot clear (≈631574), getPlot helper (≈631645), admin `unlockSlots` (≈633372). → Ajouter `f1..f8` à la même map est transparent pour eux.
- **HUD :** `MainHUD` est une ScreenGui **bakée** dans StarterGui (≈593358+), câblée par `UIController` (LocalScript, source ≈592945–593203). Pas d'élément haut-centre (place libre). `SellBtn` est le **patron de téléport** : `hrp.CFrame = pad.CFrame * CFrame.new(0,3.5,-12) * CFrame.Angles(0,π,0)` (≈593194–593197). Helpers `Theme`/`UIUtil` idiomatiques pour les boutons.
- **Shop roulette panneau** (`ShopService`, source ≈631696–632217) : panneau SurfaceGui world-fixed cliquable (Chance/Slots), `buySlot` (≈632161–632177), enregistré via `onPlotReady` (≈632194). **Modèle de référence pour le panneau d'achat de l'étage.**
- **Réseau :** `Net.onRequest`/`Net.request` (req/rép), `Net.sendEvent`/`Net.onEvent` (push).
- **Aucun multi-étage / échelle fonctionnelle existant** ; `LadderRail` sont des `Part` décoratifs. `TeleportService` inutilisé. Mouvement vertical = set `hrp.CFrame`.

## 3. Décision d'architecture : map de slots unifiée

On ajoute les 8 slots de l'étage **dans la même map `data.plot.slots`** (ids `f1..f8`) et dans **`PlotLayout.slots`** (chaque def gagne un champ `floor = 0|1`). Aucun consommateur générique de `plot.slots` n'est modifié. La distinction de niveau ne sert que :
1. à la **condition de prérequis** (« 8/8 RDC ») qui ne compte que les defs `floor==0` ;
2. au **build géométrique** (les baies `floor==1` ne se construisent que si `floor2Unlocked`).

Rejeté : sous-table séparée `plot.floor2.slots` (modifie tous les consommateurs, surface de bug), et `expansionLevel` générique par paquets (sur-ingénierie, YAGNI 1 étage).

## 4. Modèle de données (`GameConfig.PROFILE_TEMPLATE.plot`)

```lua
plot = {
  expansionLevel = 1,          -- inchangé (laissé tel quel)
  floor2Unlocked = false,      -- NOUVEAU : état d'achat de l'étage
  slots = {
    s1 = {unlocked=true,  ufoUid=false}, -- floor 0 (RDC), inchangé
    ... s8 ...,
    f1 = {unlocked=false, ufoUid=false}, -- NOUVEAU : floor 1 (étage)
    ... f8 = {unlocked=false, ufoUid=false},
  },
}
```

`:Reconcile()` ajoute `floor2Unlocked` et `f1..f8` aux profils existants sans casse.

## 5. Config (`PlotLayout`)

- Les defs `s1..s8` reçoivent `floor = 0`.
- Nouvelle constante `FLOOR_HEIGHT = 24` (studs) — dégagement au-dessus des machines RDC + plafond/dalle.
- Nouvelle constante `floorCost = 100000` (`scrap`), `floorCurrency = "scrap"`.
- 8 nouvelles defs `f1..f8`, `floor = 1`, **mêmes offsets X/Z que s1..s8** (2 colonnes miroir : droite x=+34, gauche x=-34, z ∈ {-18,4,26,48}) mais bâties à `y = FLOOR_HEIGHT`. Coûts en **continuité de courbe** (≈ s8=40000 ; facteur ~2.5/cran) :

  | slot | colonne / z | coût (scrap) |
  |------|-------------|--------------|
  | f1 | droite z=-18 | 120 000 |
  | f2 | droite z=4   | 250 000 |
  | f3 | droite z=26  | 500 000 |
  | f4 | droite z=48  | 1 000 000 |
  | f5 | gauche z=-18 | 2 000 000 |
  | f6 | gauche z=4   | 4 000 000 |
  | f7 | gauche z=26  | 8 000 000 |
  | f8 | gauche z=48  | 16 000 000 |

  (Aucun slot gratuit à l'étage : la progression reste tendue. Valeurs à équilibrer en jeu, ordre de grandeur fixé.)
- Constantes géométrie étage : dimensions dalle (empreinte 128×128 comme `plotSize`), hauteur garde-corps (~4), offset/dimensions de l'échelle (TrussPart) et de la **trémie** (trou de passage), offset du **panneau d'achat** (près du pied de l'échelle, au RDC).
- Numérotation des placards de l'étage : **« BAIE 9 » … « BAIE 16 »** (continuité avec les 8 du RDC). Mapping `f1→9 … f8→16`.

## 6. Géométrie (`PlotService`)

### 6.1 Toujours construit (dans `buildPlot`, RDC inchangé +)
- **Panneau d'achat de l'étage** : modèle world-fixed avec SurfaceGui cliquable (réutilise le style/les helpers du panneau Chance/Slots de `ShopService`), placé près du pied de l'échelle. Construit pour tout plot, quel que soit l'état.

### 6.2 Construit seulement si `data.plot.floor2Unlocked == true` — nouveau helper `buildFloor2(player, info, data)`
- **Dalle** de l'étage : grande part DiamondPlate cartoon à `y = FLOOR_HEIGHT`, empreinte 128×128, style cohérent (palette `YardPalette`/`styleParts`). Éclairage (PointLight/SurfaceLight) sous-face pour ne pas assombrir le RDC.
- **Garde-corps** périmétriques (anti-chute) tout autour de la dalle + autour de la **trémie**, en laissant l'ouverture d'accès à l'échelle.
- **Trémie** : trou dans la dalle aligné sur l'échelle.
- **Échelle escaladable** : `TrussPart` (style `Ladder`/industriel), du sol RDC (`y≈0`) à la dalle (`y=FLOOR_HEIGHT`), traversant la trémie. Habillage déco (rails latéraux, cage) en `Part` non-collidables autour pour le look, le TrussPart restant l'élément escaladable.
- **8 baies `f*`** : réutilise **exactement** la boucle de baie existante (généralisée pour prendre l'offset Y), produisant `ZoneFloor_/Inset_/Curb_/Post_/Wall_`, `SlotRing_f*`, `Slot_f*` (attribut `SlotId="f*"`), placard « BAIE 9..16 », tas de ferraille. `refreshSlot` réutilisé tel quel (les `f*` sont dans `plot.slots`).

### 6.3 Refactor de la boucle de baie
Extraire la construction d'une baie en helper paramétré `buildBay(model, origin, slotDef)` où `slotDef.offset` inclut le Y (0 pour RDC, `FLOOR_HEIGHT` pour étage). `buildPlot` et `buildFloor2` l'appellent. Garde la cohérence visuelle RDC/étage **par construction** (même code = même style).

## 7. Achat de l'étage

### 7.1 Panneau (client + rendu world-fixed)
État affiché (rafraîchi à l'`onReady`/`replicate` côté client, via un petit contrôleur ou extension du contrôleur existant qui gère les panneaux du plot) :
- **< 8/8 RDC déverrouillés** : « Débloque les 8 baies du RDC : X/8 » — non cliquable.
- **8/8 et `floor2Unlocked==false`** : « CONSTRUIRE L'ÉTAGE — `floorCost` $ » — cliquable.
- **`floor2Unlocked==true`** : panneau statut « Étage débloqué ✓ » (déco).

### 7.2 Serveur — `Net.onRequest("unlockFloor", player)`
Re-valide **toujours** côté serveur (jamais de confiance client) :
1. `data.plot.floor2Unlocked == false` (sinon no-op) ;
2. tous les `PlotLayout.slots` avec `floor==0` ont `data.plot.slots[id].unlocked == true` ;
3. solde ≥ `floorCost` → `EconomyService.spend(floorCost, floorCurrency)`.
Si OK : `data.plot.floor2Unlocked=true` → `buildFloor2(...)` → `refreshSlot` pour chaque `f*` → `DataService.replicate(player)` → `Net.sendEvent(player,"floorUnlocked")` → analytics `"floor_unlocked"`. Rafraîchir le panneau d'achat en état « débloqué ».

## 8. Bouton HUD haut-centre

- **Élément** : ajouter au `MainHUD` baké un `TextButton`/Frame `FloorBtn` (`AnchorPoint (0.5,0)`, `Position UDim2.new(0.5,0,0,12)`), stylé via `Theme`. (Option équivalente : créer à l'exécution dans `UIController` ; choisir l'approche la plus cohérente avec les autres boutons — préférer l'élément baké comme `SellBtn`.)
- **Visibilité** : `Visible=false` par défaut. Devient visible quand `floor2Unlocked==true` — état lu via `replicate` (StateController) **et** event `floorUnlocked`. Listener mis à jour si l'état change en cours de session.
- **Uniquement sur son propre plot** : le bouton est un confort proprio (il appartient au LocalPlayer), donc lié à l'état du LocalPlayer.
- **Label dynamique & téléport** : à l'ouverture et à chaque clic, déterminer l'étage courant du personnage par sa hauteur Y (seuil ≈ `FLOOR_HEIGHT/2`).
  - Au RDC → label « Monter à l'étage ↑ », clic = téléport vers spawn étage.
  - À l'étage → label « Descendre ↓ », clic = téléport vers spawn RDC.
  - Téléport = set `hrp.CFrame` côté client (comme `SellBtn`), vers un point d'arrivée dégagé (haut : à côté de la trémie sur la dalle ; bas : `info.spawnCF`). Le label se met à jour après téléport.

## 9. Edge cases

- **Étage verrouillé** → aucune dalle/échelle/baie/bouton HUD ; seul le panneau-prérequis est visible. ✓
- **8/8 atteint pendant l'observation du panneau** → maj live via listener `replicate`. ✓
- **Visiteurs sur le plot d'autrui** : l'échelle TrussPart est physique → ils peuvent monter/descendre. Le bouton HUD n'apparaît que sur **leur propre** plot (lié au LocalPlayer). ✓
- **Anti-exploit** : `unlockFloor` re-validé serveur (prérequis + coût). Le téléport HUD est sur son propre plot sans gain exploitable ; même forcé, aucun avantage. ✓
- **Respawn** : spawn RDC (`spawnCF`) inchangé ; le joueur réapparaît en bas. ✓
- **Chute** : garde-corps périmétriques + garde-corps de trémie. ✓
- **Pas de dé-achat** : 1 étage permanent (conforme « 1 étage max »). ✓
- **Catch loop / MachineService / upgrade** : opèrent sur `plot.slots[*].ufoUid` ; les `f*` n'ont de claw qu'après déverrouillage → comportement identique au RDC, sans modif. ✓
- **Profils existants** : `:Reconcile()` ajoute `floor2Unlocked` + `f1..f8` (verrouillés). ✓
- **Re-build au join** : si `floor2Unlocked==true` au chargement, `buildPlot` doit appeler `buildFloor2` → l'étage + claws posés réapparaissent. ✓

## 10. Découpage d'implémentation (indicatif, pour le plan)

1. **Données + config** : `PROFILE_TEMPLATE` (`floor2Unlocked`, `f1..f8`), `PlotLayout` (`floor` sur s/f, `FLOOR_HEIGHT`, `floorCost`, defs `f1..f8`, constantes dalle/échelle/trémie/panneau, mapping placards 9–16).
2. **Refactor baie** : extraire `buildBay(...)` paramétré Y depuis la boucle existante de `buildPlot` (sans changement visuel RDC).
3. **`buildFloor2`** : dalle + garde-corps + trémie + TrussPart échelle + 8 baies `f*` ; appelé depuis `buildPlot` si `floor2Unlocked`.
4. **Achat** : `Net.onRequest("unlockFloor")` serveur (re-valide + spend + build + replicate + event) ; panneau world-fixed (build géométrie + rendu/état client).
5. **Bouton HUD** : élément `FloorBtn` dans `MainHUD` + câblage `UIController` (visibilité sur `floor2Unlocked`, label dynamique par Y, téléport).
6. **Vérif live (Studio MCP)** : prérequis 8/8 → achat → étage apparaît, échelle escaladable, slots f déverrouillables, claws posables, bouton HUD bascule, visiteur peut grimper, rétro-compat profil.

## 11. Style visuel

L'étage **réutilise le code de construction du RDC** (mêmes helpers `styleParts`, palette `YardPalette`, mêmes pièces de baie, néons SurfaceGui), garantissant la cohérence « même style » par construction. La dalle, les garde-corps et l'échelle adoptent le langage industriel cartoon existant (DiamondPlate, métal, néons, placards). Hero meshes Blender éventuels = mise à jour future (hors périmètre).
