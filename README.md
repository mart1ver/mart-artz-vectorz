# LuxCore DMX Engine

Moteur de visualisation DMX/ArtNet temps réel en Processing.
Reçoit des paquets ArtNet UDP et génère des formes géométriques vectorielles animées en temps réel.

**Auteur :** Martin Vert

---

## Prérequis

**Processing 4** avec ces bibliothèques (Sketch → Import Library → Add Library) :
- `LazyGui` (com.krab.lazy)
- `ArtNet for Processing` (ch.bildspur.artnet)
- `PostFX for Processing` (ch.bildspur.postfx)

**Python 3** pour les scripts de contrôle :
```bash
pip install python-osc  # non requis — les scripts utilisent uniquement socket
```

---

## Lancement en 3 étapes

**1. Lancer LuxCore dans Processing**
```
Ouvrir martz_artz_verctorz.pde → Ctrl+R
```

**2. Configurer le nombre de spots dans le GUI**
```
Appuyer sur G pour afficher le GUI → config → Nb. of spots
```

**3. Lancer un script Python**
```bash
python3 demo_scripts/defile_formes.py    # show complet ~5 min
python3 demo_scripts/artnet_text.py      # animation typographique (Ctrl+C pour quitter)
python3 demo_scripts/lettre_a.py         # test affichage single char
```

---

## Documentation

| Fichier | Contenu |
|---|---|
| `docs/DEMO_INSTRUCTIONS.txt` | Guide opérationnel des scripts |
| `docs/RECOMMANDATIONS_AG_2026.md` | Audit technique complet (8 agents) |
| `CLAUDE.md` | Architecture complète, mapping DMX, encodages |
| `z_fixture_definition.pde` | Référence DMX canal par canal |
| `gdtf/` | Fichiers GDTF pour consoles MA3/Hog4/QLC+ |

---

## Capacité DMX

- **28 canaux de base** : fond RGB, 8 blades 16-bit, blend mode, effets PostFX
- **20 canaux par spot** : RGB, alpha, stroke, taille/rotation/position 16-bit, mode (15 formes)
- **24 spots maximum** dans un univers de 512 octets
- **Protocole** : ArtNet UDP port 6454, cible par défaut `127.0.0.1`
