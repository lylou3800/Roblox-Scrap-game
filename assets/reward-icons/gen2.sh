#!/usr/bin/env bash
cd "C:/Users/farhi/Documents/Projet/UFO_Catchers/assets/reward-icons"
S="bold 2D cartoon icon with THICK black outline, flat cel shading, super vivid saturated bright joyful colors, mobile gacha game reward icon, Pet Simulator style, single centered object, isolated on a flat solid light background, no shadow, high contrast"
declare -A P
P[x2_cash]="a shiny golden round coin medallion embossed with a bold black number 2 and a small x multiplication symbol, gold and yellow, $S, no extra text"
P[chance]="a bright green glossy four leaf clover lucky charm with a small golden horseshoe, $S, no text, no words"
P[cache_rare]="a chunky riveted metal treasure loot crate box with a glowing purple gem on the lid, $S, no text, no words"
P[chest]="an open wooden treasure chest with gold trim overflowing with shiny gold coins and a few gems, $S, no text, no words"
P[prize_rain]="a dynamic burst of falling green cash dollar bills and gold coins exploding upward, jackpot, $S, no text, no words"
P[double_boost]="a bold bright green upward arrow with a yellow lightning bolt in front, $S, no text, no words"
for k in x2_cash chance cache_rare chest prize_rain double_boost; do
  echo "=== $k ==="
  GEN=$(higgsfield generate create z_image --prompt "${P[$k]}" --aspect_ratio 1:1 --wait --json 2>&1)
  URL=$(echo "$GEN" | python -c "import sys,json; print(json.load(sys.stdin)[0]['result_url'])" 2>/dev/null)
  if [ -z "$URL" ]; then echo "$k GEN FAIL: $(echo "$GEN" | tail -2)"; continue; fi
  curl -s -o "${k}2_raw.png" "$URL"
  python key.py "${k}2_raw.png" "up2/$k.png"
done
echo "=== credits ==="; higgsfield account status 2>&1 | tail -1
echo "=== up2 ==="; ls -1 up2/
