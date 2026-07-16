# LuxCore DMX Engine

Moteur de visualisation **DMX / ArtNet temps réel** : il reçoit des paquets ArtNet UDP et
compose sur GPU des **formes vectorielles** et de la **vidéo**, animées canal par canal,
avec une **sortie NDI** prête à mixer. Le buffer DMX est la source de vérité — le rendu le
suit image par image.

**Auteur :** Martin Vert 

Le moteur principal est le **portage Python / moderngl** (OpenGL + NDI), dans
[`python_port/`](python_port/). Le sketch **Processing** d'origine est archivé dans
[`docs/processing/`](docs/processing/) à titre de référence.

---

## Démarrage rapide

```bash
# 1. moteur : aperçu écran + GUI + sortie NDI "LuxCore", piloté par ArtNet
python_port/.venv/bin/python python_port/run_engine.py --preview --spots 60 --duration 0
#    headless (NDI seul) : retirer --preview

# 2. envoyer de l'ArtNet (127.0.0.1:6454) — p.ex. le show complet, en boucle (Ctrl+C)
python3 demo_scripts/defile_formes.py
```

Aperçu : **`g`** = plein écran (curseur masqué + veille inhibée), **`h`** = menu.
Installation détaillée du moteur : [`python_port/README.md`](python_port/README.md).

---

## Capacités

| Domaine | Détail |
|---------|--------|
| **14 formes** | Ellipse, Rectangle, Texte, Triangle, Pentagone, Hexagone, Losange, Octogone, Étoile, Croix, Flèche, Cœur, Segment, Rafale — remplissage par triangulation ear-clip (concaves correctes), plus VIDEO |
| **Forme + vidéo** | Mode `100 + forme` : la silhouette d'une forme texturée par une vidéo |
| **9 PostFX** | feedback, kaléidoscope, pixelate, sobel, rgb split, saturation, bloom, chromatic (chaîne GPU), plus un flou séparable appliqué après les blades |
| **Vidéo** | Décodage PyAV en boucle, un décodeur par fichier, une texture par source, plein écran, sélection par canal, fixture de fond dédiée |
| **Blades** | 8 couteaux de cadrage 16-bit (A/B/C/D), avec flou par-dessus |
| **Texte** | 20 polices TTF chargées au démarrage, un spot par caractère |
| **Blend** | 10 modes (BLEND, ADD, SUBTRACT, DARKEST, LIGHTEST, DIFFERENCE, EXCLUSION, MULTIPLY, SCREEN, REPLACE), global ou par spot |
| **Sortie NDI** | UYVY 4:2:2 BT.709, packing GPU, readback PBO triple-bufferisé (1920×1080 @ 60 par défaut), visible dans OBS / vMix / Resolume |
| **Capacité** | 20 fixtures / univers, jusqu'à 9 univers ArtNet |

---

## Documentation

| Page | Contenu |
|------|---------|
| [docs/PROTOCOLE_DMX.md](docs/PROTOCOLE_DMX.md) | **référence** DMX / ArtNet : canaux, formes, blend, encodages |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | flux bout-en-bout, pipeline de rendu, PostFX, NDI, vidéo, modules |
| [docs/DEMOS.md](docs/DEMOS.md) | guide des scripts de démonstration et de leurs scènes |
| [docs/GDTF.md](docs/GDTF.md) | fixtures GDTF pour consoles (patch, régénération, vérification) |
| [CHANGELOG.md](CHANGELOG.md) | historique des versions |
| [MANIFESTO.md](MANIFESTO.md) | manifeste artistique |

---

## Structure du dépôt

| Dossier | Contenu |
|---------|---------|
| `python_port/` | **moteur principal** — lib `luxcore/` (artnet, dmx, constants, geometry, stroke, text, blades, effects, video, engine), `run_engine.py`, `tests/` |
| `demo_scripts/` | scripts Python qui pilotent le moteur par ArtNet (defile_formes, kinetic, video_show, lorem_fou, artnet_text, module partagé luxcore_artnet) |
| `data/` | polices (`fonts/`), vidéos (`videos/`, `clips_all/`, `videos_src/`) |
| `docs/` | documentation ; `docs/processing/` = sources Processing archivées |
| `gdtf/` | fixtures GDTF (Base 32ch, Spot 23ch) + générateur |

---

## Structure DMX (résumé)

Vue d'ensemble seulement — les tables complètes et faisant foi sont dans
[docs/PROTOCOLE_DMX.md](docs/PROTOCOLE_DMX.md).

- **Bloc de base : 32 canaux.** Fond RGB, 8 blades 16-bit, blend global, puis la chaîne des
  9 PostFX (blur, pixelate, sobel, rgb split, saturation, chromatic, feedback, bloom,
  kaléido). Deux effets **bistables** (sobel, chromatic) s'activent au-delà de 128.
- **Bloc par fixture : 23 canaux**, adresse `32 + spot_id × 23`. Fill RGBA, stroke, taille
  (pan/tilt 16-bit), rotation, position (16-bit, **centre = 32767**), mode/forme, enable,
  blend individuel, et un canal à **double sens** (police en mode Texte, sélecteur de
  source en mode Vidéo).
- **Fixture unifiée :** une seule sorte de fixture. Le canal Mode choisit forme (0-14),
  vidéo (14) ou forme remplie par la vidéo (100-113). **Fixture de fond** réservée au
  slot 60 = vidéo plein écran derrière tous les spots.
- **Protocole :** ArtNet UDP OpDmx port 6454, cible `127.0.0.1` ; encodage 16-bit
  big-endian (MSB en premier).

Détail complet et exact : **[docs/PROTOCOLE_DMX.md](docs/PROTOCOLE_DMX.md)**.

---

Voir aussi : [PROTOCOLE_DMX](docs/PROTOCOLE_DMX.md) · [ARCHITECTURE](docs/ARCHITECTURE.md) · [DEMOS](docs/DEMOS.md) · [GDTF](docs/GDTF.md) · [CHANGELOG](CHANGELOG.md) · [MANIFESTO](MANIFESTO.md)
