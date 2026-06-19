# Tutoriel d'onboarding guidé — Design

**Date :** 2026-06-19
**Build cible :** `build.rbxlx` (Studio, source de vérité ; Rojo connecté)
**Statut :** validé en brainstorming ("oui tout me va, fais tout jusqu'à la fin")

## Contexte / découvertes

Jeu : tycoon/simulator Roblox en petites instances, parcelle perso, pince type UFO
catcher qui ramasse de la **ferraille** automatiquement. Économie à **monnaie unique `$`**
(clé interne `scrap`), améliorations, montée en puissance, collection.

Découvertes du code existant qui **conditionnent** le design :

- **Le starter est déjà posé et catche tout seul au 1er join.** `GameConfig.STARTING`
  (`starterUFO = "common_1"` « Pince d'Atelier », `starterSlotForUFO = "s1"`) est accordé
  + **auto-posé** en slot `s1` à la première connexion (logique de placement vers
  `build.rbxlx`~1092199). `CatchService` tourne en boucle serveur (`GameConfig.CATCH.tickRate`,
  `RunService.Heartbeat`) → la machine posée ramasse seule. Le joueur arrive donc dans une
  boucle déjà amorcée : *machine qui catche → ferraille en sac → vendre `$` → améliorer*.
- **L'`OnboardingController` actuel est un scaffold abandonné** : une simple ligne d'indice
  en bas d'écran qui pointe vers des systèmes **supprimés** (Recycler, Parts, « scrap
  currency », levier RNG) et dont la 1re condition (`not next(state.ufos)`) n'est jamais
  vraie pour un nouveau joueur (il a le starter). Les `funnelFlags` n'y avancent jamais.
  → **On le remplace** par le nouveau système.
- **Briques réutilisables** :
  - `AnalyticsService.TrackOnce(player, flag, event, props?)` écrit `data.meta.funnelFlags`
    (déjà câblé : `first_ufo_placed`, `first_item_caught`, `first_item_sold`,
    `first_upgrade_bought`, `first_item_kept`, `first_collection_completion`…).
  - `ReplicatedStorage.UI.Theme` + `Client.UIUtil` (`make`/`label`/`corner`/`padding`/
    `stroke`, `UIUtil.THEME`), kit premium cartoon (vert valider `#5FD41A`, or `#F2C019`,
    panel `#241A12`, stroke `#1A120A`, fonts Luckiest Guy / Fredoka).
  - `Client.Registry` (controllers) + `Registry` serveur (services).
  - `Shared.Net.Net` : `onRequest`/`sendEvent`/`onState` (serveur), `request`/`onState`/
    événements (client, cf. `CatchFXController`).
  - `StateController` : pousse la `PlayerData` répliquée (`onChanged`, `get`).
  - `FXKit` / `CatchFXController` : patterns de feedback (bursts, particules, son).
  - `ToolService.reconcile(player)` (appelé en fin de `DataService.replicate`) : miroir des
    `Tool` du Backpack (pinces non posées + ferraille).
  - `PlacementController` : **E** à un slot vide pose la **pince équipée** (`placeUFO`).
  - `ClawPreview.make(defId, prestige, parent)` → `ViewportFrame` (vignette pince).
  - `DataService.replicate(player)` : **hook unique** appelé à chaque mutation.
  - `EconomyService.add(player, "scrap", n)` : crédite le `$`.

**Note d'environnement (pas un blocage de design, mais à savoir avant l'impl) :** la session
Studio *live* n'a **pas** les scripts serveur (`ServerScriptService` et `ServerStorage` vides) ;
ils existent dans `build.rbxlx` (236 réfs aux services). Il faudra les recharger avant
d'implémenter/tester côté serveur.

## Décisions validées (brainstorming)

1. **Geste héros = poser sa pince soi-même.** Pendant le tuto on **ne pose plus** le starter
   automatiquement : il arrive en main/sac, et le 1er objectif guidé est d'aller au slot qui
   brille et de **poser** la pince (**E**). Si le joueur **passe** le tuto → le starter est
   **auto-posé** (comportement actuel) pour qu'il soit opérationnel.
