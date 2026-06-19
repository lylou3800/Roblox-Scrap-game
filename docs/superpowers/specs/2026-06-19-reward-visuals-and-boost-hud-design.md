# Visuels des récompenses + HUD des boosts actifs — Design (2026-06-19)

## 1. Contexte & objectif

Amélioration visuelle premium de deux surfaces UI du tycoon scrapyard / UFO-catchers, plus le retrait
d'une phrase de HUD obsolète. Trois livrables :

1. **Menu CADEAUX** (`PlaytimeRewardsController`) — remplacer les glyphes texte « cheap » des 12 cartes de
   récompense par un set d'**icônes illustrées glossy-3D** premium, lisibles même en petit.
2. **HUD des boosts actifs** (`BoostHUDController`) — reconstruire la zone en **bas à droite** sous forme
   d'une pile verticale de **badges icône-glossy** avec hiérarchie de taille/glow et **compteur dessous**.
3. **Retrait de phrase** — supprimer proprement `"Open your Inventory and Sell junk for Scrap."` du HUD.

Objectif transverse : un rendu plus beau, plus propre, plus cohérent, plus « dopamine », parfaitement
aligné avec la direction artistique existante (cartoon premium, bright, thick outlines — cf. cible
« Grow a Garden »). Cohérence stricte avec `ReplicatedStorage.UI.Theme`.

## 2. Décisions clés (validées avec l'utilisateur)

| # | Décision | Choix retenu |
|---|----------|--------------|
| 1 | **Pipeline visuel** | **Hybride : art IA + construit.** Higgsfield génère les icônes illustrées des cartes ; ViewportFrame 3D pour les vrais meshes œuf/pet ; icônes construites nettes pour le petit HUD de boosts. Marketplace seulement en secours par icône. |
| 2 | **Périmètre** | **Menu CADEAUX + HUD de boosts** (+ retrait de phrase). Pas l'Index rewards ni les autres popups pour l'instant. |
| 3 | **Style d'icône** | **Glossy stylisé 3D** : formes 3D chunky, rim-light doux, reflets glossy, contour foncé épais, couleurs vives saturées. Lisible en petit. |
| 4 | **Disposition HUD boosts** | **Badges empilés + paliers de taille** : colonne verticale de badges carrés glossy en bas à droite, icône + barre de progression à la base + timer dessous ; hiérarchie par taille/glow (boost « majeur » plus gros et plus lumineux). |

Pourquoi l'hybride plutôt que « tout IA » : les générateurs IA sortent des images carrées **avec fond**,
pas des icônes UI détourées ; chaque image demande détourage + curation + upload (avec délai de modération
Roblox). L'art IA brille pour l'illustration des cartes, mais une icône **construite** reste plus nette aux
très petites tailles du HUD. D'où : IA pour les cartes, construit pour le HUD, ViewportFrame pour œuf/pet.

## 3. État actuel (références code live)

### 3.1 Menu CADEAUX — `PlaytimeRewardsController`
Chemin : `StarterPlayer.StarterPlayerScripts.Client.Controllers.PlaytimeRewardsController`
(copie texte : `docs/recovered-2026-06-19/PlaytimeRewardsController.luau`).

- `buildIcon(holder, t, color)` construit l'icône : pour `loot` → `ScrapIcons.build(h, "ufo_core", color)` ;
  sinon un **TextLabel glyphe** crude : `$` / `x2` / `+%` / `>>` / `O` / `<3` selon `t.icon`. **C'est ça à
  remplacer.**
- `buildCard(t)` : structure solide à **conserver** — `top` (montant vert ou nom), `plate` 62×62 (icône),
  badge quantité `xN` (loot), `nameLbl` (sous-texte muted), `bottom` (timer `--:--` / bouton « Reclamer » /
  stamp « RECLAME »), `stroke` teinté rareté, 4 états via `setVisual(s)` : `locked` / `ready` / `claimed`
  (+ implicitement la « prochaine »).
- Config : `ReplicatedStorage.Shared.Config.PlaytimeRewards` — 12 paliers, champs `type` (cash | boost |
  boost_double | prize_rain | loot | egg | pet_jackpot), `visual` (normal | rare | premium), `icon`
  (cash | boost_cash | boost_luck | boost_double | loot | egg | pet).

