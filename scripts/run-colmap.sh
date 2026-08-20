#!/usr/bin/env bash
# COLMAP Structure-from-Motion nad extrahovanými snímkami.
# Spúšťa sa VNÚTRI kontajnera (realivideo-cpu / realivideo-gpu).
#
#   run-colmap.sh <frames_dir> <output_dir>
#
# Ubuntu balík COLMAPu je zostavený BEZ CUDA, preto všade use_gpu=0.
# Všetky parametre sa dajú prebiť premennými prostredia — defaulty zodpovedajú
# konzervatívnemu behu, aby sa dali behy medzi sebou porovnávať.
set -euo pipefail

FRAMES="${1:?chýba cesta k snímkam}"
OUT="${2:?chýba výstupný priečinok}"
DB="$OUT/database.db"
SPARSE="$OUT/sparse"

# --- kamera ------------------------------------------------------------------
CAMERA_MODEL="${CAMERA_MODEL:-SIMPLE_RADIAL}"
SINGLE_CAMERA="${SINGLE_CAMERA:-1}"

# --- extrakcia featureov -----------------------------------------------------
# max_image_size: COLMAP zmenší snímku na túto dlhšiu hranu. 3200 = default,
#   čiže pri našich snímkach sa nezmenšuje nič.
MAX_IMAGE_SIZE="${MAX_IMAGE_SIZE:-3200}"
MAX_NUM_FEATURES="${MAX_NUM_FEATURES:-8192}"
# peak_threshold: prah, pod ktorým sa kandidát na keypoint zahodí ako šum.
#   Zníženie = viac (slabších) featureov v miestach s nízkym kontrastom —
#   presne to, čo potrebujeme v tmavých miestnostiach.
PEAK_THRESHOLD="${PEAK_THRESHOLD:-0.0066}"

# --- matchovanie -------------------------------------------------------------
OVERLAP="${OVERLAP:-10}"
QUADRATIC="${QUADRATIC:-1}"
# Vocab tree zapne detekciu slučiek: spojí snímky z rovnakého miesta, aj keď
# sú vo videu ďaleko od seba (návrat do už videnej miestnosti).
VOCAB_TREE="${VOCAB_TREE:-}"
LOOP_NUM_IMAGES="${LOOP_NUM_IMAGES:-50}"

# --- mapper ------------------------------------------------------------------
# MAPPER_TOLERANT=1 uvoľní prahy: COLMAP prijme aj slabšie podložené snímky.
#   Cena je vyššie riziko nepresnej alebo pokrivenej rekonštrukcie.
MAPPER_TOLERANT="${MAPPER_TOLERANT:-0}"

mkdir -p "$SPARSE"
step() { printf '\n\033[1m=== %s ===\033[0m\n' "$1"; date '+%H:%M:%S'; }

step "1/4 feature_extractor  ($(ls "$FRAMES" | wc -l | tr -d ' ') snímok, max_size=$MAX_IMAGE_SIZE, peak=$PEAK_THRESHOLD)"
time colmap feature_extractor \
    --database_path "$DB" \
    --image_path "$FRAMES" \
    --ImageReader.single_camera "$SINGLE_CAMERA" \
    --ImageReader.camera_model "$CAMERA_MODEL" \
    --SiftExtraction.use_gpu 0 \
    --SiftExtraction.max_image_size "$MAX_IMAGE_SIZE" \
    --SiftExtraction.max_num_features "$MAX_NUM_FEATURES" \
    --SiftExtraction.peak_threshold "$PEAK_THRESHOLD"

step "2/4 sequential_matcher  (overlap=$OVERLAP, quadratic=$QUADRATIC, loop=$([ -n "$VOCAB_TREE" ] && echo ON || echo OFF))"
MATCH_ARGS=(
    --database_path "$DB"
    --SiftMatching.use_gpu 0
    --SequentialMatching.overlap "$OVERLAP"
    --SequentialMatching.quadratic_overlap "$QUADRATIC"
)
if [ -n "$VOCAB_TREE" ]; then
    MATCH_ARGS+=(--SequentialMatching.loop_detection 1
                 --SequentialMatching.vocab_tree_path "$VOCAB_TREE"
                 --SequentialMatching.loop_detection_num_images "$LOOP_NUM_IMAGES")
fi
time colmap sequential_matcher "${MATCH_ARGS[@]}"

step "3/4 mapper  (tolerant=$MAPPER_TOLERANT)"
MAP_ARGS=(
    --database_path "$DB"
    --image_path "$FRAMES"
    --output_path "$SPARSE"
)
if [ "$MAPPER_TOLERANT" = "1" ]; then
    MAP_ARGS+=(
        --Mapper.init_min_num_inliers 50        # default 100 — ľahšie nájde štartovaciu dvojicu
        --Mapper.abs_pose_min_num_inliers 15    # default 30  — ľahšie pridá ďalšiu snímku
        --Mapper.abs_pose_min_inlier_ratio 0.15 # default 0.25
        --Mapper.min_num_matches 10             # default 15
        --Mapper.filter_max_reproj_error 6      # default 4   — netrestá slabšiu geometriu
        --Mapper.init_max_error 6               # default 4
    )
fi
time colmap mapper "${MAP_ARGS[@]}"

step "4/4 model_analyzer"
for m in "$SPARSE"/*/; do
    [ -d "$m" ] || continue
    echo "--- model $(basename "$m") ---"
    colmap model_analyzer --path "$m" 2>&1 | sed 's/^[EWI][0-9]* [0-9:.]* *[0-9]* [a-z_]*\.cc:[0-9]*\] *//'
done

echo
echo "✅ COLMAP dokončený. Výstup: $SPARSE"
