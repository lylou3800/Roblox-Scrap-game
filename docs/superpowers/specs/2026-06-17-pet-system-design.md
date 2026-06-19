# Système de Pets — Design

**Date :** 2026-06-17
**Statut :** validé en brainstorm, prêt pour le plan d'implémentation
**Décisions cadres (validées par l'utilisateur) :** gacha par rareté **+ fusion** des doublons · **3 slots équipés** extensibles jusqu'à 6 · bonus **passif + capacité active** (rares+) · shop d'œufs **lineup 100 % rotatif** qui se réapprovisionne toutes les **15 min** · 10 pets modélisés/animés sur Blender · roster thématique **arcade-industriel** (pas d'animaux de ferme génériques).

---

## Contexte — pourquoi ce système

UFO Catchers a sa boucle d'usine (`pince → tas → vente → $ → dépense`) et une progression globale via l'onglet **Amélios** (14 améliorations sur le pipeline `effectKind`, cf. `2026-06-16-economy-progression-rework-design.md`). Les **pets** ajoutent :

1. Un **nouvel axe de collection/dopamine** (gacha + fusion) parallèle aux pinces.
2. Un **sink `$` mid/late** (les œufs coûtent cher, complètent les Amélios qui se finissent vers la moitié du parcours).
3. Des **compagnons vivants** qui errent dans l'usine — présence, vie, social.

**Principe directeur :** les bonus de pets sont **petits et cumulables** et se branchent sur le **même pipeline `effectKind`** que les Amélios (aucune nouvelle mécanique de calcul de stats — on réutilise `CatchService.effectiveStats`, `InventoryService.sellStack`, `AutomationService`, l'offline de `DataService`). Les pets sont un **multiplicateur d'agrément**, pas une refonte de l'économie.

**Non-goals (v1) :** pas de trading entre joueurs ; pas de pets « shiny »/golden ; l'errance affiche **les pets du joueur local** (voir ceux des autres = fast-follow) ; pas de quêtes/œufs payants Robux (axe `$` uniquement).

---

## A. Direction artistique & roster (10 pets, 5 raretés)

Thème **mascottes arcade-industrielles** : peluches-lots qui s'animent + petits bots d'usine. Le **légendaire est l'OVNI mascotte** (clin d'œil au nom du jeu). Rendu « ultra pro » : meshes Blender riggés, bien proportionnés, textures propres.

### Raretés des pets (`PetRarities`)

Échelle dédiée (plus simple que les 12 raretés de pinces), 5 paliers, chacun avec `order`, `color` (Theme), `sellBase` (valeur de revente niv 1) :

| id | nom | order | sellBase ($) |
|---|---|---|---|
| `commun` | Commun | 1 | 1 000 |
| `peu_commun` | Peu commun | 2 | 8 000 |
| `rare` | Rare | 3 | 60 000 |
| `epique` | Épique | 4 | 500 000 |
| `legendaire` | Légendaire | 5 | 5 000 000 |

Couleurs : reprendre la palette `Theme` (réutiliser les teintes des raretés existantes si cohérent).

### Les 10 pets (`Pets`)

`passive = { {kind, value} ... }` (un ou deux effets `effectKind`), `active` présent seulement sur rares+. `value` = magnitude au **niveau 1** ; la magnitude effective scale avec le niveau (cf. §B).

| # | id | Nom | Rareté | Passif (kind @ niv1) | Capacité active |
|---|---|---|---|---|---|
| 1 | `bunny_plush` | Lapin en Peluche | commun | `speedMult` +2 % | — |
| 2 | `bolt_bot` | Boulon-Bot | commun | `sellMult` +3 % | — |
| 3 | `foam_cube` | Cube Mousse | commun | `luckAdd` +0,10 | — |
| 4 | `windup_duck` | Canard Mécanique | peu_commun | `offline` +5 % | — |
| 5 | `neon_kitten` | Chaton Néon | peu_commun | `luckAdd` +0,12 · `yield` +2 % | — |
| 6 | `magnet_drone` | Drone Aimanté | rare | `magnet` +10 % | **Auto-vente** : vend une portion du tas (respecte le keep-filter) |
| 7 | `golden_teddy` | Ourson Doré | rare | `sellMult` +6 % | **Crit garanti** sur le prochain grab |
| 8 | `mini_clawbot` | Mini Claw-Bot | epique | `multiGrab` +0,03 | **Burst** : double les grabs pendant 8 s |
| 9 | `holo_fox` | Renard Holo-Arcade | epique | `crit` +0,5 % (chance) | **Jackpot** : déclenche un crit/jackpot immédiat |
| 10 | `ufo_mascot` | OVNI Mascotte 🛸 | legendaire | `luckAdd` +0,15 · `speedMult` +3 % · `sellMult` +5 % | **Pluie de lots** : gros `yield` instantané (copies du butin vedette) |

