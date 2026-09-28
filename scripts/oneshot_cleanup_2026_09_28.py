#!/usr/bin/env python3
"""One-time cleanup of Botany's data after the Sep 28 2026 pipeline audit. Run it ONCE, between cron runs, right
after the reworked merge.py / market_sync.py are swapped in:

    python3 scripts/oneshot_cleanup_2026_09_28.py data             # live market check against the platform APIs, then write
    python3 scripts/oneshot_cleanup_2026_09_28.py data --dry-run   # print the before/after summary, write nothing
    python3 scripts/oneshot_cleanup_2026_09_28.py data --offline   # markets: rules only, no network

Idempotent: a second run changes nothing (apart from live odds that moved in between). The rules come from merge.py
and market_sync.py, so nothing is re-implemented here; this file only holds the one-off decisions: the audit's
url-specific market drops, the glossary duplicate clusters (and the pairs that only look like duplicates), and the
Nemotron notable fix. briefs.json is deliberately not touched (pending an owner decision).
"""
import json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import merge as M          # noqa: E402
import market_sync as MS   # noqa: E402

# Audit rows dropped by URL (never by index: indices shift as the pipeline runs).
AUDIT_DROPS = {
    "https://polymarket.com/event/ai-model-scores-90-on-frontiermath-before-2027": "no such Polymarket event (audit 38)",
    "https://www.metaculus.com/questions/": "the Metaculus question index, not a question (audit 12)",
    "https://www.datalearner.com/en/leaderboards/external/aa-quality-index": "404, and not a forecast (audit 15)",
    "https://www.metaculus.com/questions/21920/what-will-be-the-best-score-on-the-gpqa-benchmark-before-2025/":
        "a before-2025 question, resolved long ago (audit 29)",
    "https://artificialanalysis.ai/evaluations/artificial-analysis-intelligence-index":
        "v4.1-era AA-Index numbers, not a forecast (audit 30)",
}
NOTABLE_FIXES = [("NVIDIA Nemotron 3 Ultra", " (AA 48)")]   # stale v4.1-scale number inside the notable text
# Pairs the duplicate rules below would join but that are different things (reviewed Sep 28 2026).
DO_NOT_MERGE = [{"DeepSeek", "DeepSeek (model family)"},             # the lab vs its models
                {"FLOPs", "FLOPS (rate)"},                          # an operation count vs a per-second rate
                {"Interpretability", "Mechanistic interpretability"},    # the field vs one approach within it
                {"Circular financing", "Vendor financing"}]         # a round-trip pattern vs one kind of seller credit


def load(path):
    with open(path) as f:
        return f.read()


