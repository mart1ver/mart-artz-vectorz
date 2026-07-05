"""Réception ArtNet UDP multi-univers — remplace artnet_functions.pde (do_artnet).

Écoute UDP:6454, parse les paquets ArtDMX (OpCode 0x5000) et agrège jusqu'à 9
univers dans un buffer plat de 512×9 octets, qui est la `dmx_data[]` du moteur.

Choix de portage assumé : l'univers d'un paquet est lu depuis son champ
Port-Address 15-bit standard (octet 14 = bits bas, octet 15 = bits hauts) et
mappé directement sur la tranche [u*512 : u*512+512]. C'est ce qu'émet
`send_multi` (luxcore_artnet.py, univers 0,1,2…), donc compatible avec les shows
existants. La sémantique "subnet" d'artnet4j côté Processing était un détail
d'implémentation, ici remplacée par le comportement standard et sain.
"""
from __future__ import annotations

import socket
import struct
import threading

from . import constants as C

ARTNET_HEADER = b"Art-Net\x00"
OP_DMX = 0x5000
ARTNET_PORT = 6454


class ArtNetReceiver(threading.Thread):
    """Thread récepteur. `snapshot()` renvoie une copie stable du buffer DMX."""

    def __init__(self, port: int = ARTNET_PORT, bind_addr: str = "0.0.0.0",
                 max_universes: int = C.MAX_UNIVERSES):
        super().__init__(daemon=True)
        self.port = port
        self.bind_addr = bind_addr
        self.max_universes = max_universes
        self._buf = bytearray(C.UNIVERSE_SIZE * max_universes)
        self._lock = threading.Lock()
        self._stop = threading.Event()
        # diagnostics
        self.packets = 0
        self.last_universe_seen = -1
        self.bound = False

    def run(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((self.bind_addr, self.port))
        except OSError as e:
            print(f"[ArtNet] bind {self.bind_addr}:{self.port} impossible : {e}")
            return
        self.bound = True
        sock.settimeout(0.25)
        print(f"[ArtNet] écoute UDP {self.bind_addr}:{self.port} "
              f"({self.max_universes} univers)")
        while not self._stop.is_set():
            try:
                data, _addr = sock.recvfrom(1024)
            except socket.timeout:
                continue
            except OSError:
                break
            self._handle(data)
        sock.close()

    def _handle(self, data: bytes) -> None:
        if len(data) < 18 or data[:8] != ARTNET_HEADER:
            return
        opcode = struct.unpack_from("<H", data, 8)[0]
        if opcode != OP_DMX:
            return
        # Port-Address 15-bit : octet 14 = bits bas, octet 15 = bits hauts (7 bits)
        universe = data[14] | ((data[15] & 0x7F) << 8)
        if universe >= self.max_universes:
            return
        length = struct.unpack_from(">H", data, 16)[0]
        payload = data[18:18 + length]
        if not payload:
            return
        off = universe * C.UNIVERSE_SIZE
        n = min(len(payload), C.UNIVERSE_SIZE)
        with self._lock:
            self._buf[off:off + n] = payload[:n]
            self.packets += 1
            self.last_universe_seen = universe

    def snapshot(self) -> bytearray:
        """Copie cohérente du buffer DMX complet (512×max_universes octets)."""
        with self._lock:
            return bytearray(self._buf)

    def stop(self) -> None:
        self._stop.set()
