#!/usr/bin/env python3
"""Démo texte — écrit un mot, une police différente par lettre, vers un PNG.

    python_port/.venv/bin/python python_port/render_text_demo.py [mot] [sortie.png]
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "demo_scripts"))

from PIL import Image

from luxcore import constants as C
from luxcore.constants import Shape
from luxcore.engine import LuxCoreEngine
from luxcore_artnet import set16, char_tilt, hsv

W, H = 1280, 720
HALF_W, HALF_H = W / 2, H / 2
FONTS_DIR = os.path.join(HERE, "..", "data", "fonts")


def px_to_pos16(offset_px, half):
    lo, hi = -255 - half, 255 + half
    return int((offset_px - lo) / (hi - lo) * 65535)


def set_text(dmx, i, char, dx, size_pan, color, font_index, n_fonts):
    base = C.spot_base_addr(i)
    dmx[base + C.SP_FILL_R], dmx[base + C.SP_FILL_G], dmx[base + C.SP_FILL_B] = color
    dmx[base + C.SP_ALPHA] = 255
    set16(dmx, base + C.SP_SIZE_PAN, int(size_pan / 1000 * 65535))
    set16(dmx, base + C.SP_SIZE_TILT, char_tilt(char))        # encode le caractère
    set16(dmx, base + C.SP_POS_PAN, px_to_pos16(dx, HALF_W))
    set16(dmx, base + C.SP_POS_TILT, px_to_pos16(0, HALF_H))
    # canal +22 : on veut décoder vers font_index -> raw ≈ (idx+0.5)*256/nfonts
    dmx[base + C.SP_FONT] = min(255, int((font_index + 0.5) * 256 / max(1, n_fonts)))
    dmx[base + C.SP_MODE] = int(Shape.TEXTE)
    dmx[base + C.SP_ENABLE] = 1


def main():
    word = sys.argv[1] if len(sys.argv) > 1 else "LUXCORE"
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "render_text_demo.png")

    eng = LuxCoreEngine(W, H, fonts_dir=FONTS_DIR)
    print(f"[fonts] {eng.n_fonts} polices chargées")

    dmx = bytearray(C.UNIVERSE_SIZE * C.MAX_UNIVERSES)
    dmx[C.CH_BG_R] = dmx[C.CH_BG_G] = dmx[C.CH_BG_B] = 16

    n = len(word)
    span = 1080
    for i, ch in enumerate(word):
        dx = -span / 2 + span * i / max(1, n - 1)
        color = hsv(i / max(1, n))
        set_text(dmx, i, ch, dx, size_pan=95, color=color,
                 font_index=i % eng.n_fonts, n_fonts=eng.n_fonts)

    eng.render_dmx(dmx, n)
    Image.frombytes("RGBA", (W, H), bytes(eng.read_rgba())).save(out)
    print(f"[demo] '{word}' -> {out}")


if __name__ == "__main__":
    main()
