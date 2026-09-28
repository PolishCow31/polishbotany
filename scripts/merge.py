#!/usr/bin/env python3
"""Deterministic merge: apply data/_delta.json (proposed by claude -p) to the
authoritative data files. The LLM proposes DATA; this script is the only thing
that mutates the dataset. Idempotent: merging the same delta twice changes nothing
the second time (models dedupe by normalized name, markets by canonical market key,
glossary terms by normalized term/aka, news by url).

Transactional (Sep 28 2026 rework): every delta section is validated UP FRONT (a
malformed item is dropped with a logged reason; bad input never raises), every output
is built in memory, and only files whose bytes actually change are written, each via
tmp + os.replace, at the very end. meta.json (lastUpdated / sweeps / dataVersion) is
bumped only when some other file changed, so a no-op merge leaves data/ byte-identical.

Also the one home of the data rules the other pipeline scripts import (market_sync.py,
oneshot_cleanup_*.py): mkt_key / row_key, PRICE_RE + parse_price, BENCH_ALIAS, gkey,
validate_releases, write_atomic. Change a rule here and every script follows.
"""
import calendar, copy, json, math, os, re, sys, traceback
from datetime import datetime, timedelta
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from aa_sync import norm as name_key, AA_KEY_RE   # one model-name normalizer for the whole pipeline ("GPT 6 Sol" == "GPT-6 Sol")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
ET = ZoneInfo("America/New_York")   # DST-aware: the old fixed UTC-4 put every sweep in the wrong slot after Nov 1
SLOTS = ["12AM", "3AM", "6AM", "9AM", "12PM", "3PM", "6PM", "9PM"]   # the 8 daily sweeps, every 3h ET


def note(msg):
    print("   " + msg)


# ---------------------------------------------------------------- files
def load(name, default=None):
    p = os.path.join(DATA, name)
    if default is not None and not os.path.exists(p):
        return default
    with open(p) as f:
        return json.load(f)


def dumps(obj):   # the one serialization every data file uses (aa_sync.save writes the same bytes)
    return json.dumps(obj, indent=2, ensure_ascii=False) + "\n"


def write_atomic(path, text):
    """tmp + os.replace: a reader (the site, git, a crash) sees the old file or the new one, never half of one.
    The tmp name ends in .tmp, which .gitignore excludes, so a hard kill mid-write can't get committed."""
    d = os.path.dirname(path)
    os.makedirs(d, exist_ok=True)
    tmp = os.path.join(d, ".%s.%d.tmp" % (os.path.basename(path), os.getpid()))
    try:
        with open(tmp, "w") as f:
            f.write(text)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def commit(writes):
    """writes: [(abs path, new text, original text or None)], applied in order. If one fails, the files already
    replaced are put back (best effort) before re-raising; update.sh's `git checkout -- data/` is the outer net."""
    done = []
    try:
        for path, text, orig in writes:
            write_atomic(path, text)
            done.append((path, orig))
    except BaseException:
        for path, orig in reversed(done):
            try:
                if orig is None:
                    os.unlink(path)
                else:
                    write_atomic(path, orig)
            except OSError:
                pass
        raise


