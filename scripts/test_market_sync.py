"""Fixtures for scripts/market_sync.py: python3 scripts/test_market_sync.py [case ...] (exit 0 = all pass).
HTTP is MOCKED (market_sync.http_get is replaced): no network, and every case runs on a TEMP forecasts.json.
Run it after any edit to market_sync.py (or to merge.py's market helpers)."""
import hashlib, io, json, os, re, shutil, sys, tempfile, traceback
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import market_sync as MS

TODAY = "2026-09-28"
results = []
DIRECTION = re.compile(r"\b(up|down|easing|eased|firming|flat|jump\w*|fell|fall\w*|rose|rising|cut|cooling|surged?|"
                       r"slipp\w*|holding|unchanged|nudg\w*|collapsed|from \d)", re.I)
API_FORECAST = re.compile(r"^\d+(\.\d+)?% — [^;]+$")


def check(name, ok, detail=""):
    results.append(bool(ok))
    print("[%s] %s%s" % ("PASS" if ok else "FAIL", name, "" if ok or not detail else "\n     " + str(detail)[:1500]))


def case(name, fn):
    try:
        fn()
    except Exception:
        check(name, False, traceback.format_exc())


# ---------------------------------------------------------------- payload builders (shapes copied from the live APIs)
def pm(title, yes, closed=False, end=None):
    return {"groupItemTitle": title, "question": "Q " + title, "closed": closed, "active": True, "endDate": end,
            "outcomes": '["Yes", "No"]', "outcomePrices": json.dumps([str(yes), str(round(1 - yes, 4))])}


def poly_event(slug, markets, closed=False, end="2027-01-01T04:59:00Z", title=None, volume=None):
    ev = {"slug": slug, "title": title or ("Title of " + slug), "closed": closed, "active": True, "archived": False,
          "endDate": end, "markets": markets}
    if volume is not None:
        ev["volume"] = volume
    return [ev]


def mani(slug, user="RealUser", prob=None, resolved=False, close_ms=1798714740000, answers=None, question=None,
         bettors=None, volume=None):
    b = {"slug": slug, "creatorUsername": user, "isResolved": resolved, "closeTime": close_ms,
         "outcomeType": "MULTIPLE_CHOICE" if answers else "BINARY", "question": question or ("Question of " + slug)}
    if bettors is not None:
        b["uniqueBettorCount"], b["volume"] = bettors, volume
    if answers:
        b["answers"] = [{"text": t, "probability": p, "resolution": r} for t, p, r in answers]
    else:
        b["probability"] = prob
    return b


def kal(ticker, legs, title=None):
    return {"event": {"event_ticker": ticker, "title": title or ("Event " + ticker)},
            "markets": [{"yes_sub_title": t, "status": st, "last_price_dollars": last, "yes_bid_dollars": bid,
                         "yes_ask_dollars": ask, "close_time": "2026-12-31T15:00:00Z"} for t, st, last, bid, ask in legs]}


P = MS.POLY_URL
MF = MS.MANIFOLD_URL
K = MS.KALSHI_URL


def row(q, platform, url, forecast, rd="2026-12-31", **kw):
    r = {"question": q, "platform": platform, "forecast": forecast, "category": "ranking", "relevantBenchmark": "other",
         "resolveDate": rd, "url": url}
    r.update(kw)
    return r


class Fake:
    """Replaces MS.http_get: url -> (status, body) | Exception instance to raise. Counts calls per url."""
    def __init__(self, routes):
        self.routes, self.calls = routes, []

    def __call__(self, url):
        self.calls.append(url)
        v = self.routes.get(url)
        if v is None:
            raise AssertionError("unexpected fetch: " + url)
        if isinstance(v, Exception):
            raise v
        return v


def sync(rows, routes, clock=None, today=TODAY):
    fake = Fake(routes)
    MS.http_get = fake
    kw = {"sleep": lambda s: None}
    if clock:
        kw["clock"] = clock
    rows_copy = json.loads(json.dumps(rows))            # sync must not mutate its input
    out, st, lines, ok = MS.sync(rows_copy, today, **kw)
    return out, st, lines, ok, fake


