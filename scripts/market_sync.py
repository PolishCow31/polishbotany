#!/usr/bin/env python3
"""Deterministic market truth for data/forecasts.json markets[]: ask each platform's own public API whether a market
is still open and what it trades at, instead of trusting what the LLM read off a web page.

Why this exists: the research sweep reads markets through a browser that Kalshi rate-limits and Polymarket half-renders,
so it carried closed, resolved, dead and even 2025 markets for weeks (Sep 28 2026 audit: roughly a quarter of the 91
rows). These APIs are public and unauthenticated:
  Polymarket  gamma-api.polymarket.com/events?slug=<event-slug>
              empty list = the url is dead -> drop · every leg closed -> drop (never the event's own endDate, which
              Polymarket leaves on a ladder's first deadline)
  Manifold    api.manifold.markets/v0/slug/<slug>
              resolved / close time passed / "Contract not found" -> drop; the url is rebuilt as
              manifold.markets/<creatorUsername>/<slug> (the LLM often gets the username wrong)
  Kalshi      api.elections.kalshi.com/trade-api/v2/events/<EVENT_TICKER>
              every leg finalized/settled or "not_found" -> drop; a leg's price is its bid/ask midpoint (the last trade
              when the spread is wider than 10c)
  Metaculus   403s without an account: never fetched; the renderer's staleness rule (asOf) handles those rows
Expert rows (kind:"expert" / curated:true) are never touched.

THE INVARIANT (Sep 28 2026, round-2 skeptic): a row this script can MAP to one open, priced outcome is rendered ENTIRELY
from the platform — question = the platform's own title, forecast = "<pct>% — <outcome>" with the platform's own outcome
label ("Yes" for a yes/no market), plus up to 2 more open outcomes by price for a categorical market (3+ outcomes, not a
date ladder), resolveDate = that outcome's date, asOf = today (America/New_York), by = "api". A row it can't map is left
BYTE-IDENTICAL, so its asOf ages and the renderer's staleness mute can fire. (Before this, only the leading % was
rewritten and asOf restamped, so the LLM's leftover prose — "easing from 74", companion odds, "last read Aug 30" —
contradicted a number that looked fresh.) A mapped outcome that has CLOSED drops the row ("leg resolved"), even when
other legs are still open: the row's claim has settled.
ONE ROW PER QUESTION PER PLATFORM (Sep 28 2026): once questions come from the platforms, two markets on one platform
asking the same question read as a contradiction (Manifold's two "Will we get AGI before 2027?" markets: 2.3% and 6%).
After rendering, rows are grouped by (platform, question with case/punctuation/spacing ignored) and one survives: the
row rendered from the API this run over one that wasn't, then the market with more traders/volume, then the later
resolveDate, then the first. Expert/curated rows are exempt; the same question on two platforms is kept on both. A
group in which any row got no definitive answer this sweep (timeout, 429, time budget) is left whole until one does.
Mapping: a yes/no market always maps to its YES side, whatever the LLM wrote. Otherwise the outcome is the one the text
right after the forecast's leading % names — by date first, then exact label, then a unique whole-word match (see
pick); a negated claim ("No …", "won't …") or an ambiguous label maps to nothing.

FAIL-SAFE (aa_sync.py's philosophy): an HTTP error, timeout, 429 or unexpected JSON shape leaves that row UNCHANGED —
a row is only dropped on a definitive answer from its platform. More than half the fetches failing = write nothing.
An implausible wave of "doesn't exist" answers from one platform is treated as an API change, not as dead markets.
Always exits 0 (64 on an unknown flag): a market problem must never break the sweep.

  python3 scripts/market_sync.py              verify + render, write data/forecasts.json if anything changed
  python3 scripts/market_sync.py --dry-run    print what would change, write nothing
Summary line: "market-sync: N checked · D dropped (closed/resolved/dead) · R rendered from the API · U unmapped · F failed"
(+ " · K duplicate questions dropped" when the question dedupe removed rows; each one is logged "duplicate question: kept
<url>, dropped <url>")
"""
import calendar, json, math, os, re, sys, time, urllib.error, urllib.request
from datetime import date, datetime, timezone
from urllib.parse import quote

