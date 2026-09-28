"""Fixtures for scripts/merge.py: python3 scripts/test_merge.py (exit 0 = all pass).
Every case runs against a TEMP data dir (a small fixture, or a copy of the real data/), never the real files.
Run it after any edit to merge.py. No network."""
import copy, hashlib, io, json, os, re, shutil, sys, tempfile, traceback
from contextlib import redirect_stdout
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import merge as M

REAL = os.path.join(os.path.dirname(HERE), "data")
SWEEP = "2026-09-28T15:00:05-0400"          # BSD `date +%z` style on purpose: merge must accept it
results = []


def check(name, ok, detail=""):
    results.append(bool(ok))
    print("[%s] %s%s" % ("PASS" if ok else "FAIL", name, "" if ok or not detail else "\n     " + str(detail)[:1500]))


def md5s(d):
    out = {}
    for root, _dirs, files in os.walk(d):
        for f in files:
            p = os.path.join(root, f)
            out[os.path.relpath(p, d)] = hashlib.md5(open(p, "rb").read()).hexdigest()
    return out


def J(d, name):
    return json.load(open(os.path.join(d, name)))


def fixture():
    d = tempfile.mkdtemp(prefix="merge-test-")
    files = {
        "models.json": {"version": 1, "models": [
            {"name": "GPT-6 Sol", "lab": "OpenAI", "released": "2026-09-01", "status": "live", "open": False,
             "benchmarks": {"AA-Index": 50, "GPQA": 90}, "pricing": "$2 in / $10 out per 1M", "notable": "n"},
            {"name": "Claude Opus 5.5", "lab": "Anthropic", "released": "2026-09-22", "status": "live", "open": False,
             "benchmarks": {"AA-Index": 58, "SWE-bench": 88}, "notable": "n"},
            {"name": "Tencent Hy4 Preview", "lab": "Tencent", "released": "2026-08-28", "status": "preview",
             "open": False, "benchmarks": {}, "pricing": "0.834/2.501"},
            {"name": "Flux 3 Video", "lab": "BFL", "released": "2026-07", "status": "live", "open": False,
             "benchmarks": {}}]},
        "meta.json": {"lastUpdated": "2026-09-28T12:00:00-04:00", "models": 4, "labs": 4, "sweeps": 10,
                      "dataVersion": 20, "aaScale": "v4.3"},
        "news.json": {"updated": "2026-09-28T12:00:00-04:00", "note": "n", "items": [
            {"title": "A", "source": "CNBC", "url": "https://www.cnbc.com/2026/09/27/a.html", "date": "2026-09-27",
             "topic": "Business", "blurb": "b"}]},
        "editorial.json": {"updated": "2026-09-28T12:00:00-04:00",
                           "pulse": {"text": "old pulse", "updated": "2026-09-28T12:00:00-04:00", "routine": "12PM"},
                           "prices": {"gpt 6 sol": "$2 / $10 per 1M", "flux 3 video": "$0.17/s HD"},
                           "leaderboard": {"rows": []}},
        "releases.json": {"updated": "2026-09-28T12:00:00-04:00", "note": "r", "items": [
            {"model": "Gemini 4 Pro", "lab": "Google", "expectedWindow": "by Oct 31 2026", "expectedDate": "2026-10",
             "prob": 79, "frontier": True, "status": "expected", "basis": "b", "source": "https://polymarket.com/event/x"},
            {"model": "Grok 5", "lab": "xAI", "expectedWindow": "Q4 2026", "expectedDate": "2026-12", "prob": 44,
             "frontier": True, "status": "expected", "basis": "b", "source": "https://manifold.markets/a/b", "open": True},
            {"model": "Qwen 4", "lab": "Alibaba", "expectedWindow": "TBA", "expectedDate": "2027-01", "prob": -1,
             "frontier": False, "status": "confirmed", "basis": "b", "source": "https://x.com/a"},
            {"model": "DeepSeek V4.1 Pro", "lab": "DeepSeek", "expectedWindow": "H2 2026", "expectedDate": "2026-11",
             "prob": -1, "frontier": False, "status": "confirmed", "basis": "b", "source": "https://x.com/b"},
            {"model": "Koa GA", "lab": "Salesforce", "expectedWindow": "Winter 2026", "expectedDate": "2026-12",
             "prob": -1, "frontier": False, "status": "confirmed", "basis": "b", "source": "https://x.com/c"}]},
        "glossary.json": {"updated": "2026-09-28T12:00:00-04:00", "note": "g", "terms": [
            {"term": "Explainable AI", "acronym": "XAI", "category": "Safety & alignment", "def": "d", "aka": ["interpretable AI"]},
            {"term": "Grouped-Query Attention", "acronym": "GQA", "category": "Model architecture", "def": "d", "aka": []},
            {"term": "Tokens", "acronym": "", "category": "Model architecture", "def": "d", "aka": ["token"]}]},
        "briefs.json": {"updated": "2026-09-28T12:00:00-04:00", "note": "b", "briefs": {"GPT-6 Sol": "old brief"}},
        "sources.json": {"updated": "2026-09-28T12:00:00-04:00", "note": "s", "sweeps": [
            {"date": "2026-07-30", "routine": "9AM", "sources": [{"u": "a", "url": "https://a.com", "q": "primary"}]},
            {"date": "2026-08-01", "routine": "9PM", "sources": [{"u": "b", "url": "https://b.com", "q": "blog"}]},
            {"date": "2026-08-29", "routine": "3AM", "sources": [{"u": "c", "url": "https://c.com", "q": "blog"}]},
            {"date": "2026-09-28", "routine": "12PM", "sources": [{"u": "d", "url": "https://d.com", "q": "blog"}]}]},
        "forecasts.json": {"updated": "2026-09-28T12:00:00-04:00", "methodology": "m", "markets": [
            {"question": "Best model 2026?", "platform": "Polymarket", "forecast": "76% — Anthropic", "category": "ranking",
             "relevantBenchmark": "other", "resolveDate": "2026-12-31",
             "url": "https://polymarket.com/event/which-company-has-best-ai-model-end-of-2026"},
            {"question": "Series only", "platform": "Kalshi", "forecast": "73% — Claude", "category": "ranking",
             "relevantBenchmark": "other", "resolveDate": "2026-12-31", "url": "https://kalshi.com/markets/kxllm1/yearend-top-llm"},
            {"question": "Index page", "platform": "Metaculus", "forecast": "44%", "category": "benchmark",
             "relevantBenchmark": "other", "resolveDate": "2027-01-31", "url": "https://www.metaculus.com/questions/"},
            {"question": "Compute trend", "platform": "Epoch AI (Trends)", "forecast": "4-5x per year", "category": "capability",
             "relevantBenchmark": "other", "resolveDate": "2027-12-31", "url": "https://epoch.ai/trends"},
            {"question": "Stanford says", "platform": "Stanford AI Index 2026", "forecast": "saturated", "category": "benchmark",
             "relevantBenchmark": "GPQA", "resolveDate": "2026-12-31", "url": "https://hai.stanford.edu/ai-index/r"},
            {"question": "Fake poly", "platform": "Polymarket", "forecast": "50% — x", "category": "release",
             "relevantBenchmark": "other", "resolveDate": "2026-12-31", "url": "https://www.cnbc.com/2026/09/01/poly.html"},
            {"question": "Ended", "platform": "Polymarket", "forecast": "99% — by Sep 15", "category": "release",
             "relevantBenchmark": "other", "resolveDate": "2026-09-15", "url": "https://polymarket.com/event/gpt-6-released-by"},
            {"question": "Stale", "platform": "Manifold", "forecast": "20% — Yes", "category": "capability",
             "relevantBenchmark": "other", "resolveDate": "2027-12-31", "asOf": "2026-08-20",
             "url": "https://manifold.markets/RemNi/will-we-get-agi-before-2028-ff560f9e9346"},
            {"question": "AGI 2030 (a)", "platform": "Manifold", "forecast": "54% — Yes", "category": "capability",
             "relevantBenchmark": "other", "resolveDate": "2029-12-31", "asOf": "2026-09-20",
             "url": "https://manifold.markets/RemNi/will-we-get-agi-before-2030"},
            {"question": "AGI 2030 (b)", "platform": "Manifold", "forecast": "41% — Yes", "category": "capability",
             "relevantBenchmark": "other", "resolveDate": "2030-01-01",
             "url": "https://manifold.markets/JoshYou/will-we-get-agi-before-2030"},
            {"question": "ARC (a)", "platform": "Metaculus", "forecast": "93", "category": "benchmark", "asOf": "2026-09-20",
             "relevantBenchmark": "ARC-AGI-2", "resolveDate": "2026-12-31 (closes end of 2026)",
             "url": "https://www.metaculus.com/questions/41131/top-arc-agi-2-score-in-2026/"},
            {"question": "ARC (b)", "platform": "Metaculus", "forecast": "93.4", "category": "benchmark", "asOf": "2026-09-20",
             "relevantBenchmark": "ARC-AGI-2", "resolveDate": "2026-12-31",
             "url": "https://metaculus.com/questions/41131/some-other-slug"}],
            "historics": [{"model": "h"}], "trajForecasts": [{"lab": "t"}],
            "marketsStory": [{"h": "a", "t": "1"}, {"h": "b", "t": "2"}, {"h": "c", "t": "3"}]},
        "trends.json": {"trends": []},
        "predictions.json": {"methodology": "p", "predictions": []},
    }
    for n, obj in files.items():
        with open(os.path.join(d, n), "w") as f:
            f.write(M.dumps(obj))
    return d


