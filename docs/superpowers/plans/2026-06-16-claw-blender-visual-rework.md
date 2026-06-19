# Refonte visuelle Blender des 120 pinces — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remplacer le châssis procédural en blocs des 120 pinces par un rig maître modélisé dans Blender (grappin orange-peel scrapyard), importé en MeshParts, décliné paramétriquement par rareté+rang, animé en Motor6D, et propagé à tous les visuels (plots, roulette, index, previews).

**Architecture:** Un builder unique `ReplicatedStorage.Shared.Config.ClawModel.build` assemble des MeshParts clonés depuis des templates nommés dans `ReplicatedStorage.Assets.ClawMeshes`. `PlotService.makeUFOModel` devient un délégué. La rareté (`materialBand`) et le rang (finition) ajoutent des ornements procéduraux par-dessus le mesh. Le contrat de noms/tags/Motor6D est strictement préservé.

**Tech Stack:** Blender (bpy procédural) · addon « Upload to Roblox » (Open Cloud) · Roblox Studio MCP (`execute_luau`, `script_read`, `inspect_instance`, `screen_capture`, `get_studio_state`) · Blender MCP (`execute_blender_code`, `get_viewport_screenshot`) · Luau.

**Conventions de ce projet (IMPORTANT, lire avant de commencer) :**
- Le dépôt **n'est pas un git repo**. Les « commits » classiques n'existent pas. Le **checkpoint = `Ctrl+S` dans Studio** (sauvegarde `build.rbxlx`, source de vérité) + **read-back de vérification**. Chaque tâche se termine par un step de sauvegarde+vérif au lieu d'un `git commit`.
- Studio peut être en **Play** : repasser en **Edit** avant toute édition (gotcha : Play compile un snapshot périmé juste après un edit ; `multi_edit` peut no-op silencieusement → toujours vérifier par un `script_read`/`inspect_instance` séparé).
- Les « tests » ici sont surtout : **assertions Luau exécutables** via `execute_luau` (contrat de modèle) + **vérification visuelle** (screenshots Blender/Studio) + **read-back**. Ce ne sont pas des tests unitaires pytest ; le plan le dit explicitement où c'est le cas.
- Le `build.rbxlx` sur disque (22 Mo) peut être **en retard** sur le DM Studio en cours (certaines features sous-projet C sont en Edit DM non sauvé). **Le DM Studio live fait foi** pour l'exécution ; lire le DM via MCP, pas seulement le fichier disque.

**Référence spec :** `docs/superpowers/specs/2026-06-16-claw-blender-visual-rework-design.md`

