#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LUXCORE — Animation texte multi-mots avec triangle.
Cycle : "ArtNet" 6s → "controled" 6s → ...
Author: Martin Vert
"""

import time, signal, sys, math
import luxcore_artnet as lxa

IP   = "127.0.0.1"
sock = lxa.make_socket()
dmx  = [0] * 512

def set16(idx, val): lxa.set16(dmx, idx, val)
def send(): lxa.send(sock, dmx, IP)
def char_tilt(c): return lxa.char_tilt(c)
def hsv(h, s=1.0, v=1.0): return lxa.hsv(h, s, v)

def make_pan_u(mot, offsets_px, spacing, offset_global=0):
    px_to_u = 65535 / 2430
    step_u  = int(spacing * px_to_u)
    center_u = int(32767 + offset_global * px_to_u)
    start_u  = int(center_u - (len(mot) - 1) * step_u / 2)
    return [start_u + i * step_u + int(offsets_px[i] * px_to_u) for i in range(len(mot))]

# ── Configuration des mots ─────────────────────────────────────────────────────
MOTS = [
    {"mot": "ArtNet",     "spacing": 90, "duree": 4.0, "offsets": [0, 0, -30, 0, 0, -30]},
    {"mot": "controled",  "spacing": 75, "duree": 4.0, "offsets": [0, -20, 0, 10, 0, 0, 0, 0, 0]},
    {"mot": "generator",  "spacing": 75, "duree": 4.0, "offsets": [0, 0, 0, 0, 0, 0, 0, 0, 0]},
    {"mot": "made by:",   "spacing": 80, "duree": 4.0, "offsets": [0, 0, 0, 0, 0, 0, 0, 0]},
    {"mot": "Martin VERT","spacing": 80, "duree": 6.0, "offsets": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]},
]
DUREE_MOT = 6.0   # durée par défaut (scène 5)

# Pré-calcul des positions
for cfg in MOTS:
    cfg["pan_u"] = make_pan_u(cfg["mot"], cfg["offsets"], cfg["spacing"])

# ── Signal ────────────────────────────────────────────────────────────────────
def on_exit(sig, frame):
    print("\n  Extinction...")
    dmx[:] = [0] * 512
    send()
    sys.exit(0)

signal.signal(signal.SIGINT, on_exit)
print("🔤  ArtNet → controled — Ctrl+C pour quitter")

Y_CENTER  = 32767
SCALE_PAN = 48

t0 = time.time()
mot_actif = None

while True:
    t = time.time() - t0

    # Sélection du mot courant selon durées variables
    cycle = sum(c["duree"] for c in MOTS)
    tc = t % cycle
    mot_idx, cumul = 0, 0.0
    for idx, cfg in enumerate(MOTS):
        cumul += cfg["duree"]
        if tc < cumul:
            mot_idx = idx
            break
    cfg = MOTS[mot_idx]
    mot   = cfg["mot"]
    pan_u = cfg["pan_u"]

    if mot != mot_actif:
        print(f"  → \"{mot}\"")
        mot_actif = mot

    # ── Fond blanc
    dmx[0], dmx[1], dmx[2] = 255, 255, 255
    dmx[19] = 0   # BLEND

    # ── Couteaux
    blade_base = 8000
    blade_wave = int(2000 * math.sin(t * 0.8))
    set16(3,  blade_base + blade_wave)
    set16(5,  blade_base - blade_wave)
    set16(11, blade_base - blade_wave)
    set16(13, blade_base + blade_wave)
    set16(7,  0)
    set16(9,  0)
    set16(15, 0)
    set16(17, 0)

    # ── PostFX
    # Pixelate : fixe sur scènes 1-4, strobe sur scène 5
    if mot_idx == 4:
        dmx[22] = 2 if int(t * 8) % 2 == 0 else 0   # strobe ~8Hz
    else:
        dmx[22] = 2
    dmx[23] = 255
    dmx[24] = int(120 + 100*math.sin(t*0.7))
    dmx[27] = 255

    # ── Lettres — blackout des spots non utilisés d'abord
    for i in range(12):
        dmx[28 + i * 20 + 3] = 0

    for i, c in enumerate(mot):
        base  = 28 + i * 20
        phase = i * math.pi / 3.0

        breath = 1.0 + 0.18 * math.sin(t * 1.1)
        wave   = 0.22 * math.sin(t * 2.5 - phase)
        scale  = SCALE_PAN * (breath + wave)
        bounce = int(500 * math.sin(t * 2.0 - phase * 0.8))
        tilt_u = max(0, min(65535, Y_CENTER + bounce))

        hue = (t * 0.12 + i / len(mot)) % 1.0
        r, g, b = hsv(hue, 0.85 + 0.15*math.sin(t*0.7 + phase))
        sr, sg, sb = hsv((hue + 0.5) % 1.0)
        sw = int(max(0, 12 * abs(math.sin(t * 1.8 + phase))))
        sa = int(180 + 75 * math.sin(t * 1.3 + phase))

        dmx[base + 0] = r;  dmx[base + 1] = g;  dmx[base + 2] = b
        dmx[base + 3] = 255
        dmx[base + 4] = sw; dmx[base + 5] = sa
        dmx[base + 6] = sr; dmx[base + 7] = sg; dmx[base + 8] = sb
        set16(base + 9,  math.ceil(scale * 65535 / 1000))
        set16(base + 11, char_tilt(c))
        set16(base + 13, 0)
        set16(base + 15, pan_u[i])
        set16(base + 17, tilt_u)
        dmx[base + 19] = 2

    # ── Forme arrière-plan (spot 11, hors portée des lettres)
    bg_forme = 12 if mot_idx == 4 else 3   # cœur sur frame 5 "Martin VERT", triangle sinon
    bg_r     = (0, 0, 0) if mot_idx == 4 else (220, 0, 0)
    base_tri = 28 + 11 * 20
    rot_tri  = int((t * 60) % 360 * 65535 / 360)
    dmx[base_tri + 0] = bg_r[0]; dmx[base_tri + 1] = bg_r[1]; dmx[base_tri + 2] = bg_r[2]
    dmx[base_tri + 3] = 130
    dmx[base_tri + 4] = 0;   dmx[base_tri + 5] = 0
    bg_size = 55000 if mot_idx == 4 else 18000
    set16(base_tri + 9,  bg_size)
    set16(base_tri + 11, bg_size)
    set16(base_tri + 13, rot_tri)
    set16(base_tri + 15, 32767)
    set16(base_tri + 17, 32767)
    dmx[base_tri + 19] = bg_forme

    send()
    time.sleep(0.033)
