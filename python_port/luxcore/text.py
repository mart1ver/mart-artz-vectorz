"""Cache de polices/glyphes pour le mode TEXTE (mode 2).

Chaque spot texte n'affiche qu'UN caractère (message = char(byte(size_tilt))),
donc on met en cache un bitmap par (index_police, caractère). Les polices sont
triées alphabétiquement pour reproduire l'ordre du font_cache[] de Processing
(cf. CLAUDE.md), afin que le canal +22 (font index) reste compatible.

Le glyphe est rendu blanc sur transparent à `base_size` px (= createFont(_,200)
côté Processing) ; le renderer le met ensuite à l'échelle par size_pan/80.
"""
from __future__ import annotations

import glob
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont


class FontCache:
    def __init__(self, fonts_dir: str, base_size: int = 200):
        self.paths = sorted(glob.glob(os.path.join(fonts_dir, "*.ttf")))
        self.base_size = base_size
        self._fonts: dict[int, ImageFont.FreeTypeFont] = {}
        self._glyphs: dict[tuple[int, str], tuple[np.ndarray, int, int]] = {}
        if not self.paths:
            print(f"[fonts] aucune police .ttf dans {fonts_dir}")

    @property
    def count(self) -> int:
        return len(self.paths)

    def _font(self, index: int) -> ImageFont.FreeTypeFont:
        if index not in self._fonts:
            self._fonts[index] = ImageFont.truetype(self.paths[index], self.base_size)
        return self._fonts[index]

    def glyph(self, index: int, char: str) -> tuple[np.ndarray, int, int]:
        """Renvoie (rgba HxWx4 uint8 top-down, w, h) pour un caractère.
        RGB = blanc, alpha = couverture. (0,0,0,0) 1×1 pour un glyphe vide."""
        if not self.paths:
            return np.zeros((1, 1, 4), dtype=np.uint8), 1, 1
        index = max(0, min(index, self.count - 1))
        key = (index, char)
        cached = self._glyphs.get(key)
        if cached is not None:
            return cached

        font = self._font(index)
        bbox = font.getbbox(char)                      # (l, t, r, b)
        w = max(1, bbox[2] - bbox[0])
        h = max(1, bbox[3] - bbox[1])
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.text((-bbox[0], -bbox[1]), char, font=font, fill=(255, 255, 255, 255))
        arr = np.asarray(img, dtype=np.uint8)
        self._glyphs[key] = (arr, w, h)
        return self._glyphs[key]
