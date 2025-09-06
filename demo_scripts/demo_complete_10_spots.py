#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DÉMO COMPLÈTE LUXCORE DMX ENGINE - 10 SPOTS + TOUS PARAMÈTRES
=============================================================
Démonstration exhaustive de tous les paramètres disponibles
Author: Martin Vert
"""

import socket
import time
import math
import random

# Configuration réseau
UDP_IP = "127.0.0.1"
UDP_PORT = 6454
UNIVERSE = 0

def send_artnet(data):
    """Envoie un paquet Art-Net avec les données DMX"""
    packet = bytearray(18 + len(data))
    packet[0:8] = b"Art-Net\x00"
    packet[8:10] = (0x5000).to_bytes(2, 'little')
    packet[10:12] = (14).to_bytes(2, 'big')
    packet[12] = 0
    packet[13] = 0
    packet[14:16] = UNIVERSE.to_bytes(2, 'little')
    packet[16:18] = len(data).to_bytes(2, 'big')
    packet[18:] = data
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(packet, (UDP_IP, UDP_PORT))
    sock.close()

def set_16bit_value(data, channel_msb, value):
    """Définit une valeur 16-bit dans les données DMX (MSB/LSB)"""
    value = max(0, min(65535, int(value)))
    msb = (value >> 8) & 0xFF
    lsb = value & 0xFF
    data[channel_msb - 1] = msb
    data[channel_msb] = lsb

def set_spot_param(data, spot_id, param, value):
    """Définit un paramètre pour un spot spécifique"""
    base_addr = 28 + (spot_id * 19)  # 28 canaux base + 19 par spot
    
    if param == "red":
        data[base_addr] = value
    elif param == "green":
        data[base_addr + 1] = value
    elif param == "blue":
        data[base_addr + 2] = value
    elif param == "alpha":
        data[base_addr + 3] = value
    elif param == "stroke_weight":
        data[base_addr + 4] = value
    elif param == "stroke_alpha":
        data[base_addr + 5] = value
    elif param == "stroke_red":
        data[base_addr + 6] = value
    elif param == "stroke_green":
        data[base_addr + 7] = value
    elif param == "stroke_blue":
        data[base_addr + 8] = value
    elif param == "size_pan":
        set_16bit_value(data, base_addr + 9, value)
    elif param == "size_tilt":
        set_16bit_value(data, base_addr + 11, value)
    elif param == "rotation":
        data[base_addr + 13] = value
    elif param == "pan":
        set_16bit_value(data, base_addr + 14, value)
    elif param == "tilt":
        set_16bit_value(data, base_addr + 16, value)
    elif param == "mode":
        data[base_addr + 18] = value

def demo_complete_10_spots():
    """Démonstration complète de tous les paramètres avec 10 spots"""
    print("🚀 DÉMO COMPLÈTE LUXCORE DMX ENGINE")
    print("=" * 45)
    print("🎯 10 Spots + Tous paramètres")
    print("🎨 28 canaux base + 19×10 spots = 218 canaux")
    print()
    
    dmx_data = [0] * 512
    
    print("🌈 PHASE 1: PARAMÈTRES DE BASE (15s)")
    print("=" * 35)
    
    # Test des couleurs de base
    colors_base = [
        (255, 0, 0, "Rouge"),
        (255, 255, 0, "Jaune"),
        (0, 255, 0, "Vert"),
        (0, 255, 255, "Cyan"),
        (0, 0, 255, "Bleu"),
        (255, 0, 255, "Magenta"),
        (255, 128, 0, "Orange"),
        (255, 255, 255, "Blanc")
    ]
    
    for r, g, b, name in colors_base:
        print(f"   → Couleur base: {name}")
        dmx_data[0] = r  # Rouge base
        dmx_data[1] = g  # Vert base
        dmx_data[2] = b  # Bleu base
        send_artnet(dmx_data)
        time.sleep(1.5)
    
    print("🎭 PHASE 2: MODES DE MÉLANGE (20s)")
    print("=" * 30)
    
    # Couleur base pour voir les effets de mélange
    dmx_data[0] = 150  # Rouge base
    dmx_data[1] = 200  # Vert base
    dmx_data[2] = 255  # Bleu base
    
    blend_modes = [
        (0, "BLEND Normal"),
        (25, "BLEND Normal"),
        (51, "ADD Additif"),
        (76, "SUBTRACT Soustraction"),
        (102, "DARKEST Plus sombre"),
        (127, "LIGHTEST Plus clair"),
        (153, "DIFFERENCE Différence"),
        (178, "EXCLUSION Exclusion"),
        (204, "MULTIPLY Multiplication"),
        (229, "SCREEN Écran"),
        (255, "REPLACE Remplacement")
    ]
    
    for mode_val, mode_name in blend_modes:
        print(f"   → Mode: {mode_name}")
        dmx_data[19] = mode_val  # Canal 20 - Blend mode
        send_artnet(dmx_data)
        time.sleep(1.8)
    
    print("✨ PHASE 3: EFFETS SPÉCIAUX (25s)")
    print("=" * 28)
    
    # Reset blend mode
    dmx_data[19] = 0
    
    effects = [
        ("Pixelate", 22, [0, 50, 100, 150, 200, 255]),
        ("Sobel Edge", 23, [0, 128, 255, 128, 0]),
        ("RGB Split", 24, [0, 30, 60, 90, 120, 60, 30, 0]),
        ("Saturation A", 25, [0, 64, 128, 192, 255, 128, 64, 0]),
        ("Saturation B", 26, [0, 64, 128, 192, 255, 128, 64, 0]),
        ("Chromatic Aberration", 27, [0, 128, 255, 128, 0]),
        ("Blur A", 20, [0, 5, 10, 15, 20, 15, 10, 5, 0]),
        ("Blur B", 21, [0, 10, 20, 30, 40, 30, 20, 10, 0])
    ]
    
    for effect_name, channel, values in effects:
        print(f"   → Effet: {effect_name}")
        for value in values:
            dmx_data[channel] = value
            send_artnet(dmx_data)
            time.sleep(0.4)
        # Reset effet
        dmx_data[channel] = 0
        send_artnet(dmx_data)
        time.sleep(0.5)
    
    print("🎪 PHASE 4: BLADES 16-BIT (20s)")
    print("=" * 25)
    
    blade_positions = [
        (0, 0, 0, 0, 0, 0, 0, 0, "Toutes ouvertes"),
        (16384, 16384, 16384, 16384, 16384, 16384, 16384, 16384, "Semi-fermées"),
        (32768, 32768, 32768, 32768, 32768, 32768, 32768, 32768, "3/4 fermées"),
        (16384, 32768, 16384, 32768, 16384, 32768, 16384, 32768, "Alternées"),
        (8192, 49152, 8192, 49152, 8192, 49152, 8192, 49152, "Inclinées"),
        (65535, 65535, 65535, 65535, 65535, 65535, 65535, 65535, "Fermées")
    ]
    
    for a1, a2, b1, b2, c1, c2, d1, d2, description in blade_positions:
        print(f"   → Blades: {description}")
        set_16bit_value(dmx_data, 3, a1)   # Blade A1
        set_16bit_value(dmx_data, 5, a2)   # Blade A2
        set_16bit_value(dmx_data, 7, b1)   # Blade B1
        set_16bit_value(dmx_data, 9, b2)   # Blade B2
        set_16bit_value(dmx_data, 11, c1)  # Blade C1
        set_16bit_value(dmx_data, 13, c2)  # Blade C2
        set_16bit_value(dmx_data, 15, d1)  # Blade D1
        set_16bit_value(dmx_data, 17, d2)  # Blade D2
        send_artnet(dmx_data)
        time.sleep(3)
    
    # Reset blades
    for channel in range(3, 19, 2):
        set_16bit_value(dmx_data, channel, 0)
    
    print("🌟 PHASE 5: 10 SPOTS COMPLETS (60s)")
    print("=" * 30)
    
    # Configuration initiale des 10 spots
    spot_colors = [
        (255, 0, 0),    # Rouge
        (255, 128, 0),  # Orange
        (255, 255, 0),  # Jaune
        (128, 255, 0),  # Vert clair
        (0, 255, 0),    # Vert
        (0, 255, 128),  # Turquoise
        (0, 255, 255),  # Cyan
        (0, 128, 255),  # Bleu clair
        (0, 0, 255),    # Bleu
        (128, 0, 255)   # Violet
    ]
    
    print("   → Configuration des 10 spots...")
    for spot_id in range(10):
        r, g, b = spot_colors[spot_id]
        set_spot_param(dmx_data, spot_id, "red", r)
        set_spot_param(dmx_data, spot_id, "green", g)
        set_spot_param(dmx_data, spot_id, "blue", b)
        set_spot_param(dmx_data, spot_id, "alpha", 200)
        set_spot_param(dmx_data, spot_id, "size_pan", 20000 + spot_id * 2000)
        set_spot_param(dmx_data, spot_id, "size_tilt", 20000 + spot_id * 2000)
        set_spot_param(dmx_data, spot_id, "mode", 0)
    
    send_artnet(dmx_data)
    time.sleep(2)
    
    print("   → Test des positions...")
    # Animation des positions
    for step in range(300):  # 10 secondes à 30fps
        t = step / 299.0 * 4 * math.pi
        
        for spot_id in range(10):
            # Position en spirale
            angle = t + spot_id * (2 * math.pi / 10)
            radius = 0.3 + 0.2 * math.sin(t * 0.5)
            
            pan = int(32767 + radius * 25000 * math.cos(angle))
            tilt = int(32767 + radius * 25000 * math.sin(angle))
            
            set_spot_param(dmx_data, spot_id, "pan", pan)
            set_spot_param(dmx_data, spot_id, "tilt", tilt)
        
        send_artnet(dmx_data)
        time.sleep(1/30)
    
    print("   → Test des tailles...")
    # Animation des tailles
    for step in range(150):  # 5 secondes
        t = step / 149.0 * 2 * math.pi
        
        for spot_id in range(10):
            size_factor = 1.0 + 0.5 * math.sin(t + spot_id * math.pi / 5)
            size = int(15000 * size_factor)
            
            set_spot_param(dmx_data, spot_id, "size_pan", size)
            set_spot_param(dmx_data, spot_id, "size_tilt", size)
        
        send_artnet(dmx_data)
        time.sleep(1/30)
    
    print("   → Test des rotations...")
    # Animation des rotations
    for step in range(150):  # 5 secondes
        t = step / 149.0 * 8 * math.pi
        
        for spot_id in range(10):
            rotation = int((math.sin(t + spot_id * math.pi / 5) + 1) * 127.5)
            set_spot_param(dmx_data, spot_id, "rotation", rotation)
        
        send_artnet(dmx_data)
        time.sleep(1/30)
    
    print("   → Test des strokes...")
    # Test des contours
    for spot_id in range(10):
        set_spot_param(dmx_data, spot_id, "stroke_weight", 5)
        set_spot_param(dmx_data, spot_id, "stroke_alpha", 200)
        set_spot_param(dmx_data, spot_id, "stroke_red", 255)
        set_spot_param(dmx_data, spot_id, "stroke_green", 255)
        set_spot_param(dmx_data, spot_id, "stroke_blue", 255)
    
    send_artnet(dmx_data)
    time.sleep(3)
    
    print("   → Test des alphas...")
    # Animation des alphas
    for step in range(180):  # 6 secondes
        t = step / 179.0 * 4 * math.pi
        
        for spot_id in range(10):
            alpha = int((math.sin(t + spot_id * math.pi / 5) + 1) * 127.5)
            set_spot_param(dmx_data, spot_id, "alpha", alpha)
        
        send_artnet(dmx_data)
        time.sleep(1/30)
    
    print("🎆 PHASE 6: SPECTACLE FINAL (30s)")
    print("=" * 27)
    
    print("   → Spectacle coordonné complet...")
    # Spectacle final avec tous les paramètres
    for step in range(900):  # 30 secondes à 30fps
        t = step / 899.0 * 6 * math.pi
        
        # Couleurs de base animées
        dmx_data[0] = int(128 + 127 * math.sin(t * 0.7))
        dmx_data[1] = int(128 + 127 * math.sin(t * 0.5 + math.pi/3))
        dmx_data[2] = int(128 + 127 * math.sin(t * 0.3 + 2*math.pi/3))
        
        # Blades en mouvement fluide
        blade_base = 16384
        blade_range = 12000
        
        for i, channel in enumerate(range(3, 19, 2)):
            blade_offset = int(blade_range * math.sin(t * 0.8 + i * math.pi/4))
            set_16bit_value(dmx_data, channel, blade_base + blade_offset)
        
        # Spots en mouvement
        for spot_id in range(10):
            # Position en vortex
            angle = t + spot_id * (2 * math.pi / 10)
            spiral_factor = 0.3 + 0.4 * math.sin(t * 0.2)
            
            pan = int(32767 + spiral_factor * 28000 * math.cos(angle))
            tilt = int(32767 + spiral_factor * 28000 * math.sin(angle))
            
            set_spot_param(dmx_data, spot_id, "pan", pan)
            set_spot_param(dmx_data, spot_id, "tilt", tilt)
            
            # Taille pulsante
            size_factor = 1.0 + 0.6 * math.sin(t * 1.2 + spot_id * math.pi / 5)
            size = int(18000 * size_factor)
            set_spot_param(dmx_data, spot_id, "size_pan", size)
            set_spot_param(dmx_data, spot_id, "size_tilt", size)
            
            # Rotation
            rotation = int((t * 20 + spot_id * 25.6) % 256)
            set_spot_param(dmx_data, spot_id, "rotation", rotation)
            
            # Alpha ondulant
            alpha = int(150 + 105 * math.sin(t * 0.9 + spot_id * math.pi / 5))
            set_spot_param(dmx_data, spot_id, "alpha", alpha)
        
        # Effets spéciaux occasionnels
        if step % 30 == 0:  # Chaque seconde
            effect_choice = random.randint(0, 4)
            if effect_choice == 0:
                dmx_data[22] = random.randint(0, 100)  # Pixelate
            elif effect_choice == 1:
                dmx_data[24] = random.randint(0, 60)   # RGB Split
            elif effect_choice == 2:
                dmx_data[20] = random.randint(0, 15)   # Blur A
            elif effect_choice == 3:
                dmx_data[25] = random.randint(0, 200)  # Saturation
            else:
                # Reset effets
                dmx_data[22] = 0
                dmx_data[24] = 0
                dmx_data[20] = 0
                dmx_data[25] = 0
        
        send_artnet(dmx_data)
        time.sleep(1/30)
        
        # Affichage progrès
        if step % 150 == 0:
            progress = (step / 899.0) * 100
            print(f"   → Spectacle: {progress:.1f}%")
    
    print("🌙 FADE OUT FINAL (10s)")
    print("=" * 18)
    
    # Fade out progressif
    for fade_step in range(300):  # 10 secondes
        fade = 1.0 - (fade_step / 299.0)
        
        # Fade couleurs base
        dmx_data[0] = int(dmx_data[0] * fade)
        dmx_data[1] = int(dmx_data[1] * fade)
        dmx_data[2] = int(dmx_data[2] * fade)
        
        # Fade spots
        for spot_id in range(10):
            current_alpha = int(200 * fade)
            set_spot_param(dmx_data, spot_id, "alpha", current_alpha)
        
        # Ouverture progressive des blades
        for channel in range(3, 19, 2):
            blade_value = int(16384 * (1.0 - fade))
            set_16bit_value(dmx_data, channel, blade_value)
        
        # Reset effets
        for effect_channel in [20, 21, 22, 23, 24, 25, 26, 27]:
            dmx_data[effect_channel] = int(dmx_data[effect_channel] * fade)
        
        send_artnet(dmx_data)
        time.sleep(1/30)
    
    # Blackout final
    dmx_data = [0] * 512
    send_artnet(dmx_data)
    
    print()
    print("✨ DÉMO COMPLÈTE TERMINÉE!")
    print("=" * 30)
    print("📊 PARAMÈTRES TESTÉS:")
    print("   🎨 Couleurs base RGB")
    print("   🔀 11 modes de mélange")
    print("   ✨ 8 effets spéciaux")  
    print("   🎭 Blades 16-bit inclinables")
    print("   🌟 10 spots complets:")
    print("      → RGB, Alpha, Stroke")
    print("      → Taille 16-bit, Position 16-bit")
    print("      → Rotation, Mode")
    print("   📈 Total: 218 canaux DMX utilisés")
    print("   🚀 LuxCore DMX Engine 100% testé!")

if __name__ == "__main__":
    try:
        print("🚀 Préparation de la démo complète...")
        print("⏱️  Durée estimée: ~3 minutes")
        print("📺 Tous les paramètres seront testés")
        print("⚠️  Ctrl+C pour arrêter")
        print()
        demo_complete_10_spots()
    except KeyboardInterrupt:
        print("\n⏹️  Démo interrompue")
        send_artnet([0] * 512)
    except Exception as e:
        print(f"❌ Erreur: {e}")
        send_artnet([0] * 512)