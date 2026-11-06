"""Outlook for one asset: latest news with a simple keyword mood, a Monte Carlo range of
possible prices built from the asset's own history, and a summary that combines both with
behaviour(). Probabilities from history only - not financial advice.

Everything returned is JSON-safe (no NaN / inf). Nothing here may crash the app: news errors
give an empty news block, and short histories give an empty forecast."""
import concurrent.futures as cf
import datetime as dt
import json
import math
import re
import time
from pathlib import Path

import numpy as np
import pandas as pd

NEWS_TTL = 30 * 60          # seconds a cached headline list stays fresh
NEWS_TIMEOUT = 6            # seconds per ticker before giving up
NEWS_MAX = 10
MC_PATHS = 5000
MC_BLOCK = 10               # trading days per bootstrap block (keeps short-term clustering)
MC_MAX_H = 126              # ~6 months of trading days
MC_SEED = 20240601
VOL_WIN = 20
DRIFT_SHRINK = 0.5

# ---------------------------------------------------------------- news
POS_WORDS = {
    "surge": 1, "surges": 1, "soar": 1, "soars": 1, "rally": 1, "rallies": 1, "jump": 1, "jumps": 1,
    "gain": 0.6, "gains": 0.6, "rise": 0.6, "rises": 0.6, "climb": 0.6, "climbs": 0.6, "record": 0.6,
    "high": 0.3, "highs": 0.5, "beat": 1, "beats": 1, "upgrade": 1, "upgraded": 1, "outperform": 1,
    "bullish": 1, "strong": 0.6, "growth": 0.5, "profit": 0.5, "boost": 0.7, "boosts": 0.7,
    "rebound": 0.8, "rebounds": 0.8, "recover": 0.6, "recovery": 0.6, "buy": 0.4, "positive": 0.6,
    "optimism": 0.8, "optimistic": 0.8, "tops": 0.6, "wins": 0.7, "win": 0.5, "approval": 0.6,
    "safe-haven": 0.4, "demand": 0.3, "dividend": 0.4, "expands": 0.5, "partnership": 0.5,
}
NEG_WORDS = {
    "plunge": 1, "plunges": 1, "crash": 1, "crashes": 1, "tumble": 1, "tumbles": 1, "slump": 1,
    "slumps": 1, "fall": 0.6, "falls": 0.6, "drop": 0.6, "drops": 0.6, "decline": 0.6, "declines": 0.6,
    "slide": 0.6, "slides": 0.6, "sink": 0.7, "sinks": 0.7, "loss": 0.6, "losses": 0.6, "miss": 0.9,
    "misses": 0.9, "downgrade": 1, "downgraded": 1, "underperform": 1, "bearish": 1, "weak": 0.6,
    "weakness": 0.6, "sell-off": 0.9, "selloff": 0.9, "fear": 0.6, "fears": 0.6, "risk": 0.3,
    "risks": 0.3, "warning": 0.7, "warns": 0.7, "lawsuit": 0.7, "probe": 0.6, "cut": 0.4, "cuts": 0.4,
    "layoffs": 0.7, "recession": 0.8, "concern": 0.5, "concerns": 0.5, "volatile": 0.3, "lower": 0.4,
    "pressure": 0.4, "slowdown": 0.7, "tariff": 0.3, "tariffs": 0.3, "bankruptcy": 1, "fraud": 1,
}
NEGATORS = {"not", "no", "never", "without", "fails", "failed"}


def headline_sentiment(text):
    """Keyword finance sentiment in -1..1 (simple and transparent, not a language model)."""
    words = re.findall(r"[a-z][a-z\-']*", (text or "").lower())
    s = 0.0
    hits = 0
    for i, w in enumerate(words):
        val = POS_WORDS.get(w, 0) - NEG_WORDS.get(w, 0)
        if val:
            if i and words[i - 1] in NEGATORS:
                val = -val
            s += val
            hits += 1
    if not hits:
        return 0.0
    return round(max(-1.0, min(1.0, s / (1 + 0.5 * hits) * 1.2)), 2)


def _label(score):
    return "positive" if score >= 0.15 else "negative" if score <= -0.15 else "neutral"


