# Spec — Rework du tas de scrap devant les machines ("Contained Feed Mound")

**Date:** 2026-06-19
**Statut:** Validé (design approuvé) + durci par revue adversariale 6-lentilles ; prêt pour plan d'implémentation.
**Périmètre:** Décor — remplacer le tas de scrap procédural par baie par un tas riche, basé meshes, thématisé par rareté et lié à la machine posée.

> **Note de révision (2026-06-19) :** ce spec intègre les corrections d'une revue adversariale contre `build.rbxlx` (lentilles : fidélité-code, cycle-de-vie, échelle-rareté, perf-instanciation, ancrage-composition, complétude). Corrections clés : **16 baies/plot** (pas 8) ; **seed dérivé du slotId** (displayNum indisponible dans refreshSlot) ; **heapCF en espace-origine** (le passage par pad.CFrame*yaw inversait le côté pour la rangée droite) ; **suppression des instances déjà bakées** via re-bake ; **recolor par `BasePart.Color` uniquement** (meshes non texturés) ; **pivot mesh bottom-center** ; passe anti-flottement **bloquante**.

---

## 1. Contexte & état actuel

Chaque plot possède **16 baies** : `s1..s8` (RDC, `floor=0`) **et** `f1..f8` (étage, `floor=1`). `MAX_PLOTS = 8`. Le tas de scrap actuel est généré dans `buildBay(model, origin, slotDef, displayNum)` — appelé **deux fois** : pour le RDC dans `assemblePlot` (`build.rbxlx:1092068`, `slotDef.floor==0`) **et** pour l'étage dans `buildFloor2` (`build.rbxlx:1091651`, `slotDef.floor==1`).

Anatomie actuelle du tas (≈ `build.rbxlx:1524-1551`) :
- **1 socle** : *Ball* Slate 12 × 4.6 × 13.5, gris RGB(78,84,96), à `pileC = zc + (-outer*12.5, 0, 0)`, posé `origin * CFrame.new(pileC + (0,1.0,0))`.
- **22 `DebrisBit_`** dispersés par `Random.new(displayNum*7+13)` ; 6 « kind » (blocs, cylindres/tuyaux, plaques).
- **1 bit Neon** vert au sommet.
- `SCRAP_COLORS` = **8 entrées** (6 saturées rouge/bleu/jaune/vert/gris/orange + 2 gris neutres RGB(120,132,150), RGB(196,202,212)). Déjà cartoon, cohérent AD.
- `makePart` (`:1091045`) : `Anchored=true`, `Material=Plastic`. `bayPart` (`:1091475`) : `CanCollide=false`.

**Défauts (= la demande) :** rotations 100 % aléatoires (0–3 rad sur 3 axes) ; hauteurs en dispersion polaire jusqu'à 3.4 **sans logique de support → des bits flottent** ; uniquement des primitives ; socle = grosse boule grise informe ; aucune hiérarchie ni intention.

**Pur décor :** aucun script ne référence `DebrisPile`/`DebrisBit` (grep). Le modifier ne peut pas casser le gameplay.

**Instances déjà bakées (à supprimer, pas juste le générateur) :** 64 `DebrisPile_*` + 1473 `DebrisBit_*` sont sérialisées dans les 8 `PlotPreview_*` de `build.rbxlx`. Éditer `buildBay` ne les retire pas — voir §3.4 / §8 (re-bake).

### 1.1 Modèle de rareté de la machine (source de la cohérence)

Machine posée dynamiquement par `refreshSlot(player, slotId)` (`:1091338`) : si `slotData.ufoUid`, construit `ClawModel.build(ufoDef, owned.prestige, baseCF)` (`:1091388`, modèle `UFO_<slotId>`) ; détruit au retrait via `clearSlotVisual` (`:1091317`, ne touche **que** `UFO_<slotId>`). `ufoDef = UFOCatchers.get(defId)` ; `UFOCatchers.rarities = ClawDesign.RARITIES`.