# ---------------------------------------------------------------- clock
def sweep_clock():
    """The sweep's own clock in America/New_York. update.sh exports SWEEP_STARTED at run start, so the slot,
    date and stamps belong to the sweep that produced the delta, not to whenever the merge happens to run."""
    s = (os.environ.get("SWEEP_STARTED") or "").strip()
    if s:
        iso = re.sub(r"([+-]\d{2})(\d{2})$", r"\1:\2", s)   # BSD `date +%z` gives -0400; py3.9 fromisoformat wants -04:00
        if iso.endswith("Z"):
            iso = iso[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(iso)
            return (dt if dt.tzinfo else dt.replace(tzinfo=ET)).astimezone(ET).replace(microsecond=0)
        except ValueError:
            note("SWEEP_STARTED=%r unparseable — using the current time" % s)
    return datetime.now(ET).replace(microsecond=0)


def slot_of(dt):
    return SLOTS[(dt.hour // 3) % 8]


# ---------------------------------------------------------------- small validators
DAY_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$")
RELEASED_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])(-(0[1-9]|[12]\d|3[01]))?$")
YM_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def valid_day(d):
    if not isinstance(d, str) or not DAY_RE.match(d):
        return False
    try:
        datetime.strptime(d, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def as_bool(v):
    if isinstance(v, bool):
        return v
    if isinstance(v, str) and v.strip().lower() in ("true", "false"):
        return v.strip().lower() == "true"
    return None


def as_num(v):
    """A finite number, or None. Numeric strings are accepted ("73.5"); bools, NaN and Infinity are not (a NaN
    written back out is invalid JSON and blanks the whole app in the browser)."""
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return v if math.isfinite(v) else None
    if isinstance(v, str) and re.match(r"^\s*-?\d+(\.\d+)?\s*$", v):
        return float(v) if "." in v else int(v)
    return None


def s_or(v, default=""):
    return v.strip() if isinstance(v, str) else default


# ---------------------------------------------------------------- hosts + market identity
def url_parts(u):
    """-> (lowercase host, [non-empty path segments]); never raises."""
    try:
        p = urlparse(u.strip() if isinstance(u, str) else "")
        return (p.hostname or "").lower(), [x for x in p.path.split("/") if x]
    except ValueError:
        return "", []


def host_is(u, dom):
    """Host-based domain check: 'ft.com' must not match microsoft.com or ft.com.evil.io (a substring test did)."""
    h, _ = url_parts(u)
    return bool(dom) and (h == dom or h.endswith("." + dom))


MARKET_HOSTS = {"polymarket.com": "poly", "manifold.markets": "manifold", "kalshi.com": "kalshi",
                "metaculus.com": "metaculus"}
MARKET_PLATFORMS = ("polymarket", "manifold", "kalshi", "metaculus")


def market_tag(host):
    for dom, tag in MARKET_HOSTS.items():
        if host == dom or host.endswith("." + dom):
            return tag
    return None


def norm_url(u):
    h, parts = url_parts(u)
    if h.startswith("www."):
        h = h[4:]
    return (h + "/" + "/".join(parts)).lower().rstrip("/")


def mkt_key(u):
    """Canonical market identity, so re-reads refresh in place and one market never shows twice:
    metaculus:<id> · manifold:<slug> · poly:<event-slug> · kalshi:<EVENT-TICKER>; anything else url:<host/path>.
    Manifold slugs are global (the username in the url is decoration the LLM often gets wrong), Metaculus
    slugs are decoration on the id, and a Kalshi url's 4th path segment is the event ticker."""
    h, parts = url_parts(u)
    tag = market_tag(h)
    if tag == "metaculus":
        m = re.search(r"/questions/(\d+)(?:/|$)", "/" + "/".join(parts))
        if m:
            return "metaculus:" + m.group(1)
    elif tag == "manifold" and len(parts) >= 2:
        return "manifold:" + parts[1].lower()
    elif tag == "poly" and len(parts) >= 2 and parts[0] in ("event", "market"):
        return "poly:" + parts[1].lower()
    elif tag == "kalshi" and len(parts) >= 4:
        return "kalshi:" + parts[3].upper()
    return "url:" + norm_url(u)


def gkey(s):   # glossary key: case/punctuation-blind ("Grouped-Query Attention" == "grouped query attention")
    return re.sub(r"[^0-9a-z]+", " ", s.lower()).strip() if isinstance(s, str) else ""


def row_key(m):
    """Identity for refresh-matching + dedupe. A non-market page can back several distinct expert forecasts
    (the Stanford AI Index report backs two), so off-market rows are keyed by url AND question."""
    k = mkt_key(m.get("url"))
    return k + "|" + gkey(m.get("question")) if k.startswith("url:") else k


# ---------------------------------------------------------------- markets
MKT_DOMAINS = {"polymarket": "polymarket.com", "metaculus": "metaculus.com", "kalshi": "kalshi.com",
               "manifold": "manifold.markets", "epoch": "epoch.ai", "metr": "metr.org"}
MKT_CATS = {"ranking", "release", "benchmark", "capability"}
MKT_ASOF_MAX_DAYS = 21   # a row nobody has re-read (LLM or market_sync) in 3 weeks is a stale number, not a forecast
MKT_UNDATED_GUARD = 5    # undated rows are kept when at least this many AND over half the list lack asOf (see prune)
MKT_API_TAGS = ("poly", "manifold", "kalshi")   # the platforms market_sync reads (and dates) every sweep


def mkt_domain(platform):
    lo = platform.lower() if isinstance(platform, str) else ""
    for k, dom in MKT_DOMAINS.items():
        if k in lo:
            return dom
    return None


def mkt_open(rd, today_s):
    """Open until its resolveDate passes. Resolution is read ONLY from structured data: this date (which
    market_sync keeps in step with the platform's own leg dates) and the platforms' APIs (market_sync). Never from
    words: "31% — Yes; no agent has resolved 90% yet" is a live forecast, and an expert row saying "issues resolved"
    is not a resolved market (Sep 28 skeptic: the old text rule dropped both)."""
    d = rd[:10] if isinstance(rd, str) else ""
    return not (valid_day(d) and d < today_s)


def mkt_problem(m, today_s, check_open=True):
    """None when m is a well-formed (and, with check_open, still open) market row; else the reason it isn't."""
    q, url, fc = m.get("question"), m.get("url"), m.get("forecast")
    if not all(isinstance(x, str) and x.strip() for x in (q, url, fc)):
        return "missing question/url/forecast"
    for k in ("platform", "category", "relevantBenchmark", "resolveDate", "asOf"):
        if m.get(k) is not None and not isinstance(m[k], str):     # a list here used to crash merge (set lookup)
            return "%s is %s, not a string" % (k, type(m[k]).__name__)
    if not url.strip().lower().startswith("http"):
        return "url is not http(s)"
    dom = mkt_domain(m.get("platform"))
    if not dom:
        return "unknown platform %r" % m.get("platform")
    if not host_is(url, dom):
        return "url host doesn't match platform (%s)" % dom
    _, parts = url_parts(url)
    if dom == "kalshi.com" and len(parts) < 4:
        return "Kalshi series-only url (no event ticker)"
    if dom == "metaculus.com" and not mkt_key(url).startswith("metaculus:"):
        return "Metaculus url without /questions/<id>/"
    if dom == "polymarket.com" and not (len(parts) >= 2 and parts[0] in ("event", "market")):
        return "Polymarket url is not an event page"
    if dom == "manifold.markets" and len(parts) < 2:
        return "Manifold url is not a market page"
    if not valid_day((m.get("resolveDate") or "")[:10] if isinstance(m.get("resolveDate"), str) else None):
        return "resolveDate %r is not YYYY-MM-DD" % m.get("resolveDate")
    if check_open and not mkt_open(m.get("resolveDate"), today_s):
        return "past its resolveDate %s" % m["resolveDate"][:10]
    return None


def mkt_ok(m, today_s):   # boolean form of mkt_problem (merge logs the reason, so it calls mkt_problem directly)
    return isinstance(m, dict) and mkt_problem(m, today_s) is None


def is_expert_row(m):
    """An expert forecast (METR, Epoch, AI 2027, Stanford AI Index...) rather than a tradable market: its url is
    on no market host AND its platform doesn't claim to be a market. A 'Polymarket' row that links a news
    article is a bad market row (the classic right-outlet-wrong-link fabrication), not an expert forecast."""
    h, _ = url_parts(m.get("url"))
    if not h or market_tag(h):
        return False
    plat = m.get("platform").lower() if isinstance(m.get("platform"), str) else ""
    return not any(p in plat for p in MARKET_PLATFORMS)


def mkt_clean(m, today_s):
    """A validated delta row -> the stored shape. asOf = the sweep date: the LLM read this number this sweep
    (the prompt forbids carrying a number forward), and the renderer mutes any row whose asOf is old."""
    rb = m.get("relevantBenchmark")
    row = {"question": m["question"].strip(), "platform": m["platform"].strip(), "forecast": m["forecast"].strip(),
           "category": m["category"] if isinstance(m.get("category"), str) and m["category"] in MKT_CATS else "capability",
           "relevantBenchmark": rb.strip() if isinstance(rb, str) and rb.strip() else "other",
           "resolveDate": m["resolveDate"][:10], "url": m["url"].strip(), "asOf": today_s}
    if is_expert_row(row):
        row["kind"], row["curated"] = "expert", True
    return row


def check_existing_markets(rows, today_s):
    """D4: re-validate stored rows every merge (not only new ones). Expert forecasts are tagged kind:"expert" +
    curated:true instead of dropped; curated rows skip this check. -> (rows, [(row, reason)], n_tagged)"""
    keep, dropped, tagged = [], [], 0
    for m in rows:
        if not isinstance(m, dict):
            dropped.append(({"url": repr(m)[:80]}, "not an object"))
            continue
        if m.get("curated") is True:
            keep.append(m)
            continue
        if is_expert_row(m):
            m["kind"], m["curated"] = "expert", True
            tagged += 1
            keep.append(m)
            continue
        why = mkt_problem(m, today_s, check_open=False)
        if why:
            dropped.append((m, why))
            continue
        if len(m["resolveDate"]) > 10:          # "2026-12-31 (closes end of 2026)" -> "2026-12-31"
            m["resolveDate"] = m["resolveDate"][:10]
        keep.append(m)
    return keep, dropped, tagged


def dedupe_markets(rows, prefer_longer=False):
    """D2: one row per market. Newest asOf wins; a tie goes to the later row in file order (appended = newer), or with
    prefer_longer (the one-time cleanup, whose legacy rows carry no asOf at all) first to the longer forecast.
    Curated rows are never collapsed. -> (rows, [(dropped row, key)])"""
    best = {}
    for i, m in enumerate(rows):
        if m.get("curated") is True:
            continue
        k = row_key(m)
        j = best.get(k)
        a, b = (s_or(m.get("asOf")), s_or(rows[j].get("asOf"))) if j is not None else ("", "")
        if prefer_longer and j is not None and a == b:
            if len(s_or(m.get("forecast"))) >= len(s_or(rows[j].get("forecast"))):
                best[k] = i
        elif j is None or a >= b:
            best[k] = i
    winners = set(best.values())
    keep, gone = [], []
    for i, m in enumerate(rows):
        if m.get("curated") is True or i in winners:
            keep.append(m)
        else:
            gone.append((m, row_key(m)))
    return keep, gone


def prune_markets(rows, today_s, undated=True):
    """D1b + D3, run on EVERY merge: rows whose resolveDate has passed go (curated included — a forecast whose date
    has passed is moot), and so do non-curated rows whose asOf is more than 21 days old. A non-expert row with NO valid
    asOf is legacy — merge stamps every row the LLM writes and market_sync every row it renders:
      on a platform market_sync reads (Polymarket / Manifold / Kalshi) it goes (round-4 skeptic: "OpenAI 70% (xAI
      45%…)" would otherwise stay forever);
      anywhere else (Metaculus: no API we read) only the LLM can re-date it, so it gets a bounded grace period instead:
      `seen` = the first sweep that found it undated (asOf untouched: the renderer keeps showing it muted, "date
      unknown"), and it goes once `seen` is more than 21 days old. merge drops `seen` when the LLM re-supplies the row.
    Unless at least MKT_UNDATED_GUARD rows and over half the list are undated: that is a file the one-time cleanup
    hasn't dated yet (every live row lacked asOf before it), not a few stale rows — kept as is, with a note.
    undated=False skips the undated rules (the cleanup's --offline run). Nothing is ever pruned for what its text says
    (see mkt_open)."""
    cutoff = (datetime.strptime(today_s, "%Y-%m-%d") - timedelta(days=MKT_ASOF_MAX_DAYS)).strftime("%Y-%m-%d")
    live = lambda m: mkt_open(m.get("resolveDate"), today_s)
    legacy = lambda m: m.get("curated") is not True and m.get("kind") != "expert" and not valid_day(m.get("asOf"))
    n_undated = sum(1 for m in rows if live(m) and legacy(m))
    mass = n_undated >= MKT_UNDATED_GUARD and n_undated > len(rows) / 2
    if undated and mass:
        note("markets: %d of %d rows have no asOf — an undated legacy file, kept (the one-time cleanup dates them)"
             % (n_undated, len(rows)))
    keep, gone = [], []
    for m in rows:
        if not live(m):
            gone.append((m, "past its resolveDate %s" % m["resolveDate"][:10]))
        elif legacy(m):
            if not undated or mass:
                keep.append(m)
            elif market_tag(url_parts(m.get("url"))[0]) in MKT_API_TAGS:
                gone.append((m, "no asOf: a legacy row nobody has re-read since rows carry dates"))
            elif valid_day(m.get("seen")) and m["seen"] < cutoff:
                gone.append((m, "no asOf, undated since %s — more than %d days" % (m["seen"], MKT_ASOF_MAX_DAYS)))
            else:
                if not valid_day(m.get("seen")):
                    m["seen"] = today_s
                keep.append(m)
        elif m.get("curated") is not True and valid_day(m.get("asOf")) and m["asOf"] < cutoff:
            gone.append((m, "asOf %s is more than %d days old" % (m["asOf"], MKT_ASOF_MAX_DAYS)))
        else:
            keep.append(m)
    return keep, gone


# ---------------------------------------------------------------- prices
# Editorial prices are "in/out" USD per 1M tokens and nothing else ("4/20"). Tier/promo/cache text goes to
# editorial.priceNotes; a price that isn't two per-1M-token numbers (per second, per page, "open weights")
# never enters prices at all — the renderer falls back to the model's own `pricing` text.
PRICE_RE = re.compile(r'^\s*\$?\s*(\d+(?:\.\d+)?)\s*(?:in)?\s*/\s*\$?\s*(\d+(?:\.\d+)?)')
PRICE_BOILER = re.compile(r"^(?:\s*(?:out(?:put)?|per\s+1\s*M(?:\s+tokens)?|/\s*1\s*M(?:\s+tokens)?|USD|[,;:.]|[-–—](?=\s)))+",
                          re.I)


def parse_price(raw):
    """-> (canonical "a/b" or None, note or None).
    '4/20 (promo through Nov 21)' -> ('4/20', 'promo through Nov 21'); '$1.40 in / $4.40 out per 1M' -> ('1.4/4.4',
    None); '$0.17/s HD' -> (None, '$0.17/s HD'). The second number must not be a cached-input rate or carry a unit
    ('$0.15 in / $0.03 cached in', '$3/1M in') — those would silently become the output price."""
    if not isinstance(raw, str) or not raw.strip():
        return None, None
    s = " ".join(raw.split())
    m = PRICE_RE.match(s)
    tail = s[m.end():] if m else ""
    if not m or re.match(r"[A-Za-z]", tail[:1]) or re.match(r"\s*cache", tail, re.I):
        return None, s
    price = "%s/%s" % (format(float(m.group(1)), "g"), format(float(m.group(2)), "g"))
    rest = PRICE_BOILER.sub("", tail).strip()
    if rest.startswith("(") and rest.endswith(")") and rest.count("(") == 1:
        rest = rest[1:-1].strip()
    return price, (rest or None)


def price_key(k):
    return " ".join(k.lower().split()) if isinstance(k, str) else ""


def normalize_prices(ed, models, delta_prices=None):
    """Rebuild editorial.prices / priceNotes (D5a/D17): canonical "a/b" values, notes split out, keys re-keyed to
    the catalog's exact lowercase name when unambiguous (the renderer looks prices up by exact key), missing
    prices derived from models[].pricing. Idempotent. -> counts dict"""
    catalog = {}
    for m in models:
        if isinstance(m.get("name"), str):
            catalog.setdefault(name_key(m["name"]), []).append(m["name"].lower())
    exact = {price_key(m["name"]) for m in models if isinstance(m.get("name"), str)}

    def canon(k):
        if k in exact:
            return k
        hits = catalog.get(name_key(k), [])
        return hits[0] if len(hits) == 1 else k

    old_p = ed.get("prices") if isinstance(ed.get("prices"), dict) else {}
    old_n = ed.get("priceNotes") if isinstance(ed.get("priceNotes"), dict) else {}
    prices, notes, c = {}, dict(old_n), {"rekeyed": 0, "noted": 0, "derived": 0, "delta": 0, "delta_rejected": 0}
    for k, v in old_p.items():
        k2 = canon(price_key(k))
        if not k2:
            continue
        if k2 != price_key(k):
            c["rekeyed"] += 1
            if k2 in old_p:            # both spellings present: the exact catalog key wins
                notes.pop(price_key(k), None)
                continue
            if price_key(k) in notes and k2 not in notes:
                notes[k2] = notes.pop(price_key(k))
        p, n = parse_price(v)
        if p:
            prices[k2] = p
            if n:
                notes[k2] = n
        elif isinstance(v, str) and v.strip():
            notes[k2] = " ".join(v.split())     # not a per-1M token price: kept as a note, out of prices
            c["noted"] += 1
    for k, v in (delta_prices or {}).items():
        k2 = canon(price_key(k))
        p, n = parse_price(v)
        if not k2 or not (p or n):
            continue
        if p:
            if prices.get(k2) != p:
                notes.pop(k2, None)            # a changed price invalidates the old promo/tier note
            prices[k2] = p
            if n:
                notes[k2] = n
            c["delta"] += 1
        elif k2 in prices:
            note("price for %r not a per-1M token price (%r) — kept %s" % (k2, n, prices[k2]))
            c["delta_rejected"] += 1
        else:
            notes[k2] = n
            c["noted"] += 1
    for m in models:
        k = price_key(m.get("name"))
        if k and k not in prices:
            p, n = parse_price(m.get("pricing"))
            if p:
                prices[k] = p
                if n and k not in notes:
                    notes[k] = n
                c["derived"] += 1
    ed["prices"] = prices
    if notes:
        ed["priceNotes"] = notes
    else:
        ed.pop("priceNotes", None)
    c["unmatched"] = sorted(k for k in prices if k not in exact)
    return c


# ---------------------------------------------------------------- benchmarks
BENCH_ALIAS = {'SWE-bench': 'SWE-bench Verified', 'GPQA': 'GPQA Diamond', 'Terminal-Bench v3.0': 'Terminal-Bench 3.0',
               'Terminal-Bench 4': 'Terminal-Bench 4.0'}


def apply_bench_alias(b):
    """Canonical benchmark keys, order kept. If both spellings are present the canonical one wins.
    -> (new dict, [renamed keys], [alias keys dropped because the canonical key exists])"""
    out, renamed, clash = {}, [], []
    for k, v in b.items():
        c = BENCH_ALIAS.get(k)
        if c is None:
            out[k] = v
        elif c in b:
            clash.append(k)
        else:
            out[c] = v
            renamed.append(k)
    return out, renamed, clash


def clean_benchmarks(b, who):
    out = {}
    for k, v in b.items():
        if not isinstance(k, str) or not k.strip():
            note("%s: dropped a benchmark with no name" % who)
            continue
        if AA_KEY_RE.search(k):     # scripts/aa_sync.py owns the AA-Index column; an LLM number would be off-scale
            note("%s: dropped benchmark %r — AA-Index is written by aa_sync.py only" % (who, k))
            continue
        n = as_num(v)
        if n is None:
            note("%s: dropped benchmark %r=%r (not a number)" % (who, k, v))
            continue
        if n <= 0:              # no real score is 0 or negative; it's an LLM placeholder that renders as a real score
            note("%s: dropped benchmark %r=%r (placeholder zero)" % (who, k, v))    # (GPT-5.5 "GPQA": 0, Sep 2026)
            continue
        out[k.strip()] = n
    return apply_bench_alias(out)[0]


# ---------------------------------------------------------------- radar (releases)
REL_STATUS = {"confirmed", "expected", "rumored"}
RELK = ("model", "lab", "expectedWindow", "expectedDate", "prob", "probAsOf", "frontier", "open", "status", "late",
        "basis", "source")
REL_MIN_KEEP = 0.6   # a replacement radar shorter than 60% of the current one is a truncated LLM run, not news
REL_LATE_DAYS = 30   # a missed window stays on the radar marked late (the renderer shows LATE) this long, then drops
_MONTHS = r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
WIN_MONTH_RE = re.compile(r"\b" + _MONTHS + r"\b\.?(?:\s+(\d{1,2})(?:st|nd|rd|th)?\b)?(?:,?\s+(20\d\d)\b)?", re.I)
MON_NUM = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}
_NUMW = r"(?:\d+|a few|few|one|two|three|four|five|six|seven|eight|nine|ten)"
_REL = (r"(?:today|tomorrow|tonight|yesterday|overnight|last night|this (?:week|morning|afternoon|evening)|" + _NUMW +
        r"\s+(?:more\s+)?days?\s+(?:left|to go|remaining|away))")
REL_PAREN_RE = re.compile(r"\s*\([^()]*\b" + _REL + r"\b[^()]*\)", re.I)
REL_WORD_RE = re.compile(r"(?:^|,\s*|\s+)(?:(?:now|with|only|just|and)\s+)?" + _REL + r"\b", re.I)


def strip_relative(s):
    """Drop relative time words from radar text: the file is read for hours after it's written, so 'tomorrow' and
    'two days left' go stale (and wrong) almost immediately. Absolute dates stay."""
    if not isinstance(s, str):
        return ""
    s = REL_PAREN_RE.sub("", s)
    s = REL_WORD_RE.sub("", s)
    s = re.sub(r"\(\s*\)", "", s)
    s = re.sub(r"([—–-])\s*,\s*", r"\1 ", s)          # "- today, Sep 3" -> "- Sep 3", not "-, Sep 3"
    s = re.sub(r"\s+([,.;:!?)])", r"\1", s)
    s = re.sub(r"([,;:])\s*([.;:!?])", r"\2", s)
    s = re.sub(r"\s{2,}", " ", s).strip()
    s = re.sub(r"^[,;:.\s]+", "", s)
    return re.sub(r"[,;:]\s*$", "", s).strip()


QH_RE = re.compile(r"\b([QH])([1-4])\b(?:\s*['’/-]?\s*(20\d\d|\d\d)\b)?", re.I)
YEAR_RE = re.compile(r"\b(?:(before|by|in|end of|late|early|mid)[\s-]+)?(20\d\d)\b", re.I)
PHASE_END = {"early": (4, 30), "mid": (8, 31)}                 # "late"/"end of"/"by"/"in"/a bare year: Dec 31
SEASON_RE = re.compile(r"\b(spring|summer|fall|autumn|winter)\b(?:\s+(?:of\s+)?(20\d\d))?", re.I)
SEASON_END = {"spring": (6, 30), "summer": (9, 30), "fall": (12, 31), "autumn": (12, 31)}   # winter Y: Feb of Y+1
OPEN_WIN_RE = re.compile(r"\b(?:not\s+before|no\s+earlier\s+than|after|beyond)\b", re.I)


def window_deadline(win, fallback_year):
    """-> (deadline 'YYYY-MM-DD', month 'YYYY-MM', mode) for every window form, or None for an undated one ('TBA').
      'by Oct 15' / 'Sep 29' / 'Oct 2026'  the LAST month named: its named day, else its last day ("before <Month>" /
                                           "before <Month> 15" end the day before). mode "by" when it says by/before,
                                           else "month" (the window IS that month).
      'Q4 2026' / 'H2 2026'                the quarter's / half's last day, mode "span".
      '2027' / 'by 2027' / 'late 2026'      Dec 31 of that year ("before 2027" -> Dec 31 2026), mode "span";
                                           'early 2027' Apr 30, 'mid(-)2027' Aug 31.
      'spring/summer/fall 2027'            Jun 30 / Sep 30 / Dec 31; 'winter 2026' Feb 28/29 2027. Mode "span".
      'not before 2027' / 'after 2026'     None: open-ended ("no earlier than", "beyond" too), never late.
    Off-form windows read LENIENTLY (round-4 skeptic): a false LATE on the phone is worse than a late flag.
    The year is the one the window names, else fallback_year (the item's expectedDate year) — NEVER rolled forward: a
    window whose date has passed is LATE, not next year's. (Sep 28 skeptic: rolling "by Oct 15" read on Nov 3 into Oct
    2027 meant a missed release never retired. Round 2: Q/H/year windows had no deadline at all, so their items fell
    back to the expectedDate month and vanished a month early — Grok 4.8 "Q4 2026" would have gone on Dec 1.)"""
    win = win or ""
    if OPEN_WIN_RE.search(win):         # "not before 2027" used to read as "before 2027": LATE on Jan 1, wrongly
        return None
    hits = [m for m in WIN_MONTH_RE.finditer(win) if m.group(1) != "may"]   # lowercase "may" is the verb
    if hits:
        m = hits[-1]
        mon = MON_NUM[m.group(1)[:3].lower()]
        y = int(m.group(3)) if m.group(3) else None
        if y is None:
            yr = re.search(r"\b(20\d\d)\b", win)
            y = int(yr.group(1)) if yr else fallback_year
        last = calendar.monthrange(y, mon)[1]
        day = int(m.group(2)) if m.group(2) and 1 <= int(m.group(2)) <= last else None
        kw = re.search(r"\b(by|before|no later than)\s*$", win[:m.start()], re.I)
        if kw and kw.group(1).lower() == "before":
            dl = datetime(y, mon, day or 1) - timedelta(days=1)
        else:
            dl = datetime(y, mon, day or last)
        return dl.strftime("%Y-%m-%d"), "%04d-%02d" % (y, mon), "by" if kw else "month"
    q = [m for m in QH_RE.finditer(win) if not (m.group(1).upper() == "H" and m.group(2) not in "12")]
    if q:
        m = q[-1]
        yy = m.group(3)
        y = (int(yy) if len(yy) == 4 else 2000 + int(yy)) if yy else None
        if y is None:
            yr = re.search(r"\b(20\d\d)\b", win)
            y = int(yr.group(1)) if yr else fallback_year
        mon = int(m.group(2)) * (3 if m.group(1).upper() == "Q" else 6)
        return "%04d-%02d-%02d" % (y, mon, calendar.monthrange(y, mon)[1]), "%04d-%02d" % (y, mon), "span"
    ss = list(SEASON_RE.finditer(win))
    if ss:
        m = ss[-1]
        yr = re.search(r"\b(20\d\d)\b", win)
        y = int(m.group(2)) if m.group(2) else (int(yr.group(1)) if yr else fallback_year)
        season = m.group(1).lower()
        y, mon, day = (y + 1, 2, calendar.monthrange(y + 1, 2)[1]) if season == "winter" else (y,) + SEASON_END[season]
        return "%04d-%02d-%02d" % (y, mon, day), "%04d-%02d" % (y, mon), "span"
    ys = list(YEAR_RE.finditer(win))
    if ys:
        m = ys[-1]
        pre = (m.group(1) or "").lower()
        y = int(m.group(2)) - (1 if pre == "before" else 0)
        mon, day = PHASE_END.get(pre, (12, 31))
        return "%04d-%02d-%02d" % (y, mon, day), "%04d-%02d" % (y, mon), "span"
    return None


def clamp_prob(p):
    if isinstance(p, str):
        try:
            p = float(p.strip().rstrip("%"))
        except ValueError:
            return -1
    if isinstance(p, bool) or not isinstance(p, (int, float)) or not math.isfinite(p) or p < 0:
        return -1
    p = min(float(p), 100.0)
    return int(p) if p.is_integer() else round(p, 1)


def validate_releases(items, live_keys, now_dt, old_by_key=None, stamp_missing=True):
    """D7 radar rules. -> (clean items, [(model, reason)] dropped). stamp_missing: a live prob with no valid
    probAsOf gets the sweep date (true for a fresh delta; False when re-validating the stored list).
    Every dated window ('by Oct 15', 'Oct 2026', 'Q4 2026', 'H2 2026', '2027') is governed by its deadline
    (window_deadline): once that day has passed the item keeps its expectedDate, is marked late:true, and drops
    REL_LATE_DAYS after the deadline — never earlier because of its expectedDate. Only an undated window ('TBA') is
    governed by expectedDate: it drops once that month is behind us."""
    today_s, today_ym = now_dt.strftime("%Y-%m-%d"), now_dt.strftime("%Y-%m")
    retire = (now_dt - timedelta(days=REL_LATE_DAYS)).strftime("%Y-%m-%d")
    old_by_key = old_by_key or {}
    out, dropped = [], []
    for r in items:
        if not isinstance(r, dict):
            dropped.append(("?", "not an object"))
            continue
        bad = [f for f in ("model", "lab", "expectedWindow", "expectedDate", "status", "basis", "source")
               if r.get(f) is not None and not isinstance(r[f], str)]
        if bad:                    # a list-valued status/lab used to be coerced (or crash); now the item goes
            dropped.append((repr(r.get("model"))[:60], "%s not a string" % ", ".join(bad)))
            continue
        model = s_or(r.get("model"))
        k = name_key(model)
        if not k:
            dropped.append((repr(r.get("model")), "no model name"))
            continue
        if k in live_keys:
            dropped.append((model, "already a live catalog model"))
            continue
        win = strip_relative(r.get("expectedWindow"))
        ed = s_or(r.get("expectedDate"))
        ed = ed[:7] if RELEASED_RE.match(ed) else None
        wd = window_deadline(win, int(ed[:4]) if ed else now_dt.year)
        late = False
        if wd:
            dl, ym, mode = wd
            # a window naming its month IS that month; "by <month>" and Q/H/year spans cap the estimate at the deadline
            ed = ym if mode == "month" else (min(ed, ym) if ed else ym)
            if dl < today_s:                         # the deadline day itself is not late (both are ET calendar dates)
                if dl < retire:
                    dropped.append((model, "window ended %s, more than %d days ago" % (dl, REL_LATE_DAYS)))
                    continue
                late = True
        if not ed or not YM_RE.match(ed):
            dropped.append((model, "expectedDate %r is not YYYY-MM" % r.get("expectedDate")))
            continue
        if not wd and ed < today_ym:
            dropped.append((model, "expectedDate %s is before %s" % (ed, today_ym)))
            continue
        prob = clamp_prob(r.get("prob"))
        pa = r.get("probAsOf")
        if prob < 0:
            pa = None
        elif not (valid_day(pa) and pa <= today_s):
            pa = today_s if stamp_missing else None
        op = as_bool(r.get("open"))
        if op is None:             # unknown stays unknown (null) so the renderer's open-weights heuristics still run
            prev = old_by_key.get(k) or {}
            op = prev.get("open") if isinstance(prev.get("open"), bool) else None
        st = s_or(r.get("status")).lower()
        src = r.get("source")
        out.append({"model": model, "lab": s_or(r.get("lab")), "expectedWindow": win, "expectedDate": ed,
                    "prob": prob, "probAsOf": pa, "frontier": as_bool(r.get("frontier")) is True, "open": op,
                    "status": st if st in REL_STATUS else "expected", "late": late,
                    "basis": strip_relative(r.get("basis")),
                    "source": src.strip() if isinstance(src, str) and src.strip() else None})
    return out, dropped


def radar_update(cur_items, new_items, models, now_dt):
    """-> (items to store, dropped [(model, reason)], refused: bool). The current list is re-validated too (a model
    shipping or a window lapsing retires items), and its NON-LATE items are the baseline the 60% refusal compares
    against, counted the same way on the new list: a missed release is on its way out, so counting it would let a
    few stale items refuse a correct, shorter list sweep after sweep (the radar locks)."""
    live = {name_key(m["name"]) for m in models if m.get("status") == "live" and isinstance(m.get("name"), str)}
    old_by_key = {name_key(r.get("model")): r for r in cur_items if isinstance(r, dict) and isinstance(r.get("model"), str)}
    cur_ok, _ = validate_releases(cur_items, live, now_dt, old_by_key, stamp_missing=False)
    new_ok, dropped = validate_releases(new_items, live, now_dt, old_by_key)
    base = sum(1 for r in cur_ok if not r["late"])
    if base and sum(1 for r in new_ok if not r["late"]) < REL_MIN_KEEP * base:
        return cur_ok, dropped, True
    return new_ok, dropped, False


# ---------------------------------------------------------------- sources retention
SOURCES_KEEP_DAYS = 30
ARCHIVE_DIR = "sources-archive"


def plan_source_archive(sweeps, today_d, data_dir):
    """D14: sources.json keeps the last 30 days; older sweeps move to sources-archive/YYYY-MM.json (append-merge by
    (date, routine), so re-running is a no-op). A month whose archive file can't be read is not archived this run.
    -> (kept sweeps, {abs path: (new text, original text or None)}, n archived)"""
    cutoff = (today_d - timedelta(days=SOURCES_KEEP_DAYS)).strftime("%Y-%m-%d")
    by_month = {}
    for s in sweeps:                   # recent or undatable sweeps stay: never archive what can't be dated
        d = s.get("date") if isinstance(s, dict) else None
        if isinstance(d, str) and valid_day(d) and d < cutoff:
            by_month.setdefault(d[:7], []).append(s)
    files, moved, gone = {}, 0, set()
    for month in sorted(by_month):
        path = os.path.join(data_dir, ARCHIVE_DIR, month + ".json")
        orig = None
        try:
            if os.path.exists(path):
                with open(path) as f:
                    orig = f.read()
                arch = json.loads(orig)
                if not isinstance(arch, dict) or not isinstance(arch.get("sweeps"), list):
                    raise ValueError("unexpected shape")
            else:
                arch = {"month": month, "note": "Per-sweep source log for %s, moved out of data/sources.json after %d "
                        "days (scripts/merge.py). Same shape as sources.json sweeps[]." % (month, SOURCES_KEEP_DAYS),
                        "sweeps": []}
        except (OSError, ValueError) as e:
            note("sources: archive %s unreadable (%s) — its sweeps stay in sources.json" % (path, e))
            continue
        pos = {(x.get("date"), x.get("routine")): i for i, x in enumerate(arch["sweeps"]) if isinstance(x, dict)}
        for s in by_month[month]:
            k = (s.get("date"), s.get("routine"))
            if k in pos:
                arch["sweeps"][pos[k]] = s
            else:
                pos[k] = len(arch["sweeps"])
                arch["sweeps"].append(s)
        arch["sweeps"].sort(key=lambda x: (x.get("date") or "") if isinstance(x, dict) else "")   # stable: slot order kept
        files[path] = (dumps(arch), orig)
        moved += len(by_month[month])
        gone.update(id(s) for s in by_month[month])
    return [s for s in sweeps if id(s) not in gone], files, moved


# ---------------------------------------------------------------- news
# News integrity guard: the headless updater researches via WebSearch, which can hallucinate URLs. A news item is
# only accepted if its source is known AND the url's HOST is that source's real domain (a "CNBC" item must link to
# cnbc.com). WSJ/Reuters/AP/Bloomberg/FT are not listed: the updater's tools can't open them, so any item it writes
# for them is unverifiable (the prompt already tells it they're rejected).
NEWS_MAX = 24
NEWS_DOMAINS = {
    "CNBC": "cnbc.com", "The Economist": "economist.com", "Axios": "axios.com", "Nature": "nature.com",
    "MIT Tech Review": "technologyreview.com", "IEEE Spectrum": "spectrum.ieee.org", "The Verge": "theverge.com",
    "Ars Technica": "arstechnica.com", "Science": "science.org",
}
NEWS_KEYS = ("title", "source", "url", "date", "topic", "blurb")


def news_problem(it):
    """None when a news item is acceptable, else why not. Every field is stored or looked up, so each must be text
    (Sep 28 skeptic: a list-valued "source" raised TypeError in the dict lookup and discarded the whole sweep)."""
    if not isinstance(it, dict):
        return "not an object"
    bad = [k for k in NEWS_KEYS if it.get(k) is not None and not isinstance(it[k], str)]
    if bad:
        return "%s not a string" % ", ".join(bad)
    url = it.get("url") or ""
    if not url.lower().startswith("http"):
        return "url is not http(s)"
    dom = NEWS_DOMAINS.get(it.get("source"))
    if not dom:
        return "source %r is not an allowed outlet" % it.get("source")
    if not host_is(url, dom):
        return "url host isn't %s" % dom
    if not (it.get("title") or "").strip():
        return "no title"
    if not DAY_RE.match((it.get("date") or "")[:10]):
        return "date %r is not a full YYYY-MM-DD" % it.get("date")
    return None


def news_ok(it):
    return news_problem(it) is None


# ---------------------------------------------------------------- delta validation (up front)
MODEL_STATUS = {"live", "preview", "historic", "superseded", "pulled"}
REQUIRED_NEW = ("name", "lab", "released", "status", "open", "benchmarks")
TEXT_FIELDS = ("params", "context", "modality", "notable", "pricing")   # free text: a bad one is dropped, not the model
KNOWN_KEYS = {"newModels", "updatedModels", "news", "editorial", "releases", "markets", "marketsStory", "glossary",
              "briefs", "sweepSources", "asOf"}
RETIRED_KEYS = {"newTrendPoints", "promotedPredictions"}   # D13: nothing renders trends/predictions any more
RETIRED_EDITORIAL = ("leaderboard", "upcoming", "killed", "sources")
GK = ("term", "acronym", "category", "def", "aka")


def _nk(v):   # name_key that tolerates junk (a list-valued name in stored data must not crash an index build)
    return name_key(v) if isinstance(v, str) else ""


def _text(who, field, v):
    """-> (value, ok). Free-text model fields: text passes; a bare number in params/context becomes text (the prompt
    says "numbers as numbers", so `"context": 1000000` is honest input); anything else is refused (logged)."""
    if v is None or isinstance(v, str):
        return v, True
    if field in ("params", "context") and isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v):
        return (str(int(v)) if float(v).is_integer() else str(v)), True
    note("%s: %s %.60r is not text — field dropped" % (who, field, v))
    return None, False


