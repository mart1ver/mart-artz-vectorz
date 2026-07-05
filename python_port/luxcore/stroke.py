"""Tessellation de contour (stroke) — ruban centré sur le tracé, largeur constante.

Processing dessine un stroke CENTRÉ sur le contour du polygone, d'épaisseur
constante à l'écran (strokeWeight). On reproduit ça par un ruban (triangle strip)
construit sur les normales-miter de chaque sommet.

Le ruban est généré dans l'espace LOCAL déjà mis à l'échelle (pixels), donc les
normales sont correctes même pour les formes à échelle non-uniforme (rect,
ellipse…). Le renderer applique ensuite seulement rotation + translation
(u_scale = (1,1)).
"""
from __future__ import annotations

import numpy as np

MITER_LIMIT = 4.0    # évite les pointes infinies aux angles aigus


def outline_ribbon(points, width: float) -> np.ndarray:
    """points: séquence de sommets (x,y) d'un polygone FERMÉ (N distincts).
    Renvoie un tableau plat float32 de sommets en TRIANGLE_STRIP (ruban fermé)."""
    pts = np.asarray(points, dtype=np.float64)
    n = len(pts)
    if n < 2 or width <= 0:
        return np.empty(0, dtype="f4")

    prev = np.roll(pts, 1, axis=0)
    nxt = np.roll(pts, -1, axis=0)

    def _norm(v):
        ln = np.hypot(v[:, 0], v[:, 1])
        ln[ln == 0] = 1.0
        return v / ln[:, None]

    e1 = _norm(pts - prev)     # direction arête entrante
    e2 = _norm(nxt - pts)      # direction arête sortante
    # normales (perpendiculaires) de chaque arête
    n1 = np.stack([e1[:, 1], -e1[:, 0]], axis=1)
    n2 = np.stack([e2[:, 1], -e2[:, 0]], axis=1)
    m = _norm(n1 + n2)         # bissectrice (direction miter)

    denom = np.sum(m * n1, axis=1)
    denom = np.clip(denom, 1.0 / MITER_LIMIT, None)
    offset = m * (width * 0.5) / denom[:, None]

    outer = pts + offset
    inner = pts - offset

    # entrelace outer/inner puis referme le ruban
    strip = np.empty((2 * n + 2, 2), dtype="f4")
    strip[0:2 * n:2] = outer
    strip[1:2 * n:2] = inner
    strip[2 * n] = outer[0]
    strip[2 * n + 1] = inner[0]
    return strip.reshape(-1)


def segment_quad(length: float, thickness: float) -> np.ndarray:
    """SEGMENT (mode 13) : trait horizontal épais centré -> quad (TRIANGLE_STRIP)."""
    hl, ht = length * 0.5, max(1.0, thickness) * 0.5
    quad = np.array([[-hl, -ht], [hl, -ht], [-hl, ht], [hl, ht]], dtype="f4")
    return quad.reshape(-1)
