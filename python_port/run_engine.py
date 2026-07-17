#!/usr/bin/env python3
"""Moteur LuxCore — boucle live : ArtNet -> décodage -> rendu -> NDI (étape B).

Assemble les trois modules déjà écrits (artnet, dmx, engine) avec une sortie NDI
optimisée (readback PBO + worker d'envoi). Piloter en envoyant de l'ArtNet
(p.ex. demo_scripts/defile_formes.py) et regarder la source NDI "LuxCore" dans
OBS / vMix / Resolume.

    python_port/.venv/bin/python python_port/run_engine.py --spots 60 --duration 0
"""
import argparse
import json
import os
import queue
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from fractions import Fraction

import numpy as np

from luxcore import appconfig, netconfig
from luxcore.artnet import ArtNetReceiver
from luxcore.engine import LuxCoreEngine

# Options adossées à la config (menu/JSON) : retirées de argv lors d'une relance
# « Redémarrer moteur » pour que le fichier de config fasse foi sur la nouvelle valeur.
_CONFIG_FLAGS = {"--width", "--height", "--fps", "--spots", "--name",
                 "--artnet-nic", "--ndi-nic", "--start-universe", "--start-addr"}


def _apply_ndi_interface(ip: str) -> None:
    """Best-effort : restreint NDI à l'IP `ip` via un ndi-config.v1.json + NDI_CONFIG_DIR.
    À appeler AVANT la création du sender. Sans effet si `ip` est vide ; non garanti
    selon la version du SDK NDI (dans ce cas NDI émet sur toutes les interfaces)."""
    if not ip:
        return
    d = tempfile.mkdtemp(prefix="luxcore-ndi-")
    with open(os.path.join(d, "ndi-config.v1.json"), "w", encoding="utf-8") as f:
        json.dump({"ndi": {"networks": {"ips": ip}}}, f)
    os.environ["NDI_CONFIG_DIR"] = d
    print(f"[NDI] interface demandée {ip} (best-effort via {d})")


def _argv_for_restart(argv: list[str]) -> list[str]:
    """argv sans les options adossées à la config (pour qu'une relance relise le JSON)."""
    out: list[str] = []
    skip = False
    for a in argv:
        if skip:
            skip = False
            continue
        if a in _CONFIG_FLAGS:
            skip = True
            continue
        if any(a.startswith(f + "=") for f in _CONFIG_FLAGS):
            continue
        out.append(a)
    return out


