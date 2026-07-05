"""Test d'intégration du renderer GL (headless EGL).

Rend une scène simple et vérifie les pixels : couleur de remplissage, fond, et
orientation (une forme placée en haut de l'écran doit apparaître en haut de
l'image lue -> le flip Y NDI est correct).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "..", "demo_scripts"))

import numpy as np                                              # noqa: E402

from luxcore import constants as C                              # noqa: E402
from luxcore.constants import Shape                             # noqa: E402
from luxcore.engine import LuxCoreEngine                        # noqa: E402
from luxcore_artnet import set16                                # noqa: E402

W, H = 320, 240

# Un seul contexte/engine partagé : plusieurs contextes EGL standalone dans le
# même process ne cohabitent pas.
_ENG = None


def _engine():
    global _ENG
    if _ENG is None:
        _ENG = LuxCoreEngine(W, H)
    return _ENG


def _dmx():
    return bytearray(C.UNIVERSE_SIZE * C.MAX_UNIVERSES)


def _set_spot(dmx, i, shape, color, pos_pan16=32767, pos_tilt16=32767, size16=8000):
    base = C.spot_base_addr(i)
    dmx[base + C.SP_FILL_R], dmx[base + C.SP_FILL_G], dmx[base + C.SP_FILL_B] = color
    dmx[base + C.SP_ALPHA] = 255
    set16(dmx, base + C.SP_SIZE_PAN, size16)
    set16(dmx, base + C.SP_SIZE_TILT, size16)
    set16(dmx, base + C.SP_POS_PAN, pos_pan16)
    set16(dmx, base + C.SP_POS_TILT, pos_tilt16)
    dmx[base + C.SP_MODE] = int(shape)
    dmx[base + C.SP_ENABLE] = 1


def _frame(eng):
    data = bytes(eng.read_rgba())
    return np.frombuffer(data, dtype=np.uint8).reshape(H, W, 4)


def test_ellipse_fill_and_background():
    eng = _engine()
    dmx = _dmx()
    dmx[C.CH_BG_R] = dmx[C.CH_BG_G] = dmx[C.CH_BG_B] = 0     # fond noir
    _set_spot(dmx, 0, Shape.ELLIPSE, (255, 0, 0))           # ellipse rouge centrée
    eng.render_dmx(dmx, 1)
    img = _frame(eng)

    cx, cy = W // 2, H // 2
    assert tuple(img[cy, cx, :3]) == (255, 0, 0), img[cy, cx, :3]   # centre rouge
    assert tuple(img[5, 5, :3]) == (0, 0, 0)                        # coin = fond


def test_disabled_spot_not_drawn():
    eng = _engine()
    dmx = _dmx()
    _set_spot(dmx, 0, Shape.RECTANGLE, (255, 255, 255))
    dmx[C.spot_base_addr(0) + C.SP_ENABLE] = 0              # désactivé
    eng.render_dmx(dmx, 1)
    img = _frame(eng)
    assert img[:, :, :3].max() == 0                         # rien de dessiné


def test_vertical_orientation():
    # spot poussé vers le HAUT de l'écran (tilt petit) -> doit apparaître en haut
    eng = _engine()
    dmx = _dmx()
    _set_spot(dmx, 0, Shape.RECTANGLE, (0, 255, 0),
              pos_tilt16=24000, size16=6000)                # moitié haute, sur l'écran
    eng.render_dmx(dmx, 1)
    img = _frame(eng)
    green = (img[:, :, 1] > 100) & (img[:, :, 0] < 50)
    ys = np.where(green.any(axis=1))[0]
    assert len(ys) > 0
    assert ys.mean() < H / 2, f"forme censée être en haut, y_moyen={ys.mean()}"


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
