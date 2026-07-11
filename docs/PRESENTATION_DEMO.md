# LuxCore DMX Engine — Présentation technique
**Auteur : Martin Vert**

---

## Vue d'ensemble

LuxCore DMX Engine est un moteur de visualisation DMX/ArtNet temps réel. Le moteur
principal est un **portage Python / moderngl** (OpenGL) avec **sortie NDI**, dérivé
du sketch Processing d'origine (archivé dans `processing/`). Il reçoit des données
ArtNet (UDP port 6454) et rend des fixtures avec **14 formes** géométriques (dont la
vidéo), des blades inclinables, des effets PostFX et un fond colorisé ou vidéo.

---

## Lancement rapide

```bash
# moteur : aperçu écran + sortie NDI "LuxCore", piloté par ArtNet
python_port/.venv/bin/python python_port/run_engine.py --preview --spots 60 --duration 0

# piloter par ArtNet (127.0.0.1:6454)
python3 demo_scripts/defile_formes.py       # show complet en boucle (Ctrl+C)
python3 demo_scripts/artnet_text.py         # animation typographique
```
Aperçu : `g` = plein écran (curseur masqué + veille inhibée), `h` = menu.

---

## Les 14 formes (canal +19)

| ID | Forme | Détail |
|---|---|---|
| 0 | Ellipse | cercle/ovale |
| 1 | Rectangle | rectangle plein |
| 2 | Texte | caractères ASCII, police par fixture via canal +22 |
| 3 | Triangle | polygone 3 côtés |
| 4 | Pentagone | 5 côtés |
| 5 | Hexagone | 6 côtés |
| 6 | Losange | diamant 4 côtés |
| 7 | Octogone | 8 côtés |
| 8 | Étoile | 5 branches |
| 9 | Croix | polygone 12 vertices, contour propre |
| 10 | Flèche | remplissage ear-clip (concave correct) |
| 11 | Cœur | formule paramétrique, 72 vertices |
| 12 | Segment | ligne ouverte — size_pan=longueur, size_tilt/500=épaisseur px |
| 13 | Fleur | 6 pétales, formule polaire, 180 vertices |
| 14 | **Vidéo** | quad texturé par une vidéo du dossier (sélection via +22) |

> L'ancienne forme « Plus » a été retirée lors du portage (doublon de la Croix).

---

## Structure DMX

### Paramètres de base (32 canaux, offset 0)

| Canaux | Paramètre |
|---|---|
| 1-3 | RGB background |
| 4-19 | 8 blades 16-bit (A1/A2/B1/B2/C1/C2/D1/D2) |
| 20 | Blend mode global |
| 21-22 | Blur size / sigma |
| 23 | Pixelate |
| 24 | Sobel (bistable >128) |
| 25 | RGB Split |
| 26-27 | Saturation A / B |
| 28 | Chromatic aberration (bistable >128) |
| 29 | Feedback / trails (persistance) |
| 30 | Bloom seuil |
| 31 | Bloom intensité |
| 32 | Kaléidoscope (2-24 branches) |

### Paramètres par fixture (23 canaux, offset = 32 + spot_id × 23)

| Offset | Paramètre | Résolution |
|---|---|---|
| +0 +1 +2 | RGB fill | 8-bit |
| +3 | Alpha | 8-bit |
| +4 | Stroke weight | 8-bit |
| +5 | Stroke alpha | 8-bit |
| +6 +7 +8 | RGB stroke | 8-bit |
| +9 +10 | Taille Pan | 16-bit |
| +11 +12 | Taille Tilt | 16-bit |
| +13 +14 | Rotation | 16-bit |
| +15 +16 | Position Pan | 16-bit |
| +17 +18 | Position Tilt | 16-bit |
| +19 | Mode (forme 0-14) | 8-bit |
| +20 | Enable (0=off, 1-255=on) | 8-bit |
| +21 | Blend mode individuel (0=global, sinon LUT) | 8-bit |
| +22 | **mode Texte : police** · **mode VIDEO : sélecteur de vidéo** | 8-bit |

