#!/usr/bin/env python3
"""
Konzistencia smeru "hore" naprieč kamerami.
Človek drží telefón zhruba zvislo — svetové "hore" by malo byť u všetkých kamier
takmer rovnaké. Ak sa rozchádza, model je pokrivený.
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
    ups=[]
    lines=[l for l in open(os.path.join(txt,"images.txt")) if not l.startswith("#")]
    for i in range(0,len(lines),2):
        p=lines[i].split()
        if len(p)<10: continue
        R=qm(np.array([float(v) for v in p[1:5]]))
        ups.append(R.T @ np.array([0.,-1.,0.]))   # svetové "hore" kamery
    U=np.array(ups)
    U/=np.linalg.norm(U,axis=1,keepdims=True)
    # dominantný smer cez SVD, potom uhlová odchýlka každej kamery od neho
    mean=U.mean(0); mean/=np.linalg.norm(mean)
    ang=np.degrees(np.arccos(np.clip(U@mean,-1,1)))
    print(f"\n\033[1m{label}\033[0m  ({len(U)} kamier)")
    print(f"  odchýlka od spoločného 'hore': medián {np.median(ang):5.1f}°   "
          f"90. perc. {np.percentile(ang,90):5.1f}°   max {ang.max():5.1f}°")
    print(f"  kamier nad 30° odchýlky      : {(ang>30).sum():3d}  ({100*(ang>30).mean():4.1f} %)")
    print(f"  kamier nad 60° odchýlky      : {(ang>60).sum():3d}  ({100*(ang>60).mean():4.1f} %)")
