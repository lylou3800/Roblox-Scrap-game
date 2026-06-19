# Refonte GUI + environnement — style cartoon (UFO_Catchers)

Date : 2026-06-13
Build cible : `build.rbxlx` (Studio, Rojo connecté, pas de project.json local)

## Contexte

Le build local ne contient **aucun GUI** (`StarterGui` vide, zéro `ScreenGui`). Les
captures fournies par l'utilisateur sont la **référence de style cible** (jeu type
farming/garden bright cartoon, thème UFO/alien). On reconstruit donc une suite de GUI
**from scratch** dans ce build, restylée et centrée, plus un restyle de l'environnement.

Décisions utilisateur :
- GUI introuvables dans le build → **recréer dans ce build**.
- Captures = **référence de style cible** (couleurs/textures).
- Périmètre = **les 4 volets** : HUD complet + popups + module de thème + restyle env.
- Kit de style validé (voir ci-dessous).

## Système de style (validé)

Palette :
- Herbe lime `#54C91A`, terre terracotta `#C96A26`, ciel bleu vif.
- Barre de titre bleue `#2BA4E0`, fond de panneau `#241A12`, contour `#0E0905`.
- Valider/vert `#5FD41A`, fermer/rouge `#E8433C`, or `#F2C019`, violet `#8B4FE0`,
  cyan `#29C7E0`, pink `#EF3F6F`.

Typo (polices Roblox natives) :
- Titres : `Enum.Font.LuckiestGuy` (fallback `Cartoon`).
- Corps/boutons : `Enum.Font.FredokaOne`.
- Texte blanc + `UIStroke` foncé `#1A120A`.

Anatomie panneau :
- Fond `#241A12` + `UIStroke` 3px `#0E0905` + `UICorner` ~16px + ombre (cadre décalé).
- Barre de titre bleue, titre blanc, bouton fermer rouge carré.
- En-têtes de section = pastille dégradé (vert→or, ou violet).
- Boutons « chunky 3D » : remplissage vif + contour foncé + ombre décalée bas.

Règle de centrage (besoin principal) :
- **Popups/menus** : `AnchorPoint = (0.5,0.5)`, `Position = {0.5,0},{0.5,0}` → centrés
  quel que soit l'écran.
- **HUD** : reste ancré aux bords (AnchorPoint + Position aux coins) pour éviter le
  chevauchement au centre.

## Architecture

### 1. `ReplicatedStorage/UI/Theme` (ModuleScript) — source unique du style
Exporte :
- `Theme.Palette`, `Theme.Font`, `Theme.Dims` (constantes).
- Fabriques : `Theme.Corner(parent, r)`, `Theme.Stroke(parent, color, thick)`,
  `Theme.Shadow(parent)`, `Theme.Panel(opts)`, `Theme.Button(opts)`, `Theme.Pill(opts)`,
  `Theme.SectionHeader(opts)`, `Theme.IconLabel(opts)`.
- Chaque fabrique renvoie l'instance racine pour composition.

### 2. `StarterGui/MainHUD` (ScreenGui, IgnoreGuiInset = true)
Éléments ancrés aux bords :
- `CurrencyDisplay` (bas-gauche) — pastille verte `$1.75M`.
- `Sidebar` (gauche, `UIListLayout` vertical) — 4 boutons carrés : Boutique (pink),
  Index (violet), Récompenses (rouge), Pass (or). Chacun icône + label.
- `EventBanner` (haut-centre) — pastille foncée « Prochain événement : 00:00 ».
- `Leaderboard` (haut-droite) — panneau participants (placeholder data).
- `Hotbar` (bas-centre) — 5–6 slots carrés numérotés.
- `TimerTray` (bas-droite) — pastilles timers (droplet, ufo, rainbow…).
- `MultiplierPill` (droite) — « X2 ARGENT » dégradé arc-en-ciel.

### 3. `StarterGui/Menus` (ScreenGui, IgnoreGuiInset = true)
Popups **centrés**, `Visible = false` par défaut, chacun bâti via `Theme.Panel` :
- `Boutique`, `Index`, `RecompensesQuotidiennes`, `UpdateLog`, `PasseCarnaval`.
- Contenu = données placeholder représentatives (grille de récompenses, liste
  d'updates, items boutique…).

### 4. `StarterPlayerScripts/UIController` (LocalScript)
- Mappe chaque bouton de `Sidebar` → toggle du popup correspondant dans `Menus`.
- Bouton fermer rouge de chaque popup → ferme.
- Ouverture/fermeture = tween léger (scale/transparency).
- Un seul popup ouvert à la fois ; clic hors panneau ferme (overlay sombre optionnel).

### 5. Restyle environnement
- `Workspace.Environment` + `Workspace.MapBlockout` : recolorer sols (herbe `#54C91A`,
  terre `#C96A26`), `Material = Plastic` (studs cartoon) sur les surfaces concernées.
- `Lighting` : ambiance claire/saturée (Brightness, OutdoorAmbient, ciel bleu vif),
  éventuellement `Atmosphere`/`ColorCorrection` léger pour le rendu « candy ».
- Ne pas casser le blockout existant (positions/échelle conservées, couleurs/matériaux
  seulement).

## Méthode de construction
- Instances statiques générées via `execute_luau` (visibles + éditables en mode édition,
  centrées par construction). Le `Theme` reste un ModuleScript pour la réutilisation
  runtime ; le builder réutilise les mêmes constantes/fabriques (require du module).
- Vérification : entrer en mode Play + `screen_capture` pour confirmer rendu + centrage,
  puis itérer.

## Hors-périmètre (YAGNI)
- Aucun backend / sauvegarde / économie réelle (données placeholder).
- Pas de logique de gameplay (farming, achats réels, events serveur).
- Pas de localisation multi-langues (FR uniquement, comme les captures).

## Critères de réussite
- Les 5 popups s'ouvrent **centrés** et se ferment via la barre latérale / bouton fermer.
- HUD complet présent, ancré aux bords, lisible, au style validé.
- `Theme` réutilisable : changer une couleur de la palette se répercute partout.
- Environnement recoloré au look cartoon sans casser le blockout.
- Rendu Play conforme au kit de style validé (capture à l'appui).
