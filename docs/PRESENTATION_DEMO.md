# LuxCore DMX Engine — Presentation technique
**Auteur : Martin Vert**

---

## Vue d'ensemble

LuxCore DMX Engine est un moteur de visualisation DMX/ArtNet temps réel developpe en Processing. Il recoit des donnees ArtNet (UDP port 6454) et rend jusqu'a 65 spots simultanees avec 15 formes geometriques, des blades inclinables, des effets PostFX et un fond colorise.

---

## Lancement rapide

```bash
# Show complet en boucle infinie : intro texte + intro blades + 15 formes + finale 5 actes
python3 demo_scripts/defile_formes.py

# Duree par forme personnalisee (ex: 4s)
python3 demo_scripts/defile_formes.py 127.0.0.1 4

# Animation typographique multi-scenes (boucle infinie)
python3 demo_scripts/artnet_text.py

# Validation systeme
python3 demo_scripts/system_validation.py
```

---

## Les 15 formes

| ID | Forme | Detail |
|---|---|---|
| 0 | Ellipse | cercle/ovale |
| 1 | Rectangle | rectangle plein |
| 2 | Texte | caracteres ASCII, police par spot via canal +22 |
| 3 | Triangle | polygone 3 cotes |
| 4 | Pentagone | 5 cotes |
| 5 | Hexagone | 6 cotes |
| 6 | Losange | diamant 4 cotes |
| 7 | Octogone | 8 cotes |
| 8 | Etoile | 5 branches, pointe vers le haut |
| 9 | Croix | polygone 12 vertices, contour vectoriel propre |
| 10 | Fleche | pointant vers le haut |
| 11 | Plus | polygone 12 vertices, bras fins |
| 12 | Coeur | formule parametrique, 72 vertices |
| 13 | Segment | ligne ouverte — size_pan=longueur, size_tilt/500=epaisseur px |
| 14 | Fleur | 6 petales, formule polaire, 180 vertices |

---

## Structure DMX

### Parametres de base (28 canaux, offset 0)

| Canaux | Parametre |
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
| 20 | Blend mode global |
| 21 | Blur A — size |
| 22 | Blur B — sigma |
| 23 | Pixelate |
| 24 | Sobel (bistable >128) |
| 25 | RGB Split |
| 26 | Saturation A |
| 27 | Saturation B |
| 28 | Chromatic aberration (bistable >128) |

### Parametres par spot (23 canaux, offset = 28 + spot_id x 23)

| Offset | Parametre | Resolution |
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
| +22 | Font index (0-255 -> clamp sur nb polices) | 8-bit |

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

# Centre ecran = 32767
# Rotation 180 degres = int(180 * 65535 / 360)
```

### Encodage texte (mode 2)

`size_tilt` encode le caractere ASCII. Utiliser `math.ceil()` obligatoirement :
```python
tilt_16bit = math.ceil(ord(c) * 65535 / 1000)
```
`int()` tronque et decale vers le caractere precedent.

---

## Capacite DMX

| Configuration | Spots max |
|---|---|
| 1 univers (512 oct.) | 21 spots |
| 2 univers (1024 oct.) | 43 spots |
| 3 univers (1536 oct.) | 65 spots |

---

## Polices disponibles (mode Texte)

20 polices TTF dans `data/fonts/`, indexees 0-19 via canal +22 :

| Index | Fichier | Style |
|---|---|---|
| 0 | Audiowide | circulaire/tech |
| 1 | BebasNeue | display condense |
| 2 | Cinzel | romain classique |
| 3 | Comfortaa-Bold | geometrique arrondi |
| 4 | DejaVuSans-Bold | sans-serif standard |
| 5 | DejaVuSans | sans-serif leger |
| 6 | DejaVuSansMono | monospace |
| 7 | DejaVuSerif | serif classique |
| 8 | Exo2-Bold | sci-fi propre |
| 9 | Montserrat-Bold | flat design moderne |
| 10 | Orbitron | futuriste geometrique |
| 11 | Oswald-Bold | condense puissant |
| 12 | Pacifico | script handwritten |
| 13 | PoiretOne | art deco fin |
| 14 | PressStart2P | pixel retro jeu |
| 15 | Raleway-ExtraBold | contraste extreme |
| 16 | Raleway-Light | elegance fine |
| 17 | Righteous | retro display |
| 18 | RobotoBold | sans-serif moderne |
| 19 | SpaceMono-Bold | monospace tech |

---

## Architecture fichiers

```
martz_artz_verctorz.pde       — Point d'entree Processing
definitions.pde               — Variables globales, constantes DMX
draw_functions.pde            — Pipeline rendu, font cache
artnet_functions.pde          — Reception ArtNet UDP, parsing DMX
gui_functions.pde             — Interface LazyGui
performance_optimization.pde  — Classe SpotData, pool 256 spots, 15 formes
z_fixture_definition.pde      — Documentation mapping DMX canal par canal

demo_scripts/
  luxcore_artnet.py           — Module partage : set16(), send_multi(), hsv(), char_tilt()
  defile_formes.py            — Show complet en boucle : intro texte (30s) + intro blades (20s)
                                + 15 formes (6-15s chacune) + finale 5 actes (180s)
                                19 spots, enable/blend creatifs par forme, 20 polices cyclees
  artnet_text.py              — Animation typographique : ArtNet/controled/generator/Martin VERT
  lettre_a.py                 — Affichage single char (test)
  system_validation.py        — Validation connexion et performances
```

---

## Performances mesurees

| Configuration | FPS moyen |
|---|---|
| 19 spots, defile formes | ~12-14 FPS |
| 48 spots, finale | ~12-14 FPS |