def check_new_model(m):
    if not isinstance(m, dict):
        return None, "not an object"
    missing = [k for k in REQUIRED_NEW if k not in m]
    if missing:
        return None, "missing " + ", ".join(missing)
    if not (isinstance(m["name"], str) and name_key(m["name"])):
        return None, "bad name %.60r" % (m.get("name"),)
    if not isinstance(m["lab"], str) or not m["lab"].strip():
        return None, "lab %.60r is not text" % (m.get("lab"),)
    if not isinstance(m["released"], str) or not RELEASED_RE.match(m["released"].strip()):
        return None, "released %.60r is not YYYY-MM or YYYY-MM-DD" % (m.get("released"),)
    if not isinstance(m["status"], str) or m["status"].strip().lower() not in MODEL_STATUS:
        return None, "status %.60r not in %s" % (m.get("status"), sorted(MODEL_STATUS))
    op = as_bool(m["open"])
    if op is None:
        return None, "open %.60r is not a boolean" % (m.get("open"),)
    if not isinstance(m["benchmarks"], dict):
        return None, "benchmarks is %s, not an object" % type(m["benchmarks"]).__name__
    name = m["name"].strip()
    out = dict(m)
    out.update(name=name, lab=m["lab"].strip(), released=m["released"].strip(), status=m["status"].strip().lower(),
               open=op, benchmarks=clean_benchmarks(m["benchmarks"], name))
    for f in TEXT_FIELDS:
        v, ok = _text("newModels " + name, f, out.get(f))
        if ok and v is not None:
            out[f] = v
        elif not ok:
            out.pop(f, None)
    if "milestone" in out:
        if as_bool(out["milestone"]) is None:
            note("newModels %s: milestone %.60r is not a boolean — field dropped" % (name, out["milestone"]))
            out.pop("milestone")
        else:
            out["milestone"] = as_bool(out["milestone"])
    if "sources" in out:
        if isinstance(out["sources"], list):
            out["sources"] = [x for x in out["sources"] if isinstance(x, str) and x.strip()]
        else:
            note("newModels %s: sources is %s, not a list — field dropped" % (name, type(out["sources"]).__name__))
            out.pop("sources")
    return out, None


