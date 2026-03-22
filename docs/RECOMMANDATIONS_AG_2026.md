# Recommandations — Assemblee des agents 2026-03-18
# Session de suivi — 2026-03-22

Rapport consolide des 8 agents specialises sur l'etat du projet LuxCore DMX Engine.

---

## Seance du 2026-03-18

### Bilan de l'AG 2025 — toutes actions accomplies

---

## UI-Artist-Designer

1. ~~Embarquer une police TTF dans `data/` pour le mode texte (rendu stable entre machines)~~
2. ~~Affecter `blend_mode` global dans `do_blend_mode()` pour que le GUI soit honnete~~
3. ~~Nommer `BLADE_BASE_OFFSET = 3` comme constante dans `definitions.pde`~~

---

## Lighting-Designer-Expert

1. ~~Produire un fichier **GDTF minimal** (20 canaux/spot) pour patcher dans MA3/Hog4/QLC+~~
2. ~~Remplacer `map()` blend mode par une **LUT fixe** correspondant exactement a CLAUDE.md~~
3. ~~Implementer **ArtPollReply** (~239 octets) pour que LuxCore soit visible sur reseau ArtNet~~

---

## Business-Opportunity-Analyst

*(Rapport factuel — a choisi de decrire les cas d'usage reels plutot que de prescrire)*

Cas d'usage identifies :
- Visuel de scene pour concerts / DJ sets (integration directe console DMX)
- Installation artistique autonome en galerie (`defile_formes.py` en boucle infinie)
- Generateur de contenu typographique pilote ArtNet (`artnet_text.py`)
- Visualiseur de console DMX en loopback pour tests
- Prototypage de shows lumiere

---

## Code-Expert-Pro

1. ~~**One-liner** : affecter `blend_mode` global dans `do_blend_mode()`~~
2. ~~Remplacer `concat()` par `System.arraycopy()` dans `do_artnet()` — zero allocation par frame~~
3. ~~`try/catch` autour du JSON dans `set_fullscreen()` — evite le crash silencieux au premier lancement~~

---

## Project-Visionary

1. ~~Canal de **blend mode individuel par spot** (+21, 23 canaux/spot)~~
2. ~~Forme **"segment" / ligne ouverte** (mode 13)~~
3. ~~Canal **enable/disable par spot** (+20, coupure instantanee sans toucher l'alpha)~~
4. ~~Police configurable par spot via DMX (+22) — 20 polices chargees~~
5. ~~Documenter le mapping texte ASCII dans `z_fixture_definition.pde`~~
6. ~~Exploiter reellement le **multi-univers** en Python (3 univers, 65 spots max)~~
7. Premiere **demonstration publique** avant d'ajouter des fonctionnalites

---

## Git-Specialist

1. ~~Creer un **remote git** (GitHub public) + `git push` — protection contre perte totale~~
2. ~~Merger `robustness-improvements` dans `master` (fast-forward propre) + supprimer la branche~~
3. ~~Completer `.gitignore` : `__pycache__/`, `data/window_size.txt`, `data/bg/`, `linux-amd64/`, `data/gui/*/screenshots/`, `CLAUDE.md`, `.claude/`~~

---

## Code-Quality-Auditor

**Score global : 6.2 / 10** (seance 2026-03-18)

1. ~~**Corriger les validations fantomes** dans `error_handling.pde`~~
2. ~~**Corriger `return_blend_mode()`**~~
3. ~~**Supprimer les 11 variables mortes** dans `definitions.pde`~~
4. ~~**Extraire `luxcore_artnet.py`** — module Python partage~~
5. ~~**Securiser le parsing JSON** dans `set_fullscreen()`~~

---

## Documentation-Specialist

1. ~~**Unifier en base 0** toute la documentation DMX~~
2. ~~**Deplacer docs fictives** dans `docs/archive/`~~
3. ~~**Creer `README.md` racine** : prerequis, lancement en 3 etapes, liens~~

---

## Recapitulatif seance 2026-03-18

| Theme | Statut |
|---|---|
| Bug `blend_mode` GUI | OK |
| Remote git / backup | OK |
| Crash silencieux JSON | OK |
| Variables mortes (x11) | OK |
| Police TTF embarquee | OK |
| Validations fantomes | OK |
| Module Python partage | OK |
| `.gitignore` complet | OK |
| Merger master | OK |
| README racine | OK |
| Docs fictives archivees | OK |
| GDTF / QLC+ | OK |
| Forme segment | OK |
| Multi-univers Python | OK |
| Canal blend/spot individuel | OK |
| Canal enable/disable par spot | OK |
| Premiere demonstration publique | en attente |

---

## Session de suivi — 2026-03-22

Nouvelles realisations depuis l'AG :

| Realisation | Detail |
|---|---|
| **Defile en boucle infinie** | `run()` tourne jusqu'au Ctrl+C, redemarrage auto apres la finale |
| **Intro typographique integree** | `artnet_text.run()` appele en debut de chaque cycle (30s) |
| **19 spots par tableau** | Layout 1 centre + 6 inner (r=8000) + 12 outer (r=16000) |
| **Enable/blend creatifs par forme** | 14 formes avec strobe, scanner, heartbeat, chase, inner/outer bascule, spirale... |
| **Forme Segment spectaculaire** | 19 lignes arc-en-ciel centrees, epaisseur 0.6-80px, 3 groupes de rotation, effets dedies |
| **20 polices variees** | Orbitron, BebasNeue, Pacifico, PressStart2P, Cinzel, Raleway, Comfortaa... |
| **Font cycling temporel** | Forme Texte : cycle 20 polices en 6s. Finale Acte 3 : police differente par lettre et par mot |
| **Spots plus grands** | Centre 22k, inner 14k, outer 9k |
| **Effets Segment sans noircissement** | Timeline dediee : sobel/pixelate/chromatic sans blur, duree 15s |

*Seance du 2026-03-22 — President : Martin Vert*

---

## Nouvelles recommandations — AG 2026-03-22

Rapport consolide des 8 agents apres analyse de l'etat actuel du projet.
Etat analyse : 23 canaux/spot, 20 polices, boucle infinie, enable/blend creatifs par forme,
forme Segment spectaculaire, finale 5 actes 48 spots, GUI font supprimee.

---

## UI-Artist-Designer

1. Afficher le nom de la police active en lecture seule dans le GUI — alimenter depuis le dernier `font_index` DMX recu (canal +22). Le GUI ne permet plus de choisir la police, mais le designer doit pouvoir voir laquelle joue.
2. Ajouter un panel GUI "etat live" minimal : forme courante / temps ecoule dans le cycle / numero de cycle. Visible dans le terminal mais pas dans Processing.
3. L'intro typographique (30s) et l'intro blades (20s) ne sont pas distinguables visuellement depuis le GUI. Un overlay texte simple (`textMode(SCREEN)`) suffirait pendant ces phases.

---

## Lighting-Designer-Expert

1. **Mettre a jour le fichier GDTF** de 20 a 23 canaux par spot — ajouter les attributs Enable (ch+20), BlendMode (ch+21), GoboIndex-Font (ch+22) avec leurs ranges DMX documentes.
2. Verifier que `ArtPollReply` annonce correctement les 3 univers (`SwIn`/`SwOut` = 3) — les consoles MA3/Hog4 patching sur 3 univers doivent voir le noeud sans configuration manuelle.
3. Documenter explicitement dans le GDTF que la valeur DMX `0` sur canal +21 signifie "suit le blend mode global" (backward compatible) — les consoles assignent souvent 0 par defaut sur les canaux inconnus.

---

## Business-Opportunity-Analyst

*(Rapport factuel — descriptions de cas d'usage reels uniquement)*

Cas d'usage nouveaux identifies :
- **Installation autonome** : la boucle infinie rend `defile_formes.py` deployable sans supervision (galerie, vitrine, exposition). Documenter les prerequis materiels minimaux (CPU, RAM, reseau loopback).
- **Demonstration formelle** : le show ~5 minutes est suffisamment structure pour une presentation a un public non technique. L'item "premiere demonstration publique" reste le seul point ouvert de l'AG precedente.

---

## Code-Expert-Pro

1. **Corriger le commentaire date dans `demo_finale()`** : `# (1024 - 28) / 20 = 49.8 → 48 spots sur 2 univers` est incorrect depuis le passage a 23 canaux. Correct : 28 + 48×23 = 1132 octets → 3 univers necessaires. Le code est juste (dmx = 1536), seul le commentaire ment.
2. **`blackout_spots(n=19)` hardcode** : l'appel dans `demo_intro()` passe 19 implicitement. Si le layout change, cette valeur sera silencieusement incorrecte. Utiliser `len(POSITIONS)` comme valeur par defaut.
3. **Constante nommee** : `word_positions()` utilise `2430` comme plage pixel totale, valeur empirique non documentee. Extraire `SCREEN_PX_RANGE = 2430` en constante de module avec un commentaire expliquant son origine.

---

## Project-Visionary

1. Mode **performance live** : `python3 demo_scripts/defile_formes.py --interactive` — attend une frappe clavier (espace/entree) pour passer a la forme suivante au lieu de la duree fixe. Ideal pour des presentations ou l'orateur commente chaque forme.
2. Entree **OSC** (port 8000, bibliotheque standard uniquement) : recevoir `/forme N` pour sauter a la forme N, `/tempo X` pour modifier la duree courante. Ouvre le pilotage depuis TouchDesigner, Max/MSP ou un telephone.
3. **Forme #15 — Attracteur** : positions des spots calculees par un systeme de Lorenz discret (x,y → pan/tilt). Le chaos controle comme forme geometrique. Trois groupes d'attracteurs avec constantes differentes.

---

## Git-Specialist

1. **Committer les 7 fichiers modifies** (`M` dans `git status`) — ces changements representent une session complete de travail : boucle infinie, Segment, enable/blend creatifs, 20 polices, GUI nettoyee.
2. **Taguer `v1.0`** sur le commit resultant — ce commit represente le premier show complet en boucle infinie autonome, point de reference avant toute evolution majeure.
3. Verifier que `CLAUDE.md` dans `.gitignore` est intentionnel — les instructions de developpement ne sont pas disponibles pour un clone GitHub. Envisager une version publique `CONTRIBUTING.md` avec les conventions de base.

---

## Code-Quality-Auditor

**Score global : 7.5 / 10** (seance 2026-03-22, progression depuis 6.2)

Points positifs : stride 23 consistant, font_cache charge une fois au demarrage, _creative_enable_blend lisible malgre ses 70 lignes, _segment_effects correctement isolee du pipeline general.

1. **Commentaire errone dans `demo_finale()`** — mineur mais trompeur pour toute relecture future (voir Code-Expert-Pro #1).
2. **Valeur magique `2430`** dans `word_positions()` — non documentee, fragile si la resolution de fenetre change (voir Code-Expert-Pro #3).
3. **`blackout_spots(n=19)`** — defaut hardcode, risque silencieux (voir Code-Expert-Pro #2).
4. **Convention d'indexation DMX** : les indices `self.dmx[0]` a `self.dmx[27]` correspondent aux canaux DMX 1-28 (base 1). Cette convention est implicite dans tout le code. Un commentaire unique en en-tete de `defile_formes.py` eviterait toute confusion lors d'une reprise.

---

## Documentation-Specialist

1. **Deplacer `docs/ASSEMBLEE_GENERALE_2025.md` dans `docs/archive/`** — ce document date de septembre 2025 et a valeur historique uniquement. Il rompt la coherence du dossier `docs/` qui ne devrait contenir que la documentation active.
2. **Creer `CHANGELOG.md`** a la racine — trois entrees suffisent pour commencer : v0.1 (renommage LuxCore), v0.2 (multi-univers + 23 canaux), v1.0 (show complet boucle infinie). Permet a tout observateur du depot de comprendre l'evolution en 30 secondes.
3. Verifier que `python3 demo_scripts/artnet_text.py` lance bien une boucle infinie autonome (sans passer par `defile_formes.py`) — le README l'annonce ainsi mais `artnet_text.run()` a ete refactore. Si ce n'est plus le cas, mettre a jour le README.

---

## Recapitulatif seance 2026-03-22

| Theme | Priorite | Statut |
|---|---|---|
| Commentaire errone demo_finale (23ch) | basse | en attente |
| blackout_spots(n=len(POSITIONS)) | basse | en attente |
| Constante SCREEN_PX_RANGE | basse | en attente |
| Commit + tag v1.0 | haute | en attente |
| GDTF mis a jour 23 canaux | moyenne | en attente |
| ArtPollReply 3 univers | moyenne | en attente |
| ASSEMBLEE_GENERALE_2025 → archive | basse | en attente |
| CHANGELOG.md racine | basse | en attente |
| Mode --interactive | moyenne | en attente |
| Premiere demonstration publique | haute | en attente |

---

*Seance du 2026-03-22 — President : Martin Vert*

---

*Seance du 2026-03-18 — President : Martin Vert*
