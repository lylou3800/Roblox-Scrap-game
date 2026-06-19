# Expansion du catalogue de pinces — 120 pinces (Sous-projet A) — Design

**Date :** 2026-06-16
**Statut :** Validé (design approuvé par l'utilisateur dans la session de brainstorming)
**Langue de référence :** ce jeu est francophone ; les noms et libellés UI sont en FR.

---

## Contexte

Le jeu possède aujourd'hui un **système de 50 pinces** (les « UFO catchers », machines
placeables qui produisent le loot) : **10 raretés × 5 rangs**, entièrement **générées**
depuis `ReplicatedStorage.Shared.Config.ClawDesign` (palettes, archétypes, `genStats`)
et assemblées par `ReplicatedStorage.Shared.Config.UFOCatchers`. Les visuels sont bâtis
par `PlotService.makeUFOModel` (pelle-grappin hydraulique orange). Le roll se fait
gratuitement à la roulette (`ShopService.rollClaw`).

L'utilisateur veut **développer énormément** le nombre de pinces et leurs designs :
- **≥ 100 pinces dès le lancement.**
- Des écarts **lisibles ENTRE raretés** (on voit la rareté au premier coup d'œil).
- Des écarts **lisibles AU SEIN d'une rareté** : « du moins bon au meilleur du tier ».
- Donner **envie de collectionner** et de **roll** longtemps en boutique.
- **Rendu parfait : zéro chevauchement de texture / scintillement (z-fighting)** quand
  la caméra bouge.

Ce document ne couvre que le **sous-projet A : Catalogue & identité visuelle**. Deux
sous-systèmes connexes, évoqués pendant le brainstorming, font l'objet de leurs propres
specs (ils **dépendent de A**) :

- **Sous-projet B — Fusion & étoiles** : fusionner des pinces pour monter un niveau
  d'étoiles, menu de fusion, machine de fusion (échoppe au centre de la map, visuel
  plus tard). A **réserve** le champ `stars` mais n'implémente pas la fusion.
- **Sous-projet C — Album de collection & bonus de complétion** : album-index, sets,
  bonus permanents. A **réserve** les accroches mais n'implémente pas l'album.

---

## Objectifs (sous-projet A)

1. Passer le catalogue à **120 pinces = 12 raretés × 10 rangs**, toujours **générées**
   (équilibrage centralisé, aucun stat écrit à la main).
