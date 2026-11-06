"""Gold Hunt - price tracker, 2-year analysis, dashboard and WhatsApp alerts.

Usage:
    python gold_hunt.py              # analyse, rebuild dashboard, send alerts if triggered
    python gold_hunt.py --no-send    # same, but only print alerts (no WhatsApp)
    python gold_hunt.py --test       # send a test WhatsApp message (with chart) to everyone
    python gold_hunt.py --chart      # save the gold chart to chart.png (nothing is sent)
    python gold_hunt.py --create-template  # one-time: create the gold_report_chart template on Meta
"""
import configparser
import datetime as dt
import json
import os
import sys
import urllib.parse
from pathlib import Path

import numpy as np
import pandas as pd
import requests
import yfinance as yf

import outlook as outlook_mod

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
    # 10 years for the behaviour analysis; the usual fields/charts still use the last 2 years
    df = yf.Ticker(asset["ticker"]).history(period="10y", interval="1d", auto_adjust=False)
    if df.empty:
        raise RuntimeError(f"No data for {asset['ticker']}")
    full = df["Close"].dropna()
    full.index = full.index.tz_localize(None).normalize()
    full = full[~full.index.duplicated(keep="last")]
    if asset["key"] == "GOLD":
        full = full * USD_SAR / GRAMS_PER_OUNCE  # USD/oz -> SAR/gram
    s = full[full.index > full.index[-1] - pd.DateOffset(years=2)].copy()
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
            full = full * (dewan / s.iloc[-1])
            s = s * (dewan / s.iloc[-1])
            s.attrs.update(price_time=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                           source="dewanaldahab.com")
    s.attrs["pulled_at"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    s.attrs["long"] = full
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


def _num(v, nd=2):
    """Round to a JSON-safe float (None for NaN/inf)."""
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None
    return round(v, nd) if np.isfinite(v) else None


def _clip(v, lo=-1.0, hi=1.0):
    return 0.0 if v is None or not np.isfinite(v) else float(min(hi, max(lo, v)))


def _bucket(v, edges):
    """Index of the bucket `v` falls in (edges are the inner cut points); NaN -> -1."""
    v = np.asarray(v, dtype=float)
    return np.where(np.isnan(v), -1, np.searchsorted(edges, np.nan_to_num(v), side="right"))


def _independent(idx, gap):
    """How many sample days are at least `gap` days apart (non-overlapping forward windows)."""
    n, last = 0, -10 ** 9
    for i in idx:
        if i - last >= gap:
            n, last = n + 1, i
    return n


def _swings(c, look=250, w=10):
    """Confirmed swing highs/lows (a close that is the max/min of the w days on either side) in the
    last `look` days. The newest w days can't be confirmed yet, so nothing uses future prices."""
    v = c.values[-(look + w):] if len(c) > look + w else c.values
    highs, lows = [], []
    for i in range(w, len(v) - w):
        seg = v[i - w:i + w + 1]
        if v[i] == seg.max():
            highs.append(float(v[i]))
        elif v[i] == seg.min():
            lows.append(float(v[i]))
    return highs, lows


def _levels(points, price, above, tol=0.015, k=3):
    """Cluster swing points within `tol` and return the k nearest levels above/below the price."""
    pts = sorted(p for p in points if (p > price if above else p < price))
    clusters = []
    for p in pts:
        if clusters and p / clusters[-1][-1] - 1 <= tol:
            clusters[-1].append(p)
        else:
            clusters.append([p])
    lv = [{"price": _num(np.mean(cl)), "touches": len(cl),
           "dist_pct": _num((np.mean(cl) / price - 1) * 100)} for cl in clusters]
    lv.sort(key=lambda d: abs(d["dist_pct"]))
    return lv[:k]


BH_RSI_EDGES = [30, 45, 55, 70]
BH_RANGE_EDGES = [20, 40, 60, 80]
BH_DIST_EDGES = [-10, -3, 3, 10, 20]
BH_HORIZONS = (20, 60)
BH_WEIGHTS = {"history": 35, "trend": 20, "stretch": 20, "momentum": 15, "season": 10}


def behaviour(asset, c):
    """History-based behaviour of one asset: what happened after past days that looked like today,
    plus volatility, drawdowns, seasonality, support/resistance and momentum, combined into a score
    (-100..+100) and a stance code. Historical statistics only - not personalised advice.
    Every indicator at day t uses data up to t only, and forward returns are only taken from days
    whose 20/60-day future is already known (no look-ahead)."""
    c = c.dropna().astype(float)
    n = len(c)
    out = {"years": _num(n / 252, 1), "days": n, "from": c.index[0].strftime("%Y-%m-%d") if n else None,
           "disclaimer": "bh_disclaimer"}
    if n < 300:
        out.update(score=0, stance="hold", confidence="low", reasons=[["bh_short_history", n]], now=None,
                   similar=None, volatility=None, drawdown=None, momentum=None, seasonality=None,
                   levels=None, position=None, components=None, weights=BH_WEIGHTS)
        return out
    v = c.values
    price = float(v[-1])
    logret = np.diff(np.log(v))

    # ---- features (each uses data up to that day only)
    r = rsi(c).values
    sma50 = c.rolling(50).mean().values
    sma200 = c.rolling(200).mean().values
    dist200 = (v / sma200 - 1) * 100
    win = 252
    rangepos = np.full(n, np.nan)  # % of the previous year's closes below that day's close
    if n > win:
        sw = np.lib.stride_tricks.sliding_window_view(v, win)  # row j = v[j:j+win], ends on day j+win-1
        rangepos[win - 1:] = (sw < sw[:, -1:]).mean(axis=1) * 100
    trend = np.where((v > sma50) & (sma50 > sma200), 1, np.where((v < sma50) & (sma50 < sma200), -1, 0))
    trend = np.where(np.isnan(sma200), -9, trend)

    b_rsi = _bucket(r, BH_RSI_EDGES)
    b_rng = _bucket(rangepos, BH_RANGE_EDGES)
    b_dst = _bucket(dist200, BH_DIST_EDGES)
    valid = (b_rsi >= 0) & (b_rng >= 0) & (b_dst >= 0) & (trend != -9)
    now = {"rsi": _num(r[-1], 1), "range_pos": _num(rangepos[-1], 1), "dist_sma200_pct": _num(dist200[-1], 1),
           "trend": {1: "up", -1: "down", 0: "side"}.get(int(trend[-1]), "side")}

    # ---- forward returns after similar days (widen the match until there are enough samples)
    vol_ann = float(np.std(logret[-252:], ddof=1) * np.sqrt(252))
    match_levels = [("all", [b_rsi, b_rng, b_dst, trend]), ("no_trend", [b_rsi, b_rng, b_dst]),
                    ("rsi_range", [b_rsi, b_rng]), ("range", [b_rng])]
    similar = {"match": None, "horizons": {}}
    sim_idx = np.array([], dtype=int)
    if valid[-1]:
        for name, feats in match_levels:
            m = valid.copy()
            for f in feats:
                m &= f == f[-1]
            idx = np.flatnonzero(m[:n - BH_HORIZONS[0]])  # only days with a known future
            if len(idx) >= 40 or name == "range":
                similar["match"], sim_idx = name, idx
                break
    base_idx = np.flatnonzero(valid)
    for h in BH_HORIZONS:
        fwd = np.full(n, np.nan)
        fwd[:n - h] = (v[h:] / v[:n - h] - 1) * 100
        si = sim_idx[sim_idx < n - h]
        bi = base_idx[base_idx < n - h]
        sv, bv = fwd[si], fwd[bi]
        similar["horizons"][str(h)] = {
            "samples": int(len(sv)), "independent": _independent(si, h),
            "median_pct": _num(np.median(sv)) if len(sv) else None,
            "mean_pct": _num(np.mean(sv)) if len(sv) else None,
            "hit_rate": _num((sv > 0).mean() * 100, 1) if len(sv) else None,
            "p10_pct": _num(np.percentile(sv, 10)) if len(sv) else None,
            "p90_pct": _num(np.percentile(sv, 90)) if len(sv) else None,
            "base_median_pct": _num(np.median(bv)) if len(bv) else None,
            "base_hit_rate": _num((bv > 0).mean() * 100, 1) if len(bv) else None,
        }

    # ---- volatility, drawdown, momentum
    vol60 = pd.Series(logret).rolling(60).std().values * np.sqrt(252)
    vol60_now = float(vol60[-1])
    vol_pctile = float((vol60[~np.isnan(vol60)] < vol60_now).mean() * 100)
    volatility = {"annual_pct": _num(vol_ann * 100, 1),
                  "typical_day_pct": _num(np.median(np.abs(logret[-252:])) * 100),
                  "recent60_annual_pct": _num(vol60_now * 100, 1), "recent_vs_history_pctile": _num(vol_pctile, 0)}
    peak = np.maximum.accumulate(v)
    dd = (v / peak - 1) * 100
    drawdown = {"current_pct": _num(dd[-1]), "max_pct": _num(dd.min()),
                "max_date": c.index[int(dd.argmin())].strftime("%Y-%m-%d"),
                "median_pct": _num(np.median(dd)), "peak": _num(peak[-1]),
                "deeper_than_pct_of_days": _num((dd > dd[-1]).mean() * 100, 0)}
    mom = {f"ret{k}_pct": (_num((price / v[-k - 1] - 1) * 100) if n > k else None) for k in (20, 60, 250)}

    # ---- seasonality (month-end to month-end; the current, unfinished month is left out)
    me = c.resample("ME").last()
    if me.index[-1].to_period("M") == c.index[-1].to_period("M"):
        me = me.iloc[:-1]
    mr = me.pct_change().dropna() * 100
    months = {int(mo): {"avg_pct": _num(x.mean()), "hit_rate": _num((x > 0).mean() * 100, 0), "years": int(len(x))}
              for mo, x in mr.groupby(mr.index.month)}
    cur_m = int(c.index[-1].month)
    seasonality = {"month": cur_m, "this_month": months.get(cur_m), "next_month": months.get(cur_m % 12 + 1),
                   "all_months_avg_pct": _num(mr.mean()), "by_month": months}

    # ---- support / resistance from confirmed swing points of the last year
    highs, lows = _swings(c)
    lv = {"resistance": _levels(highs + lows, price, True), "support": _levels(highs + lows, price, False)}

    # ---- combine into a score (each component -1..+1)
    sig60 = vol_ann * np.sqrt(60 / 252) * 100  # one typical 60-day move, in %
    h20, h60 = similar["horizons"]["20"], similar["horizons"]["60"]
    comp = {}
    if h60["median_pct"] is not None and h60["base_median_pct"] is not None:
        edge = (h60["median_pct"] - h60["base_median_pct"]) / (0.5 * sig60)
        hit = (h60["hit_rate"] - h60["base_hit_rate"]) / 20
        edge20 = 0.0
        if h20["median_pct"] is not None and h20["base_median_pct"] is not None:
            edge20 = (h20["median_pct"] - h20["base_median_pct"]) / (0.5 * sig60 * np.sqrt(20 / 60))
        # fewer independent samples -> trust the history component less
        trust = min(1.0, h60["independent"] / 8)
        comp["history"] = _clip(trust * (0.5 * _clip(edge) + 0.3 * _clip(hit) + 0.2 * _clip(edge20)))
    comp["trend"] = float({1: 1, -1: -1}.get(int(trend[-1]), 0))
    # stretched above the long average / top of the yearly range / overbought -> negative (and the reverse)
    stretch = -(dist200[-1] / (vol_ann * 100 * 0.6))
    rp = 0.0 if np.isnan(rangepos[-1]) else -(rangepos[-1] - 50) / 50
    rs = -(r[-1] - 50) / 25
    comp["stretch"] = _clip(0.4 * _clip(stretch) + 0.3 * _clip(rp) + 0.3 * _clip(rs))
    if mom["ret60_pct"] is not None:
        comp["momentum"] = _clip(mom["ret60_pct"] / sig60)
    tm = seasonality["this_month"]
    if tm and tm["years"] >= 4 and tm["avg_pct"] is not None:
        comp["season"] = _clip((tm["avg_pct"] - (seasonality["all_months_avg_pct"] or 0))
                               / (vol_ann * 100 * np.sqrt(21 / 252)))
    wsum = sum(BH_WEIGHTS[k] for k in comp)
    score = int(round(sum(comp[k] * BH_WEIGHTS[k] for k in comp) / wsum * 100)) if wsum else 0
    stance = ("buy_zone" if score >= 50 else "accumulate" if score >= 20 else "hold" if score > -20
              else "take_profit" if score > -50 else "sell_zone")
    sgn = np.sign(score)
    strong = [x for x in comp.values() if abs(x) >= 0.15]
    agree = (sum(np.sign(x) == sgn for x in strong) / len(strong)) if (strong and sgn) else 0.5
    indep = h60["independent"]
    confidence = ("high" if indep >= 10 and h60["samples"] >= 80 and agree >= 0.7 and abs(score) >= 25
                  else "medium" if indep >= 5 and h60["samples"] >= 40 and agree >= 0.5 else "low")

    # ---- reason codes [code, value], translated by TEXT / i18n.js
    reasons = []
    if h60["hit_rate"] is not None:
        reasons.append(["bh_hist60", round(h60["hit_rate"])])
        reasons.append(["bh_med60", round(h60["median_pct"], 1)])
    reasons.append(["bh_trend_" + now["trend"], 0])
    if dist200[-1] >= 10:
        reasons.append(["bh_above_avg", round(float(dist200[-1]))])
    elif dist200[-1] <= -5:
        reasons.append(["bh_below_avg", round(float(-dist200[-1]))])
    if r[-1] >= 70:
        reasons.append(["bh_rsi_high", round(float(r[-1]))])
    elif r[-1] <= 30:
        reasons.append(["bh_rsi_low", round(float(r[-1]))])
    if not np.isnan(rangepos[-1]):
        if rangepos[-1] >= 85:
            reasons.append(["bh_range_high", round(float(rangepos[-1]))])
        elif rangepos[-1] <= 15:
            reasons.append(["bh_range_low", round(float(100 - rangepos[-1]))])
    if mom["ret60_pct"] is not None and abs(mom["ret60_pct"]) >= sig60:
        reasons.append(["bh_mom_strong" if mom["ret60_pct"] > 0 else "bh_mom_weak", round(mom["ret60_pct"], 1)])
    if "season" in comp and abs(comp["season"]) >= 0.3:
        reasons.append(["bh_season_good" if comp["season"] > 0 else "bh_season_bad", round(tm["avg_pct"], 1)])
    if lv["resistance"] and lv["resistance"][0]["dist_pct"] <= 3:
        reasons.append(["bh_near_res", round(lv["resistance"][0]["dist_pct"], 1)])
    if lv["support"] and lv["support"][0]["dist_pct"] >= -3:
        reasons.append(["bh_near_sup", round(-lv["support"][0]["dist_pct"], 1)])
    if dd[-1] <= -15:
        reasons.append(["bh_drawdown", round(float(-dd[-1]))])
    if vol_pctile >= 85:
        reasons.append(["bh_vol_high", round(vol60_now * 100)])

    # ---- position context (only when the user entered a buy price) - still statistics, not advice
    position = None
    buy = asset.get("buy")
    if buy:
        pl_pct = (price / buy - 1) * 100
        position = {"pl_pct": _num(pl_pct), "pl_in_typical_moves": _num(pl_pct / sig60),
                    "typical_60d_move_pct": _num(sig60),
                    "breakeven_pct": _num((buy / price - 1) * 100),
                    "buy_price_pctile_1y": _num((v[-252:] < buy).mean() * 100, 0)}
        if pl_pct >= 0:
            reasons.append(["bh_pos_gain", round(pl_pct / sig60, 1)])
        else:
            reasons.append(["bh_pos_breakeven", round((buy / price - 1) * 100, 1)])

    out.update(score=score, stance=stance, confidence=confidence, reasons=reasons, now=now, similar=similar,
               volatility=volatility, drawdown=drawdown, momentum=mom, seasonality=seasonality, levels=lv,
               position=position, components={k: _num(x) for k, x in comp.items()}, weights=BH_WEIGHTS)
    return out


def analyse(asset, s):
    long = s.attrs.pop("long", None)  # 10-year series for behaviour(); kept out of the result
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

    hist = s if long is None else long
    bh = behaviour(asset, hist)
    ol = outlook_mod.outlook(asset, hist, bh, STATE.parent / "news_cache.json")

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
        "months": months, "behaviour": bh, "outlook": ol, "pl": pl, "pl_pct": pl_pct, "value": price * asset["qty"],
        "series": _chart_series(s if long is None else long, s),
    }


