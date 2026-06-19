# Refonte visuelle Blender des 120 pinces — Design

**Date :** 2026-06-16
**Statut :** En cours de validation (brainstorming)
**Langue de référence :** jeu francophone ; noms/libellés UI en FR.

---

## Contexte

Le catalogue **120 pinces = 12 raretés × 10 rangs** (sous-projet A) est **déjà en place côté
données** dans `ReplicatedStorage.Shared.Config.ClawDesign` : 12 raretés (avec `primordial`
et `eternal`), `genStats`/`rankPower`/`ratingOf`, `RANK_WEIGHTS` (10 entrées), `fxTier` 0–7,
`scaleMult`, et **un champ `materialBand`** par rareté (`paint|metal|energized|crystal|warp|prism`).

Côté **rendu**, l'état actuel est dédoublé et inachevé :
- `ServerScriptService…PlotService.makeUFOModel` : builder **procédural** historique (blocs `Part`),
  ne consomme **pas** `materialBand` ni la finition de rang. C'est lui qui tourne en jeu.
- `ReplicatedStorage…ClawModel.build` : module **partagé serveur+client** créé pour devenir le
  builder unique, mais son corps est aujourd'hui **une copie** du procédural — la « material band »
  et la finition de rang sont planifiées, **pas implémentées**, et `makeUFOModel` ne lui délègue
  pas encore.

L'utilisateur veut : modéliser les pinces dans **Blender** (style grappin industriel « orange-peel »
de scrapyard, cf. photo de réf — bras hydraulique orange + griffe multi-tines), **animation
parfaite**, raretés différenciées entre elles **et** au sein d'une rareté (comme aujourd'hui),
importer dans Roblox, rendre jouable, et **mettre à jour tous les visuels impliqués** (plots, index,
roulette shop, previews…). Rendu « dopamine MAX », textures **optimisées Roblox**, proportions
parfaites, **zéro z-fighting**.

## Décisions de brainstorming (validées)

1. **Stratégie 3D : un rig maître paramétrique.** UN seul modèle Blender détaillé, décliné par
   rareté (couleur/matériau/halo/échelle) et par rang (greebles/finition/couronne) **en code**,
   par-dessus le mesh. Cohérent avec la génération centralisée, 1 import, perf max.
2. **Animation : Motor6D piloté par code.** Chaque griffe = MeshPart sur son `JawMotor` Motor6D ;
   descente du bras + ouverture/fermeture + jeu de vérins animés par TweenService. Garde le contrat
   FX/anim existant, aucun import de squelette.
3. **Rendu : cartoon-stylisé scrapyard.** Silhouette/détails de la photo, mais **Color3 +
   matériaux Roblox** par zones (corps orange, vérins acier, rouille suggérée par teinte).
   **Aucune image de texture lourde** (donc pas de « textures » au sens images uploadées — c'est
   géométrie détaillée + zones de couleur + matériaux). Conforme à la DA cartoon et à la règle
   anti-z-fight.
4. **Budget géométrie : ~6-9k tris / machine** (équilibré). Meshes hero détaillés + petits greebles
   en primitives.

## Non-objectifs

- Pas de refonte des **stats/données** du catalogue (sous-projet A déjà fait), ni du loot/`CatchService`,
  ni de l'UI d'upgrade, ni de l'économie roulette (formule de prix). Ils **consomment** le visuel sans
  changement de logique.
- Pas de textures PBR / SurfaceAppearance uploadées (rejeté : lourd, jure avec le cartoon, tension
  z-fight).
- Pas de squelette/armature Blender (rejeté : import complexe, dur à varier, recâblage FX).
- Pas de mesh unique par pince (rejeté : budget Roblox + casse la génération centralisée).

---

## 1. Architecture cible : un builder unique à base de meshes

- **`ClawModel.build(ufoDef, prestige, baseCF)` devient LE builder unique**, réécrit pour assembler
  des **MeshParts** clonés depuis des templates, et pour consommer `ufoDef.materialBand` + `ufoDef.rank`.
- **`PlotService.makeUFOModel` devient un délégué fin** : `return ClawModel.build(...)`. Tous les
  consommateurs en aval héritent du nouveau rendu :
  - machines de plot live (`refreshSlot`),
  - prix roulette `makePrize` (réutilise déjà `PlotService.makeUFOModel`),
  - 6 plateformes roulette + mini-previews silhouette (`RouletteRollController`/`FXKit`),
  - previews `ViewportFrame` de l'index (`IndexController`) — à router explicitement sur `ClawModel.build`
    s'ils construisent encore leur propre modèle.
- **Templates de meshes** : uploadés une fois depuis Blender, stockés **nommés** dans
  `ReplicatedStorage.Assets.ClawMeshes` (sauvés dans `build.rbxlx`). Le builder **clone** ces templates
  au runtime — **jamais** de `InsertService:LoadAsset` en jeu. ReplicatedStorage garantit la
  réplication client (indispensable aux previews index/roulette côté client).

