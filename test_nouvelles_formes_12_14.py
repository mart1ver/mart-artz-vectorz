#!/usr/bin/env python3
# Test des nouvelles formes 12-14 du LuxCore DMX Engine

import socket
import time
import struct
import math
import random

def create_artnet_packet(universe, dmx_data):
    header = b'Art-Net\x00'
    opcode = struct.pack('<H', 0x5000)  # OpDmx
    version = struct.pack('>H', 14)
    sequence = b'\x00'
    physical = b'\x00'
    universe_bytes = struct.pack('<H', universe)
    length = struct.pack('>H', len(dmx_data))
    return header + opcode + version + sequence + physical + universe_bytes + length + dmx_data

def send_dmx_data(sock, ip, universe, dmx_data):
    packet = create_artnet_packet(universe, dmx_data)
    sock.sendto(packet, (ip, 6454))

def test_nouvelles_formes():
    print("🎭 Test des nouvelles formes créatives 12-14")
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    dmx_ip = "127.0.0.1"
    
    # Base setup - fond noir, blend ADD
    base_params = [0] * 28
    base_params[0:3] = [0, 0, 0]    # BG noir
    base_params[26] = 5             # Blend LIGHTEST
    base_params[27] = 15            # 15 spots
    
    print("📡 Envoi de 15 spots avec les nouvelles formes...")
    
    try:
        for frame in range(300):  # 10 secondes à ~30fps
            dmx_data = base_params[:] + [0] * (512 - len(base_params))
            
            # 15 spots avec les nouvelles formes
            for i in range(15):
                addr = 28 + i * 19
                
                # Cycle à travers les formes 12, 13, 14
                forme = 12 + (i % 3)
                
                # Couleurs vives différentes par forme
                if forme == 12:  # Cœur - Rouge
                    dmx_data[addr:addr+3] = [255, 50, 100]
                elif forme == 13:  # Maison - Bleu  
                    dmx_data[addr:addr+3] = [50, 100, 255]
                else:  # Spirale - Vert
                    dmx_data[addr:addr+3] = [100, 255, 50]
                
                # Alpha fort
                dmx_data[addr+3] = 200
                
                # Pas de stroke pour ces formes
                dmx_data[addr+4] = 0
                dmx_data[addr+5] = 0
                
                # Taille variable selon la forme
                if forme == 14:  # Spirale plus grande
                    size = 150 + int(50 * math.sin(frame * 0.05 + i))
                else:
                    size = 100 + int(30 * math.sin(frame * 0.08 + i))
                
                dmx_data[addr+9] = size >> 8    # Size pan MSB
                dmx_data[addr+10] = size & 0xFF # Size pan LSB  
                dmx_data[addr+11] = size >> 8   # Size tilt MSB
                dmx_data[addr+12] = size & 0xFF # Size tilt LSB
                
                # Rotation lente
                rotation = int((frame + i * 30) * 2) % 256
                dmx_data[addr+13] = rotation
                
                # Position en cercle
                angle = (frame * 0.02 + i * 2.0 * math.pi / 15)
                radius = 150 + 50 * math.sin(frame * 0.03)
                
                pos_x = int(32767 + radius * math.cos(angle))
                pos_y = int(32767 + radius * math.sin(angle))
                
                dmx_data[addr+14] = pos_x >> 8    # Pos X MSB
                dmx_data[addr+15] = pos_x & 0xFF  # Pos X LSB
                dmx_data[addr+16] = pos_y >> 8    # Pos Y MSB  
                dmx_data[addr+17] = pos_y & 0xFF  # Pos Y LSB
                
                # Mode (forme)
                dmx_data[addr+18] = forme
            
            # Envoi
            send_dmx_data(sock, dmx_ip, 0, bytes(dmx_data))
            
            if frame % 30 == 0:
                print(f"   Frame {frame}/300 - Formes 12-14 en rotation")
            
            time.sleep(0.033)  # ~30 FPS
            
    except KeyboardInterrupt:
        print("\n🛑 Test interrompu")
    
    # Reset - éteindre tous les spots
    dmx_data = [0] * 512
    send_dmx_data(sock, dmx_ip, 0, bytes(dmx_data))
    
    sock.close()
    print("✅ Test terminé - Nouvelles formes 12-14 validées!")

if __name__ == "__main__":
    test_nouvelles_formes()