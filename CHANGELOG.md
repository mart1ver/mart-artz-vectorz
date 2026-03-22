# CHANGELOG — LuxCore DMX Engine

---

## v1.0 — Show complet en boucle infinie (2026-03-22)

- `defile_formes.py` tourne en boucle infinie (Ctrl+C pour quitter)
- 19 spots en 3 anneaux : 1 centre + 6 inner + 12 outer
- Forme Segment : 19 lignes arc-en-ciel, epaisseur 0.6-80px, 3 groupes de rotation, effets dedies (sobel/pixelate/chromatic sans blur)
- Enable et blend mode creatifs par forme : strobe, scanner, heartbeat, spirale, chase (14 strategies distinctes)
- 20 polices TTF en cache, cycling temporel sur l'ensemble de la piece
- Finale 5 actes : Explosion / Constellation / Mots / Vortex / Supernova (48 spots)
- `artnet_text.py` refactore en module importable + standalone

---

## v0.2 — Multi-univers, 23 canaux par spot, nouvelles formes (2026-03-18)

- 3 canaux par spot : enable/disable (+20), blend mode individuel (+21), font index (+22)
- `number_of_parameters_by_spots` : 20 → 23
- Capacite : 21 spots/univers, 43 sur 2, 65 sur 3 univers
- Forme Segment (mode 13) : ligne ouverte, size_pan = longueur, size_tilt/500 = epaisseur px
- ArtPollReply implemente (~239 octets)
- LUT blend mode fixe (10 valeurs exactes)
- Module Python partage `luxcore_artnet.py`
- Remote git GitHub, `.gitignore` complet, GDTF minimal produit

---

## v0.1 — Renommage LuxCore DMX Engine (2025-09-05)

- Renommage officiel : Martz Artz Verctorz → LuxCore DMX Engine (vote AG, 6 agents sur 8)
- Moteur de visualisation DMX/ArtNet temps reel en Processing
- Reception ArtNet UDP port 6454, parsing dmx_data[]
- Pipeline : fond RGB, 8 blades 16-bit, blend mode global, 6 effets PostFX, N spots via SpotData
- 14 formes geometriques vectorielles (ellipse a coeur)
- Scripts Python de controle : `artnet_text.py`, `lettre_a.py`, `system_validation.py`
