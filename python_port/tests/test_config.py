"""Tests de netconfig (énumération réseau) et appconfig (persistance JSON)."""
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from luxcore import netconfig as nc                           # noqa: E402
from luxcore import appconfig as ac                           # noqa: E402


# ── netconfig ────────────────────────────────────────────────────────────────
def test_list_interfaces_starts_with_all():
    ifs = nc.list_interfaces()
    assert ifs[0] == nc.ALL_IFACES == ("Toutes les interfaces", "0.0.0.0")
    for name, ip in ifs:
        assert isinstance(name, str) and isinstance(ip, str)


def test_ip_for_resolution():
    assert nc.ip_for("") == "0.0.0.0"
    assert nc.ip_for("0.0.0.0") == "0.0.0.0"
    assert nc.ip_for("interface_inexistante") == "0.0.0.0"
    # une IP littérale valable non listée est renvoyée telle quelle
    assert nc.ip_for("10.11.12.13") == "10.11.12.13"
    # résoudre par nom d'interface -> son IP (si une interface réelle existe)
    real = [(n, ip) for n, ip in nc.list_interfaces() if n != "Toutes les interfaces"]
    if real:
        name, ip = real[0]
        assert nc.ip_for(name) == ip


# ── appconfig ────────────────────────────────────────────────────────────────
def _tmp():
    d = tempfile.mkdtemp()
    return os.path.join(d, "cfg.json")


def test_load_missing_returns_defaults():
    cfg = ac.load("/nonexistent/dir/cfg.json")
    assert cfg == ac.DEFAULTS
    assert cfg is not ac.DEFAULTS          # copie, pas la référence


def test_save_then_load_roundtrip():
    p = _tmp()
    ac.save({**ac.DEFAULTS, "width": 1280, "height": 720,
             "start_universe": 3, "start_addr": 100, "artnet_ip": "192.168.1.50"}, p)
    cfg = ac.load(p)
    assert cfg["width"] == 1280 and cfg["height"] == 720
    assert cfg["start_universe"] == 3 and cfg["start_addr"] == 100
    assert cfg["artnet_ip"] == "192.168.1.50"


def test_validation_clamps_out_of_range():
    p = _tmp()
    ac.save({"width": 999999, "height": -5, "fps": 0, "spots": 200,
             "start_universe": 999, "start_addr": 0, "name": ""}, p)
    cfg = ac.load(p)
    assert cfg["width"] == 7680 and cfg["height"] == 64
    assert cfg["fps"] == 1 and cfg["spots"] == 64
    assert cfg["start_universe"] == 255 and cfg["start_addr"] == 1
    assert cfg["name"] == "LuxCore"        # nom vide -> défaut


def test_corrupt_file_falls_back_to_defaults():
    p = _tmp()
    with open(p, "w") as f:
        f.write("{ pas du json valide ,,,")
    assert ac.load(p) == ac.DEFAULTS


def test_unknown_keys_ignored():
    p = _tmp()
    ac.save({**ac.DEFAULTS, "hack": 1, "width": 800}, p)
    cfg = ac.load(p)
    assert "hack" not in cfg and cfg["width"] == 800


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
