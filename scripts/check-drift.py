#!/usr/bin/env python3
"""Priebeh 3. hlavnej osi v čase: plynulý drift vs. skutočné kmitanie."""
import sys, os
import numpy as np
TXT=sys.argv[1]
def qm(q):
    w,x,y,z=q
    return np.array([[1-2*y*y-2*z*z,2*x*y-2*z*w,2*x*z+2*y*w],
                     [2*x*y+2*z*w,1-2*x*x-2*z*z,2*y*z-2*x*w],
                     [2*x*z-2*y*w,2*y*z+2*x*w,1-2*x*x-2*y*y]])
rows=[]
lines=[l for l in open(os.path.join(TXT,"images.txt")) if not l.startswith("#")]
for i in range(0,len(lines),2):
    p=lines[i].split()
    if len(p)<10: continue
    q=np.array([float(v) for v in p[1:5]]); t=np.array([float(v) for v in p[5:8]])
    rows.append((p[9], -qm(q).T@t))
rows.sort(key=lambda r:r[0])
C=np.array([c for _,c in rows])
Cc=C-C.mean(0)
U,S,Vt=np.linalg.svd(Cc,full_matrices=False)
proj=Cc@Vt.T   # súradnice v hlavných osiach, v poradí snímok
a3=proj[:,2]
print(f"kamier: {len(C)}   SVD: {S[0]:.1f} / {S[1]:.1f} / {S[2]:.1f}")
# autokorelácia 1. rádu na 3. osi: blízko 1 = plynulý priebeh, blízko 0 = šum
d=np.diff(a3)
ac=np.corrcoef(a3[:-1],a3[1:])[0,1]
print(f"autokorelácia 3. osi   : {ac:.3f}   (>0.95 = veľmi plynulý priebeh)")
print(f"krok medzi snímkami    : medián |Δ|={np.median(np.abs(d)):.3f}, rozsah osi={a3.max()-a3.min():.2f}")
print(f"počet zmien znamienka Δ: {int((np.diff(np.sign(d))!=0).sum())} z {len(d)}  (veľa = kmitá, málo = plazí sa)")
H=17; W=96
print(f"\npriebeh 3. hlavnej osi naprieč videom (zhora nadol = rozsah osi):")
lo,hi=a3.min(),a3.max()
grid=[[" "]*W for _ in range(H)]
for i,v in enumerate(a3):
    x=int(i/(len(a3)-1)*(W-1)); y=int((v-lo)/max(hi-lo,1e-9)*(H-1))
    grid[H-1-y][x]="*"
print("┌"+"─"*W+"┐")
for r in grid: print("│"+"".join(r)+"│")
print("└"+"─"*W+"┘")
print(" začiatok videa" + " "*(W-28) + "koniec videa")