def run(d, delta, sweep=SWEEP):
    """-> (exit code, stdout). Writes delta (a dict, or raw text) as d/_delta.json and runs merge.main()."""
    with open(os.path.join(d, "_delta.json"), "w") as f:
        f.write(delta if isinstance(delta, str) else json.dumps(delta))
    M.DATA = d
    M.STATE_DIR = d.rstrip("/") + ".state"      # the freeze bookkeeping lives beside data/, never in it
    os.makedirs(M.STATE_DIR, exist_ok=True)
    if sweep is None:
        os.environ.pop("SWEEP_STARTED", None)
    else:
        os.environ["SWEEP_STARTED"] = sweep
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = M.main()
    return code, buf.getvalue()


def settled():
    """A fixture already passed through one merge, so the every-merge maintenance is done and a no-op is a no-op."""
    d = fixture()
    run(d, {})
    return d


def case(name, fn):
    try:
        fn()
    except Exception:
        check(name, False, traceback.format_exc())


# ---------------------------------------------------------------- 1. malformed input
def t_malformed():
    d = settled()
    before = md5s(d)
    bad = {"newModels": {"name": "X"}, "updatedModels": "nope", "news": {"a": 1}, "editorial": ["x"],
           "releases": "soon", "markets": 5, "glossary": {"term": "x"}, "briefs": ["x"], "sweepSources": "x",
           "marketsStory": "x", "newTrendPoints": [{"benchmark": "x"}], "promotedPredictions": [{}], "bogus": 1}
    code, out = run(d, bad)
    after = md5s(d)
    after.pop("_delta.json"); before.pop("_delta.json", None)
    check("malformed sections: exit 4 (nothing accepted), every section ignored, nothing written",
          code == 4 and "nothing accepted" in out and before == after and all(s in out for s in (
              "delta.newModels is dict", "delta.updatedModels is str", "delta.news is dict", "delta.editorial is list",
              "delta.releases is str", "delta.markets is int", "delta.glossary is dict", "delta.briefs is list",
              "delta.sweepSources is str", "marketsStory ignored", "ignored delta.newTrendPoints",
              "ignored delta.promotedPredictions", "ignored unknown delta keys: bogus")), out)
    for raw, label in (("{not json", "invalid JSON"), ("[1, 2]", "top-level list"), ("", "empty file")):
        code, out = run(d, raw)
        a2 = md5s(d); a2.pop("_delta.json")
        check("unusable delta (%s): exit 4, nothing written" % label, code == 4 and a2 == after, out)


def t_new_models():
    d = settled()
    good = {"name": "Naive-N0.5-Flash", "lab": "NaiveAI", "released": "2026-09-27", "status": "Live", "open": "true",
            "benchmarks": {"SWE-bench": 70, "AA-Index": 60, "GPQA": "91.5", "HLE": "n/a", "Terminal-Bench 4": 30},
            "notable": "n"}
    delta = '{"newModels": [%s, %s, %s, %s, %s, %s, %s, %s, %s]}' % (
        json.dumps(good),
        json.dumps({"name": "Missing Bits", "lab": "X"}),
        json.dumps(dict(good, name="Bad Date", released="Sep 2026")),
        json.dumps(dict(good, name="Bad Status", status="shipped")),
        json.dumps(dict(good, name="Bad Open", open="maybe")),
        json.dumps(dict(good, name="List Bench", benchmarks=[1, 2])),
        json.dumps(dict(good, name="GPT 6 Sol")),                    # aa_sync norm: same model as "GPT-6 Sol"
        '{"name": "NaN Bench", "lab": "X", "released": "2026-09", "status": "preview", "open": false, "benchmarks": {"MMLU": NaN, "HLE": 12}}',
        json.dumps("not an object"))
    code, out = run(d, delta)
    ms = {m["name"]: m for m in J(d, "models.json")["models"]}
    n = ms.get("Naive-N0.5-Flash", {})
    check("newModels: valid one added with canonical, numeric benchmarks (AA + non-numbers dropped)",
          code == 0 and n.get("benchmarks") == {"SWE-bench Verified": 70, "GPQA Diamond": 91.5, "Terminal-Bench 4.0": 30}
          and n.get("status") == "live" and n.get("open") is True, n)
    check("newModels: missing keys / bad date / bad status / bad open / list benchmarks / non-object dropped with a log",
          all(x not in ms for x in ("Missing Bits", "Bad Date", "Bad Status", "Bad Open", "List Bench"))
          and all(s in out for s in ("missing released, status, open, benchmarks", "'Sep 2026' is not YYYY-MM",
                                    "status 'shipped' not in", "open 'maybe' is not a boolean",
                                    "benchmarks is list, not an object", "not an object")), out)
    check("newModels: 'GPT 6 Sol' is a duplicate of 'GPT-6 Sol' (aa_sync norm), not a new model",
          "GPT 6 Sol" not in ms and len(ms) == 6, sorted(ms))
    def strict(c):
        raise ValueError("non-finite constant %s in output" % c)
    try:
        json.loads(open(os.path.join(d, "models.json")).read(), parse_constant=strict)
        strict_ok = True
    except ValueError:
        strict_ok = False
    check("newModels: NaN benchmark value dropped, output is strict JSON (no NaN/Infinity tokens)",
          ms.get("NaN Bench", {}).get("benchmarks") == {"HLE": 12} and strict_ok, ms.get("NaN Bench"))
    meta = J(d, "meta.json")
    check("meta: models/labs recounted, dataVersion+1", meta["models"] == 6 and meta["dataVersion"] == 22, meta)


def t_updated_models():
    d = settled()
    code, out = run(d, {"updatedModels": [
        {"name": "gpt 6 sol", "benchmarks": {"SWE-bench": 80}, "status": "superseded"},
        {"name": "Claude Opus 5.5", "benchmarks": "high", "released": "soon", "open": "yes", "notable": "new"},
        {"name": "Claude Opus 5.5", "benchmarks": {"SWE-bench Verified": 90}},
        {"name": "Nope Model", "notable": "x"}, {"notable": "no name"}]})
    ms = {m["name"]: m for m in J(d, "models.json")["models"]}
    check("updatedModels: matched by normalized name; benchmark key canonicalized; status applied",
          ms["GPT-6 Sol"]["benchmarks"].get("SWE-bench Verified") == 80 and ms["GPT-6 Sol"]["status"] == "superseded", ms["GPT-6 Sol"])
    opus = ms["Claude Opus 5.5"]
    check("updatedModels: non-dict benchmarks / bad released / bad open are ignored field-by-field, the rest applies",
          opus["notable"] == "new" and opus["released"] == "2026-09-22" and opus["open"] is False
          and "benchmarks is str, not an object" in out and "released 'soon'" in out and "open 'yes'" in out, out)
    check("updatedModels: a delta's canonical key retires the old spelling on the model",
          opus["benchmarks"] == {"AA-Index": 58, "SWE-bench Verified": 90}, opus["benchmarks"])
    check("updatedModels: unknown name and nameless update are logged, not applied",
          "no model named 'Nope Model'" in out and "updatedModels: dropped" in out, out)


# ---------------------------------------------------------------- 2. prices
PRICE_TABLE = [
    ("5/30", ("5/30", None)),
    ("0.20/1.20", ("0.2/1.2", None)),
    ("$0.03/$0.13", ("0.03/0.13", None)),
    ("$1.40 in / $4.40 out per 1M", ("1.4/4.4", None)),
    ("$0.15 / $0.47 per 1M", ("0.15/0.47", None)),
    ("1/2.70", ("1/2.7", None)),
    ("4/20 (cut >20% on Aug 21 2026; promotional through ~Nov 21, was 5/30)",
     ("4/20", "cut >20% on Aug 21 2026; promotional through ~Nov 21, was 5/30")),
    ("0.44/1.32 peak, 0.22/0.66 off-peak (from Aug 16 2026)", ("0.44/1.32", "peak, 0.22/0.66 off-peak (from Aug 16 2026)")),
    ("$2.00 / $6.00 per 1M tokens (cache hits $0.17 explicit, $0.25 implicit)", ("2/6", "cache hits $0.17 explicit, $0.25 implicit")),
    ("10/50 (Fast tier 20/100, up to 2x speed)", ("10/50", "Fast tier 20/100, up to 2x speed")),
    ("$2.50 in / $15 out per 1M (Pro: $30/$180)", ("2.5/15", "Pro: $30/$180")),
    ("$0.17/s HD, $0.29/s Full HD", (None, "$0.17/s HD, $0.29/s Full HD")),
    ("$0.15 in / $0.03 cached in / $0.50 out per 1M", (None, "$0.15 in / $0.03 cached in / $0.50 out per 1M")),
    ("$3/1M in, $15/1M out", (None, "$3/1M in, $15/1M out")),
    ("$0.005/min audio in / $0.018/min audio out", (None, "$0.005/min audio in / $0.018/min audio out")),
    ("$1.50 per 1,000 pages", (None, "$1.50 per 1,000 pages")),
    ("open weights (Apache 2.0) - no first-party API price", (None, "open weights (Apache 2.0) - no first-party API price")),
    ("n/a (free preview)", (None, "n/a (free preview)")),
    ("Rs 30/hr audio", (None, "Rs 30/hr audio")),
    ("", (None, None)), (None, (None, None)), (4, (None, None)),
]


