# Récompenses de temps de jeu — Design (2026-06-19)

## 1. Contexte & objectif

Nouveau menu GUI **« Récompenses de temps de jeu »** pour le tycoon scrapyard / UFO-catchers.
Un bouton dans la colonne `MainHUD.Sidebar` ouvre un panneau centré premium (style `Theme`) listant
une grille de **12 récompenses** débloquées par le **temps passé en jeu dans la session courante**.

Objectifs : rétention (donner envie de rester connecté), feeling "game feel" premium cohérent avec
les autres menus, récompenses **adaptées à la courbe de progression** et **incassables pour l'économie**.

## 2. Décisions clés (validées)

1. **Session uniquement, ZÉRO persistance inter-session.** Le timer repart de 0 à chaque connexion ;
   la progression de la session est effacée à la déconnexion. Aucune donnée sauvegardée (pas de drapeau
   quotidien, pas d'EMA persistée lue, pas de plafond dynamique).
2. **Cash = montants FIXES & modestes**, escaladant avec le temps. Conséquence assumée : le cash est le
   "sucre" de l'early/mid-game et devient trivial pour un compte très avancé. **Ce sont les BOOSTS
   (auto-équilibrés) et les OBJETS indexés (loot/œuf/pet) qui gardent le menu pertinent en lategame.**
3. **Boosts temporés = nouvelle infra `BoostService`**, implémentés en **ADDITIF** (jamais un ×2 littéral
   sur la sortie).
4. **Approche A (sync)** : le serveur envoie le planning + `joinedAt` à la connexion ; le client calcule
   des comptes à rebours fluides en local ; le **claim est validé côté serveur** (autoritaire,
   anti-double-claim).
5. **Indexation par stade** des récompenses-objets : loot/œuf/pet montent en rareté selon la progression
   live du joueur (lecture seule, aucune écriture).
6. **Cadence ~1h30 / 12 paliers**, front-loadée (1ʳᵉ récompense à 1 min).
7. **Bouton** : clone d'`IndexBtn` dans `MainHUD.Sidebar`.

### Pourquoi pas le modèle "hybride scalé sur le revenu" (rejeté)

La vérif adversariale a prouvé qu'un cash scalé sur le revenu/sec **persisté** + reset session pur est
**farmable par reconnexion** (le reward est un bonus ADDITIF par-dessus le revenu machine ; se reconnecter
re-déclenche les paliers). Bloquer ça proprement exigerait une trace persistante (drapeau 1×/jour), ce qui
contredit la contrainte "zéro persistance". Choix retenu : **cash fixe & petit** → non rentable à farmer
par sa taille absolue + gating temporel des gros paliers ; aucune persistance requise.

## 3. Modèle de progression (référence de calibration)

Extrait des scripts live (revenu/sec moyen ≈ ; banque type ≈) :

| Stade | revenu/sec | banque type | prochains achats |
|-------|-----------|-------------|------------------|
| Nouveau (0-10 min) | ~$5 (bursty ~0) | $250 | slot s3 $200, pinces $50-97, luck $218 |
| Early (~1h) | ~$16 | $6k | s4-s7 $600-14k, Chance L1 $660, œuf commun $5k |
| Mid (~3-8h) | ~$985 | $200k | s8 $40k, Étage-2 $100k + f1 $120k, egg-slot-2 $150k |
| Late (~15h) | ~$72k | $6M | slots f2-f8 $250k-16M, œufs 1.2-18M, egg-slot-3 $3M |
| Endgame (~25h+) | ~$54M | $1B | œufs 90M-1.2B, egg-slots 60M-6B |

Le cash fixe est ancré **sous l'échelle `IndexRewards`** (2k→750k, déjà traitée comme équilibrée par le jeu),
escaladant avec le temps de déblocage : petit tôt (farm sans intérêt), plus gros sur les paliers profonds
(gatés 33-90 min → re-farm absurde).

## 4. Table de récompenses (finale)

Cadence cumulée (s) : 60, 180, 360, 660, 1020, 1440, 1980, 2580, 3300, 4020, 4740, 5400.

| # | Temps | Type | Récompense (valeurs de départ — réglables en config) | Tier visuel |
|---|-------|------|------------------------------------------------------|-------------|
| 1 | 1:00 | cash | **$1 000** | normal |
| 2 | 3:00 | boost | **Boost ×2 Cash · 5 min** (additif `cash` +1.0) | normal |
| 3 | 6:00 | cash | **$5 000** | normal |
| 4 | 11:00 | loot | **Cache Rare ×3** — loot indexé `clawGateOrder + 1` | rare |
| 5 | 17:00 | boost | **Boost Chance · 8 min** — `luck` +max(0.6, 0.25·luck) | rare |
| 6 | 24:00 | prize_rain | **Pluie de Lots ≈ $30 000** (pool fixe, pièces ramassables) | rare |
| 7 | 33:00 | cash | **$75 000** — 1ᵉʳ "wow" | rare |
| 8 | 43:00 | egg | **Œuf Mystère** — œuf indexé (1 cran sous l'abordable) | premium |
| 9 | 55:00 | boost_double | **Rendement +30% & Vitesse +25% · 8 min** | premium |
| 10 | 67:00 | cash | **$250 000** | premium |
| 11 | 79:00 | loot | **Coffre Légendaire ×2** — loot indexé `clawGateOrder + 2` (cap transcendent) | premium |
| 12 | 90:00 | pet_jackpot | **JACKPOT — pet indexé (`bestOwnedPet + 1`) + $500 000** | premium ✨ |

Ladder cash fixe : **1k → 5k → 30k → 75k → 250k → 500k**.
Mix : 4× cash (dont 1 pluie), 3× boosts (cash / chance / rendement+vitesse), 2× loot indexé, 1× œuf indexé,
1× pet+magot. 5 récompenses restent pleinement pertinentes en lategame (boosts + objets indexés).

## 5. Mécanismes

### 5.1 Boosts — implémentation ADDITIVE (jamais ×2 littéral)

`BoostService.getMult(player, kind)` renvoie l'identité si inactif : **0** (additif) pour `cash`/`luck`/`yield`,
**1.0** (multiplicatif) pour `speed`. Points de lecture (confirmer la ligne exacte à l'implémentation) :

- **cash** : `+getMult(p,"cash")` ajouté dans la somme `sellMult` de `InventoryService.sellStack`
  (et au calcul de cash de `CatchService.doGrab` si applicable). Additif +1.0 ⇒ +90% pour un débutant
  (1.1×→2.1×), +49% pour un compte maxé (2.05×→3.05×) → reste perceptible partout, jamais 4.1×.
- **luck** : `eff.luck += max(0.6, 0.25 · eff.luck)` dans `CatchService.effectiveStats`
  (forme scalée-additive : garde ~+18-22% d'uplift constant à tous les stades, jamais < +0.6).
- **yield** : `eff.yieldChance += 0.30` (T9) à `CatchService.doGrab`.
- **speed** : `grabSpeed *= 0.80` (T9, +25% cadence) au site de scheduling du grab.

Règles : ne jamais empiler deux boosts du même `kind` (prendre le max) ; un reclaim ne rafraîchit pas un
boost déjà actif (ignoré jusqu'à expiration) ; durées cash 5 min, luck 8 min, rendement+vitesse 8 min.
Comme chaque palier ne se réclame qu'une fois par session, il n'y a pas d'uptime permanent.

### 5.2 Indexation des objets (lecture live, sans persistance)

- `clawGateOrder` = rareté de la meilleure pince possédée/placée, mappée sur l'échelle loot 1-10
  (common, uncommon, rare, epic, legendary, mythic, relic, divine, cosmic, transcendent).
- **T4** : 3× loot à `min(clawGateOrder+1, 10)` (défaut `rare` pour un compte neuf).
- **T11** : 2× loot à `min(clawGateOrder+2, 10)` (défaut `legendary`).
- **T8** : 1 œuf au cran **sous** le meilleur œuf abordable sur l'échelle `Eggs` 12 crans
  (commun→OVNI). Défaut `industriel` pour un mid.
- **T12** : 1 pet garanti au cran **au-dessus** du meilleur pet possédé sur l'échelle `PetRarities`
  5 crans (commun→legendaire). Défaut `rare`.

### 5.3 Pas de plafond / pas de drapeau

Cash fixe ⇒ aucun plafond universel, aucun drapeau quotidien. Le seul garde-fou est la **taille absolue
modeste** + le **gating temporel** des gros montants. Tolérance de farm acceptée (re-claim des petits
montants par reconnexion non rentable vs jouer).

## 6. Comportement de session

- État serveur par joueur : `sess[player] = { joinedAt = os.clock(), claimed = {} }`.
- Init dans `DataService.onReady`, **effacé dans `DataService.onRemoving`** → timer à 0 au retour.
- Un palier est **réclamable** quand `os.clock() - joinedAt >= unlockTimeSec` et `not claimed[tier]`.
- Le claim est **validé serveur** ; `claimed[tier] = true` empêche le double-claim.
- Les boosts actifs sont aussi de l'état session (effacés à la déconnexion).

## 7. UI / Direction artistique

Référence visuelle : `ScrapyardController` (Theme.Panel + overlay dim + UIScale Back-ease). Utiliser
**exclusivement `ReplicatedStorage.UI.Theme`** (pas `UIUtil`).

### 7.1 Panneau (via `Theme.Panel`)

- `Theme.Panel({ title = "RÉCOMPENSES DE TEMPS DE JEU", size = UDim2.fromOffset(~720, ~560) })`
  → `{ container, card, titleBar, title, close, content }`.
- **Header premium** : sur la `titleBar` bleue standard, appliquer `Theme.Gradient({Purple, Pink})` +
  petit glyphe horloge/cadeau → identité magenta de la réf tout en restant dans la palette. Titre
  `LuckiestGuy` blanc, croix rouge 32×32 standard.
- **Sous-titre** (`FredokaOne`, `Muted`) : « Reste connecté pour débloquer des récompenses — réinitialisé à la déconnexion. »
- **Barre "prochaine récompense"** : mini-icône + « Prochaine dans mm:ss » + barre de progression fine
  (remplie selon `elapsed / nextUnlock`).
- **Corps** : `ScrollingFrame` + `UIGridLayout` 4 colonnes × 3, `AutomaticCanvasSize = Y`,
  `ScrollBarThickness = 8`. Cellules ~150×172, padding 10.
- **Responsive** : `UIScale` clampé sur la taille d'écran ; reflow 4→3→2 colonnes sur petit écran/mobile.
- **Ouverture** : overlay `TextButton` dim 0.45 (clic = ferme) ; `UIScale` 0.7→1 `Back/Out 0.2s` ;
  **cascade** des cartes (UIScale 0→1 avec délai par index). Fermeture : UIScale→0.7 0.12s.

### 7.2 Carte de récompense (`RewardCard`, template réutilisable)

```
┌─────────────┐
│  $5 000     │  Haut : montant (vert, LuckiestGuy) OU nom récompense
│   ☀ rayons  │  Backplate radial teinté rareté (UIGradient, construit)
│  [ ICON ]   │  ViewportFrame 3D (œuf/pet/loot) OU glyphe vectoriel (cash/boost)
│        ×3   │  Badge quantité (loot) en coin
│ ┌─────────┐ │
│ │ 04:32   │ │  Bas (état) : timer  OU  bouton « Réclamer »  OU  stamp ✓
│ └─────────┘ │
└─────────────┘
```

Racine `Frame` + `Corner(14)` + ombre (Frame décalé +6, `Outline`, transp 0.45) + `UIStroke` teinté rareté.
Fond `PanelInner` + léger dégradé teinté rareté. Backplate rayons construit (pas de décalque).

### 7.3 États visuels (4)

| État | Apparence |
|------|-----------|
| **À venir / Verrouillé** | carte assombrie, **timer** mm:ss qui décompte, stroke rareté normal, pas de glow |
| **Prochaine / En cours** | mise en avant : plus lumineuse, pulse "respiration" sur le stroke, tag « PROCHAINE », timer proéminent |
| **Réclamable / Prêt** | **glow vert pulsé** + punch idle (1.0↔1.03) + bouton « Réclamer » vert (`Theme.Button`) + étincelles |
| **Réclamé** | **désaturée** (overlay gris), stamp « ✓ RÉCLAMÉ » tamponné, glow off, stroke atténué |

### 7.4 Tiers de rareté (3, identité intrinsèque)

- **normal** : stroke acier/cyan `darken(Cyan)`, fond plat foncé.
- **rare** : stroke `Purple` + dégradé interne violet + accent ◆.
- **premium** : stroke `Gold` (3px) + dégradé or→ambre + **sheen diagonal animé** + **glow or doux permanent**
  + pastille « ★ PREMIUM ».

Quand une carte est **Réclamable**, le glow vert se superpose à la rareté (vert dominant, identité conservée).

### 7.5 Animations

- Ouverture (overlay fade + UIScale Back + cascade cartes).
- Hover (desktop) : `Position.Y -3` + stroke éclairci 0.1s. Press : scale 0.96.
- **Timer → Prêt** : flash blanc + punch 1.0→1.12→1.0 Back, glow vert fade-in, micro-toast « PRÊT ! » + son.
- **Claim** : punch icône + particules/pièces vers le compteur $ du HUD (cash) + anneau or + stamp ✓ +
  désaturation ; toast `notify` « +$X » (`kind="reward"`) + son chime.
- Premium idle : sheen lent + glow respirant. Prochaine : pulse stroke.

### 7.6 Strip de boosts actifs (HUD)

Cluster de pills (haut-centre du HUD) : `[⚡ ×2 Cash 04:12]`, couleur par type, apparaît quand un boost
tourne (piloté par l'event `boostsChanged`), pulse < 10s. Rend les boosts visibles hors du menu.

### 7.7 Assets

Cohérence > Toolbox (recherche gratuite bruitée/amateur). On **construit/réutilise** :

- **Œuf (T8)** → `ViewportFrame` du vrai mesh d'œuf (`Assets.EggMeshes`).
- **Pet (T12)** → `ViewportFrame` d'un vrai pet (`PetMeshes`, comme `PetMenuController`).
- **Loot (T4, T11)** → builder **`ScrapIcons`** existant (vecteur teinté rareté, comme l'Index).
- **Cash / Pluie** → glyphe liasse verte vectoriel ; alternative : décalque curé `rbxassetid://9220014694`
  (*Stacks Of Cash – Money Cartoon*, gratuit) — seul asset externe envisagé.
- **Boosts** → glyphes vectoriels teintés + glow : ⚡ Vitesse, 🍀 Chance, ×2 Cash, ⬆ Rendement.
- **Rayons backplate** → `UIGradient` radial construit.

## 8. Architecture (serveur / client)

Conventions : services/contrôleurs auto-bootés (`:Init()`/`:Start()`, `Registry.get(name)`),
3 remotes via le wrapper `Net` (`ReplicatedStorage.Shared.Net.Net`).

### 8.1 Serveur — `ServerScriptService.Server.Services`

**`BoostService`** (nouveau) :
- État session `active[player] = { [kind] = { magnitude, expiresAt } }` (jamais persisté).
- `grant(player, kind, magnitude, durationSec)` ; `getMult(player, kind)` (identité si inactif :
  0 additif cash/luck/yield, 1.0 mult speed) ; `getActive(player)` (pour le HUD).
- `RunService.Heartbeat` : balaye les expirations → `Net.sendEvent(player, "boostsChanged", getActive(player))`.
- Init `active[player] = {}` en `DataService.onReady` ; clear en `DataService.onRemoving`.
- **Hooks de lecture** ajoutés dans `InventoryService.sellStack` (cash), `CatchService.effectiveStats`
  (luck, yield) et le site de scheduling du grab (speed).

**`PlaytimeRewardsService`** (nouveau) :
- `sess[player] = { joinedAt = os.clock(), claimed = {} }` ; init `onReady`, clear `onRemoving`.
- En `onReady` : `Net.sendEvent(player, "playtimeInit", { schedule = PlaytimeRewards.client(), joinedAt })`
  (le client calcule les comptes à rebours en local).
- `Net.onRequest("claimPlaytimeReward", { tier })` :
  valider `tier` ∈ [1..12], `os.clock() - sess.joinedAt >= unlockTimeSec`, `not sess.claimed[tier]` ;
  sinon `return false, "err"`. Attribuer selon le type :
  - `cash` → `EconomyService.add(player, "scrap", amount)`
  - `prize_rain` → `CollectibleService.prizeRain(player, …)` calibré ~$30k fixe
    (si la signature ne permet qu'un scaling revenu, passer un `rate` équivalent fixe ou compléter via
    `EconomyService.add` + burst cosmétique — à confirmer à l'implémentation)
  - `boost` → `BoostService.grant(player, kind, magnitude, dur)`
  - `boost_double` → deux `BoostService.grant`
  - `loot` → `InventoryService.addItem(player, { defId, rarity = indexée, modifier = "none" })` ×N
  - `egg` → `data.eggsInv[Id.new()] = { eggId = indexé }` puis `DataService.replicate(player)`
  - `pet_jackpot` → `PetService.grant(player, petDefIndexé)` + `EconomyService.add(player,"scrap",amount)`
  - puis `sess.claimed[tier] = true` ; `return { ok = true, granted = {...} }`.
- Helpers d'indexation (fonctions pures) : `clawGateOrder(data)`, `lootRarityFor(order, offset)`,
  `eggTierFor(data)`, `petTierFor(data)`.

### 8.2 Client — `StarterPlayer.StarterPlayerScripts.Client.Controllers`

**`PlaytimeRewardsController`** (nouveau) :
- En `:Start()` : construit le `ScreenGui` (parent `PlayerGui`) + `Theme.Panel` + 12 `RewardCard`
  (caché par défaut). Expose `open()` / `close()`.
- `Net.onEvent("playtimeInit", fn)` : stocke `schedule` + `joinedAt`, rend la grille, lance la boucle de
  timers locaux (`RunService.Heartbeat`/1s) qui met à jour countdowns + barre "prochaine" + transitions
  d'état (→ Prêt avec FX) sans trafic réseau.
- Clic « Réclamer » → `Net.request("claimPlaytimeReward", { tier })` → si `ok`, jouer le FX de claim selon
  `granted`, passer la carte en "Réclamé".

**`BoostHUDController`** (nouveau, léger) :
- `Net.onEvent("boostsChanged", fn)` → rend/maj le strip de pills de boosts actifs (countdown, pulse < 10s).

**`RewardCard`** (builder, module ou local au controller) : construit une carte depuis une entrée de config.

**Bouton** : instance `StarterGui.MainHUD.Sidebar.RewardsBtn` (clone d'`IndexBtn`, LayoutOrder 5, couleur
Face distincte ex. `Gold`/`Pink`, Label « RÉCOMPENSES ») + 1 ligne `wire("RewardsBtn", function() … end)`
dans `UIController` appelant `PlaytimeRewardsController.open()`.

### 8.3 Config — `ReplicatedStorage.Shared.Config.PlaytimeRewards`

Table des 12 paliers : `{ tier, unlockTimeSec, rewardType, displayName, visualTier, cashAmount?,
boostKind?, boostMagnitude?, boostDurationSec?, lootOffset?/count?, … }` + un `PlaytimeRewards.client()`
renvoyant la version "safe" envoyée au client (sans logique serveur sensible).

### 8.4 Remotes

Réutilise les 3 remotes existants via `Net`. Nouveaux noms : events `playtimeInit`, `boostsChanged` ;
action `claimPlaytimeReward`. **Aucun nouveau `RemoteEvent`.**

## 9. Composants à créer (récapitulatif)

| Type | Chemin |
|------|--------|
| Service | `ServerScriptService.Server.Services.BoostService` |
| Service | `ServerScriptService.Server.Services.PlaytimeRewardsService` |
| Config | `ReplicatedStorage.Shared.Config.PlaytimeRewards` |
| Controller | `StarterPlayer.StarterPlayerScripts.Client.Controllers.PlaytimeRewardsController` |
| Controller | `StarterPlayer.StarterPlayerScripts.Client.Controllers.BoostHUDController` |
| UI builder | `RewardCard` (module ou local au controller) |
| Instance GUI | `StarterGui.MainHUD.Sidebar.RewardsBtn` (clone d'`IndexBtn`) |
| Édition | `UIController` : 1 ligne `wire("RewardsBtn", …)` |
| Éditions hooks | `InventoryService.sellStack` (cash), `CatchService.effectiveStats`/`doGrab` (luck/yield), site scheduling grab (speed) |

Réutilise : `ReplicatedStorage.UI.Theme`, `ScrapIcons`, ViewportFrame helpers, `Net`, `EconomyService`,
`InventoryService`, `PetService`, `CollectibleService`, `DataService`, `Registry`.

## 10. Hors-scope / risques / réglages

- **Hors-scope** : récompenses inter-session, streaks de connexion quotidienne, monnaies nouvelles
  (tickets/tokens/crates — on réutilise œufs + loot existants), gamepass boosts (le `BoostService` est
  réutilisable plus tard mais pas câblé ici).
- **Risques** : (a) `multi_edit` MCP peut no-op silencieusement → vérifier chaque édition par relecture ;
  (b) signature exacte de `CollectibleService.prizeRain` à confirmer pour le pool fixe ; (c) points de
  lecture exacts des boosts (lignes) à confirmer dans `CatchService`/`InventoryService` ; (d) confirmer
  le builder `ScrapIcons` (chemin) et les meshes œuf/pet pour les ViewportFrames.
- **Réglages (config)** : la ladder cash (1k→500k), les durées/magnitudes de boost, les offsets
  d'indexation, et le pool de la pluie sont tous dans `PlaytimeRewards` pour ajustement en playtest.

## 11. Critères d'acceptation

1. Un bouton « RÉCOMPENSES » apparaît dans `MainHUD.Sidebar` et ouvre le panneau (anim premium).
2. Les 12 cartes affichent le bon état (verrouillé/prochaine/réclamable/réclamé) et des timers corrects.
3. Le 1ᵉʳ palier devient réclamable à 1 min de session ; réclamer attribue la récompense et la carte passe
   « Réclamé » (pas de double-claim).
4. Les boosts s'activent, sont lus par les services (effet réel mesurable), expirent, et s'affichent dans
   le strip HUD.
5. Les objets indexés (loot/œuf/pet) montent en rareté selon la progression du joueur.
6. À la déconnexion/reconnexion : timer remis à 0, paliers re-verrouillés, boosts effacés (zéro persistance).
7. Cohérence visuelle complète avec les autres menus (`Theme`).
