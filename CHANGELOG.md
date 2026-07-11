# CHANGELOG — LuxCore DMX Engine

---

## v2.3 — Démo « Video Show » : 100 % des fonctions vidéo (2026-07)

- Nouveau script `demo_scripts/video_show.py` : 8 scènes couvrant **toutes** les
  capacités vidéo — plein écran + sélection de source (canal +22), fixture de FOND,
  panneaux flottants (compositing/alpha), mur/mosaïque multi-sources, **désync**
  (écho de frames retardées entre panneaux d'une même source), mouvement /
  rotation / échelle, blend par panneau (ADD/SCREEN/DIFFERENCE), PostFX sur vidéo
  (bloom/feedback/kaléido/pixelate/rgb split/chromatic) et un finale kaléido mur.
- Flicker-safe (fondus doux, mouvements continus). `python3 video_show.py [ip] [n_vidéos]`.

---

## v2.2 — Confort visuel : suppression des clignotements (2026-07)

- **Anti-flicker généralisé** sur les deux démos (confort + sécurité photosensible) :
  fini les strobes plein écran et les bascules bistables au rythme.
- Nouvel utilitaire KINETIC `swell()` : respiration cosinus **avec plancher**
  (la lumière pompe en continu, ne retombe jamais au noir) — remplace `env` là où
  ça claquait.
- KINETIC : la scène « Strobe » devient « **Symétrie** » (champ kaléidoscopique qui
  respire) ; suppression des bascules sobel/chroma par temps, des throbs à la
  double-croche, et de la chase trop nerveuse (passée en 8e). Phase glitch
  sobel/pixelate à valeurs **constantes**.
- DÉFILÉ : les stratégies par forme ne strobent plus (Texte ~5 Hz, Étoile ~7 Hz,
  Croix ~2,8 Hz, heartbeats Triangle/Cœur) — remplacées par des vagues lentes ou
  des motifs spatiaux fixes ; flips de blend plein champ passés en répartition
  spatiale.

---

## v2.1 — Nouveaux PostFX : feedback, bloom, kaléidoscope (2026-07)

- **3 post-effets plein écran** ajoutés (ping-pong FBO) :
  - **Feedback / trails** : traînées lumineuses persistantes (FBO d'historique).
  - **Bloom** : bright-pass + flou + additif, seuil et intensité séparés.
  - **Kaléidoscope** : symétrie radiale à N branches (2-24).
- **Bloc de base 28 → 32 canaux** : canaux 29 (feedback), 30 (bloom seuil),
  31 (bloom intensité), 32 (kaléido). Les spots démarrent à l'offset 32.
  Capacité : 20 fixtures/univers. Ordre pipeline :
  `feedback → kaléido → pixelate → sobel → rgb split → saturation → bloom → chromatic`.
- **Démos** intègrent les effets : KINETIC (un effet dosé par scène) et le DÉFILÉ
  (bloom par forme, feedback+halo sur le Segment, un effet marquant par acte du finale).
- Tests : +2 (décodage des nouveaux canaux, bloc de base à 32) — 54 au total.

---

## v2.0 — Portage Python / moderngl + NDI (2026-07)

- Nouveau moteur principal : **portage Python / moderngl** (OpenGL) avec **sortie NDI**,
  dans `python_port/`. Sources Processing d'origine archivées dans `docs/processing/`.
- **14 formes** denses : forme « Plus » retirée (doublon de la Croix), renumérotation.
  Remplissage par triangulation ear-clip (flèche/cœur concaves corrects).
- **Fixture unifiée** : plus de famille vidéo dédiée. Le mode +19 = 14 (VIDEO) transforme
  toute fixture en panneau vidéo (sélection de la vidéo du dossier via +22, échelle plein écran).
- **Vidéo** : dossier `data/videos/`, sélection par ArtNet, désynchronisation multi-panneaux,
  **fixture de fond** (slot 60) pour une vidéo plein écran derrière les spots.
- Aperçu : plein écran `g` (curseur masqué + veille inhibée via systemd-inhibit), menu `h`.
- Défilé enrichi : positions symétriques par forme, décor vidéo permanent, finale 5 actes.
- 45 tests (décodage, géométrie, GL, effets, polices). Ménage : root rangé, code mort retiré.

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
