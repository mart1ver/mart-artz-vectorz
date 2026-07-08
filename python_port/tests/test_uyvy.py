#!/usr/bin/env python3
"""Valide le packing UYVY (BT.709, plage vidéo) de bout en bout : on rend une
couleur unie, on packe sur GPU, on relit et on décode UYVY -> RGB, puis on
compare à la couleur d'entrée. Valide la math du shader (pas l'interprétation NDI,
à confirmer à l'œil dans OBS)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import numpy as np

from luxcore import constants as C
from luxcore.engine import LuxCoreEngine

PASS = 0
FAIL = 0


def check(name, cond):
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        print(f"  FAIL {name}")


def decode_uyvy_bt709(u, y, v):
    """UYVY (plage vidéo) -> RGB 0-255, inverse BT.709."""
    yf = (y - 16.0) / 219.0
    cb = (u - 128.0) / 224.0
    cr = (v - 128.0) / 224.0
    r = yf + 1.5748 * cr
    g = yf - 0.1873 * cb - 0.4681 * cr
    b = yf + 1.8556 * cb
    return np.array([r, g, b]) * 255.0


def roundtrip(color):
    W, H = 320, 240
    eng = LuxCoreEngine(W, H)
    buf = bytearray(C.UNIVERSE_SIZE * C.MAX_UNIVERSES)
    buf[C.CH_BG_R], buf[C.CH_BG_G], buf[C.CH_BG_B] = color
    eng.render_dmx(bytes(buf), 0)
    eng.pack_uyvy()
    raw = np.frombuffer(eng._uyvy_fbo.read(components=4, dtype="f1"), dtype=np.uint8)
    raw = raw.reshape(H, W // 2, 4).astype(np.float32)
    u, y0, v, y1 = raw[H // 2, W // 4]        # un texel au centre
    rgb0 = decode_uyvy_bt709(u, y0, v)
    err = np.abs(rgb0 - np.array(color, dtype=np.float32)).max()
    check(f"UYVY roundtrip {color} (err={err:.1f})", err <= 4.0)


def test_uyvy_fbo_half_width():
    W, H = 320, 240
    eng = LuxCoreEngine(W, H)
    check("FBO UYVY demi-largeur", eng._uyvy_tex.size == (W // 2, H))


def main():
    test_uyvy_fbo_half_width()
    for col in [(100, 150, 200), (255, 255, 255), (0, 0, 0),
                (255, 0, 0), (0, 255, 0), (0, 0, 255)]:
        roundtrip(col)
    total = PASS + FAIL
    print(f"{PASS}/{total} tests OK" if FAIL == 0 else f"{PASS}/{total} — {FAIL} ÉCHEC(S)")
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