**⚠️ CORRECTIONS post-recon (Phase 0, faites le 2026-06-16 — priment sur le reste du plan) :**
- **Chemin `ClawModel` = `ReplicatedStorage.Shared.ClawModel`** (PAS `…Config.ClawModel`). Toutes les tasks qui require/éditent ClawModel utilisent ce chemin.
- **`IndexController` (`StarterPlayer…Client.Controllers.IndexController`) appelle DÉJÀ `ClawModel.build(def,0,CFrame.new())`** dans `viewport()` (WorldModel d'un ViewportFrame). ⇒ Task 13 « index » = **vérification seule**, aucune édition.
- **`CatchFXController` ne lit PAS le `fxTier` de la pince** : le climax de catch est piloté par la rareté du **scrap** (`Rarities.get(it.rarity).order`), pas par la pince. Le `fxTier` 6/7 n'alimente que l'**aura idle** construite dans `ClawModel` (`PointLight` Range=14+fxTier*2 ; `ParticleEmitter` Rate=5+fxTier*5) qui **scale déjà en continu** → **aucun plafond à lever**. ⇒ **Task 16 Step 1 (fxTier 6/7) est SANS OBJET** ; Task 16 se limite à **vérifier** que l'animation existante fonctionne avec les nouveaux meshes (le contrat `ArmPivot`/`Claw`/`JawMotor` C0/C1/`RestCF`/`OpenAngle`=rad(28) doit être préservé à l'identique) + polish optionnel des vérins.
- **L'animation de catch est déjà conforme au spec** (`animateClaw`: plonge `DIG_ANGLE=rad(16)` sous `RestCF`, `setJaws(JAW_OPEN)` en descendant, `setJaws(JAW_CLOSED)` au point bas, jitter, remontée `Quint/Out` sans overshoot). Idle: `animateWorld` remet `JawMotor.Transform=JAW_CLOSED` et applique un `sway` à `ArmPivot` via `RestCF`. **Ne rien casser de ce contrat.**
- **Toutes les éditions passent par le DM Studio LIVE via MCP** (`script_read`/`multi_edit`/`execute_luau`), jamais par le fichier `build.rbxlx` directement (le disque est en retard sur le DM : `IndexController`/`ScrapIcons`/`IndexRewards` existent live mais pas sur disque). Persistance = `Ctrl+S` (déclenché par l'utilisateur ou via Studio).

**Cibles de dimensions (S=1) lues dans le builder actuel** (les MeshParts seront modélisés à ces proportions, centrés sur leur origine ; le builder réglera `MeshPart.Size = coeff * S`) :
- `baseL = 6.5`, `baseW = 6.0`, `trackH = 1.7`, `deckTop = trackH + 1.0 = 2.7`, `cabH = 4.0`, `cabX = -baseL*0.14 = -0.91`.
- Cab : `(baseL*0.6, cabH, baseW*0.78) = (3.9, 4.0, 4.68)`.
- Counterweight : `(1.5, cabH*0.82, baseW*0.82) = (1.5, 3.28, 4.92)`.
- Boom : longueur `|elbow| = |(5.0,3.2,0)| ≈ 5.93`, épaisseur `boomThick ≈ 1.35`.
- Stick : de `elbow(5.0,3.2)` à `grapPos(7.6,-2.0)`, longueur `≈ 5.95`, épaisseur `≈ 1.107`.
- Claw (moyeu) : `(2.4, 1.5, 2.4)`.
- ClawJaw (tine) : `(0.5, 2.4, 0.85)`.
- ClawTip : `(0.55, 0.8, 0.9)`.
- Base (crawler+deck) : enveloppe `≈ (7.7, 2.7, 6.2)`.

---

## File Structure

- **Blender** (créés sous `Elements_Blender/claw_rig/`) :
  - `claw_rig_build.py` — script bpy procédural, un objet par zone, origines centrées, dims = cibles S=1.
  - `claw_rig_export.py` — sélection + export OBJ/GLB par objet vers `Elements_Blender/claw_rig/export/`.
- **Roblox (dans `build.rbxlx` / DM Studio)** :
  - `ReplicatedStorage.Assets.ClawMeshes` (NOUVEAU Folder) — MeshPart templates nommés.
  - `ReplicatedStorage.Shared.Config.ClawModel` (MODIFIÉ) — builder unique mesh-based.
  - `ServerScriptService.Server.Services.PlotService` (MODIFIÉ) — `makeUFOModel` → délégué ; re-bake PlotPreviews.
  - `StarterPlayer.StarterPlayerScripts.Client.Controllers.CatchFXController` (MODIFIÉ) — `fxTier` 6/7 + polish anim.
  - (Conditionnel) contrôleur d'index / collection s'il existe dans le DM live — router ses previews sur `ClawModel.build`.
- **Docs** : ce plan + le spec.

---

## Phase 0 — Préflight

### Task 0: Préflight & lecture de l'existant

**Files:**
- Read: `ReplicatedStorage…ClawModel` (build.rbxlx:593608-593858)
- Read: `ServerScriptService…PlotService.makeUFOModel` (build.rbxlx:619017-619255, 619770-619900)
- Read: `StarterPlayer…CatchFXController`

- [ ] **Step 1: Confirmer Studio connecté + en Edit**

Run (MCP): `mcp__Roblox_Studio__get_studio_state`
Expected: un Studio listé ; `Mode` ≠ `Play`. Si `Play` → `mcp__Roblox_Studio__start_stop_play` pour arrêter, re-vérifier `Mode` = Edit.

- [ ] **Step 2: Confirmer Blender connecté**

Run (MCP): `mcp__blender__get_scene_info`
Expected: réponse scène (pas d'erreur de connexion). Si erreur → demander à l'utilisateur d'ouvrir Blender + activer l'addon MCP (STOP, question utilisateur).

- [ ] **Step 3: Lire CatchFXController et repérer la gestion fxTier + la séquence d'anim**

Run (MCP): `mcp__Roblox_Studio__script_search` query `CatchFX` puis `script_read` du résultat.
Expected: noter comment il fait tourner `ArmPivot` (RestCF), pilote `JawMotor.Transform`, et son `fxTier` max actuel (probablement plafonné < 6).

- [ ] **Step 4: Inspecter le DM live pour un builder de previews d'index/collection**

Run (MCP): `mcp__Roblox_Studio__script_grep` pattern `ViewportFrame|WorldModel|IndexController|ScrapIcons|makeUFOModel|ClawModel`.
Expected: liste des scripts qui construisent des previews de pince. **Noter** lesquels construisent un modèle de pince (à router sur `ClawModel.build`). Si aucun → l'index n'existe pas encore dans le DM live (sous-projet C non câblé) ⇒ Task 13 ne touche que la roulette.

- [ ] **Step 5: Confirmer l'absence de `ReplicatedStorage.Assets.ClawMeshes`**

Run (MCP): `mcp__Roblox_Studio__inspect_instance` path `ReplicatedStorage.Assets`.
Expected: pas de `ClawMeshes` (sera créé Task 7). Si `Assets` n'existe pas, on le créera.

- [ ] **Step 6: Checkpoint** — pas d'édition ; consigner les chemins/constantes trouvés dans une note de session.

---

## Phase 1 — Rig maître Blender

> Chaque objet est modélisé **centré sur l'origine du monde puis déplacé**, mais son **origine d'objet** est remise à son centre géométrique avant export (`origin_set` CENTER_OF_MASS/BOUNDS). Dimensions = cibles S=1 ci-dessus. Look : cartoon-stylisé (formes nettes, biseaux légers), pas de détail micro inutile. Budget total ~6-9k tris.

### Task 1: Scène + helpers + base chenillée (`Base`)

**Files:**
- Create: `Elements_Blender/claw_rig/claw_rig_build.py`

- [ ] **Step 1: Reset scène + helpers + objet `Base`**

Run (MCP `mcp__blender__execute_blender_code`) avec ce code (et l'écrire aussi dans le fichier) :

```python
import bpy, bmesh, math
from mathutils import Vector

# --- reset ---
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
for m in list(bpy.data.meshes): bpy.data.meshes.remove(m)

def beveled_box(name, sx, sy, sz, bevel=0.06, segs=2):
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    o = bpy.context.active_object; o.name = name
    o.scale = (sx, sy, sz)
    bpy.ops.object.transform_apply(scale=True)
    m = o.modifiers.new("bev", 'BEVEL'); m.width = bevel; m.segments = segs; m.limit_method = 'ANGLE'
    bpy.ops.object.modifier_apply(modifier=m.name)
    return o

def cyl(name, r, h, axis='Z', verts=20):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=h, vertices=verts)
    o = bpy.context.active_object; o.name = name
    if axis == 'X': o.rotation_euler = (0, math.radians(90), 0)
    elif axis == 'Y': o.rotation_euler = (math.radians(90), 0, 0)
    bpy.ops.object.transform_apply(rotation=True)
    return o

def join(objs, name):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    objs[0].name = name
    return objs[0]

def center_origin(o):
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True)
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
    o.location = (0,0,0)

# === BASE: crawler tracks + deck, enveloppe ~ (7.7, 2.7, 6.2) en (X,Y,Z) Roblox.
# NB: Blender Z = up = Roblox Y. On modélise en Blender (Z up) puis l'export mappe Y/Z.
deck = beveled_box("deck", 6.5, 1.0, 6.0)        # X long, Z up=1.0, Y depth->modeled as Blender Y
deck.location = (0, 0, 1.6)
tracks = []
for s in (-1, 1):
    t = beveled_box("trk", 7.5, 1.7, 1.7, bevel=0.12)
    t.location = (0, s*2.1, 0.85)
    tracks.append(t)
    for w in (-1, 0, 1):
        wheel = cyl("wh", 0.55, 1.0, axis='Y', verts=16)
        wheel.location = (w*2.2, s*2.1, 0.7)
        tracks.append(wheel)
base = join([deck] + tracks, "Base")
center_origin(base)
```

- [ ] **Step 2: Screenshot de contrôle**

Run (MCP): `mcp__blender__get_viewport_screenshot`
Expected: une base chenillée trapue, deux chenilles + roues, pont au-dessus. Itérer les dimensions si la silhouette ne lit pas (ajuster et relancer Step 1).

- [ ] **Step 3: Checkpoint** — sauver le bloc dans `claw_rig_build.py` (section BASE).

### Task 2: Cabine + contrepoids (`Cab`, `Counterweight`)

**Files:**
- Modify: `Elements_Blender/claw_rig/claw_rig_build.py`

- [ ] **Step 1: Construire `Cab` et `Counterweight`**

Run (MCP `execute_blender_code`), append au script :

```python
# === CAB (3.9 x 4.0 x 4.68) avec toit incliné + bandeau + bloc vitre encastré
cab_body = beveled_box("cab_body", 3.9, 4.0, 4.68, bevel=0.12)
# pan coupé pour le toit incliné (face avant +X plus basse)
bm = bmesh.new(); bm.from_mesh(cab_body.data)
for v in bm.verts:
    if v.co.x > 0 and v.co.z > 0.6: v.co.z -= 0.8 * (v.co.x/1.95)
bm.to_mesh(cab_body.data); bm.free()
trim = beveled_box("cab_trim", 4.0, 0.5, 4.78, bevel=0.05); trim.location=(0,0,1.85)  # bandeau haut
glass = beveled_box("cab_glass", 0.35, 1.9, 2.4, bevel=0.03); glass.location=(1.7,0.5,0.2) # vitre encastrée (relief 0.03)
cab = join([cab_body, trim, glass], "Cab")
center_origin(cab)

cw = beveled_box("Counterweight", 1.5, 3.28, 4.92, bevel=0.15)
# nervures du contrepoids (relief, anti-coplanaire >0.03)
for k in (-1,0,1):
    rib = beveled_box("rib", 1.56, 0.45, 4.0, bevel=0.04); rib.location=(0, k*1.0, 0)
    cw = join([cw, rib], "Counterweight")
center_origin(cw)
```

- [ ] **Step 2: Screenshot + itérer** (`get_viewport_screenshot`). Toit incliné lisible, vitre en creux, nervures en relief.
- [ ] **Step 3: Checkpoint** — append au fichier.

### Task 3: Bras articulé (`Boom`, `Stick`, `Elbow`)

**Files:**
- Modify: `Elements_Blender/claw_rig/claw_rig_build.py`

- [ ] **Step 1: Construire les segments de bras (modélisés à plat selon l'axe X, longueur=axe X)**

> Le builder Roblox oriente chaque segment via `beam()` (rotation Z). On modélise donc chaque segment **aligné sur +X**, longueur sur X, section sur Y/Z, centré.

Run (MCP `execute_blender_code`), append :

```python
# Boom: longueur ~5.93, section ~1.35. Profil en I léger (creux latéraux pour le style).
boom = beveled_box("Boom", 5.93, 1.35, 1.35, bevel=0.10)
for s in (-1,1):
    notch = beveled_box("ntch", 4.6, 0.5, 0.6); notch.location=(0, s*0.55, 0)
    # creuse via boolean difference pour des flasques
    mod = boom.modifiers.new("b",'BOOLEAN'); mod.operation='DIFFERENCE'; mod.object=notch
    bpy.context.view_layer.objects.active = boom; bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(notch)
center_origin(boom)

stick = beveled_box("Stick", 5.95, 1.107, 1.107, bevel=0.09); center_origin(stick)
elbow = cyl("Elbow", 0.9, 1.65, axis='Y', verts=20); center_origin(elbow)
```

- [ ] **Step 2: Screenshot + itérer**. Segments lisibles, biseautés, flasques sur le boom.
- [ ] **Step 3: Checkpoint** — append.

### Task 4: Tête grappin + griffe orange-peel (`ClawHub`, `Jaw`, `Tip`)

**Files:**
- Modify: `Elements_Blender/claw_rig/claw_rig_build.py`

- [ ] **Step 1: Moyeu grappin + UNE griffe radiale + pointe**

> La griffe `Jaw` est modélisée **comme une tine de l'anneau d'origine** : centrée sur la cible (0.5, 2.4, 0.85), courbée vers l'intérieur (profil orange-peel). Elle sera instanciée N fois par le builder (rotation autour de l'axe vertical du moyeu) — donc modélisée **une seule fois**, orientée « pendante » (long axe = Y/vertical).

Run (MCP `execute_blender_code`), append :

```python
# Moyeu (2.4 x 1.5 x 2.4) cylindrique + collerette
hub = cyl("ClawHub", 1.15, 1.5, axis='Z', verts=24)
cap = cyl("cap", 0.8, 1.0, axis='Z', verts=20); cap.location=(0,0,0.9)
knuck = cyl("kn", 0.65, 0.7, axis='Z', verts=18); knuck.location=(0,0,-0.4)
hub = join([hub, cap, knuck], "ClawHub"); center_origin(hub)

# Griffe orange-peel: lame incurvée. Boîte (0.5 x 2.4 x 0.85) puis courbure via Simple Deform BEND.
jaw = beveled_box("Jaw", 0.5, 0.85, 2.4, bevel=0.06)   # long axe = Z (Blender up) -> deviendra Y Roblox
bend = jaw.modifiers.new("bend",'SIMPLE_DEFORM'); bend.deform_method='BEND'; bend.angle=math.radians(55); bend.deform_axis='X'
bpy.context.view_layer.objects.active = jaw; bpy.ops.object.modifier_apply(modifier="bend")
# arête interne (griffe) effilée vers le bas
bm = bmesh.new(); bm.from_mesh(jaw.data)
for v in bm.verts:
    if v.co.z < -0.9: v.co.x *= 0.45; v.co.y *= 0.55
bm.to_mesh(jaw.data); bm.free()
center_origin(jaw)

# Pointe (0.55 x 0.8 x 0.9) griffue
tip = beveled_box("Tip", 0.55, 0.9, 0.8, bevel=0.05)
bm = bmesh.new(); bm.from_mesh(tip.data)
for v in bm.verts:
    if v.co.z < 0: v.co.x *= 0.3; v.co.y *= 0.4
bm.to_mesh(tip.data); bm.free()
center_origin(tip)
```

- [ ] **Step 2: Screenshot + itérer** sur la courbure de la griffe (doit évoquer la photo : lame épaisse incurvée se refermant en sphère).
- [ ] **Step 3: Vérifier le compte de tris**

Run (MCP `execute_blender_code`):
```python
import bpy
tot = sum(len(o.data.polygons) for o in bpy.data.objects if o.type=='MESH')
print("TRIS_APPROX", tot*2)  # quads -> tris approx
```
Expected: `TRIS_APPROX` total raisonnable (objectif assemblage < ~9000 ; une machine instancie 1 base+cab+cw+boom+stick+elbow+hub + N×(jaw+tip)). Si trop élevé, baisser `verts`/`segments` et relancer.

- [ ] **Step 4: Checkpoint** — append. Le script complet construit les 9 objets nommés : `Base, Cab, Counterweight, Boom, Stick, Elbow, ClawHub, Jaw, Tip`.

### Task 5: Validation des origines & dimensions

**Files:**
- Modify: `Elements_Blender/claw_rig/claw_rig_build.py`

- [ ] **Step 1: Vérifier dimensions & origines de chaque objet**

Run (MCP `execute_blender_code`):
```python
import bpy
for n in ["Base","Cab","Counterweight","Boom","Stick","Elbow","ClawHub","Jaw","Tip"]:
    o = bpy.data.objects.get(n)
    print(n, "dim", [round(x,2) for x in o.dimensions], "loc", [round(x,2) for x in o.location])
```
Expected: chaque `loc ≈ (0,0,0)` (origine centrée), `dim` proche des cibles S=1 (cf. en-tête). Corriger sinon.

- [ ] **Step 2: Screenshot d'ensemble** (poser temporairement les objets en position d'assemblage pour juger la silhouette globale, puis les re-séparer/centrer). Valider « ça ressemble à la photo ».
- [ ] **Step 3: Checkpoint** — sauver `claw_rig_build.py` final.

### Task 6: Export + upload vers Roblox

**Files:**
- Create: `Elements_Blender/claw_rig/claw_rig_export.py`
- Create: `Elements_Blender/claw_rig/export/*.obj`

- [ ] **Step 1: Exporter chaque objet centré en OBJ**

Run (MCP `execute_blender_code`):
```python
import bpy, os
out = bpy.path.abspath("//export"); os.makedirs(out, exist_ok=True)
for n in ["Base","Cab","Counterweight","Boom","Stick","Elbow","ClawHub","Jaw","Tip"]:
    o = bpy.data.objects.get(n)
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True)
    bpy.context.view_layer.objects.active = o
    bpy.ops.wm.obj_export(filepath=os.path.join(out, n+".obj"),
        export_selected_objects=True, export_materials=False,
        forward_axis='NEGATIVE_Z', up_axis='Y')  # mapping Blender Z-up -> Roblox Y-up
```
Expected: 9 fichiers `.obj` dans `export/`.

- [ ] **Step 2: Uploader via l'addon « Upload to Roblox » (Open Cloud)**

Suivre le pipeline validé (cf. memory `blender-to-roblox-pipeline`) : sélectionner les objets, lancer l'upload (rbx.upload, async), récupérer les **asset IDs MeshPart** (ou un Model d'assets). Consigner chaque ID dans une table `name -> assetId`.
Expected: 9 asset IDs (ou un Model contenant 9 MeshParts nommés).

> **Edge case :** si l'addon n'est pas configuré (clé Open Cloud), STOP et demander à l'utilisateur de la fournir.

- [ ] **Step 3: Checkpoint** — sauver `claw_rig_export.py` + la table `name->assetId` dans la note de session.

---

## Phase 2 — Templates MeshPart dans Roblox

### Task 7: Créer `ReplicatedStorage.Assets.ClawMeshes`

**Files:**
- Modify: DM Studio (Edit) → `ReplicatedStorage.Assets.ClawMeshes`

- [ ] **Step 1: Importer les meshes et créer les templates nommés**

Run (MCP `execute_luau`, en Edit) — adapter les `assetId` de la table Task 6 :
```lua
local RS = game:GetService("ReplicatedStorage")
local assets = RS:FindFirstChild("Assets") or Instance.new("Folder")
assets.Name = "Assets"; assets.Parent = RS
local folder = assets:FindFirstChild("ClawMeshes") or Instance.new("Folder")
folder.Name = "ClawMeshes"; folder.Parent = assets
local IDS = {
  Base="rbxassetid://AAA", Cab="rbxassetid://BBB", Counterweight="rbxassetid://CCC",
  Boom="rbxassetid://DDD", Stick="rbxassetid://EEE", Elbow="rbxassetid://FFF",
  ClawHub="rbxassetid://GGG", Jaw="rbxassetid://HHH", Tip="rbxassetid://III",
}
for name, id in pairs(IDS) do
  if not folder:FindFirstChild(name) then
    local mp = Instance.new("MeshPart")
    mp.Name = name; mp.MeshId = id
    mp.Anchored = true; mp.CanCollide = false; mp.CanQuery = false
    mp.Parent = folder
  end
end
for _, mp in ipairs(folder:GetChildren()) do print(mp.Name, mp.Size) end
```
Expected: 9 MeshParts ; chaque `Size` affichée = bbox naturelle (Roblox recentre sur bbox). **Noter** les Sizes natives.

> **Alternative** si l'upload a produit un **Model** : l'insérer via `InsertService:LoadAsset(modelId)` une fois en Edit, déplacer ses MeshParts nommés dans `ClawMeshes`, supprimer le reste.

- [ ] **Step 2: Vérifier visuellement les templates**

Run (MCP): `screen_capture` après avoir temporairement parenté une copie dans Workspace, ou `inspect_instance` sur `ReplicatedStorage.Assets.ClawMeshes`.
Expected: 9 meshes présents, MeshId non vide, dimensions cohérentes.

- [ ] **Step 3: Checkpoint** — `Ctrl+S` (sauver `build.rbxlx`). Vérifier par `inspect_instance` que `ClawMeshes` a 9 enfants.

---

## Phase 3 — Réécriture de `ClawModel.build`

### Task 8: Helper de clone mesh + assemblage structurel mesh-based

**Files:**
- Modify: `ReplicatedStorage…ClawModel` (build.rbxlx:593617-593855)

> Objectif : remplacer les **parts structurels hero** par des MeshParts clonés (`Base, Cab, Counterweight, Boom, Stick, Elbow, Claw(=ClawHub), ClawJaw(=Jaw), ClawTip(=Tip)`), en gardant **exactement** les mêmes CFrames, weld, Motor6D, attributs et noms de contrat. Les petits greebles (Skirt, Rail, RailPost, Antenna, Vent, Headlight, Toolbox, Hose, Piston, WarnLight, Glow…) restent des `Part` primitifs comme aujourd'hui. Si un template manque, **fallback** sur l'ancienne primitive (robustesse).

- [ ] **Step 1: Ajouter le require + helper `meshClone` en tête de `ClawModel`**

Insérer après `local STEEL_DARK = ...` (≈ build.rbxlx:593615) :
```lua
local RS = game:GetService("ReplicatedStorage")
local MESHES = RS:FindFirstChild("Assets") and RS.Assets:FindFirstChild("ClawMeshes")

-- Clone a named mesh template, scaled to `size` (same Vector3 the old Part used), placed at world cf.
-- Falls back to a primitive Part of the given shape when the template is missing (robust in tests/Edit).
local function meshPart(model, BASE, tmplName, partName, size, color, cf, material, shape)
	local tmpl = MESHES and MESHES:FindFirstChild(tmplName)
	local p
	if tmpl and tmpl:IsA("MeshPart") then
		p = tmpl:Clone()
	else
		p = Instance.new("Part"); if shape then p.Shape = shape end
	end
	p.Name = partName
	p.Anchored = true; p.CanCollide = false
	p.Size = size; p.Color = color; p.Material = material or Enum.Material.Metal
	p.TopSurface = Enum.SurfaceType.Smooth; p.BottomSurface = Enum.SurfaceType.Smooth
	p.CFrame = BASE * cf
	p.Parent = model
	return p
end
```

- [ ] **Step 2: Remplacer la base, le pont, la cabine, le contrepoids par des meshes**

Dans `ClawModel.build`, remplacer le bloc « Crawler base » + `Deck`/`Skirt` + `Cab`/`CabTrim`/`CabGlass`/`Counterweight` (build.rbxlx:593663-593689) par :
```lua
-- Base chenillée (un seul mesh hero ; Skirt/Glow restent procéduraux).
local baseEnv = Vector3.new(baseL + 1.2 * S, deckTop, baseW + 0.2 * S)
meshPart(model, BASE, "Base", "Base", baseEnv, STEEL, CFrame.new(0, deckTop/2, 0), Enum.Material.DiamondPlate)
part("Skirt", Vector3.new(baseL + 0.4 * S, 0.7 * S, baseW + 0.2 * S), HAZ_Y, CFrame.new(0, trackH + 0.35 * S, 0), Enum.Material.SmoothPlastic)
part("Glow", Vector3.new(baseL + 0.3, 0.16, baseW + 0.3), glowC, CFrame.new(0, trackH + 0.72 * S, 0), Enum.Material.Neon)

-- Cabine (mesh) + contrepoids (mesh). La couleur de rareté est portée par la cabine.
meshPart(model, BASE, "Cab", "Cab", Vector3.new(baseL * 0.6, cabH, baseW * 0.78), accent, CFrame.new(cabX, cabCY, 0), Enum.Material.SmoothPlastic)
part("CabTrim", Vector3.new(baseL * 0.64, 0.5 * S, baseW * 0.82), trimC, CFrame.new(cabX, deckTop + cabH - 0.25 * S, 0), Enum.Material.Metal)
meshPart(model, BASE, "Counterweight", "Counterweight", Vector3.new(1.5 * S, cabH * 0.82, baseW * 0.82), STEEL_DARK, CFrame.new(cabX - baseL * 0.32, deckTop + cabH * 0.41, 0), Enum.Material.Metal)
part("ExhaustPipe", Vector3.new(0.5 * S, 1.6 * S, 0.5 * S), HAZ_K, CFrame.new(cabX - baseL * 0.18, deckTop + cabH + 0.5 * S, baseW * 0.3), Enum.Material.Metal)
```
> On **supprime** les anciens `Track`/`TrackPlate`/`Wheel`/`Deck`/`CabGlass` séparés (intégrés au mesh `Base`/`Cab`). Garder les greebles `WarnBase/WarnLight/Panel/Rail*/CWBand/Headlight/Vent/Antenna/Toolbox` tels quels (build.rbxlx:593691-593719).

- [ ] **Step 3: Remplacer le bras (`Boom/Stick/Elbow`) par des meshes welded**

Remplacer `beam("Boom"…)`, `beam("Stick"…)`, `welded("Elbow"…)` (build.rbxlx:593760-593766) par des MeshParts welded, en réutilisant la géométrie d'orientation de `beam` mais via `meshPart` + weld manuel :
```lua
local function meshBeam(tmpl, name, color, p0, p1, thick, mat)
	local d = p1 - p0; local len = d.Magnitude; local mid = (p0 + p1) / 2
	local ang = math.atan2(d.Y, d.X)
	local p = meshPart(model, BASE, tmpl, name, Vector3.new(len, thick, thick), color, pivotCF * (CFrame.new(mid) * CFrame.Angles(0, 0, ang)), mat or Enum.Material.SmoothPlastic)
	p.Anchored = false; p.Massless = true
	local w = Instance.new("WeldConstraint"); w.Part0 = pivot; w.Part1 = p; w.Parent = p
	return p
end
meshBeam("Boom", "Boom", BOOM, Vector3.new(0,0,0), elbow, boomThick)
beam("BoomTrim", HAZ_Y, Vector3.new(0, 0, boomThick / 2 + 0.06), elbow + Vector3.new(0, 0, boomThick / 2 + 0.06), boomThick * 0.32)
meshBeam("Stick", "Stick", BOOM, elbow, grapPos, boomThick * 0.82)
beam("Piston", STEEL_LIGHT, Vector3.new(0.5 * S, -0.9 * S, 0), elbow + Vector3.new(-0.2 * S, -0.9 * S, 0), 0.5 * S, Enum.Material.Metal)
beam("Hose", Color3.fromRGB(28,30,36), Vector3.new(0.3*S,-0.45*S,0.32*S), elbow + Vector3.new(-0.25*S,0.25*S,0.32*S), 0.18*S, Enum.Material.Metal)
beam("Hose", Color3.fromRGB(28,30,36), Vector3.new(0.3*S,-0.45*S,-0.32*S), elbow + Vector3.new(-0.25*S,0.25*S,-0.32*S), 0.18*S, Enum.Material.Metal)
do
	local p = meshPart(model, BASE, "Elbow", "Elbow", Vector3.new(1.5*S,1.5*S,boomThick+0.3), STEEL_DARK, pivotCF * CFrame.new(elbow), Enum.Material.Metal)
	p.Anchored=false; p.Massless=true
	local w=Instance.new("WeldConstraint"); w.Part0=pivot; w.Part1=p; w.Parent=p
end
```
> `meshBeam`/le bloc Elbow doivent être définis **après** `pivot`/`pivotCF` (build.rbxlx:593729-593744). Garder `ShoulderHub` (welded primitive) tel quel.

- [ ] **Step 4: Remplacer le moyeu grappin + les griffes + pointes par des meshes**

Remplacer le bloc `Claw`/`GrappleCap`/`Knuckle` + `hingedJaw` (build.rbxlx:593768-593811). Le `Claw` devient un mesh `ClawHub` renommé `Claw` (Part0 du Motor6D), les tines clonent `Jaw`→`ClawJaw`, les pointes `Tip`→`ClawTip` :
```lua
local clawLocal = CFrame.new(grapPos)
local claw = meshPart(model, BASE, "ClawHub", "Claw", Vector3.new(2.4*S,1.5*S,2.4*S), STEEL, pivotCF * clawLocal, Enum.Material.Metal)
claw.Anchored=false; claw.Massless=true
do local w=Instance.new("WeldConstraint"); w.Part0=pivot; w.Part1=claw; w.Parent=claw end
welded("GrappleCap", Vector3.new(1.6*S,1.0*S,1.6*S), STEEL_DARK, clawLocal * CFrame.new(0,0.9*S,0), Enum.Material.Metal)
welded("Glow", Vector3.new(0.42*S,2.0*S,2.0*S), glowC, clawLocal * CFrame.new(0,1.5*S,0) * CFrame.Angles(0,0,math.rad(90)), Enum.Material.Neon, Enum.PartType.Cylinder)
welded("Knuckle", Vector3.new(1.3*S,0.7*S,1.3*S), STEEL_LIGHT, clawLocal * CFrame.new(0,-0.4*S,0), Enum.Material.Metal)

local tineN = (arch == "force") and 6 or (arch == "cadence") and 4 or 5
local function hingedJaw(a2)
	local jawLocal = clawLocal * CFrame.Angles(0, a2, 0) * CFrame.new(1.1*S, -1.05*S, 0)
	local hinge = clawLocal * CFrame.Angles(0, a2, 0) * CFrame.new(1.0*S, 0.15*S, 0)
	local jaw = meshPart(model, BASE, "Jaw", "ClawJaw", Vector3.new(0.5*S,2.4*S,0.85*S), accent, pivotCF * jawLocal, Enum.Material.Metal)
	jaw.Anchored=false; jaw.Massless=true
	jaw:SetAttribute("OpenAngle", math.rad(28))
	local m = Instance.new("Motor6D"); m.Name="JawMotor"; m.Part0=claw; m.Part1=jaw
	m.C0 = clawLocal:Inverse() * hinge
	m.C1 = jawLocal:Inverse() * hinge
	m.Parent = claw
	local tipLocal = clawLocal * CFrame.Angles(0, a2, 0) * CFrame.new(1.85*S, -2.1*S, 0) * CFrame.Angles(0,0,math.rad(58))
	local tip = meshPart(model, BASE, "Tip", "ClawTip", Vector3.new(0.55*S,0.8*S,0.9*S), STEEL_LIGHT, pivotCF * tipLocal, Enum.Material.Metal)
	tip.Anchored=false; tip.Massless=true
	local w = Instance.new("WeldConstraint"); w.Part0=jaw; w.Part1=tip; w.Parent=tip
end
for j = 0, tineN - 1 do hingedJaw((math.pi * 2 / tineN) * j) end
```

- [ ] **Step 5: Écrire l'édition via `multi_edit` puis VÉRIFIER par read-back**

Run (MCP): `mcp__Roblox_Studio__multi_edit` sur le script `ClawModel`. Puis **OBLIGATOIRE** `mcp__Roblox_Studio__script_read` pour confirmer que les remplacements ont bien pris (multi_edit peut no-op silencieusement).
Expected: le corps contient `meshPart(... "Base" ...)`, `meshBeam`, `"ClawHub", "Claw"`, et plus aucun `part("Track"…)`/`beam("Boom"…)`.

- [ ] **Step 6: Checkpoint** — `Ctrl+S`. (Test exécutable en Task 11.)

### Task 9: Couche `materialBand` (entre raretés)

**Files:**
- Modify: `ReplicatedStorage…ClawModel`

- [ ] **Step 1: Lire `materialBand` + appliquer la finition de surface par bande**

Après le bloc `local fxTier = ...` (build.rbxlx:593629), ajouter :
```lua
local band = ufoDef.materialBand or "paint"
-- Matériau de coque + reflets par bande (cartoon : pas de texture image).
local BAND_MAT = {
	paint = Enum.Material.SmoothPlastic, metal = Enum.Material.Metal,
	energized = Enum.Material.Metal, crystal = Enum.Material.Glass,
	warp = Enum.Material.Neon, prism = Enum.Material.Neon,
}
local shellMat = BAND_MAT[band] or Enum.Material.SmoothPlastic
```

- [ ] **Step 2: Ajouter les ornements de bande (parts procédurales, anti-z-fight)**

Juste avant `model:AddTag("UFOCatcher")` (build.rbxlx:593853), ajouter un helper d'ornements par bande, monté en **relief ≥0.03** sur la cabine/le moyeu :
```lua
local STAND = 0.05 * S  -- standoff anti-z-fight
if band == "metal" or band == "energized" then
	-- liseré Neon en relief sur le bandeau de cabine
	part("BandEdge", Vector3.new(baseL * 0.66, 0.14 * S, baseW * 0.84), glowC, CFrame.new(cabX, deckTop + cabH - 0.25 * S, 0) + Vector3.new(0, 0, 0), Enum.Material.Neon)
end
if band == "energized" then
	for s = -1, 1, 2 do
		part("EdgeRunner", Vector3.new(baseL * 0.6, 0.10 * S, 0.10 * S), glowC, CFrame.new(cabX, cabCY + 1.4 * S, s * (baseW * 0.39 + STAND)), Enum.Material.Neon)
	end
end
if band == "crystal" then
	for k = 0, 3 do
		local a = math.rad(90 * k)
		local insert = part("CrystalInsert", Vector3.new(0.5 * S, 1.6 * S, 0.5 * S), glowC, CFrame.new(cabX, cabCY, 0) * CFrame.Angles(0, a, 0) * CFrame.new(baseW * 0.40 + STAND, 0, 0), Enum.Material.Glass)
		insert.Transparency = 0.35
	end
end
if band == "warp" or band == "prism" then
	-- aura coque distincte (rayon différent du halo de griffe -> pas de coplanaire)
	local aura2 = part("Aura", Vector3.new(baseL * 0.7, cabH * 1.1, baseW * 0.9), glowC, CFrame.new(cabX, cabCY, 0), Enum.Material.ForceField)
	aura2.Transparency = 0.6; aura2.CanQuery = false; aura2.CanCollide = false
end
```

- [ ] **Step 3: Appliquer `shellMat` à la cabine** — dans Task 8 Step 2, remplacer le `Enum.Material.SmoothPlastic` du `meshPart("Cab"…)` par `shellMat`. (Édition de ligne ; vérifier par read-back.)

- [ ] **Step 4: `multi_edit` + read-back + `Ctrl+S`.**

### Task 10: Échelle de finition par rang (au sein d'une rareté)

**Files:**
- Modify: `ReplicatedStorage…ClawModel`

- [ ] **Step 1: Lire le rang + dériver le niveau de finition**

Après le bloc Task 9 Step 1, ajouter :
```lua
local rank = ufoDef.rank or 1                 -- 1..10
local finish = (rank - 1) / 9                 -- 0..1
local polishMat = (rank >= 9 and Enum.Material.Foil)
	or (rank >= 6 and Enum.Material.Metal) or Enum.Material.SmoothPlastic
local trimColor = (rank >= 9 and Color3.fromRGB(255, 214, 92))      -- doré
	or (rank >= 6 and Color3.fromRGB(220, 226, 235)) or trimC        -- chrome / défaut
```

- [ ] **Step 2: Appliquer le trim de rang + greebles croissants + couronne**

Avant `model:AddTag("UFOCatcher")`, ajouter :
```lua
-- polish/trim de rang sur le bandeau
local ct = model:FindFirstChild("CabTrim"); if ct then ct.Color = trimColor; ct.Material = polishMat end
-- densité de greebles (rivets) croissante avec le rang
local rivets = math.floor(2 + finish * 8)
for i = 1, rivets do
	local a = (math.pi * 2 / rivets) * i
	part("Rivet", Vector3.new(0.16 * S, 0.16 * S, 0.16 * S), trimColor, CFrame.new(cabX, cabCY, 0) * CFrame.Angles(0, a, 0) * CFrame.new(baseW * 0.40 + 0.06 * S, (finish - 0.5) * cabH * 0.6, 0), polishMat, Enum.PartType.Ball)
end
-- fleuron rang 9, couronne rang 10 (parts procédurales, standoff)
if rank >= 9 then
	local crownN = (rank >= 10) and 8 or 1
	for k = 0, crownN - 1 do
		local a = math.rad((360 / math.max(crownN,1)) * k)
		part("Crown", Vector3.new(0.22 * S, 0.9 * S, 0.22 * S), trimColor, CFrame.new(cabX, deckTop + cabH + 0.9 * S, 0) * CFrame.Angles(0, a, 0) * CFrame.new((rank>=10) and baseW*0.16 or 0, 0, 0) * CFrame.Angles(0, 0, math.rad(12)), polishMat)
	end
end
```

- [ ] **Step 3: Halo de griffe croissant** — la part `Glow` du moyeu (Task 8 Step 4) voit sa taille modulée : remplacer `0.42*S,2.0*S,2.0*S` par `(0.42 + 0.3*finish)*S, (2.0 + 1.0*finish)*S, (2.0 + 1.0*finish)*S`.

- [ ] **Step 4: `multi_edit` + read-back + `Ctrl+S`.**

### Task 11: Test exécutable du contrat (120 défs)

**Files:**
- Test (éphémère): `execute_luau` (non sauvé dans le DM)

- [ ] **Step 1: Écrire l'assertion de contrat et la LANCER (doit échouer si un nom manque)**

Run (MCP `execute_luau`, en Edit) :
```lua
local Shared = game:GetService("ReplicatedStorage").Shared
local ClawModel = require(Shared.Config.ClawModel)
local UFOCatchers = require(Shared.Config.UFOCatchers)
local REQUIRED = {"Root","ArmPivot","Claw","ClawJaw","ClawTip","FeedbackAnchor"}
local fail = {}
local list = UFOCatchers.list
for _, def in ipairs(list) do
	local ok, model = pcall(ClawModel.build, def, 0, CFrame.new())
	if not ok then table.insert(fail, def.id.." build error: "..tostring(model)); continue end
	for _, name in ipairs(REQUIRED) do
		if not model:FindFirstChild(name, true) then table.insert(fail, def.id.." missing "..name) end
	end
	local jaws, motors = 0, 0
	for _, d in ipairs(model:GetDescendants()) do
		if d.Name == "ClawJaw" then jaws += 1 end
		if d:IsA("Motor6D") and d.Name == "JawMotor" then motors += 1 end
	end
	if jaws < 4 or jaws ~= motors then table.insert(fail, def.id.." jaws="..jaws.." motors="..motors) end
	if not model:HasTag("UFOCatcher") then table.insert(fail, def.id.." no tag") end
	model:Destroy()
end
print("BUILT", #list, "FAILURES", #fail)
for _, f in ipairs(fail) do print("FAIL", f) end
assert(#fail == 0, "contract violations: "..#fail)
```
Expected: `BUILT 120 FAILURES 0`. Si échecs → corriger `ClawModel` (Task 8-10) et relancer. **Ce test est le garde-fou de non-régression du contrat FX/anim.**

- [ ] **Step 2: Vérifier la monotonie de rendu (taille/halo) optionnelle** — non bloquant ; consigner.
- [ ] **Step 3: Checkpoint** — aucune sauvegarde (test éphémère). Passer à la convergence.

---

## Phase 4 — Convergence & propagation

### Task 12: `makeUFOModel` délègue à `ClawModel.build`

**Files:**
- Modify: `ServerScriptService…PlotService` (build.rbxlx:619017-619255 + en-tête requires)

- [ ] **Step 1: Ajouter le require de `ClawModel` en tête de PlotService**

Repérer le bloc des `require` de PlotService (via `script_read`). Ajouter :
```lua
local ClawModel = require(game:GetService("ReplicatedStorage").Shared.Config.ClawModel)
```

- [ ] **Step 2: Remplacer tout le corps de `makeUFOModel` par un délégué**

Remplacer `local function makeUFOModel(ufoDef, prestige, baseCF): Model` … `end` (build.rbxlx:619017-619255) par :
```lua
local function makeUFOModel(ufoDef, prestige, baseCF): Model
	return ClawModel.build(ufoDef, prestige, baseCF)
end
```
Garder `PlotService.makeUFOModel = makeUFOModel` (build.rbxlx:619900) inchangé.

- [ ] **Step 3: `multi_edit` + read-back** : confirmer que `makeUFOModel` ne contient plus que le `return ClawModel.build(...)` (plus aucun `part(`/`beam(` dans cette fonction).

- [ ] **Step 4: Test exécutable** — Run (MCP `execute_luau`) :
```lua
local PlotService = require(game.ServerScriptService.Server.Services.PlotService)
local UFOCatchers = require(game.ReplicatedStorage.Shared.Config.UFOCatchers)
local def = UFOCatchers.list[1]
local m = PlotService.makeUFOModel(def, 0, CFrame.new())
print("OK", m:FindFirstChild("Claw", true) ~= nil, m:FindFirstChild("ClawJaw", true) ~= nil)
m:Destroy()
```
Expected: `OK true true`.

- [ ] **Step 5: Checkpoint** — `Ctrl+S`.

### Task 13: Router les previews client (roulette + index s'il existe)

**Files:**
- Modify (conditionnel): contrôleur d'index/collection identifié en Task 0 Step 4.
- (Roulette : aucune action requise — le prix réel est server-spawné via `makePrize`→`makeUFOModel`. Les silhouettes restent volontairement des ombres cheap.)

- [ ] **Step 1: Si un builder de preview d'index a été trouvé (Task 0)**

S'il construit son propre mini-modèle de pince : le remplacer par un appel à `ClawModel.build(def, 0, CFrame.new())` (require `ReplicatedStorage.Shared.Config.ClawModel`), parenté dans le `WorldModel` du `ViewportFrame`, recadré par la caméra du viewport.
Expected: previews d'index montrent le nouveau rig.

> **Edge case :** si aucun builder d'index n'existe dans le DM live (sous-projet C non câblé), **ne rien faire** ici et le consigner. L'index héritera du nouveau rig dès qu'il sera câblé sur `ClawModel.build`.

- [ ] **Step 2: (Optionnel) rafraîchir les silhouettes roulette** pour suivre vaguement la nouvelle proportion (ombres) — non bloquant.
- [ ] **Step 3: `multi_edit` + read-back + `Ctrl+S`** (si édité).

### Task 14: Vérification en jeu (Play)

- [ ] **Step 1: Lancer Play et spawn une pince connue**

Run (MCP `start_stop_play`) pour entrer en Play. Attendre le plot du joueur, puis screenshot.
Expected: la machine de plot affiche le nouveau grappin mesh (cabine colorée, bras, griffes orange-peel).

- [ ] **Step 2: Vérifier plusieurs raretés**

Via l'admin menu (gated lylou38000) ou un `execute_luau` runtime qui place des défs T1/T5/T10/T12 sur des slots, screenshot chacun.
Expected: différences lisibles de couleur/bande/échelle/halo.

- [ ] **Step 3: Stop Play.** Consigner les screenshots.

---

## Phase 5 — Re-bake previews + animation/FX

### Task 15: Re-bake des `PlotPreview_0..7`

**Files:**
- Modify: `Workspace.MapBlockout.PlotPreviews.PlotPreview_0..7` (DM, Edit)

- [ ] **Step 1: Localiser le générateur Edit-mode des previews**

Run (MCP `script_grep`) pattern `PlotPreviews|makeUFOModel|PlotPreview_`.
Expected: trouver le script/fonction qui bake les 8 previews statiques (il utilise `PlotService.makeUFOModel`). S'il n'existe pas comme script réutilisable, écrire un script Edit-mode jetable (Step 2).

- [ ] **Step 2: Régénérer les 8 previews avec le nouveau builder**

Run (MCP `execute_luau`, en Edit) — adapter les CFrames/rotations existantes (reprendre celles des previews actuels) :
```lua
local Workspace = game:GetService("Workspace")
local RS = game:GetService("ReplicatedStorage")
local ClawModel = require(RS.Shared.Config.ClawModel)
local UFOCatchers = require(RS.Shared.Config.UFOCatchers)
local blockout = Workspace:FindFirstChild("MapBlockout")
local previews = blockout and blockout:FindFirstChild("PlotPreviews")
assert(previews, "no PlotPreviews folder")
-- def d'exemple pour la preview (pince starter / commun rang 1)
local def = UFOCatchers.get("common_1") or UFOCatchers.list[1]
for i = 0, 7 do
	local node = previews:FindFirstChild("PlotPreview_"..i)
	if node then
		local cf = node:GetPivot()           -- conserver position/rotation existante
		local old = node:FindFirstChild("UFO"); if old then old:Destroy() end
		local m = ClawModel.build(def, 0, cf)
		m.Name = "UFO"; m.Parent = node
	end
end
print("REBAKED PlotPreviews")
```
Expected: `REBAKED PlotPreviews` ; les 8 plots libres montrent le nouveau rig à la bonne orientation.

- [ ] **Step 2b: Screenshot** d'un plot libre pour valider orientation (les previews sont tournées selon le côté ; vérifier qu'elles « regardent » la pile comme avant).
- [ ] **Step 3: `Ctrl+S`** + `inspect_instance` `PlotPreview_0` pour confirmer un enfant `UFO` mesh-based.

