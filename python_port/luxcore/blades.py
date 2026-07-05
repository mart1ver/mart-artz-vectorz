"""Blades (couteaux de cadrage) — porté 1:1 de do_blades (draw_functions.pde).

4 quads noirs opaques (A haut, B droite, C bas, D gauche), chacun avec une arête
intérieure inclinable pilotée par 2 valeurs 16-bit. Sommets en pixels ABSOLUS
(origine haut-gauche). Dessinés après les spots (et, à terme, après les effets).
"""
from __future__ import annotations

import numpy as np

from .dmx import pmap


def blade_quads(blades_16: list[int], width: int, height: int) -> list[np.ndarray]:
    """blades_16 = [A1,A2,B1,B2,C1,C2,D1,D2]. Renvoie 4 quads (float32 plats,
    4 sommets chacun, TRIANGLE_FAN). Un blade à (0,0) est dégénéré -> rien."""
    A1, A2, B1, B2, C1, C2, D1, D2 = blades_16
    W, H = float(width), float(height)

    A = [(0, 0), (W, 0),
         (W, pmap(A2, 0, 65535, 0, H)), (0, pmap(A1, 0, 65535, 0, H))]
    B = [(W, 0), (W, H),
         (pmap(B2, 0, 65535, W, 0), H), (pmap(B1, 0, 65535, W, 0), 0)]
    C = [(0, H), (0, pmap(C1, 0, 65535, H, 0)),
         (W, pmap(C2, 0, 65535, H, 0)), (W, H)]
    D = [(0, H), (pmap(D2, 0, 65535, 0, W), H),
         (pmap(D1, 0, 65535, 0, W), 0), (0, 0)]
    return [np.array(q, dtype="f4").reshape(-1) for q in (A, B, C, D)]


def blade_is_active(blades_16: list[int], index: int) -> bool:
    """Un blade masque quelque chose seulement si l'une de ses 2 valeurs > 0."""
    v1, v2 = blades_16[index * 2], blades_16[index * 2 + 1]
    return v1 > 0 or v2 > 0