def _parse_item(it):
    """yfinance has two news formats (old flat, new {'content': {...}})."""
    c = it.get("content") if isinstance(it.get("content"), dict) else None
    if c:
        title = c.get("title")
        pub = (c.get("provider") or {}).get("displayName")
        link = ((c.get("canonicalUrl") or {}).get("url") or (c.get("clickThroughUrl") or {}).get("url"))
        when = c.get("pubDate") or c.get("displayTime")
    else:
        title, pub, link = it.get("title"), it.get("publisher"), it.get("link")
        ts = it.get("providerPublishTime")
        when = (dt.datetime.fromtimestamp(ts, dt.timezone.utc).isoformat(timespec="seconds")
                if isinstance(ts, (int, float)) else None)
    if not title:
        return None
    sc = headline_sentiment(title + " " + str((c or {}).get("summary") or "")[:300])
    return {"title": str(title), "publisher": pub and str(pub), "link": link and str(link),
            "time": when and str(when), "sentiment": sc, "label": _label(sc)}


def _fetch_news(ticker):
    import yfinance as yf
    return yf.Ticker(ticker).news or []


_pool = cf.ThreadPoolExecutor(max_workers=4, thread_name_prefix="news")


def news(tickers, cache_file):
    """Latest headlines for these tickers (merged, newest first), cached for 30 minutes."""
    cache_file = Path(cache_file)
    try:
        cache = json.loads(cache_file.read_text(encoding="utf-8"))
    except Exception:
        cache = {}
    now = time.time()
    items, errors, changed = [], [], False
    futures = {}
    for t in tickers:
        hit = cache.get(t)
        if hit and now - hit.get("t", 0) < NEWS_TTL:
            items += hit.get("items", [])
        else:
            futures[t] = _pool.submit(_fetch_news, t)
    for t, fut in futures.items():
        try:
            raw = fut.result(timeout=NEWS_TIMEOUT)
            got = [p for p in (_parse_item(x) for x in raw if isinstance(x, dict)) if p]
            cache[t] = {"t": now, "items": got}
            changed = True
            items += got
        except Exception as e:  # Yahoo down / timeout / format change: keep last cached copy
            errors.append(f"{t}: {type(e).__name__}")
            if cache.get(t):
                items += cache[t].get("items", [])
            else:  # don't retry a failing ticker on every page load
                cache[t] = {"t": now - NEWS_TTL + 300, "items": []}
                changed = True
    if changed:
        try:
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            cache_file.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass
    seen, uniq = set(), []
    for it in sorted(items, key=lambda x: x.get("time") or "", reverse=True):
        k = it["title"].strip().lower()
        if k not in seen:
            seen.add(k)
            uniq.append(it)
    uniq = uniq[:NEWS_MAX]
    counts = {"positive": 0, "negative": 0, "neutral": 0}
    for it in uniq:
        counts[it["label"]] += 1
    score = round(float(np.mean([it["sentiment"] for it in uniq])), 2) if uniq else 0.0
    return {"tickers": list(tickers), "items": uniq, "counts": counts, "score": score,
            "mood": _label(score) if uniq else "neutral", "count": len(uniq),
            "error": "; ".join(errors) or None, "cached_minutes": NEWS_TTL // 60,
            "method": "keyword"}


# ---------------------------------------------------------------- forecast
def _horizons():
    rest = np.unique(np.round(np.linspace(12, MC_MAX_H, 40)).astype(int))
    return list(range(1, 11)) + [int(h) for h in rest]


def _future_dates(last, n, saudi):
    mask = "Sun Mon Tue Wed Thu" if saudi else "Mon Tue Wed Thu Fri"
    d = pd.bdate_range(last + pd.Timedelta(days=1), periods=n, freq="C", weekmask=mask)
    return [x.strftime("%Y-%m-%d") for x in d]


def _r(v, nd=2):
    return None if v is None or not math.isfinite(float(v)) else round(float(v), nd)


