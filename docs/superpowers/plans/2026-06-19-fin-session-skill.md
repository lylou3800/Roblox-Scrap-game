# Skill `/fin-session` — Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Créer un skill `fin-session` qui, invoqué en fin de session, consolide l'intelligence durable (préférences, interdits, corrections, gotchas, avancement features) vers le `CLAUDE.md` du repo et le système de mémoire, pour qu'elle survive à la fermeture de session.

**Architecture:** Un unique fichier `SKILL.md` (instructions prompt, pas de code) placé sous `~/.claude/skills/fin-session/`. Project-agnostic : à l'exécution il se cale sur le repo courant (`CLAUDE.md` racine) et le répertoire mémoire du projet courant. Routage hybride : règles dures + préférences fortes → `CLAUDE.md` (toujours chargé) ; gotchas/snapshots/décisions → mémoire (rappelée par pertinence). Écriture auto + reçu transparent.

**Tech Stack:** Markdown (skill au format Claude Code / superpowers), conventions du système de mémoire du harness, git (uniquement pour les docs spec/plan, pas pour le skill).

## Global Constraints

- **Emplacement skill :** `C:\Users\farhi\.claude\skills\fin-session\SKILL.md` — HORS repo, non versionné (config perso). Aucun `git add`/`commit` ne porte sur ce fichier.
- **Nom + déclencheurs :** `name: fin-session`. Déclencheurs FR : `/fin-session`, « fin de session », « débrief », « sauvegarde/mémorise ce que tu as appris ».
- **Routage hybride :** règles dures (JAMAIS/TOUJOURS) + préférences fortes → `<repo>/CLAUDE.md`. Gotchas, snapshots feature, décisions, how-to-better contextuel → système de mémoire (`memory/*.md` + `MEMORY.md`). Escape hatch : préférence clairement trans-projet → `~/.claude/CLAUDE.md`.
- **Écriture automatique** (pas de gate), compensée par : haute-confiance **explicite** uniquement, dédup avant écriture, reçu transparent listant chaque chemin écrit.
- **`CLAUDE.md` reste lean** (chargé chaque session) : une puce = une règle actionnable, pas de dump technique verbeux (ça part en mémoire).
- **Format mémoire = miroir de l'existant :** le skill doit copier la forme de frontmatter des fichiers mémoire déjà présents dans le projet (qui utilisent `metadata.node_type`, `type`, `originSessionId`), pas une forme inventée.
- **Périmètre d'écriture restreint :** le skill n'écrit QUE dans les fichiers d'intelligence (`CLAUDE.md`, fichiers mémoire). Jamais dans le code/la logique du jeu.
- **Dates** relatives → absolues.

---

### Task 1: Scaffolder le skill (répertoire + frontmatter + squelette de sections)

**Files:**
- Create: `C:\Users\farhi\.claude\skills\fin-session\SKILL.md`

**Interfaces:**
- Consumes: rien (point de départ).
- Produces: un `SKILL.md` valide et découvrable, avec frontmatter `name: fin-session` + `description` déclenchante, et les en-têtes de sections que les tâches suivantes rempliront.

- [ ] **Step 1: Créer le répertoire du skill**

Run (PowerShell):
```powershell
New-Item -ItemType Directory -Force "C:\Users\farhi\.claude\skills\fin-session" | Out-Null; Test-Path "C:\Users\farhi\.claude\skills\fin-session"
```
Expected: `True`

- [ ] **Step 2: Écrire le frontmatter + le squelette**

Écrire dans `C:\Users\farhi\.claude\skills\fin-session\SKILL.md` :

```markdown
---
name: fin-session
description: Use at the END of a Claude Code session to consolidate durable intelligence — preferences, hard rules (never/always), corrections, technical gotchas, and feature progress — into the project's root CLAUDE.md and per-project memory system so it survives the session closing. Triggers on "/fin-session", "fin de session", "débrief", "fais le bilan", "sauvegarde / mémorise ce que tu as appris".
---

# Fin de session — Consolidation d'intelligence

## Quand l'utiliser
## Principe
## Checklist
## Formats
## Garde-fous
```

