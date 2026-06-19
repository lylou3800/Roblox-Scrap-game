# Inventaire à base de Tools (feel Roblox natif + catégories) — Design

**Date:** 2026-06-17 (pivot de la rework précédente)
**Statut:** validé en brainstorming ("oui c'est bon bas y")

## Contexte / problème

La première rework (panneau Tab custom + hotbar data-driven) ne correspond pas à l'attendu :
- L'inventaire restait synchronisé avec les pinces **posées** (badge POSÉE) au lieu de les retirer.
- Il ne s'ouvrait pas comme l'inventaire **Roblox natif** ; on ne pouvait pas **prendre un objet en main**.

Nouvelle direction (décisions utilisateur) :
1. **Vrais Tools Roblox** : tout objet (pinces ET ferraille) devient un `Tool` dans le `Backpack` ; équiper = **tenir en main** ; touches 1-0 natives.
2. **Inventaire = backpack natif restylé avec catégories** (le CoreGui natif ne pouvant pas avoir d'onglets, on le remplace par une GUI maison au comportement natif).
3. **Choisir la pince à poser = l'équiper** (en main) ; **E** pose la pince équipée.
4. **Pince posée → son Tool disparaît** du sac ; **retrait → il revient**.

## Faits du code existant (réutilisés)

- `ClawPreview.make(defId, prestige, parent) -> ViewportFrame` (vignette pince, cache `defId|prestige`).
- Serveur `PlotService` : remote `Net.onRequest("placeUFO", {slotId, uid})` (valide owns/unlocked/empty/owned/not-placed) ; prompts de slot taggés `Kind`/`SlotId` ; `SLOT_PROMPT_DIST = 18`. Lien pince↔slot = `data.plot.slots[slotId].ufoUid`. `handleUnequip` (E sur occupé) libère le slot.
- Données : `data.ufos[uid]={defId,level,prestige}` ; `data.inventory[key]={defId,rarity,modifier,count,locked}` (`key = Id.itemKey`). Valeur = `Pricing.valueOf(defId,rarity,modifier)`.
- `DataService.replicate(player)` est appelé à chaque mutation (catch, sell, place, unequip, grant claw…) → point de hook unique idéal.
- `Theme` (`ReplicatedStorage.UI.Theme`), config `Shared.Config.{UFOCatchers,LootTable,Rarities,Pricing}`.
- Backpack CoreGui actuellement désactivé par l'ancien `HotbarController` (qui sera supprimé → re-basculé dans le nouveau contrôleur).

## Architecture

### A. Serveur `ToolService` (nouveau)
Maintient les `Tool` du `Backpack` en miroir de `data`, idempotent, sans perturber le Tool équipé.
- **Tool pince** (1 par `uid` de `data.ufos` **non présent dans un slot**) : `Name = ufoDef.name`, attributs `Kind="pince"`, `UfoUid=uid`, `DefId=defId`, `Prestige=prestige`. `Handle` = petite part compacte teintée rareté (`CanCollide=false`, `Massless`), `ToolTip` = nom. (Prop compacte ; modèle claw réduit en main = polish ultérieur possible.)
- **Tool ferraille** (1 par pile de `data.inventory` avec `count>0`) : `Name = def.name.." ×"..count`, attributs `Kind="ferraille"`, `ItemKey=key`, `DefId`, `Rarity`, `Count`. `Handle` = petite part teintée rareté.
- `reconcile(player)` : calcule l'ensemble désiré (pinces non posées + piles), scanne les Tools existants (`Backpack` **et** `Character` équipé) identifiés par `UfoUid`/`ItemKey` ; **crée** les manquants dans `Backpack`, **détruit** les superflus (y compris l'équipé devenu obsolète → ex. pince posée), **met à jour** `Count`/`Name` des piles existantes sans recréer.
- **Hooks** : (1) un appel `reconcile(player)` à la fin de `DataService.replicate` (hook unique, couvre catch/sell/place/unequip/grant) ; (2) `Players.PlayerAdded`→`CharacterAdded` → `reconcile` (le Backpack est vidé au respawn).

