"""Where this user's private data lives (settings.ini, alert state, dashboard).

The installer writes data_dir.txt next to the app files, pointing at %APPDATA%\\Gold Hunt,
so reinstalling or updating the app never touches the user's own data. The environment
variable GOLD_HUNT_DATA overrides it. With neither (running from the source folder), the
files stay next to the code, exactly as before.
"""
import os
from pathlib import Path

import gold_hunt

CODE = gold_hunt.HERE


def data_dir():
    d = os.environ.get("GOLD_HUNT_DATA", "").strip()
    if not d:
        marker = CODE / "data_dir.txt"
        if marker.exists():
            d = os.path.expandvars(marker.read_text(encoding="utf-8").strip())
    return Path(d) if d else CODE


def apply():
    """Point gold_hunt's data files at the user's data folder. Returns that folder."""
    d = data_dir()
    d.mkdir(parents=True, exist_ok=True)
    gold_hunt.SETTINGS = d / "settings.ini"
    gold_hunt.STATE = d / "alerts_state.json"
    gold_hunt.GOLD_REF = d / "gold_ref.json"
    gold_hunt.DASHBOARD = d / "dashboard.html"
    return d


DATA = apply()
