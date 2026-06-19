# Système de Pets — Complétion & rework boutique

**Date :** 2026-06-17
**Statut :** validé en brainstorm (A/B/C approuvés explicitement ; D/E/F capturés sur feu vert « lance l'implémentation »), prêt pour le plan.
**Prédécesseur :** `2026-06-17-pet-system-design.md` (système de base déjà implémenté). Ce doc décrit la **complétion + les changements** demandés par l'utilisateur.

---

## 0. Contexte & écart avec l'existant

Le système de pets de base existe déjà et tourne (cf. memory `pet-system`) : configs `Eggs`/`Pets`/`PetRarities`, `EggShopService`, `PetService`, `EggShopController`/`PetController`/`PetMenuController`, 10 `PetMeshes` procéduraux, un `EggShop` 3D (`Workspace.Environment.EggShop`, pivot ~(-379,12,5)) avec **3 piédestaux** + un **NPC** part-buildé + un placeholder **roulette** (`Workspace.Environment.RoulettePad/Post/Sign`, référencés par **aucun** script — la vraie roulette est `ShopService`, construite *dans chaque plot* sous `plot.Roulette`).

**Écarts à combler (demande utilisateur) :**

| Sujet | Existant | Cible |
|---|---|---|
| Boutique | 3 piédestaux, lineup de 3, gating « lifetime $ par œuf » | **6 piédestaux**, gating par **slots d'œufs achetables** ($ croissant), slot 1 visible au départ |
| Achat | *instant-hatch* (le $ devient direct un pet) | **œuf-objet** dans l'inventaire → tenu en main → **clic = éclosion** → animal |
| Cap pets | slots équipés 3→6 (achat) | **3 pets déployés max, cap fixe** (achat de slots de pets supprimé) |
| Montée niveau | fusion (3 doublons) | **argent uniquement** (clic droit → menu → Améliorer $) ; fusion **supprimée** |
| Errance | autour du **personnage** | dans le **plot** du joueur |
| Labels prix/rareté | BillboardGui sans `MaxDistance` (visibles de toute la map) | visibles **seulement de près** ; slots verrouillés masqués |
| NPC | part-character blocky | reproportionné **style personnage Roblox** |
| Décor | quelques chevauchements | aucun décor encastré dans un autre |
| Roulette placeholder | présent derrière la boutique | **supprimé** |
| Modèles 3D pets | 10 procéduraux | **10 animaux modélisés sur Blender** (import plus tard) |

**Non-goals (inchangés) :** pas de trading, pas de pets « shiny », errance = pets du joueur local seulement, axe `$` uniquement (pas de Robux).

**Décisions cadres validées :** slots tiered (slot k = palier) · pet géré dans le **Menu Pets** (pas dans le hotbar pinces) · l'œuf reste un objet du sac · 3 pets déployés cap fixe · upgrade $ only · roster des 10 conservé.

---

## A. Boutique — 6 slots « tiered », déblocage en $

### A.1 Pool d'œufs étendu (12 œufs, 2 par palier)

Le slot `k` (1..6) affiche un œuf de **palier k**. Deux variantes par palier ⇒ l'œuf affiché **tourne toutes les 15 min** (le « 1 œuf qui change » demandé). Détermination **globale & déterministe** par le temps (réutilise `bucket = floor(os.time()/900)`), identique sur tous les serveurs.

`EggDef = { id, name, price, tier, model, weights }` — **`unlock` (lifetime $) supprimé** ; le gating est désormais le slot. `weights` = poids par rareté de pet (commun/peu_commun/rare/epique/legendaire).

| Palier | Œufs (rotation) | Prix ($) | Poids (c/pc/r/e/l) |
|---|---|---|---|
| 1 | `common_egg` Œuf Commun | 5 000 | 75/22/3/0/0 |
| 1 | `picnic_egg` Œuf Pique-Nique | 12 000 | 60/33/7/0/0 |
| 2 | `industrial_egg` Œuf Industriel | 90 000 | 35/45/18/2/0 |
| 2 | `scrap_egg` Œuf Ferraille | 140 000 | 25/48/24/3/0 |
| 3 | `neon_egg` Œuf Néon | 1 200 000 | 5/30/50/14/1 |
| 3 | `arcade_egg` Œuf Arcade | 1 800 000 | 0/28/52/18/2 |
| 4 | `voltaic_egg` Œuf Voltaïque | 12 000 000 | 0/12/48/35/5 |
| 4 | `prism_egg` Œuf Prisme | 18 000 000 | 0/8/45/40/7 |
| 5 | `legendary_egg` Œuf Légendaire | 90 000 000 | 0/0/35/50/15 |
| 5 | `mystery_egg` Œuf Mystère | 120 000 000 | 0/0/25/55/20 |
| 6 | `cosmic_egg` Œuf Cosmique | 800 000 000 | 0/0/15/55/30 |
| 6 | `ufo_egg` Œuf OVNI 🛸 | 1 200 000 000 | 0/0/0/55/45 |

> Les anciens ids (`common_egg`, `industrial_egg`, `neon_egg`, `legendary_egg`, `mystery_egg`) sont **conservés** (les saves restent compatibles) ; on en **ajoute** 7.

### A.2 Rotation
- `currentBucket()` / `nextRefreshAt()` inchangés (900 s).
- `lineupFor(bucket)` retourne **6 ids** (un par palier). Pour le palier `k`, choisit déterministe entre ses 2 variantes : `variants[1 + (bucket % #variants)]`. ⇒ même lineup pour tous, alterne chaque refresh.
- Garde-fou : le palier 1 est **toujours abordable** (œuf à 5–12 k) ⇒ jamais de boutique morte pour le slot 1.

### A.3 Déblocage des slots (en $, croissant)
- `data.eggSlots` démarre à **1**. Achetable jusqu'à **6**.
- `EGG_SLOT_COST = { [2]=150_000, [3]=3_000_000, [4]=60_000_000, [5]=600_000_000, [6]=6_000_000_000 }` (tuning knob).
- Slot 6 = endgame (multi-milliards). Avoir les 6 slots = endgame, comme demandé.

### A.4 Affichage des 6 piédestaux (par joueur)
- slot `k ≤ eggSlots` : œuf qui tourne (couleur = rareté dominante), label **nom + prix** (visible seulement de près, §D), prompt « Acheter $X ».
- slot `k == eggSlots + 1` : cadenas + label « 🔒 Débloquer ce slot » + prompt « Débloquer — $Y » (→ `buyEggSlot`).
- slot `k > eggSlots + 1` : cadenas grisé, **pas de prix**. (Un joueur 1-slot ne voit donc bien qu'**1 œuf**.)

### A.5 Achats serveur-autoritaires
- `buyEgg(player, slot)` : revalide `slot ≤ eggSlots`, mappe slot→eggId via `lineupFor(currentBucket())[slot]`, vérifie solde, débite, **grant un œuf-objet** (cf. §B) — **ne hatch plus directement**. Erreurs : `locked_slot`, `cant_afford`, `lineup_changed`.
- `buyEggSlot(player)` : `cur = eggSlots` ; refus si `cur ≥ 6` ; coût `EGG_SLOT_COST[cur+1]` ; débite ; `eggSlots = cur+1`.
- Anti-spam : un refresh de lineup entre l'affichage client et l'achat ⇒ le serveur valide contre le bucket courant et renvoie `lineup_changed` (le client rafraîchit).

---

## B. Flux achat → main → éclosion (œuf-objet)

### B.1 Données & objet
- `data.eggsInv[uid] = { eggId }` (uid = `Id.new()`). Soft-cap **50 œufs** non éclos (refus d'achat au-delà, notif) — anti-abus.
- `ToolService.reconcile` mirroir `data.eggsInv` → **Egg Tools** dans le Backpack (nouveau `Kind="egg"`, clé `e:<uid>`), en plus des pinces. Attrs : `Kind="egg"`, `EggUid=uid`, `DefId=eggId`, `Rarity=<rareté dominante>`.
- Egg Tool : `RequiresHandle=true`, `CanBeDropped=false`. **Handle non solide** (`CanCollide=false`), petit mesh « œuf » coloré par rareté. (Visuel en main uniquement, « pas un objet solide ».)

### B.2 Tenir & éclore
1. Le joueur équipe l'œuf (sac custom — natif désactivé) → œuf **tenu en main**.
2. **Clic** = `Tool.Activated` → `Net.request("hatchEgg", {uid})`.
3. Serveur `hatchEgg` : valide possession ; `defId = Eggs.rollPet(eggId)` ; **si roll échoue → ne consomme pas** ; sinon retire `eggsInv[uid]`, `PetService.grant(defId, 1)`, **auto-déploie** si < 3 déployés, événement `petHatched{uid,defId,rarity,name}`, replicate (⇒ reconcile retire l'Egg Tool).
4. Client : FX d'éclosion **dans la main / au-dessus du perso** (œuf qui se fissure + reveal animal teinté rareté, réutilise le pipeline dopamine `RouletteRollController`/FXKit). Le pet apparaît dans le Menu Pets (badge « Nouveau »).

### B.3 Sac (BackpackController)
- Affiche les **Egg Tools** (icône œuf + couleur rareté) en plus des pinces (équiper par clic / touche, comme les pinces). Activer un œuf équipé = éclore.
- Idempotence : double-clic / spam ⇒ le serveur retire l'uid atomiquement ; 2e requête trouve `nil` ⇒ no-op silencieux.

---

## C. Pets — déploiement (cap 3), errance plot, upgrade $, vente

### C.1 Posséder vs déployer
- `data.pets[uid] = { defId, level, locked }` (existant). **Remplace `equippedPets` par `deployedPets`** (liste d'uid, taille ≤ **3 fixe**). Supprime `petSlots` + `buyPetSlot`.
- Déployer/Recall depuis le Menu Pets. Déployer un 4e → refus « 3 pets max dans le plot ».
- Vendre un pet déployé → **auto-recall** puis vente (pas de blocage frustrant).

### C.2 Errance dans le plot
- `PetController` : trouve le plot local (attribut `OwnerUserId`, comme `PlotController`), calcule l'emprise (bbox du `Base`/footprint), choisit des waypoints aléatoires **dans** l'emprise (marge bord), marche + bob + orientation (lerp, pas de pathfinding). Rendu **local** seulement.
- Edge : plot non encore prêt (join) → différer le rendu jusqu'à `PlotController`/plot dispo ; plot repositionné → recalculer l'emprise ; pet retiré → détruire le modèle.

### C.3 Menu (clic DROIT) & upgrade $
- **Clic droit** sur un pet errant (ClickDetector `RightMouseClick`) → menu détail : nom, rareté, **niveau N/10**, bonus passifs (magnitudes à N), capacité active + cooldown, vente. Toujours accessible aussi via **P** (grille).
- Bouton **« Améliorer — $X »** : `upgradePet(uid)` serveur, niveau +1 (max 10), débite `Pets.upgradeCost(def, level)` (croissant, ↑ avec la rareté). À niveau 10 → bouton « Niveau max » désactivé.
- **Fusion supprimée** : retirer `fuse`/`fusePet`/le bouton + toute référence.
- Boutons : **Déployer / Recall**, **Améliorer $**, **Vendre $** (`Pets.sellValue` inchangé ; confirmation épiques+).

### C.4 Bonus & capacités actives
- Agrégation (`Pets.applyPetStats`/`bonusValue`/`sellBonus`) lit désormais **`deployedPets`** au lieu d'`equippedPets`. Aucune formule changée.
- Tick capacités actives (`PetService`) : sur les **déployés**. Inchangé sinon.
- Consommateurs (`CatchService.effectiveStats`/`doGrab`, `InventoryService.sellStack`, `AutomationService`, offline `DataService`) : juste renommer la source équipés→déployés.

---

## D. Build 3D (Studio, via MCP — Studio est connecté)

### D.1 Retrait roulette placeholder
- Supprimer `Workspace.Environment.RoulettePad`, `RoulettePost`, `RouletteSign` (aucune référence script — vérifié). Ne PAS toucher `ShopService`/`plot.Roulette` (la vraie roulette).

### D.2 EggShop → 6 piédestaux
- Reconstruire/étendre `Workspace.Environment.EggShop` à **6 piédestaux** (`Pedestal1..6`, attr `EggSlot=1..6`), comptoir élargi, alignés et espacés (pas de chevauchement). Chaque `Pedestal.Egg` : `BillboardGui` label (nom+prix) + `ProximityPrompt` « BuyPrompt » + mesh œuf.
- `Countdown` SurfaceGui « Réapprovisionnement dans MM:SS » conservé.

### D.3 NPC style personnage Roblox
- Reproportionner le NPC (`EggShop.NPC`) en silhouette personnage Roblox propre (tête ronde + visage cartoon, torse, bras, jambes, tablier de marchand « Plaid », chapeau), palette `Theme`, **idle anim** légère (bob/coucou) côté client. Billboard nom « Marchand d'Œufs » avec `MaxDistance`.

### D.4 Décor sans chevauchement
- Scan d'overlap (helper carré, cf. memory `project-architecture`) sur les décors de la zone (CrateEgg, props) ; repositionner les offenders ; profiter de l'espace libéré par la roulette. Rien d'encastré.

### D.5 MaxDistance partout
- `BillboardGui.MaxDistance` sur : labels prix/rareté des œufs (≈ 32 studs), nom du NPC, nom des pets. ⇒ plus de texte visible « de toute la map ». Les slots verrouillés au-delà du prochain n'ont **pas** de label.

---

## E. Blender — 10 animaux (import différé)

- Pipeline validé (memory `blender-to-roblox-pipeline`) : **1 objet par zone de couleur**, modèle propre & bien proportionné. Roster **conservé** (mêmes 10 ids/`model`) : `bunny_plush`, `bolt_bot`, `foam_cube`, `windup_duck`, `neon_kitten`, `magnet_drone`, `golden_teddy`, `mini_clawbot`, `holo_fox`, `ufo_mascot`.
- Livrables dans `Elements_Blender/pets/` : un script de build Python (style `claw_rig_build.py`), les **.blend** sauvegardés, des **previews** rendues, et un `asset_ids.json` vide à remplir après upload.
- **Pas d'upload / import maintenant** (plugin non connecté). Quand importés dans `ReplicatedStorage.Assets.PetMeshes[model]`, `PetController` les préfère déjà aux procéduraux (fallback en place).
- Fallback accepté : si rigging trop lourd, anim procédurale (bob/marche) sur mesh statique de qualité.

---

## F. Données, migration & edge cases

### F.1 Profil (`GameConfig.PROFILE_TEMPLATE`)
```
pets          = {},   -- { [uid] = { defId, level, locked } }  (inchangé)
deployedPets  = {},   -- liste d'uid, ≤ 3   (REMPLACE equippedPets)
eggsInv       = {},   -- { [uid] = { eggId } }   (NOUVEAU)
eggSlots      = 1,    -- 1..6, achetable   (NOUVEAU)
-- SUPPRIMÉS : petSlots, equippedPets (migrés), unlock par œuf
stats.lifetimeEarned  -- conservé (plus utilisé pour le gating œufs ; garde pour autres usages)
```

### F.2 Migration (`ProfileStore:Reconcile` + patch DataService)
- `Reconcile` ajoute `deployedPets={}`, `eggsInv={}`, `eggSlots=1`.
- `equippedPets` existant → copier dans `deployedPets` (tronqué à 3), puis ignorer `equippedPets`.
- `petSlots` ignoré (cap fixe 3).
- Saves existantes avec pets via l'ancien instant-hatch → conservés tels quels.

### F.3 Edge cases (liste de vérification)
**Boutique / slots :** achat slot verrouillé → refus ; achat hors-solde → refus + notif ; achat slot ≠ suivant / déjà 6 → refus ; refresh lineup pendant l'achat → `lineup_changed` + rafraîchit ; soft-cap 50 œufs.
**Éclosion :** clic sans tenir l'œuf → ignoré (hatch via Activated only) ; spam → atomique no-op ; roll échoue → œuf non consommé ; 3 déjà déployés → pet stocké (pas auto-déployé) + notif « déploie-le depuis le menu ».
**Pets / déploiement :** déployer un 4e → refus ; recall libère le bonus ; vendre déployé → auto-recall ; upgrade au max → bouton off ; 0 pet → menu vide état ; plot non assigné → différer déploiement jusqu'à plot prêt.
**Objets non solides :** Egg Tool & visuels `CanCollide=false`, `CanBeDropped=false` ; reconcile gère le nouveau Kind sans casser pinces.
**3D :** retrait roulette sans casser la vraie roulette ; 6 piédestaux sans chevauchement ; MaxDistance sur tous les billboards ; slots verrouillés sans label.
**Réseau :** `Net.request` renvoie `{ok,data}` ; tous les achats/éclosions revalidés serveur.

### F.4 Fichiers touchés
**Configs :** `Eggs` (pool 12 + tiers + `EGG_SLOT_COST` + lineup 6 + `unlock` retiré), `Pets` (+`upgradeCost`, fusion retirée), `GameConfig` (profil), `Types` (+`OwnedEgg`, maj).
**Services :** `EggShopService` (6 slots, `buyEgg`→objet, `buyEggSlot`, `hatchEgg`, gating eggSlots, prompts), `PetService` (deploy/recall/upgrade/sell, retrait fuse/buySlot, agrège déployés), `ToolService` (branche egg + held + activable), `DataService` (migration + offline déployés), `CatchService`/`InventoryService`/`AutomationService` (source équipés→déployés).
**Client :** `EggShopController` (6 piédestaux, gating, MaxDistance, FX éclosion au clic), `PetController` (errance plot, clic droit), `PetMenuController` (upgrade $/deploy/sell, fusion retirée, vignettes), `BackpackController` (œufs).
**3D (Studio MCP) :** retrait roulette, EggShop 6 piédestaux, NPC, décor, MaxDistance.
**Blender :** `Elements_Blender/pets/` (10 modèles + script + previews).

---

## G. Phases d'implémentation

1. **Config & données** — `Eggs` (pool/tiers/lineup6/slot costs), `Pets` (upgradeCost, -fusion), `GameConfig`/`Types`, migration `DataService`.
2. **Serveur core** — `PetService` (deploy/recall/upgrade/sell, agrège déployés, -fuse/-buySlot), branchements consommateurs (équipés→déployés).
3. **Boutique serveur** — `EggShopService` (lineup 6, gating eggSlots, `buyEgg`→objet, `buyEggSlot`, `hatchEgg`, prompts/notifs).
4. **Inventaire œuf-objet** — `ToolService` (Kind egg + held non-solide + reconcile), `BackpackController` (affichage/équip/activer œufs).
5. **Client boutique & pets** — `EggShopController` (6 piédestaux/gating/MaxDistance/FX éclosion), `PetController` (errance plot/clic droit), `PetMenuController` (upgrade $/deploy/sell).
6. **Build 3D** — retrait roulette, EggShop 6 piédestaux, NPC, décor sans chevauchement, MaxDistance.
7. **Blender** — 10 animaux + script + previews (import différé).
8. **Équilibrage & vérif end-to-end** — calibrer prix œufs/slots/upgrade sur la vraie courbe de revenus, tester tous les edge cases §F.3.

---

## H. Vérification (end-to-end)
- Boot propre (console sans erreur ; services OK).
- Achat slot d'œuf : eggSlots 1→…→6, piédestaux révélés, coûts débités, refus quand pas le suivant / pas de solde.
- Achat œuf : œuf-objet dans le sac (pas un pet direct), tenu en main non solide.
- Éclosion : clic → pet granté (distribution conforme aux poids sur N tirages), FX, auto-déploiement si < 3.
- Déploiement : 3 max, errance **dans le plot**, recall, bonus actifs uniquement déployés (dump `effectiveStats`).
- Upgrade $ : niveau +1, coût débité, magnitudes scalent, max 10 ; fusion absente.
- Vente : valeur correcte, auto-recall si déployé.
- 3D : roulette absente, 6 piédestaux propres, labels seulement de près, NPC ok, aucun décor encastré.
- Compat saves : `equippedPets`→`deployedPets` (≤3), `eggSlots=1`, joueurs existants OK.

## I. Tuning knobs
Prix des 12 œufs, `EGG_SLOT_COST`, `Pets.upgradeCost` (facteur/exposant), magnitudes/scaling pets (existant), cooldowns actifs (existant), soft-cap œufs (50), refresh 900 s, `MaxDistance` billboards (~32), cap pets déployés (3).
