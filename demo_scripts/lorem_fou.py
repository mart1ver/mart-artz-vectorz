#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LUXCORE DMX ENGINE — LOREM FOU (démo texte survitaminée)
========================================================
Un flot de « lorem ipsum » déchaîné, avec un maximum de PostFX empilés. Chaque
caractère est un spot en mode TEXTE (+19 = 2) : le caractère est encodé dans
size_tilt (char_tilt), l'échelle dans size_pan, la police via +22.

6 scènes, toutes avec des post-effets superposés :
  1. FLUX      — texte qui coule sur 3 lignes, arc-en-ciel (bloom+feedback+chroma)
  2. KALÉIDO   — grappe de lettres repliée en mandala (kaléido+bloom+saturation)
  3. GLITCH    — lettres qui tremblent, contours (sobel+pixelate+rgb split)
  4. SPIRALE   — lettres sur une spirale tournante (feedback+bloom)
  5. RAFALE    — lettres qui explosent du centre et se recyclent (feedback+chroma+rgb split)
  6. GÉANT     — quelques mots énormes qui pulsent (bloom+blur qui respirent)

Confort visuel : montées douces (swell), bistables (sobel/chroma) stables sur la
durée d'une scène -> pas de strobe.

Lancer le moteur puis :  python3 lorem_fou.py [ip]
Author: Martin Vert
"""

import math
import sys
import time

import luxcore_artnet as lxa

IP = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"

W, H = 1920, 1080
HALF_W, HALF_H = W / 2.0, H / 2.0
N_UNIVERSES = 3
DMX_LEN = 512 * N_UNIVERSES
MAX_SPOTS = 48                        # slots 0..47 (caractères simultanés)
N_FONTS = 20                          # polices chargées par le moteur

TEXTE = 2                             # mode forme = TEXTE
BLEND, ADD, SCREEN, DIFFERENCE, LIGHTEST = 0, 29, 227, 142, 114

LOREM = ("lorem ipsum dolor sit amet consectetur adipiscing elit sed do eiusmod "
         "tempor incididunt ut labore et dolore magna aliqua ut enim ad minim veniam "
         "quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo "
         "consequat duis aute irure dolor in reprehenderit voluptate velit esse cillum")
L = len(LOREM)


def clamp8(v):
    return max(0, min(255, int(v)))


def to_pan(dx):
    return int((dx + 255 + HALF_W) / (510 + 2 * HALF_W) * 65535)


def to_tilt(dy):
    return int((dy + 255 + HALF_H) / (510 + 2 * HALF_H) * 65535)


def font_raw(f):
    """Index de police 0..N_FONTS-1 -> canal +22."""
    return clamp8(int((f % N_FONTS + 0.5) * 256 / N_FONTS))


class LoremFou:
    def __init__(self, ip):
        self.ip = ip
        self.sock = lxa.make_socket()
        self.dmx = [0] * DMX_LEN

    # ── I/O ──────────────────────────────────────────────────────────────────
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

    def letter(self, i, c, dx, dy, scale, rot=0.0, rgb=(255, 255, 255), alpha=255,
               font=0, sw=0, sa=0, stroke=(0, 0, 0)):
        """Place le caractère `c` en (dx,dy) px, échelle `scale` (size_pan)."""
        if i >= MAX_SPOTS:
            return
        b = 32 + i * 23
        d = self.dmx
        d[b], d[b + 1], d[b + 2] = clamp8(rgb[0]), clamp8(rgb[1]), clamp8(rgb[2])
        d[b + 3] = clamp8(alpha)
        d[b + 4] = clamp8(sw); d[b + 5] = clamp8(sa)
        d[b + 6], d[b + 7], d[b + 8] = clamp8(stroke[0]), clamp8(stroke[1]), clamp8(stroke[2])
        lxa.set16(d, b + 9, max(0, min(65535, math.ceil(scale * 65535 / 1000))))
        lxa.set16(d, b + 11, lxa.char_tilt(c))
        lxa.set16(d, b + 13, int(rot % 360 * 65535 / 360))
        lxa.set16(d, b + 15, to_pan(dx))
        lxa.set16(d, b + 17, to_tilt(dy))
        d[b + 19] = TEXTE
        d[b + 20] = 255
        d[b + 21] = 0
        d[b + 22] = font_raw(font)

    # ── Enveloppe douce (pas de noir -> pas de clignotement) ─────────────────
    @staticmethod
    def swell(t, period, floor=0.4):
        ph = (t / period) % 1.0
        return floor + (1.0 - floor) * (0.5 + 0.5 * math.cos(2.0 * math.pi * ph))

    @staticmethod
    def scene_gain(t, dur, fade=1.6):
        if t < fade:
            x = t / fade
        elif t > dur - fade:
            x = (dur - t) / fade
        else:
            return 1.0
        return 0.5 - 0.5 * math.cos(math.pi * max(0.0, min(1.0, x)))

    # ══ SCÈNES ═══════════════════════════════════════════════════════════════
    def sc_flux(self, t):
        """Texte qui coule sur 3 lignes, arc-en-ciel. Bloom + feedback + chroma."""
        self.bg(0, 0, 0)
        self.fx(blend_global=ADD, bloom_thr=55, bloom=int(80 + 80 * self.swell(t, 2.0, 0.5)),
                feedback=110, chroma=200)
        rows, per = 3, 16
        step = int(t * 5)
        slot = 0
        for r in range(rows):
            y = (r - 1) * 250
            drift = (t * 80) % 120
            for k in range(per):
                c = LOREM[(step + r * per + k) % L]
                if c == ' ':
                    continue
                dx = (k - (per - 1) / 2.0) * 120 - drift + 60
                hue = (t * 0.10 + (r * per + k) * 0.02) % 1.0
                self.letter(slot, c, dx, y + 20 * math.sin(t * 2 + k * 0.5), 72,
                            0, lxa.hsv(hue), font=(r * 5 + k) % N_FONTS)
                slot += 1
                if slot >= MAX_SPOTS:
                    return

    def sc_kaleido(self, t):
        """Grappe de lettres au centre, repliée en mandala par le kaléidoscope."""
        self.bg(0, 0, 0)
        self.fx(blend_global=ADD, kaleido=8, bloom_thr=60, bloom=90,
                sat_a=int(120 * self.swell(t, 4.0, 0.3)))
        n = 30
        for i in range(n):
            c = LOREM[(int(t * 3) + i) % L]
            if c == ' ':
                continue
            a = i * 0.7 + t * 0.5
            rr = 60 + i * 9
            self.letter(i, c, math.cos(a) * rr, math.sin(a) * rr * 0.8, 60,
                        math.degrees(a), lxa.hsv((i * 0.05 + t * 0.1) % 1.0),
                        font=i % N_FONTS)

    def sc_glitch(self, t):
        """Lettres qui tremblent, contours + blocs + dispersion (sobel+pixelate+rgb split)."""
        self.bg(0, 0, 0)
        self.fx(blend_global=ADD, sobel=200, pixelate=int(120 + 60 * self.swell(t, 1.5, 0.0)),
                rgbsplit=40, bloom_thr=70, bloom=60)
        rows, per = 3, 15
        step = int(t * 7)
        slot = 0
        for r in range(rows):
            y = (r - 1) * 250
            for k in range(per):
                c = LOREM[(step + r * per + k) % L]
                if c == ' ':
                    continue
                jx = 14 * math.sin(t * 23 + slot * 2.1)      # tremblement rapide (spatial)
                jy = 12 * math.cos(t * 19 + slot * 1.7)
                dx = (k - (per - 1) / 2.0) * 125
                self.letter(slot, c, dx + jx, y + jy, 74, 0,
                            (255, 255, 255), font=(step + slot) % N_FONTS)
                slot += 1
                if slot >= MAX_SPOTS:
                    return

    def sc_spirale(self, t):
        """Lettres sur une spirale phyllotaxique tournante. Feedback + bloom."""
        self.bg(2, 0, 6)
        self.fx(blend_global=SCREEN, feedback=165, bloom_thr=55,
                bloom=int(70 + 70 * self.swell(t, 3.0, 0.4)))
        ga = math.pi * (3 - math.sqrt(5))
        n = 40
        for i in range(n):
            c = LOREM[(int(t * 2) + i) % L]
            if c == ' ':
                continue
            a = i * ga + t * 0.6
            rr = 26 * math.sqrt(i + 0.5)
            self.letter(i, c, math.cos(a) * rr, math.sin(a) * rr * 0.75,
                        50 + 26 * (i / n), math.degrees(a) + t * 30,
                        lxa.hsv((i * 0.03 + t * 0.12) % 1.0), font=i % N_FONTS)

    def sc_rafale(self, t):
        """Lettres qui explosent du centre et se recyclent. Feedback + chroma + rgb split."""
        self.bg(0, 0, 0)
        self.fx(blend_global=ADD, feedback=150, chroma=200,
                rgbsplit=int(20 + 30 * self.swell(t, 2.0, 0.3)), bloom_thr=50, bloom=90)
        n = 40
        for i in range(n):
            c = LOREM[(int(t * 4) + i) % L]
            if c == ' ':
                continue
            a = i * (2 * math.pi / 13) + t * 0.3
            life = ((t * 0.6 + i * 0.13) % 1.0)              # 0->1 progression radiale
            rr = 40 + life * 820
            alpha = int(255 * (1.0 - life) ** 0.6)
            self.letter(i, c, math.cos(a) * rr, math.sin(a) * rr * 0.62,
                        40 + 90 * (1.0 - life), math.degrees(a),
                        lxa.hsv((i * 0.04 + t * 0.15) % 1.0), alpha=alpha,
                        font=i % N_FONTS)

    def sc_geant(self, t):
        """Quelques mots ÉNORMES qui pulsent, un mot à la fois. Bloom + blur qui respirent."""
        self.bg(0, 0, 0)
        breath = self.swell(t, 2.5, 0.5)
        self.fx(blend_global=ADD, bloom_thr=45, bloom=int(90 + 110 * breath),
                blur=int(16 * (1 - breath)), sigma=int(8 * (1 - breath)), feedback=90)
        words = ["lorem", "ipsum", "dolor", "amet"]
        w = words[int(t / 3) % len(words)]
        scale = 190 + 40 * breath
        span = (len(w) - 1) * 210
        for i, c in enumerate(w):
            dx = i * 210 - span / 2.0
            hue = (t * 0.08 + i * 0.06) % 1.0
            self.letter(i, c, dx, 30 * math.sin(t * 1.5 + i), scale,
                        6 * math.sin(t + i), lxa.hsv(hue, 0.8, 1.0),
                        font=(int(t / 3) * 3 + i) % N_FONTS, sw=8,
                        sa=200, stroke=lxa.hsv((hue + 0.5) % 1.0))

    # ── Séquence ─────────────────────────────────────────────────────────────
    SCENES = [
        ("Flux",    "sc_flux",    16),
        ("Kaléido", "sc_kaleido", 16),
        ("Glitch",  "sc_glitch",  14),
        ("Spirale", "sc_spirale", 16),
        ("Rafale",  "sc_rafale",  16),
        ("Géant",   "sc_geant",   14),
    ]

    def run(self):
        total = sum(d for _, _, d in self.SCENES)
        print(f"🔤  LUXCORE — LOREM FOU  ({len(self.SCENES)} scènes, boucle ~{total}s)")
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
                        # fondu doux entre scènes (alpha des lettres + fond)
                        g = self.scene_gain(t, dur)
                        if g < 0.999:
                            for c in range(3):
                                self.dmx[c] = int(self.dmx[c] * g)
                            for i in range(MAX_SPOTS):
                                a = 32 + i * 23 + 3
                                self.dmx[a] = int(self.dmx[a] * g)
                        self.send()
                        time.sleep(0.02)
        except KeyboardInterrupt:
            self.frame_reset()
            self.send()
            print("\n  ⏹  Lorem fou arrêté")


if __name__ == "__main__":
    LoremFou(IP).run()
