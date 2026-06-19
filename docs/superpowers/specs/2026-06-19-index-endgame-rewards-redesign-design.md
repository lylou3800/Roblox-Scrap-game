# Index — Reward-Track Redesign + Endgame Bonuses (design)

Date: 2026-06-19
Status: validated direction, pending spec review

## Goal

Refonte visuelle de l'**Index de collection** (`IndexController`) et passage des
récompenses de paliers à des **bonus permanents endgame**, avec une **machine
exclusive** comme récompense ultime de l'index des Pinces.

Cinq problèmes adressés (demande utilisateur) :
1. Textes sombres → **blancs + contour noir** (typo « AMELIOS »).
2. Proportions du rail mauvaises.
3. **Afficher les bonus** de complétion de l'index.
4. **Jauge** : plus fluide, propre, précise (bugs de size/précision).
5. Récompenses → **endgame** (% revenu total, % revenu hors-ligne, machine exclusive).

## Existing system (grounding)

- `IndexController.render` (client) construit : onglets Pinces/Scraps, **rail gauche**
  (titre `X/Y`, jauge verticale, bouton « Récompense ! »), grille par rareté.
- `CollectionService.claimIndexReward` (serveur) **existe** : pour chaque palier
  `count >= mlt.count` non réclamé, crédite `mlt.scrap` (cash) et applique
  `mlt.bonus = {clé=valeur}` dans `data.bonuses`. Compteurs : `ownedClawCount` (pinces
  distinctes, max 120) / `scrapComboCount` (combos item×rareté, max 310).
- `data.bonuses` est le bus de bonus permanents. `luckAdd` déjà lu par `CatchService`.
- Revenu total = `sellMultTotal = 1 + Crafts.bonus + Upgrades.sellBonus + Pets.sellBonus + boostCash`
  (CatchService ~L177, InventoryService ~L62). **N'inclut pas encore `data.bonuses.sellMult`.**
- Offline = `AutomationService.grantOffline` : `pct = basePct + perLevel*level + petOffline`
  (~L40). **N'inclut pas encore `data.bonuses.offlinePct`.**

## A. Reward config (`Shared.Config.IndexRewards`)

Remplacer les récompenses cash par des bonus permanents. Schéma par palier :
`{ count, bonus = {<kind> = value} }` ou `{ count, machine = "<defId>" }`.

Kinds de bonus (additifs, fraction) :
- `sellMult` — **% revenu total** (vente + cash instantané).
- `offlinePct` — **% revenu hors-ligne**.

```
ufo = {
  { count = 10,  bonus = { sellMult   = 0.03 } },  -- +3% revenu total
  { count = 25,  bonus = { offlinePct = 0.05 } },  -- +5% hors-ligne
  { count = 50,  bonus = { sellMult   = 0.05 } },  -- +5% revenu total
  { count = 75,  bonus = { offlinePct = 0.08 } },  -- +8% hors-ligne
  { count = 100, bonus = { sellMult   = 0.08 } },  -- +8% revenu total
  { count = 120, machine = "index_exclusive_ufo" }, -- MACHINE EXCLUSIVE (TBD)
}
scrap = {
  { count = 25,  bonus = { sellMult   = 0.03 } },
  { count = 75,  bonus = { offlinePct = 0.05 } },
  { count = 150, bonus = { sellMult   = 0.06 } },
  { count = 230, bonus = { offlinePct = 0.10 } },
  { count = 310, bonus = { sellMult   = 0.15 } },  -- gros bonus (pas de machine)
}
```

`index_exclusive_ufo` = **placeholder** : le `defId` réel sera défini plus tard dans
`UFOCatchers`. Tant qu'il n'existe pas, le palier 120 est affiché « MACHINE EXCLUSIVE —
à venir » et **non réclamable** (le serveur ne le marque pas réclamé).

## B. Bonus application (serveur)

1. `CatchService` (~L177) et `InventoryService` (~L62) : ajouter
   `+ (data.bonuses and data.bonuses.sellMult or 0)` au `sellMultTotal`/`earned`.
2. `AutomationService.grantOffline` (~L40) : ajouter `+ (data.bonuses and data.bonuses.offlinePct or 0)` au `pct`.
3. `luckAdd` (CatchService ~L50) : laissé tel quel (rétrocompat, 0 par défaut).

