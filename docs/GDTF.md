# Fixtures GDTF — LuxCore DMX Engine

**Auteur : Martin Vert**

Le dossier [`gdtf/`](../gdtf/) fournit deux profils **GDTF** (Generic Device Type
Format, ANSI E1.75) pour importer LuxCore dans une console ou un logiciel lumière
(grandMA, Hog, QLC+, Capture…). Un `.gdtf` est un ZIP contenant `description.xml`.

Le mapping complet est décrit dans [PROTOCOLE_DMX.md](PROTOCOLE_DMX.md) ; les profils
GDTF en sont le reflet côté console.

---

## Les deux profils

| Fichier | Mode | Contenu |
|---|---|---|
| `LuxCore_Base_32ch.gdtf` | `32ch` | fond RGB, 8 blades 16-bit, blend global, 9 PostFX (canaux 1-32) |
| `LuxCore_Spot_23ch.gdtf` | `23ch` | une fixture (RGB, alpha, stroke, taille/rotation/position 16-bit, mode, enable, blend, police/vidéo) |

Le canal **Mode** du spot expose des **valeurs littérales** (le moteur lit l'octet
brut) : `0..14` = formes (dont 13 = Rafale, 14 = Vidéo) et `100..113` = forme remplie
par la vidéo. Le canal **Kaléido** de la base modélise `Off` (0-1) puis `Branches`
(2-255).

---

## Adressage (patch console)

- **Base** → adresse 1
- **Spot N** → adresse `32 + N × 23 + 1`
  (Spot0 = 33, Spot1 = 56, Spot2 = 79, …)

La base occupe les 32 premiers canaux de l'univers ; chaque spot est patché 23 canaux
plus loin. Voir la sortie du générateur pour le rappel des adresses.

---

## Régénération

**Ne jamais éditer les `.gdtf` (ZIP) à la main.** Le générateur
[`gdtf/generate_gdtf.py`](../gdtf/generate_gdtf.py) est la **source unique** : il
reconstruit les deux ZIP.

```bash
python3 gdtf/generate_gdtf.py
```

## Vérification

```bash
# base : 24 DMXChannels (20 + 4 PostFX), mode "32ch"
unzip -p gdtf/LuxCore_Base_32ch.gdtf description.xml | grep -c '<DMXChannel '
unzip -p gdtf/LuxCore_Base_32ch.gdtf description.xml | grep 'DMXMode Name'

# spot : présence de VIDEO (14) et de la bande forme+vidéo (100..113)
unzip -p gdtf/LuxCore_Spot_23ch.gdtf description.xml | grep -E 'DMXFrom="(14|100|113)/1"'

# XML bien formé
python3 -c "import zipfile,xml.dom.minidom as m; \
[m.parseString(zipfile.ZipFile('gdtf/'+f).read('description.xml')) \
 for f in ('LuxCore_Base_32ch.gdtf','LuxCore_Spot_23ch.gdtf')]; print('XML OK')"
```

---

Voir aussi : [Protocole DMX](PROTOCOLE_DMX.md) · [Architecture](ARCHITECTURE.md).
