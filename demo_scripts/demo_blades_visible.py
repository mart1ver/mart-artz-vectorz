#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DÉMO BLADES 16-BIT VISIBLES - LUXCORE DMX ENGINE
===============================================
Démonstration des blades avec couleurs visibles et spots actifs
Author: Martin Vert
"""

import socket
import time
import math

# Configuration réseau
UDP_IP = "127.0.0.1"
UDP_PORT = 6454
UNIVERSE = 0

def send_artnet(data):
    """Envoie un paquet Art-Net avec les données DMX"""
    # En-tête Art-Net
    packet = bytearray(18 + len(data))
    packet[0:8] = b"Art-Net\x00"
    packet[8:10] = (0x5000).to_bytes(2, 'little')  # OpCode ArtDMX
    packet[10:12] = (14).to_bytes(2, 'big')        # Version
    packet[12] = 0                                 # Sequence
    packet[13] = 0                                 # Physical
    packet[14:16] = UNIVERSE.to_bytes(2, 'little') # Universe
    packet[16:18] = len(data).to_bytes(2, 'big')   # Length
    packet[18:] = data
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(packet, (UDP_IP, UDP_PORT))
    sock.close()

def set_16bit_value(data, channel_msb, value):
    """Définit une valeur 16-bit dans les données DMX (MSB/LSB)"""
    value = max(0, min(65535, int(value)))
    msb = (value >> 8) & 0xFF
    lsb = value & 0xFF
    data[channel_msb - 1] = msb      # Canal MSB (index-1 car channels 1-based)
    data[channel_msb] = lsb          # Canal LSB

def set_spot_16bit(data, spot_id, param_offset, value):
    """Définit une valeur 16-bit pour un spot spécifique"""
    base_addr = 28 + (spot_id * 19)  # 28 canaux base + 19 par spot
    channel_msb = base_addr + param_offset
    set_16bit_value(data, channel_msb, value)

def demo_blades_visibles():
    """Démonstration visible des blades avec couleurs et spots"""
    print("🎨 DÉMO BLADES 16-BIT VISIBLES")
    print("=" * 35)
    print("✨ Couleurs éclatantes + blades fluides")
    print()
    
    # Initialisation des données DMX
    dmx_data = [0] * 512
    
    print("🌈 Phase 1: Couleurs de base éclatantes")
    
    # Couleurs de base RGB très vives
    dmx_data[0] = 255  # Rouge base
    dmx_data[1] = 200  # Vert base
    dmx_data[2] = 150  # Bleu base
    
    # Mode de mélange normal
    dmx_data[19] = 0  # Blend mode normal
    
    # Spots colorés et visibles
    for spot_id in range(3):  # 3 spots actifs
        spot_base = 28 + (spot_id * 19)
        
        # Couleurs spots RGB
        if spot_id == 0:  # Spot 1 - Rouge
            dmx_data[spot_base] = 255    # R
            dmx_data[spot_base + 1] = 100  # G
            dmx_data[spot_base + 2] = 100  # B
        elif spot_id == 1:  # Spot 2 - Vert
            dmx_data[spot_base] = 100    # R
            dmx_data[spot_base + 1] = 255  # G
            dmx_data[spot_base + 2] = 100  # B
        else:  # Spot 3 - Bleu
            dmx_data[spot_base] = 100    # R
            dmx_data[spot_base + 1] = 150  # G
            dmx_data[spot_base + 2] = 255  # B
        
        # Alpha des spots
        dmx_data[spot_base + 3] = 200  # Alpha élevé
        
        # Taille des spots (16-bit)
        set_spot_16bit(dmx_data, spot_id, 9, 30000)   # Size pan MSB/LSB
        set_spot_16bit(dmx_data, spot_id, 11, 30000)  # Size tilt MSB/LSB
        
        # Position des spots (16-bit)
        if spot_id == 0:
            set_spot_16bit(dmx_data, spot_id, 14, 20000)  # Pan
            set_spot_16bit(dmx_data, spot_id, 16, 20000)  # Tilt
        elif spot_id == 1:
            set_spot_16bit(dmx_data, spot_id, 14, 32767)  # Pan centre
            set_spot_16bit(dmx_data, spot_id, 16, 32767)  # Tilt centre
        else:
            set_spot_16bit(dmx_data, spot_id, 14, 45000)  # Pan
            set_spot_16bit(dmx_data, spot_id, 16, 45000)  # Tilt
        
        # Mode spot
        dmx_data[spot_base + 18] = 0  # Mode normal
    
    # Toutes les blades ouvertes au début
    for channel in range(3, 19, 2):  # Tous les canaux MSB des blades
        set_16bit_value(dmx_data, channel, 0)  # 0 = ouvert
    
    send_artnet(dmx_data)
    time.sleep(2)
    print("   ✓ Base colorée établie")
    
    print("🎭 Phase 2: Blades en mouvement fluide (30 secondes)")
    
    # Phase 2: Mouvement fluide des blades avec couleurs visibles
    duration = 30.0
    fps = 30
    total_steps = int(duration * fps)
    
    for step in range(total_steps):
        t = step / float(total_steps - 1) * 4 * math.pi
        
        # Maintenir les couleurs vives
        dmx_data[0] = int(200 + 55 * math.sin(t * 0.3))  # Rouge oscillant
        dmx_data[1] = int(180 + 75 * math.cos(t * 0.2))  # Vert oscillant
        dmx_data[2] = int(150 + 105 * math.sin(t * 0.4))  # Bleu oscillant
        
        # Blade A (top) - oscillation douce
        base_a = 8000
        amplitude_a = 6000
        blade_a = int(base_a + amplitude_a * math.sin(t * 0.8))
        set_16bit_value(dmx_data, 3, blade_a)  # A1
        set_16bit_value(dmx_data, 5, blade_a)  # A2 (pas d'inclinaison)
        
        # Blade B (right) - oscillation décalée
        base_b = 8000
        amplitude_b = 5000
        blade_b = int(base_b + amplitude_b * math.sin(t * 0.6 + math.pi/3))
        set_16bit_value(dmx_data, 7, blade_b)  # B1
        set_16bit_value(dmx_data, 9, blade_b)  # B2
        
        # Blade C (bottom) - oscillation inverse
        base_c = 8000
        amplitude_c = 7000
        blade_c = int(base_c + amplitude_c * math.sin(t * 0.7 + math.pi))
        set_16bit_value(dmx_data, 11, blade_c)  # C1
        set_16bit_value(dmx_data, 13, blade_c)  # C2
        
        # Blade D (left) - oscillation complexe
        base_d = 8000
        amplitude_d = 4500
        blade_d = int(base_d + amplitude_d * math.sin(t * 0.9 + 3*math.pi/2))
        set_16bit_value(dmx_data, 15, blade_d)  # D1
        set_16bit_value(dmx_data, 17, blade_d)  # D2
        
        # Animation des spots
        for spot_id in range(3):
            spot_base = 28 + (spot_id * 19)
            # Variation subtile de l'alpha
            alpha_variation = int(180 + 75 * math.sin(t * 0.5 + spot_id * math.pi/3))
            dmx_data[spot_base + 3] = alpha_variation
        
        send_artnet(dmx_data)
        time.sleep(1.0 / fps)
        
        # Affichage du progrès
        if step % (fps * 5) == 0:
            progress_percent = (step / float(total_steps)) * 100
            print(f"   → Animation: {progress_percent:.1f}%")
    
    print("   ✓ Animation terminée")
    
    print("🌟 Phase 3: Spectacle final avec inclinaisons (20 secondes)")
    
    # Phase 3: Inclinaisons spectaculaires
    duration = 20.0
    total_steps = int(duration * fps)
    
    for step in range(total_steps):
        t = step / float(total_steps - 1) * 6 * math.pi
        
        # Couleurs encore plus vives
        dmx_data[0] = 255  # Rouge max
        dmx_data[1] = 255  # Vert max
        dmx_data[2] = 255  # Bleu max
        
        # Inclinaisons des blades
        base = 15000
        incline_range = 8000
        
        # Blade A - inclinaison dynamique
        offset_a = int(incline_range * math.sin(t * 1.2))
        set_16bit_value(dmx_data, 3, base - offset_a)  # A1
        set_16bit_value(dmx_data, 5, base + offset_a)  # A2
        
        # Blade B - inclinaison opposée
        offset_b = int(incline_range * math.cos(t * 1.0))
        set_16bit_value(dmx_data, 7, base - offset_b)  # B1
        set_16bit_value(dmx_data, 9, base + offset_b)  # B2
        
        # Blade C - inclinaison décalée
        offset_c = int(incline_range * math.sin(t * 1.1 + math.pi/2))
        set_16bit_value(dmx_data, 11, base - offset_c)  # C1
        set_16bit_value(dmx_data, 13, base + offset_c)  # C2
        
        # Blade D - inclinaison complexe
        offset_d = int(incline_range * math.cos(t * 1.3 + math.pi))
        set_16bit_value(dmx_data, 15, base - offset_d)  # D1
        set_16bit_value(dmx_data, 17, base + offset_d)  # D2
        
        send_artnet(dmx_data)
        time.sleep(1.0 / fps)
    
    print("   ✓ Spectacle final terminé")
    
    # Reset progressif
    print("🌅 Reset progressif...")
    for fade_step in range(100):
        fade = 1.0 - (fade_step / 99.0)
        
        # Fade des couleurs
        dmx_data[0] = int(255 * fade)
        dmx_data[1] = int(255 * fade)
        dmx_data[2] = int(255 * fade)
        
        # Ouverture des blades
        for channel in range(3, 19, 2):
            set_16bit_value(dmx_data, channel, int(15000 * (1.0 - fade)))
        
        # Fade des spots
        for spot_id in range(3):
            spot_base = 28 + (spot_id * 19)
            dmx_data[spot_base + 3] = int(200 * fade)  # Alpha fade
        
        send_artnet(dmx_data)
        time.sleep(0.03)
    
    # Blackout final
    dmx_data = [0] * 512
    send_artnet(dmx_data)
    
    print()
    print("✨ DÉMO BLADES VISIBLES TERMINÉE!")
    print("🎨 Couleurs éclatantes + blades fluides")
    print("📈 16-bit precision utilisée")
    print("🌈 Rendu visuel spectaculaire!")

if __name__ == "__main__":
    try:
        demo_blades_visibles()
    except KeyboardInterrupt:
        print("\n⏹️  Démo interrompue")
        send_artnet([0] * 512)
    except Exception as e:
        print(f"❌ Erreur: {e}")
        send_artnet([0] * 512)