`ClawDesign.RARITIES` = **12 paliers** (`tier` 1→12 : common…eternal). Chaque palier : `palette = { core{r,g,b}, glow{r,g,b}, trim{r,g,b} }` (RGB 0–1), `fxTier` (0–7), `scaleMult` (1.00→1.74), `materialBand` ∈ {`paint`,`metal`,`energized`,`crystal`,`warp`,`prism`}.

**`materialBand` n'est PAS monotone :** t1–3 `paint`, t4–5 `metal`, t6–7 `energized`, t8–9 `crystal`, **t10 `warp`**, **t11 `crystal` (retour)**, **t12 `prism`**. (Cf. §6 qui gère ce cas.)

`ClawModel.build` consomme **déjà exactement** ces données → un builder de tas parallèle lisant la même échelle garantit **un langage visuel unique**. `ufoDef.rarity` est l'**id string** de rareté, résolu par `ClawDesign.getRarity(id)`.

**Modèle d'amélioration (corrigé) :** une pince posée ne change **jamais** de `rank`/`defId` (le rang est figé dans le `defId`, ex. `common_5`). Le prompt « Améliorer » pilote deux ops : `upgradeClaw` → `owned.level+1` seulement (**ne rappelle PAS refreshSlot**, zéro rebuild visuel) ; `transformClaw` → `owned.prestige+1` (level reset) et **appelle `refreshClaw`→`refreshSlot`**. La rareté est **invariante** sous les deux ops → le visuel du tas (clé = rareté) est intrinsèquement stable.

### 1.2 Géométrie spatiale de la baie

- `pad` au centre du slot (`slotDef.offset`), 7×1×7, centre y +0.55, sommet y +1.05. `ring` Ø 7.6. `ZoneFloor` sommet ≈ y +0.34, `ZoneInset` au-dessus.
- `UFO_HOVER = 0.5` ; `baseCF = pad.CFrame * CFrame.Angles(0, yaw, 0) * CFrame.new(0, UFO_HOVER, 0)`, `yaw = (slotDef.offset.X > 0) and π or 0`.
- `outer = (slotDef.offset.X < 0) and -1 or 1` ; `innerX = -outer` (côté **allée**).
- `pileC = zc + (-outer*12.5, 0, 0)` placé **sans yaw** : `origin * CFrame.new(pileC + …)`. `-outer = innerX` → **le tas est déjà côté allée (devant)**. ⚠️ Cette placement est en **espace-origine, non tourné** — voir §5 (heapCF).
- `SLOT_PROMPT_DIST = 18`. NamePlate : `BillboardGui` ancré ~19 studs au-dessus du pad (un tas ≤ 4.5 ne peut pas le masquer ; il n'y a **pas** d'hologramme sur la machine).

---

## 2. Décisions validées (brainstorming)

1. **Sourcing — hybride.** Recolorer les meilleurs meshes Creator Store vers la palette, combler les manques en Blender, lier avec un peu de gravats procéduraux.
2. **Thématisation — distincte par rareté**, en **échelle paramétrique** sur `tier` 1–12 (plus riche/brillant en montant), pas 12 tas peints à la main.
3. **Baies vides — petit tas neutre gris** (slot débloqué-vide) ; **rien** (slot verrouillé) ; **thématisé** (occupé).
4. **Composition — « Contained Feed Mound »** : monticule dômé dans une benne acier basse ; hiérarchie grosse base → médian → petit sommet ; pièce *hero* à la couronne.

---

## 3. Architecture

### 3.1 Nouveau module `ScrapHeapBuilder` (miroir de `ClawModel`)

> Nommé **`ScrapHeapBuilder`** (pas `ScrapHeap`) pour éviter la collision de grep avec les instances/decor existants nommés « ScrapHeap » et la clé DecorLibrary « ScrapHeap ».

