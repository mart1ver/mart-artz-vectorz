# Démos ArtNet — LuxCore DMX Engine

**Auteur : Martin Vert**

Guide des scripts de pilotage du moteur (dossier [`demo_scripts/`](../demo_scripts/)).
Tous les scripts écrivent un buffer DMX (liste d'octets) et l'envoient au moteur par
paquets ArtNet UDP vers `127.0.0.1:6454`. Ils n'ont pas besoin des dépendances du
moteur : juste Python 3 et une socket UDP. Ils bouclent jusqu'à `Ctrl+C`.

---

## Prérequis

Le moteur doit tourner **en parallèle** de la démo. Il est la source de vérité : il
reçoit l'ArtNet, décode le buffer DMX et produit l'aperçu écran + la sortie NDI.

### 1. Lancer le moteur

```bash
python_port/.venv/bin/python python_port/run_engine.py --preview --spots 60 --duration 0
```

- `--preview` ouvre la fenêtre d'aperçu (`g` = plein écran avec curseur masqué et
  veille inhibée, `h` = menu).
- `--spots 60` : requis par les gros shows (`defile_formes` a besoin de `>= 60`).
- `--duration 0` : tourne indéfiniment.
- Version headless (NDI seul) : retirer `--preview`.
- Les vidéos sont chargées depuis `data/videos/` au démarrage (option `--videos-dir`).

### 2. Lancer une démo (dans un second terminal)

```bash
python3 demo_scripts/defile_formes.py            # show maître complet
python3 demo_scripts/kinetic.py                  # géométrie rythmée BPM
python3 demo_scripts/video_show.py               # 10 scènes vidéo
python3 demo_scripts/lorem_fou.py                # texte survitaminé
python3 demo_scripts/artnet_text.py              # typographie multi-scènes
```

Vérification de syntaxe sans lancer : `python3 -m py_compile demo_scripts/<script>.py`.

### Conventions transverses

- **Buffers :** `defile_formes` / `video_show` / `kinetic` / `lorem_fou` utilisent
  1536 octets (3 univers) ; `artnet_text` et les utilitaires legacy 512 (1 univers).
  `send_multi()` découpe automatiquement le grand buffer en univers de 512 octets
  (u0 → 0-511, u1 → 512-1023…).
- **Résolution supposée :** ~1920×1080. Les mappings position dépendent de la taille
  de la fenêtre.
- **Deux échelles distinctes :** `sz_px` (vidéo, division par `1000·2.5`) ≠ `sz_shape`
  (forme, plafond 1000 px). Ne pas les confondre.
- **Encodage texte :** `char_tilt` / `set16` utilisent `math.ceil` — **obligatoire**
  (un `int()` tronquerait et glisserait au caractère précédent).

---

## `luxcore_artnet.py` — module partagé

Boîte à outils commune importée par tous les scripts. **Non exécutable seul.**

| Fonction | Rôle |
|----------|------|
| `count_videos(videos_dir=None)` | Compte les vidéos de `data/videos/` (mp4/mov/mkv/webm/avi), minimum 1 — cale `N_VID` sur ce que charge réellement le moteur |
| `make_socket()` | Crée un socket UDP |
| `set16(dmx, idx, val)` | Écrit une valeur 16-bit big-endian (MSB `dmx[idx]`, LSB `dmx[idx+1]`), clampée |
| `send(sock, dmx, ip, universe=0)` | Envoie 1 paquet ArtNet ; header + opcode 0x5000 + `bytes([0,14,0,0, universe&0xFF, (universe>>8)&0x7F])` |
| `send_multi(sock, dmx, ip)` | Découpe un grand buffer en univers de 512 octets ; capacité 2 univ = 49 spots, 9 univ = 229 |
| `hsv(h, s=1, v=1)` | h ∈ 0-1 → (r,g,b) 0-255 |
| `char_tilt(c)` | Caractère ASCII → tilt_16bit (mode Texte), `math.ceil(ord(c)*65535/1000)` — **ceil obligatoire** |
| `PORT` | 6454 |

---

## `defile_formes.py` — show maître (3 univers)

