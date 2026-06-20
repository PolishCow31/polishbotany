#!/usr/bin/env python3
"""Deterministic merge: apply data/_delta.json (proposed by claude -p) to the
authoritative data files. The LLM proposes DATA; this script is the only thing
that mutates the dataset. Additive — never drops history. Idempotent by name."""
import json, os, sys, re
from datetime import datetime, timezone, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")

def load(name):
    with open(os.path.join(DATA, name)) as f:
        return json.load(f)

def save(name, obj):
    with open(os.path.join(DATA, name), "w") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
        f.write("\n")

def norm(s):
    return (s or "").lower().replace("  ", " ").strip()

# News integrity guard: the headless updater researches via WebSearch, which can hallucinate
# URLs. A news item is only accepted if its source is known AND the url is on that source's
# real domain (a "CNBC" item must link to cnbc.com). Catches the common right-outlet-wrong-link
# fabrication. The feed is a rolling window, so anything that slips is short-lived anyway.
NEWS_MAX = 24
NEWS_DOMAINS = {
    "CNBC": "cnbc.com", "AP": "apnews.com", "Reuters": "reuters.com", "Bloomberg": "bloomberg.com",
    "WSJ": "wsj.com", "FT": "ft.com", "The Economist": "economist.com", "Axios": "axios.com",
    "Nature": "nature.com", "MIT Tech Review": "technologyreview.com",
    "IEEE Spectrum": "spectrum.ieee.org", "The Verge": "theverge.com",
    "Ars Technica": "arstechnica.com", "Science": "science.org",
}
NEWS_KEYS = ("title", "source", "url", "date", "topic", "blurb")
def news_ok(it):
    src, url = it.get("source"), (it.get("url") or "")
    dom = NEWS_DOMAINS.get(src)
    return bool(dom and dom in url and url.startswith("http") and it.get("title") and it.get("date"))

