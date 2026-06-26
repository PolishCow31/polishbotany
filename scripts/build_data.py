#!/usr/bin/env python3
"""One-shot P1 builder: transform the ai-history-foundation workflow output into
the app's data files. Run once to seed real data; thereafter the 8×/day
merge.py keeps it current."""
import json, os, re, sys
from datetime import datetime, timezone, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
SRC = sys.argv[1] if len(sys.argv) > 1 else "/private/tmp/claude-501/-Users-christian/376db47d-cee0-426f-9ede-41c2b74b4921/tasks/w7ozy0g5h.output"

raw = json.load(open(SRC))
res = raw.get("result", raw)  # handle {result:{...}} or flat

models = res.get("models", [])
trends = res.get("trends", [])
preds_groups = res.get("predictions", [])  # list of {methodology, predictions:[...]}
narrative = res.get("narrative", {})

# ---- models: add status ----
def status_for(m):
    n = (m.get("name") or "").lower()
    if "fable 5" in n: return "pulled"
    if "mythos" in n: return "preview"
    try: yr = int((m.get("released") or "2020")[:4])
    except: yr = 2020
    if yr >= 2026: return "live"   # openness is a separate flag (m.open), not a status
    return "historic"

for m in models:
    m["status"] = status_for(m)
    m.setdefault("benchmarks", {})

# ---- predictions: flatten + pick a methodology ----
methodology = ""
predictions = []
for g in preds_groups:
    if not g: continue
    if g.get("methodology") and not methodology:
        methodology = g["methodology"]
    predictions.extend(g.get("predictions", []) or [])

# ---- attach predictions to matching trend curves ----
def bkey(s):
    s = (s or "").lower()
    if "intelligence index" in s or "aa-index" in s or "aa index" in s or s.strip() == "aa": return "aa"
    if "swe" in s: return "swe"
    if "gpqa" in s: return "gpqa"
    if "mmlu" in s: return "mmlu"
    if "aime" in s or "math" in s: return "math"
    if "humaneval" in s: return "humaneval"
    if "context" in s: return "context"
    if "price" in s or "cost" in s or "token" in s: return "price"
    if "hle" in s or "humanity" in s: return "hle"
    return re.sub(r"[^a-z0-9]", "", s)[:6]

def to_date(s):
    s = (s or "").strip()
    m = re.match(r"(\d{4})[-/]?(?:q([1-4])|(\d{2}))?", s, re.I)
    if not m: return "2026-12"
    y = m.group(1)
    if m.group(2): return f"{y}-{['03','06','09','12'][int(m.group(2))-1]}"
    if m.group(3): return f"{y}-{m.group(3)}"
    return f"{y}-12"

SHORT = {"mmlu": "MMLU", "gpqa": "GPQA Diamond", "swe": "SWE-bench", "humaneval": "HumanEval",
         "aa": "AA Intelligence Index", "math": "Math (MATH → AIME)", "context": "Context window",
         "price": "API price ($/1M out)", "hle": "HLE"}
for t in trends:
    k = bkey(t.get("benchmark"))
    if k in SHORT: t["benchmark"] = SHORT[k]
    t.setdefault("predicted", [])
    t.setdefault("saturated", "saturat" in (t.get("notes", "").lower()))
tindex = {bkey(t.get("benchmark")): t for t in trends}
attached = 0
for p in predictions:
    t = tindex.get(bkey(p.get("benchmark")))
    if not t or p.get("predicted") is None: continue
    t["predicted"].append({
        "date": to_date(p.get("expectedDate")), "model": p.get("model", "forecast"),
        "lab": p.get("lab", ""), "value": p["predicted"],
        "low": p.get("low", p["predicted"]), "high": p.get("high", p["predicted"]),
    })
    t["predicted"].sort(key=lambda x: x["date"])
    attached += 1

# ---- write files ----
def save(name, obj):
    json.dump(obj, open(os.path.join(DATA, name), "w"), indent=2, ensure_ascii=False)
    open(os.path.join(DATA, name), "a").write("\n")

et = timezone(timedelta(hours=-4))
labs = sorted({m.get("lab", "").strip() for m in models if m.get("lab")})

save("models.json", {"version": 1, "models": models})
save("trends.json", {"trends": trends})
save("predictions.json", {"methodology": methodology, "predictions": predictions})
save("meta.json", {
    "lastUpdated": datetime.now(et).replace(microsecond=0).isoformat(),
    "models": len(models), "labs": len(labs), "sweeps": 1, "dataVersion": 1,
    "narrative": narrative.get("narrative", "") if isinstance(narrative, dict) else "",
    "landmarks": narrative.get("landmarks", []) if isinstance(narrative, dict) else [],
    "note": "P1: real history GPT-1 -> 2026 from ai-history-foundation workflow.",
})

print(f"built: {len(models)} models, {len(labs)} labs, {len(trends)} trends, "
      f"{len(predictions)} predictions ({attached} attached to curves)")
print("trends:", [t.get("benchmark") for t in trends])
