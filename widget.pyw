"""Gold Hunt desktop widget - a small always-visible panel with your prices and profit/loss.

Drag it anywhere; right-click for options. Refreshes every 5 minutes.
"""
import datetime as dt
import json
import socket
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path

import gold_hunt

HERE = gold_hunt.HERE
STATE = HERE / "widget_state.json"
REFRESH_MS = 5 * 60 * 1000
COLORS = {"bg": "#1e1c17", "card": "#26231d", "ink": "#f1ede4", "mute": "#a39d90",
          "gold": "#e0b44c", "up": "#4cc38a", "down": "#ef6b5b", "line": "#332f27"}
TEXT = {
    "en": {"gold": "Gold 24K", "pl": "P/L", "updated": "Updated {t}", "loading": "Loading prices…",
           "closed": "closed", "error": "Could not load prices - retrying", "refresh": "Refresh now",
           "open": "Open Gold Hunt", "top": "Always on top", "lang": "عربي", "close": "Close widget",
           "total": "Total P/L"},
    "ar": {"gold": "ذهب 24", "pl": "الربح", "updated": "آخر تحديث {t}", "loading": "جاري تحميل الأسعار…",
           "closed": "مغلق", "error": "تعذّر تحميل الأسعار - إعادة المحاولة", "refresh": "تحديث الآن",
           "open": "فتح Gold Hunt", "top": "دائماً في المقدمة", "lang": "English", "close": "إغلاق الويدجت",
           "total": "إجمالي الربح"},
}


def single_instance():
    """Only one widget at a time (a second launch just exits)."""
    s = socket.socket()
    try:
        s.bind(("127.0.0.1", 8766))
        return s
    except OSError:
        sys.exit(0)


def load_state():
    try:
        return json.loads(STATE.read_text())
    except Exception:
        return {}


