#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LUXCORE DMX ENGINE - DEMO 50 SPOTS AVEC NOUVELLES FORMES
=========================================================
Démonstration des nouvelles formes avec 50 spots animés
Author: Martin Vert
"""

import socket
import time
import math
import sys

class LuxCore50SpotsNewShapesDemo:
    def __init__(self, target_ip="127.0.0.1"):
        self.target_ip = target_ip
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.dmx_data = [0] * 1024
        self.frame_count = 0
        
    def send_artnet(self):
        """Send ArtNet packet"""
        header = b"Art-Net\x00"
        packet = (header + 
                  (0x5000).to_bytes(2, 'little') +
                  bytes([0, 14, 0, 0, 0, 0]) +
                  (len(self.dmx_data)).to_bytes(2, 'big') +
                  bytes(self.dmx_data))
        
        try:
            self.socket.sendto(packet, (self.target_ip, 6454))
            return True
        except Exception as e:
            print(f"❌ ArtNet Send FAILED: {e}")
            return False

    def animate_50_spots_new_shapes(self, time_offset):
        """50 spots avec focus sur les nouvelles formes"""
        
        # Configuration couleurs de base
        self.dmx_data[0] = 25   # Rouge background très faible
        self.dmx_data[1] = 30   # Vert background très faible
        self.dmx_data[2] = 50   # Bleu background faible
        
        # Blades ouvertes (pour bien voir les formes)
        for i in range(3, 19):
            self.dmx_data[i] = 0
        
        # Mode de mélange qui fait ressortir les formes
        blend_mode_value = int(127 + 50 * math.sin(time_offset * 0.2))
        self.dmx_data[19] = blend_mode_value
        
        # Nouvelles formes définies
        new_shapes = {
            5: "Hexagone ⬡",
            6: "Losange ♦", 
            7: "Octogone ⬢",
            8: "Étoile ✦"
        }
        
        existing_shapes = {
            0: "Ellipse",
            1: "Rectangle", 
            2: "Texte",
            3: "Triangle",
            4: "Pentagone"
        }
        
        all_shapes = {**existing_shapes, **new_shapes}
        
        # 50 spots avec distribution équilibrée des formes
        for spot_id in range(50):
            base = 28 + (spot_id * 19)
            phase = spot_id * math.pi / 12.5
            speed_factor = 0.4 + (spot_id % 7) * 0.1
            
            # Forcer l'utilisation des nouvelles formes pour certains spots
            if spot_id < 20:
                # 20 premiers spots = focus sur nouvelles formes (5-8)
                shape_id = 5 + (spot_id % 4)  # Cycle sur formes 5,6,7,8
            elif spot_id < 35:  
                # 15 spots suivants = mix nouvelles + anciennes
                shape_id = spot_id % 9  # Toutes les formes 0-8
            else:
                # 15 derniers spots = anciennes formes pour comparaison
                shape_id = spot_id % 5  # Formes 0-4
            
            # Couleurs différentes par groupe de formes
            if shape_id >= 5:  # Nouvelles formes = couleurs vives
                red = int(150 + 105 * abs(math.sin(time_offset * speed_factor + phase)))
                green = int(100 + 155 * abs(math.sin(time_offset * (speed_factor * 0.7) + phase + math.pi/3)))
                blue = int(80 + 175 * abs(math.sin(time_offset * (speed_factor * 1.1) + phase + math.pi/2)))
            else:  # Anciennes formes = couleurs plus douces
                red = int(80 + 100 * abs(math.sin(time_offset * speed_factor + phase)))
                green = int(120 + 100 * abs(math.sin(time_offset * (speed_factor * 0.8) + phase)))  
                blue = int(100 + 120 * abs(math.sin(time_offset * (speed_factor * 0.9) + phase)))
            
            self.dmx_data[base] = red
            self.dmx_data[base+1] = green  
            self.dmx_data[base+2] = blue
            
            # Alpha plus élevé pour les nouvelles formes
            if shape_id >= 5:
                alpha_base = 200  # Nouvelles formes bien visibles
            else:
                alpha_base = 150  # Anciennes formes plus discrètes
                
            alpha_variation = int(30 * math.sin(time_offset * 0.8 + phase))
            self.dmx_data[base+3] = max(100, alpha_base + alpha_variation)
            
            # Stroke pour mettre en valeur les contours des nouvelles formes
            if shape_id >= 5:
                stroke_weight = int(25 + 15 * math.sin(time_offset * 1.2 + phase))
                stroke_alpha = 180
            else:
                stroke_weight = int(15 + 10 * math.sin(time_offset * 1.1 + phase))
                stroke_alpha = 120
                
            self.dmx_data[base+4] = stroke_weight
            self.dmx_data[base+5] = stroke_alpha
            
            # Couleur stroke contrastante
            self.dmx_data[base+6] = 255 - red   
            self.dmx_data[base+7] = 255 - green 
            self.dmx_data[base+8] = 255 - blue  
            
            # Taille adaptée à la forme
            if shape_id >= 5:  # Nouvelles formes plus grandes
                size_base = 10000 + (spot_id % 8) * 1500
                size_variation = int(4000 * math.sin(time_offset * (0.5 + spot_id * 0.02) + phase))
            else:  # Anciennes formes normales
                size_base = 8000 + (spot_id % 6) * 1000  
                size_variation = int(3000 * math.sin(time_offset * (0.6 + spot_id * 0.02) + phase))
            
            pan_size = size_base + size_variation
            tilt_size = size_base - int(size_variation * 0.6)
            
            self.dmx_data[base+9] = (pan_size >> 8) & 0xFF
            self.dmx_data[base+10] = pan_size & 0xFF
            self.dmx_data[base+11] = (tilt_size >> 8) & 0xFF  
            self.dmx_data[base+12] = tilt_size & 0xFF
            
            # Rotation plus lente pour bien voir les formes
            rotation_speed = 15 + (spot_id % 6) * 3  # 15-30°/sec
            rotation = int((time_offset * rotation_speed + spot_id * 8) % 360)
            self.dmx_data[base+13] = int(rotation * 255 / 360)
            
            # Positions organisées par type de forme
            if shape_id >= 5:  # Nouvelles formes en orbite large
                orbit_radius = 5000 + (shape_id - 5) * 1500
                orbit_speed = 0.2 + (shape_id - 5) * 0.05
                pan_pos = int(32767 + orbit_radius * math.cos(time_offset * orbit_speed + phase))
                tilt_pos = int(32767 + orbit_radius * math.sin(time_offset * orbit_speed + phase))
            else:  # Anciennes formes en orbite plus serrée  
                orbit_radius = 3000 + shape_id * 800
                orbit_speed = 0.3 + shape_id * 0.04
                pan_pos = int(32767 + orbit_radius * math.cos(time_offset * orbit_speed + phase))
                tilt_pos = int(32767 + orbit_radius * math.sin(time_offset * orbit_speed + phase))
            
            # Contraintes de sécurité
            pan_pos = max(8000, min(57535, pan_pos))
            tilt_pos = max(8000, min(57535, tilt_pos))
            
            self.dmx_data[base+14] = (pan_pos >> 8) & 0xFF
            self.dmx_data[base+15] = pan_pos & 0xFF
            self.dmx_data[base+16] = (tilt_pos >> 8) & 0xFF
            self.dmx_data[base+17] = tilt_pos & 0xFF
            
            # Assigner la forme
            self.dmx_data[base+18] = shape_id

    def run_new_shapes_50_spots_demo(self, duration_seconds=60):
        """Démonstration 50 spots focus nouvelles formes"""
        print("🎨 LUXCORE 50 SPOTS - NOUVELLES FORMES SHOWCASE")
        print("=" * 55)
        print(f"🎯 Target: {self.target_ip}:6454")
        print(f"⏱️  Durée: {duration_seconds} secondes")
        print()
        print("✨ NOUVELLES FORMES MISES EN AVANT:")
        print("   • 5: Hexagone ⬡ - Polygone 6 côtés")
        print("   • 6: Losange ♦ - Forme diamant") 
        print("   • 7: Octogone ⬢ - Polygone 8 côtés")
        print("   • 8: Étoile ✦ - Étoile à 8 branches")
        print()
        print("📋 DISTRIBUTION DES 50 SPOTS:")
        print("   • Spots 1-20: Focus nouvelles formes (5-8)")
        print("   • Spots 21-35: Mix toutes formes (0-8)")
        print("   • Spots 36-50: Formes classiques (0-4)")
        print()
        print("🎨 CARACTÉRISTIQUES:")
        print("   • Nouvelles formes: couleurs vives + tailles grandes")
        print("   • Anciennes formes: couleurs douces + tailles normales")
        print("   • Contours renforcés pour bien voir les géométries")
        print("   • Rotations lentes pour apprécier chaque forme")
        print()
        
        start_time = time.time()
        frame_count = 0
        
        print("🎬 SHOWCASE 50 SPOTS NOUVELLES FORMES DÉMARRÉ...")
        
        try:
            while time.time() - start_time < duration_seconds:
                current_time = time.time() - start_time
                
                self.animate_50_spots_new_shapes(current_time)
                
                if self.send_artnet():
                    frame_count += 1
                    
                    if frame_count % 150 == 0:  # ~50 FPS * 3 sec
                        progress = (current_time / duration_seconds) * 100
                        fps = frame_count / current_time if current_time > 0 else 0
                        print(f"🎨 Progrès: {progress:.1f}% - FPS: {fps:.1f} - Nouvelles formes actives!")
                
                time.sleep(0.02)  # 50 FPS target
                
        except KeyboardInterrupt:
            print("\n⏹️  Showcase interrompu par l'utilisateur")
        
        # Blackout final
        self.dmx_data = [0] * 1024
        self.send_artnet()
        
        # Statistiques finales
        total_time = time.time() - start_time
        avg_fps = frame_count / total_time if total_time > 0 else 0
        
        print(f"\n🎨 BILAN SHOWCASE NOUVELLES FORMES:")
        print(f"   Durée totale: {total_time:.1f}s")
        print(f"   Frames envoyées: {frame_count}")
        print(f"   FPS moyen: {avg_fps:.1f}")
        print(f"   Nouvelles formes testées: 4 (hexagone, losange, octogone, étoile)")
        print(f"   Spots avec nouvelles formes: 35/50")
        
        if avg_fps >= 45:
            print(f"   🎉 PERFORMANCE EXCELLENTE avec nouvelles formes!")
        elif avg_fps >= 35:
            print(f"   ✅ PERFORMANCE BONNE - Nouvelles formes optimisées")
        else:
            print(f"   ⚠️  PERFORMANCE À SURVEILLER")
            
        print("\n💡 Utilisez le menu Processing pour tester manuellement!")

def main():
    if len(sys.argv) > 1:
        target_ip = sys.argv[1]
    else:
        target_ip = "127.0.0.1"
    
    if len(sys.argv) > 2:
        duration = int(sys.argv[2])
    else:
        duration = 45  # 45 secondes par défaut
    
    demo = LuxCore50SpotsNewShapesDemo(target_ip)
    demo.run_new_shapes_50_spots_demo(duration)

if __name__ == "__main__":
    main()