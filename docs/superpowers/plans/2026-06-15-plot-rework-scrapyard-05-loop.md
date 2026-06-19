# Plot Rework « Scrapyard » — Plan 05 : Boucle physique (tas → scoop/portage → vendeur robot + filtre)

**Série :** 5/6 · **Dépend de :** 01 (ancres pile/vendeur/filtre). **Exécution :** inline Studio.

**Goal:** La boucle de vente physique : un **gros tas** (avant-gauche) dont la hauteur reflète l'inventaire vendable ; **scoop (E)** → on porte une charge lumineuse ; **vendeur robot (E)** → vend tout (hors filtre) ; **kiosque filtre (E)** → choisir raretés/thèmes à laisser.

## Changements

### NOUVEAU `ServerScriptService.Server.Services.ScrapyardService` (auto-chargé)
- `sellFilter` par joueur (`getFilter`). Prompts E sur `IsPile`/`IsVendor`/`IsFilter` (server-authoritative, propre map `prompts`, ProximityPromptService).
- `doScoop` : si vendable>0 et pas déjà en charge → `carrying[player]=value`, charge soudée au perso (`attachCarry`), tas rétréci.
- `doSell` : `InventoryService.sellFiltered` → `EconomyService.add` (via sellStack), retire la charge, event `cashout`.
- `refreshPile` : hauteur du tas = `log(valeur vendable)` (Heartbeat 1s + sur scoop/sell/filtre).
- `buildRobot` : robot vendeur procédural (corps/tête/écran/bras), taggé `VendorBot`.
- Remote `setSellFilter` (rarity/theme/clear) → maj `data.sellFilter` + replicate.

### `InventoryService`
- `require(LootTable)` ; `sellFiltered(player, filter)` (vend non-locked & non-filtrés) ; `sellableInfo(player, filter)` → (valeur, count).

### `GameConfig.PROFILE_TEMPLATE`
- `sellFilter = { rarities = {}, themes = {} }` (Reconcile propage aux saves).

### NOUVEAU `StarterPlayer.StarterPlayerScripts.Client.Controllers.ScrapyardController` (auto-chargé)
- `onEvent("openFilter")` → panneau ScreenGui (chips raretés `Rarities.list` + thèmes `ScrapThemes.list`, toggle → `setSellFilter`).
- `onEvent("cashout")` → bannière « + $X » + son + (FX).
- Heartbeat → pulse Face/Bulb des `VendorBot`.

## Vérif (Play)
- Console propre ; `ScrapyardService` chargé (13 services).
- Tas présent, hauteur > 1 après quelques prises ; prompts E (Ramasser/Vendre/Filtre) ; robot vendeur présent.
- Scoop → charge portée + tas à plat ; Vendre → `$` crédité, charge retirée ; filtre → raretés/thèmes laissés non vendus.

## Reporté au Plan 06
Retrait de la vente-menu (UIController), retrait du recycleur (MachineService), nettoyage Tray/UI dormantes, look « éteint » des zones verrouillées + power-on, migration.
