# Guide des démos — LuxCore DMX Engine

**Auteur : Martin Vert**

Les scripts de [`demo_scripts/`](../demo_scripts/) pilotent le moteur **par ArtNet**
(`127.0.0.1:6454`). Ils n'ont pas besoin des dépendances du moteur : juste Python 3 et
une socket UDP.

## Prérequis

Lancer le moteur d'abord (aperçu + sortie NDI), puis un script de démo :

```bash
# 1. moteur
python_port/.venv/bin/python python_port/run_engine.py --preview --spots 60 --duration 0

# 2. démo (dans un autre terminal)
python3 demo_scripts/defile_formes.py
```

Aperçu : **`g`** = plein écran (curseur masqué + veille inhibée), **`h`** = menu.
Tous les shows tournent **en boucle** — `Ctrl+C` pour quitter.

---

## `luxcore_artnet.py` — module partagé

Boîte à outils importée par les autres scripts (pas lancé directement) :

- `set16(dmx, idx, val)` — écrit une valeur 16-bit big-endian
- `send(sock, dmx, ip)` / `send_multi(sock, universes, ip)` — envoi ArtNet 1 ou N univers
- `hsv(h, s, v)` — couleur HSV → RGB
- `char_tilt(c)` — encode un caractère ASCII pour le mode Texte (`math.ceil`)
- `count_videos(dir)` — nombre de clips présents dans `data/videos/`
- `make_socket()` — socket UDP prête

---

## `defile_formes.py` — le show maître

Show complet en boucle, sur **3 univers** :

1. **Intro typographique** — les mots « ArtNet / controled / generator / made by / Martin VERT »
2. **Intro blades** — les 8 couteaux s'éveillent sur une vidéo de fond
3. **Défilé des 14 formes** — positions symétriques, décor vidéo par forme (anneaux
   d'hexagones-vidéo, spirales d'étoiles-vidéo via le mode forme+vidéo)
4. **Finale 5 actes** — Explosion / Constellation / Mots / Vortex / Supernova (48 spots)

---

## `kinetic.py` — géométrie rythmée (BPM)

6 scènes calées sur un tempo : **Pulse Grid, Chase Ring, Symétrie, Rotation, Blade
Sweep, Bloom**, avec PostFX dosés. Boîte à outils rythmique interne :
`env` (pompe sèche), `gate` (porte), `swell` (respiration douce avec plancher).

---

## `video_show.py` — 100 % des fonctions vidéo

9 scènes couvrant **toutes** les capacités vidéo : plein écran + sélection de source
(+22), fond + panneaux, mur/mosaïque multi-sources, désync/écho, mouvement/rotation/
échelle, blend par panneau, **formes vidéo** (mode 100+forme), combos PostFX empilés,
et un mur kaléido final.

```bash
python3 demo_scripts/video_show.py [ip] [n_vidéos]
```

---

## `lorem_fou.py` — démo texte survitaminée

Lorem ipsum déchaîné sur 6 scènes avec PostFX empilés : **flux, kaléido, glitch,
spirale, rafale, géant**. Encode les caractères en mode Texte (`char_tilt`), cycle les
20 polices.

```bash
python3 demo_scripts/lorem_fou.py [ip]
```

---

## `artnet_text.py` — typographie multi-scènes

Animation typographique (importable comme module ou lancée seule). Sert d'intro dans
`defile_formes.py`.

---

## Confort visuel — anti-clignotement

Règle transverse à **toute** nouvelle scène (confort + sécurité photosensible) :

- **Pas de blackout plein écran** ni de bascule bistable (enable/sobel/chroma/blend) au
  rythme.
- Préférer `swell()` (respiration cosinus **avec plancher** > 0, ne retombe jamais au
  noir) aux enveloppes sèches.
- Préférer les motifs **spatiaux** aux flips temporels plein champ.

---

## Utilitaires (legacy)

Deux petits scripts mono-univers, conservés comme outils simples :

- `lettre_a.py` — affiche un « a » noir sur fond blanc (test visuel minimal).
- `system_validation.py` — harnais de validation/anti-régression basique.

---

Voir aussi : [Protocole DMX](PROTOCOLE_DMX.md) · [Architecture](ARCHITECTURE.md).
