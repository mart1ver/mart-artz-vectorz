# Fixtures GDTF — LuxCore DMX Engine

**Auteur : Martin Vert**

Le dossier [`gdtf/`](../gdtf/) fournit deux profils **GDTF** (Generic Device Type
Format, ANSI E1.75) pour importer LuxCore dans une console ou un logiciel lumière
(grandMA, Hog, QLC+, Capture, Depence…). Un `.gdtf` est un ZIP contenant un unique
`description.xml`, inspectable via `unzip -p <fichier> description.xml`.

Le mapping DMX complet est décrit dans [PROTOCOLE_DMX.md](PROTOCOLE_DMX.md) ; les
profils GDTF en sont le reflet côté console.

---

## Les deux profils

| Fichier | Taille | DMXMode | `<DMXChannel>` | Empreinte DMX |
|---------|--------|---------|----------------|---------------|
| `LuxCore_Base_32ch.gdtf` | 2384 o | `Name="32ch"` | **24** | 32 canaux (offsets 1→32) |
| `LuxCore_Spot_23ch.gdtf` | 2679 o | `Name="23ch"` | **18** | 23 canaux (offsets 1→23) |
| `generate_gdtf.py` | 36678 o | — (source unique) | — | — |

Les deux `.gdtf` présents dans `gdtf/` correspondent **exactement** à la sortie
actuelle du générateur.

> **DMXChannels ≠ canaux DMX.** Le nombre d'éléments `<DMXChannel>` est inférieur
> à l'empreinte parce que les paires 16-bit portent un offset à deux octets
> (ex. `Offset="4 5"`). Ne pas confondre les deux comptages : 24 DMXChannels pour
> 32 canaux (Base), 18 DMXChannels pour 23 canaux (Spot).

### `LuxCore_Base_32ch.gdtf` — 24 DMXChannels, empreinte 32 canaux

Bloc de base : RGB de fond, 8 blades 16-bit et les canaux PostFX. Les 8 blades
sont en 16-bit. Offsets présents :

```
1, 2, 3, [4 5], [6 7], [8 9], [10 11], [12 13], [14 15], [16 17], [18 19],
20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32
```

Mapping (1-based, patch) :

| Canaux | Paramètre |
|--------|-----------|
| 1-3 | RGB fond |
| 4-19 | 8 blades 16-bit A1 / A2 / B1 / B2 / C1 / C2 / D1 / D2 |
| 20 | Blend mode global (10 ChannelSets, BLEND=0 … REPLACE=255) |
| 21-22 | Blur size / sigma |
| 23 | Pixelate |
| 24 | Sobel (bistable) |
| 25 | RGB Split |
| 26-27 | Saturation A / Vibrance B |
| 28 | Chromatic aberration (bistable) |
| 29 | Feedback |
| 30 | Bloom seuil |
| 31 | Bloom intensité |
| 32 | Kaléidoscope |

Le canal Blend (20) porte 10 ChannelSets, un par mode :
`BLEND=0 · ADD=29 · SUBTRACT=57 · DARKEST=85 · LIGHTEST=114 · DIFFERENCE=142 ·
EXCLUSION=170 · MULTIPLY=199 · SCREEN=227 · REPLACE=255`.

### `LuxCore_Spot_23ch.gdtf` — 18 DMXChannels, empreinte 23 canaux

Bloc par fixture. 5 paires 16-bit (Size Pan/Tilt, Rotation, Pos Pan/Tilt).
Offsets présents :

```
1, 2, 3, 4, 5, 6, 7, 8, 9, [10 11], [12 13], [14 15], [16 17], [18 19],
20, 21, 22, 23
```

Mapping (offset 1-based dans la fixture) :

| Offset | Paramètre | Résolution |
|--------|-----------|-----------|
| 1-3 | RGB fill — *mode VIDEO : vitesse / départ / flags transport* | 8-bit |
| 4 | Alpha | 8-bit |
| 5 | Stroke weight — *mode VIDEO : point de fin (out)* | 8-bit |
| 6 | Stroke alpha — *mode VIDEO : groupe de sync* | 8-bit |
| 7-9 | RGB stroke — *mode VIDEO : offset 7 = strobe/hold* | 8-bit |
| 10-11 | Size Pan (largeur) | 16-bit |
| 12-13 | Size Tilt (hauteur ; mode Texte : code ASCII) | 16-bit |
| 14-15 | Rotation | 16-bit |
| 16-17 | Pos Pan (X) | 16-bit |
| 18-19 | Pos Tilt (Y) | 16-bit |
| 20 | **Mode** (forme) | 8-bit |
| 21 | Enable | 8-bit |
| 22 | Blend individuel | 8-bit |
| 23 | Police (mode Texte) / sélecteur vidéo (mode VIDEO) | 8-bit |

> **Transport vidéo** : en mode VIDEO (Mode = 14 ou 100..113), les canaux fill (1-3) et
> stroke (5-7) — inutiles — pilotent la lecture par spot (voir *Transport vidéo* dans
> [PROTOCOLE_DMX.md](PROTOCOLE_DMX.md)). Le générateur nomme ces ChannelFunctions en
> double (« Fill Red / Video Speed », etc.). Défauts à 0 = play 1× loop.

---

## Canal Mode (Spot, offset 20) — valeurs LITTÉRALES

Le moteur lit **l'octet brut** de ce canal. Le générateur le déclare en
conséquence : `PhysicalTo="113"`, `Snap="Yes"` et **30 ChannelSets** en valeurs
littérales (`DMXFrom=n/1`). Il ne faut SURTOUT PAS ajouter d'échelle ni
d'interpolation sur ce canal — chaque valeur doit rester envoyée telle quelle.

