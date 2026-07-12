# python_port — LuxCore DMX Engine (portage Python / moderngl)

Portage du moteur Processing en Python, motivé par deux fonctions impossibles
sous Processing : **sortie NDI** et **player vidéo**. Le rendu reproduit le
pipeline Processing complet, en moderngl, sans JVM.

**Aucun fichier `.pde` n'est modifié** — ce dossier est une réécriture parallèle.

## Installation

Runtime NDI (`libndi.so`) requis sur le système. Puis :

```bash
python3 -m venv --without-pip .venv          # (ensurepip absent sur py3.14)
curl -sS https://bootstrap.pypa.io/get-pip.py | .venv/bin/python
.venv/bin/python -m pip install -r requirements.txt
```

## Lancer

```bash
# aperçu écran + GUI + sortie NDI, piloté par ArtNet (défilé, etc.)
.venv/bin/python run_engine.py --preview --spots 60 --duration 0

# les vidéos sont chargées depuis un dossier (défaut ../data/videos) ; le
# canal +22 d'une fixture en mode 14 choisit laquelle est projetée
.venv/bin/python run_engine.py --preview --videos-dir ../data/videos --duration 0

# headless (NDI seul, pour serveur) : retirer --preview
```
Source NDI **`LuxCore`** visible dans OBS (plugin NDI) / vMix / Resolume.
Piloter en envoyant de l'ArtNet sur `127.0.0.1:6454` (`demo_scripts/*.py`).
Aperçu : **`g`** = plein écran (curseur masqué + veille inhibée), **`h`** = menu.

Options : `--width/--height/--fps`, `--no-gui`, `--no-fonts`, `--preview-scale`,
`--videos-dir`, `--snapshot-dir` (dump PNG périodique).

## Architecture (`luxcore/`)

| Module | Rôle |
|---|---|
| `constants.py` | mapping DMX 0-indexé, LUT blend, enums formes/blend |
| `dmx.py` | décodage 1:1 de `SpotData.update_from_dmx` (BaseState + SpotState) |
| `artnet.py` | réception UDP multi-univers (thread), compatible `send_multi` |
| `geometry.py` | les 14 formes en polygones-unité + triangulation ear-clip (VBO) |
| `stroke.py` | ruban de contour (miter) + segment |
| `text.py` | cache de glyphes 20 polices (mode TEXTE) |
| `blades.py` | 4 couteaux de cadrage 16-bit |
| `effects.py` | 6 post-effets bildspur portés en GLSL 330 |
| `video.py` | décodage vidéo PyAV (mode forme VIDEO = 14) |
| `gui.py` + `imgui_backend.py` | panneau imgui (config + status) |
| `engine.py` | pipeline : `fond → spots → effets → blades → blur → NDI` |

Pipeline fidèle à Processing : `do_background → do_spots → do_effects →
do_blades → do_blade_blur`.

## Pipeline DMX (rappel + extension)

Identique au mapping Processing (`z_fixture_definition.pde`), **plus** (extensions
propres au portage) :
- **PostFX ajoutés** : le bloc de base passe de 28 à **32 canaux** (les spots
  démarrent donc à l'offset 32). Canaux **29** feedback/trails, **30** bloom seuil,
  **31** bloom intensité, **32** kaléidoscope. Ordre pipeline :
  `feedback → kaléido → pixelate → sobel → rgb split → saturation → bloom → chromatic`.
- **Fixture unifiée** : un seul type de fixture (le spot, 23 canaux). Il n'y a
  PAS de famille vidéo dédiée — la vidéo est simplement un spot en **mode +19 =
  14 (VIDEO)** : quad texturé, positionné/dimensionné/tourné comme un rectangle,
  opacité = alpha. En mode 14, le canal **+22** sélectionne la vidéo du dossier
  (`data/videos`, trié par nom) et la taille est ré-échelonnée (plein écran
  possible malgré le plafond 1000 px du décodage).
- **Désynchronisation** : chaque vidéo garde un anneau de ses 16 dernières
  frames ; quand plusieurs panneaux affichent la même source, chacun échantillonne
  une frame retardée différente.
- **Fixture de FOND** (slot réservé `BG_FIXTURE_SLOT = 60`) : une fixture 23
  canaux dessinée DERRIÈRE tous les spots. En mode 14 = vidéo plein écran de fond
  (choisie par +22, alpha pour fondre avec la couleur RGB) ; sinon le fond reste
  la couleur RGB (canaux 1-3). Garder `num_spots <= 60`.

## Vidéos : clips + garde-fou VRAM

Le moteur charge **toutes** les vidéos de `data/videos/` au démarrage (un décodeur +
un anneau de 16 textures ≈ **~133 Mo VRAM/vidéo**, décodées en continu → coût CPU).

- `data/videos/`     — jeu de travail chargé (par défaut **8 clips** de 10 s ≈ 52 fps).
- `data/clips_all/`  — réserve des clips de 10 s (non chargée) ; copier ceux voulus
  dans `data/videos/`.
- `data/videos_src/` — originaux (backup, non chargés).
- `--max-videos N`   — garde-fou : ne charge qu'au plus N vidéos (échantillonnées
  uniformément). Repère mesuré : 8 ≈ 52 fps, 16 ≈ 28 fps (aperçu).

Découper une source en clips de 10 s (copie de flux, rapide) :
```bash
ffmpeg -i src.mp4 -c copy -an -map 0:v:0 -f segment -segment_time 10 \
       -reset_timestamps 1 data/clips_all/src_%03d.mp4
```

## Tests

```bash
for t in dmx geometry stroke blades engine text effects; do
  .venv/bin/python tests/test_$t.py; done
```
43 tests (décodage, géométrie recalculée depuis le `.pde`, triangulation,
contour, blades, intégration GL, polices, post-effets).

## État

Pipeline de rendu **complet** : 14 formes (fill/contour/texte/segment) + VIDEO,
blades, 6 post-effets, GUI, sortie NDI. Perf ~45-56 fps à 1080p/48 spots sur
iGPU Intel UHD 630 (2018) — plafond = readback NDI, pas le rendu.

Optimisations connues pour 60 fps garanti sur scènes très denses : instancing
des formes (une passe par type) + sortie NDI UYVY. Calibration fine possible des
post-effets vs Processing (cf. audit).