def check_update(u):
    """-> (name, {field: value}) with invalid fields dropped (logged), or (None, reason)."""
    if not isinstance(u, dict):
        return None, "not an object"
    if not isinstance(u.get("name"), str) or not name_key(u["name"]):
        return None, "no usable name"
    name = u["name"].strip()
    fields = {}
    for k, v in u.items():
        if k == "name":
            continue
        if k == "benchmarks":
            if not isinstance(v, dict):
                note("updatedModels %s: benchmarks is %s, not an object — field ignored" % (name, type(v).__name__))
                continue
            v = clean_benchmarks(v, name)
        elif k == "released" and not (isinstance(v, str) and RELEASED_RE.match(v.strip())):
            note("updatedModels %s: released %.60r is not YYYY-MM[-DD] — field ignored" % (name, v))
            continue
        elif k == "status":
            if not isinstance(v, str) or v.strip().lower() not in MODEL_STATUS:
                note("updatedModels %s: status %.60r not allowed — field ignored" % (name, v))
                continue
            v = v.strip().lower()
        elif k in ("open", "milestone"):
            if as_bool(v) is None:
                note("updatedModels %s: %s %.60r is not a boolean — field ignored" % (name, k, v))
                continue
            v = as_bool(v)
        elif k == "lab":
            if not isinstance(v, str) or not v.strip():
                note("updatedModels %s: lab %.60r is not text — field ignored" % (name, v))
                continue
            v = v.strip()
        elif k in TEXT_FIELDS:
            v, ok = _text("updatedModels " + name, k, v)
            if not ok:
                continue
        elif k == "sources":
            if not isinstance(v, list):
                note("updatedModels %s: sources is %s, not a list — field ignored" % (name, type(v).__name__))
                continue
            v = [x for x in v if isinstance(x, str) and x.strip()]
        fields[k] = v
    return name, fields


