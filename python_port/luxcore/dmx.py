"""Décodage DMX — porté fidèlement de SpotData.update_from_dmx (performance_optimization.pde).

Transforme le tableau d'octets DMX (source de vérité) en états exploitables :
un BaseState (fond, blend global, blades, effets) et une liste de SpotState.
"""
from __future__ import annotations

from dataclasses import dataclass

from . import constants as C
from .constants import BlendMode, Shape


# ---------------------------------------------------------------------------
# Helpers — équivalents Processing
# ---------------------------------------------------------------------------
def u16(buf, i: int) -> int:
    """Lecture 16-bit big-endian (MSB, LSB), comme (dmx[i]<<8)|dmx[i+1]."""
    return ((buf[i] & 0xFF) << 8) | (buf[i + 1] & 0xFF)


def pmap(v: float, a: float, b: float, c: float, d: float) -> float:
    """map() de Processing — interpolation linéaire SANS clamp."""
    return c + (d - c) * (v - a) / (b - a)


Color = tuple[int, int, int]


# ---------------------------------------------------------------------------
# États décodés
# ---------------------------------------------------------------------------
@dataclass
class SpotState:
    fill: Color
    alpha: int
    stroke: Color
    stroke_alpha: int
    stroke_weight: int
    size_pan: float            # 0..1000 (largeur)
    size_tilt: float           # 0..1000 (hauteur ; mode Texte : code ASCII)
    rotation: float            # degrés 0..360
    position_pan: float        # décalage X depuis le centre écran (px)
    position_tilt: float       # décalage Y depuis le centre écran (px)
    mode: int                  # octet brut 0..255
    enabled: bool
    blend_mode: BlendMode
    font_index: int
    sel_raw: int = 0           # canal +22 brut ; en mode VIDEO : sélecteur de vidéo
    # Transport vidéo (canaux fill/stroke réinterprétés en mode VIDEO ; défauts à
    # 0 = « lecture 1× en boucle depuis le début », cf. constants).
    vid_speed_raw: int = 0     # +0
    vid_in_raw: int = 0        # +1
    vid_flags: int = 0         # +2
    vid_out_raw: int = 0       # +4
    vid_sync: int = 0          # +5 : groupe de sync (0 = indépendant)
    vid_strobe: int = 0        # +6 : hold 1 frame sur N (0 = off)

    @property
    def vid_speed(self) -> float:
        """Facteur de vitesse (défaut 1×)."""
        return C.vid_speed_factor(self.vid_speed_raw)

    @property
    def vid_transport(self) -> int:
        """0/3 = play, 1 = pause, 2 = stop (bits 0-1 du canal flags)."""
        return self.vid_flags & C.VID_TRANSPORT_MASK

    @property
    def vid_reverse(self) -> bool:
        return bool(self.vid_flags & C.VID_DIR_REVERSE_BIT)

    @property
    def vid_loop_mode(self) -> int:
        """0 = loop, 1 = once, 2 = ping-pong (bits 3-4 du canal flags)."""
        return (self.vid_flags >> C.VID_LOOP_SHIFT) & C.VID_LOOP_MASK

    @property
    def vid_in(self) -> float:
        """Point de départ, 0..1 du clip."""
        return self.vid_in_raw / 255.0

    @property
    def vid_out(self) -> float:
        """Point de fin, 0..1 ; 0 (canal vierge) = fin du clip (1.0)."""
        return 1.0 if self.vid_out_raw == 0 else self.vid_out_raw / 255.0

    @property
    def video_fill(self) -> bool:
        """Mode « forme remplie par la vidéo » : +19 dans [BASE, BASE+13]."""
        base = C.VIDEO_FILL_MODE_BASE
        return base <= self.mode <= base + 13

    @property
    def shape(self) -> Shape:
        """Forme effective : hors 0..14 -> RECTANGLE (case default du switch).
        En mode « forme+vidéo » (100+forme), on retire l'offset pour retrouver la forme."""
        m = self.mode - C.VIDEO_FILL_MODE_BASE if self.video_fill else self.mode
        return Shape(m) if 0 <= m <= C.MAX_SHAPE_MODE else Shape.RECTANGLE

    @property
    def text_char(self) -> str:
        """Mode Texte : caractère ASCII, via byte(size_tilt) côté Processing."""
        return chr(int(self.size_tilt) & 0xFF)

    def is_drawable(self) -> bool:
        """Réplique render_optimized : ignoré si désactivé ou alpha nul."""
        return self.enabled and self.alpha > 0


@dataclass
class BaseState:
    bg: Color
    blend_global: BlendMode
    blades_16: list[int]       # 8 valeurs 16-bit (A1,A2,B1,B2,C1,C2,D1,D2)
    blur_size: int
    blur_sigma: int
    pixelate: int
    sobel: bool                # bistable > 128
    rgb_split: int
    saturation_a: int
    saturation_b: int
    chromatic: bool            # bistable > 128
    feedback: int              # traînées : 0=off, sinon persistance (0-255)
    bloom_threshold: int       # seuil de luminance du glow (0-255)
    bloom_amount: int          # intensité du bloom : 0=off, sinon force
    kaleido: int               # kaléidoscope : 0/1=off, 2-255 = nb de branches