# ---------------------------------------------------------------- cases
def t_mixed():
    rows = [
        row("best 2026", "Polymarket", "https://polymarket.com/event/best-2026", "76% — Anthropic, up a point; Google 11%"),
        row("closed", "Polymarket", "https://polymarket.com/event/gpt-6-released-by", "99% — by Sep 15"),
        row("dead", "Polymarket", "https://polymarket.com/event/no-such-thing", "82% — Yes"),
        row("ended", "Polymarket", "https://polymarket.com/event/ended-one", "98% — Anthropic", rd="2026-09-30"),
        row("mani bin", "Manifold", "https://manifold.markets/WrongUser/agi-2030", "54% — Yes", rd="2029-12-31"),
        row("mani bin dup", "Manifold", "https://manifold.markets/Other/agi-2030", "41% — Yes"),
        row("mani resolved", "Manifold", "https://manifold.markets/u/gpt5-release", "97% — Yes"),
        row("mani gone", "Manifold", "https://manifold.markets/u/vanished", "50% — Yes"),
        row("mani mc", "Manifold", "https://manifold.markets/jim/arena-top", "64% — OpenAI, flat; xAI 32%"),
        row("mani mc vague", "Manifold", "https://manifold.markets/jim/arena-top-2", "70% — Yes"),
        row("kal settled", "Kalshi", "https://kalshi.com/markets/kxgpt/when/kxgpt-open", "67% — before 2027"),
        row("kal open", "Kalshi", "https://kalshi.com/markets/kxllm1/top/kxllm1-26dec31", "71.5% — Claude, easing"),
        row("kal gone", "Kalshi", "https://kalshi.com/markets/kxx/y/kxx-gone", "10% — Yes"),
        row("metaculus", "Metaculus", "https://www.metaculus.com/questions/5121/agi/", "50% by 2033", rd="2033-01-01"),
        row("expert", "Epoch AI", "https://epoch.ai/trends", "4-5x/yr", kind="expert", curated=True),
    ]
    routes = {
        P % "best-2026": (200, poly_event("best-2026", [pm("Anthropic", 0.745, end="2026-12-31T17:00:00Z"),
                                                        pm("Google", 0.105, end="2026-12-31T17:00:00Z")])),
        P % "gpt-6-released-by": (200, poly_event("gpt-6-released-by", [pm("September 15, 2026", 1.0, True)], closed=True)),
        P % "no-such-thing": (200, []),
        P % "ended-one": (200, poly_event("ended-one", [pm("Anthropic", 0.99, True)], end="2026-09-01T00:00:00Z")),
        MF % "agi-2030": (200, mani("agi-2030", user="RemNi", prob=0.5352, close_ms=1898636340000)),
        MF % "gpt5-release": (200, mani("gpt5-release", prob=0.99, resolved=True)),
        MF % "vanished": (404, {"message": "Contract not found"}),
        MF % "arena-top": (200, mani("arena-top", user="jim", answers=[("OpenAI", 0.61, None), ("Google", 1, "YES")])),
        MF % "arena-top-2": (200, mani("arena-top-2", user="jim", answers=[("OpenAI", 0.61, None), ("xAI", 0.3, None)])),
        K % "KXGPT-OPEN": (200, kal("KXGPT-OPEN", [("Before 2027", "finalized", "0.99", "0", "1"),
                                                  ("Before Oct 1", "settled", "0.99", "0", "1")])),
        K % "KXLLM1-26DEC31": (200, kal("KXLLM1-26DEC31", [("Claude", "active", "0.7580", "0.7570", "0.7580"),
                                                          ("Gemini", "active", "0.089", "0.087", "0.089")])),
        K % "KXX-GONE": (404, {"error": {"code": "not_found", "message": "not found"}}),
    }
    out, st, lines, ok, fake = sync(rows, routes)
    by = {r["question"]: r for r in out}
    check("drops: Polymarket closed / empty (dead) / every leg closed, Manifold resolved / not-found, Kalshi all-settled "
          "/ not_found; the second row of the one Manifold market goes as a duplicate question",
          st["dropped"] == 7 and st.get("duplicates") == 1 and len(out) == len(rows) - 8, (sorted(by), lines))
    b = by.get("Title of best-2026", {})
    check("Polymarket categorical: rendered from the API — question = the event title, forecast = '<pct>% — <leg>', "
          "resolveDate = that leg's date, asOf + by:api",
          b.get("forecast") == "74.5% — Anthropic" and b.get("resolveDate") == "2026-12-31" and b.get("asOf") == TODAY
          and b.get("by") == "api" and b.get("category") == "ranking" and b.get("url").endswith("best-2026"), b)
    m = by.get("Question of agi-2030", {})
    check("Manifold binary: '<pct>% — Yes' under the platform's question; url rebuilt from creatorUsername; resolveDate "
          "from closeTime", m.get("forecast") == "53.5% — Yes" and m.get("url") == "https://manifold.markets/RemNi/agi-2030"
          and m.get("resolveDate") == "2030-03-01" and m.get("by") == "api", m)
    check("duplicate rows of one market cost one fetch", fake.calls.count(MF % "agi-2030") == 1, fake.calls)
    mc = [r for r in out if r.get("url", "").endswith("/arena-top")][0]
    check("Manifold multiple choice: the named open answer is rendered; a 'Yes' label on a multi-answer market maps to "
          "nothing and the row stays byte-identical",
          mc.get("forecast") == "61% — OpenAI" and mc.get("question") == "Question of arena-top"
          and by["mani mc vague"] == rows[9], (mc, by.get("mani mc vague")))
    kl = by.get("Event KXLLM1-26DEC31", {})
    check("Kalshi: the named leg's bid/ask midpoint, rendered under the event title",
          kl.get("forecast") == "75.8% — Claude" and kl.get("by") == "api", kl)
    check("Metaculus + expert rows: never fetched, untouched",
          by["metaculus"] == rows[13] and by["expert"] == rows[14]
          and not any("metaculus" in c or "epoch" in c for c in fake.calls), fake.calls)
    check("stats: checked / rendered / unmapped / failed counted per row; write allowed",
          st["checked"] == 13 and st["rendered"] == 5 and st["unmapped"] == 1 and st["failed"] == 0 and ok, st)


def t_failures_leave_rows():
    rows = [row("rl", "Polymarket", "https://polymarket.com/event/a", "50% — Yes"),
            row("rl2", "Polymarket", "https://polymarket.com/event/b", "40% — Yes"),
            row("timeout", "Manifold", "https://manifold.markets/u/t", "30% — Yes"),
            row("garbage", "Manifold", "https://manifold.markets/u/g", "20% — Yes"),
            row("html404", "Manifold", "https://manifold.markets/u/h", "25% — Yes"),
            row("other slug", "Manifold", "https://manifold.markets/u/s", "35% — Yes"),
            row("shape", "Kalshi", "https://kalshi.com/markets/a/b/kx-shape", "10% — Yes"),
            row("ok1", "Kalshi", "https://kalshi.com/markets/a/b/kx-ok1", "10% — Claude"),
            row("ok2", "Kalshi", "https://kalshi.com/markets/a/b/kx-ok2", "10% — Claude"),
            row("ok3", "Kalshi", "https://kalshi.com/markets/a/b/kx-ok3", "10% — Claude"),
            row("ok4", "Kalshi", "https://kalshi.com/markets/a/b/kx-ok4", "10% — Claude"),
            row("ok5", "Kalshi", "https://kalshi.com/markets/a/b/kx-ok5", "10% — Claude")]
    ok_leg = [("Claude", "active", "0.5", "0.49", "0.51"), ("Other", "active", "0.1", "0.09", "0.11")]
    routes = {P % "a": (429, None),
              MF % "t": MS.FetchError("timeout: timed out"),
              MF % "g": (200, None),
              MF % "h": (404, None),
              MF % "s": (200, mani("somebody-else", prob=0.9)),
              K % "KX-SHAPE": (200, {"markets": []})}
    for i in range(1, 6):
        routes[K % ("KX-OK%d" % i)] = (200, kal("KX-OK%d" % i, ok_leg))
    out, st, lines, ok, fake = sync(rows, routes)
    by = {r["question"]: r for r in out}
    unchanged = [q for q in ("rl", "rl2", "timeout", "garbage", "html404", "other slug", "shape")
                 if by.get(q) != rows[[r["question"] for r in rows].index(q)]]
    check("429 / timeout / garbage JSON / non-JSON 404 / wrong market / wrong shape: rows left exactly as they were",
          not unchanged and st["failed"] == 6, (unchanged, lines))
    check("after a 429 the rest of that platform is skipped this run (not fetched, not a failure)",
          P % "b" not in fake.calls and st["limited"] == 1, (fake.calls, st))
    check("6 failures of 11 fetches is over half: the run must not write", st["fetches"] == 11 and not ok, st)
    rows2 = rows[7:] + [rows[3]]
    out2, st2, _l, ok2, _f = sync(rows2, routes)
    check("1 failure in 6 fetches: the good rows render and the write is allowed",
          ok2 and st2["rendered"] == 5 and st2["failed"] == 1 and out2[-1] == rows[3], st2)


def t_mass_dead():
    rows = [row("d%d" % i, "Polymarket", "https://polymarket.com/event/d%d" % i, "50% — Yes") for i in range(5)]
    rows.append(row("live", "Polymarket", "https://polymarket.com/event/live", "50% — Yes"))
    routes = {P % ("d%d" % i): (200, []) for i in range(5)}
    routes[P % "live"] = (200, poly_event("live", [pm("", 0.6)]))
    out, st, lines, ok, _f = sync(rows, routes)
    check("a wave of 'no such event' answers (5 of 6) is treated as an API problem: nothing dropped, nothing written",
          st["dropped"] == 0 and len(out) == 6 and not ok and any("treated as an API problem" in l for l in lines), (st, lines))
    rows2 = rows[:1] + [row("l%d" % i, "Polymarket", "https://polymarket.com/event/l%d" % i, "50% — Yes") for i in range(5)]
    for i in range(5):
        routes[P % ("l%d" % i)] = (200, poly_event("l%d" % i, [pm("", 0.6)]))
    out2, st2, _l, ok2, _f = sync(rows2, routes)
    check("a single dead url among live ones is still dropped", st2["dropped"] == 1 and ok2 and len(out2) == 5, st2)


