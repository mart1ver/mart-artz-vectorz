# Protocole DMX / ArtNet — LuxCore DMX Engine

**Auteur : Martin Vert** (mart1ver@gmail.com)

Référence unique et exhaustive du protocole DMX / ArtNet du moteur **LuxCore**. Toutes
les autres pages renvoient ici plutôt que de recopier les tableaux de canaux.

> **Source de vérité :** le code fait foi — [`python_port/luxcore/constants.py`](../python_port/luxcore/constants.py)
> (mapping, LUT, enums, `BG_FIXTURE_SLOT`) et [`python_port/luxcore/dmx.py`](../python_port/luxcore/dmx.py)
> (décodage 1:1). Cette page en est le **miroir lisible** : en cas de divergence,
> `constants.py` gagne.

---

## Vue d'ensemble

| Élément | Valeur |
|---------|--------|
| Transport | ArtNet, **UDP port 6454** (OpDmx `0x5000`), cible par défaut `127.0.0.1` |
| Univers | 0..8 (`MAX_UNIVERSES = 9`), Port-Address 15-bit standard |
| Taille d'un univers | 512 octets (`UNIVERSE_SIZE`) |
| Buffer DMX complet | `512 × 9 = 4608` octets |
| Bloc de base | **32 canaux** (`NUM_BASE_PARAMETERS`), au tout début de l'univers 0 |
| Bloc par fixture / spot | **23 canaux** (`NUM_PARAMS_PER_SPOT`) |
| Capacité | `(512 − 32) / 23 =` **20 fixtures / univers** (43 sur 2, 65 sur 3) |
| Fixture de fond | slot réservé **60** (`BG_FIXTURE_SLOT`, adresse 1412) |
| Sortie | **NDI « LuxCore »** en UYVY 4:2:2 (par défaut 1920×1080 @ 60) |

Le buffer DMX est la **source de vérité** : l'ArtNet arrive dans `artnet.py` (thread
UDP), `dmx.py` décode chaque canal, `engine.py` rend l'image, puis la frame part en NDI.

Adresse du 1ᵉʳ canal d'un spot : `spot_base_addr(id) = 32 + id × 23`. Garder `num_spots ≤ 60`.

### Convention d'indexation — 0-based vs 1-based

