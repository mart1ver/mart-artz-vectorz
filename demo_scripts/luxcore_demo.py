#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LuxCore DMX Engine - Interactive Demo Controller
Created for LuxCore DMX Engine by Martin Vert
Demo script pilotable par Claude Code pour assemblée générale
"""

import socket
import struct
import time
import math
import threading
import sys

class LuxCoreController:
    def __init__(self, target_ip="127.0.0.1", artnet_port=6454):
        self.target_ip = target_ip
        self.artnet_port = artnet_port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.universe = 0
        self.sequence = 0
        self.dmx_data = [0] * 512
        self.running = True
        
    def send_artnet(self):
        """Send ArtNet packet to LuxCore"""
        header = b"Art-Net\x00"  # Art-Net header
        opcode = struct.pack("<H", 0x5000)  # ArtDMX opcode
        universe = struct.pack("<H", self.universe)
        length = struct.pack(">H", len(self.dmx_data))
        
        packet = header + opcode + b"\x00" * 12 + universe + length + bytes(self.dmx_data)
        self.socket.sendto(packet, (self.target_ip, self.artnet_port))
    
    def set_background(self, r, g, b):
        """Set background color (channels 1-3)"""
        self.dmx_data[0] = r
        self.dmx_data[1] = g  
        self.dmx_data[2] = b
    
    def set_blend_mode(self, mode):
        """Set blend mode (channel 12, modes 1-10)"""
        self.dmx_data[11] = max(1, min(10, mode))
    
    def set_spot(self, spot_id, r, g, b, alpha=255, size_pan=100, size_tilt=100, 
                 pos_pan=127, pos_tilt=127, rotation=0, shape=0):
        """Set spot parameters (19 channels per spot starting at channel 21)"""
        base_addr = 20 + (spot_id * 19)  # Base parameters (20) + spot offset
        
        if base_addr >= 500:  # Safety check
            return
            
        # Colors and alpha
        self.dmx_data[base_addr] = r
        self.dmx_data[base_addr + 1] = g  
        self.dmx_data[base_addr + 2] = b
        self.dmx_data[base_addr + 3] = alpha
        
        # Stroke (contour)
        self.dmx_data[base_addr + 4] = 2  # Stroke weight
        self.dmx_data[base_addr + 5] = 255  # Stroke alpha
        self.dmx_data[base_addr + 6] = 255  # Stroke R
        self.dmx_data[base_addr + 7] = 255  # Stroke G  
        self.dmx_data[base_addr + 8] = 255  # Stroke B
        
        # Size (16-bit)
        size_pan_16 = max(0, min(65535, size_pan * 65))
        size_tilt_16 = max(0, min(65535, size_tilt * 65))
        
        self.dmx_data[base_addr + 9] = (size_pan_16 >> 8) & 0xFF   # MSB
        self.dmx_data[base_addr + 10] = size_pan_16 & 0xFF         # LSB
        self.dmx_data[base_addr + 11] = (size_tilt_16 >> 8) & 0xFF # MSB
        self.dmx_data[base_addr + 12] = size_tilt_16 & 0xFF        # LSB
        
        # Rotation
        self.dmx_data[base_addr + 13] = int(rotation * 255 / 360) % 256
        
        # Position (16-bit)
        pos_pan_16 = max(0, min(65535, pos_pan * 256))
        pos_tilt_16 = max(0, min(65535, pos_tilt * 256))
        
        self.dmx_data[base_addr + 14] = (pos_pan_16 >> 8) & 0xFF   # MSB
        self.dmx_data[base_addr + 15] = pos_pan_16 & 0xFF          # LSB
        self.dmx_data[base_addr + 16] = (pos_tilt_16 >> 8) & 0xFF  # MSB
        self.dmx_data[base_addr + 17] = pos_tilt_16 & 0xFF         # LSB
        
        # Shape mode
        self.dmx_data[base_addr + 18] = shape
    
    def set_effects(self, blur=0, pixelate=0, sobel=False, rgb_split=0):
        """Set post-processing effects"""
        self.dmx_data[12] = blur  # Blur A
        self.dmx_data[13] = blur  # Blur B
        self.dmx_data[14] = pixelate
        self.dmx_data[15] = 255 if sobel else 0
        self.dmx_data[16] = rgb_split
    
    def blackout(self):
        """Turn off all spots and background"""
        self.dmx_data = [0] * 512
        self.send_artnet()
    
    def demo_spectacular(self):
        """Séquence spectaculaire complète"""
        print("🎭 SÉQUENCE SPECTACULAIRE - LuxCore DMX Engine")
        
        # 1. Ouverture dramatique
        print("   Phase 1: Ouverture dramatique...")
        self.blackout()
        time.sleep(0.5)
        
        for i in range(100):
            self.set_background(i*2, 0, i)
            self.send_artnet()
            time.sleep(0.02)
        
        # 2. Explosion de spots colorés
        print("   Phase 2: Explosion de couleurs...")
        self.set_blend_mode(2)  # ADD mode
        
        colors = [(255,0,0), (0,255,0), (0,0,255), (255,255,0), (255,0,255), (0,255,255), (255,255,255)]
        
        for i in range(7):
            r, g, b = colors[i]
            self.set_spot(i, r, g, b, 255, 150, 150, 
                         64 + i*32, 64 + (i%3)*64, i*50, i%3)
            
        # 3. Animation rotative
        print("   Phase 3: Animation rotative...")
        for frame in range(200):
            for i in range(7):
                rotation = (frame * (i+1) * 5) % 360
                pos_x = 127 + int(60 * math.cos(frame * 0.1 + i))
                pos_y = 127 + int(60 * math.sin(frame * 0.1 + i))
                
                r, g, b = colors[i]
                self.set_spot(i, r, g, b, 255, 150, 150, pos_x, pos_y, rotation, i%3)
            
            self.send_artnet()
            time.sleep(0.05)
        
        # 4. Effets finaux
        print("   Phase 4: Effets visuels...")
        self.set_effects(blur=10, rgb_split=20)
        for i in range(50):
            self.send_artnet()
            time.sleep(0.1)
        
        print("🎉 DÉMONSTRATION TERMINÉE !")
    
    def interactive_mode(self):
        """Mode interactif pour contrôle en temps réel"""
        print("\n🎮 MODE INTERACTIF LUXCORE")
        print("Commandes disponibles:")
        print("  'demo' - Séquence spectaculaire")
        print("  'red' - Tout en rouge") 
        print("  'rainbow' - Arc-en-ciel")
        print("  'blackout' - Extinction")
        print("  'quit' - Quitter")
        
        while self.running:
            try:
                cmd = input("\n> ").strip().lower()
                
                if cmd == 'quit':
                    break
                elif cmd == 'demo':
                    self.demo_spectacular()
                elif cmd == 'red':
                    self.set_background(255, 0, 0)
                    for i in range(7):
                        self.set_spot(i, 255, 0, 0, 255, 200, 200, 127, 127, 0, 0)
                    self.send_artnet()
                elif cmd == 'rainbow':
                    colors = [(255,0,0), (255,127,0), (255,255,0), (0,255,0), 
                             (0,0,255), (75,0,130), (148,0,211)]
                    for i, (r,g,b) in enumerate(colors):
                        self.set_spot(i, r, g, b, 255, 150, 150, 64+i*24, 127, 0, 1)
                    self.send_artnet()
                elif cmd == 'blackout':
                    self.blackout()
                else:
                    print("Commande inconnue!")
                    
            except KeyboardInterrupt:
                break
        
        self.blackout()
        print("\n👋 Au revoir!")

def main():
    controller = LuxCoreController()
    
    if len(sys.argv) > 1:
        cmd = sys.argv[1].lower()
        if cmd == 'demo':
            controller.demo_spectacular()
        elif cmd == 'test':
            print("🔧 Test de connexion LuxCore...")
            controller.set_background(255, 0, 0)
            controller.send_artnet()
            print("✅ Signal ArtNet envoyé!")
        else:
            print(f"Commande inconnue: {cmd}")
    else:
        controller.interactive_mode()

if __name__ == "__main__":
    main()