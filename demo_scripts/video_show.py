#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LUXCORE DMX ENGINE — VIDEO SHOW (démo 100 % des fonctions vidéo)
================================================================
Montre TOUTES les capacités vidéo du moteur, une scène par capacité :

  1. PLEIN ÉCRAN   — cycle des vidéos du dossier en fondu enchaîné (sélecteur +22,
                     échelle plein écran, alpha)
  2. FOND+PANNEAUX — fixture de FOND plein écran + panneaux flottants par-dessus
                     (compositing, alpha)
  3. MUR VIDÉO     — mosaïque de panneaux, vidéos réparties (multi-sources)
  4. DÉSYNC        — beaucoup de panneaux de la MÊME vidéo -> écho temporel (frames
                     retardées, anneau de désync)
  5. MOUVEMENT     — panneaux qui orbitent, tournent et respirent (pan/tilt/rotation/échelle)
  6. BLEND         — même vidéo superposée en ADD / SCREEN / DIFFERENCE (blend par panneau)
  7. POSTFX        — une vidéo plein écran, tous les post-effets en douceur
                     (bloom, feedback, kaléido, pixelate, rgb split, chromatic)
  8. KALÉIDO MUR   — mur de vidéos + kaléidoscope + bloom (finale hypnotique)

Confort visuel : aucune scène ne clignote (fondus doux, mouvements continus).
La sélection de vidéo suppose N_VID sources dans data/videos/ (le moteur mappe
le canal +22 [0-255] vers l'index disponible). Ajuster N_VID au dossier.

Lancer :  python3 video_show.py [ip] [n_videos]
          (le moteur doit tourner : run_engine.py --preview ...)

Author: Martin Vert
"""

import math
import sys
import time

import luxcore_artnet as lxa

# ── Réglages ─────────────────────────────────────────────────────────────────
IP = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
N_VID = int(sys.argv[2]) if len(sys.argv) > 2 else 3   # nb de vidéos dans data/videos/

W, H = 1920, 1080
HALF_W, HALF_H = W / 2.0, H / 2.0
N_UNIVERSES = 3
DMX_LEN = 512 * N_UNIVERSES
MAX_PANELS = 24                       # slots 0..23 pour les panneaux vidéo
BG_SLOT = 60                          # fixture de FOND (aligné sur C.BG_FIXTURE_SLOT)
VIDEO_SIZE_SCALE = 2.5                # ré-échelonnage moteur des fixtures vidéo

VIDEO = 14                            # mode forme = VIDEO

# Blend modes — valeurs DMX exactes
BLEND, ADD, SUBTRACT, DARKEST, LIGHTEST = 0, 29, 57, 85, 114
DIFFERENCE, EXCLUSION, MULTIPLY, SCREEN, REPLACE = 142, 170, 199, 227, 255


def clamp8(v):
    return max(0, min(255, int(v)))


def to_pan(dx):
    """Offset px horizontal depuis le centre -> position pan 16-bit."""
    return int((dx + 255 + HALF_W) / (510 + 2 * HALF_W) * 65535)


def to_tilt(dy):
    return int((dy + 255 + HALF_H) / (510 + 2 * HALF_H) * 65535)


def sz_px(px):
    """Largeur/hauteur vidéo en px -> valeur 16-bit (compte tenu de VIDEO_SIZE_SCALE)."""
    return max(0, min(65535, int(px / (1000 * VIDEO_SIZE_SCALE) * 65535)))


def vsel(v):
    """Index de vidéo 0..N_VID-1 -> canal +22 (milieu de plage, robuste)."""
    return int((v % max(1, N_VID) + 0.5) / max(1, N_VID) * 256)


def lay_grid(cols, rows, span_x, span_y):
    """Grille centrée : liste d'offsets (dx, dy) en px depuis le centre."""
    pts = []
    for r in range(rows):
        for c in range(cols):
            dx = (c - (cols - 1) / 2.0) * (span_x / max(1, cols - 1)) if cols > 1 else 0.0
            dy = (r - (rows - 1) / 2.0) * (span_y / max(1, rows - 1)) if rows > 1 else 0.0
            pts.append((dx, dy))
    return pts


class VideoShow:
    def __init__(self, ip):
        self.ip = ip
        self.sock = lxa.make_socket()
        self.dmx = [0] * DMX_LEN

    # ── Émission / cadre ─────────────────────────────────────────────────────
    def send(self):
        lxa.send_multi(self.sock, self.dmx, self.ip)

    def frame_reset(self):
        self.dmx = [0] * DMX_LEN

    def bg(self, r, g, b):
        self.dmx[0], self.dmx[1], self.dmx[2] = clamp8(r), clamp8(g), clamp8(b)

    def fx(self, blend_global=0, blur=0, sigma=0, pixelate=0, sobel=0, rgbsplit=0,
           sat_a=0, sat_b=0, chroma=0, feedback=0, bloom_thr=60, bloom=0, kaleido=0):
        d = self.dmx
        d[19] = clamp8(blend_global)
        d[20] = clamp8(blur); d[21] = clamp8(sigma)
        d[22] = clamp8(pixelate); d[23] = clamp8(sobel)
        d[24] = clamp8(rgbsplit); d[25] = clamp8(sat_a); d[26] = clamp8(sat_b)
        d[27] = clamp8(chroma)
        d[28] = clamp8(feedback); d[29] = clamp8(bloom_thr)
        d[30] = clamp8(bloom); d[31] = clamp8(kaleido)

    def blade(self, idx, val16):
        lxa.set16(self.dmx, 3 + idx * 2, val16)

    # ── Écriture d'un panneau vidéo ──────────────────────────────────────────
    def vspot(self, i, dx, dy, w, rot=0.0, alpha=255, v=0, blend=0, h=None):
        """Panneau vidéo `i` (mode 14), largeur w px (hauteur h ou 16:9), centre
        (dx,dy) px, rotation deg, opacité alpha, source v (index), blend."""
        if i >= MAX_PANELS or alpha <= 0:
            return
        if h is None:
            h = w * 9.0 / 16.0
        b = 32 + i * 23
        d = self.dmx
        d[b] = d[b + 1] = d[b + 2] = 255                  # fill blanc (ignoré en vidéo)
        d[b + 3] = clamp8(alpha)
        lxa.set16(d, b + 9, sz_px(w))
        lxa.set16(d, b + 11, sz_px(h))
        lxa.set16(d, b + 13, int(rot % 360 * 65535 / 360))
        lxa.set16(d, b + 15, to_pan(dx))
        lxa.set16(d, b + 17, to_tilt(dy))
        d[b + 19] = VIDEO
        d[b + 20] = 255                                   # enable
        d[b + 21] = clamp8(blend)
        d[b + 22] = clamp8(vsel(v))                       # sélecteur de vidéo

    def bgvid(self, v=0, alpha=255, blend=0):
        """Fixture de FOND : vidéo plein écran DERRIÈRE tous les panneaux."""
        b = 32 + BG_SLOT * 23
        d = self.dmx
        d[b] = d[b + 1] = d[b + 2] = 255
        d[b + 3] = clamp8(alpha)
        d[b + 19] = VIDEO
        d[b + 20] = 255
        d[b + 21] = clamp8(blend)
        d[b + 22] = clamp8(vsel(v))

    # ── Enveloppe douce (respiration, jamais de noir) ────────────────────────
    @staticmethod
    def swell(t, period, floor=0.4):
        ph = (t / period) % 1.0
        return floor + (1.0 - floor) * (0.5 + 0.5 * math.cos(2.0 * math.pi * ph))

    @staticmethod
    def bump(t, period):
        """Cloche douce 0 -> 1 -> 0 sur la période (effet qui apparaît et disparaît)."""
        return 0.5 - 0.5 * math.cos(2.0 * math.pi * ((t / period) % 1.0))

    @staticmethod
    def scene_gain(t, dur, fade=2.0):
        """Fondu entrant/sortant (cosinus) pour des transitions douces entre scènes."""
        if t < fade:
            x = t / fade
        elif t > dur - fade:
            x = (dur - t) / fade
        else:
            return 1.0
        x = max(0.0, min(1.0, x))
        return 0.5 - 0.5 * math.cos(math.pi * x)

    # ══ SCÈNES ═══════════════════════════════════════════════════════════════
    def sc_fullscreen(self, t):
        """Cycle des N_VID vidéos en plein écran, fondu enchaîné entre elles."""
        self.bg(0, 0, 0)
        self.fx(blend_global=BLEND)
        hold = 4.0                                        # durée par vidéo
        pos = t / hold
        cur = int(pos) % N_VID
        nxt = (cur + 1) % N_VID
        frac = pos - int(pos)
        xf = max(0.0, (frac - 0.75) / 0.25)               # fondu sur le dernier quart
        # deux spots plein écran superposés : sortant -> entrant
        self.vspot(0, 0, 0, W, 0, int(255 * (1.0 - xf)), v=cur, blend=BLEND)
        self.vspot(1, 0, 0, W, 0, int(255 * xf), v=nxt, blend=BLEND)

    def sc_bg_panels(self, t):
        """Fond vidéo plein écran + 3 panneaux flottants (vidéos variées)."""
        self.bg(0, 0, 0)
        self.fx(blend_global=BLEND)
        self.bgvid(v=0, alpha=255)                         # décor plein écran
        breath = self.swell(t, 6.0, 0.6)
        for k in range(3):
            a = t * 0.25 + k * 2.094
            dx = math.cos(a) * 430
            dy = math.sin(a * 1.3) * 230
            self.vspot(k, dx, dy, 430 + 60 * breath, math.sin(a) * 8,
                       220, v=(k + 1) % N_VID, blend=BLEND)

    def sc_wall(self, t):
        """Mur / mosaïque : 4×3 panneaux, vidéos réparties sur le dossier."""
        self.bg(4, 4, 8)
        self.fx(blend_global=BLEND)
        pts = lay_grid(4, 3, 1360, 720)
        breath = self.swell(t, 5.0, 0.85)
        for i, (dx, dy) in enumerate(pts):
            self.vspot(i, dx, dy, 470 * breath, 0, 255, v=i % N_VID, blend=BLEND)

    def sc_desync(self, t):
        """Beaucoup de panneaux de la MÊME vidéo, alignés en diagonale : chaque
        panneau lit une frame plus ou moins retardée -> écho temporel visible."""
        self.bg(0, 0, 0)
        self.fx(blend_global=SCREEN)
        n = 10
        for i in range(n):
            f = i / (n - 1)                               # 0..1 le long de la diagonale
            dx = (f - 0.5) * 1400
            dy = (f - 0.5) * 620
            self.vspot(i, dx, dy, 560, 0, 200, v=1, blend=SCREEN)

    def sc_motion(self, t):
        """5 panneaux qui orbitent, tournent et respirent (pan/tilt/rotation/échelle)."""
        self.bg(6, 2, 10)
        self.fx(blend_global=SCREEN, feedback=140)         # légère rémanence
        for k in range(5):
            a = t * 0.6 + k * (2 * math.pi / 5)
            r = 360 + 90 * math.sin(t * 0.5 + k)
            dx = math.cos(a) * r
            dy = math.sin(a) * r * 0.62
            w = 360 + 120 * self.swell(t + k * 0.3, 4.0, 0.5)
            self.vspot(k, dx, dy, w, math.degrees(a) + t * 30, 210,
                       v=k % N_VID, blend=SCREEN)

    def sc_blend(self, t):
        """Fond vidéo + 3 copies de la même vidéo superposées en ADD/SCREEN/DIFFERENCE."""
        self.bg(0, 0, 0)
        self.fx(blend_global=BLEND)
        self.bgvid(v=2, alpha=170)
        modes = [ADD, SCREEN, DIFFERENCE]
        for k, bl in enumerate(modes):
            a = t * 0.3 + k * 2.094
            dx = math.cos(a) * 300
            dy = math.sin(a) * 170
            self.vspot(k, dx, dy, 720, math.sin(a) * 6, 200, v=0, blend=bl)

    def sc_postfx(self, t):
        """Une vidéo plein écran ; les post-effets défilent en douceur dessus."""
        self.bg(0, 0, 0)
        # 6 phases de post-effet, montée/descente douce de chacune
        phases = t / 3.0
        idx = int(phases) % 6
        amt = self.bump(t, 3.0)                            # 0 -> 1 -> 0 dans chaque phase
        kw = dict(blend_global=BLEND)
        if idx == 0:
            kw.update(bloom_thr=45, bloom=int(60 + 180 * amt))
        elif idx == 1:
            kw.update(feedback=int(60 + 150 * amt))
        elif idx == 2:
            kw.update(kaleido=6)
        elif idx == 3:
            kw.update(pixelate=int(30 + 170 * amt))
        elif idx == 4:
            kw.update(rgbsplit=int(4 + 60 * amt))
        else:
            kw.update(chroma=200, sat_a=int(120 * amt))
        self.fx(**kw)
        self.vspot(0, 0, 0, W, 0, 255, v=0, blend=BLEND)

    def sc_kaleido_wall(self, t):
        """FINALE : mur de vidéos + kaléidoscope + bloom, respiration lente."""
        self.bg(0, 0, 0)
        self.fx(blend_global=ADD, kaleido=8, bloom_thr=60,
                bloom=int(60 + 90 * self.swell(t, 4.0, 0.4)))
        pts = lay_grid(4, 3, 1200, 680)
        spin = t * 10
        for i, (dx, dy) in enumerate(pts):
            self.vspot(i, dx, dy, 420, spin * (1 if i % 2 else -1),
                       230, v=i % N_VID, blend=ADD)

    # ── Séquence ─────────────────────────────────────────────────────────────
    SCENES = [
        ("Plein écran",   "sc_fullscreen",   16),
        ("Fond+Panneaux", "sc_bg_panels",    16),
        ("Mur vidéo",     "sc_wall",         14),
        ("Désync (écho)", "sc_desync",       14),
        ("Mouvement",     "sc_motion",       16),
        ("Blend",         "sc_blend",        14),
        ("PostFX",        "sc_postfx",       18),
        ("Kaléido mur",   "sc_kaleido_wall", 16),
    ]

    def run(self):
        total = sum(d for _, _, d in self.SCENES)
        print(f"🎬  LUXCORE — VIDEO SHOW  ({N_VID} vidéos, {len(self.SCENES)} scènes, "
              f"boucle ~{total}s)")
        print(f"   cible {self.ip}:6454  ·  Ctrl+C pour quitter\n")
        try:
            while True:
                for name, fn, dur in self.SCENES:
                    print(f"  ▸ {name}  ({dur}s)")
                    scene = getattr(self, fn)
                    t0 = time.time()
                    while True:
                        t = time.time() - t0
                        if t >= dur:
                            break
                        self.frame_reset()
                        scene(t)
                        # transition douce : fondu par l'alpha des panneaux + fond
                        g = self.scene_gain(t, dur)
                        if g < 0.999:
                            for c in range(3):
                                self.dmx[c] = int(self.dmx[c] * g)
                            for i in range(MAX_PANELS):
                                a = 32 + i * 23 + 3
                                self.dmx[a] = int(self.dmx[a] * g)
                            ab = 32 + BG_SLOT * 23 + 3     # fixture de fond
                            self.dmx[ab] = int(self.dmx[ab] * g)
                        self.send()
                        time.sleep(0.02)
        except KeyboardInterrupt:
            self.frame_reset()
            self.send()
            print("\n  ⏹  Video show arrêté")


if __name__ == "__main__":
    VideoShow(IP).run()