- [ ] **Step 3: Vérifier la validité du frontmatter et la découvrabilité**

Run (PowerShell):
```powershell
Get-Content "C:\Users\farhi\.claude\skills\fin-session\SKILL.md" -TotalCount 4
```
Expected : les 3 premières lignes montrent `---`, `name: fin-session`, et une ligne `description:` non vide commençant par `Use at the END`.

---

### Task 2: Rédiger le corps — « Quand l'utiliser », « Principe », et étapes 1→3 de la checklist

**Files:**
- Modify: `C:\Users\farhi\.claude\skills\fin-session\SKILL.md`

**Interfaces:**
- Consumes: le squelette de Task 1.
- Produces: les sections `## Quand l'utiliser`, `## Principe`, et le début de `## Checklist` (étapes 1 Localiser, 2 Scanner, 3 Filtrer).

- [ ] **Step 1: Remplacer la section `## Quand l'utiliser`**

Remplacer la ligne `## Quand l'utiliser` par :

```markdown
## Quand l'utiliser
À la fin d'une session, quand l'utilisateur tape `/fin-session` ou demande de sauvegarder / mémoriser / faire le bilan de ce qui a été appris. But : empêcher que les préférences, interdits, corrections, gotchas techniques et l'avancement des features disparaissent à la fermeture de la session.
```

- [ ] **Step 2: Remplacer la section `## Principe`**

Remplacer la ligne `## Principe` par :

