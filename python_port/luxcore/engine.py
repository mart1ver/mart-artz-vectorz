"""Moteur de rendu moderngl — mini-pipeline bout-en-bout (étape B).

Rend le fond + les spots (formes remplies) depuis un buffer DMX décodé, dans un
FBO prêt pour NDI. Rétained-mode : chaque forme est un VBO-unité construit une
fois, mis à l'échelle/tourné/positionné par spot via des uniforms.

Couverture actuelle :
  - 14 formes remplies via TRIANGLE_FAN depuis l'origine (correct pour toutes les
    formes étoilées-convexes : ellipse, rect, polygones réguliers, losange,
    triangle, étoile, croix, plus, fleur ; cœur/flèche ~corrects, earcut en 3b).
  - blend mode par spot (BLEND/ADD/SCREEN/MULTIPLY/LIGHTEST/DARKEST ; les autres
    retombent sur BLEND pour l'instant).
  - fond RGB (do_background).
Reporté : contour (stroke), TEXTE (atlas glyphes), SEGMENT épais, post-effets.
"""
from __future__ import annotations

import math

import moderngl
import numpy as np

from . import blades as blades_mod
from . import geometry as geo
from . import stroke as stroke_mod
from .constants import BlendMode, Shape
from .dmx import BaseState, SpotState, decode_all
from .text import FontCache

# Contour : ellipse/rect utilisent strokeWeight plein ; les autres polygones
# strokeWeight/5 (cf. render_*_optimized).
_FULL_STROKE = (Shape.ELLIPSE, Shape.RECTANGLE)

VERT = """
#version 330
in vec2 in_pos;
uniform vec2 u_scale;
uniform float u_rot;         // radians (sens horaire, espace pixel Y-bas)
uniform vec2 u_translate;    // pixels, origine haut-gauche
uniform vec2 u_res;
void main() {
    vec2 p = in_pos * u_scale;
    float c = cos(u_rot), s = sin(u_rot);
    vec2 r = vec2(p.x * c - p.y * s, p.x * s + p.y * c);
    vec2 world = r + u_translate;
    // origine haut-gauche, Y bas ; stocké top-down pour lecture NDI directe :
    float x = world.x / u_res.x * 2.0 - 1.0;
    float y = world.y / u_res.y * 2.0 - 1.0;
    gl_Position = vec4(x, y, 0.0, 1.0);
}
"""

FRAG = """
#version 330
out vec4 frag;
uniform vec4 u_color;        // straight alpha (r,g,b,a) 0..1
void main() { frag = u_color; }
"""

# Programme texte : même transform, avec UV pour échantillonner le glyphe
TEXT_VERT = """
#version 330
in vec2 in_pos;
in vec2 in_uv;
out vec2 uv;
uniform vec2 u_scale;
uniform float u_rot;
uniform vec2 u_translate;
uniform vec2 u_res;
void main() {
    vec2 p = in_pos * u_scale;
    float c = cos(u_rot), s = sin(u_rot);
    vec2 r = vec2(p.x * c - p.y * s, p.x * s + p.y * c);
    vec2 world = r + u_translate;
    gl_Position = vec4(world.x / u_res.x * 2.0 - 1.0,
                       world.y / u_res.y * 2.0 - 1.0, 0.0, 1.0);
    uv = in_uv;
}
"""

TEXT_FRAG = """
#version 330
in vec2 uv;
out vec4 frag;
uniform sampler2D glyph;
uniform vec4 u_color;        // couleur de remplissage du texte
void main() {
    float a = texture(glyph, uv).a;      // couverture du glyphe
    frag = vec4(u_color.rgb, u_color.a * a);
}
"""

# Formes rendues comme éventail depuis l'origine (toutes sauf TEXTE et SEGMENT)
_FAN_SHAPES = [s for s in Shape if s not in (Shape.TEXTE, Shape.SEGMENT)]


