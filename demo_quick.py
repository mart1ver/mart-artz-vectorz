#!/usr/bin/env python3
"""
LUXCORE DÉMO RAPIDE - Script de test pour Claude Code
====================================================

Script simplifié pour tester rapidement les fonctions DMX
sans interface interactive.
"""

import sys
import os

# Ajouter le répertoire parent au path pour importer luxcore_demo
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from luxcore_demo import LuxCoreDMXController
import time

def demo_quick_test():
    """Test rapide des fonctionnalités principales"""
    print("🚀 LUXCORE - TEST RAPIDE")
    print("=" * 30)
    
    # Initialiser le contrôleur
    controller = LuxCoreDMXController()
    
    try:
        print("🔴 Test couleur rouge...")
        controller.set_all_spots_color(255, 0, 0)
        time.sleep(1)
        
        print("🟢 Test couleur verte...")
        controller.set_all_spots_color(0, 255, 0)
        time.sleep(1)
        
        print("🔵 Test couleur bleue...")
        controller.set_all_spots_color(0, 0, 255)
        time.sleep(1)
        
        print("🌑 Test blackout...")
        controller.blackout()
        time.sleep(0.5)
        
        print("⚡ Test spot individuel...")
        controller.set_spot_color(0, 255, 255, 0)  # Spot 0 en jaune
        controller.set_spot_color(1, 255, 0, 255)  # Spot 1 en magenta
        time.sleep(1)
        
        print("✅ Test rapide terminé avec succès!")
        
    except Exception as e:
        print(f"❌ Erreur lors du test: {e}")
        return False
    
    return True

def demo_spectacular():
    """Lance une séquence spectaculaire automatique"""
    print("🎭 LANCEMENT SÉQUENCE SPECTACULAIRE")
    print("=" * 40)
    
    controller = LuxCoreDMXController()
    
    try:
        print("🎬 Phase 1: Ouverture dramatique...")
        controller.demo_sequence_1_dramatic_opening()
        
        time.sleep(2)
        
        print("🌈 Phase 2: Explosion de couleurs...")  
        controller.demo_sequence_2_color_explosion()
        
        time.sleep(2)
        
        print("🌊 Phase 3: Effet vague...")
        controller.demo_sequence_3_wave_effect()
        
        print("🎉 SÉQUENCE SPECTACULAIRE TERMINÉE!")
        
    except KeyboardInterrupt:
        print("\n⏹️ Séquence interrompue par l'utilisateur")
        controller.stop_all_effects()
        controller.blackout()
    
    except Exception as e:
        print(f"❌ Erreur lors de la séquence: {e}")
        return False
    
    return True

def main():
    """Fonction principale avec sélection du mode"""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 demo_quick.py test        - Test rapide des fonctions")
        print("  python3 demo_quick.py spectacular - Séquence spectaculaire complète")
        print("  python3 demo_quick.py interactive - Interface interactive complète")
        return
    
    mode = sys.argv[1].lower()
    
    if mode == "test":
        demo_quick_test()
    elif mode == "spectacular":
        demo_spectacular()
    elif mode == "interactive":
        # Importer et lancer l'interface complète
        from luxcore_demo import main as interactive_main
        interactive_main()
    else:
        print(f"❌ Mode inconnu: {mode}")
        print("Modes disponibles: test, spectacular, interactive")

if __name__ == "__main__":
    main()