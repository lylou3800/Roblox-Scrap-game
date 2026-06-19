# Refonte Économie & Progression — Design

**Date :** 2026-06-16
**Statut :** validé en brainstorm, prêt pour le plan d'implémentation
**Décisions cadres (validées par l'utilisateur) :** monnaie unique `$` · pas de rebirth · cible de rythme **~15-25 h** pour le gros de la progression · **refonte complète** (rééquilibrage + onglet Amélios riche + nouvelles mécaniques dopamine).

---

## Contexte — pourquoi ce changement

Le jeu (UFO Catchers) a une boucle saine — *pince attrape → tas → vente au robot → `$` → on dépense* — mais sa **progression globale est plate** :

1. **L'onglet Amélios est pauvre** : seulement 2 améliorations de compte (`luck`, `grab_speed`), plafonnées **niveau 10**, maxées pour ~36 k $ **en tout**. Après ~30 min, le joueur n'a plus aucune progression d'usine globale. C'est le cœur de la demande.
2. **Les Parts `⚙` sont une monnaie morte** : gagnées au recycleur, dépensées nulle part d'utile.
3. **Toute la dopamine repose sur le RNG de rareté** : il manque les stats demandées (vitesse de récup, rendement, revente) **et** des mécaniques « waouh » (crit/jackpot, automatisation, gains passifs).

**Objectif :** une progression cohérente, longue (~15-25 h sur le gros, la collection/index en fil rouge par-dessus), à dopamine maximale mais dosée — paliers rapprochés la 1ʳᵉ heure puis qui s'espacent. Transformer **Amélios** en *« Centre de Commande de l'Usine »* et rééquilibrer **tous** les prix/courbes sur un cadre unifié.

**Non-goals :** pas de rebirth/prestige d'usine pour cette passe ; pas de 2ᵉ/3ᵉ monnaie (tout en `$`) ; on ne touche pas à la génération des stats de pinces (`ClawDesign.genStats`) ni aux visuels.

---

## État actuel (référence) — fichiers & valeurs

Tous les *configs* sont dans `ReplicatedStorage.Shared.Config.*`, les services dans `ServerScriptService.Server.Services.*`.

- **Monnaies** (`GameConfig.CURRENCY`) : `scrap` = `$` (vente), `parts` = `⚙` (recyclage). Départ : 50 $, 0 ⚙, pince `common_1` en slot s1 ; s1+s2 déverrouillés.
- **Boucle de production** (`CatchService`) : chaque pince placée grab toutes les `grabSpeed` s → `rollLoot` (item via `dropWeight`, **rareté** tirée et bridée à `order ≤ clamp(tier+1,1,10)`, modificateur) → `InventoryService.addItem` (le tas). Vente = `InventoryService.sellStack` → `floor(unit × n × (1 + Crafts.bonus(sellMult)))`.
- **Valeur d'un butin** (`Pricing.valueOf`) = `floor(baseValue × rarité.valueMult × modificateur.valueMult)`, min 1. `baseValue` 2-140 (`LootTable`) ; `valueMult` rareté 1→60 000 (`Rarities`) ; modificateur ×2→×25 (`Modifiers`).
- **Améliorations compte** (`Upgrades` + `UpgradeService`, net `buyUpgrade`) : `luck` (base 100, ×1,6, max 10, +0,1/niv) et `grab_speed` (base 120, ×1,6, max 10, −5 %/niv). Consommées dans `CatchService.effectiveStats`.
- **Upgrade par pince** (`ClawUpgrade` + `ClawUpgradeService`) : `costFor = 50·(1+0,9(tier−1))·1,18^(level−1)`, max 25 ; `transformCostFor = 5000·(1+1,4(tier−1))·2,2^prestige`, prestige max 5. Payé en `$`.
- **Roulette** (`ShopService`) : levier gratuit, achat de la pince révélée à `priceOf = floor(100·tier²·(1+0,3(rank−1)))`. Upgrades sur le panneau : `SHOP_LUCK` (base 400, ×1,7, max 8, +0,18 luck roulette/niv) et `SLOTS` (base 1500, ×2,1, max 5 → 1→6 plateformes).
- **Slots de parcelle** (`PlotLayout.slots[].unlockCost`, `PlotService.handleUnlock`) : s3=300, s4=900, s5=2 500, s6=6 000, s7=15 000, s8=40 000.
- **Crafts** (`Crafts` + `CraftService`) : 4 machines permanentes payées en **butin par rareté** (pas en monnaie). Bonus `sellMult/modifierAdd/luckAdd/powerAll` lus dans `CatchService`/`InventoryService`.
- **Récompenses index** (`IndexRewards` + `CollectionService`) : paliers pinces 2 k→750 k $, scraps 1,5 k→300 k $ ; codex complet +500 $/+100 ⚙.
- **Recycleur** (`Machines.recycler` + `MachineService`) : 150 $, consomme le butin *gardé* le moins cher → `parts` (rate 0,5/s, yield 0,4×).

---

## A. Cadre de rythme & courbe unifiée

**Modèle de revenu (ancre de calibrage).** Catch ≈ `E[baseValue] × E[rareté] × E[mod] × (1+sellMult) × throughput`.
- **t = 0** (1 pince tier 1, gate rareté ≤ peu commun, luck 0) : ≈ 13 × 1,4 × 1,0 ≈ **18 $/catch**, grab 3,75 s → **~5 $/s**.
- Le revenu monte **~×10 par étage** au fil des slots remplis, des meilleures pinces (gate de rareté qui s'ouvre : ×35 épique, ×120 légendaire, …) et des amélios.

**Règle de calibrage des sinks :** chaque achat doit coûter *quelques minutes à quelques dizaines de minutes* du **revenu courant** au moment où le joueur le vise. → bases basses + croissance douce (×1,45-1,5) pour les amélios longue traîne (« jamais fini ») ; bases hautes + croissance ×1,8-2,1 pour les gros paliers (slots, plateformes).

**Forme commune :** `cost(n→n+1) = round(base × growth^n)` (n = niveau courant, 0-indexé). Coût total pour maxer = `base × (growth^maxLevel − 1) / (growth − 1)`.

**Schéma de jalons visé (la « cadence dopamine ») :**

| Temps | Revenu ~ | Jalons |
|---|---|---|
| 0-5 min | ~5 $/s | slot s3 · 3-4 niv d'Amélios · 1ʳᵉ pince roulette · **1ᵉʳ crit** |
| 5-30 min | ~30-100 $/s | slots s4-s5 · 1ʳᵉ pince rare · Chance niv 1-2 · recycleur |
| 30-90 min | ~0,3-1 k$/s | 8 slots remplis · Automatisation en ligne · 1ᵉʳ **Épique** |
| 1,5-5 h | ~3-30 k$/s | pinces épiques/légendaires · prestige de pince · index ~40 % |
| 5-15 h | ~50-300 k$/s | pinces mythiques+ · amélios profondes · chasse **jackpots** |
| 15-25 h+ | millions/s | index → 100 % · max des amélios clés · top pinces |

---

## B. L'onglet **Amélios** refondu → « Centre de Commande de l'Usine »

**14 améliorations globales** réparties en **5 familles**, toutes multi-paliers. Payées en `$`. Les ✦ sont neuves ; `Chance`/`Vitesse de Pince` réutilisent les ids existants `luck`/`grab_speed` (retunés). `cost(n) = round(base × growth^n)`.

### 🍀 Famille CHANCE & RARETÉ

| id | Nom | Effet / niveau | max | base | growth | total→max |
|---|---|---|---|---|---|---|
| `luck` | **Chance** | +0,08 luck (toutes pinces) | 20 | 150 | 1,45 | ~562 k |
| `quality` ✦ | **Œil Expert** | +0,06 qualityBias | 15 | 220 | 1,50 | ~192 k |
| `modifiers` ✦ | **Modificateurs** | +0,04 modifierChance | 15 | 260 | 1,50 | ~227 k |
| `crit_master` ✦ | **Coup de Maître** | +0,4 % crit ; mult ×10→×50 | 12 | 500 | 1,70 | ~415 k |

### ⚡ Famille CADENCE & DÉBIT

| id | Nom | Effet / niveau | max | base | growth | total→max |
|---|---|---|---|---|---|---|
| `grab_speed` | **Vitesse de Pince** | ×0,97 temps de grab (multiplicatif) | 20 | 180 | 1,45 | ~675 k |
| `multi_grab` ✦ | **Multi-Prise** | +0,015 multiGrab (combos) | 15 | 300 | 1,50 | ~262 k |
| `weight_cap` ✦ | **Capacité de Charge** | ×1,06 weightCap | 15 | 240 | 1,50 | ~210 k |

### 💰 Famille VALEUR & REVENTE

| id | Nom | Effet / niveau | max | base | growth | total→max |
|---|---|---|---|---|---|---|
| `sell_mult` ✦ | **Prix de Revente** | +4 % `$` à la vente | 20 | 200 | 1,50 | ~1,33 M |
| `yield` ✦ | **Rendement des Scraps** | +3 % chance d'un butin bonus/catch | 15 | 280 | 1,50 | ~245 k |
| `bulk_bonus` ✦ | **Vente en Lot** | +3 % si vente ≥ 50 items d'un coup | 10 | 400 | 1,60 | ~73 k |

### 🧲 Famille AUTOMATISATION & RÉCUP

| id | Nom | Effet / niveau | max | base | growth | total→max |
|---|---|---|---|---|---|---|
| `magnet` ✦ | **Aimant Récupérateur** | auto-récup du tas : + rapide & + gros | 15 | 300 | 1,50 | ~262 k |
| `recycler_pro` ✦ | **Recycleur Pro** | +débit & +rendement recycleur | 12 | 350 | 1,50 | ~90 k |

### 🏦 Famille MÉTA & PASSIF

| id | Nom | Effet / niveau | max | base | growth | total→max |
|---|---|---|---|---|---|---|
| `vault` ✦ | **Coffre / Intérêts** | +0,1 %/min passif sur le `$` détenu (plafonné) | 10 | 1 000 | 1,70 | ~287 k |
| `offline` ✦ | **Gains Hors-Ligne** | +7 % du taux AFK (20 %→76 %) ; +1 h de cap | 8 | 2 000 | 1,80 | ~273 k |

**Coût total pour TOUT maxer ≈ 5,1 M $.** Les amélios sont la **colonne vertébrale du early-mid** ; combinées à l'achat des pinces, aux slots, au **prestige de pince** et à l'**index**, elles portent les 15-25 h. Le revenu finissant par dépasser le coût des amélios (croissance ×1,5/niv vs revenu ×10/étage), l'**endgame bascule sur le prestige de pince + l'index** — c'est intentionnel (les amélios se finissent vers la moitié du parcours, pas à la toute fin).

**Découpage en vagues** (pour phaser l'implémentation) :
- **Core 8 (vague 1)** : `luck`, `grab_speed`, `sell_mult`, `crit_master`, `multi_grab`, `yield`, `magnet`, `offline`.
- **Extended 6 (vague 2)** : `quality`, `modifiers`, `weight_cap`, `bulk_bonus`, `recycler_pro`, `vault`.

**Checkpoints de coût (exemples, formule = source de vérité) :**
- `luck` : L0→1 = 150 · L4→5 ≈ 663 · L9→10 ≈ 4 250 · L14→15 ≈ 27 240 · L19→20 ≈ 174 600.
- `sell_mult` : L0→1 = 200 · L9→10 ≈ 7 700 · L19→20 ≈ 443 000 (effet final +80 % cumulé, additif avec la Fonderie +25 %).
- `crit_master` : L0→1 = 500 · L11→12 ≈ 171 400.

### Modèle de données `Upgrades` (refonte)

Étendre chaque `UpgradeDef` et passer d'une liste plate à des **familles** ordonnées :

```
UpgradeDef = {
  id, name, family,            -- family ∈ "chance"|"cadence"|"valeur"|"auto"|"meta"
  icon,                        -- clé d'icône vectorielle (cf. UI)
  maxLevel, baseCost, growth,  -- courbe
  effectKind,                  -- "luckAdd"|"speedMult"|"sellMult"|"crit"|"magnet"|"offline"|... (consommateur)
  perLevel,                    -- magnitude par niveau (sens selon effectKind)
  params,                      -- bag spécifique (ex. crit = {multBase=10, multPerLevel≈3.6})
  descTemplate,                -- texte avec {effet}/{next} pour la carte
}
Upgrades.FAMILIES = { {id="chance", name="Chance & Rareté", color, icon}, ... }
Upgrades.costFor(def, level)   -- inchangé (round(base*growth^level))
Upgrades.effectFor(def, level) -- = perLevel*level (pour l'affichage ; les consommateurs appliquent leur propre formule)
```

`luck`/`grab_speed` **gardent leurs ids** (les niveaux des saves restent valides) — on ne fait que retuner `maxLevel`/`baseCost`/`growth`/`perLevel` et ajouter `family`/`icon`. Les 12 autres ids sont neufs → `ProfileStore:Reconcile` les remplit à 0 sur les saves existantes (aucune migration manuelle).

`GameConfig.PROFILE_TEMPLATE.upgrades` passe de `{ luck=0, grab_speed=0 }` à la liste complète des 14 ids = 0.

---

## C. Nouvelles mécaniques dopamine — spécifications

Toutes lues côté serveur ; un helper `Upgrades.levelOf(data, id)` lit `data.upgrades[id]`.

### C-1. Crit / Jackpot (`crit_master`)
Dans `CatchService.doGrab`, après calcul de la valeur unité de l'item *vedette* :
- `critChance = 0.004 × level` (max 4,8 %).
- `critMult = params.multBase + params.multPerLevel × level` → ladder ×10 (L1) → ~×50 (L12).
- Si `math.random() < critChance` : **grant cash instantané** `floor(unit × (critMult − 1) × (1 + sellMultTotal))` via `EconomyService.add(scrap, …)`, item normal déposé dans le tas en plus, et `catch` event porte `crit = {mult, bonus}` → le client joue le FX « JACKPOT ×N ! +$X » (réutiliser le pipeline jackpot existant de `CatchFXController`).
- *Raison du cash instantané* (vs copies dans le tas) : ne casse pas le stacking `(defId,rarity,modifier)` et ne noie pas le tas ; EV moyen modéré (~+15 % à max) mais pics spectaculaires = dopamine.

### C-2. Rendement (`yield`)
Dans `doGrab`, après un catch réussi : `if math.random() < 0.03 × level then addItem(copie de l'item vedette) end` (avant l'envoi du `catch`). Augmente débit/valeur de façon lisible.

### C-3. Aimant Récupérateur (`magnet`) — *« vitesse de récupération de scrap »*
Boucle serveur périodique par joueur (dans le tick de `CatchService` ou un nouveau `AutomationService`) :
- `interval = max(3, 12 − 0.6 × level)` s ; `fraction = min(1, 0.2 + 0.06 × level)`.
- À chaque pulse : auto-vend `fraction` du tas en respectant le **keep-filter** (`InventoryService.sellFiltered(player, data.sellFilter)` sur une portion). Réalise passivement tas→`$`. FX léger côté client (compteur qui monte).
- À `level = 0` : inactif (le joueur scoope à la main).

### C-4. Recycleur Pro (`recycler_pro`)
`MachineService` lit `recycler_pro` : `ratePerSec ×(1 + 0.15×level)`, `yieldMult ×(1 + 0.1×level)`. (Le recycleur sort désormais du `$`, cf. E.)

### C-5. Coffre / Intérêts (`vault`)
Boucle serveur 60 s : `grant = floor(min(balance, cap) × rate)` avec `rate = 0.001 × level` (par minute), `cap = 50 000 × level`. Notif discrète « Intérêts : +$X ». Le cap empêche l'explosion exponentielle.

### C-6. Gains Hors-Ligne (`offline`)
- Maintenir `data.stats.avgIncomePerSec` par EMA dans `InventoryService` (à chaque vente/auto-vente/crit : `avg = 0.98·avg + 0.02·tauxRécent`).
- À la connexion (`DataService.onReady`) : `dt = now − data.meta.lastSeenAt` ; `pct = 0.20 + 0.07×level` ; `cap = (4 + level)×3600` s ; `grant = floor(avgIncomePerSec × min(dt, cap) × pct)`. Popup « Pendant ton absence : +$X ». `level = 0` ⇒ pas de gains hors-ligne. `lastSeenAt` est déjà écrit à la sauvegarde.

---

## D. Rééquilibrage des sinks existants (réponse point par point)

| Sink | Fichier | Aujourd'hui | **Proposé** |
|---|---|---|---|
| **Slots de parcelle** | `PlotLayout.slots[].unlockCost` | 300/900/2500/6000/15000/40000 | **200 / 600 / 1 800 / 5 000 / 14 000 / 40 000** (≈×3 lissé ; tiers inchangés) |
| **Prix des pinces (roulette)** | `ShopService.priceOf` | `100·tier²·(1+0,3(rank−1))` → top ~53 k | **`round(80·tier^2.4·(1+0.28(rank−1)))`** → t1 ~80-282 $, t6 ~5,9-21 k, **top (t12 r10) ~110 k** |
| **Chance roulette** | `ShopService.SHOP_LUCK` | base 400, ×1,7, **max 8** | base 400, ×1,65, **max 12** (vraie traîne) |
| **Slots roulette** (1→6) | `ShopService.SLOTS` | base 1500, ×2,1, max 5 | **inchangé** (limite physique 6 plateformes) |
| **Upgrade par pince / prestige** | `ClawUpgrade` | `50·(1+0,9(t−1))·1,18^n` ; `5000·…·2,2^p` | **inchangé** (axe séparé déjà cohérent) |
| **Stats des pinces** | `ClawDesign.genStats` | générées | **inchangé** ; le levier global passe par Amélios |
| **Prix des scraps (revente)** | `Pricing.valueOf` | `base × rareté × mod` | **source inchangée** ; boostée via `sell_mult`/`yield`/`crit` |
| **Recycleur** | `Machines.recycler` | 150 $, sort `parts` | 150 $, **sort `scrap`** (cf. E), boosté par `recycler_pro` |

Tous ces réglages sont **config-only** sauf `priceOf` (1 ligne dans `ShopService`) et le recycleur (output dans `MachineService`).

---

## E. Sort des Parts `⚙` (monnaie unique)

- **Recycleur → produit du `$`** au lieu des Parts (`Machines.recycler.output = "scrap"`, `MachineService` adapté). Il devient la 1ʳᵉ brique d'automatisation passive (auto-vente lente du butin gardé), cohérente avec la famille 🧲.
- **Parts retirées de l'UI active** : masquer `PartsDisplay` du HUD (`UIController.updateCurrency`). Le champ `currency.parts` reste en save (compat) mais n'est plus gagné ni dépensé. Le palier codex « +100 parts » devient « +X $ ».
- **Crafts inchangés** : ils coûtent du **butin par rareté** (jamais des Parts) → aucune dépendance cassée.

---

## F. Refonte UI de l'onglet Amélios

`UIController.populate("Ameliorations")` (lignes ~141-162) passe d'une liste plate à un rendu **groupé par famille** (idéalement un contrôleur dédié type `IndexController`, pour alléger `UIController`) :

- En-têtes de famille (icône + couleur + libellé), cartes repliables.
- Chaque amélio = carte : nom + icône, **valeur d'effet courante** + **delta niveau suivant** (▲ vert), barre de niveau `n/max`, bouton **AMÉLIORER `$coût`** (grisé via `P.PanelInner` si non payable, pastille **MAX** dorée au plafond).
- **Juice** (réutiliser les patterns existants de `ClawMenuController`/billboard roulette) : count-up des nombres, `floatPlus` « +X » à l'achat, flash (UIScale pop + pulse de stroke), son `ding`.
- **Crafts** : conservés dans une sous-section « Machines spéciales » en bas. Le pointeur « améliore tes pinces sur la parcelle » reste.
- Mockup :

```
┌── AMÉLIOS · CENTRE DE COMMANDE ──────────── 💲 12,480 ─┐
│ 🍀 CHANCE & RARETÉ                                     │
│  ┌─────────────────────────────────────────────────┐  │
│  │ 🍀 Chance        Niv 7   luck +0.56  ▲+0.08       │  │
│  │ ▓▓▓▓▓▓▓░░░░░░░░░░░░  7/20      [ AMÉLIORER  840$ ] │  │
│  ├─────────────────────────────────────────────────┤  │
│  │ ✦ Coup de Maître Niv 3   crit 1.2% ×12  ▲+0.4%    │  │
│  │ ▓▓▓░░░░░░░░░         3/12       [ AMÉLIORER 2,4k$ ]│  │
│  └─────────────────────────────────────────────────┘  │
│ ⚡ CADENCE  💰 VALEUR  🧲 AUTO  🏦 MÉTA  (repliables)  │
│ ── Machines spéciales (crafts) ──────────────────────  │
└───────────────────────────────────────────────────────┘
```

`UpgradeService.buy` reste valable (générique, lit `Upgrades.costFor`) ; les nouveaux ids passent par le même net `buyUpgrade`. Les consommateurs (`CatchService`, `InventoryService`, `MachineService`, automation/offline/vault) lisent simplement les niveaux et appliquent leur formule.

---

## G. Découpage en phases (implémentation)

1. **Modèle de données Amélios** — refonte de `Upgrades` (familles, courbes, `effectKind`, `params`), `GameConfig.PROFILE_TEMPLATE.upgrades` complet, branchement des stats « simples » (`luck`, `grab_speed`, `quality`, `modifiers`, `weight_cap`, `multi_grab`, `sell_mult`) dans `CatchService.effectiveStats` / `InventoryService.sellStack`. *(Core simple, débloque l'essentiel.)*
2. **Mécaniques actives** — `crit_master` + `yield` dans `CatchService.doGrab` (+ payload `catch` & FX client).
3. **Automatisation & passif** — `AutomationService` (ou extension `CatchService`) pour `magnet` + `vault` ; `offline` dans `DataService.onReady` (+ EMA `avgIncomePerSec` dans `InventoryService`) ; `recycler_pro` dans `MachineService`.
4. **Consolidation Parts → `$`** — recycleur output `scrap`, masquage HUD ⚙, palier codex en `$`.
5. **Refonte UI** — rendu groupé par famille + juice (nouveau contrôleur).
6. **Passe de rééquilibrage** — `PlotLayout` (slots), `ShopService` (`priceOf`, `SHOP_LUCK`), puis **vérification du rythme** (simulation, cf. ci-dessous).

---

## H. Vérification (end-to-end)

- **Boot propre** : démarrer Play, console sans erreur, 13+ services / contrôleurs OK.
- **Achats Amélios** : via le client réel `Net.request("buyUpgrade",{id=…})` (l'`execute_luau` serveur a un `Registry` isolé — cf. memory) ; vérifier débit `$`, niveau +1, et l'effet appliqué (lire `effectiveStats` d'une pince placée avant/après via un dump serveur).
- **Crit** : forcer `crit_master` haut + admin scrap, observer le grant instantané + le `catch.crit` (log + FX).
- **Automatisation / hors-ligne / coffre** : `magnet` > 0 → le tas se vide et le `$` monte sans action ; reculer `data.meta.lastSeenAt` pour simuler une absence → vérifier le lump de reconnexion ; `vault` → +intérêts toutes les 60 s.
- **Rééquilibrage / rythme** : script de simulation (`execute_luau`) qui modélise le revenu à plusieurs étapes (pince(s) tier T, amélios niveaux N) et confronte les **temps-jusqu'aux-jalons** au tableau §A. Ajuster bases/growth si un palier sort de la fourchette « quelques min → quelques dizaines de min ».
- **Outils de test** : `AdminService` (grant scrap, placer des pinces, `fillJunk`) — admin `lylou38000`.
- **Compat saves** : charger une save existante (mock ProfileStore Studio) → `Reconcile` remplit les 12 nouveaux ids à 0, `luck`/`grab_speed` conservent leur niveau.

---

## I. Récapitulatif des fichiers touchés

**Configs** (`ReplicatedStorage.Shared.Config`) : `Upgrades` (refonte), `GameConfig` (PROFILE_TEMPLATE.upgrades + recycleur si besoin), `PlotLayout` (unlockCost), `Machines` (recycler.output), `Types` (UpgradeDef étendu, champs stats). `ShopService` n'est pas un config mais porte `priceOf`/`SHOP_LUCK`.

**Services** (`ServerScriptService.Server.Services`) : `CatchService` (effectiveStats + crit/yield), `InventoryService` (sellMult upgrade + EMA income + bulk_bonus), `MachineService` (recycler $ + recycler_pro), `ShopService` (priceOf, SHOP_LUCK cap), `DataService` (offline grant), **`AutomationService`** (nouveau : magnet + vault), `CollectionService` (palier codex en $), `UpgradeService` (inchangé, générique).

**Client** (`StarterPlayer.StarterPlayerScripts`) : `UIController` (rendu Amélios groupé + HUD parts masqué) ou nouveau `Controllers.AmeliosController` ; `CatchFXController` (FX crit/auto si besoin).

---

## J. Boutons de réglage (tuning knobs) laissés explicites

Pour itérer le rythme sans toucher la logique : toutes les `base`/`growth`/`maxLevel`/`perLevel` des 14 amélios (dans `Upgrades`), les 6 `unlockCost` (PlotLayout), le coefficient/exposant de `priceOf`, et les params crit (`multBase`/`multPerLevel`), magnet (`interval`/`fraction`), vault (`rate`/`cap`), offline (`pct`/`cap`). Centralisés en tête de leurs modules respectifs.