def t_budget():
    ticks = iter([0, 0, 1, 500, 500, 500, 500, 500, 500, 500])   # t0, row0, row1, then past the budget
    rows = [row("b%d" % i, "Polymarket", "https://polymarket.com/event/b%d" % i, "50% — Yes") for i in range(4)]
    routes = {P % ("b%d" % i): (200, poly_event("b%d" % i, [pm("", 0.7)])) for i in range(4)}
    out, st, lines, ok, fake = sync(rows, routes, clock=lambda: next(ticks))
    check("time budget: rows not reached are left unchanged and are not failures",
          len(fake.calls) == 2 and st["late"] == 2 and st["failed"] == 0 and ok
          and out[2] == rows[2] and out[3] == rows[3] and out[0]["forecast"] == "70% — Yes", (fake.calls, st))


def t_headline_rules():
    table = [("76% — Anthropic, up a point; Google 11%", "anthropic"), ("99.5% - by Sep 15, settled", "by sep 15"),
             ("~97%.", ""), ("OpenAI 70% (xAI 45%)", None), ("3-3.5 mo = 32%", None), ("36% — odds of 1530+ Elo, up", "odds of 1530+ elo"),
             ("10% — for #1; 13% for top 3", "for #1"), ("27% — Z.ai, easing", "z.ai"), (None, None)]
    bad = [(fc, MS.lead_label(fc), want) for fc, want in table if MS.lead_label(fc) != want]
    check("lead_label table (%d forecasts)" % len(table), not bad, bad)
    c = lambda *titles: [(t, 0.5, True) for t in titles]
    picks = [("anthropic", c("Anthropic", "Google"), 0), ("odds of 1530+ elo", c("↑ 1510", "↑ 1530", "↑ 1540"), 1),
             ("by oct 31", c("October 15", "October 31", "December 31"), 1),
             ("by sep 30", c("September 30, 2026", "October 31, 2026"), 0),
             ("before 2028", c("Before Oct 1, 2027", "Before Jan 1, 2028"), 1),
             ("before sep 1", c("Before September", "Before October"), 0),
             ("by dec 31", c("December 31, 2025", "December 31, 2026"), None),
             ("for #1", c("#1", "#10", "#3"), 0), ("yes", c("Anthropic", "Google"), None),
             ("", c("A", "B"), None), ("anything", c("Only"), None)]
    badp = [(lab, [t for t, _p, _o in cands], MS.pick(lab, cands), want) for lab, cands, want in picks if MS.pick(lab, cands) != want]
    check("pick table (%d labels): date first, then exact, then one whole-word match — never a guess" % len(picks), not badp, badp)
    dates = [("2027-01-01T04:59:00Z", "2026-12-31"), ("2026-12-31T17:00:00.000Z", "2026-12-31"),
             ("2026-12-31", "2026-12-31"), ("2026-07-01T00:00:00+00:00", "2026-06-30"), ("garbage", None), (None, None)]
    badd = [(s, MS.et_date(s), want) for s, want in dates if MS.et_date(s) != want]
    check("et_date: API timestamps become America/New_York calendar dates", not badd, badd)


def t_main():
    d = tempfile.mkdtemp(prefix="market-sync-test-")
    MS.DATA = d
    MS.PACE = 0
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = MS.main([])
    check("main: no forecasts.json -> logged, exit 0, nothing created", code == 0 and "ERROR" in buf.getvalue()
          and os.listdir(d) == [], buf.getvalue())
    fc = {"updated": "x", "markets": [row("a", "Polymarket", "https://polymarket.com/event/a", "50% — Yes"),
                                      row("b", "Polymarket", "https://polymarket.com/event/b", "50% — Yes"),
                                      row("c", "Polymarket", "https://polymarket.com/event/c", "50% — Yes")],
          "historics": [1], "marketsStory": [{"h": "h", "t": "t"}]}
    path = os.path.join(d, "forecasts.json")
    with open(path, "w") as f:
        f.write(json.dumps(fc, indent=2))
    md5 = lambda: hashlib.md5(open(path, "rb").read()).hexdigest()
    before = md5()
    MS.http_get = Fake({P % "a": (500, None), P % "b": MS.FetchError("reset"), P % "c": (200, poly_event("c", [pm("", 0.8)]))})
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = MS.main([])
    check("main: >50% of fetches failed -> writes nothing, says so, exit 0",
          code == 0 and md5() == before and "SKIPPED" in buf.getvalue(), buf.getvalue())

    def boom(url):
        raise ZeroDivisionError("parser bug")
    MS.http_get = boom
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = MS.main([])
    check("main: an unexpected exception inside a fetch is a failure, never a crash", code == 0 and md5() == before, buf.getvalue())
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = MS.main(["--dry-rn"])
    check("main: an unknown flag exits 64 and does nothing", code == 64 and md5() == before, buf.getvalue())
    MS.http_get = Fake({P % "a": (200, poly_event("a", [pm("", 0.8)])), P % "b": (200, []),
                        P % "c": (200, poly_event("c", [pm("", 0.8)]))})
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = MS.main(["--dry-run"])
    check("main --dry-run: reports, writes nothing", code == 0 and md5() == before and "--dry-run" in buf.getvalue(), buf.getvalue())
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = MS.main([])
    new = json.load(open(path))
    check("main: changes written atomically (valid JSON, other keys kept, updated stamped, no .tmp left)",
          code == 0 and md5() != before and [r["question"] for r in new["markets"]] == ["Title of a", "Title of c"]
          and new["markets"][0]["forecast"] == "80% — Yes" and new["historics"] == [1] and new["updated"] != "x"
          and not [f for f in os.listdir(d) if f.endswith(".tmp")]
          and "3 checked · 1 dropped (closed/resolved/dead) · 2 rendered from the API · 0 unmapped (left as is) · 0 failed"
          in buf.getvalue(), buf.getvalue())
    shutil.rmtree(d)


