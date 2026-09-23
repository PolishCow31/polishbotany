#!/usr/bin/env python3
"""Keep Botany's AA-Index column an exact copy of Artificial Analysis's live Intelligence Index.

Why this exists: AA re-versions its index every few months (v4.0 Jan, v4.1 Jun 16, v4.3 Sep 22 2026) and every
re-version re-scores every model non-linearly. When the numbers were LLM-researched and pinned to one version,
the leaderboard froze on a dead scale (Sep 2026: Fable 5.1 shown at 66 vs AA's live 53, Opus 5.5 missing).
So the LLM no longer writes AA numbers; this script copies them.

Source: AA's leaderboard page embeds the full model dataset its table renders (Next.js flight data). Every value
the page DISPLAYS is cross-checked against the embedded floats before anything is written. AA lists each model
once per effort setting (max / xhigh / high ...); Botany shows one number per model, the best variant, rounded
half-up exactly like AA's table.

  python3 scripts/aa_sync.py                 check only (default): report drift, write nothing
  python3 scripts/aa_sync.py --sync          same-scale upkeep, run by update.sh after every merge: fills missing
                                             values, mirrors re-scores, drops values AA doesn't list. REFUSES
                                             (exit 2) when AA has re-versioned, so scales can never mix.
  python3 scripts/aa_sync.py --rebase        the manual step after AA re-versions: rewrites the whole column onto
                                             AA's current version and stamps data/meta.json aaScale.
  --dry-run                                  with --sync/--rebase: print the plan, write nothing.

Exit: 0 ok · 1 fetch/parse failure (nothing written) · 2 AA re-versioned vs meta.aaScale (run --rebase).
"""
import json, math, os, re, sys, urllib.request
from datetime import datetime
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
URL = "https://artificialanalysis.ai/leaderboards/models"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36"
KEY = "AA-Index"
AA_KEY_RE = re.compile(r"aa[ -]?index|intelligence index", re.I)   # mirrors index.html benchOf('aa')
MIN_SCORED, MIN_CHECKED = 300, 50                                  # sanity floors for a trustworthy parse

# Botany name -> AA base name, only where normalized names genuinely differ. Keep this short and explicit.
ALIASES = {
    "Gemini 3.1 Pro": "Gemini 3.1 Pro Preview",   # AA only ever listed the preview entry
    "Grok 4.20 Beta": "Grok 4.20 0309 v2",        # Botany's entry covers the line through the 0309 v2 reasoning variant
}
LAB_PREFIXES = {"meta", "ibm", "nvidia", "google", "openai", "xai", "anthropic", "alibaba", "microsoft",
                "amazon", "mistral", "cohere", "tencent", "baidu", "xiaomi", "zhipu", "moonshot"}
EFFORT_RE = re.compile(r"\s*\((?=[^()]*\b(?:max|xhigh|high|medium|low|minimal|non-reasoning|reasoning|"
                       r"with fallback|thinking|effort)\b)[^()]*\)\s*$", re.I)


def load(name):
    with open(os.path.join(DATA, name)) as f:
        return json.load(f)


def save(name, obj):                      # identical to merge.py's save()
    with open(os.path.join(DATA, name), "w") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
        f.write("\n")


def half_up(x):
    return int(math.floor(x + 0.5))


def norm(name):
    return " ".join(re.sub(r"[^0-9a-z.]+", " ", (name or "").lower()).split())


def base_name(short):
    prev = None
    while prev != short:
        prev, short = short, EFFORT_RE.sub("", short)
    return short.strip()


# ---------------------------------------------------------------- fetch + parse
def fetch(url=URL):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html"})
    with urllib.request.urlopen(req, timeout=45) as r:
        return r.read().decode("utf-8", "replace")


def _array_end(text, start):
    """Index just past the JSON array that opens at text[start] ('['): string-aware bracket matching."""
    depth, instr, esc = 0, False, False
    for j in range(start, len(text)):
        c = text[j]
        if instr:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                instr = False
        elif c == '"':
            instr = True
        elif c == "[":
            depth += 1
        elif c == "]":
            depth -= 1
            if depth == 0:
                return j + 1
    raise ValueError("unterminated array")


