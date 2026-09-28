"""Fixtures for scripts/oneshot_cleanup_2026_09_28.py: python3 scripts/test_oneshot_cleanup.py [case ...] (exit 0 = pass).
Runs the cleanup in-process on TEMP copies of a small fixture data dir, with market_sync's HTTP mocked (no network)."""
import hashlib, io, json, os, sys, tempfile, traceback
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import merge as M
import market_sync as MS
import oneshot_cleanup_2026_09_28 as OC
import test_merge as TM                 # fixture() only: its cases run under __main__

results = []
AGI_URL = "https://manifold.markets/%s/will-we-get-agi-before-2030"


def check(name, ok, detail=""):
    results.append(bool(ok))
    print("[%s] %s%s" % ("PASS" if ok else "FAIL", name, "" if ok or not detail else "\n     " + str(detail)[:1500]))


def case(name, fn):
    try:
        fn()
    except Exception:
        check(name, False, traceback.format_exc())


def data_dir():
    """TM's fixture, its markets replaced by three duplicates of one Manifold market (legacy rows: no asOf) and its
    glossary given the Circular / Vendor financing pair the duplicate rules would join."""
    d = TM.fixture()
    fc = json.load(open(os.path.join(d, "forecasts.json")))
    fc["markets"] = [
        {"question": "AGI before 2030 (a)", "platform": "Manifold", "forecast": "54% — Yes, up from 50",
         "category": "capability", "relevantBenchmark": "row-a", "resolveDate": "2029-12-31", "url": AGI_URL % "RemNi"},
        {"question": "AGI before 2030 (b)", "platform": "Manifold",
         "forecast": "41.5% - Yes, nudging up from 41%, so traders pushed probability out from 2028 rather than off the table",
         "category": "capability", "relevantBenchmark": "row-b", "resolveDate": "2030-01-01", "url": AGI_URL % "JoshYou"},
        {"question": "AGI before 2030 (c)", "platform": "Manifold",
         "forecast": "39% - Yes. Companion legs: 3% before 2027. Last confirmed read Aug 30.",
         "category": "capability", "relevantBenchmark": "row-c", "resolveDate": "2030-01-01", "url": AGI_URL % "RemNiflheim"}]
    with open(os.path.join(d, "forecasts.json"), "w") as f:
        f.write(M.dumps(fc))
    gl = json.load(open(os.path.join(d, "glossary.json")))
    gl["terms"] += [
        {"term": "Circular financing", "acronym": "", "category": "Economics & compute",
         "def": "Arrangements where a vendor funds a customer that then spends the money on the vendor's own products.",
         "aka": ["circular deals", "vendor financing", "round-tripping"]},
        {"term": "Vendor financing", "acronym": "", "category": "Economics & compute",
         "def": "A supplier lends to or invests in a customer so it can buy the supplier's products.",
         "aka": ["circular deal", "circular financing"]}]
    with open(os.path.join(d, "glossary.json"), "w") as f:
        f.write(M.dumps(gl))
    return d


def run(d):
    MS.PACE = 0
    MS.http_get = lambda url: (200, {"slug": "will-we-get-agi-before-2030", "creatorUsername": "RemNi",
                                     "question": "Will we get AGI before 2030?", "outcomeType": "BINARY",
                                     "probability": 0.535, "isResolved": False, "closeTime": 1898636340000})
    os.environ["SWEEP_STARTED"] = "2026-09-28T15:00:00-04:00"
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = OC.main([d])
    return code, buf.getvalue()


def t_dedupe_before_sync():         # F: collapse duplicates BEFORE the platform check, keeping the longest forecast
    d = data_dir()
    code, out = run(d)
    rows = json.load(open(os.path.join(d, "forecasts.json")))["markets"]
    check("dedupe_before_sync: 3 legacy duplicates -> 1 row, the one with the longest forecast (row b, not the last-in-file "
          "'Last confirmed read Aug 30'), then rendered from the API",
          code == 0 and len(rows) == 1 and rows[0]["relevantBenchmark"] == "row-b" and rows[0]["forecast"] == "53.5% — Yes"
          and rows[0].get("by") == "api", (rows, out[-800:]))


