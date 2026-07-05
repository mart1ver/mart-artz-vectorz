#!/usr/bin/env python3
"""
Spike de dé-risquage — LuxCore DMX Engine, portage Python (moteur moderngl).

Objectif : PROUVER que la boucle temps-reel tient la cible (defaut 1080p60) avec,
dans le meme process et sans JVM :
    1. contexte OpenGL possede (moderngl, EGL standalone -> pas besoin de fenetre)
    2. source video decodee par PyAV -> texture GL   (ou mire procedurale GPU)
    3. un shader de post-effet (sobel mixe par `amount`) applique en FBO
    4. lecture du FBO -> numpy (read_into, buffer pre-alloue)
    5. sortie NDI via cyndilib (visible dans OBS / vMix / Resolume)
    6. reception ArtNet UDP:6454 -> le canal 1 module l'intensite de l'effet

Il ne porte AUCUNE des 15 formes ni le GUI : il valide uniquement l'ossature
d'E/S pixels, la ou Processing/py5 echouent. Si le FPS et les temps de
readback/send tiennent ici, l'architecture moderngl est validee.

Usage :
    .venv/bin/python spike_ndi.py                 # mire procedurale, 1080p60, 20 s
    .venv/bin/python spike_ndi.py --video clip.mp4 --width 1920 --height 1080 --fps 60
    .venv/bin/python spike_ndi.py --duration 0    # tourne jusqu'a Ctrl+C

Puis ouvrir un recepteur NDI (OBS + plugin NDI, vMix, Resolume, NDI Studio Monitor)
et selectionner la source "LuxCore-Spike".
"""
from __future__ import annotations

import argparse
import socket
import struct
import threading
import time
from fractions import Fraction

import numpy as np
import moderngl


# ----------------------------------------------------------------------------
# Shaders GLSL
# ----------------------------------------------------------------------------

# Quad plein-ecran. On inverse Y de gl_Position pour que le FBO soit lu
# top-down (NDI veut la 1re ligne = haut de l'image ; OpenGL lit bottom-up).
VERT = """
#version 330
in vec2 in_pos;
out vec2 uv;
uniform int flip;               // 1 = inverse Y (sortie top-down pour NDI)
void main() {
    uv = in_pos * 0.5 + 0.5;
    float y = (flip == 1) ? -in_pos.y : in_pos.y;
    gl_Position = vec4(in_pos.x, y, 0.0, 1.0);
}
"""

# Passe 1 (mode mire) : barres animees + degrade, pour exercer le pipeline
# sans fichier video.
FRAG_PATTERN = """
#version 330
in vec2 uv;
out vec4 frag;
uniform float t;
void main() {
    float bars = step(0.5, fract(uv.x * 12.0 + t * 0.5));
    vec3 grad = vec3(uv.x, uv.y, 0.5 + 0.5 * sin(t));
    vec3 col = mix(grad, vec3(1.0) - grad, bars);
    // quelques diagonales nettes pour donner du grain au sobel
    col *= 0.6 + 0.4 * step(0.5, fract((uv.x + uv.y) * 40.0));
    frag = vec4(col, 1.0);
}
"""

# Passe 2 : sobel sur la source, mixe avec l'original selon `amount`
# (module par ArtNet). C'est un des 14 effets bildspur, reecrit en GLSL direct.
FRAG_SOBEL = """
#version 330
in vec2 uv;
out vec4 frag;
uniform sampler2D src;
uniform vec2 texel;             // 1.0 / resolution
uniform float amount;           // 0..1 : dose de l'effet (canal DMX 1)
float lum(vec3 c) { return dot(c, vec3(0.299, 0.587, 0.114)); }
void main() {
    vec3 orig = texture(src, uv).rgb;
    float gx = 0.0, gy = 0.0;
    // noyau 3x3 Sobel
    float kx[9] = float[](-1., 0., 1., -2., 0., 2., -1., 0., 1.);
    float ky[9] = float[](-1., -2., -1., 0., 0., 0., 1., 2., 1.);
    int i = 0;
    for (int y = -1; y <= 1; y++) {
        for (int x = -1; x <= 1; x++) {
            float l = lum(texture(src, uv + vec2(x, y) * texel).rgb);
            gx += l * kx[i]; gy += l * ky[i]; i++;
        }
    }
    float edge = clamp(length(vec2(gx, gy)), 0.0, 1.0);
    vec3 col = mix(orig, vec3(edge), amount);
    frag = vec4(col, 1.0);
}
"""


