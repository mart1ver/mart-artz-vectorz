#!/usr/bin/env python3
"""
SCRIPT DE DÉMONSTRATION EXPRESS POUR CLAUDE CODE
=================================================

Script optimisé pour les commandes directes de Claude Code.
Permet de lancer des effets spectaculaires d'une seule ligne.
"""

import sys
from luxcore_demo import LuxCoreDMXController
import time

def execute_command(cmd_args):
    """Exécute une commande DMX et retourne le résultat"""
    controller = LuxCoreDMXController()
    
    if not cmd_args:
        return "❌ Aucune commande fournie"
    
    cmd = cmd_args[0].lower()
    
    try:
        if cmd == "test":
            # Test rapide
            controller.set_all_spots_color(255, 0, 0)
            time.sleep(0.5)
            controller.set_all_spots_color(0, 255, 0) 
            time.sleep(0.5)
            controller.set_all_spots_color(0, 0, 255)
            time.sleep(0.5)
            controller.blackout()
            return "✅ Test couleurs terminé"
        
        elif cmd == "demo1":
            controller.demo_sequence_1_dramatic_opening()
            return "🎭 Ouverture dramatique terminée"
        
        elif cmd == "demo2": 
            controller.demo_sequence_2_color_explosion()
            return "🌈 Explosion de couleurs terminée"
        
        elif cmd == "demo3":
            controller.demo_sequence_3_wave_effect()  
            return "🌊 Effet vague terminé"
        
        elif cmd == "strobe":
            controller.demo_sequence_strobe()
            return "⚡ Effet stroboscopique terminé"
        
        elif cmd == "red":
            controller.set_all_spots_color(255, 0, 0)
            return "🔴 Tous spots: Rouge"
        
        elif cmd == "green":
            controller.set_all_spots_color(0, 255, 0)
            return "🟢 Tous spots: Vert"
        
        elif cmd == "blue":
            controller.set_all_spots_color(0, 0, 255)
            return "🔵 Tous spots: Bleu"
        
        elif cmd == "white":
            controller.set_all_spots_color(255, 255, 255)
            return "⚪ Tous spots: Blanc"
        
        elif cmd == "rainbow":
            colors = [(255,0,0), (0,255,0), (0,0,255), (255,255,0), (255,0,255), (0,255,255)]
            for i in range(controller.max_spots):
                color = colors[i % len(colors)]
                controller.set_spot_color(i, *color)
            return "🌈 Arc-en-ciel activé"
        
        elif cmd == "blackout":
            controller.blackout()
            return "🌑 Blackout activé"
        
        elif cmd == "spectacular":
            # Séquence complète pour impressionner
            print("🎭 SÉQUENCE SPECTACULAIRE DÉMARRÉE")
            controller.demo_sequence_1_dramatic_opening()
            time.sleep(1)
            controller.demo_sequence_2_color_explosion() 
            time.sleep(1)
            controller.demo_sequence_3_wave_effect()
            return "🎉 SÉQUENCE SPECTACULAIRE TERMINÉE!"
        
        elif cmd == "color" and len(cmd_args) >= 4:
            r, g, b = int(cmd_args[1]), int(cmd_args[2]), int(cmd_args[3])
            controller.set_all_spots_color(r, g, b)
            return f"🎨 Couleur RGB({r},{g},{b}) appliquée"
        
        elif cmd == "spot" and len(cmd_args) >= 5:
            spot_num = int(cmd_args[1])
            r, g, b = int(cmd_args[2]), int(cmd_args[3]), int(cmd_args[4])
            controller.set_spot_color(spot_num, r, g, b)
            return f"🎯 Spot {spot_num}: RGB({r},{g},{b})"
        
        else:
            return f"❌ Commande inconnue: {cmd}"
    
    except Exception as e:
        return f"❌ Erreur: {e}"

def main():
    """Point d'entrée principal"""
    if len(sys.argv) < 2:
        print("""
🎭 LUXCORE CLAUDE DEMO - Commandes disponibles:

🎬 SÉQUENCES:
  python3 claude_demo.py demo1        # Ouverture dramatique
  python3 claude_demo.py demo2        # Explosion couleurs  
  python3 claude_demo.py demo3        # Effet vague
  python3 claude_demo.py spectacular  # Séquence complète
  python3 claude_demo.py strobe       # Stroboscope

🎨 COULEURS:
  python3 claude_demo.py red          # Rouge
  python3 claude_demo.py green        # Vert
  python3 claude_demo.py blue         # Bleu
  python3 claude_demo.py white        # Blanc
  python3 claude_demo.py rainbow      # Arc-en-ciel
  python3 claude_demo.py blackout     # Extinction

🔧 AVANCÉ:
  python3 claude_demo.py color R G B        # Couleur custom tous spots
  python3 claude_demo.py spot N R G B       # Couleur spot spécifique
  python3 claude_demo.py test               # Test rapide
        """)
        return
    
    # Exécuter la commande
    result = execute_command(sys.argv[1:])
    print(result)

if __name__ == "__main__":
    main()