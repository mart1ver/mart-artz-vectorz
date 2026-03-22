# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commits Git
- Martin Vert (mart1ver@gmail.com) est l'UNIQUE auteur de ce code
- JAMAIS mentionner Claude, assistant, IA ou outils externes dans les commits
- JAMAIS ajouter de signatures "Generated with" ou "Co-Authored-By"
- Messages de commit UNIQUEMENT au nom de Martin
- Martin est le seul créateur et développeur reconnu

## Précautions CRITIQUES
- Ce code est le "bébé" de Martin — EXTRÊME PRUDENCE requise
- Changements UNIQUEMENT step-by-step sous contrôle de Martin
- TOUJOURS utiliser git pour traçabilité avant toute modification

## Projet
- Nom: LuxCore DMX Engine
- Ancien nom: Martz Artz Verctorz
- Type: Moteur de visualisation DMX/ArtNet temps réel en Processing
- Auteur: Martin Vert

---

## Commandes essentielles

### Lancer les scripts Python
```bash
python3 demo_scripts/defile_formes.py              # show complet ~5min
python3 demo_scripts/artnet_text.py                # animation typographique (boucle infinie, Ctrl+C pour quitter)
python3 demo_scripts/lettre_a.py                   # test single char
python3 -m py_compile demo_scripts/foo.py          # vérification syntaxe
```

### Processing
Ouvrir `martz_artz_verctorz.pde` dans Processing IDE, puis Ctrl+R pour lancer.
Le sketch s'ouvre en plein écran. Le nombre de spots se configure dans le GUI LazyGui.

---

## Architecture

### Flux de données
```
ArtNet UDP :6454  →  artnet_functions.pde  →  dmx_data[]  →  draw() pipeline
```
Le tableau `dmx_data` (byte[]) est la source de vérité. Tout le rendu lit depuis ce tableau à chaque frame.

### Boucle Processing (martz_artz_verctorz.pde)
```
draw() :
  do_artnet()          — lit le paquet ArtNet, remplit dmx_data[]
  do_background()      — fond RGB (canaux 1-3)
  do_blend_mode()      — blend mode global (canal 20)
  do_spots_optimized() — rendu des N spots via SpotData pool
  do_effects()         — PostFX : blur, pixelate, sobel, rgb split, saturation, chromatic
  do_blades()          — 8 couteaux (canaux 4-19, 16-bit)
  do_blade_blur()      — blur appliqué par-dessus les blades
```

### Structure DMX (512 octets max, univers 0)

**Base (28 canaux) :**
| Canaux | Paramètre |
|--------|-----------|
| 1-3 | RGB fond |
| 4-19 | 8 blades A1/A2/B1/B2/C1/C2/D1/D2 (16-bit chacun) |
| 20 | Blend mode global |
| 21-22 | Blur size / sigma (s'applique sur les blades aussi) |
| 23 | Pixelate |
| 24 | Sobel (bistable >128) |
| 25 | RGB Split |
| 26-27 | Saturation A / B |
| 28 | Chromatic aberration (bistable >128) |

**Par spot (20 canaux, offset = 28 + spot_id × 20) :**
| Offset | Paramètre | Résolution |
|--------|-----------|-----------|
| +0..+2 | RGB fill | 8-bit |
| +3 | Alpha | 8-bit |
| +4 | Stroke weight | 8-bit |
| +5 | Stroke alpha | 8-bit |
| +6..+8 | RGB stroke | 8-bit |
| +9..+10 | Taille Pan | 16-bit |
| +11..+12 | Taille Tilt | 16-bit |
| +13..+14 | Rotation | 16-bit |
| +15..+16 | Position Pan | 16-bit |
| +17..+18 | Position Tilt | 16-bit |
| +19 | Mode (forme 0-14) | 8-bit |

**Capacité max dans 512 octets :** (512 - 28) / 20 = **24 spots**

### Blend modes (Processing: `int(map(dmx, 0, 255, 1, 10))`)
Valeurs DMX exactes à envoyer :
`BLEND=0  ADD=29  SUBTRACT=57  DARKEST=85  LIGHTEST=114  DIFFERENCE=142  EXCLUSION=170  MULTIPLY=199  SCREEN=227  REPLACE=255`

Sur fond **noir** : ADD, BLEND, LIGHTEST, DIFFERENCE, EXCLUSION, SCREEN fonctionnent.
Sur fond **blanc** : BLEND, DIFFERENCE, EXCLUSION seulement (ADD/LIGHTEST/SCREEN → invisible).

### Les 15 formes (canal mode +19)
```
0 Ellipse   1 Rectangle  2 Texte      3 Triangle   4 Pentagone
5 Hexagone  6 Losange    7 Octogone   8 Étoile5    9 Croix
10 Flèche   11 Plus      12 Cœur      13 Segment    14 Fleur
```
Croix (9) et Plus (11) : polygones 12 vertices (contour propre, pas deux rectangles).
Cœur (12) : formule paramétrique, 72 vertices. Fleur (14) : polaire, 180 vertices.

### Encodage texte (mode 2)
`size_tilt` encode le caractère ASCII affiché via `byte(size_tilt)` dans Processing.
Utiliser **`math.ceil()`** (pas `int()`) pour éviter le glissement vers le char précédent :
```python
tilt_16bit = math.ceil(ord(c) * 65535 / 1000)
```

### Encodage 16-bit Python
```python
def set16(dmx, idx, val):
    val = max(0, min(65535, int(val)))
    dmx[idx]     = (val >> 8) & 0xFF
    dmx[idx + 1] = val & 0xFF
```
Centre écran = 32767. Positions pan/tilt mappées vers pixels selon la taille de la fenêtre.

### Paquet ArtNet
```python
header = b"Art-Net\x00"
pkt = header + (0x5000).to_bytes(2,'little') + bytes([0,14,0,0,0,0]) \
      + len(dmx).to_bytes(2,'big') + bytes(dmx)
sock.sendto(pkt, ("127.0.0.1", 6454))
```
Toujours clamper les valeurs : `bytes(max(0, min(255, int(v))) for v in dmx)`

### Fichiers Processing
- `performance_optimization.pde` — SpotData class + pool 256 spots + rendu des 15 formes
- `definitions.pde` — toutes les variables globales (`number_of_parameters_by_spots = 20`)
- `draw_functions.pde` — pipeline de rendu
- `artnet_functions.pde` — réception UDP et parsing DMX
- `z_fixture_definition.pde` — documentation de référence du mapping DMX (commentaires)

### Scripts Python
- `defile_formes.py` — show ~5min : `DefileFormes` class avec `demo_intro()`, `render_forme()`, `set_effects()`, `demo_finale()` (5 actes, 24 spots)
- `artnet_text.py` — typographie multi-scènes, durées variables par mot, forme arrière-plan par scène
