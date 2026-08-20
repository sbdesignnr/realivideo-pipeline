#!/usr/bin/env python3
"""
Porovná viac COLMAP behov vedľa seba.

  python3 compare-runs.py <názov>=<colmap_dir>:<frames_dir> [...]

napr.
  compare-runs.py "v1 (720p)"=/workspace/data/colmap:/workspace/data/frames \
                  "v2 (1080p)"=/workspace/data/colmap-v2:/workspace/data/frames_full
"""
import sys, os, glob, sqlite3
import numpy as np


def load(colmap_dir, frames_dir):
    frames = sorted(os.listdir(frames_dir))
    N = len(frames)
    idx = {n: i for i, n in enumerate(frames)}
    member = np.full(N, -1, int)
    pts_per_model = {}
    for d in sorted(glob.glob(colmap_dir + "/sparse/*_txt")):
        mid = int(os.path.basename(d).split("_")[0])
        pts_per_model[mid] = sum(
            1 for l in open(d + "/points3D.txt") if not l.startswith("#"))
        for line in open(d + "/images.txt"):
            if line.startswith("#"):
                continue
            p = line.split()
            if len(p) >= 10 and p[9].endswith(".jpg") and p[9] in idx:
                member[idx[p[9]]] = mid
    kp = np.array([0]*N)
    db = colmap_dir + "/database.db"
    if os.path.exists(db):
        con = sqlite3.connect("file:" + db + "?mode=ro", uri=True)
        n2k = {n: r for n, r in con.execute(
            "SELECT i.name, COALESCE(k.rows,0) FROM images i "
            "LEFT JOIN keypoints k ON k.image_id=i.image_id")}
        kp = np.array([n2k.get(n, 0) for n in frames])
        geo = con.execute(
            "SELECT COUNT(*), COALESCE(SUM(rows),0) FROM two_view_geometries WHERE rows>0").fetchone()
        con.close()
    else:
        geo = (0, 0)
    return dict(N=N, member=member, kp=kp, pts=pts_per_model,
                geo_pairs=geo[0], geo_inl=geo[1], frames=frames)


runs = []
for a in sys.argv[1:]:
    name, paths = a.split("=", 1)
    cdir, fdir = paths.split(":", 1)
    runs.append((name, load(cdir, fdir)))

rows = [
    ("snímok na vstupe",        lambda d: f"{d['N']}"),
    ("keypointov spolu",        lambda d: f"{d['kp'].sum():,}"),
    ("keypointov medián/snímku", lambda d: f"{np.median(d['kp']):.0f}"),
    ("overených dvojíc",        lambda d: f"{d['geo_pairs']:,}"),
    ("overených korešpondencií", lambda d: f"{d['geo_inl']:,}"),
    ("modelov",                 lambda d: f"{len(d['pts'])}"),
    ("registrovaných kdekoľvek", lambda d: f"{(d['member']>=0).sum()} ({100*(d['member']>=0).mean():.1f} %)"),
]


def biggest(d):
    if not len(d['pts']):
        return -1, 0
    counts = {m: int((d['member'] == m).sum()) for m in d['pts']}
    m = max(counts, key=counts.get)
    return m, counts[m]


rows += [
    ("★ v najväčšom modeli",    lambda d: (lambda mc: f"{mc[1]} ({100*mc[1]/d['N']:.1f} %)")(biggest(d))),
    ("★ 3D bodov v ňom",        lambda d: f"{d['pts'].get(biggest(d)[0],0):,}"),
    ("★ bodov na snímku",       lambda d: (lambda mc: f"{d['pts'].get(mc[0],0)/max(mc[1],1):.0f}")(biggest(d))),
]

W = max(26, *(len(r[0]) for r in rows)) + 1
COL = max(18, *(len(n) for n, _ in runs)) + 2
print("\n" + " " * W + "".join(n.ljust(COL) for n, _ in runs))
print("─" * (W + COL * len(runs)))
for label, fn in rows:
    line = label.ljust(W)
    for _, d in runs:
        try:
            line += str(fn(d)).ljust(COL)
        except Exception:
            line += "—".ljust(COL)
    print(line)
print("\n★ = čísla, ktoré rozhodujú o použiteľnosti pre Gaussian Splatting\n")

for name, d in runs:
    reg = d['member'] >= 0
    BAR = 88
    bar = ""
    for b in range(BAR):
        lo, hi = int(b*d['N']/BAR), int((b+1)*d['N']/BAR)
        f = reg[lo:hi].mean() if hi > lo else 0
        bar += "█" if f > .9 else ("▓" if f > .6 else ("░" if f > .2 else "·"))
    print(f"{name:>14} {bar}")
print(" "*15 + "█ >90 %   ▓ 60-90 %   ░ 20-60 %   · takmer nič")