def t_glossary_do_not_merge():      # F: Circular financing and Vendor financing are different concepts
    d = data_dir()
    code, out = run(d)
    terms = {t["term"] for t in json.load(open(os.path.join(d, "glossary.json")))["terms"]}
    check("glossary_do_not_merge: 'Circular financing' and 'Vendor financing' both survive the cleanup",
          {"Circular financing", "Vendor financing"} <= terms, sorted(terms))


def t_idempotent():                 # F: a second run changes nothing
    d = data_dir()
    run(d)
    md5 = lambda: {f: hashlib.md5(open(os.path.join(r, f), "rb").read()).hexdigest()
                   for r, _ds, fs in os.walk(d) for f in fs}
    first = md5()
    code, out = run(d)
    check("idempotent: the second cleanup run leaves every file byte-identical", code == 0 and md5() == first, out[-600:])


LMSYS = "who-will-ever-rank-1-in-lmsys-chatb-zUZLSEsSNN"
MET = "https://www.metaculus.com/questions/%s/"
METR = "what-will-be-the-metr-time-horizon"


def legacy_dir():
    """Undated rows as they sit in the live file: the two unmapped Manifold rows (21 and 25 in the Sep 28 dry run), an
    expert row and a mappable market."""
    d = TM.fixture()
    fc = json.load(open(os.path.join(d, "forecasts.json")))
    fc["markets"] = [
        {"question": "Who will ever rank #1 in LMSYS Chatbot Arena text leaderboard in 2026?", "platform": "Manifold",
         "forecast": "OpenAI 70% (xAI 45%, DeepSeek 32%, Mistral 26%)", "category": "ranking", "relevantBenchmark": "other",
         "resolveDate": "2026-12-31", "url": "https://manifold.markets/Soli/" + LMSYS},
        {"question": "METR time-horizon doubling time in 2026?", "platform": "Manifold",
         "forecast": "3-3.5 mo = 32% (3.5-4mo 18%, 4-4.5mo 16%)", "category": "capability", "relevantBenchmark": "other",
         "resolveDate": "2026-12-31", "url": "https://manifold.markets/Jim/" + METR},
        {"question": "Frontier training compute", "platform": "Epoch AI", "forecast": "4-5x per year",
         "category": "capability", "relevantBenchmark": "other", "resolveDate": "2027-12-31", "url": "https://epoch.ai/trends"},
        {"question": "AGI before 2030", "platform": "Manifold", "forecast": "54% — Yes", "category": "capability",
         "relevantBenchmark": "other", "resolveDate": "2029-12-31", "url": AGI_URL % "RemNi"},
        {"question": "Top ARC-AGI-2 score achieved by any AI in 2026", "platform": "Metaculus",
         "forecast": "Community median 93.4 (50% CI 89.3–96.7). 737 forecasters.", "category": "benchmark",
         "relevantBenchmark": "ARC-AGI-2", "resolveDate": "2026-12-31", "url": MET % "41131/top-arc-agi-2-score-in-2026"},
        {"question": "GPT-6 release date?", "platform": "Metaculus", "forecast": "Median Jan 17 2028 — Metaculus (60 forecasters)",
         "category": "release", "relevantBenchmark": "other", "resolveDate": "2028-01-17",
         "url": MET % "39297/gpt-6-release-date"}]
    with open(os.path.join(d, "forecasts.json"), "w") as f:
        f.write(M.dumps(fc))
    return d


def run_routes(d, routes):
    MS.PACE = 0

    def get(url):
        v = routes.get(url)
        if isinstance(v, Exception):
            raise v
        if v is None:
            raise AssertionError("unexpected fetch: " + url)
        return v
    MS.http_get = get
    os.environ["SWEEP_STARTED"] = "2026-09-28T15:00:00-04:00"
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = OC.main([d])
    return code, buf.getvalue()