# ---------------------------------------------------------------- round 1 (Sep 28 skeptic) regressions
def t_poly_stale_event_enddate():   # item 1: Polymarket's event endDate is stale; legs decide
    slug = "next-alibaba-qwen-plus-3pt8-released-byptptpt"
    url = "https://polymarket.com/event/" + slug
    ev = poly_event(slug, [pm("August 31", 0.0, True, "2026-09-01T03:59:00Z"),
                           pm("September 30", 0.1155, False, "2026-10-01T03:59:00Z"),
                           pm("September 15", 0.0, True, "2026-09-16T03:59:00Z"),
                           pm("December 31", 0.64, False, "2027-01-01T04:59:00Z"),
                           pm("October 31", 0.205, False, "2026-11-01T03:59:00Z")],
                    end="2026-10-01T03:59:00Z", title="Next Alibaba Qwen Plus 3.8 released by...?")
    rows = [row("qwen named leg", "Polymarket", url, "20% — by Oct 31", rd="2026-09-30"),
            row("qwen no leg named", "Polymarket", url, "64% — Yes", rd="2026-09-30")]
    out, st, lines, ok, _f = sync(rows, {P % slug: (200, ev)}, today="2026-10-02")
    a = [r for r in out if r.get("by") == "api"]
    b = [r for r in out if r.get("question") == "qwen no leg named"]
    check("poly_stale_event_enddate: an event past its (stale) endDate with open later legs is NOT dropped; the named "
          "leg is rendered and dates the row (Oct 31); a row naming no leg stays byte-identical",
          st["dropped"] == 0 and len(a) == 1 and a[0]["resolveDate"] == "2026-10-31"
          and a[0]["forecast"] == "20.5% — October 31" and a[0]["question"] == "Next Alibaba Qwen Plus 3.8 released by...?"
          and a[0]["asOf"] == "2026-10-02" and b == [rows[1]], (out, lines))


def t_poly_all_legs_closed():       # item 1: the drop is decided at leg level
    rows = [row("legs closed, event open", "Polymarket", "https://polymarket.com/event/x1", "90% — by Sep 15"),
            row("legs closed, event closed", "Polymarket", "https://polymarket.com/event/x2", "90% — by Sep 15")]
    routes = {P % "x1": (200, poly_event("x1", [pm("September 15", 1.0, True, "2026-09-16T03:59:00Z"),
                                                pm("October 31", 1.0, True, "2026-11-01T03:59:00Z")],
                                         closed=False, end="2027-01-01T04:59:00Z")),
              P % "x2": (200, poly_event("x2", [pm("September 15", 1.0, True, "2026-09-16T03:59:00Z")], closed=True))}
    out, st, lines, ok, _f = sync(rows, routes)
    check("poly_all_legs_closed: an event whose every leg is closed is dropped, whatever the event-level flags say",
          out == [] and st["dropped"] == 2 and all("every leg closed" in l for l in lines), (out, lines))


def t_negated_unchanged():          # item 5 (round 2: yes/no markets always map to YES)
    one = lambda slug: (200, poly_event(slug, [pm("", 0.07)], title="Will %s happen?" % slug))
    rows = [row("no agi", "Polymarket", "https://polymarket.com/event/n1", "93% — No AGI before 2027"),
            row("wont", "Polymarket", "https://polymarket.com/event/n2", "93% — won't ship by Oct 31"),
            row("not openai", "Polymarket", "https://polymarket.com/event/n3", "88% — Anthropic not OpenAI"),
            row("yes row", "Polymarket", "https://polymarket.com/event/n4", "5% — Yes")]
    out, st, lines, ok, _f = sync(rows, {P % "n1": one("n1"), P % "n2": one("n2"),
                                         P % "n3": (200, poly_event("n3", [pm("Anthropic", 0.8), pm("OpenAI", 0.1)])),
                                         P % "n4": one("n4")})
    by = {r["url"].split("/")[-1]: r for r in out}
    check("negated_unchanged: a yes/no market renders its YES side under the platform's own question whatever the "
          "LLM's label ('93% — No AGI…' -> '7% — Yes'); a negated claim on a multi-outcome market maps to nothing and "
          "stays byte-identical",
          all(by[s]["forecast"] == "7% — Yes" and by[s]["question"] == "Will %s happen?" % s for s in ("n1", "n2", "n4"))
          and by["n3"] == rows[2], [by[k] for k in sorted(by)])


def t_not_found_small_n():          # item 6: every row on a platform "not found" in one run = an API problem
    gone = (404, {"message": "Contract not found"})
    for n in (3, 2):
        rows = [row("m%d" % i, "Manifold", "https://manifold.markets/u/gone-%d" % i, "50% — Yes") for i in range(n)]
        out, st, lines, ok, _f = sync(rows, {MF % ("gone-%d" % i): gone for i in range(n)})
        check("not_found_small_n: %d of %d Manifold rows 'not found' in one run -> none dropped" % (n, n),
              st["dropped"] == 0 and out == rows and any("treated as an API problem" in l for l in lines), (st, lines))


def t_refresh_strips_relative():    # item 9b (round 2: the whole forecast comes from the API, so no stale prose at all)
    rows = [row("sept", "Polymarket", "https://polymarket.com/event/s1",
                "99.7% — Anthropic with two days left; every rival under 1%"),
            row("today", "Polymarket", "https://polymarket.com/event/s2", "82% - today, Sep 3, easing from 84.5%"),
            row("plain", "Polymarket", "https://polymarket.com/event/s3", "50% — Yes, flat")]
    out, st, lines, ok, _f = sync(rows, {P % "s1": (200, poly_event("s1", [pm("Anthropic", 0.745), pm("Google", 0.1)])),
                                         P % "s2": (200, poly_event("s2", [pm("", 0.6)])),
                                         P % "s3": (200, poly_event("s3", [pm("", 0.55)]))})
    by = {r["url"].split("/")[-1]: r["forecast"] for r in out}
    check("refresh_strips_relative: no relative-time or movement prose survives a re-read",
          by == {"s1": "74.5% — Anthropic", "s2": "60% — Yes", "s3": "55% — Yes"}, by)


# ---------------------------------------------------------------- round 2 (second skeptic) regressions
BY_WHEN_AGI = {"slug": "by-when-will-we-have-agi", "question": "By when will we have AGI?", "outcomeType": "MULTIPLE_CHOICE",
               "isResolved": False, "closeTime": 1966564740000, "creatorUsername": "2s",
               "answers": [{"text": t, "probability": p, "resolution": None} for t, p in
                           [("2024 (we have it)", 0.01), ("2025", 0.0104), ("2026", 0.0386), ("2027", 0.28), ("2028", 0.5),
                            ("2029", 0.6923), ("2030", 0.76), ("2031", 0.77), ("2032", 0.8), ("2033 or later", 0.9)]]}


