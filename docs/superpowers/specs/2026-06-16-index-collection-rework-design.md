# Rework de l'Index de collection (album + récompenses) — Design

**Date :** 2026-06-16
**Statut :** Validé (design approuvé par l'utilisateur en brainstorming)
**Réf visuelle :** capture « Pet Index! » de Pet Simulator (panneau cartoon, barre de
récompenses verticale « Cash Prize! », grille de cases « ? », X rouge).
**Lien :** c'est le **sous-projet C** (album de collection + bonus de complétion) de la
refonte des pinces. Voir [[2026-06-16-claw-catalogue-expansion-design]] (sous-projet A).

---

## Contexte

Il existe déjà un menu **`StarterGui.Menus.IndexUFO`** (carte + `ScrollingFrame`), peuplé
par **`StarterPlayerScripts.UIController`** (fonction `populate("IndexUFO")`). Aujourd'hui :
- C'est une **liste de lignes** (texte + pastille de couleur), pas une grille.
- Un **toggle Pinces/Scraps** existe déjà (`idxMode`, bouton « Changer », l.167-204).
- **Pinces** = `UFOCatchers.list` (compte « possédé xN / Non débloqué » via `st.ufos`).
- **Scraps** = `LootTable.list` × `Rarities` (codex `st.collection[itemId].variants`
  keyé par `<rarityId>_<modifier>`).
- Aucun `ViewportFrame`/`WorldModel` n'est utilisé (pas d'aperçu 3D).
- Thème : `ReplicatedStorage.UI.Theme` (cartoon clair : `Palette`, `Corner`, `Stroke`,
  `Button`, `Pill`, `darken`, `Font`, `Dims`).

Données de référence confirmées :
- **31 items de scrap** (`LootTable`), classés par **rareté seule** (familles/thèmes
  supprimés 2026-06-16) ; rareté rollée au catch.
- **10 raretés loot** (`Rarities` : common→transcendent, avec `color`/`icon`/`order`) —
  **distinctes des 12 raretés de pinces** (`ClawDesign`).
- **Pinces** : 50 aujourd'hui, **120** après le sous-projet A.

---

## Objectifs

1. Reworker l'index en **page grille stylée** (réf Pet Index) : panneau cartoon, **barre de
   récompenses verticale à gauche**, **grille de cases à droite**, **X** de fermeture.
2. **2 onglets** propres **Pinces / Scraps** (rebâtir le toggle existant).
3. **Vignettes d'items** : **`ViewportFrame`** (rendu 3D du vrai modèle) pour les pinces ;
   **icônes 2D générées** pour les scraps (~31 icônes recolorées par rareté).
4. **Barre de récompenses par onglet** : **cash one-shot par palier _+_ bonus permanent**
   (palier final / set de rareté complété).
5. **Perf** maîtrisée pour ~120 cases (ViewportFrames **virtualisés**).
6. Rendu net, lisible, compréhensible.

## Non-objectifs

- **Fusion & étoiles** (sous-projet B) : l'index **affiche** le badge ★ si la pince a des
  étoiles, mais ne gère pas la fusion.
- **Refonte du catalogue/stats** (sous-projet A) : indépendant. Tant que A n'est pas
  implémenté, les vignettes pinces montrent les **modèles actuels (50)** ; elles passent
  **automatiquement** aux 120 nouveaux via le builder partagé (voir §5).
- Refonte de l'inventaire (`Inventaire`) ou des améliorations (`Ameliorations`).

---

## 1. Structure GUI (Menus.IndexUFO reconstruit)

```
IndexUFO (Frame, plein écran centré)
└─ Card
   ├─ TitleBar : Titre dynamique ("🦾 Index des Pinces !" / "⚙️ Index des Scraps !")
   │            + Onglets [Pinces | Scraps] + Close (X rouge, top-right)
   └─ Content (Frame, flex horizontal)
      ├─ RewardRail (gauche, largeur fixe ~150)
      │   ├─ Counter ("53 / 120 pinces collectées")
      │   ├─ ProgressBar (track sombre + fill doré) + marqueurs de paliers + tags
      │   └─ ClaimButton ("🎁 Récompense !")  (actif si un palier est réclamable)
      └─ GridScroll (ScrollingFrame, droite)
          └─ UIListLayout de "blocs de rareté", chacun :
             ├─ SectionHeader ("Légendaire  6/10")
             └─ CellsHolder (UIGridLayout, 5 colonnes) de Cases
```

