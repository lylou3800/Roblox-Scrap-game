# Inventaire + Hotbar + Rework pose des pinces — Design

**Date:** 2026-06-17
**Statut:** validé en brainstorming, en attente de revue utilisateur

## Contexte

L'inventaire actuel est un menu `Inventaire` (dans la ScreenGui pré-authorée `Menus`, ouvert par le bouton « INVENT. » de la sidebar, peuplé par `populateInventory()` dans le LocalScript `StarterGui.MainHUD.UIController`). Il est en lecture seule, peu lisible, et un second contrôleur `InventoryUIController` (legacy) existe mais n'est jamais ouvert.

L'utilisateur veut :
1. Un **inventaire ultra propre style « Grow a Garden »** (réf. fournie) : sidebar de catégories à gauche, recherche en haut à droite, grille de cartes, accessible « comme l'inventaire Roblox ».
2. Reworker la **pose/récupération des pinces** : les pinces vivent dans un **hotbar** (en main), on en sélectionne une puis on la **place dans une usine avec E** (au lieu de l'auto-sélection serveur actuelle).
3. **Augmenter la distance** de pose et d'amélioration d'une usine (10 studs → trop court).

### Décisions prises (questions/réponses)
- **Catégories** : `Tout` (+ filtre rareté) · `Ferraille` (loot) · `Pinces` (UFOs possédés). Pas les objets craftés.
- **Hotbar** = pinces possédées ; sert à choisir la pince à poser.
- **Accès** : hotbar toujours visible + **touche** qui ouvre/ferme le panneau ; **sac à dos Roblox désactivé**.
- **Pose** : **prompt E** sur l'emplacement (« Placer : <pince sélectionnée> »), réutilise le système de prompts/distances existant.

## Faits du code existant (références)

- Style canonique : `ReplicatedStorage.UI.Theme` (Palette cartoon, `Font.Title`=LuckiestGuy / `Font.Body`=FredokaOne, helpers `Corner/Stroke/TextStroke/Pill/Panel/Button/Gradient/SectionHeader`). À utiliser partout.
- Pattern contrôleur : modules sous `StarterPlayer.StarterPlayerScripts.Client.Controllers`, auto-`require` + `Registry.controllers[name]`, phases `:Init()` puis `:Start()`. Accès croisé `Registry.get("X")` / `Registry.controllers["X"]`.
- Données joueur (`Shared.Types`) : `inventory` = `{[key]=InventoryStack{defId,rarity,modifier,count,locked}}` ; `ufos` = `{[uid]={defId,level,prestige}}`. Clé pile = `Id.itemKey`. Valeur calculée via `Pricing.valueOf` (pas stockée). Réplication : `DataService.replicate` → `Net.pushState` → client `StateController.get()/onChanged(fn)`.
- Pas d'assets image d'objets. Raretés : `Rarities.list` (10 tiers, `.color`, `.icon` emoji). Aperçus de pinces possibles via le builder de modèle (`makeUFOModel`/`ClawModel.build`) — `IndexController` utilise déjà des `ViewportFrame` de machines.
- Placement actuel (`PlotService`, serveur) : prompt E « Place UFO » sur emplacement vide → `PromptTriggered` (serveur) → `handlePlace` qui **auto-pioche** `findFreeUFO`. Emplacement occupé : E « Ranger l'UFO » (`handleUnequip`), R « Ameliorer » (`handleUpgrade` → event `openClawMenu` → `ClawMenuController`). Lien pince↔emplacement = `data.plot.slots[slotId].ufoUid` (les pinces restent toujours dans `data.ufos`).
- Tous les prompts d'emplacement : `Style=Custom`, `MaxActivationDistance=10`, `RequiresLineOfSight=false` (`PlotService.refreshSlot`, ~630838-630902). Rendu par `PromptStyleController` (lit `prompt.MaxActivationDistance`, `bb.MaxDistance = dist+6`, empilement via `UIOffset.Y`).
- Sac à dos Roblox : **non désactivé** mais inutilisé (aucun Tool dans le jeu).

## Architecture (composants)

### A. `InventoryController` (nouveau, client) — le grand panneau
- Construit une `ScreenGui` "InventoryPanel" via `Theme` (panneau plein écran centré, overlay sombre, pop UIScale ; fermeture overlay/X/Échap, cohérent avec les autres panneaux).
- **Layout** (calqué réf.) :
  - **Sidebar gauche** : boutons-onglets `Tout` · `Ferraille` · `Pinces` (icône + libellé, onglet actif surligné).
  - **Barre recherche** en haut à droite (TextBox + icône loupe) → filtre la grille par nom (insensible casse/accents).
  - **Grille** centrale : `ScrollingFrame` + `UIGridLayout`, cartes de taille fixe.
- **Contenu par onglet** :
  - `Tout` : agrège Ferraille + Pinces ; rangée de **puces de filtre par rareté** (toutes + 10 tiers) au-dessus de la grille.
  - `Ferraille` : une carte par pile `data.inventory` — fond couleur rareté + emoji rareté + nom + `×count` + valeur (`Pricing.valueOf × count`). Lecture seule (vente via vendeur physique inchangée). Cadenas si `locked`.
  - `Pinces` : une carte par `data.ufos` — **aperçu `ViewportFrame`** du modèle de pince + nom + pastille rareté + badge `RANG <roman>`. Cliquer une carte **sélectionne** la pince (= sélection hotbar). Badge « posée » si déjà sur un emplacement.
- **Données** : `StateController.get()` ; re-render sur `onChanged` si visible.
- **Toggle** : touche configurable `TOGGLE_KEY` (constante en tête de fichier ; défaut proposé `Tab`, ne pas utiliser 1-0 réservés au hotbar). Le panneau apparait/disparait ; le hotbar reste visible.

### B. `HotbarController` (nouveau, client) — barre du bas permanente
- `ScreenGui` "Hotbar" toujours visible, alignée en bas (style réf.), slots numérotés `1..0`.
- Affiche les **pinces possédées** (`data.ufos`) : mini `ViewportFrame` + numéro de slot + nom court + pastille rareté.
- **Sélection** : touches `1`-`0` + clic. Pince sélectionnée = bordure dorée (Theme.Gold). État `selectedUid`.
- Pinces déjà posées : carte **grisée** + petit badge « posée ».
- Expose `HotbarController.getSelected() -> uid?` (consommé par la logique de pose) et `HotbarController.select(uid)` (appelé par le panneau Pinces).
- Re-render sur `StateController.onChanged` (nouvelle pince, pose/retrait).
- **Désactive le sac à dos Roblox** dans `:Start()` : `StarterGui:SetCoreGuiEnabled(Enum.CoreGuiType.Backpack, false)` (avec retry pcall au join).

### C. Pose / récupération reworkées (`PlotService` serveur + client)
- **Pose pilotée client** : le prompt E reste sur l'emplacement vide (Custom). Le serveur pose des **attributs** sur le prompt (`prompt:SetAttribute("Kind","place")`, `("SlotId", slotId)`) pour que le client l'identifie. À `ProximityPromptService.PromptTriggered` côté **client**, si `Kind=="place"` : lire `HotbarController.getSelected()` et envoyer `Net.request("placeUFO", { slotId, uid })`. Si aucune pince sélectionnée/libre → notify « Sélectionne une pince ».
- **Serveur** : nouveau handler `Net.onRequest("placeUFO", ...)` qui valide (plot du joueur, slot débloqué+vide, `uid` possédé et non déjà posé via le set `assigned`) puis `slotData.ufoUid = uid`, `refreshSlot`, replicate. **Supprimer** la branche serveur `kind=="place"` (auto-pick `findFreeUFO`) et `handlePlace`.
- L'`ObjectText` du prompt place affiche « Placer : <nom de la pince sélectionnée> » (mis à jour côté client à `PromptShown`/changement de sélection).
- **Récupération** (E sur occupé, `handleUnequip`) : inchangée — la pince redevient libre et réapparait active dans le hotbar.
- **Amélioration** (R, `handleUpgrade` → `openClawMenu` → `ClawMenuController`) : logique inchangée.

### D. Distances
- Dans `PlotService.refreshSlot`, passer `MaxActivationDistance` de **10 → 18** pour les prompts : déverrouillage, pose, récupération, amélioration. `PromptStyleController` suit automatiquement (`bb.MaxDistance = dist+6 = 24`). Constante partagée `SLOT_PROMPT_DIST = 18` en tête de `PlotService` pour cohérence.

### E. Nettoyage (suppression de l'inventaire GUI actuel)
- `UIController` LocalScript : retirer le bloc `populateInventory()` et le câblage `wire("InventaireBtn", open("Inventaire"))`. Le bouton « INVENT. » est **masqué** (accès par touche). (Rebrancher sur le nouveau panneau = une ligne, si souhaité plus tard.)
- `InventoryUIController` (legacy orphelin) : **supprimé** (ModuleScript retiré) — plus rien ne l'ouvre.
- La Frame pré-authorée `Menus.Inventaire` n'est plus ouverte ; suppression optionnelle (laisser inerte est sans risque).
- Conserver : `ScrapyardController` (« TRI DU TAS »), vente au vendeur, menu d'amélioration.

## Flux de données

1. Catch/pose/retrait/achat → mutation serveur → `DataService.replicate` → `Net.pushState`.
2. Client `StateController` met à jour + notifie ; `HotbarController` et `InventoryController` (si visible) se re-rendent.
3. Pose : clic/E → client lit `getSelected()` → `Net.request("placeUFO",{slotId,uid})` → serveur valide+pose → replicate → UI suit.

## Unités & interfaces (isolation)

- `HotbarController` : barre + sélection ; API `getSelected()/select(uid)`. Dépend de `StateController`, `Theme`, builder de modèle pinces.
- `InventoryController` : panneau + onglets + recherche ; toggle touche ; dépend de `StateController`, `Theme`, `HotbarController.select`, builder d'aperçu.
- Helper d'aperçu pince partagé (ViewportFrame) : un petit module/utilitaire réutilisé par hotbar + panneau + (déjà) index, basé sur `makeUFOModel`/`ClawModel.build`.
- `PlotService` : remote `placeUFO` + distances ; le serveur reste l'autorité (validation possession/slot).

## Gestion des erreurs / cas limites
- Pose sans sélection / pince déjà posée / slot occupé/verrouillé : validations serveur + notify client, aucun effet.
- `SetCoreGuiEnabled` au join : pcall + une nouvelle tentative différée.
- Aucune pince possédée : hotbar montre des slots vides ; onglet Pinces vide avec message.
- Performance ViewportFrame : nombre de pinces faible (≤ ~quelques dizaines) ; previews construits une fois et mis en cache par defId/rank.

## Vérification (MCP Studio)
1. Edit DM : appliquer scripts (et miroir disque `build.rbxlx`), aucune erreur de compile (console propre au Play).
2. Play : hotbar visible en bas ; sac à dos Roblox absent ; touche ouvre/ferme le panneau ; onglets Tout/Ferraille/Pinces + recherche fonctionnent ; cartes correctes (count/valeur, aperçus pinces).
3. Sélectionner une pince (1-0 ou clic), s'approcher d'un emplacement vide : prompt « Placer : <nom> », E pose **cette** pince ; vérifier `slotData.ufoUid` côté serveur. E sur occupé récupère ; la pince repasse active au hotbar.
4. Vérifier la nouvelle distance (~18) : prompt activable plus loin (pose + amélioration).
5. `screen_capture` (caméra scriptable en Play) pour valider le rendu ; comparer à la réf.
6. **Ctrl+S** pour persister.

## Hors scope
- Objets craftés dans l'inventaire ; aperçu fantôme « building » ; refonte de la vente ; nouveaux assets image.
