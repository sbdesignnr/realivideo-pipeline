#!/usr/bin/env python3
"""Rozlíši snímky neregistrované vôbec od tých v odtrhnutom fragmente."""
import os, glob, sqlite3
import numpy as np
import sys
OUT = sys.argv[1]; FR = sys.argv[2]; FPS = float(sys.argv[3]) if len(sys.argv)>3 else 2.0
frames = sorted(os.listdir(FR)); idx = {n: i for i, n in enumerate(frames)}; N = len(frames)

member = np.full(N, -1, dtype=int)
for d in sorted(glob.glob(OUT + "/sparse/*_txt")):
    mid = int(os.path.basename(d).split("_")[0])
    for line in open(d + "/images.txt"):
        if line.startswith("#"):
            continue
        p = line.split()
        if len(p) >= 10 and p[9].endswith(".jpg") and p[9] in idx:
            member[idx[p[9]]] = mid

con = sqlite3.connect("file:" + OUT + "/database.db?mode=ro", uri=True)
name2kp = {n: r for n, r in con.execute(
    "SELECT i.name, COALESCE(k.rows,0) FROM images i LEFT JOIN keypoints k ON k.image_id=i.image_id")}
kp = np.array([name2kp.get(n, 0) for n in frames])

def mmss(s): return f"{int(s//60)}:{int(s%60):02d}"

unreg = member < 0
print(f"snímok spolu             : {N}")
print(f"neregistrovaných NIKDE   : {unreg.sum()}  ({100*unreg.mean():.1f} %)")
print(f"registrovaných           : {(~unreg).sum()}  ({100*(~unreg).mean():.1f} %)")
print(f"  z toho v najväčšom mod.: {(member==1).sum()}")
print(f"\nkeypointy — registrované : medián {np.median(kp[~unreg]):.0f}")
print(f"keypointy — neregistrované: medián {np.median(kp[unreg]):.0f}")

print("\nčasová os po 10 s (číslo = id modelu, ~ = zmiešané, · = nikde):")
SEG = int(10*FPS); sym = "0123456789"
for s in range(0, N, SEG*6):
    row = ""
    for b in range(s, min(s+SEG*6, N), SEG):
        seg = member[b:b+SEG]
        if (seg < 0).all():
            row += " ·"
        else:
            vals, cnt = np.unique(seg[seg >= 0], return_counts=True)
            row += (" "+sym[vals[cnt.argmax()]]) if cnt.max() >= len(seg)*0.6 else " ~"
    print(f"  {mmss(s/FPS):>5} {row}")

print("\nsúvislé úseky BEZ akejkoľvek registrácie (>=5 s):")
runs = []; st = None
for i, u in enumerate(unreg):
    if u and st is None: st = i
    elif not u and st is not None: runs.append((st, i-1)); st = None
if st is not None: runs.append((st, N-1))
for a, b in sorted([r for r in runs if r[1]-r[0]+1 >= 10], key=lambda r: -(r[1]-r[0])):
    n = b-a+1
    print(f"  {mmss(a/FPS)}–{mmss(b/FPS)}  {n:3d} snímok ({n/FPS:5.1f} s)  medián kp={np.median(kp[a:b+1]):.0f}")