- **Case** (Frame carré, `UICorner`, `UIStroke`) :
  - **Possédée/découverte** : bordure = **couleur de rareté** ; contenu = `ViewportFrame`
    (pince) ou `ImageLabel`/icône (scrap) ; + label **rang** (haut-gauche), **★ étoiles**
    (haut-droite, si >0), **nom** (bas, tronqué). Un `TextButton` transparent par-dessus →
    ouvre le **détail**.
  - **Inconnue** : fond neutre, gros **« ? »** (`P.Muted`), pas de ViewportFrame.
- **Détail** (clic sur une case possédée) : petit popup réutilisant `Theme` — nom, rareté,
  rang, étoiles, stats (`genStats`) / valeur, et « possédé xN » (pinces) ou raretés
  découvertes (scraps).
- **Tri/regroupement** : par rareté croissante (`ClawDesign` pour les pinces : 12 sections ;
  `Rarities` pour les scraps : 10 sections). Cases d'une section triées par rang (pinces) /
  par item (scraps).

## 2. Onglets Pinces / Scraps

- Rebâtir `idxMode` en **2 boutons-onglets** dans la TitleBar ; le clic re-peuple la grille,
  le titre, le compteur et la barre de récompenses.
- **Pinces** : `UFOCatchers.list`. Découverte = possédée (≥1 dans `st.ufos`). 12 sections de
  rareté (`ClawDesign`), 10 cases/section.
- **Scraps** : `LootTable.list` (31 items) × `Rarities` (10 raretés). 10 sections de rareté ;
  chaque section liste les items **collectables** (cases découvertes via
  `st.collection[itemId]` pour cette rareté, sinon « ? »). Même icône d'item, **recolorée**
  par la rareté de la section. ⚠️ *Point ouvert : périmètre exact = les 31 items, ou
  seulement ceux avec `uses.collect` (~17) ? L'index actuel compte les 31 ; à confirmer.*

## 3. Vignettes

- **Pinces → `ViewportFrame`** : chaque case possédée contient un `ViewportFrame`
  (+`WorldModel`) où l'on clone le **modèle de pince** construit depuis le `def`. Caméra
  cadrée automatiquement (bbox → distance/angle 3/4). **Aucun upload** ; mise à jour
  automatique quand A change les visuels.
- **Scraps → icônes 2D** : **~31 icônes vectorielles** (une par item de `LootTable`),
  construites en **primitives GUI** (Frames/ImageLabels arrondis composant un pictogramme :
  canette, tôle, boulon, circuit, pneu, vérin, noyau…) dans un module réutilisable
  `ScrapIcons` (`itemId → builder`). **Teinte = couleur de la rareté** de la section. Net,
  zéro modération/upload, recolorage trivial. *(Alternative repli : assets du Creator Store
  via `insert_from_creator_store`, ou images uploadées — décidé au plan si le rendu vectoriel
  ne suffit pas.)*

## 4. Barre de récompenses (par onglet)

- **Visuel** : barre verticale (track sombre + fill doré = `découverts/total`), marqueurs de
  paliers avec tag de récompense, bouton **« Récompense ! »** (vert) actif si un palier
  atteint n'est pas encore réclamé (sinon grisé / « Réclamé »).
- **Paliers (config `IndexRewards`, tunable)** — exemple :
  - **Pinces** : cash à **10 / 25 / 50 / 75 / 100** pinces (montants croissants) ; **bonus
    permanent** à **120** (collection complète) ; **+ bonus permanent par set de rareté
    complété** (les 10 rangs d'une rareté → ex. +chance ou +revenus, l'ampleur montant avec
    la rareté).
  - **Scraps** : cash à des paliers de **combos découverts** ; bonus permanent à la
    complétion totale (et éventuellement par rareté complétée).
- **Réclamation** : event `Net` **`claimIndexReward {tab, milestoneId}`** → le serveur valide
  (compte courant ≥ seuil **et** pas déjà réclamé dans `data.indexRewards`), crédite le cash
  ou applique le bonus permanent (`data.bonuses`), marque réclamé, renvoie l'état.