def main():
    delta_path = os.path.join(DATA, "_delta.json")
    if not os.path.exists(delta_path):
        print("no _delta.json; nothing to merge"); return 0
    with open(delta_path) as f:
        delta = json.load(f)
    if not delta:
        print("empty delta; nothing to merge"); return 0

    models = load("models.json")
    trends = load("trends.json")
    preds  = load("predictions.json")
    meta   = load("meta.json")

    by_name = {norm(m["name"]): m for m in models["models"]}
    added = updated = points = promoted = 0

    # 1. new models (skip if name already known)
    for m in delta.get("newModels", []) or []:
        k = norm(m.get("name"))
        if not k or k in by_name:
            continue
        models["models"].append(m); by_name[k] = m; added += 1

    # 2. patch existing models with changed fields
    for u in delta.get("updatedModels", []) or []:
        k = norm(u.get("name"))
        tgt = by_name.get(k)
        if not tgt:
            continue
        for key, val in u.items():
            if key == "name":
                continue
            if key == "benchmarks" and isinstance(val, dict):
                tgt.setdefault("benchmarks", {}).update(val)
            else:
                tgt[key] = val
        updated += 1

    # 3. append trend points (dedupe by benchmark+date+model)
    tindex = {t["benchmark"]: t for t in trends["trends"]}
    for p in delta.get("newTrendPoints", []) or []:
        t = tindex.get(p["benchmark"])
        if not t:
            t = {"benchmark": p["benchmark"], "unit": "", "higherBetter": True,
                 "points": [], "predicted": [], "notes": ""}
            trends["trends"].append(t); tindex[p["benchmark"]] = t
        sig = (p.get("date"), norm(p.get("model")))
        if any((x.get("date"), norm(x.get("model"))) == sig for x in t["points"]):
            continue
        t["points"].append({"date": p["date"], "model": p["model"],
                             "lab": p.get("lab", ""), "value": p["value"]})
        t["points"].sort(key=lambda x: x["date"])
        points += 1

    # 4. promote predictions whose model was just measured
    for pr in delta.get("promotedPredictions", []) or []:
        for x in preds.get("predictions", []):
            if norm(x.get("model")) == norm(pr.get("model")) and x.get("benchmark") == pr.get("benchmark"):
                x["measured"] = pr.get("measuredValue")
                x["measuredDate"] = pr.get("date")
                promoted += 1

    et = timezone(timedelta(hours=-4))
    now_dt = datetime.now(et)
    now_iso = now_dt.replace(microsecond=0).isoformat()

    # 5. news — rolling refresh: validate, dedupe by url, newest-first, cap the window
    news_added = news_dropped = 0
    if delta.get("news"):
        try:
            news = load("news.json")
        except FileNotFoundError:
            news = {"items": []}
        items = news.get("items", []) or []
        seen = {norm(x.get("url")) for x in items}
        for it in delta["news"]:
            if not news_ok(it):
                news_dropped += 1; continue
            k = norm(it.get("url"))
            if k in seen:
                continue
            items.append({kk: it.get(kk) for kk in NEWS_KEYS}); seen.add(k); news_added += 1
        if news_added:
            items.sort(key=lambda x: (x.get("date") or ""), reverse=True)
            news["items"] = items[:NEWS_MAX]
            news["updated"] = now_iso
            save("news.json", news)

    # 6. editorial — merge prices (never drop), replace any provided snapshot list
    ed_changed = 0
    ed_delta = delta.get("editorial") or {}
    if ed_delta:
        try:
            ed = load("editorial.json")
        except FileNotFoundError:
            ed = {}
        if isinstance(ed_delta.get("prices"), dict):
            ed.setdefault("prices", {}).update({norm(k): v for k, v in ed_delta["prices"].items()}); ed_changed += 1
        for key in ("leaderboard", "upcoming", "killed", "sources"):
            if ed_delta.get(key):
                ed[key] = ed_delta[key]; ed_changed += 1
        # pulse — the Home "what's up" paragraph; replace each run, stamp time + which routine (AM/PM)
        pulse_in = ed_delta.get("pulse")
        pulse_text = pulse_in.get("text") if isinstance(pulse_in, dict) else (pulse_in if isinstance(pulse_in, str) else None)
        if pulse_text and pulse_text.strip():
            routine = "AM" if now_dt.hour < 12 else "PM"
            ed["pulse"] = {"text": pulse_text.strip(), "updated": now_iso, "routine": routine}; ed_changed += 1
        if ed_changed:
            ed["updated"] = now_iso
            save("editorial.json", ed)

    # 6b. releases — replace the frontier-release radar snapshot if provided (dates/probs shift)
    rel_changed = 0
    if delta.get("releases"):
        try:
            rel = load("releases.json")
        except FileNotFoundError:
            rel = {}
        RELK = ("model", "lab", "expectedWindow", "expectedDate", "prob", "frontier", "status", "basis", "source")
        rel["items"] = [{k: r.get(k) for k in RELK} for r in delta["releases"]]
        rel["updated"] = now_iso
        save("releases.json", rel); rel_changed = len(rel["items"])

    # 6c. glossary — additive by term (never drop existing definitions)
    gloss_added = 0
    if delta.get("glossary"):
        try:
            gl = load("glossary.json")
        except FileNotFoundError:
            gl = {"terms": []}
        gterms = gl.get("terms", []) or []
        gseen = {norm(t.get("term")) for t in gterms}
        GK = ("term", "acronym", "category", "def", "aka")
        for t in delta["glossary"]:
            k = norm(t.get("term"))
            if not k or k in gseen or not t.get("def"):
                continue
            gterms.append({kk: t.get(kk) for kk in GK}); gseen.add(k); gloss_added += 1
        if gloss_added:
            gterms.sort(key=lambda x: (x.get("term") or "").lower())
            gl["terms"] = gterms; gl["updated"] = now_iso
            save("glossary.json", gl)

    # 6d. briefs — per-model plain-English writeups, merged by model name (add/replace)
    briefs_changed = 0
    if delta.get("briefs"):
        try:
            bf = load("briefs.json")
        except FileNotFoundError:
            bf = {"briefs": {}}
        bf.setdefault("briefs", {})
        for name, txt in (delta["briefs"] or {}).items():
            if name and txt:
                bf["briefs"][name] = txt; briefs_changed += 1
        if briefs_changed:
            bf["updated"] = now_iso
            save("briefs.json", bf)

    # 6e. sources — log this sweep's consulted sources under today's AM/PM routine
    src_logged = 0
    if delta.get("sweepSources"):
        try:
            sj = load("sources.json")
        except FileNotFoundError:
            sj = {"sweeps": []}
        sj.setdefault("sweeps", [])
        routine = "AM" if now_dt.hour < 12 else "PM"
        date_s = now_dt.strftime("%Y-%m-%d")
        srcs = [{k: x.get(k) for k in ("u", "url", "q")} for x in (delta["sweepSources"] or []) if x.get("u") or x.get("url")]
        if srcs:
            entry = next((s for s in sj["sweeps"] if s.get("date") == date_s and s.get("routine") == routine), None)
            if entry:
                entry["sources"] = srcs            # same routine ran twice the same day -> overwrite
            else:
                sj["sweeps"].append({"date": date_s, "routine": routine, "sources": srcs})
            sj["updated"] = now_iso
            save("sources.json", sj)
            src_logged = len(srcs)

    # 6f. forecasts.json — PREDICTION MARKETS + narrative + chart cones (the Predict tab).
    #     Markets refresh BY URL (re-reading a market updates its live odds), new ones append, and
    #     resolved/past-date markets are pruned. historics + methodology are NEVER touched here (those
    #     are the manual AA-rebaseline territory). marketsStory/trajForecasts replace-if-provided.
    MKT_DOMAINS = {"polymarket": "polymarket.com", "metaculus": "metaculus.com", "kalshi": "kalshi.com",
                   "manifold": "manifold.markets", "epoch": "epoch.ai", "metr": "metr.org"}
    MKT_CATS = {"ranking", "release", "benchmark", "capability"}
    today_s = now_dt.strftime("%Y-%m-%d")
    def mkt_domain(platform):
        lo = (platform or "").lower()
        for k, dom in MKT_DOMAINS.items():
            if k in lo:
                return dom
        return None
    def mkt_open(q, fc, rd):
        d = (rd or "")[:10]
        if d and re.match(r"^\d{4}-\d{2}-\d{2}$", d) and d < today_s:
            return False
        if re.search(r"resolved", (q or "") + " " + (fc or ""), re.I):
            return False
        return True
    def mkt_ok(m):
        q, url, fc = m.get("question"), (m.get("url") or ""), (m.get("forecast") or "")
        dom = mkt_domain(m.get("platform"))
        d = (m.get("resolveDate") or "")[:10]
        if not (q and fc and dom and dom in url and url.startswith("http")):
            return False
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", d):
            return False
        return mkt_open(q, fc, m.get("resolveDate"))
    def mkt_clean(m):
        cat = m.get("category") if m.get("category") in MKT_CATS else "capability"
        return {"question": m.get("question"), "platform": m.get("platform"), "forecast": m.get("forecast"),
                "category": cat, "relevantBenchmark": m.get("relevantBenchmark", "other"),
                "resolveDate": m.get("resolveDate"), "url": m.get("url")}
    mkt_added = mkt_upd = story_set = traj_set = 0
    if delta.get("markets") or delta.get("marketsStory") or delta.get("trajForecasts"):
        try:
            fc = load("forecasts.json")
        except FileNotFoundError:
            fc = {}
        # markets: refresh existing by url + append new (validated), then prune resolved/past
        if delta.get("markets"):
            existing = fc.get("markets", []) or []
            by_url = {norm(m.get("url")): m for m in existing if m.get("url")}
            for m in delta["markets"]:
                if not mkt_ok(m):
                    continue
                clean = mkt_clean(m); k = norm(clean["url"])
                if k in by_url:
                    by_url[k].update(clean); mkt_upd += 1
                else:
                    existing.append(clean); by_url[k] = clean; mkt_added += 1
            if mkt_added or mkt_upd:   # only reshape when the run actually contributed valid markets
                fc["markets"] = [m for m in existing
                                 if mkt_open(m.get("question"), m.get("forecast"), m.get("resolveDate"))]
        # marketsStory: replace only a sane 3-6 paragraph set (each needs text)
        ms = delta.get("marketsStory")
        if isinstance(ms, list) and 3 <= len(ms) <= 6 and all(isinstance(s, dict) and s.get("t") for s in ms):
            fc["marketsStory"] = [{"h": s.get("h", ""), "t": s.get("t")} for s in ms]; story_set = len(ms)
        # trajForecasts: optional full-set replace (chart cones)
        tf = delta.get("trajForecasts")
        if isinstance(tf, list) and len(tf) >= 4:
            TFK = ("lab", "benchmark", "expectedDate", "predicted", "low", "high", "basis", "source")
            fc["trajForecasts"] = [{k: t.get(k) for k in TFK} for t in tf if t.get("lab") and t.get("benchmark")]
            traj_set = len(fc["trajForecasts"])
        if mkt_added or mkt_upd or story_set or traj_set:
            fc["updated"] = now_iso
            save("forecasts.json", fc)   # historics + methodology preserved untouched

    # 7. bump meta
    meta["lastUpdated"] = now_iso
    meta["models"] = len(models["models"])
    meta["labs"] = len({norm(m.get("lab")) for m in models["models"] if m.get("lab")})
    meta["sweeps"] = int(meta.get("sweeps", 0)) + 1
    meta["dataVersion"] = int(meta.get("dataVersion", 0)) + 1

    save("models.json", models)
    save("trends.json", trends)
    save("predictions.json", preds)
    save("meta.json", meta)
    print(f"merged: +{added} models, ~{updated} updated, +{points} points, "
          f"{promoted} promoted, +{news_added} news (-{news_dropped} rejected), "
          f"{ed_changed} editorial fields, {rel_changed} releases, "
          f"+{mkt_added} markets (~{mkt_upd} refreshed, {story_set}p story, {traj_set} cones), "
          f"+{gloss_added} terms, {briefs_changed} briefs, {src_logged} sources; "
          f"dataVersion={meta['dataVersion']}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