def _chart_series(full, s, years=5):
    """Up to 5 years of closes + averages for the dashboard range buttons (1M..5Y).
    Averages come from the full history so the first chart days already have them."""
    full = full.copy()
    full.iloc[-1] = s.iloc[-1]  # same latest price as the analysis
    m50, m200 = full.rolling(50).mean(), full.rolling(200).mean()
    keep = full.index > full.index[-1] - pd.DateOffset(years=years)
    r = lambda v: None if pd.isna(v) else round(float(v), 2)
    return {"dates": [d.strftime("%Y-%m-%d") for d in full.index[keep]],
            "close": [r(v) for v in full[keep]], "sma50": [r(v) for v in m50[keep]],
            "sma200": [r(v) for v in m200[keep]]}


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
        "morning": "☀️ Good morning - your portfolio report {d}",
        "m_price": "Gold 24K now {p:,.2f} SAR/gram ({c:+.1f}% since yesterday)",
        "m_pl": "Your {g:,.0f} g bought at {b:,.2f}: {pl:+,.0f} SAR ({pp:+.1f}%)",
        "m_range": "2-year range {lo:,.0f} - {hi:,.0f} - today is higher than {r}% of days",
        "m_signal": "Signal: {v}",
        "h_line": "{i} {n}: {p:,.2f} {c} (yesterday {y:,.2f}, {cp:+.1f}%)",
        "h_pl": " - {q:,.0f} {qn} bought at {b:,.2f} - profit {pl:+,.0f} {c} ({pp:+.1f}%)",
        "h_grams": "g", "h_shares": "shares", "h_total": "Total: ",
        "mv_title": "{a} Gold 24K moved {d:+.2f} SAR",
        "mv_line": "From {old:,.2f} to {new:,.2f} SAR/gram (dewanaldahab.com)",
        "stance_buy_zone": "Historically a buy zone", "stance_accumulate": "Historically leaned positive",
        "stance_hold": "Historically neutral - hold / wait",
        "stance_take_profit": "Historically leaned negative - profit-taking zone",
        "stance_sell_zone": "Historically a sell zone",
        "conf_low": "low confidence", "conf_medium": "medium confidence", "conf_high": "high confidence",
        "bh_hist60": "historically, in similar conditions the price was higher 60 trading days later {v}% of the time",
        "bh_med60": "median move 60 trading days after similar days: {v:+}%",
        "bh_trend_up": "uptrend (above 50- and 200-day averages)",
        "bh_trend_down": "downtrend (below 50- and 200-day averages)", "bh_trend_side": "no clear trend",
        "bh_above_avg": "{v}% above its 200-day average (stretched)", "bh_below_avg": "{v}% below its 200-day average",
        "bh_rsi_high": "RSI {v} = overbought", "bh_rsi_low": "RSI {v} = oversold",
        "bh_range_high": "higher than {v}% of the past year", "bh_range_low": "lower than {v}% of the past year",
        "bh_mom_strong": "strong 60-day rise ({v:+}%)", "bh_mom_weak": "weak last 60 days ({v:+}%)",
        "bh_season_good": "this month has historically averaged {v:+}%",
        "bh_season_bad": "this month has historically averaged {v:+}%",
        "bh_near_res": "resistance (past swing high) {v}% above", "bh_near_sup": "support (past swing low) {v}% below",
        "bh_drawdown": "{v}% below its peak", "bh_vol_high": "unusually volatile now ({v}% a year)",
        "bh_pos_gain": "your gain equals {v}x a typical 60-day move",
        "bh_pos_breakeven": "price needs {v:+}% to reach your buy price",
        "bh_short_history": "only {v} days of history - not enough for analysis",
        "ol_disclaimer": "Probabilities from this asset's own price history and a simple headline word count - not financial advice and not a personal recommendation. The past does not guarantee the future.",
        "ol_short_history": "not enough price history for a forecast",
        "ol_lean_favourable": "Historical odds favour a rise", "ol_lean_neutral": "Historical odds are balanced",
        "ol_lean_unfavourable": "Historical odds lean towards a fall",
        "ol_odds_up": "Odds of being higher: 1 week {w}%, 1 month {m}%, 3 months {q}%",
        "ol_range_1m": "Likely range in 1 month (80% of simulations): {lo:,.2f} - {hi:,.2f}",
        "ol_r_behaviour": "behaviour score {v:+}",
        "ol_r_fc_up21": "{v}% of simulations end higher in 1 month",
        "ol_r_fc_up63": "{v}% of simulations end higher in 3 months",
        "ol_r_fc_dip5": "{v}% chance of touching -5% within a month",
        "ol_r_fc_pop5": "{v}% chance of touching +5% within a month",
        "ol_r_fc_buy63": "{v}% chance of being above your buy price in 3 months",
        "ol_r_news_positive": "{v} positive headlines recently", "ol_r_news_negative": "{v} negative headlines recently",
        "news_positive": "positive", "news_negative": "negative", "news_neutral": "neutral",
        "news_title": "Latest news", "news_none": "no recent news available",
        "fc_title": "Range of possible prices", "fc_prob_up": "chance higher", "fc_touch_up5": "touch +5%",
        "fc_touch_dn5": "touch -5%", "fc_above_buy": "above buy price",
        "bh_disclaimer": "Historical statistics only, not financial advice. The past does not guarantee the future.",
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
        "morning": "☀️ صباح الخير - تقرير محفظتك {d}",
        "m_price": "ذهب عيار 24 الآن {p:,.2f} ريال/جرام ({c:+.1f}% منذ أمس)",
        "m_pl": "لديك {g:,.0f} جرام بسعر شراء {b:,.2f}: {pl:+,.0f} ريال ({pp:+.1f}%)",
        "m_range": "نطاق السنتين {lo:,.0f} - {hi:,.0f} - السعر اليوم أعلى من {r}% من الأيام",
        "m_signal": "الإشارة: {v}",
        "h_line": "{i} {n}: {p:,.2f} {c} (أمس {y:,.2f}، {cp:+.1f}%)",
        "h_pl": " - {q:,.0f} {qn} بسعر شراء {b:,.2f} - الربح {pl:+,.0f} {c} ({pp:+.1f}%)",
        "h_grams": "جرام", "h_shares": "سهم", "h_total": "الإجمالي: ",
        "mv_title": "{a} سعر ذهب عيار 24 تغيّر {d:+.2f} ريال",
        "mv_line": "من {old:,.2f} إلى {new:,.2f} ريال/جرام (ديوان الذهب)",
        "stance_buy_zone": "تاريخياً منطقة شراء", "stance_accumulate": "تاريخياً يميل للإيجابية",
        "stance_hold": "تاريخياً محايد - احتفظ / انتظر",
        "stance_take_profit": "تاريخياً يميل للسلبية - منطقة جني أرباح",
        "stance_sell_zone": "تاريخياً منطقة بيع",
        "conf_low": "ثقة منخفضة", "conf_medium": "ثقة متوسطة", "conf_high": "ثقة عالية",
        "bh_hist60": "تاريخياً، في ظروف مشابهة كان السعر أعلى بعد 60 يوم تداول في {v}% من الحالات",
        "bh_med60": "الحركة الوسيطة بعد 60 يوم تداول من أيام مشابهة: {v:+}%",
        "bh_trend_up": "اتجاه صاعد (فوق متوسط 50 و200 يوم)",
        "bh_trend_down": "اتجاه هابط (تحت متوسط 50 و200 يوم)", "bh_trend_side": "لا يوجد اتجاه واضح",
        "bh_above_avg": "أعلى بـ {v}% من متوسط 200 يوم (مرتفع جداً)", "bh_below_avg": "أقل بـ {v}% من متوسط 200 يوم",
        "bh_rsi_high": "مؤشر RSI عند {v} = تشبّع شرائي", "bh_rsi_low": "مؤشر RSI عند {v} = تشبّع بيعي",
        "bh_range_high": "أعلى من {v}% من أيام السنة الماضية", "bh_range_low": "أقل من {v}% من أيام السنة الماضية",
        "bh_mom_strong": "صعود قوي خلال 60 يوماً ({v:+}%)", "bh_mom_weak": "ضعف خلال آخر 60 يوماً ({v:+}%)",
        "bh_season_good": "هذا الشهر كان متوسطه تاريخياً {v:+}%",
        "bh_season_bad": "هذا الشهر كان متوسطه تاريخياً {v:+}%",
        "bh_near_res": "مقاومة (قمة سابقة) أعلى بـ {v}%", "bh_near_sup": "دعم (قاع سابق) أقل بـ {v}%",
        "bh_drawdown": "أقل بـ {v}% من أعلى سعر له", "bh_vol_high": "تذبذب أعلى من المعتاد ({v}% سنوياً)",
        "bh_pos_gain": "ربحك يعادل {v} ضعف الحركة المعتادة خلال 60 يوماً",
        "bh_pos_breakeven": "يحتاج السعر {v:+}% ليصل إلى سعر شرائك",
        "bh_short_history": "تاريخ {v} يوم فقط - غير كافٍ للتحليل",
        "ol_disclaimer": "احتمالات مبنية على تاريخ سعر هذا الأصل وعدّ بسيط لكلمات العناوين - ليست نصيحة مالية ولا توصية شخصية. الماضي لا يضمن المستقبل.",
        "ol_short_history": "تاريخ الأسعار غير كافٍ للتوقع",
        "ol_lean_favourable": "الاحتمالات التاريخية تميل للصعود", "ol_lean_neutral": "الاحتمالات التاريخية متوازنة",
        "ol_lean_unfavourable": "الاحتمالات التاريخية تميل للهبوط",
        "ol_odds_up": "احتمال أن يكون السعر أعلى: بعد أسبوع {w}%، بعد شهر {m}%، بعد 3 أشهر {q}%",
        "ol_range_1m": "النطاق المرجّح بعد شهر (80% من المحاكاة): {lo:,.2f} - {hi:,.2f}",
        "ol_r_behaviour": "درجة السلوك {v:+}",
        "ol_r_fc_up21": "{v}% من المحاكاة تنتهي أعلى بعد شهر",
        "ol_r_fc_up63": "{v}% من المحاكاة تنتهي أعلى بعد 3 أشهر",
        "ol_r_fc_dip5": "احتمال {v}% أن يلمس -5% خلال شهر",
        "ol_r_fc_pop5": "احتمال {v}% أن يلمس +5% خلال شهر",
        "ol_r_fc_buy63": "احتمال {v}% أن يكون فوق سعر شرائك بعد 3 أشهر",
        "ol_r_news_positive": "{v} عناوين إيجابية مؤخراً", "ol_r_news_negative": "{v} عناوين سلبية مؤخراً",
        "news_positive": "إيجابي", "news_negative": "سلبي", "news_neutral": "محايد",
        "news_title": "آخر الأخبار", "news_none": "لا توجد أخبار حديثة",
        "fc_title": "نطاق الأسعار المحتملة", "fc_prob_up": "احتمال الارتفاع", "fc_touch_up5": "يلمس +5%",
        "fc_touch_dn5": "يلمس -5%", "fc_above_buy": "فوق سعر الشراء",
        "bh_disclaimer": "إحصاءات تاريخية فقط وليست نصيحة مالية. الماضي لا يضمن المستقبل.",
    },
}


