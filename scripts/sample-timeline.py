#!/usr/bin/env python3
"""Rozloženie počtu featureov v čase na vzorke z assess-video.sh."""
import sys, sqlite3
import numpy as np
W=sys.argv[1]; STEP=float(sys.argv[2]) if len(sys.argv)>2 else 2.0
con=sqlite3.connect(W+"/sample.db")
rows=sorted(con.execute("SELECT i.name, COALESCE(k.rows,0) FROM images i LEFT JOIN keypoints k ON k.image_id=i.image_id"))
con.close()
K=np.array([r for _,r in rows]); names=[n for n,_ in rows]
def mmss(s): return f"{int(s//60)}:{int(s%60):02d}"
print(f"vzorka {len(K)} snímok, každé {STEP:.0f} s\n")
BAR=len(K)
line=""
for v in K:
    line += "█" if v>=1500 else ("▓" if v>=800 else ("░" if v>=400 else "·"))
for i in range(0,len(line),70):
    t0=i*STEP
    print(f"  {mmss(t0):>5} {line[i:i+70]}")
print("\n  █ >=1500 featureov   ▓ 800-1500   ░ 400-800   · <400\n")
print(f"najslabších 6 snímok vzorky:")
for i in np.argsort(K)[:6]:
    print(f"  {names[i]}  t={mmss(i*STEP)}  {K[i]} featureov")
print(f"\nnajlepších 4 snímky vzorky:")
for i in np.argsort(K)[-4:][::-1]:
    print(f"  {names[i]}  t={mmss(i*STEP)}  {K[i]} featureov")
