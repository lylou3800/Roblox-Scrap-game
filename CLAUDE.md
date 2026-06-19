# UFO Catchers — Règles de travail
> Auto-maintenu par /fin-session. Interdits + préférences fortes, valables chaque session.
> Le savoir contextuel/features vit dans le système de mémoire (memory/MEMORY.md).

## Ne JAMAIS faire
- Ne JAMAIS AI-générer les icônes / logos / images d'UI — les sourcer sur le Roblox Creator Marketplace (style flat-2D). L'utilisateur a rejeté les icônes IA 2×. Détails : mémoire `marketplace-icons-not-ai`.
- Ne JAMAIS écrire directement dans `build.rbxlx` à la main — c'est la source de vérité, éditée via Studio (MCP) puis sauvée par l'utilisateur.

## Toujours faire
- Répondre en **français**.
- Après TOUTE édition Studio via MCP (géométrie ou script), **rappeler à l'utilisateur de faire `Ctrl+S`** — les édits vivent dans la DataModel et ne sont PAS sauvés sur disque tant qu'il ne sauve pas.
- Après un `screen_capture` en mode **Édit**, remettre `workspace.CurrentCamera.CameraType = Custom` — la capture laisse la caméra Édit en `Scriptable` et **verrouille la navigation** de l'utilisateur (il l'a signalé explicitement).
- **Vérifier en live avant d'affirmer que c'est fini** : Play + lecture d'état (`execute_luau`), console sans erreur, capture. Pas d'affirmation de succès sans preuve.
- Travail géométrie/décor : lancer un détecteur coplanaire même-orientation après génération (anti-scintillement, offset ≥ 0.04). Détails : mémoire `z-fighting-coplanar-rule`.

## Préférences de travail
- Itératif et visuel : l'utilisateur envoie des screenshots, attend des corrections ciblées + une capture de vérification.
- Décor procédural cohérent avec la palette/menuiserie existante du jeu (pas de refonte non demandée).
