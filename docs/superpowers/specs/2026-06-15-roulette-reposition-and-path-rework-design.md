# Repositionnement roulette + rework des chemins — Design

Date : 2026-06-15

## Contexte

Deux problèmes visuels sur la map :
1. La zone roulette RNG est mal centrée (tassée en avant-gauche, débordant sur l'herbe).
2. Les petits chemins reliant les plots à la route principale sont des dalles plates sans relief, à restyliser (textures LEGO conservées).

## Partie 1 — Recentrer la roulette

- La zone est construite par `ShopService` autour de `O`, dérivé de `PlotLayout.rouletteOffset` (= `(34,0,-90)`).
- Le pad atterrit à world `(-320.5, -56)` pour Plot_507921524 → trop à gauche, à moitié sur l'herbe.
- **Correctif** : recalculer `rouletteOffset` pour centrer le pad dans le rectangle d'herbe avant-gauche :
  - X ∈ [−352 (bord plot) → −299 (bord gauche chemin central)]
  - Z ∈ [−80 (bord avant plot) → −24 (trottoir route)]
  - Centre cible ≈ **(−326, −52)**, entièrement sur l'herbe, marges ~4–5 studs, carré, à gauche du chemin.
- `rouletteOffset` est relatif au plot et partagé par les 8 plots → correctif global.
- Aucune modif du design de la machine. Offset exact calculé depuis le `plot.origin` réel, puis vérifié par capture et ajusté au stud près.

## Partie 2 — Rework des chemins (style « route pavée cartoon »)

- 8 dalles identiques dans `Workspace.MapBlockout.PlotConnectors` (22×58, plates, tan).
- Nouveau chemin, même empreinte 22×58, `Material.Plastic` (tenons LEGO) :
  - Sol à tenons deux tons (crème clair surélevé ~0.3 + bordure intérieure tan foncé).
  - Ligne centrale pointillée (4–5 tirets, blanc cassé).
  - Bordures arrondies basses des deux côtés (cylindres couchés, ton clair).
  - 2 lampadaires à l'entrée côté route (poteau + tête + ampoule néon chaude). Option : +2 côté plot.
- **Implémentation** : générateur Luau lancé une fois en mode Edit, remplace les 8 dalles par le modèle stylisé (orienté par rangée nord/sud), bake statique. Idempotent, conservé pour ajustements.

## Notes

- Studio doit être en mode **Edit** pour modifier la source (`.rbxlx` = source de vérité).
- Vérification visuelle par capture d'écran après chaque partie.