def forecast(c, buy=None, saudi=False):
    """Block-bootstrap Monte Carlo of daily log returns. Blocks whose starting volatility looks
    like today's get more weight (mild regime conditioning). Volatility at a block's start uses
    only returns up to that day; all blocks are from the past, so there is no look-ahead."""
    c = c.dropna().astype(float)
    c = c[c > 0]
    lr = np.diff(np.log(c.values))
    if len(lr) < 260:
        return None
    price = float(c.iloc[-1])
    # Halve the historical drift: a stock that tripled in the past should not be assumed to keep
    # doing so. Shape and volatility of the moves stay as they were.
    lr = lr - DRIFT_SHRINK * lr.mean()
    vol = pd.Series(lr).rolling(VOL_WIN).std().values           # vol[i] uses lr[i-19..i]
    v_now = float(vol[-1])
    starts = np.arange(VOL_WIN, len(lr) - MC_BLOCK + 1)           # block = lr[i..i+9], vol known at i-1
    v_start = vol[starts - 1]
    ok = np.isfinite(v_start) & (v_start > 0)
    starts, v_start = starts[ok], v_start[ok]
    d = np.log(v_start / v_now) if v_now > 0 else np.zeros(len(starts))
    w = 0.5 + 0.5 * np.exp(-0.5 * (d / 0.4) ** 2)                 # floor 0.5 keeps it mild
    w /= w.sum()
    eff_n = float(1 / np.sum(w ** 2))

    rng = np.random.default_rng(MC_SEED)
    nb = -(-MC_MAX_H // MC_BLOCK)
    pick = rng.choice(starts, size=(MC_PATHS, nb), p=w)
    idx = (pick[:, :, None] + np.arange(MC_BLOCK)).reshape(MC_PATHS, -1)[:, :MC_MAX_H]
    cum = np.cumsum(lr[idx], axis=1)                               # log(price_t / price_0)
    run_max = np.maximum.accumulate(cum, axis=1)
    run_min = np.minimum.accumulate(cum, axis=1)
    up5, dn5 = math.log(1.05), math.log(0.95)
    lbuy = math.log(buy / price) if buy else None

    hs = _horizons()
    dates = _future_dates(c.index[-1], MC_MAX_H, saudi)
    rows = []
    for h in hs:
        x = cum[:, h - 1]
        p10, p50, p90 = np.exp(np.percentile(x, [10, 50, 90])) * price
        rows.append({"date": dates[h - 1], "h": h, "prob_up": _r((x > 0).mean() * 100, 1),
                     "p10": _r(p10), "p50": _r(p50), "p90": _r(p90),
                     "touch_up5": _r((run_max[:, h - 1] >= up5).mean() * 100, 1),
                     "touch_dn5": _r((run_min[:, h - 1] <= dn5).mean() * 100, 1),
                     "prob_above_buy": _r((x > lbuy).mean() * 100, 1) if lbuy is not None else None})
    mu = float(np.average(lr[starts[:, None] + np.arange(MC_BLOCK)].mean(axis=1), weights=w))
    return {"method": "block_bootstrap", "paths": MC_PATHS, "block_days": MC_BLOCK, "seed": MC_SEED, "drift_shrink": DRIFT_SHRINK,
            "history_days": int(len(lr)), "price": _r(price), "buy": _r(buy) if buy else None,
            "vol_now_ann_pct": _r(v_now * math.sqrt(252) * 100, 1),
            "vol_hist_ann_pct": _r(float(np.std(lr, ddof=1)) * math.sqrt(252) * 100, 1),
            "drift_ann_pct": _r((math.exp(mu * 252) - 1) * 100, 1),
            "effective_samples": int(eff_n), "week": "sun_thu" if saudi else "mon_fri", "rows": rows}


# ---------------------------------------------------------------- summary
def _row(fc, h):
    if not fc:
        return None
    return min(fc["rows"], key=lambda r: abs(r["h"] - h))


def summary(bh, fc, nw):
    bh_score = (bh or {}).get("score") or 0
    s_bh = max(-1.0, min(1.0, bh_score / 100))
    r5, r21, r63 = _row(fc, 5), _row(fc, 21), _row(fc, 63)
    s_fc = max(-1.0, min(1.0, ((r21["prob_up"] - 50) / 20 + (r63["prob_up"] - 50) / 20) / 2)) if fc else 0.0
    s_nw = nw["score"] if nw and nw["count"] >= 3 else 0.0
    combined = 0.5 * s_bh + 0.35 * s_fc + 0.15 * max(-1.0, min(1.0, s_nw * 2))
    lean = "favourable" if combined >= 0.15 else "unfavourable" if combined <= -0.15 else "neutral"

    pro, con = [], []

    def add(code, val, strength):
        (pro if strength > 0 else con).append([code, val, abs(strength)])

    if bh:
        if abs(s_bh) >= 0.05:
            add("ol_r_behaviour", bh_score, s_bh)
        for code, val in (bh.get("reasons") or [])[:6]:
            sign = {"bh_trend_up": 1, "bh_trend_down": -1, "bh_rsi_low": 1, "bh_rsi_high": -1,
                    "bh_range_low": 0.5, "bh_range_high": -0.5, "bh_mom_strong": 0.5, "bh_mom_weak": -0.5,
                    "bh_season_good": 0.4, "bh_season_bad": -0.4, "bh_near_sup": 0.4, "bh_near_res": -0.4,
                    "bh_above_avg": -0.5, "bh_below_avg": 0.5, "bh_vol_high": -0.3}.get(code)
            if code == "bh_hist60" and isinstance(val, (int, float)):
                sign = (val - 50) / 25
            if sign:
                add(code, val, sign * 0.6)
    if fc:
        add("ol_r_fc_up21", r21["prob_up"], (r21["prob_up"] - 50) / 10)
        add("ol_r_fc_up63", r63["prob_up"], (r63["prob_up"] - 50) / 10)
        if r21["touch_dn5"] is not None and r21["touch_dn5"] >= 40:
            add("ol_r_fc_dip5", r21["touch_dn5"], -(r21["touch_dn5"] - 30) / 30)
        if r21["touch_up5"] is not None and r21["touch_up5"] >= 40:
            add("ol_r_fc_pop5", r21["touch_up5"], (r21["touch_up5"] - 30) / 30)
        if fc.get("buy") and r63.get("prob_above_buy") is not None:
            add("ol_r_fc_buy63", r63["prob_above_buy"], (r63["prob_above_buy"] - 50) / 20)
    if nw and nw["count"] >= 3 and nw["mood"] != "neutral":
        add("ol_r_news_" + nw["mood"], nw["counts"][nw["mood"]], s_nw * 2)
    pro.sort(key=lambda x: -x[2])
    con.sort(key=lambda x: -x[2])
    strip = lambda lst: [[c, v] for c, v, _ in lst[:3]]

    signs = [np.sign(x) for x in (s_bh, s_fc, s_nw) if abs(x) >= 0.05]
    agree = bool(signs) and (all(s > 0 for s in signs) or all(s < 0 for s in signs))
    pts = (abs(combined) >= 0.3) + (agree and len(signs) >= 2) + bool(fc and fc["history_days"] >= 1500)
    if (bh or {}).get("confidence") == "low":
        pts -= 1
    confidence = "high" if pts >= 3 else "medium" if pts >= 1 else "low"

    return {"lean": lean, "score": int(round(combined * 100)), "confidence": confidence,
            "parts": {"behaviour": _r(s_bh), "forecast": _r(s_fc), "news": _r(s_nw)},
            "weights": {"behaviour": 0.5, "forecast": 0.35, "news": 0.15},
            "odds_up": {"1w": r5 and r5["prob_up"], "1m": r21 and r21["prob_up"], "3m": r63 and r63["prob_up"]},
            "range_1m": ({"date": r21["date"], "p10": r21["p10"], "p50": r21["p50"], "p90": r21["p90"]}
                         if r21 else None),
            "reasons_for": strip(pro), "reasons_against": strip(con)}


def outlook(asset, long_series, bh, cache_file):
    """Whole outlook block for analyse(). Never raises."""
    t0 = time.time()
    try:
        tick = ["GC=F", "GLD"] if asset.get("key") == "GOLD" else [asset["ticker"]]
        nw = news(tick, cache_file)
    except Exception as e:
        nw = {"tickers": [], "items": [], "counts": {"positive": 0, "negative": 0, "neutral": 0},
              "score": 0.0, "mood": "neutral", "count": 0, "error": type(e).__name__,
              "cached_minutes": NEWS_TTL // 60, "method": "keyword"}
    try:
        fc = forecast(long_series, asset.get("buy"), str(asset.get("ticker", "")).upper().endswith(".SR"))
    except Exception:
        fc = None
    try:
        sm = summary(bh, fc, nw)
    except Exception:
        sm = None
    return {"summary": sm, "forecast": fc, "news": nw, "disclaimer": "ol_disclaimer",
            "note": None if fc else "ol_short_history", "generated_at":
            dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "seconds": _r(time.time() - t0)}
