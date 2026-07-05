"""Tests de la tessellation de contour (stroke.py)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import numpy as np                                              # noqa: E402

from luxcore import stroke                                     # noqa: E402


def test_square_ribbon_miter():
    # carré 100x100 (coins ±50), contour large de 20 -> miter à 45° aux coins
    pts = [(-50, -50), (50, -50), (50, 50), (-50, 50)]
    ribbon = stroke.outline_ribbon(pts, 20.0)
    v = ribbon.reshape(-1, 2)
    assert len(v) == 2 * 4 + 2                 # 4 sommets -> 10 (ruban fermé)
    outer = v[0:8:2]                           # sommets extérieurs
    inner = v[1:8:2]                           # sommets intérieurs
    assert abs(np.abs(outer).max() - 60) < 0.5   # coin poussé de +10 en x et y
    assert abs(np.abs(inner).max() - 40) < 0.5   # coin tiré de -10


def test_degenerate_returns_empty():
    assert stroke.outline_ribbon([(0, 0)], 10).size == 0
    assert stroke.outline_ribbon([(0, 0), (1, 1)], 0).size == 0


def test_segment_quad():
    q = stroke.segment_quad(200, 40).reshape(-1, 2)
    assert len(q) == 4
    assert abs(q[:, 0].max() - 100) < 1e-6     # demi-longueur
    assert abs(q[:, 1].max() - 20) < 1e-6      # demi-épaisseur
    # épaisseur minimale plancher à 1
    q2 = stroke.segment_quad(10, 0).reshape(-1, 2)
    assert abs(q2[:, 1].max() - 0.5) < 1e-6


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