META_API = "https://graph.facebook.com/v25.0/{phone_id}/messages"
META_MEDIA = "https://graph.facebook.com/v25.0/{phone_id}/media"
# The new gold_report template (one {{1}} placeholder) is sent by default; the META_WA_TEMPLATE
# secret can name another one. If it isn't approved yet (Meta error 132001), gold_alert is used.
META_TEMPLATE = os.environ.get("META_WA_TEMPLATE", "").strip() or "gold_report"
META_FALLBACK_TEMPLATE = "gold_alert"
TEMPLATE_NOT_FOUND = 132001
# Same text as gold_report plus an image header for the chart. Tried first whenever there is a
# chart; until Meta approves it (132001) the templates above are used. Created by --create-template.
META_CHART_TEMPLATE = "gold_report_chart"
CHART_TEMPLATE_BODY = ("تحديث تنبيه سعر الذهب الذي قمت بإعداده في حسابك على Gold Hunt: {{1}}"
                       " - يمكنك تعديل مستويات التنبيه من الإعدادات.")
CHART_TEMPLATE_EXAMPLE = "ذهب عيار 24 الآن 395.64 ريال/جرام (+0.4% منذ أمس)"
# Morning report: chart image on top, one line per holding. Template values can't contain new
# lines, so each holding gets its own placeholder and the line breaks live in the template itself.
META_REPORT_TEMPLATE = "gold_portfolio"
REPORT_SLOTS = 6
REPORT_TEMPLATE_BODY = (
    "☀️ صباح الخير - تقرير محفظتك على Gold Hunt ليوم {{1}}\n\n"
    + "".join(f"{{{{{i}}}}}\n\n" for i in range(2, REPORT_SLOTS + 2))
    + f"💰 الإجمالي: {{{{{REPORT_SLOTS + 2}}}}}\n\n"
    "السعر مقارنة بأمس، والكمية وسعر الشراء والربح لكل استثمار. "
    "الصورة تعرض آخر 30 يوماً. يمكنك تعديل المحفظة من الإعدادات.")
