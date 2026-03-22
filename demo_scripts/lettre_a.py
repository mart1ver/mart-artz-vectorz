#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LUXCORE — Affiche un 'a' noir sur fond blanc.
Author: Martin Vert
"""

import time
import signal
import sys
import math
import luxcore_artnet as lxa

IP  = "127.0.0.1"
sock = lxa.make_socket()
dmx  = [0] * 512

def set16(idx, val): lxa.set16(dmx, idx, val)
def send(): lxa.send(sock, dmx, IP)

def blackout():
    global dmx
    dmx = [0] * 512
    send()

# ── Fond blanc ────────────────────────────────────────────────────────────────
dmx[0] = 255   # R fond
dmx[1] = 255   # G fond
dmx[2] = 255   # B fond

# ── Blend mode BLEND (0) — rendu normal sur fond blanc ───────────────────────
dmx[19] = 0

# ── Blades ouvertes (à 0 = pas de découpe) ───────────────────────────────────
for ch in [3, 5, 7, 9, 11, 13, 15, 17]:
    set16(ch, 0)

# ── Spot 0 — lettre 'a' noire, centré ────────────────────────────────────────
BASE = 28  # spot 0

# Fill : noir
dmx[BASE + 0] = 0    # R
dmx[BASE + 1] = 0    # G
dmx[BASE + 2] = 0    # B
dmx[BASE + 3] = 255  # alpha

# Stroke : désactivé
dmx[BASE + 4] = 0    # stroke weight
dmx[BASE + 5] = 0    # stroke alpha

# Taille : size_pan contrôle l'échelle du texte (Processing: scale -size_pan/80)
#          size_tilt encode le caractère ASCII — byte('a') = 97
SCALE_PAN  = 200                           # → scale ≈ 2.5× (lisible)
CHAR_ASCII = ord('a')                      # 97

set16(BASE + 9,  math.ceil(SCALE_PAN  * 65535 / 1000))  # size_pan
set16(BASE + 11, math.ceil(CHAR_ASCII * 65535 / 1000))  # size_tilt → char 'a'

# Rotation : nulle
set16(BASE + 13, 0)

# Position : centre écran (32767, 32767)
set16(BASE + 15, 32767)  # pan
set16(BASE + 17, 32767)  # tilt

# Mode : 2 = Texte
dmx[BASE + 19] = 2
dmx[BASE + 20] = 255  # enable

# ── Boucle d'envoi ────────────────────────────────────────────────────────────
def on_exit(sig, frame):
    print("\n  Extinction...")
    blackout()
    sys.exit(0)

signal.signal(signal.SIGINT, on_exit)

print("🔤 Affichage 'a' noir sur fond blanc — Ctrl+C pour quitter")
while True:
    send()
    time.sleep(0.05)
