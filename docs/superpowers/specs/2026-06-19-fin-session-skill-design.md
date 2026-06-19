# Skill `/fin-session` — Consolidation d'intelligence en fin de session

**Date :** 2026-06-19
**Statut :** Design validé, prêt pour le plan d'implémentation
**Auteur :** Lyam Farhi (brainstorming avec Claude)

## Problème

À chaque session Claude Code, l'assistant apprend : préférences de travail, choses à
ne jamais faire, corrections de méthode, pièges techniques, avancement des features.
Quand la session se ferme, cette intelligence disparaît. La session suivante repart de
zéro et il faut tout réexpliquer.

Le projet dispose déjà d'un **système de mémoire par-projet** (`memory/MEMORY.md` +
~24 fichiers `memory/*.md`), mais il est presque exclusivement rempli de *snapshots de
feature* (`type: project`). La couche **méta** — préférences, interdits, corrections,
« fais plutôt comme ça » — n'est pas capturée de façon systématique. De plus, la mémoire
est **rappelée par pertinence** : une règle critique peut ne pas remonter dans une
session donnée.

## Objectif

Un skill invocable en fin de session (`/fin-session`) qui :

1. **Scanne** la conversation pour en extraire l'intelligence durable.
2. **Trie** chaque apprentissage vers la bonne destination (routage hybride).
3. **Dédoublonne** contre l'existant et **fusionne** plutôt que dupliquer.
4. **Écrit automatiquement** (pas de validation préalable).
5. **Affiche un reçu** clair de ce qui a été écrit et où, pour relecture/annulation.

## Décisions de design (issues du brainstorming)

| Décision | Choix retenu |
|---|---|
| **Routage** | **Hybride** : règles dures + préférences fortes → fichier toujours chargé ; le reste → mémoire rappelée par pertinence. |
| **Périmètre** | **Méta + progression** : couche méta ET mise à jour de l'avancement des features. |
| **Validation** | **Écriture automatique**, compensée par dédup + haute-confiance + reçu transparent. |
| **Emplacement des règles** | **`CLAUDE.md` à la racine du repo** (auto-chargé, versionné par git). Escape hatch vers `~/.claude` pour une préférence vraiment trans-projet. |
| **Packaging** | Un **skill** (`SKILL.md`), invoqué par `/fin-session` ou en langage naturel. |

## Architecture

### Composants

- **`~/.claude/skills/fin-session/SKILL.md`** — le skill lui-même. Project-agnostic :
  il se cale sur le projet courant (répertoire mémoire du projet + `CLAUDE.md` à la
  racine du repo courant). Contient la checklist de process, les règles de triage et
  les conventions de format (restituées pour être robuste même si le contexte système
  change).

- **`<repo>/CLAUDE.md`** *(créé au premier run si absent)* — foyer des règles
  toujours chargées. Gardé **court** car chargé à chaque session.

- **Répertoire mémoire du projet** *(existant)* —
  `…/.claude/projects/<projet>/memory/` : `MEMORY.md` (index) + fichiers `*.md`.
  Le skill réutilise le protocole et le format en place, sans le modifier.

- **`~/.claude/…`** *(optionnel, cas par cas)* — pour une préférence générale de
  travail clairement trans-projet.

### Flux de données

```
Conversation (en contexte)
        │  scan 6 catégories
        ▼
   Apprentissages candidats (haute-confiance, explicites)
        │  triage
        ├──► Règles dures / préférences fortes ──► <repo>/CLAUDE.md   (toujours chargé)
        │                                          └─(trans-projet)──► ~/.claude/…
        └──► Gotchas / snapshots feature / décisions / how-to-better ──► memory/*.md + MEMORY.md
                 │  (dédup + merge contre l'existant avant écriture)
                 ▼
            Reçu catégorisé affiché à l'utilisateur (chemins + écartés)
```

## Process du skill (checklist)

Le skill crée une tâche par étape et les exécute dans l'ordre :

