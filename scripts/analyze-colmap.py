#!/usr/bin/env python3
"""
Analýza výsledkov COLMAPu: koľko snímok sa zaregistrovalo, kde vznikli diery
v priestore/čase a či je scéna pripravená na Gaussian Splatting.

Spúšťa sa v kontajneri:
  python3 analyze-colmap.py <colmap_dir> <frames_dir> [fps]
"""
import sys, os, sqlite3, subprocess, glob
import numpy as np

OUT = sys.argv[1]
FRAMES_DIR = sys.argv[2]
FPS = float(sys.argv[3]) if len(sys.argv) > 3 else 2.0
DB = os.path.join(OUT, "database.db")
SPARSE = os.path.join(OUT, "sparse")


def h(t):
    print(f"\n\033[1m{t}\033[0m")
    print("─" * len(t))


def read_images_txt(path):
    """images.txt -> {name: (quaternion, translation, n_points2D_with_3D)}"""
    out = {}
    with open(path) as f:
        lines = [l for l in f if not l.startswith("#")]
    for i in range(0, len(lines), 2):
        p = lines[i].split()
        if len(p) < 10:
            continue
        q = np.array([float(x) for x in p[1:5]])   # QW QX QY QZ
        t = np.array([float(x) for x in p[5:8]])
        name = p[9]
        pts = lines[i + 1].split() if i + 1 < len(lines) else []
        n3d = sum(1 for j in range(2, len(pts), 3) if pts[j] != "-1")
        out[name] = (q, t, n3d)
    return out


def qvec2rotmat(q):
    w, x, y, z = q
    return np.array([
        [1-2*y*y-2*z*z, 2*x*y-2*z*w,   2*x*z+2*y*w],
        [2*x*y+2*z*w,   1-2*x*x-2*z*z, 2*y*z-2*x*w],
        [2*x*z-2*y*w,   2*y*z+2*x*w,   1-2*x*x-2*y*y]])


# ─── 1. Keypointy z databázy ────────────────────────────────────────────────
h("1. Extrakcia featureov")
con = sqlite3.connect(DB)
n_img_db = con.execute("SELECT COUNT(*) FROM images").fetchone()[0]
kp_total, kp_rows = con.execute(
    "SELECT COALESCE(SUM(rows),0), COUNT(*) FROM keypoints").fetchone()
per_img = con.execute("SELECT image_id, rows FROM keypoints").fetchall()
counts = np.array([r for _, r in per_img]) if per_img else np.array([0])
print(f"snímok v databáze      : {n_img_db}")
print(f"keypointov spolu       : {kp_total:,}")
print(f"na snímku  priemer/med : {counts.mean():.0f} / {np.median(counts):.0f}")
print(f"           min/max     : {counts.min()} / {counts.max()}")
weak = int((counts < 500).sum())
print(f"snímok s <500 keypointmi: {weak}  ({100*weak/max(len(counts),1):.1f} %)")

# ─── 2. Matchovanie ─────────────────────────────────────────────────────────
h("2. Matchovanie")
n_pairs = con.execute("SELECT COUNT(*) FROM matches WHERE rows>0").fetchone()[0]
n_inl = con.execute("SELECT COUNT(*) FROM two_view_geometries WHERE rows>0").fetchone()[0]
inl_sum = con.execute("SELECT COALESCE(SUM(rows),0) FROM two_view_geometries").fetchone()[0]
print(f"dvojíc s matchmi       : {n_pairs:,}")
print(f"dvojíc s geometriou    : {n_inl:,}  (prežili verifikáciu)")
print(f"overených korešpondencií: {inl_sum:,}")
if n_pairs:
    print(f"úspešnosť verifikácie  : {100*n_inl/n_pairs:.1f} %")
con.close()

# ─── 3. Registrácia ─────────────────────────────────────────────────────────
h("3. Registrácia snímok (rekonštrukcia)")
models = sorted([d for d in glob.glob(os.path.join(SPARSE, "*")) if os.path.isdir(d)])
if not models:
    print("❌ COLMAP nevytvoril žiadny model — rekonštrukcia úplne zlyhala.")
    sys.exit(1)

print(f"počet modelov          : {len(models)}"
      + ("   ⚠️ scéna je rozpadnutá na viac nespojených častí" if len(models) > 1 else ""))

all_frames = sorted(os.listdir(FRAMES_DIR))
total_frames = len(all_frames)
model_stats = []

for m in models:
    txt = m + "_txt"
    os.makedirs(txt, exist_ok=True)
    subprocess.run(["colmap", "model_converter", "--input_path", m,
                    "--output_path", txt, "--output_type", "TXT"],
                   check=True, capture_output=True)
    imgs = read_images_txt(os.path.join(txt, "images.txt"))
    n_pts = sum(1 for l in open(os.path.join(txt, "points3D.txt")) if not l.startswith("#"))
    model_stats.append((os.path.basename(m), imgs, n_pts))

