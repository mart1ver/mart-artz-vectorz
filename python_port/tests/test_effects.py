"""Tests d'intégration des post-effets (pipeline ping-pong GL, headless)."""
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
_ENG = None


def _engine():
    global _ENG
    if _ENG is None:
        _ENG = LuxCoreEngine(W, H)
    return _ENG


def _scene(effects=None):
    dmx = bytearray(C.UNIVERSE_SIZE * C.MAX_UNIVERSES)
    b = C.spot_base_addr(0)
    dmx[b + C.SP_FILL_R] = dmx[b + C.SP_FILL_G] = dmx[b + C.SP_FILL_B] = 255  # blanc
    dmx[b + C.SP_ALPHA] = 255
    set16(dmx, b + C.SP_SIZE_PAN, 12000)      # ~183px : laisse des bords dans la ligne médiane
    set16(dmx, b + C.SP_SIZE_TILT, 12000)
    set16(dmx, b + C.SP_POS_PAN, 32767)
    set16(dmx, b + C.SP_POS_TILT, 32767)
    dmx[b + C.SP_MODE] = int(Shape.RECTANGLE)
    dmx[b + C.SP_ENABLE] = 1
    for idx, val in (effects or {}).items():
        dmx[idx] = val
    return dmx


def _frame(eng):
    return np.frombuffer(bytes(eng.read_rgba()), dtype=np.uint8).reshape(H, W, 4)


def test_no_effect_passthrough():
    eng = _engine()
    eng.render_dmx(_scene(), 1)
    img = _frame(eng)
    assert tuple(img[H // 2, W // 2, :3]) == (255, 255, 255)   # centre blanc


def test_sobel_hollows_interior():
    # rectangle blanc uniforme -> sobel = bords seuls, intérieur noir
    eng = _engine()
    eng.render_dmx(_scene({C.CH_SOBEL: 200}), 1)                  # ch23 > 128
    img = _frame(eng)
    assert img[H // 2, W // 2, :3].max() < 30                  # intérieur creusé


def test_pixelate_changes_output_but_keeps_content():
    eng = _engine()
    eng.render_dmx(_scene({C.CH_PIXELATE: 250}), 1)               # ch22
    img = _frame(eng)
    assert img[:, :, :3].max() > 200                           # du contenu subsiste


def test_blur_softens_edge():
    # sans blur : transition nette ; avec blur : valeurs intermédiaires apparaissent
    eng = _engine()
    eng.render_dmx(_scene(), 1)
    row = _frame(eng)[H // 2, :, 0].astype(int)
    sharp_mid = np.sum((row > 40) & (row < 215))
    eng.render_dmx(_scene({C.CH_BLUR_SIZE: 60, C.CH_BLUR_SIGMA: 10}), 1)
    row_b = _frame(eng)[H // 2, :, 0].astype(int)
    soft_mid = np.sum((row_b > 40) & (row_b < 215))
    assert soft_mid > sharp_mid                                # bord adouci


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
