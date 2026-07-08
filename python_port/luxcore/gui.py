"""Panneau de contrôle imgui — équivalent du GUI LazyGui (gui_functions.pde).

Reprend l'esprit du GUI Processing : dossier `config` (nb de spots, univers,
restart ArtNet) + dossier `status` (usage, blend mode). Adapté au moteur Python
(fps, paquets ArtNet, source NDI, bypass des post-effets).

`draw_gui(state, status)` lit/écrit le dict `state` partagé avec la boucle :
  state["spots"]           : int  — nombre de fixtures rendues (mode 14 = vidéo)
  state["effects"]         : bool — post-effets activés
  state["restart_artnet"]  : bool — mis à True au clic (consommé par la boucle)
"""
from __future__ import annotations

from imgui_bundle import imgui


def draw_gui(state: dict, status: dict) -> None:
    imgui.begin("LuxCore DMX Engine")

    imgui.separator_text("config")
    changed, v = imgui.slider_int("Nb. de fixtures", state["spots"], 0, 64)
    if changed:
        state["spots"] = v
    changed, v = imgui.checkbox("Post-effets", state["effects"])
    if changed:
        state["effects"] = v
    if imgui.button("Restart ArtNet"):
        state["restart_artnet"] = True

    imgui.separator_text("status")
    imgui.text(f"FPS        : {status['fps']:.1f}")
    imgui.text(f"ArtNet     : {status['packets']} paquets")
    imgui.text(f"Univers vu : {status['universe']}")
    imgui.text(f"NDI        : {status['ndi']}")
    imgui.text(f"Résolution : {status['res']}")
    imgui.text(f"Blend      : {status['blend']}")

    imgui.separator_text("raccourcis")
    imgui.text("h : masquer ce menu")
    imgui.text("g : plein écran")

    imgui.end()
