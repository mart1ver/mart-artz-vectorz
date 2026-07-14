# Protocole DMX / ArtNet — LuxCore DMX Engine

**Auteur : Martin Vert**

Référence unique du protocole. Toutes les autres pages renvoient ici plutôt que de
recopier les tableaux de canaux. La **source de vérité** reste le code
([`python_port/luxcore/constants.py`](../python_port/luxcore/constants.py) et
[`dmx.py`](../python_port/luxcore/dmx.py)) ; cette page en est le miroir lisible.

---

## Vue d'ensemble

| Élément | Valeur |
|---|---|
| Transport | ArtNet UDP, port **6454**, cible par défaut `127.0.0.1` |
| Univers | 0 à 8 (`MAX_UNIVERSES = 9`), buffer 512 × 9 = 4608 octets |
| Bloc de base | **32 canaux** (fond + blades + 9 PostFX), au tout début de l'univers 0 |
| Par fixture | **23 canaux** ; adresse du 1ᵉʳ canal = `32 + spot_id × 23` |
| Capacité | **20 fixtures/univers** — 43 sur 2, 65 sur 3 |
| Fixture de fond | slot réservé **60** (`BG_FIXTURE_SLOT`, adresse 1412) |
| Sortie | **NDI « LuxCore »** (UYVY 4:2:2) |

> **0-based vs 1-based.** Le code indexe le tableau d'octets à partir de 0. Une
> console DMX numérote les canaux à partir de 1. Les tableaux ci-dessous donnent le
> **canal 1-based** (colonne « Canal ») et l'**offset 0-based** relatif au spot.

---

## Bloc de base — 32 canaux

| Canal | Paramètre | Détail |
|---|---|---|
| 1-3 | **RGB fond** | couleur d'arrière-plan |
| 4-19 | **8 blades 16-bit** | A1, A2, B1, B2, C1, C2, D1, D2 (2 octets chacun) |
| 20 | Blend mode global | via LUT (voir plus bas) |
| 21-22 | Blur size / sigma | s'applique aussi sur les blades |
| 23 | Pixelate | |
| 24 | Sobel | **bistable** (> 128 = on) |
| 25 | RGB Split | |
| 26-27 | Saturation A / B | |
| 28 | Chromatic aberration | **bistable** (> 128 = on) |
| 29 | **Feedback / trails** | 0 = off, sinon persistance |
| 30 | **Bloom seuil** | luminance du glow |
| 31 | **Bloom intensité** | 0 = off, sinon force du halo |
| 32 | **Kaléidoscope** | 0/1 = off, 2-24 = nombre de branches |

Les canaux 29-32 sont les 4 PostFX ajoutés lors du portage (le bloc est passé de 28
à 32 canaux). Les 4 « couteaux » physiques A/B/C/D sont pilotés par **8 valeurs
16-bit** (2 par couteau), soit les canaux 4 à 19.

---

## Par fixture — 23 canaux

Adresse absolue du 1ᵉʳ canal = `32 + spot_id × 23`.

| Offset | Paramètre | Résolution |
|---|---|---|
| +0..+2 | RGB fill | 8-bit |
| +3 | Alpha | 8-bit |
| +4 | Stroke weight | 8-bit |
| +5 | Stroke alpha | 8-bit |
| +6..+8 | RGB stroke | 8-bit |
| +9..+10 | Taille Pan (largeur) | 16-bit → 0..1000 |
| +11..+12 | Taille Tilt (hauteur) ; **mode Texte : code ASCII** | 16-bit |
| +13..+14 | Rotation | 16-bit → 0..360° |
| +15..+16 | Position Pan (X), 32767 = centre | 16-bit |
| +17..+18 | Position Tilt (Y), 32767 = centre | 16-bit |
| +19 | **Mode / forme** | 8-bit (octet brut) |
| +20 | Enable (0 = off, > 0 = on) | 8-bit |
| +21 | Blend mode individuel (0 = global, sinon LUT) | 8-bit |
| +22 | **mode Texte : police** · **mode VIDEO / forme+vidéo : sélecteur de vidéo** | 8-bit |

Une fixture est *dessinée* si elle est activée **et** `alpha > 0`.

---

## Canal Mode (+19)

Le moteur lit l'**octet brut**. Deux plages :

### Formes 0..14

