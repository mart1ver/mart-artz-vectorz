#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LUXCORE DMX ENGINE - SYSTEM VALIDATION SCRIPT
=============================================
Script de validation complète du système pour détecter toute régression
Author: Martin Vert
"""

import socket
import time
import sys

class LuxCoreValidator:
    def __init__(self, target_ip="127.0.0.1"):
        self.target_ip = target_ip
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.dmx_data = [0] * 512
        self.test_results = []
        
    def send_artnet(self):
        """Send ArtNet packet - baseline functionality"""
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
            self.test_results.append(f"❌ ArtNet Send FAILED: {e}")
            return False

    def test_baseline_colors(self):
        """Test 1: Basic RGB colors"""
        print("🧪 Test 1: Couleurs de base...")
        
        colors = [
            (255, 0, 0, "Rouge"),
            (0, 255, 0, "Vert"),
            (0, 0, 255, "Bleu"),
            (255, 255, 255, "Blanc"),
            (0, 0, 0, "Noir")
        ]
        
        for r, g, b, name in colors:
            self.dmx_data[0] = r
            self.dmx_data[1] = g  
            self.dmx_data[2] = b
            
            if self.send_artnet():
                self.test_results.append(f"✅ Couleur {name}: OK")
            else:
                self.test_results.append(f"❌ Couleur {name}: FAILED")
            
            time.sleep(0.5)
        
        return True

    def test_blades_16bit(self):
        """Test 2: Blades 16-bit functionality"""
        print("🧪 Test 2: Blades 16-bit...")
        
        blade_tests = [
            (0, 0, 0, 0, 0, 0, 0, 0, "Toutes ouvertes"),
            (1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, "Légère fermeture"),
            (5000, 3000, 4000, 2000, 6000, 4000, 5000, 3500, "Inclinaisons"),
            (0, 0, 0, 0, 0, 0, 0, 0, "Retour ouvert")
        ]
        
        # Couleur de fond pour voir les blades
        self.dmx_data[0] = 100
        self.dmx_data[1] = 150
        self.dmx_data[2] = 200
        
        for a1, a2, b1, b2, c1, c2, d1, d2, description in blade_tests:
            # Set 16-bit blade values (MSB/LSB)
            self.dmx_data[3] = (a1 >> 8) & 0xFF
            self.dmx_data[4] = a1 & 0xFF
            self.dmx_data[5] = (a2 >> 8) & 0xFF
            self.dmx_data[6] = a2 & 0xFF
            self.dmx_data[7] = (b1 >> 8) & 0xFF
            self.dmx_data[8] = b1 & 0xFF
            self.dmx_data[9] = (b2 >> 8) & 0xFF
            self.dmx_data[10] = b2 & 0xFF
            self.dmx_data[11] = (c1 >> 8) & 0xFF
            self.dmx_data[12] = c1 & 0xFF
            self.dmx_data[13] = (c2 >> 8) & 0xFF
            self.dmx_data[14] = c2 & 0xFF
            self.dmx_data[15] = (d1 >> 8) & 0xFF
            self.dmx_data[16] = d1 & 0xFF
            self.dmx_data[17] = (d2 >> 8) & 0xFF
            self.dmx_data[18] = d2 & 0xFF
            
            if self.send_artnet():
                self.test_results.append(f"✅ Blade {description}: OK")
            else:
                self.test_results.append(f"❌ Blade {description}: FAILED")
                
            time.sleep(1)
        
        return True

    def test_spots_functionality(self):
        """Test 3: Spots avec toutes les formes"""
        print("🧪 Test 3: Spots et formes...")
        
        # Reset blades
        for i in range(3, 19):
            self.dmx_data[i] = 0
            
        spot_forms = [
            (0, "Ellipse"),
            (1, "Rectangle"), 
            (2, "Texte"),
            (3, "Triangle"),
            (4, "Pentagone")
        ]
        
        for form_id, form_name in spot_forms:
            # Premier spot (canal 28+)
            base = 28
            self.dmx_data[base] = 255      # Rouge
            self.dmx_data[base+1] = 200    # Vert
            self.dmx_data[base+2] = 100    # Bleu
            self.dmx_data[base+3] = 255    # Alpha
            
            # Taille 16-bit
            size = 15000
            self.dmx_data[base+9] = (size >> 8) & 0xFF
            self.dmx_data[base+10] = size & 0xFF
            self.dmx_data[base+11] = (size >> 8) & 0xFF
            self.dmx_data[base+12] = size & 0xFF
            
            # Position centrée 16-bit
            center = 32767
            self.dmx_data[base+14] = (center >> 8) & 0xFF
            self.dmx_data[base+15] = center & 0xFF
            self.dmx_data[base+16] = (center >> 8) & 0xFF
            self.dmx_data[base+17] = center & 0xFF
            
            # Forme
            self.dmx_data[base+18] = form_id
            
            if self.send_artnet():
                self.test_results.append(f"✅ Spot {form_name}: OK")
            else:
                self.test_results.append(f"❌ Spot {form_name}: FAILED")
                
            time.sleep(1.5)
        
        return True

    def test_effects(self):
        """Test 4: Effets spéciaux"""
        print("🧪 Test 4: Effets spéciaux...")
        
        effects = [
            (20, 10, "Blur A"),
            (21, 15, "Blur B"),
            (22, 50, "Pixelate"),
            (24, 30, "RGB Split"),
            (25, 200, "Saturation A"),
            (27, 255, "Chromatic Aberration")
        ]
        
        # Spots visibles pour voir les effets
        base = 28
        for i in range(3):
            spot_base = base + (i * 19)
            self.dmx_data[spot_base] = 255
            self.dmx_data[spot_base+1] = 255
            self.dmx_data[spot_base+2] = 255
            self.dmx_data[spot_base+3] = 200
        
        for channel, value, effect_name in effects:
            self.dmx_data[channel] = value
            
            if self.send_artnet():
                self.test_results.append(f"✅ Effet {effect_name}: OK")
            else:
                self.test_results.append(f"❌ Effet {effect_name}: FAILED")
                
            time.sleep(1)
            
            # Reset effet
            self.dmx_data[channel] = 0
            self.send_artnet()
            time.sleep(0.5)
        
        return True

    def test_blend_modes(self):
        """Test 5: Modes de mélange"""
        print("🧪 Test 5: Modes de mélange...")
        
        blend_modes = [
            (0, "Normal"),
            (51, "Add"),
            (204, "Multiply"),
            (127, "Lightest"),
            (153, "Difference")
        ]
        
        # Couleur de base
        self.dmx_data[0] = 100
        self.dmx_data[1] = 150
        self.dmx_data[2] = 200
        
        for mode_val, mode_name in blend_modes:
            self.dmx_data[19] = mode_val  # Canal 20 - Blend mode
            
            if self.send_artnet():
                self.test_results.append(f"✅ Blend {mode_name}: OK")
            else:
                self.test_results.append(f"❌ Blend {mode_name}: FAILED")
                
            time.sleep(1)
        
        return True

    def run_full_validation(self):
        """Exécute validation complète du système"""
        print("🚀 VALIDATION SYSTÈME LUXCORE DMX ENGINE")
        print("=" * 50)
        print(f"🎯 Target: {self.target_ip}:6454")
        print("⏱️  Durée estimée: ~30 secondes")
        print()
        
        start_time = time.time()
        
        # Tests séquentiels
        tests = [
            self.test_baseline_colors,
            self.test_blades_16bit,
            self.test_spots_functionality, 
            self.test_effects,
            self.test_blend_modes
        ]
        
        for test in tests:
            try:
                test()
            except Exception as e:
                self.test_results.append(f"❌ Test {test.__name__} CRASHED: {e}")
        
        # Blackout final
        self.dmx_data = [0] * 512
        self.send_artnet()
        
        # Rapport final
        duration = time.time() - start_time
        print(f"\n⏱️  Tests terminés en {duration:.1f}s")
        print("\n📋 RÉSULTATS:")
        print("=" * 30)
        
        success_count = 0
        for result in self.test_results:
            print(result)
            if "✅" in result:
                success_count += 1
        
        total_tests = len(self.test_results)
        success_rate = (success_count / total_tests * 100) if total_tests > 0 else 0
        
        print(f"\n📊 BILAN: {success_count}/{total_tests} tests réussis ({success_rate:.1f}%)")
        
        if success_rate >= 95:
            print("🎉 SYSTÈME VALIDÉ - Excellent état!")
            return True
        elif success_rate >= 80:
            print("⚠️  SYSTÈME OK - Quelques problèmes mineurs")
            return True
        else:
            print("🚨 SYSTÈME DÉFAILLANT - Intervention requise!")
            return False

def main():
    if len(sys.argv) > 1:
        target_ip = sys.argv[1]
    else:
        target_ip = "127.0.0.1"
    
    validator = LuxCoreValidator(target_ip)
    success = validator.run_full_validation()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()