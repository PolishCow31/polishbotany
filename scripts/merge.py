#!/usr/bin/env python3
"""Deterministic merge: apply data/_delta.json (proposed by claude -p) to the
authoritative data files. The LLM proposes DATA; this script is the only thing
that mutates the dataset. Additive — never drops history. Idempotent by name."""
import json, os, sys
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

    # 5. bump meta
    et = timezone(timedelta(hours=-4))
    meta["lastUpdated"] = datetime.now(et).replace(microsecond=0).isoformat()
    meta["models"] = len(models["models"])
    meta["labs"] = len({norm(m.get("lab")) for m in models["models"] if m.get("lab")})
    meta["sweeps"] = int(meta.get("sweeps", 0)) + 1
    meta["dataVersion"] = int(meta.get("dataVersion", 0)) + 1

    save("models.json", models)
    save("trends.json", trends)
    save("predictions.json", preds)
    save("meta.json", meta)
    print(f"merged: +{added} models, ~{updated} updated, +{points} points, "
          f"{promoted} promoted; dataVersion={meta['dataVersion']}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
