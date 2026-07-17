"""Panneau de contrôle imgui — config + status du moteur.

`draw_gui(state, status)` lit/écrit le dict `state` partagé avec la boucle :
  Réglages runtime :
    state["spots"]           : int  — nombre de fixtures rendues
    state["effects"]         : bool — post-effets activés
  Réglages ArtNet (appliqués À CHAUD via le bouton « Appliquer ArtNet ») :
    state["artnet_ip"]       : str  — IP de l'interface de réception ("0.0.0.0" = toutes)
    state["start_universe"]  : int  — 1er univers du patch
    state["start_addr"]      : int  — 1re adresse DMX (1-based)
  Réglages au DÉMARRAGE (appliqués via « Redémarrer moteur » = relance du process) :
    state["width"], state["height"] : int — résolution de rendu
    state["ndi_ip"]          : str  — interface d'émission NDI ("" = toutes, best-effort)
  Fourni par la boucle :
    state["interfaces"]      : list[(nom, ip)] — cartes réseau détectées
  Drapeaux (mis à True au clic, consommés par la boucle) :
    state["restart_artnet"], state["apply_artnet"], state["restart_engine"],
    state["save_config"]
"""
from __future__ import annotations

from imgui_bundle import imgui

from . import appconfig
from . import constants as C

# largeur des champs numériques
_W = 120.0


def _iface_items(interfaces):
    """Libellés « nom (ip) » pour un combo d'interfaces."""
    return [f"{name} ({ip})" for name, ip in interfaces]


def _index_of_ip(interfaces, ip, default=0):
    for i, (_name, iip) in enumerate(interfaces):
        if iip == ip:
            return i
    return default


def draw_gui(state: dict, status: dict) -> None:
    imgui.begin("LuxCore DMX Engine")
    interfaces = state.get("interfaces", [("Toutes les interfaces", "0.0.0.0")])

    # ── Runtime ──────────────────────────────────────────────────────────────
    imgui.separator_text("runtime")
    changed, v = imgui.slider_int("Nb. de fixtures", state["spots"], 0, 64)
    if changed:
        state["spots"] = v
    changed, v = imgui.checkbox("Post-effets", state["effects"])
    if changed:
        state["effects"] = v

    # ── ArtNet (appliqué à chaud) ────────────────────────────────────────────
    imgui.separator_text("ArtNet (à chaud)")
    items = _iface_items(interfaces)
    cur = _index_of_ip(interfaces, state["artnet_ip"], 0)
    imgui.set_next_item_width(220)
    changed, idx = imgui.combo("Carte réception", cur, items)
    if changed:
        state["artnet_ip"] = interfaces[idx][1]
    imgui.set_next_item_width(_W)
    changed, v = imgui.input_int("Univers départ", state["start_universe"])
    if changed:
        state["start_universe"] = max(0, min(255, v))
    imgui.set_next_item_width(_W)
    changed, v = imgui.input_int("Adresse départ", state["start_addr"])
    if changed:
        state["start_addr"] = max(1, min(512, v))

    # Position DMX réelle (univers, adresse) du 1er spot et du fond, pour patcher
    su, sa = state["start_universe"], state["start_addr"]
    spot_u, spot_a = C.patch_position(C.spot_base_addr(0), su, sa)
    bg_u, bg_a = C.patch_position(C.bg_fixture_base_addr(), su, sa)
    imgui.text_disabled(f"1er spot : univers {spot_u}, adresse {spot_a}")
    imgui.text_disabled(f"Fond     : univers {bg_u}, adresse {bg_a}")

    if imgui.button("Appliquer ArtNet"):
        state["apply_artnet"] = True

    # ── Démarrage (nécessite un redémarrage du moteur) ───────────────────────
    imgui.separator_text("démarrage (redémarrage requis)")
    # résolution : combo de préréglages + champs libres
    res_items = [f"{w}x{h}" for w, h in appconfig.RESOLUTIONS] + ["personnalisé"]
    cur_res = next((i for i, (w, h) in enumerate(appconfig.RESOLUTIONS)
                    if w == state["width"] and h == state["height"]), len(appconfig.RESOLUTIONS))
    imgui.set_next_item_width(160)
    changed, idx = imgui.combo("Résolution", cur_res, res_items)
    if changed and idx < len(appconfig.RESOLUTIONS):
        state["width"], state["height"] = appconfig.RESOLUTIONS[idx]
    imgui.set_next_item_width(_W)
    changed, v = imgui.input_int("Largeur", state["width"])
    if changed:
        state["width"] = max(64, min(7680, v))
    imgui.set_next_item_width(_W)
    changed, v = imgui.input_int("Hauteur", state["height"])
    if changed:
        state["height"] = max(64, min(4320, v))
    # carte NDI (best-effort)
    ndi_items = _iface_items(interfaces)
    cur_ndi = _index_of_ip(interfaces, state["ndi_ip"], 0) if state["ndi_ip"] else 0
    imgui.set_next_item_width(220)
    changed, idx = imgui.combo("Carte NDI", cur_ndi, ndi_items)
    if changed:
        # index 0 = « Toutes les interfaces » -> "" (toutes), sinon l'IP
        state["ndi_ip"] = "" if idx == 0 else interfaces[idx][1]
    if imgui.button("Redémarrer moteur"):
        state["restart_engine"] = True

    imgui.separator()
    if imgui.button("Sauver config"):
        state["save_config"] = True

    # ── Status ───────────────────────────────────────────────────────────────
    imgui.separator_text("status")
    imgui.text(f"FPS        : {status['fps']:.1f}")
    imgui.text(f"ArtNet     : {status['packets']} paquets")
    imgui.text(f"Univers vu : {status['universe']}")
    imgui.text(f"NDI        : {status['ndi']}")
    imgui.text(f"Résolution : {status['res']}")
    imgui.text(f"Blend      : {status['blend']}")

    imgui.separator_text("raccourcis")
    imgui.text("h : masquer ce menu   ·   g : plein écran")

    imgui.end()