### Fixture unifiée + fond vidéo

- **Une seule sorte de fixture.** Le mode `+19 = 14` (VIDEO) transforme n'importe
  quelle fixture en panneau vidéo : la vidéo du dossier `data/videos/` est choisie
  par le canal `+22`, et la taille est ré-échelonnée (plein écran possible).
- **Désynchronisation** : chaque vidéo garde un anneau de ses dernières frames ;
  plusieurs panneaux d'une même source échantillonnent des frames décalées.
- **Fixture de fond** (slot réservé **60**) : en mode 14, vidéo plein écran derrière
  tous les spots (choisie par +22, `alpha` pour la fondre avec la couleur RGB).

### Blend modes — valeurs DMX exactes

```
BLEND=0  ADD=29  SUBTRACT=57  DARKEST=85  LIGHTEST=114
DIFFERENCE=142  EXCLUSION=170  MULTIPLY=199  SCREEN=227  REPLACE=255
```
Sur fond **noir** : ADD, BLEND, LIGHTEST, DIFFERENCE, EXCLUSION, SCREEN fonctionnent.
Sur fond **blanc** : BLEND, DIFFERENCE, EXCLUSION seulement.

### Encodage Python 16-bit

```python
def set16(dmx, idx, val):
    val = max(0, min(65535, int(val)))
    dmx[idx]     = (val >> 8) & 0xFF
    dmx[idx + 1] = val & 0xFF
# Centre écran = 32767 ; Rotation 180° = int(180 * 65535 / 360)
```

### Encodage texte (mode 2)

`size_tilt` encode le caractère ASCII. Utiliser `math.ceil()` obligatoirement :
```python
tilt_16bit = math.ceil(ord(c) * 65535 / 1000)   # int() tronque et décale
```

---

## Capacité DMX

| Configuration | Fixtures max |
|---|---|
| 1 univers (512 oct.) | 21 |
| 2 univers (1024 oct.) | 43 |
| 3 univers (1536 oct.) | 65 |

---

## Polices disponibles (mode Texte, canal +22)

20 polices TTF dans `data/fonts/`, chargées par `luxcore/text.py` :
Audiowide · BebasNeue · Cinzel · Comfortaa-Bold · DejaVuSans-Bold · DejaVuSans ·
DejaVuSansMono · DejaVuSerif · Exo2-Bold · Montserrat-Bold · Orbitron · Oswald-Bold ·
Pacifico · PoiretOne · PressStart2P · Raleway-ExtraBold · Raleway-Light · Righteous ·
RobotoBold · SpaceMono-Bold

---

## Architecture fichiers

```
python_port/
  run_engine.py               — boucle live : ArtNet → décodage → rendu → NDI + GUI
  luxcore/
    constants.py              — mapping DMX, LUT blend, enums, BG_FIXTURE_SLOT
    dmx.py                    — décodage BaseState + SpotState
    artnet.py                 — réception ArtNet UDP multi-univers
    geometry.py               — 14 formes + triangulation ear-clip
    stroke.py / text.py       — contour, glyphes 20 polices
    blades.py / effects.py    — couteaux 16-bit, 6 post-effets GLSL
    video.py                  — décodage vidéo PyAV
    engine.py                 — pipeline de rendu complet
    gui.py / imgui_backend.py — panneau imgui
  tests/                      — 45 tests (décodage, géométrie, GL, effets…)

demo_scripts/
  luxcore_artnet.py           — module partagé : set16(), send_multi(), hsv(), char_tilt()
  defile_formes.py            — show complet en boucle (intro texte + blades + 14 formes + finale)
  artnet_text.py              — animation typographique multi-scènes

data/                         — fonts/, videos/, gui/
docs/processing/              — sources Processing d'origine (archive)
```

---

## Performances

~55-60 FPS à 1080p (48-60 fixtures) sur iGPU Intel UHD 630 (2018). Le plafond est le
readback NDI, pas le rendu. Sortie NDI `LuxCore` visible dans OBS / vMix / Resolume.
