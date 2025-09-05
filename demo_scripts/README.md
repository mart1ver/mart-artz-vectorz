# 🎭 LuxCore DMX Engine - Scripts de Démonstration

Scripts Python pour contrôler LuxCore DMX Engine via ArtNet, spécialement conçus pour les démonstrations de l'Assemblée Générale.

## 📁 Fichiers Inclus

### `claude_demo.py` - Contrôle par Claude Code
Script optimisé pour utilisation directe par Claude Code via ligne de commande.

**Usage :**
```bash
python3 claude_demo.py [command]
```

**Commandes disponibles :**
- `demo1` - Ouverture dramatique avec fondu
- `demo2` - Explosion de couleurs multiples  
- `demo3` - Effet de vague colorée
- `spectacular` - Séquence complète spectaculaire
- `strobe` - Effet stroboscope
- `red`, `green`, `blue`, `white`, `yellow`, `purple`, `cyan` - Couleurs rapides
- `blackout` - Extinction totale
- `test` - Test de connexion

### `luxcore_demo.py` - Mode Interactif Complet
Script avec interface interactive pour contrôle avancé.

**Usage :**
```bash
python3 luxcore_demo.py          # Mode interactif
python3 luxcore_demo.py demo     # Séquence automatique
python3 luxcore_demo.py test     # Test de connexion
```

## 🎯 Configuration LuxCore

**Avant utilisation, vérifier dans LuxCore :**
- Interface réseau : `127.0.0.1` (localhost)
- Univers de départ : `0`
- Nombre de spots : `7` minimum configuré

## 🚀 Démonstration Express

**Pour impressionner l'assemblée :**

1. **Démarrer LuxCore** (Processing)
2. **Test rapide :**
   ```bash
   python3 claude_demo.py test
   ```
3. **Séquence spectaculaire :**
   ```bash
   python3 claude_demo.py spectacular
   ```

## ⚡ Architecture DMX Utilisée

- **20 paramètres de base** (background, blend modes, effets)
- **19 paramètres par spot** (couleurs, positions, tailles, formes)
- **Protocol ArtNet** sur port 6454
- **Adressage 16-bit** pour positions et tailles précises

## 🎨 Effets Visuels Inclus

- **Fondus colorés** progressifs
- **Animations de positions** en temps réel  
- **Rotations** dynamiques
- **Blend modes** (ADD, MULTIPLY, etc.)
- **Formes multiples** (rectangles, ellipses, étoiles)
- **Effets post-traitement** (blur, RGB split)

## 🔧 Dépendances

**Aucune dépendance externe** - 100% Python stdlib
- `socket` - Communication réseau ArtNet
- `struct` - Formatage packets DMX
- `time` - Timing des séquences
- `math` - Calculs trigonométriques pour animations

## 🎪 Utilisation par Claude Code

Claude peut exécuter ces commandes directement :

```bash
# Tests et démonstrations
python3 demo_scripts/claude_demo.py test
python3 demo_scripts/claude_demo.py spectacular

# Contrôle couleurs
python3 demo_scripts/claude_demo.py red
python3 demo_scripts/claude_demo.py rainbow

# Effets spéciaux
python3 demo_scripts/claude_demo.py strobe
python3 demo_scripts/claude_demo.py demo3
```

---

**Créé pour l'Assemblée Générale LuxCore DMX Engine**  
**Auteur :** Martin Vert  
**Scripts :** Optimisés pour démonstration Claude Code