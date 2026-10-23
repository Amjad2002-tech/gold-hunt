"""Gold Hunt - price tracker, 2-year analysis, dashboard and WhatsApp alerts.

Usage:
    python gold_hunt.py              # analyse, rebuild dashboard, send alerts if triggered
    python gold_hunt.py --no-send    # same, but only print alerts (no WhatsApp)
    python gold_hunt.py --test       # send a test WhatsApp message to everyone
"""
import configparser
import datetime as dt
import json
import os
import sys
import urllib.parse
from pathlib import Path

import pandas as pd
import requests
import yfinance as yf

HERE = Path(__file__).resolve().parent
SETTINGS = HERE / "settings.ini"
STATE = HERE / "alerts_state.json"
DASHBOARD = HERE / "dashboard.html"

USD_SAR = 3.75            # the riyal is pegged to the dollar
GRAMS_PER_OUNCE = 31.1035


# ---------------------------------------------------------------- settings
def load_settings():
    cfg = configparser.ConfigParser(inline_comment_prefixes=("#",))
    cfg.optionxform = str  # keep phone numbers / tickers as written
    # On GitHub the whole settings file comes from the GOLD_HUNT_SETTINGS secret
    if os.environ.get("GOLD_HUNT_SETTINGS"):
        cfg.read_string(os.environ["GOLD_HUNT_SETTINGS"].lstrip("﻿?"))
    else:
        cfg.read(SETTINGS, encoding="utf-8")

    def num(section, key):
        v = cfg.get(section, key, fallback="").strip()
        return float(v) if v else None

    assets = [{
        "key": "GOLD", "ticker": "GC=F", "name": "Gold 24K", "unit": "SAR/gram",
        "currency": "SAR", "qty": num("gold", "grams") or 0, "qty_label": "grams",
        "buy": num("gold", "buy_price"),
        "above": num("gold", "alert_above"), "below": num("gold", "alert_below"),
    }]
    for sec in cfg.sections():
        if sec.startswith("stock:"):
            t = sec.split(":", 1)[1].strip()
            cur = cfg.get(sec, "currency", fallback="USD").strip().upper()
            assets.append({
                "key": t, "ticker": t, "name": cfg.get(sec, "name", fallback=t),
                "unit": cur + "/share", "currency": cur,
                "qty": num(sec, "shares") or 0, "qty_label": "shares",
                "buy": num(sec, "buy_price"),
                "above": num(sec, "alert_above"), "below": num(sec, "alert_below"),
            })
    alerts = {
        "daily_move": num("alerts", "daily_move_percent") or 2.0,
    }
    phones = dict(cfg.items("whatsapp")) if cfg.has_section("whatsapp") else {}
    # On GitHub the numbers come from the WHATSAPP_RECIPIENTS secret: "phone=key" per line
    for line in os.environ.get("WHATSAPP_RECIPIENTS", "").replace(",", "\n").splitlines():
        if "=" in line:
            phone, key = line.split("=", 1)
            phones[phone.strip()] = key.strip()
    return assets, alerts, phones


# ---------------------------------------------------------------- data
def fetch(asset):
    df = yf.Ticker(asset["ticker"]).history(period="2y", interval="1d", auto_adjust=False)
    if df.empty:
        raise RuntimeError(f"No data for {asset['ticker']}")
    s = df["Close"].dropna()
    s.index = s.index.tz_localize(None).normalize()
    if asset["key"] == "GOLD":
        s = s * USD_SAR / GRAMS_PER_OUNCE  # USD/oz -> SAR/gram
    # latest intraday price if available
    try:
        live = yf.Ticker(asset["ticker"]).fast_info["last_price"]
        if live and live == live:
            if asset["key"] == "GOLD":
                live = live * USD_SAR / GRAMS_PER_OUNCE
            s.iloc[-1] = live
    except Exception:
        pass
    return s


def rsi(s, n=14):
    d = s.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn)


