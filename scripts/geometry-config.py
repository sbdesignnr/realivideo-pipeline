#!/usr/bin/env python3
"""
Typ dvojpohľadovej geometrie. COLMAP pri každej overenej dvojici zaznamená,
akú konfiguráciu našiel. Kľúčové sú PLANAR a PANORAMIC:
matchujú sa výborne, ale nedá sa z nich triangulovať hĺbka.
  PANORAMIC = kamera sa otáčala bez posunu (nulová paralaxa)
  PLANAR    = celý záber je jedna rovina (prázdna stena, strop)
"""
import sys, sqlite3
NAMES = {1:"UNDEFINED", 2:"DEGENERATE", 3:"CALIBRATED", 4:"UNCALIBRATED",
         5:"PLANAR", 6:"PANORAMIC", 7:"PLANAR_OR_PANORAMIC", 8:"WATERMARK", 9:"MULTIPLE"}
BAD = {2, 5, 6, 7}
for arg in sys.argv[1:]:
    label, db = arg.split("=", 1)
    con = sqlite3.connect("file:"+db+"?mode=ro", uri=True)
    rows = list(con.execute(
        "SELECT config, COUNT(*) FROM two_view_geometries WHERE rows>0 GROUP BY config"))
    con.close()
    tot = sum(c for _, c in rows) or 1
    bad = sum(c for cfg, c in rows if cfg in BAD)
    print(f"\n\033[1m{label}\033[0m   ({tot:,} overených dvojíc)")
    for cfg, c in sorted(rows, key=lambda r: -r[1]):
        mark = "  ⚠️ nepoužiteľné na trianguláciu" if cfg in BAD else ""
        print(f"   {NAMES.get(cfg,cfg):22} {c:6,}  {100*c/tot:5.1f} %{mark}")
    print(f"   \033[1m→ degenerovaných spolu: {bad:,} / {tot:,} = {100*bad/tot:.1f} %\033[0m")