model_stats.sort(key=lambda x: -len(x[1]))
for name, imgs, n_pts in model_stats:
    pct = 100 * len(imgs) / total_frames
    print(f"  model {name}: {len(imgs):4d}/{total_frames} snímok ({pct:5.1f} %), "
          f"{n_pts:,} 3D bodov")

main_name, main_imgs, main_pts = model_stats[0]
reg_all = set()
for _, imgs, _ in model_stats:
    reg_all |= set(imgs.keys())
print(f"\nzaregistrovaných spolu : {len(reg_all)}/{total_frames} "
      f"({100*len(reg_all)/total_frames:.1f} %)")
print(f"v najväčšom modeli     : {len(main_imgs)}/{total_frames} "
      f"({100*len(main_imgs)/total_frames:.1f} %)")

# ─── 4. Diery v čase ────────────────────────────────────────────────────────
h("4. Pokrytie v čase (kde rekonštrukcia vypadla)")
idx = {n: i for i, n in enumerate(all_frames)}
reg_mask = np.zeros(total_frames, dtype=bool)
for n in main_imgs:
    if n in idx:
        reg_mask[idx[n]] = True


def mmss(sec):
    return f"{int(sec//60)}:{int(sec%60):02d}"


# pás pokrytia
BAR = 100
bar = ""
for b in range(BAR):
    lo, hi = int(b*total_frames/BAR), int((b+1)*total_frames/BAR)
    frac = reg_mask[lo:hi].mean() if hi > lo else 0
    bar += "█" if frac > 0.9 else ("▓" if frac > 0.6 else ("░" if frac > 0.2 else "·"))
print(f"0:00 {bar} {mmss(total_frames/FPS)}")
print("     █ >90 % zaregistrované   ▓ 60-90 %   ░ 20-60 %   · takmer nič\n")

gaps, s = [], None
for i, r in enumerate(reg_mask):
    if not r and s is None:
        s = i
    elif r and s is not None:
        gaps.append((s, i-1)); s = None
if s is not None:
    gaps.append((s, total_frames-1))
big = [g for g in gaps if g[1]-g[0]+1 >= 4]
print(f"celkovo dier: {len(gaps)}, z toho súvislých ≥2 s: {len(big)}")
for a, b in sorted(big, key=lambda g: -(g[1]-g[0]))[:12]:
    n = b-a+1
    print(f"  {mmss(a/FPS)}–{mmss(b/FPS)}  ({n:3d} snímok, {n/FPS:5.1f} s)")

# ─── 5. Priestorové pokrytie ────────────────────────────────────────────────
h("5. Priestorové pokrytie (pôdorys z pozícií kamier)")
centers, order = [], []
for n in sorted(main_imgs.keys()):
    q, t, _ = main_imgs[n]
    R = qvec2rotmat(q)
    centers.append(-R.T @ t)
    order.append(idx.get(n, 0))
C = np.array(centers)
if len(C) < 3:
    print("príliš málo kamier na analýzu")
    sys.exit(0)

Cc = C - C.mean(0)
_, S, Vt = np.linalg.svd(Cc, full_matrices=False)
P = Cc @ Vt[:2].T          # projekcia do dominantnej roviny = pôdorys
print(f"rozptyl osí (SVD)      : {S[0]:.2f} / {S[1]:.2f} / {S[2]:.2f}")
print(f"rovinnosť trajektórie  : {S[2]/S[0]:.3f}  (nízke = jedno podlažie)")

W, H = 78, 26
mn, mx = P.min(0), P.max(0)
span = np.maximum(mx-mn, 1e-9)
grid = [[" "]*W for _ in range(H)]
for k, (x, y) in enumerate(P):
    gx = int((x-mn[0])/span[0]*(W-1))
    gy = int((y-mn[1])/span[1]*(H-1))
    frac = order[k]/max(total_frames-1, 1)
    grid[gy][gx] = "0123456789"[min(int(frac*10), 9)]
print("\npôdorys trajektórie (číslo = desatina videa, 0=začiatok, 9=koniec):")
print("┌" + "─"*W + "┐")
for row in grid:
    print("│" + "".join(row) + "│")
print("└" + "─"*W + "┘")

occ = sum(1 for r in grid for c in r if c != " ")
print(f"obsadených buniek      : {occ}/{W*H} ({100*occ/(W*H):.1f} %)")

# ─── 6. Kvalita pre Gaussian Splatting ──────────────────────────────────────
h("6. Ukazovatele kvality pre Gaussian Splatting")
n3d = np.array([v[2] for v in main_imgs.values()])
print(f"3D bodov v modeli      : {main_pts:,}")
print(f"pozorovaní na snímku   : priemer {n3d.mean():.0f}, medián {np.median(n3d):.0f}, "
      f"min {n3d.min()}")
thin = int((n3d < 100).sum())
print(f"snímok s <100 pozorovaniami: {thin} ({100*thin/max(len(n3d),1):.1f} %)")
print(f"bodov na snímku        : {main_pts/max(len(main_imgs),1):.0f}")
