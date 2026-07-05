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

from . import geometry as geo
from .constants import BlendMode, Shape
from .dmx import SpotState, decode_all

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

# Formes rendues comme éventail depuis l'origine (toutes sauf TEXTE et SEGMENT)
_FAN_SHAPES = [s for s in Shape if s not in (Shape.TEXTE, Shape.SEGMENT)]


class LuxCoreEngine:
    def __init__(self, width: int, height: int, ctx: moderngl.Context | None = None):
        self.width, self.height = width, height
        self.ctx = ctx or moderngl.create_context(standalone=True, backend="egl")
        self.prog = self.ctx.program(vertex_shader=VERT, fragment_shader=FRAG)
        self.prog["u_res"] = (float(width), float(height))

        # FBO cible (RGBA8) -> lu pour NDI / PNG
        self.tex = self.ctx.texture((width, height), 4)
        self.fbo = self.ctx.framebuffer(color_attachments=[self.tex])

        self._build_shape_vbo()
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
    def render(self, base_bg, spots: list[SpotState]):
        self.fbo.use()
        r, g, b = base_bg
        self.ctx.clear(r / 255.0, g / 255.0, b / 255.0, 1.0)

        for sp in spots:
            if not sp.is_drawable():
                continue
            shape = sp.shape
            if shape not in self._ranges:      # TEXTE / SEGMENT : reportés
                continue
            self._apply_blend(sp.blend_mode)

            sx, sy = geo.scale_factors(shape, sp.size_pan, sp.size_tilt)
            self.prog["u_scale"] = (sx, sy)
            self.prog["u_rot"] = math.radians(sp.rotation)
            self.prog["u_translate"] = (self.width * 0.5 + sp.position_pan,
                                        self.height * 0.5 + sp.position_tilt)
            fr, fg, fb = sp.fill
            self.prog["u_color"] = (fr / 255.0, fg / 255.0, fb / 255.0,
                                    sp.alpha / 255.0)

            first, count = self._ranges[shape]
            self.vao.render(moderngl.TRIANGLE_FAN, vertices=count, first=first)

    def render_dmx(self, dmx_buf, num_spots: int, n_fonts: int = 0):
        base, spots = decode_all(dmx_buf, num_spots, self.width, self.height, n_fonts)
        self.render(base.bg, spots)
        return base, spots

    def read_rgba(self, into: bytearray | None = None):
        """Lit le FBO en octets RGBA (top-down)."""
        if into is not None:
            self.fbo.read_into(into, components=4, dtype="f1")
            return into
        return self.fbo.read(components=4, dtype="f1")