# ----------------------------------------------------------------------------
# Reception ArtNet (thread) — canal 1 de l'univers 0 -> amount
# ----------------------------------------------------------------------------
class ArtNetReceiver(threading.Thread):
    """Ecoute UDP:6454, parse les paquets ArtDMX, expose le dernier dmx_data[]."""

    HEADER = b"Art-Net\x00"
    OP_DMX = 0x5000

    def __init__(self, port: int = 6454):
        super().__init__(daemon=True)
        self.port = port
        self.dmx = bytearray(512)
        self.lock = threading.Lock()
        self._stop = threading.Event()
        self.packets = 0

    def run(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("0.0.0.0", self.port))
        except OSError as e:
            print(f"[ArtNet] bind :{self.port} impossible ({e}) — effet a 0.")
            return
        sock.settimeout(0.25)
        print(f"[ArtNet] ecoute UDP:{self.port}")
        while not self._stop.is_set():
            try:
                data, _ = sock.recvfrom(1024)
            except socket.timeout:
                continue
            except OSError:
                break
            if len(data) < 18 or data[:8] != self.HEADER:
                continue
            opcode = struct.unpack_from("<H", data, 8)[0]
            if opcode != self.OP_DMX:
                continue
            length = struct.unpack_from(">H", data, 16)[0]
            payload = data[18:18 + length]
            with self.lock:
                self.dmx[:len(payload)] = payload
            self.packets += 1
        sock.close()

    def amount(self) -> float:
        with self.lock:
            return self.dmx[0] / 255.0   # canal 1 (index 0) -> 0..1

    def stop(self):
        self._stop.set()