def t_prices():
    bad = [(raw, M.parse_price(raw), want) for raw, want in PRICE_TABLE if M.parse_price(raw) != want]
    check("parse_price table (%d cases): canonical a/b, notes split off, non-token prices refused" % len(PRICE_TABLE),
          not bad, bad)
    d = settled()
    ed = J(d, "editorial.json")
    check("prices on merge: 'gpt 6 sol' re-keyed to the catalog's exact 'gpt-6 sol', value canonical",
          ed["prices"].get("gpt-6 sol") == "2/10" and "gpt 6 sol" not in ed["prices"], ed["prices"])
    check("prices on merge: a per-second video price leaves prices for priceNotes",
          "flux 3 video" not in ed["prices"] and ed.get("priceNotes", {}).get("flux 3 video") == "$0.17/s HD", ed)
    check("prices on merge: derived from models[].pricing when missing ('tencent hy4 preview' -> 0.834/2.501)",
          ed["prices"].get("tencent hy4 preview") == "0.834/2.501", ed["prices"])
    check("editorial: retired keys are no longer written by merge (the one-time cleanup removes old ones)",
          "leaderboard" in ed, ed.keys())   # merge preserves, never writes/refreshes them
    code, out = run(d, {"editorial": {"prices": {"GPT-6 Sol": "2/10 (promo through Nov 1)", "claude opus 5.5": "$4 in / $20 out per 1M",
                                                 "tencent hy4 preview": "free (promo)", "Unknown Model X": "1/2"},
                                      "leaderboard": {"rows": [1]}}})
    ed = J(d, "editorial.json")
    check("delta prices: new note stored, new price canonical, unparseable value never replaces a real price",
          ed["prices"]["gpt-6 sol"] == "2/10" and ed["priceNotes"]["gpt-6 sol"] == "promo through Nov 1"
          and ed["prices"]["claude opus 5.5"] == "4/20" and ed["prices"]["tencent hy4 preview"] == "0.834/2.501"
          and "kept 0.834/2.501" in out, (ed, out))
    check("delta prices: a key matching no catalog model is logged",
          "price keys matching no catalog model: unknown model x" in out, out)
    check("delta editorial.leaderboard: ignored with a log, not written",
          "ignored delta.editorial.leaderboard" in out and ed["leaderboard"] == {"rows": []}, out)
    code, out = run(d, {"editorial": {"prices": {"gpt-6 sol": "3/12"}}})
    ed = J(d, "editorial.json")
    check("delta prices: a changed price drops its stale note", ed["prices"]["gpt-6 sol"] == "3/12"
          and "gpt-6 sol" not in ed.get("priceNotes", {}), ed)


# ---------------------------------------------------------------- 3. benchmarks
def t_bench_alias():
    b, r, c = M.apply_bench_alias({"SWE-bench": 1, "HLE": 5, "GPQA": 2, "Terminal-Bench v3.0": 3, "Terminal-Bench 4": 4})
    check("BENCH_ALIAS: all four renamed, order kept",
          list(b.items()) == [("SWE-bench Verified", 1), ("HLE", 5), ("GPQA Diamond", 2), ("Terminal-Bench 3.0", 3),
                              ("Terminal-Bench 4.0", 4)] and len(r) == 4 and not c, b)
    b, r, c = M.apply_bench_alias({"SWE-bench": 70, "SWE-bench Verified": 72})
    check("BENCH_ALIAS: canonical spelling wins a collision", b == {"SWE-bench Verified": 72} and c == ["SWE-bench"], b)


# ---------------------------------------------------------------- 4. market identity + pipeline
def t_mkt_key():
    table = [
        ("https://www.metaculus.com/questions/5121/date-of-artificial-general-intelligence/", "metaculus:5121"),
        ("https://metaculus.com/questions/5121/date-of-first-agi-strong", "metaculus:5121"),
        ("https://www.metaculus.com/questions/", "url:metaculus.com/questions"),
        ("https://manifold.markets/RemNi/will-we-get-agi-before-2030", "manifold:will-we-get-agi-before-2030"),
        ("https://manifold.markets/JoshYou/will-we-get-agi-before-2030?r=abc", "manifold:will-we-get-agi-before-2030"),
        ("https://polymarket.com/event/Gpt-6-Released-By/", "poly:gpt-6-released-by"),
        ("https://kalshi.com/markets/kxllm1/yearend-top-llm/kxllm1-26dec31", "kalshi:KXLLM1-26DEC31"),
        ("https://kalshi.com/markets/kxllm1/yearend-top-llm", "url:kalshi.com/markets/kxllm1/yearend-top-llm"),
        ("https://www.Epoch.ai/trends/?x=1#y", "url:epoch.ai/trends"),
        ("not a url", "url:/not a url"),
        (None, "url:"),
    ]
    bad = [(u, M.mkt_key(u), want) for u, want in table if M.mkt_key(u) != want]
    check("mkt_key table (%d urls)" % len(table), not bad, bad)
    rows = [{"url": "https://manifold.markets/a/s", "asOf": "2026-09-20", "question": "1"},
            {"url": "https://manifold.markets/b/s", "question": "2"},
            {"url": "https://manifold.markets/c/s", "asOf": "2026-09-20", "question": "3"},
            {"url": "https://epoch.ai/r", "question": "Q1"}, {"url": "https://epoch.ai/r", "question": "Q2"},
            {"url": "https://polymarket.com/event/x", "question": "4", "curated": True},
            {"url": "https://polymarket.com/event/x", "question": "5", "curated": True}]
    keep, gone = M.dedupe_markets(rows)
    check("dedupe: newest asOf wins, a tie goes to the later row; one page backing two questions is two rows; "
          "curated rows are never collapsed",
          [r["question"] for r in keep] == ["3", "Q1", "Q2", "4", "5"] and len(gone) == 2, [r["question"] for r in keep])


def t_markets_merge():
    d = fixture()
    code, out = run(d, {})                       # no market delta at all: the prune still runs (D1b)
    rows = J(d, "forecasts.json")["markets"]
    by_q = {m["question"]: m for m in rows}
    check("markets, every merge: series-only Kalshi, Metaculus index page, fake-Polymarket news link dropped",
          all(q not in by_q for q in ("Series only", "Index page", "Fake poly"))
          and "Kalshi series-only url" in out and "Metaculus url without /questions/<id>/" in out
          and "url host doesn't match platform" in out, out)
    check("markets, every merge: off-market expert rows kept as kind:expert + curated",
          by_q.get("Compute trend", {}).get("kind") == "expert" and by_q["Compute trend"].get("curated") is True
          and by_q.get("Stanford says", {}).get("kind") == "expert", [by_q.get("Compute trend"), by_q.get("Stanford says")])
    check("markets, every merge: past resolveDate pruned without any market delta; asOf older than 21 days pruned",
          "Ended" not in by_q and "Stale" not in by_q and "asOf 2026-08-20 is more than 21 days old" in out, out)
    check("markets, every merge: duplicates collapsed by canonical key (Manifold slug, Metaculus id)",
          ("AGI 2030 (a)" in by_q) != ("AGI 2030 (b)" in by_q) and ("ARC (a)" in by_q) != ("ARC (b)" in by_q)
          and "AGI 2030 (a)" in by_q and "ARC (b)" in by_q, sorted(by_q))
    check("forecasts: historics, trajForecasts, methodology untouched",
          J(d, "forecasts.json")["historics"] == [{"model": "h"}] and J(d, "forecasts.json")["methodology"] == "m", "")
    delta = {"markets": [
        {"question": "AGI 2030", "platform": "Manifold", "forecast": "53.5% — Yes", "category": "capability",
         "resolveDate": "2030-03-01", "url": "https://manifold.markets/SomeoneElse/will-we-get-agi-before-2030"},
        {"question": "New one", "platform": "Polymarket", "forecast": "40% — Yes", "category": "weird",
         "resolveDate": "2026-12-31", "url": "https://polymarket.com/event/new-one"},
        {"question": "METR horizon", "platform": "METR", "forecast": "5 hours", "category": "capability",
         "resolveDate": "2026-12-31", "url": "https://metr.org/blog/x"},
        {"question": "Bad", "platform": "Kalshi", "forecast": "10%", "category": "ranking",
         "resolveDate": "2026-12-31", "url": "https://kalshi.com/markets/kxllm1"},
        {"question": "Resolved", "platform": "Polymarket", "forecast": "100% — resolved Yes", "category": "release",
         "resolveDate": "2026-12-31", "url": "https://polymarket.com/event/done"}, "junk"]}
    code, out = run(d, delta)
    rows = J(d, "forecasts.json")["markets"]
    agi = [m for m in rows if M.mkt_key(m["url"]) == "manifold:will-we-get-agi-before-2030"]
    new = [m for m in rows if m["question"] == "New one"]
    metr = [m for m in rows if m["question"] == "METR horizon"]
    check("delta market refreshes in place by canonical key (different username), asOf = sweep date",
          len(agi) == 1 and agi[0]["forecast"] == "53.5% — Yes" and agi[0]["asOf"] == "2026-09-28", agi)
    check("delta market appended (category coerced), expert-host delta row tagged expert",
          len(new) == 1 and new[0]["category"] == "capability" and new[0]["asOf"] == "2026-09-28"
          and len(metr) == 1 and metr[0].get("kind") == "expert", (new, metr))
    check("delta markets: series-only / non-object rejected with reasons; the word 'resolved' rejects nothing",
          out.count("markets: rejected") == 2 and "Kalshi series-only" in out
          and any(m["question"] == "Resolved" for m in rows), out)