```markdown
## Principe
Routage **hybride** :
- **Règles dures + préférences fortes** → `<repo>/CLAUDE.md` (chargé à CHAQUE session, donc garanti en contexte).
- **Gotchas techniques, snapshots de feature, décisions, how-to-better contextuel** → système de mémoire par-projet (`memory/*.md` + `MEMORY.md`), rappelé par pertinence.

Écriture **automatique** (pas de validation préalable), compensée par trois garde-fous : haute-confiance **explicite** uniquement, **dédup** contre l'existant, et un **reçu** affiché à la fin listant chaque chemin écrit (pour relecture/annulation facile).
```

- [ ] **Step 3: Remplacer la section `## Checklist` par l'en-tête + étapes 1→3**

Remplacer la ligne `## Checklist` par :

```markdown
## Checklist
Créer une tâche par étape et les exécuter dans l'ordre.

### 1. Localiser les cibles
- **Répertoire mémoire du projet courant** : le harness l'expose dans le bloc contexte « # Memory ». Sinon : `~/.claude/projects/<slug-du-projet>/memory/` ; l'index est `MEMORY.md`.
- **`CLAUDE.md` à la racine du repo courant** : `git rev-parse --show-toplevel` donne la racine. S'il n'existe pas, le créer avec l'en-tête type (voir `## Formats`).
- **Lire un fichier mémoire existant** du projet pour relever la forme exacte de son frontmatter (ce projet utilise `metadata.node_type`, `type`, `originSessionId`) afin de la reproduire à l'identique.

### 2. Scanner la conversation (6 catégories)
Relire le transcript de CETTE session et collecter les signaux durables :
- **Règles dures** — « ne JAMAIS faire X », « TOUJOURS faire Y », interdits formels.
- **Préférences** — langue, style, outils, verbosité, conventions, workflow (ex. « teste avant de dire que c'est fini », « Ctrl+S après édition Studio »).
- **Corrections / "fais plutôt comme ça"** — moments où l'utilisateur a redressé l'approche et indiqué une meilleure méthode.
- **Gotchas techniques** — pièges qui ont coûté du temps (échecs d'outils silencieux, comportements contre-intuitifs).
- **Avancement features** — ce qui a été construit/changé cette session (pour mettre à jour les snapshots existants).
- **Décisions + le "pourquoi"** non visible dans git.

### 3. Filtrer par confiance
Ne garder que l'**explicite et haut-confiance** : ce que l'utilisateur a réellement dit/demandé, ou un fait technique vérifié cette session. **Écarter** : suppositions, préférences inférées d'un seul exemple ambigu, état transitoire d'une tâche, et tout ce qui est déjà dans git / le code / les fichiers existants. En cas de doute → écarter (et le lister dans le reçu).
```

- [ ] **Step 4: Vérifier la présence des sections**

Run (PowerShell):
```powershell
Select-String -Path "C:\Users\farhi\.claude\skills\fin-session\SKILL.md" -Pattern "## Quand l'utiliser","## Principe","### 1. Localiser","### 2. Scanner","### 3. Filtrer" | ForEach-Object { $_.Line }
```
Expected : les 5 en-têtes ressortent, chacun une seule fois.

---

### Task 3: Rédiger les étapes 4→6 (Trier / Dédup / Écrire) + la section `## Formats`

**Files:**
- Modify: `C:\Users\farhi\.claude\skills\fin-session\SKILL.md`

**Interfaces:**
- Consumes: la checklist partielle de Task 2.
- Produces: étapes 4 (Trier), 5 (Dédoublonner & fusionner), 6 (Écrire) de la checklist, et la section `## Formats` complète (template `CLAUDE.md` + format fichier mémoire). C'est le cœur logique du skill.

- [ ] **Step 1: Ajouter les étapes 4→6 après l'étape 3**

Insérer, juste après le bloc de l'étape 3 (`### 3. Filtrer par confiance`) :

```markdown
### 4. Trier vers la destination
- **Règle dure / préférence forte** → `CLAUDE.md`. Si la préférence est clairement **trans-projet** (vaut pour tous les projets, pas spécifique à celui-ci) → fichier global `~/.claude/CLAUDE.md` (le créer si besoin) plutôt que le `CLAUDE.md` du repo.
- **Gotcha / snapshot feature / décision / how-to-better contextuel** → fichier mémoire.

### 5. Dédoublonner & fusionner
Avant TOUTE écriture, LIRE l'existant : `CLAUDE.md`, `MEMORY.md`, et les fichiers mémoire dont le sujet recoupe un apprentissage.
- Déjà présent → mettre à jour / fusionner, **jamais de doublon**.
- Contredit une règle/mémoire existante → remplacer et le **signaler dans le reçu**.
- Une feature a évolué → mettre à jour SON fichier mémoire + son pointeur `MEMORY.md` (ne pas en créer un second).

### 6. Écrire (automatique)
- **`CLAUDE.md`** : ajouter/fusionner chaque règle dans la bonne section (`## Ne JAMAIS faire`, `## Toujours faire`, `## Préférences de travail`). Une puce = une règle actionnable, terse. Garder le fichier **court** ; aucun détail technique verbeux ici (ça va en mémoire).
- **Mémoire** : pour chaque apprentissage routé vers la mémoire, créer ou mettre à jour un fichier `<slug>.md` au format frontmatter du projet (voir `## Formats`), puis ajouter/mettre à jour son pointeur une-ligne dans `MEMORY.md`. Convertir les dates relatives en absolu. Lier les sujets connexes via `[[autre-slug]]`.
```

- [ ] **Step 2: Remplacer la section `## Formats`**

Remplacer la ligne `## Formats` par :

````markdown
## Formats

### `CLAUDE.md` (le créer s'il manque)
```markdown
# <NomProjet> — Règles de travail
> Auto-maintenu par /fin-session. Interdits + préférences fortes, valables chaque session.
> Le savoir contextuel/features vit dans le système de mémoire (memory/MEMORY.md).

## Ne JAMAIS faire

## Toujours faire

## Préférences de travail
```

### Fichier mémoire (miroir du format existant du projet)
Reproduire la forme de frontmatter des fichiers mémoire déjà présents. Forme type :
```markdown
---
name: <slug-kebab-case>
description: <résumé une ligne — sert au rappel par pertinence>
metadata:
  node_type: memory
  type: feedback | project | user | reference
  originSessionId: <id de session courant si disponible>
---

<le fait. Pour `feedback`/`project`, faire suivre de lignes **Why:** et **How to apply:**. Lier les sujets connexes via [[autre-slug]].>
```
Puis ajouter une ligne d'index dans `MEMORY.md` : `- [Titre](slug.md) — accroche`.

**Types :** `user` = qui est l'utilisateur (rôle, préférences durables) ; `feedback` = comment je dois travailler (corrections/préférences confirmées, avec le pourquoi) ; `project` = travail/contraintes en cours non déductibles du code ; `reference` = ressources externes (URL, tickets).
````

- [ ] **Step 3: Vérifier la présence des étapes et des templates**

Run (PowerShell):
```powershell
Select-String -Path "C:\Users\farhi\.claude\skills\fin-session\SKILL.md" -Pattern "### 4. Trier","### 5. Dédoublonner","### 6. Écrire","Ne JAMAIS faire","node_type: memory" | ForEach-Object { $_.Line }
```
Expected : les 5 motifs ressortent (le « Ne JAMAIS faire » apparaît dans le template `CLAUDE.md`).

---

### Task 4: Rédiger l'étape 7 (Reçu), la section `## Garde-fous`, et les cas limites

**Files:**
- Modify: `C:\Users\farhi\.claude\skills\fin-session\SKILL.md`

**Interfaces:**
- Consumes: la checklist 1→6 + `## Formats` des tâches précédentes.
- Produces: étape 7 (Reçu) avec gabarit d'affichage + gestion du cas « rien à enregistrer », et la section `## Garde-fous`. Le skill est alors complet.

- [ ] **Step 1: Ajouter l'étape 7 après l'étape 6**

Insérer, juste après le bloc de l'étape 6 (`### 6. Écrire`) et AVANT `## Formats` :

````markdown
### 7. Afficher le reçu
Terminer par un récap catégorisé, avec **chemins**, pour relecture/annulation. Gabarit :
```
🧠 Débrief de session

Règles → <repo>/CLAUDE.md
  + [Ne JAMAIS]   <règle ajoutée>
  ~ [Préférence]  <règle mise à jour>

Mémoire
  + créé        memory/<slug>.md — <accroche>
  ~ mis à jour  memory/<slug>.md — <ce qui a changé>

Écartés (faible confiance)
  – <item> — <raison>
```
Si AUCUN apprentissage haut-confiance n'est détecté : ne rien écrire, et l'annoncer (« Session sans apprentissage durable détecté — rien enregistré. »).
````

- [ ] **Step 2: Remplacer la section `## Garde-fous`**

Remplacer la ligne `## Garde-fous` par :

```markdown
## Garde-fous
- **Haut-confiance explicite uniquement** ; dans le doute, écarter (et le lister).
- **Toujours dédoublonner** avant d'écrire (lire l'existant d'abord).
- **`CLAUDE.md` reste lean** : règles actionnables uniquement, pas de verbeux technique.
- **Périmètre restreint** : n'écrire QUE dans les fichiers d'intelligence (`CLAUDE.md`, fichiers mémoire, `MEMORY.md`). Jamais dans le code ou la logique du jeu.
- **Reçu obligatoire** : lister chaque chemin écrit pour que l'utilisateur puisse annuler.
- **Idempotence** : un re-run immédiat ne doit rien dupliquer (la dédup l'assure).
```

- [ ] **Step 3: Relire le fichier complet pour cohérence**

Run (PowerShell):
```powershell
Get-Content "C:\Users\farhi\.claude\skills\fin-session\SKILL.md" | Measure-Object -Line
Select-String -Path "C:\Users\farhi\.claude\skills\fin-session\SKILL.md" -Pattern "### 7. Afficher","## Garde-fous","Idempotence" | ForEach-Object { $_.Line }
```
Expected : le fichier fait ~90–120 lignes ; les 3 motifs ressortent. Relire visuellement : 7 étapes numérotées présentes et dans l'ordre, sections `Quand l'utiliser / Principe / Checklist / Formats / Garde-fous` toutes remplies (aucun en-tête vide laissé par le squelette).

---

### Task 5: Vérification comportementale de bout en bout (test à blanc, sans effet de bord)

**Files:**
- (aucune écriture de production — test only)

**Interfaces:**
- Consumes: le `SKILL.md` complet (Tasks 1→4).
- Produces: la preuve que le skill route correctement. Aucun fichier de production modifié.

- [ ] **Step 1: Construire un mini-transcript synthétique de test**

Préparer (mentalement ou dans un scratch) un transcript de 5 items plantés :
1. Règle dure : utilisateur dit « ne lance JAMAIS Play juste après une édition, le snapshot est périmé ».
2. Préférence : « réponds-moi toujours en français ».
3. Gotcha technique : « `multi_edit` a reporté succès mais n'a rien changé sur PlotService ».
4. Avancement feature : « on a fini le menu récompenses, pending Ctrl+S ».
5. Bruit faible-confiance : une seule occurrence ambiguë où l'assistant a supposé une préférence de couleur sans confirmation.

- [ ] **Step 2: Lancer un subagent qui lit SEULEMENT le skill + le transcript et produit le triage (sans écrire)**

Dispatcher un subagent (Explore ou general-purpose) avec pour consigne : lire `C:\Users\farhi\.claude\skills\fin-session\SKILL.md`, appliquer son process au transcript synthétique fourni dans le prompt, et **retourner uniquement** le plan de triage (quelle destination pour chaque item + ce qui est écarté), **sans rien écrire sur le disque**.

- [ ] **Step 3: Vérifier le routage attendu**

Expected :
- Item 1 (règle dure) → `CLAUDE.md` § Ne JAMAIS faire.
- Item 2 (préférence langue) → `CLAUDE.md` § Préférences (ou global si jugé trans-projet — acceptable).
- Item 3 (gotcha) → fichier mémoire `type: feedback`.
- Item 4 (avancement) → mise à jour mémoire `type: project` (snapshot feature).
- Item 5 (bruit) → **écarté**, listé dans « Écartés ».

Si un item est mal routé ou l'item 5 n'est pas écarté : corriger le `SKILL.md` (préciser la règle de triage/filtre concernée) et relancer Step 2.

- [ ] **Step 4: Commit du plan dans le repo (pas le skill — il est hors repo)**

```bash
git add docs/superpowers/plans/2026-06-19-fin-session-skill.md
git commit -m "docs(fin-session): plan d'implémentation du skill de consolidation"
```

Note : le `SKILL.md` lui-même vit dans `~/.claude/skills/` (hors repo) et n'est pas versionné — c'est attendu.

---

## Self-Review (effectuée à l'écriture du plan)

**Couverture du spec :**
- Routage hybride → Tasks 2 (principe) + 3 (étape 4 Trier). ✓
- 6 catégories de scan → Task 2 étape 2. ✓
- Filtre haute-confiance → Task 2 étape 3. ✓
- Dédup/merge → Task 3 étape 1 (étape 5). ✓
- Écriture auto → Task 3 étape 1 (étape 6). ✓
- Reçu transparent → Task 4 étape 1. ✓
- Formats `CLAUDE.md` + mémoire → Task 3 étape 2. ✓
- Garde-fous → Task 4 étape 2. ✓
- Cas limites (rien à enregistrer, contradiction, projet vs global) → Task 3 (étapes 4-5) + Task 4 (étape 7). ✓
- Vérification → Task 5. ✓

**Placeholders :** aucun « TBD/TODO ». Les `<…>` (ex. `<repo>`, `<slug>`, `<NomProjet>`) sont des gabarits intentionnels résolus à l'exécution, pas des trous de plan.

**Cohérence des noms :** sections `## Ne JAMAIS faire` / `## Toujours faire` / `## Préférences de travail` identiques entre le template `CLAUDE.md` (Task 3) et le gabarit du reçu (Task 4). Les 7 étapes numérotées sont continues et sans collision. Le nom `fin-session` est constant.