`kind` ∈ vocabulaire `effectKind` existant (`luckAdd`, `speedMult`, `sellMult`, `crit`, `magnet`, `offline`, `multiGrab`, `yield`, et extensibles `qualityBias`/`modifierChance`/`weightCap`). **Aucun consommateur nouveau** : ces effets sont déjà lus côté serveur pour les Amélios.

---

## B. Niveaux, fusion, slots, vente

### Niveau & scaling
- **Max niveau 10.** Magnitude effective d'un passif : `value × (1 + 0.15 × (level − 1))` (niv 10 ≈ ×2,35).
- **Cooldown actif** : `baseCooldown × (1 − 0.03 × (level − 1))` (niv 10 ≈ −27 %), plancher 30 s.
- Cooldowns de base par rareté : rare **180 s**, épique **150 s**, légendaire **120 s**.

### Fusion (consomme les doublons)
- **3 pets identiques** (même `defId` **et** même `level`) → **1 pet `level + 1`**.
- Déclenchée depuis le menu pet (bouton **Fusionner**, actif si ≥3 dispo non équipés au bon niveau). Serveur-autoritaire : vérifie possession, retire 3, ajoute 1.

### Slots équipés
- Départ **3**. Achetables jusqu'à **6** en `$` : slot 4 = **250 k**, slot 5 = **5 M**, slot 6 = **80 M** (`petSlots` dans le profil).
- Les bonus des pets **équipés** se cumulent (somme par `kind`). Les pets non équipés ne donnent aucun bonus.

### Vente
- Valeur = `PetRarities[rarity].sellBase × (1 + 0.5 × (level − 1))`. Bouton **VENDRE `$X`** (image 2). Confirmation pour les épiques+.

---

## C. Shop d'œufs (logique serveur, rotation 15 min)

### Types d'œufs (`Eggs`)
`weights` = table de poids par rareté ; `unlock` = palier de déblocage (lifetime `$` gagné) ; `price` en `$`.

| id | Nom | Prix ($) | Déblocage (lifetime $) | Poids (commun/peu_c/rare/épique/légend.) |
|---|---|---|---|---|
| `common_egg` | Œuf Commun | 5 000 | 0 (départ) | 70 / 25 / 5 / 0 / 0 |
| `industrial_egg` | Œuf Industriel | 75 000 | 500 k | 35 / 45 / 18 / 2 / 0 |
| `neon_egg` | Œuf Néon | 1 200 000 | 10 M | 0 / 30 / 50 / 18 / 2 |
| `legendary_egg` | Œuf Légendaire | 25 000 000 | 250 M | 0 / 0 / 35 / 50 / 15 |
| `mystery_egg` | Œuf Mystère (vedette) | 8 000 000 | 10 M | 0 / 0 / 0 / 60 / 40 |

`mystery_egg` n'est **pas** garanti dans le lineup : il est injecté ~1 refresh sur 3 (cf. rotation). Prix/poids = **boutons de réglage**.

### Rotation « lineup 100 % rotatif » (global / par serveur)
- **3 emplacements** d'œuf visibles. Toutes les **15 min**, le lineup est **entièrement re-tiré**.
- **Lineup global, déterministe par le temps** : `bucket = floor(os.time() / 900)` ; `nextRefreshAt = (bucket + 1) × 900`. RNG seedé par `bucket` ⇒ **même lineup pour tous les joueurs** (et identique sur tous les serveurs, alignés à la seconde près) ; fonction partagée serveur/client dans `Config.Eggs`, pas de DataStore.
  - Tirage des 3 slots parmi **tous** les types d'œufs (`mystery_egg` injecté probabilistiquement), pondéré pour rester varié.
  - **Garde-fou anti-magasin-mort** : au moins **un slot est toujours `common_egg`** (unlock 0) ⇒ tout le monde a toujours un œuf achetable, même un débutant.
