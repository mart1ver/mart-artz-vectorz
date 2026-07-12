#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LUXCORE DMX ENGINE — Démo KINETIC
=================================
Géométrie rythmée sur tempo : des formes pures qui pulsent, tournent, strobent
et se cadrent au BPM, avec effets PostFX et couteaux rythmés. Ni texte ni vidéo.

Lancer le moteur puis ce script :
    python_port/.venv/bin/python python_port/run_engine.py --preview --spots 60 --duration 0
    python3 demo_scripts/kinetic.py [ip] [bpm]

Author: Martin Vert
"""
import math
import sys
import time

import luxcore_artnet as lxa

# ── Réglages ─────────────────────────────────────────────────────────────────
IP = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
BPM = float(sys.argv[2]) if len(sys.argv) > 2 else 128.0

W, H = 1920, 1080
HALF_W, HALF_H = W / 2.0, H / 2.0
N_UNIVERSES = 3
DMX_LEN = 512 * N_UNIVERSES
MAX_SPOTS = 48                       # slots 0..47 (les 48 fixtures de formes)

# Blend modes — valeurs DMX exactes
BLEND, ADD, SUBTRACT, DARKEST, LIGHTEST = 0, 29, 57, 85, 114
DIFFERENCE, EXCLUSION, MULTIPLY, SCREEN, REPLACE = 142, 170, 199, 227, 255

# Formes (canal +19)
ELLIPSE, RECT, TEXTE, TRIANGLE, PENTA, HEXA, LOSANGE = 0, 1, 2, 3, 4, 5, 6
OCTO, ETOILE, CROIX, FLECHE, COEUR, SEGMENT, RAFALE = 7, 8, 9, 10, 11, 12, 13


# ── Mapping pixels → DMX (identique au décodage du moteur) ───────────────────
def to_pan(dx):
    return int((dx + 255 + HALF_W) / (510 + 2 * HALF_W) * 65535)


def to_tilt(dy):
    return int((dy + 255 + HALF_H) / (510 + 2 * HALF_H) * 65535)


def sz(px):
    return int(max(0.0, min(1000.0, px)) / 1000.0 * 65535)


def rot16(deg):
    return int((deg % 360) / 360.0 * 65535)


# ── Layouts symétriques ──────────────────────────────────────────────────────
def lay_grid(cols, rows, span_x, span_y):
    pts = []
    for r in range(rows):
        fy = 0.0 if rows == 1 else r / (rows - 1) - 0.5
        for c in range(cols):
            fx = 0.0 if cols == 1 else c / (cols - 1) - 0.5
            pts.append((fx * span_x, fy * span_y))
    return pts


def lay_ring(n, radius, phase=0.0, squash=1.0):
    return [(radius * math.cos(2 * math.pi * k / n + phase),
             radius * math.sin(2 * math.pi * k / n + phase) * squash)
            for k in range(n)]


class Kinetic:
    def __init__(self, ip=IP, bpm=BPM):
        self.ip = ip
        self.sock = lxa.make_socket()
        self.dmx = [0] * DMX_LEN
        self.spb = 60.0 / bpm            # secondes par temps (beat)

    # ── I/O ──────────────────────────────────────────────────────────────────
    def send(self):
        lxa.send_multi(self.sock, self.dmx, self.ip)

    def frame_reset(self):
        """Repart d'une ardoise noire chaque frame (aucun résidu de scène)."""
        self.dmx = [0] * DMX_LEN

    def bg(self, r, g, b):
        self.dmx[0], self.dmx[1], self.dmx[2] = int(r), int(g), int(b)

    def fx(self, blur=0, sigma=0, pixelate=0, sobel=0, rgbsplit=0,
           sat_a=0, sat_b=0, chroma=0, blend_global=0,
           feedback=0, bloom_thr=60, bloom=0, kaleido=0):
        d = self.dmx
        d[19] = int(blend_global)
        d[20] = int(blur); d[21] = int(sigma)
        d[22] = int(pixelate); d[23] = int(sobel)
        d[24] = int(rgbsplit); d[25] = int(sat_a); d[26] = int(sat_b)
        d[27] = int(chroma)
        d[28] = int(feedback); d[29] = int(bloom_thr)      # PostFX ajoutés :
        d[30] = int(bloom); d[31] = int(kaleido)           # feedback/bloom/kaléido

    def blade(self, idx, val16):
        """Couteau idx (0..7) sur 16 bits (0 = ouvert, grand = couvre)."""
        lxa.set16(self.dmx, 3 + idx * 2, val16)

    def spot(self, i, rgb, alpha, dx, dy, w, h, deg, mode,
             blend=0, sw=0, sa=0, stroke=(255, 255, 255)):
        if i >= MAX_SPOTS:
            return
        b = 32 + i * 23
        d = self.dmx
        d[b], d[b + 1], d[b + 2] = int(rgb[0]), int(rgb[1]), int(rgb[2])
        d[b + 3] = int(max(0, min(255, alpha)))
        d[b + 4] = int(sw); d[b + 5] = int(sa)
        d[b + 6], d[b + 7], d[b + 8] = int(stroke[0]), int(stroke[1]), int(stroke[2])
        lxa.set16(d, b + 9, sz(w))
        lxa.set16(d, b + 11, sz(h))
        lxa.set16(d, b + 13, rot16(deg))
        lxa.set16(d, b + 15, to_pan(dx))
        lxa.set16(d, b + 17, to_tilt(dy))
        d[b + 19] = int(mode)
        d[b + 20] = 255
        d[b + 21] = int(blend)

    # ── Enveloppes de tempo ──────────────────────────────────────────────────
    def env(self, t, div=1.0, sharp=6.0):
        """Pulse qui claque sur la subdivision (1=beat, 0.5=8e, 0.25=16e) et décroît."""
        ph = (t / (self.spb * div)) % 1.0
        return math.exp(-sharp * ph)

    def gate(self, t, div=1.0, duty=0.25):
        """Porte on/off (strobe) : 1 pendant `duty` de la subdivision, sinon 0."""
        return 1.0 if (t / (self.spb * div)) % 1.0 < duty else 0.0

    def swell(self, t, div=1.0, floor=0.4):
        """Respiration douce (cosinus) sur la subdivision, plancher `floor` -> ne
        retombe JAMAIS à zéro. À préférer à `env` pour éviter tout clignotement :
        la lumière pompe en continu au lieu de claquer du noir au plein feu."""
        ph = (t / (self.spb * div)) % 1.0
        return floor + (1.0 - floor) * (0.5 + 0.5 * math.cos(2.0 * math.pi * ph))

    def beat_i(self, t):
        return int(t / self.spb)

    def bar_i(self, t):
        return int(t / (self.spb * 4))

    def scene_gain(self, t, dur, fade_beats=4.0):
        """Gain global 0..1 : fondu ENTRANT puis SORTANT (courbe cosinus) pour des
        transitions douces à travers le noir entre scènes."""
        fade = self.spb * fade_beats
        if t < fade:
            x = t / fade
        elif t > dur - fade:
            x = (dur - t) / fade
        else:
            return 1.0
        x = max(0.0, min(1.0, x))
        return 0.5 - 0.5 * math.cos(math.pi * x)      # smoothstep cosinus

    # ══ SCÈNES ═══════════════════════════════════════════════════════════════
    def sc_pulse_grid(self, t):
        """Grille de formes qui gonflent sur le kick, couleur par mesure, ADD."""
        self.bg(0, 0, 0)
        beat = self.swell(t, 1.0, 0.5)
        blur = int(18 * beat)
        self.fx(blur=blur, sigma=blur // 2, blend_global=ADD,
                bloom_thr=90, bloom=int(70 + 110 * beat))     # halo qui respire (pas de flash)
        hue0 = (self.bar_i(t) * 0.13) % 1.0
        pts = lay_grid(8, 5, 1500, 720)
        mode = RECT if (self.bar_i(t) // 2) % 2 else ELLIPSE
        for i, (dx, dy) in enumerate(pts):
            local = self.swell(t + i * 0.02, 1.0, 0.5)    # léger retard -> vague douce
            s = 70 + 100 * local
            col = lxa.hsv(hue0 + i * 0.012, 1.0, 0.6 + 0.4 * local)
            self.spot(i, col, int(150 + 105 * local), dx, dy, s, s, 0, mode, blend=ADD)

    def sc_chase_ring(self, t):
        """Deux anneaux ; un point lumineux chasse sur les 16e, SCREEN."""
        self.bg(0, 0, 0)
        # feedback = comètes : le point qui chasse laisse une traînée lumineuse
        # (chase = lumière qui court le long de l'anneau -> mouvement, pas clignotement)
        self.fx(blend_global=SCREEN, rgbsplit=4, feedback=150)
        step = int(t / (self.spb * 0.5))                  # position en 8e (plus lent, moins nerveux)
        # base = taille au repos (bien > espacement -> forte superposition)
        rings = [(16, 470, 0.0, ETOILE, 400), (10, 250, math.pi / 10, TRIANGLE, 340)]
        i = 0
        for count, rad, ph, mode, base in rings:
            spin = t * 0.5 * (1 if count == 16 else -1)
            for k, (dx, dy) in enumerate(lay_ring(count, rad, ph + spin)):
                on = 1.0 if (step % count) == k else 0.0
                tail = max(on, 0.6 if (step - 1) % count == k else 0.0,
                           0.35 if (step - 2) % count == k else 0.0,
                           0.18 if (step - 3) % count == k else 0.0)
                col = lxa.hsv((k / count + t * 0.05) % 1.0, 1.0, 0.45 + 0.55 * tail)
                deg = math.degrees(math.atan2(dy, dx)) + t * 40
                s = base + 90 * on                        # sursaut adouci
                self.spot(i, col, int(110 + 145 * tail), dx, dy,
                          s, s, deg, mode, blend=SCREEN)
                i += 1

    def sc_symmetry(self, t):
        """Champ symétrique kaléidoscopique qui respire doucement (remplace l'ancien
        strobe : aucun blackout ni flash, la lumière pompe en continu)."""
        self.bg(0, 0, 0)
        # kaléido fixe sur la scène (changer le nb de branches ferait « sauter » le
        # motif) ; bloom léger constant pour la matière
        self.fx(blend_global=ADD, kaleido=6, bloom_thr=80, bloom=90)
        breath = self.swell(t, 2.0, 0.55)                 # respiration lente (2 temps)
        hue = t * 0.06
        for i, (dx, dy) in enumerate(lay_grid(9, 5, 1650, 760)):
            col = lxa.hsv(hue + (i % 9) * 0.02, 0.7, 0.6 + 0.4 * breath)
            s = 120 + 55 * breath
            self.spot(i, col, int(160 + 80 * breath), dx, dy,
                      s, s, t * 20, RECT, blend=ADD)

    def sc_rotation(self, t):
        """Anneaux concentriques verrouillés en rotation, blur pulsé, DIFFERENCE."""
        self.bg(10, 0, 14)
        beat = self.swell(t, 1.0, 0.45)
        # feedback : les anneaux qui tournent laissent des spirales rémanentes
        self.fx(blur=int(30 * beat), sigma=int(15 * beat), blend_global=DIFFERENCE,
                feedback=175)
        i = 0
        for ring, (count, rad, mode) in enumerate(
                [(6, 180, TRIANGLE), (10, 340, ETOILE), (14, 500, HEXA)]):
            spin = t * (30 + ring * 22) * (1 if ring % 2 == 0 else -1)
            for dx, dy in lay_ring(count, rad):
                col = lxa.hsv((ring * 0.3 + t * 0.08) % 1.0, 0.9, 1.0)
                # taille bien > espacement -> forte superposition des anneaux
                s = 360 + ring * 55 + 60 * beat
                self.spot(i, col, 210, dx, dy, s, s, spin, mode,
                          blend=BLEND, sw=14, sa=255, stroke=(255, 255, 255))
                i += 1

    def sc_blade_sweep(self, t):
        """Champ de formes derrière des couteaux qui s'ouvrent/ferment à la mesure."""
        self.bg(0, 0, 0)
        pulse = self.swell(t, 1.0, 0.45)
        # bloom : le champ de formes derrière les couteaux irradie sur la respiration
        self.fx(blend_global=ADD, bloom_thr=70, bloom=int(90 + 90 * pulse))
        # couteaux haut/bas qui respirent sur 2 mesures
        ph = (t / (self.spb * 8)) % 1.0
        cover = int(26000 * (0.5 - 0.5 * math.cos(2 * math.pi * ph)))
        for b in (0, 1, 4, 5):        # A1/A2 (haut) + C1/C2 (bas)
            self.blade(b, cover)
        for i, (dx, dy) in enumerate(lay_grid(10, 4, 1700, 620)):
            col = lxa.hsv((0.55 + i * 0.02 + t * 0.05) % 1.0, 0.85, 1.0)
            s = 60 + 90 * pulse
            self.spot(i, col, 220, dx, dy, s, s, t * 60, PENTA, blend=ADD)

    def sc_bloom(self, t):
        """FINALE : floraison de grandes formes concentriques qui pulsent, tournent
        et se chevauchent fortement (ADD). Flash + chroma sur le kick, montée en
        intensité sur la durée. Grosses formes -> superposition et glow."""
        self.bg(0, 0, 0)
        kick = self.swell(t, 1.0, 0.5)                     # pompe douce sur le temps
        build = min(1.0, t / (self.spb * 16))              # montée progressive
        # BLOOM au sommet : halo qui monte avec la scène + feedback rémanent ;
        # kaléido qui se referme sur les 4 dernières mesures pour la sortie
        bars = self.bar_i(t)
        self.fx(blur=int(22 * kick), sigma=int(11 * kick),
                blend_global=ADD,
                bloom_thr=45, bloom=int(90 + 140 * build),
                feedback=int(120 * build),
                kaleido=8 if bars >= 8 else 0)
        hue0 = t * 0.28
        # 3 couronnes concentriques de GRANDES formes (cœur + hexagones + étoiles)
        rings = [(1, 0, 470, ELLIPSE), (6, 230, 380, HEXA), (12, 440, 320, ETOILE)]
        i = 0
        for ring, (count, rad, base, mode) in enumerate(rings):
            spin = t * (55 - ring * 40)
            pts = [(0.0, 0.0)] if count == 1 else lay_ring(count, rad, t * 0.4)
            for k, (dx, dy) in enumerate(pts):
                s = base + 160 * kick + 90 * build
                col = lxa.hsv(hue0 + k * 0.03 + ring * 0.14, 1.0, 1.0)
                deg = spin + math.degrees(math.atan2(dy, dx))
                self.spot(i, col, int(140 + 115 * kick), dx, dy, s, s, deg,
                          mode, blend=ADD)
                i += 1

    # ── Séquence ─────────────────────────────────────────────────────────────
    SCENES = [
        ("Pulse Grid",  "sc_pulse_grid", 8),
        ("Chase Ring",  "sc_chase_ring", 8),
        ("Symétrie",    "sc_symmetry",   8),
        ("Rotation",    "sc_rotation",   8),
        ("Blade Sweep", "sc_blade_sweep", 8),
        ("Bloom",       "sc_bloom",     12),
    ]

    def run(self):
        bars_to_s = self.spb * 4
        total = sum(b for _, _, b in self.SCENES) * bars_to_s
        print(f"🎛️  LUXCORE — KINETIC  ({BPM:.0f} BPM, {len(self.SCENES)} scènes, "
              f"boucle ~{total:.0f}s)")
        print(f"   cible {self.ip}:6454  ·  Ctrl+C pour quitter\n")
        try:
            while True:
                for name, fn, bars in self.SCENES:
                    dur = bars * bars_to_s
                    print(f"  ▸ {name}  ({bars} mesures)")
                    fx = getattr(self, fn)
                    t0 = time.time()
                    while True:
                        t = time.time() - t0
                        if t >= dur:
                            break
                        self.frame_reset()
                        fx(t)
                        # Phase GLITCH commune : sobel + pixelate CONSTANTS sur le 3e
                        # quart de chaque scène (valeurs figées -> aucun scintillement).
                        if dur * 0.5 <= t < dur * 0.75:
                            self.dmx[23] = 200                       # sobel (>128 = on)
                            self.dmx[22] = 190                       # pixelate constant
                        # Transition douce : fondu entrant + sortant (1 mesure de
                        # chaque côté), sur l'alpha des spots ET le fond -> passage
                        # progressif par le noir entre les scènes.
                        g = self.scene_gain(t, dur)
                        if g < 0.999:
                            self.dmx[0] = int(self.dmx[0] * g)
                            self.dmx[1] = int(self.dmx[1] * g)
                            self.dmx[2] = int(self.dmx[2] * g)
                            for i in range(MAX_SPOTS):
                                a = 32 + i * 23 + 3
                                self.dmx[a] = int(self.dmx[a] * g)
                        self.send()
                        time.sleep(0.02)
        except KeyboardInterrupt:
            self.frame_reset()
            self.send()
            print("\n  ⏹  Kinetic arrêté")


if __name__ == "__main__":
    Kinetic().run()