# ---------------------------------------------------------------- 5. radar
def t_radar():
    d = settled()
    items = [
        {"model": "Gemini 4 Pro", "lab": "Google", "expectedWindow": "by Oct 31 2026", "expectedDate": "2026-12",
         "prob": 150, "frontier": True, "status": "Leaked", "basis": "Leak on Sep 26, now two days left.", "source": "s"},
        {"model": "GPT-6 Cyber", "lab": "OpenAI", "expectedWindow": "preview at DevDay Sep 29 (tomorrow)",
         "expectedDate": "2026-10", "prob": -5, "frontier": False, "status": "confirmed",
         "basis": "Launches tomorrow at DevDay, per Fortune.", "source": "s"},
        {"model": "Old Thing", "lab": "X", "expectedWindow": "Aug 2026", "expectedDate": "2026-08", "prob": 10,
         "status": "expected", "basis": "b"},
        {"model": "Older Thing", "lab": "X", "expectedWindow": "Jul 2026", "expectedDate": "2026-07", "prob": 10,
         "status": "expected", "basis": "b"},
        {"model": "Claude Opus 5.5", "lab": "Anthropic", "expectedWindow": "Oct 2026", "expectedDate": "2026-10",
         "prob": 90, "status": "expected", "basis": "b"},
        {"model": "Grok 5", "lab": "xAI", "expectedWindow": "Q4 2026", "expectedDate": "2026-11", "prob": "44",
         "frontier": "true", "status": "expected", "basis": "b"},
        {"model": "Qwen 4", "lab": "Alibaba", "expectedWindow": "TBA", "expectedDate": "2027-01-15", "prob": None,
         "status": "confirmed", "basis": "b", "open": "true"},
        {"model": "No Date", "lab": "X", "expectedWindow": "someday", "expectedDate": None, "prob": 5}]
    code, out = run(d, {"releases": items})
    got = {r["model"]: r for r in J(d, "releases.json")["items"]}
    g = got.get("Gemini 4 Pro", {})
    check("radar: 'by <month>' caps a later expectedDate at the deadline month; prob clamped; status coerced; "
          "relative words stripped", g.get("expectedDate") == "2026-10" and g.get("prob") == 100
          and g.get("status") == "expected" and g.get("basis") == "Leak on Sep 26." and g.get("probAsOf") == "2026-09-28", g)
    c = got.get("GPT-6 Cyber", {})
    check("radar: a window naming a date sets expectedDate to that month; '(tomorrow)' and 'tomorrow' stripped",
          c.get("expectedDate") == "2026-09" and c.get("expectedWindow") == "preview at DevDay Sep 29"
          and c.get("basis") == "Launches at DevDay, per Fortune." and c.get("prob") == -1 and c.get("probAsOf") is None, c)
    check("radar: a lapsed window (Aug, 28 days ago) stays, marked late; one lapsed >30 days, a live catalog model and "
          "an undatable item drop (all logged)",
          got.get("Old Thing", {}).get("late") is True and got["Old Thing"]["expectedDate"] == "2026-08"
          and all(x not in got for x in ("Older Thing", "Claude Opus 5.5", "No Date"))
          and "window ended 2026-07-31, more than 30 days ago" in out and "already a live catalog model" in out
          and "expectedDate None is not YYYY-MM" in out, out)
    gk = got.get("Grok 5", {})
    check("radar: numeric-string prob accepted, 'true' strings -> booleans, missing open carried from the old item",
          gk.get("prob") == 44 and gk.get("frontier") is True and gk.get("open") is True
          and got.get("Qwen 4", {}).get("open") is True and got["Qwen 4"]["expectedDate"] == "2027-01", (gk, got.get("Qwen 4")))
    check("radar: every stored item has exactly the RELK keys", all(tuple(r) == M.RELK for r in got.values()), "")
    before = J(d, "releases.json")["items"]
    code, out = run(d, {"releases": items[:1]})
    after = J(d, "releases.json")["items"]
    check("radar: a replacement under 60% of the current list is refused and the current list kept",
          "REFUSED" in out and [r["model"] for r in after] == [r["model"] for r in before], out)


def t_window_deadline():
    table = [("by Oct 15", 2026, ("2026-10-15", "2026-10", "by")), ("Oct 2026", 2026, ("2026-10-31", "2026-10", "month")),
             ("Q4 2026", 2026, ("2026-12-31", "2026-12", "span")), ("by Jan 15", 2026, ("2026-01-15", "2026-01", "by")),
             ("may slip to H2", 2026, ("2026-12-31", "2026-12", "span")), ("May 2027", 2026, ("2027-05-31", "2027-05", "month")),
             ("before Nov", 2026, ("2026-10-31", "2026-11", "by")), ("Sept 30", 2026, ("2026-09-30", "2026-09", "month")),
             ("before Nov 15", 2026, ("2026-11-14", "2026-11", "by")), ("by Feb 30 2027", 2026, ("2027-02-28", "2027-02", "by")),
             ("H1 2027", 2026, ("2027-06-30", "2027-06", "span")), ("2027", 2026, ("2027-12-31", "2027-12", "span")),
             ("before 2027", 2026, ("2026-12-31", "2026-12", "span")), ("TBA", 2026, None)]
    bad = [(w, M.window_deadline(w, y), want) for w, y, want in table if M.window_deadline(w, y) != want]
    check("window_deadline table (%d windows)" % len(table), not bad, bad)


# ---------------------------------------------------------------- 6. glossary
def t_glossary():
    d = settled()
    code, out = run(d, {"glossary": [
        {"term": "Grouped Query Attention", "acronym": "GQA", "category": "c", "def": "d"},
        {"term": "token", "acronym": "", "category": "c", "def": "d"},
        {"term": "XAI", "acronym": "", "category": "Orgs, models & ecosystem", "def": "the lab"},
        {"term": "Global Query Aggregation", "acronym": "GQA", "category": "c", "def": "d", "aka": "gqa-agg"},
        {"term": "No Def", "def": ""}, {"term": "  ", "def": "x"},
        {"term": "Brand-New Term", "acronym": "", "category": "c", "def": "d", "aka": ["bnt"]},
        {"term": "brand new term", "acronym": "", "category": "c", "def": "dup within the same delta"}]})
    terms = {t["term"]: t for t in J(d, "glossary.json")["terms"]}
    check("glossary: normalized-term and aka duplicates skipped (incl. within one delta)",
          "Grouped Query Attention" not in terms and "token" not in terms and "brand new term" not in terms
          and out.count("duplicate of existing") == 3, out)
    check("glossary: a match on an acronym only is logged, not rejected",
          "XAI" in terms and "Global Query Aggregation" in terms and terms["Global Query Aggregation"]["aka"] == ["gqa-agg"]
          and "'XAI' shares 'xai' with the acronym of 'Explainable AI'" in out
          and "'Global Query Aggregation' shares 'gqa'" in out, out)
    check("glossary: missing def / empty term dropped with a log; valid new term added; list stays sorted",
          "No Def" not in terms and "no def" in out and "no term" in out and "Brand-New Term" in terms
          and [t.lower() for t in terms] == sorted(t.lower() for t in terms), out)


# ---------------------------------------------------------------- 7. news + hosts
def t_hosts():
    check("host check: microsoft.com is NOT ft.com; ft.com.evil.io is NOT ft.com; www.ft.com IS ft.com",
          not M.host_is("https://microsoft.com/a", "ft.com") and not M.host_is("https://ft.com.evil.io/a", "ft.com")
          and M.host_is("https://www.ft.com/a", "ft.com") and not M.host_is("not a url", "ft.com")
          and not M.host_is("http://[::1", "ft.com"), "")
    ok = {"title": "t", "source": "CNBC", "url": "https://www.cnbc.com/2026/09/28/x.html", "date": "2026-09-28"}
    check("news_ok: right outlet + right host passes; lookalike host, dropped outlets (FT/Reuters/WSJ) fail",
          M.news_ok(ok) and not M.news_ok(dict(ok, url="https://www.cnbc.com.evil.io/x"))
          and not M.news_ok(dict(ok, source="FT", url="https://www.ft.com/x"))
          and not M.news_ok(dict(ok, source="Reuters", url="https://www.reuters.com/x"))
          and not M.news_ok(dict(ok, source="WSJ", url="https://www.wsj.com/x"))
          and not M.news_ok(dict(ok, date=20260928)), "")
    d = settled()
    code, out = run(d, {"news": [dict(ok, topic="Business", blurb="b"), dict(ok, url="https://microsoft.com/cnbc.com/x"),
                                 "junk", dict(ok, url="https://www.cnbc.com/2026/09/28/x.html")]})
    items = J(d, "news.json")["items"]
    check("news merge: 1 added, 2 rejected, url duplicate skipped, newest first",
          len(items) == 2 and items[0]["url"].endswith("x.html") and "+1 news (-2 rejected)" in out, (items, out))