2. **Récompense = une pince rare garantie** (saut net au-dessus du starter `common_1`). Elle
   sert aussi de **machine #2** à poser en conclusion (bookend du geste « poser »).
3. **Déclenchement = popup auto au 1er join, non rejouable.** Complétion **persistée côté
   serveur**. Pas de bouton « ? » de relance (explicitement écarté).

## Approche retenue : A

**Step-machine client + gates/récompense serveur-authoritatifs + toolkit `GuideFX`
réutilisable.** Chaque étape avance en observant la **vraie action de jeu** (poser / catcher /
vendre / améliorer), lue depuis `StateController` + `funnelFlags`. Le serveur possède la
récompense et le flag de complétion (anti-triche, grant-once). `GuideFX` (flèches monde,
anneaux sol, highlights, pointeurs écran + scrim, indicateurs hors-champ) est le cœur visuel
et reste réutilisable pour de futures quêtes.

*(Écartées : B « on-rails » scripté = trop intrusif vs « non intrusif » demandé ; C « beacons
d'indices » seuls = trop maigre, pas de proposal/gating/récompense.)*

## Flux / arc (proposal + 4 actions + payoff, ~60–90 s)

**Popup de proposition** (auto, 1er join, centré, panel `Theme`) :
> ✨ *Bienvenue dans l'atelier !* Tour express (~60 s) pour bien démarrer.
> **Finis-le → pince rare offerte.** — `[ C'est parti ]` · `[ Passer ]`

Motivant, une ligne, annonce la récompense, les deux choix visibles. *Passer* → `tutorialSkip`
(auto-pose le starter, marque done).

**Étapes guidées** (chacune = carte objectif courte + guidage monde/écran + feedback de fin) :

1. **Pose ta pince** *(geste héros)* — `groundRing` + `worldArrow` + `offscreenIndicator` sur
   le slot `s1` vide et surligné ; indice « Approche et appuie sur **E** ». *Fin sur
   `first_ufo_placed`* → la machine se pose (claquement) et **démarre**.
2. **Regarde-la bosser** — `highlight` + `worldArrow` sur la machine ; « Ta pince ramasse la
   ferraille **toute seule** ! » Une prise → un morceau tombe dans le sac. *Fin sur
   `first_item_caught`* → burst « +1 ferraille ».
3. **Vends ta ferraille** — `screenPointer` + `spotlight` sur le bouton inventaire/sac ;
   « Ouvre ton sac et **vends** ta ferraille ». *Fin sur `first_item_sold`* → premier `$` qui
   pop (compteur animé).
4. **Améliore-toi** — `screenPointer` sur le bouton Améliorations ; « Dépense tes **$** pour
   booster ta pince ». *Fin sur `first_upgrade_bought`* → flash de power-up.

**Conclusion (célébration premium)** : confettis plein écran + la pince rare révélée dans un
`ViewportFrame` qui tourne avec étincelles → « **Pince Rare débloquée !** » → objectif doux
final : `worldArrow`/`groundRing` vers un **slot libre** (`s2`), « Pose ta nouvelle machine ! »
(bookend du geste « poser », enchaîne droit sur le vrai jeu). **La récompense est accordée
serveur dès la fin de l'étape 4** → ce beat ne peut pas soft-lock ; le guidage s'auto-dissipe
après la pose ou après un court délai, puis les contrôles sont rendus (« À toi de jouer ! »).

## Architecture

### Serveur — `TutorialService` (nouveau, enregistré dans `Registry`)

Toutes les mutations passent par `DataService.replicate` (→ push `StateController` +
`ToolService.reconcile`).

- **Données** (`GameConfig` defaults + `Types`) : `data.meta.tutorialDone: boolean`
  (défaut `false`) = **gate grant-once persisté**. Pas de `tutorialStep` persisté : l'étape
  courante se **dérive des `funnelFlags`** à l'entrée (auto-réparant).
- **Changement du grant de départ** (la logique d'auto-pose au 1er join,
  `build.rbxlx`~1092199) : si `tutorialDone == false` au 1er join → accorder `common_1` à
  `data.ufos` **sans poser** `s1` (la pince apparaît comme `Tool` via `ToolService`). Si
  `tutorialDone == true` → **garder** l'auto-pose actuelle (robustesse).
- **Remotes** (`Net.onRequest`) :
  - `tutorialStatus` → `{ shouldOffer = (not tutorialDone) }`. Le client n'affiche le proposal
    que si `true`.
  - `tutorialSkip` → `tutorialDone = true`, **auto-pose** le starter en `s1` (réutilise la
    logique de placement existante), replicate. Joueur opérationnel immédiatement.
  - `tutorialFinish` → **valide que le funnel a réellement eu lieu** (les 4 `funnelFlags`
    vrais). Si valide & pas déjà done : accorde la **pince rare garantie** à `data.ufos`,
    **assure un slot libre déverrouillé** pour elle (déverrouille `s2` gratuitement au finish
    si verrouillé), `tutorialDone = true`, replicate, `Net.sendEvent(player, "tutorialReward",
    …)` → célébration client.
- **Anti-triche / intégrité** : le serveur ne fait jamais confiance au « j'ai fini » client —
  il vérifie les `funnelFlags`, posés **seulement** par les vrais services (`CatchService`,
  `InventoryService`, `UpgradeService`, `PlotService`). Un client ne peut pas truquer la
  complétion pour farmer des pinces rares. Récompense gardée par `tutorialDone` (**grant-once**).
- **Pince récompense** : une pince **Rare** garantie au rang 1 — `defId` exact résolu contre
  `Config.UFOCatchers`/`ClawDesign` à la planification (saut net au-dessus de `common_1`, sans
  trivialiser la progression early).

### Client — `TutorialController` (nouveau ; remplace `OnboardingController`)

Machine à états finis. Chaque étape = `{ id, objectif (texte court), cible (slot/machine/bouton
HUD), guides `GuideFX`, condition de fin (signal `StateController`/`funnelFlags`), feedback de
réussite }`.

- Au join : `Net.request("tutorialStatus")` ; si `shouldOffer` → affiche le proposal.
- S'abonne à `StateController.onChanged` ; dérive l'étape courante des `funnelFlags` (s'aligne
  même si le joueur fait une action « en avance »).
- Pilote : proposal → cartes par étape → guides `GuideFX` (créés à l'entrée, nettoyés à la fin
  de l'étape) → conclusion. À la fin de l'étape 4 : `Net.request("tutorialFinish")` ; écoute
  l'événement `tutorialReward` → joue la célébration.
- **Suppression** de l'ancien `OnboardingController` (remplacé).

### Client — `GuideFX` (nouveau module ; cœur visuel, réutilisable)

Identité : **vert** `#5FD41A` (« va ici »), **or** `#F2C019` (succès/récompense), stroke
`#1A120A`, fonts du `Theme` → natif à l'UI existante, jamais un overlay étranger. Chaque
fabrique renvoie un **handle `:Destroy()`-able** ; `GuideFX.clearAll()` purge tout.

- **Monde** : `worldArrow(target)` (chevron vert qui flotte ~0.4 stud, always-on-top, pulse) ;
  `groundRing(cframe)` (anneau lumineux pulsant au sol) ; `highlight(instance)` (`Highlight`
  vert outline + fill léger, breathing) ; `offscreenIndicator(worldTarget)` (**flèche au bord
  de l'écran qui pointe vers la cible quand elle est hors-champ**, fade quand visible → garantie
  « jamais perdu ») ; `pathBeam(char → slot)` (traînée de chevrons au sol, étape 1 seulement).
- **Écran** (boutons HUD) : `screenPointer(button)` (flèche + halo pulsant) ; `spotlight(button)`
  (scrim/vignette douce qui assombrit *sauf* la cible — premium, **non agressif**) ;
  `pulse(button)` (scale-breathe subtil).

### Client — carte d'étape + couche de feedback

- **Carte** (bas-centre, panel `Theme`) : icône + **une ligne courte** (≤ ~8 mots) + pips
  d'étape `●●○○` + petit lien « Passer ». Slide+scale à l'entrée (chime) ; à la fin : tampon
  check vert + bouffée de confettis + son satisfaisant, puis avance. **Jamais de paragraphe.**
- **Feedback** (réutilise `FXKit`/`CatchFXController`) : ping « objectif repéré » → flash
  « action correcte » → burst « étape terminée » → pop de progression (premier `$` qui compte ;
  flash d'upgrade) → shimmer « récompense proche » → **célébration finale** (confettis plein
  écran + pince rare dans un `ViewportFrame` étincelant + son triomphal).

## Cas limites / risques

- **Déconnexion en plein tuto** : `tutorialDone` reste `false` → au rejoin, **re-proposer**
  (anti-soft-lock : le starter resterait non posé). C'est un léger écart au « 1er join
  uniquement », **assumé** pour ne pas laisser le joueur sans machine posée et sans guidage.
  (Alternative écartée : auto-pose + done silencieux = perte de la récompense quasi acquise.)
- **Action « en avance »** (ex. le joueur vend avant l'étape Vente) : la step-machine dérive
  l'étape des `funnelFlags` → elle saute à la bonne étape, les guides suivent.
- **Skip en cours d'étape** : `GuideFX.clearAll()`, `tutorialSkip`, auto-pose starter.
- **Starter déjà posé / `tutorialDone == true` au join** : pas de proposal.
- **Slot `s2` verrouillé / coûteux** : déverrouillé gratuitement au `tutorialFinish` pour que
  la conclusion fonctionne toujours.
- **Timing `ToolService`** : la pince accordée apparaît comme `Tool` après `reconcile` ; les
  guides de l'étape 1 attendent que le `Tool` existe (et idéalement soit équipé).
- **Perf / mobile** : nombre de `Highlight` limité, `BillboardGui.MaxDistance`, scrim léger,
  tweens nettoyés.
- **Gotchas Studio (impl)** : `multi_edit` peut silencieusement no-op (vérifier par relecture) ;
  la VM Server de `execute_luau` est isolée (tester les services via un `Script` temporaire) ;
  Play compile un snapshot juste après une édition (re-vérifier).

## Tests / vérification (MCP Studio)

1. **Recharger les scripts serveur** dans la session.
2. **1er join** : pas d'auto-place ; le proposal s'affiche, annonce la récompense.
3. **« C'est parti »** → guides étape 1 sur `s1` ; **E** pose → machine démarre → étape avance.
4. **Catch auto** → étape 2 done (`first_item_caught`).
5. **Vendre** → étape 3 done, premier `$` (`first_item_sold`).
6. **Améliorer** → étape 4 done (`first_upgrade_bought`) → `tutorialFinish` → pince rare +
   slot `s2` + célébration ; conclusion pointe le slot libre.
7. **Skip** (autre compte/reset) → starter auto-posé, `tutorialDone`, plus de proposal.
8. **Rejoin après done** : pas de proposal.
9. **Anti-triche** : `tutorialFinish` sans les `funnelFlags` → refusé, pas de pince.
10. **Ctrl+S**.

## Hors-scope (YAGNI)

- Rejouabilité / bouton « ? » (explicitement écarté).
- Localisation multi-langue (FR uniquement).
- Tutos des systèmes avancés (pets, roulette, crafting, index, automation) — le tuto couvre
  **uniquement** le cœur (poser → catcher → vendre → améliorer).
- Système de quêtes / récompenses quotidiennes (réutiliser `GuideFX` plus tard, pas maintenant).
- Modèle de pince réduit en main (déjà hors-scope côté inventaire Tools).

## Critères de réussite

- Proposal au 1er join, skippable, **annonce la récompense**, formulé de façon engageante.
- 4 étapes = **vraies actions**, guidées visuellement (flèches/anneaux/highlights/offscreen/
  spotlight) + **feedback à chaque étape** (début, repérage, action correcte, fin, progression,
  approche récompense).
- **Jamais perdu** (offscreen indicator), **jamais passif** (chaque étape met en mouvement).
- Conclusion premium + **pince rare** + enchaînement naturel sur le vrai gameplay.
- **Serveur-authoritatif**, grant-once, non rejouable, complétion persistée.
- Cohérent avec le `Theme` ; perf mobile correcte.
