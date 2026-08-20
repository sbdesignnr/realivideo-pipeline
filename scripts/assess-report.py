#!/usr/bin/env python3
"""Vypíše namerané hodnoty a postaví ich vedľa dvoch známych behov."""
import sys, re, sqlite3
import numpy as np
W = sys.argv[1]


def load(path, key):
    return np.array(sorted(float(x) for x in re.findall(key + r"=([0-9.]+)", open(path).read())))


Y = load(W + "/bright.txt", r"lavfi\.signalstats\.YAVG")
B = load(W + "/blur.txt", r"lavfi\.blur")
con = sqlite3.connect(W + "/sample.db")
K = np.array(sorted(r for (r,) in con.execute("SELECT rows FROM keypoints")))
con.close()


def q(v, p):
    return v[min(int(len(v)*p), len(v)-1)] if len(v) else float("nan")


# referenčné hodnoty z dvoch odmeraných behov (obidva SKONČILI NEÚSPEŠNE)
REF = [
    ("staré 60fps", 84, 4.99, 1548, "27 % v najväčšom modeli"),
    ("nové 30fps",  154, 5.52, 806, "19 % v najväčšom modeli"),
]

print("\n\033[1mNamerané\033[0m")
print("─" * 68)
print(f"{'jas (Y) medián':28}{q(Y,.5):8.0f}    10. perc. {q(Y,.1):5.0f}   min {Y.min() if len(Y) else 0:5.0f}")
print(f"{'rozmazanie medián':28}{q(B,.5):8.2f}    90. perc. {q(B,.9):5.2f}   max {B.max() if len(B) else 0:5.2f}")
print(f"{'featureov medián':28}{q(K,.5):8.0f}    10. perc. {q(K,.1):5.0f}   min {K.min() if len(K) else 0:5.0f}")
print(f"{'snímok pod 500 featureov':28}{100*(K<500).mean() if len(K) else 0:7.1f} %")

print("\n\033[1mPorovnanie s doteraz odmeranými behmi\033[0m")
print("─" * 68)
print(f"{'':16}{'jas':>8}{'rozmaz.':>10}{'featury':>10}   výsledok")
for name, y, b, k, res in REF:
    print(f"{name:16}{y:>8}{b:>10.2f}{k:>10}   {res}")
print(f"\033[1m{'toto video':16}{q(Y,.5):>8.0f}{q(B,.5):>10.2f}{q(K,.5):>10.0f}   ?\033[0m")

print("""
\033[33mPozor na interpretáciu:\033[0m obidva referenčné behy DOPADLI ZLE, takže zatiaľ
nemáme príklad úspešnej scény. Tieto čísla hovoria "lepšie/horšie než dva
neúspešné pokusy", nie "prejde/neprejde". Kalibrovať sa to dá až po prvom
behu, ktorý naozaj vyjde.
""")
