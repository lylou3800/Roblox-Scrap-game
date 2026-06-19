# Claw grab animation fix + Scrap "familles" removal (rarity-only) — Design

**Date :** 2026-06-16
**Statut :** Validé (design approuvé par l'utilisateur)

## Contexte

Deux chantiers liés au gameplay de scrap des machines à pince (UFO catchers) :

1. **Bug d'animation 3D de la pince.** En jeu, l'animation de grab est « à l'envers » :
   le bras semble grab vers le haut, et les mâchoires de la pince paraissent en
   permanence ouvertes au maximum. À corriger.
2. **Suppression des familles/thèmes de scrap.** Le système de scrap classe les
   items sur des dimensions non-raretés (`theme` + `family`). L'utilisateur veut
   **supprimer entièrement ces dimensions** et ne garder que la **rareté** comme
   seul classificateur, en data ET en UI. Plus aucun affichage de famille/thème
   nulle part. Tous les systèmes qui dépendaient de family/theme sont recâblés
   sur la rareté.

### Décisions validées (utilisateur, 2026-06-16)

- **Portée scrap :** tout supprimer (`theme` + `family`). La rareté devient le seul
  classificateur.
- **Coût de craft :** « X scraps d'une rareté donnée » (au lieu d'une famille).
- **Bonus de claw (`specialEfficiency`) :** bonus de valeur sur une **rareté**
  donnée (au lieu d'une famille).
- **Gating des drops :** re-gating par **rareté** — les meilleures claws débloquent
  les raretés supérieures (au lieu du gating `minTier` par thème).
- **Recycleur :** plus de catégorie → accepte **tout le scrap**.

---

## Partie A — Correction de l'animation de pince

### Cause racine (investiguée)

Trois sources de vérité en conflit, dont deux mal renseignées par le **builder
serveur de plot** :

1. **Direction du bras :** le builder écrit l'attribut `ArmPivot.RestCF` avec une
   rotation **identité (0°)**, alors que le bras repose physiquement à **~−27°**.
   La boucle idle (`animateWorld`) et `animateClaw` lisent `RestCF` ; comme il est
   faux, chaque frame snap le bras à 0° puis le dip est calculé autour de la
   mauvaise base → l'arc swing dans le mauvais sens (« vers le haut »).
2. **Mâchoires :** l'écart des mâchoires est **doublement encodé** — un spread de
   **+32° baké dans le `C1` de chaque `JawMotor`** (serveur) ET un `Transform`
   piloté côté client (`JAW_OPEN=-0.2`, `JAW_GRAB=-0.6`). Le spread statique
   domine ; même la valeur « grab » ne referme jamais visiblement les mâchoires.
3. **Troisième source non réconciliée :** chaque `ClawJaw` porte un attribut
   `OpenAngle=0.5` jamais lu par le client.

### Surfaces de code

- **Serveur — builder de plot** (à localiser en **mode Edit** ; non visible en Play ;
  construit `Plot_<userId>` dont `UFO_s*` : `ArmPivot`, `Claw`, `ClawJaw`×5,
  `ClawTip`×5, `JawMotor`×5, `FeedbackAnchor`).
- **Client — `CatchFXController`** (`StarterPlayer.StarterPlayerScripts.Client.Controllers.CatchFXController`,
  source de vérité ; miroir runtime `Players.lylou38000.PlayerScripts...`).
  Fonctions concernées : `animateClaw` (~293–361), boucle idle `animateWorld`
  (~533–552), constantes `DIG_ANGLE`, `JAW_OPEN`, `JAW_GRAB` (~286–290).

### Changements (single source of truth)

1. **`RestCF` correct.** Le builder écrit `ArmPivot.RestCF` = la **CFrame réelle**
   construite du bras (rest ~−27°), pas l'identité. Une fois correct, le dip
   `rest * CFrame.Angles(0,0,-DIG_ANGLE)` descend bien depuis le vrai repos et le
   snap parasite disparaît. (Le fallback `pivot.CFrame` existant ne se déclenche
   pas tant que `RestCF` est un CFrame, même faux — d'où le masquage du bug.)
2. **`C1` à la pose fermée.** Le builder bake chaque `JawMotor.C1` à la pose de
   **grip fermé** (mâchoires jointes, spread 0°) au lieu de +32°. Le client ouvre
   alors les mâchoires via un `Transform` **positif** et repose/grab à
   `Transform = 0` (= fermé).
3. **Réconcilier en une seule valeur.** Remplacer les trois valeurs d'ouverture
   non synchronisées (C1 +32°, attribut `OpenAngle=0.5`, constantes client) par
   **une seule** valeur d'ouverture (constante client, ou attribut `JawOpen` lu
   par le client — au choix à l'implémentation, mais une seule source). Séquence :
   1. descente → mâchoires **s'ouvrent**,
   2. bas → **snap fermé** (`Transform = 0`) au grab,
   3. remontée → **restent fermées** (tient le tas),
   4. repos → **se rouvrent** pour relâcher.
   Angle exact calibré visuellement à l'implémentation.
4. **Deux miroirs client.** Éditer la source `StarterPlayerScripts…CatchFXController`
   (la copie `Players.lylou38000…` est un clone runtime). Le changement builder se
   fait en **mode Edit** (rbxlx = source de vérité).

### Vérification

- En Play : le bras descend (pas vers le haut), les mâchoires sont **visiblement
  fermées au repos/grab** et s'ouvrent uniquement pendant la descente.
- Vérifier via inspection : `ArmPivot.RestCF` ≈ CFrame réelle du bras ; `JawMotor.C1`
  sans spread +32°.

---

## Partie B — Suppression des familles/thèmes (rarity-only)

### Dimensions retirées

- **`theme`** (11 groupes : domestic, raw_metal, auto, bolts, tools, consumer_elec,
  computer, energy, telecom, heavy_industrial, lab, anomaly) — pilotait l'icône/
  couleur des cartes, le regroupement de l'index, et le **gating de drop par tier**
  (`minTier`).
- **`family`** (5 buckets : monetary, utility, craft, collection, event) — pilotait
  les **recettes de craft**, le **recycleur** (`accepts`), et le **bonus de rang de
  claw** (`specialEfficiency`).

> Piège : les chips « Garder par **famille** » du terminal de tri filtrent en réalité
> par **`theme`**. Le mot « famille » à l'écran ≠ le champ data `family`. Les deux
> dimensions doivent être retirées.

### Source de couleur/icône de rareté

`ReplicatedStorage.Shared.Config.Rarities` (accès `Rarities.list` / `byId` /
`get(id)`) — 10 raretés ordonnées (common → transcendent), chacune avec
`id, name, color({r,g,b}), weight, valueMult, order`. **Pas d'icône** aujourd'hui.
→ Ajouter un champ optionnel **`icon`** (emoji) par rareté dans `Rarities` et dans
le type `RarityDef` (`Types`), comme source unique pour la touche visuelle de
l'index/inventaire (là où l'icône de thème était utilisée). Tous les contrôleurs
UI scrap importent déjà `Rarities`.

### Couche data (ReplicatedStorage.Shared)

- **`Types`** : retirer `ItemFamily`, `ScrapTheme`, `LootItemDef.family`,
  `LootItemDef.theme`, `MachineDef.accepts` ; changer `UFOStats.specialEfficiency`
  de `{ family, mult }` → `{ rarity, mult }` ; ajouter `RarityDef.icon: string?`.
- **`Config.ScrapThemes`** : **supprimer le module** + toutes les références
  `require`.
- **`Config.LootTable`** : retirer `family` et `theme` des 31 items (garder
  `id, name, baseValue, rarity, dropWeight`).
- **`Config.Rarities`** : ajouter `icon` par rareté (10 emojis).
- **`Config.Crafts`** : recettes re-clés sur la **rareté** (ex. `{ rarity="common",
  count=40 }, { rarity="rare", count=10 }`).
- **`Config.ClawDesign`** : `RANKS[*].family` → `RANKS[*].rarity` (rareté ciblée par
  le bonus) ; `genStats()` construit `specialEfficiency = { rarity = r.rarity,
  mult = … }`. Le rang « all » → bonus universel (rarity = "all" géré côté logique).
- **`Config.Machines`** : retirer `recycler.accepts` (recycleur accepte tout).
- **`Config.GameConfig`** : `PROFILE_TEMPLATE.sellFilter` de
  `{ rarities = {}, themes = {} }` → `{ rarities = {} }` (la reconciliation au load
  retire la clé morte `themes` des profils existants).

### Couche logique serveur (dans `build.rbxlx`, mode Edit)

- **`CatchService.rollLoot`** : remplacer le gating thème `minTier` par un **gating
  par rareté selon le tier de claw** (meilleure claw → raretés supérieures
  débloquées) ; remplacer le match `se.family == itemDef.family` par un match
  **`se.rarity == itemDef.rarity`** (avec `"all"` → bonus universel).
- **`CraftService`** : `familyCount` / `consume` / `craft` → comptent et consomment
  l'inventaire **par rareté** (`def.rarity`).
- **`InventoryService`** : retirer le filtre `themes` et le calcul `byTheme` de
  `sellFiltered`, `sellableInfo`, `sellableByRarity`, `holdings` ; garder
  `byRarity`.
- **`ScrapyardService`** : `getFilter` ne sème plus `themes` ; le handler
  `setSellFilter` retire la branche `kind == "theme"`.
- **`MachineService`** : le recycleur n'utilise plus `accepts`/family → accepte tout
  le scrap.
- **`ClawUpgrade`** : `specialEfficiency` désormais clé sur la rareté ; gérer le cas
  nil proprement (l'estimation $/s ne crash pas).

### Couche UI client

- **`ScrapyardController`** (TRI DU TAS) : supprimer `FAMILY_LABEL`, la liste
  `families`, la section **« Garder par famille »** et ses requêtes
  `setSellFilter{kind="theme"}`. Conserver la section de tri par rareté + le
  breakdown d'inventaire par rareté.
- **`UIController`** — menu Inventaire : retirer le chip de filtre par thème ; les
  lignes de junk sont colorées / iconées / nommées par **rareté** (via `Rarities`)
  au lieu du thème.
- **`UIController`** — IndexUFO (mode SCRAPS) : regrouper l'index **par rareté** (une
  section par tier, triées par `order`) au lieu de par thème.
- **`UIController`** — menu Améliorations (craft) : afficher les exigences de recette
  **par rareté** (libellé + compteur).
- **Kiosque 3D de tri** (PlotService) : déjà rarity-only (« scan rareté ») — aucun
  changement.

### Edge cases / risques (traités)

1. **Profils sérialisés** : `sellFilter.themes` reste dans les saves existantes →
   la reconciliation du template le retire (clé morte sinon inoffensive).
2. **Contrat client↔serveur** : `setSellFilter{kind="theme"}` retiré des **deux**
   côtés simultanément (pas de requête orpheline).
3. **`byTheme`** : champ calculé mais non consommé par le client → supprimé.
4. **`theme.axis`** : confirmé sans consommateur runtime → part avec les thèmes.
5. **Gating** : sans la boucle de filtre `minTier`, ne pas laisser
   `ScrapThemes.get(...)` orphelin (sinon nil/erreur) ; le remplacer par le gating
   rareté.
6. **Index regroupé par thème** : nécessite une nouvelle clé de regroupement
   (rareté), pas juste masquer un label.
7. **Deux miroirs client** : éditer la source `StarterPlayerScripts`.
8. **Littéraux dispersés** : strings family/theme codés en dur dans `FAMILY_LABEL`,
   `Crafts`, `ClawDesign.RANKS`, `Machines.accepts`, `ScrapThemes`/`LootTable` — tous
   indépendants, à traiter un par un.

## Portée / non-objectifs

- Pas de refonte du système d'upgrade au-delà du recâblage rareté.
- Pas de nouveaux assets sonores.
- Corrections paramétriques via les générateurs serveur (pas part-par-part) pour le
  builder de plot.
- L'équilibrage fin (courbe de gating par rareté, coûts de craft exacts, multiplis
  de bonus) reprend les valeurs existantes transposées sur la rareté ; ajustable à
  l'implémentation.