### Formes — 0..14

| Val | Forme | Val | Forme |
|-----|-------|-----|-------|
| 0 | Ellipse | 8 | Étoile (5 branches) |
| 1 | Rectangle | 9 | Croix |
| 2 | Texte | 10 | Flèche |
| 3 | Triangle | 11 | Cœur |
| 4 | Pentagone | 12 | Segment |
| 5 | Hexagone | 13 | Rafale (étoile 14 pointes) |
| 6 | Losange | 14 | VIDEO (quad texturé plein écran) |
| 7 | Octogone | | |

### Zone Rectangle — 15..99

Toute valeur `15..99` retombe sur **Rectangle** (ChannelSet unique déclaré à
`DMXFrom="15/1"`, cohérent avec le `default` du switch moteur : hors 0..14 et hors
bande 100..113 → RECTANGLE).

### Bande « forme remplie par la vidéo » — 100..113

`Mode = 100 + forme` (forme ∈ 0..13) → plage **100..113**. Le spot prend la
silhouette de la forme (triangulation) mais est texturé par la vidéo (source
choisie par le canal 23) au lieu d'une couleur unie :

- 100 = Ellipse + vidéo
- 103 = Triangle + vidéo
- 113 = Rafale + vidéo

Cette bande est rétrocompatible : les modes 0..14 sont inchangés.

### Bistables (seuil On = 128)

Les deux ChannelSets « Off / On » bistables — Sobel (Base canal 24) et Chromatic
(Base canal 28) — déclarent le seuil On à **128**, exactement cohérent avec le
décodage moteur `raw > 128` : un octet ≤ 128 laisse l'effet OFF.

---

## Adressage (patch console, 1-based)

- **Base** → adresse **1**
- **Spot N** → adresse **32 + N × 23 + 1**

La base occupe les 32 premiers canaux de l'univers ; chaque spot est patché 23
canaux plus loin, l'adresse DMX 1-based ajoutant le **+1** :

| Spot | Adresse |
|------|---------|
| Spot 0 | 33 |
| Spot 1 | 56 |
| Spot 2 | 79 |
| Spot N | 32 + N × 23 + 1 |

> **Erreur classique.** Oublier le **+1**. En code (base 0), l'adresse de départ
> d'un spot est `32 + N × 23` (index du tableau) ; en patch DMX (base 1), on ajoute
> +1. Les deux décrivent le même octet — voir la convention d'indexation dans
> [PROTOCOLE_DMX.md](PROTOCOLE_DMX.md).

Capacité : **20 spots / univers**, 43 sur 2 univers, 65 sur 3.

---

## FixtureTypeID (UUID des ZIP présents)

- Spot : `9afa5603-54da-4de0-933e-9df07433cdbf`
- Base : `48971068-bdc9-49c1-acc6-29323a401e40`

Chaque exécution du générateur régénère un nouvel UUID (`str(uuid.uuid4())`) : les
octets du ZIP diffèrent à chaque run, mais la structure reste identique. Un diff
binaire après régénération est donc **normal**. Pour comparer deux versions, on
diffuse le `description.xml` en ignorant la ligne FixtureTypeID.

---

## Régénération (source unique — ne JAMAIS éditer les ZIP à la main)

Le générateur [`gdtf/generate_gdtf.py`](../gdtf/generate_gdtf.py) est la **seule
source de vérité** : il reconstruit les deux ZIP. On ne patche jamais un `.gdtf`
à la main — toute retouche manuelle diverge irréversiblement de la source.

```bash
python3 gdtf/generate_gdtf.py    # réécrit les 2 .gdtf + rappel de patch et valeurs de blend
```

Le générateur est déjà correct et testé. Les deux `.gdtf` présents dans `gdtf/`
sont sa sortie fidèle — il n'y a rien à réécrire, seulement à régénérer si l'on
modifie la source.

---

## Vérification

```bash
# Le générateur compile
python3 -m py_compile gdtf/generate_gdtf.py

# Nombre de DMXChannels (attendu : Base=24, Spot=18)
unzip -p gdtf/LuxCore_Base_32ch.gdtf description.xml | grep -c '<DMXChannel '
unzip -p gdtf/LuxCore_Spot_23ch.gdtf description.xml | grep -c '<DMXChannel '

# DMXMode de chaque profil
unzip -p gdtf/LuxCore_Base_32ch.gdtf description.xml | grep 'DMXMode Name'
unzip -p gdtf/LuxCore_Spot_23ch.gdtf description.xml | grep 'DMXMode Name'

# Empreinte DMX (offsets présents)
unzip -p gdtf/LuxCore_Spot_23ch.gdtf description.xml | grep -oE 'Offset="[0-9 ]+"'

# Canal Mode : bande littérale 0..14 + 100..113
unzip -p gdtf/LuxCore_Spot_23ch.gdtf description.xml | grep -E 'DMXFrom="(14|100|113)/1"'

# XML bien formé (les deux description.xml doivent se parser sans erreur)
python3 -c "import zipfile,xml.dom.minidom as m; \
[m.parseString(zipfile.ZipFile('gdtf/'+f).read('description.xml')) \
 for f in ('LuxCore_Base_32ch.gdtf','LuxCore_Spot_23ch.gdtf')]; print('XML OK')"
```

Comptages attendus : **Base = 24** DMXChannels, **Spot = 18** DMXChannels.

---

Voir aussi : [Protocole DMX](PROTOCOLE_DMX.md) · [Architecture](ARCHITECTURE.md) · [Démos](DEMOS.md)
