# Recommandations — Assemblée des agents 2026-03-18

Rapport consolidé des 8 agents spécialisés sur l'état du projet LuxCore DMX Engine.

---

## 🎨 UI-Artist-Designer

1. Embarquer une police TTF dans `data/` pour le mode texte (rendu stable entre machines)
2. Affecter `blend_mode` global dans `do_blend_mode()` pour que le GUI soit honnête
3. Nommer `BLADE_BASE_OFFSET = 3` comme constante dans `definitions.pde`

---

## ⚡ Lighting-Designer-Expert

1. Produire un fichier **GDTF minimal** (20 canaux/spot) pour patcher dans MA3/Hog4/QLC+
2. Remplacer `map()` blend mode par une **LUT fixe** correspondant exactement à CLAUDE.md
3. Implémenter **ArtPollReply** (~239 octets) pour que LuxCore soit visible sur réseau ArtNet

---

## 💼 Business-Opportunity-Analyst

*(Rapport factuel — a choisi de décrire les cas d'usage réels plutôt que de prescrire)*

Cas d'usage identifiés :
- Visuel de scène pour concerts / DJ sets (intégration directe console DMX)
- Installation artistique autonome en galerie (`defile_formes.py` en boucle)
- Générateur de contenu typographique piloté ArtNet (`artnet_text.py`)
- Visualiseur de console DMX en loopback pour tests
- Prototypage de shows lumière

---

## 💻 Code-Expert-Pro

1. **One-liner** : affecter `blend_mode` global dans `do_blend_mode()`
2. Remplacer `concat()` par `System.arraycopy()` dans `do_artnet()` — zéro allocation par frame
3. `try/catch` autour du JSON dans `set_fullscreen()` — évite le crash silencieux au premier lancement

---

## 🚀 Project-Visionary

1. Canal de **blend mode individuel par spot** (+1 canal, 23 spots max)
2. Forme **"segment" / ligne ouverte** (mode 15)
3. Canal **enable/disable par spot** (court-circuite le pipeline sans toucher à l'alpha)
4. Police configurable dans le GUI
5. Documenter le mapping texte ASCII dans `z_fixture_definition.pde`
6. Exploiter réellement le **multi-univers** en Python pour dépasser 24 spots
7. Première **démonstration publique** avant d'ajouter des fonctionnalités

---

## 📚 Git-Specialist

1. Créer un **remote git** (GitHub/GitLab privé) + `git push` — protection contre perte totale
2. Merger `robustness-improvements` dans `master` (fast-forward propre) + supprimer la branche
3. Compléter `.gitignore` :
   - `__pycache__/`
   - `data/window_size.txt`
   - `data/bg/`
   - `linux-amd64/`
   - `data/gui/*/screenshots/`

---

## 🔍 Code-Quality-Auditor

**Score global : 6.2 / 10**

1. **Corriger les validations fantômes** dans `error_handling.pde` (`& 0xFF` rend tout toujours valide)
2. **Corriger `return_blend_mode()`** — affecter `blend_mode` global dans `do_blend_mode()`
3. **Supprimer les 11 variables mortes** dans `definitions.pde` (`spot_color`, `spot_alpha`, `spot_stroke`, `spot_stroke_alpha`, `spot_stroke_color`, `spot_size_pan`, `spot_size_tilt`, `spot_rotation`, `spot_position_pan`, `spot_position_tilt`, `spot_mode`) + liquider ou exclure `linux-amd64/`
4. **Extraire `luxcore_artnet.py`** — module Python partagé pour `set16()`, `send()`, `hsv()`, `char_tilt()`
5. **Sécuriser le parsing JSON** dans `set_fullscreen()` (index ordinal fragile, crash silencieux)

---

## 📖 Documentation-Specialist

1. **Unifier en base 0** toute la documentation DMX (doc actuellement en base 1, code en base 0)
2. **Déplacer docs fictives** dans `docs/archive/` :
   - `ARTISTIC_USAGE_GUIDE.md` (décrit un GUI inexistant)
   - `LUMIERES_ETERNELLES_MANIFESTO.md` (fonctionnalités non implémentées)
   - `demo_scripts/README.md` (référence des scripts inexistants)
3. **Créer `README.md` racine** : prérequis, lancement en 3 étapes, liens vers la doc

---

## Récapitulatif par thème

| Thème | Agents | Priorité |
|---|---|---|
| Bug `blend_mode` GUI (toujours "BLEND") | UI, Code-Expert, Quality | **Haute** |
| Remote git / backup | Git | **Urgence absolue** |
| Crash silencieux JSON au démarrage | Code-Expert, Quality | **Haute** |
| Variables mortes `definitions.pde` (×11) | Quality | Moyenne |
| Police TTF embarquée | UI, Visionary | Moyenne |
| Validations fantômes `error_handling.pde` | Quality | Moyenne |
| Module Python partagé `luxcore_artnet.py` | Quality | Moyenne |
| `.gitignore` complet | Git | Faible |
| Merger `master` | Git | Faible |
| README racine | Docs | Faible |
| Docs fictives à archiver | Docs | Faible |
| GDTF / intégration console pro | Lighting | Long terme |
| Nouvelles fonctionnalités (segment, enable, blend/spot) | Visionary | Long terme |

---

*Séance du 2026-03-18 — Président : Martin Vert*
