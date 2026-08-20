#!/usr/bin/env bash
# Zabalí COLMAP model do štruktúry, akú očakáva OpenSplat:
#
#   <projekt>/images/frame_XXXXX.jpg
#   <projekt>/sparse/0/{cameras.bin, images.bin, points3D.bin}
#
# Kopíruje LEN snímky, ktoré sú v modeli naozaj zaregistrované — zvyšok by sa
# aj tak nepoužil a len by nafúkol prenos na RunPod.
#
#   export-for-opensplat.sh <colmap_dir> <model_id> <frames_dir> <výstup>
set -euo pipefail
CM="${1:?colmap dir}"; MODEL="${2:?id modelu}"; FRAMES="${3:?frames dir}"; OUT="${4:?výstup}"
SRC="$CM/sparse/$MODEL"
[ -f "$SRC/cameras.bin" ] || { echo "❌ $SRC/cameras.bin neexistuje"; exit 1; }

rm -rf "$OUT"; mkdir -p "$OUT/images" "$OUT/sparse/0"
cp "$SRC"/cameras.bin "$SRC"/images.bin "$SRC"/points3D.bin "$OUT/sparse/0/"

# zoznam použitých snímok vytiahneme z textovej podoby modelu
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
colmap model_converter --input_path "$SRC" --output_path "$TMP" --output_type TXT >/dev/null 2>&1
grep -v '^#' "$TMP/images.txt" | awk 'NF>=10 {print $10}' | sort -u > "$TMP/used.txt"

N=0
while read -r f; do
  [ -f "$FRAMES/$f" ] && { cp "$FRAMES/$f" "$OUT/images/"; N=$((N+1)); }
done < "$TMP/used.txt"

echo "✅ balíček pripravený: $OUT"
echo "   snímok      : $N"
echo "   3D bodov    : $(grep -vc '^#' "$TMP/points3D.txt")"
echo "   veľkosť     : $(du -sh "$OUT" | cut -f1)"
echo
echo "štruktúra:"
find "$OUT" -maxdepth 2 -type d | sed 's|^|   |'
ls "$OUT/sparse/0" | sed 's|^|   sparse/0/|'