import merge as M   # one set of data rules: url parsing, market identity, the ET clock, atomic writes

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
UA = "botany-market-sync/1.0"
POLY_URL = "https://gamma-api.polymarket.com/events?slug=%s"
MANIFOLD_URL = "https://api.manifold.markets/v0/slug/%s"
KALSHI_URL = "https://api.elections.kalshi.com/trade-api/v2/events/%s"
TIMEOUT = 8        # seconds per request
PACE = 0.3         # seconds between requests: polite, far under every platform's published rate limits
BUDGET = 90        # seconds for the whole run; rows not reached in time are left unchanged (not failures)
FAIL_MAX = 0.5     # more than half the fetches failing = the platforms (or this Mac's network) are sick: write nothing
DEAD_MIN = 4       # "doesn't exist" answers only count as dead urls below this many per platform, or below half of
                   # that platform's fetches — a wave of them means the API changed, not that the markets vanished.
                   # And if EVERY market fetched on a platform is "not found" (2 or more), same verdict: 3 of 3 rows
                   # dropped at once is an outage signature, not three markets dying together (Sep 28 skeptic).
KALSHI_SETTLED = {"finalized", "settled"}                       # the whole event is over when every leg is one of these
KALSHI_CLOSED = {"finalized", "settled", "closed", "determined"}  # a leg that can't trade again
KALSHI_OPEN = {"active", "open"}


class FetchError(Exception):
    pass


def http_get(url):
    """-> (HTTP status, parsed JSON body or None). Raises FetchError on any transport failure. Tests replace this."""
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            status, raw = r.status, r.read(8000000)
    except urllib.error.HTTPError as e:
        try:
            status, raw = e.code, e.read(65536)
        except Exception:
            status, raw = e.code, b""
    except Exception as e:      # URLError, timeouts, resets, IncompleteRead...: all just "this row failed"
        raise FetchError("%s: %s" % (type(e).__name__, str(e)[:120]))
    try:
        return status, json.loads(raw.decode("utf-8", "replace"))
    except ValueError:
        return status, None


# ---------------------------------------------------------------- verdicts + dates
def _fail(why, limited=False):
    return {"state": "fail", "why": why, "limited": limited}


def _drop(why, dead=False):
    return {"state": "drop", "why": why, "dead": dead}


def _open(title, cands, binary, url=None, resolve=None, weight=None):
    """weight: the market's size for the question dedupe — Polymarket event volume, Manifold (traders, volume), Kalshi
    summed leg volume — or None when the API didn't say. Never written to a row."""
    return {"state": "open", "title": title, "cands": cands, "binary": binary, "url": url, "resolveDate": resolve,
            "weight": weight}


def cand(title, price, is_open, end=None, closed=None):
    """One outcome/leg: (title, price 0-1 or None, trading now, calendar date it resolves, closed for good)."""
    return (title, price, is_open, end, (not is_open) if closed is None else closed)


def _end(c):
    return c[3] if len(c) > 3 else None


def _closed(c):
    return c[4] if len(c) > 4 else not c[2]


def et_date(s, utc_midnight_is_date=False):
    """The calendar date an API timestamp names, read in America/New_York ('2027-01-01T04:59:00Z' is the last minute of
    Dec 31 ET). utc_midnight_is_date: Polymarket writes date-only leg ends as a bare midnight-UTC stamp
    ('2026-12-31T00:00:00Z' on its end-of-2026 legs), which names its UTC date, not the ET evening before. Not a general
    rule: Manifold's "before October 1, 2026" market closes 2026-10-01T00:00Z, which is Sep 30 ET. And not Polymarket's
    endDateIso either: across 3,402 live legs it is always the UTC date part of endDate, which would put every
    end-of-ET-day leg ("October 31" ending 2026-11-01T03:59Z — 1,859 of them) a day late."""
    if not isinstance(s, str) or not s.strip():
        return None
    s = s.strip()
    if M.valid_day(s):
        return s
    if utc_midnight_is_date and re.match(r"^\d{4}-\d{2}-\d{2}T00:00(:00(\.0+)?)?(Z|\+00:00)$", s) \
            and M.valid_day(s[:10]):
        return s[:10]
    t = s[:-1] + "+00:00" if s.endswith("Z") else s
    t = re.sub(r"\.(\d+)(?=[+-]\d{2}:\d{2}$|$)", lambda m: "." + (m.group(1) + "000000")[:6], t)   # py3.9: 6 digits
    try:
        dt = datetime.fromisoformat(t)
    except ValueError:
        return s[:10] if M.valid_day(s[:10]) else None
    return (dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)).astimezone(M.ET).strftime("%Y-%m-%d")


def ms_date(ms):
    if isinstance(ms, bool) or not isinstance(ms, (int, float)) or not 0 < ms < 1e14:
        return None
    return et_date(datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))


