"""Tests des blades (blades.py) — parité avec do_blades (.pde)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import numpy as np                                              # noqa: E402

from luxcore import blades                                     # noqa: E402

W, H = 1920, 1080


def test_all_zero_is_degenerate():
    quads = blades.blade_quads([0] * 8, W, H)
    A = quads[0].reshape(-1, 2)
    # blade A : (0,0),(W,0),(W,0),(0,0) -> aire nulle (aucun masque)
    assert np.allclose(A, [(0, 0), (W, 0), (W, 0), (0, 0)])
    assert not any(blades.blade_is_active([0] * 8, i) for i in range(4))


def test_blade_a_full_height():
    # A1=A2=65535 -> blade A couvre tout l'écran
    b = [65535, 65535, 0, 0, 0, 0, 0, 0]
    A = blades.blade_quads(b, W, H)[0].reshape(-1, 2)
    assert np.allclose(A, [(0, 0), (W, 0), (W, H), (0, H)])
    assert blades.blade_is_active(b, 0)


def test_blade_partial_slant():
    # A1=0 (gauche à 0), A2=32767 (~mi-hauteur à droite) -> arête inclinée
    b = [0, 32767, 0, 0, 0, 0, 0, 0]
    A = blades.blade_quads(b, W, H)[0].reshape(-1, 2)
    assert abs(A[2][1] - H / 2) < 1.0        # coin droit ~mi-hauteur
    assert abs(A[3][1] - 0.0) < 1e-6         # coin gauche en haut


def test_active_flags():
    b = [0, 0, 100, 0, 0, 0, 0, 5]
    assert blades.blade_is_active(b, 1)      # B (v1=100)
    assert blades.blade_is_active(b, 3)      # D (v2=5)
    assert not blades.blade_is_active(b, 0)  # A
    assert not blades.blade_is_active(b, 2)  # C


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
