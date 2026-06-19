# Système de Pets — Phases 2→7 : Record d'implémentation

**Date :** 2026-06-17
**Statut :** implémenté + vérifié live (Edit DM, **EN ATTENTE de Ctrl+S**). Implémenté en continu (pas de plan TDD par micro-tâche pour ces phases ; vérif par Script temporaire dans la vraie VM serveur + boot propre). Spec : `2026-06-17-pet-system-design.md`. Phase 1 : `2026-06-17-pet-system-01-data-bonus-core.md`.

> ⚠️ **VM isolée** : `execute_luau(datamodel_type="Server")` ne voit pas le Registry live → tous les tests passent par un `Script` temporaire sous `ServerScriptService` qui `print("TAG: …")` (lu via console), puis supprimé. (cf. memory `roblox-studio-mcp-gotchas`.)

## Phase 2 — Capacités actives + passifs restants ✅
- `PetService` réécrit : tick Heartbeat ~1 s déclenchant les `active` des pets équipés sur cooldown (`Pets.cooldownAt`, **plancher 30 s**) ; flags `consumeCritFlag`/`isDoubleGrab`. Dispatch : `autosell`(InventoryService.sellFiltered), `guaranteed_crit`(flag), `double_grab`(fenêtre os.clock), `jackpot`/`prize_rain`(burst cash ∝ avgIncomePerSec). Event `petAbility`. (+ clamp niveau dans `grant`.)
- `CatchService.doGrab` : `yieldChance += Pets.bonusValue(data,"yield")` ; bloc crit refondu = `crit_master` + `Pets.bonusValue(data,"crit")` + `forcedMult` (flag) ; `sellMultTotal += Pets.sellBonus`. Tick : double-grab → `doGrab` ×2.
- `AutomationService` : `effMagnetLevel(data) = magnetLvl + petMagnet*10` (gate+interval+pulse) ; `grantOffline` pct/gate incluent `Pets.bonusValue(data,"offline")`.
- **Vérif** `PETACT: PASS` (5 actives via cooldown raccourci à 2 s → mais plancher 30 s, donc attente 34 s).

## Phase 3 — Eggs config + EggShopService ✅
- `Config.Eggs` : 5 œufs (common/industrial/neon/legendary/mystery) prix+unlock+weights ; `lineupFor(bucket)` global déterministe (Fisher-Yates seedé, `common_egg` garanti) ; `rollPet(eggId)` (rareté pondérée → pet aléatoire) ; `currentBucket`/`nextRefreshAt` (REFRESH=900 s).
- `EggShopService` : `getPetShop` (lineup+unlock par joueur), `buyEgg` (in-lineup + gating lifetimeEarned + spend + roll + `PetService.grant` + event `petHatched`), `PromptTriggered` sur `BuyPrompt` (via attribut `EggSlot`), refresh loop → `petShopRefreshed` + notif.
- **Vérif** `PETSHOP: PASS` (lineup, gating "locked", "not_in_lineup", buy charge 5000 + grant) ; distribution `rollPet` ~70/25/5.

## Phase 4 — Build 3D du shop ✅
- `workspace.Environment.EggShop` procédural idempotent (~(-490,0,0), « au bout de la map », collé à la roulette via connecteur) : pad orange + bordure + **foundation** (anti-flottement), mur+arche « MARCHAND D'ŒUFS » (SurfaceGui), **countdown** SurfaceGui (`Countdown/CountdownGui/Time`), 3 piédestaux (`Pedestal i` + `Egg` boule + `BuyPrompt` + `Info` billboard `EggName`/`EggPrice`), attribut `EggSlot`.

## Phase 5 — Errance + interaction + menus ✅ (3 controllers, +19 total)
- `EggShopController` : remplit nom/prix/lock + couleur d'œuf (rareté top) + countdown (maj/s) + spin des œufs + **FX éclosion** (`petHatched` → popup Theme.Panel pop-in).
- `PetController` : rend les pets équipés (`Assets.PetMeshes[model]` sinon placeholder), errance waypoints+bob autour du perso, ClickDetector→menu ; sync `StateController`.
- `PetMenuController` : grille des pets (icône+niveau, surbrillance équipés) + détail (icône/nom/rareté/passifs) + boutons Équiper/Déséquiper/Fusionner(si 3)/Vendre/Slot ; **touche P**. Net.request vers les remotes.
- **Vérif** : boot propre 19 controllers 0 erreur ; capture → 3 pets errants rendus avec billboards. (Menu/FX compilent ; **playtest humain** recommandé.)

## Phase 6 — Modèles de pets ✅
- `ReplicatedStorage.Assets.PetMeshes` = **10 modèles procéduraux distincts** (corps/tête/yeux + features : oreilles lapin, antenne bot, cube, bec canard, oreilles chat+queue néon, anneau+aimant drone, ourson, claw-bot vitré, renard holo translucide, alien+soucoupe). `PetController` les utilise ; **meshes héros Blender = follow-up** (drop dans PetMeshes, le controller les préfère).

## Phase 7 — Équilibrage & vérif end-to-end ✅
- Valeurs calibrées de la spec conservées (œufs 5k→25M, magnitudes faibles, cooldowns 180/150/120 + plancher 30 s, slots 250k/5M/80M) — boutons de réglage en tête des modules.
- **Vérif** `PETFINAL: PASS` : buyEgg→hatch→equip→`applyPetStats` bonus→fuse L2→sell crédit ; boot propre 16 services/19 controllers, 0 erreur pet (les `animation failed to load` + `[TASK4-TEMP]` sont préexistants, hors pets).

## Reste / follow-up
1. **Ctrl+S** pour persister dans `build.rbxlx`.
2. **Playtest humain** : ouvrir le menu (P), aller au shop, acheter un œuf via prompt, voir l'éclosion, fusionner/vendre.
3. **Meshes Blender héros** (10 pets riggés idle+marche) → upload → `PetMeshes` (remplace les procéduraux).
4. Polish optionnel : anti-chevauchement de l'errance, placement fin du shop sur sol plein, slip/FX d'éclosion œuf qui se fissure.
