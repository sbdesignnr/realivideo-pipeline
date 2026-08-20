#!/usr/bin/env python3
"""Koreluje jas snímky s tým, či ju COLMAP zaregistroval."""
import re, os, glob
import numpy as np
B="/workspace/data/brightness.txt"; FR="/workspace/data/frames"
Y=np.array([float(m) for m in re.findall(r"YAVG=([0-9.]+)", open(B).read())])
frames=sorted(os.listdir(FR)); N=len(frames); idx={n:i for i,n in enumerate(frames)}
member=np.full(N,-1,int)
for d in sorted(glob.glob("/workspace/data/colmap/sparse/*_txt")):
    mid=int(os.path.basename(d).split("_")[0])
    for line in open(d+"/images.txt"):
        if line.startswith("#"): continue
        p=line.split()
        if len(p)>=10 and p[9].endswith(".jpg") and p[9] in idx: member[idx[p[9]]]=mid
reg=member>=0; Y=Y[:N]
print(f"snímok s meraním jasu         : {len(Y)}")
print(f"jas (Y, 0-255) celé video     : medián {np.median(Y):.0f}, min {Y.min():.0f}, max {Y.max():.0f}")
print(f"jas — ZAREGISTROVANÉ          : medián {np.median(Y[reg]):.0f}")
print(f"jas — NEREGISTROVANÉ          : medián {np.median(Y[~reg]):.0f}")
print()
for th in (40,60,80,100):
    m=Y<th
    if m.sum():
        print(f"  Y < {th:<3} : {m.sum():3d} snímok ({100*m.mean():4.1f} %) → zaregistrovaných {100*reg[m].mean():5.1f} %")
m=Y>=100
print(f"  Y >= 100: {m.sum():3d} snímok ({100*m.mean():4.1f} %) → zaregistrovaných {100*reg[m].mean():5.1f} %")