Emplacement : **`ReplicatedStorage.Shared.ScrapHeapBuilder`** (miroir de `ReplicatedStorage.Shared.ClawModel`, requis par PlotService à `:1091064`). **Ne requiert QUE `ReplicatedStorage.Shared.Config.ClawDesign`** (config feuille, acyclique) ; il ne requiert ni PlotService ni UFOCatchers — `refreshSlot`/`buildPreviewPlot` lui passent le `ufoDef` déjà résolu.

API :
```lua
ScrapHeapBuilder.build(ufoDef: UFODef?, seed: number, baseCF: CFrame) -> Model
```
- `ufoDef == nil` → **tas neutre « tier 0 »** (baie vide / preview).
- `ufoDef` fourni → `ClawDesign.getRarity(ufoDef.rarity)` → palette/materialBand/fxTier/tier.
- `seed` → mélange la **sélection de variante** par rôle (jamais le nombre de rôles) + jitter borné (déterministe).
- `baseCF` → CFrame d'ancrage **en espace-origine** (voir §5).
- Retourne un `Model` `Anchored`, attribut `Rarity` = `ufoDef.rarity` ou `"neutral"` ; nommé par l'appelant `Heap_<slotId>`. Aucun script runtime (statique une fois construit).

**Seed (corrige le blocker) :** `displayNum` n'existe pas dans `refreshSlot`. Définir un seed **dérivé du `slotId` seul**, identique côté runtime et côté preview-bake :
```lua
local function heapSeed(slotId: string): number
    local n = 0
    for i = 1, #slotId do n = n + string.byte(slotId, i) * i end
    return n
end
```
(Le même slot → toujours le même tas, sur plot joueur ET sur PlotPreview.)

### 3.2 Kit d'assets — `ReplicatedStorage.Assets.ScrapKit` (à créer)

**N'existe pas encore.** Livrable : créer un `Folder` `ScrapKit` sous `ReplicatedStorage.Assets` (à côté de `ClawMeshes`/`PetMeshes`/`EggMeshes`), peuplé de **MeshParts non texturés** (pas de `SurfaceAppearance`), nommés par rôle exact que `ScrapHeapBuilder.build` cherchera via `FindFirstChild` (miroir de `ClawModel`/`ClawMeshes`).

**Contrats de mesh (corrige le piège de recentrage) :** Roblox recentre chaque MeshPart sur sa bbox à l'import/clone. Donc **chaque mesh du kit est normalisé pour que son pivot = bottom-center** (ou bien on stocke sa demi-hauteur dans un manifeste `ScrapKitManifest`). Le layout pose alors chaque pièce à `supportTopY + pieceHalfHeight` (pas « center on Y »).

Rôles & **pools de variantes** (chaque rôle a ≥1 variante ; le seed choisit laquelle, jamais « rien ») :

| rôle | qté/tas | variantes | exemples |
|---|---|---|---|
| `Container` | 1 (fixe) | 1–2 | benne acier basse open-top (front rabaissé) |
| `Base_*` (grosses) | 3 (fixe) | 4–6 | fût écrasé, panneau cintré, gros engrenage/bloc |
| `Mid_*` (médianes) | 4 (fixe) | 5–7 | tuyaux droit+coude, chute IPN, bloc moteur, moyeu/jante, canister |
| `Small_*` (accents) | 3 (fixe) | 4–6 | grappe boulons, ressort, petit pignon, tôle froissée |
| `Hero_*` (couronne) | 1 (fixe) | par bande matériau | pépite → lingot → cristal → cœur prisme |
| `Rubble_*` (procédural) | **0–2** | primitifs | éclats recolorés (liant + ancrage) |

→ Base de composition = **12 instances** (1+3+4+3+1). Neutre tier-0 = sous-ensemble (≈ 8).

### 3.3 Cycle de vie — branché dans `refreshSlot` (slot-agnostique : RDC **et** étage)