> Le **CODE** est en **base 0** : c'est l'index du tableau `dmx_data[]` (le premier canal
> est l'index `0`). Une console DMX (et `CLAUDE.md`, et le patch GDTF) numérote les canaux
> à partir de **1**. Exemples :
> - « RGB fond 1-3 » (1-based) = index **0-2** (0-based).
> - « PostFX 29-32 » (1-based) = index **28-31** (0-based).
>
> Les deux conventions désignent exactement les mêmes octets. Le bloc de base ci-dessous
> est donné en **canal 1-based** ; les spots en **offset 0-based** relatif à leur adresse.
> Ne jamais confondre les deux comptages.

---

## Tailles globales (`constants.py`)

| Constante | Valeur | Sens |
|-----------|--------|------|
| `NUM_BASE_PARAMETERS` | 32 | bloc de base (28 d'origine + 4 PostFX) |
| `NUM_PARAMS_PER_SPOT` | 23 | canaux par fixture / spot |
| `UNIVERSE_SIZE` | 512 | octets par univers |
| `MAX_UNIVERSES` | 9 | univers 0..8 → buffer `512 × 9 = 4608` octets |
| `BG_FIXTURE_SLOT` | 60 | fixture de fond, adresse `32 + 60×23 = 1412` (univers 2, offset 388) |

---

## Bloc de base — 32 canaux (index 0..31, 0-based)

| Index | Canal | Constante | Paramètre | Décodage |
|-------|-------|-----------|-----------|----------|
| 0 | 1 | `CH_BG_R` | Fond R | `& 0xFF` |
| 1 | 2 | `CH_BG_G` | Fond G | `& 0xFF` |
| 2 | 3 | `CH_BG_B` | Fond B | `& 0xFF` |
| 3..18 | 4-19 | `BLADE_BASE_OFFSET` = 3 | 8 blades 16-bit (A1,A2,B1,B2,C1,C2,D1,D2) | `u16(buf, 3 + 2·i)`, i = 0..7 |
| 19 | 20 | `CH_BLEND_GLOBAL` | Blend mode global | `BLEND_LUT[raw]` |
| 20 | 21 | `CH_BLUR_SIZE` | Blur size | `& 0xFF` |
| 21 | 22 | `CH_BLUR_SIGMA` | Blur sigma | `& 0xFF` |
| 22 | 23 | `CH_PIXELATE` | Pixelate | `& 0xFF` |
| 23 | 24 | `CH_SOBEL` | Sobel | **bistable** `raw > 128` |
| 24 | 25 | `CH_RGB_SPLIT` | RGB split | `& 0xFF` |
| 25 | 26 | `CH_SATURATION_A` | Saturation A | `& 0xFF` |
| 26 | 27 | `CH_SATURATION_B` | Saturation B (vibrance) | `& 0xFF` |
| 27 | 28 | `CH_CHROMATIC` | Chromatic aberration | **bistable** `raw > 128` |
| 28 | 29 | `CH_FEEDBACK` | Feedback / traînées (0 = off) | `& 0xFF` |
| 29 | 30 | `CH_BLOOM_THRESHOLD` | Bloom seuil (luminance glow) | `& 0xFF` |
| 30 | 31 | `CH_BLOOM_AMOUNT` | Bloom intensité (0 = off) | `& 0xFF` |
| 31 | 32 | `CH_KALEIDO` | Kaléidoscope (0/1 = off, 2-255 = branches) | `& 0xFF` |

Les 4 « couteaux » physiques A/B/C/D sont pilotés par **8 valeurs 16-bit** (2 par couteau),
soit les canaux 4 à 19 (blur des canaux 21-22 s'applique aussi sur les blades).

> **PostFX ajoutés.** Les 4 canaux PostFX occupent les index **28..31** (canaux 29..32),
> dans l'ordre : Feedback (28) · Bloom seuil (29) · Bloom intensité (30) · Kaléidoscope (31).
>
> **Bistables (> 128) :** Sobel (index 23) et Chromatic (index 27) — un octet ≤ 128 les laisse OFF.
>
> **Kaléido :** 0 ET 1 = off ; seules les valeurs 2..255 activent (nombre de branches).

---

## Bloc par fixture / spot — 23 canaux

Offset relatif à `base_addr = 32 + id × 23`.

| Offset | Constante | Paramètre | Résolution / mapping |
|--------|-----------|-----------|----------------------|
| +0 | `SP_FILL_R` | Fill R — **mode VIDEO : vitesse** (`SP_VID_SPEED`) | 8-bit |
| +1 | `SP_FILL_G` | Fill G — **mode VIDEO : point de départ (in)** (`SP_VID_IN`) | 8-bit |
| +2 | `SP_FILL_B` | Fill B — **mode VIDEO : flags transport** (`SP_VID_FLAGS`) | 8-bit |
| +3 | `SP_ALPHA` | Alpha | 8-bit |
| +4 | `SP_STROKE_WEIGHT` | Stroke weight — **mode VIDEO : point de fin (out)** (`SP_VID_OUT`) | 8-bit |
| +5 | `SP_STROKE_ALPHA` | Stroke alpha — **mode VIDEO : groupe de sync** (`SP_VID_SYNC`) | 8-bit |
| +6 | `SP_STROKE_R` | Stroke R — **mode VIDEO : strobe/hold** (`SP_VID_STROBE`) | 8-bit |
| +7 | `SP_STROKE_G` | Stroke G | 8-bit |
| +8 | `SP_STROKE_B` | Stroke B | 8-bit |
| +9..+10 | `SP_SIZE_PAN` = 9 | Taille Pan (largeur) | 16-bit → `map(0..65535 → 0..1000)` |
| +11..+12 | `SP_SIZE_TILT` = 11 | Taille Tilt (hauteur ; **mode Texte : code ASCII**) | 16-bit → `map(0..65535 → 0..1000)` |
| +13..+14 | `SP_ROTATION` = 13 | Rotation | 16-bit → `map(0..65535 → 0..360)` deg |
| +15..+16 | `SP_POS_PAN` = 15 | Position Pan (X) | 16-bit → `map(0..65535 → −255−half_w, 255+half_w)`, **32767 = centre** |
| +17..+18 | `SP_POS_TILT` = 17 | Position Tilt (Y) | 16-bit → `map(0..65535 → −255−half_h, 255+half_h)`, **32767 = centre** |
| +19 | `SP_MODE` | Mode / forme (octet brut 0..255) | voir modes ci-dessous |
| +20 | `SP_ENABLE` | Enable | `raw > 0` = on |
| +21 | `SP_BLEND` | Blend individuel | `0` = blend global, sinon `BLEND_LUT[raw]` |
| +22 | `SP_FONT` | mode Texte : **police** ; mode VIDEO / forme+vidéo : **sélecteur vidéo** (`sel_raw` brut) | voir font_index |

`font_index` (mode Texte) : `font_index = (raw × max(1, n_fonts)) // 256`, puis
`clamp(0, n_fonts − 1)`. `sel_raw` = même octet +22 brut, réinterprété en mode VIDEO par
l'engine. Le canal +22 a donc un **double sens**.

### Transport vidéo — canaux réinterprétés en mode VIDEO (14 et 100..113)

En mode vidéo, les canaux **fill (+0..+2)** et **stroke (+4..+6)** — morts (la vidéo
fournit la couleur, pas de contour) — pilotent la **lecture par spot** (playhead virtuel
côté engine). **Tous les défauts sont à 0 = « lecture 1× en boucle depuis le début »**,
donc tout contenu DMX existant continue de jouer normalement. Conséquence : un spot en
**forme+vidéo** (100..113) n'a plus de contour (canaux stroke réutilisés).

| Offset | Constante | Rôle | Encodage |
|--------|-----------|------|----------|
| +0 | `SP_VID_SPEED` | Vitesse | `0` = 1× (défaut) ; sinon `2^((raw−128)/64)` → **128 ≈ 1×**, ≈ 0.25×..4× |
| +1 | `SP_VID_IN` | Point de départ (in) | `raw/255` → 0..100 % du clip |
| +2 | `SP_VID_FLAGS` | Flags | bits 0-1 transport (`0/3`=play, `1`=pause, `2`=stop) · bit 2 sens (`1`=arrière) · bits 3-4 loop (`0`=loop, `1`=once, `2`=ping-pong) |
| +4 | `SP_VID_OUT` | Point de fin (out) | `raw/255` → 0..100 % ; `0` = fin du clip (défaut) |
| +5 | `SP_VID_SYNC` | Groupe de sync | `0` = indépendant ; `1..255` = spots partageant un playhead (même source) |
| +6 | `SP_VID_STROBE` | Strobe / hold | `0` = off ; `N` = fige sur des paliers de N frames |

Le moteur décode chaque clip **entièrement en cache** et calcule, par spot, sa tête de
lecture : `pos += sens · vitesse · fps · dt` (bornée à la région `[in, out]` selon le mode
de boucle), puis échantillonne `cache[round(pos)]`.

Le mapping position pan/tilt dépend de la taille de la fenêtre (`half_w`/`half_h`) et
**n'est pas clampé** (`pmap` = map Processing sans borne).

**Règle drawable :** `is_drawable()` = `enabled AND alpha > 0` — un spot est ignoré sinon.

---

## Canal Mode (+19, `SP_MODE`) — 15 modes + bande forme+vidéo

Le moteur lit l'**octet brut**.

### Formes 0..14

| Val | Forme (enum `Shape`) | | Val | Forme |
|-----|----------------------|---|-----|-------|
| 0 | Ellipse | | 8 | Étoile (5 branches) |
| 1 | Rectangle | | 9 | Croix (12 vertices) |
| 2 | Texte | | 10 | Flèche |
| 3 | Triangle | | 11 | Cœur (72 vertices) |
| 4 | Pentagone | | 12 | Segment (ligne ouverte) |
| 5 | Hexagone | | 13 | **Rafale** (étoile 14 pointes, 28 vertices) |
| 6 | Losange | | 14 | **Vidéo** (quad texturé, source = +22) |
| 7 | Octogone | | | |

`MAX_SHAPE_MODE = 14`. Toute valeur hors 0..14 (et hors bande 100..113) tombe dans le
`default` du switch → **RECTANGLE**. La forme « Plus » de l'ère Processing a été retirée
au portage.

### Bande « forme remplie par la vidéo » — `VIDEO_FILL_MODE_BASE = 100`

`+19 = 100 + forme` avec forme ∈ 0..13 → plage **100..113**. Le spot prend la
**silhouette** de la forme (triangulation) mais est **texturé par la vidéo** (source via
+22) au lieu d'une couleur unie. Rétrocompatible : les modes 0..14 restent inchangés.

- `video_fill` = vrai si `100 ≤ mode ≤ 113`.
- Forme effective : si `video_fill`, soustraire 100 ; sinon mode brut. Hors 0..14 → RECTANGLE.
- Exemples : `100` = ellipse vidéo, `103` = triangle vidéo, `113` = rafale vidéo.

---

## Fixture unifiée & fond vidéo

- **Une seule sorte de fixture** (23 canaux). Le canal `+19` la transforme : `14` (VIDEO)
  en fait un panneau vidéo (source via +22, échelle plein écran possible), et la bande
  `100..113` la texture d'une vidéo dans la silhouette d'une forme.
- **Lecture par spot** : chaque vidéo est décodée en cache mémoire ; chaque spot tient
  son propre playhead (start / vitesse / pause / loop, cf. *Transport vidéo* ci-dessus).
  Des spots d'un même **groupe de sync** (+5) partagent un playhead.
- **Fixture de fond** : slot réservé **60** (`BG_FIXTURE_SLOT`), même layout 23 canaux
  qu'un spot, adresse `bg_fixture_base_addr() = spot_base_addr(60) = 1412`. Dessinée
  **DERRIÈRE** tous les spots ; en mode 14 (VIDEO) = vidéo plein écran choisie par +22 ;
  sinon le fond reste la couleur RGB des canaux de base 0-2.

---

## Blend modes — enum + LUT

Ordre `BlendMode` (index 0..9) : BLEND=0, ADD=1, SUBTRACT=2, DARKEST=3, LIGHTEST=4,
DIFFERENCE=5, EXCLUSION=6, MULTIPLY=7, SCREEN=8, REPLACE=9.

Valeurs DMX exactes `BLEND_DMX_VALUES` (à envoyer sur le canal de base 20 / offset +21) :

| Mode | DMX | | Mode | DMX |
|------|-----|---|------|-----|
| BLEND | 0 | | DIFFERENCE | 142 |
| ADD | 29 | | EXCLUSION | 170 |
| SUBTRACT | 57 | | MULTIPLY | 199 |
| DARKEST | 85 | | SCREEN | 227 |
| LIGHTEST | 114 | | REPLACE | 255 |

`BLEND_LUT[256]` : LUT plus-proche-voisin DMX 0-255 → BlendMode. Tie-break **strict**
(`dist < best_dist`) : au point médian, l'index **inférieur** gagne (14 → BLEND, 15 → ADD).

**Compatibilité fond :**
- sur fond **noir** : ADD, BLEND, LIGHTEST, DIFFERENCE, EXCLUSION, SCREEN fonctionnent ;
- sur fond **blanc** : seuls BLEND, DIFFERENCE, EXCLUSION (ADD/LIGHTEST/SCREEN → invisibles).

---

## Encodages

### 16-bit big-endian

Lecture `u16(buf, i) = (buf[i] << 8) | buf[i+1]` (MSB en premier). Écriture :

```python
def set16(dmx, idx, val):
    val = max(0, min(65535, int(val)))
    dmx[idx]     = (val >> 8) & 0xFF   # MSB
    dmx[idx + 1] = val & 0xFF          # LSB
# Centre écran = 32767 ; rotation 180° = int(180 * 65535 / 360)
```

### Texte (mode 2)

Le caractère est encodé dans `size_tilt` (+11/+12). En envoi, `math.ceil` est
**OBLIGATOIRE** (pas `int`, qui tronque et glisse au caractère précédent) :

```python
tilt_16bit = math.ceil(ord(c) * 65535 / 1000)
```

Décodage moteur : `text_char = chr(int(size_tilt) & 0xFF)`, où
`size_tilt = map(tilt_16, 0..65535 → 0..1000)`.

### Paquet ArtNet (OpDmx, port 6454)

```python
header = b"Art-Net\x00"
pkt = header + (0x5000).to_bytes(2, 'little') + bytes([0, 14, 0, 0, 0, 0]) \
      + len(dmx).to_bytes(2, 'big') + bytes(dmx)
sock.sendto(pkt, ("127.0.0.1", 6454))
```

Toujours clamper l'octet : `bytes(max(0, min(255, int(v))) for v in dmx)`. L'univers est
lu en **Port-Address 15-bit standard** (octets 14/15) ; pour un multi-univers, découper le
buffer en tranches de 512 octets (u0 → 0-511, u1 → 512-1023, …).

---

## Capacité DMX

`(512 − 32) / 23 =` **20 fixtures / univers**.

| Configuration | Fixtures max |
|---------------|--------------|
| 1 univers (512 oct.) | **20** |
| 2 univers | 43 |
| 3 univers | 65 |

Adresse du 1ᵉʳ canal d'un spot : `spot_base_addr(id) = 32 + id × 23`. Garder `num_spots ≤ 60`.

---

## Polices disponibles (mode Texte, canal +22)

20 fichiers TTF dans `data/fonts/`, chargés au démarrage par `luxcore/text.py`, triés
alphabétiquement et indexés via `font_index = (raw × max(1, n_fonts)) // 256` :

Audiowide · BebasNeue · Cinzel · Comfortaa-Bold · DejaVuSans-Bold · DejaVuSans ·
DejaVuSansMono · DejaVuSerif · Exo2-Bold · Montserrat-Bold · Orbitron · Oswald-Bold ·
Pacifico · PoiretOne · PressStart2P · Raleway-ExtraBold · Raleway-Light · Righteous ·
RobotoBold · SpaceMono-Bold.

---

## Rappel 0-based vs 1-based

- **Code / décodage** : 0-based (index de `dmx_data[]`, offsets relatifs pour les spots).
- **Console DMX / `CLAUDE.md` / patch GDTF** : 1-based (numéro de canal).
- Bloc de base : index 0-based `0..31` = canaux 1-based `1..32`.
- Spot : offset `+n` = canal 1-based `n+1` dans la fixture ; adresse absolue de patch
  `32 + id×23 + 1` (Spot0 = 33, Spot1 = 56…). Erreur classique : oublier le **+1**.

---

Voir aussi : [Architecture](ARCHITECTURE.md) · [Guide des démos](DEMOS.md) ·
[Fixtures GDTF](GDTF.md).
