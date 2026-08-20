#!/usr/bin/env python3
"""Sila sekvenčného reťazca: koľko overených inlierov majú susedné snímky."""
import sys, sqlite3
import numpy as np
DB, LABEL = sys.argv[1], sys.argv[2]
con = sqlite3.connect("file:"+DB+"?mode=ro", uri=True)
ids = {name: iid for iid, name in con.execute("SELECT image_id, name FROM images")}
names = sorted(ids)
M = 2147483647
def pid(a, b): return (a*M+b) if a < b else (b*M+a)
geo = dict(con.execute("SELECT pair_id, rows FROM two_view_geometries"))
cons = []
for i in range(len(names)-1):
    cons.append(geo.get(pid(ids[names[i]], ids[names[i+1]]), 0))
c = np.array(cons)
print(f"\n{LABEL}  ({len(names)} snímok)")
print(f"  susedné dvojice        : {len(c)}")
print(f"  inlierov medián        : {np.median(c):.0f}")
print(f"  inlierov priemer       : {c.mean():.0f}")
print(f"  dvojíc s 0 inliermi    : {(c==0).sum():3d}  ({100*(c==0).mean():.1f} %)  ← pretrhnutý reťazec")
print(f"  dvojíc pod 30 inlierov : {(c<30).sum():3d}  ({100*(c<30).mean():.1f} %)")
print(f"  dvojíc nad 100         : {(c>=100).sum():3d}  ({100*(c>=100).mean():.1f} %)")
