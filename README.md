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

**Python 3** pour les scripts de contrôle — aucune dépendance externe (socket standard uniquement).

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
python3 demo_scripts/defile_formes.py      # show complet en boucle infinie (Ctrl+C pour quitter)
python3 demo_scripts/artnet_text.py        # animation typographique (boucle infinie, Ctrl+C)
python3 demo_scripts/lettre_a.py           # test affichage single char
python3 demo_scripts/system_validation.py  # validation connexion et performances
```

---

## Documentation

| Fichier | Contenu |
|---|---|
| `docs/PRESENTATION_DEMO.md` | Architecture DMX complète, mapping canal par canal |
| `docs/RECOMMANDATIONS_AG_2026.md` | Audit technique + roadmap (AG 2026-03-18) |
| `CLAUDE.md` | Instructions de développement, encodages, conventions |
| `z_fixture_definition.pde` | Référence DMX canal par canal (code Processing) |
| `gdtf/` | Fichiers GDTF/QXF pour consoles MA3/Hog4/QLC+ |

---

## Capacité DMX

- **28 canaux de base** : fond RGB, 8 blades 16-bit, blend mode, 6 effets PostFX
- **23 canaux par spot** : RGB, alpha, stroke, taille/rotation/position 16-bit, mode, enable, blend individuel, font index
- **43 spots** sur 2 univers ArtNet · **65 spots** sur 3 univers
- **Protocole** : ArtNet UDP port 6454, cible par défaut `127.0.0.1`

## Les 15 formes

`0` Ellipse · `1` Rectangle · `2` Texte · `3` Triangle · `4` Pentagone ·
`5` Hexagone · `6` Losange · `7` Octogone · `8` Etoile · `9` Croix ·
`10` Fleche · `11` Plus · `12` Coeur · `13` Segment · `14` Fleur

## Polices (mode Texte, canal +22 par spot)

20 polices TTF dans `data/fonts/` :
Audiowide · BebasNeue · Cinzel · Comfortaa-Bold · DejaVuSans · DejaVuSans-Bold ·
DejaVuSansMono · DejaVuSerif · Exo2-Bold · Montserrat-Bold · Orbitron · Oswald-Bold ·
Pacifico · PoiretOne · PressStart2P · Raleway-ExtraBold · Raleway-Light ·
Righteous · RobotoBold · SpaceMono-Bold
