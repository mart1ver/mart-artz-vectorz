#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DÉMO BLEND MODES + EFFETS AVEC SPOTS VISIBLES - LUXCORE DMX ENGINE
=================================================================
Démonstration des modes de mélange et effets avec spots toujours visibles
Les blades restent ouvertes pour voir les effets clairement
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

def setup_visible_spots(data, num_spots=7):
    """Configure des spots visibles et colorés"""
    spot_colors = [
        (255, 100, 100),  # Rouge clair
        (255, 200, 100),  # Orange
        (255, 255, 100),  # Jaune
        (100, 255, 100),  # Vert clair
        (100, 200, 255),  # Bleu clair
        (200, 100, 255),  # Violet
        (255, 150, 200),  # Rose
    ]
    
    for spot_id in range(num_spots):
        r, g, b = spot_colors[spot_id]
        set_spot_param(data, spot_id, "red", r)
        set_spot_param(data, spot_id, "green", g)
        set_spot_param(data, spot_id, "blue", b)
        set_spot_param(data, spot_id, "alpha", 220)  # Bien visible
        
        # Tailles variées
        size = 25000 + spot_id * 3000
        set_spot_param(data, spot_id, "size_pan", size)
        set_spot_param(data, spot_id, "size_tilt", size)
        
        # Positions réparties
        angle = spot_id * (2 * math.pi / num_spots)
        radius = 0.3
        pan = int(32767 + radius * 25000 * math.cos(angle))
        tilt = int(32767 + radius * 25000 * math.sin(angle))
        
        set_spot_param(data, spot_id, "pan", pan)
        set_spot_param(data, spot_id, "tilt", tilt)
        set_spot_param(data, spot_id, "mode", 0)

def keep_blades_fixed_minimal(data, time_factor):
    """Blades fixes à des valeurs très faibles (0-3% fermeture)"""
    # Dans Processing: fill(0) + map() = 0=ouvert, 65535=fermé (masque noir)
    # Blades quasi-fixes entre 0-3% de fermeture pour visibilité maximale
    min_closure = 0       # Complètement ouvert
    max_closure = 1966    # 3% de fermeture maximum (3% de 65535)
    movement_range = 1000 # Mouvement très subtil
    
    # Blade A (top) - quasi-fixe avec variation minimale
    blade_a1_base = 500 + 400 * math.sin(time_factor * 0.02)  # 0.7-1.4% fermeture
    blade_a2_base = 600 + 300 * math.sin(time_factor * 0.015 + math.pi/6)  # 0.9-1.4% fermeture
    
    # Inclinaison A très minimale
    incline_a = 200 * math.sin(time_factor * 0.01)
    blade_a1 = int(max(min_closure, min(blade_a1_base + incline_a, max_closure)))
    blade_a2 = int(max(min_closure, min(blade_a2_base - incline_a, max_closure)))
    
    set_16bit_value(data, 3, blade_a1)  # A1
    set_16bit_value(data, 5, blade_a2)  # A2
    
    # Blade B (right) - quasi-fixe avec variation minimale
    blade_b1_base = 400 + 350 * math.sin(time_factor * 0.018 + math.pi/3)  # 0.6-1.1% fermeture
    blade_b2_base = 550 + 250 * math.sin(time_factor * 0.022 + math.pi/2)  # 0.8-1.2% fermeture
    
    # Inclinaison B minimale
    incline_b = 150 * math.sin(time_factor * 0.012 + math.pi/4)
    blade_b1 = int(max(min_closure, min(blade_b1_base + incline_b, max_closure)))
    blade_b2 = int(max(min_closure, min(blade_b2_base - incline_b, max_closure)))
    
    set_16bit_value(data, 7, blade_b1)  # B1
    set_16bit_value(data, 9, blade_b2)  # B2
    
    # Blade C (bottom) - quasi-fixe avec variation minimale
    blade_c1_base = 300 + 450 * math.sin(time_factor * 0.025 + 2*math.pi/3)  # 0.5-1.1% fermeture
    blade_c2_base = 700 + 400 * math.sin(time_factor * 0.017 + 5*math.pi/6)  # 1.0-1.7% fermeture
    
    # Inclinaison C minimale
    incline_c = 180 * math.sin(time_factor * 0.008 + math.pi/2)
    blade_c1 = int(max(min_closure, min(blade_c1_base + incline_c, max_closure)))
    blade_c2 = int(max(min_closure, min(blade_c2_base - incline_c, max_closure)))
    
    set_16bit_value(data, 11, blade_c1)  # C1
    set_16bit_value(data, 13, blade_c2)  # C2
    
    # Blade D (left) - quasi-fixe avec variation minimale
    blade_d1_base = 650 + 500 * math.sin(time_factor * 0.019 + math.pi)  # 1.0-1.8% fermeture
    blade_d2_base = 800 + 350 * math.sin(time_factor * 0.013 + 4*math.pi/3)  # 1.2-1.8% fermeture
    
    # Inclinaison D minimale
    incline_d = 220 * math.sin(time_factor * 0.006 + 3*math.pi/4)
    blade_d1 = int(max(min_closure, min(blade_d1_base + incline_d, max_closure)))
    blade_d2 = int(max(min_closure, min(blade_d2_base - incline_d, max_closure)))
    
    set_16bit_value(data, 15, blade_d1)  # D1
    set_16bit_value(data, 17, blade_d2)  # D2

