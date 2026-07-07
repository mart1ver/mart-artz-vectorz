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
.venv/bin/python run_engine.py --preview --spots 48 --duration 0

# avec une source vidéo (mode forme 15)
.venv/bin/python run_engine.py --preview --video ../ma_video.mp4 --duration 0

# headless (NDI seul, pour serveur) : retirer --preview
```
Source NDI **`LuxCore`** visible dans OBS (plugin NDI) / vMix / Resolume.
Piloter en envoyant de l'ArtNet sur `127.0.0.1:6454` (`demo_scripts/*.py`).

Options : `--width/--height/--fps`, `--no-gui`, `--no-fonts`, `--preview-scale`,
`--snapshot-dir` (dump PNG périodique).

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

Identique au mapping Processing (`z_fixture_definition.pde`), **plus** :
- **mode +19 = 14 → VIDEO** : quad texturé par la source vidéo, positionné/
  dimensionné (`size_pan × size_tilt`) / tourné comme un rectangle, opacité =
  alpha du spot. Extension propre au portage.

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