### Task 16: `CatchFXController` — fxTier 6/7 + polish animation

**Files:**
- Modify: `StarterPlayer…CatchFXController`

- [ ] **Step 1: Étendre les paliers d'aura à fxTier 6/7**

Repérer (Task 0 Step 3) le code qui mappe `fxTier` aux FX de catch (burst/shockwave/beam/explode, cf. les seuils `tier>=4/6/8` côté roulette pour cohérence). Ajouter des paliers pour `fxTier` 6 et 7 (aura la plus spectaculaire : double burst + beam + teinte prismatique pour 7). Écrire les seuils explicitement, p.ex. :
```lua
-- dans la fonction de climax de catch, après les paliers existants :
if fxTier >= 6 then FXKit.lightBeam(anchorCF, glowC); FXKit.burst(anchorCF, glowC, 6, true) end
if fxTier >= 7 then FXKit.explode(anchorCF, glowC); FXKit.shake(0.7, 0.5) end
```
> Adapter aux helpers réellement présents dans `CatchFXController`/`FXKit` (lus en Task 0). Ne pas inventer de helper inexistant.

- [ ] **Step 2: Polir la séquence d'anim (descente → ouverture → fermeture → remontée + vérins)**

Dans la coroutine de catch, garantir l'ordre et l'easing :
```lua
-- pseudo-séquence à câbler sur les tweens existants (ArmPivot RestCF + JawMotor.Transform) :
-- 1) ouvrir griffes (Transform = OpenAngle) en montant vers la pile
-- 2) plonger ArmPivot un peu sous RestCF (EasingStyle.Quad, In)
-- 3) fermer griffes (Transform = identité) au point bas (clamp)
-- 4) remonter ArmPivot -> RestCF (Quad, Out) SANS Back/Out (pas d'overshoot)
```
Implémenter avec les tweens déjà présents ; **interdire** `EasingStyle.Back`/`Elastic` sur la remontée (cohérent avec le correctif documenté « arm va vers le haut »). Synchroniser un léger mouvement du `Piston` si exposé.

