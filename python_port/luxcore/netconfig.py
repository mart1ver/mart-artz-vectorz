"""Énumération des cartes réseau (stdlib pure, sans dépendance).

Sert au menu : choisir sur quelle interface lier la réception ArtNet (bind d'un
socket UDP sur une IP précise) et, best-effort, restreindre l'émission NDI.

`list_interfaces()` renvoie une liste de `(nom, ipv4)` triée, toujours préfixée
par l'entrée « toutes les interfaces » (`0.0.0.0`). L'IPv4 est lue via l'ioctl
Linux `SIOCGIFADDR` ; sur un OS sans `fcntl` (ex. Windows) on dégrade proprement
en ne listant que « toutes les interfaces ».
"""
from __future__ import annotations

import socket

ALL_IFACES = ("Toutes les interfaces", "0.0.0.0")

_SIOCGIFADDR = 0x8915


def _ipv4_of(ifname: str) -> str | None:
    """IPv4 de l'interface `ifname` (None si aucune / non disponible)."""
    try:
        import fcntl
        import struct
    except ImportError:
        return None
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        packed = struct.pack("256s", ifname.encode()[:15])
        return socket.inet_ntoa(fcntl.ioctl(s.fileno(), _SIOCGIFADDR, packed)[20:24])
    except OSError:
        return None
    finally:
        s.close()


def list_interfaces() -> list[tuple[str, str]]:
    """Liste `(nom, ipv4)` des interfaces ayant une IPv4, précédée de
    « Toutes les interfaces » (0.0.0.0). L'ordre des interfaces réelles suit
    `if_nameindex` (stable)."""
    out = [ALL_IFACES]
    try:
        names = [name for _idx, name in socket.if_nameindex()]
    except (OSError, AttributeError):
        return out
    for name in names:
        ip = _ipv4_of(name)
        if ip:
            out.append((name, ip))
    return out


def ip_for(label_or_ip: str) -> str:
    """Résout un choix (nom d'interface OU IP) vers l'IP de bind. Un nom inconnu
    ou vide -> '0.0.0.0' (toutes les interfaces)."""
    if not label_or_ip:
        return "0.0.0.0"
    for name, ip in list_interfaces():
        if label_or_ip in (name, ip):
            return ip
    # peut-être déjà une IP littérale valable
    try:
        socket.inet_aton(label_or_ip)
        return label_or_ip
    except OSError:
        return "0.0.0.0"
