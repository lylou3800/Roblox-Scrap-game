# Polish pinces, hologrammes & prompts — Design

**Date :** 2026-06-16
**Statut :** Validé (design approuvé par l'utilisateur)

## Contexte

Pass de polish visuel/UX sur les machines de pince (UFO catchers) du jeu. Six
ajustements ciblés portant sur l'hologramme de feedback au-dessus des machines,
les prompts d'interaction E/R, le placement des panneaux de zone, et
l'animation 3D de la pince.

### Surfaces de code concernées

- **Client — `CatchFXController`** (`StarterPlayer.StarterPlayerScripts.Client.Controllers.CatchFXController`,
  miroir dans `Players.lylou38000.PlayerScripts...`) : hologramme `FeedbackBoard`
  (`getBoard`), feedback de loupé (`onCatch` branche `data.slip`, `floatingText`),
  animation de pince (`animateClaw`).
- **Client — nouveau renderer de prompt** : un petit contrôleur écoutant
  `ProximityPromptService.PromptShown/PromptHidden` pour dessiner un visuel
  compact (style Custom).
- **Serveur — service de construction de plot** (à localiser en mode Edit) :
  construit `Plot_<userId>` au runtime, dont les `Slot_s*` + leurs 2
  `ProximityPrompt`, les `ZoneSign_s*` / `ZonePost_s*`, et le modèle de pince
  (`UFO_s*` : `ArmPivot`, `Claw`, `ClawJaw`×5, `ClawTip`×5, `FeedbackAnchor`...).

> **Important :** la géométrie des plots et les ProximityPrompts sont générés
> par un service serveur au runtime. Ces scripts ne sont pas visibles en mode
> Play. L'implémentation doit se faire en mode Edit pour modifier les
> générateurs serveur de façon persistante (rbxlx = source de vérité).

## Changements

### 1. Hologramme plus compact (`CatchFXController.getBoard`)

- Réduire la taille du `FeedbackBoard` de **168×112 → ~100×72** (≈ −40 %).
  Les labels internes sont en `Scale`, donc s'adaptent automatiquement.
- Réduire `MaxDistance` de 320 → ~180 (note : il est défini deux fois dans le
  code actuel — 220 puis 320 ; consolider en une seule valeur ~180).
- Le board reste ancré sur `FeedbackAnchor` et garde son pulse/punch à chaque
  catch.

### 2. Feedback "loupé / trop lourd" intégré à l'hologramme

- **Supprimer** l'appel `floatingText(...)` dans la branche `data.slip` de
  `onCatch` (le texte néon 3D "Raté !" / "Trop lourd !" qui s'envole — c'est le
  « petit shadow » à enlever). `floatingText` n'est appelé qu'à cet endroit ; le
  retirer supprime entièrement le texte volant.
- À la place, piloter le board en cas de slip :
  - header en **rouge** (`UIUtil.THEME.warn`), texte **"RATÉ"** (wobble) ou
    **"TROP LOURD"** (trop lourd),
  - `nameL` / `valL` neutralisés (ou masqués) pour cet état,
  - **pulse rouge** du board (réutiliser `pulseBoard` avec la couleur warn) +
    léger shake.
- L'animation de pince sur loupé (dip + wobble via `animateClaw`) est conservée.

### 3. Prompts E/R compacts (style Custom)

- Dans le service plot (serveur) : passer les 2 `ProximityPrompt` de chaque
  `Slot_s*` en **`Style = Enum.ProximityPromptStyle.Custom`**.
- Nouveau renderer client via `ProximityPromptService.PromptShown` /
  `PromptHidden` : billboard **compacte** = pastille de touche (E / R) + texte
  d'action court, nettement plus petite que le style Default. Conserver le
  stacking (E au-dessus, R en dessous) en s'appuyant sur `UIOffset` ou un
  décalage géré par le renderer.
- ObjectText/ActionText/KeyboardKeyCode actuels conservés
  ("Pince d'Atelier" / "Ranger l'UFO" sur E / "Ameliorer" sur R).

### 4. Distance d'accès resserrée

- Dans le service plot, sur les 2 prompts de chaque slot :
  - `MaxActivationDistance = 10` (au lieu de 32),
  - `RequiresLineOfSight = false`.
- Résultat : impossible d'interagir avec une machine voisine sans être pile
  devant → élimine les missclicks.
- **Note d'implémentation (2026-06-16) :** les slots sont espacés de **22 studs**,
  donc `MaxActivationDistance = 10` suffit à lui seul à empêcher les missclicks sur
  les machines voisines. `RequiresLineOfSight = true` a été testé puis **abandonné** :
  le prompt est ancré sur le pad situé SOUS la grosse machine, qui bloque alors la
  ligne de vue de son propre prompt (machine non interactable). On garde donc LOS=false.

### 5. Panneaux de zone bien posés sur les poteaux

- Dans le service plot : recalculer la position des `ZoneSign_s*` pour qu'ils
  soient **plaqués proprement devant / au sommet** du `ZonePost_s*` au lieu de
  le traverser. Offset propre sur l'axe du poteau + léger recul de l'épaisseur.
- Appliqué aux 8 slots via le générateur (correction paramétrique, pas
  part-par-part).
- Géométrie observée (slot s1) : `ZonePostSign_s1` pos X=-301.8, taille
  0.55×3.4×0.55 ; `ZoneSign_s1` pos X=-301.35, taille 3.6×1.7×0.22, rot Y=-90°.
  Le panneau chevauche le poteau → ajuster l'offset pour le poser devant.

### 6. Animation 3D : pince qui ouvre et ferme ses mâchoires

- **Pré-requis builder (serveur)** : rendre les 5 `ClawJaw` (+ `ClawTip`)
  pilotables en charnière. Approche recommandée : **Motor6D** par mâchoire
  (hinge au niveau du `Knuckle`/`Claw`), pilotable par `Transform`/`C1` côté
  client. Alternative : stocker `RestCF` / `OpenCF` par mâchoire en attribut et
  les tweener côté client en composant avec la CFrame vivante de la pince.
- **Séquence d'animation** synchronisée avec le dip existant dans `animateClaw`
  (`up → down → jitter → rest`) :
  1. mâchoires **s'ouvrent** pendant la descente,
  2. **se ferment (clamp)** en bas au moment du grab,
  3. restent **fermées** à la remontée (elle « tient » le tas),
  4. **se rouvrent** au repos pour relâcher.

## Portée / non-objectifs

- Pas de refonte du système de pince, du loot, ou de l'UI d'upgrade
  (`ClawMenuController`).
- Pas de nouveaux assets sonores (réutiliser les sons existants).
- Correction paramétrique via les générateurs, pas d'édition part-par-part.

## Risques / points ouverts

- **Localiser le service plot serveur** en mode Edit (non visible en Play).
- **Mécanisme des mâchoires** : valider Motor6D vs CFrame une fois le builder
  ouvert (dépend de la façon dont les parts sont actuellement weldées/ancrées).
- Garder les deux miroirs client (`StarterPlayer...` source ; `Players...` =
  copie runtime) cohérents — éditer la source `StarterPlayerScripts`.