# ----------------------------------------------------------------------------
# Decodage video (thread) — PyAV -> derniere frame RGBA en numpy (h, w, 4)
# ----------------------------------------------------------------------------
class VideoDecoder(threading.Thread):
    def __init__(self, path: str, width: int, height: int):
        super().__init__(daemon=True)
        self.path = path
        self.width, self.height = width, height
        self.frame = None
        self.lock = threading.Lock()
        self._stop = threading.Event()
        self.ok = False

    def run(self):
        import av
        try:
            container = av.open(self.path)
        except Exception as e:
            print(f"[Video] ouverture '{self.path}' impossible : {e}")
            return
        self.ok = True
        stream = container.streams.video[0]
        print(f"[Video] {self.path} — {stream.width}x{stream.height} @ ~{float(stream.average_rate or 0):.1f}fps (boucle)")
        while not self._stop.is_set():
            for frame in container.decode(stream):
                if self._stop.is_set():
                    break
                rgba = frame.reformat(width=self.width, height=self.height, format="rgba")
                arr = np.frombuffer(rgba.planes[0], dtype=np.uint8)
                arr = arr.reshape(self.height, rgba.planes[0].line_size // 4, 4)[:, :self.width, :]
                with self.lock:
                    self.frame = np.ascontiguousarray(arr)
            container.seek(0)   # boucle infinie

    def latest(self):
        with self.lock:
            return self.frame

    def stop(self):
        self._stop.set()


# ----------------------------------------------------------------------------
# Boucle principale
# ----------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Spike NDI+video+ArtNet moderngl")
    ap.add_argument("--video", help="fichier video source (sinon mire procedurale)")
    ap.add_argument("--width", type=int, default=1920)
    ap.add_argument("--height", type=int, default=1080)
    ap.add_argument("--fps", type=int, default=60)
    ap.add_argument("--duration", type=float, default=20.0, help="secondes (0 = jusqu'a Ctrl+C)")
    ap.add_argument("--name", default="LuxCore-Spike", help="nom de la source NDI")
    ap.add_argument("--no-flip", action="store_true", help="ne pas inverser Y")
    args = ap.parse_args()

    W, H, FPS = args.width, args.height, args.fps
    flip = 0 if args.no_flip else 1

    # -- contexte GL headless (pas de fenetre : marche en SSH / sans compositeur) --
    ctx = moderngl.create_context(standalone=True, backend="egl")
    print(f"[GL] {ctx.info['GL_RENDERER']} — {ctx.info['GL_VERSION']}")

    quad = ctx.buffer(np.array([-1, -1, 1, -1, -1, 1, 1, 1], dtype="f4").tobytes())

    prog_pattern = ctx.program(vertex_shader=VERT, fragment_shader=FRAG_PATTERN)
    prog_sobel = ctx.program(vertex_shader=VERT, fragment_shader=FRAG_SOBEL)
    prog_pattern["flip"] = 0          # source: pas de flip (le flip se fait a la sortie)
    prog_sobel["flip"] = flip
    prog_sobel["texel"] = (1.0 / W, 1.0 / H)

    vao_pattern = ctx.vertex_array(prog_pattern, [(quad, "2f4", "in_pos")])
    vao_sobel = ctx.vertex_array(prog_sobel, [(quad, "2f4", "in_pos")])

    src_tex = ctx.texture((W, H), 4)
    src_tex.repeat_x = src_tex.repeat_y = False
    src_fbo = ctx.framebuffer(color_attachments=[src_tex])   # cible passe mire

    out_tex = ctx.texture((W, H), 4)
    out_fbo = ctx.framebuffer(color_attachments=[out_tex])   # cible sortie NDI

    # -- readback PBO double-buffer : on lit le FBO dans un Buffer GPU (async,
    #    ne stalle pas), et on rapatrie en CPU le PBO de la frame PRECEDENTE.
    #    Cote CPU, double bufferisation aussi car l'envoi NDI est asynchrone
    #    (NDI lit encore le buffer apres le retour de l'appel).
    #    Triple-buffer : le worker NDI peut encore lire un slot pendant que le
    #    thread GL en remplit un autre.
    NB = 3
    nbytes = W * H * 4
    pbos = [ctx.buffer(reserve=nbytes) for _ in range(NB)]
    read_bufs = [bytearray(nbytes) for _ in range(NB)]
    ndi_views = [np.frombuffer(b, dtype=np.uint8) for b in read_bufs]

    # -- sortie NDI --
    from cyndilib.sender import Sender
    from cyndilib.video_frame import VideoSendFrame
    from cyndilib.wrapper.ndi_structs import FourCC
    sender = Sender(args.name)
    vframe = VideoSendFrame()
    vframe.set_resolution(W, H)
    vframe.set_frame_rate(Fraction(FPS, 1))
    vframe.set_fourcc(FourCC.RGBA)
    sender.set_video_frame(vframe)
    sender.open()
    print(f"[NDI] source '{args.name}' — {W}x{H} @ {FPS} RGBA")

    # worker d'envoi NDI : la copie interne cyndilib (~8 Mo) quitte le thread GL
    import queue
    send_q: "queue.Queue" = queue.Queue(maxsize=NB - 1)
    send_time = {"total": 0.0}

    def ndi_worker():
        while True:
            view = send_q.get()
            if view is None:
                break
            t = time.perf_counter()
            sender.write_video_async(view)
            send_time["total"] += time.perf_counter() - t
            send_q.task_done()

    threading.Thread(target=ndi_worker, daemon=True).start()

    # -- threads I/O --
    artnet = ArtNetReceiver()
    artnet.start()

    decoder = None
    if args.video:
        decoder = VideoDecoder(args.video, W, H)
        decoder.start()
        time.sleep(0.3)   # laisse une 1re frame arriver

    # -- boucle temps-reel --
    frame_dt = 1.0 / FPS
    stats = {"n": 0, "read": 0.0, "send": 0.0, "upload": 0.0}
    t0 = time.perf_counter()
    next_tick = t0
    print("[loop] demarre — Ctrl+C pour arreter\n")
    try:
        while True:
            now = time.perf_counter()
            if args.duration and now - t0 >= args.duration:
                break

            amount = artnet.amount()
            prog_sobel["amount"] = amount

            # --- source -> src_tex ---
            if decoder is not None:
                fr = decoder.latest()
                if fr is not None:
                    t = time.perf_counter()
                    src_tex.write(fr.tobytes())
                    stats["upload"] += time.perf_counter() - t
            else:
                src_fbo.use()
                prog_pattern["t"] = now - t0
                vao_pattern.render(moderngl.TRIANGLE_STRIP)

            # --- effet -> out_fbo ---
            out_fbo.use()
            src_tex.use(0)
            prog_sobel["src"] = 0
            vao_sobel.render(moderngl.TRIANGLE_STRIP)

            cur = stats["n"] % NB
            prev = (stats["n"] - 1) % NB

            # --- readback GPU->PBO (async) puis PBO precedent->CPU ---
            t = time.perf_counter()
            out_fbo.read_into(pbos[cur], components=4, dtype="f1")   # non bloquant
            if stats["n"] > 0:
                pbos[prev].read_into(read_bufs[prev])               # frame n-1, deja prete
            stats["read"] += time.perf_counter() - t

            # --- envoi NDI (frame n-1) delegue au worker ---
            if stats["n"] > 0:
                send_q.put(ndi_views[prev])

            stats["n"] += 1

            # cadence a FPS
            next_tick += frame_dt
            sleep = next_tick - time.perf_counter()
            if sleep > 0:
                time.sleep(sleep)
            else:
                next_tick = time.perf_counter()   # on a pris du retard : on resynchronise

            if stats["n"] % FPS == 0:
                el = time.perf_counter() - t0
                fps = stats["n"] / el
                print(f"  t={el:5.1f}s  fps={fps:5.1f}  "
                      f"[GL-thread] read={1000*stats['read']/stats['n']:.2f}ms  "
                      f"upload={1000*stats['upload']/max(1,stats['n']):.2f}ms  "
                      f"| [worker] send={1000*send_time['total']/stats['n']:.2f}ms  "
                      f"artnet_pkts={artnet.packets}  effet={amount:.2f}", flush=True)
    except KeyboardInterrupt:
        print("\n[loop] interrompu.")

    # -- bilan --
    el = time.perf_counter() - t0
    n = max(1, stats["n"])
    print("\n===== BILAN =====")
    print(f"frames            : {stats['n']} en {el:.1f}s  ->  {stats['n']/el:.1f} fps (cible {FPS})")
    print(f"[GL-thread] read  : {1000*stats['read']/n:.2f} ms/frame")
    if decoder:
        print(f"[GL-thread] upload: {1000*stats['upload']/n:.2f} ms/frame")
    print(f"[worker] envoi NDI: {1000*send_time['total']/n:.2f} ms/frame (hors chemin critique)")
    print(f"paquets ArtNet    : {artnet.packets}")
    budget = 1000.0 / FPS
    gl_used = 1000 * (stats['read'] + stats['upload']) / n
    print(f"budget/frame      : {budget:.1f} ms  |  chemin critique GL : {gl_used:.2f} ms "
          f"({100*gl_used/budget:.0f}%)")
    verdict = "TIENT LA CIBLE" if stats['n']/el >= FPS * 0.95 else "SOUS LA CIBLE"
    print(f"verdict        : {verdict}")

    artnet.stop()
    if decoder:
        decoder.stop()
    send_q.put(None)          # arrete le worker NDI
    time.sleep(0.1)
    sender.close()


if __name__ == "__main__":
    main()