# ---------------------------------------------------------------- 8. clock, sources, meta, pulse
def t_clock_sources_meta():
    for s, want in (("2026-09-28T15:00:05-0400", "3PM 2026-09-28"), ("2026-09-28T15:00:05-04:00", "3PM 2026-09-28"),
                    ("2026-11-02T00:30:00-0500", "12AM 2026-11-02"), ("2026-11-02T05:30:00Z", "12AM 2026-11-02"),
                    ("2026-09-28T20:59:00", "6PM 2026-09-28")):
        os.environ["SWEEP_STARTED"] = s
        dt = M.sweep_clock()
        check("clock: SWEEP_STARTED %s -> %s" % (s, want), "%s %s" % (M.slot_of(dt), dt.strftime("%Y-%m-%d")) == want,
              dt.isoformat())
    os.environ["SWEEP_STARTED"] = "garbage"
    buf = io.StringIO()
    with redirect_stdout(buf):
        dt = M.sweep_clock()
    check("clock: unparseable SWEEP_STARTED falls back to now (logged)",
          "unparseable" in buf.getvalue() and abs((datetime.now(M.ET) - dt).total_seconds()) < 60, buf.getvalue())
    d = fixture()
    code, out = run(d, {"sweepSources": [{"u": "x", "url": "https://x.com", "q": "primary"}, {"q": "no url"}]})
    sw = J(d, "sources.json")["sweeps"]
    arch_dir = os.path.join(d, "sources-archive")
    arch = {f: json.load(open(os.path.join(arch_dir, f))) for f in sorted(os.listdir(arch_dir))} if os.path.isdir(arch_dir) else {}
    check("sources: this sweep logged under its SWEEP_STARTED slot (3PM), not the merge time",
          sw[-1]["date"] == "2026-09-28" and sw[-1]["routine"] == "3PM" and len(sw[-1]["sources"]) == 1, sw[-1])
    check("sources: sweeps older than 30 days moved to sources-archive/YYYY-MM.json, the rest kept in order",
          [s["date"] for s in sw] == ["2026-08-29", "2026-09-28", "2026-09-28"]
          and sorted(arch) == ["2026-07.json", "2026-08.json"]
          and [s["date"] for s in arch["2026-07.json"]["sweeps"]] == ["2026-07-30"]
          and [s["date"] for s in arch["2026-08.json"]["sweeps"]] == ["2026-08-01"] and "(1 archived)" not in out, (sw, arch))
    with open(os.path.join(d, "sources.json")) as f:     # simulate a crash that archived but didn't trim
        sj = json.load(f)
    sj["sweeps"].insert(0, {"date": "2026-08-01", "routine": "9PM", "sources": [{"u": "b2", "url": "https://b2.com"}]})
    with open(os.path.join(d, "sources.json"), "w") as f:
        f.write(M.dumps(sj))
    run(d, {})
    a8 = json.load(open(os.path.join(arch_dir, "2026-08.json")))["sweeps"]
    check("sources: re-archiving is append-merge by (date, slot): replaced, never duplicated",
          len(a8) == 1 and a8[0]["sources"][0]["u"] == "b2", a8)
    with open(os.path.join(arch_dir, "2026-06.json"), "w") as f:
        f.write("{corrupt")
    sj = J(d, "sources.json")
    sj["sweeps"].insert(0, {"date": "2026-06-20", "routine": "3AM", "sources": []})
    with open(os.path.join(d, "sources.json"), "w") as f:
        f.write(M.dumps(sj))
    code, out = run(d, {})
    check("sources: an unreadable archive month is left alone and its sweeps stay in sources.json",
          J(d, "sources.json")["sweeps"][0]["date"] == "2026-06-20" and "unreadable" in out, out)

    d = settled()
    before = md5s(d)
    code, out = run(d, {})
    after = md5s(d)
    check("meta: a no-op merge changes nothing at all (no dataVersion / sweeps / lastUpdated bump)",
          {k: v for k, v in before.items() if k != "_delta.json"} == {k: v for k, v in after.items() if k != "_delta.json"}
          and "no data changes" in out, out)
    meta0 = J(d, "meta.json")
    code, out = run(d, {"editorial": {"pulse": "old pulse"}})
    check("pulse: an unchanged pulse keeps its old stamp (no change, no bump)",
          J(d, "editorial.json")["pulse"]["updated"] == "2026-09-28T12:00:00-04:00" and J(d, "meta.json") == meta0, out)
    code, out = run(d, {"editorial": {"pulse": {"text": "  new pulse  "}}})
    p = J(d, "editorial.json")["pulse"]
    m1 = J(d, "meta.json")
    check("pulse: a new pulse is stamped with the sweep's clock + slot; meta bumps exactly once",
          p == {"text": "new pulse", "updated": "2026-09-28T15:00:05-04:00", "routine": "3PM"}
          and m1["dataVersion"] == meta0["dataVersion"] + 1 and m1["sweeps"] == meta0["sweeps"] + 1
          and m1["lastUpdated"] == "2026-09-28T15:00:05-04:00", (p, m1))
    tr = hashlib.md5(open(os.path.join(d, "trends.json"), "rb").read()).hexdigest()
    run(d, {"newTrendPoints": [{"benchmark": "x", "date": "2026-09-01", "model": "m", "value": 1}]})
    check("retired: trends.json / predictions.json are never written",
          hashlib.md5(open(os.path.join(d, "trends.json"), "rb").read()).hexdigest() == tr, "")


# ---------------------------------------------------------------- 9. transactions
def t_transactional():
    d = settled()
    with open(os.path.join(d, "glossary.json"), "w") as f:
        f.write("{corrupt")                  # an unreadable data file: nothing can be merged safely
    before = md5s(d)
    try:
        run(d, {"news": [{"title": "t", "source": "CNBC", "url": "https://www.cnbc.com/z", "date": "2026-09-28"}],
                "editorial": {"pulse": "p2"}})
        raised = False
    except ValueError:
        raised = True
    after = md5s(d)
    check("transaction: an unreadable data file raises (update.sh sees non-zero) and writes NOTHING",
          raised and {k: v for k, v in before.items() if k != "_delta.json"} == {k: v for k, v in after.items() if k != "_delta.json"}, "")
    d = settled()
    before = md5s(d)
    real_w, calls = M.write_atomic, []

    def flaky(path, text):
        calls.append(path)
        if len(calls) == 3:
            raise OSError("disk full")
        real_w(path, text)
    M.write_atomic = flaky
    try:
        run(d, {"news": [{"title": "t", "source": "CNBC", "url": "https://www.cnbc.com/z", "date": "2026-09-28"}],
                "editorial": {"pulse": "p3"}, "briefs": {"GPT-6 Sol": "new"}, "glossary": [{"term": "Zeta", "def": "d"}]})
        raised = False
    except OSError:
        raised = True
    finally:
        M.write_atomic = real_w
    after2 = md5s(d)
    stray = [f for f in os.listdir(d) if f.endswith(".tmp")]
    check("transaction: a failure mid-write rolls back the files already replaced; no .tmp left behind",
          raised and len(calls) == 5 and calls[3:] == calls[:2][::-1] and not stray
          and {k: v for k, v in before.items() if k != "_delta.json"} == {k: v for k, v in after2.items() if k != "_delta.json"},
          (calls, stray))


# ---------------------------------------------------------------- 10. idempotency
REALISTIC_DELTA = {
    "newModels": [{"name": "Claude Sonnet 5.5", "lab": "Anthropic", "released": "2026-09-28", "params": "unknown",
                   "context": "—", "modality": "text, image in; text out", "open": False,
                   "benchmarks": {"Terminal-Bench 4": 70.6, "HLE (with tools)": 64.5}, "milestone": False,
                   "status": "live", "notable": "Anthropic's mid-tier model.", "sources": ["https://www.anthropic.com/news"]}],
    "updatedModels": [{"name": "claude opus 5.5", "notable": "Leads the leaderboard."}],
    "news": [{"title": "Anthropic ships Sonnet 5.5", "source": "CNBC", "url": "https://www.cnbc.com/2026/09/28/sonnet.html",
              "date": "2026-09-28", "topic": "Models", "blurb": "b"}],
    "editorial": {"prices": {"claude sonnet 5.5": "2/10"}, "pulse": "**Claude Sonnet 5.5** shipped Sep 28."},
    "releases": [{"model": "Claude Haiku 5.5", "lab": "Anthropic", "expectedWindow": "by Oct 31", "expectedDate": "2026-10",
                  "prob": 96, "frontier": False, "open": False, "status": "confirmed", "basis": "Anthropic says weeks away.",
                  "source": "https://polymarket.com/event/next-claude-haiku-released-byptptpt-20260701205353326"},
                 {"model": "Gemini 4 Pro", "lab": "Google DeepMind", "expectedWindow": "by Oct 31", "expectedDate": "2026-10",
                  "prob": 78, "frontier": True, "open": False, "status": "expected", "basis": "Checkpoint seen on LMArena.",
                  "source": "https://polymarket.com/event/next-google-gemini-pro-model-released-byptptpt"}],
    "markets": [{"question": "Which company has the best AI model end of 2026?", "platform": "Polymarket",
                 "forecast": "75% — Anthropic, best model at end of 2026", "category": "ranking", "relevantBenchmark": "other",
                 "resolveDate": "2026-12-31", "url": "https://polymarket.com/event/which-company-has-best-ai-model-end-of-2026"}],
    "marketsStory": [{"h": "Race —", "t": "a"}, {"h": "Next —", "t": "b"}, {"h": "Bench —", "t": "c"}, {"h": "AGI —", "t": "d"}],
    "glossary": [{"term": "DNS tunneling", "acronym": "", "category": "Safety & alignment", "def": "Hiding data in DNS lookups.",
                  "aka": ["DNS exfiltration"]}],
    "briefs": {"Claude Sonnet 5.5": "Para one.\n\nPara two."},
    "sweepSources": [{"u": "anthropic.com/news", "url": "https://www.anthropic.com/news", "q": "primary"}],
    "asOf": "2026-09-28"}


def t_idempotent():
    for label, mk in (("fixture", fixture), ("copy of real data/", None)):
        if mk:
            d = mk()
        else:
            if not os.path.exists(os.path.join(REAL, "models.json")):
                check("idempotency on real data (skipped: no data/ next to scripts/)", True)
                continue
            d = tempfile.mkdtemp(prefix="merge-test-real-")
            shutil.rmtree(d)
            shutil.copytree(REAL, d, ignore=shutil.ignore_patterns("_delta.json", "*.tmp"))
        code1, out1 = run(d, copy.deepcopy(REALISTIC_DELTA))
        first = md5s(d)
        code2, out2 = run(d, copy.deepcopy(REALISTIC_DELTA))
        second = md5s(d)
        json_ok = all(json.load(open(os.path.join(d, n))) is not None for n in ("models.json", "forecasts.json", "releases.json"))
        check("idempotency (%s): the same delta merged twice leaves every file byte-identical the second time" % label,
              code1 == 0 and code2 == 0 and first == second and "no data changes" in out2 and json_ok,
              (out1[-600:], out2[-600:], sorted(k for k in first if first.get(k) != second.get(k))))


