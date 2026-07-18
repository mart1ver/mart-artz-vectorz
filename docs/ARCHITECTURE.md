# Architecture — LuxCore DMX Engine

**Auteur : Martin Vert**

Le moteur principal est un **portage Python / moderngl** (OpenGL) du sketch Processing d'origine, avec **sortie NDI**. Il vit dans [`python_port/`](../python_port/) ; les sources Processing sont archivées dans [`docs/processing/`](processing/).

Ce document décrit le flux de données, le pipeline de rendu, les PostFX, la sortie NDI, le pipeline vidéo, la géométrie, les modules et les performances. Le mapping DMX complet est décrit dans [PROTOCOLE_DMX.md](PROTOCOLE_DMX.md).

> **Convention d'indexation.** Le code est en **base 0** (index du tableau `dmx_data[]`). Les tableaux ci-dessous indiquent les index de code (base 0) pour les canaux PostFX ; `CLAUDE.md` décrit les mêmes octets en base 1. Les deux conventions désignent les mêmes octets — ne pas les confondre.

---

## Flux de données (bout-en-bout)

Le **buffer DMX est la source de vérité**. Tout part de lui et rien ne le contourne.

```
ArtNet UDP:6454  (artnet.py, thread récepteur)
  → snapshot()             copie du buffer DMX (512 × 9 univers) sous lock
  → engine.render_dmx(dmx, num_spots)
      → dmx.decode_all / decode_spot    (BaseState + SpotState[] + bg_fix)
      → engine.render(base, spots, bg_fix)   [pipeline GPU]
  → pack_uyvy()            (GPU RGBA → UYVY, FBO demi-largeur)
  → readback PBO triple-bufferisé (W·H·2 octets)
  → queue → thread ndi_worker → sender.write_video_async  (source NDI "LuxCore")
```

- `artnet.py` (`ArtNetReceiver`) reçoit les paquets ArtDMX (opcode `0x5000`) dans un thread dédié, lit le **Port-Address 15-bit standard** et remplit un buffer multi-univers. Le socket peut être **lié à une carte réseau** précise (IP), et le **1er univers du patch** (`start_universe`) est remappé sur le slot 0 du buffer. `snapshot()` renvoie une copie cohérente sous lock.
- La boucle live est dans `run_engine.py:main()`, cadencée à `1/FPS` via `time.perf_counter`.
- `dmx.py` décode **1:1** le buffer en un `BaseState` + une liste de `SpotState` + une fixture de fond (portage direct de `SpotData.update_from_dmx`). Un `base_offset` (= adresse ArtNet de départ − 1) décale tout le patch.

### Configuration (menu / JSON)

`run_engine` charge une config JSON (`appconfig`, défaut `~/.config/luxcore/config.json`,
précédence **flag CLI > fichier > défaut**) : résolution, cartes réseau (ArtNet / NDI),
**univers + adresse de départ** du patch. Le menu imgui les édite ; carte ArtNet et
univers/adresse s'appliquent **à chaud**, résolution et carte NDI via une **relance du
process** (`os.execv`) — plus simple et sûr qu'une reconstruction GL. `netconfig` liste
les interfaces (stdlib) ; `constants.patch_position` donne l'**univers/adresse réels**
d'un élément (affiché dans le menu pour le 1er spot et le fond).

### Tailles globales (constants.py)