- **Gating par joueur (affichage)** : un œuf du lineup dont le `unlock` n'est pas atteint pour ce joueur s'affiche **VERROUILLÉ** + le palier requis (comme les pads « VERROUILLE » image 3). Le déblocage lit `data.stats.totalEarned` (lifetime `$`). Le lineup reste le même pour tous ; seul l'état acheté/verrouillé diffère par joueur.
- Notif globale à chaque refresh : **« Le magasin d'œufs a été réapprovisionné. »** (image 1) + countdown `Réapprovisionnement dans MM:SS` sur le SurfaceGui du shop.

### Achat → éclosion (gacha)
1. Client `Net.request("buyEgg", {eggId})`.
2. `EggShopService` : vérifie que `eggId` est dans le lineup courant **et** débloqué pour ce joueur, débite le prix (`EconomyService`), tire un `petDef` au poids des `weights`.
3. `PetService.grantPet(player, defId, level=1)` → ajoute au profil.
4. Réponse + event `petHatched` (defId/rarity) → le client joue l'**animation d'éclosion** (œuf qui se fissure + reveal FX de rareté, réutilise le pipeline dopamine `RouletteRollController`/`FXKit`).

---

## D. Capacités actives (tick serveur)

`PetService` fait tourner une boucle par joueur (accumulateur sur Heartbeat, pas de `wait` serré) qui, pour chaque pet **équipé** doté d'une `active`, suit un cooldown et déclenche l'effet quand prêt. Tous les effets **réutilisent des mécaniques existantes** :