- [ ] **Step 3: `multi_edit` + read-back.**

- [ ] **Step 4: Vérif en Play** : déclencher un catch sur une pince fxTier élevé (T10/T12). Screenshot/observer : griffes s'ouvrent en haut, plongent, se ferment, remontent sans overshoot ; aura 6/7 visible.

- [ ] **Step 5: Checkpoint** — `Ctrl+S`.

---

## Phase 6 — Recette & clôture

### Task 17: Recette d'acceptation + mémoire

- [ ] **Step 1: Test z-fight caméra** — en Play, placer une pince de chaque bande (T1 `common_1`, T5 `legendary_5`, T7 `relic_5`, T9 `cosmic_5`, T10 `transcendent_5`, T12 `eternal_10`) ; tourner la caméra autour (`character_navigation`/déplacement + `screen_capture`). Critère : **zéro scintillement** aux jonctions.
- [ ] **Step 2: Lisibilité 2 axes** — comparer T1 rang 1 vs rang 10 d'une même rareté (greebles/chrome/doré/couronne) ; comparer raretés entre elles (couleur/bande/échelle/halo). Critère : différences évidentes.
- [ ] **Step 3: Animation** — un catch fluide, repos griffes fermées poisées bas, pas d'overshoot.
- [ ] **Step 4: Propagation** — plots ✓, prix roulette ✓, PlotPreviews statiques ✓, index (si câblé) ✓, bannière « nouvelle pince » ✓.
- [ ] **Step 5: Perf** — plusieurs machines + (index ouvert si dispo) restent fluides ; vérifier `get_console_output` (pas d'erreurs/spam).
- [ ] **Step 6: Régression** — prompts E/R, feedback board, Motor6D mâchoires, FX catch intacts. Relancer le test contrat (Task 11 Step 1) : `BUILT 120 FAILURES 0`.
- [ ] **Step 7: `Ctrl+S` final** + mettre à jour la mémoire (`claw-system.md` / `blender-to-roblox-pipeline.md` / nouveau fichier « claw-blender-rig ») : rig Blender mesh-based, `ClawModel.build` builder unique, `makeUFOModel` délégué, templates `ReplicatedStorage.Assets.ClawMeshes`, fxTier 6/7, PlotPreviews re-bakés.

---

## Self-Review (rempli par l'auteur du plan)

**Couverture spec :**
- §1 builder unique + délégué → Tasks 8-12. ✓
- §1 templates ReplicatedStorage → Task 7. ✓
- §1 contrat noms/tags → préservé Tasks 8/12 + testé Task 11. ✓
- §2 rig Blender (9 meshes, griffe instanciée) → Tasks 1-6. ✓
- §3 animation Motor6D polie + repos → Task 16. ✓
- §4 axe rareté `materialBand` → Task 9. ✓
- §4 axe rang finition → Task 10. ✓
- §4/§5 anti-z-fight (standoff, transparences échelonnées, parts distinctes) → Tasks 8-10 (STAND) + recette Task 17 Step 1. ✓
- §5 surfaces : plots (Task 12/14), roulette (Task 13 — auto via makePrize), index (Task 13 conditionnel), PlotPreviews (Task 15), CatchFX fxTier 6/7 (Task 16), bannière (inchangée, vérifiée Task 17). ✓
- §6 pipeline + recentrage bbox + hinge + N tines + scaleMult + Edit-mode + Ctrl+S/read-back → Tasks 6/7/8 + conventions d'en-tête. ✓
- §8 critères de recette → Task 17. ✓

**Placeholders :** les pseudo-blocs de Task 16 Step 2 sont des **consignes de câblage sur des tweens existants non encore lus** (CatchFXController lu seulement à l'exécution) — Task 0 Step 3 + Task 16 Step 1 imposent de lire le vrai code avant ; les seuils FX (Step 1) sont du code réel à adapter aux helpers existants. Aucun « TODO/TBD ».

**Cohérence des types/noms :** templates `Base/Cab/Counterweight/Boom/Stick/Elbow/ClawHub/Jaw/Tip` → parts de contrat `Base/Cab/Counterweight/Boom/Stick/Elbow/Claw/ClawJaw/ClawTip`. Helper `meshPart(model, BASE, tmplName, partName, size, color, cf, material, shape)` cohérent dans toutes les tasks. `meshBeam(tmpl, name, …)` défini Task 8 Step 3. ✓
