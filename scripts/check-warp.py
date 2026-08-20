#!/usr/bin/env python3
"""Hľadá odľahlé kamery a kontroluje, či je trajektória naozaj plochá."""
import sys, os
import numpy as np
TXT = sys.argv[1]
def qm(q):
    w,x,y,z=q
    return np.array([[1-2*y*y-2*z*z,2*x*y-2*z*w,2*x*z+2*y*w],
                     [2*x*y+2*z*w,1-2*x*x-2*z*z,2*y*z-2*x*w],
                     [2*x*z-2*y*w,2*y*z+2*x*w,1-2*x*x-2*y*y]])
C=[];names=[]
lines=[l for l in open(os.path.join(TXT,"images.txt")) if not l.startswith("#")]
for i in range(0,len(lines),2):
    p=lines[i].split()
    if len(p)<10: continue
    q=np.array([float(v) for v in p[1:5]]); t=np.array([float(v) for v in p[5:8]])
    C.append(-qm(q).T@t); names.append(p[9])
C=np.array(C); n=len(C)
med=np.median(C,axis=0)
d=np.linalg.norm(C-med,axis=1)
print(f"kamier: {n}")
print(f"vzdialenosť od stredu — medián {np.median(d):.2f}, 90. perc. {np.percentile(d,90):.2f}, max {d.max():.2f}")
thr=np.percentile(d,90)*3
out=np.where(d>thr)[0]
print(f"odľahlých kamier (>3× 90. percentil): {len(out)}")
for i in out[:8]: print(f"   {names[i]}  vzdialenosť {d[i]:.1f}")
keep=d<=thr
print(f"\n--- SVD po odstránení odľahlých ({keep.sum()} kamier) ---")
for label,X in (("všetky",C),("bez odľahlých",C[keep])):
    Xc=X-X.mean(0); S=np.linalg.svd(Xc,full_matrices=False)[1]
    print(f"  {label:16} {S[0]:7.2f} / {S[1]:6.2f} / {S[2]:6.2f}   rovinnosť={S[2]/S[0]:.3f}")
