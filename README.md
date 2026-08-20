# realivideo-pipeline

Jadro pipeline: video-prechádzka z telefónu → cinematic "dronové" video.

```
video.mp4
  │
  ├─ ffmpeg          extrakcia snímok (deduplikácia, rozlíšenie)
  ├─ COLMAP          Structure-from-Motion → pozície kamery + riedky mrak bodov   [CPU]
  ├─ OpenSplat       tréning 3D Gaussian Splatting scény → .ply / .splat          [GPU]
  ├─ render          naskriptovaná kamerová dráha cez scénu → snímky              [GPU]
  └─ ffmpeg          grading, hudba, branding → finálne video
```

Tento repozitár zatiaľ pokrýva **prostredie** (Docker image-y). Samotné kroky
pipeline pribudnú ako ďalšie.

## Dva image-y, nie jeden

| | `Dockerfile.cpu` | `Dockerfile.gpu` |
|---|---|---|
| Obsah | COLMAP, ffmpeg | COLMAP, ffmpeg, CUDA, libtorch, OpenSplat |
| Veľkosť | **931 MB** (overené) | ~15 GB (odhad) |
| Beží na | čomkoľvek (aj Apple Silicon) | NVIDIA GPU, x86_64 |
| Zostaviteľné na tvojom Macu | **áno** (overené, 3m38s) | **nie** |

COLMAP je CPU-bound, takže nedáva zmysel držať GPU pod vyťažený počas SfM.
Rozdelenie zároveň znamená, že polovicu pipeline vieš testovať doma.

GPU image obsahuje COLMAP tiež — v prvej verzii chceš vedieť spustiť všetko na
jednom pode. Odštiepiť SfM na lacnejší CPU pod je optimalizácia na neskôr.

## Lokálne (MacBook)

```bash
make build-cpu     # zostaví CPU image natívne pre arm64
make smoke-cpu     # overí, že COLMAP naozaj beží headless na CPU
make shell-cpu     # shell v kontajneri, data/ namountované
```

## Kde zostaviť GPU image

Na Apple Silicon sa zostaviť **nedá**: libtorch s CUDA existuje len pre x86_64
a kompilácia CUDA kernelov pod QEMU emuláciou je nepoužiteľne pomalá.
Možnosti, zoradené podľa toho, ako málo sa s nimi narobíš:

1. **GitHub Actions** → push do `ghcr.io`. Zadarmo, x86_64, reprodukovateľné,
   RunPod si image potiahne priamo z registry. Runner má cca 14 GB voľných na
   `/`, čo je na tento image tesné — treba krok na uvoľnenie miesta.
2. **Lacný x86 VPS na hodinu** (Hetzner CPX41 a pod., rádovo centy). Plná
   kontrola, dosť disku, build 30–60 min, potom `docker push` a server zrušíš.
3. **Runtime inštalácia na RunPode** — vezmeš hotový PyTorch template a
   OpenSplat skompiluješ až v pode. Najrýchlejšie k prvému výsledku, ale
   kompiluje sa to znova pri každom novom pode.

## Verzie a prečo práve tieto

- `CUDA 12.1.1` + `libtorch 2.2.1+cu121` — kombinácia, ktorú OpenSplat sám
  testuje. Meniť jedno bez druhého sa nedá.
- `OPENSPLAT_REF=v1.1.6` — pripnutý tag, nie `main`.
- `CMAKE_CUDA_ARCHITECTURES="86;89"` — 89 je RTX 4090 / L40S, 86 je RTX 3090 /
  A5000 ako záloha, keď 4090 nie je na RunPode voľná. Upstream default
  (`70;75;80`) by na 4090 **nefungoval**.
- Ubuntu 24.04 v CPU image (COLMAP 3.9.1), Ubuntu 22.04 v GPU image (COLMAP
  3.7) — GPU image je viazaný na CUDA 12.1, ktorá 24.04 nepodporuje.

## Poznámky k COLMAP

Ubuntu balík je zostavený **bez CUDA**. Preto vždy:

```bash
colmap feature_extractor --SiftExtraction.use_gpu 0 ...
colmap exhaustive_matcher --SiftMatching.use_gpu 0 ...
```

Bez toho sa COLMAP pokúsi otvoriť GPU/GL kontext a v kontajneri spadne.

## Skripty pipeline

| skript | čo robí |
|---|---|
| `scripts/assess-video.sh` | **Rýchle premeranie vstupu (~2 min)** — jas, ostrosť, počty featureov na vzorke snímok. Spúšťať PRED plným behom. |
| `scripts/run-colmap.sh` | Celý SfM: feature_extractor → matcher → mapper → analyzer. Parametre cez premenné prostredia. |
| `scripts/analyze-colmap.py` | Rozbor výsledku: registrácia, diery v čase, pôdorys trajektórie, ukazovatele pre GS. |
| `scripts/coverage-detail.py` | Rozlíši snímky neregistrované vôbec od tých v odtrhnutom fragmente. |
| `scripts/chain-strength.py` | Sila sekvenčného reťazca — inliery medzi susednými snímkami. |
| `scripts/compare-runs.py` | Postaví viac behov vedľa seba. |
| `scripts/smoke-test-cpu.sh` | Overí, že COLMAP + ffmpeg v image fungujú. |

Príklad:

```bash
docker run --rm -v "$HOME/Downloads:/input:ro" -v "$PWD/data:/workspace/data" \
  -v "$PWD/scripts:/workspace/scripts:ro" realivideo-cpu:dev \
  bash /workspace/scripts/assess-video.sh /input/VIDEO.MOV /workspace/data/assess 0.5
```

## Čo sme zatiaľ namerali

Dva testovacie behy, **oba neúspešné** — žiadna scéna zatiaľ nie je pripravená
na OpenSplat:

| | staré video (tmavý byt) | nové video (svetlý byt) |
|---|---|---|
| snímok | 628 | 480 |
| jas medián | 84 | 154 |
| rozmazanie medián | 4,99 | 5,52 |
| featureov medián | 1 548 | 806 |
| registrovaných | 70,5 % | 41,5 % |
| v najväčšom modeli | 26,9 % | 19,4 % |

Poučenia:

- **Jas je nutná, nie postačujúca podmienka.** Druhé video malo 100 % snímok nad
  prahom, ktorý v prvom videu predikoval 93 % úspešnosť — a dopadlo horšie.
  Rovnomerne osvetlená biela stena je svetlá a zároveň bez textúry.
- **Textúra scény rozhoduje viac než osvetlenie.** Mieriť na nábytok, koberce,
  kuchynské linky, kresbu podlahy — nie na prázdne steny.
- **30 fps len do šera.** V svetlom priestore dlhší expozičný čas iba pridá
  motion blur; tam patrí 60 fps.
- **Na CPU regulovať kvalitu cez `max_image_size`.** `max_num_features` strop
  nedrží a znižovanie `peak_threshold` rozstrelí cenu matchovania kvadraticky.
