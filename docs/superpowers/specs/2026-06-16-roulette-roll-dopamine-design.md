# Roulette Shop — Roll dopamine overhaul (design)

Date: 2026-06-16

## Context

The roulette shop lets players hold-E on a lever to free-pull claw machines onto
unlocked platforms. Two visual problems:

1. The floating preview above each platform is a generic gold trophy
   (`ShopService.makePrize`) that looks nothing like the real claw machines
   (built by `PlotService.makeUFOModel`). It is "out of date".
2. Between the lever pull and the prize appearing there is no animation above the
   platforms — no "roll", no suspense, no dopamine.

Goal: a clean, smooth, full-dopamine roll with 3D mini-machines.

## Decisions (validated with user)

- **Roll style**: in-place swap. One shaded hologram per unlocked platform that
  swaps through machines, decelerates, snaps to the winner.
- **Pacing**: FAST but not instant. `ROLL_TIME ≈ 1.9s`. Front-loaded fast swaps,
  short ease-out deceleration, brief near-miss (~0.2s lingering on a rare
  silhouette), final snap. Too slow = not dopamine; too fast = feels cheat.
- **FX intensity scales with rolled rarity** (common = small pop; legendary =
  explosion + screen shake + jackpot + light column).
- **Colour**: dark silhouettes during the roll → full-colour reveal on stop.

## Architecture

Roll animation runs CLIENT-side (smooth 60fps, no replication jank). The server
stays authoritative: it decides outcomes (`rollClaw`) and spawns the real
buyable prize. No physics/CFrame replication during the animation.

### Server (`ServerScriptService.Server.Services.ShopService`)
- Replace `makePrize` with a **mini real machine**: `makeUFOModel(def,0,anchor)`
  scaled 0.32, `RemoveTag("UFOCatcher")` (else `CatchFXController.animateWorld`
  fights the float), all parts welded to the anchored Root so the existing float
  Heartbeat moves one part (cheap network), full colour, "Acheter" prompt unchanged.
- `pull(player)`: compute results per active platform, fire new event
  `shopRoll {results=[{index,defId,rarity,tier,fxTier}], duration=ROLL_TIME}` to
  the roller; `task.delay(ROLL_TIME)` then spawn the real mini-machine prizes.
- Keep the existing server lever tween; add a cabinet charge-up trigger via the
  same event so the client can light it up.

### Client (`StarterPlayer.StarterPlayerScripts.Client.Controllers.RouletteRollController`, new)
- On `shopRoll`: for each result, find the `Platform` (by `Index` attribute) under
  the local plot's `Roulette` model, read its `PrizeAnchor` CFrame attribute.
- Cabinet dopamine: flash + `igniteWave` neon orbs travelling cabinet→platforms.
- Silhouettes are **client-built simplified dark-slate machine shapes** (a fresh
  pool of 6 cheap ~9-part shadows per platform, built in `buildSilhouette` — NO
  server pool / no replication). Swap the visible one on an ease-out interval over
  `ROLL_TIME`, bob/spin via RenderStepped (only the active one), near-miss linger
  on the tallest shadow, final snap → silhouette destroyed. Server colour prize
  fades in in sync.
- Landing climax scaled by `def.tier` (flash always; ≥4 shockwave; ≥6 beam+jackpot;
  ≥8 explode+shake). All FX via the new `FXKit`.

### FX (`FXKit`, new shared module)
Extract reusable primitives (`burst`, `shockwave`, `lightBeam`, `explode`,
`shake`, `tweenNumber`, `playSound`) so the new controller and (later)
`CatchFXController` share one implementation. To limit risk this pass, FXKit is
created fresh; `CatchFXController` is left working as-is and can adopt it later.

## Files
- `ServerScriptService.Server.Services.ShopService` (edit)
- `ServerScriptService.Server.Services.PlotService` (read; reuse `makeUFOModel`)
- `StarterPlayer.StarterPlayerScripts.Client.Controllers.RouletteRollController` (new)
- shared `FXKit` module (new)
- `ReplicatedStorage.RouletteSilhouettes` (runtime folder, server-built)

## Verification
- Play in Studio, walk to the roulette zone, pull the lever.
- Confirm: cabinet dopamine FX; each unlocked platform shows dark silhouettes
  swapping fast → decelerate → near-miss → snap; full-colour mini real machine
  appears in sync with rarity-scaled climax; "Acheter" prompt works; buying
  fires the existing `newClaw` banner. Re-roll cancels in-flight animation.