def check_glossary_item(t):
    if not isinstance(t, dict):
        return None, "not an object"
    bad = [f for f in ("term", "acronym", "category", "def") if t.get(f) is not None and not isinstance(t[f], str)]
    if bad:
        return None, "%s not a string" % ", ".join(bad)
    term, d = s_or(t.get("term")), s_or(t.get("def"))
    if not gkey(term):
        return None, "no term"
    if not d:
        return None, "no def"
    aka = t.get("aka")
    aka = [aka] if isinstance(aka, str) else aka if isinstance(aka, list) else []
    return {"term": term, "acronym": s_or(t.get("acronym")), "category": s_or(t.get("category")), "def": d,
            "aka": [a.strip() for a in aka if isinstance(a, str) and a.strip()]}, None


def check_source(x):
    """A sweepSources entry: u / url / q must be text when present, and it needs a label or a url."""
    if not isinstance(x, dict) or any(x.get(k) is not None and not isinstance(x[k], str) for k in ("u", "url", "q")):
        return None
    if not ((x.get("u") or "").strip() or (x.get("url") or "").strip()):
        return None
    return {k: x.get(k) for k in ("u", "url", "q")}


def read_delta(path):
    """-> dict or None. NaN/Infinity parse as None so they fail every number check downstream. A markdown fence around
    the JSON (```json ... ```), which the model sometimes writes, is stripped first: the content is perfectly usable."""
    try:
        with open(path) as f:
            text = f.read().strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else ""
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3]
        delta = json.loads(text, parse_constant=lambda c: None)
    except (OSError, ValueError) as e:
        note("_delta.json unreadable (%s) — nothing merged" % str(e)[:200])
        return None
    if not isinstance(delta, dict):
        note("_delta.json is a %s, not an object — nothing merged" % type(delta).__name__)
        return None
    unknown = sorted(set(delta) - KNOWN_KEYS - RETIRED_KEYS)
    if unknown:
        note("ignored unknown delta keys: " + ", ".join(unknown))
    for k in sorted(RETIRED_KEYS & set(delta)):
        note("ignored delta.%s (retired: trends/predictions are no longer rendered)" % k)
    return delta