def analyse(asset, s):
    price = float(s.iloc[-1])
    prev = float(s.iloc[-2])
    sma50 = s.rolling(50).mean()
    sma200 = s.rolling(200).mean()
    std50 = s.rolling(50).std()
    r = rsi(s)
    hi, lo = float(s.max()), float(s.min())
    pct_rank = float((s < price).mean() * 100)  # % of days in 2y that were cheaper

    # Auto alert levels = Bollinger-style bands (unusual moves), unless user set them
    upper = float(sma50.iloc[-1] + 2 * std50.iloc[-1])
    lower = float(sma50.iloc[-1] - 2 * std50.iloc[-1])
    above = asset["above"] or upper
    below = asset["below"] or lower

    # Sell-signal score (historical/technical, not advice)
    reasons = []
    if pct_rank >= 85:
        reasons.append(f"price is higher than {pct_rank:.0f}% of the last 2 years")
    if r.iloc[-1] >= 70:
        reasons.append(f"RSI {r.iloc[-1]:.0f} = overbought (rose too fast)")
    if price >= 1.10 * sma200.iloc[-1]:
        reasons.append(f"{(price / sma200.iloc[-1] - 1) * 100:.0f}% above its 200-day average (stretched)")
    if price < sma50.iloc[-1] and sma50.iloc[-1] > sma200.iloc[-1]:
        reasons.append("dropped below 50-day average - uptrend may be fading")
    score = len(reasons)
    if score >= 3:
        verdict, tone = "Strong sell zone (historically)", "high"
    elif score == 2:
        verdict, tone = "Watch closely - sell signals building", "mid"
    else:
        verdict, tone = "No sell signal - trend not stretched", "low"

    trend = ("Uptrend" if price > sma50.iloc[-1] > sma200.iloc[-1]
             else "Downtrend" if price < sma50.iloc[-1] < sma200.iloc[-1] else "Sideways")

    # Average return by calendar month (small sample - indicative only)
    monthly = s.resample("ME").last().pct_change().dropna()
    by_month = monthly.groupby(monthly.index.month).mean() * 100
    months = {int(m): round(float(v), 2) for m, v in by_month.items()}

    pl = (price - asset["buy"]) * asset["qty"] if asset["buy"] else None
    pl_pct = (price / asset["buy"] - 1) * 100 if asset["buy"] else None

    return {
        **asset, "price": price, "prev": prev, "change_pct": (price / prev - 1) * 100,
        "hi": hi, "hi_date": s.idxmax().strftime("%Y-%m-%d"),
        "lo": lo, "lo_date": s.idxmin().strftime("%Y-%m-%d"),
        "pct_rank": pct_rank, "rsi": float(r.iloc[-1]),
        "sma50": float(sma50.iloc[-1]), "sma200": float(sma200.iloc[-1]),
        "above": above, "below": below, "above_auto": asset["above"] is None,
        "below_auto": asset["below"] is None,
        "score": score, "reasons": reasons, "verdict": verdict, "tone": tone, "trend": trend,
        "months": months, "pl": pl, "pl_pct": pl_pct, "value": price * asset["qty"],
        "series": {
            "dates": [d.strftime("%Y-%m-%d") for d in s.index],
            "close": [round(float(v), 2) for v in s],
            "sma50": [None if pd.isna(v) else round(float(v), 2) for v in sma50],
            "sma200": [None if pd.isna(v) else round(float(v), 2) for v in sma200],
        },
    }


# ---------------------------------------------------------------- alerts
def find_alerts(a, cfg_alerts):
    out = []
    p = a["price"]
    if p >= a["above"]:
        out.append(("above", f"⬆️ {a['name']} is {p:,.2f} {a['unit']} - above your alert level {a['above']:,.2f}"))
    if p <= a["below"]:
        out.append(("below", f"⬇️ {a['name']} is {p:,.2f} {a['unit']} - below your alert level {a['below']:,.2f}"))
    if abs(a["change_pct"]) >= cfg_alerts["daily_move"]:
        arrow = "📈" if a["change_pct"] > 0 else "📉"
        out.append(("move", f"{arrow} {a['name']} moved {a['change_pct']:+.1f}% today ({p:,.2f} {a['unit']})"))
    if a["score"] >= 3:
        out.append(("sell", f"🟡 {a['name']}: {a['verdict']} - " + "; ".join(a["reasons"])))
    return out


def send_whatsapp(phones, text):
    for phone, key in phones.items():
        url = ("https://api.callmebot.com/whatsapp.php?phone=" + phone.strip()
               + "&text=" + urllib.parse.quote(text) + "&apikey=" + key.strip())
        try:
            r = requests.get(url, timeout=30)
            print(f"  WhatsApp -> {phone[-4:].rjust(len(phone), '*')}: HTTP {r.status_code}")
        except Exception as e:
            print(f"  WhatsApp -> {phone}: FAILED {e}")


def dispatch(results, cfg_alerts, phones, send=True):
    today = dt.date.today().isoformat()
    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    state = {k: v for k, v in state.items() if v == today}  # forget older days
    lines = []
    for a in results:
        pl = f" | your P/L: {a['pl']:+,.0f} {a['currency']} ({a['pl_pct']:+.1f}%)" if a["pl"] is not None else ""
        for kind, msg in find_alerts(a, cfg_alerts):
            k = f"{a['key']}:{kind}"
            if k in state:
                continue  # each alert only once per day
            state[k] = today
            lines.append(msg + pl)
    if not lines:
        print("No new alerts.")
    else:
        text = "Gold Hunt alert\n\n" + "\n\n".join(lines)
        print(text)
        if send and phones:
            send_whatsapp(phones, text)
        elif send:
            print("  (no WhatsApp numbers in settings.ini yet)")
    STATE.write_text(json.dumps(state))


# ---------------------------------------------------------------- dashboard
def build_dashboard(results):
    data = json.dumps(results)
    stamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    html = (HERE / "dashboard_template.html").read_text(encoding="utf-8")
    html = html.replace("__DATA__", data).replace("__STAMP__", stamp)
    DASHBOARD.write_text(html, encoding="utf-8")
    print(f"Dashboard: {DASHBOARD}")


# ---------------------------------------------------------------- main
def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    assets, cfg_alerts, phones = load_settings()
    if "--test" in sys.argv:
        send_whatsapp(phones, "✅ Gold Hunt test message - alerts are working.")
        return
    results = []
    for a in assets:
        try:
            r = analyse(a, fetch(a))
            results.append(r)
            print(f"{r['name']:<10} {r['price']:>10,.2f} {r['unit']:<10} {r['change_pct']:+.2f}%  {r['verdict']}")
        except Exception as e:
            print(f"{a['name']}: error - {e}")
    build_dashboard(results)
    dispatch(results, cfg_alerts, phones, send="--no-send" not in sys.argv)


if __name__ == "__main__":
    main()
