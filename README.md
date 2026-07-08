# LuxCore DMX Engine

Moteur de visualisation DMX/ArtNet temps réel : reçoit des paquets ArtNet UDP et
génère des formes géométriques vectorielles (et de la vidéo) animées en temps réel.

**Auteur :** Martin Vert

Le moteur principal est le **portage Python / moderngl** (OpenGL + sortie **NDI**).
Le code Processing d'origine est archivé dans [`docs/processing/`](docs/processing/).

---

## Démarrage rapide

```bash
# 1. moteur : aperçu écran + sortie NDI "LuxCore", piloté par ArtNet
python_port/.venv/bin/python python_port/run_engine.py --preview --spots 60 --duration 0

# 2. envoyer de l'ArtNet (127.0.0.1:6454) — p.ex. le show complet
python3 demo_scripts/defile_formes.py       # défilé + finale, en boucle (Ctrl+C)
python3 demo_scripts/artnet_text.py         # typographie animée
```

Aperçu : **`g`** = plein écran (curseur masqué + veille inhibée), **`h`** = menu.
Détails moteur, architecture et tests : [`python_port/README.md`](python_port/README.md).

---

## Structure

| Dossier | Contenu |
|---|---|
| `python_port/` | **moteur principal** (lib `luxcore/`, `run_engine.py`, tests) |
| `demo_scripts/` | scripts Python qui pilotent le moteur par ArtNet (shows, tests) |
| `data/` | polices (`fonts/`), vidéos (`videos/`), GUI |
| `docs/` | documentation ; `docs/processing/` = sources Processing archivées |
| `gdtf/` | fichiers GDTF pour consoles (MA3 / Hog4 / QLC+) |

---

## Structure DMX

- **28 canaux de base** : fond RGB, 8 blades 16-bit, blend mode global, 6 effets PostFX.
- **23 canaux par fixture** : RGB, alpha, stroke, taille/rotation/position 16-bit,
  mode (forme), enable, blend individuel, sélecteur police/vidéo.
- **Fixture unifiée** : une seule sorte de fixture. Le **mode +19 = 14 (VIDEO)**
  transforme n'importe quelle fixture en panneau vidéo (sélection de la vidéo du
  dossier via `+22`, échelle plein écran).
- **Fixture de fond** (slot réservé 60) : vidéo plein écran derrière tous les spots.
- **Protocole** : ArtNet UDP port 6454, cible par défaut `127.0.0.1`.

## Les 14 formes (canal +19)

`0` Ellipse · `1` Rectangle · `2` Texte · `3` Triangle · `4` Pentagone ·
`5` Hexagone · `6` Losange · `7` Octogone · `8` Étoile · `9` Croix ·
`10` Flèche · `11` Cœur · `12` Segment · `13` Fleur · `14` **Vidéo**
