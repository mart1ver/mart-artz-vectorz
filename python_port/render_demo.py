#!/usr/bin/env python3
"""Démo de rendu hors-ligne — vérifie le mini-moteur (étape B) en sauvant un PNG.

Construit un buffer DMX avec une forme différente par spot (chemin complet
dmx -> decode_all -> LuxCoreEngine.render), rend dans le FBO, et écrit un PNG.

    python_port/.venv/bin/python python_port/render_demo.py [sortie.png]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "demo_scripts"))

from PIL import Image

from luxcore import constants as C
from luxcore.constants import Shape
from luxcore.dmx import pmap
from luxcore.engine import LuxCoreEngine
from luxcore_artnet import set16, hsv

W, H = 1280, 720
HALF_W, HALF_H = W / 2, H / 2


def px_to_pos16(offset_px: float, half: float) -> int:
    """Inverse de map(pos16,0,65535,-255-half,255+half) pour un décalage px."""
    lo, hi = -255 - half, 255 + half
    return int((offset_px - lo) / (hi - lo) * 65535)


def size_to_16(size_px: float) -> int:
    """Inverse de map(size16,0,65535,0,1000)."""
    return int(size_px / 1000 * 65535)


def set_spot(dmx, spot_id, shape, dx, dy, size, color, rot_deg=0.0):
    base = C.spot_base_addr(spot_id)
    dmx[base + C.SP_FILL_R], dmx[base + C.SP_FILL_G], dmx[base + C.SP_FILL_B] = color
    dmx[base + C.SP_ALPHA] = 255
    set16(dmx, base + C.SP_SIZE_PAN, size_to_16(size))
    set16(dmx, base + C.SP_SIZE_TILT, size_to_16(size))
    set16(dmx, base + C.SP_ROTATION, int(rot_deg / 360 * 65535))
    set16(dmx, base + C.SP_POS_PAN, px_to_pos16(dx, HALF_W))
    set16(dmx, base + C.SP_POS_TILT, px_to_pos16(dy, HALF_H))
    dmx[base + C.SP_MODE] = int(shape)
    dmx[base + C.SP_ENABLE] = 1


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "render_demo.png")

    num_spots = 15
    dmx = bytearray(C.UNIVERSE_SIZE * C.MAX_UNIVERSES)

    cols = [-500, -250, 0, 250, 500]
    rows = [-220, 0, 220]
    for i in range(num_spots):
        dx = cols[i % 5]
        dy = rows[i // 5]
        color = hsv(i / num_spots)
        rot = 20.0 if Shape(i) in (Shape.TRIANGLE, Shape.FLECHE, Shape.ETOILE) else 0.0
        set_spot(dmx, i, Shape(i), dx, dy, 190, color, rot)

    eng = LuxCoreEngine(W, H)
    # fond gris foncé pour voir les formes sombres
    dmx[C.CH_BG_R] = dmx[C.CH_BG_G] = dmx[C.CH_BG_B] = 24
    base, spots = eng.render_dmx(dmx, num_spots, n_fonts=0)

    data = bytes(eng.read_rgba())
    Image.frombytes("RGBA", (W, H), data).save(out)
    drawn = sum(1 for s in spots if s.is_drawable() and s.shape != Shape.TEXTE)
    print(f"[demo] {drawn} formes rendues -> {out}")
    print(f"[demo] fond={base.bg}  formes={[Shape(i).name for i in range(num_spots)]}")


if __name__ == "__main__":
    main()
