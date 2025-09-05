# 🎭 LUXCORE DMX ENGINE - SCRIPT DÉMO INTERACTIF

## 🎯 OBJECTIF
Script Python pilotable par Claude Code pour des démonstrations spectaculaires avec LuxCore via ArtNet.

## 📁 FICHIERS CRÉÉS

### Scripts Principaux
- **`luxcore_demo.py`** - Interface interactive complète avec toutes les fonctionnalités
- **`claude_demo.py`** - Script simplifié optimisé pour Claude Code 
- **`demo_quick.py`** - Script de test et séquences automatiques

### Documentation
- **`DEMO_INSTRUCTIONS.txt`** - Instructions détaillées d'utilisation
- **`PRESENTATION_DEMO.md`** - Ce fichier de présentation

## 🚀 UTILISATION RAPIDE POUR CLAUDE CODE

### Commandes Express (1 ligne)
```bash
python3 claude_demo.py demo1        # Ouverture dramatique
python3 claude_demo.py demo2        # Explosion de couleurs
python3 claude_demo.py demo3        # Effet vague  
python3 claude_demo.py spectacular  # Séquence complète
python3 claude_demo.py strobe       # Effet stroboscopique
```

### Contrôles Couleurs Rapides
```bash
python3 claude_demo.py red          # Tous spots rouge
python3 claude_demo.py green        # Tous spots vert
python3 claude_demo.py blue         # Tous spots bleu
python3 claude_demo.py white        # Éclairage blanc
python3 claude_demo.py rainbow      # Arc-en-ciel
python3 claude_demo.py blackout     # Extinction totale
```

### Contrôles Avancés
```bash
python3 claude_demo.py color 255 128 0      # Couleur orange tous spots
python3 claude_demo.py spot 0 255 0 0       # Spot 0 en rouge
python3 claude_demo.py test                 # Test rapide connection
```

## 🎬 SÉQUENCES SPECTACULAIRES

### 1. Ouverture Dramatique (`demo1`)
- Blackout initial dramatique
- Apparition progressive des spots un par un
- Couleurs dorées élégantes  
- Synchronisation finale avec flash
- Éclairage final puissant

### 2. Explosion de Couleurs (`demo2`) 
- Couleurs aléatoires dynamiques
- Positions changeantes en continu
- Tailles variables des spots
- Rythme rapide et énergique
- 7 couleurs différentes rotation

### 3. Effet Vague (`demo3`)
- Calculs sinusoïdaux pour fluidité
- Couleurs oscillantes RGB
- Positions en mouvement de vague
- Effet hypnotique et fluide
- 20 cycles de vague complète

### 4. Séquence Spectaculaire (`spectacular`)
- Enchaînement automatique des 3 séquences
- Timing optimisé entre les effets
- Démonstration complète de 2-3 minutes
- Idéal pour impressionner l'assemblée

## 🔧 ARCHITECTURE TECHNIQUE

### Protocole ArtNet
- **Port**: 6454 (standard ArtNet)
- **Cible**: 127.0.0.1 (localhost LuxCore)
- **Univers**: 0 (configurable)
- **Format**: Packets ArtNet standard

### Mapping DMX Analysé
- **Paramètres de base**: 20 canaux (0-19)
- **Paramètres par spot**: 19 canaux par spot
- **Nombre de spots**: 7 spots configurés
- **Total canaux utilisés**: ~153 canaux

### Structure des Spots
```
Spot N commence au canal: 20 + (N × 19)
- Canal +0: Rouge (R)
- Canal +1: Vert (G)  
- Canal +2: Bleu (B)
- Canal +3: Alpha/Intensité
- Canal +4: Position Pan
- Canal +5: Position Tilt
- Canal +6: Taille Pan
- Canal +7: Taille Tilt
- Canaux +8-18: Autres paramètres
```

## 🎭 SCÉNARIO DE DÉMONSTRATION

### Pour l'Assemblée Générale

1. **Préparation**
   ```bash
   # Démarrer LuxCore (Processing)
   # Vérifier la connection
   python3 claude_demo.py test
   ```

2. **Démonstration Rapide** (30 secondes)
   ```bash
   python3 claude_demo.py spectacular
   ```

3. **Contrôle Interactif par Claude**
   ```bash
   python3 luxcore_demo.py
   # Claude peut taper des commandes en direct
   ```

4. **Effets Express** (pendant présentation)
   ```bash
   python3 claude_demo.py red
   python3 claude_demo.py rainbow  
   python3 claude_demo.py strobe
   python3 claude_demo.py blackout
   ```

## 🎯 AVANTAGES POUR CLAUDE CODE

### Interface Simplifiée
- Commandes en une ligne
- Résultats immédiats dans LuxCore
- Aucune installation requise (stdlib Python)
- Messages de feedback clairs

### Contrôle Temps Réel
- Claude peut modifier les effets en direct
- Arrêt d'urgence avec Ctrl+C
- Passage fluide entre les séquences
- Contrôle individuel des spots

### Robustesse
- Gestion d'erreurs complète
- Timeout automatique des effets
- Validation des paramètres DMX
- Messages d'état informatifs

## 🏆 RÉSULTAT

**Un système complet permettant à Claude Code de "jouer" LuxCore comme un instrument pour créer des démonstrations visuelles spectaculaires et impressionner les 8 agents de l'assemblée générale.**

## 📞 SUPPORT

Pour toute question ou problème, les scripts incluent:
- Messages d'aide intégrés (`help` command)
- Validation des paramètres
- Messages d'erreur explicites
- Documentation complète

---
**Status**: ✅ **PRÊT POUR DÉMONSTRATION SPECTACULAIRE**