2. Ajouter **2 nouvelles raretés** tout en haut (chase end-game).
3. **Modèle de stats hybride** : le rang est une **échelle de puissance monotone**
   (rang 1 = le pire du tier, rang 10 = le meilleur) **+** une **saveur d'archétype**
   par rang (variété sans casser l'échelle).
4. **Langage visuel à 2 axes**, sur **un châssis paramétrique unique** :
   - **Entre raretés** : couleur + **bande de matériau** + halo + taille.
   - **Au sein d'une rareté** : **finition croissante** (détails, polissage, halo, couronne).
5. **Règles de build anti-scintillement** strictes (priorité utilisateur).
6. **120 noms** uniques, regroupés par thème de rareté.
7. **Migration sans perte** des sauvegardes existantes.

## Non-objectifs (hors sous-projet A)

- Le **système de fusion** et les **étoiles** (sous-projet B) — A se contente de réserver
  le champ `stars`.
- L'**album de collection** et les **bonus de complétion** (sous-projet C) — A réserve
  les accroches.
- Refonte du loot/`CatchService`, de l'UI d'upgrade (`ClawMenuController`), ou de la
  roulette (`ShopService`) — elles consomment le catalogue **sans changement** (voir §8).
- Création de la **micro-saveur visuelle d'archétype** : décision prise = la saveur reste
  **stats-only** (pas d'accent 3D), pour la lisibilité et le rendu net.

---

## 1. Structure du catalogue (12 × 10 = 120)

- IDs inchangés dans la forme : **`<rarityId>_<rank>`** avec `rank` ∈ **1..10**
  (ex. `legendary_7`, `eternal_10`).
- 12 raretés ordonnées par `tier` 1..12 ; 10 rangs par rareté.
- Tout est **généré** dans `UFOCatchers` à partir de `ClawDesign` (boucle
  `for rank = 1, 10`), comme aujourd'hui — on passe juste de 5 à 10 rangs et de 10 à 12
  raretés. L'API publique ne change pas : `list`, `byId`, `byRarity`,
  `getByRarityRank(rarityId, rank)`, `get(id)`, `rollClaw(luck)`.

---

## 2. Les 2 nouvelles raretés

On prolonge la table `RARITIES` au-dessus de `transcendent` (tier 10). Palettes/halo/échelle
**à ajuster librement** ; valeurs proposées (validées sur la maquette) :

| tier | id | nom FR | rôle couleur | bande matériau | fxTier | scaleMult |
|---|---|---|---|---|---|---|
| 11 | `primordial` | **Primordial** | opale / iridescent (blanc-bleuté nacré) | Cristallin → Originel | 6 | 1.66 |
| 12 | `eternal` | **Éternel** | prismatique arc-en-ciel | Prismatique | 7 | 1.74 |

- `fxTier` passe donc de 0–5 à **0–7** ; `CatchFXController` et `makeUFOModel` doivent
  gérer les 2 nouveaux paliers (halo/particules les plus spectaculaires). Aucun palier
  existant n'est modifié.
- Palettes proposées (format `{core, glow, trim}` comme les autres) :
  - `primordial` : core `{0.90,0.94,1.00}`, glow `{0.98,1.00,1.00}`, trim `{0.62,0.72,0.86}`
    (rendu **opale** : voir §4, motif facettes + reflets arc-en-ciel discrets).
  - `eternal` : core `{1.00,0.62,0.88}`, glow `{0.70,0.90,1.00}`, trim `{0.48,0.30,0.95}`
    (rendu **prismatique** : dégradé multi-teintes, voir §4).

---

## 3. Modèle de stats — échelle hybride (10 rangs)

On conserve le jeu de stats existant (`Types.UFOStats`) : `grabSpeed`, `weightCap`,
`luck`, `qualityBias`, `modifierChance`, `stability`, `multiGrab`, `specialEfficiency`.
`genStats(tier, rank)` est réécrit pour **12 tiers × 10 rangs** selon ce principe :

### 3.1 Courbe de rareté (tier 1..12)
Prolonge la courbe actuelle ; constantes **tunables** dans le bloc `BASE` de `ClawDesign` :
- `grabSpeed` base = `3.0 - 2.5 * (step/11)` (step = tier−1) → ~3.0 s au tier 1, ~0.5 s au tier 12.
- `weightCap` base = `5.0 * (1.45 ^ step)` (croissance ramenée de 1.50 à **1.45** pour que
  le tier 12 reste raisonnable, ~270).
- `luck` = `0.28*step`, `qualityBias` = `0.14*step`, `modifierChance` = `0.23*step`,
  `stability` = `0.50 + 0.040*step` (clamp ≤ 0.96), `multiGrab` = `0.045*step` (clamp ≤ 0.95).

### 3.2 Échelle de rang (1..10) — puissance monotone
- `rankPower(rank) = 0.80 + 0.06*(rank-1)` → **0.80 (rang 1) → 1.34 (rang 10)**, strictement
  croissant. Multiplie les stats « bénéfiques » vers le haut (et l'inverse sur `grabSpeed`,
  où plus bas = mieux).
- Garantit que le **rating global** (voir 3.4) est **monotone** : rang 10 = le meilleur du
  tier, sans ambiguïté.

### 3.3 Saveur d'archétype (redistribution dans le budget)
Une saveur par rang **redistribue** l'emphase (multiplicateurs ~« moyenne-préservante »
autour de 1.0), pour de la variété sans contredire l'échelle. Affectation des 10 rangs :

| rang | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|---|
| saveur | Équilibre | Force | Cadence | Précision | Équilibre | Force | Cadence | Précision | Spécialiste | **Apex** |

- Profils (héritent de l'esprit de l'actuel bloc `ARCH`) :
  - **Équilibre** : tout proche de 1.0.
  - **Force** : `weightCap`↑↑, `stability`↑, `grabSpeed` un peu plus lent, `luck`↓.
  - **Cadence** : `grabSpeed`↑↑ (plus rapide), `multiGrab`↑↑, `weightCap`↓.
  - **Précision** : `luck`↑↑, `qualityBias`↑↑, `modifierChance`↑↑, `weightCap`↓.
  - **Spécialiste** (rang 9) : un **gros** `specialEfficiency` ciblé sur **une rareté de scrap**,
    le reste neutre.
  - **Apex** (rang 10) : toutes stats hautes + `specialEfficiency` **universelle** (`"all"`).
- ✅ **`specialEfficiency` — DÉJÀ ALIGNÉ (vérifié en mode Edit 2026-06-16)** : `Types.UFOStats`
  **et** `ClawDesign` (`SpecialEfficiency = { rarity: string, mult: number }`, `genStats` lignes
  130-134) émettent **déjà** `{ rarity, mult }` (bonus de valeur sur une rareté de scrap ;
  `"all"` = universel), et `CatchService`/`ClawUpgrade` le consomment ainsi. **Aucune correction
  nécessaire** : il suffit d'étendre la table `RANKS` à 10 entrées **en conservant le champ
  `rarity` par rang** (la « rareté fétiche »). Mapping proposé (10 rangs) : balanced→`nil`,
  force→`rare`/`legendary`, cadence→`common`/`uncommon`, precision→`epic`/`mythic`,
  specialist(9)→`divine`, apex(10)→`"all"`. *(Mon analyse initiale « genStats émet family »
  venait d'un snapshot Play périmé — le vrai `build.rbxlx`, lu en Edit, est déjà en `{rarity}`.)*

### 3.4 Rating global (tri & garantie de monotonie)
- Helper `ratingOf(stats)` = somme pondérée normalisée des stats (lisible 0–100), **utilisé**
  pour : trier l'album (sous-projet C), afficher une « note » de pince, et **vérifier en test**
  que `rating(rank n) < rating(rank n+1)` pour chaque rareté. C'est l'invariant « du moins
  bon au meilleur ».

### 3.5 Poids de roll
- `RANK_WEIGHTS` (10 entrées, décroissant — le haut du tier est la chasse interne) :
  proposé `{140, 100, 72, 52, 37, 26, 17, 10, 5, 2}`.
- `rarityWeight(tier, luck)` : on garde la formule actuelle `1000 / 3^(tier-1)` étendue aux
  **12 tiers** (les T11–T12 deviennent extrêmement rares) ; la chance continue de soulever
  les tiers rares. `rollClaw` reste un tirage 2-étages (rareté puis rang).

---

## 4. Langage visuel — 2 axes sur un châssis paramétrique

**Décision (approche A « finition croissante »).** Un **seul châssis** (la pelle-grappin
orange = identité du jeu), décliné paramétriquement. La pince de **pince** (mâchoires)
reste **orange** sur toutes les raretés (couleur de marque) ; c'est le corps/cab qui porte
la rareté.

### Axe ① — ENTRE raretés (lecture « quelle rareté »)
Pilote par `rarity` (palette + `fxTier` + `scaleMult`) **et** une **bande de matériau** par
paliers, pour que T1 et T12 soient visuellement aux antipodes :

| tiers | bande | rendu 3D (sans z-fight) |
|---|---|---|
| 1–3 | **Acier peint** | `Material.Metal` mat, couleur de rareté, peu de greebles |
| 4–5 | **Métal brossé + néon** | métal clair + un liseré `Neon` (part séparée, en relief) |
| 6–7 | **Énergisé** | arêtes lumineuses (parts Neon offset) + petites particules |
| 8–9 | **Cristallin** | inserts translucides facettés (parts distinctes), halo |
| 10 | **Warp** | aura intense + distorsion (particules), `fxTier 5` |
| 11 | **Originel / opale** | facettes nacrées + reflets arc-en-ciel discrets, `fxTier 6` |
| 12 | **Prismatique** | dégradé multi-teintes + aura prismatique, `fxTier 7` |

→ couleur + bande + halo + taille = la rareté se lit instantanément.

### Axe ② — AU SEIN d'une rareté (lecture « quelle place dans le tier »)
Pilote par `rank` via un **niveau de finition 1..10** ; la couleur/bande de la rareté est
**figée**, seule la finition monte :
- **Densité de greebles** (rivets, vents, antenne, phares, tuyaux) : 0 → max.
- **Polissage** : mat → satiné → liseré **chrome** (rangs ~6+) → **trim doré** (rangs ~9+).
- **Halo** : intensité croissante (part Neon/aura dédiée).
- **Couronne / fleuron** au sommet : petit fleuron rang 9, **couronne** rang 10.

→ détails + polissage + halo + couronne = « du moins bon au meilleur du tier » se lit d'un
coup d'œil.

### Implémentation
`PlotService.makeUFOModel(ufoDef, prestige, baseCF)` est étendu pour lire :
- `ufoDef.rarity` → palette, **bande de matériau**, `fxTier`, `scaleMult` ;
- `ufoDef.rank` → **niveau de finition** (greebles/polish/halo/crown).

Le builder garde les **noms de parts/tags critiques** (`Claw`, `ClawJaw`/`ClawTip`,
`ArmPivot`, `Glow`, `WarnLight`, `Aura`, `FeedbackAnchor`, tag `UFOCatcher`) pour ne pas
casser les FX (`CatchFXController`) ni l'animation de mâchoires (Motor6D). Les greebles et
trims sont des **parts additionnelles** clairement nommées (préfixe `Detail_`) montées en
relief/encastré (voir §5).

---

## 5. Règles anti-scintillement (rendu net) — NORMATIF

Toute la génération du châssis **doit** respecter :

1. **Aucune face coplanaire.** Deux surfaces qui se superposent ne partagent jamais la même
   hauteur/plan : l'élément ajouté est **encastré** (poussé dans le corps) ou **en relief**
   d'au moins **~0.03 stud**. (Même discipline que les correctifs déjà documentés du projet :
   tops décalés, `BaseRim` sous le bord, etc.)
2. **Pas de décals qui se chevauchent** sur une même face. Priorité à
   **`Material` + `Color`** et, si besoin, **une seule `Texture`/`SurfaceAppearance` par
   face**, dimensionnée à la face (jamais deux textures empilées).
3. **Bandes/trims/liserés = parts distinctes** légèrement en relief, **pas** des décals posés
   à plat sur le corps.
4. **Halos / auras = parts `Neon` distinctes, à rayons différents** ; jamais deux coques
   transparentes coplanaires (sinon scintillement quand la caméra bouge). Transparences
   échelonnées.
5. **Inserts (vitres, vents, facettes cristallines)** = parts **encastrées** avec un vrai jeu,
   ou un seul part texturé — jamais un part fin posé pile sur la surface.
6. **Couronne/greebles** montés avec un **petit standoff** (jeu) par rapport à la surface.
7. Le tableau de bord/board de feedback (`FeedbackAnchor`) et les SurfaceGui restent
   **world-fixed** où c'est déjà le cas ; pas de GUI coplanaire.

**Critère de recette :** en mode Play, faire tourner la caméra autour d'une pince de chaque
bande de matériau (T1, T5, T7, T9, T10, T12) et confirmer **zéro scintillement** aux jonctions.

---

## 6. Les 120 noms (approche : noms uniques par thème de rareté)

Le **rang** n'est PAS dans le nom (il s'affiche en chiffre + étoiles via l'UI). Chaque rareté
est un **univers thématique**. Liste complète (rang 1 → 10) :

- **Commun** (atelier/manutention) : Pince d'Atelier · Crochet de Manutention · Griffe de Tri ·
  Pince Convoyeur · Bras d'Établi · Pince Cargo · Crochet Robuste · Griffe Tandem ·
  Pince Cadence · Pince Contremaître
- **Peu commun** (chantier) : Bras Stator · Fourche Hydraulique · Pince Sprint ·
  Griffe Sélective · Pince Chantier · Bras Levier · Griffe Ratisseuse · Pince Relais ·
  Atelier Pro · Pince Chef d'Équipe
- **Rare** (industriel) : Grappin Vector · Bras Hydraulique XL · Pince Dash · Scanner Grip ·
  Bras Tracteur · Griffe Cyclone · Pince Vortex · Bras Magnéto · Pince Forge ·
  Pince Surintendant
- **Épique** (high-tech) : Griffe Sigma · Bras Hydra · Pince Turbo · Omni Claw · Bras Plasma ·
  Griffe Onyx · Pince Spectre · Bras Quantum · Pince Nova · Pince Archimède
- **Légendaire** (titans) : Bras Atlas · Griffe Titan · Pince Colosse · Magnus Clamp ·
  Bras Goliath · Griffe Hyperion · Pince Prométhée · Bras Cronos · Pince Orion · Pince Olympe
- **Mythique** (créatures) : Bras Aegis · Chimère Grip · Griffe Manticore · Pince Wyverne ·
  Bras Basilic · Griffe Phénix · Pince Hydre · Omni Scanner MK-II · Pince Léviathan · Pince Séraph
- **Relique** (sacré/ancien) : Pince Ancienne · Bastion Clamp · Griffe Templier · Relic Scanner ·
  Bras Oracle · Pince Paladin · Griffe Reliquaire · Pince Sanctuaire · Forge Relique ·
  Pince Excalibur
- **Divin** (céleste) : Archon Claw · Dominus Arm · Griffe Séraphique · Judicator Grip ·
  Bras Empyrée · Pince Halo · Griffe Ambroisie · Pince Aurora · Celestium Clamp · Pince Panthéon
- **Cosmique** (espace) : Pulsar Claw · Quasar Arm · Griffe Supernova · Singularity Grip ·
  Bras Galaxion · Pince Nébula · Griffe Andromède · Bras Astral · Event Horizon Clamp ·
  Pince Zénith Cosmique
- **Transcendant** (au-delà) : Apex Claw · Paradox Arm · Griffe Infinité · Final Judge Grip ·
  Bras Ascendant · Pince Nirvana · Griffe Absolue · Origin Clamp · Pince Oméga · Pince Transcendance
- **Primordial** ✦ *(nouveau)* (origine/opale) : Pince Genèse · Bras Primordial · Griffe Aube ·
  Pince Éclosion · Bras Originel · Griffe Iridia · Pince Opaline · Bras Chaos Premier ·
  Griffe Aurore · Pince Big Bang
- **Éternel** ✦ *(nouveau)* (éternité/prisme) : Pince Éternité · Bras Infini · Griffe Prisme ·
  Pince Alpha-Oméga · Bras Sempiternel · Griffe Chromatique · Pince Perpétuelle · Bras Immortel ·
  Griffe Arc-en-Ciel · Pince Absolu

*(Noms ajustables : ce sont des propositions cohérentes par thème ; l'utilisateur peut en
renommer n'importe lequel sans impact technique.)*

---

## 7. Données, API & migration

- **`ClawDesign`** : `RARITIES` passe à 12 entrées (ajout `primordial`, `eternal`) ; `RANKS`
  passe à **10 entrées** (avec `archetype`/saveur ; `specialEfficiency` = `{ rarity, mult }`, cf. §3.3) ;
  `NAMES` passe à **12 × 10 = 120** ; `genStats` réécrit (§3) ; `RANK_WEIGHTS` à 10 entrées.
- **`UFOCatchers`** : boucle `for rank = 1, 10` × 12 raretés (génération inchangée dans le
  principe). API stable. Ajout d'un helper `ratingOf` (ou exposition depuis `ClawDesign`).
- **`Types.UFODef`** : inchangé (porte déjà `rank`, `rarity`, `palette`, `fxTier`,
  `scaleMult`…). **Données joueur** : `data.ufos[uid] = { defId, level, stars }` — `stars`
  **ajouté et réservé** (défaut `1`), non utilisé par A (sous-projet B le consommera).
- **Migration (sans perte) :**
  - `LEGACY_REMAP` conservé (`ufo_basic`/`ufo_collector`/`ufo_prism` → ids actuels).
  - **Remap de rang** pour les sauvegardes de l'ère « 5 rangs » : dans `get()`, un id
    `<rarity>_<r>` issu d'un profil où le rang signifiait « 1..5 » est remappé
    **`{1→1, 2→3, 3→5, 4→7, 5→10}`** afin que l'ancien « rang 5 = meilleur » devienne le
    nouveau « rang 10 = meilleur » (on ne lèse pas les joueurs). ⚠️ Détail d'implémentation à
    cadrer : distinguer un ancien `_5` d'un nouveau `_5` légitime — proposé : un flag de
    version de schéma sur le profil (`data.clawSchema`), migration **one-shot** au chargement
    (DataService), puis tous les ids sont « nouveau schéma ». À valider au moment du plan.

---

## 8. Intégration (consommateurs du catalogue — sans changement de leur logique)

- **Roulette (`ShopService`)** : roll déjà via `UFOCatchers.rollClaw(luck)` et prix dérivé de
  `tier`/`rank` (`priceOf = round(100 * tier^2 * (1 + 0.3*(rank-1)))`). Avec 12 tiers / 10 rangs,
  les bornes s'étendent automatiquement (prix max plus élevé pour T12/rang 10) — **vérifier**
  que la formule de prix reste cohérente (pas de débordement, montants lisibles).
- **Affichage des pinces** : roulette (`makePrize`/previews) et plots utilisent
  `PlotService.makeUFOModel` → les 120 visuels arrivent dès que le builder gère
  rareté+rang (§4). Les **previews de plots** et **RoulettePreview** statiques devront être
  **re-bakées** (générateur Edit-mode) pour refléter le nouveau châssis — à inclure au plan.
- **Bannière « NOUVELLE PINCE ! »** (`CatchFXController` sur event `newClaw`) : inchangée.
- **FX de catch** (`CatchFXController`) : gérer `fxTier` 6 et 7 (2 nouveaux paliers d'aura).
- **Accroches réservées** (non implémentées en A) : champ `stars` (pour B) ; un index
  collection par `defId` (12×10) + un registre de bonus de complétion (pour C).

---

## 9. Surfaces de code concernées

- `ReplicatedStorage.Shared.Config.ClawDesign` (raretés, rangs, noms, `genStats`, poids).
- `ReplicatedStorage.Shared.Config.UFOCatchers` (génération du catalogue, `rollClaw`, remap).
- `ReplicatedStorage.Shared.Types` (champ `stars` sur les données joueur).
- `ServerScriptService.Server.Services.PlotService` → `makeUFOModel` (châssis paramétrique,
  bandes de matériau, finition par rang, règles anti-z-fight). **Visible uniquement en mode
  Edit** (généré au runtime ; non visible en Play) — implémentation en Edit, `build.rbxlx`
  = source de vérité.
- `StarterPlayer…Client.Controllers.CatchFXController` (paliers `fxTier` 6/7).
- `ShopService` (sanity-check de la formule de prix sur la plage étendue).
- Générateur Edit-mode des **previews** (plots + roulette) à re-baker.
- `DataService` (migration one-shot du schéma de pinces, §7).

---

## 10. Risques / points ouverts

- **Localiser & ouvrir les générateurs serveur en mode Edit** (PlotService non visible en
  Play). Studio est actuellement en **Play** — repasser en Edit pour lire/modifier.
- **Coût visuel des bandes de matériau** : cristallin/prismatique/warp doivent rester
  **performants** (parts Neon + particules maîtrisées) et **sans z-fight** (§5).
- **Migration de rang** (§7) : bien distinguer ancien vs nouveau schéma pour ne pas
  re-remapper des ids déjà migrés (flag de version + one-shot).
- **Équilibrage** : valider l'invariant `rating(rang n) < rating(rang n+1)` par rareté
  (test généré), et que T11/T12 ne cassent pas l'éco (prix/poids de roll).
- **Re-bake des previews** obligatoire après changement du châssis (sinon plots libres /
  roulette montrent l'ancien design).

---

## Séquençage global (rappel)

**A (ce doc)** → **B : Fusion & étoiles** → **C : Album & bonus de complétion**.
Chaque sous-projet aura sa propre spec → plan → implémentation.