# ---------------------------------------------------------------- glossary clusters
def glossary_clusters(terms):
    """Duplicate clusters under four rules (keys via merge.gkey):
      same term key ("Grouped-Query Attention" / "Grouped Query Attention"); same term once a trailing "(...)"
      qualifier is dropped ("MXFP4 (Microscaling FP4)" / "MXFP4"); each lists the other as an aka; same acronym and
      one lists the other as an aka. Joined transitively, minus DO_NOT_MERGE. -> [[index, ...], ...]"""
    gk = M.gkey
    tk = [gk(t.get("term")) for t in terms]
    base = [(gk(re.sub(r"\s*\([^()]*\)\s*$", "", t.get("term") or "")), bool(re.search(r"\)\s*$", t.get("term") or "")))
            for t in terms]
    ak = [gk(t.get("acronym")) for t in terms]
    akas = [{gk(a) for a in (t.get("aka") if isinstance(t.get("aka"), list) else []) if gk(a)} for t in terms]
    never = [{gk(x) for x in pair} for pair in DO_NOT_MERGE]
    parent = list(range(len(terms)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for i in range(len(terms)):
        for j in range(i + 1, len(terms)):
            if {tk[i], tk[j]} in never:
                continue
            if (tk[i] and tk[i] == tk[j]) \
                    or (base[i][0] and base[i][0] == base[j][0] and (base[i][1] or base[j][1])) \
                    or (tk[i] in akas[j] and tk[j] in akas[i]) \
                    or (ak[i] and ak[i] == ak[j] and (tk[i] in akas[j] or tk[j] in akas[i])):
                parent[find(i)] = find(j)
    groups = {}
    for i in range(len(terms)):
        groups.setdefault(find(i), []).append(i)
    return [sorted(g) for g in groups.values() if len(g) > 1]


def merge_cluster(terms, idx):
    """Keep the richest timeless def (a def naming a 20xx year loses to one that doesn't, then more words wins, then
    file order); union every other member's term, aka and acronym into the survivor's aka / acronym."""
    def rank(i):
        d = terms[i].get("def") or ""
        return (bool(re.search(r"\b20\d\d\b", d)), -len(d.split()), i)
    keep = min(idx, key=rank)
    s = dict(terms[keep])
    have = {M.gkey(s.get("term")), M.gkey(s.get("acronym"))} | {M.gkey(a) for a in (s.get("aka") or [])}
    aka = list(s.get("aka") or [])
    for i in idx:
        if i == keep:
            continue
        t = terms[i]
        if not s.get("acronym") and t.get("acronym"):
            s["acronym"] = t["acronym"]
            have.add(M.gkey(t["acronym"]))
        for v in [t.get("term"), t.get("acronym")] + list(t.get("aka") or []):
            if isinstance(v, str) and M.gkey(v) and M.gkey(v) not in have:
                aka.append(v.strip())
                have.add(M.gkey(v))
    s["aka"] = aka
    return keep, s


# ---------------------------------------------------------------- main
def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    if not args:
        print(__doc__)
        return 2
    data = os.path.abspath(args[0])
    dry, offline = "--dry-run" in argv, "--offline" in argv
    M.DATA = MS.DATA = data
    now_dt = M.sweep_clock()
    today_s = now_dt.strftime("%Y-%m-%d")
    names = ("models.json", "editorial.json", "forecasts.json", "glossary.json", "sources.json", "releases.json")
    orig = {n: load(os.path.join(data, n)) for n in names}
    doc = {n: json.loads(orig[n]) for n in names}
    report = []

    def say(msg):
        report.append(msg)

    # ---- models.json: canonical benchmark keys, stale AA number out of one notable
    models = doc["models.json"]["models"]
    renamed = clashed = 0
    for m in models:
        if isinstance(m.get("benchmarks"), dict):
            m["benchmarks"], r, c = M.apply_bench_alias(m["benchmarks"])
            renamed, clashed = renamed + len(r), clashed + len(c)
            for k in r:
                say("models: %s  %r -> %r" % (m["name"], k, M.BENCH_ALIAS[k]))
            for k in c:
                say("models: %s  dropped %r (its canonical key already has a value)" % (m["name"], k))
    for name, frag in NOTABLE_FIXES:
        m = next((x for x in models if x.get("name") == name), None)
        if m and isinstance(m.get("notable"), str) and frag in m["notable"]:
            m["notable"] = m["notable"].replace(frag, "")
            say("models: %s notable: removed %r" % (name, frag.strip()))
    bad_rel = [(m["name"], m.get("released")) for m in models if not M.RELEASED_RE.match(str(m.get("released") or ""))]

    # ---- editorial.json: prices normalized (+ priceNotes, derived from models[].pricing), retired keys out
    ed = doc["editorial.json"]
    p_before = dict(ed.get("prices") or {})
    pc = M.normalize_prices(ed, models)
    retired = [k for k in M.RETIRED_EDITORIAL if k in ed]
    for k in retired:
        del ed[k]
    changed_prices = sum(1 for k, v in p_before.items() if ed["prices"].get(k) != v)

    # ---- forecasts.json: methodology out; markets: audit drops -> D4 -> live platform check -> dedupe -> prune
    fc = doc["forecasts.json"]
    had_method = fc.pop("methodology", None) is not None
    rows = fc.get("markets") or []
    n0 = len(rows)
    drops = {M.norm_url(u): why for u, why in AUDIT_DROPS.items()}
    kept = []
    for m in rows:
        why = drops.get(M.norm_url(m.get("url"))) if isinstance(m, dict) else None
        if why:
            say("markets: dropped %s — %s" % (m.get("url"), why))
        else:
            kept.append(m)
    n_audit = n0 - len(kept)
    rows, bad, tagged = M.check_existing_markets(kept, today_s)
    for m, why in bad:
        say("markets: dropped %s — %s" % (m.get("url"), why))
    # dedupe BEFORE the platform check: syncing first gave every duplicate the same fresh asOf, so the tie fell to file
    # order and kept the stalest prose ("Last confirmed read Aug 30"). Legacy rows carry no asOf: longest forecast wins.
    rows, dupes = M.dedupe_markets(rows, prefer_longer=True)
    for m, k in dupes:
        say("markets: dropped %s — duplicate of %s" % (m.get("url"), k))
    sync_line, incomplete = "skipped (--offline)", None
    if not offline:
        synced, st, lines, ok = MS.sync(rows, today_s)
        sync_line = ("%d checked · %d dropped (closed/resolved/dead) · %d rendered from the API · %d unmapped · %d "
                     "failed · %d duplicate questions%s" % (st["checked"], st["dropped"], st["rendered"], st["unmapped"],
                                                             st["failed"], st["duplicates"],
                                                             "" if ok else " — MORE THAN HALF FAILED, platform results NOT applied"))
        for ln in lines:
            say("markets: " + ln)
        if ok:
            rows = synced
        if not ok or st["failed"] or st["late"] or st["limited"]:   # an undated row it couldn't reach would be pruned
            incomplete = "%d failed, %d not reached, %d rate-limited%s" % (             # as legacy below: write nothing
                st["failed"], st["late"], st["limited"], "" if ok else ", results not applied")
    rows, pruned = M.prune_markets(rows, today_s, undated=not offline)
    for m, why in pruned:
        say("markets: dropped %s — %s" % (m.get("url"), why))
    fc["markets"] = rows

    # ---- glossary.json: merge the duplicate clusters
    gl = doc["glossary.json"]
    terms = gl.get("terms") or []
    g0 = len(terms)
    clusters = glossary_clusters(terms)
    gone, replace = set(), {}
    for idx in clusters:
        keep, merged = merge_cluster(terms, idx)
        replace[keep] = merged
        gone.update(i for i in idx if i != keep)
        say("glossary: kept %r <- merged %s" % (merged["term"], ", ".join(repr(terms[i]["term"]) for i in idx if i != keep)))
    terms = [replace.get(i, t) for i, t in enumerate(terms) if i not in gone]
    terms.sort(key=lambda x: (x.get("term") or "").lower())
    gl["terms"] = terms

    # ---- sources.json: 30-day retention (older sweeps -> sources-archive/YYYY-MM.json)
    sj = doc["sources.json"]
    s0 = len(sj.get("sweeps") or [])
    sj["sweeps"], archive_files, archived = M.plan_source_archive(sj.get("sweeps") or [], now_dt.date(), data)
    if archived and isinstance(sj.get("note"), str) and "sources-archive" not in sj["note"]:
        sj["note"] = sj["note"].rstrip() + (" Sweeps older than %d days are moved to data/sources-archive/YYYY-MM.json "
                                            "by scripts/merge.py." % M.SOURCES_KEEP_DAYS)

    # ---- releases.json: the new radar rules, once (existing probs keep no probAsOf: nobody re-read them just now)
    rel = doc["releases.json"]
    items = rel.get("items") or []
    live = {M.name_key(m["name"]) for m in models if m.get("status") == "live"}
    old_by_key = {M.name_key(r.get("model")): r for r in items if isinstance(r, dict)}
    new_items, rdrop = M.validate_releases(items, live, now_dt, old_by_key, stamp_missing=False)
    for model, why in rdrop:
        say("releases: dropped %s — %s" % (model, why))
    for a, b in zip([r for r in items if isinstance(r, dict) and M.name_key(r.get("model")) in
                     {M.name_key(x["model"]) for x in new_items}], new_items):
        for k in ("expectedDate", "expectedWindow", "basis"):
            if a.get(k) != b.get(k):
                say("releases: %s  %s %r -> %r" % (b["model"], k, a.get(k), b.get(k)))
    rel["items"] = new_items

    # ---- write (only what changed; archives before the trimmed sources.json)
    writes = []
    for n in names:
        text = M.dumps(doc[n])
        if text != orig[n]:
            if n != "models.json":
                doc[n]["updated"] = now_dt.isoformat()
                text = M.dumps(doc[n])
            writes.append((os.path.join(data, n), text, orig[n]))
    archive_writes = [(p, t, o) for p, (t, o) in sorted(archive_files.items()) if t != o]

    print("oneshot cleanup %s on %s%s" % (today_s, data, " (dry run: nothing written)" if dry else ""))
    print("  markets    %d -> %d  (audit drops %d · invalid %d · platform check: %s · duplicates %d · pruned %d · "
          "expert-tagged %d)" % (n0, len(rows), n_audit, len(bad), sync_line, len(dupes), len(pruned), tagged))
    print("  forecasts  methodology %s" % ("deleted" if had_method else "already gone"))
    print("  models     %d benchmark keys renamed, %d alias duplicates dropped; released not YYYY-MM[-DD] (left as-is): %s"
          % (renamed, clashed, bad_rel or "none"))
    print("  editorial  prices %d -> %d (%d rewritten, %d moved to priceNotes, %d derived from models[].pricing, %d re-keyed); "
          "priceNotes %d; retired keys removed: %s"
          % (len(p_before), len(ed["prices"]), changed_prices, pc["noted"], pc["derived"], pc["rekeyed"],
             len(ed.get("priceNotes") or {}), ", ".join(retired) or "none"))
    if pc["unmatched"]:
        print("             price keys matching no catalog model: " + ", ".join(pc["unmatched"]))
    print("  glossary   %d -> %d terms (%d duplicate clusters merged)" % (g0, len(terms), len(clusters)))
    print("  sources    %d -> %d sweeps kept (%d archived to %s)"
          % (s0, len(sj["sweeps"]), archived, ", ".join(os.path.relpath(p, data) for p, _t, _o in archive_writes) or "nothing new"))
    print("  releases   %d -> %d items (%d dropped)" % (len(items), len(new_items), len(rdrop)))
    print("  files      " + (", ".join(os.path.relpath(p, data) for p, _t, _o in archive_writes + writes) or "no changes"))
    for line in report:
        print("   " + line)
    if incomplete:
        print("NOT WRITTEN: the platform check was incomplete (%s). Its undated rows would have been pruned as legacy "
              "rows; re-run when the platforms answer." % incomplete)
        return 1
    if not dry:
        M.commit(archive_writes + writes)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
