#!/usr/bin/env python3
"""
Debug ArtNet pour LuxCore DMX Engine
Test de connexion avec packet ArtNet correct
"""

import socket
import struct
import time

def send_artnet_debug(target_ip="127.0.0.1", port=6454):
    """Send proper ArtNet packet with debug info"""
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    # Créer packet ArtNet correct
    dmx_data = [0] * 512
    
    # Test simple : Background rouge
    dmx_data[0] = 255  # Rouge background
    dmx_data[1] = 0    # Vert background  
    dmx_data[2] = 0    # Bleu background
    
    # Premier spot en blanc
    base = 20  # Adresse spot 1
    dmx_data[base] = 255      # Rouge spot
    dmx_data[base+1] = 255    # Vert spot
    dmx_data[base+2] = 255    # Bleu spot
    dmx_data[base+3] = 255    # Alpha spot
    
    # Taille spot (16-bit)
    size = 10000  # Grande taille
    dmx_data[base+9] = (size >> 8) & 0xFF   # MSB Pan
    dmx_data[base+10] = size & 0xFF         # LSB Pan  
    dmx_data[base+11] = (size >> 8) & 0xFF  # MSB Tilt
    dmx_data[base+12] = size & 0xFF         # LSB Tilt
    
    # Position centrée
    pos = 127 * 256  # Position 16-bit
    dmx_data[base+14] = (pos >> 8) & 0xFF   # MSB Pan pos
    dmx_data[base+15] = pos & 0xFF          # LSB Pan pos
    dmx_data[base+16] = (pos >> 8) & 0xFF   # MSB Tilt pos  
    dmx_data[base+17] = pos & 0xFF          # LSB Tilt pos
    
    dmx_data[base+18] = 0  # Rectangle
    
    print(f"🔧 DEBUG: Envoi vers {target_ip}:{port}")
    print(f"📊 DMX Data sample: Background RGB = {dmx_data[0]},{dmx_data[1]},{dmx_data[2]}")
    print(f"📍 Spot 1: RGB = {dmx_data[20]},{dmx_data[21]},{dmx_data[22]}, Alpha = {dmx_data[23]}")
    print(f"📏 Spot 1 Size: MSB={dmx_data[29]}, LSB={dmx_data[30]} (Total={dmx_data[29]*256+dmx_data[30]})")
    
    # Construire packet ArtNet EXACT
    header = b"Art-Net\x00"
    opcode = struct.pack("<H", 0x5000)  # ArtDMX 
    prot_ver_hi = 0
    prot_ver_lo = 14
    sequence = 0
    physical = 0
    sub_uni = 0
    net = 0
    length_hi = (len(dmx_data) >> 8) & 0xFF
    length_lo = len(dmx_data) & 0xFF
    
    packet = (header + 
              opcode + 
              bytes([prot_ver_hi, prot_ver_lo, sequence, physical, sub_uni, net, length_hi, length_lo]) +
              bytes(dmx_data))
    
    print(f"📦 Packet size: {len(packet)} bytes")
    print(f"🎯 Sending to LuxCore...")
    
    try:
        sock.sendto(packet, (target_ip, port))
        print("✅ Packet sent successfully!")
        
        # Envoyer plusieurs fois pour être sûr
        for i in range(5):
            time.sleep(0.2)
            sock.sendto(packet, (target_ip, port))
            print(f"   Packet {i+2} sent...")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        sock.close()

if __name__ == "__main__":
    print("🚀 LuxCore ArtNet Debug Test")
    send_artnet_debug()
    print("🎭 Si LuxCore est ouvert, vous devriez voir un fond rouge et un spot blanc !")