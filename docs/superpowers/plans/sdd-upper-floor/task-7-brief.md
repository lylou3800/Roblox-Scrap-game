## Task 7 : Vérification d'intégration + edge cases

**Files:** aucun (vérification seulement).

- [ ] **Step 1 : Rétro-compat profil existant** — en Play avec un profil pré-existant (ou simuler : Script temporaire qui retire `floor2Unlocked` et `f*` d'un `data.plot` puis appelle `DataService` reconcile/au prochain join). Vérifier via Script temporaire :
```luau
local Registry = require(game:GetService("ServerScriptService").Server.Registry)
local data = Registry.get("DataService").get(game:GetService("Players"):GetPlayers()[1])
local okF = data.plot.floor2Unlocked ~= nil
local okSlots = data.plot.slots.f1 ~= nil and data.plot.slots.f8 ~= nil
print("TAG_RECON: floor2Unlocked="..tostring(okF).." f1="..tostring(okSlots))
```
Attendu : `TAG_RECON: floor2Unlocked=true f1=true` (Reconcile a backfillé). Supprimer le Script.

- [ ] **Step 2 : Catch loop sur les baies de l'étage** — étage débloqué, débloquer une baie `f*` (prompt « Unlock ») puis y poser un UFO (prompt « Place UFO »). Vérifier via Script temporaire que `data.plot.slots.f1.ufoUid` est set et que la production tourne (le compteur scrap augmente, ou `CatchService` traite la baie). Attendu : la baie de l'étage produit comme une baie RDC (la boucle itère `data.plot.slots` génériquement).

- [ ] **Step 3 : Visiteur** — 2e joueur (ou simuler) : monter sur le plot d'un autre via l'échelle truss (doit fonctionner physiquement) ; vérifier que **son** `FloorBtn` est lié à **son** plot (pas celui du proprio visité). Le bouton ne doit pas apparaître/agir sur le plot d'autrui.

- [ ] **Step 4 : Respawn + chute** — à l'étage, se faire respawn (reset) → réapparaître au RDC (`spawnCF`, inchangé). Vérifier que les garde-corps empêchent de tomber de la dalle (faire le tour) et que la trémie est bordée (rails latéraux).

- [ ] **Step 5 : Idempotence** — appeler `PlotService.tryUnlockFloor` une 2e fois (Script temporaire) → pas de dalle dupliquée (garde `Floor2`), pas de re-débit (déjà couvert TAG_C). `screen_capture` : une seule dalle/échelle.

- [ ] **Step 6 : Récap final** — `screen_capture` du plot complet (RDC + étage) ; confirmer le style cohérent (DiamondPlate/métal/néons/placards), l'éclairage sous-dalle (RDC pas trop sombre). Noter tout ajustement de tuning (hauteur dalle, position panneau, recul échelle) à appliquer.

- [ ] **Step 7 : Checkpoint final** — prévenir l'utilisateur qu'il peut sauvegarder (Ctrl+S) et lister ce qui reste éventuellement à tuner.

---

