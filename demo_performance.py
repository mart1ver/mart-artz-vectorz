#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LUXCORE DMX ENGINE - PERFORMANCE DEMO WITH ANIMATION
=====================================================
Test de performance avec plusieurs spots en mouvement et rotation
Author: Martin Vert
"""

import socket
import time
import math
import sys

class LuxCorePerformanceDemo:
    def __init__(self, target_ip="127.0.0.1"):
        self.target_ip = target_ip
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.dmx_data = [0] * 512
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

    def animate_spots(self, time_offset):
        """Animer 5 spots avec mouvements et rotations complexes"""
        
        # Configuration couleurs de base
        self.dmx_data[0] = 30   # Rouge background faible
        self.dmx_data[1] = 40   # Vert background faible
        self.dmx_data[2] = 60   # Bleu background faible
        
        # Blades légèrement fermées (1-2%)
        for i in range(3, 19):
            blade_value = int(655 + 300 * math.sin(time_offset * 0.3))  # 1-2% closure avec légère oscillation
            self.dmx_data[i] = (blade_value >> 8) & 0xFF    # MSB
            self.dmx_data[i+1] = blade_value & 0xFF         # LSB
            i += 1  # Skip LSB since we handled it
        
        # 5 spots avec animations différentes
        for spot_id in range(5):
            base = 28 + (spot_id * 19)  # Base address for each spot
            phase = spot_id * math.pi / 2.5  # Décalage de phase entre spots
            
            # Couleurs animées
            red = int(128 + 127 * math.sin(time_offset * 0.7 + phase))
            green = int(128 + 127 * math.sin(time_offset * 0.5 + phase + math.pi/3))
            blue = int(128 + 127 * math.sin(time_offset * 0.9 + phase + math.pi/2))
            
            self.dmx_data[base] = red       # Rouge
            self.dmx_data[base+1] = green   # Vert  
            self.dmx_data[base+2] = blue    # Bleu
            self.dmx_data[base+3] = 200     # Alpha élevé
            
            # Stroke animé
            self.dmx_data[base+4] = int(20 + 15 * math.sin(time_offset * 1.1 + phase))
            self.dmx_data[base+5] = 150     # Stroke alpha
            
            # Couleur stroke différente
            self.dmx_data[base+6] = 255 - red   # Rouge stroke inversé
            self.dmx_data[base+7] = 255 - green # Vert stroke inversé  
            self.dmx_data[base+8] = 255 - blue  # Bleu stroke inversé
            
            # Taille animée 16-bit (oscillation entre 8000 et 25000)
            size_base = int(16000 + 9000 * math.sin(time_offset * 0.8 + phase))
            size_variation = int(3000 * math.sin(time_offset * 1.5 + phase))
            
            pan_size = size_base + size_variation
            tilt_size = size_base - size_variation
            
            self.dmx_data[base+9] = (pan_size >> 8) & 0xFF   # Pan size MSB
            self.dmx_data[base+10] = pan_size & 0xFF         # Pan size LSB
            self.dmx_data[base+11] = (tilt_size >> 8) & 0xFF # Tilt size MSB  
            self.dmx_data[base+12] = tilt_size & 0xFF        # Tilt size LSB
            
            # Rotation continue
            rotation = int((time_offset * 30 + spot_id * 45) % 360)  # 30°/sec avec décalage
            self.dmx_data[base+13] = int(rotation * 255 / 360)
            
            # Position en orbite 16-bit
            orbit_radius = 8000 + spot_id * 2000
            orbit_speed = 0.4 + spot_id * 0.1
            
            pan_pos = int(32767 + orbit_radius * math.cos(time_offset * orbit_speed + phase))
            tilt_pos = int(32767 + orbit_radius * math.sin(time_offset * orbit_speed + phase))
            
            self.dmx_data[base+14] = (pan_pos >> 8) & 0xFF   # Pan pos MSB
            self.dmx_data[base+15] = pan_pos & 0xFF          # Pan pos LSB
            self.dmx_data[base+16] = (tilt_pos >> 8) & 0xFF  # Tilt pos MSB
            self.dmx_data[base+17] = tilt_pos & 0xFF         # Tilt pos LSB
            
            # Mode cyclique
            mode = (spot_id + int(time_offset * 0.2)) % 5
            self.dmx_data[base+18] = mode

    def run_performance_demo(self, duration_seconds=60):
        """Démonstration de performance avec animation complexe"""
        print("🚀 LUXCORE PERFORMANCE DEMO - SPOTS EN MOUVEMENT")
        print("=" * 55)
        print(f"🎯 Target: {self.target_ip}:6454")
        print(f"⏱️  Durée: {duration_seconds} secondes")
        print("📊 5 spots animés avec rotation et mouvement orbital")
        print("💡 Appuyez sur 'P' dans Processing pour voir les stats de performance")
        print()
        
        start_time = time.time()
        frame_count = 0
        
        print("🎬 Animation démarrée...")
        
        try:
            while time.time() - start_time < duration_seconds:
                current_time = time.time() - start_time
                
                # Animer les spots
                self.animate_spots(current_time)
                
                # Envoyer les données
                if self.send_artnet():
                    frame_count += 1
                    
                    # Affichage du progrès toutes les 5 secondes
                    if frame_count % 250 == 0:  # ~50 FPS * 5 sec
                        progress = (current_time / duration_seconds) * 100
                        fps = frame_count / current_time if current_time > 0 else 0
                        print(f"⏳ Progrès: {progress:.1f}% - FPS moyen: {fps:.1f}")
                
                # 50 FPS target
                time.sleep(0.02)
                
        except KeyboardInterrupt:
            print("\n⏹️  Animation interrompue par l'utilisateur")
        
        # Blackout final
        self.dmx_data = [0] * 512
        self.send_artnet()
        
        # Statistiques finales
        total_time = time.time() - start_time
        avg_fps = frame_count / total_time if total_time > 0 else 0
        
        print(f"\n📊 BILAN:")
        print(f"   Durée totale: {total_time:.1f}s")
        print(f"   Frames envoyées: {frame_count}")
        print(f"   FPS moyen: {avg_fps:.1f}")
        print(f"   État final: ✅ SUCCÈS")
        print("\n💡 Vérifiez les stats Processing avec la touche 'P'")

def main():
    if len(sys.argv) > 1:
        target_ip = sys.argv[1]
    else:
        target_ip = "127.0.0.1"
    
    if len(sys.argv) > 2:
        duration = int(sys.argv[2])
    else:
        duration = 30  # 30 secondes par défaut
    
    demo = LuxCorePerformanceDemo(target_ip)
    demo.run_performance_demo(duration)

if __name__ == "__main__":
    main()