- `magnet_drone` → **auto-vente** : `InventoryService.sellFiltered(player, data.sellFilter)` sur une portion (même mécanique que l'aimant Amélios).
- `golden_teddy` → **crit garanti** : pose un flag par-joueur consommé au prochain `CatchService.doGrab` (force `crit`).
- `mini_clawbot` → **burst** : pose une fenêtre 8 s lue dans `doGrab` → chaque grab s'exécute 2×.
- `holo_fox` → **jackpot** : grant cash instantané immédiat (réutilise le pipeline crit/jackpot de `CatchService` + FX `catch.crit`).
- `ufo_mascot` → **pluie de lots** : ajoute N copies du butin vedette au tas (réutilise `yield`), FX dédié.

Chaque déclenchement émet un event léger `petAbility {uid, kind}` → FX client au-dessus du pet concerné.

---

## E. Agrégation des bonus passifs (intégration pipeline)

`PetService.aggregate(player)` calcule, à partir des pets **équipés**, une table `{ [effectKind] = scommeDesMagnitudesScalées }`. Recalculée à chaque équip/déséquip/fusion/level-up et mise en cache. Exposée via `PetService.bonusFor(player, kind)` (renvoie 0 si absent).

**Branchements (édits ciblés, additifs aux Amélios) :**

| Consommateur | Fichier | Ajout |
|---|---|---|
| Chance, vitesse, multi-grab, crit, qualité, modif, capacité | `CatchService.effectiveStats` | `+= PetService.bonusFor(player, kind)` pour chaque kind concerné |
| Multiplicateur de revente | `InventoryService.sellStack` | `sellMult += PetService.bonusFor(player, "sellMult")` |
| Aimant (débit/fraction), yield | `AutomationService` / `CatchService.doGrab` | bonus `magnet`/`yield` ajouté |
| Gains hors-ligne | `DataService.onReady` | `pct += PetService.bonusFor(player, "offline")` |

Aucune formule de stat n'est réécrite : les pets **alimentent** les mêmes accumulateurs.

---

## F. Modèle de données

### Profil (`GameConfig.PROFILE_TEMPLATE`)
```
pets         = {},   -- liste de { uid=string, defId=string, level=number, locked=bool }
equippedPets = {},   -- liste d'uid (taille ≤ petSlots)
petSlots     = 3,
stats.totalEarned = 0,  -- lifetime $ gagné (gating shop) ; migration : init = balance si 0
```
- `uid` : id unique par instance de pet (compteur monotone ou HttpService:GenerateGUID).
- **Migration façon `clawSchema`** (cf. memory) : `ProfileStore:Reconcile` remplit `pets`/`equippedPets`/`petSlots`/`totalEarned` sur les saves existantes. Pour `totalEarned == 0` sur une save non-neuve, l'initialiser à la balance courante (évite de re-gater les joueurs riches).

### État du shop
**Pas de persistance** : dérivé du temps uniquement. `bucket = floor(os.time()/900)` ; le lineup **global** est recalculé à la volée côté serveur **et** côté client via la même fonction `Eggs.lineupFor(bucket)` ⇒ lineup identique pour tous, aucun DataStore. `nextRefreshAt = (bucket + 1) × 900`. Le gating (acheté/verrouillé) est appliqué par-dessus, par joueur, à partir de `data.stats.totalEarned`.

### Configs (`ReplicatedStorage.Shared.Config`)
- `Pets` (defs + helpers : `Pets.rarityOf`, `Pets.passiveAt(def, level)`, `Pets.cooldownAt(def, level)`, `Pets.sellValue(def, level)`).
- `PetRarities` (échelle + couleurs).
- `Eggs` (defs + `Eggs.lineupFor(bucket)` global partagé serveur/client + `Eggs.rollPet(eggId, rng)`).
- `Types` étendu : `PetDef`, `EggDef`, `OwnedPet`.

---

## G. Architecture & fichiers

**Configs** (`ReplicatedStorage.Shared.Config`) : `Pets`, `PetRarities`, `Eggs`, `Types` (+defs), `GameConfig` (PROFILE_TEMPLATE).

**Services** (`ServerScriptService.Server.Services`) :
- **`PetService`** (nouveau) : grant/fusion/équip/déséquip/vente, `aggregate`/`bonusFor`, tick capacités actives, net handlers `equipPet`/`unequipPet`/`fusePet`/`sellPet`/`buyPetSlot`, events `petsChanged`/`petAbility`.
- **`EggShopService`** (nouveau) : lineup courant (dérivé temps), gating par joueur, net `buyEgg` + `getPetShop`, broadcast `petShopRefreshed`, notif réappro.
- Édits : `CatchService` (effectiveStats + flags crit-garanti/burst-grab), `InventoryService` (sellMult pet), `AutomationService` (magnet/yield pet), `DataService` (migration schéma + offline pet + `totalEarned` incrémenté dans le flux cash).

**Client** (`StarterPlayer.StarterPlayerScripts.Controllers`) :
- **`PetController`** : rend les pets équipés (clone `ReplicatedStorage.Assets.PetMeshes[defId]`, placeholder d'ici les assets Blender), **errance** (points aléatoires autour de la parcelle, lerp + orientation + bob/marche), idle/walk anim, `BillboardGui` nom + `ProximityPrompt`/clic → ouvre le menu sur ce pet.
- **`PetMenuController`** : GUI inventaire (grille + carte détail `ViewportFrame`, niveau, boost, capacité+cooldown, **Équiper/Déséquiper/Fusionner/Vendre**, achat de slots). Construit au runtime avec `Theme` (GUIs gameplay runtime, cf. memory).
- **`EggShopController`** : lit le lineup + `nextRefreshAt`, pilote le SurfaceGui countdown, prompts d'achat par piédestal, **FX d'éclosion** (overlay reveal).

**3D** (dans `build.rbxlx`, zone d'accueil près de la roulette — emplacement image 3) : modèle **`EggShop`** procédural idempotent (générateur Edit-mode, comme `MapBlockout.PlotConnectors`/roulette) : 3 piédestaux à œufs, arche « MARCHAND D'ŒUFS », SurfaceGui countdown, props `DecorLibrary` cohérents avec la zone roulette. Assets héros Blender possibles ensuite.

**Blender** (`Elements_Blender/pets/`) : 10 pets, **1 objet par zone de couleur** (pipeline validé memory), **riggés** (armature simple : idle respiration + cycle de marche), upload via l'addon officiel « Upload to Roblox » → asset IDs dans `Elements_Blender/pets/asset_ids.json` → importés dans `ReplicatedStorage.Assets.PetMeshes`. **Fallback** accepté : si le rigging des 10 pets est trop lourd, animation **procédurale** (bob + sautillement) sur mesh statique haute qualité.

---

## H. Phases d'implémentation

1. **Data & bonus core** — configs `Pets`/`PetRarities`/`Eggs`/`Types`, migration `GameConfig`/`DataService`, `PetService` (inventaire + fusion + équip/vente + `aggregate`/`bonusFor`), branchement des **passifs** dans `CatchService`/`InventoryService`/`AutomationService`/`DataService`. *(Testable en headless via admin : grant pets, équiper, dumper `effectiveStats`.)*
2. **Capacités actives** — tick `PetService` + flags/fenêtres dans `CatchService.doGrab` + auto-vente/jackpot/pluie + events `petAbility`.
3. **Logique shop** — `EggShopService` (lineup dérivé temps, gating, `buyEgg` → tirage → grant), notif réappro + countdown.
4. **Build 3D shop** — modèle `EggShop` procédural dans la zone d'accueil + SurfaceGui.
5. **Errance + interaction + menus** — `PetController` (rendu/errance/interaction, placeholders), `PetMenuController`, `EggShopController` + FX éclosion.
6. **Assets Blender** — 10 pets modélisés/riggés/animés + upload + câblage `PetMeshes` (remplace les placeholders). *(Parallélisable.)*
7. **Équilibrage & vérif end-to-end** — calibrage prix œufs / magnitudes / cooldowns, simulation de rythme, tests.

---

## I. Vérification (end-to-end)

- **Boot propre** : Play, console sans erreur, `PetService`/`EggShopService` OK.
- **Éclosion** : admin grant `$`, `buyEgg` via client réel → pet ajouté, FX reveal, rareté conforme aux poids (tirer N fois, vérifier la distribution).
- **Bonus passifs** : équiper un pet → dump `effectiveStats` avant/après (la magnitude scale au niveau attendu) ; cumul de 3 pets.
- **Fusion** : 3 identiques même niveau → 1 niveau +1, inventaire correct.
- **Capacités actives** : forcer cooldown court, observer crit garanti / burst / auto-vente / jackpot / pluie + events.
- **Shop rotation** : avancer `os.time` (ou attendre un bucket) → lineup re-tiré, **global et identique** pour tous les joueurs / client & serveur (même `bucket`), countdown juste, `common_egg` toujours présent, œufs non débloqués affichés VERROUILLÉ par joueur.
- **Hors-ligne** : pet `offline` équipé → reculer `lastSeenAt` → le lump de reconnexion intègre le bonus pet.
- **Compat saves** : charger une save existante → `Reconcile` remplit `pets`/`petSlots`/`totalEarned`, joueur riche non re-gaté.
- **Outils** : `AdminService` (`lylou38000`) — ajouter un grant pet/level pour tester.

---

## J. Boutons de réglage (tuning knobs)

Centralisés en tête de leurs modules : magnitudes `value`/scaling 0,15 (Pets), cooldowns de base + scaling 0,03 + plancher, `sellBase` par rareté, **prix + `unlock` + `weights`** des œufs (Eggs), fenêtre de refresh 900 s, probabilité d'injection `mystery_egg`, coûts des slots (250 k/5 M/80 M), taille d'auto-vente et N de la pluie de lots.

---

## K. Risques & décisions ouvertes

- **Rigging Blender × 10** = poste le plus lourd (phase 6) → fallback procédural prévu ; les placeholders permettent de livrer 1-5 sans bloquer sur l'art.
- **Errance** : IA simple (waypoints autour de la parcelle) pour éviter le coût perf ; pas de pathfinding lourd. Pets des autres joueurs non rendus en v1.
- **Déterminisme du shop** : lineup **global** seedé par `bucket = floor(os.time()/900)` (même contenu pour tous, serveurs alignés à la seconde près), pas de DataStore. Garde-fou `common_egg` toujours présent → jamais de magasin 100 % verrouillé. Le gating verrouillé/acheté est appliqué par-dessus, par joueur.
