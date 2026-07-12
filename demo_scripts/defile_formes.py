#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LUXCORE DMX ENGINE - DÉFILÉ DES 14 FORMES
==========================================
Affiche chaque forme une par une, avec 7 spots arrangés,
fond blanc, blades encadrantes et couleur thématique.
Author: Martin Vert

Convention d'indexation DMX (base 0) :
  self.dmx[0..2]   = canaux DMX 1-3   (RGB fond)
  self.dmx[3..18]  = canaux DMX 4-19  (8 blades 16-bit)
  self.dmx[19]     = canal DMX 20     (blend mode global)
  self.dmx[20..31] = canaux DMX 21-32 (effets PostFX : + feedback/bloom/kaléido)
  self.dmx[32 + spot_id * 23 + offset] = parametre spot (canaux 33+)
"""

import time
import math
import sys
import luxcore_artnet as lxa
import artnet_text

# ── Identité de chaque forme ─────────────────────────────────────────────────
# blend : valeur DMX exacte — map(dmx, 0, 255, 1, 10) dans Processing
#   BLEND=0  ADD=29  LIGHTEST=114  DIFFERENCE=142  EXCLUSION=170  SCREEN=227
#   (SUBTRACT=57 DARKEST=85 MULTIPLY=199 REPLACE=255 — évités sur fond noir)
FORMES = [
    {"id": 0,  "nom": "Ellipse",    "r": 220, "g":  80, "b":  80, "blend":  29},  # ADD      → lueur rouge
    {"id": 1,  "nom": "Rectangle",  "r":  80, "g": 160, "b": 220, "blend":   0},  # BLEND    → propre
    {"id": 2,  "nom": "Texte",      "r": 180, "g":  60, "b": 200, "blend": 227},  # SCREEN   → violet lumineux
    {"id": 3,  "nom": "Triangle",   "r": 220, "g": 160, "b":  40, "blend": 142},  # DIFFERENCE → doré psyché
    {"id": 4,  "nom": "Pentagone",  "r":  60, "g": 200, "b": 120, "blend":   0},  # BLEND    → propre
    {"id": 5,  "nom": "Hexagone",   "r":  40, "g": 180, "b": 220, "blend":  29},  # ADD      → lueur cyan
    {"id": 6,  "nom": "Losange",    "r": 220, "g":  80, "b": 160, "blend": 170},  # EXCLUSION → rose alterné
    {"id": 7,  "nom": "Octogone",   "r": 100, "g": 100, "b": 220, "blend": 114},  # LIGHTEST → bleu max
    {"id": 8,  "nom": "Étoile",     "r": 240, "g": 200, "b":  40, "blend":  29},  # ADD      → étoile dorée
    {"id": 9,  "nom": "Croix",      "r": 220, "g":  60, "b":  60, "blend":   0},  # BLEND    → propre
    {"id": 10, "nom": "Flèche",     "r":  60, "g": 220, "b":  80, "blend": 227},  # SCREEN   → vert lumineux
    {"id": 11, "nom": "Cœur",       "r": 240, "g":  40, "b":  80, "blend":  29},  # ADD      → lueur rouge passion
    {"id": 12, "nom": "Segment",    "r": 180, "g": 255, "b": 255, "blend":  29, "duree": 15.0},  # ADD → lignes cyan lumineuses
    {"id": 13, "nom": "Rafale",     "r":  80, "g": 200, "b": 200, "blend": 227},  # SCREEN   → étoile 14 pointes
]

# ── 19 positions : 1 centre + 6 anneau intérieur + 12 anneau extérieur ───────
# Valeurs 16-bit (0-65535), centre = 32767
def positions_3_rings(r1=8000, r2=16000):
    pos = [(32767, 32767)]  # centre
    for i in range(6):
        angle = i * math.pi / 3
        pos.append((int(32767 + r1*math.cos(angle)), int(32767 + r1*math.sin(angle))))
    for i in range(12):
        angle = i * math.pi / 6
        pos.append((int(32767 + r2*math.cos(angle)), int(32767 + r2*math.sin(angle))))
    return pos

POSITIONS = positions_3_rings()

# Fixture unifiée : plus de famille vidéo dédiée — une « vidéo » est un spot en
# mode 14. Par convention la démo réserve les slots 48+ à ses panneaux vidéo pour
# ne pas écraser les 48 spots de formes. Lancer le moteur avec --spots >= 60.
VIDEO_FIXTURE_SLOT0 = 48         # 1er slot des panneaux vidéo de la démo (convention)
NUM_VIDEO_FIXTURES = 12          # panneaux vidéo simultanés (slots 48..59)
BG_FIXTURE_SLOT = 60             # fixture de FOND (aligné sur luxcore.constants.BG_FIXTURE_SLOT)

# Plage pixel totale calibrée empiriquement pour une fenêtre 1920px.
# Processing mappe 0-65535 sur la largeur réelle de la fenêtre ; cette valeur
# est à ajuster si la fenêtre est redimensionnée via le GUI (data/window_size.txt).
SCREEN_PX_RANGE = 2430


# ── Géométrie d'écran : offset pixel (depuis le centre) -> position 16-bit ────
# Le moteur mappe pan sur [-255-960, 255+960] et tilt sur [-255-540, 255+540].
# Les deux axes ont donc des échelles DIFFÉRENTES : on convertit chaque axe
# séparément pour que les cercles soient ronds et les grilles régulières.
_HALF_W, _HALF_H = 960, 540


def to_pan(dx):
    return max(0, min(65535, int((dx + 255 + _HALF_W) / (2 * (255 + _HALF_W)) * 65535)))


def to_tilt(dy):
    return max(0, min(65535, int((dy + 255 + _HALF_H) / (2 * (255 + _HALF_H)) * 65535)))


# Le moteur ré-échelonne les fixtures vidéo par VIDEO_SIZE_SCALE (=2.5) pour
# autoriser le plein écran ; on divise donc par 1000·2.5 = 2500 (rester synchro).
VIDEO_SIZE_SCALE = 2.5


def sz_px(px):
    """Largeur/hauteur vidéo en px -> valeur 16-bit (size_pan), compte tenu du
    ré-échelonnage moteur des fixtures vidéo."""
    return max(0, min(65535, int(px / (1000 * VIDEO_SIZE_SCALE) * 65535)))


def vspread(k, n):
    """Valeur du canal +22 pour répartir le panneau k (sur n) sur les vidéos du
    dossier : le moteur mappe 0-255 -> index. Panneaux voisins -> vidéos variées."""
    return int((k + 0.5) / max(1, n) * 256)


# ── Générateurs de dispositions SYMÉTRIQUES (offsets pixel depuis le centre) ──
def lay_ring(n, R, phase=0.0):
    """n points régulièrement espacés sur un cercle de rayon R."""
    return [(R * math.cos(2 * math.pi * k / n + phase),
             R * math.sin(2 * math.pi * k / n + phase)) for k in range(n)]


def lay_rings(specs, phase=0.0):
    """Anneaux concentriques (mandala). specs = [(n, R, phase_offset), ...]."""
    pts = []
    for (n, R, ph) in specs:
        pts += lay_ring(n, R, phase + ph)
    return pts


def lay_phyllo(n, scale, phase=0.0):
    """Spirale de phyllotaxie (tournesol) — angle d'or, densité naturelle."""
    ga = math.pi * (3 - math.sqrt(5))
    return [(scale * math.sqrt(k + 0.5) * math.cos(k * ga + phase),
             scale * math.sqrt(k + 0.5) * math.sin(k * ga + phase)) for k in range(n)]


