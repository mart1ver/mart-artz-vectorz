"""Tests de fidélité du décodage DMX + compatibilité avec l'émetteur existant.

Lancer : python_port/.venv/bin/python -m pytest python_port/tests -q
     ou : python_port/.venv/bin/python python_port/tests/test_dmx.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))                      # python_port/
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "..", "demo_scripts"))

from luxcore import constants as C                              # noqa: E402
from luxcore.constants import BlendMode, Shape                  # noqa: E402
from luxcore import dmx                                         # noqa: E402
from luxcore.artnet import ArtNetReceiver                       # noqa: E402


# ---------------------------------------------------------------------------
# LUT blend — tie-break identique à build_blend_mode_lut (dist < best_dist)
# ---------------------------------------------------------------------------
def test_blend_lut_reference_values():
    for dmx_val, expected in zip(
        C.BLEND_DMX_VALUES,
        [BlendMode.BLEND, BlendMode.ADD, BlendMode.SUBTRACT, BlendMode.DARKEST,
         BlendMode.LIGHTEST, BlendMode.DIFFERENCE, BlendMode.EXCLUSION,
         BlendMode.MULTIPLY, BlendMode.SCREEN, BlendMode.REPLACE],
    ):
        assert C.BLEND_LUT[dmx_val] == expected


def test_blend_lut_midpoint_tiebreak():
    # médiane 0<->29 = 14.5 : 14 -> index inférieur (BLEND), 15 -> ADD
    assert C.BLEND_LUT[14] == BlendMode.BLEND
    assert C.BLEND_LUT[15] == BlendMode.ADD
    assert C.BLEND_LUT[255] == BlendMode.REPLACE
    assert C.BLEND_LUT[199] == BlendMode.MULTIPLY


def test_u16_big_endian():
    buf = bytes([0x12, 0x34])
    assert dmx.u16(buf, 0) == 0x1234 == 4660


def test_pmap_no_clamp():
    assert dmx.pmap(0, 0, 65535, 0, 1000) == 0
    assert dmx.pmap(65535, 0, 65535, 0, 1000) == 1000
    # non clampé : au-delà des bornes on extrapole (comme map() Processing)
    assert dmx.pmap(131070, 0, 65535, 0, 1000) == 2000


# ---------------------------------------------------------------------------
# Décodage d'un spot
# ---------------------------------------------------------------------------
def _blank_buf():
    return bytearray(C.UNIVERSE_SIZE * C.MAX_UNIVERSES)


def test_decode_spot_mapping():
    buf = _blank_buf()
    base = C.spot_base_addr(0)                                  # 28
    buf[base + C.SP_FILL_R] = 10
    buf[base + C.SP_FILL_G] = 20
    buf[base + C.SP_FILL_B] = 30
    buf[base + C.SP_ALPHA] = 200
    # size_pan 16-bit = 65535 -> 1000
    buf[base + C.SP_SIZE_PAN] = 0xFF
    buf[base + C.SP_SIZE_PAN + 1] = 0xFF
    # position pan 16-bit = 32767 -> ~centre (0 de décalage)
    buf[base + C.SP_POS_PAN] = 0x7F
    buf[base + C.SP_POS_PAN + 1] = 0xFF
    buf[base + C.SP_MODE] = int(Shape.COEUR)
    buf[base + C.SP_ENABLE] = 1

    s = dmx.decode_spot(buf, base, half_w=960, half_h=540,
                        blend_global=BlendMode.BLEND, n_fonts=20)
    assert s.fill == (10, 20, 30)
    assert s.alpha == 200
    assert s.size_pan == 1000
    assert abs(s.position_pan) < 0.1        # 32767 ~ centre
    assert s.shape == Shape.COEUR
    assert s.enabled is True
    assert s.is_drawable() is True


def test_mode_out_of_range_is_rectangle():
    buf = _blank_buf()
    base = C.spot_base_addr(0)
    buf[base + C.SP_ENABLE] = 1
    buf[base + C.SP_ALPHA] = 255
    for raw in (16, 50, 99, 200, 255):      # hors 0..14 et hors bande vidéo -> rect
        buf[base + C.SP_MODE] = raw
        s = dmx.decode_spot(buf, base, 960, 540, BlendMode.BLEND, 20)
        assert s.shape == Shape.RECTANGLE
        assert s.video_fill is False


def test_mode_14_is_video():
    buf = _blank_buf()
    base = C.spot_base_addr(0)
    buf[base + C.SP_MODE] = 14
    s = dmx.decode_spot(buf, base, 960, 540, BlendMode.BLEND, 20)
    assert s.shape == Shape.VIDEO


def test_video_fill_mode_band():
    # +19 = 100 + forme -> forme remplie par la vidéo (video_fill True, forme = raw-100)
    buf = _blank_buf()
    base = C.spot_base_addr(0)
    for shape in (Shape.ELLIPSE, Shape.TRIANGLE, Shape.ETOILE, Shape.COEUR, Shape.RAFALE):
        buf[base + C.SP_MODE] = C.VIDEO_FILL_MODE_BASE + int(shape)
        s = dmx.decode_spot(buf, base, 960, 540, BlendMode.BLEND, 20)
        assert s.video_fill is True
        assert s.shape == shape


def test_sel_raw_is_raw_plus22():
    # fixture unifiée : +22 est aussi le sélecteur vidéo (brut, non clampé police)
    buf = _blank_buf()
    base = C.spot_base_addr(0)
    buf[base + C.SP_FONT] = 200
    s = dmx.decode_spot(buf, base, 960, 540, BlendMode.BLEND, n_fonts=20)
    assert s.sel_raw == 200


def test_decode_base_postfx_channels():
    # PostFX ajoutés (feedback / bloom / kaléido) décodés depuis le bloc de base
    buf = _blank_buf()
    buf[C.CH_FEEDBACK] = 120
    buf[C.CH_BLOOM_THRESHOLD] = 90
    buf[C.CH_BLOOM_AMOUNT] = 200
    buf[C.CH_KALEIDO] = 8
    b = dmx.decode_base(buf)
    assert b.feedback == 120
    assert b.bloom_threshold == 90
    assert b.bloom_amount == 200
    assert b.kaleido == 8


def test_base_block_is_32_and_spots_follow():
    # l'extension PostFX porte le bloc de base à 32 ; les spots démarrent après
    assert C.NUM_BASE_PARAMETERS == 32
    assert C.CH_KALEIDO == 31
    assert C.spot_base_addr(0) == 32
    assert C.spot_base_addr(1) == 32 + 23


def test_bg_fixture_address_is_reserved_slot():
    # la fixture de fond vit à un slot réservé, hors de la plage des spots
    assert C.bg_fixture_base_addr() == C.spot_base_addr(C.BG_FIXTURE_SLOT)
    assert C.BG_FIXTURE_SLOT >= 60


def test_spot_blend_zero_uses_global():
    buf = _blank_buf()
    base = C.spot_base_addr(0)
    buf[base + C.SP_BLEND] = 0               # 0 -> blend global
    s = dmx.decode_spot(buf, base, 960, 540, BlendMode.SCREEN, 20)
    assert s.blend_mode == BlendMode.SCREEN
    buf[base + C.SP_BLEND] = 199             # -> MULTIPLY via LUT
    s = dmx.decode_spot(buf, base, 960, 540, BlendMode.SCREEN, 20)
    assert s.blend_mode == BlendMode.MULTIPLY


def test_font_index_constrain():
    buf = _blank_buf()
    base = C.spot_base_addr(0)
    buf[base + C.SP_FONT] = 255
    s = dmx.decode_spot(buf, base, 960, 540, BlendMode.BLEND, n_fonts=20)
    assert s.font_index == 19                # constrain à nfonts-1
    buf[base + C.SP_FONT] = 0
    s = dmx.decode_spot(buf, base, 960, 540, BlendMode.BLEND, n_fonts=20)
    assert s.font_index == 0


# ---------------------------------------------------------------------------
# Mode Texte : round-trip avec le vrai encodeur char_tilt (luxcore_artnet.py)
# ---------------------------------------------------------------------------
def test_text_char_roundtrip():
    from luxcore_artnet import char_tilt      # émetteur existant, source de vérité
    buf = _blank_buf()
    base = C.spot_base_addr(0)
    for code in range(32, 127):              # ASCII imprimable
        c = chr(code)
        t16 = char_tilt(c)
        buf[base + C.SP_SIZE_TILT] = (t16 >> 8) & 0xFF
        buf[base + C.SP_SIZE_TILT + 1] = t16 & 0xFF
        s = dmx.decode_spot(buf, base, 960, 540, BlendMode.BLEND, 20)
        assert s.text_char == c, f"{c!r} -> {s.text_char!r} (t16={t16})"


# ---------------------------------------------------------------------------
# Récepteur ArtNet : parse ce qu'émet réellement send_multi (fausse socket)
# ---------------------------------------------------------------------------
class _FakeSocket:
    """Capture les paquets passés à sendto() sans réseau."""
    def __init__(self):
        self.packets = []

    def sendto(self, pkt, addr):
        self.packets.append(pkt)


def test_receiver_matches_send_multi():
    import luxcore_artnet as la

    # construit un tableau DMX multi-univers (2 univers), spot 20 sur l'univers 1
    total = C.UNIVERSE_SIZE * 2
    dmx_out = [0] * total
    # spot 0 (univers 0) : ellipse rouge
    b0 = C.spot_base_addr(0)
    dmx_out[b0 + C.SP_FILL_R] = 255
    dmx_out[b0 + C.SP_ENABLE] = 1
    dmx_out[b0 + C.SP_ALPHA] = 255
    la.set16(dmx_out, b0 + C.SP_SIZE_PAN, 65535)
    # un spot qui déborde sur l'univers 1 (offset > 512)
    b_hi = C.spot_base_addr(21)               # 32 + 21*23 = 515 -> chevauche 512
    if b_hi + C.SP_ENABLE < total:
        dmx_out[b_hi + C.SP_ENABLE] = 1

    fake = _FakeSocket()
    la.send_multi(fake, dmx_out, ip="127.0.0.1")
    assert len(fake.packets) == 2             # 2 univers émis

    # réinjecte les paquets réels dans le parseur du récepteur
    rx = ArtNetReceiver()
    for pkt in fake.packets:
        rx._handle(pkt)
    snap = rx.snapshot()

    base, spots = dmx.decode_all(snap, num_spots=1, width=1920, height=1080,
                                 n_fonts=20)
    assert spots[0].fill == (255, 0, 0)
    assert spots[0].size_pan == 1000
    assert spots[0].enabled is True
    assert rx.last_universe_seen == 1         # le 2e univers a bien été vu


if __name__ == "__main__":
    import traceback
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for fn in fns:
        try:
            fn()
            print(f"  ok   {fn.__name__}")
        except Exception:
            failed += 1
            print(f"  FAIL {fn.__name__}")
            traceback.print_exc()
    print(f"\n{len(fns) - failed}/{len(fns)} tests OK")
    sys.exit(1 if failed else 0)