# ---------------------------------------------------------------- fix round (Sep 28 skeptic + coordinator) regressions
def t_malformed_field_types():      # item 3: list-valued fields that crashed the merge now drop just their item
    d = settled()
    ok_news = {"title": "ok", "source": "CNBC", "url": "https://www.cnbc.com/2026/09/28/ok.html", "date": "2026-09-28",
               "topic": "Business", "blurb": "b"}
    rel = lambda name, **kw: dict({"model": name, "lab": "A", "expectedWindow": "Q1 2027", "expectedDate": "2027-02",
                                   "prob": 5, "status": "expected", "basis": "b"}, **kw)
    code, out = run(d, {
        "news": [dict(ok_news, source=["Axios"], url="https://www.axios.com/2026/09/28/a"),
                 dict(ok_news, topic=["Policy"], url="https://www.cnbc.com/2026/09/28/t.html"), ok_news],
        "markets": [{"question": "Q list", "platform": "Polymarket", "forecast": "40% — Yes", "category": ["ranking"],
                     "resolveDate": "2026-12-31", "url": "https://polymarket.com/event/list-cat"},
                    {"question": "Q ok", "platform": "Polymarket", "forecast": "41% — Yes", "category": "ranking",
                     "resolveDate": "2026-12-31", "url": "https://polymarket.com/event/ok-cat"}],
        "releases": [rel("Bad Status", status=["confirmed"]), rel("Bad Lab", lab=["Google"]),
                     rel("R1"), rel("R2"), rel("R3"), rel("R4")],
        "newModels": [{"name": "Status List", "lab": "X", "released": "2026-09-28", "status": ["live"], "open": False,
                       "benchmarks": {}},
                      {"name": "Lab List", "lab": ["X"], "released": "2026-09-28", "status": "live", "open": False,
                       "benchmarks": {}},
                      {"name": "Good Model", "lab": "X", "released": "2026-09-28", "status": "live", "open": False,
                       "benchmarks": {}, "params": 70, "notable": ["not", "text"]}],
        "glossary": [{"term": "Cat List", "category": ["x"], "def": "d"}, {"term": "Good Term", "category": "c", "def": "d"}],
        "sweepSources": [{"u": ["x"], "url": "https://x.com"}, {"u": "ok", "url": "https://ok.com", "q": "primary"}]})
    news = [x["url"] for x in J(d, "news.json")["items"]]
    mk = {m["question"] for m in J(d, "forecasts.json")["markets"]}
    rl = {r["model"] for r in J(d, "releases.json")["items"]}
    ms = {m["name"]: m for m in J(d, "models.json")["models"]}
    gl = {t["term"] for t in J(d, "glossary.json")["terms"]}
    sw = J(d, "sources.json")["sweeps"][-1]
    check("malformed_field_types: list-valued source/topic/category/status/lab items dropped with a reason, merge exits 0, "
          "the valid items land",
          code == 0 and news.count(ok_news["url"]) == 1 and len(news) == 2 and "Q ok" in mk and "Q list" not in mk
          and {"R1", "R2", "R3", "R4"} <= rl and not {"Bad Status", "Bad Lab"} & rl
          and "Good Model" in ms and not {"Status List", "Lab List"} & set(ms) and ms["Good Model"].get("params") == "70"
          and "notable" not in ms["Good Model"] and "Good Term" in gl and "Cat List" not in gl
          and len(sw["sources"]) == 1 and sw["sources"][0]["u"] == "ok"
          and all(x in out for x in ("source not a string", "topic not a string", "category is list, not a string",
                                     "status not a string", "lab not a string", "lab ['X'] is not text",
                                     "category not a string")), out)


def t_section_isolated():           # item 3: an unexpected error inside one section can't take down the merge
    d = settled()
    real = M.normalize_prices
    M.normalize_prices = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom in prices"))
    try:
        code, out = run(d, {"editorial": {"pulse": "isolated pulse", "prices": {"gpt-6 sol": "9/99"}},
                            "news": [{"title": "t", "source": "CNBC", "url": "https://www.cnbc.com/2026/09/28/iso.html",
                                      "date": "2026-09-28"}]})
    finally:
        M.normalize_prices = real
    ed = J(d, "editorial.json")
    check("section_isolated: a crashing section is skipped (its file keeps its content), the other sections land, "
          "merge exits 3 (partial)",
          code == 3 and "editorial.prices: SKIPPED" in out and ed["prices"]["gpt-6 sol"] == "2/10"
          and ed["pulse"]["text"] == "isolated pulse"
          and any(x["url"].endswith("iso.html") for x in J(d, "news.json")["items"]), out)


def t_radar_late_not_rolled():      # item 7: a missed "by Oct 15" is LATE, never next year's, and retires after 30 days
    items = [{"model": "Late Model", "lab": "X", "expectedWindow": "by Oct 15", "expectedDate": "2026-10", "prob": 40,
              "status": "expected", "basis": "b"}]
    res = {}
    for day in ("2026-10-20", "2026-11-03", "2026-11-20"):
        now = datetime(int(day[:4]), int(day[5:7]), int(day[8:]), 15, 0, tzinfo=M.ET)
        buf = io.StringIO()
        with redirect_stdout(buf):
            got, dropped = M.validate_releases(items, set(), now)
        res[day] = (got[0] if got else None, dropped)
    a, b = res["2026-10-20"][0] or {}, res["2026-11-03"][0] or {}
    check("radar_late_not_rolled: 'by Oct 15' read Oct 20 keeps 2026-10 and is marked late",
          a.get("expectedDate") == "2026-10" and a.get("late") is True, res["2026-10-20"])
    check("radar_late_not_rolled: read Nov 3 it is still 2026-10 + late (not rolled into 2027)",
          b.get("expectedDate") == "2026-10" and b.get("late") is True, res["2026-11-03"])
    check("radar_late_not_rolled: read Nov 20 (36 days past its deadline) it drops, logged",
          res["2026-11-20"][0] is None and "more than 30 days" in str(res["2026-11-20"][1]), res["2026-11-20"])


def t_radar_late_baseline():        # item 7: late items don't count toward the 60% refusal baseline
    now = datetime(2026, 10, 20, 15, 0, tzinfo=M.ET)
    late = [{"model": "Late %d" % i, "lab": "X", "expectedWindow": "by Oct %d" % (10 + i), "expectedDate": "2026-10",
             "prob": 30, "status": "expected", "basis": "b"} for i in range(4)]
    normal = [{"model": "Next %d" % i, "lab": "Y", "expectedWindow": "Q1 2027", "expectedDate": "2027-02", "prob": -1,
               "status": "expected", "basis": "b"} for i in range(6)]
    buf = io.StringIO()
    with redirect_stdout(buf):
        items, dropped, refused = M.radar_update(late + normal, normal[:5], [], now)
    check("radar_late_baseline: a correct 5-item list is not refused against 10 stored items of which 4 are late",
          not refused and [r["model"] for r in items] == ["Next %d" % i for i in range(5)],
          (refused, [r["model"] for r in items]))


def t_resolved_text_kept():         # item 8: the word "resolved" never removes a row
    d = settled()
    fc = J(d, "forecasts.json")
    fc["markets"] += [
        {"question": "Will an agent resolve 90% of SWE-bench tasks?", "platform": "Manifold",
         "forecast": "31% — Yes; no agent has resolved 90% yet", "category": "benchmark", "relevantBenchmark": "other",
         "resolveDate": "2026-12-31", "url": "https://manifold.markets/u/agent-resolve-90", "asOf": "2026-09-27"},
        {"question": "Share of GitHub issues resolved by agents", "platform": "Epoch AI",
         "forecast": "About 60% of issues resolved by agents by 2027", "category": "capability",
         "relevantBenchmark": "other", "resolveDate": "2027-12-31", "url": "https://epoch.ai/data/issues",
         "kind": "expert", "curated": True}]
    with open(os.path.join(d, "forecasts.json"), "w") as f:
        f.write(M.dumps(fc))
    code, out = run(d, {"markets": [{"question": "Resolved-word delta", "platform": "Polymarket",
                                     "forecast": "12% — Yes; nothing resolved yet", "category": "release",
                                     "resolveDate": "2026-12-31", "url": "https://polymarket.com/event/resolved-word"}]})
    qs = {m["question"] for m in J(d, "forecasts.json")["markets"]}
    check("resolved_text_kept: '...no agent has resolved 90% yet', a curated expert row saying 'issues resolved' and a "
          "delta row mentioning 'resolved' all survive",
          {"Will an agent resolve 90% of SWE-bench tasks?", "Share of GitHub issues resolved by agents",
           "Resolved-word delta"} <= qs, (sorted(qs), out))


def t_benchmark_zero():             # item 10: 0 / negative benchmark values are placeholders, not scores
    buf = io.StringIO()
    with redirect_stdout(buf):
        got = M.clean_benchmarks({"GPQA": 0, "X": -3, "HLE": 41.2, "GDPval": 1695}, "t")
    check("benchmark_zero: {GPQA:0, X:-3, HLE:41.2, GDPval:1695} keeps HLE and GDPval only (no upper bound)",
          got == {"HLE": 41.2, "GDPval": 1695} and buf.getvalue().count("placeholder zero") == 2, (got, buf.getvalue()))
    d = settled()
    code, out = run(d, {"newModels": [{"name": "Zero Model", "lab": "X", "released": "2026-09-28", "status": "live",
                                       "open": False, "benchmarks": {"GPQA": 0, "HLE": 41.2}}],
                        "updatedModels": [{"name": "GPT-6 Sol", "benchmarks": {"SWE-bench Pro": 0}}]})
    ms = {m["name"]: m for m in J(d, "models.json")["models"]}
    check("benchmark_zero: through the merge, a 0 never lands on a new or an updated model",
          ms["Zero Model"]["benchmarks"] == {"HLE": 41.2} and "SWE-bench Pro" not in ms["GPT-6 Sol"]["benchmarks"], out)


PROMPT = os.path.join(HERE, "research-prompt.md")


def _prompt_section(head):
    txt = open(PROMPT).read()
    return txt.split(head, 1)[1].split("\n## ", 1)[0] if head in txt else ""


def t_prompt_news_date():           # item 9a
    news = _prompt_section("## Also refresh the News feed")
    check("prompt_news_date: the news rules require a full YYYY-MM-DD date or leaving the item out",
          "full YYYY-MM-DD" in news and "leave the item out" in news, news[-400:])


