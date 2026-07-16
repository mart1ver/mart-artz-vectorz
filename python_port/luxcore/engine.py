"""Moteur de rendu moderngl — mini-pipeline bout-en-bout (étape B).

Rend le fond + les spots (formes remplies) depuis un buffer DMX décodé, dans un
FBO prêt pour NDI. Rétained-mode : chaque forme est un VBO-unité construit une
fois, mis à l'échelle/tourné/positionné par spot via des uniforms.

Couverture actuelle :
  - 13 formes remplies via GL_TRIANGLES (triangulation ear-clip pré-calculée,
    cf. geometry.unit_triangles_np) : ellipse, rect, polygones réguliers,
    losange, triangle, étoile, croix, flèche, cœur, rafale — correct y compris
    pour les formes concaves (flèche/cœur) que l'éventail-origine recouvrait.
  - blend mode par spot (BLEND/ADD/SCREEN/MULTIPLY/LIGHTEST/DARKEST ; les autres
    retombent sur BLEND pour l'instant).
  - fond RGB (do_background).
Reporté : contour (stroke), TEXTE (atlas glyphes), SEGMENT épais, post-effets.
"""
from __future__ import annotations

import math
import time

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

# Forme remplie par la vidéo : même transform que VERT, UV calculé depuis la
# position unité (formes en [-0.5,0.5] -> uv [0,1], comme le quad vidéo). Le
# fragment échantillonne la vidéo (VIDEO_FRAG) ; la triangulation de la forme
# sert de masque -> la vidéo prend la silhouette du spot.
SHAPEVID_VERT = """
#version 330
in vec2 in_pos;
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
    uv = in_pos + 0.5;
}
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
        # programme « forme remplie par la vidéo » (UV depuis la position unité)
        self._shapevid_prog = self.ctx.program(vertex_shader=SHAPEVID_VERT,
                                               fragment_shader=VIDEO_FRAG)
        self._shapevid_prog["u_res"] = (float(width), float(height))

        # FBO cible (RGBA8) -> lu pour NDI / PNG
        self.tex = self.ctx.texture((width, height), 4)
        self.fbo = self.ctx.framebuffer(color_attachments=[self.tex])

        self._build_shape_vbo()
        # VAO forme+vidéo : mêmes triangles que les formes, texturés par la vidéo
        self._shapevid_vao = self.ctx.vertex_array(
            self._shapevid_prog, [(self.vbo, "2f4", "in_pos")])

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
        self._stroke_cache: dict[tuple, tuple[bytes, int]] = {}   # ruban par (forme,taille,largeur)

        self.enable_effects = True             # bypassable depuis le GUI
        self._build_effects()
        self._build_uyvy()
        paths = list(video_paths) if video_paths else ([video_path] if video_path else [])
        self._build_video(paths, video_size)
        self.ctx.enable(moderngl.BLEND)

    # -- mode VIDEO : clips décodés en cache + playhead virtuel par spot ----------
    # Chaque source (VideoClip) est décodée UNE FOIS en cache mémoire. Chaque spot
    # vidéo tient sa propre tête de lecture (start/vitesse/pause/loop, cf. dmx) : à
    # chaque frame on calcule son index, on téléverse la frame voulue dans une
    # texture dédiée au slot, et on l'échantillonne. Le canal +22 choisit la source.
    def _build_video(self, video_paths, video_size):
        self._video_prog = self.ctx.program(vertex_shader=TEXT_VERT,
                                             fragment_shader=VIDEO_FRAG)
        self._video_prog["u_res"] = (float(self.width), float(self.height))
        self._video_vbo = self.ctx.buffer(_VIDEO_QUAD.tobytes())
        self._video_vao = self.ctx.vertex_array(
            self._video_prog, [(self._video_vbo, "2f4 2f4", "in_pos", "in_uv")])
        vw, vh = video_size
        self._vid_wh = (vw, vh)
        from .video import VideoClip
        self._vid = [VideoClip(path, vw, vh).load() for path in video_paths]
        self.n_videos = len(self._vid)
        # état de lecture + texture d'upload, indexés par clé de slot (int ; "bg"
        # pour la fixture de fond). Créés paresseusement au premier rendu du slot.
        self._playheads: dict = {}
        self._vid_slot_tex: dict = {}
        self._vid_slot_last: dict = {}    # (vidx, idx) déjà téléversé -> évite les ré-uploads
        self._now = 0.0                   # horloge de la frame courante (monotonic)

    # -- playhead : avance l'état de lecture d'un spot et renvoie sa texture -------
    def _video_tex_for(self, sp: SpotState, slot):
        """Sélectionne la source (+22), avance le playhead du spot `slot` selon le
        transport DMX, téléverse la frame voulue dans la texture du slot et la
        renvoie (ou None si aucune source/rien décodé). Les spots d'un même groupe
        de sync (+5) sur la même source partagent un playhead ET une texture."""
        if self.n_videos == 0:
            return None
        vidx = min((sp.sel_raw * self.n_videos) // 256, self.n_videos - 1)
        clip = self._vid[vidx]
        n = clip.nframes
        if n == 0:
            return None

        # clé d'état : groupe de sync partagé (même id + même source), sinon le slot
        key = ("sync", sp.vid_sync, vidx) if sp.vid_sync else slot

        lo = sp.vid_in * (n - 1)
        hi = sp.vid_out * (n - 1)
        if hi <= lo:                       # région invalide -> clip entier
            lo, hi = 0.0, float(n - 1)

        st = self._playheads.get(key)
        if st is None or st["vidx"] != vidx:
            st = {"vidx": vidx, "pos": lo, "t": self._now, "pp": 1}
            self._playheads[key] = st

        dt = self._now - st["t"]
        st["t"] = self._now
        dt = 0.0 if dt < 0 else min(dt, 0.25)   # clamp des grands sauts (démarrage/pause horloge)

        tr = sp.vid_transport
        if tr == C.VID_STOP:
            st["pos"] = lo
        elif tr == C.VID_PAUSE:
            pass
        else:                              # play (0 ou 3)
            step = sp.vid_speed * clip.fps * dt
            direction = -1.0 if sp.vid_reverse else 1.0
            loop = sp.vid_loop_mode
            if loop == C.VID_PINGPONG:
                direction *= st["pp"]
            pos = st["pos"] + direction * step
            span = hi - lo
            if span <= 0:
                pos = lo
            elif loop == C.VID_ONCE:
                pos = max(lo, min(hi, pos))
            elif loop == C.VID_PINGPONG:
                if pos > hi:
                    pos = hi - (pos - hi); st["pp"] *= -1
                elif pos < lo:
                    pos = lo + (lo - pos); st["pp"] *= -1
                pos = max(lo, min(hi, pos))
            else:                          # VID_LOOP
                pos = lo + ((pos - lo) % span)
            st["pos"] = pos

        idx = int(round(st["pos"]))
        if sp.vid_strobe > 1:              # hold : fige sur des paliers de N frames
            idx = (idx // sp.vid_strobe) * sp.vid_strobe
        idx = max(0, min(n - 1, idx))

        tex = self._vid_slot_tex.get(key)
        if tex is None:
            tex = self.ctx.texture(self._vid_wh, 4)
            tex.repeat_x = tex.repeat_y = False
            self._vid_slot_tex[key] = tex
        if self._vid_slot_last.get(key) != (vidx, idx):    # upload seulement si la frame change
            tex.write(clip.frames[idx].tobytes())
            self._vid_slot_last[key] = (vidx, idx)
        return tex

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
                           ("chromatic", fx.CHROMATIC_FRAG), ("blur", fx.BLUR_FRAG),
                           ("kaleido", fx.KALEIDO_FRAG)]:
            prog = self.ctx.program(vertex_shader=fx.FULLSCREEN_VERT, fragment_shader=frag)
            if "resolution" in prog:
                prog["resolution"] = res
            self._fx[name] = prog
            self._fx_vao[name] = self.ctx.vertex_array(prog, [(fs, "2f4", "in_pos")])
        self._fx["kaleido"]["aspect"] = self.width / self.height

        # feedback : programme à 2 samplers (courant + historique) + FBO persistant
        self._fb_tex = self.ctx.texture((self.width, self.height), 4)
        self._fb_fbo = self.ctx.framebuffer(color_attachments=[self._fb_tex])
        self._fb_fbo.use()
        self.ctx.clear(0.0, 0.0, 0.0, 1.0)         # historique noir au démarrage
        fbp = self.ctx.program(vertex_shader=fx.FULLSCREEN_VERT,
                               fragment_shader=fx.FEEDBACK_FRAG)
        fbp["tex"] = 0
        fbp["hist"] = 1
        self._fx_feedback = fbp
        self._fx_feedback_vao = self.ctx.vertex_array(fbp, [(fs, "2f4", "in_pos")])

        # bloom : bright-pass + combine (2 samplers) + 2 FBO scratch pour le flou
        self._bloom_tex = [self.ctx.texture((self.width, self.height), 4) for _ in range(2)]
        self._bloom_fbo = [self.ctx.framebuffer(color_attachments=[t])
                           for t in self._bloom_tex]
        bbp = self.ctx.program(vertex_shader=fx.FULLSCREEN_VERT,
                               fragment_shader=fx.BLOOM_BRIGHT_FRAG)
        bbp["tex"] = 0
        self._fx_bloom_bright = bbp
        self._fx_bloom_bright_vao = self.ctx.vertex_array(bbp, [(fs, "2f4", "in_pos")])
        bcp = self.ctx.program(vertex_shader=fx.FULLSCREEN_VERT,
                               fragment_shader=fx.BLOOM_COMBINE_FRAG)
        bcp["tex"] = 0
        bcp["bloomTex"] = 1
        self._fx_bloom_combine = bcp
        self._fx_bloom_combine_vao = self.ctx.vertex_array(bcp, [(fs, "2f4", "in_pos")])

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
        # horloge de la frame : pilote tous les playheads vidéo (temps réel)
        self._now = time.monotonic()

        self.fbo.use()
        r, g, b = base.bg
        self.ctx.clear(r / 255.0, g / 255.0, b / 255.0, 1.0)

        # fixture de FOND : vidéo plein écran derrière tout (avant les spots)
        if bg_fix is not None and bg_fix.is_drawable() and bg_fix.shape == Shape.VIDEO:
            self._draw_bg_video(bg_fix)

        for slot, sp in enumerate(spots):
            if not sp.is_drawable():
                continue
            shape = sp.shape
            self._apply_blend(sp.blend_mode)

            cx = self.width * 0.5 + sp.position_pan
            cy = self.height * 0.5 + sp.position_tilt

            # forme remplie par la vidéo (mode 100+forme) : la silhouette de la forme
            # masque la vidéo. Le contour (stroke) n'existe plus ici : les canaux
            # stroke sont réinterprétés en transport vidéo (out/sync/strobe).
            if sp.video_fill and shape in self._ranges and self.n_videos > 0:
                sx, sy = geo.scale_factors(shape, sp.size_pan, sp.size_tilt)
                self._draw_shape_video(sp, shape, sx, sy, cx, cy, slot)
                continue

            if shape == Shape.TEXTE:
                if self.fonts:
                    self._draw_text(sp, cx, cy)
                continue

            if shape == Shape.VIDEO:
                self._draw_video(sp, cx, cy, slot)
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
        cf, ct, af, at = self._apply_feedback(base, cf, ct, af, at)
        if base.kaleido > 1:
            seg = float(max(2, min(24, base.kaleido)))
            cf, ct, af, at = self._fx_pass("kaleido", cf, ct, af, at,
                                           lambda p: p.__setitem__("segments", seg))
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
        cf, ct, af, at = self._apply_bloom(base, cf, ct, af, at)
        if base.chromatic:
            cf, ct, af, at = self._fx_pass("chromatic", cf, ct, af, at)
        self.ctx.enable(moderngl.BLEND)
        return cf, ct, af, at

    def _apply_feedback(self, base, cf, ct, af, at):
        """Traînées : out = max(courant, historique × décroissance), mémorisé
        comme historique pour la frame suivante."""
        if base.feedback <= 1:
            return cf, ct, af, at
        decay = pmap(base.feedback, 2, 255, 0.80, 0.985)
        af.use()
        ct.use(0)
        self._fb_tex.use(1)
        self._fx_feedback["decay"] = float(decay)
        self._fx_feedback_vao.render(moderngl.TRIANGLE_STRIP)
        self.ctx.copy_framebuffer(self._fb_fbo, af)   # historique <- résultat
        return af, at, cf, ct

    def _apply_bloom(self, base, cf, ct, af, at):
        """Halo lumineux : bright-pass (seuil) -> flou (blur existant) -> additif."""
        if base.bloom_amount <= 1:
            return cf, ct, af, at
        thr = base.bloom_threshold / 255.0
        inten = pmap(base.bloom_amount, 2, 255, 0.2, 2.5)
        fa, fb = self._bloom_fbo
        ta, tb = self._bloom_tex
        # 1) extraction des zones lumineuses : ct -> fa
        fa.use()
        ct.use(0)
        self._fx_bloom_bright["threshold"] = float(thr)
        self._fx_bloom_bright_vao.render(moderngl.TRIANGLE_STRIP)
        # 2) flou séparable du halo : fa -> fb (H) -> fa (V), via le prog blur
        blur = self._fx["blur"]
        blur["texOffset"] = (1.0 / self.width, 1.0 / self.height)
        blur["blurSize"] = 30
        blur["sigma"] = 8.0
        blur["tex"] = 0
        blur["horizontalPass"] = 1
        fb.use(); ta.use(0); self._fx_vao["blur"].render(moderngl.TRIANGLE_STRIP)
        blur["horizontalPass"] = 0
        fa.use(); tb.use(0); self._fx_vao["blur"].render(moderngl.TRIANGLE_STRIP)
        # 3) combine : scène (ct) + halo (ta) -> af
        af.use()
        ct.use(0)
        ta.use(1)
        self._fx_bloom_combine["intensity"] = float(inten)
        self._fx_bloom_combine_vao.render(moderngl.TRIANGLE_STRIP)
        return af, at, cf, ct

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
        # Le ruban ne dépend que de (forme, taille, largeur) — pas de la position ni
        # de la rotation (appliquées par uniformes). Les layouts symétriques ont donc
        # beaucoup de spots identiques : on mémoïse le ruban pour ne le calculer qu'une fois.
        key = (int(shape), round(sp.size_pan, 1), round(sp.size_tilt, 1), round(width, 2))
        cached = self._stroke_cache.get(key)
        if cached is None:
            poly = geo.scaled_polygon_np(shape, sp.size_pan, sp.size_tilt)
            ribbon = stroke_mod.outline_ribbon(poly, width)
            cached = (ribbon.tobytes(), ribbon.size // 2) if ribbon.size else (b"", 0)
            if len(self._stroke_cache) > 256:
                self._stroke_cache.clear()
            self._stroke_cache[key] = cached
        rb, nverts = cached
        if not nverts:
            return
        self._dyn_vbo.write(rb)
        self.prog["u_scale"] = (1.0, 1.0)      # ruban déjà en pixels locaux
        self.prog["u_color"] = (*[c / 255.0 for c in sp.stroke],
                                sp.stroke_alpha / 255.0)
        self._dyn_vao.render(moderngl.TRIANGLE_STRIP, vertices=nverts)

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
        # sélecteur (+22), l'alpha, le blend et le transport de la fixture de fond.
        tex = self._video_tex_for(sp, "bg")
        if tex is None:
            return
        self._apply_blend(sp.blend_mode)
        self._video_prog["u_scale"] = (float(self.width), float(self.height))
        self._video_prog["u_rot"] = 0.0
        self._video_prog["u_translate"] = (self.width * 0.5, self.height * 0.5)
        self._video_prog["alpha"] = sp.alpha / 255.0
        tex.use(0)
        self._video_prog["vid"] = 0
        self._video_vao.render(moderngl.TRIANGLE_STRIP, vertices=4)

    def _draw_video(self, sp: SpotState, cx: float, cy: float, slot):
        # quad texturé par la vidéo, dimensionné/positionné comme un rectangle.
        # Choix de la source (canal +22) + playhead par spot. N'IMPORTE QUEL spot
        # en mode 14 passe ici : parité totale spot/vidéo.
        tex = self._video_tex_for(sp, slot)
        if tex is None:
            return
        # échelle vidéo (permet le plein écran malgré le plafond 1000px du décodage)
        self._video_prog["u_scale"] = (sp.size_pan * VIDEO_SIZE_SCALE,
                                       sp.size_tilt * VIDEO_SIZE_SCALE)
        self._video_prog["u_rot"] = math.radians(sp.rotation)
        self._video_prog["u_translate"] = (cx, cy)
        self._video_prog["alpha"] = sp.alpha / 255.0
        tex.use(0)
        self._video_prog["vid"] = 0
        self._video_vao.render(moderngl.TRIANGLE_STRIP, vertices=4)

    def _draw_shape_video(self, sp: SpotState, shape: Shape, sx: float, sy: float,
                          cx: float, cy: float, slot):
        # La forme (triangulée) masque la vidéo : le spot prend la silhouette voulue.
        # Même sélection de source (+22) + playhead que _draw_video ; échelle = celle
        # d'une forme (pas de VIDEO_SIZE_SCALE : c'est une forme, pas un plein écran).
        tex = self._video_tex_for(sp, slot)
        if tex is None:
            return
        prog = self._shapevid_prog
        prog["u_scale"] = (sx, sy)
        prog["u_rot"] = math.radians(sp.rotation)
        prog["u_translate"] = (cx, cy)
        prog["alpha"] = sp.alpha / 255.0
        tex.use(0)
        prog["vid"] = 0
        first, count = self._ranges[shape]
        self._shapevid_vao.render(moderngl.TRIANGLES, vertices=count, first=first)

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
