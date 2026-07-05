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
    Renvoie un tableau plat float32 de sommets en TRIANGLE_STRIP (ruban fermé).

    Écrit sans np.roll / np.stack / appels de fonction : sur le chemin chaud
    (un appel par spot par frame), le surcoût par-appel de numpy domine, donc on
    minimise le nombre d'opérations numpy.
    """
    pts = np.asarray(points, dtype=np.float32)
    n = len(pts)
    if n < 2 or width <= 0:
        return np.empty(0, dtype="f4")

    # arête sortante e2[i] = pts[i+1] - pts[i] (bouclée), normalisée
    e2 = np.empty_like(pts)
    e2[:-1] = pts[1:] - pts[:-1]
    e2[-1] = pts[0] - pts[-1]
    ln = np.sqrt(e2[:, 0] ** 2 + e2[:, 1] ** 2)
    ln[ln == 0] = 1.0
    e2 /= ln[:, None]
    # arête entrante e1[i] = e2[i-1] (décalage par slice, pas de roll)
    e1 = np.empty_like(e2)
    e1[1:] = e2[:-1]
    e1[0] = e2[-1]

    # normales perpendiculaires (y, -x) ; miter m = normalize(n1 + n2)
    mx = e1[:, 1] + e2[:, 1]
    my = -e1[:, 0] - e2[:, 0]
    mln = np.sqrt(mx * mx + my * my)
    mln[mln == 0] = 1.0
    mx /= mln
    my /= mln
    # denom = dot(m, n1) avec n1 = (e1.y, -e1.x)
    denom = mx * e1[:, 1] - my * e1[:, 0]
    np.clip(denom, 1.0 / MITER_LIMIT, None, out=denom)
    k = (width * 0.5) / denom
    ox = mx * k
    oy = my * k

    strip = np.empty((2 * n + 2, 2), dtype="f4")
    strip[0:2 * n:2, 0] = pts[:, 0] + ox      # outer
    strip[0:2 * n:2, 1] = pts[:, 1] + oy
    strip[1:2 * n:2, 0] = pts[:, 0] - ox      # inner
    strip[1:2 * n:2, 1] = pts[:, 1] - oy
    strip[2 * n] = strip[0]
    strip[2 * n + 1] = strip[1]
    return strip.reshape(-1)


def segment_quad(length: float, thickness: float) -> np.ndarray:
    """SEGMENT (mode 13) : trait horizontal épais centré -> quad (TRIANGLE_STRIP)."""
    hl, ht = length * 0.5, max(1.0, thickness) * 0.5
    quad = np.array([[-hl, -ht], [hl, -ht], [-hl, ht], [hl, ht]], dtype="f4")
    return quad.reshape(-1)