def lay_rose(n, k, R, phase=0.0):
    """Points le long d'une rosace r = R·cos(k·θ) — symétrie à k (ou 2k) pétales."""
    pts = []
    for j in range(n):
        th = math.pi * j / n                 # un demi-tour : la rosace se referme
        r = R * math.cos(k * th)
        pts.append((r * math.cos(th + phase), r * math.sin(th + phase)))
    return pts


def lay_polygons(sides, layers, R0, dR, phase=0.0):
    """Polygones réguliers concentriques — symétrie d'ordre `sides`."""
    pts = []
    for L in range(layers):
        pts += lay_ring(sides, R0 + L * dR, phase + L * math.pi / sides)
    return pts


def lay_grid(cols, rows, sx, sy, rot=0.0):
    """Grille centrée, éventuellement tournée d'un angle rot (reste symétrique)."""
    ca, sa = math.cos(rot), math.sin(rot)
    pts = []
    for r in range(rows):
        for c in range(cols):
            x = (c - (cols - 1) / 2) * sx
            y = (r - (rows - 1) / 2) * sy
            pts.append((x * ca - y * sa, x * sa + y * ca))
    return pts


class DefileFormes:
    def __init__(self, ip="127.0.0.1"):
        self.ip = ip
        self.sock = lxa.make_socket()
        self.dmx = [0] * 1536  # 3 univers → 65 spots max (48 spots × 23ch = 1132 bytes)

    # ── Envoi ArtNet ─────────────────────────────────────────────────────────
    def send(self):
        lxa.send_multi(self.sock, self.dmx, self.ip)

    # ── Écriture helpers ─────────────────────────────────────────────────────
    def set16(self, idx, val):
        lxa.set16(self.dmx, idx, val)

    def set_spot(self, spot_id, r, g, b, alpha, sw, sa, sr, sg, sb,
                 size_pan, size_tilt, rot16, pan, tilt, mode,
                 enable=255, spot_blend=0, font=0):
        base = 32 + spot_id * 23
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
        self.dmx[base + 20] = enable
        self.dmx[base + 21] = spot_blend
        self.dmx[base + 22] = font

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

        # Effets off (y compris les PostFX ajoutés : feedback/bloom/kaléido)
        for i in range(20, 32):
            self.dmx[i] = 0

        # Nombre de spots actifs = 7
        self.dmx[27] = 0  # pas de canal "nb spots" ici, géré par le pool Processing

    # ── Rendu d'une forme pendant sa tranche de temps ────────────────────────
    def render_forme(self, forme, t_local, alpha_factor=1.0, duree=6.0):
        fid = forme["id"]
        r0, g0, b0 = forme["r"], forme["g"], forme["b"]

        # Fond noir quand les spots sont visibles
        self.dmx[0] = 0
        self.dmx[1] = 0
        self.dmx[2] = 0

        # Blend mode propre à la forme
        self.dmx[19] = forme["blend"]

        # Effets PostFX
        if fid == 12:
            self._segment_effects(t_local, duree)
        else:
            self.set_effects(t_local, duree)

        # Repartir d'une ardoise propre : tous les spots ET fixtures vidéo éteints,
        # puis on rallume seulement ceux de la disposition courante (évite les
        # résidus d'une forme à l'autre quand le nombre de spots change).
        self.blackout_spots(VIDEO_FIXTURE_SLOT0 + NUM_VIDEO_FIXTURES)

        # Fixtures vidéo présentes TOUT AU LONG du défilé (arrangement par forme)
        self._video_backdrop(fid, t_local, alpha_factor)

        # ── Mode spécial Segment : lignes arc-en-ciel, épaisseur dramatique ─────
        if fid == 12:
            N = len(POSITIONS)
            t = t_local
            for i in range(N):
                phase = i * 2 * math.pi / N

                # Arc-en-ciel : chaque ligne a sa propre teinte qui dérive lentement
                hue = (t * 0.06 + i / N) % 1.0
                r, g, b = lxa.hsv(hue, 1.0, 1.0)
                alpha = int(230 * alpha_factor)
                sa    = int(230 * alpha_factor)

                # Longueur : très longue + pulsation ample
                size_pan = int(max(8000, 58000 + 10000 * math.sin(t * 0.38 + phase * 0.7)))

                # ÉPAISSEUR : de fil (1px) à poutre (80px) — rythme propre à chaque ligne
                # size_tilt / 500.0 = épaisseur en pixels dans Processing
                thick = 0.5 + 0.5 * math.sin(t * (0.55 + i * 0.09) + phase)
                size_tilt = int(300 + 40000 * thick)  # ~0.6px → ~80px

                # Rotation : 3 groupes, vitesses variables avec accélération
                if i == 0:
                    rot = int((t * 10) % 360 * 65535 / 360)
                elif i <= 6:
                    speed = 22 + 10 * math.sin(t * 0.28 + i)
                    rot = int(((i - 1) * 30 + t * speed) % 360 * 65535 / 360)
                else:
                    speed = 38 + 14 * math.sin(t * 0.22 + i)
                    rot = int(((i - 7) * 15 - t * speed) % 360 * 65535 / 360)

                # Mouvement : orbites par groupe, amplitude importante
                if i <= 6:
                    # Centre + anneau intérieur : petite orbite rapide autour du centre
                    orb_r = int(3500 * abs(math.sin(t * 0.32 + phase)))
                    orb_a = t * 0.55 + phase
                    pan  = max(0, min(65535, 32767 + int(orb_r * math.cos(orb_a))))
                    tilt = max(0, min(65535, 32767 + int(orb_r * math.sin(orb_a))))
                else:
                    # Anneau extérieur : va-et-vient entre leur position et le centre
                    px0, py0 = POSITIONS[i]
                    pull = 0.15 + 0.2 * abs(math.sin(t * 0.25 + phase))
                    # Oscillation transversale supplémentaire
                    perp = int(2000 * math.sin(t * 0.5 + phase + math.pi / 2))
                    pan  = max(0, min(65535, int(32767 + (px0 - 32767) * pull) + perp))
                    tilt = max(0, min(65535, int(32767 + (py0 - 32767) * pull) + int(perp * 0.6)))

                self.set_spot(i, r, g, b, alpha, 0, sa, r, g, b,
                              size_pan, size_tilt, rot, pan, tilt, fid)
            return

        # ── Rendu générique : disposition SYMÉTRIQUE riche, propre à la forme ──
        positions = self._forme_positions(fid, t_local)
        N = len(positions)
        # Plus il y a de spots, plus ils sont fins (lisibilité de la symétrie)
        base_size = 13000 if N <= 24 else (9500 if N <= 38 else 7400)
        # Respiration radiale : même facteur pour TOUS -> la symétrie est préservée
        breath = 1.0 + 0.06 * math.sin(t_local * 1.2)

        for i, (dx, dy) in enumerate(positions):
            phase = i * 2 * math.pi / N

            # RGB fill : modulation douce autour de la teinte thématique
            r = int(max(0, min(255, r0 * (0.75 + 0.25 * math.sin(t_local * 0.8 + phase)))))
            g = int(max(0, min(255, g0 * (0.75 + 0.25 * math.sin(t_local * 0.9 + phase + 1)))))
            b = int(max(0, min(255, b0 * (0.75 + 0.25 * math.sin(t_local * 0.7 + phase + 2)))))

            alpha = int(210 * alpha_factor * (0.85 + 0.15 * math.sin(t_local * 1.1 + phase)))
            sw = int(max(0, 13 * abs(math.sin(t_local * 0.9 + phase))))
            sa = int(max(0, min(255, 120 + 120 * math.sin(t_local * 0.7 + phase + 1.5))))
            sr = int(max(0, min(255, (r * 0.4 + g * 0.6))))
            sg = int(max(0, min(255, (g * 0.4 + b * 0.6))))
            sb = int(max(0, min(255, (b * 0.4 + r * 0.6))))

            size_pan  = int(base_size + 2600 * math.sin(t_local * 0.6 + phase))
            size_tilt = int(base_size + 2600 * math.sin(t_local * 0.6 + phase + math.pi / 2))

            rot_speed = 45 if i % 2 == 0 else -30
            rot = int((t_local * rot_speed + i * 25) % 360 * 65535 / 360)

            pan  = to_pan(dx * breath)
            tilt = to_tilt(dy * breath)

            # Police : cycle temporel sur les 20 polices pour la forme Texte
            font_val = (int(t_local * 1.5 + i) % 20) * 256 // 20 if fid == 2 else 0
            en, sblend = self._creative_enable_blend(fid, i, t_local, phase, N)
            self.set_spot(i, r, g, b, alpha, sw, sa, sr, sg, sb,
                          size_pan, size_tilt, rot, pan, tilt, fid,
                          enable=en, spot_blend=sblend, font=font_val)

    # ── Disposition symétrique propre à chaque forme (offsets pixel) ──────────
    def _forme_positions(self, fid, t):
        """Retourne une liste d'offsets pixel (dx, dy), arrangement symétrique
        distinct par forme, en rotation lente pour la vie sans casser la symétrie."""
        ph = t * 0.14
        if fid == 0:      # Ellipse — mandala à 3 anneaux
            return lay_rings([(1, 0, 0), (8, 210, 0), (16, 410, 0)], ph)
        if fid == 1:      # Rectangle — grille 6×6 lentement tournée
            return lay_grid(6, 6, 150, 128, rot=ph * 0.4)
        if fid == 3:      # Triangle — triangles concentriques (symétrie 3)
            return lay_polygons(3, 4, 150, 108, ph)
        if fid == 4:      # Pentagone — pentagones concentriques (symétrie 5)
            return lay_polygons(5, 3, 165, 128, ph)
        if fid == 5:      # Hexagone — pavage hexagonal (symétrie 6)
            return lay_rings([(1, 0, 0), (6, 150, 0), (12, 300, 0), (18, 440, 0)], ph)
        if fid == 6:      # Losange — rosace k=2 (symétrie 4)
            return lay_rose(40, 2, 460, ph)
        if fid == 7:      # Octogone — octogones concentriques (symétrie 8)
            return lay_polygons(8, 3, 170, 128, ph)
        if fid == 8:      # Étoile — phyllotaxie (tournesol d'étoiles)
            return lay_phyllo(42, 74, ph)
        if fid == 9:      # Croix — anneaux 4-fold sur les axes
            return lay_rings([(1, 0, 0), (4, 170, 0), (4, 320, math.pi / 4),
                              (8, 470, 0)], ph)
        if fid == 10:     # Flèche — GRILLE plein écran (8×5) + rosace centrale
            grid = lay_grid(8, 5, 248, 230)      # 40 flèches, couvre tout l'écran
            rose = lay_rose(8, 5, 300, ph)       # + 8 de la rosace (déjà en place)
            return grid + rose                    # 48 spots (plafond du moteur)
        if fid == 11:     # Cœur — anneaux concentriques (symétrie miroir)
            return lay_rings([(1, 0, 0), (7, 200, 0), (14, 400, 0)], ph)
        if fid == 13:     # Rafale — spots disposés en rosace k=6 (constellation)
            return lay_rose(48, 6, 470, ph)
        # Texte (2) et défaut — anneau de lettres
        return lay_ring(26, 430, ph * 0.6)

    # ── Fixtures vidéo : un panneau texturé par la source vidéo ───────────────
    def _set_video(self, idx, dx, dy, w, rot_deg, alpha, blend=0, vsel=0):
        """Place la fixture vidéo `idx` (16:9) — largeur w px, centre (dx,dy).
        vsel (0-255) = canal +22 : choisit la vidéo du dossier (le moteur mappe
        vers l'index disponible). Répartir vsel entre panneaux -> vidéos variées."""
        if idx >= NUM_VIDEO_FIXTURES:
            return
        self.set_spot(VIDEO_FIXTURE_SLOT0 + idx, 255, 255, 255,
                      int(max(0, min(255, alpha))), 0, 0, 0, 0, 0,
                      sz_px(w), sz_px(w * 9.0 / 16.0),
                      int(rot_deg % 360 * 65535 / 360),
                      to_pan(dx), to_tilt(dy), 14, spot_blend=blend,
                      font=int(max(0, min(255, vsel))))

    def _set_shape_video(self, idx, shape, dx, dy, w, rot_deg, alpha, blend=0, vsel=0, h=None):
        """Panneau vidéo `idx` en FORME `shape` (mode 100+forme) : la vidéo prend la
        silhouette (étoile, hexagone…). Taille en px, échelle forme (plafond 1000 px)."""
        if idx >= NUM_VIDEO_FIXTURES:
            return
        if h is None:
            h = w

        def s16(px):
            return max(0, min(65535, int(max(0, min(1000, px)) / 1000 * 65535)))

        self.set_spot(VIDEO_FIXTURE_SLOT0 + idx, 255, 255, 255,
                      int(max(0, min(255, alpha))), 0, 0, 0, 0, 0,
                      s16(w), s16(h), int(rot_deg % 360 * 65535 / 360),
                      to_pan(dx), to_tilt(dy), 100 + int(shape), spot_blend=blend,
                      font=int(max(0, min(255, vsel))))

    def _set_bg_video(self, vsel=0, alpha=255, blend=0):
        """Fixture de FOND : vidéo plein écran DERRIÈRE tous les spots.
        vsel (+22) choisit la vidéo ; alpha permet de la fondre avec la couleur
        RGB de fond. Le moteur force le plein écran (taille/position ignorées)."""
        self.set_spot(BG_FIXTURE_SLOT, 255, 255, 255,
                      int(max(0, min(255, alpha))), 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 0, 14, spot_blend=blend,
                      font=int(max(0, min(255, vsel))))

    def _clear_bg_video(self):
        """Éteint la fixture de fond (hors plage des blackouts de spots)."""
        self.set_spot(BG_FIXTURE_SLOT, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                      0, 0, 0, 0, 0, 0, enable=0)

    # ── Décor vidéo présent en permanence — un preset symétrique par forme ────
    def _video_backdrop(self, fid, t, af):
        """6 arrangements vidéo symétriques (cyclés par forme) démontrant les
        possibilités du player : panneau héros, miroir, anneau (hexagones-vidéo),
        coins, grille, spirale (étoiles-vidéo). Rotation / pulsation / échelle animées.
        Les presets 2 et 5 utilisent la vidéo EN FORME (mode 100+forme)."""
        a0 = int(210 * af)
        preset = fid % 6

        if preset == 0:        # panneau central unique (héros) : rotation + respiration
            w = 680 + 60 * math.sin(t * 0.5)
            # héros = une vidéo différente à chaque occurrence du preset (formes 0/6/12)
            self._set_video(0, 0, 0, w, 6 * math.sin(t * 0.3), int(a0 * 0.95),
                            vsel=vspread(fid // 6, 3))

        elif preset == 1:      # paire miroir gauche/droite, contra-rotation
            for s, idx in ((-1, 0), (1, 1)):
                self._set_video(idx, s * 520, 30 * math.sin(t * 0.6), 470,
                                s * 10 * math.sin(t * 0.4), a0, vsel=vspread(idx, 2))

        elif preset == 2:      # anneau de 6 panneaux HEXAGONE-vidéo tournants (ADD)
            for k in range(6):
                a = 2 * math.pi * k / 6 + t * 0.35
                self._set_shape_video(k, 5, 470 * math.cos(a), 300 * math.sin(a), 340,
                                      math.degrees(a) + t * 20, int(a0 * 0.9), blend=29,
                                      vsel=vspread(k, 6))    # 5 = hexagone

        elif preset == 3:      # 4 coins miroir, pulsation synchronisée
            for k, (sx, sy) in enumerate(((-1, -1), (1, -1), (-1, 1), (1, 1))):
                pulse = 0.85 + 0.15 * math.sin(t * 2 + k)
                self._set_video(k, sx * 560, sy * 300, 430 * pulse,
                                sx * sy * 8 * math.sin(t * 0.5), a0, vsel=vspread(k, 4))

        elif preset == 4:      # grille 3×2 en vague d'opacité
            idx = 0
            for yy in (-250, 250):
                for xx in (-620, 0, 620):
                    pulse = 0.82 + 0.18 * math.sin(t * 2.5 + idx * 0.9)
                    self._set_video(idx, xx, yy, 380 * pulse, 0,
                                    int(a0 * (0.7 + 0.3 * math.sin(t * 1.5 + idx))),
                                    vsel=vspread(idx, 6))
                    idx += 1

        else:                  # preset 5 : spirale phyllotaxique de 8 ÉTOILES-vidéo (ADD)
            ga = math.pi * (3 - math.sqrt(5))
            for k in range(8):
                a = k * ga + t * 0.3
                rr = 70 * math.sqrt(k + 0.5)
                self._set_shape_video(k, 8, rr * math.cos(a), rr * math.sin(a) * 0.7,
                                      150 + 26 * k, math.degrees(a),
                                      int(a0 * 0.85), blend=29, vsel=vspread(k, 8))  # 8 = étoile

    def _video_fill(self, alpha=255, vsel=0):
        """Vidéo plein écran, sans couture : une seule fixture (ré-échelonnée par
        le moteur) légèrement plus grande que l'écran (1960×1102 > 1920×1080).
        vsel (+22) choisit la vidéo du dossier."""
        self._set_video(0, 0, 0, 1960, 0, alpha, vsel=vsel)

    # ── Enable et blend créatifs par forme ───────────────────────────────────
    def _creative_enable_blend(self, fid, i, t, phase, N):
        """Retourne (enable, spot_blend) selon la forme et le spot.
        Blend DMX : ADD=29  LIGHTEST=114  DIFFERENCE=142  EXCLUSION=170  MULTIPLY=199  SCREEN=227
        enable    : 0=off, 255=on"""
        en, sb = 255, 0  # sb=0 → utilise le blend global de la forme

        if fid == 0:    # Ellipse — ADD rouge : vague d'extinction + halos SCREEN
            en = 255 if math.sin(t * 2.5 - i * math.pi / N) > -0.45 else 0
            sb = 227 if i % 3 == 0 else 0           # 1 spot/3 en SCREEN

        elif fid == 1:  # Rectangle — BLEND bleu : scanner (1 spot off tournant) + DIFFERENCE
            en = 0 if int(t * 2.2) % N == i else 255
            sb = 142 if i % 4 == 0 else 0           # DIFFERENCE réparti dans l'espace (fixe)

        elif fid == 2:  # Texte — SCREEN violet : vague douce décalée + boost ADD spatial
            en = 255 if math.sin(t * 1.0 + i * 0.5) > -0.7 else 0   # vague lente, jamais tout noir
            sb = 29 if i % 3 == 0 else 0

        elif fid == 3:  # Triangle — DIFFERENCE doré : EXCLUSION alternée (spatiale)
            en = 255                                # plus de heartbeat -> aucun clignotement
            sb = 170 if i % 2 == 0 else 0           # alternance EXCLUSION / DIFFERENCE

        elif fid == 4:  # Pentagone — BLEND vert : vague sinusoïdale + ADD centre blazing
            en = 255 if math.sin(t * 1.1 - i * math.pi / N) > -0.3 else 0
            sb = 29 if i == 0 else 0                 # centre en ADD

        elif fid == 5:  # Hexagone — ADD cyan : inner/outer bascule + SCREEN outer
            grp = 0.0 if i <= 6 else math.pi
            en = 255 if math.sin(t * 1.3 + grp) > 0 else 0
            sb = 227 if i > 6 else 0                 # outer en SCREEN, inner en ADD

        elif fid == 6:  # Losange — EXCLUSION rose : spirale (vague lente) + DIFFERENCE spatial
            frac = (i / N - t * 0.28) % 1.0
            en = 255 if frac > 0.2 else 0           # spirale : chaque spot s'éteint 1× / ~3,5 s
            sb = 142 if i % 3 == 0 else 0           # DIFFERENCE réparti dans l'espace (fixe)

        elif fid == 7:  # Octogone — LIGHTEST bleu : breathe + burst ADD au sommet
            breathe = 0.5 + 0.5 * math.sin(t * 0.75 + phase * 0.25)
            en = 255 if breathe > 0.15 else 0
            sb = 29 if breathe > 0.88 else 0

        elif fid == 8:  # Étoile — ADD doré : anneau plein + SCREEN centre (plus de strobe)
            en = 255                                # outer ne strobe plus
            sb = 227 if i == 0 else 0                # halo SCREEN centre

        elif fid == 9:  # Croix — BLEND rouge : MULTIPLY inner (spatial, sans clignotement)
            en = 255                                # plus de bascule 2,8 Hz
            sb = 199 if i <= 6 else 0                # MULTIPLY sur le groupe interne (fixe)

        elif fid == 10: # Flèche — grille PEUPLÉE : toutes ON + éclairs ADD qui circulent lentement
            en = 255                                            # plus d'extinctions nerveuses
            sb = 29 if (i + int(t * 1.2)) % 5 == 0 else 0       # éclair ADD qui avance doucement

        elif fid == 11: # Cœur — ADD rouge passion : SCREEN glow (battement retiré)
            en = 255                                # plus de double battement -> pas de flash
            sb = 227 if i % 3 == 0 else 0

        elif fid == 13: # Rafale — SCREEN turquoise : révélation en balayage + LIGHTEST
            en = 255 if i <= (t * 0.7) % N else 0
            sb = 114 if i % 2 == 0 else 0            # alternance SCREEN / LIGHTEST

        return en, sb

    # ── Effets spéciaux pour le Segment ──────────────────────────────────────
    def _segment_effects(self, t, duree=15.0):
        """Timeline d'effets pour la forme Segment : sobel / pixelate / chromatic
        en séquence et parfois en simultané — sans blur qui noircit."""

        def bell(t, peak, width, max_val):
            x = (t - peak) / (width / 2)
            return int(max_val * max(0.0, 1.0 - x * x)) if abs(x) < 1.0 else 0

        def gate(t, start, end):
            return 255 if start <= t <= end else 0

        # Canaux 20-27 : blur off, tout le reste séquencé
        self.dmx[20] = 0   # blur size  — désactivé
        self.dmx[21] = 0   # blur sigma — désactivé

        # Pixelate : pic à 25% et à 75% (deux vagues)
        pix1 = bell(t, duree * 0.25, duree * 0.18, 200)
        pix2 = bell(t, duree * 0.75, duree * 0.16, 240)
        self.dmx[22] = max(pix1, pix2)

        # Sobel : ON entre 40%-55% et entre 85%-95%
        sobel = gate(t, duree * 0.40, duree * 0.55) or gate(t, duree * 0.85, duree * 0.95)
        self.dmx[23] = 255 if sobel else 0

        # RGB split : deux pics — l'un avant sobel, l'autre après
        self.dmx[24] = bell(t, duree * 0.33, duree * 0.18, 160) + \
                       bell(t, duree * 0.62, duree * 0.14, 120)

        # Saturation : légère poussée en milieu de séquence
        self.dmx[25] = bell(t, duree * 0.50, duree * 0.30, 140)
        self.dmx[26] = bell(t, duree * 0.52, duree * 0.24, 100)

        # Chromatic aberration : deux éclats courts
        chroma = gate(t, duree * 0.47, duree * 0.53) or gate(t, duree * 0.80, duree * 0.84)
        self.dmx[27] = 255 if chroma else 0

        # PostFX ajoutés : le segment qui balaie laisse une traînée + un halo
        self.dmx[28] = bell(t, duree * 0.50, duree * 0.60, 160)  # feedback
        self.dmx[29] = 70                                        # bloom : seuil
        self.dmx[30] = bell(t, duree * 0.40, duree * 0.50, 180)  # bloom : intensité
        self.dmx[31] = 0                                         # kaléido OFF

    # ── Timeline effets PostFX ────────────────────────────────────────────────
    def set_effects(self, t, duree=6.0):
        """Anime tous les paramètres d'effets en séquence sur la durée d'une forme.
        Chaque effet a son pic à un moment distinct — enveloppe en cloche (parabole)."""

        def bell(t, peak, width, max_val):
            """Cloche parabolique centrée sur peak, largeur width."""
            x = (t - peak) / (width / 2)
            return int(max_val * max(0.0, 1.0 - x * x)) if abs(x) < 1.0 else 0

        def gate(t, start, end):
            """Bistable ON entre start et end."""
            return 255 if start <= t <= end else 0

        # 8 effets répartis sur la durée, séquencés sans se chevaucher trop
        self.dmx[20] = bell(t, duree * 0.13, duree * 0.22, 100)  # blur size
        self.dmx[21] = bell(t, duree * 0.17, duree * 0.22,  60)  # blur sigma (décalé)
        self.dmx[22] = bell(t, duree * 0.38, duree * 0.22, 220)  # pixelate
        self.dmx[23] = gate(t, duree * 0.52, duree * 0.64)       # sobel ON
        self.dmx[24] = bell(t, duree * 0.62, duree * 0.22, 110)  # rgb split
        self.dmx[25] = bell(t, duree * 0.76, duree * 0.24, 230)  # saturation A
        self.dmx[26] = bell(t, duree * 0.80, duree * 0.20, 160)  # saturation B
        self.dmx[27] = gate(t, duree * 0.88, duree * 0.97)       # chromatic aberration ON
        # PostFX ajoutés : bloom sur chaque forme (halo), formes lisibles -> pas de
        # feedback ni kaléido dans le défilé (mis à 0 explicitement, aucune fuite)
        self.dmx[28] = 0                                         # feedback OFF
        self.dmx[29] = 70                                        # bloom : seuil
        self.dmx[30] = bell(t, duree * 0.50, duree * 0.42, 190)  # bloom : intensité
        self.dmx[31] = 0                                         # kaléido OFF

        # Blades : ouvertes (0) pendant la phase pixelate — unfade progressif
        pix_norm = bell(t, duree * 0.38, duree * 0.22, 255) / 255.0
        if pix_norm > 0.0:
            margin = int((4000 + 1500 * math.sin(t * 0.4)) * (1.0 - pix_norm))
            for ch in [3, 5, 7, 9, 11, 13, 15, 17]:
                self.set16(ch, margin)

    # ── Intro : blades, couleurs de fond, blur ───────────────────────────────
    def demo_intro(self, duree=20.0):
        """Démo des blades, couleurs de fond et blur — sans spots."""
        print("  ✦  Intro — blades / couleurs / blur")

        # Palette de fond : séquences de couleurs expressives
        couleurs_fond = [
            (  0,   0,   0),   # noir
            (180,   0,   0),   # rouge profond
            (  0,   0, 180),   # bleu nuit
            (  0, 140,  80),   # vert émeraude
            (180,   0, 120),   # magenta
            (255, 200,   0),   # or
            (255, 255, 255),   # blanc
        ]

        t0 = time.time()
        try:
            while True:
                t = time.time() - t0
                if t >= duree:
                    break

                p = t / duree  # 0.0 → 1.0

                # ── Couleur de fond : interpolation douce entre palettes
                n = len(couleurs_fond)
                idx_f = (t / duree) * (n - 1)
                i0 = int(idx_f)
                i1 = min(i0 + 1, n - 1)
                frac = idx_f - i0
                r0, g0, b0 = couleurs_fond[i0]
                r1, g1, b1 = couleurs_fond[i1]
                self.dmx[0] = int(r0 + (r1 - r0) * frac)
                self.dmx[1] = int(g0 + (g1 - g0) * frac)
                self.dmx[2] = int(b0 + (b1 - b0) * frac)

                # ── Blades : choreographie en 3 actes
                if p < 0.33:
                    # Acte 1 — ouverture progressive depuis les 4 coins
                    ap = p / 0.33
                    depth = int(20000 * ap * (0.8 + 0.2 * math.sin(t * 2.1)))
                    tilt  = int(6000 * math.sin(t * 1.3))
                    self.set16(3,  depth - tilt)   # A1 top-gauche
                    self.set16(5,  depth + tilt)   # A2 top-droite
                    self.set16(11, depth + tilt)   # C1 bas-gauche
                    self.set16(13, depth - tilt)   # C2 bas-droite
                    self.set16(7,  depth - tilt)   # B1 droite-haut
                    self.set16(9,  depth + tilt)   # B2 droite-bas
                    self.set16(15, depth + tilt)   # D1 gauche-haut
                    self.set16(17, depth - tilt)   # D2 gauche-bas

                elif p < 0.66:
                    # Acte 2 — blades qui dansent indépendamment
                    tp = t
                    self.set16(3,  int(16000 + 14000 * math.sin(tp * 0.7)))
                    self.set16(5,  int(16000 + 14000 * math.sin(tp * 0.7 + 1.0)))
                    self.set16(11, int(14000 + 12000 * math.sin(tp * 0.9 + 2.0)))
                    self.set16(13, int(14000 + 12000 * math.sin(tp * 0.9 + 0.5)))
                    self.set16(7,  int(12000 + 10000 * math.sin(tp * 1.1 + 1.5)))
                    self.set16(9,  int(12000 + 10000 * math.sin(tp * 1.1 + 3.0)))
                    self.set16(15, int(10000 + 10000 * math.sin(tp * 0.8 + 0.8)))
                    self.set16(17, int(10000 + 10000 * math.sin(tp * 0.8 + 2.5)))

                else:
                    # Acte 3 — fermeture progressive (blades se referment)
                    ap = (p - 0.66) / 0.34
                    depth = int(20000 * (1.0 - ap))
                    tilt  = int(4000 * math.sin(t * 1.8))
                    self.set16(3,  max(0, depth + tilt))
                    self.set16(5,  max(0, depth - tilt))
                    self.set16(11, max(0, depth - tilt))
                    self.set16(13, max(0, depth + tilt))
                    self.set16(7,  max(0, depth + tilt))
                    self.set16(9,  max(0, depth - tilt))
                    self.set16(15, max(0, depth - tilt))
                    self.set16(17, max(0, depth + tilt))

                # ── Blur : monte en acte 2, redescend en acte 3
                if p < 0.33:
                    blur = 0
                elif p < 0.66:
                    blur = int(80 * math.sin((p - 0.33) / 0.33 * math.pi))
                else:
                    blur = int(30 * (1.0 - (p - 0.66) / 0.34))
                self.dmx[20] = blur          # blur size
                self.dmx[21] = blur // 2     # blur sigma

                # Blend mode et autres effets off (PostFX ajoutés compris)
                self.dmx[19] = 0
                for i in range(22, 32):
                    self.dmx[i] = 0

                # Spots (formes) invisibles — le fond est fait par la vidéo
                self.blackout_spots(VIDEO_FIXTURE_SLOT0 + NUM_VIDEO_FIXTURES)

                # ── Fond VIDÉO plein écran : les couteaux viennent le rogner et le
                #    révéler. Cycle des 3 vidéos du dossier en 3 tiers de l'intro.
                self._video_fill(255, vsel=vspread(min(2, int(p * 3)), 3))

                self.send()
                time.sleep(0.02)

        except KeyboardInterrupt:
            raise

        # Transition vers le défilé : fade vers noir, blades off, blur off
        for i in range(20):
            self.dmx[0] = max(0, self.dmx[0] - 13)
            self.dmx[1] = max(0, self.dmx[1] - 13)
            self.dmx[2] = max(0, self.dmx[2] - 13)
            self.dmx[20] = max(0, self.dmx[20] - 4)
            self.dmx[21] = max(0, self.dmx[21] - 2)
            self.blackout_spots()
            self.send()
            time.sleep(0.02)

        self.dmx[0] = 0
        self.dmx[1] = 0
        self.dmx[2] = 0
        self.dmx[20] = 0
        self.dmx[21] = 0
        for i in range(3, 19):
            self.dmx[i] = 0

    # ── Blackout (spots alpha = 0) ────────────────────────────────────────────
    def blackout_spots(self, n=None):
        if n is None:
            n = len(POSITIONS)
        for i in range(n):
            base = 32 + i * 23
            self.dmx[base + 3] = 0  # alpha = 0

    # ── Utilitaires finale ────────────────────────────────────────────────────
    @staticmethod
    def hsv(h, s=1.0, v=1.0): return lxa.hsv(h, s, v)

    @staticmethod
    def char_tilt(c): return lxa.char_tilt(c)

    def word_positions(self, word, spacing_px=108, y_16=32767):
        """Positions 16-bit centrées pour les lettres d'un mot (écran ~1920px)."""
        px_to_u = 65535 / SCREEN_PX_RANGE
        step = int(spacing_px * px_to_u)
        start = int(32767 - (len(word) - 1) * step / 2)
        return [(start + i * step, y_16) for i in range(len(word))]

    # ── FINALE ────────────────────────────────────────────────────────────────
    def demo_finale(self, duree=90.0):
        """5 actes, 48 spots sur 3 univers ArtNet, tous les paramètres, texte dynamique."""
        N = 48   # 32 + 48 × 23 = 1136 octets → 3 univers nécessaires (dmx = 1536)
        WORDS = ["LUXCORE", "MARTIN", "ART DMX"]

        print("\n  🌟  FINALE — L'APOTHÉOSE (5 actes)")

        t0 = time.time()
        try:
            while True:
                t = time.time() - t0
                if t >= duree:
                    break
                p = t / duree  # 0→1

                # Fond noir par défaut
                self.dmx[0] = self.dmx[1] = self.dmx[2] = 0
                # PostFX ajoutés : réinit chaque frame -> chaque acte réactive au besoin
                self.dmx[28] = self.dmx[30] = self.dmx[31] = 0  # feedback/bloom/kaléido OFF
                self.dmx[29] = 60                               # bloom : seuil par défaut

                # ─────────────────────────────────────
                # ACTE 1 — EXPLOSION  (p: 0→0.17)
                # Burst radial depuis le centre, toutes formes
                # ─────────────────────────────────────
                if p < 0.17:
                    tp = p / 0.17
                    self.dmx[19] = 29   # ADD
                    self.dmx[20] = int(80 * (1 - tp))
                    self.dmx[21] = int(40 * (1 - tp))
                    for ch in range(22, 28): self.dmx[ch] = 0
                    self.dmx[29] = 55; self.dmx[30] = int(70 + 170 * tp)  # bloom du burst
                    for ch in [3,5,7,9,11,13,15,17]: self.set16(ch, 0)

                    for i in range(N):
                        angle = 2*math.pi*i/N
                        radius = int(tp * 20000 * (0.5 + 0.5*math.sin(angle*3 + t*2)))
                        pan  = max(0, min(65535, int(32767 + radius*math.cos(angle))))
                        tilt = max(0, min(65535, int(32767 + radius*math.sin(angle))))
                        r, g, b = self.hsv((i/N + t*0.15) % 1.0)
                        sz = int(5000 + 5000*tp + 3000*math.sin(t*3 + i))
                        rot = int((t*120 + i*18) % 360 * 65535/360)
                        alpha = min(255, int(tp * 500))
                        sw = int(20*abs(math.sin(t*4 + i*0.3)))
                        font_a1 = (int(t * 2 + i * 3) % 20) * 256 // 20
                        self.set_spot(i, r, g, b, alpha, sw, 200,
                                      255-r, 255-g, 255-b,
                                      sz, sz, rot, pan, tilt, i % 14, font=font_a1)

                # ─────────────────────────────────────
                # ACTE 2 — CONSTELLATION  (p: 0.17→0.38)
                # Lissajous, épicycloïdes, hypotrochoides
                # ─────────────────────────────────────
                elif p < 0.38:
                    tp = (p - 0.17) / 0.21
                    self.dmx[19] = 29   # ADD
                    self.dmx[20] = int(50 * math.sin(tp * math.pi))
                    self.dmx[21] = int(25 * math.sin(tp * math.pi))
                    self.dmx[22] = 0
                    self.dmx[23] = 0
                    self.dmx[24] = int(90 * math.sin(tp * math.pi * 2))
                    self.dmx[25] = int(160 * tp)
                    self.dmx[26] = int(110 * tp)
                    self.dmx[27] = 0
                    self.dmx[28] = 170        # feedback : traînées le long des courbes
                    for ch in [3,5,7,9,11,13,15,17]: self.set16(ch, 0)

                    # Groupe 1 : 8 étoiles sur courbe de Lissajous (∞ déphasé)
                    R1 = int(13000 + 2000*math.sin(tp * math.pi))
                    for i in range(8):
                        a = 2*math.pi*i/8 + t*0.28
                        pan  = max(0, min(65535, int(32767 + R1*math.cos(a))))
                        tilt = max(0, min(65535, int(32767 + R1*math.sin(2*a + t*0.13))))
                        r, g, b = self.hsv(0.14 + 0.04*math.sin(t*0.5 + i))
                        sz = int(11000 + 2500*math.sin(t*1.1 + i))
                        rot = int((t*55 + i*45) % 360 * 65535/360)
                        self.set_spot(i, r, g, b, 230, 10, 200,
                                      200, 160, 0, sz, sz, rot, pan, tilt, 8)

                    # Groupe 2 : 10 formes variées sur épicycloïde (spirographe externe)
                    R2, r2 = 8500, 3200
                    for i in range(10):
                        theta = 2*math.pi*i/10 - t*0.42
                        phi   = (R2/r2) * theta
                        pan  = max(0, min(65535, int(32767 + (R2+r2)*math.cos(theta) - r2*math.cos(phi))))
                        tilt = max(0, min(65535, int(32767 + (R2+r2)*math.sin(theta) - r2*math.sin(phi))))
                        r, g, b = self.hsv((i/10 + t*0.07) % 1.0)
                        sz = int(7000 + 1800*math.sin(t*0.9 + i))
                        rot = int((t*-45 + i*36) % 360 * 65535/360)
                        fid = [0,3,4,5,6,7,9,10,11,12][i]
                        self.set_spot(8+i, r, g, b, 210, 6, 160,
                                      255-r, 255-g, 255-b,
                                      sz, int(sz*1.2), rot, pan, tilt, fid)

                    # Groupe 3 : 6 ellipses sur hypotrochide (rose à 4 pétales)
                    R3, r3 = 5500, 1600
                    for i in range(6):
                        theta = 2*math.pi*i/6 + t*0.95
                        phi   = (R3/r3) * theta
                        pan  = max(0, min(65535, int(32767 + (R3-r3)*math.cos(theta) + r3*math.cos(phi))))
                        tilt = max(0, min(65535, int(32767 + (R3-r3)*math.sin(theta) - r3*math.sin(phi))))
                        r, g, b = self.hsv((i/6 + t*0.2) % 1.0)
                        sz = int(3200 + 1200*math.sin(t*2.2 + i))
                        rot = int((t*130 + i*60) % 360 * 65535/360)
                        self.set_spot(18+i, r, g, b, 190, 3, 130,
                                      r//3, g//3, b//3,
                                      sz, int(sz*1.6), rot, pan, tilt, 0)

                # ─────────────────────────────────────
                # ACTE 3 — MOTS  (p: 0.38→0.60)
                # Lettres écrites une à une, spots orbitent autour
                # ─────────────────────────────────────
                elif p < 0.60:
                    tp = (p - 0.38) / 0.22
                    wi = min(int(tp * len(WORDS)), len(WORDS)-1)
                    word = WORDS[wi]
                    wtp = (tp * len(WORDS)) - wi   # 0→1 dans le mot

                    self.dmx[19] = 227  # SCREEN
                    self.dmx[20] = int(25 * math.sin(tp * math.pi))
                    self.dmx[21] = int(12 * math.sin(tp * math.pi))
                    self.dmx[22] = 0
                    self.dmx[23] = 0
                    self.dmx[24] = int(70 + 80*math.sin(t*0.9))
                    self.dmx[25] = int(210 + 45*math.sin(t*0.5))
                    self.dmx[26] = int(160 + 60*math.sin(t*0.7))
                    self.dmx[27] = 255   # chromatic ON
                    self.dmx[29] = 95; self.dmx[30] = 110   # bloom léger (texte lisible)
                    bv = int(9000 + 4500*math.sin(t*0.35))
                    bh = int(7000 + 3500*math.sin(t*0.42 + 1.0))
                    for ch in [3,5,11,13]: self.set16(ch, bv)
                    for ch in [7,9,15,17]: self.set16(ch, bh)

                    LT_COLORS = [
                        (255,80,80),(255,190,0),(80,255,80),(0,190,255),
                        (220,0,255),(255,255,60),(80,255,220),(255,120,0),
                    ]
                    pos = self.word_positions(word, spacing_px=115, y_16=31000)
                    n_vis = int(wtp * len(word) * 2.5) + 1

                    for idx, c in enumerate(word):
                        if c == ' ':
                            # Spot invisible pour l'espace
                            base = 32 + idx * 23
                            self.dmx[base + 3] = 0
                            continue
                        alpha_l = min(255, max(0, (n_vis - idx) * 255))
                        pan_u, tilt_u = pos[idx]
                        # sz_pan contrôle l'échelle du texte (Processing: scale -size_pan/80)
                        sz_pan = int(13000 + 2500*math.sin(t*1.4 + idx*0.6))
                        sz_tilt = self.char_tilt(c)
                        rot = int((t*15*(1 if idx%2==0 else -1) + idx*12) % 360 * 65535/360)
                        tc = LT_COLORS[idx % len(LT_COLORS)]
                        tp_u = max(0, min(65535, tilt_u + int(1800*math.sin(t*1.1 + idx*0.5))))
                        # Police différente par lettre, change à chaque mot
                        font_lt = ((wi * 7 + idx * 3) % 20) * 256 // 20
                        self.set_spot(idx, tc[0], tc[1], tc[2], alpha_l,
                                      10, 220, 255-tc[0], 255-tc[1], 255-tc[2],
                                      sz_pan, sz_tilt, rot, pan_u, tp_u, 2, font=font_lt)

                    # Spots géométriques qui orbitent autour des lettres
                    n_text = len(word)
                    for i in range(n_text, N):
                        si = i - n_text
                        lc = pos[si % n_text]
                        a = 2*math.pi*si/(N-n_text) + t*(0.9 + si*0.012)
                        radius = int(5500 + 3000*math.sin(t*0.7 + si))
                        pan  = max(0, min(65535, lc[0] + int(radius*math.cos(a))))
                        tilt = max(0, min(65535, lc[1] + int(radius*math.sin(a))))
                        r, g, b = self.hsv((si/(N-n_text) + t*0.12) % 1.0)
                        sz = int(3800 + 1800*math.sin(t*2.2 + si))
                        rot = int((t*90 + si*22) % 360 * 65535/360)
                        self.set_spot(i, r, g, b, 190, 5, 160,
                                      255-r, 255-g, 255-b,
                                      sz, sz, rot, pan, tilt, si % 14)

                # ─────────────────────────────────────
                # ACTE 4 — VORTEX  (p: 0.60→0.80)
                # Spirale d'Archimède + tous les PostFX + blades se ferment
                # ─────────────────────────────────────
                elif p < 0.80:
                    tp = (p - 0.60) / 0.20
                    self.dmx[19] = 170  # EXCLUSION
                    self.dmx[20] = int(100 * math.sin(tp * math.pi))
                    self.dmx[21] = int(50  * math.sin(tp * math.pi))
                    self.dmx[22] = int(90  * tp)
                    self.dmx[23] = 255 if tp > 0.25 else 0
                    self.dmx[24] = int(160 + 95*math.sin(t*1.7))
                    self.dmx[25] = 255
                    self.dmx[26] = 210
                    self.dmx[27] = 255
                    # VORTEX = tous les PostFX : feedback (spirale rémanente) + kaléido
                    self.dmx[28] = 190
                    self.dmx[31] = 6 + int(6 * tp)          # branches qui augmentent
                    close = int(tp * 22000)
                    sw_b = int(3000 * math.sin(t * 2.1))
                    self.set16(3,  max(0, close + sw_b))
                    self.set16(5,  max(0, close - sw_b))
                    self.set16(11, max(0, close - sw_b))
                    self.set16(13, max(0, close + sw_b))
                    for ch in [7,9,15,17]:
                        self.set16(ch, max(0, int(close*0.7 + 2500*math.sin(t*2.3))))

                    for i in range(N):
                        s = ((i/N) + tp * 1.8) % 1.0
                        angle = s * 7*math.pi + t*2.8
                        radius = int(s * 21000 * (1 - tp*0.45))
                        pan  = max(0, min(65535, int(32767 + radius*math.cos(angle))))
                        tilt = max(0, min(65535, int(32767 + radius*math.sin(angle))))
                        r, g, b = self.hsv((s + t*0.35) % 1.0)
                        sz = int((3500 + 9000*s) * (0.7 + 0.3*math.sin(t*3.5 + i)))
                        rot = int((t*(180 + i*2) + i*8) % 360 * 65535/360)
                        alpha = int(210 + 45*math.sin(t*2.3 + i))
                        sw = int(14*abs(math.sin(t*4.5 + i*0.4)))
                        fid = (i + int(t*4)) % 14   # forme change !
                        font_a4 = (int(t * 1.8 + i * 3) % 20) * 256 // 20
                        self.set_spot(i, r, g, b, alpha, sw, 220,
                                      255-r, 255-g, 255-b,
                                      sz, int(sz*1.35), rot, pan, tilt, fid, font=font_a4)

                # ─────────────────────────────────────
                # ACTE 5 — SUPERNOVA  (p: 0.80→1.0)
                # Explosion radiale + tout à fond + extinction progressive
                # ─────────────────────────────────────
                else:
                    tp = (p - 0.80) / 0.20
                    fade = max(0.0, 1.0 - tp * 1.25)
                    self.dmx[19] = 29   # ADD
                    self.dmx[20] = int(130 * fade)
                    self.dmx[21] = int(65  * fade)
                    self.dmx[22] = int(180 * math.sin(tp*math.pi) * fade)
                    self.dmx[23] = 255 if tp < 0.65 else 0
                    self.dmx[24] = int(230 * fade)
                    self.dmx[25] = int(255 * fade)
                    self.dmx[26] = int(200 * fade)
                    self.dmx[27] = 255 if tp < 0.7 else 0
                    # apothéose : bloom fort + feedback, qui s'éteignent avec la scène
                    self.dmx[29] = 50; self.dmx[30] = int(230 * fade)
                    self.dmx[28] = int(150 * fade)
                    # Blades se claquent à 0
                    for ch in [3,5,7,9,11,13,15,17]:
                        self.set16(ch, max(0, int(18000 * (1 - tp/0.55))))

                    for i in range(N):
                        angle = 2*math.pi*i/N + t*0.25
                        explode = int(tp * 30000 * (0.5 + 0.5*math.sin(angle*5 + t)))
                        pan  = max(0, min(65535, int(32767 + explode*math.cos(angle))))
                        tilt = max(0, min(65535, int(32767 + explode*math.sin(angle))))
                        sz = int((14000 + 6000*math.sin(t*6+i)) * (1 - tp*0.75))
                        h = (i/N + t*0.6) % 1.0
                        sat = min(1.0, tp/0.25)
                        r, g, b = self.hsv(h, sat, 1.0)
                        alpha = int(255 * max(0.0, 1.0 - tp*1.3))
                        rot = int((t*(220 + i*3) + i*18) % 360 * 65535/360)
                        sw = int(25 * max(0.0, 1.0 - tp*1.6))
                        font_a5 = (int(t * 2.5 + i * 3) % 20) * 256 // 20
                        self.set_spot(i, r, g, b, alpha, sw, int(220*fade),
                                      255, 255, 255,
                                      sz, sz, rot, pan, tilt, i % 14, font=font_a5)

                self.send()
                time.sleep(0.016)

        except KeyboardInterrupt:
            raise

        # Extinction finale
        for _ in range(40):
            for i in range(N):
                base = 32 + i * 23
                self.dmx[base + 3] = max(0, self.dmx[base + 3] - 7)
            for ch in range(32):
                self.dmx[ch] = max(0, self.dmx[ch] - 7)
            self.send()
            time.sleep(0.025)
        self.dmx = [0] * 1536
        self.send()

    # ── Boucle principale ────────────────────────────────────────────────────
    def run(self, duree_par_forme=6.0, transition=0.6, duree_intro=20.0,
            duree_text=30.0):
        # La vidéo est désormais présente partout (fond des couteaux + décor de
        # chaque forme) : la scène vidéo dédiée a été retirée de la séquence.
        total = (duree_text + duree_intro
                 + len(FORMES) * (duree_par_forme + transition) + 180)
        print("🎭 LUXCORE - DÉFILÉ DES 14 FORMES + FINALE (48 spots / 2 univers)")
        print("=" * 48)
        print(f"   Texte intro : {duree_text:.0f}s (artnet_text)")
        print(f"   Intro       : {duree_intro:.0f}s (blades / vidéo de fond / blur)")
        print(f"   {len(FORMES)} formes × {duree_par_forme}s + {transition}s transition")
        print("   Finale      : 180s (5 actes, 48 spots / 2 univers)")
        print(f"   Durée totale : {total:.0f}s")
        print(f"   Cible       : {self.ip}:6454")
        print()

        fps_count = 0
        fps_t0 = time.time()

        try:
            while True:
                print("  ✦  Texte intro")
                artnet_text.run(duree=duree_text, ip=self.ip, sock=self.sock)
                print()

                self.demo_intro(duree_intro)
                print()

                for forme in FORMES:
                    duree_forme = forme.get("duree", duree_par_forme)
                    print(f"  ▶  Forme {forme['id']:2d} — {forme['nom']}")

                    # --- Affichage principal ---
                    t0 = time.time()
                    while True:
                        t_local = time.time() - t0
                        if t_local >= duree_forme:
                            break

                        # Fade in (0.4s) et fade out (0.4s)
                        if t_local < 0.4:
                            af = t_local / 0.4
                        elif t_local > duree_forme - 0.4:
                            af = (duree_forme - t_local) / 0.4
                        else:
                            af = 1.0

                        self.set_base(t_local)
                        self.render_forme(forme, t_local, af, duree_forme)
                        self.send()

                        fps_count += 1
                        time.sleep(0.02)

                    # --- Transition (blackout court, fond noir, effets off) ---
                    t0 = time.time()
                    while time.time() - t0 < transition:
                        self.set_base(0)
                        self.dmx[0] = 0
                        self.dmx[1] = 0
                        self.dmx[2] = 0
                        for i in range(20, 28):
                            self.dmx[i] = 0
                        self.blackout_spots()
                        self.send()
                        time.sleep(0.02)

                # --- FINALE après les 14 formes ---
                print()
                self.demo_finale(duree=180.0)

                print()
                print("  🔄  Redémarrage...")
                print()

        except KeyboardInterrupt:
            print("\n  ⏹  Interrompu")

        # Reset final
        self.dmx = [0] * 1536
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