### 3.2 HUD boosts — `BoostHUDController`
Chemin : `StarterPlayer.StarterPlayerScripts.Client.Controllers.BoostHUDController`
(copie texte : `docs/recovered-2026-06-19/BoostHUDController.luau`).

- Conteneur actuel : `ScreenGui "BoostHUD"` (DisplayOrder 20) → `Frame` **ancré haut-centre**
  (`AnchorPoint (0.5,0)`, `Position (0.5,0,0,8)`) + `UIListLayout` **horizontal**.
- `KIND` : `cash` → « x2 Cash » `P.Confirm` · `luck` → « +Chance » `P.Purple` · `yield` → « +Rendement »
  `P.Gold` · `speed` → « +Vitesse » `P.Cyan`.
- `makePill(kind)` : `Theme.Pill` **texte seul** « x2 Cash  00:00 » (150×36). Pas d'icône, pas de hiérarchie.
- Données : event `boostsChanged` → liste de `{ kind, remaining }`. Heartbeat met à jour le timer +
  pulse < 10 s. **C'est ça à reconstruire** (relocalisation bas-droite + badges icône).

### 3.3 Phrase — `OnboardingController`
Chemin : `StarterPlayer.StarterPlayerScripts...OnboardingController` (utilise l'**ancien** `UIUtil.THEME`,
pas `Theme`). Système de hint contextuel unique en bas d'écran (`nextHint(state)` renvoie la prochaine
action). La phrase est **une branche** `elseif` :

```lua
elseif not flags["first_item_sold"] and hasInventory then
    return "Open your Inventory and Sell junk for Scrap."
```

Le HUD `Boost +0%` statique de `MainHUD` (boost **passif** de compte) est **distinct** des boosts temporés et
reste inchangé.

## 4. Livrable 1 — Cartes CADEAUX (icônes premium)

### 4.1 Set d'icônes à générer (Higgsfield, glossy 3D)
Direction de prompt commune : *« glossy stylized 3D game reward icon, chunky cartoon, soft rim light, glossy
highlights, thick dark outline, vivid saturated colors, centered single object, flat neutral background,
mobile gacha UI »* (fond neutre = détourage facile). Set minimal (réutilisé sur plusieurs paliers) :

| clé | sujet | paliers utilisateurs |
|-----|-------|----------------------|
| `cash` | liasse / sac de billets verts | T1, T3, T7, T10 |
| `x2_cash` | jeton/badge doré « ×2 » | T2 (boost cash) |
| `cache_rare` | caisse de ferraille robuste teintée rareté | T4 (loot) |
| `chance` | trèfle / fer à cheval porte-bonheur | T5 (boost luck) |
| `prize_rain` | éclat/burst de pièces qui pleuvent | T6 |
| `double_boost` | flèche montante + éclair combinés | T9 (yield+speed) |
| `chest_legendary` | coffre au trésor premium | T11 (loot) |

- **Œuf (T8)** et **Pet (T12)** : **PAS d'IA** → `ViewportFrame` du vrai mesh (`Assets.EggMeshes`,
  `PetMeshes` comme `PetMenuController`). Plus authentique, déjà en moteur, pas de modération.
- Total IA visé : ~7 icônes nettes. Marketplace en secours par icône uniquement si une génération échoue.

### 4.2 Refonte de la carte (squelette conservé, plate améliorée)
- **Icône** : remplacer le glyphe texte par
  - un `ImageLabel` de l'**asset uploadé** (clé d'icône → asset-id via `RewardIcons`), OU
  - un `ViewportFrame` (œuf/pet), OU
  - **fallback construit** (glyphe stylisé / `ScrapIcons`) rendu **immédiatement** tant que l'asset n'est pas
    modéré (voir §7).
- **Backplate** : panneau radial de rayons **construit** (`UIGradient` radial) teinté par le tier visuel ;
  ombre douce ; léger inner-glow.
- **Tiers de rareté** (identité intrinsèque, conservée du build actuel) :
  - `normal` → stroke cyan `darken(Cyan)`, fond plat foncé.
  - `rare` → stroke `Purple` + dégradé interne violet.
  - `premium` → stroke `Gold` 3px + dégradé or→ambre + **sheen diagonal animé** + **glow or doux permanent**.
- **États** (inchangés) : `locked` (timer), `ready` (glow vert + bouton Réclamer), `claimed` (désaturé +
  stamp ✓), « prochaine » mise en avant. Le glow vert « ready » se superpose à la rareté.