Le plus gros script : show complet en boucle, ≈ 230 s et plus.

**Lancer :**
```bash
python3 demo_scripts/defile_formes.py [ip] [duree_par_forme]
```
Défauts : `127.0.0.1` · `6.0` s. Requiert le moteur lancé avec `--spots >= 60`.

Classe `DefileFormes` ; buffer `dmx = [0]*1536` (3 univers → jusqu'à 65 spots).
Importe `luxcore_artnet` **et** `artnet_text`.

**Séquence (`run()`) :**
1. **Texte intro** (30 s) — délègue à `artnet_text.run()`.
2. **`demo_intro()`** (20 s) — blades / couleurs / blur en 3 actes (ouverture des
   coins → blades qui dansent → fermeture), fond VIDÉO plein écran révélé par les
   couteaux, palette de fond interpolée (noir→rouge→bleu→vert→magenta→or→blanc),
   puis fade vers noir.
3. **Défilé des 14 formes** — chaque forme sa tranche (6 s ; Segment 15 s), fade
   in/out 0.4 s, transition 0.6 s. Par forme : couleur + blend thématiques (table
   `FORMES`), disposition symétrique dédiée (`_forme_positions`), décor vidéo
   permanent (`_video_backdrop`, 6 presets), pattern `enable/blend` créatif
   (`_creative_enable_blend`), timeline PostFX (`set_effects`, cloche parabolique +
   gates).
4. **`demo_finale()`** (180 s) — 48 spots sur 3 univers, 5 actes : ACTE 1 Explosion
   (burst radial), ACTE 2 Constellation (Lissajous / épicycloïdes / hypotrochoïdes),
   ACTE 3 Mots (« LUXCORE », « MARTIN », « ART DMX » lettre par lettre + orbites),
   ACTE 4 Vortex (spirale d'Archimède + tous PostFX + kaléido + blades qui ferment),
   ACTE 5 Supernova (explosion + fade out).

**Slots :** formes 0-47 · panneaux vidéo 48-59 (`VIDEO_FIXTURE_SLOT0=48`,
`NUM_VIDEO_FIXTURES=12`) · fond = slot 60.

**Encodage :** `to_pan` / `to_tilt` avec demi-écran 960×540, échelles X/Y différentes
(cercles ronds), `SCREEN_PX_RANGE=2430` calibré empiriquement. Vidéo : `sz_px()`
divise par `1000·VIDEO_SIZE_SCALE(2.5)` ; forme-vidéo via `_set_shape_video` mode
`100+forme` (plafond 1000 px). `vspread(k,n)` varie le canal +22 entre panneaux
voisins. Layouts symétriques : `lay_ring`, `lay_rings`, `lay_phyllo`, `lay_rose`,
`lay_polygons`, `lay_grid`.

Table `FORMES` : Ellipse(ADD), Rectangle(BLEND), Texte(SCREEN), Triangle(DIFFERENCE),
Pentagone(BLEND), Hexagone(ADD), Losange(EXCLUSION), Octogone(LIGHTEST), Étoile(ADD),
Croix(BLEND), Flèche(SCREEN), Cœur(ADD), Segment(ADD, 15 s), Rafale(SCREEN).

---

## `kinetic.py` — géométrie rythmée sur tempo (BPM)

**Lancer :**
```bash
python3 demo_scripts/kinetic.py [ip] [bpm]
```
Défauts : `127.0.0.1` · `128` BPM. Formes pures, ni texte ni vidéo. `dmx=[0]*1536`,
`MAX_SPOTS=48`. Classe `Kinetic` ; `spb = 60/bpm` ; `frame_reset()` repart d'un
buffer noir chaque frame.

| Scène | Méthode | Mesures | Contenu |
|-------|---------|---------|---------|
| Pulse Grid | `sc_pulse_grid` | 8 | Grille 8×5 qui gonfle, couleur par mesure, ADD, bloom respirant |
| Chase Ring | `sc_chase_ring` | 8 | 2 anneaux, point qui chasse sur les 8e, comètes (feedback), SCREEN |
| Symétrie | `sc_symmetry` | 8 | Champ kaléidoscopique (kaleido=6 fixe) qui respire, ADD |
| Rotation | `sc_rotation` | 8 | 3 anneaux concentriques verrouillés, blur pulsé, DIFFERENCE, feedback |
| Blade Sweep | `sc_blade_sweep` | 8 | Champ derrière couteaux qui s'ouvrent/ferment à la mesure, ADD, bloom |
| Bloom | `sc_bloom` | 12 | FINALE : couronnes de grandes formes qui pulsent, montée d'intensité, kaléido de sortie |

Boîte à outils rythmique : `env(t,div,sharp)` (pompe sèche exponentielle),
`gate(t,div,duty)` (porte on-off), `swell(t,div,floor=0.4)` (respiration cosinus avec
**plancher**, jamais zéro), `beat_i`, `bar_i`, `scene_gain` (fondu cosinus). Phase
GLITCH commune : sobel + pixelate CONSTANTS sur le 3e quart de chaque scène (valeurs
figées = pas de scintillement).

---

## `video_show.py` — 10 scènes vidéo (100 % des fonctions vidéo)

**Lancer :**
```bash
python3 demo_scripts/video_show.py [ip] [n_videos]
```
`N_VID` auto-détecté via `count_videos()`. `MAX_PANELS=24` (slots 0-23), `BG_SLOT=60`.
Classe `VideoShow`. Méthodes : `vspot()` (panneau vidéo mode 14, 16:9), `vshape()`
(forme remplie mode `100+forme`), `bgvid()` (fond plein écran), `blade()`. Toutes
acceptent le **transport** en `**tr` (`speed`, `vin`, `transport`, `reverse`, `loop`,
`vout`, `sync`, `strobe`) ; helpers `vid_flags()` et `spd(facteur)`. Enveloppes
`swell`, `bump`, `scene_gain`.

| Scène | Méthode | s | Démontre |
|-------|---------|---|----------|
| Plein écran | `sc_fullscreen` | 16 | Cycle des vidéos en fondu, sélecteur +22 |
| Fond+Panneaux | `sc_bg_panels` | 16 | Fixture de fond + 3 panneaux flottants |
| Mur vidéo | `sc_wall` | 14 | Mosaïque 4×3, multi-sources |
| Écho (départs décalés) | `sc_echo` | 16 | Même vidéo, départs échelonnés (+1) → cascade temporelle |
| Transport | `sc_transport` | 18 | 4 modes côte à côte : ralenti / normal / arrière / ping-pong |
| Mouvement | `sc_motion` | 16 | 5 panneaux orbitent / tournent / respirent |
| Blend | `sc_blend` | 14 | Même vidéo en ADD/SCREEN/DIFFERENCE |
| Formes vidéo | `sc_video_shapes` | 16 | Silhouettes (étoile/cœur/hexa…) dans la vidéo |
| PostFX (combos) | `sc_postfx` | 24 | 6 combos superposés qui montent/descendent |
| Kaléido mur | `sc_kaleido_wall` | 16 | FINALE : mur + kaléidoscope + bloom |

`vsel(v)` mappe l'index vidéo → canal +22 (milieu de plage). `sz_px` (vidéo, ÷2.5) vs
`sz_shape` (forme, plafond 1000 px) sont distincts. Les scènes Écho/Transport respectent
l'anti-clignotement : variété **spatiale** (pas de flip temporel plein champ).

---

## `lorem_fou.py` — texte survitaminé

**Lancer :**
```bash
python3 demo_scripts/lorem_fou.py [ip]
```
Chaque caractère = un spot en mode TEXTE (`+19=2`) : caractère dans `size_tilt` via
`char_tilt`, échelle dans `size_pan`, police via `+22`. `MAX_SPOTS=48`, `N_FONTS=20`,
texte `LOREM` bouclé.

| Scène | Méthode | s | Contenu + PostFX |
|-------|---------|---|------------------|
| Flux | `sc_flux` | 16 | Texte qui coule, 3 lignes arc-en-ciel (bloom+feedback+chroma) |
| Kaléido | `sc_kaleido` | 16 | Grappe repliée en mandala (kaleido+bloom+saturation) |
| Glitch | `sc_glitch` | 14 | Lettres qui tremblent (sobel+pixelate+rgb split) |
| Spirale | `sc_spirale` | 16 | Lettres sur spirale phyllotaxique (feedback+bloom) |
| Rafale | `sc_rafale` | 16 | Lettres explosent du centre et se recyclent (feedback+chroma+rgb split) |
| Géant | `sc_geant` | 14 | Mots énormes qui pulsent un par un (bloom+blur respirant) |

`font_raw(f)` mappe l'index police → `+22`. `swell` et `scene_gain` assurent les
transitions.

---

## `artnet_text.py` — typographie multi-scènes (importable + standalone)

**Lancer :**
```bash
python3 demo_scripts/artnet_text.py
```
Boucle infinie en autonome, OU importé : `artnet_text.run(duree=None, ip, sock=None)`
(utilisé par `defile_formes.py`). Buffer 512 octets (1 univers).

Cycle de 5 mots : « ArtNet » (4 s) → « controled » (4 s) → « generator » (4 s) →
« made by: » (4 s) → « Martin VERT » (6 s). Chaque lettre = spot mode 2, positions
pré-calculées (`make_pan_u`, `SCALE_PAN=48`). Fond blanc, couteaux ondulants, PostFX
(pixelate / sobel / rgbsplit / chromatic). Forme d'arrière-plan spot 11 : Triangle
rouge (mots 0-3) ou Cœur noir (dernier mot). ~30 fps (sleep 0.033). Blackout final.

---

## Règle transverse : ANTI-CLIGNOTEMENT (confort visuel)

Appliquée dans toutes les démos récentes (`kinetic`, `video_show`, `lorem_fou`,
`defile_formes`). À tenir pour **toute** nouvelle scène (confort + sécurité
photosensible) :

- **Pas de blackout plein écran ni de strobe** au rythme ; pas de bascule bistable
  (enable / sobel / chroma / blend) plein champ au tempo.
- Préférer **`swell()`** (respiration cosinus, plancher > 0, ne retombe jamais au
  noir) aux enveloppes sèches (`env`).
- Préférer des motifs **spatiaux** (vagues, chases, patterns fixes répartis) aux flips
  **temporels** plein champ.
- Bistables (sobel / pixelate) tenus **CONSTANTS** sur la durée d'une scène / phase
  (valeurs figées).
- Transitions entre scènes par **fondu doux** (`scene_gain`, cosinus) sur l'alpha des
  spots ET le fond.

Cette règle est documentée dans `CLAUDE.md` et matérialisée par les commentaires
« plus de strobe / vague spatiale » dans `_creative_enable_blend`.

---

## Utilitaires legacy

> ⚠️ **Indexation DMX ancienne — ne pas prendre pour référence.** Ces deux scripts
> précèdent l'unification du mapping et ne suivent pas le layout canonique
> `32 + spot×23`.

- **`lettre_a.py`** — affiche un « a » noir (mode Texte) sur fond blanc, centré, spot
  0, statique. Utilise `BASE = 28` (ancienne base 28 canaux, avant les 4 PostFX), non
  aligné sur `32 + spot*23`. N'utilise pas `luxcore_artnet.set_spot`.
- **`system_validation.py`** — `python3 demo_scripts/system_validation.py [ip]`,
  classe `LuxCoreValidator`, ~30 s, 5 tests séquentiels (couleurs, blades 16-bit,
  spots/formes, effets, blend). Écrit son propre paquet ArtNet inline (n'importe pas
  `luxcore_artnet`) et ne valide que le **succès d'envoi UDP**, pas le rendu visuel.
  `base = 32` pour spot 0 mais sans `+22` par spot ; tailles écrites en dur sur
  `base+9..12` et `15..18`.

---

Voir aussi : [Protocole DMX](PROTOCOLE_DMX.md) · [Architecture](ARCHITECTURE.md) · [Fichiers GDTF](GDTF.md).
