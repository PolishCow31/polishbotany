#!/usr/bin/env python3
"""Build data/forecasts.json from a markets+historics research run.

Input  : scripts/markets-historics-raw.json  (the deep-research workflow output,
         shape = {result:{markets, historics, predictions, methodology, verify}})
Output : data/forecasts.json                  (consumed by index.html)

forecasts.json bundles the three forecast-research datasets the Charts tab needs:
  markets        - prediction-market / expert forecasts (the Prediction-markets section)
  historics      - back-estimated AA/SWE points that extend the trajectory lines pre-2026
  trajForecasts  - per-lab AA/SWE next-model forecasts that re-anchor the dashed dots
                   (renamed from the raw file's `predictions` to avoid colliding with the
                    legacy data/predictions.json, which stays as-is)
  methodology    - how the forecasts were built (shown under the markets section)

Re-run after a fresh research pass:  python3 scripts/build_forecasts.py
"""
import json, os, sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RAW  = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "markets-historics-raw.json")
OUT  = os.path.join(ROOT, "data", "forecasts.json")

raw = json.load(open(RAW))
res = raw.get("result", raw)  # tolerate either the wrapped workflow output or a bare result

MKT_KEYS  = ("question", "platform", "forecast", "category", "relevantBenchmark", "resolveDate", "url")
HIST_KEYS = ("benchmark", "model", "lab", "date", "value", "estimate", "basis")
FC_KEYS   = ("lab", "benchmark", "expectedDate", "predicted", "low", "high", "basis", "source")

def pick(d, keys):
    return {k: d[k] for k in keys if k in d}

out = {
    "updated": datetime.now(timezone.utc).astimezone().replace(microsecond=0).isoformat(),
    "methodology": res.get("methodology", ""),
    "markets":       [pick(m, MKT_KEYS)  for m in res.get("markets", [])],
    "historics":     [pick(h, HIST_KEYS) for h in res.get("historics", [])],
    "trajForecasts": [pick(p, FC_KEYS)   for p in res.get("predictions", [])],
}

json.dump(out, open(OUT, "w"), indent=2, ensure_ascii=False)
print(f"wrote {OUT}")
print(f"  markets={len(out['markets'])} historics={len(out['historics'])} trajForecasts={len(out['trajForecasts'])}")