| Val | Forme | | Val | Forme |
|---|---|---|---|---|
| 0 | Ellipse | | 8 | Étoile (5 branches) |
| 1 | Rectangle | | 9 | Croix (12 vertices) |
| 2 | Texte | | 10 | Flèche |
| 3 | Triangle | | 11 | Cœur (72 vertices) |
| 4 | Pentagone | | 12 | Segment (ligne ouverte) |
| 5 | Hexagone | | 13 | **Rafale** (étoile 14 pointes, 28 vertices) |
| 6 | Losange | | 14 | **Vidéo** (quad texturé, source = +22) |
| 7 | Octogone | | | |

Toute valeur hors 0..14 (et hors plage vidéo ci-dessous) retombe sur **Rectangle**.
La forme « Plus » de l'ère Processing a été retirée au portage.

### Forme remplie par la vidéo : 100 + forme (100..113)

`+19 = 100 + forme` → le spot prend la **silhouette** de la forme mais est **texturé
par la vidéo** (source via +22) au lieu d'une couleur unie.

```
100 Ellipse+vid   103 Triangle+vid   106 Losange+vid   109 Croix+vid    112 Segment+vid
101 Rect+vid      104 Penta+vid      107 Octo+vid      110 Fleche+vid   113 Rafale+vid
102 Texte+vid     105 Hexa+vid       108 Etoile+vid    111 Coeur+vid
```

Rétrocompatible : les modes 0..14 sont inchangés. (114 n'est pas traité : le mode 14
est déjà la vidéo plein quad.)

---

## Fixture unifiée + fond vidéo

- **Une seule sorte de fixture.** Le mode `+19 = 14` (VIDEO) transforme n'importe
  quelle fixture en panneau vidéo : la vidéo de `data/videos/` est choisie par `+22`,
  la taille est ré-échelonnée (plein écran possible).
- **Désynchronisation** : chaque vidéo garde un anneau de ses 16 dernières frames ;
  plusieurs panneaux d'une même source échantillonnent des frames décalées.
- **Fixture de fond** (slot **60**) : en mode 14, vidéo plein écran **derrière** tous
  les spots (source via +22, `alpha` pour la fondre avec la couleur RGB). Garder
  `num_spots <= 60`.

---

## Blend modes — valeurs DMX exactes

```
BLEND=0  ADD=29  SUBTRACT=57  DARKEST=85  LIGHTEST=114
DIFFERENCE=142  EXCLUSION=170  MULTIPLY=199  SCREEN=227  REPLACE=255
```

La LUT choisit le mode le plus proche (plus proche voisin). Sur fond **noir** :
ADD, BLEND, LIGHTEST, DIFFERENCE, EXCLUSION, SCREEN fonctionnent. Sur fond **blanc** :
BLEND, DIFFERENCE, EXCLUSION seulement (ADD/LIGHTEST/SCREEN → invisibles).

---

## Encodages

### 16-bit

```python
def set16(dmx, idx, val):
    val = max(0, min(65535, int(val)))
    dmx[idx]     = (val >> 8) & 0xFF
    dmx[idx + 1] = val & 0xFF
# Centre écran = 32767 ; rotation 180° = int(180 * 65535 / 360)
```

### Texte (mode 2)

`size_tilt` (+11..+12) encode le caractère ASCII. Utiliser **`math.ceil()`** — `int()`
tronque et décale d'un caractère :

```python
tilt_16bit = math.ceil(ord(c) * 65535 / 1000)
```

### Paquet ArtNet

```python
header = b"Art-Net\x00"
pkt = header + (0x5000).to_bytes(2, 'little') + bytes([0, 14, 0, 0, 0, 0]) \
      + len(dmx).to_bytes(2, 'big') + bytes(dmx)
sock.sendto(pkt, ("127.0.0.1", 6454))
```

Toujours clamper : `bytes(max(0, min(255, int(v))) for v in dmx)`.

---

## Capacité DMX

| Configuration | Fixtures max |
|---|---|
| 1 univers (512 oct.) | **20** — `(512 − 32) / 23 = 20,86` |
| 2 univers | 43 |
| 3 univers | 65 |

---

## Polices (mode Texte, canal +22)

20 polices TTF dans `data/fonts/`, chargées par `luxcore/text.py` :
Audiowide · BebasNeue · Cinzel · Comfortaa-Bold · DejaVuSans-Bold · DejaVuSans ·
DejaVuSansMono · DejaVuSerif · Exo2-Bold · Montserrat-Bold · Orbitron · Oswald-Bold ·
Pacifico · PoiretOne · PressStart2P · Raleway-ExtraBold · Raleway-Light · Righteous ·
RobotoBold · SpaceMono-Bold.

---

Voir aussi : [Architecture](ARCHITECTURE.md) · [Guide des démos](DEMOS.md) ·
[Fixtures GDTF](GDTF.md).