| Constante | Valeur | Sens |
|-----------|--------|------|
| `NUM_BASE_PARAMETERS` | 32 | bloc de base (28 d'origine + 4 PostFX) |
| `NUM_PARAMS_PER_SPOT` | 23 | canaux par fixture / spot |
| `UNIVERSE_SIZE` | 512 | octets par univers |
| `MAX_UNIVERSES` | 9 | univers 0..8 → buffer `512 × 9 = 4608` octets |
| `BG_FIXTURE_SLOT` | 60 | fixture de fond, adresse `32 + 60×23 = 1412` |

Capacité : `(512 − 32) / 23 =` **20 fixtures / univers**. Adresse d'un spot : `spot_base_addr(id) = 32 + id × 23`. Garder `num_spots ≤ 60`.

---

## Pipeline de rendu (`luxcore/engine.py`) — ordre EXACT

`render(base, spots, bg_fix)` enchaîne, en ping-pong FBO (`fbo/tex` ↔ `_fbo2/_tex2`) :

| # | Étape | Code |
|---|-------|------|
| 1 | Horloge de frame (`self._now = time.monotonic()`) pour les playheads vidéo | `render()` |
| 2 | `clear` fond RGB (base.bg, canaux 0-2) | `ctx.clear(r/255, g/255, b/255, 1)` |
| 3 | Fond vidéo plein écran (bg_fix mode 14, derrière tout) | `_draw_bg_video` |
| 4 | Spots (formes / texte / vidéo / forme+vidéo, blend par spot) | boucle `for sp in spots` |
| 5 | PostFX (feedback … chromatic) sur bg + spots | `_apply_effects` |
| 6 | Blades (couteaux de cadrage 16-bit) | `_draw_blades` |
| 7 | Blur (s'applique par-dessus les blades) | `_apply_blur` |
| 8 | Copie du résultat final dans `self.tex` si besoin | `copy_framebuffer` |

Le remplissage des formes utilise la triangulation ear-clip. Le drapeau `enable_effects` (bypass depuis la GUI) court-circuite les étapes **5** et **7**. Règle drawable d'un spot : `is_drawable() = enabled AND alpha > 0` (spot ignoré sinon).

---

## Les 9 PostFX (`engine._apply_effects`) — ordre EXACT

```
feedback → kaléido → pixelate → sobel → rgb split → saturation → bloom → chromatic
```

Le **blur** (canaux base 20-21) est appliqué SÉPARÉMENT après les blades (`_apply_blur`, étape 7). Il **n'est PAS** dans cette chaîne.

| Effet | Canal base (0-based) | Activation | Paramètre |
|-------|----------------------|-----------|-----------|
| feedback | 28 | `feedback > 1` | decay = pmap(2..255 → 0.80..0.985) ; `out = max(cur, hist·decay)` |
| kaléido | 31 | `kaleido > 1` | segments = clamp(2..24) |
| pixelate | 22 | `pixelate > 1` | amount = pmap(0..255 → 255..20) |
| sobel | 23 | `sobel` (bistable > 128) | — |
| rgb split | 24 | `rgb_split > 1` | delta = rgb_split |
| saturation | 25-26 | `sat_a > 0.001 OR sat_b > 0.001` | saturation = A, vibrance = B |
| bloom | 29-30 | `bloom_amount > 1` | threshold = ch29/255 ; intensity = pmap(2..255 → 0.2..2.5) ; blur interne codé en dur (size 30, σ 8) |
| chromatic | 27 | `chromatic` (bistable > 128) | 12 itérations, max_distort 2.2 |
| **blur** *(hors chaîne)* | 20-21 | `blur_size > 0.1 OR blur_sigma > 0.1` | 2 passes séparables H puis V, gaussien incrémental (APRÈS blades) |

- **Feedback** : historique persistant `_fb_fbo` (noir au départ), recopié après chaque passe.
- **Bloom** : bright-pass (smoothstep seuil) → flou séparable → additif (`scene + glow·intensity`). Son blur interne (size 30, σ 8) est **codé en dur** et distinct du blur utilisateur.
- Tous les PostFX désactivent le BLEND (`ctx.disable(BLEND)`) car ils écrasent la cible.
- **Bistables (> 128)** : Sobel (23) et Chromatic (27) — un octet ≤ 128 les laisse OFF.
- **Kaléido** : 0 ET 1 = off ; seules les valeurs 2..255 activent (nombre de branches, clampé 2..24).

---

## Sortie NDI UYVY 4:2:2

- Format `FourCC.UYVY`, résolution W×H, `Fraction(FPS, 1)` (défaut **1920×1080 @ 60**). Source publiée : **`LuxCore`** (visible dans OBS / vMix / Resolume).
- **Packing GPU** (`UYVY_FRAG`) : conversion BT.709, plage vidéo (Y 16-235, C 128±112). Le FBO cible est **W/2 × H** en RGBA8 : chaque texel encode 2 pixels source, octets `(U, Y0, V, Y1)`.
- **Readback** = **W·H·2 octets** (moitié du RGBA équivalent), via `pack_uyvy()` → `_uyvy_fbo.read_into`.
- **Triple-buffering PBO** (`NB = 3`) + `bytearray` / `np.frombuffer` + queue vers le thread `ndi_worker` (`write_video_async`).
- **Décalage volontaire d'une frame** : on envoie le PBO de la frame n−1 pour laisser le DMA se terminer sans bloquer la boucle de rendu.

Le **plafond de performance est le readback NDI**, pas le rendu OpenGL.

---

## Pipeline vidéo (`luxcore/video.py` + `engine._build_video` / `_video_tex_for`)

- **PyAV** : `VideoClip.load()` décode le clip **entier une seule fois** au démarrage (bloquant), reformate chaque frame `frame.reformat(w, h, 'rgba')` → numpy contigu, et stocke la liste `frames` + `fps` + `duration`. Résolution de cache par défaut **640×360** (`video_size` ; = qualité live actuelle, réglable).
- **Décode-une-fois** : plus de thread de décodage continu → **coût CPU permanent nul** en régime établi ; lecture **déterministe** (horloge `time.monotonic()`).
- **Playhead par spot** : `_video_tex_for(sp, slot)` avance l'état de lecture du slot selon le transport DMX (start/vitesse/pause/stop/loop/ping-pong/sens), calcule l'index `round(pos)`, téléverse la frame voulue dans la **texture du slot** (pool paresseux) et la renvoie. Ré-upload seulement si la frame change.
- **Groupes de sync** (+5) : les spots d'un même groupe sur la même source partagent une clé d'état → **un seul playhead et une seule texture**, dessinée à plusieurs positions.
- **RAM cache ≈ largeur·hauteur·4 · nb_frames par clip** (≈ 270 Mo/clip de 10 s à 640×360) ; le dossier entier est chargé au démarrage, ce qui borne le nombre de clips (`--max-videos`).
- **Échelle** : `VIDEO_SIZE_SCALE = 2.5` permet le plein écran malgré le plafond de décodage à 1000 px de la pmap taille. Appliquée UNIQUEMENT aux fixtures vidéo (`_draw_video`), **pas** aux formes.
- **Sélection de source** (canal +22) : `vidx = min(sel_raw × n_videos // 256, n_videos − 1)`.
- **Forme + vidéo (mode `100 + forme`)** : si `sp.video_fill` et forme dans `_ranges` → `_draw_shape_video` : la triangulation de la forme **masque** la vidéo (échelle de forme, PAS `VIDEO_SIZE_SCALE`). Shader `SHAPEVID_VERT` + `VIDEO_FRAG`, UV = `in_pos + 0.5`. Bande `VIDEO_FILL_MODE_BASE = 100` → plage 100..113 (0 = ellipse vidéo … 13 = rafale vidéo), rétrocompatible.
- **Fond vidéo** : `_draw_bg_video` plein écran (étape 3 du pipeline), respecte sélecteur / alpha / blend de la fixture de fond (slot 60).

### Option `--max-videos N` (garde-fou VRAM)

Si `len(video_paths) > N`, échantillonnage **uniforme** : `keep = {round(i·(n−1)/(m−1)) for i in range(m)}` (m > 1). Vidéos triées par nom ; `--video` (fichier unique) mis en tête ; dédoublonnage en gardant l'ordre. Repère mesuré : **8 clips ≈ 52 fps, 16 ≈ 28 fps** en aperçu.

### Organisation des dossiers vidéo

| Dossier | Rôle | Chargé au démarrage |
|---------|------|---------------------|
| `data/videos/` | jeu de travail (**8 clips de 10 s** par défaut) | **oui** (tout le dossier) |
| `data/clips_all/` | réserve des ~129 clips de 10 s | non |
| `data/videos_src/` | originaux conservés (backup) | non |

Découper une source en clips de 10 s (copie de flux, sans réencodage, rapide) :

```bash
ffmpeg -i src.mp4 -c copy -an -map 0:v:0 -f segment -segment_time 10 \
       -reset_timestamps 1 data/clips_all/src_%03d.mp4
```

Voir `python_port/README` pour la procédure complète.

---

## Formes et géométrie (`luxcore/geometry.py`)

Les **14 formes** sont définies comme polygones-unité (centrés en (0,0), rayon / demi-côté 0.5) puis remplies par **triangulation ear-clip** :

| Valeur | Forme | | Valeur | Forme |
|--------|-------|---|--------|-------|
| 0 | Ellipse (72 seg) | | 8 | Étoile 5 branches (outer 0.5 / inner 0.2) |
| 1 | Rectangle | | 9 | Croix (12 sommets, contour propre) |
| 2 | Texte | | 10 | Flèche (7 sommets, concave) |
| 3 | Triangle | | 11 | Cœur (72 sommets, paramétrique `16·sin³…`) |
| 4 | Pentagone (offset −π/2) | | 12 | Segment (2 extrémités) |
| 5 | Hexagone | | 13 | Rafale (étoile 14 pointes, 28 sommets) |
| 6 | Losange | | 14 | VIDEO (quad texturé plein écran) |
| 7 | Octogone | | | |

VIDEO (14), TEXTE (2) et SEGMENT (12) sont des cas spéciaux (non triangulés). `MAX_SHAPE_MODE = 14` ; toute valeur hors 0..14 (et hors bande 100..113) → **RECTANGLE**.

La **rafale** (mode 13, `_sunburst`, outer 0.5 / inner 0.17, une pointe en haut) a remplacé l'ancienne rosace « fleur ».

- **Modes d'échelle** (`SCALE_MODE`) :
  - `pan_tilt` (sx = pan, sy = tilt) : ellipse / rectangle / triangle / losange / flèche / cœur / segment ;
  - `pan_only` (sx = sy = pan, size_tilt ignoré) : pentagone / hexagone / octogone / étoile / croix / rafale.
- **Ear clipping** (`_triangulate`) : normalise en anti-horaire (`_signed_area`), coupe les oreilles convexes non contenantes (test `_point_in_triangle`), plafond ≤ 10000 itérations. Remplit correctement les concaves (flèche / cœur). Résultats en cache (`_UNIT_TRI_CACHE`), concaténés en un seul VBO (`_build_shape_vbo`, `_ranges[shape] = (first, count)`), rendus en `GL_TRIANGLES`.

---

## Modules (`python_port/luxcore/`)

| Module | Rôle |
|--------|------|
| `run_engine.py` | Boucle live : ArtNet → décodage → render → NDI ; fenêtre aperçu moderngl-window + GUI imgui (`g` plein écran, `h` menu) ; inhibition veille (systemd-inhibit + xset) ; snapshots PNG ; triple-PBO NDI |
| `engine.py` | `LuxCoreEngine` : programmes GL (VERT/FRAG formes, TEXT, VIDEO, SHAPEVID, UYVY), pipeline `render()`, PostFX, blades, blur, `pack_uyvy` ; caches stroke/glyphes ; textures vidéo |
| `effects.py` | 9 shaders PostFX GLSL 330 (pixelate/sobel/rgbsplit/saturation/chromatic/feedback/kaléido/bloom bright+combine/blur) + `FULLSCREEN_VERT` |
| `video.py` | `VideoClip` : décode le clip entier en cache mémoire (frames RGBA numpy) au démarrage ; `frame_at(idx)` borné |
| `geometry.py` | 14 formes en polygones-unité + triangulation ear-clip, caches numpy, `scale_factors` |
| `blades.py` | 4 quads noirs de cadrage (A/B/C/D) depuis 8 valeurs 16-bit, `blade_is_active` |
| `stroke.py` | Ruban de contour (miter, `MITER_LIMIT = 4`) vectorisé numpy + `segment_quad` |
| `text.py` | `FontCache` : glyphes bitmap RGBA par (police, char), 20 polices triées alphabétiquement |
| `artnet.py` | `ArtNetReceiver` thread UDP:6454, parse ArtDMX 0x5000, Port-Address 15-bit, **bind par interface** + **`start_universe`** (remap du 1er univers du patch sur le slot 0), buffer multi-univers, `snapshot()` sous lock |
| `constants.py` | mapping DMX 0-indexé, LUT blend, enums formes/blend, `BG_FIXTURE_SLOT`, `patch_position` (univers/adresse réels) |
| `dmx.py` | décodage 1:1 (`BaseState` + `SpotState`, `sel_raw` = +22 brut) ; `base_offset` = adresse ArtNet de départ |
| `gui.py` + `imgui_backend.py` | panneau imgui (config réseau/patch/résolution + status) |
| `netconfig.py` | énumération des cartes réseau + IPv4 (stdlib `socket`+`ioctl`) |
| `appconfig.py` | config JSON persistée + validation (résolution, cartes réseau, patch ArtNet) |

---

## Performances

- **Cible matérielle** : iGPU Intel **UHD 630** (2018). Défaut : 1920×1080 @ 60. Cadence observée : ~45-56 fps à 1080p (48-60 fixtures).
- **Plafond = readback NDI.** Le goulot n'est pas le rendu des formes mais la lecture GPU→CPU pour la sortie NDI. D'où les optimisations : packing UYVY 4:2:2 (readback réduit à `W·H·2` octets, moitié du RGBA), triple-buffering PBO (`NB = 3`) et décalage volontaire d'une frame pour recouvrir le DMA.
- **Vidéo** : décode-une-fois en cache RAM (≈ 270 Mo/clip de 10 s à 640×360) → **coût CPU permanent nul** en lecture (contre un décodage continu auparavant). Uploads GPU bornés au nombre de spots vidéo visibles (frame courante de chaque playhead). `--max-videos` borne la RAM. Cadence live sur le jeu de travail : **8 clips ≈ 52 fps**, **16 ≈ 28 fps**.
- **Caches** : rubans de contour mémoïsés (par forme / taille / largeur), triangulations unité en cache (`_UNIT_TRI_CACHE`), glyphes bitmap en cache (`FontCache`) — pour éviter tout recalcul par frame.

### Points de vigilance (non-bugs à préserver)

- Le docstring de `engine.py` dit « 13 formes » : lire **14** (0-13 remplies + VIDEO=14). `CLAUDE.md` fait foi.
- Le blur (canaux base 20-21) n'est PAS dans la chaîne des 9 PostFX : appliqué séparément APRÈS les blades.
- Le blur INTERNE au bloom (size 30, σ 8) est codé en dur, distinct du blur utilisateur.
- `RGBSPLIT_FRAG` : l'alpha de sortie est `c1.a + c2.a + c3.b` (`.b` au lieu de `.a`) — porté tel quel, ne PAS « corriger » sans validation de Martin.
- `VIDEO_SIZE_SCALE = 2.5` doit rester synchronisé avec `sz_px()` des `demo_scripts` (dépendance croisée non enforced par le code).

---

Voir aussi : [Protocole DMX](PROTOCOLE_DMX.md) · [Guide des démos](DEMOS.md) · [Fixtures GDTF](GDTF.md).
