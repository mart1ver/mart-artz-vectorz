# GUIDE D'UTILISATION - LUMIÈRES ÉTERNELLES
## Comment utiliser votre nouveau système artistique

---

### DÉMARRAGE RAPIDE

1. **Lancer le programme** : Exécutez `martz_artz_verctorz.pde` dans Processing
2. **Configurer les spots** : Dans le GUI, définissez le nombre de spots (recommandé: 50-100)
3. **Démarrer la démo** : `python3 demo_scripts/defile_formes.py`
4. **Profiter de l'expérience** : Défilé des 15 formes avec effets et blades animés

---

### CONTRÔLES PRINCIPAUX

#### **Interface Graphique**
Le panneau `🎭 LUMIÈRES ÉTERNELLES` contient tous les contrôles:
- **START/STOP** : Démarre ou arrête la démo
- **Informations temps réel** : Mouvement actuel, progression, spots actifs
- **Jump to Movement** : Saut direct vers un mouvement spécifique
- **Durées configurables** : Ajustez la durée des mouvements et transitions

#### **Raccourcis Clavier** (Plus fluides pour les performances live)
```
ESPACE  : Démarrer/Arrêter la démo
1-7     : Saut direct vers les mouvements I-VII
R       : Redémarrer le mouvement actuel
N       : Mouvement suivant
P       : Mouvement précédent  
H       : Afficher l'aide
```

---

### PERSONNALISATION ARTISTIQUE

#### **Modification des Durées**
```processing
movement_duration = 60.0;    // Durée de chaque mouvement (30-180s)
transition_duration = 5.0;   // Durée des transitions (2-15s)
```

#### **Adaptation du Nombre de Spots**
- **Minimum recommandé** : 30 spots pour voir tous les effets
- **Optimal** : 50-80 spots pour l'expérience complète
- **Maximum** : 100 spots pour l'apothéose finale

#### **Modification des Palettes de Couleurs**
Éditez les couleurs thématiques par forme dans `demo_scripts/defile_formes.py` :
```python
FORMES = [
    {"id": 0, "nom": "Ellipse", "r": 220, "g": 80, "b": 80},
    # ... une entrée par forme, ajustez r/g/b
]
```

---

### UTILISATION EN PERFORMANCE LIVE

#### **Scénario 1: Démo Automatique Complète**
1. Démarrez la démo (ESPACE)
2. Laissez défiler les 7 mouvements automatiquement
3. Durée totale: ~8-10 minutes selon vos réglages

#### **Scénario 2: Contrôle Manuel Artistique**
1. Démarrez la démo (ESPACE)
2. Utilisez les touches 1-7 pour naviguer selon votre inspiration
3. Utilisez R pour répéter un moment particulièrement réussi
4. Créez votre propre séquence narrative

#### **Scénario 3: Présentation Éducative**
1. Expliquez chaque mouvement avant de le lancer
2. Utilisez les touches numériques pour montrer les différents styles
3. Référez-vous au manifeste pour expliquer les inspirations artistiques

---

### INTÉGRATION AVEC HARDWARE DMX

Le système fonctionne avec n'importe quel matériel DMX compatible Art-Net:
- **Consoles DMX** : Peuvent coexister ou reprendre le contrôle
- **Fixtures LED** : Spots, wash, matrices LED
- **Serveurs vidéo** : Pour projection architecturale
- **Systèmes hybrides** : Combinez avec d'autres contrôleurs

---

### TROUBLESHOOTING ARTISTIQUE

#### **"Pas assez de spots visibles"**
- Augmentez `number_of_spots` dans la config
- Vérifiez votre configuration Art-Net
- Certains mouvements utilisent moins de spots (Contemplation = 12)

#### **"Mouvements trop rapides/lents"**
- Ajustez `movement_duration` dans l'interface
- Modifiez `transition_duration` pour des changements plus doux

#### **"Couleurs pas assez vives"**
- Vérifiez la saturation de vos fixtures
- Les palettes sont conçues pour l'émotion, pas la saturation maximale

#### **"Effets PostFX trop intenses"**
- Réduisez les valeurs dans les fonctions de chaque mouvement
- Désactivez certains effets en commentant les lignes correspondantes

---

### EXTENSIONS POSSIBLES

#### **Nouveaux Mouvements**
Ajoutez vos propres mouvements en:
1. Créant une nouvelle fonction `movement_votre_nom(float phase)`
2. Ajoutant une palette de couleurs
3. Intégrant dans le switch de `execute_movement()`

#### **Synchronisation Audio**
Intégrez un analyseur audio pour synchroniser avec la musique:
```processing
// Exemple d'intégration
float audio_amplitude = getAudioLevel(); // Votre fonction audio
movement_duration = map(audio_amplitude, 0, 1, 45, 90);
```

#### **Contrôle OSC/MIDI**
Ajoutez des bibliothèques OSC ou MIDI pour contrôle externe depuis des surfaces de contrôle professionnelles.

---

### PERFORMANCES RECOMMANDÉES

#### **Pour Galeries d'Art**
- Durées longues (120-180s par mouvement)
- Transitions lentes (10-15s)
- Accent sur Contemplation et Renaissance

#### **Pour Concerts/Festivals**
- Durées moyennes (45-75s par mouvement) 
- Transitions rapides (3-5s)
- Accent sur Migration et Tempête

#### **Pour Espaces Méditation**
- Mouvements sélectionnés: Genesis, Respiration, Contemplation, Renaissance
- Transitions ultra-lentes (15s)
- Éviter Tempête

---

### SIGNATURE ARTISTIQUE

Quand vous utilisez LUMIÈRES ÉTERNELLES dans vos créations, n'hésitez pas à mentionner:
- **Conception artistique**: L'Artiste
- **Architecture technique**: LuxCore DMX Engine
- **Inspiration culturelle**: Les grands maîtres de l'art visuel

Cette œuvre représente la fusion parfaite entre tradition artistique et innovation technologique, créant des expériences émotionnelles qui transcendent le simple spectacle pour devenir de véritables moments d'art vivant.

---

*"Que la lumière soit votre pinceau et l'émotion votre toile."*

**Bon voyage dans les LUMIÈRES ÉTERNELLES !**