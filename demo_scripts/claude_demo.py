#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LuxCore DMX Engine - Claude Code Controller
Script optimisé pour contrôle direct par Claude Code
Usage: python3 claude_demo.py [command]
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
    
    def demo1_opening(self):
        """Ouverture dramatique avec fondu"""
        print("🎭 Ouverture dramatique...")
        for i in range(0, 255, 5):
            self.dmx_data[0] = i//3  # Rouge background
            self.dmx_data[1] = 0     # Vert background  
            self.dmx_data[2] = i//2  # Bleu background
            
            # Spot central qui grandit
            base = 20  # Premier spot
            self.dmx_data[base] = 255      # Rouge spot
            self.dmx_data[base+1] = i      # Vert spot
            self.dmx_data[base+2] = 255    # Bleu spot
            self.dmx_data[base+3] = i      # Alpha
            
            # Taille qui grandit (16-bit)
            size = i * 200
            self.dmx_data[base+9] = (size >> 8) & 0xFF
            self.dmx_data[base+10] = size & 0xFF
            self.dmx_data[base+11] = (size >> 8) & 0xFF  
            self.dmx_data[base+12] = size & 0xFF
            
            # Position centré
            self.dmx_data[base+14] = 127  # Pan MSB
            self.dmx_data[base+15] = 127  # Pan LSB
            self.dmx_data[base+16] = 127  # Tilt MSB
            self.dmx_data[base+17] = 127  # Tilt LSB
            
            self.dmx_data[base+18] = 1    # Ellipse
            
            self.send_artnet()
            time.sleep(0.05)
    
    def demo2_explosion(self):
        """Explosion de couleurs multiples"""
        print("💥 Explosion de couleurs...")
        
        # Mode ADD pour brillance maximum
        self.dmx_data[11] = 2
        
        colors = [(255,0,0), (0,255,0), (0,0,255), (255,255,0), (255,0,255), (0,255,255)]
        
        for i, (r, g, b) in enumerate(colors):
            base = 20 + (i * 19)
            
            # Couleur
            self.dmx_data[base] = r
            self.dmx_data[base+1] = g
            self.dmx_data[base+2] = b
            self.dmx_data[base+3] = 255  # Alpha max
            
            # Taille
            size = 8000
            self.dmx_data[base+9] = (size >> 8) & 0xFF
            self.dmx_data[base+10] = size & 0xFF
            self.dmx_data[base+11] = (size >> 8) & 0xFF
            self.dmx_data[base+12] = size & 0xFF
            
            # Position en cercle
            angle = i * 60  # 60 degrés entre chaque
            pos_x = 127 + int(60 * math.cos(math.radians(angle)))
            pos_y = 127 + int(60 * math.sin(math.radians(angle)))
            
            pos_x_16 = pos_x * 256
            pos_y_16 = pos_y * 256
            
            self.dmx_data[base+14] = (pos_x_16 >> 8) & 0xFF
            self.dmx_data[base+15] = pos_x_16 & 0xFF  
            self.dmx_data[base+16] = (pos_y_16 >> 8) & 0xFF
            self.dmx_data[base+17] = pos_y_16 & 0xFF
            
            self.dmx_data[base+18] = 1  # Ellipse
        
        self.send_artnet()
    
    def demo3_wave(self):
        """Effet de vague colorée"""
        print("🌊 Effet vague...")
        
        for frame in range(100):
            for i in range(6):
                base = 20 + (i * 19)
                
                # Couleur qui ondule
                hue = (frame + i * 20) % 360
                r = int(127 + 127 * math.sin(math.radians(hue)))
                g = int(127 + 127 * math.sin(math.radians(hue + 120)))
                b = int(127 + 127 * math.sin(math.radians(hue + 240)))
                
                self.dmx_data[base] = r
                self.dmx_data[base+1] = g  
                self.dmx_data[base+2] = b
                self.dmx_data[base+3] = 255
                
                # Position qui ondule
                pos_x = 127 + int(100 * math.sin(math.radians(frame * 10 + i * 30)))
                pos_y = 127 + int(50 * math.cos(math.radians(frame * 5 + i * 45)))
                
                pos_x_16 = pos_x * 256
                pos_y_16 = pos_y * 256
                
                self.dmx_data[base+14] = (pos_x_16 >> 8) & 0xFF
                self.dmx_data[base+15] = pos_x_16 & 0xFF
                self.dmx_data[base+16] = (pos_y_16 >> 8) & 0xFF  
                self.dmx_data[base+17] = pos_y_16 & 0xFF
                
                # Taille constante
                size = 5000
                self.dmx_data[base+9] = (size >> 8) & 0xFF
                self.dmx_data[base+10] = size & 0xFF
                self.dmx_data[base+11] = (size >> 8) & 0xFF
                self.dmx_data[base+12] = size & 0xFF
                
                self.dmx_data[base+18] = 0  # Rectangle
            
            self.send_artnet()
            time.sleep(0.08)
    
    def spectacular_sequence(self):
        """Séquence complète spectaculaire"""
        print("🎉 SÉQUENCE SPECTACULAIRE LUXCORE!")
        self.demo1_opening()
        time.sleep(1)
        self.demo2_explosion()
        time.sleep(2)
        self.demo3_wave()
        time.sleep(1)
        self.strobe_effect()
        print("✨ Démonstration terminée!")
    
    def strobe_effect(self):
        """Effet stroboscope"""
        print("⚡ Effet stroboscope...")
        for i in range(20):
            if i % 2:
                # Tout allumé
                for spot in range(6):
                    base = 20 + (spot * 19)
                    self.dmx_data[base] = 255
                    self.dmx_data[base+1] = 255
                    self.dmx_data[base+2] = 255
                    self.dmx_data[base+3] = 255
            else:
                # Tout éteint
                for spot in range(6):
                    base = 20 + (spot * 19)
                    self.dmx_data[base+3] = 0  # Alpha = 0
            
            self.send_artnet()
            time.sleep(0.1)
    
    def quick_colors(self, color_name):
        """Couleurs rapides"""
        colors = {
            'red': (255, 0, 0),
            'green': (0, 255, 0), 
            'blue': (0, 0, 255),
            'white': (255, 255, 255),
            'yellow': (255, 255, 0),
            'purple': (255, 0, 255),
            'cyan': (0, 255, 255)
        }
        
        if color_name in colors:
            r, g, b = colors[color_name]
            print(f"🎨 Couleur: {color_name}")
            
            # Background
            self.dmx_data[0] = r//3
            self.dmx_data[1] = g//3  
            self.dmx_data[2] = b//3
            
            # Tous les spots
            for i in range(7):
                base = 20 + (i * 19)
                self.dmx_data[base] = r
                self.dmx_data[base+1] = g
                self.dmx_data[base+2] = b
                self.dmx_data[base+3] = 255
                
                size = 6000
                self.dmx_data[base+9] = (size >> 8) & 0xFF
                self.dmx_data[base+10] = size & 0xFF
                self.dmx_data[base+11] = (size >> 8) & 0xFF
                self.dmx_data[base+12] = size & 0xFF
                
                self.dmx_data[base+18] = i % 3  # Formes variées
            
            self.send_artnet()
    
    def blackout(self):
        """Extinction totale"""
        print("🌑 Blackout")
        self.dmx_data = [0] * 512
        self.send_artnet()

def main():
    controller = ClaudeLuxController()
    
    if len(sys.argv) < 2:
        print("Usage: python3 claude_demo.py [command]")
        print("Commands: demo1, demo2, demo3, spectacular, strobe")
        print("         red, green, blue, white, rainbow, blackout, test")
        return
    
    cmd = sys.argv[1].lower()
    
    commands = {
        'demo1': controller.demo1_opening,
        'demo2': controller.demo2_explosion, 
        'demo3': controller.demo3_wave,
        'spectacular': controller.spectacular_sequence,
        'strobe': controller.strobe_effect,
        'blackout': controller.blackout,
        'red': lambda: controller.quick_colors('red'),
        'green': lambda: controller.quick_colors('green'),
        'blue': lambda: controller.quick_colors('blue'), 
        'white': lambda: controller.quick_colors('white'),
        'yellow': lambda: controller.quick_colors('yellow'),
        'purple': lambda: controller.quick_colors('purple'),
        'cyan': lambda: controller.quick_colors('cyan'),
        'test': lambda: (controller.quick_colors('red'), print("✅ Test envoyé!"))
    }
    
    if cmd in commands:
        commands[cmd]()
    else:
        print(f"❌ Commande inconnue: {cmd}")

if __name__ == "__main__":
    main()