"""Starts the desktop widget with this user's data folder (see app_paths.py)."""
import importlib.machinery
import importlib.util
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import app_paths  # noqa: E402  (sets the data folder before the widget loads settings)

spec = importlib.util.spec_from_loader(
    "gold_hunt_widget",
    importlib.machinery.SourceFileLoader("gold_hunt_widget", str(app_paths.CODE / "widget.pyw")))
widget = importlib.util.module_from_spec(spec)
spec.loader.exec_module(widget)
widget.STATE = app_paths.DATA / "widget_state.json"

lock = widget.single_instance()
widget.Widget().mainloop()