class LuxCoreEngine:
    def __init__(self, width: int, height: int, ctx: moderngl.Context | None = None,
                 fonts_dir: str | None = None):
        self.width, self.height = width, height
        self.ctx = ctx or moderngl.create_context(standalone=True, backend="egl")
        self.prog = self.ctx.program(vertex_shader=VERT, fragment_shader=FRAG)
        self.prog["u_res"] = (float(width), float(height))

        # FBO cible (RGBA8) -> lu pour NDI / PNG
        self.tex = self.ctx.texture((width, height), 4)
        self.fbo = self.ctx.framebuffer(color_attachments=[self.tex])

        self._build_shape_vbo()

        # VBO dynamique pour contours/segments (ruban recalculé par spot)
        self._dyn_vbo = self.ctx.buffer(reserve=8192, dynamic=True)
        self._dyn_vao = self.ctx.vertex_array(
            self.prog, [(self._dyn_vbo, "2f4", "in_pos")])

        # -- texte : polices + programme + quad dynamique (pos+uv) + cache textures --
        self.fonts = FontCache(fonts_dir) if fonts_dir else None
        self.n_fonts = self.fonts.count if self.fonts else 0
        self._text_prog = self.ctx.program(vertex_shader=TEXT_VERT,
                                            fragment_shader=TEXT_FRAG)
        self._text_prog["u_res"] = (float(width), float(height))
        self._text_vbo = self.ctx.buffer(reserve=4 * 4 * 4, dynamic=True)  # 4 verts×4f
        self._text_vao = self.ctx.vertex_array(
            self._text_prog, [(self._text_vbo, "2f4 2f4", "in_pos", "in_uv")])
        self._glyph_tex: dict[tuple[int, str], moderngl.Texture] = {}

        self.ctx.enable(moderngl.BLEND)

    # -- construction des VBO-unité (une fois) --
    def _build_shape_vbo(self):
        verts: list[float] = []
        self._ranges: dict[Shape, tuple[int, int]] = {}
        for shape in _FAN_SHAPES:
            poly = geo.unit_polygon(shape)
            fan = [(0.0, 0.0)] + list(poly) + [poly[0]]   # centre + contour fermé
            first = len(verts) // 2
            for (x, y) in fan:
                verts.extend((x, y))
            self._ranges[shape] = (first, len(fan))
        arr = np.array(verts, dtype="f4")
        self.vbo = self.ctx.buffer(arr.tobytes())
        self.vao = self.ctx.vertex_array(self.prog, [(self.vbo, "2f4", "in_pos")])

    # -- mapping blend BlendMode -> état GL --
    def _apply_blend(self, mode: BlendMode):
        ctx = self.ctx
        A, O = moderngl.SRC_ALPHA, moderngl.ONE
        if mode == BlendMode.ADD:
            ctx.blend_equation = moderngl.FUNC_ADD
            ctx.blend_func = (A, O)
        elif mode == BlendMode.SCREEN:
            ctx.blend_equation = moderngl.FUNC_ADD
            ctx.blend_func = (moderngl.ONE, moderngl.ONE_MINUS_SRC_COLOR)
        elif mode == BlendMode.MULTIPLY:
            ctx.blend_equation = moderngl.FUNC_ADD
            ctx.blend_func = (moderngl.DST_COLOR, moderngl.ZERO)
        elif mode == BlendMode.LIGHTEST:
            ctx.blend_equation = moderngl.MAX
            ctx.blend_func = (moderngl.ONE, moderngl.ONE)
        elif mode == BlendMode.DARKEST:
            ctx.blend_equation = moderngl.MIN
            ctx.blend_func = (moderngl.ONE, moderngl.ONE)
        else:   # BLEND (normal) + fallback pour SUBTRACT/DIFFERENCE/EXCLUSION/REPLACE
            ctx.blend_equation = moderngl.FUNC_ADD
            ctx.blend_func = (moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA)

    # -- rendu d'une frame --
    def render(self, base: BaseState, spots: list[SpotState]):
        self.fbo.use()
        r, g, b = base.bg
        self.ctx.clear(r / 255.0, g / 255.0, b / 255.0, 1.0)

        for sp in spots:
            if not sp.is_drawable():
                continue
            shape = sp.shape
            self._apply_blend(sp.blend_mode)

            cx = self.width * 0.5 + sp.position_pan
            cy = self.height * 0.5 + sp.position_tilt

            if shape == Shape.TEXTE:
                if self.fonts:
                    self._draw_text(sp, cx, cy)
                continue

            self.prog["u_rot"] = math.radians(sp.rotation)
            self.prog["u_translate"] = (cx, cy)

            if shape == Shape.SEGMENT:
                self._draw_segment(sp)
                continue

            # -- remplissage (fan rétained-mode) --
            sx, sy = geo.scale_factors(shape, sp.size_pan, sp.size_tilt)
            self.prog["u_scale"] = (sx, sy)
            self.prog["u_color"] = (*[c / 255.0 for c in sp.fill], sp.alpha / 255.0)
            first, count = self._ranges[shape]
            self.vao.render(moderngl.TRIANGLE_FAN, vertices=count, first=first)

            # -- contour (stroke), seulement s'il est visible --
            if sp.stroke_alpha > 0 and sp.stroke_weight > 0:
                self._draw_stroke(sp, shape)

        self._draw_blades(base)

    def _draw_blades(self, base: BaseState):
        # 4 quads noirs opaques, en pixels absolus, après les spots
        self._apply_blend(BlendMode.BLEND)
        self.prog["u_scale"] = (1.0, 1.0)
        self.prog["u_rot"] = 0.0
        self.prog["u_translate"] = (0.0, 0.0)
        self.prog["u_color"] = (0.0, 0.0, 0.0, 1.0)
        quads = blades_mod.blade_quads(base.blades_16, self.width, self.height)
        for i, quad in enumerate(quads):
            if not blades_mod.blade_is_active(base.blades_16, i):
                continue
            self._dyn_vbo.write(quad.tobytes())
            self._dyn_vao.render(moderngl.TRIANGLE_FAN, vertices=4)

    def _draw_stroke(self, sp: SpotState, shape: Shape):
        width = sp.stroke_weight if shape in _FULL_STROKE else sp.stroke_weight / 5.0
        poly = geo.scaled_polygon_np(shape, sp.size_pan, sp.size_tilt)
        ribbon = stroke_mod.outline_ribbon(poly, width)
        if ribbon.size == 0:
            return
        self._dyn_vbo.write(ribbon.tobytes())
        self.prog["u_scale"] = (1.0, 1.0)      # ruban déjà en pixels locaux
        self.prog["u_color"] = (*[c / 255.0 for c in sp.stroke],
                                sp.stroke_alpha / 255.0)
        self._dyn_vao.render(moderngl.TRIANGLE_STRIP, vertices=ribbon.size // 2)

    def _draw_segment(self, sp: SpotState):
        # SEGMENT : trait épais en couleur de contour (size_tilt -> épaisseur)
        thickness = max(1.0, sp.size_tilt / 500.0)
        quad = stroke_mod.segment_quad(sp.size_pan, thickness)
        self._dyn_vbo.write(quad.tobytes())
        self.prog["u_scale"] = (1.0, 1.0)
        self.prog["u_color"] = (*[c / 255.0 for c in sp.stroke],
                                sp.stroke_alpha / 255.0)
        self._dyn_vao.render(moderngl.TRIANGLE_STRIP, vertices=4)

    def _draw_text(self, sp: SpotState, cx: float, cy: float):
        char = sp.text_char
        arr, w, h = self.fonts.glyph(sp.font_index, char)
        if w <= 1 and h <= 1:                  # glyphe vide (espace)
            return
        key = (sp.font_index, char)
        tex = self._glyph_tex.get(key)
        if tex is None:
            tex = self.ctx.texture((w, h), 4, arr.tobytes())
            tex.filter = (moderngl.LINEAR, moderngl.LINEAR)
            tex.repeat_x = tex.repeat_y = False    # clamp : pas de bleed aux bords
            self._glyph_tex[key] = tex

        hw, hh = w * 0.5, h * 0.5              # glyphe centré (textAlign CENTER)
        quad = np.array([-hw, -hh, 0.0, 0.0,
                         hw, -hh, 1.0, 0.0,
                         -hw, hh, 0.0, 1.0,
                         hw, hh, 1.0, 1.0], dtype="f4")
        self._text_vbo.write(quad.tobytes())
        scale = sp.size_pan / 80.0             # scale(size_pan/80) de Processing
        self._text_prog["u_scale"] = (scale, scale)
        self._text_prog["u_rot"] = math.radians(sp.rotation)
        self._text_prog["u_translate"] = (cx, cy)
        self._text_prog["u_color"] = (*[c / 255.0 for c in sp.fill], sp.alpha / 255.0)
        tex.use(0)
        self._text_prog["glyph"] = 0
        self._text_vao.render(moderngl.TRIANGLE_STRIP, vertices=4)

    def render_dmx(self, dmx_buf, num_spots: int, n_fonts: int | None = None):
        nf = self.n_fonts if n_fonts is None else n_fonts
        base, spots = decode_all(dmx_buf, num_spots, self.width, self.height, nf)
        self.render(base, spots)
        return base, spots

    def read_rgba(self, into: bytearray | None = None):
        """Lit le FBO en octets RGBA (top-down)."""
        if into is not None:
            self.fbo.read_into(into, components=4, dtype="f1")
            return into
        return self.fbo.read(components=4, dtype="f1")
