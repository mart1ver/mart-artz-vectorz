"""Adaptateur imgui-bundle 1.92 <-> moderngl-window.

moderngl-window 3.1.1 rend imgui via moderngl, mais suppose l'ancienne API
d'atlas de police (get_tex_data_as_rgba32), supprimée dans imgui-bundle 1.92 au
profit d'un protocole de textures dynamiques (ImGuiBackendFlags_RendererHasTextures
+ platform_io.textures). On réutilise le rendu (vertices/clip) de l'intégration
et on ne réimplémente que la gestion des textures.

Usage :
    impl = Imgui192Renderer(window)
    ...
    imgui.new_frame(); build_ui(); imgui.render()
    impl.update_textures()                 # créer/màj/détruire les textures
    impl.render(imgui.get_draw_data())
"""
from __future__ import annotations

import ctypes

import moderngl
from imgui_bundle import imgui
from moderngl_window.integrations.imgui_bundle import ModernglWindowRenderer


class Imgui192Renderer(ModernglWindowRenderer):
    def __init__(self, window):
        io = imgui.get_io()
        io.backend_flags |= imgui.BackendFlags_.renderer_has_textures.value
        self._td_tex: dict[int, moderngl.Texture] = {}
        super().__init__(window)              # appelle refresh_font_texture() (no-op ici)
        # texture 1x1 par défaut pour le bind initial de render() (rebind par commande)
        self._font_texture = self.ctx.texture((1, 1), 4, b"\xff\xff\xff\xff")
        self.register_texture(self._font_texture)

    def refresh_font_texture(self):
        pass                                  # géré par update_textures() (protocole 1.92)

    def render(self, draw_data):
        # Copie de ModernglWindowRenderer.render avec command.texture_id ->
        # command.get_tex_id() (renommé dans imgui-bundle 1.92).
        io = self.io
        display_width, display_height = io.display_size
        fb_width = int(display_width * io.display_framebuffer_scale[0])
        fb_height = int(display_height * io.display_framebuffer_scale[1])
        if fb_width == 0 or fb_height == 0:
            return
        self.projMat.value = (
            2.0 / display_width, 0.0, 0.0, 0.0,
            0.0, 2.0 / -display_height, 0.0, 0.0,
            0.0, 0.0, -1.0, 0.0,
            -1.0, 1.0, 0.0, 1.0,
        )
        draw_data.scale_clip_rects(imgui.ImVec2(*io.display_framebuffer_scale))
        self.ctx.enable_only(moderngl.BLEND)
        self.ctx.blend_equation = moderngl.FUNC_ADD
        self.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
        self._font_texture.use()
        for commands in draw_data.cmd_lists:
            vtx_type = ctypes.c_byte * commands.vtx_buffer.size() * imgui.VERTEX_SIZE
            idx_type = ctypes.c_byte * commands.idx_buffer.size() * imgui.INDEX_SIZE
            vtx_arr = (vtx_type).from_address(commands.vtx_buffer.data_address())
            idx_arr = (idx_type).from_address(commands.idx_buffer.data_address())
            self._vertex_buffer.write(vtx_arr)
            self._index_buffer.write(idx_arr)
            idx_pos = 0
            for command in commands.cmd_buffer:
                tex_id = command.get_tex_id()
                texture = self._textures.get(tex_id)
                if texture is not None:
                    texture.use(0)
                x, y, z, w = command.clip_rect
                self.ctx.scissor = int(x), int(fb_height - w), int(z - x), int(w - y)
                self._vao.render(moderngl.TRIANGLES, vertices=command.elem_count,
                                 first=idx_pos)
                idx_pos += command.elem_count
        self.ctx.scissor = None

    def update_textures(self):
        for td in imgui.get_platform_io().textures:
            st = td.status
            if st == imgui.ImTextureStatus.want_create:
                data = _pixels_bytes(td)
                tex = self.ctx.texture((td.width, td.height), 4, data=data)
                tex.filter = (moderngl.LINEAR, moderngl.LINEAR)
                self.register_texture(tex)
                td.set_tex_id(tex.glo)
                td.set_status(imgui.ImTextureStatus.ok)
                self._td_tex[td.unique_id] = tex
            elif st == imgui.ImTextureStatus.want_updates:
                tex = self._td_tex.get(td.unique_id)
                if tex is not None:
                    tex.write(_pixels_bytes(td))
                    td.set_status(imgui.ImTextureStatus.ok)
            elif st == imgui.ImTextureStatus.want_destroy and td.unused_frames > 0:
                tex = self._td_tex.pop(td.unique_id, None)
                if tex is not None:
                    self.remove_texture(tex)
                    tex.release()
                td.set_tex_id(0)
                td.set_status(imgui.ImTextureStatus.destroyed)


def _pixels_bytes(td) -> bytes:
    arr = td.get_pixels_array()               # (h, w, 4) uint8
    return arr.tobytes() if hasattr(arr, "tobytes") else bytes(arr)
