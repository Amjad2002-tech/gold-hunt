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
GOLD_REF = HERE / "gold_ref.json"  # gold price at the last "moved X SAR" alert
DASHBOARD = HERE / "dashboard.html"

USD_SAR = 3.75            # the riyal is pegged to the dollar
GRAMS_PER_OUNCE = 31.1035
RIYADH = dt.timezone(dt.timedelta(hours=3), "AST")  # Saudi Arabia has no daylight saving


# ---------------------------------------------------------------- settings
def load_settings():
    cfg = configparser.ConfigParser(inline_comment_prefixes=("#",))
    cfg.optionxform = str  # keep phone numbers / tickers as written
    # On GitHub the whole settings file comes from the GOLD_HUNT_SETTINGS secret
    if os.environ.get("GOLD_HUNT_SETTINGS"):
        cfg.read_string(os.environ["GOLD_HUNT_SETTINGS"].lstrip("﻿"))
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
        "move_sar": num("gold", "move_alert_sar") or 10.0,
        "lang": "ar" if cfg.get("alerts", "language", fallback="en").strip().lower() == "ar" else "en",
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
    # During trading hours the last daily bar already holds the current price.
    # Time of the last trade = last 1-minute bar (falls back to the daily bar's date).
    price_time = df.index[-1]
    try:
        minute = yf.Ticker(asset["ticker"]).history(period="5d", interval="1m")
        if not minute.empty:
            price_time = minute.index[-1]
    except Exception:
        pass
    s.attrs["price_time"] = price_time.isoformat()
    s.attrs["source"] = "yahoo"
    if asset["key"] == "GOLD":
        dewan = dewan_price()
        if dewan:
            # Use Dewan Al Dahab's local 24K price; scale history by the same ratio so the
            # 2-year analysis stays consistent with it (Dewan = world price + their fees)
            s = s * (dewan / s.iloc[-1])
            s.attrs.update(price_time=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                           source="dewanaldahab.com")
    s.attrs["pulled_at"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    return s


DEWAN_URL = "https://www.dewanaldahab.com/ar"
_dewan_cache = {"t": 0.0, "price": None}


def dewan_price():
    """24K price (SAR/gram) shown on dewanaldahab.com, or None if it can't be read.
    The site fills prices in live with JavaScript, so a headless browser reads it."""
    import time
    if time.time() - _dewan_cache["t"] < 60:  # reuse for a minute (pages ask often)
        return _dewan_cache["price"]
    price = None
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(DEWAN_URL, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_function("document.querySelector('#caret24_Price')"
                                   " && document.querySelector('#caret24_Price').getAttribute('data-price')",
                                   timeout=45000)
            value = float(page.get_attribute("#caret24_Price", "data-price"))
            browser.close()
            if 100 < value < 2000:  # sanity check against a broken page
                price = value
    except Exception as e:
        print(f"Dewan price unavailable ({type(e).__name__}) - using world price")
    _dewan_cache.update(t=time.time(), price=price)
    return price


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
    above = upper if asset["above"] is None else asset["above"]
    below = lower if asset["below"] is None else asset["below"]

    # Sell-signal score (historical/technical, not advice). Codes are translated by TEXT / i18n.js
    codes = []
    if pct_rank >= 85:
        codes.append(["rank", round(pct_rank)])
    if r.iloc[-1] >= 70:
        codes.append(["rsi", round(float(r.iloc[-1]))])
    if price >= 1.10 * sma200.iloc[-1]:
        codes.append(["stretch", round((price / sma200.iloc[-1] - 1) * 100)])
    if price < sma50.iloc[-1] and sma50.iloc[-1] > sma200.iloc[-1]:
        codes.append(["fading", 0])
    score = len(codes)
    verdict_code, tone = ("strong", "high") if score >= 3 else ("watch", "mid") if score == 2 else ("none", "low")
    trend_code = ("up" if price > sma50.iloc[-1] > sma200.iloc[-1]
                  else "down" if price < sma50.iloc[-1] < sma200.iloc[-1] else "side")
    en = TEXT["en"]
    reasons = [en["reason_" + k].format(v=v) for k, v in codes]
    verdict, trend = en["verdict_" + verdict_code], en["trend_" + trend_code]

    # Average return by calendar month (small sample - indicative only)
    monthly = s.resample("ME").last().pct_change().dropna()
    by_month = monthly.groupby(monthly.index.month).mean() * 100
    months = {int(m): round(float(v), 2) for m, v in by_month.items()}

    pl = (price - asset["buy"]) * asset["qty"] if asset["buy"] else None
    pl_pct = (price / asset["buy"] - 1) * 100 if asset["buy"] else None

    return {
        **asset, "price": price, "prev": prev, "change_pct": (price / prev - 1) * 100,
        "price_time": s.attrs.get("price_time"), "pulled_at": s.attrs.get("pulled_at"),
        "hi": hi, "hi_date": s.idxmax().strftime("%Y-%m-%d"),
        "lo": lo, "lo_date": s.idxmin().strftime("%Y-%m-%d"),
        "pct_rank": pct_rank, "rsi": float(r.iloc[-1]),
        "sma50": float(sma50.iloc[-1]), "sma200": float(sma200.iloc[-1]),
        "above": above, "below": below, "band_upper": upper, "band_lower": lower, "above_auto": asset["above"] is None,
        "below_auto": asset["below"] is None,
        "score": score, "reasons": reasons, "verdict": verdict, "tone": tone, "trend": trend,
        "reason_codes": codes, "verdict_code": verdict_code, "trend_code": trend_code,
        "months": months, "pl": pl, "pl_pct": pl_pct, "value": price * asset["qty"],
        "series": {
            "dates": [d.strftime("%Y-%m-%d") for d in s.index],
            "close": [round(float(v), 2) for v in s],
            "sma50": [None if pd.isna(v) else round(float(v), 2) for v in sma50],
            "sma200": [None if pd.isna(v) else round(float(v), 2) for v in sma200],
        },
    }


# ---------------------------------------------------------------- alerts
def unit(a, T):
    return T["unit_gram"] if a["key"] == "GOLD" else T["unit_share"].format(c=T.get("cur_" + a["currency"], a["currency"]))


def find_alerts(a, cfg_alerts):
    T = TEXT[cfg_alerts["lang"]]
    out = []
    p, u = a["price"], unit(a, T)
    name = T["gold_name"] if a["key"] == "GOLD" else a["name"]
    if p >= a["above"]:
        out.append(("above", T["alert_above"].format(n=name, p=p, u=u, lvl=a["above"])))
    if p <= a["below"]:
        out.append(("below", T["alert_below"].format(n=name, p=p, u=u, lvl=a["below"])))
    if abs(a["change_pct"]) >= cfg_alerts["daily_move"]:
        arrow = "📈" if a["change_pct"] > 0 else "📉"
        out.append(("move", T["alert_move"].format(a=arrow, n=name, c=a["change_pct"], p=p, u=u)))
    if a["score"] >= 3:
        reasons = T["sep"].join(T["reason_" + k].format(v=v) for k, v in a["reason_codes"])
        out.append(("sell", f"🟡 {name}: {T['verdict_' + a['verdict_code']]} - {reasons}"))
    return out


# All user-facing text for WhatsApp alerts (the pages use i18n.js)
TEXT = {
    "en": {
        "title": "Gold Hunt alert", "riyadh": "Riyadh time", "sep": "; ", "gold_name": "Gold 24K",
        "unit_gram": "SAR/gram", "unit_share": "{c}/share", "cur_SAR": "SAR", "cur_USD": "USD",
        "alert_above": "⬆️ {n} is {p:,.2f} {u} - above your alert level {lvl:,.2f}",
        "alert_below": "⬇️ {n} is {p:,.2f} {u} - below your alert level {lvl:,.2f}",
        "alert_move": "{a} {n} moved {c:+.1f}% today ({p:,.2f} {u})",
        "pl": " | your P/L: {pl:+,.0f} {c} ({pp:+.1f}%)",
        "reason_rank": "price is higher than {v}% of the last 2 years",
        "reason_rsi": "RSI {v} = overbought (rose too fast)",
        "reason_stretch": "{v}% above its 200-day average (stretched)",
        "reason_fading": "dropped below 50-day average - uptrend may be fading",
        "verdict_strong": "Strong sell zone (historically)",
        "verdict_watch": "Watch closely - sell signals building",
        "verdict_none": "No sell signal - trend not stretched",
        "trend_up": "Uptrend", "trend_down": "Downtrend", "trend_side": "Sideways",
        "test": "✅ Gold Hunt test message - alerts are working.",
        "morning": "☀️ Good morning - gold report {d}",
        "m_price": "Gold 24K now {p:,.2f} SAR/gram ({c:+.1f}% since yesterday)",
        "m_pl": "Your {g:,.0f} g bought at {b:,.2f}: {pl:+,.0f} SAR ({pp:+.1f}%)",
        "m_range": "2-year range {lo:,.0f} - {hi:,.0f} - today is higher than {r}% of days",
        "m_signal": "Signal: {v}",
        "mv_title": "{a} Gold 24K moved {d:+.2f} SAR",
        "mv_line": "From {old:,.2f} to {new:,.2f} SAR/gram (dewanaldahab.com)",
    },
    "ar": {
        "title": "تنبيه Gold Hunt", "riyadh": "بتوقيت الرياض", "sep": "، ", "gold_name": "ذهب عيار 24",
        "unit_gram": "ريال/جرام", "unit_share": "{c}/سهم", "cur_SAR": "ريال", "cur_USD": "دولار",
        "alert_above": "⬆️ {n} وصل إلى {p:,.2f} {u} - أعلى من مستوى التنبيه {lvl:,.2f}",
        "alert_below": "⬇️ {n} نزل إلى {p:,.2f} {u} - أقل من مستوى التنبيه {lvl:,.2f}",
        "alert_move": "{a} {n} تحرك {c:+.1f}% اليوم ({p:,.2f} {u})",
        "pl": " | ربحك/خسارتك: {pl:+,.0f} {c} ({pp:+.1f}%)",
        "reason_rank": "السعر أعلى من {v}% من أيام آخر سنتين",
        "reason_rsi": "مؤشر RSI عند {v} = تشبّع شرائي (ارتفع بسرعة)",
        "reason_stretch": "أعلى بـ {v}% من متوسط 200 يوم (مرتفع جداً)",
        "reason_fading": "نزل تحت متوسط 50 يوم - الاتجاه الصاعد قد يضعف",
        "verdict_strong": "منطقة بيع قوية (تاريخياً)",
        "verdict_watch": "راقب عن قرب - إشارات البيع تتزايد",
        "verdict_none": "لا توجد إشارة بيع",
        "trend_up": "اتجاه صاعد", "trend_down": "اتجاه هابط", "trend_side": "اتجاه عرضي",
        "test": "✅ رسالة تجريبية من Gold Hunt - التنبيهات تعمل.",
        "morning": "☀️ صباح الخير - تقرير الذهب {d}",
        "m_price": "ذهب عيار 24 الآن {p:,.2f} ريال/جرام ({c:+.1f}% منذ أمس)",
        "m_pl": "لديك {g:,.0f} جرام بسعر شراء {b:,.2f}: {pl:+,.0f} ريال ({pp:+.1f}%)",
        "m_range": "نطاق السنتين {lo:,.0f} - {hi:,.0f} - السعر اليوم أعلى من {r}% من الأيام",
        "m_signal": "الإشارة: {v}",
        "mv_title": "{a} سعر ذهب عيار 24 تغيّر {d:+.2f} ريال",
        "mv_line": "من {old:,.2f} إلى {new:,.2f} ريال/جرام (ديوان الذهب)",
    },
}


META_API = "https://graph.facebook.com/v25.0/{phone_id}/messages"
# Approved Utility template with one {{1}} placeholder; switch with the META_WA_TEMPLATE secret
META_TEMPLATE = os.environ.get("META_WA_TEMPLATE", "").strip() or "gold_alert"


def meta_config():
    """WhatsApp Cloud API (Meta) settings from GitHub secrets / environment, or None."""
    token = os.environ.get("META_WA_TOKEN", "").strip()
    phone_id = os.environ.get("META_WA_PHONE_ID", "").strip()
    to = [n.strip().lstrip("+") for n in os.environ.get("META_WA_TO", "").replace("\n", ",").split(",") if n.strip()]
    return {"token": token, "phone_id": phone_id, "to": to} if token and phone_id and to else None


def send_meta_hello(cfg):
    """Delivery check with Meta's pre-approved hello_world template (works before gold_alert is approved)."""
    for number in cfg["to"]:
        body = {"messaging_product": "whatsapp", "to": number, "type": "template",
                "template": {"name": "hello_world", "language": {"code": "en_US"}}}
        r = requests.post(META_API.format(phone_id=cfg["phone_id"]), json=body, timeout=30,
                          headers={"Authorization": "Bearer " + cfg["token"]})
        err = "" if r.ok else " " + str(r.json().get("error", {}).get("code", ""))
        print(f"  WhatsApp (Meta hello) -> {number[-4:].rjust(len(number), '*')}: HTTP {r.status_code}{err}")


def send_meta(cfg, text):
    """Send through the approved template. Template values can't hold new lines or tabs,
    or more than 4 spaces in a row, so the alert is flattened into one line."""
    value = " | ".join(part.strip() for part in text.split("\n") if part.strip())
    value = " ".join(value.split())[:1000]
    delivered = False
    for number in cfg["to"]:
        body = {"messaging_product": "whatsapp", "to": number, "type": "template",
                "template": {"name": META_TEMPLATE, "language": {"code": "ar"},  # the template exists in Arabic only
                             "components": [{"type": "body", "parameters": [{"type": "text", "text": value}]}]}}
        masked = number[-4:].rjust(len(number), "*")
        try:
            r = requests.post(META_API.format(phone_id=cfg["phone_id"]), json=body, timeout=30,
                              headers={"Authorization": "Bearer " + cfg["token"]})
            delivered |= r.ok
            err = "" if r.ok else " " + str(r.json().get("error", {}).get("code", ""))
            print(f"  WhatsApp (Meta) -> {masked}: HTTP {r.status_code}{err}")
        except Exception as e:
            print(f"  WhatsApp (Meta) -> {masked}: FAILED ({type(e).__name__})")
    return delivered


def send_whatsapp(phones, text):
    """Send to every recipient; return True if at least one message was delivered.
    Uses Meta's WhatsApp Cloud API when configured, otherwise CallMeBot numbers."""
    meta = meta_config()
    if meta:
        return send_meta(meta, text)
    delivered = False
    for phone, key in phones.items():
        url = ("https://api.callmebot.com/whatsapp.php?phone=" + phone.strip()
               + "&text=" + urllib.parse.quote(text) + "&apikey=" + key.strip())
        masked = phone.strip()[-4:].rjust(len(phone.strip()), "*")
        try:
            r = requests.get(url, timeout=30)
            delivered |= r.ok
            print(f"  WhatsApp -> {masked}: HTTP {r.status_code}")
        except Exception as e:  # message would contain the URL with the API key
            print(f"  WhatsApp -> {masked}: FAILED ({type(e).__name__})")
    return delivered


def dispatch(results, cfg_alerts, phones, send=True):
    today = dt.date.today().isoformat()
    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    state = {k: v for k, v in state.items() if v == today}  # forget older days
    T = TEXT[cfg_alerts["lang"]]
    keys, lines = [], []
    for a in results:
        pl = (T["pl"].format(pl=a["pl"], c=T.get("cur_" + a["currency"], a["currency"]), pp=a["pl_pct"])
              if a["pl"] is not None else "")
        for kind, msg in find_alerts(a, cfg_alerts):
            k = f"{a['key']}:{kind}"
            if k not in state:  # each alert only once per day
                keys.append(k)
                lines.append(msg + pl)
    if not lines:
        print("No new alerts.")
        return
    riyadh = dt.datetime.now(RIYADH).strftime("%Y-%m-%d %H:%M")
    text = f"{T['title']}\n🕒 {riyadh} ({T['riyadh']})\n\n" + "\n\n".join(lines)
    print(text)
    if not send:
        return
    if not phones and not meta_config():
        print("  (no WhatsApp numbers yet)")
        return
    # Only remember alerts that actually went out, so failed ones retry next check
    if send_whatsapp(phones, text):
        state.update(dict.fromkeys(keys, today))
        STATE.write_text(json.dumps(state))


def watch_gold(assets, cfg_alerts, phones, send=True):
    """Gold-only check: alert when the price has moved move_sar (default 10 SAR) up or down
    since the last alert. The first run only remembers the price."""
    T = TEXT[cfg_alerts["lang"]]
    gold = next(a for a in assets if a["key"] == "GOLD")
    a = analyse(gold, fetch(gold))
    price, step = a["price"], cfg_alerts["move_sar"]
    try:
        ref = json.loads(GOLD_REF.read_text())["price"]
    except Exception:
        ref = None
    if ref is None:
        GOLD_REF.write_text(json.dumps({"price": price}))
        print(f"Gold reference set to {price:.2f}")
        return
    diff = price - ref
    print(f"Gold {price:.2f} vs reference {ref:.2f} ({diff:+.2f}, alert at ±{step:g})")
    if abs(diff) < step:
        return
    lines = [T["mv_title"].format(a="📈" if diff > 0 else "📉", d=diff),
             T["mv_line"].format(old=ref, new=price)]
    if a["pl"] is not None:
        lines.append(T["m_pl"].format(g=a["qty"], b=a["buy"], pl=a["pl"], pp=a["pl_pct"]))
    lines.append(f"🕒 {dt.datetime.now(RIYADH).strftime('%Y-%m-%d %H:%M')} ({T['riyadh']})")
    text = "\n".join(lines)
    print(text)
    if not send:
        return
    if send_whatsapp(phones, text):  # only move the reference once the alert went out
        GOLD_REF.write_text(json.dumps({"price": price}))


def morning_report(assets, cfg_alerts, phones, send=True):
    """Daily gold-only summary (sent by the 8:00 AM Riyadh schedule)."""
    T = TEXT[cfg_alerts["lang"]]
    gold = next(a for a in assets if a["key"] == "GOLD")
    a = analyse(gold, fetch(gold))
    lines = [T["morning"].format(d=dt.datetime.now(RIYADH).strftime("%Y-%m-%d")),
             T["m_price"].format(p=a["price"], c=a["change_pct"])]
    if a["pl"] is not None:
        lines.append(T["m_pl"].format(g=a["qty"], b=a["buy"], pl=a["pl"], pp=a["pl_pct"]))
    lines.append(T["m_range"].format(lo=a["lo"], hi=a["hi"], r=round(a["pct_rank"])))
    reasons = T["sep"].join(T["reason_" + k].format(v=v) for k, v in a["reason_codes"])
    lines.append(T["m_signal"].format(v=T["verdict_" + a["verdict_code"]]) + (f" ({reasons})" if reasons else ""))
    text = "\n".join(lines)
    print(text)
    if send:
        send_whatsapp(phones, text)


# ---------------------------------------------------------------- dashboard
def build_dashboard(results):
    data = json.dumps(results).replace("</", "<\\/")  # keep user text from closing the <script>
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
        send_whatsapp(phones, TEXT[cfg_alerts["lang"]]["test"])
        return
    if "--hello" in sys.argv:
        cfg = meta_config()
        if os.environ.get("ONLY_TO", "").strip():  # send to one number only
            cfg["to"] = [os.environ["ONLY_TO"].strip().lstrip("+")]
        send_meta_hello(cfg)
        return
    if "--watch" in sys.argv:
        watch_gold(assets, cfg_alerts, phones, send="--no-send" not in sys.argv)
        return
    if "--morning" in sys.argv:
        morning_report(assets, cfg_alerts, phones, send="--no-send" not in sys.argv)
        return
    results, failed = [], 0
    for a in assets:
        try:
            r = analyse(a, fetch(a))
            results.append(r)
            print(f"{r['name']:<10} {r['price']:>10,.2f} {r['unit']:<10} {r['change_pct']:+.2f}%  {r['verdict']}")
        except Exception as e:
            failed += 1
            print(f"{a['name']}: error - {e}")
            print(f"FAILED_ASSET {type(e).__name__}")  # name-free line for the public cloud log
    build_dashboard(results)
    dispatch(results, cfg_alerts, phones, send="--no-send" not in sys.argv)
    if failed:
        sys.exit(1)  # make the cloud run show red so failures are noticed


if __name__ == "__main__":
    main()
