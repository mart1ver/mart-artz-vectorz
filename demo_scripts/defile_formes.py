#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LUXCORE DMX ENGINE - DÉFILÉ DES 15 FORMES
==========================================
Affiche chaque forme une par une, avec 7 spots arrangés,
fond blanc, blades encadrantes et couleur thématique.
Author: Martin Vert
"""

import socket
import time
import math
import sys

# ── Identité de chaque forme ─────────────────────────────────────────────────
FORMES = [
    {"id": 0,  "nom": "Ellipse",        "r": 220, "g":  80, "b":  80},
    {"id": 1,  "nom": "Rectangle",      "r":  80, "g": 160, "b": 220},
    {"id": 2,  "nom": "Texte",          "r": 180, "g":  60, "b": 200},
    {"id": 3,  "nom": "Triangle",       "r": 220, "g": 160, "b":  40},
    {"id": 4,  "nom": "Pentagone",      "r":  60, "g": 200, "b": 120},
    {"id": 5,  "nom": "Hexagone",       "r":  40, "g": 180, "b": 220},
    {"id": 6,  "nom": "Losange",        "r": 220, "g":  80, "b": 160},
    {"id": 7,  "nom": "Octogone",       "r": 100, "g": 100, "b": 220},
    {"id": 8,  "nom": "Étoile",         "r": 240, "g": 200, "b":  40},
    {"id": 9,  "nom": "Croix",          "r": 220, "g":  60, "b":  60},
    {"id": 10, "nom": "Flèche",         "r":  60, "g": 220, "b":  80},
    {"id": 11, "nom": "Plus",           "r": 180, "g": 180, "b": 180},
    {"id": 12, "nom": "Cœur",           "r": 240, "g":  40, "b":  80},
    {"id": 13, "nom": "Maison",         "r": 140, "g": 100, "b":  60},
    {"id": 14, "nom": "Spirale Carrée", "r":  80, "g": 200, "b": 200},
]

# ── 7 positions disposées : 1 centre + 6 en cercle ───────────────────────────
# Valeurs 16-bit (0-65535), centre = 32767
def positions_cercle(rayon_16bit=10000):
    pos = [(32767, 32767)]  # centre
    for i in range(6):
        angle = i * math.pi / 3
        x = int(32767 + rayon_16bit * math.cos(angle))
        y = int(32767 + rayon_16bit * math.sin(angle))
        pos.append((x, y))
    return pos

POSITIONS = positions_cercle(11000)


class DefileFormes:
    def __init__(self, ip="127.0.0.1"):
        self.ip = ip
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.dmx = [0] * 512

    # ── Envoi ArtNet ─────────────────────────────────────────────────────────
    def send(self):
        header = b"Art-Net\x00"
        pkt = (header
               + (0x5000).to_bytes(2, 'little')
               + bytes([0, 14, 0, 0, 0, 0])
               + len(self.dmx).to_bytes(2, 'big')
               + bytes(self.dmx))
        self.sock.sendto(pkt, (self.ip, 6454))

    # ── Écriture helpers ─────────────────────────────────────────────────────
    def set16(self, idx, val):
        val = max(0, min(65535, int(val)))
        self.dmx[idx]     = (val >> 8) & 0xFF
        self.dmx[idx + 1] = val & 0xFF

    def set_spot(self, spot_id, r, g, b, alpha, sw, sa, sr, sg, sb,
                 size_pan, size_tilt, rot16, pan, tilt, mode):
        base = 28 + spot_id * 20
        self.dmx[base]     = r
        self.dmx[base + 1] = g
        self.dmx[base + 2] = b
        self.dmx[base + 3] = alpha
        self.dmx[base + 4] = sw
        self.dmx[base + 5] = sa
        self.dmx[base + 6] = sr
        self.dmx[base + 7] = sg
        self.dmx[base + 8] = sb
        self.set16(base + 9,  size_pan)
        self.set16(base + 11, size_tilt)
        self.set16(base + 13, rot16)   # Rotation 16-bit MSB+LSB
        self.set16(base + 15, pan)
        self.set16(base + 17, tilt)
        self.dmx[base + 19] = mode

    # ── Fond + blades en cadre fixe ──────────────────────────────────────────
    def set_base(self, t):
        # Fond blanc
        self.dmx[0] = 255
        self.dmx[1] = 255
        self.dmx[2] = 255

        # Blades : cadre serré qui respire légèrement
        margin = int(4000 + 1500 * math.sin(t * 0.4))

        self.set16(3,  margin)           # A1 (top gauche)
        self.set16(5,  margin)           # A2 (top droite)
        self.set16(11, margin)           # C1 (bas gauche)
        self.set16(13, margin)           # C2 (bas droite)
        self.set16(7,  margin)           # B1 (droite haut)
        self.set16(9,  margin)           # B2 (droite bas)
        self.set16(15, margin)           # D1 (gauche haut)
        self.set16(17, margin)           # D2 (gauche bas)

        # Blend mode fixe (BLEND normal)
        self.dmx[19] = 0

        # Effets off
        for i in range(20, 28):
            self.dmx[i] = 0

        # Nombre de spots actifs = 7
        self.dmx[27] = 0  # pas de canal "nb spots" ici, géré par le pool Processing

    # ── Rendu d'une forme pendant sa tranche de temps ────────────────────────
    def render_forme(self, forme, t_local, alpha_factor=1.0):
        fid = forme["id"]
        r0, g0, b0 = forme["r"], forme["g"], forme["b"]

        for i, (px, py) in enumerate(POSITIONS):
            phase = i * math.pi / 3.5

            # Couleur : modulation douce autour de la teinte thématique
            r = int(max(0, min(255, r0 * (0.75 + 0.25 * math.sin(t_local * 0.8 + phase)))))
            g = int(max(0, min(255, g0 * (0.75 + 0.25 * math.sin(t_local * 0.9 + phase + 1)))))
            b = int(max(0, min(255, b0 * (0.75 + 0.25 * math.sin(t_local * 0.7 + phase + 2)))))

            # Alpha avec fade
            alpha = int(200 * alpha_factor * (0.85 + 0.15 * math.sin(t_local * 1.1 + phase)))

            # Stroke contrastant
            sw = 20 if i == 0 else 12
            sa = 180
            sr, sg, sb = 255 - r, 255 - g, 255 - b

            # Taille : spot central plus grand
            base_size = 14000 if i == 0 else 9000
            size = int(base_size + 2000 * math.sin(t_local * 0.6 + phase))

            # Rotation 16-bit lente, sens alterné
            rot_speed = 8 if i % 2 == 0 else -6
            rot = int((t_local * rot_speed + i * 25) % 360 * 65535 / 360)

            # Position orbitale légère autour de la position de base
            orbit = int(600 * math.sin(t_local * 0.5 + phase))
            pan  = max(0, min(65535, px + orbit))
            tilt = max(0, min(65535, py + int(orbit * 0.6)))

            self.set_spot(i, r, g, b, alpha, sw, sa, sr, sg, sb,
                          size, size, rot, pan, tilt, fid)

    # ── Blackout (spots alpha = 0) ────────────────────────────────────────────
    def blackout_spots(self):
        for i in range(7):
            base = 28 + i * 20
            self.dmx[base + 3] = 0  # alpha = 0

    # ── Boucle principale ────────────────────────────────────────────────────
    def run(self, duree_par_forme=6.0, transition=0.6):
        total = len(FORMES) * (duree_par_forme + transition)
        print("🎭 LUXCORE - DÉFILÉ DES 15 FORMES")
        print("=" * 45)
        print(f"   {len(FORMES)} formes × {duree_par_forme}s + {transition}s transition")
        print(f"   Durée totale : {total:.0f}s")
        print(f"   Cible       : {self.ip}:6454")
        print()

        fps_count = 0
        fps_t0 = time.time()

        try:
            for forme in FORMES:
                print(f"  ▶  Forme {forme['id']:2d} — {forme['nom']}")

                # --- Affichage principal ---
                t0 = time.time()
                while True:
                    t_local = time.time() - t0
                    if t_local >= duree_par_forme:
                        break

                    # Fade in (0.4s) et fade out (0.4s)
                    if t_local < 0.4:
                        af = t_local / 0.4
                    elif t_local > duree_par_forme - 0.4:
                        af = (duree_par_forme - t_local) / 0.4
                    else:
                        af = 1.0

                    self.set_base(t_local)
                    self.render_forme(forme, t_local, af)
                    self.send()

                    fps_count += 1
                    time.sleep(0.02)

                # --- Transition (blackout court) ---
                t0 = time.time()
                while time.time() - t0 < transition:
                    self.set_base(0)
                    self.blackout_spots()
                    self.send()
                    time.sleep(0.02)

        except KeyboardInterrupt:
            print("\n  ⏹  Interrompu")

        # Reset final
        self.dmx = [0] * 512
        self.send()

        elapsed = time.time() - fps_t0
        fps_avg = fps_count / elapsed if elapsed > 0 else 0
        print()
        print(f"✅ Défilé terminé — {fps_count} frames — {fps_avg:.1f} FPS moyen")


def main():
    ip = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
    duree = float(sys.argv[2]) if len(sys.argv) > 2 else 6.0

    DefileFormes(ip).run(duree_par_forme=duree)


if __name__ == "__main__":
    main()