class _Table(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows, self.row, self.cell, self.in_tbody = [], None, None, False

    def handle_starttag(self, tag, attrs):
        if tag == "tbody":
            self.in_tbody = True
        elif tag == "tr" and self.in_tbody:
            self.row = []
        elif tag == "td" and self.row is not None:
            self.cell = []

    def handle_endtag(self, tag):
        if tag == "td" and self.cell is not None:
            self.row.append(" ".join("".join(self.cell).split()))
            self.cell = None
        elif tag == "tr" and self.row is not None:
            self.rows.append(self.row)
            self.row = None
        elif tag == "tbody":
            self.in_tbody = False

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)


def parse(html):
    """-> (aa_models, version_or_None, stats). Raises ValueError when the page can't be trusted."""
    flight = "".join(json.loads(m.group(1)) for m in
                     re.finditer(r'self\.__next_f\.push\(\[1,("(?:[^"\\]|\\.)*")\]\)', html))
    best, pos, opener = None, 0, re.compile(r'\[\{"slug":"')
    while True:                           # linear: scan each slug-object array once; skip past the model list
        m = opener.search(flight, pos)
        if not m:
            break
        pos = m.end()                     # a non-model array may still nest model arrays: keep scanning inside it
        try:
            e = _array_end(flight, m.start())
            arr = json.loads(flight[m.start():e])
        except ValueError:                # json.JSONDecodeError subclasses ValueError
            continue
        if isinstance(arr, list) and arr and isinstance(arr[0], dict) and "intelligenceIndex" in arr[0]:
            if best is None or len(arr) > len(best):
                best = arr
            pos = e
    if not best:
        raise ValueError("no embedded model array with intelligenceIndex")
    scored = [m for m in best if isinstance(m.get("intelligenceIndex"), (int, float))]

    t = _Table()
    t.feed(html)
    by_short = {}
    for m in scored:
        by_short.setdefault(m.get("shortName"), []).append(m)
    checked, bad = 0, []
    for row in t.rows:
        if len(row) < 4 or not re.match(r"^\d+\*?$", row[3]):
            continue
        shown, est = int(row[3].rstrip("*")), row[3].endswith("*")
        cands = by_short.get(row[0], [])
        checked += 1
        if not any(half_up(c["intelligenceIndex"]) == shown and bool(c.get("intelligenceIndexIsEstimated")) == est
                   for c in cands):
            bad.append(row[0])
    if len(scored) < MIN_SCORED or checked < MIN_CHECKED or bad:
        raise ValueError("untrustworthy parse: %d scored, %d displayed rows checked, %d mismatched %s"
                         % (len(scored), checked, len(bad), bad[:5]))
    vers = re.findall(r"Intelligence Index v(\d+\.\d+)", html)
    version = ("v" + max(vers, key=lambda v: tuple(map(int, v.split("."))))) if vers else None
    return scored, version, {"scored": len(scored), "checked": checked}


# ---------------------------------------------------------------- mapping
def group(aa_models):
    """norm(base name) -> {'value', 'est', 'base', 'variants'} keeping the best variant per model."""
    g = {}
    for m in aa_models:
        base = base_name(m.get("shortName") or m.get("name") or "")
        k = norm(base)
        v = float(m["intelligenceIndex"])
        cur = g.get(k)
        if cur is None or v > cur["raw"]:
            g[k] = {"raw": v, "value": half_up(v), "est": bool(m.get("intelligenceIndexIsEstimated")),
                    "base": base, "creator": m.get("modelCreatorName"), "variants": (cur or {}).get("variants", [])}
        g[k]["variants"].append(m.get("shortName"))
    return g


def match(models, groups):
    """-> ({botany name: group}, [(botany name, reason)] unmatched-with-old-value, conflicts)."""
    hits, claimed, conflicts = {}, {}, []
    exact = {}
    for m in models:
        k = norm(ALIASES.get(m["name"], m["name"]))
        if k in groups:
            exact[m["name"]] = k
    for m in models:
        name = m["name"]
        k = exact.get(name)
        if k is None:
            toks = norm(name).split()
            if len(toks) > 1 and toks[0] in LAB_PREFIXES:
                k2 = " ".join(toks[1:])
                if k2 in groups and k2 not in exact.values():
                    k = k2
        if k is None:
            continue
        if k in claimed:
            conflicts.append((name, claimed[k], groups[k]["base"]))
            continue
        claimed[k] = name
        hits[name] = groups[k]
    return hits, conflicts


