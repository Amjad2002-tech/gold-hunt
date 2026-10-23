"""Gold Hunt settings page - a small local web page to edit settings.ini and upload it to GitHub.

Run:  python settings_page.py   (or double-click "Gold Hunt Settings.bat")
Only reachable from this PC (127.0.0.1).
"""
import configparser
import json
import subprocess
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import gold_hunt

HERE = gold_hunt.HERE
SETTINGS = gold_hunt.SETTINGS
PAGE = HERE / "settings_page.html"
GH = r"C:\Program Files\GitHub CLI\gh.exe"
REPO = "Amjad2002-tech/gold-hunt"
PORT = 8765
STOCK_KEYS = ["name", "shares", "buy_price", "currency", "alert_above", "alert_below"]


# ---------------------------------------------------------------- settings file
def read_settings():
    cfg = configparser.ConfigParser(inline_comment_prefixes=("#",))
    cfg.optionxform = str
    cfg.read(SETTINGS, encoding="utf-8")
    gold = {k: cfg.get("gold", k, fallback="") for k in ["grams", "buy_price", "alert_above", "alert_below"]}
    stocks = [{"ticker": sec.split(":", 1)[1], **{k: cfg.get(sec, k, fallback="") for k in STOCK_KEYS}}
              for sec in cfg.sections() if sec.startswith("stock:")]
    alerts = {"daily_move_percent": cfg.get("alerts", "daily_move_percent", fallback="2"),
              "check_every_minutes": cfg.get("alerts", "check_every_minutes", fallback="30")}
    whatsapp = list(cfg.items("whatsapp")) if cfg.has_section("whatsapp") else []
    return {"gold": gold, "stocks": stocks, "alerts": alerts}, whatsapp


def number(value, label, required=False):
    value = str(value).strip()
    if not value:
        if required:
            raise ValueError(f"{label} is required")
        return ""
    try:
        if float(value) < 0:
            raise ValueError
    except ValueError:
        raise ValueError(f"{label} must be a positive number (got '{value}')") from None
    return value


def clean(data):
    """Validate what the page sent; raise ValueError with a friendly message."""
    g = data.get("gold", {})
    gold = {"grams": number(g.get("grams", ""), "Gold grams", True),
            "buy_price": number(g.get("buy_price", ""), "Gold buy price", True),
            "alert_above": number(g.get("alert_above", ""), "Gold alert above"),
            "alert_below": number(g.get("alert_below", ""), "Gold alert below")}
    stocks, seen = [], set()
    for s in data.get("stocks", []):
        ticker = str(s.get("ticker", "")).strip().upper()
        if not ticker:
            continue
        if ticker in seen:
            raise ValueError(f"{ticker} is listed twice - remove one")
        if any(c in ticker for c in "[]#= "):
            raise ValueError(f"'{ticker}' is not a valid ticker")
        seen.add(ticker)
        name = str(s.get("name", "")).strip().replace("#", "") or ticker
        stocks.append({"ticker": ticker, "name": name,
                       "shares": number(s.get("shares", ""), f"{name} shares", True),
                       "buy_price": number(s.get("buy_price", ""), f"{name} buy price", True),
                       "currency": (str(s.get("currency", "")).strip().upper() or "SAR"),
                       "alert_above": number(s.get("alert_above", ""), f"{name} alert above"),
                       "alert_below": number(s.get("alert_below", ""), f"{name} alert below")})
    a = data.get("alerts", {})
    alerts = {"daily_move_percent": number(a.get("daily_move_percent", ""), "Daily move %", True),
              "check_every_minutes": number(a.get("check_every_minutes", "30"), "Check every") or "30"}
    return gold, stocks, alerts


def render(gold, stocks, alerts, whatsapp):
    """Return (public text for GitHub, full text for the PC). WhatsApp stays on the PC only."""
    lines = ["# GOLD HUNT settings - edit with the settings page (Gold Hunt Settings.bat)", "", "[gold]"]
    lines += [f"{k} = {v}" for k, v in gold.items()] + [""]
    for s in stocks:
        lines += [f"[stock:{s['ticker']}]"] + [f"{k} = {s[k]}" for k in STOCK_KEYS] + [""]
    lines += ["[alerts]"] + [f"{k} = {v}" for k, v in alerts.items()] + [""]
    public = "\n".join(lines)
    private = "\n[whatsapp]\n# 9665XXXXXXXX = 123456\n" + "".join(f"{p} = {k}\n" for p, k in whatsapp)
    return public, public + private


def upload(public):
    try:
        r = subprocess.run([GH, "secret", "set", "GOLD_HUNT_SETTINGS", "-R", REPO],
                           input=public.encode("utf-8"), capture_output=True, timeout=60,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return r.returncode == 0, r.stderr.decode(errors="replace").strip()
    except Exception as e:  # gh missing, timeout, ...
        return False, str(e)


def save(data):
    gold, stocks, alerts = clean(data)
    _, whatsapp = read_settings()
    public, full = render(gold, stocks, alerts, whatsapp)
    SETTINGS.write_text(full, encoding="utf-8")
    ok, err = upload(public)
    return {"ok": True, "github": ok, "error": err}


# ---------------------------------------------------------------- live quotes for suggestions
def quote(ticker, currency):
    if ticker.upper() == "GOLD":
        asset = {"key": "GOLD", "ticker": "GC=F", "name": "Gold 24K", "unit": "SAR/gram", "currency": "SAR"}
    else:
        asset = {"key": ticker, "ticker": ticker, "name": ticker, "unit": currency + "/share", "currency": currency}
    asset.update(qty=0, qty_label="", buy=None, above=None, below=None)
    a = gold_hunt.analyse(asset, gold_hunt.fetch(asset))
    keep = ["price", "change_pct", "hi", "hi_date", "lo", "lo_date", "pct_rank", "rsi",
            "sma50", "sma200", "band_upper", "band_lower", "verdict", "tone", "trend"]
    return {k: a[k] for k in keep}


# ---------------------------------------------------------------- web server
class Handler(BaseHTTPRequestHandler):
    def send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        url = urlparse(self.path)
        if url.path == "/":
            self.send(200, PAGE.read_bytes(), "text/html")
        elif url.path == "/api/settings":
            self.send(200, read_settings()[0])
        elif url.path == "/api/quote":
            q = parse_qs(url.query)
            try:
                self.send(200, quote(q.get("ticker", [""])[0].strip().upper(),
                                     q.get("currency", ["SAR"])[0].strip().upper()))
            except Exception:
                self.send(404, {"error": "Could not find prices for this ticker"})
        else:
            self.send(404, {"error": "not found"})

    def do_POST(self):
        # Only accept saves from this page itself (blocks other websites posting here)
        if self.path != "/api/save" or self.headers.get("Origin") not in (None, f"http://127.0.0.1:{PORT}"):
            return self.send(403, {"error": "forbidden"})
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
            self.send(200, save(body))
        except ValueError as e:
            self.send(400, {"error": str(e)})

    def log_message(self, *args):
        pass  # keep the console quiet


def main():
    try:
        server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    except OSError:  # already running - just open it
        webbrowser.open(f"http://127.0.0.1:{PORT}/")
        return
    url = f"http://127.0.0.1:{PORT}/"
    print(f"Gold Hunt settings page: {url}\nClose this window to stop it.")
    if "--no-browser" not in sys.argv:
        threading.Timer(0.5, webbrowser.open, [url]).start()
    server.serve_forever()


if __name__ == "__main__":
    main()
