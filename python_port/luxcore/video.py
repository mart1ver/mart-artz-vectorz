"""Décodage vidéo (PyAV) pour le mode VIDEO.

`VideoClip` décode le clip **entier une seule fois** dans un cache mémoire de
frames RGBA numpy (résolution réduite). Le moteur pioche `cache[idx]` selon un
**playhead virtuel par spot** (start / vitesse / pause / loop) → contrôle de
lecture indépendant, coût CPU permanent nul, lecture déterministe. Coût : RAM
(≈ largeur·hauteur·4 · nb_frames par clip).
"""
from __future__ import annotations

import numpy as np


class VideoClip:
    """Clip décodé intégralement en cache mémoire (frames RGBA numpy contiguës).

    `load()` est bloquant (à appeler au démarrage). Ensuite `frames[idx]` donne
    la frame `idx` (0..nframes-1) et `fps`/`duration` situent la timeline. Le
    moteur convertit un temps de lecture en index : `idx = round(t · fps)`.
    """

    def __init__(self, path: str, width: int, height: int, max_frames: int | None = None):
        self.path = path
        self.width, self.height = width, height
        self.max_frames = max_frames
        self.frames: list[np.ndarray] = []
        self.fps = 30.0
        self.ok = False

    def load(self) -> "VideoClip":
        import av
        try:
            container = av.open(self.path)
        except Exception as e:                # noqa: BLE001
            print(f"[video] ouverture '{self.path}' impossible : {e}")
            return self
        stream = container.streams.video[0]
        rate = stream.average_rate or stream.base_rate
        self.fps = float(rate) if rate else 30.0
        for frame in container.decode(stream):
            rgba = frame.reformat(width=self.width, height=self.height, format="rgba")
            plane = rgba.planes[0]
            arr = np.frombuffer(plane, dtype=np.uint8)
            arr = arr.reshape(self.height, plane.line_size // 4, 4)[:, :self.width, :]
            self.frames.append(np.ascontiguousarray(arr))
            if self.max_frames is not None and len(self.frames) >= self.max_frames:
                break
        container.close()
        self.ok = len(self.frames) > 0
        print(f"[video] {self.path} — {stream.width}x{stream.height} -> "
              f"{len(self.frames)} frames @ {self.fps:.2f} fps "
              f"(cache {self.width}x{self.height})")
        return self

    @property
    def nframes(self) -> int:
        return len(self.frames)

    @property
    def duration(self) -> float:
        return self.nframes / self.fps if self.fps else 0.0

    def frame_at(self, idx: int) -> np.ndarray | None:
        """Frame `idx` bornée dans [0, nframes-1]. None si le cache est vide."""
        n = self.nframes
        if n == 0:
            return None
        return self.frames[max(0, min(n - 1, int(idx)))]

    def latest(self) -> tuple[np.ndarray | None, int]:
        with self._lock:
            return self._frame, self._version

    def stop(self):
        self._stop.set()
