"""Tharwa settings page - a small local web page to edit settings.ini and upload it to GitHub.

Run:  python settings_page.py   (or double-click "Gold Hunt Settings.bat")
Only reachable from this PC (127.0.0.1).
"""
import configparser
import json
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import shutil

import gold_hunt
import app_paths  # points gold_hunt at this user's own data folder

HERE = gold_hunt.HERE
SETTINGS = gold_hunt.SETTINGS
PAGE = HERE / "settings_page.html"
# GitHub upload is optional: only when gh is installed AND settings.ini has [github] repo = owner/name
GH = shutil.which("gh") or r"C:\Program Files\GitHub CLI\gh.exe"
PORT = 8765
IDLE_SECONDS = 90  # the open page pings every 20s; stop when nobody has for this long
last_ping = time.time()
STOCK_KEYS = ["name", "shares", "buy_price", "currency", "alert_above", "alert_below"]


# ---------------------------------------------------------------- settings file
def read_settings():
    cfg = configparser.ConfigParser(inline_comment_prefixes=("#",))
    cfg.optionxform = str
    cfg.read(SETTINGS, encoding="utf-8")
    gold = {k: cfg.get("gold", k, fallback="") for k in ["grams", "buy_price", "alert_above", "alert_below", "move_alert_sar"]}
    stocks = [{"ticker": sec.split(":", 1)[1], **{k: cfg.get(sec, k, fallback="") for k in STOCK_KEYS}}
              for sec in cfg.sections() if sec.startswith("stock:")]
    alerts = {"daily_move_percent": cfg.get("alerts", "daily_move_percent", fallback="2"),
              "check_every_minutes": cfg.get("alerts", "check_every_minutes", fallback="30"),
              "language": cfg.get("alerts", "language", fallback="en")}
    whatsapp = list(cfg.items("whatsapp")) if cfg.has_section("whatsapp") else []
    return {"gold": gold, "stocks": stocks, "alerts": alerts}, whatsapp


def github_repo():
    """The repo to upload settings to, or '' (default for new users: saved on this PC only)."""
    cfg = configparser.ConfigParser(inline_comment_prefixes=("#",))
    cfg.read(SETTINGS, encoding="utf-8")
    repo = cfg.get("github", "repo", fallback="").strip()
    return repo if repo.count("/") == 1 and " " not in repo else ""


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
            "alert_below": number(g.get("alert_below", ""), "Gold alert below"),
            "move_alert_sar": number(g.get("move_alert_sar", "10"), "Gold move alert (SAR)") or "10"}
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
              "check_every_minutes": number(a.get("check_every_minutes", "30"), "Check every") or "30",
              "language": "ar" if a.get("language") == "ar" else "en"}
    return gold, stocks, alerts


def render(gold, stocks, alerts, whatsapp, repo=""):
    """Return (text for GitHub, full text for the PC). WhatsApp and [github] stay on the PC only."""
    lines = ["# GOLD HUNT settings - edit with the settings page (Gold Hunt Settings.bat)", "", "[gold]"]
    lines += [f"{k} = {v}" for k, v in gold.items()] + [""]
    for s in stocks:
        lines += [f"[stock:{s['ticker']}]"] + [f"{k} = {s[k]}" for k in STOCK_KEYS] + [""]
    lines += ["[alerts]"] + [f"{k} = {v}" for k, v in alerts.items()] + [""]
    public = "\n".join(lines)
    private = "\n[whatsapp]\n# 9665XXXXXXXX = 123456\n" + "".join(f"{p} = {k}\n" for p, k in whatsapp)
    private += ("\n[github]\n# Optional: owner/name of your own GitHub repo for cloud alerts. Blank = this PC only.\n"
                f"repo = {repo}\n")
    return public, public + private