1. **Localiser les cibles** — répertoire mémoire du projet courant, `MEMORY.md`,
   `CLAUDE.md` à la racine du repo (le créer s'il manque).
2. **Scanner la conversation** selon 6 catégories de signal :
   - **Règles dures** — « ne JAMAIS faire X », « TOUJOURS faire Y ».
   - **Préférences** — style, langue, outils, verbosité, workflow.
   - **Corrections / « fais plutôt comme ça »** — redressements de méthode.
   - **Gotchas techniques** — pièges qui ont coûté du temps.
   - **Avancement features** — ce qui a été construit/changé cette session.
   - **Décisions + le « pourquoi »** non visible dans git.
3. **Filtrer par confiance** — ne garder que l'explicite et le haut-confiance
   (énoncé par l'utilisateur, pas inféré). Écarter le transitoire, le one-off, et
   ce qui est déjà dans git/le code.
4. **Trier** chaque apprentissage retenu vers sa destination (voir routage).
5. **Dédoublonner & fusionner** — lire l'existant (CLAUDE.md, MEMORY.md, fichiers
   mémoire pertinents) ; mettre à jour/fusionner au lieu de dupliquer ; marquer
   obsolète ce qui est dépassé.
6. **Écrire** — automatiquement, sans gate :
   - `CLAUDE.md` : ajouter/fusionner dans la bonne section, garder lean.
   - Mémoire : créer/MAJ les fichiers `*.md` au format frontmatter existant, mettre
     à jour le pointeur une-ligne dans `MEMORY.md`.
7. **Afficher le reçu** — récap catégorisé (règles ajoutées/MAJ, mémoires
   créées/MAJ) avec chemins, plus la liste de ce qui a été écarté et pourquoi.

## Formats de fichiers

### `<repo>/CLAUDE.md`

```markdown
# UFO_Catchers — Règles de travail
> Auto-maintenu par /fin-session. Interdits + préférences fortes, valables chaque session.
> Le savoir contextuel/features vit dans le système de mémoire (memory/MEMORY.md).

## Ne JAMAIS faire
- …

## Toujours faire
- …

## Préférences de travail
- …
```

Contraintes : terse, dédoublonné, pas de dump technique verbeux (ça part en mémoire).
Chaque puce = une règle actionnable. Le fichier reste court pour ne pas gonfler le
contexte de départ.

### Fichiers mémoire (format existant, inchangé)

Frontmatter `name` / `description` / `metadata.type` (`feedback|project|user|reference`),
corps avec liens `[[autre-memoire]]`, et pour `feedback`/`project` les lignes
`**Why:**` / `**How to apply:**`. Pointeur une-ligne ajouté/maj dans `MEMORY.md`.
Dates relatives converties en absolu.

## Gestion d'erreurs / cas limites

- **`CLAUDE.md` absent** → le créer avec l'en-tête type, puis remplir.
- **Aucun apprentissage haute-confiance** → ne rien écrire ; le dire explicitement
  dans le reçu (« session sans apprentissage durable détecté »).
- **Apprentissage déjà présent** → fusionner/mettre à jour, ne pas dupliquer.
- **Apprentissage contredisant une règle existante** → remplacer et signaler le
  changement dans le reçu (l'utilisateur peut annuler).
- **Ambiguïté projet vs global** → défaut **projet** ; ne router vers global que si
  clairement trans-projet.
- **Doute sur la confiance** → écarter et lister dans « écartés » plutôt que polluer
  les fichiers permanents.

## Garde-fous (compensent l'écriture auto)

- Haut-confiance **explicite** uniquement.
- Dédup systématique avant écriture.
- `CLAUDE.md` gardé lean.
- Reçu transparent avec chemins → annulation facile.
- Aucune écriture dans le code ou la logique du jeu ; le skill ne touche qu'aux
  fichiers d'intelligence (CLAUDE.md, mémoire).

## Vérification

- **Run à vide** (session sans apprentissage) → reçu « rien à enregistrer », zéro
  écriture.
- **Run avec une règle dure** explicite → apparaît dans `CLAUDE.md` § Ne JAMAIS faire.
- **Run avec un gotcha technique** → fichier mémoire `type: feedback` + pointeur
  `MEMORY.md`.
- **Re-run immédiat** → idempotent : pas de doublon, fusion propre.
- **Inspection manuelle** des fichiers écrits contre le reçu affiché.

## Hors périmètre (YAGNI)

- Pas de hook automatique SessionEnd (invocation manuelle voulue).
- Pas de validation item-par-item ni de gate de relecture.
- Pas de réécriture/refactor des 24 fichiers mémoire existants (seulement MAJ
  ciblées des features touchées cette session).
- Pas de synchronisation multi-machines ni de stockage externe.
```