# ---------------------------------------------------------------- main
EXIT_PARTIAL = 3   # merged, but at least one section hit an unexpected error and was skipped (update.sh: publish + alarm)
EXIT_NOTHING = 4   # the delta was unusable, or not one item in it was accepted: a failed sweep for the dead-streak alarm,
                   # though update.sh still runs aa_sync/market_sync and publishes their changes. (Round-2 skeptic: this
                   # used to exit 0, so a sweep that landed nothing reset the streak while news/pulse/radar froze.)
STATE_DIR = os.path.join(ROOT, "scripts")          # updater state (gitignored), not data: tests point it elsewhere
REJECTS_FILE, ALARM_FILE = ".section_rejects.json", ".section_alarm"
SECTION_ALARM_EVERY = 8   # 8 sweeps = a day of one section offering items and landing none


def section_rejects(offered, accepted):
    """Per-section freeze counter: +1 for every sweep in which a section was offered 1+ items and accepted none, reset
    to 0 by any acceptance, untouched when the section wasn't offered. Every 8th consecutive sweep lands in ALARM_FILE
    ("<section> <count>" lines, rewritten each merge) for update.sh to notify: a section can freeze (the LLM keeps
    writing news the merge rejects) while other sections — and market_sync — keep the sweep looking healthy."""
    path = os.path.join(STATE_DIR, REJECTS_FILE)
    try:
        with open(path) as f:
            state = json.load(f)
        state = state if isinstance(state, dict) else {}
    except (OSError, ValueError):
        state = {}
    alarms = []
    for sec, n in sorted(offered.items()):
        if n <= 0:
            continue
        if accepted.get(sec, 0) > 0:
            state[sec] = 0
        else:
            state[sec] = (state.get(sec) if isinstance(state.get(sec), int) else 0) + 1
            if state[sec] % SECTION_ALARM_EVERY == 0:
                alarms.append((sec, state[sec]))
    write_atomic(path, json.dumps(state, sort_keys=True) + "\n")
    write_atomic(os.path.join(STATE_DIR, ALARM_FILE), "".join("%s %d\n" % a for a in alarms))
    return alarms