def main():
    ap = argparse.ArgumentParser()
    # Réglages adossés au fichier de config (menu) : default=None -> valeur du JSON
    # si le flag n'est pas passé (le flag CLI reste prioritaire quand fourni).
    ap.add_argument("--config", default=None, help="fichier de config JSON (défaut : "
                    "~/.config/luxcore/config.json)")
    ap.add_argument("--width", type=int, default=None)
    ap.add_argument("--height", type=int, default=None)
    ap.add_argument("--fps", type=int, default=None)
    ap.add_argument("--spots", type=int, default=None,
                    help="nombre de fixtures décodées (une fixture en mode 14 = vidéo)")
    ap.add_argument("--name", default=None, help="nom de la source NDI")
    ap.add_argument("--artnet-nic", default=None,
                    help="carte réseau (nom ou IP) pour la réception ArtNet")
    ap.add_argument("--ndi-nic", default=None,
                    help="carte réseau (nom ou IP) pour l'émission NDI (best-effort)")
    ap.add_argument("--start-universe", type=int, default=None,
                    help="1er univers ArtNet du patch (0-based)")
    ap.add_argument("--start-addr", type=int, default=None,
                    help="1re adresse DMX du patch dans cet univers (1-based)")
    ap.add_argument("--duration", type=float, default=20.0, help="0 = jusqu'à Ctrl+C")
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
    ap.add_argument("--max-videos", type=int, default=None,
                    help="charge au plus N vidéos du dossier (échantillonnées "
                         "uniformément pour la variété) — garde-fou VRAM (~133 Mo/vidéo)")
    args = ap.parse_args()

    # -- config (JSON persistée) : le flag CLI, s'il est fourni, l'emporte --------
    cfg = appconfig.load(args.config)

    def _pick(cli, key):
        return cli if cli is not None else cfg[key]

    W = _pick(args.width, "width")
    H = _pick(args.height, "height")
    FPS = _pick(args.fps, "fps")
    spots0 = _pick(args.spots, "spots")
    ndi_name = _pick(args.name, "name")
    artnet_ip = netconfig.ip_for(args.artnet_nic) if args.artnet_nic else cfg["artnet_ip"]
    ndi_ip = netconfig.ip_for(args.ndi_nic) if args.ndi_nic else cfg["ndi_ip"]
    start_universe = _pick(args.start_universe, "start_universe")
    start_addr = _pick(args.start_addr, "start_addr")
    base_offset = start_addr - 1

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
    # garde-fou VRAM : échantillonne uniformément si trop de vidéos (~133 Mo/vidéo)
    if args.max_videos and len(video_paths) > args.max_videos:
        n, m = len(video_paths), args.max_videos
        keep = sorted({round(i * (n - 1) / (m - 1)) for i in range(m)}) if m > 1 else [0]
        print(f"[video] {n} vidéos trouvées -> {len(keep)} chargées (--max-videos {m})")
        video_paths = [video_paths[i] for i in keep]
    if video_paths:
        print(f"[video] {len(video_paths)} vidéo(s) : "
              + ", ".join(os.path.basename(p) for p in video_paths))

    snap_idx = 0
    last_snap = 0.0
    if args.snapshot_dir:
        os.makedirs(args.snapshot_dir, exist_ok=True)

    # état partagé avec le GUI (réglages runtime + config éditable au menu)
    state = {"spots": spots0, "effects": True,
             "restart_artnet": False, "gui_visible": True,
             "artnet_ip": artnet_ip, "ndi_ip": ndi_ip,
             "width": W, "height": H,
             "start_universe": start_universe, "start_addr": start_addr,
             "interfaces": netconfig.list_interfaces(),
             "apply_artnet": False, "restart_engine": False, "save_config": False}

    def _snapshot_config():
        """Config courante (état menu) pour sauvegarde / relance."""
        return {"width": state["width"], "height": state["height"], "fps": FPS,
                "spots": state["spots"], "name": ndi_name,
                "artnet_ip": state["artnet_ip"], "ndi_ip": state["ndi_ip"],
                "start_universe": state["start_universe"],
                "start_addr": state["start_addr"]}

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
        window = window_cls(size=(Wp, Hp), title=f"LuxCore — aperçu ({ndi_name})",
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

    # -- sortie NDI (readback PBO + worker d'envoi) --
    _apply_ndi_interface(ndi_ip)         # best-effort : restreint NDI à l'IP choisie
    from cyndilib.sender import Sender
    from cyndilib.video_frame import VideoSendFrame
    from cyndilib.wrapper.ndi_structs import FourCC
    sender = Sender(ndi_name)
    vf = VideoSendFrame()
    vf.set_resolution(W, H)
    vf.set_frame_rate(Fraction(FPS, 1))
    vf.set_fourcc(FourCC.UYVY)          # 4:2:2 — readback W*H*2 (moitié du RGBA)
    sender.set_video_frame(vf)
    sender.open()
    print(f"[NDI] source '{ndi_name}' — {W}x{H} @ {FPS} (UYVY)")

    NB = 3
    nbytes = W * H * 2                  # UYVY : 2 octets/pixel
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

    artnet = ArtNetReceiver(bind_addr=artnet_ip, start_universe=start_universe)
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

            # ArtNet appliqué À CHAUD : carte réseau + univers + adresse de départ
            if state["restart_artnet"] or state["apply_artnet"]:
                state["restart_artnet"] = False
                state["apply_artnet"] = False
                artnet.stop()
                artnet = ArtNetReceiver(bind_addr=state["artnet_ip"],
                                        start_universe=state["start_universe"])
                artnet.start()
                base_offset = state["start_addr"] - 1
                print(f"[artnet] appliqué : {state['artnet_ip']} · univers "
                      f"{state['start_universe']} · adresse {state['start_addr']}")

            # Sauvegarde de la config (menu)
            if state["save_config"]:
                state["save_config"] = False
                appconfig.save(_snapshot_config(), args.config)
                print("[config] sauvegardée")

            # Redémarrage du moteur (résolution / carte NDI) : relance propre du process
            if state["restart_engine"]:
                appconfig.save(_snapshot_config(), args.config)
                print("[engine] redémarrage (résolution / carte NDI)…")
                artnet.stop()
                send_q.put(None)
                time.sleep(0.1)
                sender.close()
                _sleep_inhibit(False)
                os.execv(sys.executable, [sys.executable] + _argv_for_restart(sys.argv))

            dmx = artnet.snapshot()
            base, _ = eng.render_dmx(dmx, state["spots"], base_offset=base_offset)

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
                              "ndi": ndi_name,
                              "res": f"{W}x{H} @ {FPS}",
                              "blend": base.blend_global.name}
                    draw_gui(state, status)
                    imgui.render()
                    gui_impl.update_textures()
                    gui_impl.render(imgui.get_draw_data())

                window.swap_buffers()

            # snapshot PNG (debug) : lit le FBO RGBA avant le packing UYVY
            if args.snapshot_dir and now - last_snap >= args.snapshot_interval:
                from PIL import Image
                rgba = eng.fbo.read(components=4, dtype="f1")
                path = os.path.join(args.snapshot_dir, f"snap_{snap_idx:03d}.png")
                Image.frombytes("RGBA", (W, H), bytes(rgba)).save(path)
                snap_idx += 1
                last_snap = now

            # NDI : packe en UYVY (GPU) puis readback double-bufferisé (W*H*2)
            eng.pack_uyvy()
            cur, prev = n % NB, (n - 1) % NB
            eng._uyvy_fbo.read_into(pbos[cur], components=4, dtype="f1")
            if n > 0:
                pbos[prev].read_into(bufs[prev])
                send_q.put(views[prev])
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