def t_api_render_claim_layer():     # A: a mapped row is rendered ENTIRELY from the API; an unmapped row is byte-identical
    rows = [row("which lab leads", "Polymarket", "https://polymarket.com/event/best-2026",
                "75.8% — Anthropic, easing from 77; Google 11%, OpenAI 9%; last confirmed read Aug 30"),
            row("gemini ladder", "Polymarket", "https://polymarket.com/event/gem-ladder",
                "78.5% — by Oct 31, a point off; Oct 23 79% on thin volume"),
            row("ipo", "Polymarket", "https://polymarket.com/event/ipo-first", "94.9% — Anthropic first; $386K volume"),
            row("agi binary", "Manifold", "https://manifold.markets/x/agi-2030", "53.5% - Yes. Companion legs: 3% before 2027"),
            row("chatbot mc", "Manifold", "https://manifold.markets/jim/arena-top", "64% — OpenAI, flat; xAI fell to 32% from 48"),
            row("kalshi llm", "Kalshi", "https://kalshi.com/markets/kxllm1/top/kxllm1-26dec31",
                "75.8% — Claude, easing from 74; ChatGPT 10.8%, Gemini 8.9%"),
            row("no lead %", "Manifold", "https://manifold.markets/h/who-ever-1", "OpenAI 70% (xAI 45%, DeepSeek 32%)"),
            row("vague label", "Polymarket", "https://polymarket.com/event/best-2026", "70% — the favourite, firming")]
    routes = {
        P % "best-2026": (200, poly_event("best-2026", [pm("Anthropic", 0.745, end="2026-12-31T17:00:00Z"),
                                                        pm("Google", 0.105, end="2026-12-31T17:00:00Z"),
                                                        pm("OpenAI", 0.085, end="2026-12-31T17:00:00Z"),
                                                        pm("Company A", 0.001, True, "2026-12-31T00:00:00Z")],
                                          title="Which company has best AI model end of 2026?")),
        P % "gem-ladder": (200, poly_event("gem-ladder", [pm("October 15", 0.45, end="2026-10-16T03:59:00Z"),
                                                          pm("October 31", 0.785, end="2026-11-01T03:59:00Z"),
                                                          pm("December 31", 0.9, end="2027-01-01T04:59:00Z")],
                                           title="Next Google Gemini Pro Model released by...?")),
        P % "ipo-first": (200, [{"slug": "ipo-first", "title": "Will Anthropic or OpenAI IPO first?", "closed": False,
                                 "markets": [{"groupItemTitle": "", "closed": False, "active": True,
                                              "endDate": "2028-01-01T04:59:00Z", "outcomes": '["Anthropic", "OpenAI"]',
                                              "outcomePrices": '["0.949", "0.051"]'}]}]),
        MF % "agi-2030": (200, mani("agi-2030", user="RemNi", prob=0.5352, close_ms=1898636340000,
                                    question="Will we get AGI before 2030?")),
        MF % "arena-top": (200, mani("arena-top", user="jim", question="Which Companies will top Chatbot Arena in 2026?",
                                     answers=[("OpenAI", 0.64, None), ("xAI", 0.323, None), ("DeepSeek", 0.137, None),
                                              ("Google", 1, "YES")])),
        K % "KXLLM1-26DEC31": (200, kal("KXLLM1-26DEC31", [("Claude", "active", "0.758", "0.757", "0.758"),
                                                          ("ChatGPT", "active", "0.113", "0.11", "0.116"),
                                                          ("Gemini", "active", "0.094", "0.092", "0.096"),
                                                          ("Grok", "active", "0.0145", "0.014", "0.015")],
                                        title="Best AI at the end of 2026?")),
        MF % "who-ever-1": (200, mani("who-ever-1", answers=[("OpenAI", 0.7, None), ("xAI", 0.33, None)])),
    }
    out, st, lines, ok, _f = sync(rows, routes)
    titles = {"best-2026": "Which company has best AI model end of 2026?",
              "gem-ladder": "Next Google Gemini Pro Model released by...?", "ipo-first": "Will Anthropic or OpenAI IPO first?",
              "agi-2030": "Will we get AGI before 2030?", "arena-top": "Which Companies will top Chatbot Arena in 2026?",
              "kxllm1-26dec31": "Best AI at the end of 2026?"}
    api = [r for r in out if r.get("by") == "api"]
    bad = [r for r in api if not API_FORECAST.match(r["forecast"]) or DIRECTION.search(r["forecast"])
           or r["question"] != titles.get(r["url"].split("/")[-1].lower())]
    unmapped = [r for r in out if r.get("by") != "api"]
    check("api_render_claim_layer: every by=api row is '<pct>% — <outcome>[ · companions]' with no direction words under "
          "the platform's own title; every unmapped row is byte-identical to its input",
          len(api) == 6 and not bad and unmapped == [rows[6], rows[7]], (bad, unmapped))
    f = {r["url"].split("/")[-1].lower(): r["forecast"] for r in api}
    check("api_render_claim_layer: categorical adds up to 2 more open outcomes by price, a date ladder and a two-outcome "
          "market don't; Kalshi uses the midpoint",
          f == {"best-2026": "74.5% — Anthropic · Google 10.5% · OpenAI 8.5%", "gem-ladder": "78.5% — October 31",
                "ipo-first": "94.9% — Anthropic", "agi-2030": "53.5% — Yes",
                "arena-top": "64% — OpenAI · xAI 32.3% · DeepSeek 13.7%",
                "kxllm1-26dec31": "75.8% — Claude · ChatGPT 11.3% · Gemini 9.4%"}, f)


def t_binary_maps_to_yes():         # A: a yes/no market's row states its YES side, whatever the LLM wrote
    rows = [row("unlikely", "Polymarket", "https://polymarket.com/event/agi-2027", "82.5% — unlikely before 2027")]
    out, st, lines, ok, _f = sync(rows, {P % "agi-2027": (200, poly_event("agi-2027", [pm("", 0.175)],
                                                                          title="OpenAI announces AGI before 2027?"))})
    check("binary_maps_to_yes: '82.5% — unlikely before 2027' becomes '17.5% — Yes' under the platform's own question",
          out and out[0]["forecast"] == "17.5% — Yes" and out[0]["question"] == "OpenAI announces AGI before 2027?", out)


def t_pick_by_when_agi():           # A: the live Manifold "By when will we have AGI?" cases
    rows = [row("r28", "Manifold", "https://manifold.markets/2s/by-when-will-we-have-agi", "28% — before 2028"),
            row("r4", "Manifold", "https://manifold.markets/2s/by-when-will-we-have-agi", "4% — before 2027"),
            row("r50", "Manifold", "https://manifold.markets/2s/by-when-will-we-have-agi", "50% — by 2028")]
    out, st, lines, ok, _f = sync(rows, {MF % "by-when-will-we-have-agi": (200, BY_WHEN_AGI)})
    by = {r.get("forecast"): r for r in out}
    check("pick_by_when_agi: '28% — before 2028' does not become 50%, '4% — before 2027' does not become 28% (both stay "
          "untouched); '50% — by 2028' maps to the '2028' answer",
          out[0] == rows[0] and out[1] == rows[1] and out[2].get("forecast") == "50% — 2028" and out[2].get("by") == "api",
          out)