REPORT_TEMPLATE_EXAMPLE = (
    ["2026-11-06"]
    + ["🔴 ذهب عيار 24: 493.83 ريال (أمس 500.60، -1.4%) - 600 جرام بسعر شراء 501.00 - الربح -4,302 ريال (-1.4%)"]
    + ["🟢 NVIDIA: 191.95 دولار (أمس 181.60، +5.7%) - 10 سهم بسعر شراء 120.00 - الربح +719 دولار (+60.0%)"] * (REPORT_SLOTS - 1)
    + ["-4,436 ريال (-1.5%)، +719 دولار (+60.0%)"])


# ---------------------------------------------------------------- chart
def price_chart(a, days=30, ref=None):
    """PNG chart (bytes) of the last `days` closing prices, with the buy price and the
    last alert price marked. None if matplotlib is missing or there's too little data."""
    try:
        import io
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
    except ImportError:
        print("Chart skipped (matplotlib not installed)")
        return None
    dates = pd.to_datetime(a["series"]["dates"])
    keep = dates >= dates[-1] - pd.Timedelta(days=days)  # calendar days, not trading days
    dates, close = dates[keep], [c for c, k in zip(a["series"]["close"], keep) if k]
    if len(close) < 2:
        return None
    up = close[-1] >= close[0]
    color = "#1f9d55" if up else "#d64545"
    fig, ax = plt.subplots(figsize=(8, 4.2), dpi=150)
    fig.patch.set_facecolor("#ffffff")
    ax.plot(dates, close, color=color, linewidth=2.2)
    ax.fill_between(dates, close, min(close), color=color, alpha=0.10)
    ax.scatter([dates[-1]], [close[-1]], color=color, s=40, zorder=3)
    ax.annotate(f"{close[-1]:,.2f}", (dates[-1], close[-1]), textcoords="offset points",
                xytext=(-8, 12), ha="right", fontsize=11, fontweight="bold", color=color)
    lo, hi = min(close), max(close)
    for level, label, style in ((a.get("buy"), "Buy", "--"), (ref, "Last alert", ":")):
        if level and lo - (hi - lo) * 0.6 <= level <= hi + (hi - lo) * 0.6:  # only if near the chart
            ax.axhline(level, color="#6b6b6b", linestyle=style, linewidth=1)
            ax.annotate(f"{label} {level:,.2f}", (dates[0], level), textcoords="offset points",
                        xytext=(2, 4), fontsize=8, color="#6b6b6b")
    change = (close[-1] / close[0] - 1) * 100
    unit = "SAR/gram" if a["key"] == "GOLD" else a["unit"]
    name = "Gold 24K" if a["key"] == "GOLD" else a["name"]
    ax.set_title(f"{name} - last {days} days  ({change:+.1f}%)", fontsize=13, loc="left")
    ax.set_ylabel(unit)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    ax.grid(axis="y", alpha=0.25)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    fig.text(0.99, 0.01, "Gold Hunt - " + dt.datetime.now(RIYADH).strftime("%Y-%m-%d %H:%M") + " Riyadh",
             ha="right", fontsize=7, color="#8a8a8a")
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    return buf.getvalue()