def leg_date(title, stamp):
    """A Polymarket leg's calendar date: the day its own title names ("October 31") in the year of its end stamp, read in
    ET or in UTC, whichever puts that day closer to the stamp ("December 31" ending 2027-01-01T00:00Z — 7 pm Dec 31 ET —
    is Dec 31 2026, not 2027: round-4 skeptic). A title day before both readings gives way to the end itself (a leg
    titled "October 9" that trades until Oct 15 resolves Oct 15). No day in the title: its end stamp (et_date,
    midnight-UTC read as a date)."""
    end = et_date(stamp, utc_midnight_is_date=True)
    sig = date_sig(title or "")
    if end and sig and sig[0] == "day":
        utc = stamp.strip()[:10] if re.match(r"^\s*\d{4}-\d{2}-\d{2}T.*(Z|\+00:00)\s*$", stamp) else None
        ends = sorted(date.fromisoformat(d) for d in {end, et_date(stamp), utc} if d and M.valid_day(d))
        years = [sig[3]] if sig[3] else sorted({e.year for e in ends})
        days = [date(y, sig[1], sig[2]) for y in years if 1 <= sig[2] <= calendar.monthrange(y, sig[1])[1]]
        if days:
            best = min(days, key=lambda d: min(abs((d - e).days) for e in ends))   # the title's day, when it is one
            return (best if best >= ends[0] else max(best, date.fromisoformat(end))).isoformat()   # of the readings
    return end