## C. Claim (`CollectionService.claimIndexReward`)

- Requérir `UFOCatchers` + `Util.Id`.
- Boucle de claim : pour un palier atteint non réclamé —
  - si `mlt.machine` : `def = UFOCatchers.get(mlt.machine)`. Si `def` existe →
    `data.ufos[Id.new()] = { defId = mlt.machine, level = 1, prestige = 0 }` puis marquer
    réclamé. **Sinon `continue`** (machine pas encore définie → reste réclamable plus tard).
  - si `mlt.bonus` : appliquer dans `data.bonuses` (déjà en place).
  - retirer la logique `mlt.scrap` (plus de cash).
- Notify : « Bonus d'index débloqué ! » (et « Machine exclusive obtenue ! » si machine).
- Le claim reste **« réclamer tous les paliers atteints »** : cliquer un nœud « prêt »
  envoie `claimIndexReward{tab}` ; le serveur réclame tous les disponibles (UX : tous les
  nœuds prêts passent réclamés).

## D. UI — rail = « piste de récompenses » verticale (`IndexController`)

Rail élargi **150 → 190**. Contenu :
- En-tête : titre `PINCES`/`SCRAPS` + `X / Y` (blanc + contour).
- **Jauge verticale** : barre arrondie ; remplissage doré dégradé ; hauteur =
  **exacte** `count/total` (suppression du clamp 0.02 ; petit minimum visuel ~0.006
  seulement si `count>0`) ; **animée en tween** (~0.35 s) depuis 0 à l'ouverture.
- **Nœuds de paliers** positionnés à `count/total` le long de la barre, du bas (0) au
  haut (1) :
  - `sellMult` → pastille or, glyphe « $ », label « +X% revenu ».
  - `offlinePct` → pastille bleue, glyphe lune/horloge, label « +X% hors-ligne ».
  - `machine` (sommet) → pastille plus grosse, glyphe trophée, label « Machine exclusive ».
  - États : **réclamé** (vert + ✓), **prêt** (or, contour blanc, pulse, cliquable),
    **verrouillé** (gris, montre le `count` requis), **à venir** (machine non définie).
  - Clic sur un nœud prêt → claim (puis re-render).
- Plus de bouton « Récompense ! » générique (remplacé par les nœuds cliquables).

Le `IndexController` requiert `IndexRewards` (client) et lit `st.indexRewards[tab]`
(flags réclamés) + `count`/`total` pour dériver l'état de chaque nœud.

## E. UI — textes blancs + proportions

- Onglets **Pinces/Scraps** : texte blanc + contour (retirer l'override `INK`/gold-dark).
- En-têtes de rareté : déjà blancs (conserver).
- Cases possédées : `nm` (nom) et `rk` (rang) **blancs + contour** (au lieu de `INK`).
  Le `?` des cases verrouillées reste gris.
- Rail élargi → libellés des nœuds lisibles ; espacements nettoyés.

## Files touched

- `ReplicatedStorage.Shared.Config.IndexRewards` (réécriture tiers).
- `StarterPlayer.StarterPlayerScripts.Client.Controllers.IndexController` (rail track + blancs + jauge).
- `ServerScriptService.Server.Services.CollectionService` (claim machine + notify).
- `ServerScriptService.Server.Services.CatchService` (+sellMult bonus).
- `ServerScriptService.Server.Services.InventoryService` (+sellMult bonus).
- `ServerScriptService.Server.Services.AutomationService` (+offlinePct bonus).

## Out of scope / later

- Design de la **machine exclusive** (`index_exclusive_ufo`) : modèle + stats, défini
  ultérieurement ; on branche juste le `defId`.
- Icônes de nœuds : glyphes thématiques simples pour l'instant (pas d'assets marketplace).

## Verification

- `Format`/calcul : pas concerné.
- Live (Play) : ouvrir l'index, vérifier blancs + jauge tween + nœuds (états réclamé/
  prêt/verrouillé/à venir), proportions ; cliquer un nœud prêt → bonus crédité dans
  `data.bonuses` (lire via `execute_luau`), revenu/vente reflètent le `sellMult`,
  offline reflète `offlinePct`. Console sans erreur. Capture.