def portfolio_chart(results, days=30):
    """One PNG with a small 30-day chart per holding (WhatsApp templates carry one image)."""
    try:
        import io
        import math
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
    except ImportError:
        print("Chart skipped (matplotlib not installed)")
        return None
    cols = 2 if len(results) > 1 else 1
    rows = math.ceil(len(results) / cols)
    fig, axes = plt.subplots(rows, cols, figsize=(5.2 * cols, 2.9 * rows), dpi=130, squeeze=False)
    fig.patch.set_facecolor("#ffffff")
    for ax, a in zip(axes.flat, results):
        dates = pd.to_datetime(a["series"]["dates"])
        keep = dates >= dates[-1] - pd.Timedelta(days=days)
        d, close = dates[keep], [c for c, k in zip(a["series"]["close"], keep) if k]
        if len(close) < 2:
            ax.set_visible(False)
            continue
        color = "#1f9d55" if close[-1] >= close[0] else "#d64545"
        ax.plot(d, close, color=color, linewidth=1.8)
        ax.fill_between(d, close, min(close), color=color, alpha=0.10)
        lo, hi = min(close), max(close)
        if a.get("buy") and lo - (hi - lo) * 0.6 <= a["buy"] <= hi + (hi - lo) * 0.6:
            ax.axhline(a["buy"], color="#6b6b6b", linestyle="--", linewidth=0.9)
            ax.annotate(f"Buy {a['buy']:,.2f}", (d[0], a["buy"]), textcoords="offset points",
                        xytext=(2, 3), fontsize=7, color="#6b6b6b")
        name = "Gold 24K" if a["key"] == "GOLD" else a["name"]
        unit = "SAR/g" if a["key"] == "GOLD" else a["currency"]
        pl = f"   P/L {a['pl_pct']:+.1f}%" if a.get("pl_pct") is not None else ""
        ax.set_title(f"{name}  {close[-1]:,.2f} {unit}  ({(close[-1] / close[0] - 1) * 100:+.1f}%){pl}",
                     fontsize=9.5, loc="left", color="#222222")
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
        ax.tick_params(labelsize=7)
        ax.grid(axis="y", alpha=0.25)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
    for ax in list(axes.flat)[len(results):]:
        ax.set_visible(False)
    fig.text(0.99, 0.005, f"Gold Hunt - last {days} days - " + dt.datetime.now(RIYADH).strftime("%Y-%m-%d %H:%M")
             + " Riyadh", ha="right", fontsize=7, color="#8a8a8a")
    fig.tight_layout(rect=(0, 0.02, 1, 1))
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    return buf.getvalue()


