## Task 6 : Bouton HUD haut-centre (téléport haut↔bas)

**Files:**
- Modify: `UIController` (LocalScript, ≈592945–593203) — créer le bouton à l'exécution + le câbler

**Interfaces:**
- Consumes : `hud` (MainHUD), `StateController.get()/onChanged`, `PlotLayout.floor2.height`, `Theme`.
- Produces : un `TextButton` `FloorBtn` parenté à `hud`, ancré haut-centre, visible ssi `st.plot.floor2Unlocked`, label basculant selon la hauteur Y du personnage, téléportant via `HumanoidRootPart.CFrame`.

- [ ] **Step 1 : Require `PlotLayout` côté client** (`multi_edit` sur `UIController`)

Remplacer exactement :
```luau
local Pricing=require(RS.Shared.Config.Pricing)
```
par :
```luau
local Pricing=require(RS.Shared.Config.Pricing)
local PlotLayout=require(RS.Shared.Config.PlotLayout)
```

- [ ] **Step 2 : Créer + câbler le bouton d'étage** (`multi_edit` sur `UIController`)

Remplacer exactement :
```luau
qbtn("SellBtn", function()
	-- Amene le joueur DEVANT l'echoppe du vendeur (et non sur la dalle/dedans), face au comptoir.
	local plot=workspace:FindFirstChild("Plot_"..player.UserId)
	local pad=plot and plot:FindFirstChild("SellPad")
	local char=player.Character; local hrp=char and char:FindFirstChild("HumanoidRootPart")
	if pad and hrp then hrp.CFrame=pad.CFrame*CFrame.new(0,3.5,-12)*CFrame.Angles(0,math.pi,0) end
end)
qbtn("BuildBtn",function() req("buildMachine",{defId="recycler"}) end)
```
par :
```luau
qbtn("SellBtn", function()
	-- Amene le joueur DEVANT l'echoppe du vendeur (et non sur la dalle/dedans), face au comptoir.
	local plot=workspace:FindFirstChild("Plot_"..player.UserId)
	local pad=plot and plot:FindFirstChild("SellPad")
	local char=player.Character; local hrp=char and char:FindFirstChild("HumanoidRootPart")
	if pad and hrp then hrp.CFrame=pad.CFrame*CFrame.new(0,3.5,-12)*CFrame.Angles(0,math.pi,0) end
end)
qbtn("BuildBtn",function() req("buildMachine",{defId="recycler"}) end)

-- ===== Bouton d'étage (haut-centre) : apparait quand l'étage est débloque, telep. haut<->bas =====
local FLOOR_H=PlotLayout.floor2.height
local floorBtn=Instance.new("TextButton")
floorBtn.Name="FloorBtn"
floorBtn.AnchorPoint=Vector2.new(0.5,0)
floorBtn.Position=UDim2.new(0.5,0,0,12)
floorBtn.Size=UDim2.fromOffset(220,46)
floorBtn.AutoButtonColor=true
floorBtn.BackgroundColor3=P.Purple
floorBtn.Font=Theme.Font.Body
floorBtn.Text="\u{25B2} Monter à l'étage"
floorBtn.TextColor3=P.White
floorBtn.TextScaled=true
floorBtn.Visible=false
floorBtn.Parent=hud
Theme.Corner(floorBtn,UDim.new(0,12))
Theme.Stroke(floorBtn,P.Outline,2.5)
Theme.TextStroke(floorBtn,2)
local fbc=Instance.new("UITextSizeConstraint");fbc.MaxTextSize=20;fbc.Parent=floorBtn

local function onUpperFloor()
	local char=player.Character; local hrp=char and char:FindFirstChild("HumanoidRootPart")
	return hrp ~= nil and hrp.Position.Y > (FLOOR_H/2)
end
local function updateFloorLabel()
	floorBtn.Text=onUpperFloor() and "\u{25BC} Descendre" or "\u{25B2} Monter à l'étage"
end
floorBtn.MouseButton1Click:Connect(function()
	local plot=workspace:FindFirstChild("Plot_"..player.UserId)
	local base=plot and plot:FindFirstChild("Base")
	local char=player.Character; local hrp=char and char:FindFirstChild("HumanoidRootPart")
	if not (base and hrp) then return end
	if onUpperFloor() then
		hrp.CFrame=base.CFrame*CFrame.new(0,4,-54) -- retour au RDC (zone de spawn)
	else
		hrp.CFrame=base.CFrame*CFrame.new(0,FLOOR_H+4,-50) -- arrivee sur la dalle, pres de la tremie
	end
	task.wait(0.1)
	updateFloorLabel()
end)
local function refreshFloorBtn(st)
	local unlocked=st and st.plot and st.plot.floor2Unlocked==true
	floorBtn.Visible=unlocked
	if unlocked then updateFloorLabel() end
end
StateController.onChanged(refreshFloorBtn)
refreshFloorBtn(StateController.get())
-- Met a jour le label si le joueur change d'etage par l'echelle (sans cliquer le bouton).
task.spawn(function()
	while true do
		task.wait(0.5)
		if floorBtn.Visible then updateFloorLabel() end
	end
end)
```

- [ ] **Step 3 : Relire pour confirmer** — `script_read` sur `UIController` : `floorBtn` créé, `StateController.onChanged(refreshFloorBtn)`, require `PlotLayout`.

- [ ] **Step 4 : Vérif live — visibilité + téléport** — en Play :
  1. Au spawn (étage non débloqué) → `screen_capture` : **pas** de bouton haut-centre.
  2. Script temporaire serveur (réutiliser Task 5 Step 7 §2) pour débloquer l'étage → après `replicate`, `screen_capture` : bouton « ▲ Monter à l'étage » visible haut-centre.
  3. `user_mouse_input` clic sur le bouton (ou téléport manuel) → vérifier que le perso monte sur la dalle ; `screen_capture` : label devient « ▼ Descendre ».
  4. Re-clic → retour RDC ; label « ▲ Monter à l'étage ».
  5. Monter par l'échelle (sans cliquer) puis attendre ~0.6s → label « ▼ Descendre » (boucle de rafraîchissement).
- [ ] **Step 5 : Checkpoint** — prévenir l'utilisateur qu'il peut sauvegarder (Ctrl+S).

---

