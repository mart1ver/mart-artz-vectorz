#!/usr/bin/env python3
"""Moteur LuxCore — boucle live : ArtNet -> décodage -> rendu -> NDI (étape B).

Assemble les trois modules déjà écrits (artnet, dmx, engine) avec la sortie NDI
optimisée du spike (readback PBO + worker d'envoi). Piloter en envoyant de
l'ArtNet (p.ex. demo_scripts/defile_formes.py) et regarder la source NDI
"LuxCore" dans OBS / vMix / Resolume.

    python_port/.venv/bin/python python_port/run_engine.py --spots 15 --duration 0
"""
import argparse
import os
import queue
import shutil
import subprocess
import threading
import time
from fractions import Fraction

import numpy as np

from luxcore.artnet import ArtNetReceiver
from luxcore.engine import LuxCoreEngine


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--width", type=int, default=1920)
    ap.add_argument("--height", type=int, default=1080)
    ap.add_argument("--fps", type=int, default=60)
    ap.add_argument("--spots", type=int, default=60,
                    help="nombre de fixtures décodées (une fixture en mode 14 = vidéo)")
    ap.add_argument("--duration", type=float, default=20.0, help="0 = jusqu'à Ctrl+C")
    ap.add_argument("--name", default="LuxCore")
    ap.add_argument("--snapshot-dir", help="sauve un PNG toutes les --snapshot-interval s")
    ap.add_argument("--snapshot-interval", type=float, default=2.0)
    ap.add_argument("--preview", action="store_true",
                    help="ouvre une fenêtre d'aperçu à l'écran (en plus du NDI)")
    ap.add_argument("--preview-scale", type=float, default=0.66,
                    help="taille de la fenêtre d'aperçu (× la résolution de rendu)")
    ap.add_argument("--fonts-dir",
                    default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                         "..", "data", "fonts"),
                    help="dossier des polices .ttf (mode TEXTE)")
    ap.add_argument("--no-fonts", action="store_true", help="désactive le texte")
    ap.add_argument("--no-gui", action="store_true",
                    help="désactive le panneau GUI imgui (aperçu seul)")
    ap.add_argument("--video", help="fichier vidéo unique (compat) pour le mode forme VIDEO")
    ap.add_argument("--videos-dir",
                    default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                         "..", "data", "videos"),
                    help="dossier de vidéos ; le canal +22 d'un spot en mode 14 choisit "
                         "laquelle est projetée (trié par nom)")
    args = ap.parse_args()

    fonts_dir = None if args.no_fonts else args.fonts_dir

    # Liste des vidéos : dossier (trié par nom) + éventuel --video en tête
    import glob
    video_paths = []
    if args.video:
        video_paths.append(args.video)
    if args.videos_dir and os.path.isdir(args.videos_dir):
        for ext in ("*.mp4", "*.mov", "*.mkv", "*.webm", "*.avi"):
            video_paths.extend(sorted(glob.glob(os.path.join(args.videos_dir, ext))))
    # dédoublonne en gardant l'ordre
    video_paths = list(dict.fromkeys(video_paths))
    if video_paths:
        print(f"[video] {len(video_paths)} vidéo(s) : "
              + ", ".join(os.path.basename(p) for p in video_paths))

    snap_idx = 0
    last_snap = 0.0
    if args.snapshot_dir:
        os.makedirs(args.snapshot_dir, exist_ok=True)

    W, H, FPS = args.width, args.height, args.fps

    # état partagé avec le GUI
    state = {"spots": args.spots, "effects": True,
             "restart_artnet": False, "gui_visible": True}

    # -- contexte GL : fenêtre d'aperçu (pyglet) ou headless (EGL standalone) --
    # -- plein écran : masquer le curseur + empêcher la mise en veille --------
    _inhibit = {"proc": None, "xset": False}

    def _sleep_inhibit(on):
        """Bloque (on=True) / libère la mise en veille idle+sleep de l'ordinateur."""
        if on and _inhibit["proc"] is None and shutil.which("systemd-inhibit"):
            _inhibit["proc"] = subprocess.Popen(
                ["systemd-inhibit", "--what=idle:sleep", "--who=LuxCore",
                 "--why=LuxCore plein écran", "--mode=block", "sleep", "infinity"])
        if not on and _inhibit["proc"] is not None:
            _inhibit["proc"].terminate()
            _inhibit["proc"] = None
        # En complément (X11) : désactive économiseur d'écran + DPMS.
        # Silencieux : certains serveurs X n'ont pas l'extension DPMS (sans gravité,
        # systemd-inhibit reste le mécanisme principal).
        if os.environ.get("DISPLAY") and shutil.which("xset"):
            devnull = subprocess.DEVNULL
            if on and not _inhibit["xset"]:
                subprocess.call(["xset", "s", "off"], stdout=devnull, stderr=devnull)
                subprocess.call(["xset", "-dpms"], stdout=devnull, stderr=devnull)
                _inhibit["xset"] = True
            elif not on and _inhibit["xset"]:
                subprocess.call(["xset", "s", "on"], stdout=devnull, stderr=devnull)
                subprocess.call(["xset", "+dpms"], stdout=devnull, stderr=devnull)
                _inhibit["xset"] = False

    def _set_fullscreen(_w, full):
        """Passe en/hors plein écran : masque le curseur et inhibe la veille."""
        _w.fullscreen = full
        try:
            _w.cursor = not full            # curseur masqué en plein écran
        except Exception:
            pass
        _sleep_inhibit(full)

    window = None
    blit = None
    gui_impl = None
    if args.preview:
        # fenêtre moderngl-window : contexte GL + intégration imgui via moderngl
        # (pas de PyOpenGL, robuste sur Wayland/X11)
        import moderngl_window as mglw
        Wp, Hp = int(W * args.preview_scale), int(H * args.preview_scale)
        window_cls = mglw.get_local_window_cls()
        window = window_cls(size=(Wp, Hp), title=f"LuxCore — aperçu ({args.name})",
                            gl_version=(3, 3), vsync=False, resizable=True)
        mglw.activate_context(window=window)
        ctx = window.ctx
        eng = LuxCoreEngine(W, H, ctx=ctx, fonts_dir=fonts_dir, video_paths=video_paths)
        # blit : FBO (top-down pour NDI) -> écran, V inversé pour être droit
        blit_prog = ctx.program(
            vertex_shader="#version 330\nin vec2 p;out vec2 uv;"
                          "void main(){uv=p*0.5+0.5;gl_Position=vec4(p,0,1);}",
            fragment_shader="#version 330\nin vec2 uv;out vec4 f;uniform sampler2D t;"
                            "void main(){f=texture(t,vec2(uv.x,1.0-uv.y));}")
        quad = ctx.buffer(np.array([-1, -1, 1, -1, -1, 1, 1, 1], dtype="f4").tobytes())
        blit_vao = ctx.vertex_array(blit_prog, [(quad, "2f4", "p")])
        blit = (ctx, blit_prog, blit_vao)

        # -- GUI imgui (rendu via moderngl) --
        if not args.no_gui:
            from imgui_bundle import imgui
            from luxcore.imgui_backend import Imgui192Renderer
            imgui.create_context()
            try:
                imgui.get_io().set_ini_filename("")   # pas de imgui.ini dans le repo
            except Exception:
                pass
            gui_impl = Imgui192Renderer(window)
            window.mouse_position_event_func = gui_impl.mouse_position_event
            window.mouse_drag_event_func = gui_impl.mouse_drag_event
            window.mouse_press_event_func = gui_impl.mouse_press_event
            window.mouse_release_event_func = gui_impl.mouse_release_event
            window.mouse_scroll_event_func = gui_impl.mouse_scroll_event
            window.unicode_char_entered_func = gui_impl.unicode_char_entered
            window.resize_func = gui_impl.resize

            def on_key(key, action, modifiers, _w=window, _s=state):
                if action == _w.keys.ACTION_PRESS:
                    if key == _w.keys.H:            # masquer / afficher le menu
                        _s["gui_visible"] = not _s["gui_visible"]
                    elif key == _w.keys.G:          # (dés)activer le plein écran
                        _set_fullscreen(_w, not _w.fullscreen)
                gui_impl.key_event(key, action, modifiers)
            window.key_event_func = on_key
            print("[gui] panneau imgui actif — h: masquer menu, g: plein écran")
        else:
            # sans GUI : garder au moins le raccourci plein écran (g)
            def on_key(key, action, modifiers, _w=window):
                if action == _w.keys.ACTION_PRESS and key == _w.keys.G:
                    _set_fullscreen(_w, not _w.fullscreen)
            window.key_event_func = on_key
        print(f"[preview] fenêtre {Wp}x{Hp} ouverte — g: plein écran")
    else:
        eng = LuxCoreEngine(W, H, fonts_dir=fonts_dir, video_paths=video_paths)
    print(f"[GL] {eng.ctx.info['GL_RENDERER']}")

    # -- sortie NDI (readback PBO + worker, cf. spike) --
    from cyndilib.sender import Sender
    from cyndilib.video_frame import VideoSendFrame
    from cyndilib.wrapper.ndi_structs import FourCC
    sender = Sender(args.name)
    vf = VideoSendFrame()
    vf.set_resolution(W, H)
    vf.set_frame_rate(Fraction(FPS, 1))
    vf.set_fourcc(FourCC.RGBA)
    sender.set_video_frame(vf)
    sender.open()
    print(f"[NDI] source '{args.name}' — {W}x{H} @ {FPS}")

    NB = 3
    nbytes = W * H * 4
    pbos = [eng.ctx.buffer(reserve=nbytes) for _ in range(NB)]
    bufs = [bytearray(nbytes) for _ in range(NB)]
    views = [np.frombuffer(b, dtype=np.uint8) for b in bufs]

    send_q: "queue.Queue" = queue.Queue(maxsize=NB - 1)

    def ndi_worker():
        while True:
            v = send_q.get()
            if v is None:
                break
            sender.write_video_async(v)
            send_q.task_done()
    threading.Thread(target=ndi_worker, daemon=True).start()

    artnet = ArtNetReceiver()
    artnet.start()

    frame_dt = 1.0 / FPS
    t0 = time.perf_counter()
    next_tick = t0
    n = 0
    print("[loop] démarre — Ctrl+C pour arrêter\n")
    try:
        while True:
            now = time.perf_counter()
            if args.duration and now - t0 >= args.duration:
                break
            if window is not None and window.is_closing:
                print("\n[preview] fenêtre fermée.")
                break

            # contrôles GUI appliqués à la frame
            eng.enable_effects = state["effects"]
            if state["restart_artnet"]:
                state["restart_artnet"] = False
                artnet.stop()
                artnet = ArtNetReceiver()
                artnet.start()
                print("[artnet] redémarré")

            dmx = artnet.snapshot()
            base, _ = eng.render_dmx(dmx, state["spots"])

            # aperçu écran : blit du FBO vers le framebuffer de la fenêtre
            if blit is not None:
                ctx, blit_prog, blit_vao = blit
                window.use()
                eng.tex.use(0)
                blit_prog["t"] = 0
                import moderngl as _mgl
                blit_vao.render(_mgl.TRIANGLE_STRIP)

                if gui_impl is not None and state["gui_visible"]:
                    from imgui_bundle import imgui
                    from luxcore.gui import draw_gui
                    imgui.new_frame()
                    status = {"fps": n / max(1e-6, time.perf_counter() - t0),
                              "packets": artnet.packets,
                              "universe": artnet.last_universe_seen,
                              "ndi": args.name,
                              "res": f"{W}x{H} @ {FPS}",
                              "blend": base.blend_global.name}
                    draw_gui(state, status)
                    imgui.render()
                    gui_impl.update_textures()
                    gui_impl.render(imgui.get_draw_data())

                window.swap_buffers()

            cur, prev = n % NB, (n - 1) % NB
            eng.fbo.read_into(pbos[cur], components=4, dtype="f1")
            if n > 0:
                pbos[prev].read_into(bufs[prev])
                send_q.put(views[prev])
                if args.snapshot_dir and now - last_snap >= args.snapshot_interval:
                    from PIL import Image
                    path = os.path.join(args.snapshot_dir, f"snap_{snap_idx:03d}.png")
                    Image.frombytes("RGBA", (W, H), bytes(bufs[prev])).save(path)
                    snap_idx += 1
                    last_snap = now
            n += 1

            next_tick += frame_dt
            sleep = next_tick - time.perf_counter()
            if sleep > 0:
                time.sleep(sleep)
            else:
                next_tick = time.perf_counter()

            if n % FPS == 0:
                el = time.perf_counter() - t0
                print(f"  t={el:5.1f}s  fps={n/el:5.1f}  "
                      f"artnet_pkts={artnet.packets}  "
                      f"univ_vu={artnet.last_universe_seen}", flush=True)
    except KeyboardInterrupt:
        print("\n[loop] interrompu.")

    el = time.perf_counter() - t0
    print(f"\n{n} frames en {el:.1f}s -> {n/el:.1f} fps (cible {FPS})")
    _sleep_inhibit(False)                 # libère la veille + restaure DPMS
    artnet.stop()
    send_q.put(None)
    time.sleep(0.1)
    sender.close()


if __name__ == "__main__":
    main()