def main():
    alarm = os.path.join(STATE_DIR, ALARM_FILE)
    try:        # update.sh reads ALARM_FILE after every merge, and only section_rejects (near the end) rewrites it: an
        if os.path.getsize(alarm):      # early return (unusable delta) left the last sweep's alarm to fire again
            open(alarm, "w").close()
    except OSError:
        pass
    delta_path = os.path.join(DATA, "_delta.json")
    if not os.path.exists(delta_path):
        print("no _delta.json; nothing to merge")
        return 0
    delta = read_delta(delta_path)
    if delta is None:
        print("merge: unusable delta — nothing merged")
        return EXIT_NOTHING

    now_dt = sweep_clock()
    now_iso, today_s, routine = now_dt.isoformat(), now_dt.strftime("%Y-%m-%d"), slot_of(now_dt)

    # ---- load every file this merge may touch (all-or-nothing: an unreadable data file raises before any write)
    names = ("models.json", "meta.json", "news.json", "editorial.json", "releases.json", "glossary.json",
             "briefs.json", "sources.json", "forecasts.json")
    orig, doc = {}, {}
    for n in names:
        p = os.path.join(DATA, n)
        orig[n] = open(p).read() if os.path.exists(p) else None
        if orig[n] is None and n in ("models.json", "meta.json"):
            raise FileNotFoundError(p)
    defaults = {"news.json": {"items": []}, "editorial.json": {}, "releases.json": {}, "glossary.json": {"terms": []},
                "briefs.json": {"briefs": {}}, "sources.json": {"sweeps": []}, "forecasts.json": {}}
    for n in names:
        doc[n] = json.loads(orig[n]) if orig[n] is not None else json.loads(json.dumps(defaults[n]))
    c = dict.fromkeys(("added", "updated", "news_added", "news_dropped", "ed_fields", "rel_n", "rel_dropped",
                       "gloss_added", "briefs", "srcs", "archived", "mkt_added", "mkt_upd", "mkt_rej", "mkt_dropped",
                       "story"), 0)
    c["archive_files"], skipped = {}, []
    off, acc = {}, {}                   # per section: items the delta offered / items that passed validation

    def offer(sec, key):
        """The delta's list for key, counted as offered. A non-list value counts as one offered, rejected item."""
        v = delta.get(key)
        if v is None:
            return []
        if not isinstance(v, list):
            note("delta.%s is %s, not a list — section ignored" % (key, type(v).__name__))
            off[sec] = off.get(sec, 0) + 1
            return []
        off[sec] = off.get(sec, 0) + len(v)
        return v

    def ok(sec, n=1):
        acc[sec] = acc.get(sec, 0) + n

    def section(label, files, fn):
        """One merge step. An unexpected error inside it skips just that step (its files keep their pre-step
        content, the reason is logged), never the whole merge: one malformed field must not freeze publishing
        (Sep 28 skeptic: a list-valued news "source" raised TypeError and threw away every section of the sweep)."""
        snap = {n: copy.deepcopy(doc[n]) for n in files}
        try:
            fn()
        except Exception as e:
            for n in files:
                doc[n] = snap[n]
            skipped.append(label)
            tb = traceback.extract_tb(e.__traceback__)[-1]
            note("%s: SKIPPED this run, file left as it was — %s: %s (at %s:%d)"
                 % (label, type(e).__name__, str(e)[:160], os.path.basename(tb.filename), tb.lineno))

    def each(label, items, fn):
        """Per-item guard: an unexpected error on one item drops that item (logged); the rest of the section runs."""
        for raw in items:
            try:
                fn(raw)
            except Exception as e:
                note("%s: dropped %.60r — unexpected %s: %s" % (label, raw, type(e).__name__, str(e)[:120]))

    # 1. new models — required fields validated, duplicate names skipped (aa_sync's normalizer: "GPT 6 Sol" == "GPT-6 Sol")
    def new_models():
        models = doc["models.json"]["models"]
        by_key = {_nk(m.get("name")): m for m in models if isinstance(m, dict)}

        def one(raw):
            m, why = check_new_model(raw)
            if why:
                note("newModels: dropped %.80r — %s" % (raw.get("name") if isinstance(raw, dict) else raw, why))
                return
            ok("newModels")
            k = name_key(m["name"])
            if k not in by_key:
                models.append(m)
                by_key[k] = m
                c["added"] += 1
        each("newModels", offer("newModels", "newModels"), one)
    section("newModels", ["models.json"], new_models)

    # 2. patch existing models with changed fields (built on a copy, swapped in whole: no half-applied update)
    def updated_models():
        by_key = {_nk(m.get("name")): m for m in doc["models.json"]["models"] if isinstance(m, dict)}

        def one(raw):
            name, fields = check_update(raw)
            if name is None:
                note("updatedModels: dropped %.80r — %s" % (raw, fields))
                return
            tgt = by_key.get(name_key(name))
            if not tgt:
                note("updatedModels: no model named %r" % name)
                return
            if fields:
                ok("updatedModels")
            new_t = copy.deepcopy(tgt)
            for key, val in fields.items():
                if key == "benchmarks":
                    b = new_t.get("benchmarks") if isinstance(new_t.get("benchmarks"), dict) else {}
                    b.update(val)
                    new_t["benchmarks"] = apply_bench_alias(b)[0]   # a delta's canonical key retires the old spelling
                else:
                    new_t[key] = val
            tgt.clear()
            tgt.update(new_t)
            c["updated"] += 1
        each("updatedModels", offer("updatedModels", "updatedModels"), one)
    section("updatedModels", ["models.json"], updated_models)

    # (3-4. trend points + prediction promotion: retired Sep 28 2026 — nothing renders trends/predictions)
    # 5. news — rolling refresh: validate, dedupe by url, newest-first, cap the window
    def news():
        nj = doc["news.json"]
        items = [x for x in (nj.get("items") or []) if isinstance(x, dict)]
        seen = {norm_url(x.get("url")) for x in items}

        def one(it):
            why = news_problem(it)
            if why:
                c["news_dropped"] += 1
                note("news: dropped %.70r — %s" % (it.get("url") if isinstance(it, dict) else it, why))
                return
            ok("news")
            k = norm_url(it["url"])
            if k not in seen:
                items.append({kk: it.get(kk) for kk in NEWS_KEYS})
                seen.add(k)
                c["news_added"] += 1
        each("news", offer("news", "news"), one)
        if c["news_added"]:
            items.sort(key=lambda x: x.get("date") if isinstance(x.get("date"), str) else "", reverse=True)
            nj["items"] = items[:NEWS_MAX]
    section("news", ["news.json"], news)

    # 6. editorial — prices normalized (+ notes), pulse replaced. leaderboard/upcoming/killed/sources are retired (D13)
    ed_delta = delta.get("editorial")
    if ed_delta is not None and not isinstance(ed_delta, dict):
        note("delta.editorial is %s, not an object — section ignored" % type(ed_delta).__name__)
        ed_delta = None
    ed_delta = ed_delta or {}
    for key in RETIRED_EDITORIAL:
        if key in ed_delta:
            note("ignored delta.editorial.%s (retired: the app no longer renders it)" % key)

    def prices():
        dp = ed_delta.get("prices")
        if dp is not None and not isinstance(dp, dict):
            note("delta.editorial.prices is %s, not an object — ignored" % type(dp).__name__)
            off["editorial.prices"] = 1
            dp = None
        for k, v in (dp or {}).items():
            off["editorial.prices"] = off.get("editorial.prices", 0) + 1
            if not isinstance(v, str):
                note("editorial.prices: %r is %s, not text — ignored" % (k, type(v).__name__))
            elif parse_price(v) != (None, None):
                ok("editorial.prices")
        pc = normalize_prices(doc["editorial.json"], doc["models.json"]["models"], dp)
        if pc["unmatched"]:
            note("price keys matching no catalog model: " + ", ".join(pc["unmatched"]))
        c["ed_fields"] += 1 if dp else 0
    section("editorial.prices", ["editorial.json"], prices)

    def pulse():
        ed = doc["editorial.json"]
        pulse_in = ed_delta.get("pulse")
        pulse_text = pulse_in.get("text") if isinstance(pulse_in, dict) else pulse_in
        if pulse_in is not None:
            off["editorial.pulse"] = 1
            if not isinstance(pulse_text, str):
                note("delta.editorial.pulse has no text — ignored")
        if isinstance(pulse_text, str) and pulse_text.strip():
            ok("editorial.pulse")
            old = ed.get("pulse") if isinstance(ed.get("pulse"), dict) else {}
            if old.get("text") != pulse_text.strip():   # an unchanged pulse keeps its old stamp: it didn't get fresher
                ed["pulse"] = {"text": pulse_text.strip(), "updated": now_iso, "routine": routine}
                c["ed_fields"] += 1
    section("editorial.pulse", ["editorial.json"], pulse)

    # 6b. releases — the radar snapshot, replaced when the delta carries one (D7 rules in validate_releases)
    def releases():
        rel_in = offer("releases", "releases")
        if not rel_in:
            return
        rel = doc["releases.json"]
        cur = [r for r in (rel.get("items") or []) if isinstance(r, dict)]
        new_items, dropped, refused = radar_update(cur, rel_in, doc["models.json"]["models"], now_dt)
        for model, why in dropped:
            note("releases: dropped %s — %s" % (model, why))
        if refused:
            note("releases: REFUSED a %d-item replacement for a %d-item radar (<%d%% of its non-late items) — kept the "
                 "current list" % (len(rel_in) - len(dropped), len(new_items), REL_MIN_KEEP * 100))
        rel["items"] = new_items
        c["rel_n"], c["rel_dropped"] = len(new_items), len(dropped)
        ok("releases", 0 if refused else len(rel_in) - len(dropped))
    section("releases", ["releases.json"], releases)

    # 6c. glossary — additive; a term matching an existing term or aka is a duplicate. A match on an acronym alone
    #     is logged, not rejected (xAI the lab vs XAI explainable AI share letters, not meaning).
    def glossary():
        gl = doc["glossary.json"]
        gterms = [t for t in (gl.get("terms") or []) if isinstance(t, dict)]
        gidx, aidx = {}, {}
        for t in gterms:
            akas = t.get("aka") if isinstance(t.get("aka"), list) else []
            for v in [t.get("term")] + akas:
                if gkey(v):
                    gidx.setdefault(gkey(v), t.get("term"))
            if gkey(t.get("acronym")):
                aidx.setdefault(gkey(t.get("acronym")), t.get("term"))

        def one(raw):
            t, why = check_glossary_item(raw)
            if why:
                note("glossary: dropped %.60r — %s" % (raw.get("term") if isinstance(raw, dict) else raw, why))
                return
            ok("glossary")
            k = gkey(t["term"])
            if k in gidx:
                note("glossary: skipped %r — duplicate of existing %r" % (t["term"], gidx[k]))
                return
            for kk in {k, gkey(t["acronym"])} - {""}:
                if kk in aidx:
                    note("glossary: %r shares %r with the acronym of %r (kept both)" % (t["term"], kk, aidx[kk]))
            gterms.append({kk: t.get(kk) for kk in GK})
            gidx[k] = t["term"]
            for a in t["aka"]:
                gidx.setdefault(gkey(a), t["term"])
            if gkey(t["acronym"]):
                aidx.setdefault(gkey(t["acronym"]), t["term"])
            c["gloss_added"] += 1
        each("glossary", offer("glossary", "glossary"), one)
        if c["gloss_added"]:
            gterms.sort(key=lambda x: (x.get("term") or "").lower() if isinstance(x.get("term"), str) else "")
            gl["terms"] = gterms
    section("glossary", ["glossary.json"], glossary)

    # 6d. briefs — per-model plain-English writeups, merged by model name (add/replace)
    def briefs():
        bf = doc["briefs.json"]
        bf.setdefault("briefs", {})
        bd = delta.get("briefs")
        if bd is not None and not isinstance(bd, dict):
            note("delta.briefs is %s, not an object — section ignored" % type(bd).__name__)
            off["briefs"] = 1
            bd = None
        for name, txt in (bd or {}).items():
            off["briefs"] = off.get("briefs", 0) + 1
            if isinstance(name, str) and name.strip() and isinstance(txt, str) and txt.strip():
                ok("briefs")
                if bf["briefs"].get(name) != txt:
                    bf["briefs"][name] = txt
                    c["briefs"] += 1
            else:
                note("briefs: dropped %.60r — the brief is empty or not text" % (name,))
    section("briefs", ["briefs.json"], briefs)

    # 6e. sources — log this sweep's consulted sources under its 3-hour slot, then apply the 30-day retention (D14)
    def sources():
        sj = doc["sources.json"]
        sweeps = [s for s in (sj.get("sweeps") or []) if isinstance(s, dict)]
        raw = offer("sweepSources", "sweepSources")
        srcs = [x for x in (check_source(r) for r in raw) if x]
        ok("sweepSources", len(srcs))
        if len(srcs) != len(raw):
            note("sweepSources: dropped %d malformed entries" % (len(raw) - len(srcs)))
        if srcs:
            entry = next((s for s in sweeps if s.get("date") == today_s and s.get("routine") == routine), None)
            if entry:
                entry["sources"] = srcs            # same slot ran twice the same day -> overwrite
            else:
                sweeps.append({"date": today_s, "routine": routine, "sources": srcs})
        kept, files, archived = plan_source_archive(sweeps, now_dt.date(), DATA)
        sj["sweeps"] = kept
        c["srcs"], c["archived"], c["archive_files"] = len(srcs), archived, files   # last: set only on success
    section("sources", ["sources.json"], sources)

    # 6f. forecasts.json — PREDICTION MARKETS + narrative. Stored rows re-validated (D4), deduped by canonical market
    #     key (D2), delta rows refresh by that key or append (asOf stamped, D3), then the prune runs EVERY merge (D1b).
    #     historics + trajForecasts are never touched here (manual AA-rebaseline territory).
    def markets():
        fc = doc["forecasts.json"]
        rows = fc.get("markets") if isinstance(fc.get("markets"), list) else []
        rows, bad, tagged = check_existing_markets(rows, today_s)
        rows, dupes = dedupe_markets(rows)
        by_row = {row_key(m): m for m in rows}

        def one(m):
            why = mkt_problem(m, today_s) if isinstance(m, dict) else "not an object"
            if why:
                c["mkt_rej"] += 1
                note("markets: rejected %.80r — %s" % (m.get("url") if isinstance(m, dict) else m, why))
                return
            ok("markets")
            clean = mkt_clean(m, today_s)
            k = row_key(clean)
            if k in by_row:                  # the LLM's re-read replaces the row's text; market_sync re-renders it from
                by_row[k].pop("by", None)    # the platform later this sweep if it can map it; the fresh asOf ends an
                by_row[k].pop("seen", None)  # undated row's grace period (prune_markets)
                by_row[k].update(clean)
                c["mkt_upd"] += 1
            else:
                rows.append(clean)
                by_row[k] = clean
                c["mkt_added"] += 1
        each("markets", offer("markets", "markets"), one)
        rows, pruned = prune_markets(rows, today_s)
        for m, why in bad + [(m, "duplicate of " + k) for m, k in dupes] + pruned:
            note("markets: dropped %s — %s" % (m.get("url"), why))
        if tagged:
            note("markets: tagged %d off-market rows kind:expert + curated" % tagged)
        if "markets" in fc or rows:
            fc["markets"] = rows
        c["mkt_dropped"] = len(bad) + len(dupes) + len(pruned)
    section("markets", ["forecasts.json"], markets)

    def story():
        ms = delta.get("marketsStory")
        if ms is None:
            return
        off["marketsStory"] = 1
        if isinstance(ms, list) and 3 <= len(ms) <= 6 and all(isinstance(s, dict) and s_or(s.get("t")) for s in ms):
            doc["forecasts.json"]["marketsStory"] = [{"h": s_or(s.get("h")), "t": s_or(s.get("t"))} for s in ms]
            c["story"] = len(ms)
            ok("marketsStory")
        else:
            note("delta.marketsStory ignored (needs 3-6 paragraphs, each with text)")
    section("marketsStory", ["forecasts.json"], story)

    # ---- stamp + serialize only what changed; meta bumps only if something did
    writes, changed = [], []
    for n, stamp_key in (("news.json", "updated"), ("editorial.json", "updated"), ("releases.json", "updated"),
                         ("glossary.json", "updated"), ("briefs.json", "updated"), ("sources.json", "updated"),
                         ("forecasts.json", "updated"), ("models.json", None)):
        text = dumps(doc[n])
        if text != orig[n]:
            if stamp_key:
                doc[n][stamp_key] = now_iso
                text = dumps(doc[n])
            writes.append((os.path.join(DATA, n), text, orig[n]))
            changed.append(n)
    meta = doc["meta.json"]
    models = doc["models.json"]["models"]
    if changed or c["archive_files"]:
        meta["lastUpdated"] = now_iso
        meta["models"] = len(models)
        meta["labs"] = len({m.get("lab").lower().strip() for m in models
                            if isinstance(m, dict) and isinstance(m.get("lab"), str) and m.get("lab").strip()})
        meta["sweeps"] = int(meta.get("sweeps", 0)) + 1
        meta["dataVersion"] = int(meta.get("dataVersion", 0)) + 1
        writes.append((os.path.join(DATA, "meta.json"), dumps(meta), orig["meta.json"]))
    # archives land before the trimmed sources.json: a crash in between duplicates sweeps (re-archived idempotently
    # next run) instead of losing them
    archive_writes = [(p, t, o) for p, (t, o) in sorted(c["archive_files"].items()) if t != o]
    commit(archive_writes + writes)

    print("merged: +%d models, ~%d updated, +%d news (-%d rejected), %d editorial fields, %d releases (-%d invalid), "
          "+%d markets (~%d refreshed, -%d rejected, -%d dropped, %dp story), +%d terms, %d briefs, %d sources "
          "(%d archived); %s%s"
          % (c["added"], c["updated"], c["news_added"], c["news_dropped"], c["ed_fields"], c["rel_n"], c["rel_dropped"],
             c["mkt_added"], c["mkt_upd"], c["mkt_rej"], c["mkt_dropped"], c["story"], c["gloss_added"], c["briefs"],
             c["srcs"], c["archived"],
             ("dataVersion=%s" % meta["dataVersion"]) if (changed or c["archive_files"]) else "no data changes",
             ("; SKIPPED (see above): " + ", ".join(skipped)) if skipped else ""))
    n_off, n_acc = sum(off.values()), sum(acc.values())
    try:
        for sec, n in section_rejects(off, acc):
            note("SECTION FREEZE: %s offered items and accepted none for %d sweeps running" % (sec, n))
    except OSError as e:               # the alarm's bookkeeping must never fail the merge itself
        note("section-reject state not updated (%s)" % e)
    if n_acc == 0:
        print("merge: nothing accepted (%d rejected)" % (n_off - n_acc))
        return EXIT_NOTHING
    return EXIT_PARTIAL if skipped else 0


if __name__ == "__main__":
    sys.exit(main())
