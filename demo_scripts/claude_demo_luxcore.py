#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LuxCore DMX Engine - Claude Code Controller (MISE À JOUR 2025)
Script optimisé pour la nouvelle empreinte DMX avec blades 16-bit
Usage: python3 claude_demo_luxcore.py [command]
"""

import socket
import struct
import time
import math
import sys

class ClaudeLuxController:
    def __init__(self, target_ip="127.0.0.1"):
        self.target_ip = target_ip
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.dmx_data = [0] * 512
        
    def send_artnet(self):
        """Send ArtNet packet to LuxCore - CORRECT FORMAT"""
        header = b"Art-Net\x00"
        opcode = struct.pack("<H", 0x5000)  # ArtDMX 
        prot_ver_hi = 0
        prot_ver_lo = 14
        sequence = 0
        physical = 0
        sub_uni = 0
        net = 0
        length_hi = (len(self.dmx_data) >> 8) & 0xFF
        length_lo = len(self.dmx_data) & 0xFF
        
        packet = (header + 
                  opcode + 
                  bytes([prot_ver_hi, prot_ver_lo, sequence, physical, sub_uni, net, length_hi, length_lo]) +
                  bytes(self.dmx_data))
        
        self.socket.sendto(packet, (self.target_ip, 6454))

    def set_blade_16bit(self, channel_msb, value):
        """Configure une blade 16-bit (MSB/LSB)"""
        value = max(0, min(65535, int(value)))
        msb = (value >> 8) & 0xFF
        lsb = value & 0xFF
        self.dmx_data[channel_msb - 1] = msb  # Canal MSB (index-1 car channels 1-based)
        self.dmx_data[channel_msb] = lsb      # Canal LSB

    def set_blades_minimal(self):
        """Configure toutes les blades quasi-ouvertes (0-3%)"""
        # Valeurs très faibles pour visibilité maximale
        blade_values = [800, 600, 700, 500, 900, 650, 750, 850]  # 0.7-1.3% environ
        
        for i, value in enumerate(blade_values):
            channel_msb = 3 + (i * 2)  # Canaux 3,5,7,9,11,13,15,17 pour MSB
            self.set_blade_16bit(channel_msb, value)

    def set_spot_param(self, spot_id, param, value):
        """Configure un paramètre d'un spot spécifique"""
        base_addr = 28 + (spot_id * 19)  # 28 canaux base + 19 par spot
        
        if param == "rgb":
            r, g, b = value
            self.dmx_data[base_addr] = r
            self.dmx_data[base_addr + 1] = g
            self.dmx_data[base_addr + 2] = b
        elif param == "alpha":
            self.dmx_data[base_addr + 3] = value
        elif param == "size":
            # Taille 16-bit (pan et tilt identiques)
            self.set_blade_16bit(base_addr + 9, value)   # Size pan MSB/LSB
            self.set_blade_16bit(base_addr + 11, value)  # Size tilt MSB/LSB
        elif param == "position":
            pan, tilt = value
            self.set_blade_16bit(base_addr + 14, pan)   # Pan MSB/LSB
            self.set_blade_16bit(base_addr + 16, tilt)  # Tilt MSB/LSB
        elif param == "rotation":
            self.dmx_data[base_addr + 13] = value
        elif param == "mode":
            self.dmx_data[base_addr + 18] = value

    def demo1_opening(self):
        """Ouverture dramatique avec fondu"""
        print("🎭 Ouverture dramatique LuxCore...")
        
        # Configuration blades minimales
        self.set_blades_minimal()
        
        for i in range(0, 255, 5):
            # Couleurs de base
            self.dmx_data[0] = i//3  # Rouge background
            self.dmx_data[1] = 0     # Vert background  
            self.dmx_data[2] = i//2  # Bleu background
            
            # Mode de mélange normal
            self.dmx_data[19] = 0    # Canal 20 - Blend mode
            
            # Spot central qui grandit
            self.set_spot_param(0, "rgb", (255, i, 255))
            self.set_spot_param(0, "alpha", i)
            self.set_spot_param(0, "size", i * 200)
            self.set_spot_param(0, "position", (32767, 32767))  # Centre 16-bit
            self.set_spot_param(0, "mode", 1)  # Ellipse
            
            self.send_artnet()
            time.sleep(0.05)

    def demo2_explosion(self):
        """Explosion de couleurs multiples"""
        print("💥 Explosion de couleurs LuxCore...")
        
        # Mode ADD pour brillance maximum
        self.dmx_data[19] = 51  # Canal 20 - ADD blend mode
        
        # Configuration blades minimales
        self.set_blades_minimal()
        
        colors = [(255,0,0), (0,255,0), (0,0,255), (255,255,0), (255,0,255), (0,255,255), (255,128,0)]
        
        for i, (r, g, b) in enumerate(colors[:7]):  # Max 7 spots
            # Configuration spot
            self.set_spot_param(i, "rgb", (r, g, b))
            self.set_spot_param(i, "alpha", 255)
            self.set_spot_param(i, "size", 15000)
            
            # Position en cercle
            angle = i * (360 / 7)  # Répartition équitable
            radius = 0.4
            pan = int(32767 + radius * 25000 * math.cos(math.radians(angle)))
            tilt = int(32767 + radius * 25000 * math.sin(math.radians(angle)))
            
            self.set_spot_param(i, "position", (pan, tilt))
            self.set_spot_param(i, "mode", 1)  # Ellipse
        
        self.send_artnet()

    def demo3_wave(self):
        """Effet de vague colorée avec effets spéciaux"""
        print("🌊 Effet vague + effets LuxCore...")
        
        # Configuration blades minimales
        self.set_blades_minimal()
        
        for frame in range(200):
            # Effet RGB Split progressif
            self.dmx_data[24] = int(abs(50 * math.sin(frame * 0.1)))  # Canal 25 - RGB Split
            
            # Effet Blur léger
            self.dmx_data[20] = int(abs(10 + 5 * math.sin(frame * 0.05)))  # Canal 21 - Blur A
            
            for i in range(7):
                # Couleur qui ondule
                hue = (frame + i * 30) % 360
                r = int(127 + 127 * math.sin(math.radians(hue)))
                g = int(127 + 127 * math.sin(math.radians(hue + 120)))
                b = int(127 + 127 * math.sin(math.radians(hue + 240)))
                
                self.set_spot_param(i, "rgb", (r, g, b))
                self.set_spot_param(i, "alpha", 255)
                
                # Position qui ondule
                pos_x = 32767 + int(20000 * math.sin(math.radians(frame * 8 + i * 40)))
                pos_y = 32767 + int(15000 * math.cos(math.radians(frame * 6 + i * 50)))
                
                self.set_spot_param(i, "position", (pos_x, pos_y))
                self.set_spot_param(i, "size", 8000)
                self.set_spot_param(i, "rotation", (frame * 5 + i * 20) % 256)
                self.set_spot_param(i, "mode", 0)  # Rectangle
            
            self.send_artnet()
            time.sleep(0.05)
        
        # Reset effets
        self.dmx_data[24] = 0  # RGB Split off
        self.dmx_data[20] = 0  # Blur off
        self.send_artnet()

    def demo4_effects_showcase(self):
        """Showcase de tous les effets spéciaux"""
        print("✨ Showcase effets spéciaux LuxCore...")
        
        # Configuration spots visibles
        for i in range(5):
            self.set_spot_param(i, "rgb", (200, 150, 255))
            self.set_spot_param(i, "alpha", 200)
            self.set_spot_param(i, "size", 12000)
            
            angle = i * 72  # 5 spots en pentagon
            pan = int(32767 + 18000 * math.cos(math.radians(angle)))
            tilt = int(32767 + 18000 * math.sin(math.radians(angle)))
            self.set_spot_param(i, "position", (pan, tilt))
            self.set_spot_param(i, "mode", 1)
        
        effects = [
            ("Pixelate", 22, [0, 50, 100, 150, 200, 100, 50, 0]),
            ("RGB Split", 24, [0, 30, 60, 90, 60, 30, 0]),
            ("Blur", 20, [0, 8, 15, 25, 15, 8, 0]),
            ("Saturation", 25, [128, 180, 230, 255, 200, 150, 128]),
            ("Chromatic Aberration", 27, [0, 128, 255, 128, 0])
        ]
        
        for effect_name, channel, values in effects:
            print(f"   → {effect_name}")
            for value in values:
                self.dmx_data[channel] = value
                self.send_artnet()
                time.sleep(0.8)
            # Reset
            self.dmx_data[channel] = 0
            self.send_artnet()
            time.sleep(0.5)

    def spectacular_sequence(self):
        """Séquence complète spectaculaire"""
        print("🎉 SÉQUENCE SPECTACULAIRE LUXCORE 2025!")
        print("   → Nouvelle empreinte DMX 28 canaux + blades 16-bit")
        
        self.demo1_opening()
        time.sleep(2)
        self.demo2_explosion()
        time.sleep(3)
        self.demo3_wave()
        time.sleep(2)
        self.demo4_effects_showcase()
        time.sleep(1)
        self.strobe_effect()
        print("✨ Démonstration LuxCore terminée!")

    def strobe_effect(self):
        """Effet stroboscope avec blend modes"""
        print("⚡ Effet stroboscope LuxCore...")
        
        # Configuration blades minimales
        self.set_blades_minimal()
        
        # Mode LIGHTEST pour strobe intense
        self.dmx_data[19] = 127  # LIGHTEST blend mode
        
        for i in range(30):
            if i % 2:
                # Tout allumé - couleurs vives
                for spot in range(7):
                    color = [(255,0,0), (0,255,0), (0,0,255), (255,255,0), (255,0,255), (0,255,255), (255,255,255)][spot]
                    self.set_spot_param(spot, "rgb", color)
                    self.set_spot_param(spot, "alpha", 255)
                    self.set_spot_param(spot, "size", 20000)
            else:
                # Tout éteint
                for spot in range(7):
                    self.set_spot_param(spot, "alpha", 0)
            
            self.send_artnet()
            time.sleep(0.1)
        
        # Reset blend mode
        self.dmx_data[19] = 0

    def quick_colors(self, color_name):
        """Couleurs rapides avec nouvelle empreinte"""
        colors = {
            'red': (255, 0, 0),
            'green': (0, 255, 0), 
            'blue': (0, 0, 255),
            'white': (255, 255, 255),
            'yellow': (255, 255, 0),
            'purple': (255, 0, 255),
            'cyan': (0, 255, 255),
            'orange': (255, 128, 0),
            'pink': (255, 150, 200)
        }
        
        if color_name in colors:
            r, g, b = colors[color_name]
            print(f"🎨 Couleur LuxCore: {color_name}")
            
            # Background
            self.dmx_data[0] = r//4  # Plus subtil
            self.dmx_data[1] = g//4  
            self.dmx_data[2] = b//4
            
            # Blades minimales
            self.set_blades_minimal()
            
            # Tous les spots (7 max)
            for i in range(7):
                self.set_spot_param(i, "rgb", (r, g, b))
                self.set_spot_param(i, "alpha", 255)
                self.set_spot_param(i, "size", 10000)
                
                # Position en grille
                row = i // 3
                col = i % 3
                pan = int(32767 + (col - 1) * 15000)
                tilt = int(32767 + (row - 1) * 12000)
                self.set_spot_param(i, "position", (pan, tilt))
                self.set_spot_param(i, "mode", i % 3)  # Formes variées
            
            self.send_artnet()

    def blackout(self):
        """Extinction totale"""
        print("🌑 Blackout LuxCore")
        self.dmx_data = [0] * 512
        self.send_artnet()

    def test_blades(self):
        """Test des blades 16-bit"""
        print("🎭 Test des blades 16-bit...")
        
        # Fond coloré pour voir l'effet
        self.dmx_data[0] = 100  # Rouge
        self.dmx_data[1] = 150  # Vert
        self.dmx_data[2] = 200  # Bleu
        
        # Spots visibles
        for i in range(3):
            self.set_spot_param(i, "rgb", (255, 200, 100))
            self.set_spot_param(i, "alpha", 200)
            self.set_spot_param(i, "size", 15000)
            
            angle = i * 120
            pan = int(32767 + 20000 * math.cos(math.radians(angle)))
            tilt = int(32767 + 20000 * math.sin(math.radians(angle)))
            self.set_spot_param(i, "position", (pan, tilt))
            self.set_spot_param(i, "mode", 1)
        
        # Test des blades progressivement
        blade_tests = [
            (0, 0, 0, 0, 0, 0, 0, 0, "Toutes ouvertes"),
            (2000, 1500, 1800, 1200, 2200, 1600, 1900, 1700, "Fermeture 3%"),
            (1000, 3000, 800, 2500, 1200, 2800, 900, 2600, "Inclinaisons"),
            (0, 0, 0, 0, 0, 0, 0, 0, "Retour ouvertes")
        ]
        
        for a1, a2, b1, b2, c1, c2, d1, d2, description in blade_tests:
            print(f"   → {description}")
            
            self.set_blade_16bit(3, a1)   # Blade A1
            self.set_blade_16bit(5, a2)   # Blade A2
            self.set_blade_16bit(7, b1)   # Blade B1
            self.set_blade_16bit(9, b2)   # Blade B2
            self.set_blade_16bit(11, c1)  # Blade C1
            self.set_blade_16bit(13, c2)  # Blade C2
            self.set_blade_16bit(15, d1)  # Blade D1
            self.set_blade_16bit(17, d2)  # Blade D2
            
            self.send_artnet()
            time.sleep(3)