def plan(models, groups):
    hits, conflicts = match(models, groups)
    changes = []                                     # (name, old, new)
    for m in models:
        b = m.get("benchmarks") or {}
        olds = {k: v for k, v in b.items() if AA_KEY_RE.search(k)}
        old = olds.get(KEY)
        g = hits.get(m["name"])
        new = g["value"] if g else None
        stray = [k for k in olds if k != KEY]         # any other AA-like key would win benchOf()'s max()
        if old != new or stray:
            changes.append((m["name"], old, new, stray))
    return hits, conflicts, changes


def apply(models, changes):
    by = {m["name"]: m for m in models}
    for name, _old, new, stray in changes:
        b = by[name].setdefault("benchmarks", {})
        for k in stray:
            b.pop(k, None)
        if new is None:
            b.pop(KEY, None)
        else:
            b[KEY] = new


def main(argv):
    mode = "--rebase" if "--rebase" in argv else "--sync" if "--sync" in argv else "--check"
    dry = "--dry-run" in argv or mode == "--check"
    verbose = "-v" in argv or dry
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        aa, version, stats = parse(fetch())
    except Exception as e:                            # network, block, layout change: never write on doubt
        print("%s aa-sync: SKIPPED (%s) — nothing written" % (stamp, str(e)[:200]))
        return 1
    meta = load("meta.json")
    pinned = meta.get("aaScale")
    doc = load("models.json")
    models = doc["models"]
    groups = group(aa)
    hits, conflicts, changes = plan(models, groups)

    # rescale guard: a version change (or, when the page stops naming its version, a mass shift) must never
    # be mirrored piecemeal — that is exactly how two scales end up on one leaderboard.
    moved = [(n, o, v) for n, o, v, _ in changes if o is not None and v is not None and abs(o - v) >= 3]
    valued = sum(1 for m in models if (m.get("benchmarks") or {}).get(KEY) is not None)
    mass_shift = valued >= 10 and len(moved) >= 0.25 * valued
    rescaled = (version is not None and version != pinned) or (version is None and mass_shift) or not pinned
    added = [c for c in changes if c[1] is None and c[2] is not None]
    dropped = [c for c in changes if c[1] is not None and c[2] is None]
    rescored = [c for c in changes if c[1] is not None and c[2] is not None and c[1] != c[2]]
    summary = ("%s aa-sync %s: AA %s (pinned %s) · %d AA models scored, %d displayed rows cross-checked · "
               "Botany matched %d · %d re-scored, %d added, %d dropped%s"
               % (stamp, mode[2:], version or "version?", pinned or "none", stats["scored"], stats["checked"],
                  len(hits), len(rescored), len(added), len(dropped),
                  " · %d name conflicts" % len(conflicts) if conflicts else ""))
    if verbose:
        for n, o, v, s in sorted(changes, key=lambda c: -(c[2] if c[2] is not None else -1)):
            print("   %-38s %6s -> %-5s%s" % (n[:38], o, v, ("  (drops %s)" % s) if s else ""))
        for c in conflicts:
            print("   CONFLICT: %r and %r both map to AA %r (first kept)" % (c[1], c[0], c[2]))
        top = sorted(groups.values(), key=lambda g: -g["raw"])[:25]
        matched_bases = {id(g) for g in hits.values()}
        miss = ["%s (%d)" % (g["base"], g["value"]) for g in top if id(g) not in matched_bases]
        if miss:
            print("   AA top-25 with no Botany model: " + ", ".join(miss))
    if rescaled and mode != "--rebase":
        print(summary)
        print("%s aa-sync: RESCALE — Artificial Analysis is on %s, Botany is pinned to %s%s. Nothing written. "
              "Fix: python3 scripts/aa_sync.py --rebase"
              % (stamp, version or "an unannounced scale", pinned or "nothing",
                 "" if version else " (%d of %d values would move 3+ points)" % (len(moved), valued)))
        return 2
    if mode == "--rebase" and not version:
        print(summary)
        print("%s aa-sync: can't read AA's index version off the page — refusing to stamp a scale." % stamp)
        return 1
    print(summary)
    if dry or not changes and (mode != "--rebase" or pinned == version):
        return 0
    apply(models, changes)
    save("models.json", doc)
    if mode == "--rebase":
        meta["aaScale"] = version
        meta["aaRebasedAt"] = datetime.now().strftime("%Y-%m-%d")
        save("meta.json", meta)
        print("%s aa-sync: column rebased onto %s and pinned in meta.json" % (stamp, version))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
