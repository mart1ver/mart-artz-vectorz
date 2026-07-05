"""Constantes du mapping DMX — fidèles à z_fixture_definition.pde / definitions.pde.

Tous les index sont en BASE 0 (= index du tableau dmx_data[] côté Processing).
"""
from __future__ import annotations

from enum import IntEnum

# ---------------------------------------------------------------------------
# Tailles (definitions.pde)
# ---------------------------------------------------------------------------
NUM_BASE_PARAMETERS = 28          # number_of_base_parameters
NUM_PARAMS_PER_SPOT = 23          # number_of_parameters_by_spots
UNIVERSE_SIZE = 512
MAX_UNIVERSES = 9                 # do_artnet : univers 0..8 (dmx_buffer = 512*9)

# ---------------------------------------------------------------------------
# Canaux de base (index 0..27)
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

# ---------------------------------------------------------------------------
# Offsets par spot (relatifs à base = 28 + spot_id * 23)
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
SP_FONT = 22


def spot_base_addr(spot_id: int) -> int:
    """Index DMX du premier canal d'un spot."""
    return NUM_BASE_PARAMETERS + spot_id * NUM_PARAMS_PER_SPOT


# ---------------------------------------------------------------------------
# Fixtures vidéo — famille de fixtures dédiée (même layout 23 canaux qu'un spot,
# mais toujours rendue en vidéo, mode forcé). Placées APRÈS le bloc des spots
# (à partir du slot MAX_SPOTS) pour ne jamais entrer en collision avec eux.
# ---------------------------------------------------------------------------
MAX_SPOTS = 48                    # slots 0..47 réservés aux spots
VIDEO_FIXTURE_SLOT0 = MAX_SPOTS   # les fixtures vidéo commencent au slot 48


def video_base_addr(fixture_id: int) -> int:
    """Index DMX du premier canal d'une fixture vidéo."""
    return spot_base_addr(VIDEO_FIXTURE_SLOT0 + fixture_id)


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
    PLUS = 11
    COEUR = 12
    SEGMENT = 13
    FLEUR = 14
    VIDEO = 15                     # extension du portage : quad texturé par la vidéo
    # Toute valeur hors 0..15 -> rectangle (case default du switch Processing)


MAX_SHAPE_MODE = 15                # dernière forme reconnue (au-delà -> rectangle)


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
