# python_port — Spike de dé-risquage (portage moderngl)

Prototype **isolé** validant l'ossature du futur moteur Python. Il ne touche à
**aucun** fichier `.pde` du projet Processing.

But : prouver que la boucle temps-réel tient la cible avec, dans un **seul
process Python sans JVM**, les quatre capacités que Processing/py5 ne font pas
proprement :

1. contexte OpenGL possédé — **moderngl** (EGL standalone, marche sans fenêtre)
2. **vidéo décodée** (PyAV) → texture GL
3. post-effet **shader GLSL** (sobel, dose modulée par ArtNet)
4. lecture framebuffer → **sortie NDI** (cyndilib)
5. réception **ArtNet** UDP:6454 → canal 1 = intensité de l'effet

## Installation

Le runtime NDI (`libndi.so`) doit être présent sur le système (déjà le cas ici,
`/usr/local/lib/libndi.so.6`). Puis :

```bash
python3 -m venv --without-pip .venv          # (ensurepip absent sur py3.14)
curl -sS https://bootstrap.pypa.io/get-pip.py | .venv/bin/python
.venv/bin/python -m pip install -r requirements.txt
```

## Lancer

```bash
# mire procédurale, 1080p60, 20 s
.venv/bin/python spike_ndi.py

# vidéo réelle
.venv/bin/python spike_ndi.py --video ../ma_video.mp4 --width 1920 --height 1080 --fps 60

# jusqu'à Ctrl+C
.venv/bin/python spike_ndi.py --duration 0
```

Puis ouvrir un **récepteur NDI** (OBS + plugin NDI, vMix, Resolume, NDI Studio
Monitor) et sélectionner la source **`LuxCore-Spike`**.
Envoyer de l'ArtNet sur le canal 1 (p.ex. `demo_scripts/luxcore_artnet.py`) fait
varier la dose de sobel en direct.

## Résultats mesurés (Intel UHD 630, iGPU 2018 — quasi pire-cas)

| Résolution | FPS      | read (GL) | upload | send NDI (worker) | verdict |
|-----------:|---------:|----------:|-------:|------------------:|:--------|
| 1280×720   | **59.9** | 5.8 ms    | 2.4 ms | 16.5 ms           | **tient 60** |
| 1920×1080  | ~51.5    | 8.5 ms    | 4.9 ms | 19.2 ms           | ~52 fps |

Optimisations déjà intégrées : readback **PBO** double-buffer (async), envoi NDI
**asynchrone** délégué à un **worker thread** (triple-buffer). Le chemin critique
GL en 1080p n'est que 13.4 ms (80 % du budget) ; le plafond restant est l'étape
d'envoi NDI (~19 ms, largement fixe → *pacing* cyndilib, peu sensible à la
résolution).

## Pistes pour 1080p60 plein (non implémentées)

- **Sortie UYVY** (2 octets/pixel au lieu de 4 en RGBA) : conversion sur GPU
  dans un shader, NDI n'a plus à convertir. À valider (le coût d'envoi observé
  est surtout fixe, gain incertain).
- Toute GPU postérieure à 2018 (readback/upload bien plus rapides).
- `sender.clock_video` / réglage fin du rythme cyndilib.

## Conclusion

Architecture **validée** : les quatre sous-systèmes tournent ensemble en un seul
process Python natif. Aucun blocage architectural — la sortie NDI et le player
vidéo, impossibles proprement sous Processing/py5, sont ici de première classe.
