#!/usr/bin/env bash
# Rýchle premeranie vstupného videa PRED spustením plného COLMAP behu.
# Spúšťa sa vnútri kontajnera:
#   assess-video.sh <video> <pracovný_priečinok> [vzorkovanie_fps]
#
# Meria tri veci, ktoré sa nám doteraz ukázali ako rozhodujúce:
#   jas      — tmavé snímky nemajú dosť kontrastu na detekciu featureov
#   ostrosť  — motion blur featury rozmaže
#   featury  — priamy proxy na textúrnosť scény; toto je z tých troch najdôležitejšie,
#              lebo meria presne to, s čím potom COLMAP pracuje
#
# Beží nad vzorkou snímok, nie nad celým videom — ide o minúty, nie hodiny.
set -euo pipefail

VIDEO="${1:?chýba cesta k videu}"
WORK="${2:?chýba pracovný priečinok}"
SAMPLE_FPS="${3:-0.5}"     # 0.5 = jedna snímka každé 2 s

S="$WORK/sample"
rm -rf "$S"; mkdir -p "$S"
hdr() { printf '\n\033[1m%s\033[0m\n%s\n' "$1" "$(printf '─%.0s' $(seq 1 ${#1}))"; }

hdr "Metadáta"
ffprobe -v error -select_streams v:0 \
  -show_entries stream=width,height,r_frame_rate,codec_name \
  -show_entries format=duration -of default=noprint_wrappers=1 "$VIDEO"
ROT=$(ffprobe -v error -select_streams v:0 -show_entries stream_side_data=rotation \
      -of default=noprint_wrappers=1:nokey=1 "$VIDEO" 2>/dev/null | head -1)
echo "rotation=${ROT:-0}$([ -n "$ROT" ] && echo '   (video je na výšku)' || echo '   (na šírku)')"

hdr "Vzorkovanie snímok (${SAMPLE_FPS} fps)"
ffmpeg -hide_banner -loglevel error -i "$VIDEO" \
  -vf "fps=${SAMPLE_FPS},scale=w=1280:h=1280:force_original_aspect_ratio=decrease:force_divisible_by=2" \
  -q:v 2 "$S/f_%04d.jpg"
N=$(ls "$S" | wc -l | tr -d ' ')
echo "vzorka: $N snímok"

hdr "Meranie jasu a ostrosti"
ffmpeg -hide_banner -loglevel error -f image2 -i "$S/f_%04d.jpg" \
  -vf "signalstats,metadata=print:key=lavfi.signalstats.YAVG:file=$WORK/bright.txt" -f null - 
ffmpeg -hide_banner -loglevel error -f image2 -i "$S/f_%04d.jpg" \
  -vf "blurdetect=block_width=32:block_height=32,metadata=print:key=lavfi.blur:file=$WORK/blur.txt" -f null -
echo "hotovo"

hdr "Detekcia featureov (COLMAP, CPU)"
rm -f "$WORK/sample.db"
colmap feature_extractor \
  --database_path "$WORK/sample.db" --image_path "$S" \
  --ImageReader.single_camera 1 --SiftExtraction.use_gpu 0 \
  >"$WORK/feat.log" 2>&1
echo "hotovo"

python3 /workspace/scripts/assess-report.py "$WORK"
