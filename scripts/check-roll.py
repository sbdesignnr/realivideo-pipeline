#!/usr/bin/env python3
"""
Test pokrivenia necitlivý na naklonenie kamery hore/dole.
Smer "vpravo" u kamery je pri zvisle drženom telefóne vždy vodorovný, aj keď
mieriš do stropu. Nájdeme smer gravitácie ako ten, na ktorý sú všetky "vpravo"
vektory najkolmejšie, a zmeriame zvyškovú odchýlku = roll.
"""
import sys, os
import numpy as np
def qm(q):
    w,x,y,z=q
    return np.array([[1-2*y*y-2*z*z,2*x*y-2*z*w,2*x*z+2*y*w],
                     [2*x*y+2*z*w,1-2*x*x-2*z*z,2*y*z-2*x*w],
                     [2*x*z-2*y*w,2*y*z+2*x*w,1-2*x*x-2*y*y]])
for arg in sys.argv[1:]:
    label, txt = arg.split("=",1)
    R_right=[]
    lines=[l for l in open(os.path.join(txt,"images.txt")) if not l.startswith("#")]
    for i in range(0,len(lines),2):
        p=lines[i].split()
        if len(p)<10: continue
        R=qm(np.array([float(v) for v in p[1:5]]))
        R_right.append(R.T @ np.array([1.,0.,0.]))     # smer "vpravo" vo svete
    A=np.array(R_right); A/=np.linalg.norm(A,axis=1,keepdims=True)
    # gravitácia = smer najkolmejší na všetky "vpravo" vektory
    g=np.linalg.svd(A,full_matrices=False)[2][-1]
    roll=np.degrees(np.arcsin(np.clip(np.abs(A@g),0,1)))
    print(f"\n\033[1m{label}\033[0m  ({len(A)} kamier)")
    print(f"  roll: medián {np.median(roll):5.1f}°  90.perc {np.percentile(roll,90):5.1f}°  max {roll.max():5.1f}°")
    print(f"  kamier s rollom nad 20°: {(roll>20).sum():3d}  ({100*(roll>20).mean():4.1f} %)")
