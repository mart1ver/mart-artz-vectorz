"""Configuration persistée du moteur (JSON) — pilotée par le menu.

Regroupe les réglages choisis dans le menu et mémorisés d'un lancement à l'autre :
résolution, cartes réseau (ArtNet / NDI), point de départ ArtNet (univers +
adresse), plus les réglages déjà exposés (nb de fixtures, nom NDI, fps).

`load()` fusionne le fichier sur les valeurs par défaut et **valide/borne** chaque
champ (une config corrompue ne casse jamais le démarrage). `save()` écrit le JSON.
"""
from __future__ import annotations

import json
import os

DEFAULTS = {
    "width": 1920,
    "height": 1080,
    "fps": 60,
    "spots": 60,
    "name": "LuxCore",          # nom de la source NDI
    "artnet_ip": "0.0.0.0",     # interface de réception ArtNet ("0.0.0.0" = toutes)
    "ndi_ip": "",               # interface d'émission NDI ("" = toutes, best-effort)
    "start_universe": 0,        # 1er univers ArtNet du patch (0-based)
    "start_addr": 1,            # 1re adresse DMX dans cet univers (1-based)
}

# Résolutions proposées dans le menu (le champ reste libre si l'on veut autre chose)
RESOLUTIONS = [
    (1280, 720), (1920, 1080), (2560, 1440), (3840, 2160),
    (1080, 1920), (1024, 768), (800, 600),
]


def default_path() -> str:
    """Chemin du fichier de config (respecte XDG_CONFIG_HOME)."""
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return os.path.join(base, "luxcore", "config.json")


def _validate(cfg: dict) -> dict:
    out = dict(DEFAULTS)
    out.update({k: v for k, v in cfg.items() if k in DEFAULTS})
    out["width"] = max(64, min(7680, int(out["width"])))
    out["height"] = max(64, min(4320, int(out["height"])))
    out["fps"] = max(1, min(240, int(out["fps"])))
    out["spots"] = max(0, min(64, int(out["spots"])))
    out["start_universe"] = max(0, min(255, int(out["start_universe"])))
    out["start_addr"] = max(1, min(512, int(out["start_addr"])))
    out["name"] = str(out["name"]) or "LuxCore"
    out["artnet_ip"] = str(out["artnet_ip"]) or "0.0.0.0"
    out["ndi_ip"] = str(out["ndi_ip"])
    return out


def load(path: str | None = None) -> dict:
    """Config validée : fichier fusionné sur les défauts (défauts seuls si absent
    ou illisible)."""
    path = path or default_path()
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError("config n'est pas un objet")
        return _validate(data)
    except (OSError, ValueError, json.JSONDecodeError):
        return dict(DEFAULTS)


def save(cfg: dict, path: str | None = None) -> None:
    """Écrit la config validée (crée le dossier au besoin)."""
    path = path or default_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(_validate(cfg), f, indent=2, ensure_ascii=False)