### Contrat à préserver à l'identique (sinon FX/anim cassent)
Noms/tags et structure de joints **inchangés** :
`Root` (PrimaryPart, invisible) · `ArmPivot` (ancré, invisible, attribut `RestCF`) · `Claw` (moyeu
grappin) · `ClawJaw` (×N, attribut `OpenAngle`, joint `JawMotor` Motor6D avec C0/C1 standard) ·
`ClawTip` (weldé à sa griffe) · `FeedbackAnchor` (invisible) · `Aura` (invisible, ParticleEmitter) ·
`Glow` (Neon) · tag modèle `UFOCatcher`. Build en **CFrame monde** (`BASE*cf`), assemblage soudé
unanchored, **jamais `PivotTo`** (ne réplique pas sur un assemblage soudé).

---

## 2. Le rig Blender (grappin « orange-peel » de scrapyard)

Un seul rig maître, modélisé en **objets séparés par zone de couleur/fonction**, cartoon-optimisé
(~6-9k tris pour tout l'assemblage), normales propres, échelle de base = échelle actuelle des parts.

**Meshes hero (MeshParts) :**
- **Base chenillée** : `Track` (×2, silhouette trapue), `Deck`/châssis + capot.
- **Cabine** `Cab` + `Counterweight` (portent la couleur de rareté).
- **Bras articulé** : `Boom` → `Elbow` → `Stick`, + `Piston` (vérin) et `Hose` (durites).
- **Tête grappin** : `Claw` (moyeu/rotateur) + `GrappleCap` + `Knuckle`.
- **Griffe orange-peel** : **UN seul mesh `ClawJaw`** (griffe incurvée, profil de la photo) +
  `ClawTip`. **Instancié N fois** autour de l'anneau (N = 4/5/6 selon archétype cadence/balanced/force)
  ⇒ un seul asset couvre toutes les variantes de tines.

**Greebles légers** (rivets, rails, antenne, vents, toolbox, headlights) : restent des **primitives**
bon marché ou sont bakés dans les meshes hero — ils servent aussi d'**échelle de finition par rang**
(voir §4).

**Modélisation anti-z-fight (NORMATIF) :** chaque objet exporté est **centré sur son origine locale =
centre de la part actuelle** (le builder garde les mêmes CFrames). Inserts/bandes/trims = **parts
distinctes** en relief/encastrées ≥ 0.03 stud, jamais coplanaires. Pas de faces qui se superposent
au même plan.

---

## 3. Animation « parfaite » (Motor6D piloté par code)

- **Repos** : bras *dipped* bas, grappin poisé au-dessus de la pile, griffes **fermées**
  (`RestCF` = pivot.CFrame). Les N griffes referment en corolle (grip serré encodé dans C1).
- **Séquence de catch** (polie dans `CatchFXController`) :
  1. **Descente** : rotation de `ArmPivot` vers la pile (+X), easing doux, **sans overshoot**
     (conforme aux correctifs déjà documentés).
  2. **Ouverture** des griffes (`JawMotor.Transform = +OpenAngle`).
  3. **Plongée + fermeture/serrage** synchronisée.
  4. **Remontée** vers la pose de repos.
- **Jeu de vérins** : léger mouvement du `Piston`/durites synchronisé à l'ouverture pour la lisibilité
  hydraulique.
- La variation rareté/rang **ne touche jamais** au rig de joints (mesh + couleurs seulement) ⇒ l'anim
  reste identique pour les 120 pinces.

---

## 4. Langage visuel à 2 axes (par-dessus le mesh, en code)

### Axe ① — ENTRE raretés, via `materialBand`
| band | tiers | rendu (parts procédurales en plus du mesh) |
|---|---|---|
| `paint` | 1–3 | métal mat peint à la couleur de rareté, peu de greebles |
| `metal` | 4–5 | métal brossé clair + liseré `Neon` (part séparée en relief) |
| `energized` | 6–7 | arêtes lumineuses Neon offset + petites particules |
| `crystal` | 8–9, 11 | inserts translucides facettés (parts distinctes) + halo |
| `warp` | 10 | aura intense + distorsion (particules), `fxTier 5` |
| `prism` | 12 | dégradé multi-teintes + aura prismatique, `fxTier 7` |

Couleur = `palette` (`core/glow/trim`) ; taille = `scaleMult` (1.00 → 1.74) ; FX = `fxTier` 0–7.

### Axe ② — AU SEIN d'une rareté, via `rank` (1→10) = niveau de finition
- **Densité de greebles** (rivets, vents, antenne, phares, durites) : 0 → max.
- **Polissage** : mat → satiné → liseré **chrome** (rang ~6+) → **trim doré** (rang ~9+).
- **Halo** : intensité croissante (part Neon/aura dédiée).
- **Fleuron** rang 9, **couronne** rang 10 (petite part procédurale, standoff).

Tout l'ornement (Neon, inserts, couronne, particules) = **parts procédurales** ajoutées au mesh,
**jamais coplanaires** : standoff ≥ 0.03 stud, transparences échelonnées, halos à rayons différents,
pas de textures empilées (règles anti-z-fight du spec catalogue, NORMATIVES).

---

## 5. Surfaces visuelles mises à jour (exhaustif)

- ✅ **Machines de plot** (live, `refreshSlot`) — via `ClawModel.build`.
- ✅ **Roulette** : prix (`makePrize`), 6 plateformes, mini-previews silhouette
  (`RouletteRollController`/`FXKit`) — réutilisent le builder.
- ✅ **Index collection** : previews `ViewportFrame` (`IndexController`) — routés sur `ClawModel.build`.
- ✅ **PlotPreviews statiques** `PlotPreview_0..7` — **re-bakés** via le générateur Edit-mode
  (sinon les plots libres montrent l'ancien châssis).
- ✅ **`CatchFXController`** : gère `fxTier` **6 et 7** (auras des 2 nouvelles raretés) + séquence
  d'anim polie (§3).
- ✅ **Bannière « NOUVELLE PINCE ! »** : inchangée (consomme le modèle).

---

## 6. Pipeline Blender → Roblox & edge cases

- **Pipeline** (déjà validé sur le baril) : modélisation procédurale Blender (objet séparé par zone) →
  addon officiel « Upload to Roblox » (Open Cloud) → Studio → **extraction des MeshParts** dans
  `ReplicatedStorage.Assets.ClawMeshes` (sauvé dans `build.rbxlx`). Le builder clone ensuite ces
  templates.
- **Recentrage bbox Roblox** : Roblox recentre les MeshParts sur leur bbox ⇒ chaque objet est exporté
  **centré sur son origine = centre de la part actuelle**, pour que CFrames et C0/C1 Motor6D restent
  inchangés. Vérifier le `Size` natif de chaque MeshPart importé.
- **Hinge des griffes** : le mesh `ClawJaw` est centré comme la part `ClawJaw` actuelle ; la charnière
  reste portée par C0/C1 (relatifs aux CFrames de parts) ⇒ aucune retouche math.
- **Une seule griffe instanciée N×** : N varie (4/5/6) ⇒ le mesh doit être symétrique/radial pour
  être posé proprement autour de l'anneau quel que soit N.
- **scaleMult jusqu'à 1.74** : meshes lisibles à toutes les échelles (scale uniforme).
- **`fxTier` 6/7** : vérifier/étendre `CatchFXController` pour 2 paliers d'aura supplémentaires.
- **Previews client** : doivent cloner depuis `ReplicatedStorage` (meshes répliqués) et ne dépendre
  d'aucune logique serveur.
- **Précondition Studio** : doit être en **mode Edit** (actuellement Play). `build.rbxlx` = source de
  vérité ; **Ctrl+S** après édition ; vérifier les edits par **read-back séparé** + confirmer `Mode`
  (gotchas MCP : `multi_edit` peut no-op silencieux ; Play compile un snapshot périmé juste après un
  edit).
- **Compat ascendante** : ne **jamais** renommer parts/tags du contrat (§1).

---

## 7. Surfaces de code concernées

- `ReplicatedStorage…ClawModel` (réécriture du builder : meshes + `materialBand` + finition rang +
  ornements anti-z-fight).
- `ServerScriptService…PlotService.makeUFOModel` (devient délégué) + re-bake générateur `PlotPreviews`.
- `StarterPlayer…CatchFXController` (paliers `fxTier` 6/7 + polissage anim).
- `IndexController` / `RouletteRollController` / `FXKit` (router previews sur `ClawModel.build` si besoin).
- `ReplicatedStorage.Assets.ClawMeshes` (nouveau dossier de templates MeshPart).
- Fichiers Blender + `.obj`/assets dans le repo (sous `Elements_Blender/` ou `assets/`).

---

## 8. Critères de recette

1. **Z-fight** : tourner la caméra autour d'une pince de chaque bande (T1/T5/T7/T9/T10/T12) →
   **zéro scintillement** aux jonctions, caméra en mouvement.
2. **Lisibilité 2 axes** : on distingue la rareté au premier coup d'œil ; au sein d'une rareté on
   lit « du moins bon (rang 1) au meilleur (rang 10) ».
3. **Animation** : jouer un catch → descente/ouverture/fermeture/remontée fluides, sans overshoot,
   vérins synchronisés ; repos griffes fermées poisées bas.
4. **Propagation** : plots, index (viewports), roulette (prix + plateformes + mini-previews),
   PlotPreviews statiques, bannière « nouvelle pince » → tous affichent le nouveau rig.
5. **Perf** : plusieurs machines + index ouvert restent fluides (~6-9k tris, meshes instanciés).
6. **Régression** : FX de catch, Motor6D mâchoires, prompts E/R, feedback board — intacts.

---

## 9. Risques / points ouverts

- **Convergence des deux builders** : bien faire de `ClawModel.build` la source unique et de
  `makeUFOModel` un délégué (supprimer la divergence procédurale).
- **Coût des bandes cristallin/warp/prism** : garder Neon + particules maîtrisés (perf + anti-z-fight).
- **Re-bake des PlotPreviews** obligatoire après changement du châssis.
- **Routage des previews index** : vérifier que `IndexController` passe bien par `ClawModel.build`.
- **Studio en Play** : repasser en Edit avant toute édition.