def t_prompt_no_zero():             # item 10
    txt = open(PROMPT).read()
    check("prompt_no_zero: the model rules forbid 0 as a placeholder benchmark",
          "never write 0 as a placeholder" in txt and "Omit any benchmark you don't have a sourced number for" in txt, "")


def t_prompt_one_row_per_question():   # round 3: same-question duplicates on one platform read as a contradiction
    txt = " ".join(open(PROMPT).read().lower().split())
    check("prompt_one_row_per_question: the market rules say one row per question per platform",
          "one row per question per platform: never add a second market with the same question on the same platform"
          in txt, "")


def t_prompt_radar_late():          # item 7
    radar = _prompt_section("## Also refresh the frontier-release radar")
    check("prompt_radar_late: the radar rules say dates never roll into next year and lapsed items stay late 30 days",
          "never" in radar and "rolls a date into next year" in radar and "late for 30 days" in radar
          and "drops items dated before the current month" not in radar, radar[:600])


# ---------------------------------------------------------------- round 2 (second skeptic) regressions
NEWS_OK = {"title": "ok", "source": "CNBC", "url": "https://www.cnbc.com/2026/09/28/fenced.html", "date": "2026-09-28",
           "topic": "Models", "blurb": "b"}


def t_fenced_delta_usable():        # B: a ```json fence around a valid delta is stripped, not a dead sweep
    d = settled()
    code, out = run(d, "```json\n" + json.dumps({"news": [NEWS_OK]}) + "\n```\n")
    urls = [x["url"] for x in J(d, "news.json")["items"]]
    check("fenced_delta_usable: a fenced delta merges (exit 0) and its item lands", code == 0 and NEWS_OK["url"] in urls, out)


def t_unusable_delta_exit4():       # B: an unusable delta is a failed sweep, never exit 0
    d = settled()
    code, out = run(d, "I could not finish the research this time.")
    check("unusable_delta_exit4: non-JSON delta -> exit 4 'merge: unusable delta'",
          code == 4 and "merge: unusable delta" in out, out)


def t_nothing_accepted_exit4():     # B: a delta whose every item is rejected is a failed sweep
    d = settled()
    code, out = run(d, {"news": [dict(NEWS_OK, source="Reuters", url="https://www.reuters.com/x")],
                        "markets": [{"question": "q", "platform": "Polymarket", "forecast": "50%", "category": "release",
                                     "resolveDate": "2026-12-31", "url": "https://news.example.com/x"}]})
    check("nothing_accepted_exit4: 2 items offered, 0 accepted -> exit 4 'merge: nothing accepted (2 rejected)'",
          code == 4 and "merge: nothing accepted (2 rejected)" in out, out)


def t_section_freeze_state():       # B: one section rejected 8 sweeps running raises its own alarm
    d = settled()
    af, rf = ".section_alarm", ".section_rejects.json"   # literal: update.sh reads these by name
    alarm = lambda: open(os.path.join(M.STATE_DIR, af)).read() if os.path.exists(os.path.join(M.STATE_DIR, af)) else ""
    state_of = lambda: json.load(open(os.path.join(M.STATE_DIR, rf))) if os.path.exists(os.path.join(M.STATE_DIR, rf)) else {}
    seen = []
    for i in range(8):                  # the pulse lands every sweep (so no dead streak), news is always rejected
        code, out = run(d, {"editorial": {"pulse": "pulse %d" % i},
                            "news": [dict(NEWS_OK, source="Reuters", url="https://www.reuters.com/%d" % i)]})
        seen.append(alarm())
    state = state_of()
    check("section_freeze_state: news rejected 8 sweeps running -> 'news 8' in .section_alarm on the 8th (not before)",
          seen[-1] == "news 8\n" and not any(seen[:7]) and state.get("news") == 8 and state.get("editorial.pulse") == 0
          and "SECTION FREEZE: news" in out, (seen, state))
    code, out = run(d, {"news": [NEWS_OK]})
    state = state_of()
    check("section_freeze_state: one accepted news item resets the counter and clears the alarm",
          state.get("news") == 0 and alarm() == "", (state, alarm()))


def t_delta_row_clears_by():        # A: the LLM's re-read replaces an API-rendered row's text and clears "by"
    d = settled()
    fc = J(d, "forecasts.json")
    fc["markets"].append({"question": "Which company has best AI model end of 2026?", "platform": "Polymarket",
                          "forecast": "74.5% — Anthropic · Google 10.5%", "category": "ranking", "relevantBenchmark": "other",
                          "resolveDate": "2026-12-31", "url": "https://polymarket.com/event/by-api-row", "asOf": "2026-09-20",
                          "by": "api"})
    with open(os.path.join(d, "forecasts.json"), "w") as f:
        f.write(M.dumps(fc))
    code, out = run(d, {"markets": [{"question": "Best AI model end of 2026?", "platform": "Polymarket",
                                     "forecast": "76% — Anthropic", "category": "ranking", "resolveDate": "2026-12-31",
                                     "url": "https://polymarket.com/event/by-api-row"}]})
    r = [m for m in J(d, "forecasts.json")["markets"] if m["url"].endswith("by-api-row")]
    check("delta_row_clears_by: the delta's text replaces the row, 'by' is removed, asOf = the sweep date",
          len(r) == 1 and "by" not in r[0] and r[0]["forecast"] == "76% — Anthropic"
          and r[0]["question"] == "Best AI model end of 2026?" and r[0]["asOf"] == "2026-09-28", r)


def t_radar_qh_year_windows():      # C: Q/H/year windows run to their period's end, then 30 days late, then drop
    items = [{"model": n, "lab": "X", "expectedWindow": w, "expectedDate": "2026-11", "prob": -1, "status": "expected",
              "basis": "b"} for n, w in [("Grok 4.8", "Q4 2026 (named, undated)"),
                                         ("DeepSeek V4.1 Pro", "H2 2026 (announced, undated)"),
                                         ("GPT-5.6 Sol Ultrafast (general availability)", "H2 2026"),
                                         ("Tencent Hy4 (general availability)", "H2 2026")]]
    res = {}
    for day in ("2026-12-01", "2026-12-31", "2027-01-01", "2027-01-30", "2027-01-31"):
        now = datetime(int(day[:4]), int(day[5:7]), int(day[8:]), 15, 0, tzinfo=M.ET)
        buf = io.StringIO()
        with redirect_stdout(buf):
            got, dropped = M.validate_releases(items, set(), now)
        res[day] = (len(got), [g.get("late") for g in got], len(dropped))
    check("radar_qh_year_windows: all 4 survive Dec 1 and Dec 31 (the deadline day is NOT late), are late Jan 1 and "
          "Jan 30, and drop Jan 31 2027",
          res["2026-12-01"] == (4, [False] * 4, 0) and res["2026-12-31"] == (4, [False] * 4, 0)
          and res["2027-01-01"] == (4, [True] * 4, 0) and res["2027-01-30"] == (4, [True] * 4, 0)
          and res["2027-01-31"] == (0, [], 4), res)


def t_prompt_no_empty_delta():      # round 4, item 2: the pulse is the heartbeat; an empty {} is a failed sweep (exit 4)
    txt = " ".join(open(PROMPT).read().split())
    told = [m.group(0) for m in re.finditer(r"(?:\bnever\s+)?\b(?:write|output|return|emit|produce)\s+(?:an?\s+)?"
                                           r"(?:empty\s+)?`?\{\s*\}`?", txt, re.I)
            if not m.group(0).lower().startswith("never")]
    check("prompt_no_empty_delta: the prompt never tells the model to write {}; it always writes at least the pulse",
          not told and "always write at least editorial.pulse, even when nothing else changed; never write an empty {}"
          in txt.lower(), told)


def _radar_at(items, day):
    now = datetime(int(day[:4]), int(day[5:7]), int(day[8:]), 12, 0, tzinfo=M.ET)
    out, dropped = M.validate_releases([dict(i) for i in items], set(), now, stamp_missing=False)
    return {r["model"]: r["late"] for r in out}, {m: why for m, why in dropped}


def t_window_offform():             # round 4, item 3: windows outside the forms read LENIENTLY
    table = [("early 2027", 2027, ("2027-04-30", "2027-04", "span")), ("mid-2027", 2027, ("2027-08-31", "2027-08", "span")),
             ("mid 2027", 2027, ("2027-08-31", "2027-08", "span")), ("late 2027", 2027, ("2027-12-31", "2027-12", "span")),
             ("spring 2027", 2027, ("2027-06-30", "2027-06", "span")), ("Summer 2027", 2027, ("2027-09-30", "2027-09", "span")),
             ("fall 2026", 2026, ("2026-12-31", "2026-12", "span")), ("autumn 2026", 2026, ("2026-12-31", "2026-12", "span")),
             ("Winter 2026", 2026, ("2027-02-28", "2027-02", "span")), ("winter 2027", 2027, ("2028-02-29", "2028-02", "span")),
             ("not before 2027", 2027, None), ("no earlier than Q2 2027", 2027, None), ("after 2026", 2027, None),
             ("beyond 2027", 2027, None)]
    bad = [(w, M.window_deadline(w, y), want) for w, y, want in table if M.window_deadline(w, y) != want]
    it = lambda n, w, ed: {"model": n, "lab": "X", "expectedWindow": w, "expectedDate": ed, "prob": -1,
                           "status": "rumored", "basis": "b", "source": "https://x.com/" + n}
    items = [it("Llama 6", "mid-2027", "2027-06"), it("Gemini 5", "early 2027", "2027-02"),
             it("GPT-7", "not before 2027", "2027-06")]                # skeptic3/radar_windows.py
    jan, oct_, sep = _radar_at(items, "2027-01-02"), _radar_at(items, "2027-10-15"), _radar_at(items, "2027-09-10")
    koa = [it("Koa GA", "Winter 2026", "2026-12")]
    koa_jan, koa_mar = _radar_at(koa, "2027-01-15"), _radar_at(koa, "2027-03-01")
    check("window_offform: early/mid/late, seasons (winter = Feb of the next year) and open-ended windows; on 2027-01-02 "
          "nothing is LATE (GPT-7 'not before 2027' was); by 2027-10-15 mid-2027 and early 2027 have lapsed 30 days and "
          "the open-ended one has passed its expectedDate; Winter 2026 is not late on Jan 15 2027",
          not bad and jan == ({"Llama 6": False, "Gemini 5": False, "GPT-7": False}, {})
          and oct_[0] == {} and oct_[1].get("Llama 6", "").startswith("window ended 2027-08-31")
          and oct_[1].get("Gemini 5", "").startswith("window ended 2027-04-30")
          and oct_[1].get("GPT-7", "").startswith("expectedDate 2027-06") and sep[0].get("Llama 6") is True
          and koa_jan == ({"Koa GA": False}, {}) and koa_mar == ({"Koa GA": True}, {}),
          (bad, jan, oct_, sep, koa_jan, koa_mar))


