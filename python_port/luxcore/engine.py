"""Moteur de rendu moderngl — mini-pipeline bout-en-bout (étape B).

Rend le fond + les spots (formes remplies) depuis un buffer DMX décodé, dans un
FBO prêt pour NDI. Rétained-mode : chaque forme est un VBO-unité construit une
fois, mis à l'échelle/tourné/positionné par spot via des uniforms.

Couverture actuelle :
  - 13 formes remplies via GL_TRIANGLES (triangulation ear-clip pré-calculée,
    cf. geometry.unit_triangles_np) : ellipse, rect, polygones réguliers,
    losange, triangle, étoile, croix, flèche, cœur, fleur — correct y compris
    pour les formes concaves (flèche/cœur) que l'éventail-origine recouvrait.
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
from . import constants as C
from .constants import BlendMode, Shape
from .dmx import BaseState, SpotState, decode_all, decode_spot, pmap
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

# Formes remplies par triangulation (toutes sauf TEXTE/SEGMENT/VIDEO)
_FILL_SHAPES = [s for s in Shape
                if s not in (Shape.TEXTE, Shape.SEGMENT, Shape.VIDEO)]

# Les fixtures vidéo peuvent couvrir tout l'écran : le décodage de taille plafonne
# à 1000px (pmap 0-65535 -> 0-1000), insuffisant pour du 1920px plein cadre. On
# ré-échelonne donc UNIQUEMENT les fixtures vidéo (les formes ne sont pas touchées).
# Doit rester synchronisé avec sz_px() côté demo_scripts (÷ 1000·VIDEO_SIZE_SCALE).
VIDEO_SIZE_SCALE = 2.5

# Quad-unité texturé (pos + uv), TRIANGLE_STRIP — pour le mode VIDEO
_VIDEO_QUAD = np.array([-0.5, -0.5, 0.0, 0.0,
                        0.5, -0.5, 1.0, 0.0,
                        -0.5, 0.5, 0.0, 1.0,
                        0.5, 0.5, 1.0, 1.0], dtype="f4")

VIDEO_FRAG = """
#version 330
in vec2 uv; out vec4 frag;
uniform sampler2D vid;
uniform float alpha;
void main() { vec4 c = texture(vid, uv); frag = vec4(c.rgb, c.a * alpha); }
"""

# Packing RGBA -> UYVY 4:2:2 (BT.709, plage vidéo 16-235) pour la sortie NDI.
# Chaque texel de sortie code 2 pixels source : octets (U, Y0, V, Y1). La cible
# fait donc W/2 × H en RGBA8, soit un readback de W*H*2 octets (moitié du RGBA).
UYVY_FRAG = """
#version 330
out vec4 frag;
uniform sampler2D src;
void main() {
    int ox = int(gl_FragCoord.x);
    int y  = int(gl_FragCoord.y);
    vec3 c0 = texelFetch(src, ivec2(ox * 2,     y), 0).rgb;
    vec3 c1 = texelFetch(src, ivec2(ox * 2 + 1, y), 0).rgb;
    vec3 cm = 0.5 * (c0 + c1);
    float y0 = 0.2126 * c0.r + 0.7152 * c0.g + 0.0722 * c0.b;
    float y1 = 0.2126 * c1.r + 0.7152 * c1.g + 0.0722 * c1.b;
    float ym = 0.2126 * cm.r + 0.7152 * cm.g + 0.0722 * cm.b;
    float cb = (cm.b - ym) / 1.8556;
    float cr = (cm.r - ym) / 1.5748;
    float U  = (128.0 + 224.0 * cb) / 255.0;
    float V  = (128.0 + 224.0 * cr) / 255.0;
    float Y0 = (16.0 + 219.0 * y0) / 255.0;
    float Y1 = (16.0 + 219.0 * y1) / 255.0;
    frag = vec4(U, Y0, V, Y1);      // octets U Y0 V Y1 = UYVY
}
"""


class LuxCoreEngine:
    def __init__(self, width: int, height: int, ctx: moderngl.Context | None = None,
                 fonts_dir: str | None = None, video_path: str | None = None,
                 video_paths: list[str] | None = None,
                 video_size: tuple[int, int] = (640, 360)):
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

        self.enable_effects = True             # bypassable depuis le GUI
        self._build_effects()
        self._build_uyvy()
        paths = list(video_paths) if video_paths else ([video_path] if video_path else [])
        self._build_video(paths, video_size)
        self.ctx.enable(moderngl.BLEND)

    # -- mode VIDEO : POOL de décodeurs (1 par fichier) + ring buffer par source --
    # Chaque source garde ses N dernières frames dans un anneau de textures, ce qui
    # permet de DÉSYNCHRONISER les panneaux (chacun échantillonne une frame retardée
    # différente) même quand plusieurs affichent la même vidéo. Le canal +22 de la
    # fixture vidéo sélectionne QUELLE vidéo du dossier est projetée.
    _VID_RING = 16                    # frames d'historique par source (désync ;
                                      # 16 suffit pour répartir les délais, ~2× moins de VRAM)

    def _build_video(self, video_paths, video_size):
        self._video_prog = self.ctx.program(vertex_shader=TEXT_VERT,
                                             fragment_shader=VIDEO_FRAG)
        self._video_prog["u_res"] = (float(self.width), float(self.height))
        self._video_vbo = self.ctx.buffer(_VIDEO_QUAD.tobytes())
        self._video_vao = self.ctx.vertex_array(
            self._video_prog, [(self._video_vbo, "2f4 2f4", "in_pos", "in_uv")])
        vw, vh = video_size
        from .video import VideoDecoder
        self._vid = []                # une entrée par vidéo du dossier
        for path in video_paths:
            dec = VideoDecoder(path, vw, vh)
            dec.start()
            ring = [self.ctx.texture((vw, vh), 4) for _ in range(self._VID_RING)]
            for t in ring:
                t.repeat_x = t.repeat_y = False
            self._vid.append({"dec": dec, "ring": ring, "head": 0, "filled": 0, "ver": -1})
        self.n_videos = len(self._vid)

    # -- post-effets : 2e FBO (ping-pong) + programmes plein écran --
    def _build_effects(self):
        from . import effects as fx
        self._tex2 = self.ctx.texture((self.width, self.height), 4)
        self._fbo2 = self.ctx.framebuffer(color_attachments=[self._tex2])
        fs = self.ctx.buffer(
            np.array([-1, -1, 1, -1, -1, 1, 1, 1], dtype="f4").tobytes())
        res = (float(self.width), float(self.height))
        self._fx = {}
        self._fx_vao = {}
        for name, frag in [("pixelate", fx.PIXELATE_FRAG), ("sobel", fx.SOBEL_FRAG),
                           ("rgbsplit", fx.RGBSPLIT_FRAG), ("saturation", fx.SATURATION_FRAG),
                           ("chromatic", fx.CHROMATIC_FRAG), ("blur", fx.BLUR_FRAG)]:
            prog = self.ctx.program(vertex_shader=fx.FULLSCREEN_VERT, fragment_shader=frag)
            if "resolution" in prog:
                prog["resolution"] = res
            self._fx[name] = prog
            self._fx_vao[name] = self.ctx.vertex_array(prog, [(fs, "2f4", "in_pos")])

    # -- sortie NDI UYVY : FBO demi-largeur + programme de packing --
    def _build_uyvy(self):
        from . import effects as fx
        self._uyvy_tex = self.ctx.texture((self.width // 2, self.height), 4)
        self._uyvy_fbo = self.ctx.framebuffer(color_attachments=[self._uyvy_tex])
        self._uyvy_prog = self.ctx.program(vertex_shader=fx.FULLSCREEN_VERT,
                                           fragment_shader=UYVY_FRAG)
        self._uyvy_prog["src"] = 0
        fs = self.ctx.buffer(
            np.array([-1, -1, 1, -1, -1, 1, 1, 1], dtype="f4").tobytes())
        self._uyvy_vao = self.ctx.vertex_array(
            self._uyvy_prog, [(fs, "2f4", "in_pos")])

    def pack_uyvy(self):
        """Rend self.tex (RGBA) en UYVY 4:2:2 dans _uyvy_fbo (largeur W/2).
        À lire ensuite pour NDI : W*H*2 octets au lieu de W*H*4. Retourne le FBO."""
        self._uyvy_fbo.use()
        self.ctx.disable(moderngl.BLEND)
        self.tex.use(0)
        self._uyvy_vao.render(moderngl.TRIANGLE_STRIP)
        self.ctx.enable(moderngl.BLEND)
        return self._uyvy_fbo

    # -- construction des VBO-unité (une fois) --
    def _build_shape_vbo(self):
        # Remplissage par triangulation ear-clip (GL_TRIANGLES) : correct pour
        # les formes concaves (flèche, cœur) que l'éventail-origine recouvrait.
        chunks: list[np.ndarray] = []
        self._ranges: dict[Shape, tuple[int, int]] = {}
        first = 0
        for shape in _FILL_SHAPES:
            tris = geo.unit_triangles_np(shape)               # (M,2), 3 sommets/triangle
            count = len(tris)
            self._ranges[shape] = (first, count)
            chunks.append(tris)
            first += count
        arr = np.concatenate(chunks).astype("f4") if chunks else np.empty((0, 2), "f4")
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
    def render(self, base: BaseState, spots: list[SpotState],
               bg_fix: SpotState | None = None):
        # téléverse la dernière frame de CHAQUE source dans son anneau (désync)
        for s in self._vid:
            frame, ver = s["dec"].latest()
            if frame is not None and ver != s["ver"]:
                s["ring"][s["head"]].write(frame.tobytes())
                s["head"] = (s["head"] + 1) % self._VID_RING
                s["filled"] = min(s["filled"] + 1, self._VID_RING)
                s["ver"] = ver

        # nb de fixtures vidéo visibles -> répartition des délais de désync
        n_vid = sum(1 for sp in spots if sp.is_drawable() and sp.shape == Shape.VIDEO)

        self.fbo.use()
        r, g, b = base.bg
        self.ctx.clear(r / 255.0, g / 255.0, b / 255.0, 1.0)

        # fixture de FOND : vidéo plein écran derrière tout (avant les spots)
        if bg_fix is not None and bg_fix.is_drawable() and bg_fix.shape == Shape.VIDEO:
            self._draw_bg_video(bg_fix)

        vid_ord = 0
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

            if shape == Shape.VIDEO:
                self._draw_video(sp, cx, cy, vid_ord, n_vid)
                vid_ord += 1
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
            self.vao.render(moderngl.TRIANGLES, vertices=count, first=first)

            # -- contour (stroke), seulement s'il est visible --
            if sp.stroke_alpha > 0 and sp.stroke_weight > 0:
                self._draw_stroke(sp, shape)

        # -- pipeline : effets (bg+spots) -> blades -> blur (do_blade_blur) --
        cf, ct, af, at = self.fbo, self.tex, self._fbo2, self._tex2
        cf, ct, af, at = self._apply_effects(base, cf, ct, af, at)

        cf.use()
        self._draw_blades(base)

        cf, ct, af, at = self._apply_blur(base, cf, ct, af, at)

        if ct is not self.tex:                 # le résultat final doit être dans self.tex
            self.ctx.copy_framebuffer(self.fbo, cf)

    def _fx_pass(self, name, cf, ct, af, at, setup=None):
        af.use()
        ct.use(0)
        prog = self._fx[name]
        prog["tex"] = 0
        if setup:
            setup(prog)
        self._fx_vao[name].render(moderngl.TRIANGLE_STRIP)
        return af, at, cf, ct               # buffers échangés

    def _apply_effects(self, base, cf, ct, af, at):
        if not self.enable_effects:
            return cf, ct, af, at
        self.ctx.disable(moderngl.BLEND)      # les effets écrasent, pas de blend
        if base.pixelate > 1:
            amt = pmap(base.pixelate, 0, 255, 255, 20)
            cf, ct, af, at = self._fx_pass("pixelate", cf, ct, af, at,
                                           lambda p: p.__setitem__("amount", amt))
        if base.sobel:
            cf, ct, af, at = self._fx_pass("sobel", cf, ct, af, at)
        if base.rgb_split > 1:
            cf, ct, af, at = self._fx_pass("rgbsplit", cf, ct, af, at,
                                           lambda p: p.__setitem__("delta", float(base.rgb_split)))
        if base.saturation_a > 0.001 or base.saturation_b > 0.001:
            def _su(p):
                p["saturation"] = float(base.saturation_a)
                p["vibrance"] = float(base.saturation_b)
            cf, ct, af, at = self._fx_pass("saturation", cf, ct, af, at, _su)
        if base.chromatic:
            cf, ct, af, at = self._fx_pass("chromatic", cf, ct, af, at)
        self.ctx.enable(moderngl.BLEND)
        return cf, ct, af, at

    def _apply_blur(self, base, cf, ct, af, at):
        if not self.enable_effects or (base.blur_size <= 0.1 and base.blur_sigma <= 0.1):
            return cf, ct, af, at
        self.ctx.disable(moderngl.BLEND)
        prog = self._fx["blur"]
        prog["texOffset"] = (1.0 / self.width, 1.0 / self.height)
        prog["blurSize"] = int(base.blur_size)
        prog["sigma"] = max(0.1, float(base.blur_sigma))
        prog["horizontalPass"] = 1
        cf, ct, af, at = self._fx_pass("blur", cf, ct, af, at)
        prog["horizontalPass"] = 0
        cf, ct, af, at = self._fx_pass("blur", cf, ct, af, at)
        self.ctx.enable(moderngl.BLEND)
        return cf, ct, af, at

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

    def _draw_bg_video(self, sp: SpotState):
        # vidéo de FOND : plein écran, derrière tous les spots. Respecte le
        # sélecteur (+22), l'alpha et le blend de la fixture de fond.
        if self.n_videos == 0:
            return
        vidx = min((sp.sel_raw * self.n_videos) // 256, self.n_videos - 1)
        s = self._vid[vidx]
        if s["filled"] == 0:
            return
        tex = s["ring"][(s["head"] - 1) % self._VID_RING]
        self._apply_blend(sp.blend_mode)
        self._video_prog["u_scale"] = (float(self.width), float(self.height))
        self._video_prog["u_rot"] = 0.0
        self._video_prog["u_translate"] = (self.width * 0.5, self.height * 0.5)
        self._video_prog["alpha"] = sp.alpha / 255.0
        tex.use(0)
        self._video_prog["vid"] = 0
        self._video_vao.render(moderngl.TRIANGLE_STRIP, vertices=4)

    def _draw_video(self, sp: SpotState, cx: float, cy: float, ord: int = 0, n_vid: int = 1):
        # quad texturé par la vidéo, dimensionné/positionné comme un rectangle.
        # Choix de la source (canal +22) + frame retardée (désync entre panneaux).
        # N'IMPORTE QUEL spot en mode 14 passe ici : parité totale spot/vidéo.
        if self.n_videos == 0:
            return
        vidx = min((sp.sel_raw * self.n_videos) // 256, self.n_videos - 1)
        s = self._vid[vidx]
        if s["filled"] == 0:
            return                              # rien encore décodé
        delay = 0
        if n_vid > 1:                           # >1 panneau -> on les désynchronise
            delay = int(round(ord / n_vid * (s["filled"] - 1)))
        tex = s["ring"][(s["head"] - 1 - delay) % self._VID_RING]
        # échelle vidéo (permet le plein écran malgré le plafond 1000px du décodage)
        self._video_prog["u_scale"] = (sp.size_pan * VIDEO_SIZE_SCALE,
                                       sp.size_tilt * VIDEO_SIZE_SCALE)
        self._video_prog["u_rot"] = math.radians(sp.rotation)
        self._video_prog["u_translate"] = (cx, cy)
        self._video_prog["alpha"] = sp.alpha / 255.0
        tex.use(0)
        self._video_prog["vid"] = 0
        self._video_vao.render(moderngl.TRIANGLE_STRIP, vertices=4)

    def render_dmx(self, dmx_buf, num_spots: int, n_fonts: int | None = None):
        # Fixture unifiée : plus de famille vidéo dédiée. Tout spot en mode 14
        # (VIDEO) est rendu en vidéo, avec sélection (+22) et échelle plein écran.
        nf = self.n_fonts if n_fonts is None else n_fonts
        base, spots = decode_all(dmx_buf, num_spots, self.width, self.height, nf)
        # fixture de fond (slot réservé, dessinée derrière les spots)
        bg_fix = decode_spot(dmx_buf, C.bg_fixture_base_addr(),
                             self.width * 0.5, self.height * 0.5,
                             base.blend_global, nf)
        self.render(base, spots, bg_fix)
        return base, spots

    def read_rgba(self, into: bytearray | None = None):
        """Lit le FBO en octets RGBA (top-down)."""
        if into is not None:
            self.fbo.read_into(into, components=4, dtype="f1")
            return into
        return self.fbo.read(components=4, dtype="f1")