def upload_chart(cfg, png):
    """Upload the chart to Meta once; returns its media id (or None)."""
    try:
        r = requests.post(META_MEDIA.format(phone_id=cfg["phone_id"]), timeout=60,
                          headers={"Authorization": "Bearer " + cfg["token"]},
                          data={"messaging_product": "whatsapp", "type": "image/png"},
                          files={"file": ("gold_chart.png", png, "image/png")})
        print(f"  Chart upload: HTTP {r.status_code}")
        return r.json().get("id") if r.ok else None
    except Exception as e:
        print(f"  Chart upload: FAILED ({type(e).__name__})")
        return None


def meta_config():
    """WhatsApp Cloud API (Meta) settings from GitHub secrets / environment, or None.
    ONLY_TO (the "only to" box on the Run workflow form) sends to that one number instead of everyone."""
    token = os.environ.get("META_WA_TOKEN", "").strip()
    phone_id = os.environ.get("META_WA_PHONE_ID", "").strip()
    to = [n.strip().lstrip("+") for n in os.environ.get("META_WA_TO", "").replace("\n", ",").split(",") if n.strip()]
    if os.environ.get("ONLY_TO", "").strip():
        to = [os.environ["ONLY_TO"].strip().lstrip("+")]
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


def send_meta(cfg, text, chart=None, slots=None):
    """Send through the approved template. Template values can't hold new lines or tabs,
    or more than 4 spaces in a row, so the alert is flattened into one line.
    A chart (PNG bytes) goes in the template's image header; if the template has none,
    it follows as a separate image message."""
    value = " | ".join(part.strip() for part in text.split("\n") if part.strip())
    value = " ".join(value.split())[:1000]
    media_id = upload_chart(cfg, chart) if chart else None

    def call(body):
        r = requests.post(META_API.format(phone_id=cfg["phone_id"]), json=body, timeout=30,
                          headers={"Authorization": "Bearer " + cfg["token"]})
        code = None if r.ok else r.json().get("error", {}).get("code")
        return r, code

    def post(number, template, image):
        components = [{"type": "body", "parameters": [{"type": "text", "text": value}]}]
        if image:
            components.insert(0, {"type": "header", "parameters": [{"type": "image", "image": {"id": image}}]})
        return call({"messaging_product": "whatsapp", "to": number, "type": "template",
                     "template": {"name": template, "language": {"code": "ar"},  # templates exist in Arabic only
                                  "components": components}})

    delivered = False
    for number in cfg["to"]:
        masked = number[-4:].rjust(len(number), "*")
        try:
            if slots and media_id:  # multi-line report with the chart on top
                r, code = call({"messaging_product": "whatsapp", "to": number, "type": "template",
                                "template": {"name": META_REPORT_TEMPLATE, "language": {"code": "ar"}, "components": [
                                    {"type": "header", "parameters": [{"type": "image", "image": {"id": media_id}}]},
                                    {"type": "body", "parameters": [
                                        {"type": "text", "text": " ".join(v.split())[:300]} for v in slots]}]}})
                if r.ok:
                    delivered = True
                    print(f"  WhatsApp (Meta report) -> {masked}: HTTP {r.status_code} with chart")
                    continue
                print(f"  Report template not usable yet: HTTP {r.status_code} {code}")
            templates = ([META_CHART_TEMPLATE] if media_id else []) + [META_TEMPLATE, META_FALLBACK_TEMPLATE]
            for template in dict.fromkeys(templates):  # in order, without repeats
                r, code = post(number, template, media_id)
                # Try the next one if this template isn't approved yet, or the chart template failed
                if r.ok or not (code == TEMPLATE_NOT_FOUND or template == META_CHART_TEMPLATE):
                    break
            # Rejected with the image (template has no image header, or Meta reports it as a
            # parameter problem such as 132018): send the text alone and the chart separately
            separate = bool(media_id) and not r.ok and template != META_CHART_TEMPLATE
            if separate:
                r, code = post(number, template, None)
            delivered |= r.ok
            print(f"  WhatsApp (Meta) -> {masked}: HTTP {r.status_code}{'' if r.ok else f' {code}'}"
                  + (" with chart" if media_id and r.ok and not separate else ""))
            if separate and r.ok:
                # Works when the recipient wrote to the business number in the last 24 hours
                ri, ci = call({"messaging_product": "whatsapp", "to": number, "type": "image",
                               "image": {"id": media_id}})
                print(f"  Chart image -> {masked}: HTTP {ri.status_code}{'' if ri.ok else f' {ci}'}")
        except Exception as e:
            print(f"  WhatsApp (Meta) -> {masked}: FAILED ({type(e).__name__})")
    return delivered


