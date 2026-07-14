# LuxCore DMX Engine

Moteur de visualisation **DMX / ArtNet temps réel** : reçoit des paquets ArtNet UDP et
génère des formes géométriques vectorielles (et de la vidéo) animées, avec sortie
**NDI**.

**Auteur :** Martin Vert

Le moteur principal est le **portage Python / moderngl** (OpenGL + NDI). Le code
Processing d'origine est archivé dans [`docs/processing/`](docs/processing/).

---

## Démarrage rapide

```bash
# 1. moteur : aperçu écran + sortie NDI "LuxCore", piloté par ArtNet
python_port/.venv/bin/python python_port/run_engine.py --preview --spots 60 --duration 0

# 2. envoyer de l'ArtNet (127.0.0.1:6454) — p.ex. le show complet
python3 demo_scripts/defile_formes.py       # défilé + finale, en boucle (Ctrl+C)
python3 demo_scripts/video_show.py          # démo vidéo (9 scènes)
```

Aperçu : **`g`** = plein écran (curseur masqué + veille inhibée), **`h`** = menu.
Installation détaillée du moteur : [`python_port/README.md`](python_port/README.md).

---

## Capacités

- **14 formes** vectorielles (ellipse, texte, cœur, rafale…) + **vidéo**, avec contour,
  et un mode **forme remplie par la vidéo**.
- **9 post-effets** plein écran : blur, pixelate, sobel, rgb split, saturation,
  chromatic, feedback, bloom, kaléidoscope.
- **8 blades** de cadrage 16-bit, **fond** colorisé ou vidéo, **20 polices** TTF.
- Sortie **NDI** (UYVY 4:2:2) visible dans OBS / vMix / Resolume.

---

## Documentation

| Page | Contenu |
|---|---|
| [docs/PROTOCOLE_DMX.md](docs/PROTOCOLE_DMX.md) | **référence** DMX/ArtNet : canaux, formes, blend, encodages |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | pipeline de rendu, NDI, vidéo, modules |
| [docs/DEMOS.md](docs/DEMOS.md) | guide des scripts de démonstration |
| [docs/GDTF.md](docs/GDTF.md) | fixtures GDTF pour consoles |
| [CHANGELOG.md](CHANGELOG.md) | historique des versions |
| [MANIFESTO.md](MANIFESTO.md) | manifeste artistique |

---

## Structure du dépôt

| Dossier | Contenu |
|---|---|
| `python_port/` | **moteur principal** (lib `luxcore/`, `run_engine.py`, tests) |
| `demo_scripts/` | scripts Python qui pilotent le moteur par ArtNet |
| `data/` | polices (`fonts/`), vidéos (`videos/`), GUI |
| `docs/` | documentation ; `docs/processing/` = sources Processing archivées |
| `gdtf/` | fixtures GDTF (grandMA / Hog / QLC+) |

---

## Structure DMX (résumé)

- **32 canaux de base** : fond RGB, 8 blades 16-bit, blend global, 9 PostFX.
- **23 canaux par fixture** : RGB, alpha, stroke, taille/rotation/position 16-bit, mode
  (forme), enable, blend individuel, sélecteur police/vidéo. Adresse = `32 + spot_id × 23`.
- **Fixture unifiée** : le mode `+19 = 14` (VIDEO) transforme toute fixture en panneau
  vidéo ; **fixture de fond** au slot 60 = vidéo plein écran derrière tout.
- **Protocole** : ArtNet UDP port 6454, cible `127.0.0.1`.

Détail complet et exact : **[docs/PROTOCOLE_DMX.md](docs/PROTOCOLE_DMX.md)**.
