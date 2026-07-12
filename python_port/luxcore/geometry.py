"""Géométrie des 15 formes — portée 1:1 de render_*_optimized (performance_optimization.pde).

Chaque forme est définie en **coordonnées-unité** (size_pan = size_tilt = 1),
centrée sur (0,0), pour être pré-construite une fois en VBO (rétained-mode) puis
mise à l'échelle par le model matrix du renderer — indispensable pour tenir 60fps
(l'audit interdit d'appeler vertex() ~8600×/frame via un pont natif).

Règle d'échelle par forme (SCALE_MODE) :
  'pan_tilt' : mise à l'échelle non-uniforme (sx=size_pan, sy=size_tilt).
               Formes qui utilisent size_pan ET size_tilt.
  'pan_only' : mise à l'échelle uniforme (sx=sy=size_pan).
               Formes basées sur un rayon = size_pan/2 (size_tilt ignoré,
               exactement comme le .pde).

TEXTE et SEGMENT sont des cas spéciaux (glyphe / trait épais) gérés par le
renderer, pas par un polygone rempli.
"""
from __future__ import annotations

import math

import numpy as np

from .constants import Shape

TWO_PI = 2.0 * math.pi
HALF_PI = math.pi / 2.0

Vec2 = tuple[float, float]

# Mode d'échelle par forme
SCALE_MODE: dict[Shape, str] = {
    Shape.ELLIPSE: "pan_tilt",
    Shape.RECTANGLE: "pan_tilt",
    Shape.TRIANGLE: "pan_tilt",
    Shape.LOSANGE: "pan_tilt",
    Shape.FLECHE: "pan_tilt",
    Shape.COEUR: "pan_tilt",
    Shape.SEGMENT: "pan_tilt",     # x=longueur (size_pan), épaisseur=size_tilt
    Shape.PENTAGONE: "pan_only",
    Shape.HEXAGONE: "pan_only",
    Shape.OCTOGONE: "pan_only",
    Shape.ETOILE: "pan_only",
    Shape.CROIX: "pan_only",
    Shape.RAFALE: "pan_only",
    # TEXTE : cas spécial (pas de polygone)
}

ELLIPSE_SEGMENTS = 72              # tessellation de l'ellipse (lissage)


# ---------------------------------------------------------------------------
# Générateurs de polygones-unité (size_pan = size_tilt = 1)
# ---------------------------------------------------------------------------
def _ellipse() -> list[Vec2]:
    # ellipseMode CENTER : rayons size_pan/2, size_tilt/2 -> unité 0.5
    return [(0.5 * math.cos(TWO_PI * i / ELLIPSE_SEGMENTS),
             0.5 * math.sin(TWO_PI * i / ELLIPSE_SEGMENTS))
            for i in range(ELLIPSE_SEGMENTS)]


def _rectangle() -> list[Vec2]:
    # rectMode CENTER : coins ±size_pan/2, ±size_tilt/2
    return [(-0.5, -0.5), (0.5, -0.5), (0.5, 0.5), (-0.5, 0.5)]


def _triangle() -> list[Vec2]:
    return [(0.0, -0.5), (-0.5, 0.5), (0.5, 0.5)]


def _regular_polygon(n: int, angle_offset: float) -> list[Vec2]:
    # rayon = size_pan/2 -> 0.5 en unité
    return [(0.5 * math.cos(TWO_PI * k / n + angle_offset),
             0.5 * math.sin(TWO_PI * k / n + angle_offset)) for k in range(n)]


def _pentagon() -> list[Vec2]:
    return _regular_polygon(5, -HALF_PI)        # pointe vers le haut


def _hexagon() -> list[Vec2]:
    return _regular_polygon(6, 0.0)


def _octagon() -> list[Vec2]:
    return _regular_polygon(8, 0.0)


def _diamond() -> list[Vec2]:
    return [(0.0, -0.5), (0.5, 0.0), (0.0, 0.5), (-0.5, 0.0)]


def _star() -> list[Vec2]:
    outer, inner = 0.5, 0.5 * 0.4                # inner = outer * 0.4
    pts: list[Vec2] = []
    for s in range(10):
        angle = TWO_PI * s / 10 - HALF_PI
        r = outer if s % 2 == 0 else inner
        pts.append((r * math.cos(angle), r * math.sin(angle)))
    return pts


