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
    ap.add_argument("--spots", type=int, default=15)
    ap.add_argument("--duration", type=float, default=20.0, help="0 = jusqu'à Ctrl+C")
    ap.add_argument("--name", default="LuxCore")
    ap.add_argument("--snapshot-dir", help="sauve un PNG toutes les --snapshot-interval s")
    ap.add_argument("--snapshot-interval", type=float, default=2.0)
    args = ap.parse_args()

    snap_idx = 0
    last_snap = 0.0
    if args.snapshot_dir:
        os.makedirs(args.snapshot_dir, exist_ok=True)

    W, H, FPS = args.width, args.height, args.fps
    eng = LuxCoreEngine(W, H)
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

            dmx = artnet.snapshot()
            eng.render_dmx(dmx, args.spots, n_fonts=0)

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
    artnet.stop()
    send_q.put(None)
    time.sleep(0.1)
    sender.close()


if __name__ == "__main__":
    main()
