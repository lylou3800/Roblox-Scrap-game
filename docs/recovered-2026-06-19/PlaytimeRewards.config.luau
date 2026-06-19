--!strict
-- PlaytimeRewards.luau
-- Config des recompenses de temps de jeu (SESSION-only, zero persistance).
-- Cash FIXE (non farmable par sa taille). Boosts additifs. Objets indexes a l'attribution (serveur).

local PlaytimeRewards = {}

local BOOST_CASH_DUR = 300    -- 5 min
local BOOST_LUCK_DUR = 480    -- 8 min
local BOOST_DOUBLE_DUR = 480  -- 8 min

-- type : cash | boost | boost_double | prize_rain | loot | egg | pet_jackpot
-- visual : normal | rare | premium
PlaytimeRewards.tiers = {
	{ tier = 1,  unlock = 60,   type = "cash",         visual = "normal",  cash = 1000,   name = "Premiere Prime",      icon = "cash" },
	{ tier = 2,  unlock = 180,  type = "boost",        visual = "normal",  boostKind = "cash", boostDur = BOOST_CASH_DUR, name = "Boost x2 Cash",   icon = "boost_cash",   desc = "x2 Cash - 5 min" },
	{ tier = 3,  unlock = 360,  type = "cash",         visual = "normal",  cash = 5000,   name = "Prime de Ferraille", icon = "cash" },
	{ tier = 4,  unlock = 660,  type = "loot",         visual = "rare",    lootOffset = 1, lootCount = 3, name = "Cache Rare",     icon = "loot" },
	{ tier = 5,  unlock = 1020, type = "boost",        visual = "rare",    boostKind = "luck", boostDur = BOOST_LUCK_DUR, name = "Boost Chance",  icon = "boost_luck",   desc = "+Chance - 8 min" },
	{ tier = 6,  unlock = 1440, type = "prize_rain",   visual = "rare",    rainFloor = 6000, name = "Pluie de Lots",    icon = "cash" },
	{ tier = 7,  unlock = 1980, type = "cash",         visual = "rare",    cash = 75000,  name = "Jackpot Ferrailleur", icon = "cash" },
	{ tier = 8,  unlock = 2580, type = "egg",          visual = "premium", name = "Oeuf Mystere",        icon = "egg" },
	{ tier = 9,  unlock = 3300, type = "boost_double", visual = "premium", boostKinds = {"yield","speed"}, boostDur = BOOST_DOUBLE_DUR, name = "Double Boost", icon = "boost_double", desc = "Rendement +30% & Vitesse +25% - 8 min" },
	{ tier = 10, unlock = 4020, type = "cash",         visual = "premium", cash = 250000, name = "Gros Lot Premium",   icon = "cash" },
	{ tier = 11, unlock = 4740, type = "loot",         visual = "premium", lootOffset = 2, lootCount = 2, name = "Coffre Legendaire", icon = "loot" },
	{ tier = 12, unlock = 5400, type = "pet_jackpot",  visual = "premium", cash = 500000, name = "JACKPOT FINAL",      icon = "pet",          desc = "Pet + Magot" },
}

function PlaytimeRewards.client()
	local out = {}
	for _, t in ipairs(PlaytimeRewards.tiers) do
		out[#out + 1] = {
			tier = t.tier, unlock = t.unlock, type = t.type, visual = t.visual,
			name = t.name, icon = t.icon, desc = t.desc, cash = t.cash, lootCount = t.lootCount,
		}
	end
	return out
end

function PlaytimeRewards.get(tier: number)
	return PlaytimeRewards.tiers[tier]
end

return PlaytimeRewards