def t_leg_resolved_drop():          # A: the row's own leg has closed (other legs open) -> the row goes
    rows = [row("math arena", "Polymarket", "https://polymarket.com/event/math-arena", "50% — 1550+ (1525+ ~94%)")]
    ev = poly_event("math-arena", [pm("1525", 1.0, True, "2026-12-31T00:00:00Z"), pm("1550", 1.0, True, "2026-12-31T00:00:00Z"),
                                   pm("1575", 0.52, False, "2027-01-01T04:59:00Z"), pm("1600", 0.0535, False, "2027-01-01T04:59:00Z")])
    out, st, lines, ok, _f = sync(rows, {P % "math-arena": (200, ev)})
    check("leg_resolved_drop: '50% — 1550+' on a leg closed at p=1.0 is dropped even though 1575/1600 are open",
          out == [] and st["dropped"] == 1 and any("leg resolved" in l for l in lines), (out, lines))


def t_et_date_named_day():          # A: the calendar date a leg names, not a UTC artefact either way
    ev = poly_event("dates", [pm("Company A", 0.3, end="2026-12-31T00:00:00Z"), pm("Company B", 0.2, end="2026-12-31T00:00:00Z"),
                              pm("October 31", 0.4, end="2026-11-01T03:59:00Z")], title="Dates?")
    rows = [row("a", "Polymarket", "https://polymarket.com/event/dates", "30% — Company A", rd="2027-06-30"),
            row("oct", "Polymarket", "https://polymarket.com/event/dates", "40% — by Oct 31", rd="2027-06-30")]
    rd = [r.get("resolveDate") for one in rows for r in sync([one], {P % "dates": (200, ev)})[0]]   # one sync per row:
    # both rows render to the event's one question, and the question dedupe keeps one row per question
    man = MS.et_date("2026-10-01T00:00:00Z")
    check("et_date_named_day: a Polymarket leg ending 2026-12-31T00:00:00Z resolves Dec 31 (not Dec 30); one ending "
          "2026-11-01T03:59Z ('October 31') resolves Oct 31 (not endDateIso's Nov 1); Manifold's 2026-10-01T00:00Z "
          "close ('before October 1') stays Sep 30",
          rd == ["2026-12-31", "2026-10-31"] and man == "2026-09-30", (rd, man))


def t_api_rows_remap():             # A: a row rendered from the API must map again next sweep (or its asOf ages out)
    rows = [row("which lab leads", "Polymarket", "https://polymarket.com/event/best-2026", "75% — Anthropic, easing"),
            row("kalshi agi", "Kalshi", "https://kalshi.com/markets/kxagico/agi/kxagico-comp", "64% — before 2028, cooling"),
            row("ladder", "Polymarket", "https://polymarket.com/event/gem-ladder", "78% — by Oct 31"),
            row("thresholds", "Polymarket", "https://polymarket.com/event/arena", "36% — odds of 1530+ Elo")]
    routes = {
        P % "best-2026": (200, poly_event("best-2026", [pm("Anthropic", 0.745), pm("Google", 0.105), pm("OpenAI", 0.085)])),
        K % "KXAGICO-COMP": (200, kal("KXAGICO-COMP", [("Before Jan 1, 2027", "active", "0.175", "0.17", "0.18"),
                                                      ("Before Jan 1, 2028", "active", "0.645", "0.64", "0.65"),
                                                      ("Before Jan 1, 2029", "active", "0.795", "0.79", "0.80")])),
        P % "gem-ladder": (200, poly_event("gem-ladder", [pm("October 15", 0.45, end="2026-10-16T03:59:00Z"),
                                                          pm("October 31", 0.785, end="2026-11-01T03:59:00Z")])),
        P % "arena": (200, poly_event("arena", [pm("↑ 1530", 0.35), pm("↑ 1540", 0.166), pm("↑ 1550", 0.13)]))}
    out1, st1, _l, _ok, _f = sync(rows, routes)
    out2, st2, lines2, _ok, _f = sync(out1, routes, today="2026-09-29")
    check("api_rows_remap: every row rendered from the API maps again on the next sweep (companions and commas in the "
          "platform's own labels don't break it) and gets that day's asOf",
          st1["rendered"] == 4 and st2["rendered"] == 4 and st2["unmapped"] == 0
          and all(r.get("asOf") == "2026-09-29" for r in out2)
          and [r["forecast"] for r in out2] == [r["forecast"] for r in out1], (st2, lines2, [r["forecast"] for r in out1]))


def t_llm_fallback_form_maps():      # A: the prompt's own "NN% — <outcome>" form must map, commas and all
    kal_agi = kal("KXAGICO-COMP", [("Before Jan 1, 2027", "active", "0.175", "0.17", "0.18"),
                                   ("Before Jan 1, 2028", "active", "0.645", "0.64", "0.65"),
                                   ("Before Jan 1, 2029", "active", "0.795", "0.79", "0.80")])
    llm = kal("KXLLM1-26DEC31", [("Claude", "active", "0.76", "0.75", "0.77"), ("ChatGPT", "active", "0.112", "0.11", "0.12"),
                                 ("Gemini", "active", "0.093", "0.09", "0.10")])
    rows = [row("agi", "Kalshi", "https://kalshi.com/markets/kxagico/agi/kxagico-comp", "64% — Before Jan 1, 2028"),
            row("best", "Polymarket", "https://polymarket.com/event/best-2026", "75% — Anthropic · Google 10.5%"),
            row("prose", "Kalshi", "https://kalshi.com/markets/kxllm1/top/kxllm1-26dec31",
                "71.5% — Anthropic's model, easing; ChatGPT 10.8%"),
            row("none", "Polymarket", "https://polymarket.com/event/nobody", "12% — None of these")]
    routes = {K % "KXAGICO-COMP": (200, kal_agi), K % "KXLLM1-26DEC31": (200, llm),
              P % "best-2026": (200, poly_event("best-2026", [pm("Anthropic", 0.745), pm("Google", 0.105), pm("OpenAI", 0.085)])),
              P % "nobody": (200, poly_event("nobody", [pm("OpenAI", 0.5), pm("Google", 0.38), pm("None of these", 0.12)]))}
    out, st, lines, _ok, _f = sync(rows, routes)
    fc = [r["forecast"] for r in out]
    check("llm_fallback_form_maps: LLM rows in the prompt's form map by the platform's WHOLE label (a comma inside "
          "'Before Jan 1, 2028', companions copied from the app, an outcome that merely looks negated), and prose whose "
          "lead is no outcome is never matched by a later mention ('Anthropic's model ... ChatGPT' stays unmapped)",
          fc[0] == "64.5% — Before Jan 1, 2028" and fc[1].startswith("74.5% — Anthropic · ")
          and fc[2] == rows[2]["forecast"] and out[2].get("by") is None
          and fc[3].startswith("12% — None of these") and st["rendered"] == 3 and st["unmapped"] == 1, (fc, st, lines))


MAR_1_2027 = 1803898740000        # 2027-03-02T04:59Z = Mar 1 11:59 pm ET (mani's default close is Dec 31 2026 ET)


def _kept(out, url):
    return any(r.get("url") == url for r in out)