MF = MS.MANIFOLD_URL
ROUTES = {MF % LMSYS: (200, {"slug": LMSYS, "creatorUsername": "Soli", "question": "Who will ever rank #1?",
                              "outcomeType": "MULTIPLE_CHOICE", "isResolved": False, "closeTime": 1798714740000,
                              "answers": [{"text": "OpenAI", "probability": 0.7, "resolution": None},
                                          {"text": "xAI", "probability": 0.335, "resolution": None}]}),
          MF % METR: (200, {"slug": METR, "creatorUsername": "Jim", "question": "METR doubling time in 2026?",
                             "outcomeType": "MULTIPLE_CHOICE", "isResolved": False, "closeTime": 1798714740000,
                             "answers": [{"text": "3-3.5 mo", "probability": 0.32, "resolution": None},
                                         {"text": "3.5-4 mo", "probability": 0.18, "resolution": None}]}),
          MF % "will-we-get-agi-before-2030": (200, {"slug": "will-we-get-agi-before-2030", "creatorUsername": "RemNi",
                                                     "question": "Will we get AGI before 2030?", "outcomeType": "BINARY",
                                                     "probability": 0.535, "isResolved": False,
                                                     "closeTime": 1898636340000})}


def t_undated_rows_dropped():       # round 4, item 8 (revised): undated API rows go; undated Metaculus rows get 21 days
    d = legacy_dir()
    md5 = lambda: {f: hashlib.md5(open(os.path.join(r, f), "rb").read()).hexdigest()
                   for r, _ds, fs in os.walk(d) for f in fs}
    code, out = run_routes(d, ROUTES)
    first = md5()
    rows = json.load(open(os.path.join(d, "forecasts.json")))["markets"]
    by_url = {r["url"]: r for r in rows}
    met = [r for r in rows if "metaculus.com" in r["url"]]
    check("undated_rows_dropped: the two unmapped, undated Manifold rows are dropped and logged ('no asOf'); the undated "
          "Metaculus rows stay with seen=2026-09-28 and no asOf; the undated expert row is untouched; the mappable row "
          "is rendered and dated",
          code == 0 and not any(LMSYS in u or METR in u for u in by_url) and out.count("— no asOf: a legacy row") == 2
          and len(met) == 2 and all(r.get("seen") == "2026-09-28" and "asOf" not in r for r in met)
          and by_url["https://epoch.ai/trends"].get("kind") == "expert" and "seen" not in by_url["https://epoch.ai/trends"]
          and "asOf" not in by_url["https://epoch.ai/trends"]
          and by_url[AGI_URL % "RemNi"].get("by") == "api" and by_url[AGI_URL % "RemNi"].get("asOf") == "2026-09-28",
          (sorted(by_url), out[-900:]))
    code2, out2 = run_routes(d, ROUTES)
    check("undated_rows_dropped: a second cleanup the same day leaves every file byte-identical",
          code2 == 0 and md5() == first, out2[-600:])


def t_incomplete_check_writes_nothing():   # the undated prune must never catch a row the platform check didn't reach
    d = legacy_dir()
    md5 = lambda: {f: hashlib.md5(open(os.path.join(r, f), "rb").read()).hexdigest()
                   for r, _ds, fs in os.walk(d) for f in fs}
    before = md5()
    routes = dict(ROUTES)
    routes[MF % "will-we-get-agi-before-2030"] = MS.FetchError("timeout: The read operation timed out")
    code, out = run_routes(d, routes)
    check("incomplete_check_writes_nothing: one market timed out -> exit 1, 'NOT WRITTEN', every file byte-identical",
          code == 1 and "NOT WRITTEN" in out and md5() == before, (code, out[-500:]))


CASES = [("dedupe_before_sync", t_dedupe_before_sync), ("glossary_do_not_merge", t_glossary_do_not_merge),
         ("idempotent", t_idempotent), ("undated_rows_dropped", t_undated_rows_dropped),
         ("incomplete_check_writes_nothing", t_incomplete_check_writes_nothing)]

if __name__ == "__main__":
    only = sys.argv[1:]
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
