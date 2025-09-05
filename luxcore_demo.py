#!/usr/bin/env python3
"""
LUXCORE DMX ENGINE - SCRIPT DÉMO INTERACTIVE
============================================

Script Python pilotable par Claude Code pour envoyer des données ArtNet à LuxCore.
Permet des démonstrations spectaculaires en temps réel.

Architecture DMX analysée:
- 20 paramètres de base (univers 0, canaux 0-19)
- 19 paramètres par spot (canaux suivants)
- ArtNet sur 127.0.0.1 (localhost LuxCore)
- Univers 0 par défaut (configurable)

Usage:
    python3 luxcore_demo.py
    
Commandes disponibles:
    demo1, demo2, demo3    - Séquences pré-programmées
    red, green, blue       - Couleurs globales
    spot N color R G B     - Contrôle spot individuel
    pan N value            - Position horizontale spot N
    tilt N value           - Position verticale spot N
    size N value           - Taille spot N
    all color R G B        - Couleur tous spots
    blackout               - Extinction totale
    help                   - Afficher l'aide
    quit                   - Quitter
"""

import socket
import struct
import time
import sys
import threading
from typing import List, Tuple
import random
import math

class LuxCoreDMXController:
    """Contrôleur DMX pour LuxCore via ArtNet"""
    
    def __init__(self, target_ip: str = "127.0.0.1", universe: int = 0):
        self.target_ip = target_ip
        self.universe = universe
        self.port = 6454  # Port ArtNet standard
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        
        # Configuration DMX basée sur l'analyse du code Processing
        self.base_params = 20  # Paramètres globaux
        self.spot_params = 19  # Paramètres par spot
        self.max_spots = 7     # Nombre de spots par défaut
        
        # Buffer DMX (512 canaux par univers)
        self.dmx_data = [0] * 512
        
        # État des effets
        self.running_effects = []
        self.effect_thread = None
        self.stop_effects = False
        
        print(f"🎭 LuxCore DMX Controller initialisé")
        print(f"📡 Cible: {target_ip}:{self.port} - Univers: {universe}")
        print(f"🔧 Architecture: {self.base_params} params base + {self.spot_params} par spot")
    
    def send_artnet_packet(self) -> None:
        """Envoie un packet ArtNet avec les données DMX actuelles"""
        # Header ArtNet
        packet = bytearray()
        packet.extend(b"Art-Net\x00")  # ID
        packet.extend(struct.pack("<H", 0x5000))  # OpCode DMX
        packet.extend(struct.pack(">H", 14))  # Protocol version
        packet.append(0)  # Sequence
        packet.append(0)  # Physical
        packet.extend(struct.pack("<H", self.universe))  # Universe
        packet.extend(struct.pack(">H", 512))  # Data length
        packet.extend(self.dmx_data)  # DMX data
        
        self.sock.sendto(packet, (self.target_ip, self.port))
    
    def set_base_param(self, param_index: int, value: int) -> None:
        """Définit un paramètre de base (0-19)"""
        if 0 <= param_index < self.base_params:
            self.dmx_data[param_index] = max(0, min(255, value))
            self.send_artnet_packet()
    
    def set_spot_param(self, spot_num: int, param_index: int, value: int) -> None:
        """Définit un paramètre de spot spécifique"""
        if 0 <= spot_num < self.max_spots and 0 <= param_index < self.spot_params:
            dmx_address = self.base_params + (spot_num * self.spot_params) + param_index
            if dmx_address < 512:
                self.dmx_data[dmx_address] = max(0, min(255, value))
                self.send_artnet_packet()
    
    def set_spot_color(self, spot_num: int, r: int, g: int, b: int) -> None:
        """Définit la couleur RGB d'un spot"""
        # Mapping basé sur l'analyse du code (positions estimées)
        self.set_spot_param(spot_num, 0, r)  # Rouge
        self.set_spot_param(spot_num, 1, g)  # Vert  
        self.set_spot_param(spot_num, 2, b)  # Bleu
        self.set_spot_param(spot_num, 3, 255)  # Alpha/Intensité
    
    def set_spot_position(self, spot_num: int, pan: int, tilt: int) -> None:
        """Définit la position pan/tilt d'un spot"""
        self.set_spot_param(spot_num, 4, pan)   # Pan
        self.set_spot_param(spot_num, 5, tilt)  # Tilt
    
    def set_spot_size(self, spot_num: int, size_pan: int, size_tilt: int = None) -> None:
        """Définit la taille d'un spot"""
        if size_tilt is None:
            size_tilt = size_pan
        self.set_spot_param(spot_num, 6, size_pan)   # Taille Pan
        self.set_spot_param(spot_num, 7, size_tilt)  # Taille Tilt
    
    def set_all_spots_color(self, r: int, g: int, b: int) -> None:
        """Définit la couleur de tous les spots"""
        for i in range(self.max_spots):
            self.set_spot_color(i, r, g, b)
    
    def blackout(self) -> None:
        """Extinction totale"""
        for i in range(512):
            self.dmx_data[i] = 0
        self.send_artnet_packet()
        print("🌑 Blackout activé")
    
    def stop_all_effects(self) -> None:
        """Arrête tous les effets en cours"""
        self.stop_effects = True
        if self.effect_thread and self.effect_thread.is_alive():
            self.effect_thread.join(timeout=1.0)
        self.running_effects.clear()
        self.stop_effects = False
    
    def effect_runner(self, effect_func, *args, **kwargs) -> None:
        """Lance un effet dans un thread séparé"""
        self.stop_all_effects()
        self.effect_thread = threading.Thread(
            target=effect_func, 
            args=args, 
            kwargs=kwargs,
            daemon=True
        )
        self.effect_thread.start()
    
    # SÉQUENCES SPECTACULAIRES
    
    def demo_sequence_1_dramatic_opening(self) -> None:
        """🎭 SÉQUENCE 1: Ouverture dramatique"""
        print("🎭 Lancement: Ouverture dramatique...")
        
        # Phase 1: Blackout total
        self.blackout()
        time.sleep(1)
        
        # Phase 2: Apparition progressive des spots un par un
        for spot in range(self.max_spots):
            if self.stop_effects:
                return
            
            # Couleur dorée progressive
            for intensity in range(0, 256, 5):
                if self.stop_effects:
                    return
                self.set_spot_color(spot, intensity, intensity//2, 0)
                time.sleep(0.02)
            
            # Position aléatoire élégante
            pan = random.randint(64, 192)
            tilt = random.randint(64, 192)
            self.set_spot_position(spot, pan, tilt)
            time.sleep(0.3)
        
        # Phase 3: Synchronisation finale
        for i in range(3):
            if self.stop_effects:
                return
            self.set_all_spots_color(255, 200, 0)
            time.sleep(0.2)
            self.set_all_spots_color(0, 0, 0)
            time.sleep(0.2)
        
        # Phase 4: Éclairage final puissant
        self.set_all_spots_color(255, 255, 255)
        print("✨ Ouverture dramatique terminée!")
    
    def demo_sequence_2_color_explosion(self) -> None:
        """🌈 SÉQUENCE 2: Explosion de couleurs"""
        print("🌈 Lancement: Explosion de couleurs...")
        
        colors = [
            (255, 0, 0),    # Rouge
            (0, 255, 0),    # Vert
            (0, 0, 255),    # Bleu
            (255, 255, 0),  # Jaune
            (255, 0, 255),  # Magenta
            (0, 255, 255),  # Cyan
            (255, 128, 0),  # Orange
        ]
        
        for cycle in range(10):
            if self.stop_effects:
                return
            
            for spot in range(self.max_spots):
                if self.stop_effects:
                    return
                
                # Couleur aléatoire
                color = random.choice(colors)
                self.set_spot_color(spot, *color)
                
                # Position dynamique
                pan = random.randint(0, 255)
                tilt = random.randint(0, 255)
                self.set_spot_position(spot, pan, tilt)
                
                # Taille variable
                size = random.randint(50, 200)
                self.set_spot_size(spot, size)
                
                time.sleep(0.1)
        
        print("🎆 Explosion de couleurs terminée!")
    
    def demo_sequence_3_wave_effect(self) -> None:
        """🌊 SÉQUENCE 3: Effet vague"""
        print("🌊 Lancement: Effet vague...")
        
        for wave in range(20):
            if self.stop_effects:
                return
            
            t = wave * 0.5
            
            for spot in range(self.max_spots):
                if self.stop_effects:
                    return
                
                # Calcul sinusoïdal pour l'effet vague
                phase = (spot * math.pi * 2 / self.max_spots) + t
                
                # Couleur oscillante
                r = int((math.sin(phase) + 1) * 127)
                g = int((math.sin(phase + math.pi/3) + 1) * 127)
                b = int((math.sin(phase + 2*math.pi/3) + 1) * 127)
                
                self.set_spot_color(spot, r, g, b)
                
                # Position en vague
                pan = int((math.sin(phase) + 1) * 127)
                tilt = int((math.cos(phase) + 1) * 127)
                self.set_spot_position(spot, pan, tilt)
            
            time.sleep(0.1)
        
        print("🌊 Effet vague terminé!")
    
    def demo_sequence_strobe(self) -> None:
        """⚡ SÉQUENCE: Effet stroboscopique"""
        print("⚡ Lancement: Effet stroboscopique...")
        
        for i in range(20):
            if self.stop_effects:
                return
            self.set_all_spots_color(255, 255, 255)
            time.sleep(0.05)
            self.blackout()
            time.sleep(0.05)
        
        print("⚡ Effet stroboscopique terminé!")

def print_help():
    """Affiche l'aide des commandes"""
    help_text = """
🎭 LUXCORE DMX ENGINE - COMMANDES DISPONIBLES
=============================================

🎬 SÉQUENCES SPECTACULAIRES:
  demo1                    - Ouverture dramatique
  demo2                    - Explosion de couleurs  
  demo3                    - Effet vague
  strobe                   - Effet stroboscopique

🎨 COULEURS GLOBALES:
  red                      - Tous spots en rouge
  green                    - Tous spots en vert
  blue                     - Tous spots en bleu
  white                    - Tous spots en blanc
  rainbow                  - Arc-en-ciel aléatoire

🎯 CONTRÔLE INDIVIDUEL:
  spot N color R G B       - Couleur spot N (ex: spot 0 color 255 0 0)
  pan N value              - Position horizontale spot N (0-255)
  tilt N value             - Position verticale spot N (0-255)
  size N value             - Taille spot N (0-255)

🔧 UTILITAIRES:
  all color R G B          - Couleur tous spots (ex: all color 255 128 0)
  blackout                 - Extinction totale
  stop                     - Arrêter tous les effets
  status                   - État du contrôleur
  help                     - Afficher cette aide
  quit / exit              - Quitter

💡 EXEMPLES:
  > demo1                  # Lance l'ouverture dramatique
  > spot 0 color 255 0 0   # Spot 0 en rouge pur
  > all color 0 255 0      # Tous spots en vert
  > pan 2 128              # Spot 2 au centre horizontal
"""
    print(help_text)

def main():
    """Fonction principale - Interface interactive"""
    print("🎭 LUXCORE DMX ENGINE - DÉMO INTERACTIVE")
    print("=" * 50)
    print("Initialisation du contrôleur DMX...")
    
    # Initialiser le contrôleur
    controller = LuxCoreDMXController()
    
    print("✅ Contrôleur prêt! Tapez 'help' pour voir les commandes.")
    print("🎬 Prêt pour la démonstration spectaculaire!")
    print()
    
    # Boucle interactive
    while True:
        try:
            command = input("LuxCore> ").strip().lower()
            
            if not command:
                continue
            
            parts = command.split()
            cmd = parts[0]
            
            # Commandes de sortie
            if cmd in ['quit', 'exit', 'q']:
                controller.stop_all_effects()
                print("👋 Arrêt du contrôleur LuxCore DMX. Au revoir!")
                break
            
            # Aide
            elif cmd == 'help':
                print_help()
            
            # Séquences spectaculaires
            elif cmd == 'demo1':
                controller.effect_runner(controller.demo_sequence_1_dramatic_opening)
            
            elif cmd == 'demo2':
                controller.effect_runner(controller.demo_sequence_2_color_explosion)
            
            elif cmd == 'demo3':
                controller.effect_runner(controller.demo_sequence_3_wave_effect)
            
            elif cmd == 'strobe':
                controller.effect_runner(controller.demo_sequence_strobe)
            
            # Couleurs globales rapides
            elif cmd == 'red':
                controller.stop_all_effects()
                controller.set_all_spots_color(255, 0, 0)
                print("🔴 Tous spots: Rouge")
            
            elif cmd == 'green':
                controller.stop_all_effects()
                controller.set_all_spots_color(0, 255, 0)
                print("🟢 Tous spots: Vert")
            
            elif cmd == 'blue':
                controller.stop_all_effects()
                controller.set_all_spots_color(0, 0, 255)
                print("🔵 Tous spots: Bleu")
            
            elif cmd == 'white':
                controller.stop_all_effects()
                controller.set_all_spots_color(255, 255, 255)
                print("⚪ Tous spots: Blanc")
            
            elif cmd == 'rainbow':
                controller.stop_all_effects()
                colors = [(255,0,0), (0,255,0), (0,0,255), (255,255,0), (255,0,255), (0,255,255)]
                for i in range(controller.max_spots):
                    color = colors[i % len(colors)]
                    controller.set_spot_color(i, *color)
                print("🌈 Arc-en-ciel activé")
            
            elif cmd == 'blackout':
                controller.stop_all_effects()
                controller.blackout()
            
            elif cmd == 'stop':
                controller.stop_all_effects()
                print("⏹️ Tous les effets arrêtés")
            
            # Contrôle individuel des spots
            elif cmd == 'spot' and len(parts) >= 5:
                try:
                    spot_num = int(parts[1])
                    if parts[2] == 'color':
                        r, g, b = int(parts[3]), int(parts[4]), int(parts[5])
                        controller.stop_all_effects()
                        controller.set_spot_color(spot_num, r, g, b)
                        print(f"🎯 Spot {spot_num}: RGB({r},{g},{b})")
                    else:
                        print("❌ Usage: spot N color R G B")
                except (ValueError, IndexError):
                    print("❌ Valeurs invalides. Usage: spot N color R G B")
            
            elif cmd == 'pan' and len(parts) >= 3:
                try:
                    spot_num = int(parts[1])
                    value = int(parts[2])
                    controller.stop_all_effects()
                    current_tilt = 128  # Valeur par défaut
                    controller.set_spot_position(spot_num, value, current_tilt)
                    print(f"↔️ Spot {spot_num}: Pan = {value}")
                except (ValueError, IndexError):
                    print("❌ Usage: pan N value")
            
            elif cmd == 'tilt' and len(parts) >= 3:
                try:
                    spot_num = int(parts[1])
                    value = int(parts[2])
                    controller.stop_all_effects()
                    current_pan = 128  # Valeur par défaut
                    controller.set_spot_position(spot_num, current_pan, value)
                    print(f"↕️ Spot {spot_num}: Tilt = {value}")
                except (ValueError, IndexError):
                    print("❌ Usage: tilt N value")
            
            elif cmd == 'size' and len(parts) >= 3:
                try:
                    spot_num = int(parts[1])
                    value = int(parts[2])
                    controller.stop_all_effects()
                    controller.set_spot_size(spot_num, value)
                    print(f"📏 Spot {spot_num}: Taille = {value}")
                except (ValueError, IndexError):
                    print("❌ Usage: size N value")
            
            elif cmd == 'all' and len(parts) >= 5:
                try:
                    if parts[1] == 'color':
                        r, g, b = int(parts[2]), int(parts[3]), int(parts[4])
                        controller.stop_all_effects()
                        controller.set_all_spots_color(r, g, b)
                        print(f"🎨 Tous spots: RGB({r},{g},{b})")
                    else:
                        print("❌ Usage: all color R G B")
                except (ValueError, IndexError):
                    print("❌ Valeurs invalides. Usage: all color R G B")
            
            elif cmd == 'status':
                print(f"📊 Contrôleur: {controller.target_ip}:{controller.port}")
                print(f"🌐 Univers: {controller.universe}")
                print(f"🎯 Spots configurés: {controller.max_spots}")
                print(f"⚡ Effets en cours: {len(controller.running_effects)}")
            
            else:
                print(f"❌ Commande inconnue: '{command}'")
                print("💡 Tapez 'help' pour voir les commandes disponibles")
        
        except KeyboardInterrupt:
            controller.stop_all_effects()
            print("\n👋 Arrêt du contrôleur. Au revoir!")
            break
        
        except Exception as e:
            print(f"❌ Erreur: {e}")
            print("💡 Tapez 'help' pour voir les commandes disponibles")

if __name__ == "__main__":
    main()