def _cross() -> list[Vec2]:
    t = 0.25                                     # size_pan * 0.25
    a = 0.50                                     # size_pan * 0.50
    return [(-t / 2, -a), (t / 2, -a), (t / 2, -t / 2), (a, -t / 2),
            (a, t / 2), (t / 2, t / 2), (t / 2, a), (-t / 2, a),
            (-t / 2, t / 2), (-a, t / 2), (-a, -t / 2), (-t / 2, -t / 2)]


def _arrow() -> list[Vec2]:
    # unité : size_pan = size_tilt = 1
    head_w = 0.6                                 # size_pan * 0.6
    head_h = 0.3                                 # size_tilt * 0.3
    shaft_w = 0.25                               # size_pan * 0.25
    top = -0.5                                   # -size_tilt/2
    bot = 0.5                                    # size_tilt/2
    return [(0.0, top),
            (head_w / 2, top + head_h),
            (shaft_w / 2, top + head_h),
            (shaft_w / 2, bot),
            (-shaft_w / 2, bot),
            (-shaft_w / 2, top + head_h),
            (-head_w / 2, top + head_h)]


def _heart() -> list[Vec2]:
    w, h = 0.4, 0.4                              # size_pan*0.4, size_tilt*0.4 (unité)
    steps = 72
    pts: list[Vec2] = []
    for i in range(steps):
        t = TWO_PI * i / steps
        hx = 16 * math.sin(t) ** 3
        hy = -(13 * math.cos(t) - 5 * math.cos(2 * t)
               - 2 * math.cos(3 * t) - math.cos(4 * t))
        pts.append((hx * w / 16.0, hy * h / 17.0))
    return pts


def _sunburst() -> list[Vec2]:
    # Rafale : étoile à 14 pointes fines (remplace l'ancienne rosace « fleur »).
    # Rayon externe 0.5, interne 0.17 -> pointes acérées. 28 sommets, une pointe en haut.
    n = 14
    outer, inner = 0.5, 0.17
    pts: list[Vec2] = []
    for k in range(2 * n):
        r = outer if k % 2 == 0 else inner
        a = math.pi * k / n - HALF_PI
        pts.append((r * math.cos(a), r * math.sin(a)))
    return pts


def _segment() -> list[Vec2]:
    # trait horizontal : line(-size_pan/2, 0, size_pan/2, 0) -> unité ±0.5
    return [(-0.5, 0.0), (0.5, 0.0)]


_GENERATORS = {
    Shape.ELLIPSE: _ellipse,
    Shape.RECTANGLE: _rectangle,
    Shape.TRIANGLE: _triangle,
    Shape.PENTAGONE: _pentagon,
    Shape.HEXAGONE: _hexagon,
    Shape.LOSANGE: _diamond,
    Shape.OCTOGONE: _octagon,
    Shape.ETOILE: _star,
    Shape.CROIX: _cross,
    Shape.FLECHE: _arrow,
    Shape.COEUR: _heart,
    Shape.SEGMENT: _segment,
    Shape.RAFALE: _sunburst,
}

# Cache des polygones-unité (construits une fois)
_UNIT_CACHE: dict[Shape, list[Vec2]] = {}


def unit_polygon(shape: Shape) -> list[Vec2]:
    """Sommets-unité fermés d'une forme (hors TEXTE). SEGMENT = 2 extrémités."""
    if shape == Shape.TEXTE:
        raise ValueError("TEXTE n'est pas un polygone (rendu par glyphe)")
    if shape not in _UNIT_CACHE:
        _UNIT_CACHE[shape] = _GENERATORS[shape]()
    return _UNIT_CACHE[shape]


def scale_factors(shape: Shape, size_pan: float, size_tilt: float) -> Vec2:
    """(sx, sy) à appliquer au polygone-unité selon SCALE_MODE."""
    if SCALE_MODE.get(shape, "pan_tilt") == "pan_only":
        return (size_pan, size_pan)
    return (size_pan, size_tilt)


def scaled_polygon(shape: Shape, size_pan: float, size_tilt: float) -> list[Vec2]:
    """Sommets à l'échelle réelle (utile pour tests / rendu CPU de référence)."""
    sx, sy = scale_factors(shape, size_pan, size_tilt)
    return [(x * sx, y * sy) for (x, y) in unit_polygon(shape)]


