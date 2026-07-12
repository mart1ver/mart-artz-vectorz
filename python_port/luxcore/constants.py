"""Constantes du mapping DMX — fidèles à z_fixture_definition.pde / definitions.pde.

Tous les index sont en BASE 0 (= index du tableau dmx_data[] côté Processing).
"""
from __future__ import annotations

from enum import IntEnum

# ---------------------------------------------------------------------------
# Tailles (definitions.pde)
# ---------------------------------------------------------------------------
NUM_BASE_PARAMETERS = 32          # number_of_base_parameters (28 d'origine + 4 PostFX)
NUM_PARAMS_PER_SPOT = 23          # number_of_parameters_by_spots
UNIVERSE_SIZE = 512
MAX_UNIVERSES = 9                 # do_artnet : univers 0..8 (dmx_buffer = 512*9)

# ---------------------------------------------------------------------------
# Canaux de base (index 0..31)
# ---------------------------------------------------------------------------
CH_BG_R, CH_BG_G, CH_BG_B = 0, 1, 2
BLADE_BASE_OFFSET = 3             # premier canal blade (A1 MSB) — 8 blades 16-bit -> 3..18
CH_BLEND_GLOBAL = 19
CH_BLUR_SIZE = 20
CH_BLUR_SIGMA = 21
CH_PIXELATE = 22
CH_SOBEL = 23                     # bistable > 128
CH_RGB_SPLIT = 24
CH_SATURATION_A = 25
CH_SATURATION_B = 26
CH_CHROMATIC = 27                # bistable > 128
# PostFX ajoutés (extension du portage) — index 28..31
CH_FEEDBACK = 28                 # traînées : 0=off, sinon persistance (décroissance)
CH_BLOOM_THRESHOLD = 29          # seuil de luminance du glow
CH_BLOOM_AMOUNT = 30             # intensité du halo : 0=off, sinon force
CH_KALEIDO = 31                  # kaléidoscope : 0/1=off, 2-255 = nb de branches

# ---------------------------------------------------------------------------
# Offsets par spot (relatifs à base = 32 + spot_id * 23)
# ---------------------------------------------------------------------------
SP_FILL_R, SP_FILL_G, SP_FILL_B = 0, 1, 2
SP_ALPHA = 3
SP_STROKE_WEIGHT = 4
SP_STROKE_ALPHA = 5
SP_STROKE_R, SP_STROKE_G, SP_STROKE_B = 6, 7, 8
SP_SIZE_PAN = 9                   # 16-bit (MSB, LSB)
SP_SIZE_TILT = 11                 # 16-bit ; en mode Texte : caractère ASCII
SP_ROTATION = 13                  # 16-bit
SP_POS_PAN = 15                   # 16-bit ; 32767 = centre
SP_POS_TILT = 17                  # 16-bit ; 32767 = centre
SP_MODE = 19
SP_ENABLE = 20
SP_BLEND = 21                     # 0 = blend global ; sinon même LUT que canal 19
SP_FONT = 22                      # mode Texte : police ; mode VIDEO : sélecteur de
                                  # vidéo du dossier (raw 0-255 -> index, cf. engine)


def spot_base_addr(spot_id: int) -> int:
    """Index DMX du premier canal d'un spot."""
    return NUM_BASE_PARAMETERS + spot_id * NUM_PARAMS_PER_SPOT


# ---------------------------------------------------------------------------
# Fixture unifiée : il n'existe qu'UN type de fixture (le spot, 23 canaux).
# La vidéo n'est plus une famille dédiée : c'est simplement un spot en mode 14
# (VIDEO), qui gagne alors la sélection de vidéo (+22) et l'échelle plein écran.
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Fixture de FOND — une fixture 23 canaux (même layout qu'un spot) dessinée
# DERRIÈRE tous les spots. En mode 14 (VIDEO) elle projette une vidéo plein
# écran (choisie par +22) en fond ; sinon le fond reste la couleur RGB (0-2).
# Slot réservé, hors de la plage des spots rendus (garder num_spots <= ce slot).
# ---------------------------------------------------------------------------
BG_FIXTURE_SLOT = 60              # adresse = 32 + 60*23 = 1412 (univers 2, offset 388)


def bg_fixture_base_addr() -> int:
    """Index DMX du premier canal de la fixture de fond."""
    return spot_base_addr(BG_FIXTURE_SLOT)

# ---------------------------------------------------------------------------
# Formes (canal +19)
# ---------------------------------------------------------------------------
class Shape(IntEnum):
    ELLIPSE = 0
    RECTANGLE = 1
    TEXTE = 2
    TRIANGLE = 3
    PENTAGONE = 4
    HEXAGONE = 5
    LOSANGE = 6
    OCTOGONE = 7
    ETOILE = 8
    CROIX = 9
    FLECHE = 10
    COEUR = 11
    SEGMENT = 12
    FLEUR = 13
    VIDEO = 14                     # extension du portage : quad texturé par la vidéo
    # Toute valeur hors 0..14 -> rectangle (case default du switch Processing)


MAX_SHAPE_MODE = 14                # dernière forme reconnue (au-delà -> rectangle)

# Mode « forme remplie par la vidéo » : +19 = VIDEO_FILL_MODE_BASE + forme (0..13).
# Le spot prend la forme choisie mais est texturé par la vidéo (+22 = source) au
# lieu d'une couleur unie. N'altère pas les modes 0..14 (rétrocompatible).
VIDEO_FILL_MODE_BASE = 100         # 100=ellipse vidéo, 103=triangle vidéo, ... 113=fleur


# ---------------------------------------------------------------------------
# Blend modes
# ---------------------------------------------------------------------------
class BlendMode(IntEnum):
    """Les 10 modes de blend Processing, dans l'ordre de la LUT."""
    BLEND = 0
    ADD = 1
    SUBTRACT = 2
    DARKEST = 3
    LIGHTEST = 4
    DIFFERENCE = 5
    EXCLUSION = 6
    MULTIPLY = 7
    SCREEN = 8
    REPLACE = 9


# Valeurs DMX de référence (CLAUDE.md) alignées sur l'ordre de BlendMode
BLEND_DMX_VALUES = (0, 29, 57, 85, 114, 142, 170, 199, 227, 255)
_BLEND_ORDER = (
    BlendMode.BLEND, BlendMode.ADD, BlendMode.SUBTRACT, BlendMode.DARKEST,
    BlendMode.LIGHTEST, BlendMode.DIFFERENCE, BlendMode.EXCLUSION,
    BlendMode.MULTIPLY, BlendMode.SCREEN, BlendMode.REPLACE,
)


def build_blend_lut() -> list[BlendMode]:
    """LUT nearest-neighbor DMX 0-255 -> BlendMode, tie-break identique à Processing.

    Réplique build_blend_mode_lut() : boucle dans l'ordre avec `dist < best_dist`
    STRICT, donc au point médian c'est le mode d'index INFÉRIEUR qui gagne
    (ex. 14 -> BLEND, 15 -> ADD).
    """
    lut: list[BlendMode] = []
    for d in range(256):
        best = _BLEND_ORDER[0]
        best_dist = 256
        for i, ref in enumerate(BLEND_DMX_VALUES):
            dist = abs(d - ref)
            if dist < best_dist:
                best_dist = dist
                best = _BLEND_ORDER[i]
        lut.append(best)
    return lut


BLEND_LUT = build_blend_lut()
