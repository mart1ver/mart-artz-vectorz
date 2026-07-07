"""Tests de la géométrie des formes — parité avec render_*_optimized (.pde).

Chaque test recalcule INDÉPENDAMMENT la formule du .pde et la compare au module,
pour garantir la fidélité (et pas seulement la cohérence interne).
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from luxcore import geometry as geo                              # noqa: E402
from luxcore.constants import Shape                              # noqa: E402

TWO_PI = 2 * math.pi
HALF_PI = math.pi / 2


def _close(a, b, eps=1e-9):
    return abs(a[0] - b[0]) < eps and abs(a[1] - b[1]) < eps


# ---------------------------------------------------------------------------
# Comptes de sommets (doc CLAUDE.md / .pde)
# ---------------------------------------------------------------------------
def test_vertex_counts():
    expected = {
        Shape.RECTANGLE: 4, Shape.TRIANGLE: 3, Shape.PENTAGONE: 5,
        Shape.HEXAGONE: 6, Shape.LOSANGE: 4, Shape.OCTOGONE: 8,
        Shape.ETOILE: 10, Shape.CROIX: 12, Shape.FLECHE: 7,
        Shape.COEUR: 72, Shape.FLEUR: 180,
        Shape.SEGMENT: 2, Shape.ELLIPSE: geo.ELLIPSE_SEGMENTS,
    }
    for shape, n in expected.items():
        assert len(geo.unit_polygon(shape)) == n, shape


# ---------------------------------------------------------------------------
# Parité formule par forme (recalcul indépendant)
# ---------------------------------------------------------------------------
def test_triangle_matches_pde():
    sp, st = 200.0, 120.0
    exp = [(0, -st / 2), (-sp / 2, st / 2), (sp / 2, st / 2)]
    got = geo.scaled_polygon(Shape.TRIANGLE, sp, st)
    assert all(_close(g, e) for g, e in zip(got, exp))


def test_regular_polygons_match_pde():
    sp, st = 300.0, 77.0                         # st ignoré (pan_only)
    for shape, n, off in [(Shape.PENTAGONE, 5, -HALF_PI),
                          (Shape.HEXAGONE, 6, 0.0),
                          (Shape.OCTOGONE, 8, 0.0)]:
        radius = sp / 2
        exp = [(radius * math.cos(TWO_PI * k / n + off),
                radius * math.sin(TWO_PI * k / n + off)) for k in range(n)]
        got = geo.scaled_polygon(shape, sp, st)
        assert all(_close(g, e) for g, e in zip(got, exp)), shape


def test_cross_matches_pde():
    sp = 100.0
    t, a = sp * 0.25, sp * 0.50
    exp = [(-t/2, -a), (t/2, -a), (t/2, -t/2), (a, -t/2), (a, t/2),
           (t/2, t/2), (t/2, a), (-t/2, a), (-t/2, t/2), (-a, t/2),
           (-a, -t/2), (-t/2, -t/2)]
    got = geo.scaled_polygon(Shape.CROIX, sp, 999.0)   # tilt ignoré
    assert all(_close(g, e) for g, e in zip(got, exp))


def test_star_matches_pde():
    sp = 200.0
    outer = sp / 2
    inner = outer * 0.4
    exp = []
    for s in range(10):
        angle = TWO_PI * s / 10 - HALF_PI
        r = outer if s % 2 == 0 else inner
        exp.append((r * math.cos(angle), r * math.sin(angle)))
    got = geo.scaled_polygon(Shape.ETOILE, sp, 0.0)
    assert all(_close(g, e) for g, e in zip(got, exp))


def test_heart_matches_pde():
    sp, st = 250.0, 180.0
    w, h = sp * 0.4, st * 0.4
    exp = []
    for i in range(72):
        t = TWO_PI * i / 72
        hx = 16 * math.sin(t) ** 3
        hy = -(13*math.cos(t) - 5*math.cos(2*t) - 2*math.cos(3*t) - math.cos(4*t))
        exp.append((hx * w / 16.0, hy * h / 17.0))
    got = geo.scaled_polygon(Shape.COEUR, sp, st)
    assert all(_close(g, e) for g, e in zip(got, exp))


def test_flower_matches_pde():
    sp = 400.0
    outer = sp * 0.45
    exp = []
    for i in range(180):
        t = TWO_PI * i / 180
        r = outer * (0.28 + 0.72 * abs(math.cos(3 * t)))
        exp.append((r * math.cos(t), r * math.sin(t)))
    got = geo.scaled_polygon(Shape.FLEUR, sp, 12.0)
    assert all(_close(g, e) for g, e in zip(got, exp))


# ---------------------------------------------------------------------------
# Modes d'échelle
# ---------------------------------------------------------------------------
def test_pan_only_ignores_tilt():
    # une forme pan_only doit être identique quelle que soit size_tilt
    a = geo.scaled_polygon(Shape.HEXAGONE, 300, 10)
    b = geo.scaled_polygon(Shape.HEXAGONE, 300, 900)
    assert all(_close(x, y) for x, y in zip(a, b))
    assert geo.scale_factors(Shape.HEXAGONE, 300, 900) == (300, 300)


def test_pan_tilt_uses_both():
    assert geo.scale_factors(Shape.RECTANGLE, 200, 100) == (200, 100)
    r = geo.scaled_polygon(Shape.RECTANGLE, 200, 100)
    assert _close(r[2], (100, 50))               # coin (0.5,0.5)*(200,100)


def test_pentagon_points_up():
    # premier sommet à -π/2 -> pointe en haut (0, -0.5) en unité
    assert _close(geo.unit_polygon(Shape.PENTAGONE)[0], (0.0, -0.5))


def test_texte_is_not_polygon():
    try:
        geo.unit_polygon(Shape.TEXTE)
    except ValueError:
        return
    raise AssertionError("TEXTE devrait lever ValueError")


# ---------------------------------------------------------------------------
# Triangulation (ear clipping) — remplissage correct, y compris concaves
# ---------------------------------------------------------------------------
def _poly_area(pts):
    a = 0.0
    n = len(pts)
    for i in range(n):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % n]
        a += x0 * y1 - x1 * y0
    return abs(a) / 2


def test_triangulation_covers_full_area():
    # chaque forme remplie : n-2 triangles disjoints couvrant EXACTEMENT l'aire
    # du polygone (les triangles disjoints => somme des aires == aire polygone).
    fill_shapes = [s for s in Shape
                   if s not in (Shape.TEXTE, Shape.SEGMENT, Shape.VIDEO)]
    for shape in fill_shapes:
        poly = geo.unit_polygon(shape)
        tris = geo.unit_triangles_np(shape)
        n_tri = len(tris) // 3
        assert n_tri == len(poly) - 2, (shape, n_tri, len(poly))
        tri_area = sum(_poly_area([tuple(tris[i]), tuple(tris[i + 1]),
                                   tuple(tris[i + 2])])
                       for i in range(0, len(tris), 3))
        assert abs(tri_area - _poly_area(poly)) < 1e-5, shape


def test_arrow_triangulation_no_overlap():
    # La flèche est CONCAVE : l'ancien éventail-origine se recouvrait. La
    # triangulation ear-clip doit couvrir exactement l'aire (pas de recouvrement,
    # qui gonflerait la somme des aires au-delà de l'aire réelle).
    poly = geo.unit_polygon(Shape.FLECHE)
    tris = geo.unit_triangles_np(Shape.FLECHE)
    tri_area = sum(_poly_area([tuple(tris[i]), tuple(tris[i + 1]),
                               tuple(tris[i + 2])])
                   for i in range(0, len(tris), 3))
    assert abs(tri_area - _poly_area(poly)) < 1e-6


if __name__ == "__main__":
    import traceback
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for fn in fns:
        try:
            fn(); print(f"  ok   {fn.__name__}")
        except Exception:
            failed += 1; print(f"  FAIL {fn.__name__}"); traceback.print_exc()
    print(f"\n{len(fns) - failed}/{len(fns)} tests OK")
    sys.exit(1 if failed else 0)
