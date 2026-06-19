# EggShop — Pass d'art « premium » (polish visuel)

- **Date** : 2026-06-19
- **Cible** : `game.Workspace.Environment.EggShop` (modèle statique baké dans `build.rbxlx`)
- **Type** : pass de polish visuel (PAS un redesign) — hybride natif + 3 meshes Blender hero
- **Réf. visuelle** : capture style Pet-Sim-99 (échoppe orange, bois, comptoir doré, frise rouge/blanche, panneaux bois sombres, œufs sur piédestaux)

## 1. Contexte & contraintes

### Stockage
Aucun script ne construit la géométrie (grep `Canopy`/`EggShop` → seuls les scripts de **logique** existent : `EggShopController`, `EggShopService`). La géométrie est **statique et bakée** dans `build.rbxlx` (source de vérité). Le polish s'applique donc par **édition directe des instances en mode Édit**, via un script Luau **idempotent** (ré-exécutable sans dupliquer), puis sauvegarde par l'utilisateur (Ctrl+S). Les changements vivent dans la DataModel Studio tant que Ctrl+S n'est pas fait.

### Géométrie actuelle (relevé exact)
Le shop fait face à **+X** (client en X > -369), large selon **Z** (±15), haut selon **Y**. Pivot monde (-379, 0.5, 0).

| Part | Size (X,Y,Z) | Pos (X,Y,Z) | Couleur / Matériau |
|---|---|---|---|
| Deck | 24, 0.8, 32 | -379, 0.5, 0 | orange / Plastic |
| BackWall | 1.6, 17, 32 | -388, 8.7, 0 | orange / Plastic |
| PostFront ×2 | 2.4, 20, 2.4 | -369, 10.1, ±15 | brun / Plastic |
| PostBack ×2 | 2.2, 18, 2.2 | -387, 9.1, ±15 | brun / Plastic |
| BeamFront | 2.8, 2.8, 34 | -369, 20.6, 0 | brun |
| BeamBack | 2.8, 2.8, 34 | -387, 18.6, 0 | brun |
| Canopy | 22, 1, 35 | -378, 22.1, 0 | orange |
| Valance ×10 | 1.2, 2.2, 3.4 | -367.8, 19.3, z∈[-15.3..15.3] | rouge/cream alterné |
| CounterBase | 5, 4.6, 28 | -371, 2.4, 0 | brun foncé (haut Y≈4.7) |
| CounterTop | 6.4, 0.9, 29 | -371, 4.9, 0 | doré (**haut Y≈5.35**) |
| EggsSign (Œufs) | 0.82, 2.46, 9 | -368, 16.3, +8 | brun très foncé |
| Countdown | 0.82, 4.43, 15 | -368, 14.5, -8 | brun très foncé |
| Pedestal1..6 | invisible | -371, 5.5, z∈{-12.5,-7.5,-2.5,2.5,7.5,12.5} | transparent |
| Egg (×6) | invisible | -371, **5.9** (ped6 = **6.7** ← bug) | transparent |
| NPC.shopkeeper | R6 | torse ≈ -383.4, 4.4, 0.9 | mi-enterré derrière comptoir |

### Contraintes fonctionnelles à NE PAS casser
1. **Noms exacts** liés par `EggShopController` : `Pedestal1..6` → enfant `Egg` → enfants `Visual` (Model), `Info` (BillboardGui : labels `EggName`/`EggPrice`/`EggOdds`), `BuyPrompt` (ProximityPrompt). `Countdown` → `CountdownGui` → `Time`.
2. **Contrat « œuf sur comptoir »** : `setEggTier` pose chaque modèle d'œuf à `Y = 5.4 + hauteur/2` (donc posé sur le plateau à **Y≈5.35**), à `egg.Position.X/Z`. ⇒ **Le haut du CounterTop doit rester à Y≈5.35**, et les positions X/Z des Egg ne doivent pas bouger, sinon les œufs flottent/s'enfoncent ou se décentrent.
3. Les `SurfaceGui`/`TextLabel` gardent leurs noms (le contrôleur écrit dedans à chaque refresh). On ne touche que style/police/padding/position du support.
4. Le `Visual` est cloné/remplacé au runtime → ne rien parenter dedans ; les ajouts décoratifs vont sur `Pedestal*` ou le shop, jamais dans `Egg`/`Visual`.