def t_stale_alarm_cleared():        # round 4, item 4: an early-returning merge must not leave the last alarm to re-fire
    d = settled()
    af = lambda: open(os.path.join(M.STATE_DIR, ".section_alarm")).read() \
        if os.path.exists(os.path.join(M.STATE_DIR, ".section_alarm")) else ""
    for i in range(8):
        run(d, {"editorial": {"pulse": "pulse %d" % i},
                "news": [dict(NEWS_OK, source="Reuters", url="https://www.reuters.com/%d" % i)]})
    eighth = af()
    code, out = run(d, "I could not finish the research this time.")
    check("stale_alarm_cleared: after 8 freeze sweeps ('news 8'), an unusable delta (exit 4) leaves .section_alarm empty",
          eighth == "news 8\n" and code == 4 and af() == "", (eighth, code, af()))


def t_radar_refused_freeze():       # round 4, item 7: a radar the 60% rule refuses sweep after sweep is a frozen section
    d = settled()
    af = lambda: open(os.path.join(M.STATE_DIR, ".section_alarm")).read() \
        if os.path.exists(os.path.join(M.STATE_DIR, ".section_alarm")) else ""
    one = [{"model": "Claude Haiku 5.5", "lab": "Anthropic", "expectedWindow": "by Oct 31", "expectedDate": "2026-10",
            "prob": 96, "status": "confirmed", "basis": "b", "source": "https://x.com/h"}]
    seen, out = [], ""
    for i in range(8):
        code, out = run(d, {"editorial": {"pulse": "pulse %d" % i}, "releases": one})
        seen.append(af())
    check("radar_refused_freeze: a 1-item radar refused 8 sweeps running (under 60% of 5 items) raises 'releases 8'",
          seen[-1] == "releases 8\n" and not any(seen[:7]) and "REFUSED" in out, (seen, out[-400:]))


def t_prune_undated_legacy():       # round 4, item 8 (revised): undated API rows go; undated no-API rows get 21 days
    met = {"question": "ARC-AGI-2 top score", "platform": "Metaculus", "forecast": "Community median 93.4",
           "resolveDate": "2026-12-31", "url": "https://www.metaculus.com/questions/41131/top-arc-agi-2-score-in-2026/"}
    rows = [{"question": "LMSYS #1", "platform": "Manifold", "forecast": "OpenAI 70% (xAI 45%)",
             "resolveDate": "2026-12-31", "url": "https://manifold.markets/a/who-will-ever-rank-1"},
            {"question": "Compute", "platform": "Epoch AI", "forecast": "4-5x/yr", "resolveDate": "2027-12-31",
             "url": "https://epoch.ai/trends", "kind": "expert", "curated": True},
            {"question": "Dated", "platform": "Manifold", "forecast": "6% — Yes", "resolveDate": "2026-12-31",
             "url": "https://manifold.markets/a/b", "asOf": "2026-09-27"}, met]
    keep, gone = M.prune_markets(copy.deepcopy(rows), "2026-09-28")
    kept_met = [m for m in keep if m["question"] == "ARC-AGI-2 top score"]
    check("prune_undated_legacy: the undated Manifold row goes (logged); the undated Metaculus row stays with "
          "seen=2026-09-28 and no asOf; the undated expert row and the dated row stay untouched",
          [m["question"] for m in keep] == ["Compute", "Dated", "ARC-AGI-2 top score"]
          and kept_met[0].get("seen") == "2026-09-28" and "asOf" not in kept_met[0] and "seen" not in keep[0]
          and [(m["question"], w[:8]) for m, w in gone] == [("LMSYS #1", "no asOf:")], (keep, gone))
    k21, g21 = M.prune_markets([dict(met, seen="2026-09-28")], "2026-10-19")
    k22, g22 = M.prune_markets([dict(met, seen="2026-09-28")], "2026-10-20")
    check("prune_undated_legacy: seen 2026-09-28 is kept on day 21 (2026-10-19) and dropped on day 22 (2026-10-20)",
          len(k21) == 1 and not g21 and not k22 and len(g22) == 1 and "undated since 2026-09-28" in g22[0][1], (g21, g22))
    legacy = [dict(rows[0], url="https://manifold.markets/a/%d" % i) for i in range(6)] + [rows[2], dict(met)]
    with redirect_stdout(io.StringIO()):                 # its "undated legacy file, kept" note
        keep2, gone2 = M.prune_markets(copy.deepcopy(legacy), "2026-09-28")
    keep3, gone3 = M.prune_markets(copy.deepcopy(rows), "2026-09-28", undated=False)
    check("prune_undated_legacy: 7 of 8 rows undated = a file the cleanup hasn't dated yet: all kept as is (no seen "
          "stamped), so the new merge can't wipe the un-cleaned live file; undated=False (cleanup --offline) keeps "
          "and stamps nothing",
          len(keep2) == 8 and not gone2 and not any("seen" in m for m in keep2)
          and len(keep3) == 4 and not gone3 and not any("seen" in m for m in keep3), (len(keep2), gone2, gone3))


def t_resupply_clears_seen():       # round 4, item 8 (revised): the LLM re-reading an undated row ends its grace period
    d = settled()
    fc = J(d, "forecasts.json")
    url = "https://www.metaculus.com/questions/5121/date-of-artificial-general-intelligence/"
    fc["markets"].append({"question": "Strong AGI date", "platform": "Metaculus", "forecast": "Median Mar 2033",
                          "category": "capability", "relevantBenchmark": "other", "resolveDate": "2033-03-01",
                          "url": url, "seen": "2026-09-20"})
    with open(os.path.join(d, "forecasts.json"), "w") as f:
        f.write(M.dumps(fc))
    code, out = run(d, {"markets": [{"question": "Strong AGI date", "platform": "Metaculus", "forecast": "Median Feb 2033",
                                     "category": "capability", "resolveDate": "2033-03-01", "url": url}]})
    row = [m for m in J(d, "forecasts.json")["markets"] if M.mkt_key(m["url"]) == "metaculus:5121"]
    check("resupply_clears_seen: the LLM re-supplying an undated Metaculus row stamps asOf and removes seen",
          len(row) == 1 and row[0].get("asOf") == "2026-09-28" and "seen" not in row[0]
          and row[0]["forecast"] == "Median Feb 2033", (row, out[-300:]))


CASES = [("malformed input", t_malformed), ("newModels validation", t_new_models),
         ("updatedModels validation", t_updated_models), ("prices", t_prices), ("benchmark aliases", t_bench_alias),
         ("market keys + dedupe", t_mkt_key), ("market pipeline", t_markets_merge), ("radar", t_radar),
         ("window_deadline", t_window_deadline), ("glossary", t_glossary), ("hosts + news", t_hosts),
         ("clock, sources, meta, pulse", t_clock_sources_meta), ("transactions", t_transactional),
         ("idempotency", t_idempotent),
         ("malformed_field_types", t_malformed_field_types), ("section_isolated", t_section_isolated),
         ("radar_late_not_rolled", t_radar_late_not_rolled), ("radar_late_baseline", t_radar_late_baseline),
         ("resolved_text_kept", t_resolved_text_kept), ("benchmark_zero", t_benchmark_zero),
         ("prompt_news_date", t_prompt_news_date), ("prompt_no_zero", t_prompt_no_zero),
         ("prompt_one_row_per_question", t_prompt_one_row_per_question),
         ("prompt_no_empty_delta", t_prompt_no_empty_delta), ("window_offform", t_window_offform),
         ("stale_alarm_cleared", t_stale_alarm_cleared), ("radar_refused_freeze", t_radar_refused_freeze),
         ("prune_undated_legacy", t_prune_undated_legacy), ("resupply_clears_seen", t_resupply_clears_seen),
         ("prompt_radar_late", t_prompt_radar_late),
         ("fenced_delta_usable", t_fenced_delta_usable), ("unusable_delta_exit4", t_unusable_delta_exit4),
         ("nothing_accepted_exit4", t_nothing_accepted_exit4), ("section_freeze_state", t_section_freeze_state),
         ("delta_row_clears_by", t_delta_row_clears_by), ("radar_qh_year_windows", t_radar_qh_year_windows)]

if __name__ == "__main__":
    only = sys.argv[1:]                 # python3 scripts/test_merge.py [case name ...]: run just those cases
    unknown = [n for n in only if n not in dict(CASES)]
    if unknown:
        print("unknown case(s): %s — known: %s" % (unknown, [n for n, _ in CASES]))
        sys.exit(2)
    for name, fn in CASES:
        if not only or name in only:
            case(name, fn)
    os.environ.pop("SWEEP_STARTED", None)
    print("ALL PASS (%d checks)" % len(results) if results and all(results)
          else "SOME FAILED (%d of %d)" % (results.count(False), len(results)))
    sys.exit(0 if results and all(results) else 1)