# Cache numpy des polygones-unité (chemin chaud du renderer, sans boucle Python)
_UNIT_NP_CACHE: dict[Shape, np.ndarray] = {}


def unit_polygon_np(shape: Shape) -> np.ndarray:
    """Polygone-unité en tableau numpy (N,2) float32, mis en cache."""
    arr = _UNIT_NP_CACHE.get(shape)
    if arr is None:
        arr = np.array(unit_polygon(shape), dtype="f4")
        _UNIT_NP_CACHE[shape] = arr
    return arr


def scaled_polygon_np(shape: Shape, size_pan: float, size_tilt: float) -> np.ndarray:
    """Comme scaled_polygon, vectorisé numpy (pas de boucle Python par sommet)."""
    sx, sy = scale_factors(shape, size_pan, size_tilt)
    return unit_polygon_np(shape) * np.array((sx, sy), dtype="f4")


# ---------------------------------------------------------------------------
# Triangulation (ear clipping) — remplissage correct des polygones CONCAVES.
#
# L'éventail-depuis-l'origine (ancien rendu) ne fonctionne que pour les formes
# « étoilées » vis-à-vis de leur centre (l'origine voit chaque sommet). La
# flèche ne l'est pas : l'origine, dans le fût, ne « voit » pas les barbes ->
# les triangles de l'éventail se recouvraient (croisements visibles). Le cœur
# a le même défaut latent (creux du haut). L'ear clipping découpe le polygone
# en triangles disjoints, universellement corrects. Pour les formes convexes /
# étoilées, la surface couverte est identique à l'éventail : rendu inchangé.
# ---------------------------------------------------------------------------
def _signed_area(pts: list[Vec2]) -> float:
    a = 0.0
    n = len(pts)
    for i in range(n):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % n]
        a += x0 * y1 - x1 * y0
    return 0.5 * a


def _point_in_triangle(p: Vec2, a: Vec2, b: Vec2, c: Vec2) -> bool:
    (px, py), (ax, ay), (bx, by), (cx, cy) = p, a, b, c
    d1 = (px - bx) * (ay - by) - (ax - bx) * (py - by)
    d2 = (px - cx) * (by - cy) - (bx - cx) * (py - cy)
    d3 = (px - ax) * (cy - ay) - (cx - ax) * (py - ay)
    has_neg = d1 < 0 or d2 < 0 or d3 < 0
    has_pos = d1 > 0 or d2 > 0 or d3 > 0
    return not (has_neg and has_pos)


def _triangulate(pts: list[Vec2]) -> list[Vec2]:
    """Ear clipping d'un polygone simple. Renvoie une liste plate de sommets,
    3 consécutifs par triangle (à rendre en GL_TRIANGLES)."""
    if len(pts) < 3:
        return []
    verts = list(pts)
    if _signed_area(verts) < 0:              # normaliser en sens anti-horaire
        verts.reverse()
    idx = list(range(len(verts)))
    tris: list[Vec2] = []
    guard = 0
    while len(idx) > 3 and guard < 10000:
        guard += 1
        m = len(idx)
        ear_found = False
        for i in range(m):
            i0, i1, i2 = idx[(i - 1) % m], idx[i], idx[(i + 1) % m]
            a, b, c = verts[i0], verts[i1], verts[i2]
            cross = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
            if cross <= 0:                   # sommet réflexe/plat -> pas une oreille
                continue
            if any(k not in (i0, i1, i2) and _point_in_triangle(verts[k], a, b, c)
                   for k in idx):
                continue                     # un autre sommet est dans l'oreille
            tris.extend((a, b, c))
            del idx[i]
            ear_found = True
            break
        if not ear_found:                    # polygone dégénéré : stop
            break
    if len(idx) == 3:
        tris.extend((verts[idx[0]], verts[idx[1]], verts[idx[2]]))
    return tris


_UNIT_TRI_CACHE: dict[Shape, np.ndarray] = {}


def unit_triangles_np(shape: Shape) -> np.ndarray:
    """Triangulation-unité (M,2) float32 d'une forme remplie, mise en cache.
    3 sommets consécutifs = 1 triangle (GL_TRIANGLES)."""
    arr = _UNIT_TRI_CACHE.get(shape)
    if arr is None:
        arr = np.array(_triangulate(unit_polygon(shape)), dtype="f4").reshape(-1, 2)
        _UNIT_TRI_CACHE[shape] = arr
    return arr