### Contraintes projet (mémoire)
- **Anti z-fighting** : jamais deux faces coplanaires de même orientation. Toute moulure/latte/cap offset **≥ 0.04 studs** de la surface support. Passe de détection coplanaire à la fin.
- **MCP gotchas** : `multi_edit` peut no-op silencieusement → préférer `execute_luau` idempotent + **relecture de vérification**. La caméra `screen_capture` ne bouge pas en Play → capturer en Édit.
- Édits dans la DataModel ⇒ **pending Ctrl+S** (l'utilisateur sauvegarde).

## 2. Direction artistique

Garder l'**identité exacte** et la **palette** actuelles (orange `#C46C2A`, brun `#965E1C` / `#784524`, doré `#F0C446`, rouge `#E14640` + cream `#F8F4EE`, bois sombre `#462E1E`). Ajouter **relief + matière** par textures et petites moulures natives ; réserver Blender aux courbes qu'un bloc ne sait pas faire. Rendu cartoon propre, lisible à distance, jamais réaliste ni surchargé.

## 3. Périmètre du polish

### S1 — Profondeur des surfaces & matériaux
- **Murs / façade (BackWall + retour)** : conserver l'orange ; ajouter une `Texture` tuilée discrète (motif planches/inset, teintée orange, faible contraste) sur les faces visibles, + quelques **lattes verticales** fines en relief (parts minces, offset ≥0.04) pour casser l'uniformité.
- **Toit / canopée** : matériau planches + **faîtage** (ridge cap) + léger débord avant ; battens de planches espacés.
- **Comptoir** : plateau doré conservé ; ajouter **moulure de rebord** (liseré plus foncé tout autour, offset 0.05, hors zone des œufs), **rainures verticales** sur la base, et **boutons-gemmes rouges** (demi-sphères Neon douce sur petits socles métal) alignés sur la face avant de la base (signature de la réf).
- **Poteaux / poutres** : matériau planches + léger bandeau d'ombre en bas / lumière en haut (faux AO peint via 2 tons).
- Palette inchangée ; uniquement variation de tons pour le relief.

### S2 — Signalétique (priorité explicite)
- **Ordre du compte à rebours corrigé** : `Marchand d'œufs` (titre, haut) → `Réapprovisionnement dans` (sous-titre) → `MM:SS` (timer). (Aujourd'hui rendu inversé.)
- **Disposition réf** : Marchand à **gauche** / Œufs à **droite** (on s'aligne sur la réf).
- **Placement** : deux panneaux remontés sur le bandeau de façade, à **hauteur identique**, **centrés/symétriques** par rapport au volume, **suspendus à BeamFront** avec petits supports (tiges/chaînes courtes), flush juste devant le plan de façade, **sans chevaucher** l'intérieur ni les œufs.
- **Cadres = Blender hero #3** : cartouches bois sculptées (coins arrondis + léger biseau) remplaçant `EggsSignFrame`/`CountdownFrame` plats. Bois sombre, derrière la face sombre du panneau.
- **Emblème œuf = Blender hero #1** : œuf cartoon 3D (léger craquelé + éclat) couronnant le panneau `ŒUFS`, centré sur son bord haut.
- Texte : police titre type LuckiestGuy, blanc + contour sombre, `UIPadding`, tailles cohérentes ; GUI orientée +X, support offset derrière (anti z-fight).

### S3 — Corbeaux & finition structurelle (Blender hero #2)
- **Équerres bois sculptées** aux 2 jonctions PostFront→BeamFront (+ supports de panneaux si pertinent). Petites, low-poly, purement additives. Effet « échoppe construite/artisanale ».

### S4 — Œufs & intégrité du placement (vérif finale explicite)
- **Bug corrigé** : `Pedestal6.Egg` ramené à **Y 5.9** (alignement des 6 ; n'affecte que l'ancre du `Info`/`BuyPrompt`, pas le `Visual` posé sur le comptoir).
- **Présentoirs** : `Holder` décoratif sous chaque œuf (anneau/puck foncé + liseré coloré), top à Y≈5.35–5.4 (sur le comptoir), centré sur X/Z du piédestal, `CanQuery=false`/`CanCollide=false`, **parenté à `Pedestal*`** (jamais à `Egg`/`Visual`), ne bloque pas le `BuyPrompt`.
- **Vérifs** : les 6 œufs centrés (X=-371), espacés de 5 en Z, symétriques ±12.5 ; aucun ne flotte/s'enfonce ; labels prix alignés ; CounterTop toujours haut Y≈5.35.

### S5 — Marchand (NPC)
- **Rehaussé/avancé** sur une petite estrade cachée pour que tête + torse dépassent le comptoir (visible comme dans la réf), R6 + chapeau/tenue conservés. **NamePlate** remontée au-dessus de la tête (StudsOffset), sans chevaucher les œufs.

### S6 — Optimisation & sécurité
- **3 meshes Blender** low-poly (≈ quelques centaines de tris chacun), uploadés une fois (pipeline validé : Blender procédural → addon « Upload to Roblox » Open Cloud → `InsertService:LoadAsset` + repositionnement).
- 1 image de texture réutilisée (tuilage), pas de SurfaceAppearance lourd.
- Décor pur : `Anchored=true`, `CanCollide=false`, `CanQuery=false`.
- Noms fonctionnels et hauteur « œuf sur comptoir » **préservés**.

## 4. Critères d'acceptation
1. Identité reconnaissable, palette conservée, plus « fini/premium » qu'avant (screenshots avant/après).
2. Panneaux : ordre du timer correct, Marchand-gauche/Œufs-droite, à hauteur égale, centrés/symétriques, cadres sculptés, emblème œuf centré sur le panneau Œufs ; texte très lisible de loin.
3. Surfaces : murs/toit/comptoir/poutres ont un relief/matière lisible (plus « plat »), sans bruit ni surcharge.
4. Corbeaux présents aux jonctions avant.
5. Œufs : 6 alignés (même Y), centrés, posés proprement sur des Holders, aucun flottant/enfoncé ; CounterTop top à Y≈5.35 ; bindings intacts (E/achat fonctionnent).
6. NPC visible (tête+torse au-dessus du comptoir), nameplate au-dessus de la tête.
7. **Aucune** paire de faces coplanaires même-orientation introduite (détecteur OK). Tout décor `CanQuery=false`.
8. Logique inchangée : noms `Pedestal1..6/Egg/Visual/Info/BuyPrompt/Countdown/CountdownGui/Time` présents et bindés.

## 5. Hors périmètre (YAGNI)
- Pas d'auvent en tissu sculpté (non retenu) — la frise rouge/blanche reste native, juste polie.
- Pas de refonte de la logique d'achat/éclosion.
- Pas de modification des configs `Eggs`/`Pets`.
- Pas de remplacement des œufs eux-mêmes (gérés au runtime).

## 6. Risques & mitigations
- **Casser un binding** → ne renommer/supprimer aucun nœud lié ; n'ajouter que des décor nommés neutre (`Holder`, `GemBtn`, `Corbel`, `Batten`, `RidgeCap`, `Molding`). Vérif read-back des noms en fin.
- **Œufs qui flottent** → ne pas changer CounterTop top (5.35) ni X/Z des Egg ; vérif Y des 6 après coup.
- **Z-fighting** → offsets ≥0.04 + détecteur coplanaire ; corriger avant de conclure.
- **MCP no-op** → script idempotent + relecture de vérification après chaque section.
- **Upload mesh** → si l'upload Open Cloud échoue, fallback : approximation native (cartouche = parts arrondis ; emblème = mesh œuf existant ; corbeau = wedges) pour ne pas bloquer le reste du polish.
