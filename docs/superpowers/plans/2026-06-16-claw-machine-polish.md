# Polish pinces, hologrammes & prompts — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Polish des machines de pince : hologramme compact + feedback de loupé intégré, prompts E/R compacts et resserrés, panneaux de zone bien posés, et animation 3D de mâchoires qui s'ouvrent/ferment.

**Architecture :** Tout passe par deux fichiers serveur/client : `ServerScriptService.Server.Services.PlotService` (construction runtime des plots : prompts, panneaux, modèle de pince) et `StarterPlayer.StarterPlayerScripts.Client.Controllers.CatchFXController` (hologramme + animation pince), plus un nouveau contrôleur client `PromptStyleController` (rendu compact des prompts en style Custom).

**Tech Stack :** Roblox Studio, Luau, MCP Roblox Studio (`multi_edit`, `script_read`, `execute_luau`, `start_stop_play`, `screen_capture`, `get_console_output`).

---

## Réalités du projet (lire avant de commencer)

- **Pas de git** dans ce dossier : aucune étape de commit. Chaque tâche se termine par un **checkpoint de vérification en Studio** (lancer Play, lire la console, capturer l'écran).
- **Pas de tests unitaires** : un jeu Roblox visuel. La « vérification » = absence d'erreur Luau au chargement (`get_console_output`) + inspection visuelle (`screen_capture`) + lecture de propriétés runtime via `execute_luau` (datamodel `Server`/`Client`) en mode Play.
- **La géométrie des plots est construite au runtime** par `PlotService` (le plot s'appelle `Plot_<userId>`). Les changements ne se voient donc qu'en **mode Play**. Toutes les éditions de script se font en **mode Edit** (`datamodel_type: "Edit"`), source de vérité.
- **Deux miroirs client** existent (`StarterPlayer.StarterPlayerScripts...` = source ; `Players.<name>.PlayerScripts...` = copie runtime). **Éditer uniquement la source `StarterPlayerScripts`.**
- Avant chaque édition : faire `get_studio_state`. Si Mode = Play, faire `start_stop_play(false)` pour repasser en Edit.

## File Structure

- **Modify** `ServerScriptService.Server.Services.PlotService` :
  - prompts (`refreshSlot`, ~l.339-398) → distance 10, ligne de vue, style Custom ;
  - panneau de zone (`buildPlot`, ~l.543-546) → repositionnement ;
  - mâchoires (`makeUFOModel`, ~l.236-250) → jointage Motor6D.
- **Modify** `StarterPlayer.StarterPlayerScripts.Client.Controllers.CatchFXController` :
  - `getBoard` (~l.248-252) → taille réduite ;
  - `onCatch` branche slip (~l.359-366) → feedback dans l'hologramme, suppression du texte volant ;
  - `floatingText` (~l.153-185) → suppression (devient mort) ;
  - `animateClaw` (~l.298-376) → ouverture/fermeture des mâchoires.
- **Create** `StarterPlayer.StarterPlayerScripts.Client.Controllers.PromptStyleController` (ModuleScript) : rendu compact des ProximityPrompt style Custom.

---

## Task 1 : Hologramme compact + feedback de loupé intégré

**Files:**
- Modify: `StarterPlayer.StarterPlayerScripts.Client.Controllers.CatchFXController`

- [ ] **Step 1 : Réduire la taille du board**

Dans `getBoard`, le bloc actuel :

```lua
	bb.Name = "FeedbackBoard"
	bb.Size = UDim2.fromOffset(168, 112); bb.MaxDistance = 220
	bb.AlwaysOnTop = true
	bb.MaxDistance = 320
```

Remplacer par (≈ −40 % + une seule `MaxDistance`) :

```lua
	bb.Name = "FeedbackBoard"
	bb.Size = UDim2.fromOffset(100, 72)
	bb.AlwaysOnTop = true
	bb.MaxDistance = 180
```

Utiliser `multi_edit` (`datamodel_type: "Edit"`) avec `old_string` = les 4 lignes ci-dessus exactement.

- [ ] **Step 2 : Router le feedback de loupé dans l'hologramme (supprimer le texte volant)**

Dans `onCatch`, le bloc actuel :

```lua
	if data.slip then
		if slotId then
			animateClaw(slotId, data.wobble == true, true, UIUtil.THEME.warn)
		end
		if ufo and ufo.PrimaryPart then
			floatingText(aboveModel(ufo, 0.5), data.wobble and "Rate !" or "Trop lourd !", UIUtil.THEME.warn, false)
			playSound(SOUNDS.slip, ufo.PrimaryPart, 0.5)
		end
		return
	end
```

Remplacer par :

```lua
	if data.slip then
		if slotId then
			animateClaw(slotId, data.wobble == true, true, UIUtil.THEME.warn)
			local b = getBoard(slotId)
			if b then
				b.header.Text = data.wobble and "RATE !" or "TROP LOURD"
				b.header.BackgroundColor3 = UIUtil.THEME.warn
				b.nameL.Text = "-"
				b.valL.Text = "$0"
				if b.oddsL then b.oddsL.Text = "" end
				b.combo.Visible = false
				pulseBoard(b, UIUtil.THEME.warn, false)
			end
		end
		if ufo and ufo.PrimaryPart then
			playSound(SOUNDS.slip, ufo.PrimaryPart, 0.5)
		end
		return
	end
```

- [ ] **Step 3 : Supprimer la fonction `floatingText` devenue inutilisée**

Supprimer entièrement le bloc `local function floatingText(...) ... end` (≈ lignes 153-185). Vérifier d'abord qu'il n'y a plus aucun appel : `script_grep` query `floatingText` ne doit renvoyer que la définition. `comboText` et `aboveModel` restent utilisés ailleurs — ne pas les toucher.

- [ ] **Step 4 : Vérifier le chargement sans erreur**

Run: `get_studio_state` (doit être Edit) → `start_stop_play(true)` → `get_console_output`.
Expected: aucune ligne `CatchFXController ... error` ni `attempt to call`. Le message `[Client] ready (N controllers)` apparaît.

- [ ] **Step 5 : Vérifier visuellement**

En Play, `screen_capture` face à une machine, puis déclencher un catch (laisser la machine tourner) et un loupé.
Expected: l'hologramme est nettement plus petit ; sur loupé l'entête passe en rouge "RATE !"/"TROP LOURD" et pulse ; **aucun** texte 3D ne s'envole. Puis `start_stop_play(false)`.

---

## Task 2 : Prompts resserrés + style Custom (serveur)

**Files:**
- Modify: `ServerScriptService.Server.Services.PlotService`

> Les 4 prompts du plot (`unlock`, `unequip` E, `upgrade` R, `place`) utilisent tous `MaxActivationDistance = 32` et `RequiresLineOfSight = false`, en style Default. On les passe en distance 10 + ligne de vue + style Custom (rendu par le contrôleur de la Task 3).

- [ ] **Step 1 : Appliquer les 6 remplacements**

Via `multi_edit` (`datamodel_type: "Edit"`), dans l'ordre, avec `replace_all: true` pour chaque :

1. `local prompt = Instance.new("ProximityPrompt")` → `local prompt = Instance.new("ProximityPrompt")\n\t\tprompt.Style = Enum.ProximityPromptStyle.Custom`
2. `local up = Instance.new("ProximityPrompt")` → `local up = Instance.new("ProximityPrompt")\n\t\t\tup.Style = Enum.ProximityPromptStyle.Custom`
3. `prompt.MaxActivationDistance = 32` → `prompt.MaxActivationDistance = 10`
4. `up.MaxActivationDistance = 32` → `up.MaxActivationDistance = 10`
5. `prompt.RequiresLineOfSight = false` → `prompt.RequiresLineOfSight = true`
6. `up.RequiresLineOfSight = false` → `up.RequiresLineOfSight = true`

(L'indentation des lignes `Style` ajoutées est cosmétique ; Luau l'ignore.)

- [ ] **Step 2 : Vérifier les remplacements**

Run: `script_grep` query `MaxActivationDistance = 32`.
Expected: 0 résultat dans `PlotService`.
Run: `script_grep` query `ProximityPromptStyle.Custom`.
Expected: 4 occurrences dans `PlotService`.

- [ ] **Step 3 : Vérifier runtime (les prompts sont en Custom + distance 10)**

Run `execute_luau` (`datamodel_type: "Server"`, après `start_stop_play(true)`) :

```lua
local out = {}
for _, p in ipairs(workspace:GetDescendants()) do
	if p:IsA("ProximityPrompt") and p.Parent and p.Parent.Name:match("^Slot_") then
		table.insert(out, string.format("%s | style=%s | dist=%d | los=%s", p.ActionText, tostring(p.Style), p.MaxActivationDistance, tostring(p.RequiresLineOfSight)))
	end
end
return table.concat(out, "\n")
```

Expected: chaque prompt de slot → `style=Enum.ProximityPromptStyle.Custom | dist=10 | los=true`.

> Note : en Custom sans renderer, les prompts sont INVISIBLES — c'est normal jusqu'à la Task 3. Garder Play ouvert ou refaire Play après la Task 3.

---

## Task 3 : Contrôleur de rendu compact des prompts (client)

**Files:**
- Create: `StarterPlayer.StarterPlayerScripts.Client.Controllers.PromptStyleController`

- [ ] **Step 1 : Créer le contrôleur**

Via `multi_edit` (`datamodel_type: "Edit"`, `className: "ModuleScript"`, `file_path: "StarterPlayer.StarterPlayerScripts.Client.Controllers.PromptStyleController"`), premier edit `old_string` vide, `new_string` =

```lua
--!strict
-- PromptStyleController.luau
-- Rendu COMPACT des ProximityPrompt passés en Style=Custom par PlotService.
-- Dessine une petite carte (pastille touche + texte d'action) bien plus petite que
-- le style Default. Le stacking vertical (E/R) suit le signe de prompt.UIOffset.Y.

local ProximityPromptService = game:GetService("ProximityPromptService")
local TweenService = game:GetService("TweenService")
local UserInputService = game:GetService("UserInputService")

local PromptStyleController = {}

local guis: { [ProximityPrompt]: BillboardGui } = {}

local function keyText(prompt: ProximityPrompt): string
	if UserInputService.GamepadEnabled and not UserInputService.KeyboardEnabled then
		return prompt.GamepadKeyCode.Name
	end
	local k = prompt.KeyboardKeyCode
	return (k ~= Enum.KeyCode.Unknown) and k.Name or "E"
end

local function build(prompt: ProximityPrompt)
	local parent = prompt.Parent
	if not parent or not parent:IsA("BasePart") then return end

	local bb = Instance.new("BillboardGui")
	bb.Name = "PromptCompact"
	bb.Size = UDim2.fromOffset(150, 34)
	bb.SizeOffset = Vector2.new(0, 0)
	bb.AlwaysOnTop = true
	bb.MaxDistance = prompt.MaxActivationDistance + 6
	-- Hauteur de lecture + stacking (UIOffset.Y positif = plus haut, pour conserver l'ordre actuel).
	bb.StudsOffset = Vector3.new(0, 6 + prompt.UIOffset.Y / 40, 0)
	bb.Parent = parent

	local card = Instance.new("Frame")
	card.Size = UDim2.fromScale(1, 1)
	card.BackgroundColor3 = Color3.fromRGB(24, 26, 34)
	card.BackgroundTransparency = 0.1
	card.BorderSizePixel = 0
	card.Parent = bb
	local cc = Instance.new("UICorner"); cc.CornerRadius = UDim.new(0, 10); cc.Parent = card
	local cs = Instance.new("UIStroke"); cs.Thickness = 2; cs.Color = Color3.fromRGB(120, 130, 150); cs.Parent = card

	local key = Instance.new("TextLabel")
	key.AnchorPoint = Vector2.new(0, 0.5)
	key.Position = UDim2.new(0, 4, 0.5, 0)
	key.Size = UDim2.fromOffset(26, 26)
	key.BackgroundColor3 = Color3.fromRGB(244, 246, 250)
	key.Font = Enum.Font.GothamBlack
	key.Text = keyText(prompt)
	key.TextColor3 = Color3.fromRGB(20, 22, 30)
	key.TextScaled = true
	key.Parent = card
	local kc = Instance.new("UICorner"); kc.CornerRadius = UDim.new(0, 7); kc.Parent = key
	local kpad = Instance.new("UIPadding")
	kpad.PaddingTop = UDim.new(0, 4); kpad.PaddingBottom = UDim.new(0, 4)
	kpad.PaddingLeft = UDim.new(0, 4); kpad.PaddingRight = UDim.new(0, 4)
	kpad.Parent = key

	local action = Instance.new("TextLabel")
	action.AnchorPoint = Vector2.new(0, 0.5)
	action.Position = UDim2.new(0, 36, 0.5, 0)
	action.Size = UDim2.new(1, -42, 1, -8)
	action.BackgroundTransparency = 1
	action.Font = Enum.Font.GothamBold
	action.Text = prompt.ActionText
	action.TextColor3 = Color3.fromRGB(235, 238, 245)
	action.TextScaled = true
	action.TextXAlignment = Enum.TextXAlignment.Left
	action.Parent = card
	local ac = Instance.new("UITextSizeConstraint"); ac.MaxTextSize = 16; ac.Parent = action

	-- Petit pop d'apparition.
	local scale = Instance.new("UIScale"); scale.Scale = 0.6; scale.Parent = card
	TweenService:Create(scale, TweenInfo.new(0.16, Enum.EasingStyle.Back, Enum.EasingDirection.Out), { Scale = 1 }):Play()

	guis[prompt] = bb
end

function PromptStyleController:Start()
	ProximityPromptService.PromptShown:Connect(function(prompt: ProximityPrompt)
		if prompt.Style ~= Enum.ProximityPromptStyle.Custom then return end
		if guis[prompt] then return end
		build(prompt)
	end)
	ProximityPromptService.PromptHidden:Connect(function(prompt: ProximityPrompt)
		local bb = guis[prompt]
		if bb then
			bb:Destroy()
			guis[prompt] = nil
		end
	end)
end

return PromptStyleController
```

- [ ] **Step 2 : Vérifier le chargement**

Run: `start_stop_play(true)` → `get_console_output`.
Expected: `[Client] ready` avec **un contrôleur de plus** qu'avant, aucune erreur `PromptStyleController`.

- [ ] **Step 3 : Vérifier visuellement la compacité + le stacking**

S'approcher d'une machine équipée (< 10 studs), `screen_capture`.
Expected: deux petites cartes E (Ranger l'UFO) et R (Ameliorer) bien plus petites que le style Default, lisibles, non superposées. En reculant > 10 studs ou derrière un mur, les prompts disparaissent (distance/ligne de vue OK).

- [ ] **Step 4 : Ajuster si besoin**

Si la taille/hauteur/ordre ne conviennent pas, ajuster dans `build` : `bb.Size`, `bb.StudsOffset` (le `6` = hauteur, le `/40` = écart de stacking ; inverser le signe de `prompt.UIOffset.Y / 40` pour échanger l'ordre E/R). Re-vérifier (Step 3). `start_stop_play(false)` une fois satisfait.

---

## Task 4 : Panneaux de zone bien posés sur les poteaux

**Files:**
- Modify: `ServerScriptService.Server.Services.PlotService`

> Le poteau `ZonePostSign` (centre Y=1.7, hauteur 3.4 → sommet à 3.4) et le panneau `ZoneSign` (centre Y=3.5, hauteur 1.7 → bas à 2.65) se chevauchent : le sommet du poteau (3.4) pénètre dans le panneau (2.65–4.35). Le panneau est aussi décalé de `innerX*0.45` en X. Fix : poser le panneau **sur** le poteau (bas du panneau = sommet du poteau → centre Y = 4.25) et le **centrer** sur le poteau en X.

- [ ] **Step 1 : Repositionner le panneau**

Ligne actuelle (`makePart("ZoneSign_" ...)`) :

```lua
		local board = makePart("ZoneSign_" .. slotDef.id, Vector3.new(3.6, 1.7, 0.22), Color3.fromRGB(26, 28, 36), origin * CFrame.new(zc + Vector3.new(signX + innerX * 0.45, 3.5, signZ)) * CFrame.Angles(0, innerX > 0 and math.rad(-90) or math.rad(90), 0), model)
```

Remplacer le `Vector3.new(signX + innerX * 0.45, 3.5, signZ)` par `Vector3.new(signX, 4.25, signZ)` :

```lua
		local board = makePart("ZoneSign_" .. slotDef.id, Vector3.new(3.6, 1.7, 0.22), Color3.fromRGB(26, 28, 36), origin * CFrame.new(zc + Vector3.new(signX, 4.25, signZ)) * CFrame.Angles(0, innerX > 0 and math.rad(-90) or math.rad(90), 0), model)
```

- [ ] **Step 2 : Vérifier la géométrie runtime**

Run `execute_luau` (`datamodel_type: "Server"`, en Play) :

```lua
local plot
for _, m in ipairs(workspace:GetChildren()) do
	if m:IsA("Model") and m.Name:match("^Plot_") then plot = m break end
end
local post = plot:FindFirstChild("ZonePostSign_s1")
local sign = plot:FindFirstChild("ZoneSign_s1")
local postTop = post.Position.Y + post.Size.Y/2
local signBot = sign.Position.Y - sign.Size.Y/2
return string.format("postTop=%.2f signBot=%.2f gap=%.2f", postTop, signBot, signBot - postTop)
```

Expected: `gap` ≈ 0 (et ≥ 0, pas de chevauchement vertical).

- [ ] **Step 3 : Vérifier visuellement**

`screen_capture` cadré sur un panneau de baie (ex. "BAIE 1").
Expected: le panneau repose proprement au sommet du poteau, sans le traverser. Ajuster `4.25` (monter/descendre) si le rendu n'est pas net, re-vérifier. `start_stop_play(false)` une fois satisfait.

---

## Task 5 : Mâchoires qui s'ouvrent / se ferment

### Task 5a : Builder — jointer les mâchoires en Motor6D (serveur)

**Files:**
- Modify: `ServerScriptService.Server.Services.PlotService` (`makeUFOModel`)

> Aujourd'hui chaque `ClawJaw` et `ClawTip` est `welded()` (WeldConstraint sur `ArmPivot`) → statique. On joint chaque `ClawJaw` au `claw` par un **Motor6D** (charnière au sommet de la mâchoire) et on **welde le `ClawTip` à sa mâchoire** pour qu'il suive. Le client pilotera `Motor6D.Transform`.

- [ ] **Step 1 : Remplacer la boucle des tines**

Bloc actuel :

```lua
	local tineN = (arch == "force") and 6 or (arch == "cadence") and 4 or 5
	for j = 0, tineN - 1 do
		local a2 = (math.pi * 2 / tineN) * j
		welded("ClawJaw", Vector3.new(0.5 * S, 2.4 * S, 0.85 * S), accent, clawLocal * CFrame.Angles(0, a2, 0) * CFrame.new(1.1 * S, -1.05 * S, 0) * CFrame.Angles(0, 0, math.rad(32)), Enum.Material.Metal)
		welded("ClawTip", Vector3.new(0.55 * S, 0.8 * S, 0.9 * S), STEEL_LIGHT, clawLocal * CFrame.Angles(0, a2, 0) * CFrame.new(1.85 * S, -2.1 * S, 0) * CFrame.Angles(0, 0, math.rad(58)), Enum.Material.Metal)
	end
```

Remplacer par :

```lua
	-- Mâchoires articulées : chaque ClawJaw est joint au "Claw" par un Motor6D (charnière au
	-- sommet de la mâchoire). Au repos Transform = identité => pose fermée. Le client ouvre via
	-- Motor6D.Transform = CFrame.Angles(0, 0, OpenAngle). Le ClawTip est weldé à sa mâchoire.
	local tineN = (arch == "force") and 6 or (arch == "cadence") and 4 or 5
	local function hingedJaw(a2)
		local jawLocal = clawLocal * CFrame.Angles(0, a2, 0) * CFrame.new(1.1 * S, -1.05 * S, 0) * CFrame.Angles(0, 0, math.rad(32))
		local hinge = clawLocal * CFrame.Angles(0, a2, 0) * CFrame.new(1.0 * S, 0.15 * S, 0)
		local jaw = part("ClawJaw", Vector3.new(0.5 * S, 2.4 * S, 0.85 * S), accent, pivotCF * jawLocal, Enum.Material.Metal)
		jaw.Anchored = false
		jaw.Massless = true
		jaw:SetAttribute("OpenAngle", -0.5)
		local m = Instance.new("Motor6D")
		m.Name = "JawMotor"
		m.Part0 = claw
		m.Part1 = jaw
		m.C0 = clawLocal:Inverse() * hinge
		m.C1 = hinge:Inverse() * jawLocal
		m.Parent = claw
		local tipLocal = clawLocal * CFrame.Angles(0, a2, 0) * CFrame.new(1.85 * S, -2.1 * S, 0) * CFrame.Angles(0, 0, math.rad(58))
		local tip = part("ClawTip", Vector3.new(0.55 * S, 0.8 * S, 0.9 * S), STEEL_LIGHT, pivotCF * tipLocal, Enum.Material.Metal)
		tip.Anchored = false
		tip.Massless = true
		local w = Instance.new("WeldConstraint")
		w.Part0 = jaw
		w.Part1 = tip
		w.Parent = tip
	end
	for j = 0, tineN - 1 do
		hingedJaw((math.pi * 2 / tineN) * j)
	end
```

(Note : `part`, `claw`, `clawLocal`, `pivotCF`, `S`, `accent`, `STEEL_LIGHT` sont tous définis plus haut dans `makeUFOModel` ; `BASE` et `pivotCF` s'annulent dans le calcul C0/C1 car les deux parts les partagent.)

- [ ] **Step 2 : Vérifier la structure runtime**

Run `execute_luau` (`datamodel_type: "Server"`, en Play) :

```lua
local plot
for _, m in ipairs(workspace:GetChildren()) do
	if m:IsA("Model") and m.Name:match("^Plot_") then plot = m break end
end
local ufo = plot:FindFirstChild("UFO_s1")
local motors, jaws = 0, 0
for _, d in ipairs(ufo:GetDescendants()) do
	if d:IsA("Motor6D") and d.Name == "JawMotor" then motors += 1 end
	if d.Name == "ClawJaw" then jaws += 1 end
end
return string.format("jaws=%d motors=%d", jaws, motors)
```

Expected: `jaws=5 motors=5` (machine starter = archetype standard → 5 tines).

- [ ] **Step 3 : Vérifier que la pince est intacte au repos**

`screen_capture` de la pince starter.
Expected: la pince a la même apparence fermée qu'avant (les mâchoires ne se sont pas affaissées ni écartées). Si elles se sont écartées au repos, le signe/zéro de référence est faux : vérifier que `Transform` n'est pas piloté (il ne l'est pas encore) — la pose fermée doit correspondre à Transform = identité. `start_stop_play(false)`.

### Task 5b : Client — animer l'ouverture/fermeture (client)

**Files:**
- Modify: `StarterPlayer.StarterPlayerScripts.Client.Controllers.CatchFXController` (`animateClaw`)

- [ ] **Step 1 : Récupérer les moteurs et ajouter un helper `setJaws`**

Dans `animateClaw`, juste après la validation `pivot`/`claw` (après le bloc `if not pivot ... then return end` et `clawBusy[slotId] = true`), insérer :

```lua
	local jawMotors = {}
	for _, d in ipairs(ufo:GetDescendants()) do
		if d:IsA("Motor6D") and d.Name == "JawMotor" then
			table.insert(jawMotors, d)
		end
	end
	local function setJaws(frac: number, dur: number)
		for _, m in ipairs(jawMotors) do
			local openAngle = (m.Part1 and m.Part1:GetAttribute("OpenAngle")) or -0.5
			TweenService:Create(m, TweenInfo.new(dur, Enum.EasingStyle.Quad), { Transform = CFrame.Angles(0, 0, openAngle * frac) }):Play()
		end
	end
```

- [ ] **Step 2 : Ouvrir pendant la descente**

Dans `t1.Completed:Connect(function() ... end)`, juste avant `tP:Play()`, ajouter `setJaws(1, 0.24)` :

```lua
		local tP = TweenService:Create(pivot, TweenInfo.new(0.24, Enum.EasingStyle.Quad, Enum.EasingDirection.In), { CFrame = down })
		setJaws(1, 0.24)
		tP.Completed:Connect(function()
```

- [ ] **Step 3 : Refermer (grab) en bas**

Dans `tP.Completed:Connect(function() ... end)`, juste après `playSound(SOUNDS.clamp, claw, 0.5)`, ajouter `setJaws(0, 0.12)` :

```lua
			playSound(SOUNDS.clamp, claw, 0.5)
			setJaws(0, 0.12)
			digBurst((claw :: BasePart).CFrame * CFrame.new(0, -1.4, 0), col)
```

- [ ] **Step 4 : Rouvrir (relâche) au retour au repos**

Dans `tU.Completed:Connect(function() ... end)`, juste avant `clawBusy[slotId] = nil`, ajouter une ré-ouverture puis détente :

```lua
						setJaws(1, 0.18)
						task.delay(0.22, function() setJaws(0, 0.25) end)
						clawBusy[slotId] = nil
```

- [ ] **Step 5 : Vérifier le chargement**

Run: `start_stop_play(true)` → `get_console_output`.
Expected: aucune erreur `CatchFXController`.

- [ ] **Step 6 : Vérifier l'animation**

Laisser la machine attraper, `screen_capture` pendant le cycle (plusieurs captures).
Expected: les mâchoires **s'ouvrent** à la descente, **se ferment** en bas (grab), restent fermées à la remontée, puis se rouvrent au repos. Si elles s'ouvrent dans le **mauvais sens** (vers l'intérieur au lieu de l'extérieur), inverser le signe de l'attribut `OpenAngle` dans Task 5a Step 1 (`-0.5` → `0.5`) et re-vérifier. Ajuster l'amplitude (`0.5`) au goût. `start_stop_play(false)` une fois satisfait.

> **Risque technique (à valider ici) :** si le `Motor6D.Transform` piloté côté client ne bouge PAS visuellement (les mâchoires restent figées), c'est que l'articulation locale ne s'applique pas. Fallback : piloter à la place la CFrame de chaque `ClawJaw` directement chaque frame relativement à `claw.CFrame` (lire les attributs de pose), au lieu du Motor6D — mais d'abord confirmer que le Transform ne marche pas (il devrait, le dip pilote déjà des CFrames côté client sur cette assemblée).

---

## Vérification finale (toutes tâches)

- [ ] **Step 1 :** `start_stop_play(true)`, `get_console_output` → zéro erreur serveur/client.
- [ ] **Step 2 :** S'approcher d'une machine : hologramme compact, prompts E/R compacts visibles seulement de près (≤10 studs, ligne de vue), panneau de baie propre sur son poteau.
- [ ] **Step 3 :** Observer un catch (mâchoires ouvrent/ferment) et un loupé (feedback rouge dans l'hologramme, pas de texte volant).
- [ ] **Step 4 :** `start_stop_play(false)` pour revenir en Edit. Le `build.rbxlx` contient désormais les scripts modifiés (source de vérité).