def upload(public, repo):
    if not repo:
        return None, "No GitHub repo set - saved on this PC only"
    if not Path(GH).exists():
        return None, "GitHub CLI (gh) not installed - saved on this PC only"
    try:
        r = subprocess.run([GH, "secret", "set", "GOLD_HUNT_SETTINGS", "-R", repo],
                           input=public.encode("utf-8"), capture_output=True, timeout=60,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return r.returncode == 0, r.stderr.decode(errors="replace").strip()
    except Exception as e:  # gh missing, timeout, ...
        return False, str(e)


def save(data):
    gold, stocks, alerts = clean(data)
    _, whatsapp = read_settings()
    repo = github_repo()
    public, full = render(gold, stocks, alerts, whatsapp, repo)
    SETTINGS.write_text(full, encoding="utf-8")
    ok, err = upload(public, repo)
    # github: True = uploaded, False = upload failed, None = not configured (saved on this PC only)
    return {"ok": True, "github": ok, "local_only": ok is None, "error": err}


# ---------------------------------------------------------------- live quotes for suggestions
def quote(ticker, currency):
    if ticker.upper() == "GOLD":
        asset = {"key": "GOLD", "ticker": "GC=F", "name": "Gold 24K", "unit": "SAR/gram", "currency": "SAR"}
    else:
        asset = {"key": ticker, "ticker": ticker, "name": ticker, "unit": currency + "/share", "currency": currency}
    asset.update(qty=0, qty_label="", buy=None, above=None, below=None)
    a = gold_hunt.analyse(asset, gold_hunt.fetch(asset))
    keep = ["price", "prev", "change_pct", "hi", "hi_date", "lo", "lo_date", "pct_rank", "rsi",
            "sma50", "sma200", "band_upper", "band_lower", "verdict", "tone", "trend",
            "verdict_code", "trend_code", "price_time", "pulled_at"]
    return {k: a[k] for k in keep}


def search(query):
    """Find stocks/ETFs by company name or ticker (Yahoo Finance search)."""
    out = []
    for q in gold_hunt.yf.Search(query, max_results=8).quotes:
        sym = q.get("symbol", "")
        if q.get("quoteType") not in ("EQUITY", "ETF") or not sym:
            continue
        if "." in sym and not sym.endswith(".SR"):
            continue  # only Saudi (.SR) and US listings - the app works in SAR and USD
        out.append({"ticker": sym, "name": q.get("shortname") or q.get("longname") or sym,
                    "exchange": q.get("exchDisp") or q.get("exchange", ""),
                    "currency": "SAR" if sym.endswith(".SR") else "USD"})
    return out


# ---------------------------------------------------------------- live prices for the dashboard
LIVE_TTL = 10          # seconds a stock quote is reused (many polls -> one Yahoo call)
DEWAN_EVERY = 5        # seconds between reads of the open Dewan page
_live_cache, _live_lock = {}, threading.Lock()
_dewan = {"price": None, "t": 0.0, "started": False, "error": None}
_gold_ref = {"ratio": None}  # Dewan price / world price, to scale the futures price if Dewan stops


def _dewan_loop():
    """Keep ONE headless browser page on dewanaldahab.com open and read its live 24K price
    every few seconds (launching a browser per poll would be far too slow)."""
    while True:
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page()
                opened = time.time()
                page.goto(gold_hunt.DEWAN_URL, wait_until="domcontentloaded", timeout=60000)
                while True:
                    if time.time() - last_ping > IDLE_SECONDS:  # app closed: stop using the network
                        browser.close()
                        _dewan["started"] = False
                        return
                    if time.time() - opened > 600:  # reload every 10 min in case the feed stalls
                        page.reload(wait_until="domcontentloaded", timeout=60000)
                        opened = time.time()
                    v = page.get_attribute("#caret24_Price", "data-price", timeout=15000)
                    try:
                        v = float(v)
                    except (TypeError, ValueError):
                        v = None
                    if v and 100 < v < 2000:
                        _dewan.update(price=v, t=time.time(), error=None)
                    time.sleep(DEWAN_EVERY)
        except Exception as e:
            _dewan["error"] = type(e).__name__
            time.sleep(30)  # browser missing / site down: try again later, futures fallback meanwhile


def _minute_quote(ticker):
    """Last 1-minute bar from Yahoo: (price, time ISO) or (None, None)."""
    h = gold_hunt.yf.Ticker(ticker).history(period="5d", interval="1m")
    h = h.dropna(subset=["Close"])
    if h.empty:
        return None, None
    return float(h["Close"].iloc[-1]), h.index[-1].isoformat()


def live_quote(key):
    now = time.time()
    with _live_lock:
        hit = _live_cache.get(key)
    if hit and now - hit[0] < LIVE_TTL:
        return hit[1]
    if key == "GOLD":
        if not _dewan["started"]:
            _dewan["started"] = True
            threading.Thread(target=_dewan_loop, daemon=True).start()
        world, wtime = _minute_quote("GC=F")
        world = world * gold_hunt.USD_SAR / gold_hunt.GRAMS_PER_OUNCE if world else None
        fresh = _dewan["price"] and now - _dewan["t"] < 60
        if fresh and world:
            _gold_ref["ratio"] = _dewan["price"] / world
        elif world and not _gold_ref["ratio"] and gold_hunt._dewan_cache.get("price"):
            _gold_ref["ratio"] = gold_hunt._dewan_cache["price"] / world  # from the dashboard build
        if fresh:
            q = {"price": _dewan["price"], "time": dt_iso(_dewan["t"]), "source": "dewanaldahab.com", "delay_min": 0}
        elif world:
            q = {"price": world * (_gold_ref["ratio"] or 1), "time": wtime,
                 "source": "Yahoo GC=F" + (" ×Dewan" if _gold_ref["ratio"] else ""), "delay_min": 10}
        else:
            q = None
    else:
        price, ptime = _minute_quote(key)
        # Yahoo's Saudi (Tadawul) quotes are delayed ~15 min; US quotes are near real time
        q = {"price": price, "time": ptime, "source": "Yahoo Finance",
             "delay_min": 15 if key.endswith(".SR") else 0} if price else None
    if q:
        q["pulled"] = dt_iso(now)
        with _live_lock:
            _live_cache[key] = (now, q)
    return q


def dt_iso(ts):
    import datetime as dt
    return dt.datetime.fromtimestamp(ts, dt.timezone.utc).isoformat(timespec="seconds")


def live(keys):
    from concurrent.futures import ThreadPoolExecutor
    keys = [k for k in dict.fromkeys(keys) if k and len(k) <= 20 and all(c.isalnum() or c in ".-=^" for c in k)][:20]

    def one(k):
        try:
            return k, live_quote(k)
        except Exception:
            return k, None
    with ThreadPoolExecutor(max_workers=6) as ex:
        return {"quotes": dict(ex.map(one, keys)), "server_time": dt_iso(time.time())}


# ---------------------------------------------------------------- web server
def no_nan(v):
    """JSON has no NaN (e.g. a 200-day average for a stock listed months ago): send null instead."""
    if isinstance(v, float) and v != v:
        return None
    if isinstance(v, dict):
        return {k: no_nan(x) for k, x in v.items()}
    if isinstance(v, list):
        return [no_nan(x) for x in v]
    return v


class Handler(BaseHTTPRequestHandler):
    def send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else json.dumps(no_nan(body)).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        url = urlparse(self.path)
        if url.path == "/":
            self.send(200, PAGE.read_bytes(), "text/html")
        elif url.path == "/i18n.js":
            self.send(200, (HERE / "i18n.js").read_bytes(), "text/javascript")
        elif url.path == "/api/ping":
            global last_ping
            last_ping = time.time()
            self.send(200, {"ok": True})
        elif url.path == "/dashboard":
            self.send(200, build_dashboard(), "text/html")
        elif url.path == "/api/live":
            last_ping = time.time()  # an open dashboard counts as the app being used
            keys = parse_qs(url.query).get("tickers", [""])[0].upper().split(",")
            self.send(200, live([k.strip() for k in keys]))
        elif url.path == "/api/settings":
            self.send(200, read_settings()[0])
        elif url.path == "/api/search":
            q = parse_qs(url.query).get("q", [""])[0].strip()
            try:
                self.send(200, search(q) if len(q) >= 2 else [])
            except Exception:
                self.send(200, [])
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


def build_dashboard():
    """Fresh analysis of the PC settings -> dashboard HTML (no alerts are sent)."""
    assets, _, _ = gold_hunt.load_settings()
    results = []
    for a in assets:
        try:
            results.append(gold_hunt.analyse(a, gold_hunt.fetch(a)))
        except Exception:
            pass  # a bad ticker just doesn't show
    gold_hunt.build_dashboard(results)
    return gold_hunt.DASHBOARD.read_bytes()


def open_app(url):
    """Open as its own app window (Edge/Chrome app mode), else a normal browser tab."""
    for exe in [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
                r"C:\Program Files\Google\Chrome\Application\chrome.exe"]:
        if Path(exe).exists():
            subprocess.Popen([exe, f"--app={url}", "--window-size=1100,900"])
            return
    webbrowser.open(url)


def watchdog(server):
    """Stop the background program a while after the app window is closed."""
    while True:
        time.sleep(15)
        if time.time() - last_ping > IDLE_SECONDS:
            server.shutdown()
            return


class Server(ThreadingHTTPServer):
    allow_reuse_address = False  # on Windows reuse lets a 2nd copy share the port silently


def main():
    global last_ping
    url = f"http://127.0.0.1:{PORT}/"
    try:
        server = Server(("127.0.0.1", PORT), Handler)
    except OSError:  # already running - just open another window
        open_app(url)
        return
    last_ping = time.time()
    if "--no-browser" not in sys.argv:
        threading.Timer(0.3, open_app, [url]).start()
    threading.Thread(target=watchdog, args=(server,), daemon=True).start()
    server.serve_forever()


if __name__ == "__main__":
    main()
