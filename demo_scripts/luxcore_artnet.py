#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LUXCORE DMX ENGINE — Utilitaires ArtNet partagés
=================================================
Fonctions communes à tous les scripts Python :
  set16, send, hsv, char_tilt, make_socket

Author: Martin Vert
"""

import math
import socket

PORT = 6454


def make_socket():
    """Crée et retourne un socket UDP."""
    return socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


def set16(dmx, idx, val):
    """Écrit une valeur 16-bit (0-65535) dans dmx[idx] (MSB) et dmx[idx+1] (LSB)."""
    val = max(0, min(65535, int(val)))
    dmx[idx]     = (val >> 8) & 0xFF
    dmx[idx + 1] = val & 0xFF


def send(sock, dmx, ip="127.0.0.1"):
    """Envoie dmx (liste d'octets) sous forme de paquet ArtNet UDP."""
    data = bytes(max(0, min(255, int(v))) for v in dmx)
    pkt = (b"Art-Net\x00"
           + (0x5000).to_bytes(2, 'little')
           + bytes([0, 14, 0, 0, 0, 0])
           + len(data).to_bytes(2, 'big')
           + data)
    sock.sendto(pkt, (ip, PORT))


def hsv(h, s=1.0, v=1.0):
    """h:0-1 → r,g,b 0-255"""
    h6 = (h % 1.0) * 6
    i  = int(h6) % 6
    f  = h6 - int(h6)
    p, q, tv = v*(1-s), v*(1-s*f), v*(1-s*(1-f))
    rgb = [(v,tv,p),(q,v,p),(p,v,tv),(p,q,v),(tv,p,v),(v,p,q)][i]
    return int(rgb[0]*255), int(rgb[1]*255), int(rgb[2]*255)


def char_tilt(c):
    """Caractère ASCII → tilt_16bit pour mode Texte (Processing: byte(size_tilt)).
    ceil() obligatoire : int() tronque et fait glisser vers le caractère précédent."""
    return math.ceil(ord(c) * 65535 / 1000)
