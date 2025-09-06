#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LUXCORE DMX ENGINE - PERFORMANCE DEMO WITH 50 SPOTS
===================================================
Test de performance intensive avec 50 spots animés simultanément
Author: Martin Vert
"""

import socket
import time
import math
import sys

class LuxCore50SpotsDemo:
    def __init__(self, target_ip="127.0.0.1"):
        self.target_ip = target_ip
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # DMX data pour supporter 50 spots (28 base + 50*19 = 978 canaux)
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

    def animate_50_spots(self, time_offset):
        """Animer 50 spots avec mouvements et rotations diverses"""
        
        # Configuration couleurs de base
        self.dmx_data[0] = 20   # Rouge background très faible
        self.dmx_data[1] = 25   # Vert background très faible
        self.dmx_data[2] = 40   # Bleu background faible
        
        # Blades très légèrement fermées (0.5-1%)
        for i in range(3, 19, 2):
            blade_value = int(327 + 200 * math.sin(time_offset * 0.2))  # 0.5-1% closure
            self.dmx_data[i] = (blade_value >> 8) & 0xFF    # MSB
            self.dmx_data[i+1] = blade_value & 0xFF         # LSB
        
        # Canal 20 - Blend mode animé
        blend_mode_value = int(127 + 100 * math.sin(time_offset * 0.3))
        self.dmx_data[19] = blend_mode_value
        
        # 50 spots avec animations différentes et variées
        for spot_id in range(50):
            base = 28 + (spot_id * 19)  # Base address for each spot
            
            # Phases différentes pour chaque spot
            phase = spot_id * math.pi / 12.5  # Plus de variation
            speed_factor = 0.5 + (spot_id % 5) * 0.2  # Vitesses variables
            
            # Couleurs animées avec patterns différents
            red = int(100 + 155 * abs(math.sin(time_offset * speed_factor + phase)))
            green = int(80 + 175 * abs(math.sin(time_offset * (speed_factor * 0.7) + phase + math.pi/3)))
            blue = int(120 + 135 * abs(math.sin(time_offset * (speed_factor * 1.2) + phase + math.pi/2)))
            
            self.dmx_data[base] = red       # Rouge
            self.dmx_data[base+1] = green   # Vert  
            self.dmx_data[base+2] = blue    # Bleu
            
            # Alpha variable selon le spot
            alpha_base = 150 if spot_id < 25 else 180  # Première moitié moins intense
            alpha_variation = int(50 * math.sin(time_offset * 0.9 + phase))
            self.dmx_data[base+3] = max(50, alpha_base + alpha_variation)
            
            # Stroke animé
            stroke_weight = int(15 + 10 * math.sin(time_offset * 1.3 + phase))
            self.dmx_data[base+4] = stroke_weight
            self.dmx_data[base+5] = 120     # Stroke alpha modéré
            
            # Couleur stroke contrastante
            self.dmx_data[base+6] = 255 - red   # Rouge stroke inversé
            self.dmx_data[base+7] = 255 - green # Vert stroke inversé  
            self.dmx_data[base+8] = 255 - blue  # Bleu stroke inversé
            
            # Taille animée 16-bit avec variation par spot
            size_base = 8000 + (spot_id % 10) * 1500  # Tailles de base variées
            size_variation = int(4000 * math.sin(time_offset * (0.6 + spot_id * 0.02) + phase))
            
            pan_size = size_base + size_variation
            tilt_size = size_base - int(size_variation * 0.7)  # Ellipses
            
            self.dmx_data[base+9] = (pan_size >> 8) & 0xFF   # Pan size MSB
            self.dmx_data[base+10] = pan_size & 0xFF         # Pan size LSB
            self.dmx_data[base+11] = (tilt_size >> 8) & 0xFF # Tilt size MSB  
            self.dmx_data[base+12] = tilt_size & 0xFF        # Tilt size LSB
            
            # Rotation continue avec vitesses différentes
            rotation_speed = 20 + (spot_id % 8) * 5  # 20-55 degrés/sec
            rotation = int((time_offset * rotation_speed + spot_id * 7.2) % 360)
            self.dmx_data[base+13] = int(rotation * 255 / 360)
            
            # Position avec patterns variés
            if spot_id < 17:  # Orbite circulaire
                orbit_radius = 6000 + (spot_id % 5) * 1200
                orbit_speed = 0.3 + (spot_id % 3) * 0.15
                pan_pos = int(32767 + orbit_radius * math.cos(time_offset * orbit_speed + phase))
                tilt_pos = int(32767 + orbit_radius * math.sin(time_offset * orbit_speed + phase))
                
            elif spot_id < 34:  # Mouvement en 8
                figure8_scale = 5000 + (spot_id % 4) * 1000
                t = time_offset * (0.4 + (spot_id % 3) * 0.1) + phase
                pan_pos = int(32767 + figure8_scale * math.sin(t))
                tilt_pos = int(32767 + figure8_scale * math.sin(2*t) / 2)
                
            else:  # Mouvement linéaire oscillant
                oscillation = 8000 + (spot_id % 6) * 800
                osc_speed = 0.5 + (spot_id % 4) * 0.2
                pan_pos = int(32767 + oscillation * math.sin(time_offset * osc_speed + phase))
                tilt_pos = int(32767 + oscillation * math.cos(time_offset * (osc_speed * 0.7) + phase))
            
            # Contraintes de sécurité
            pan_pos = max(8000, min(57535, pan_pos))
            tilt_pos = max(8000, min(57535, tilt_pos))
            
            self.dmx_data[base+14] = (pan_pos >> 8) & 0xFF   # Pan pos MSB
            self.dmx_data[base+15] = pan_pos & 0xFF          # Pan pos LSB
            self.dmx_data[base+16] = (tilt_pos >> 8) & 0xFF  # Tilt pos MSB
            self.dmx_data[base+17] = tilt_pos & 0xFF         # Tilt pos LSB
            
            # Mode cyclique avec patterns
            if spot_id < 20:
                mode = (spot_id + int(time_offset * 0.15)) % 5  # Lent
            else:
                mode = (spot_id % 5)  # Mode fixe par spot

            self.dmx_data[base+18] = mode

    def run_50_spots_demo(self, duration_seconds=60):
        """Démonstration de performance avec 50 spots animés"""
        print("🚀 LUXCORE 50 SPOTS STRESS TEST")
        print("=" * 45)
        print(f"🎯 Target: {self.target_ip}:6454")
        print(f"⏱️  Durée: {duration_seconds} secondes")
        print("🔥 50 SPOTS SIMULTANÉS avec animations complexes:")
        print("   • Orbites circulaires (spots 1-17)")
        print("   • Mouvements en forme de 8 (spots 18-34)")  
        print("   • Oscillations linéaires (spots 35-50)")
        print("💡 Appuyez sur 'P' dans Processing pour voir les stats !")
        print("⚠️  ATTENTION: Test intensif - surveiller les performances")
        print()
        
        start_time = time.time()
        frame_count = 0
        
        print("🎬 50 SPOTS ANIMATION DÉMARRÉE...")
        
        try:
            while time.time() - start_time < duration_seconds:
                current_time = time.time() - start_time
                
                # Animer les 50 spots
                self.animate_50_spots(current_time)
                
                # Envoyer les données
                if self.send_artnet():
                    frame_count += 1
                    
                    # Affichage du progrès toutes les 3 secondes
                    if frame_count % 150 == 0:  # ~50 FPS * 3 sec
                        progress = (current_time / duration_seconds) * 100
                        fps = frame_count / current_time if current_time > 0 else 0
                        print(f"🔥 Progrès: {progress:.1f}% - FPS: {fps:.1f} - 50 spots actifs")
                
                # 50 FPS target
                time.sleep(0.02)
                
        except KeyboardInterrupt:
            print("\n⏹️  Test 50 spots interrompu par l'utilisateur")
        
        # Blackout final
        self.dmx_data = [0] * 1024
        self.send_artnet()
        
        # Statistiques finales
        total_time = time.time() - start_time
        avg_fps = frame_count / total_time if total_time > 0 else 0
        total_calculations = frame_count * 50  # 50 spots par frame
        
        print(f"\n🔥 BILAN 50 SPOTS STRESS TEST:")
        print(f"   Durée totale: {total_time:.1f}s")
        print(f"   Frames envoyées: {frame_count}")
        print(f"   FPS moyen: {avg_fps:.1f}")
        print(f"   Total calculs spots: {total_calculations:,}")
        print(f"   Calculs/seconde: {int(total_calculations/total_time):,}")
        
        # Évaluation de performance
        if avg_fps >= 45:
            print(f"   🎉 PERFORMANCE EXCELLENTE - Système très robuste !")
        elif avg_fps >= 35:
            print(f"   ✅ PERFORMANCE BONNE - Acceptable pour production")
        elif avg_fps >= 25:
            print(f"   ⚠️  PERFORMANCE MOYENNE - Limite atteinte")
        else:
            print(f"   🚨 PERFORMANCE CRITIQUE - Réduire le nombre de spots")
            
        print("\n💡 Vérifiez les stats Processing détaillées avec 'P' !")

def main():
    if len(sys.argv) > 1:
        target_ip = sys.argv[1]
    else:
        target_ip = "127.0.0.1"
    
    if len(sys.argv) > 2:
        duration = int(sys.argv[2])
    else:
        duration = 45  # 45 secondes par défaut pour le stress test
    
    demo = LuxCore50SpotsDemo(target_ip)
    demo.run_50_spots_demo(duration)

if __name__ == "__main__":
    main()