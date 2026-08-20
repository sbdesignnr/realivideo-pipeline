#!/usr/bin/env bash
# Smoke test pre realivideo-cpu image. Spúšťa sa VNÚTRI kontajnera:
#   docker run --rm realivideo-cpu:dev bash /workspace/scripts/smoke-test-cpu.sh
#
# Neoveruje len "existujú binárky" — overuje, že COLMAP naozaj prejde CPU SIFT
# cestou bez displeja a bez GPU. To je presne to, čo sa v kontajneri najčastejšie
# rozbije a čo by si inak zistil až na RunPode.
set -euo pipefail

ok()   { printf '  \033[32m✓\033[0m %s\n' "$1"; }
info() { printf '\n\033[1m%s\033[0m\n' "$1"; }

info "1/4  Verzie nástrojov"
# COLMAP nepozná --version; verziu berieme z balíčkovača a funkčnosť z `colmap help`
colmap help >/dev/null 2>&1 || { echo "❌ colmap CLI neodpovedá"; exit 1; }
ok "colmap: $(dpkg-query -W -f='${Version}' colmap 2>/dev/null || echo '?')"
ok "ffmpeg: $(ffmpeg -version 2>/dev/null | head -1 | cut -d' ' -f1-3)"
ok "python: $(python3 --version)"

WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

info "2/4  ffmpeg vyrobí testovacie snímky"
# mandelbrot = silne textúrovaný zdroj, SIFT na ňom nájde tisíce bodov
ffmpeg -loglevel error -f lavfi -i "mandelbrot=size=640x480:rate=1" \
       -frames:v 4 "$WORK/frame_%03d.png"
ok "vygenerované $(ls "$WORK"/frame_*.png | wc -l | tr -d ' ') snímky"

info "3/4  COLMAP feature_extractor (CPU, bez GPU, bez displeja)"
colmap feature_extractor \
    --database_path "$WORK/database.db" \
    --image_path "$WORK" \
    --SiftExtraction.use_gpu 0 \
    --SiftExtraction.max_image_size 640 \
    >"$WORK/colmap.log" 2>&1 \
  || { echo "❌ feature_extractor zlyhal:"; tail -30 "$WORK/colmap.log"; exit 1; }
ok "database.db vytvorená ($(du -h "$WORK/database.db" | cut -f1))"

info "4/4  Kontrola, že sa naozaj našli keypointy"
KP=$(python3 - "$WORK/database.db" <<'PY'
import sqlite3, sys
con = sqlite3.connect(sys.argv[1])
print(con.execute("SELECT COALESCE(SUM(rows),0) FROM keypoints").fetchone()[0])
PY
)
[ "$KP" -gt 0 ] || { echo "❌ COLMAP nenašiel žiadne keypointy"; exit 1; }
ok "keypointov spolu: $KP"

printf '\n\033[32m✅ CPU image je funkčný — COLMAP beží headless na CPU.\033[0m\n'