def t_dup_question_pairs():         # one row per question per platform: the two live pairs
    q, arc = "Will we get AGI before 2027?", "Top ARC-AGI-2 score achieved by any AI in 2026"
    big, small = "https://manifold.markets/RemNi/agi-2027-a", "https://manifold.markets/Mario/agi-2027-b"
    m41131, m31287 = ("https://www.metaculus.com/questions/41131/top-arc-agi-2-score-in-2026/",
                      "https://www.metaculus.com/questions/31287/")
    met = [row(arc, "Metaculus", m41131, "Community median 93.4 (50% CI 89.3–96.7). 737 forecasters."),
           row(arc, "Metaculus", m31287, "93.4 - community median (50% CI 89.3-96.7), 737 forecasters.")]
    # as in the live data: the big Manifold market (334 traders) first, closing later than the small one (69)
    routes = {MF % "agi-2027-a": (200, mani("agi-2027-a", user="RemNi", prob=0.0226, close_ms=MAR_1_2027, question=q,
                                            bettors=334, volume=276812.4)),
              MF % "agi-2027-b": (200, mani("agi-2027-b", user="Mario", prob=0.0604, question=q, bettors=69,
                                            volume=8453.9))}
    rows = [row("AGI 2027 (a)", "Manifold", big, "2% — Yes"), met[0], row("AGI 2027 (b)", "Manifold", small, "6% — Yes"),
            met[1]]
    out, st, lines, ok, _f = sync(rows, routes)
    live_order = (len(out) == 2 and _kept(out, big) and _kept(out, m41131) and st.get("duplicates") == 2
                  and "duplicate question: kept %s, dropped %s" % (big, small) in lines
                  and "duplicate question: kept %s, dropped %s" % (m41131, m31287) in lines
                  and [r["forecast"] for r in out if r["url"] == big] == ["2.3% — Yes"])
    # swapped: the big market SECOND and closing EARLIER, so only the traders/volume rule can keep it
    routes2 = {MF % "agi-2027-a": (200, mani("agi-2027-a", user="RemNi", prob=0.0226, question=q, bettors=334,
                                             volume=276812.4)),
               MF % "agi-2027-b": (200, mani("agi-2027-b", user="Mario", prob=0.0604, close_ms=MAR_1_2027, question=q,
                                             bettors=69, volume=8453.9))}
    out2, st2, lines2, _ok, _f = sync([rows[2], rows[0]], routes2)
    check("dup_question_pairs: Manifold's two 'Will we get AGI before 2027?' markets collapse to the one with more "
          "traders (kept whether it comes first or second, closing later or earlier); Metaculus 41131 / 31287 (same "
          "question, same stats, no API size) collapse to the first; each drop logged 'duplicate question: kept <url>, "
          "dropped <url>'",
          live_order and len(out2) == 1 and _kept(out2, big) and st2.get("duplicates") == 1,
          (st.get("duplicates"), lines, [r.get("url") for r in out], lines2, [r.get("url") for r in out2]))


def t_dup_question_rules():         # the survivor order: rendered now > bigger market > later resolveDate > first
    # the unmapped row comes first, is the BIGGER market and has the later resolveDate: only "rendered from the API
    # this run" can keep the other one. Its question differs only in case and punctuation.
    rows = [row("Which company has the best AI model end of 2026?", "Polymarket", "https://polymarket.com/event/best-a",
                "OpenAI 70% (xAI 45%)", rd="2027-06-30"),
            row("best b", "Polymarket", "https://polymarket.com/event/best-b", "75% — Anthropic"),
            row("ARC-AGI-3 top score, end of 2026", "Metaculus", "https://www.metaculus.com/questions/1/", "40", rd="2026-12-31"),
            row("ARC-AGI-3 top score — end of 2026?", "Metaculus", "https://www.metaculus.com/questions/2/", "41", rd="2027-01-31")]
    legs = [pm("Anthropic", 0.745), pm("Google", 0.105), pm("OpenAI", 0.085)]
    routes = {P % "best-a": (200, poly_event("best-a", legs, title="Which company has the best AI model end of 2026?",
                                             volume=9e6)),
              P % "best-b": (200, poly_event("best-b", legs, title="Which Company Has The BEST AI model, end of 2026?",
                                             volume=1e3))}
    out, st, lines, ok, _f = sync(rows, routes)
    urls = [r.get("url") for r in out]
    check("dup_question_rules: a row rendered from the API beats an unmapped one (even a bigger, later, earlier-listed "
          "one); with no API size the later resolveDate wins; questions match across case and punctuation",
          urls == ["https://polymarket.com/event/best-b", "https://www.metaculus.com/questions/2/"]
          and st.get("duplicates") == 2, (urls, lines))


def t_dup_cross_platform_kept():    # the same question on two platforms is information, not a duplicate
    q = "When will OpenAI achieve AGI?"
    rows = [row("p", "Polymarket", "https://polymarket.com/event/oai-agi", "20% — Before 2027"),
            row("k", "Kalshi", "https://kalshi.com/markets/oaiagi/when/oaiagi", "18% — Before 2027"),
            row(q, "Metaculus", "https://www.metaculus.com/questions/3/", "Median 2029")]
    routes = {P % "oai-agi": (200, poly_event("oai-agi", [pm("Before 2027", 0.2), pm("Before 2028", 0.45)], title=q)),
              K % "OAIAGI": (200, kal("OAIAGI", [("Before 2027", "active", "0.18", "0.17", "0.19"),
                                                 ("Before 2028", "active", "0.45", "0.44", "0.46")], title=q))}
    out, st, lines, ok, _f = sync(rows, routes)
    check("dup_cross_platform_kept: a Polymarket, a Kalshi and a Metaculus row with the same question all survive",
          len(out) == 3 and [r["question"] for r in out] == [q, q, q] and not st.get("duplicates"), (out, lines))


def t_dup_expert_exempt():          # expert (curated) rows are never deduped
    q = "Frontier training compute by 2027"
    rows = [row(q, "Epoch AI", "https://epoch.ai/trends", "4-5x/yr", kind="expert", curated=True),
            row(q, "Epoch AI", "https://epoch.ai/data/notable-ai-models", "1e27 by 2027", kind="expert", curated=True)]
    out, st, lines, ok, _f = sync(rows, {})
    check("dup_expert_exempt: two expert rows with the same question on the same platform both survive, untouched",
          out == rows and not st.get("duplicates"), (out, lines))


