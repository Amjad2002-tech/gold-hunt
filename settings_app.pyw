"""Gold Hunt settings window - edit grams, prices and stocks, then save to PC + GitHub."""
import configparser
import subprocess
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

HERE = Path(__file__).resolve().parent
SETTINGS = HERE / "settings.ini"
GH = r"C:\Program Files\GitHub CLI\gh.exe"
REPO = "Amjad2002-tech/gold-hunt"
STOCK_FIELDS = [("ticker", "Ticker", 10), ("name", "Name", 14), ("shares", "Shares", 8),
                ("buy_price", "Buy price", 9), ("currency", "Currency", 7),
                ("alert_above", "Alert above", 10), ("alert_below", "Alert below", 10)]


def load():
    cfg = configparser.ConfigParser(inline_comment_prefixes=("#",))
    cfg.optionxform = str
    cfg.read(SETTINGS, encoding="utf-8")
    return cfg


def number(value, label, required=False):
    value = value.strip()
    if not value:
        if required:
            raise ValueError(f"{label} is required")
        return ""
    try:
        float(value)
    except ValueError:
        raise ValueError(f"{label} must be a number (got '{value}')") from None
    return value


def render(gold, stocks, daily, every, whatsapp):
    """Build settings.ini text. WhatsApp lines are only kept on the PC, never uploaded."""
    parts = ["# GOLD HUNT settings - edit with 'Gold Hunt Settings' (settings_app.pyw)\n",
             "[gold]",
             f"grams = {gold['grams']}", f"buy_price = {gold['buy_price']}",
             f"alert_above = {gold['alert_above']}", f"alert_below = {gold['alert_below']}", ""]
    for s in stocks:
        parts += [f"[stock:{s['ticker']}]"] + [f"{k} = {s[k]}" for k, _, _ in STOCK_FIELDS[1:]] + [""]
    parts += ["[alerts]", f"daily_move_percent = {daily}", f"check_every_minutes = {every}", ""]
    public = "\n".join(parts)
    private = "[whatsapp]\n# 9665XXXXXXXX = 123456\n" + "".join(f"{p} = {k}\n" for p, k in whatsapp)
    return public, public + "\n" + private


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Gold Hunt Settings")
        self.resizable(False, False)
        cfg = load()
        self.whatsapp = list(cfg.items("whatsapp")) if cfg.has_section("whatsapp") else []
        pad = {"padx": 8, "pady": 4}

        g = ttk.LabelFrame(self, text="Gold (24K)")
        g.pack(fill="x", **pad)
        self.gold = {}
        for i, (key, label) in enumerate([("grams", "Grams I hold"), ("buy_price", "Buy price (SAR/gram)"),
                                          ("alert_above", "Alert above (blank = auto)"),
                                          ("alert_below", "Alert below (blank = auto)")]):
            ttk.Label(g, text=label).grid(row=i // 2, column=(i % 2) * 2, sticky="w", **pad)
            e = ttk.Entry(g, width=12)
            e.insert(0, cfg.get("gold", key, fallback=""))
            e.grid(row=i // 2, column=(i % 2) * 2 + 1, **pad)
            self.gold[key] = e

        self.sframe = ttk.LabelFrame(self, text="Stocks  (Saudi tickers end with .SR, e.g. 2222.SR)")
        self.sframe.pack(fill="x", **pad)
        for c, (_, label, _) in enumerate(STOCK_FIELDS):
            ttk.Label(self.sframe, text=label).grid(row=0, column=c, padx=4)
        self.rows = []
        for sec in cfg.sections():
            if sec.startswith("stock:"):
                vals = {"ticker": sec.split(":", 1)[1]}
                vals.update({k: cfg.get(sec, k, fallback="") for k, _, _ in STOCK_FIELDS[1:]})
                self.add_row(vals)
        ttk.Button(self, text="+ Add stock", command=self.add_row).pack(anchor="w", **pad)

        a = ttk.LabelFrame(self, text="Alerts")
        a.pack(fill="x", **pad)
        ttk.Label(a, text="Alert if price moves more than (% per day)").grid(row=0, column=0, sticky="w", **pad)
        self.daily = ttk.Entry(a, width=6)
        self.daily.insert(0, cfg.get("alerts", "daily_move_percent", fallback="2"))
        self.daily.grid(row=0, column=1, **pad)
        self.every = cfg.get("alerts", "check_every_minutes", fallback="30")

        b = ttk.Frame(self)
        b.pack(fill="x", **pad)
        ttk.Button(b, text="Save", command=self.save).pack(side="right", padx=4)
        self.status = ttk.Label(b, text="")
        self.status.pack(side="left")

    def add_row(self, vals=None):
        vals = vals or {"currency": "SAR"}
        r = len(self.rows) + 1
        entries = {}
        for c, (key, _, w) in enumerate(STOCK_FIELDS):
            e = ttk.Entry(self.sframe, width=w)
            e.insert(0, vals.get(key, ""))
            e.grid(row=r, column=c, padx=4, pady=2)
            entries[key] = e
        btn = ttk.Button(self.sframe, text="Remove", width=8)
        btn.grid(row=r, column=len(STOCK_FIELDS), padx=4)
        row = (entries, btn)
        btn.configure(command=lambda: self.remove_row(row))
        self.rows.append(row)

    def remove_row(self, row):
        for w in [*row[0].values(), row[1]]:
            w.destroy()
        self.rows.remove(row)

    def collect(self):
        gold = {"grams": number(self.gold["grams"].get(), "Grams", True),
                "buy_price": number(self.gold["buy_price"].get(), "Gold buy price", True),
                "alert_above": number(self.gold["alert_above"].get(), "Gold alert above"),
                "alert_below": number(self.gold["alert_below"].get(), "Gold alert below")}
        stocks = []
        for entries, _ in self.rows:
            s = {k: e.get().strip() for k, e in entries.items()}
            if not s["ticker"]:
                continue  # empty row
            s["ticker"] = s["ticker"].upper()
            if any(o["ticker"] == s["ticker"] for o in stocks):
                raise ValueError(f"{s['ticker']} is listed twice - remove one row")
            name = s["name"] or s["ticker"]
            s["name"] = name
            s["currency"] = (s["currency"] or "SAR").upper()
            s["shares"] = number(s["shares"], f"{name} shares", True)
            s["buy_price"] = number(s["buy_price"], f"{name} buy price", True)
            s["alert_above"] = number(s["alert_above"], f"{name} alert above")
            s["alert_below"] = number(s["alert_below"], f"{name} alert below")
            stocks.append(s)
        daily = number(self.daily.get(), "Daily move %", True)
        return gold, stocks, daily

    def save(self):
        try:
            gold, stocks, daily = self.collect()
        except ValueError as e:
            messagebox.showerror("Please fix", str(e))
            return
        public, full = render(gold, stocks, daily, self.every, self.whatsapp)
        SETTINGS.write_text(full, encoding="utf-8")
        self.status.configure(text="Saved on PC. Uploading to GitHub...")
        self.update()
        try:
            r = subprocess.run([GH, "secret", "set", "GOLD_HUNT_SETTINGS", "-R", REPO],
                               input=public.encode("utf-8"), capture_output=True, timeout=60,
                               creationflags=subprocess.CREATE_NO_WINDOW)
            ok = r.returncode == 0
            err = r.stderr.decode(errors="replace")
        except Exception as e:  # gh missing, timeout, ...
            ok, err = False, str(e)
        if ok:
            self.status.configure(text="✓ Saved on PC and GitHub")
            messagebox.showinfo("Saved", "Saved! GitHub will use the new numbers from the next check.")
        else:
            self.status.configure(text="Saved on PC only")
            messagebox.showwarning("GitHub upload failed",
                                   "Saved on this PC, but GitHub was not updated.\n\n" + err.strip())


if __name__ == "__main__":
    App().mainloop()