- **Bonus permanents** : stockés dans **`data.bonuses`** (ex. `luckMult`, `incomeMult`) et
  **consommés** au bon endroit (chance de roll / valeur de vente / production — points
  d'application listés au plan ; cohérent avec « specialEfficiency »/économie existante).

## 5. Dépendance clé — builder de pince accessible au client

Le `ViewportFrame` est **client-side** ; il faut un **modèle de pince constructible côté
client** depuis un `def`. Aujourd'hui `makeUFOModel` vit côté **serveur** (`PlotService`) et
n'est pas appelé par le client (grep `makeUFOModel`/`WorldModel` → aucun usage client).

**Recommandation (à coordonner avec le sous-projet A)** : extraire le builder de pince dans
un **module partagé** `ReplicatedStorage.Shared` (ex. `ClawModel.build(def, opts)`), utilisé
par : (a) `PlotService` (serveur, machines sur les parcelles), (b) l'index (client,
ViewportFrame), (c) les mini-previews de la roulette. Dé-duplique et garantit que l'index
montre exactement la vraie pince. Si A est fait d'abord, écrire son builder **directement en
module partagé**. Sinon, A et C partageront ce refactor.

*(Repli si pas de builder partagé à temps : le serveur pré-construit un template par `def`
sous `ReplicatedStorage` que le client clone — plus lourd, non retenu par défaut.)*

## 6. Performance (≈120 cases)

- Seules les cases **possédées** portent un `ViewportFrame` ; les inconnues sont de simples
  « ? » (légères).
- **Virtualisation** : n'instancier/peupler le `ViewportFrame` que pour les cases **visibles**
  dans le scroll (écoute `CanvasPosition` + marge), **pooling** des ViewportFrames recyclés
  hors champ. Cible : ≤ ~20 ViewportFrames actifs simultanément.
- Validation : en Play, ouvrir l'index avec ~50 pinces possédées et confirmer la fluidité.

## 7. Données & surfaces de code

- **Client** :
  - **Nouveau** `StarterPlayerScripts.Client.Controllers.IndexController` (sort la logique
    d'index de `UIController`, qui est déjà chargé) : `open/refresh/setTab/populate/claim`,
    construction des cases, ViewportFrames virtualisés, popup détail.
  - `UIController` : retirer l'ancien `populate("IndexUFO")` (l.167-204) ; `IndexBtn` ouvre
    et délègue à `IndexController`. Garder `open/close/overlay`.
  - **Nouveau** `ReplicatedStorage.Shared.ScrapIcons` (module d'icônes vectorielles).
  - **Nouveau/partagé** `ReplicatedStorage.Shared.ClawModel` (§5).
- **Serveur** :
  - Service de collection/récompenses (**nouveau** `CollectionService` ou extension d'un
    service existant) : calcule complétion (pinces/scraps, par rareté + total), valide et
    applique `claimIndexReward`.
  - `DataService` : nouveaux champs profil **`data.indexRewards`** (paliers réclamés par
    onglet) et **`data.bonuses`** (multiplicateurs permanents) ; répliqués dans
    `StateController` (`st.indexRewards`, `st.bonuses`).
  - Points d'application des bonus permanents (`CatchService`/`Pricing`/économie).
- **Config** : **nouveau** `ReplicatedStorage.Shared.Config.IndexRewards` (paliers + montants
  + bonus, tunable).
- **GUI** : restructurer `StarterGui.Menus.IndexUFO` (TitleBar + onglets + RewardRail +
  GridScroll). **Mode Edit requis** (GUI statique + scripts).
- **Net** : `claimIndexReward`.

## 8. Risques / points ouverts

- **Builder de pince partagé** (§5) : confirmer le chemin et coordonner avec A (le plus gros
  point technique).
- **Périmètre scraps collectables** (§2) : 31 items ou sous-ensemble `uses.collect` ; impacte
  le total du compteur (jusqu'à 31×10=310).
- **Perf ViewportFrame** : valider la virtualisation en Play.
- **Économie** : calibrer les montants cash et l'ampleur des bonus permanents (ne pas casser
  l'éco ; cohérence avec les prix de roll étendus de A).
- **Séquençage** : l'index peut être construit maintenant (vignettes = 50 pinces actuelles) ;
  il reflètera les 120 automatiquement une fois A implémenté.
- **Étoiles ★** : affichées si `data.ufos[uid].stars` existe (réservé par A, rempli par B).

---

## Séquençage recommandé

Cet index = **sous-projet C**. Idéalement **A (catalogue/visuels) puis C (cet index)** pour
que les vignettes montrent les 120 nouveaux designs — mais l'UI de l'index est **autonome**
et peut être faite avant (elle s'améliore automatiquement après A). **B (fusion)** alimente
le badge ★.