def t_dedupe_transient_keeps_rows():   # round 4, item 1: a row is only ever deleted on a platform's definitive answer
    q = "Will we get AGI before 2027?"
    big, small = "https://manifold.markets/RemNi/agi-2027-a", "https://manifold.markets/Mario/agi-2027-b"
    stored = row(q, "Manifold", big, "2.3% — Yes", rd="2027-03-01", asOf="2026-09-27", by="api")   # rendered last sweep
    added = row(q, "Manifold", small, "6% — Yes", asOf="2026-09-28")                                # appended by merge
    ok_big = (200, mani("agi-2027-a", user="RemNi", prob=0.0226, close_ms=MAR_1_2027, question=q, bettors=334,
                        volume=276812.4))
    ok_small = (200, mani("agi-2027-b", user="Mario", prob=0.0604, question=q, bettors=69, volume=8453.9))
    timeout = MS.FetchError("timeout: The read operation timed out")
    healthy, st_h, _l, _ok, _f = sync([stored, added], {MF % "agi-2027-a": ok_big, MF % "agi-2027-b": ok_small})
    runs = {"timeout": sync([stored, added], {MF % "agi-2027-a": timeout, MF % "agi-2027-b": ok_small}),
            "429": sync([added, stored], {MF % "agi-2027-a": (429, None), MF % "agi-2027-b": ok_small}),
            "time budget": sync([added, stored], {MF % "agi-2027-a": ok_big, MF % "agi-2027-b": ok_small},
                                clock=lambda _t=iter([0, 0, 500, 500, 500]): next(_t))}
    kept = {k: (sorted(r["url"] for r in v[0]), v[1].get("duplicates"), v[3]) for k, v in runs.items()}
    check("dedupe_transient_keeps_rows: a healthy sweep collapses the pair to the bigger market; a sweep in which one of "
          "them timed out, hit a 429 or missed the time budget keeps BOTH rows (the stored one untouched)",
          [r["url"] for r in healthy] == [big] and st_h.get("duplicates") == 1
          and all(v == (sorted([big, small]), 0, True) for v in kept.values())
          and all(stored in v[0] for v in runs.values()), (kept, [r["url"] for r in healthy]))


def t_leg_date_year():              # round 4, item 5: a titled leg's day in the year nearest its end stamp
    table = [("December 31", "2027-01-01T00:00:00Z", "2026-12-31"),   # the skeptic's case (was 2027-12-31)
             ("December 31", "2026-01-31T00:00:00Z", "2026-12-31"),   # live open legs, Sep 28: nicols-maduro-released-,
             ("December 31", "2026-03-31T00:00:00Z", "2026-12-31"),   # cilia-flores-released-, us-strike-on-colombia-
             ("October 31", "2026-11-01T03:59:00Z", "2026-10-31"),    # (stamped Jan 31) and venezuela-presidential-
             ("October 9", "2026-10-15T16:00:00Z", "2026-10-15"),     # election-scheduled-by (stamped Mar 31)
             ("December 31", "2026-01-01T00:00:00Z", "2025-12-31"),   # hyperliquid-airdop-by (closed; was 2026-12-31)
             ("June 30, 2026", "2025-12-31T12:00:00Z", "2026-06-30")]
    bad = [(t, s, MS.leg_date(t, s), want) for t, s, want in table if MS.leg_date(t, s) != want]
    ev = poly_event("colombia", [pm("January 31", 0.0, True, "2026-01-31T00:00:00Z"),
                                 pm("March 31", 0.0, True, "2026-01-31T00:00:00Z"),
                                 pm("December 31", 0.165, False, "2026-01-31T00:00:00Z")], end="2026-01-31T00:00:00Z")
    out = sync([row("c", "Polymarket", "https://polymarket.com/event/colombia", "3% — December 31")],
               {P % "colombia": (200, ev)})[0]
    check("leg_date_year: 'December 31' ending 2027-01-01T00:00Z is Dec 31 2026; the 4 open year-crossing legs stamped "
          "on their ladder's first deadline stay Dec 31 2026 (the live colombia event renders '16.5% — December 31', "
          "resolving 2026-12-31)",
          not bad and [(r["forecast"], r["resolveDate"]) for r in out] == [("16.5% — December 31", "2026-12-31")],
          (bad, out))


def t_single_leg_label():           # round 4, item 6: a one-market event keeps its leg's own label
    rows = [row("h", "Polymarket", "https://polymarket.com/event/haiku-oct", "95% — Yes"),
            row("k", "Kalshi", "https://kalshi.com/markets/kxone/x/kxone-26", "45% — Yes"),
            row("p", "Polymarket", "https://polymarket.com/event/plain", "20% — Yes")]
    routes = {P % "haiku-oct": (200, poly_event("haiku-oct", [pm("October 31", 0.95, end="2026-11-01T03:59:00Z")],
                                                title="Claude Haiku released by October 31?")),
              K % "KXONE-26": (200, kal("KXONE-26", [("Before 2027", "active", "0.45", "0.44", "0.46")],
                                        title="Will xAI release Grok 5 before 2027?")),
              P % "plain": (200, poly_event("plain", [pm("", 0.2)], title="Plain yes/no?"))}
    out, st, lines, ok, _f = sync(rows, routes)
    fc = [(r["forecast"], r.get("resolveDate")) for r in out]
    check("single_leg_label: a one-market Polymarket event renders its groupItemTitle ('95% — October 31', resolving Oct "
          "31) and a one-leg Kalshi event its subtitle ('45% — Before 2027'); an unlabelled leg still says 'Yes'",
          fc == [("95% — October 31", "2026-10-31"), ("45% — Before 2027", "2026-12-31"), ("20% — Yes", "2026-12-31")],
          (fc, lines))


CASES = [("mixed platforms", t_mixed), ("failures leave rows unchanged", t_failures_leave_rows),
         ("mass not-found guard", t_mass_dead), ("time budget", t_budget), ("headline rules", t_headline_rules),
         ("main", t_main),
         ("poly_stale_event_enddate", t_poly_stale_event_enddate), ("poly_all_legs_closed", t_poly_all_legs_closed),
         ("negated_unchanged", t_negated_unchanged), ("not_found_small_n", t_not_found_small_n),
         ("refresh_strips_relative", t_refresh_strips_relative),
         ("api_render_claim_layer", t_api_render_claim_layer), ("binary_maps_to_yes", t_binary_maps_to_yes),
         ("pick_by_when_agi", t_pick_by_when_agi), ("leg_resolved_drop", t_leg_resolved_drop),
         ("et_date_named_day", t_et_date_named_day), ("api_rows_remap", t_api_rows_remap),
         ("llm_fallback_form_maps", t_llm_fallback_form_maps), ("dup_question_pairs", t_dup_question_pairs),
         ("dup_question_rules", t_dup_question_rules), ("dup_cross_platform_kept", t_dup_cross_platform_kept),
         ("dup_expert_exempt", t_dup_expert_exempt), ("dedupe_transient_keeps_rows", t_dedupe_transient_keeps_rows),
         ("leg_date_year", t_leg_date_year), ("single_leg_label", t_single_leg_label)]

if __name__ == "__main__":
    only = sys.argv[1:]                 # python3 scripts/test_market_sync.py [case name ...]: run just those cases
    unknown = [n for n in only if n not in dict(CASES)]
    if unknown:
        print("unknown case(s): %s — known: %s" % (unknown, [n for n, _ in CASES]))
        sys.exit(2)
    for name, fn in CASES:
        if not only or name in only:
            case(name, fn)
    print("ALL PASS (%d checks)" % len(results) if results and all(results)
          else "SOME FAILED (%d of %d)" % (results.count(False), len(results)))
    sys.exit(0 if results and all(results) else 1)
