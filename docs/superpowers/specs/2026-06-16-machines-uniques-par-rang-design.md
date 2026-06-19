# Machines uniques par rang — 10 archétypes × 12 raretés — Design

**Date :** 2026-06-16
**Statut :** Validé (brainstorming approuvé par l'utilisateur — « je valide », implémentation autorisée)
**Langue de référence :** jeu francophone ; noms/libellés UI en FR.
**Blueprint exhaustif (sortie workflow 14 agents) :** `tasks/wplfjv9bq.output` (taxonomie 40 modules, escalade 12 raretés, panneau-nom, 10 fiches archétype, passe de cohérence). Ce doc en est la synthèse implémentable.

---

## Contexte & problème

Le catalogue **120 pinces = 12 raretés × 10 rangs** est en place côté données (`ClawDesign`) et rendu par un **builder unique** `ReplicatedStorage.Shared.ClawModel.build(ufoDef, prestige, baseCF)`. `PlotService.makeUFOModel` y délègue, `IndexController` et `ShopService` l'utilisent → **tout le rendu passe par ce builder**.

**Problème (utilisateur) :** au sein d'une rareté, les 10 rangs (I→X) **se ressemblent tous**. Le builder ne produit **qu'une seule silhouette** (pelle-grue chenillée) et ne fait varier que `boomThick`, `tineN` (4/5/6), un glow « precision » et la couronne « apex ». Pire : `archetype` (la clé visuelle actuelle) n'a que **6 valeurs répétées** (rang 1=5=balanced, 2=6=force, 3=7=cadence, 4=8=precision, 9=specialist, 10=apex) → rangs 1 et 5 seraient **identiques** de forme.

**Objectif :** au sein d'une rareté, les 10 rangs deviennent **10 machines radicalement différentes** (formes uniques), tout en gardant une lecture rareté instantanée. Dopamine maximale à chaque catch. Un **petit panneau-nom** flotte au-dessus (nom + rareté + rang), discret, visible à l'approche.

---

## Le modèle (validé)

> **Le RANG choisit la FORME (10 archétypes distincts). La RARETÉ choisit la PEAU (palette + matériau + FX + échelle) et fait escalader des modules cosmétiques. → 10 formes × 12 peaux = 120 machines toutes uniques.**

- **Production :** un **kit modulaire d'~40 modules** (8 familles-slots) assemblés par le builder. **23 modules procéduraux** (parts Roblox, créés en code) + **17 meshes héros** (Blender). Les **9 meshes déjà uploadés** (Base, Cab, Counterweight, Boom, Stick, Elbow, ClawHub, Jaw, Tip) couvrent le tronc tête/bras → **les 10 formes sont livrables en procédural d'abord**, les meshes Blender élèvent ensuite les silhouettes signature.
- **Pas de changement de données.** `ufoDef.rank` (1..10) **arrive déjà** dans le builder (lu ligne 31). On branche la forme sur `rank` directement — **aucune modif de `ClawDesign`/`UFOCatchers`/schéma joueur**. `archetype` reste la clé **stats** (table `ARCH`), `rank` devient la clé **silhouette**.

### Décision clé (simplification vs blueprint)
Le blueprint proposait un nouveau champ `def.shapeId=rank`. Inutile : `rank` est déjà disponible dans `build()`. On l'utilise tel quel comme sélecteur de silhouette.

---

## 1. `ClawModel.build` devient un ROUTEUR de silhouettes

```
build(ufoDef, prestige, baseCF):
  skin = resolveSkin(ufoDef)      -- palette core/glow/trim, materialBand, fxTier, scaleMult, tier
  ctx  = makeContext(model, BASE, skin, prestige)   -- helpers part()/welded()/beam() + S (échelle)
  geo  = SHAPES[clamp(ufoDef.rank,1,10)](ctx)        -- sous-builder par rang -> renvoie {pivotCF, headAnchor, topY, cabX...}
  buildTrunk(ctx, geo)            -- TRONC COMMUN: ArmPivot + bras + Claw(ClawHub) + N ClawJaw(JawMotor)+ClawTip
  applySkin(ctx, geo)             -- bande de matériau + escalade rareté (neon/cristal/halo/crown/levitation)
  applyRankFinish(ctx, geo)       -- densité greebles + polish (chrome rang6+/doré rang9+) + finial rang9 + crown rang10
  addNamePlateAnchor(ctx, geo)    -- part 'NamePlateAnchor' (la GUI est posée par le client)
  addFX(ctx, geo)                 -- PointLight/Aura selon fxTier (inchangé)
  model:AddTag("UFOCatcher")
```

- **`SHAPES[1..10]`** = un sous-builder par archétype (voir §3). Chacun pose **base + corps + locomotion + mât** propres à sa forme, puis renvoie un `geo` décrivant **où** ancrer le tronc commun (épaule/`pivotCF`, hauteur du sommet pour le panneau, `cabX`, `tineN`…).
- **Tronc commun** (`buildTrunk`) = **identique aux 120** : c'est l'identité de marque + le **contrat d'animation**. Il porte `ArmPivot`, le bras (Boom/Stick/Elbow), `Claw`, les `N` `ClawJaw` sur `JawMotor`, `ClawTip`. Le nombre de griffes `tineN` vient d'une **table par rang** (§4), plus de l'`archetype`-stats.

### Contrat technique INTANGIBLE (sinon FX/anim cassent)
Noms/tags/joints **inchangés**, quelle que soit la silhouette : `Root` (PrimaryPart invisible) · `ArmPivot` (ancré, attribut `RestCF`, **rotation Z = plongée vers +X**) · `Claw` (moyeu = ClawHub) · `ClawJaw` ×N (`Motor6D` **JawMotor**, attribut `OpenAngle`, **C1 = pose fermée bakée**) · `ClawTip` (weld) · `FeedbackAnchor` (invisible) · `Aura` (ParticleEmitter) · `Glow` (Neon) · tag **`UFOCatcher`**. Build en **CFrame monde** (`pivotCF*localCF` soudé unanchored), **jamais `PivotTo`**. Le **corps/base = parts ancrées** ; **le bras+tête+griffes = soudés à `ArmPivot`** (pour plonger en bloc). `CatchFXController.animateClaw` ne lit que `ArmPivot`/`Claw`/`JawMotor`/`RestCF` → il **tolère n'importe quelle silhouette et n'importe quel `tineN`** (vérifié dans le code).

---

## 2. Le kit modulaire (40 modules, 8 slots) — synthèse

Détail complet (forme, tris, notes Blender, anti-z-fight, procédural/héros) dans le blueprint. Familles :

| Slot | Modules | Héros (Blender) | Procéduraux (code) |
|---|---|---|---|
| **base** | Deck_Chassis, Track_Crawler, Wheel_Heavy, Skid_Rail, TripodLeg, HoverPod_AntiGrav, SpiderLeg | Deck, Track, HoverPod | Wheel, Skid, TripodLeg, SpiderLeg |
| **body** | Cab_Wedge, Counterweight_Block, TurretRing, DrillColumn, PressFrame, ReactorCore, TitanTorso, Body_Glass | Cab, DrillColumn, ReactorCore, TitanTorso | Counterweight*, TurretRing, PressFrame, Body_Glass |
| **arm** | Boom_IBeam, Stick_IBeam, Elbow_Joint, Piston_Hydraulic, Hose_Conduit, Arm_Ram | Boom, Stick | Elbow*, Piston, Hose, Arm_Ram |
| **mast** | Mast_Pole, RadarDish, SensorBoom, ExhaustStack, WarnBeacon | (RadarDish si concavité) | Mast, SensorBoom, ExhaustStack, WarnBeacon |
| **head** | ClawHub, Rotator_Wrist, GrappleCap | ClawHub* | Rotator, GrappleCap |
| **jaw** | ClawJaw, ClawTip | ClawJaw*(Jaw) | ClawTip*(Tip) |
| **topper** | Crown_Ring, Finial_Crest, Halo_Disc, CrystalShard | — | tous |
| **greeble** | Lug, RailKit, Headlight, Vent, Toolbox, HazardStrip, RivetPanel, CoreGlow, **HoverGlow (ajout)** | — | tous |

(*) mesh déjà uploadé et réutilisé à l'identique (origine figée pour le contrat de joints).

**Correctifs intégrés depuis la passe de cohérence :**
- **Ajouter `Greeble_HoverGlow`** (procédural) — disque/anneau Neon sous chaque buse de pod (manquant du kit).
- **`tineN` par rang** (table, découplé des stats) — §4.
- **Modules cosmétiques A4** (LaserSight_Reticle / OpticCamera_Pod / Iris_Aperture) — procéduraux, non bloquants, pour vendre le « scanner ».
- **Invariants d'exclusivité** : `RadarDish` exclusif à A4 ; `Crown_Ring` de base réservé à A10 (les autres ne l'ont qu'en escalade apex de tier) ; **locomotion hover réservée à A7 en base** (les autres reçoivent seulement un *accent* de lévitation `HoverGlow` aux hauts tiers — on **ne swappe pas** la locomotion pour préserver l'identité d'archétype).

---

## 3. Les 10 archétypes (recettes — `rank` → forme)

Montée de grandeur du rang 1 (humble) au rang 10 (colosse). Tous finissent par le **tronc commun** (pince animée).

| Rang | Archétype | Base | Corps | Bras / spécifique | Mât / props | tineN |
|---|---|---|---|---|---|---|
| **1** | **Chariot-Griffe** | Deck + Wheel ×4 | Cab_Wedge | Boom/Stick courts | — | 5 |
| **2** | **Grue à Fléau** | Deck + Track ×2 | Counterweight | Boom/Stick longs (treillis) | SensorBoom (contre-flèche) | 4 |
| **3** | **Tourelle Rapide** | Deck + Skid ×2 | TurretRing | double bras fin | — | 3 |
| **4** | **Sentinelle Scanner** | Deck + TripodLeg ×3 | TurretRing | bras moyen | Mast_Pole + **RadarDish** (+ Laser/Optic) | 5 |
| **5** | **Foreuse Tarière** | Deck + TripodLeg ×3 (stab.) | DrillColumn | Boom court | tête de forage | 5 |
| **6** | **Presse Bélier** | Deck + Skid/Wheel | PressFrame | **Arm_Ram** (au lieu du bras) + Piston ×2 | — | 5 |
| **7** | **Hover-Drone** | Deck + **HoverPod ×4** | Cab_Wedge bas | Boom/Stick rétractables | Halo_Disc | 4 |
| **8** | **Araignée Octo-Bras** | Deck + **SpiderLeg ×8** | TitanTorso/nacelle (ReactorCore + Body_Glass = yeux) | Boom/Stick | — | 6 |
| **9** | **Réacteur Forge** | Deck + Track ×2 | **ReactorCore** (+CoreGlow) | Boom/Stick | **ExhaustStack ×4** | 5 |
| **10** | **Colosse Couronné** | TripodLeg/SpiderLeg (pylônes) | PressFrame (demi-portique) + TitanTorso | **2 bras** (Boom/Stick ×2) + Arm_Ram (poing) | **Crown_Ring** | 6 |

**Anim spéciale A6/A10 :** l'`Arm_Ram` est **soudé à `ArmPivot`** → il plonge avec la descente générique, zéro code en plus (reste dans le contrat).

---

## 4. `tineN` par rang (découplé des stats)

```
JAW_N = { [1]=5, [2]=4, [3]=3, [4]=5, [5]=5, [6]=5, [7]=4, [8]=6, [9]=5, [10]=6 }
```
La fonction `hingedJaw` boucle déjà sur `tineN` et bake la pose fermée en C1 par tine → **3 et 6 griffes fonctionnent** (recalcul du jeu inter-tines ≥ 0.05, surtout pour 3 longues dents).

---

## 5. Escalade par rareté (peau, par-dessus le mesh)

On **garde** le pilotage par `materialBand` (déjà en code) et on **enrichit** les substitutions cosmétiques. La **forme** (locomotion/corps) reste **figée par l'archétype** ; seule la peau escalade.

| band | tiers | rendu (parts procédurales ajoutées) |
|---|---|---|
| `paint` | 1–3 | core mat peint, Glow **éteint** (T1) → 1 liseré Neon timide (T2/T3), peu de greebles cosmétiques |
| `metal` | 4–5 | métal satiné + `Greeble_HazardStrip` **chrome** en relief |
| `energized` | 6–7 | arêtes `Glow` Neon (montants) + `Halo_Disc` + particules `Aura` |
| `crystal` | 8–9, 11 | `CrystalShard` inserts facettés + halo ; `ClawTip` acier → **cristal** |
| `warp` | 10 | `Halo_Disc` multi-rayons + particules intenses + **accent lévitation `HoverGlow`** sous la base |
| `prism` | 12 | `CrystalShard` prismatique + `Halo` arc-en-ciel + lévitation prismatique |

- **Couleur** = `palette` (core/glow/trim), **échelle** = `scaleMult` (1.00→1.74), **FX** = `fxTier` (0→7, déjà géré numériquement — pas de trou à 6/7).
- **Couronne** : de base au rang 10 (tous tiers) ; sur les **apex de tier** (hauts tiers), un fleuron/couronne s'ajoute aussi.
- **LOD/budget** : plafonner `CrystalShard` (~110 tris, nombre limité), `Halo`/`Crown` en primitives Neon légères, **masquer greebles+cristaux secondaires au-delà d'une distance** pour tenir le pire cas **A10×T12** sous ~9k tris.

---

## 6. Le panneau-nom (billboard à l'approche)

- **Builder :** ajoute une part invisible **`NamePlateAnchor`** au-dessus du sommet (`cabX, deckTop + cabH + (hasCrown and 7.8 or 6.6)*S, 0`), **sœur** de `FeedbackAnchor` (qui reste pour les popups de catch, plus bas). Stocke l'identité en attribut : `model:SetAttribute("DefId", ufoDef.id)`. **Pas de GUI côté builder** (il tourne aussi en serveur/preview/ViewportFrame).
- **Client : nouveau `NamePlateController`** (StarterPlayerScripts, chargé par le bootstrap des controllers). Sur `CollectionService` add/remove du tag `UFOCatcher`, peuple un `BillboardGui` **`NamePlate`** sur l'ancre :
  - **Card** (coins arrondis + UIStroke, ombre portée) façon `Theme.Panel`, `LightInfluence=0`.
  - **Titre** = `def.name` (LuckiestGuy, `Theme.Font.Title`, TextStroke).
  - **MetaRow** = `Theme.Pill` recoloré à `def.palette.glow` (texte `def.rarityName` MAJ ; gradient arc-en-ciel pour transcendent/eternal) + **bloc rang** (`def.roman` en P.Gold + N étoiles ★, N=rank, petites).
  - **Taille** `UDim2.fromOffset(220, 96)` (offset pur → taille écran constante, « juste assez »), `AlwaysOnTop=false` (profondeur naturelle).
- **Fade par proximité** (controller, Heartbeat throttle ~7 Hz) : `SHOW=55`, `FULL=38`, `HIDE=62` studs ; alpha = `clamp01((SHOW-d)/(SHOW-FULL))` ; tween 0.15 s aux franchissements ; **ne garder actifs que les ~10 panneaux les plus proches** (anti-mur d'étiquettes). `GUI.Enabled=false` au-delà de HIDE.
- **Contrat :** on n'ajoute QUE `NamePlateAnchor` + une GUI client, hors subtree animé → FX/anim de catch intacts.

---

## 7. Surfaces de code & propagation

- **`ReplicatedStorage.Shared.ClawModel`** — réécriture en routeur (§1) + escalade peau + rank-finish + `NamePlateAnchor`. **Source unique** : plots (`refreshSlot`), roulette (`makePrize`, plateformes, mini-previews), index (`IndexController` ViewportFrame) en héritent automatiquement.
- **Nouveau `StarterPlayer…Controllers.NamePlateController`** (panneau client).
- **`MapBlockout.PlotPreviews.PlotPreview_0..7`** statiques → **re-bake** via `execute_luau` en Edit (sinon plots libres = ancien châssis).
- **`ReplicatedStorage.Assets.ClawMeshes`** — nouveaux MeshParts héros (Deck, Track, HoverPod, DrillColumn, ReactorCore, TitanTorso, PressFrame, RadarDish) ajoutés au fil de l'eau (enhancement ; le procédural fonctionne sans).
- **`CatchFXController`** — inchangé (anim générique tolère les 10 formes ; fxTier 6/7 déjà numérique). Idle `WarnLight`/`Glow`/`ArmPivot` sway → on garde ces noms sur chaque archétype.
- **`addon.py`** + `Elements_Blender/` — pipeline Blender→Roblox (Open Cloud) pour les meshes héros.

---

## 8. Ordre d'implémentation (du tronc qui débloque les 120 → feuilles)

- **Phase 0 — Routeur (pur code, 0 mesh) :** `ClawModel.build` branché sur `rank`, `SHAPES[1..10]`, `buildTrunk` partagé, table `JAW_N`, module procédural `Greeble_HoverGlow`. **Débloque la distinction des 120.**
- **Phase 1 — 10 silhouettes procédurales** (réutilise les 9 meshes pour le tronc + primitives pour base/corps/mât). Toutes les formes deviennent distinctes **immédiatement et de façon fiable**.
- **Phase 2 — Panneau-nom** (ancre + `NamePlateController`).
- **Phase 3 — Test Studio** : build des 10 archétypes à des CFrames de test, screenshots, vérif anim (descente/jaws) + **zéro z-fight** (caméra tournante sur T1/T5/T7/T9/T10/T12).
- **Phase 4 — Escalade peau** (12 tiers) + LOD + re-bake `PlotPreviews`.
- **Phase 5 — Meshes héros Blender** (Deck, Track, HoverPod, DrillColumn, ReactorCore, TitanTorso, PressFrame, RadarDish) : modéliser (objet séparé par zone, origine=centre, `_ibeam` bbox exact), upload Open Cloud, extraire dans `ClawMeshes`, brancher dans le builder. **Enhancement** — élève les silhouettes sans casser le procédural.
- **Phase 6 — Cosmétiques A4** (Laser/Optic/Iris) + polish final + `Ctrl+S`.

---

## 9. Critères de recette

1. **Lisibilité 2 axes** : au sein d'une rareté, les 10 rangs sont **10 machines visiblement différentes** ; la rareté se lit au premier coup d'œil (peau).
2. **Z-fight** : caméra tournante autour d'une pince de chaque bande (T1/T5/T7/T9/T10/T12) → **zéro scintillement**.
3. **Animation** : catch jouable sur **chaque** archétype (descente `ArmPivot` + ouverture/fermeture `JawMotor` + remontée), sans overshoot ; repos griffes fermées poisées bas.
4. **Panneau-nom** : apparaît à l'approche, discret, nom + pastille rareté colorée + rang (romain + étoiles) ; ≤ ~10 panneaux affichés à la fois.
5. **Propagation** : plots, index (viewports), roulette (prix + plateformes + mini-previews), `PlotPreview_0..7`, bannière « nouvelle pince » → tous le nouveau rendu.
6. **Perf** : pire cas A10×T12 sous ~9k tris (LOD) ; plusieurs machines + index ouvert fluides.
7. **Régression** : FX de catch, Motor6D mâchoires, prompts E/R, feedback board — intacts.

---

## 10. Risques / points ouverts

- **Distinction de forme = pur code** (Phase 0/1) : c'est le cœur ; le reste est cosmétique/enhancement.
- **`tineN` 3 et 6** : recalcul du jeu inter-tines en C1 (anti-interpénétration), surtout 3 longues dents.
- **A10×T12 budget tris** : LOD obligatoire (masquage greebles/cristaux à distance).
- **Meshes héros Blender** : origine=centre (BOUNDS), bbox exact pour Boom/Stick (`_ibeam` DIFFERENCE only), têtes (ClawHub/Jaw/Tip) origine **non bougée** (C0/C1 en dépendent). Upload Open Cloud asynchrone.
- **Re-bake `PlotPreviews`** obligatoire après changement du châssis.
- **Studio en Edit** (OK actuellement) ; `Ctrl+S` après édition ; vérifier les edits par read-back (gotchas MCP).
