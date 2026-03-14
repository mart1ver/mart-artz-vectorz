# LuxCore DMX Engine — Présentation technique
**Auteur : Martin Vert**

---

## Vue d'ensemble

LuxCore DMX Engine est un moteur de visualisation DMX/ArtNet temps réel développé en Processing. Il reçoit des données ArtNet (UDP port 6454) et rend jusqu'à 256 spots simultanés avec 15 formes géométriques, des blades inclinables, des effets PostFX et un fond colorisé.

---

## Lancement rapide

```bash
# Show complet ~5min : intro + défilé 15 formes + finale 5 actes
python3 demo_scripts/defile_formes.py

# Défilé rapide (4s par forme)
python3 demo_scripts/defile_formes.py 127.0.0.1 4

# Animation typographique multi-scènes (boucle infinie)
python3 demo_scripts/artnet_text.py

# Validation système
python3 demo_scripts/system_validation.py
```

---

## Les 15 formes

| ID | Forme | Détail |
|---|---|---|
| 0 | Ellipse | — |
| 1 | Rectangle | — |
| 2 | Texte | Caractères ASCII |
| 3 | Triangle | — |
| 4 | Pentagone | 5 côtés |
| 5 | Hexagone | 6 côtés |
| 6 | Losange | Diamant 4 côtés |
| 7 | Octogone | 8 côtés |
| 8 | Étoile | 5 branches, pointe vers le haut |
| 9 | Croix | Polygone 12 vertices, contour vectoriel propre |
| 10 | Flèche | Pointant vers le haut |
| 11 | Plus | ✚ polygone 12 vertices, bras fins |
| 12 | Cœur | Formule paramétrique, 72 vertices |
| 13 | Éclair | ⚡ 6 vertices remplis |
| 14 | Fleur | 6 pétales, formule polaire, 180 vertices |

---

## Structure DMX

### Paramètres de base (28 canaux, offset 0)

| Canaux | Paramètre |
|---|---|
| 1-3 | RGB background |
| 4-5 | Blade A1 16-bit (top gauche) |
| 6-7 | Blade A2 16-bit (top droite) |
| 8-9 | Blade B1 16-bit (droite haut) |
| 10-11 | Blade B2 16-bit (droite bas) |
| 12-13 | Blade C1 16-bit (bas gauche) |
| 14-15 | Blade C2 16-bit (bas droite) |
| 16-17 | Blade D1 16-bit (gauche haut) |
| 18-19 | Blade D2 16-bit (gauche bas) |
| 20 | Blend mode |
| 21 | Blur A — size |
| 22 | Blur B — sigma |
| 23 | Pixelate |
| 24 | Sobel (bistable >128) |
| 25 | RGB Split |
| 26 | Saturation A |
| 27 | Saturation B |
| 28 | Chromatic aberration (bistable >128) |

### Paramètres par spot (20 canaux, offset = 28 + spot_id × 20)

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

### Encodage Python 16-bit

```python
# Rotation (0-360°)
rot16 = int(rotation_deg * 65535 / 360)
dmx[base+13] = (rot16 >> 8) & 0xFF
dmx[base+14] = rot16 & 0xFF

# Position (0-65535, centre = 32767)
dmx[base+15] = (pan >> 8) & 0xFF
dmx[base+16] = pan & 0xFF
```

---

## Performances

| Spots actifs | FPS mesuré |
|---|---|
| 7 | ~49 FPS |
| 50 | ~47-49 FPS |
| 256 (max) | non testé |

---

## Architecture fichiers

```
martz_artz_verctorz.pde       — Point d'entrée Processing
definitions.pde               — Variables globales, constantes DMX
draw_functions.pde            — Rendu spots, blades, effets PostFX
artnet_functions.pde          — Réception ArtNet UDP
gui_functions.pde             — Interface LazyGui
sys_functions.pde             — Multi-écran, clavier
error_handling.pde            — Validation DMX, fallback
performance_optimization.pde  — Pool 256 spots, 15 formes, caching
z_fixture_definition.pde      — Documentation mapping DMX

demo_scripts/
  defile_formes.py            — Show complet : intro + défilé 15 formes + finale 5 actes (180s)
  artnet_text.py              — Animation typographique : ArtNet/controled/generator/made by:/Martin VERT
  lettre_a.py                 — Affichage single char (script de test)
  system_validation.py        — Validation connexion et performances
```

---

## Notes techniques

### Encodage texte (mode 2)
`size_tilt` encode le caractère ASCII affiché. Utiliser `math.ceil()` (pas `int()`) :
```python
tilt_16bit = math.ceil(ord(c) * 65535 / 1000)
```
`int()` tronque et décale vers le caractère précédent.

### Blend modes compatibles fond noir
ADD(29), BLEND(0), SCREEN(227), LIGHTEST(114), DIFFERENCE(142), EXCLUSION(170)
DARKEST(85), MULTIPLY(199), SUBTRACT(57) → invisible sur fond noir.

### Blend modes compatibles fond blanc
BLEND(0), DIFFERENCE(142), EXCLUSION(170)
ADD(29), LIGHTEST(114), SCREEN(227) → rouge/couleur vive disparaît sur blanc.

### Capacité DMX univers 0
Max 24 spots dans 512 octets : (512 - 28) / 20 = 24.2
