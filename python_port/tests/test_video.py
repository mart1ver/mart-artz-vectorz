"""Tests du cache de décodage vidéo (VideoClip).

Génère un mini-clip synthétique (PyAV) puis vérifie le décodage-en-cache :
nombre de frames, fps, résolution du cache, bornage de l'index, garde-fou
`max_frames`. Autonome (pas de dépendance à data/videos).
"""
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import numpy as np                                              # noqa: E402

from luxcore.video import VideoClip                             # noqa: E402

N_FRAMES = 12
SRC_W, SRC_H, FPS = 64, 48, 10


def _make_clip(path):
    """Encode N_FRAMES images de couleurs variées à FPS ips dans `path`."""
    import av
    container = av.open(path, mode="w")
    stream = container.add_stream("mpeg4", rate=FPS)
    stream.width, stream.height, stream.pix_fmt = SRC_W, SRC_H, "yuv420p"
    for i in range(N_FRAMES):
        img = np.zeros((SRC_H, SRC_W, 3), np.uint8)
        img[:, :, i % 3] = 40 + i * 15                 # couleur qui évolue
        frame = av.VideoFrame.from_ndarray(img, format="rgb24")
        for pkt in stream.encode(frame):
            container.mux(pkt)
    for pkt in stream.encode():                        # flush
        container.mux(pkt)
    container.close()


def _clip(**kw):
    tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
    tmp.close()
    _make_clip(tmp.name)
    return tmp.name, VideoClip(tmp.name, 32, 24, **kw).load()


def test_decodes_all_frames_to_cache():
    path, clip = _clip()
    try:
        assert clip.ok
        assert clip.nframes == N_FRAMES, clip.nframes
        assert abs(clip.fps - FPS) < 1e-6, clip.fps
        assert abs(clip.duration - N_FRAMES / FPS) < 1e-6
        # frames au format cache demandé (H, W, RGBA), contiguës
        assert clip.frames[0].shape == (24, 32, 4), clip.frames[0].shape
        assert clip.frames[0].flags["C_CONTIGUOUS"]
    finally:
        os.unlink(path)


def test_frame_at_is_clamped():
    path, clip = _clip()
    try:
        assert clip.frame_at(-5) is clip.frames[0]
        assert clip.frame_at(0) is clip.frames[0]
        assert clip.frame_at(999) is clip.frames[clip.nframes - 1]
    finally:
        os.unlink(path)


def test_max_frames_caps_cache():
    path, clip = _clip(max_frames=5)
    try:
        assert clip.nframes == 5, clip.nframes
    finally:
        os.unlink(path)


def test_empty_clip_is_safe():
    clip = VideoClip("/nonexistent/path.mp4", 32, 24).load()
    assert not clip.ok
    assert clip.nframes == 0
    assert clip.frame_at(0) is None


if __name__ == "__main__":
    import traceback
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for fn in fns:
        try:
            fn(); print(f"  ok   {fn.__name__}")
        except Exception:
            failed += 1; print(f"  FAIL {fn.__name__}"); traceback.print_exc()
    print(f"\n{len(fns) - failed}/{len(fns)} tests OK")
    sys.exit(1 if failed else 0)