def demo_blend_effects_spots():
    """Démonstration des blend modes et effets avec spots visibles"""
    print("🎨 DÉMO BLEND MODES + EFFETS AVEC SPOTS VISIBLES")
    print("=" * 55)
    print("✨ Spots toujours visibles")
    print("🎭 Blades quasi-fixes (0-3% fermeture)")
    print("🔀 Focus sur blend modes et effets")
    print()
    
    dmx_data = [0] * 512
    
    # Configuration initiale - fond coloré
    print("🌈 Configuration initiale...")
    dmx_data[0] = 80   # Rouge base (modéré pour voir les effets)
    dmx_data[1] = 120  # Vert base
    dmx_data[2] = 160  # Bleu base
    
    # Configuration des spots visibles
    setup_visible_spots(dmx_data, 7)
    
    # Blades en mouvement fluide continu
    keep_blades_fixed_minimal(dmx_data, 0)
    
    send_artnet(dmx_data)
    time.sleep(2)
    print("   ✓ Base établie avec spots visibles")
    
    print("\n🔀 PHASE 1: MODES DE MÉLANGE AVEC SPOTS (60s)")
    print("=" * 45)
    
    blend_modes = [
        (0, "BLEND - Normal", 15),
        (25, "BLEND - Normal (25)", 15),
        (51, "ADD - Additif", 15),
        (76, "SUBTRACT - Soustraction", 10),
        (102, "DARKEST - Plus sombre", 10),
        (127, "LIGHTEST - Plus clair", 15),
        (153, "DIFFERENCE - Différence", 12),
        (178, "EXCLUSION - Exclusion", 12),
        (204, "MULTIPLY - Multiplication", 10),
        (229, "SCREEN - Écran", 15),
        (255, "REPLACE - Remplacement", 8)
    ]
    
    for mode_val, mode_name, duration in blend_modes:
        print(f"   🎭 Mode: {mode_name}")
        
        dmx_data[19] = mode_val  # Canal 20 - Blend mode
        
        # Animation pendant le test du mode
        for step in range(duration * 10):  # 10 fps pour cette phase
            t = step / float(duration * 10 - 1) * 2 * math.pi
            
            # Variations subtiles du fond pour voir l'effet du blend mode
            dmx_data[0] = int(80 + 60 * math.sin(t * 0.7))
            dmx_data[1] = int(120 + 80 * math.sin(t * 0.5 + math.pi/3))
            dmx_data[2] = int(160 + 70 * math.sin(t * 0.3 + 2*math.pi/3))
            
            # Animation légère des spots
            for spot_id in range(7):
                # Légère variation d'alpha
                base_alpha = 220
                alpha_var = int(base_alpha + 35 * math.sin(t + spot_id * math.pi/7))
                set_spot_param(dmx_data, spot_id, "alpha", alpha_var)
                
                # Rotation lente
                rotation = int((t * 10 + spot_id * 36.5) % 256)
                set_spot_param(dmx_data, spot_id, "rotation", rotation)
            
            # Blades légèrement mobiles
            # Blades en mouvement fluide continu
            keep_blades_fixed_minimal(dmx_data, t)
            
            send_artnet(dmx_data)
            time.sleep(0.1)
    
    print("   ✓ Tous les blend modes testés")
    
    # Reset au mode normal pour les effets
    dmx_data[19] = 0
    
    print("\n✨ PHASE 2: EFFETS SPÉCIAUX AVEC SPOTS (80s)")
    print("=" * 42)
    
    effects_tests = [
        ("Pixelate", 22, [0, 30, 60, 100, 150, 200, 255, 150, 100, 50, 0], 20),
        ("RGB Split", 24, [0, 20, 40, 60, 80, 100, 80, 60, 40, 20, 0], 20),
        ("Blur A (Size)", 20, [0, 5, 10, 15, 20, 25, 20, 15, 10, 5, 0], 20),
        ("Blur B (Sigma)", 21, [0, 10, 20, 30, 40, 50, 40, 30, 20, 10, 0], 20),
        ("Saturation A", 25, [128, 150, 180, 200, 230, 255, 200, 150, 128], 15),
        ("Saturation B", 26, [128, 100, 80, 50, 20, 0, 50, 100, 128], 15),
        ("Sobel Edge", 23, [0, 128, 255, 128, 0], 10),
        ("Chromatic Aberration", 27, [0, 128, 255, 128, 0], 10)
    ]
    
    for effect_name, channel, values, base_duration in effects_tests:
        print(f"   ✨ Effet: {effect_name}")
        
        steps_per_value = max(15, base_duration // len(values))
        
        for value in values:
            dmx_data[channel] = value
            
            # Animation pendant l'effet
            for step in range(steps_per_value):
                t = step / float(steps_per_value - 1) * 2 * math.pi
                
                # Animation des spots pendant l'effet
                for spot_id in range(7):
                    # Position légèrement mobile
                    base_angle = spot_id * (2 * math.pi / 7)
                    radius = 0.3 + 0.1 * math.sin(t * 0.5)
                    
                    pan = int(32767 + radius * 25000 * math.cos(base_angle + t * 0.2))
                    tilt = int(32767 + radius * 25000 * math.sin(base_angle + t * 0.2))
                    
                    set_spot_param(dmx_data, spot_id, "pan", pan)
                    set_spot_param(dmx_data, spot_id, "tilt", tilt)
                    
                    # Taille pulsante
                    size_base = 25000 + spot_id * 3000
                    size_var = int(size_base + 5000 * math.sin(t + spot_id * math.pi/7))
                    set_spot_param(dmx_data, spot_id, "size_pan", size_var)
                    set_spot_param(dmx_data, spot_id, "size_tilt", size_var)
                
                # Fond animé
                dmx_data[0] = int(80 + 40 * math.sin(t * 0.6))
                dmx_data[1] = int(120 + 50 * math.sin(t * 0.4 + math.pi/3))
                dmx_data[2] = int(160 + 45 * math.sin(t * 0.8 + 2*math.pi/3))
                
                # Blades mobiles
                # Blades en mouvement fluide continu
                keep_blades_fixed_minimal(dmx_data, t * 2)
                
                send_artnet(dmx_data)
                time.sleep(0.067)  # ~15 fps
        
        # Reset de l'effet
        dmx_data[channel] = 0
        send_artnet(dmx_data)
        time.sleep(0.5)
    
    print("   ✓ Tous les effets testés")
    
    print("\n🎪 PHASE 3: COMBINAISONS BLEND + EFFETS (45s)")
    print("=" * 44)
    
    combinations = [
        ("ADD + Pixelate", 51, 22, 80, 15),
        ("MULTIPLY + RGB Split", 204, 24, 50, 15),
        ("SCREEN + Blur", 229, 20, 15, 15),
        ("DIFFERENCE + Saturation", 153, 25, 200, 15),
        ("LIGHTEST + Chromatic", 127, 27, 255, 12)
    ]
    
    for combo_name, blend_val, effect_channel, effect_val, duration in combinations:
        print(f"   🔥 Combinaison: {combo_name}")
        
        dmx_data[19] = blend_val  # Blend mode
        dmx_data[effect_channel] = effect_val  # Effet
        
        # Animation spectaculaire
        for step in range(duration * 15):  # 15 fps
            t = step / float(duration * 15 - 1) * 4 * math.pi
            
            # Fond très animé
            dmx_data[0] = int(100 + 80 * math.sin(t * 0.8))
            dmx_data[1] = int(140 + 90 * math.sin(t * 0.6 + math.pi/3))
            dmx_data[2] = int(180 + 75 * math.sin(t * 0.4 + 2*math.pi/3))
            
            # Spots en mouvement dynamique
            for spot_id in range(7):
                # Mouvement en spirale
                angle = t * 0.3 + spot_id * (2 * math.pi / 7)
                radius = 0.2 + 0.3 * math.sin(t * 0.2)
                
                pan = int(32767 + radius * 28000 * math.cos(angle))
                tilt = int(32767 + radius * 28000 * math.sin(angle))
                
                set_spot_param(dmx_data, spot_id, "pan", pan)
                set_spot_param(dmx_data, spot_id, "tilt", tilt)
                
                # Alpha pulsant
                alpha = int(180 + 75 * math.sin(t * 0.7 + spot_id * math.pi/7))
                set_spot_param(dmx_data, spot_id, "alpha", alpha)
                
                # Rotation rapide
                rotation = int((t * 30 + spot_id * 51.4) % 256)
                set_spot_param(dmx_data, spot_id, "rotation", rotation)
            
            # Blades avec mouvement fluide et inclinaisons coordonnées
            keep_blades_fixed_minimal(dmx_data, t + step * 0.01)
            
            send_artnet(dmx_data)
            time.sleep(1/15)
        
        # Reset
        dmx_data[effect_channel] = 0
        send_artnet(dmx_data)
        time.sleep(1)
    
    print("   ✓ Combinaisons testées")
    
    print("\n🌅 FADE OUT PROGRESSIF (15s)")
    print("=" * 27)
    
    # Reset blend mode
    dmx_data[19] = 0
    
    # Fade out élégant
    for fade_step in range(225):  # 15 secondes à 15fps
        fade = 1.0 - (fade_step / 224.0)
        
        # Fade du fond
        dmx_data[0] = int(80 * fade)
        dmx_data[1] = int(120 * fade)
        dmx_data[2] = int(160 * fade)
        
        # Fade des spots
        for spot_id in range(7):
            alpha = int(220 * fade)
            set_spot_param(dmx_data, spot_id, "alpha", alpha)
        
        # Ouverture finale des blades (vers 0 = complètement ouvert)
        initial_closure = 1966  # 3% de fermeture au début du fade
        final_blade = int(initial_closure * (1.0 - fade))  # Fade vers 0 (ouvert)
        for channel in range(3, 19, 2):
            set_16bit_value(dmx_data, channel, final_blade)
        
        send_artnet(dmx_data)
        time.sleep(1/15)
    
    # Blackout final
    dmx_data = [0] * 512
    send_artnet(dmx_data)
    
    print()
    print("✨ DÉMO BLEND MODES + EFFETS TERMINÉE!")
    print("=" * 42)
    print("🎭 RÉSULTATS:")
    print("   🔀 11 modes de mélange testés avec spots visibles")
    print("   ✨ 8 effets spéciaux démontrés en action")
    print("   🔥 5 combinaisons spectaculaires")
    print("   🎨 Spots toujours colorés et mobiles")
    print("   🎪 Blades majoritairement ouvertes")
    print("   🌈 Rendu visuel optimal pour voir les effets!")

if __name__ == "__main__":
    try:
        print("🎨 Démarrage démo blend modes + effets...")
        print("⏱️  Durée: ~3-4 minutes")
        print("👁️  Spots toujours visibles")
        print("🎭 Blades ouvertes pour voir les effets")
        print("⚠️  Ctrl+C pour arrêter")
        print()
        demo_blend_effects_spots()
    except KeyboardInterrupt:
        print("\n⏹️  Démo interrompue")
        send_artnet([0] * 512)
    except Exception as e:
        print(f"❌ Erreur: {e}")
        send_artnet([0] * 512)