### B. Client `BackpackController` (nouveau ; remplace HotbarController + InventoryController)
GUI maison qui se comporte comme le backpack natif **mais** avec catégories.
- Désactive le CoreGui `Backpack` (pcall + retry).
- **Hotbar** permanente en bas (slots 1-0) : montre jusqu'à 10 Tools (pinces d'abord, puis ferraille, ordre stable) ; **clic** ou **touche 1-0** = `humanoid:EquipTool(tool)` (re-presser = `UnequipTools`) ; Tool équipé surligné (or). Icône pince = `ClawPreview` ; ferraille = cellule teintée rareté + emoji + `×count`.
- **Panneau extensible** (bouton + touche, ex. `Tab`/touche sac) : onglets **Tout / Ferraille / Pinces** + **recherche** + grille ; cliquer une carte équipe le Tool.
- Lit l'état réel : `player.Backpack` + Tool équipé (`Character`). Rafraîchit sur `Backpack.ChildAdded/Removed` + `Character.ChildAdded/Removed` + `CharacterAdded`.

### C. Client `PlacementController` (ajusté)
- À un prompt `Kind=="place"` : lit le **Tool équipé** (`character:FindFirstChildOfClass("Tool")`) ; si `Kind=="pince"` → `Net.request("placeUFO", {slotId, uid = tool:GetAttribute("UfoUid")})` ; sinon `ObjectText`/notify « Équipe une pince ». `PromptShown` met `ObjectText` = nom de la pince équipée ou « Équipe une pince ». Ne dépend plus de `HotbarController`.

### D. Suppression
- Supprimer `HotbarController` + `InventoryController` (remplacés par `BackpackController`). Garder `ClawPreview`, `PlacementController` (ajusté), le remote `placeUFO`.

## Flux

1. Mutation data (catch/sell/place/unequip/grant) → `DataService.replicate` → `ToolService.reconcile` → Backpack à jour (pinces non posées + ferraille).
2. Joueur équipe une pince (1-0/clic) → tenue en main.
3. À un slot vide, **E** → `PlacementController` lit le Tool équipé → `placeUFO{slotId,uid}` → serveur lie le slot + replicate → reconcile **détruit** le Tool (pince « disparaît » du sac et apparait dans le slot).
4. **E** sur slot occupé (`handleUnequip`) → slot libéré + replicate → reconcile **recrée** le Tool pince dans le Backpack.

## Cas limites / risques
- `reconcile` idempotent : ne pas détruire/recréer un Tool inchangé (clé stable `UfoUid`/`ItemKey`) ; mettre à jour `Count`/`Name` en place.
- Détruire le Tool équipé quand la pince est posée = comportement voulu (sort de la main → slot).
- Respawn vide le Backpack → reconcile sur `CharacterAdded`.
- Sans CoreGui backpack, les touches 1-0 n'équipent plus nativement → `BackpackController` les gère (`EquipTool`).
- Beaucoup de Tools ferraille possibles → hotbar = 10 premiers (pinces priorisées), reste dans la vue étendue catégorisée. Handles `CanCollide=false`, légers.
- `reconcile` au respawn doit attendre `Backpack` + `Humanoid` prêts.

## Vérification (MCP Studio)
1. Tools apparaissent dans `Backpack` (pinces non posées + ferraille) ; counts corrects ; pince posée → pas de Tool.
2. Équiper une pince (1-0/clic) → en main ; E à un slot vide pose CELLE-ci ; le Tool disparait ; E sur occupé → Tool revient.
3. GUI : hotbar + panneau catégories Tout/Ferraille/Pinces + recherche ; backpack natif absent.
4. Catch ajoute/maj un Tool ferraille (count) sans casser l'équipé.
5. **Ctrl+S**.

## Hors scope
- Modèle claw réduit en main (polish ultérieur ; prop compacte pour l'instant).
- Drag-drop / réarrangement des slots (équip simple au clic/touche).
- Usage en main de la ferraille (équipable mais sans effet).
