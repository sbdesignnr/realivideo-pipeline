#!/usr/bin/env bash
# Štartovací proces pre RunPod pod.
#
# Dôvod existencie: nvidia base image má ENTRYPOINT, ktorý vypíše banner a potom
# spustí CMD. Ak je CMD /bin/bash a nie je pripojený terminál, bash načíta EOF
# a hneď skončí -> kontajner zomrie -> RunPod ho reštartuje -> crash-loop.
# Kontajner teda musí držať bežať proces, ktorý sám od seba neskončí.

# --- SSH prístup -------------------------------------------------------------
# RunPod vkladá verejný kľúč do premennej PUBLIC_KEY.
if [ -n "${PUBLIC_KEY:-}" ]; then
    mkdir -p /root/.ssh
    echo "$PUBLIC_KEY" >> /root/.ssh/authorized_keys
    chmod 700 /root/.ssh
    chmod 600 /root/.ssh/authorized_keys
    echo "[start] SSH kľúč z PUBLIC_KEY nainštalovaný"
else
    echo "[start] PUBLIC_KEY nie je nastavený — SSH kľúčom nebude fungovať"
fi

# Hostiteľské kľúče sa generujú až tu, nie v image — inak by všetky pody
# zdieľali tie isté kľúče.
ssh-keygen -A >/dev/null 2>&1
mkdir -p /run/sshd
if /usr/sbin/sshd; then
    echo "[start] sshd beží na porte 22"
else
    echo "[start] ⚠️ sshd sa nepodarilo spustiť"
fi

# --- Vlastná kontrola, viditeľná v logoch podu -------------------------------
# Bez tohto by sme sa o nefunkčnej binárke dozvedeli až po pripojení cez SSH.
echo "[start] ---- kontrola prostredia ----"
if nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader 2>/dev/null; then :; else
    echo "[start] ⚠️ nvidia-smi nevidí GPU"
fi
if opensplat --help >/dev/null 2>&1; then
    echo "[start] ✅ opensplat sa spúšťa"
else
    echo "[start] ⚠️ opensplat NEBEŽÍ — výpis chyby:"
    opensplat --help 2>&1 | head -5
fi
command -v colmap >/dev/null && echo "[start] ✅ colmap: $(dpkg-query -W -f='${Version}' colmap 2>/dev/null)"
command -v ffmpeg >/dev/null && echo "[start] ✅ ffmpeg prítomný"
echo "[start] ---- pripravené, kontajner zostáva bežať ----"

# Toto je to, čo v pôvodnom Dockerfile chýbalo.
sleep infinity