def create_chart_template(cfg, sample_png, name=META_CHART_TEMPLATE):
    """One-time setup: create the gold_report_chart template (Arabic, Utility, image header)
    on the WhatsApp Business Account, or report its status if it already exists.
    Prints only status lines - no token, numbers or prices."""
    graph = "https://graph.facebook.com/v25.0/"
    auth = {"Authorization": "Bearer " + cfg["token"]}

    def show_error(r, step):
        e = r.json().get("error", {}) if r.content else {}
        print(f"META_ERROR {step}: HTTP {r.status_code} code {e.get('code')} subcode {e.get('error_subcode')}")
        msg = " ".join(str(e.get("error_user_msg") or e.get("message") or "").split())[:300]
        if msg:
            print(f"META_MSG {msg}")

    # Business account and app come from the token itself (or the META_WA_WABA_ID secret)
    r = requests.get(graph + "debug_token", timeout=30,
                     params={"input_token": cfg["token"], "access_token": cfg["token"]})
    if not r.ok:
        show_error(r, "debug_token")
        return False
    data = r.json().get("data", {})
    app_id = data.get("app_id")
    waba = os.environ.get("META_WA_WABA_ID", "").strip()
    scopes = data.get("scopes") or [g["scope"] for g in data.get("granular_scopes", [])]
    print(f"TEMPLATE_TOKEN type={data.get('type')} scopes={','.join(scopes)}")
    if not waba:
        for scope in data.get("granular_scopes", []):
            if scope.get("scope") == "whatsapp_business_management" and scope.get("target_ids"):
                waba = scope["target_ids"][0]
    if not waba:  # ask the businesses the token can see for their WhatsApp accounts
        r = requests.get(graph + "me/businesses", headers=auth, timeout=30, params={"fields": "id"})
        for biz in (r.json().get("data", []) if r.ok else []):
            for edge in ("owned_whatsapp_business_accounts", "client_whatsapp_business_accounts"):
                rw = requests.get(graph + f"{biz['id']}/{edge}", headers=auth, timeout=30,
                                  params={"fields": "id,phone_numbers{id}"})
                for acc in (rw.json().get("data", []) if rw.ok else []):
                    phones = [n.get("id") for n in acc.get("phone_numbers", {}).get("data", [])]
                    if not waba or cfg["phone_id"] in phones:
                        waba = acc["id"]
        if not r.ok:
            show_error(r, "me/businesses")
    if not waba:
        print("META_ERROR token has no whatsapp_business_management access to a business account"
              " (add it to the token, or set the META_WA_WABA_ID secret)")
        return False

    r = requests.get(graph + f"{waba}/message_templates", headers=auth, timeout=30,
                     params={"name": name, "fields": "name,status,category,language"})
    if not r.ok:
        show_error(r, "list_templates")
        return False
    for t in r.json().get("data", []):
        if t.get("name") == name:
            print(f"TEMPLATE_EXISTS {name} {t.get('status')} {t.get('category')} {t.get('language')}")
            return True

    # The sample header image has to be uploaded first (Resumable Upload API -> handle)
    r = requests.post(graph + f"{app_id}/uploads", headers=auth, timeout=30,
                      params={"file_name": "gold_chart.png", "file_length": len(sample_png),
                              "file_type": "image/png"})
    if not r.ok:
        show_error(r, "upload_session")
        return False
    r = requests.post(graph + r.json()["id"], data=sample_png, timeout=60,
                      headers={"Authorization": "OAuth " + cfg["token"], "file_offset": "0"})
    if not r.ok:
        show_error(r, "upload_image")
        return False
    handle = r.json()["h"]

    body = {
        "name": name, "language": "ar", "category": "UTILITY",
        "components": [
            {"type": "HEADER", "format": "IMAGE", "example": {"header_handle": [handle]}},
            {"type": "BODY", "text": CHART_TEMPLATE_BODY,
             "example": {"body_text": [[CHART_TEMPLATE_EXAMPLE]]}},
        ],
    }
    if name == META_REPORT_TEMPLATE:
        body["components"][1] = {"type": "BODY", "text": REPORT_TEMPLATE_BODY,
                                 "example": {"body_text": [REPORT_TEMPLATE_EXAMPLE]}}
        body["components"].append({"type": "BUTTONS", "buttons": [
            {"type": "URL", "text": "شارت الذهب على TradingView",
             "url": "https://www.tradingview.com/chart/?symbol=TVC:GOLD"}]})
    r = requests.post(graph + f"{waba}/message_templates", headers=auth, json=body, timeout=30)
    if not r.ok:
        show_error(r, "create_template")
        return False
    j = r.json()
    print(f"TEMPLATE_CREATED {name} {j.get('status')} {j.get('category')}")
    return True


