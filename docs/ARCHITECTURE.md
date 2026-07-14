# Architecture — LuxCore DMX Engine

**Auteur : Martin Vert**

Le moteur principal est un **portage Python / moderngl** (OpenGL) du sketch Processing
d'origine, avec **sortie NDI**. Il vit dans [`python_port/`](../python_port/) ; les
sources Processing sont archivées dans [`docs/processing/`](processing/).

Le mapping DMX est décrit dans [PROTOCOLE_DMX.md](PROTOCOLE_DMX.md).

---

## Flux de données

```
ArtNet UDP :6454  →  luxcore/artnet.py  →  dmx_buf  →  luxcore/dmx.py  →  engine.render()  →  FBO  →  NDI
```

Le **buffer DMX est la source de vérité**. `artnet.py` reçoit les paquets (thread,
multi-univers) et remplit `dmx_buf`. `dmx.py` décode 1:1 le buffer en un `BaseState`
+ une liste de `SpotState` (portage direct de `SpotData.update_from_dmx`).

---

## Pipeline de rendu (`luxcore/engine.py`)

`render(base, spots, bg_fix)` enchaîne :

1. **clear** — fond RGB (canaux 1-3)
2. **fond vidéo** — fixture de fond (slot 60) en mode 14, plein écran derrière tout
3. **spots** — formes / texte / vidéo / forme+vidéo, blend par spot, triangulation ear-clip
4. **PostFX** — `feedback → kaléido → pixelate → sobel → rgb split → saturation → bloom → chromatic`
5. **blades** — 8 couteaux de cadrage 16-bit
6. **blur des blades** — appliqué par-dessus les blades

Le rendu part dans un FBO, relu via PBO, puis envoyé en NDI.

### Post-effets (9)

Chaîne ping-pong FBO, dans l'ordre du pipeline ci-dessus :

| Effet | Canal | Note |
|---|---|---|
| Feedback / trails | 29 | FBO d'historique, `out = max(cur, hist × decay)` |
| Kaléidoscope | 32 | symétrie radiale à N branches (2-24) |
| Pixelate | 23 | |
| Sobel | 24 | bistable |
| RGB split | 25 | |
| Saturation A / B | 26-27 | |
| Bloom | 30-31 | bright-pass (seuil) → flou → additif (intensité) |
| Chromatic | 28 | bistable |
| Blur | 21-22 | appliqué après les blades |

---

## Sortie NDI

Rendu en FBO puis **readback PBO** vers un ring de buffers, encodé en **UYVY 4:2:2**
et publié comme source NDI **`LuxCore`** (visible dans OBS / vMix / Resolume). Le
plafond de performance est le readback NDI, pas le rendu OpenGL.

---

## Pipeline vidéo (`luxcore/video.py`)

- Décodage **PyAV**. Le moteur charge **toutes** les vidéos de `data/videos/` au
  démarrage : un décodeur + un anneau de 16 textures ≈ **~133 Mo VRAM/vidéo**,
  décodées en continu (coût CPU).
- **Sélection** : canal +22 d'une fixture en mode 14 (ou 100..113) choisit la source
  (dossier trié par nom).
- **Désync** : anneau de 16 frames ; plusieurs panneaux d'une même source lisent des
  frames décalées (effet d'écho).
- **Échelle** : ré-échelonnée pour permettre le plein écran malgré le plafond 1000 px
  du décodage de taille.
- **Forme+vidéo** (mode 100+forme) : la silhouette de la forme (triangulation ear-clip)
  sert de masque, texturé par la vidéo au lieu d'une couleur.
- **Garde-fou VRAM** : `--max-videos N` ne charge qu'au plus N vidéos (échantillonnées
  uniformément). Repère mesuré : 8 clips ≈ 52 fps, 16 ≈ 28 fps en aperçu.

Organisation des clips :

| Dossier | Rôle |
|---|---|
| `data/videos/` | jeu de travail **chargé** (8 clips de 10 s par défaut) |
| `data/clips_all/` | réserve de clips de 10 s (non chargée) |
| `data/videos_src/` | originaux (backup, non chargés) |

Découper une source en clips de 10 s (copie de flux, rapide) :

```bash
ffmpeg -i src.mp4 -c copy -an -map 0:v:0 -f segment -segment_time 10 \
       -reset_timestamps 1 data/clips_all/src_%03d.mp4
```

---

## Formes et géométrie (`luxcore/geometry.py`)

Les 14 formes sont définies comme polygones-unité puis remplies par **triangulation
ear-clip** (les formes concaves flèche/cœur sont correctement remplies). La **rafale**
(mode 13) est une étoile à 14 pointes fines (28 vertices), qui a remplacé l'ancienne
rosace « fleur ». Le **cœur** (mode 11) est paramétrique (72 vertices), la **croix**
(mode 9) un polygone à 12 vertices avec contour propre.

---

## Modules (`python_port/luxcore/`)

| Module | Rôle |
|---|---|
| `constants.py` | mapping DMX 0-indexé, LUT blend, enums formes/blend, `BG_FIXTURE_SLOT` |
| `dmx.py` | décodage 1:1 (`BaseState` + `SpotState`) |
| `artnet.py` | réception UDP multi-univers (thread) |
| `geometry.py` | 14 formes en polygones-unité + triangulation ear-clip (VBO) |
| `stroke.py` | ruban de contour (miter) + segment |
| `text.py` | cache de glyphes 20 polices (mode Texte) |
| `blades.py` | 8 valeurs 16-bit (4 couteaux de cadrage A/B/C/D) |
| `effects.py` | 9 post-effets GLSL 330 |
| `video.py` | décodage vidéo PyAV, anneau de désync |
| `engine.py` | pipeline de rendu complet |
| `gui.py` + `imgui_backend.py` | panneau imgui (config + status) |
| `run_engine.py` | boucle live : ArtNet → décodage → rendu → NDI + GUI |

---

## Performances

~45-56 fps à 1080p (48-60 fixtures) sur iGPU **Intel UHD 630** (2018). Le plafond est
le readback NDI, pas le rendu. Le nombre de vidéos chargées pèse fortement (décodage
CPU continu) : voir `--max-videos`.

---

Voir aussi : [Protocole DMX](PROTOCOLE_DMX.md) · [Guide des démos](DEMOS.md) ·
[Fixtures GDTF](GDTF.md).
