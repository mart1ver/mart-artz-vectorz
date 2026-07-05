"""Décodage vidéo en thread (PyAV) — source partagée pour le mode forme VIDEO.

Décode un fichier en boucle vers des frames RGBA numpy (redimensionnées à une
taille de texture fixe). Le moteur téléverse la dernière frame dans une texture
GL une fois par frame de rendu ; tous les spots en mode VIDEO l'échantillonnent.
"""
from __future__ import annotations

import threading

import numpy as np


class VideoDecoder(threading.Thread):
    def __init__(self, path: str, width: int, height: int):
        super().__init__(daemon=True)
        self.path = path
        self.width, self.height = width, height
        self._frame: np.ndarray | None = None
        self._version = 0
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self.ok = False

    def run(self):
        import av
        try:
            container = av.open(self.path)
        except Exception as e:                # noqa: BLE001
            print(f"[video] ouverture '{self.path}' impossible : {e}")
            return
        self.ok = True
        stream = container.streams.video[0]
        print(f"[video] {self.path} — {stream.width}x{stream.height} (boucle)")
        while not self._stop.is_set():
            for frame in container.decode(stream):
                if self._stop.is_set():
                    break
                rgba = frame.reformat(width=self.width, height=self.height, format="rgba")
                plane = rgba.planes[0]
                arr = np.frombuffer(plane, dtype=np.uint8)
                arr = arr.reshape(self.height, plane.line_size // 4, 4)[:, :self.width, :]
                with self._lock:
                    self._frame = np.ascontiguousarray(arr)
                    self._version += 1
            container.seek(0)                 # boucle infinie

    def latest(self) -> tuple[np.ndarray | None, int]:
        with self._lock:
            return self._frame, self._version

    def stop(self):
        self._stop.set()
