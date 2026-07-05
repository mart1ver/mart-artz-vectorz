"""Tests du cache de polices/glyphes (text.py)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from luxcore.text import FontCache                             # noqa: E402

FONTS_DIR = os.path.join(HERE, "..", "..", "data", "fonts")


def test_loads_all_fonts_sorted():
    fc = FontCache(FONTS_DIR)
    assert fc.count == 20
    # tri alphabétique -> compat avec l'ordre font_cache[] de Processing
    names = [os.path.basename(p) for p in fc.paths]
    assert names == sorted(names)
    assert names[0] == "Audiowide.ttf"


def test_glyph_has_coverage():
    fc = FontCache(FONTS_DIR)
    arr, w, h = fc.glyph(0, "A")
    assert w > 1 and h > 1
    assert arr.shape == (h, w, 4)
    assert arr[:, :, 3].max() > 0              # de l'alpha (couverture) présent


def test_space_is_empty_glyph():
    fc = FontCache(FONTS_DIR)
    arr, w, h = fc.glyph(0, " ")
    assert arr[:, :, 3].max() == 0             # espace : aucune couverture


def test_font_index_clamped():
    fc = FontCache(FONTS_DIR)
    a1, _, _ = fc.glyph(999, "M")              # index hors borne -> clampé
    a2, _, _ = fc.glyph(fc.count - 1, "M")
    assert (a1 == a2).all()


def test_glyph_cached():
    fc = FontCache(FONTS_DIR)
    g1 = fc.glyph(3, "Z")
    g2 = fc.glyph(3, "Z")
    assert g1 is g2                            # même objet en cache


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