class Widget(tk.Tk):
    def __init__(self):
        super().__init__()
        self.state_ = {"x": None, "y": None, "top": False, "lang": "ar", **load_state()}
        self.overrideredirect(True)          # no title bar
        self.attributes("-toolwindow", True)  # no taskbar button
        self.attributes("-alpha", 0.95)
        self.attributes("-topmost", self.state_["top"])
        self.configure(bg=COLORS["line"])
        self.body = tk.Frame(self, bg=COLORS["bg"], padx=14, pady=10)
        self.body.pack(padx=1, pady=1)
        self.results = None
        self.error = False

        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        x = self.state_["x"] if self.state_["x"] is not None else sw - 330
        y = self.state_["y"] if self.state_["y"] is not None else 80
        self.geometry(f"+{min(max(0, x), sw - 100)}+{min(max(0, y), sh - 100)}")

        for w in (self, self.body):
            w.bind("<ButtonPress-1>", self.start_drag)
            w.bind("<B1-Motion>", self.drag)
            w.bind("<ButtonRelease-1>", self.end_drag)
            w.bind("<Button-3>", self.menu)
        self.draw()
        self.refresh()
        self.poll()

    # ---------------------------------------------------------------- data
    def refresh(self):
        def work():
            try:
                assets, _, _ = gold_hunt.load_settings()
                out = []
                for a in assets:
                    try:
                        out.append(gold_hunt.analyse(a, gold_hunt.fetch(a)))
                    except Exception:
                        pass
                self.results, self.error = out, not out
            except Exception:
                self.error = True
            self.ready = True  # Tk isn't thread-safe: the main thread redraws (see poll)
        self.ready = False
        threading.Thread(target=work, daemon=True).start()
        self.timer = self.after(REFRESH_MS, self.refresh)

    def poll(self):
        if self.ready:
            self.ready = False
            self.draw()
        self.after(300, self.poll)

    # ---------------------------------------------------------------- drawing
    def T(self, k, **kw):
        return TEXT[self.state_["lang"]][k].format(**kw)

    def label(self, parent, text, fg="ink", size=10, bold=False, **grid):
        lbl = tk.Label(parent, text=text, bg=parent["bg"], fg=COLORS[fg],
                       font=("Segoe UI", size, "bold" if bold else "normal"))
        lbl.grid(**grid)
        for ev, fn in (("<ButtonPress-1>", self.start_drag), ("<B1-Motion>", self.drag),
                       ("<ButtonRelease-1>", self.end_drag), ("<Button-3>", self.menu)):
            lbl.bind(ev, fn)
        return lbl

    def draw(self):
        for w in self.body.winfo_children():
            w.destroy()
        rtl = self.state_["lang"] == "ar"
        side, other = ("e", "w") if rtl else ("w", "e")
        head = tk.Frame(self.body, bg=COLORS["bg"])
        head.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        self.label(head, "Gold Hunt", "gold", 11, True, row=0, column=0, sticky="w")
        if not self.results:
            self.label(self.body, self.T("error" if self.error else "loading"), "mute", 9,
                       row=1, column=0, sticky=side)
            return

        rows = tk.Frame(self.body, bg=COLORS["bg"])
        rows.grid(row=1, column=0, sticky="ew")
        cols = [0, 1, 2, 3] if not rtl else [3, 2, 1, 0]  # name, price, change, P/L
        totals = {}
        for i, a in enumerate(self.results):
            name = self.T("gold") if a["key"] == "GOLD" else a["name"]
            fresh = a.get("price_time") and (
                dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(a["price_time"])).total_seconds() < 1200
            up = a["change_pct"] >= 0
            self.label(rows, name + ("" if fresh else f" ({self.T('closed')})"), "ink" if fresh else "mute", 10,
                       row=i, column=cols[0], sticky=side, padx=(0, 10))
            self.label(rows, f"{a['price']:,.2f}", "ink", 11, True, row=i, column=cols[1], sticky=other, padx=4)
            self.label(rows, f"{'▲' if up else '▼'} {a['change_pct']:+.1f}%", "up" if up else "down", 9,
                       row=i, column=cols[2], sticky=other, padx=4)
            if a.get("pl") is not None:
                self.label(rows, f"{a['pl']:+,.0f}", "up" if a["pl"] >= 0 else "down", 10,
                           row=i, column=cols[3], sticky=other, padx=(6, 0))
                totals[a["currency"]] = totals.get(a["currency"], 0) + a["pl"]

        foot = tk.Frame(self.body, bg=COLORS["bg"])
        foot.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        total = "   ".join(f"{v:+,.0f} {c}" for c, v in totals.items())
        self.label(foot, f"{self.T('total')}: {total}", "mute", 9, row=0, column=0, sticky=side)
        stamp = dt.datetime.now(gold_hunt.RIYADH).strftime("%H:%M")
        self.label(foot, self.T("updated", t=stamp), "mute", 8, row=1, column=0, sticky=side)

    # ---------------------------------------------------------------- moving + menu
    def start_drag(self, e):
        self._dx, self._dy = e.x_root - self.winfo_x(), e.y_root - self.winfo_y()

    def drag(self, e):
        self.geometry(f"+{e.x_root - self._dx}+{e.y_root - self._dy}")

    def end_drag(self, _e):
        self.state_["x"], self.state_["y"] = self.winfo_x(), self.winfo_y()
        self.save()

    def save(self):
        try:
            STATE.write_text(json.dumps(self.state_))
        except Exception:
            pass

    def menu(self, e):
        m = tk.Menu(self, tearoff=0)
        m.add_command(label=self.T("refresh"), command=self.refresh_now)
        m.add_command(label=self.T("open"), command=self.open_app)
        top = tk.BooleanVar(value=self.state_["top"])
        m.add_checkbutton(label=self.T("top"), variable=top, command=lambda: self.set_top(top.get()))
        m.add_command(label=self.T("lang"), command=self.toggle_lang)
        m.add_separator()
        m.add_command(label=self.T("close"), command=self.destroy)
        m.tk_popup(e.x_root, e.y_root)

    def refresh_now(self):
        self.after_cancel(self.timer)  # restart the 5-minute cycle from now
        self.results = None
        self.draw()
        self.refresh()

    def set_top(self, on):
        self.state_["top"] = on
        self.attributes("-topmost", on)
        self.save()

    def toggle_lang(self):
        self.state_["lang"] = "en" if self.state_["lang"] == "ar" else "ar"
        self.save()
        self.draw()

    def open_app(self):
        subprocess.Popen([sys.executable, str(HERE / "settings_page.py")], cwd=HERE,
                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))


if __name__ == "__main__":
    lock = single_instance()
    Widget().mainloop()