def _p(v):
    """A probability in [0, 1] from a float or a numeric string, else None."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if 0.0 <= f <= 1.0 else None


def _num(v):
    """A finite, non-negative number from an int/float or a numeric string ('42503.78'), else None."""
    if isinstance(v, bool):
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) and f >= 0 else None


def _jlist(v):
    if isinstance(v, list):
        return v
    try:
        v = json.loads(v) if isinstance(v, str) else None
    except ValueError:
        return None
    return v if isinstance(v, list) else None


def poly_price(mk):
    outs, prices = _jlist(mk.get("outcomes")), _jlist(mk.get("outcomePrices"))
    if not outs or not prices or len(outs) != len(prices):
        return None
    return _p(prices[outs.index("Yes") if "Yes" in outs else 0])


# ---------------------------------------------------------------- platform checks
def check_poly(slug, today_s):
    st, body = http_get(POLY_URL % quote(slug, safe=""))
    if st == 429:
        return _fail("429 rate-limited", True)
    if st != 200 or not isinstance(body, list):
        return _fail("HTTP %s, %s body" % (st, type(body).__name__))
    if not body:
        return _drop("dead url (Polymarket has no such event)", dead=True)
    ev = next((e for e in body if isinstance(e, dict) and str(e.get("slug", "")).lower() == slug.lower()), None)
    if ev is None:                      # the filter was ignored: never judge a row by some other event
        return _fail("response is for a different event")
    legs = [mk for mk in ev.get("markets") or [] if isinstance(mk, dict)] if isinstance(ev.get("markets"), list) else []
    if not legs:
        return _fail("event has no markets list")
    # Decided per LEG, never from the event: Polymarket leaves a "by <date>" event's endDate on its FIRST deadline
    # while later legs trade on (Sep 28 skeptic: next-alibaba-qwen-plus-3pt8 said Sep 30 with its Oct 31 and Dec 31
    # legs open). The event goes only when every leg has closed; each leg's own date is what dates a row.
    def trading(mk):
        return mk.get("closed") is not True and mk.get("active") is not False and mk.get("archived") is not True
    if len(legs) == 1:                  # one market: yes/no -> its YES side; named outcomes -> each is a candidate
        mk = legs[0]
        outs, prices = _jlist(mk.get("outcomes")), _jlist(mk.get("outcomePrices"))
        if not outs or not prices or len(outs) != len(prices):
            return _fail("market outcomes unreadable")
        end, op, shut = leg_date(mk.get("groupItemTitle"), mk.get("endDate")), trading(mk), mk.get("closed") is True
        if [str(o).strip().lower() for o in outs] == ["yes", "no"]:   # its YES side, under the leg's own label if any
            lab = str(mk.get("groupItemTitle") or "").strip()
            cands, binary = [cand(lab if lab and lab.lower() != "yes" else "Yes", _p(prices[0]), op, end, shut)], True
        else:                           # "Will Anthropic or OpenAI IPO first?" trades Anthropic / OpenAI, not Yes / No
            cands, binary = [cand(str(o), _p(p), op, end, shut) for o, p in zip(outs, prices)], False
    else:
        cands = [cand(str(mk.get("groupItemTitle") or mk.get("question") or ""), poly_price(mk), trading(mk),
                      leg_date(mk.get("groupItemTitle"), mk.get("endDate")), mk.get("closed") is True) for mk in legs]
        binary = False
    if not any(c[2] for c in cands):
        return _drop("every leg closed")
    return _open(ev.get("title"), cands, binary, weight=_num(ev.get("volume")))


def check_manifold(slug, today_s):
    st, body = http_get(MANIFOLD_URL % quote(slug, safe=""))
    if st == 429:
        return _fail("429 rate-limited", True)
    if st == 404 and isinstance(body, dict) and "not found" in str(body.get("message", "")).lower():
        return _drop("dead url (Manifold: contract not found)", dead=True)
    if st != 200 or not isinstance(body, dict):
        return _fail("HTTP %s, %s body" % (st, type(body).__name__))
    if str(body.get("slug", "")).lower() != slug.lower():
        return _fail("response is for a different market")
    if body.get("isResolved") is True:
        return _drop("resolved")
    close = ms_date(body.get("closeTime"))
    if close and close < today_s:
        return _drop("closed %s" % close)
    user = body.get("creatorUsername")
    url = "https://manifold.markets/%s/%s" % (user, body["slug"]) if isinstance(user, str) and user.strip() else None
    traders, vol = _num(body.get("uniqueBettorCount")), _num(body.get("volume"))
    w = (traders, vol) if traders is not None and vol is not None else None   # traders first: mana volume is whale-heavy
    if body.get("outcomeType") == "BINARY":
        return _open(body.get("question"), [cand("Yes", _p(body.get("probability")), True, close)], True, url, close, w)
    cands = [cand(str(a.get("text") or ""), _p(a.get("probability")), not a.get("resolution"), close,
                  bool(a.get("resolution"))) for a in (body.get("answers") or []) if isinstance(a, dict)]
    return _open(body.get("question"), cands, False, url, close, w)   # no answers (numeric markets): renders nothing


def check_kalshi(ticker, today_s):
    st, body = http_get(KALSHI_URL % quote(ticker, safe=""))
    if st == 429:
        return _fail("429 rate-limited", True)
    if st == 404 and isinstance(body, dict) and isinstance(body.get("error"), dict) \
            and body["error"].get("code") == "not_found":
        return _drop("dead url (Kalshi: event not found)", dead=True)
    if st != 200 or not isinstance(body, dict) or not isinstance(body.get("event"), dict):
        return _fail("HTTP %s, %s body" % (st, type(body).__name__))
    if str(body["event"].get("event_ticker", "")).upper() != ticker.upper():
        return _fail("response is for a different event")
    legs = body.get("markets") if isinstance(body.get("markets"), list) else body["event"].get("markets")
    legs = [m for m in (legs or []) if isinstance(m, dict)]
    if not legs:
        return _fail("event has no legs")
    if all(str(m.get("status", "")).lower() in KALSHI_SETTLED for m in legs):
        return _drop("every leg settled")

    def price(m):
        """Bid/ask midpoint when the spread is 10c or less, else the last trade (Polymarket's display rule): on a
        thin book the last trade can sit outside the live spread (Sep 28: last 0.66 vs bid 0.70 / ask 0.72)."""
        bid, ask = _p(m.get("yes_bid_dollars")), _p(m.get("yes_ask_dollars"))
        if bid is not None and ask is not None and 0 <= ask - bid <= 0.10:
            return (bid + ask) / 2
        v = _p(m.get("last_price_dollars"))
        if v is None and isinstance(m.get("last_price"), (int, float)) and not isinstance(m.get("last_price"), bool):
            v = _p(m["last_price"] / 100.0)      # older API: cents
        return v
    status = lambda m: str(m.get("status", "")).lower()

    def label(m):   # a one-leg event states its YES side, under the leg's own subtitle if it has one ("Before 2027")
        if len(legs) == 1:
            sub = str(m.get("yes_sub_title") or m.get("subtitle") or "").strip()
            return sub if sub and sub.lower() != "yes" else "Yes"
        return str(m.get("yes_sub_title") or m.get("subtitle") or m.get("title") or "")
    cands = [cand(label(m), price(m), status(m) in KALSHI_OPEN, et_date(m.get("close_time")), status(m) in KALSHI_CLOSED)
             for m in legs]
    vols = [_num(m.get("volume_fp")) if m.get("volume_fp") is not None else _num(m.get("volume")) for m in legs]
    return _open(body["event"].get("title"), cands, len(legs) == 1,
                 weight=sum(vols) if all(v is not None for v in vols) else None)


CHECKS = {"poly": check_poly, "manifold": check_manifold, "kalshi": check_kalshi}


def target(m):
    """-> (platform tag, API identifier) for rows this script can verify, else (None, None)."""
    h, parts = M.url_parts(m.get("url"))
    tag = M.market_tag(h)
    if tag == "poly" and len(parts) >= 2 and parts[0] == "event":
        return "poly", parts[1].lower()
    if tag == "manifold" and len(parts) >= 2:
        return "manifold", parts[1]
    if tag == "kalshi" and len(parts) >= 4:
        return "kalshi", parts[3].upper()
    return None, None


# ---------------------------------------------------------------- which outcome does the row claim?
LEAD_PCT = re.compile(r"^(\s*[~≈]?\s*)(\d{1,3}(?:\.\d+)?)(\s*%)")
# A claim on the NO side of one outcome ("93% — No Gemini by Oct 31", "7% — won't ship by Oct") names no outcome's YES
# price, so on a categorical/ladder market such a row maps to nothing. (Yes/no markets map to YES regardless: the
# rendered row then states the YES side under the platform's own question, which is true.)
NEG_RE = re.compile(r"^(?:no|not|never|none)\b|\b(?:no|not|never|none|won'?t|will not|wouldn'?t|isn'?t|is not|"
                    r"doesn'?t|does not|didn'?t|did not|can'?t|cannot|fails? to)\b")


def simp(s):
    return " ".join(str(s or "").lower().replace("’", "'").split()).strip(" .,:;")


def simp_title(s):   # candidate titles can lead with a glyph: Polymarket's "↑ 1530" is the 1530+ leg
    return re.sub(r"^[^0-9a-z#$]+", "", simp(s))


def lead_label(fc):
    """'76% — Anthropic, up a point; ...' -> 'anthropic'. None when the forecast has no leading %."""
    m = LEAD_PCT.match(fc if isinstance(fc, str) else "")
    if not m:
        return None
    rest = re.sub(r"^\s*(?:[—–-]+|:)\s*", "", fc[m.end():])
    return simp(re.split(r"\s*(?:[,;(]|\.\s|\s[—–-]\s)", rest, 1)[0])


def api_outcome(fc):
    """The outcome label of a forecast in the "NN% — <outcome>" form, read WHOLE: '74.5% — Anthropic · Google 10.5%'
    -> 'anthropic', '64.5% — Before Jan 1, 2028' -> 'before jan 1, 2028'. That is the form this script writes and the
    form the prompt asks the LLM for, and a platform's own labels carry commas ("Before Jan 1, 2028"), which
    lead_label's prose split would cut: the row would stop mapping and its asOf would age into the 21-day prune."""
    m = re.match(r"^\s*[~≈]?\s*\d{1,3}(?:\.\d+)?\s*%\s*(?:[—–-]+|:)\s*(.+?)(?:\s+·\s+|$)", fc if isinstance(fc, str) else "")
    return simp(m.group(1)) if m else None


def pick_whole(label, cands):
    """Index of the outcome a WHOLE label is: the platform's exact outcome title, or, for a label that is itself a date,
    the leg with that date. Never a substring guess — "71.5% — Anthropic's model, easing; ChatGPT 10.8%" must not land
    on ChatGPT — so it is safe on any row, LLM-written or not, and runs before lead_label's prose reading."""
    if not label:
        return None
    if date_sig(label):
        return pick(label, cands)                       # pick's date branch never falls through to text
    for norm in (simp, simp_title):                     # "↑ 1530" exactly first, then glyph-insensitive
        hit = [i for i, c in enumerate(cands) if norm(c[0]) and norm(c[0]) == norm(label)]
        if hit:
            return hit[0] if len(hit) == 1 else None
    return None


def date_sig(s):
    """'by Sep 30' / 'September 30, 2026' -> ('day', 9, 30, year|None); 'before 2028' / 'Before Jan 1, 2028' ->
    ('before-year', 2028, None, None); 'by 2028' / '2028' -> ('year', 2028, None, None); 'Before September' /
    'before Sep 1' -> ('before-month', 9, None, year|None)."""
    s = simp(s)
    m = re.match(r"^before\s+jan(?:uary)?\.?\s+1(?:st)?,?\s+(20\d\d)$", s)
    if m:
        return ("before-year", int(m.group(1)), None, None)
    m = re.match(r"^(by|before|in)?\s*(20\d\d)$", s)
    if m:
        return ("before-year" if m.group(1) == "before" else "year", int(m.group(2)), None, None)
    m = re.match(r"^(by|before|on|until)?\s*" + M._MONTHS + r"\.?(?:\s+(\d{1,2})(?:st|nd|rd|th)?)?(?:,?\s+(20\d\d))?$", s)
    if m:
        mon, day = M.MON_NUM[m.group(2)[:3]], int(m.group(3)) if m.group(3) else None
        yr = int(m.group(4)) if m.group(4) else None
        if m.group(1) == "before" and day in (None, 1):
            return ("before-month", mon, None, yr)
        return ("day", mon, day, yr) if day else ("month", mon, None, yr)
    return None


def _same_date(a, b):
    return a[:3] == b[:3] and (a[3] is None or b[3] is None or a[3] == b[3])


def pick(label, cands):
    """Index of the ONE outcome the label names, else None (never a guess). In order:
      1. a date: a label that is itself a date ("by Oct 31", "before 2028") matches an outcome only by date — the date
         its title names, else (for a "by <day>" label) the leg's own date — and never falls through to text: "before
         2028" must not land on a "2028" answer, which in a by-year market is a different number (28% vs 50%);
      2. exact normalized label;
      3. a UNIQUE whole-word match of an outcome's title inside the label. Two or more -> None."""
    if not label:
        return None
    sig = date_sig(label)
    if sig:
        hit = [i for i, c in enumerate(cands) if date_sig(c[0]) and _same_date(sig, date_sig(c[0]))]
        if not hit and sig[0] == "day":
            hit = [i for i, c in enumerate(cands) if _end(c) and (int(_end(c)[5:7]), int(_end(c)[8:10])) == sig[1:3]
                   and (sig[3] is None or int(_end(c)[:4]) == sig[3])]
        return hit[0] if len(hit) == 1 else None
    hit = [i for i, c in enumerate(cands) if simp_title(c[0]) == label]
    if len(hit) == 1:
        return hit[0]
    if hit:
        return None
    hit = [i for i, c in enumerate(cands)
           if simp_title(c[0]) and re.search(r"(?<![0-9a-z])" + re.escape(simp_title(c[0])) + r"(?![0-9a-z])", label)]
    return hit[0] if len(hit) == 1 else None


def fmt_pct(p):
    return ("%.1f" % round(p * 100, 1)).rstrip("0").rstrip(".")


def date_ladder(cands):
    """Outcomes that are dates ("October 31", "Before 2027", "2028"): cumulative legs, so no companion odds."""
    titled = [c for c in cands if simp(c[0])]
    return bool(titled) and 2 * sum(1 for c in titled if date_sig(c[0])) >= len(titled)


def render(m, v, today_s):
    """-> ("api", fields to set) | ("drop", why) | ("skip", why the row stays byte-identical)."""
    cands, title = v.get("cands") or [], v.get("title")
    if not (isinstance(title, str) and title.strip()):
        return "skip", "the API gave no title"
    if v.get("binary"):
        c = cands[0]
        outcome = c[0] or "Yes"
    else:
        i = pick_whole(api_outcome(m.get("forecast")), cands)   # "NN% — <one of the platform's own outcomes>"
        if i is None:                                           # else read the lead of LLM prose, guarded
            label = lead_label(m.get("forecast"))
            if label is None:
                return "skip", "forecast has no leading % naming an outcome"
            if NEG_RE.search(label):
                return "skip", "negated claim (%r) on a multi-outcome market" % label
            i = pick(label, cands)
            if i is None:
                return "skip", "%r names no single outcome" % label
        c, outcome = cands[i], cands[i][0].strip()
    if _closed(c):
        return "drop", "leg resolved (%s)" % outcome
    if not c[2] or c[1] is None:
        return "skip", "outcome %r is not trading or has no price" % outcome
    fc = "%s%% — %s" % (fmt_pct(c[1]), outcome)
    if not v.get("binary") and len(cands) >= 3 and not date_ladder(cands):
        others = sorted((k for k in cands if k is not c and k[2] and k[1] is not None and simp(k[0])),
                        key=lambda k: -k[1])[:2]
        fc += "".join(" · %s %s%%" % (k[0].strip(), fmt_pct(k[1])) for k in others)
    fields = {"question": title.strip(), "forecast": fc, "asOf": today_s, "by": "api"}
    rd = _end(c) or v.get("resolveDate")
    if rd and M.valid_day(rd):
        fields["resolveDate"] = rd
    if v.get("url"):
        fields["url"] = v["url"]
    return "api", fields


# ---------------------------------------------------------------- one row per question per platform
def qkey(q):
    """'Will we get AGI before 2027?' -> 'will we get agi before 2027': case, punctuation and spacing don't make a
    different question."""
    return " ".join(re.sub(r"[\W_]+", " ", q.lower()).split()) if isinstance(q, str) else ""


def dedupe_questions(rows, meta):
    """-> (rows with one per (platform, question), one log line per dropped row). meta[i] = (rendered from the API this
    run, weight from this run's fetch or None, no definitive answer this run). A group with ANY row that got no
    definitive answer (timeout, 429, time budget) is skipped this sweep: rows are only ever deleted on a platform's
    definitive answer, and a timed-out row would otherwise lose to its rendered twin (Sep 28 round-4 skeptic).
    Survivor: rendered-now over not; then the bigger market, compared only when every row of the group has a size;
    then the later resolveDate; then the first. Expert/curated rows are exempt (off-market forecasts: two can share a
    question). The platform comes from the url, so the same question on two platforms is two groups: cross-platform
    agreement is information, not a duplicate."""
    groups = {}
    for i, m in enumerate(rows):
        if not isinstance(m, dict) or m.get("kind") == "expert" or m.get("curated") is True:
            continue
        q = qkey(m.get("question"))
        if not q:
            continue
        tag = M.mkt_key(m.get("url")).split(":", 1)[0]
        plat = tag if tag != "url" else "url/" + str(m.get("platform") or "").strip().lower()
        groups.setdefault((plat, q), []).append(i)
    drop, lines = set(), []
    for idx in groups.values():
        if len(idx) < 2 or any(meta[i][2] for i in idx):
            continue
        ws = [meta[i][1] for i in idx]
        sized = all(w is not None for w in ws) and len({type(w) for w in ws}) == 1

        def rank(i):
            rd = rows[i].get("resolveDate")
            return (meta[i][0], meta[i][1] if sized else 0, rd if M.valid_day(rd) else "", -i)
        keep = max(idx, key=rank)
        for i in idx:
            if i != keep:
                drop.add(i)
                lines.append("duplicate question: kept %s, dropped %s" % (rows[keep].get("url"), rows[i].get("url")))
    return [m for i, m in enumerate(rows) if i not in drop], lines


# ---------------------------------------------------------------- run
def sync(rows, today_s, clock=time.monotonic, sleep=time.sleep):
    """Pure-ish core (network only via http_get). -> (new rows, stats dict, detail lines, write_ok)."""
    t0, cache, order, blocked = clock(), {}, [], set()
    st = {"checked": 0, "dropped": 0, "rendered": 0, "unmapped": 0, "failed": 0, "fetches": 0, "fetch_fail": 0,
          "late": 0, "limited": 0, "duplicates": 0}
    lines = []
    for m in rows:                                       # pass 1: one fetch per distinct market
        if not isinstance(m, dict) or m.get("curated") is True or m.get("kind") == "expert":
            continue
        tag, ident = target(m)
        if not tag:
            continue
        key = (tag, ident.lower())
        if key in cache:
            continue
        if tag in blocked:
            cache[key] = _fail("skipped: %s rate-limited this run" % tag, True)
            continue
        if clock() - t0 > BUDGET:
            cache[key] = None                            # not reached: row left as-is, not counted as a failure
            continue
        if st["fetches"]:
            sleep(PACE)
        st["fetches"] += 1
        try:
            v = CHECKS[tag](ident, today_s)
        except FetchError as e:
            v = _fail(str(e))
        except Exception as e:                            # a parser bug on one weird payload must not kill the run
            v = _fail("unexpected %s: %s" % (type(e).__name__, str(e)[:100]))
        if v["state"] == "fail":
            st["fetch_fail"] += 1
            if v.get("limited"):
                blocked.add(tag)
        cache[key] = v
        order.append(key)
    for tag in CHECKS:                                   # pass 2: a wave of "doesn't exist" = the API moved, not the markets
        dead = [k for k in order if k[0] == tag and cache[k]["state"] == "drop" and cache[k].get("dead")]
        n = sum(1 for k in order if k[0] == tag)
        if (n >= 2 and len(dead) == n) or (len(dead) >= DEAD_MIN and len(dead) > 0.5 * n):
            lines.append("%s reported %d of %d markets missing — treated as an API problem, nothing dropped"
                         % (tag, len(dead), n))
            for k in dead:
                cache[k] = _fail("implausible mass not-found")
                st["fetch_fail"] += 1
    out, meta = [], []          # meta[i] for out[i]: (rendered from the API now, market size, no definitive answer now)
    for m in rows:                                       # pass 3: apply verdicts
        tag, ident = target(m) if isinstance(m, dict) and m.get("curated") is not True and m.get("kind") != "expert" \
            else (None, None)
        if not tag:
            out.append(m)
            meta.append((False, None, False))            # no API to ask (Metaculus): nothing transient about it
            continue
        v = cache.get((tag, ident.lower()))
        if v is None:
            st["late"] += 1
            out.append(m)
            meta.append((False, None, True))
            continue
        if v.get("limited") and v["why"].startswith("skipped"):
            st["limited"] += 1
            out.append(m)
            meta.append((False, None, True))
            continue
        st["checked"] += 1
        if v["state"] == "fail":
            st["failed"] += 1
            lines.append("unchanged %s:%s — %s" % (tag, ident, v["why"]))
            out.append(m)
            meta.append((False, None, True))
            continue
        if v["state"] == "drop":
            st["dropped"] += 1
            lines.append("dropped %s:%s — %s" % (tag, ident, v["why"]))
            continue
        crashed = False
        try:
            kind, x = render(m, v, today_s)
        except Exception as e:                            # a render bug on one row leaves that row exactly as it was
            kind, x, crashed = "skip", "unexpected %s: %s" % (type(e).__name__, str(e)[:100]), True
        if kind == "drop":
            st["dropped"] += 1
            lines.append("dropped %s:%s — %s" % (tag, ident, x))
            continue
        if kind == "api":
            m = dict(m)
            m.update(x)
            st["rendered"] += 1
        else:
            st["unmapped"] += 1
            lines.append("unmapped %s:%s — %s" % (tag, ident, x))
        out.append(m)
        meta.append((kind == "api", v.get("weight"), crashed))
    out, dup_lines = dedupe_questions(out, meta)         # pass 4: one row per question per platform
    st["duplicates"] = len(dup_lines)
    lines.extend(dup_lines)
    write_ok = not (st["fetches"] and st["fetch_fail"] > FAIL_MAX * st["fetches"])
    return out, st, lines, write_ok


def main(argv):
    bad = [a for a in argv if a != "--dry-run"]
    if bad:    # a typo'd flag (e.g. "--dry-rn") must never fall through to a real write; update.sh passes no arguments
        print("market-sync: unknown argument %s; usage: market_sync.py [--dry-run]. Nothing done." % " ".join(bad))
        return 64
    dry = "--dry-run" in argv
    stamp = datetime.now(M.ET).strftime("%Y-%m-%d %H:%M:%S")
    try:
        path = os.path.join(DATA, "forecasts.json")
        with open(path) as f:
            orig = f.read()
        fc = json.loads(orig)
        rows = fc.get("markets") if isinstance(fc, dict) else None
        if not isinstance(rows, list):
            print("%s market-sync: SKIPPED (forecasts.json has no markets list) — nothing written" % stamp)
            return 0
        now = datetime.now(M.ET)
        new_rows, st, lines, write_ok = sync(rows, now.strftime("%Y-%m-%d"))
        extra = "".join([" · %d not reached (%ds budget)" % (st["late"], BUDGET) if st["late"] else "",
                         " · %d skipped after a 429" % st["limited"] if st["limited"] else "",
                         " · %d duplicate questions dropped" % st["duplicates"] if st["duplicates"] else ""])
        print("%s market-sync: %d checked · %d dropped (closed/resolved/dead) · %d rendered from the API · %d unmapped "
              "(left as is) · %d failed%s" % (stamp, st["checked"], st["dropped"], st["rendered"], st["unmapped"],
                                               st["failed"], extra))
        for ln in lines[:60]:
            print("   " + ln)
        if not write_ok:
            print("%s market-sync: SKIPPED — %d of %d fetches failed (>%d%%); nothing written"
                  % (stamp, st["fetch_fail"], st["fetches"], FAIL_MAX * 100))
            return 0
        if new_rows == rows:
            return 0
        fc["markets"] = new_rows
        fc["updated"] = now.replace(microsecond=0).isoformat()
        if dry:
            print("%s market-sync: --dry-run, nothing written" % stamp)
            return 0
        M.write_atomic(path, M.dumps(fc))
    except Exception as e:                                # never break the sweep
        print("%s market-sync: ERROR %s: %s — nothing written" % (stamp, type(e).__name__, str(e)[:200]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