# ---------------------------------------------------------------------------
# Décodage
# ---------------------------------------------------------------------------
def decode_base(buf) -> BaseState:
    blades = [u16(buf, C.BLADE_BASE_OFFSET + 2 * i) for i in range(8)]
    return BaseState(
        bg=(buf[C.CH_BG_R] & 0xFF, buf[C.CH_BG_G] & 0xFF, buf[C.CH_BG_B] & 0xFF),
        blend_global=C.BLEND_LUT[buf[C.CH_BLEND_GLOBAL] & 0xFF],
        blades_16=blades,
        blur_size=buf[C.CH_BLUR_SIZE] & 0xFF,
        blur_sigma=buf[C.CH_BLUR_SIGMA] & 0xFF,
        pixelate=buf[C.CH_PIXELATE] & 0xFF,
        sobel=(buf[C.CH_SOBEL] & 0xFF) > 128,
        rgb_split=buf[C.CH_RGB_SPLIT] & 0xFF,
        saturation_a=buf[C.CH_SATURATION_A] & 0xFF,
        saturation_b=buf[C.CH_SATURATION_B] & 0xFF,
        chromatic=(buf[C.CH_CHROMATIC] & 0xFF) > 128,
        feedback=buf[C.CH_FEEDBACK] & 0xFF,
        bloom_threshold=buf[C.CH_BLOOM_THRESHOLD] & 0xFF,
        bloom_amount=buf[C.CH_BLOOM_AMOUNT] & 0xFF,
        kaleido=buf[C.CH_KALEIDO] & 0xFF,
    )


def decode_spot(buf, base_addr: int, half_w: float, half_h: float,
                blend_global: BlendMode, n_fonts: int) -> SpotState:
    """Porté 1:1 de update_from_dmx."""
    def b(off: int) -> int:
        return buf[base_addr + off] & 0xFF

    pan_16 = u16(buf, base_addr + C.SP_SIZE_PAN)
    tilt_16 = u16(buf, base_addr + C.SP_SIZE_TILT)
    rot_16 = u16(buf, base_addr + C.SP_ROTATION)
    pos_pan_16 = u16(buf, base_addr + C.SP_POS_PAN)
    pos_tilt_16 = u16(buf, base_addr + C.SP_POS_TILT)

    blend_raw = b(C.SP_BLEND)
    blend_mode = blend_global if blend_raw == 0 else C.BLEND_LUT[blend_raw]

    # font_index = constrain(raw * max(1,nfonts) / 256, 0, max(0,nfonts-1))
    raw_font = b(C.SP_FONT)
    font_index = (raw_font * max(1, n_fonts)) // 256
    font_index = max(0, min(font_index, max(0, n_fonts - 1)))

    return SpotState(
        fill=(b(C.SP_FILL_R), b(C.SP_FILL_G), b(C.SP_FILL_B)),
        alpha=b(C.SP_ALPHA),
        stroke=(b(C.SP_STROKE_R), b(C.SP_STROKE_G), b(C.SP_STROKE_B)),
        stroke_alpha=b(C.SP_STROKE_ALPHA),
        stroke_weight=b(C.SP_STROKE_WEIGHT),
        size_pan=pmap(pan_16, 0, 65535, 0, 1000),
        size_tilt=pmap(tilt_16, 0, 65535, 0, 1000),
        rotation=pmap(rot_16, 0, 65535, 0, 360),
        position_pan=pmap(pos_pan_16, 0, 65535, -255 - half_w, 255 + half_w),
        position_tilt=pmap(pos_tilt_16, 0, 65535, -255 - half_h, 255 + half_h),
        mode=b(C.SP_MODE),
        enabled=b(C.SP_ENABLE) > 0,
        blend_mode=blend_mode,
        font_index=font_index,
        sel_raw=raw_font,          # même canal (+22) réinterprété en mode VIDEO
        vid_speed_raw=b(C.SP_VID_SPEED),
        vid_in_raw=b(C.SP_VID_IN),
        vid_flags=b(C.SP_VID_FLAGS),
        vid_out_raw=b(C.SP_VID_OUT),
        vid_sync=b(C.SP_VID_SYNC),
        vid_strobe=b(C.SP_VID_STROBE),
    )


def decode_all(buf, num_spots: int, width: int, height: int,
               n_fonts: int) -> tuple[BaseState, list[SpotState]]:
    """Décode la base + `num_spots` spots pour une fenêtre width×height."""
    base = decode_base(buf)
    half_w, half_h = width * 0.5, height * 0.5
    spots = [
        decode_spot(buf, C.spot_base_addr(i), half_w, half_h,
                    base.blend_global, n_fonts)
        for i in range(num_spots)
    ]
    return base, spots