## 5. Livrable 2 — HUD des boosts actifs (bas-droite)

### 5.1 Conteneur & placement
- `ScreenGui "BoostHUD"` conservé ; `Frame` racine **ré-ancré bas-droite** : `AnchorPoint (1,1)`,
  `Position (1, -16, 1, -16)`, **inset au-dessus de la zone bouton-saut mobile** (sur mobile, Roblox place
  le saut en bas-droite → marge basse plus haute si `UserInputService.TouchEnabled`, p. ex.
  `Position (1,-16,1,-150)`).
- `UIListLayout` **vertical**, `VerticalAlignment = Bottom`, `HorizontalAlignment = Right`, padding ~10,
  **croissance vers le haut** (`SortOrder` stable pour éviter le ré-ordonnancement qui fait sauter les badges).

### 5.2 Badge (par boost actif)
Structure verticale (l'icône au-dessus, le **timer dessous**, conforme à la demande) :

```
   +------------+
   |   ICON     |   <- ImageLabel/glyphe glossy + cadre teinté kind
   |  ########  |   <- barre de progression fine (remaining/duration) à la base
   +------------+
      04:12         <- TextLabel timer, sous le badge
```

- Cadre carré arrondi (`Corner ~14`), `UIStroke` teinté par `kind`, fond `PanelInner` + dégradé teinté,
  ombre douce, petit glow (intensifié pour les majeurs).
- **Barre de progression** : nécessite `duration` en plus de `remaining` dans l'event `boostsChanged`
  (sinon, on mémorise le `remaining` initial vu côté client comme référence — voir §6).
- Timer `mm:ss` (`Theme.Font.Title`, TextStroke) directement **sous** le badge.

### 5.3 Couleurs & hiérarchie
- Couleurs par `kind` (réutilise `KIND`) : `cash` accent vert/or · `luck` violet · `yield` or-ambre ·
  `speed` cyan.
- **Paliers de taille** : `cash` (« ×2 Cash ») = **majeur** → badge plus grand (~76px) + cadre or + glow
  plus fort + label court « ×2 ». `luck`/`yield`/`speed` = **standard** (~60px). Mapping majeur/standard
  exposé en table (tunable).

### 5.4 Animations
- **Apparition** : pop scale 0→1 Back/Out.
- **Disparition** : fade + scale→0 quand `remaining <= 0` ou absent de la liste.
- **Urgence < 10 s** : pulse (lerp couleur vers blanc en `sin`), déjà présent — conservé/renforcé.
- **Idle majeur** : léger sheen/glow respirant (cohérent avec le premium des cartes).

## 6. Données / remotes

- Aucune nouvelle remote. On réutilise l'event `boostsChanged` (liste `{ kind, remaining }`).
- **Barre de progression** : pour un remplissage exact, ajouter `duration` (ou `expiresAt`) à la charge utile
  de `boostsChanged` côté `BoostService.getActive`. Si on ne veut **aucune** modif serveur, fallback client :
  retenir `maxRemaining[kind] = max(vu)` comme dénominateur (approché, se recale au grant). **Décision :
  ajouter `duration` côté serveur** (1 champ, lecture seule, déjà dispo dans `active[player][kind]`) pour une
  barre exacte — modif minimale, validée par read-back.

## 7. Pipeline Higgsfield → Roblox (détaillé)

1. **Setup (utilisateur, interactif, une fois)** : `npm install -g @higgsfield/cli` → `! higgsfield auth login`
   → `npx skills add higgsfield-ai/skills`. Ensuite je pilote.
2. **Génération** : pour chaque clé d'icône, générer plusieurs variantes (prompt commun §4.1 + sujet), viser
   fond neutre/plat et objet centré.
3. **Curation stricte** : ne garder que les rendus on-style (glossy 3D, lisibles en petit, silhouette claire) ;
   rejeter tout ce qui est réaliste/cheap/bruité/hors-thème.
4. **Détourage** : retirer le fond → PNG transparent (silhouette propre).
5. **Upload Roblox** : via le MCP Studio (`upload_image`) → asset-id par clé d'icône.
6. **Modération** : un asset uploadé doit être modéré avant de s'afficher. **Mitigation obligatoire** : chaque
   carte/badge se construit et **rend correctement avec une icône construite immédiatement** ; l'image IA
   **se substitue** par asset-id quand elle est approuvée (lecture du map `RewardIcons`).
7. **Fallback par icône** : échec curation/modération → garder le construit / `ViewportFrame`, ou un asset
   marketplace curé. Aucune carte/badge jamais vide.

## 8. Architecture / composants

| Type | Chemin | Action |
|------|--------|--------|
| Module (nouveau) | `ReplicatedStorage.Shared.RewardIcons` | map `clé → { assetId?, build(holder,color) }` : asset-id IA si présent + **builder de secours**. Source unique d'icônes pour cartes ET HUD. |
| Controller | `...Client.Controllers.PlaytimeRewardsController` | `buildIcon` → consomme `RewardIcons` (image/viewport/fallback) + backplate rayons + sheen premium. |
| Controller | `...Client.Controllers.BoostHUDController` | **reconstruction** : conteneur bas-droite vertical, badges icône + barre + timer, hiérarchie taille/glow, anims. |
| Controller | `...OnboardingController` | retirer la branche `first_item_sold` (cf. §9). |
| Service | `ServerScriptService.Server.Services.BoostService` | `getActive` : ajouter `duration` (ou `expiresAt`) à chaque entrée (barre de progression exacte). |
| Assets | nouveaux image-assets Roblox | uploadés via MCP ; asset-ids renseignés dans `RewardIcons`. |

Réutilise : `ReplicatedStorage.UI.Theme` (Palette/Font/Panel/Button/Pill/Corner/Stroke/Gradient/darken/
TextStroke), `ScrapIcons`, helpers `ViewportFrame` (cf. `PetMenuController`/Index), `Net`.

**Aucun changement de logique gameplay** (économie, catch, sell, grant). Modif serveur limitée au champ
`duration` exposé par `BoostService.getActive`.

## 9. Livrable 3 — Retrait de phrase

Dans `OnboardingController.nextHint`, supprimer la branche :

```lua
elseif not flags["first_item_sold"] and hasInventory then
    return "Open your Inventory and Sell junk for Scrap."
```

Le système de hint **retombe automatiquement** sur la prochaine branche applicable → aucun trou visuel,
aucun ré-alignement nécessaire. Le flag `first_item_sold` reste utilisé ailleurs (funnel) ; seul son hint
disparaît.

## 10. Hors-scope / risques

- **Hors-scope** : Index rewards rail, popups daily (`RecompensesQuotidiennes`), nouvelles mécaniques de
  boost, refonte de la config `PlaytimeRewards`, gamepass.
- **Risques** :
  - (a) **Modération Roblox** des images uploadées (délai) → mitigé par « construit d'abord, IA en swap ».
  - (b) **Style IA inconstant** → budget de curation (plusieurs gens / icône), rejet strict ; fallback construit.
  - (c) **`multi_edit` MCP no-op silencieux** + **Play compile un snapshot périmé** → vérifier chaque édition
    par read-back séparé, confirmer `Mode=Play` (cf. [[roblox-studio-mcp-gotchas]]).
  - (d) **Auth Higgsfield interactive** → l'utilisateur doit lancer `! higgsfield auth login` (je ne peux pas).
  - (e) **Zone mobile bas-droite** (bouton saut) → inset conditionnel `TouchEnabled`.

## 11. Critères d'acceptation

1. Les 12 cartes CADEAUX affichent une **icône premium glossy-3D** (image IA détourée, ou ViewportFrame
   œuf/pet, ou fallback construit) à la place des glyphes texte ; lisibles en petit ; cohérentes `Theme`.
2. Aucune carte/badge n'est jamais vide, même avant approbation de modération.
3. Le HUD de boosts est **en bas à droite**, pile verticale de badges **icône + barre + timer dessous**,
   bien aligné/espacé, avec hiérarchie (×2 Cash plus présent), inset au-dessus du saut mobile.
4. Les badges apparaissent/disparaissent proprement, pulsent < 10 s, et le timer décompte juste.
5. La phrase « Open your Inventory and Sell junk for Scrap. » n'apparaît plus ; le HUD de hint reste cohérent.
6. Aucune régression de gameplay ; build se compile, boot propre.
7. Rendu global perceptiblement plus premium / propre / « dopamine », cohérent avec les autres menus.