def main():
    controller = ClaudeLuxController()
    
    if len(sys.argv) < 2:
        print("🚀 LuxCore DMX Engine - Claude Controller 2025")
        print("=" * 50)
        print("Usage: python3 claude_demo_luxcore.py [command]")
        print()
        print("📋 COMMANDES DISPONIBLES:")
        print("  demo1        - Ouverture dramatique")
        print("  demo2        - Explosion de couleurs") 
        print("  demo3        - Effet vague + effets")
        print("  demo4        - Showcase effets spéciaux")
        print("  spectacular  - Séquence complète")
        print("  strobe       - Effet stroboscope")
        print("  test-blades  - Test des blades 16-bit")
        print()
        print("🎨 COULEURS RAPIDES:")
        print("  red, green, blue, white, yellow")
        print("  purple, cyan, orange, pink")
        print()
        print("🔧 UTILITAIRES:")
        print("  blackout     - Extinction")
        print("  test         - Test de connexion")
        print()
        print("✨ Nouvelle empreinte: 28 canaux base + blades 16-bit!")
        return
    
    cmd = sys.argv[1].lower()
    
    commands = {
        'demo1': controller.demo1_opening,
        'demo2': controller.demo2_explosion, 
        'demo3': controller.demo3_wave,
        'demo4': controller.demo4_effects_showcase,
        'spectacular': controller.spectacular_sequence,
        'strobe': controller.strobe_effect,
        'test-blades': controller.test_blades,
        'blackout': controller.blackout,
        'red': lambda: controller.quick_colors('red'),
        'green': lambda: controller.quick_colors('green'),
        'blue': lambda: controller.quick_colors('blue'), 
        'white': lambda: controller.quick_colors('white'),
        'yellow': lambda: controller.quick_colors('yellow'),
        'purple': lambda: controller.quick_colors('purple'),
        'cyan': lambda: controller.quick_colors('cyan'),
        'orange': lambda: controller.quick_colors('orange'),
        'pink': lambda: controller.quick_colors('pink'),
        'test': lambda: (controller.quick_colors('red'), print("✅ Test LuxCore envoyé!"))
    }
    
    if cmd in commands:
        commands[cmd]()
    else:
        print(f"❌ Commande inconnue: {cmd}")
        print("💡 Utilisez sans paramètre pour voir la liste des commandes")

if __name__ == "__main__":
    main()