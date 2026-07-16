# CHANGELOG — LuxCore DMX Engine

---

## v2.8 — Contrôle de lecture vidéo par spot (2026-07)

- **Playhead virtuel par spot** : chaque spot vidéo contrôle sa propre lecture —
  **point de départ (in)**, **vitesse** (0.25×..4×, 128≈1×), **play / pause / stop**,
  **loop / once / ping-pong**, **sens** (avant/arrière), **point de fin (out)**,
  **groupe de sync** (playhead partagé) et **strobe/hold**.
- **Nouveaux canaux** (mode vidéo 14 et 100-113) : les canaux fill (+0..+2) et
  stroke (+4..+6), inutiles en vidéo, sont réinterprétés en transport — **+0**
  vitesse, **+1** in, **+2** flags, **+4** out, **+5** sync, **+6** strobe. Bloc
  23 canaux et capacité (20 fixtures/univers) **inchangés**. Défauts à 0 = lecture
  1× en boucle → **contenu DMX existant compatible**. Contrepartie : plus de contour
  sur les spots forme+vidéo (canaux stroke réutilisés).
- **Moteur — décode-une-fois** : `VideoClip` décode chaque clip **entièrement en
  cache RAM** au démarrage (remplace le décodeur continu `VideoDecoder`, supprimé).
  Coût CPU permanent nul en lecture, lecture déterministe ; RAM ≈ 270 Mo/clip de 10 s
  à 640×360. Textures par slot (upload de la frame courante), groupes de sync partagés.
- **`video_show.py`** : 2 nouvelles scènes (**Écho** — départs décalés ; **Transport**
  — 4 modes côte à côte), helpers transport (`vid_flags`, `spd`, `**tr`). 10 scènes.
- **Correctifs rétro-compat** : `defile_formes.py` mettait fill=255 sur ses panneaux
  vidéo (→ 4× arrière avec le nouveau mapping) — remis à 0 (play 1× loop).
- **Tests** : `test_video.py` (cache) + 3 tests transport dans `test_dmx.py`.

---

## v2.7 — Retrait de la désynchronisation vidéo (2026-07)

- **Désync vidéo supprimée** : l'anneau de 16 frames par source (`_VID_RING`) est
  remplacé par **une seule texture par source** (dernière frame décodée). Plus de
  frames retardées ni d'« écho temporel » entre panneaux d'une même vidéo.
  `_draw_video` / `_draw_shape_video` / `_draw_bg_video` échantillonnent la texture
  courante ; `render()` n'a plus à calculer de délais (`ord`/`n_vid` retirés).
- **`video_show.py`** : scène « Désync (écho) » retirée — 8 scènes au lieu de 9.
- **Bonus VRAM** : une texture au lieu de 16 par source.
- **Manifeste** : retrait de la description détaillée du spectacle (garde vision +
  instrument technique).

---

## v2.6 — Documentation carrée + fixtures GDTF à jour (2026-07)

- **Documentation réorganisée** pour un dépôt clair : `docs/PROTOCOLE_DMX.md`
  (référence unique des canaux), `docs/ARCHITECTURE.md` (pipeline/NDI/vidéo/modules),
  `docs/DEMOS.md` (guide des scripts), `docs/GDTF.md`. Le README racine devient une
  vitrine avec liens. Fin des tables de canaux dupliquées (source des dérives 28↔32).
- **Manifeste** promu à la racine (`MANIFESTO.md`), corrigé (14 formes).
- **Archives assainies** : `docs/archive/` reçoit un index non-normatif ; suppression
  des documents 100 % périmés (`DEMO_INSTRUCTIONS.txt`, ancien guide artistique,
  ancien README de démos) ; le PV 2026 est archivé.
- **Fixtures GDTF régénérées** : base **32 canaux** (`LuxCore_Base_32ch.gdtf`, avec
  feedback/bloom/kaléido), canal Mode du spot en **valeurs DMX littérales** 0..14 +
  bande **100..113** (forme remplie par la vidéo). Correction d'un XML non conforme
  (attributs collés) dans le générateur. Adresse spot = `32 + N×23 + 1`.
- **python_port/README** aligné : 9 post-effets, 49 tests (8 fichiers), forme+vidéo.

---

## v2.5 — Forme+vidéo, forme « rafale », démo texte (2026-07)

- **Forme remplie par la vidéo** : nouveau mode `+19 = 100 + forme` (0..13) — le spot
  prend la silhouette d'une forme (étoile, cœur, hexagone…) mais est texturé par la
  vidéo (+22 = source) au lieu d'une couleur. Masque = triangulation de la forme.
  Rétrocompatible (modes 0..14 inchangés). Shader `SHAPEVID_VERT`, `_draw_shape_video`.
- **`video_show.py`** : scène « Formes vidéo » ; `defile_formes.py` : décor vidéo
  en forme (anneau d'hexagones-vidéo, spirale d'étoiles-vidéo).
- **Forme 13 : « fleur » → « rafale »** (étoile à 14 pointes fines, 28 sommets ;
  `Shape.FLEUR` → `Shape.RAFALE`, mode DMX 13 inchangé).
- **`lorem_fou.py`** (nouvelle démo texte) : lorem ipsum déchaîné, 6 scènes avec
  PostFX empilés (flux, kaléido, glitch, spirale, rafale, géant).
- **Correctif** : `artnet_text.py` utilisait encore l'offset spot 28 (bloc de base
  d'avant l'extension) — corrigé en 32.

---

## v2.4 — Vidéos découpées en clips de 10 s + garde-fou VRAM (2026-07)

- **Sources découpées en clips de 10 s** (ffmpeg, copie de flux, sans ré-encodage).
  Organisation :
  - `data/videos/`     — jeu de travail chargé par le moteur (**8 clips** par défaut,
    répartis sur les 3 sources → ~52 fps en aperçu).
  - `data/clips_all/`  — réserve des ~129 clips de 10 s (non chargée).
  - `data/videos_src/` — originaux conservés (backup, non chargés).
- **`run_engine.py --max-videos N`** : garde-fou VRAM (~133 Mo/vidéo). Échantillonne
  uniformément le dossier si trop de vidéos. Mesuré : 8 clips ≈ 52 fps, 16 ≈ 28 fps.
- **Démos auto-adaptées** : `luxcore_artnet.count_videos()` ; `video_show.py` cale
  `N_VID` sur le nombre de clips présents. `defile_formes.py` s'adapte déjà (vspread
  normalise sur 0-255, remappé par le moteur).

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