def send_whatsapp(phones, text, chart=None, slots=None):
    """Send to every recipient; return True if at least one message was delivered.
    Uses Meta's WhatsApp Cloud API when configured (with the chart image),
    otherwise CallMeBot numbers (text only)."""
    meta = meta_config()
    if meta:
        return send_meta(meta, text, chart, slots)
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
    keys, lines, alerted = [], [], []
    for a in results:
        pl = (T["pl"].format(pl=a["pl"], c=T.get("cur_" + a["currency"], a["currency"]), pp=a["pl_pct"])
              if a["pl"] is not None else "")
        for kind, msg in find_alerts(a, cfg_alerts):
            k = f"{a['key']}:{kind}"
            if k not in state:  # each alert only once per day
                keys.append(k)
                lines.append(msg + pl)
                if a not in alerted:
                    alerted.append(a)
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
    # Chart of gold if it triggered an alert, otherwise of the first asset that did
    chart_of = next((a for a in alerted if a["key"] == "GOLD"), alerted[0])
    # Only remember alerts that actually went out, so failed ones retry next check
    if send_whatsapp(phones, text, price_chart(chart_of)):
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
    if send_whatsapp(phones, text, price_chart(a, ref=ref)):  # only move the reference once the alert went out
        GOLD_REF.write_text(json.dumps({"price": price}))


def tradingview_url(a):
    """Link to the holding's live TradingView chart."""
    if a["key"] == "GOLD":
        sym = "TVC:GOLD"
    elif a["ticker"].endswith(".SR"):
        sym = "TADAWUL:" + a["ticker"][:-3]
    else:
        sym = a["ticker"]  # TradingView finds the US exchange by itself
    return "https://www.tradingview.com/chart/?symbol=" + urllib.parse.quote(sym, safe=":")


def holding_line(a, T):
    """One line per holding: today vs yesterday, what you hold at what price, profit/loss."""
    name = T["gold_name"] if a["key"] == "GOLD" else a["name"]
    c = T.get("cur_" + a["currency"], a["currency"])
    up = (a["pl"] if a["pl"] is not None else a["change_pct"]) >= 0
    line = T["h_line"].format(i="🟢" if up else "🔴", n=name, p=a["price"], c=c, y=a["prev"], cp=a["change_pct"])
    if a["pl"] is not None:
        qty = T["h_grams"] if a["key"] == "GOLD" else T["h_shares"]
        line += T["h_pl"].format(q=a["qty"], qn=qty, b=a["buy"], pl=a["pl"], pp=a["pl_pct"], c=c)
    return line


def morning_report(assets, cfg_alerts, phones, send=True):
    """Daily summary of every holding (sent by the 8:00 AM Riyadh schedule) with one chart image
    that has a small 30-day chart per holding, and TradingView links as far as Meta's length allows."""
    T = TEXT[cfg_alerts["lang"]]
    results = []
    for a in assets:
        try:
            results.append(analyse(a, fetch(a)))
        except Exception as e:
            print(f"FAILED_ASSET {type(e).__name__}")
    if not results:
        return
    day = dt.datetime.now(RIYADH).strftime("%Y-%m-%d")
    lines = [T["morning"].format(d=day)]
    holdings = [holding_line(a, T) for a in results]
    lines += holdings
    totals = {}
    for a in results:
        if a["pl"] is not None:
            t = totals.setdefault(a["currency"], [0.0, 0.0])
            t[0] += a["pl"]
            t[1] += a["buy"] * a["qty"]
    total = T["sep"].join(f"{pl:+,.0f} {T.get('cur_' + c, c)} ({pl / cost * 100:+.1f}%)"
                          for c, (pl, cost) in totals.items() if cost) or "-"
    lines.append(T["h_total"] + total)
    # One placeholder per holding in the report template; extra holdings share the last one
    spots = holdings[:REPORT_SLOTS - 1] + [" | ".join(holdings[REPORT_SLOTS - 1:]) or "-"]
    spots += ["-"] * (REPORT_SLOTS - len(spots))
    slots = [day] + spots + [total]
    # Links last, only as many as fit in the ~1000-character template value
    links, size = [], len(" | ".join(lines))
    for a in results:
        link = f"{T['gold_name'] if a['key'] == 'GOLD' else a['ticker']}: {tradingview_url(a)}"
        if size + len(link) + 3 > 990:
            break
        links.append(link)
        size += len(link) + 3
    text = "\n".join(lines + links)
    print(text)
    if send:
        send_whatsapp(phones, text, portfolio_chart(results), slots)


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
        gold = next(a for a in assets if a["key"] == "GOLD")
        try:
            chart = price_chart(analyse(gold, fetch(gold)))
        except Exception as e:
            print(f"Chart skipped ({type(e).__name__})")
            chart = None
        send_whatsapp(phones, TEXT[cfg_alerts["lang"]]["test"], chart)
        return
    if "--chart" in sys.argv:
        gold = next(a for a in assets if a["key"] == "GOLD")
        png = price_chart(analyse(gold, fetch(gold)))
        if png:
            (HERE / "chart.png").write_bytes(png)
            print(f"Chart: {HERE / 'chart.png'}")
        return
    if "--create-template" in sys.argv:
        cfg = meta_config()
        if not cfg:
            print("Meta WhatsApp is not configured (META_WA_TOKEN / META_WA_PHONE_ID / META_WA_TO)")
            sys.exit(1)
        gold = next(a for a in assets if a["key"] == "GOLD")
        png = price_chart(analyse(gold, fetch(gold)))
        ok = [create_chart_template(cfg, png, n) for n in (META_CHART_TEMPLATE, META_REPORT_TEMPLATE)]
        if not all(ok):
            sys.exit(1)
        return
    if "--hello" in sys.argv:
        cfg = meta_config()
        if not cfg:
            print("Meta WhatsApp is not configured (META_WA_TOKEN / META_WA_PHONE_ID / META_WA_TO)")
            sys.exit(1)
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
