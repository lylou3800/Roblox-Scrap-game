#!/usr/bin/env bash
# Generate + background-remove the remaining reward icons with Z Image (cheapest, 0.15) + bg remover (1.0).
set -u
cd "C:/Users/farhi/Documents/Projet/UFO_Catchers/assets/reward-icons"

S="glossy stylized 3D mobile game reward icon, chunky cartoon style, soft rim light, glossy highlights, thick dark outline, vivid saturated colors, single centered object, isolated on a plain flat solid light gray background, high contrast"

declare -A PROMPTS
PROMPTS[x2_cash]="a shiny golden round coin medallion embossed with a bold large number 2 and a small multiplication cross x symbol, gold and yellow, $S"
PROMPTS[chance]="a glossy emerald green four leaf clover with a small golden horseshoe, lucky charm, $S, no text, no words"
PROMPTS[cache_rare]="a rugged riveted metal storage crate box with a glowing purple gem on the lid, sci-fi loot cache, $S, no text, no words"
PROMPTS[chest]="an open premium treasure chest overflowing with shiny gold coins and gems, wooden body with gold trim, $S, no text, no words"
PROMPTS[prize_rain]="a burst explosion of falling shiny gold coins and green dollar bills, jackpot, dynamic, $S, no text, no words"
PROMPTS[double_boost]="a bold upward pointing green arrow intertwined with a bright yellow lightning bolt, speed and power boost emblem, $S, no text, no words"

extract() { python -c "import sys,json; d=json.load(sys.stdin); print(d[0].get('$1',''))"; }

for key in x2_cash chance cache_rare chest prize_rain double_boost; do
  echo "=== $key : generating ==="
  GEN=$(higgsfield generate create z_image --prompt "${PROMPTS[$key]}" --aspect_ratio 1:1 --wait --json 2>&1)
  GID=$(echo "$GEN" | extract id 2>/dev/null)
  if [ -z "$GID" ]; then echo "$key GEN FAILED: $(echo "$GEN" | tail -3)"; continue; fi
  echo "$key gen id=$GID -> removing bg"
  RM=$(higgsfield generate create image_background_remover --image "$GID" --wait --json 2>&1)
  RURL=$(echo "$RM" | extract result_url 2>/dev/null)
  if [ -z "$RURL" ]; then echo "$key BGREMOVE FAILED: $(echo "$RM" | tail -3)"; continue; fi
  curl -s -o "$key.png" "$RURL"
  echo "$key DONE -> $key.png ($(wc -c < "$key.png") bytes)"
done
echo "=== credits ==="
higgsfield account status 2>&1 | tail -1
echo "=== files ==="
ls -1 *.png