- **`clearHeap(info, slotId)`** (détruit `Heap_<slotId>`) appelé **inconditionnellement** à côté de `clearSlotVisual` (≈ `:1091363`), **AVANT** le `return` anticipé de la branche verrouillée (`:1091377`). → aucun tas fantôme ne survit à un verrouillage/rebuild.
- **Slot occupé** (`slotData.ufoUid` + `ufoDef`) : `ScrapHeapBuilder.build(ufoDef, heapSeed(slotId), heapCF)`, parenté dans `info.model`, nommé `Heap_<slotId>`, attribut `SlotId`.
- **Slot débloqué vide** : `ScrapHeapBuilder.build(nil, heapSeed(slotId), heapCF)` (tas neutre). **(Ajout requis :** la branche « Placer la pince » à `:1091426` ne construit aujourd'hui aucun modèle.)
- **Slot verrouillé** : rien (le `clearHeap` inconditionnel a déjà nettoyé).
- **Pas de skip-optimisation :** `refreshSlot` reconstruit déjà tout le modèle machine à chaque appel ; le tas (clone+recolor, **≤** coût d'un build machine) le suit inconditionnellement. La rareté étant invariante sous upgrade/transform, le rebuild est au pire **redondant**, jamais incorrect. Le tas suit donc exactement le cycle de vie machine existant (y compris sur join, où `refreshSlot` recrée les machines occupées).

### 3.4 Suppression de l'ancien tas + previews

1. Retirer de `buildBay` la génération `DebrisPile_`/`DebrisBit_` (socle + boucle 22 + neon). `buildBay` ne produit plus de tas.
2. **`buildPreviewPlot` (`:1092463`) doit appeler explicitement** `ScrapHeapBuilder.build(nil, heapSeed(slotId), heapCF)` par slot débloqué, parenté/nommé `Heap_<slotId>` — car les previews **n'appellent jamais `refreshSlot`** (« AUCUNE machine, AUCUN prompt »). Sans cet ajout, les previews re-bakées n'auraient **aucun** tas.
3. **Suppression des instances déjà bakées :** `EditPreviewBaker.run()` (`:1095305`) fait `old:Destroy()` sur tout le dossier `PlotPreviews` (`:1095308-1095309`) puis reconstruit. C'est **uniquement** ce re-bake qui efface les 64 `DebrisPile_*` + 1473 `DebrisBit_*` et bake les nouveaux `Heap_*` neutres. **Ordre de bake :** (1) éditer `buildBay` + `buildPreviewPlot` + `refreshSlot`/`ScrapHeapBuilder` ; (2) re-run `EditPreviewBaker.run()`.

---

## 4. Pipeline d'assets (la phase de recherche imposée, transformée en méthode)

### Phase 1 — Recherche (Creator Store via `search_asset`)
Thèmes : scrap, junk, metal debris, industrial junk, machine parts, broken pipes, gears, barrels/drums, pipes, I-beams, pallets/skips, canisters, springs, bolts. Présélection : meshes **stylisés** low/mid-poly, sets cohérents, silhouettes nettes, **recolorables = NON TEXTURÉS** (pas de SurfaceAppearance ; sinon le recolor par `Color` est inopérant — cf. §7), **libres/insérables** (permissions vérifiées). Liste de candidats (asset IDs + thumbnail).

### Phase 2 — Test & analyse (dans `build.rbxlx`, jamais `recovery.rbxl`)
Insérer dans une zone de staging, voir à l'échelle **à côté d'une vraie machine**, `screen_capture`, **noter sur grille** :
- [ ] Style colle (cartoon premium, ni réaliste ni cheap) — [ ] Recolorable (non texturé) vers palette rareté — [ ] Proportions — [ ] Silhouette lisible à distance — [ ] Enrichit sans confondre — [ ] Premium > cheap — [ ] Échelle correcte — [ ] Se marie avec la machine — [ ] Coût (tris/poly) raisonnable.

Shortlist notée ; rejet des inadaptés ; **documenter le set retenu** (asset IDs + rôle dans le kit). Normaliser chaque mesh (pivot bottom-center, cf. §3.2).

### Phase 3 — Combler les manques en Blender
Rôles sans bon asset Store — **prioritairement le `Container` (benne)** et les `Hero_*` par bande matériau. Pipeline prouvé : Blender (un objet par zone couleur, **non texturé**) → addon « Upload to Roblox » (Open Cloud, asset MODEL) → `InsertService:LoadAsset` + repositionnement (Roblox recentre → cf. contrats §3.2).

### Phase 4 — Liant procédural
`Rubble_*` primitifs recolorés (0–2/tas), très peu coûteux, pour combler les vides, unifier la palette, verrouiller l'ancrage.

---

## 5. Composition & ancrage — « Contained Feed Mound »

Monticule dômé **dans la benne acier basse**. La benne pose sur le sol de baie → **ancre la couche de base**.

**Construction en couches (déterministe, layout écrit à la main) :**
1. `Container` posé : plancher de benne sur le `ZoneFloor`/`ZoneInset` (sol de baie).
2. `Base_*` (3) reposant sur le plancher de la benne — chaque pièce posée à `floorTopY + pieceHalfHeight`.
3. `Mid_*` (4) nichées dans les creux / sur des pièces de base — chacune **déclare une pièce de support** ; posée à `supportTopY + pieceHalfHeight`.
4. `Small_*` (3) calées dans les interstices (même règle de support).
5. `Hero_*` (1) à la couronne, débordant légèrement la lèvre avant vers l'allée.

**Réglages :** inclinaisons contrôlées (±~15–25° sur un axe de repos, face ~plate vers le bas) ; **pas** de spin 0–3 rad. Le **seed ne choisit que la variante de chaque rôle (pool jamais vide) + un jitter borné** → bays différentes mais toujours bien composées.

**Garantie anti-flottement (corrigée — pas « par construction ») :** la benne n'ancre que la base ; les pièces hautes reposent sur d'autres pièces via leur **référence de support** déclarée. La garantie **autoritaire** est la **passe anti-flottement au bake (§8), BLOQUANTE** (échec dur, pas seulement log).

**Empreinte/placement :** ~8–10 large × 8–10 profond, **hauteur ≤ ~4.5** (raison : garder le **corps de la machine** héros / silhouette lisible — pas une question de nameplate). `CanCollide=false`.

**heapCF (corrige le blocker de côté) :** calculer **en espace-origine, exactement comme `pileC` actuel**, sans router par `pad.CFrame*yaw` (qui inverse le côté pour la rangée `offset.X>0`). Dans `refreshSlot`/`buildPreviewPlot` (qui ont `info.origin` et `slotDef`) :
```lua
local outer  = (slotDef.offset.X < 0) and -1 or 1
local innerX = -outer
local heapCF = info.origin * CFrame.new(slotDef.offset + Vector3.new(innerX * D, baseY, frontZ))
-- D ≈ 10–12 (resserré vs 12.5) ; frontZ ≈ 0 ; baseY tel que le plancher benne pose sur le ZoneFloor/ZoneInset.
-- L'orientation interne du modèle (face hero vers l'allée) est appliquée DANS le modèle, pas sur l'offset.
```
**Valider en Studio sur les DEUX rangées** (`offset.X>0` ET `offset.X<0`) avant bake : un test mono-rangée masque le bug de signe. `baseY` de départ : plancher benne ≈ sol de baie (`ZoneInset` top), ajuster ±0.3 en Studio.

---

## 6. Échelle de rareté (paramétrique sur `tier` 1–12)

Lit `ClawDesign.getRarity(id)` → `palette` / `materialBand` / `fxTier` (mapping vérifié conforme au config, **t11=crystal** inclus) :

- **Couleur** (via `BasePart.Color` uniquement) : base = `trim` (sourd) ; médianes = mix `trim`+`core` ; accents/hero = `core`/`glow`. Bas paliers ≈ gris scrapyard + soupçon de teinte ; hauts paliers saturés.
- **Matériau (`materialBand`) :** `paint`(t1–3)=SmoothPlastic/Metal peint mat · `metal`(t4–5)=Metal réfléchissant · `energized`(t6–7)=Metal + **parts Neon** d'accent · `crystal`(t8–9,**11**)=Glass/Glimmer + cœur Neon · `warp`(t10)=irisé/Neon · `prism`(t12)=accents arc-en-ciel. **Toute « brillance » passe par `Material` + parts Neon/Glass séparées, jamais par SurfaceAppearance** (qui écraserait `Color`).
- **fxTier (0–7) — caps concrets :** parts Neon d'accent ≤ 2/tas, activées seulement `fxTier ≥ 2`. Particules (sparkle) seulement `fxTier ≥ 3`, `Rate ≤ 6`, `MaxParticles ≤ 15`, 1 émetteur max/tas. (Aligne la rigueur sur le gating `fxTier` de `ClawModel`.)
- **Richesse :** haut palier → swap 1–2 pièces premium + upgrade de la couronne `Hero_*` ; **nombre de pièces ~constant** (perf) — la **qualité** monte, pas la **quantité**. `scaleMult` peut légèrement agrandir le hero.
- **Tas neutre (tier 0, baie vide/preview) :** benne + ~7 pièces grises, **aucun** Neon ni particule (variante la moins chère, dominante car omniprésente).

---

## 7. Budget performance (rebasé sur 16 baies/plot)

- **Composition ≤ 18 instances/tas** (cap dur 20) : `Container 1 + Base 3 + Mid 4 + Small 3 + Hero 1` = **12**, + ≤ 4 accents/FX (Neon/particule) + ≤ 2 `Rubble` = **≤ 18**. Neutre ≈ **8**.
- **Recolor = `BasePart.Color` (miroir `ClawModel`)** sur MeshParts **non texturés** partageant ~12–16 `MeshId` → **instanciation rendu** préservée (l'instanciation tient si Material identique **et** pas de SurfaceAppearance/TextureID ; teinter via `Color` ne casse pas le batch ; **un SurfaceAppearance par teinte casserait** le batch → proscrit).
- **Worst-case résident :**
  - Live : `MAX_PLOTS 8 × 16 baies = 128` tas max (mais seulement occupés + débloqués-vides ; verrouillés = 0).
  - Bakés : 8 `PlotPreview` × (8 RDC [+ étage si baké]) tas neutres **toujours résidents** — ~64+ tas neutres (variante la moins chère).
  - Géométrie partagée (MeshId) → peu de draw calls malgré le compte ; `CanCollide=false` → 0 physique.
- **Net par état de slot** (vs ~24 primitives sur **chaque** des 16 baies aujourd'hui, y compris verrouillées) : **verrouillé 24 → 0** (gain net) ; **occupé/vide 24 primitives → ≤ 18 meshes** (neutre-à-mieux en draw calls grâce à l'instanciation ; mémoire/instance un peu plus haute en mesh). Plus léger qu'un build machine (`ClawModel.build` émet des dizaines de parts).
- Aucun script per-frame ; FX plafonnés (§6). Construction = clone template + recolor.

---

## 8. Vérification & déploiement

**Prérequis bloquant :** `build.rbxlx` **ouvert & actif** en Studio, **mode Edit** — **pas** `recovery.rbxl` (seule instance ouverte, en Play, **incomplète** : il lui manque le script plot-builder). Confirmer via `list_roblox_studios` + `set_active_studio` avant toute édition. **Ne jamais sauvegarder `recovery.rbxl` par-dessus `build.rbxlx`.**

**Rollback :** `build.rbxlx` est git-tracké mais binaire (`.gitattributes : *.rbxlx -text -diff`) → revert **fichier entier** seulement. **Avant le bake : commit `build.rbxlx` (ou snapshot `.bak`)**, afin qu'un re-bake raté soit annulable par `git checkout`/restauration.

Étapes :
1. Créer `ReplicatedStorage.Assets.ScrapKit` (meshes non texturés, pivot bottom-center, nommés par rôle).
2. Écrire `ReplicatedStorage.Shared.ScrapHeapBuilder` (require `Config.ClawDesign` seulement).
3. Éditer `refreshSlot` (clearHeap inconditionnel + build occupé/vide) ; retirer le tas de `buildBay` ; ajouter le build neutre dans `buildPreviewPlot`.
4. Re-run `EditPreviewBaker.run()` (efface l'ancien debris + bake les `Heap_*` neutres).
5. **Passe coplanaire/z-fight** (règle projet : décaler les faces ≥ 0.04).
6. **Passe anti-flottement BLOQUANTE** : raycast/AABB sous chaque pièce ; **échec dur** si une pièce n'a pas de support dans la tolérance.
7. **Validation visuelle Studio** : captures angle d'approche + distance, plusieurs raretés (common / médian / eternal) + tas vide, **les deux rangées** (offset.X ±). Confirmer : lisible, ancré, machine héros, prompts atteignables (dist 18), pas de débordement allée, bon côté.
8. Test séquence : place → transform (prestige) → unequip → re-lock → join avec slot déjà occupé. Aucun tas orphelin/doublon.

---

## 9. Hors périmètre / non-objectifs

- Pas de changement aux modèles machine, pads, prompts, gameplay, logique de catch.
- Le scrap décor **séparé** = la prop DecorLibrary clé `"ScrapHeap"` posée dans la **zone roulette** (`placeDecor(hub,"ScrapHeap",…)`, `:1092835`, via `buildRouletteGeometry`) **et/ou** les 8 instances bakées `Decor_ScrapHeap` (décor par plot, ex. `:312180`). Ni l'un ni l'autre n'est « dans le hub ». → follow-up optionnel (réutiliser le kit), hors périmètre principal.
- Pas de collision/physique sur les débris.
- Hero meshes Blender « finaux » au-delà des rôles manquants : non requis (meshes Store recolorés suffisent ; Blender comble les trous).

---

## 10. Risques & mitigations

| risque | mitigation |
|---|---|
| Studio actif = `recovery.rbxl` incomplet, en Play | **Bloquant** : exiger `build.rbxlx` en Edit ; warning anti-écrasement |
| Re-bake raté (fichier 40 MB binaire) | Commit/snapshot `build.rbxlx` avant bake ; revert fichier entier |
| Seed indisponible dans refreshSlot | `heapSeed(slotId)` déterministe, partagé runtime/preview (§3.1) |
| heapCF inverse le côté (rangée offset.X>0) | Offset en **espace-origine** comme `pileC` ; valider **les deux rangées** en Studio (§5) |
| Instances bakées non supprimées | Re-bake `EditPreviewBaker.run()` (`old:Destroy()` + rebuild) (§3.4) |
| Recolor inopérant sur mesh texturé | Phase 1 exige meshes **non texturés** ; recolor par `Color`, brillance par `Material`/Neon (§6/§7) |
| MeshPart recentré sur bbox → flotte/s'enfonce | Pivot bottom-center + pose `supportTopY + halfHeight` (§3.2/§5) |
| Flottement résiduel | Passe anti-flottement **bloquante** au bake (§8) |
| Budget instances (8 plots × 16 baies + previews) | MeshId partagés, cap ≤18/tas, tas seulement si actif/vide, neutre = variante la moins chère |
| FX coûteux × beaucoup de tas | Caps concrets : Neon ≤2 (fxTier≥2), particules fxTier≥3 Rate≤6 Max≤15 (§6) |
| z-fighting (faces coplanaires) | Passe détecteur coplanaire + offset ≥ 0.04 |
| `refreshSlot` régressions | clearHeap inconditionnel avant le return verrouillé ; tas suit le cycle machine ; test séquence (§8) |
