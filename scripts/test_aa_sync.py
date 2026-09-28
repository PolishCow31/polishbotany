"""Failure-path fixtures for scripts/aa_sync.py: python3 scripts/test_aa_sync.py (exit 0 = all pass).
Fetches AA's live page ONCE, then runs every case against TEMP copies of data/, never the real files.
Run it after any edit to aa_sync.py; it needs data/ to be in sync first (python3 scripts/aa_sync.py)."""
import hashlib, io, json, os, shutil, sys, tempfile
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import aa_sync as A

REAL = os.path.join(os.path.dirname(HERE), "data")
PAGE = A.fetch()
VER = A.parse(PAGE)[1]           # the version AA's page names today; a hardcoded "v4.3" broke every case at each re-version
if not VER:
    sys.exit("AA's page names no index version today — the re-version cases below can't be built")
BANNER = "Intelligence Index " + VER
_maj, _min = VER[1:].split(".")
NEXT_BANNER = "Intelligence Index v%s.%d" % (_maj, int(_min) + 1)
md5 = lambda p: hashlib.md5(open(p, "rb").read()).hexdigest()
results = []
ONLY = sys.argv[1:]                    # python3 scripts/test_aa_sync.py [case name ...]: run just those cases

def case(name, page, argv, want_exit, want_written, mutate=None):
    if ONLY and name not in ONLY:
        return ""
    tmp = tempfile.mkdtemp(prefix="aa-sync-test-")
    for f in ("models.json", "meta.json"):
        shutil.copy(os.path.join(REAL, f), tmp)
    if mutate:
        mutate(tmp)
    before = {f: md5(os.path.join(tmp, f)) for f in ("models.json", "meta.json")}
    A.DATA = tmp
    A.fetch = (lambda url=A.URL: page) if not isinstance(page, Exception) else (lambda url=A.URL: (_ for _ in ()).throw(page))
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = A.main(argv)
    written = any(md5(os.path.join(tmp, f)) != before[f] for f in before)
    ok = code == want_exit and written == want_written
    results.append(ok)
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: exit {code} (want {want_exit}), wrote={written} (want {want_written})")
    if not ok:
        print("     " + buf.getvalue().strip().replace("\n", "\n     ")[:900])
    shutil.rmtree(tmp)
    return buf.getvalue()

def set_models(tmp, fn):
    p = os.path.join(tmp, "models.json"); d = json.load(open(p)); fn(d["models"])
    json.dump(d, open(p, "w"), indent=2, ensure_ascii=False)

def set_meta(tmp, **kw):
    p = os.path.join(tmp, "meta.json"); d = json.load(open(p)); d.update(kw)
    for k, v in kw.items():
        if v is None: d.pop(k, None)
    json.dump(d, open(p, "w"), indent=2, ensure_ascii=False)

# 1. in sync -> no-op
case("in-sync --sync is a no-op", PAGE, ["--sync"], 0, False)
# 2. AA re-versions (page names the next version) -> refuse, write nothing, exit 2
case("re-version refuses --sync", PAGE.replace(BANNER, NEXT_BANNER), ["--sync"], 2, False)
# 3. same, in check mode -> exit 2 (the alarm signal update.sh keys on)
case("re-version flagged by --check", PAGE.replace(BANNER, NEXT_BANNER), [], 2, False)
# 4. truncated / garbage page -> exit 1, nothing written
case("truncated page -> no write", PAGE[:400000], ["--sync"], 1, False)
# 5. network failure -> exit 1, nothing written
case("fetch error -> no write", OSError("simulated network down"), ["--sync"], 1, False)
# 6. a new model the LLM added with an off-scale AA number -> sync overwrites it with AA's value
def llm_wrote_wrong(tmp):
    set_models(tmp, lambda ms: next(m for m in ms if m["name"] == "Claude Opus 5.5")["benchmarks"].__setitem__("AA-Index", 71))
out = case("off-scale LLM value corrected by --sync", PAGE, ["--sync"], 0, True, mutate=llm_wrote_wrong)
# 7. a model AA doesn't list, given an AA value -> dropped by --sync
def phantom(tmp):
    set_models(tmp, lambda ms: ms.append({"name": "Totally Unlisted Model 9", "lab": "X", "status": "live", "benchmarks": {"AA-Index": 60}}))
case("unlisted model's AA value dropped", PAGE, ["--sync"], 0, True, mutate=phantom)
# 8. a second AA-like key (would win benchOf's max) -> removed
def stray(tmp):
    set_models(tmp, lambda ms: next(m for m in ms if m["name"] == "Claude Fable 5.1")["benchmarks"].__setitem__("AA Index (v4.1)", 66))
case("stray AA-like key removed", PAGE, ["--sync"], 0, True, mutate=stray)
# 9. no pinned scale in meta -> sync refuses (must rebase first)
case("unpinned meta refuses --sync", PAGE, ["--sync"], 2, False, mutate=lambda t: set_meta(t, aaScale=None))
# 10. page drops its version banner AND values shift massively -> treated as a rescale
def shifted_page():
    return PAGE.replace(BANNER, "Intelligence Index")
def inflate(tmp):
    set_models(tmp, lambda ms: [m["benchmarks"].__setitem__("AA-Index", m["benchmarks"]["AA-Index"] + 12)
                                for m in ms if (m.get("benchmarks") or {}).get("AA-Index") is not None])
case("versionless page + mass shift -> refuse", shifted_page(), ["--sync"], 2, False, mutate=inflate)
# 11. versionless page, values unchanged -> normal sync (no false alarm)
case("versionless page, no shift -> no alarm", shifted_page(), ["--sync"], 0, False)

# 12. AA renames its models (every name prefixed with its lab: the Sep 28 skeptic's scenario) -> nothing matches, so
#     --sync would drop every AA value on the leaderboard. The drop guard refuses: exit 2, nothing written.
def lab_prefixed(real):
    def parse(html):
        models, version, stats = real(html)
        out = []
        for m in models:
            m = dict(m)
            for k in ("shortName", "name"):
                if m.get(k):
                    m[k] = "%s %s" % (m.get("modelCreatorName") or "Lab", m[k])
            out.append(m)
        return out, version, stats
    return parse
if not ONLY or "mass_drop_refused" in ONLY:
    real_parse = A.parse
    A.parse = lab_prefixed(real_parse)
    try:
        out = case("mass_drop_refused", PAGE, ["--sync"], 2, False)
    finally:
        A.parse = real_parse
    ok = "AA-SYNC REFUSED: would drop" in out
    results.append(ok)
    print(f"[{'PASS' if ok else 'FAIL'}] mass_drop_refused: logs 'AA-SYNC REFUSED: would drop N scores'")

# 13. save() is atomic: a serialization error mid-write leaves the previous file whole, no tmp behind
if not ONLY or "atomic_save" in ONLY:
    tmp = tempfile.mkdtemp(prefix="aa-sync-save-")
    p = os.path.join(tmp, "models.json")
    with open(p, "w") as f:
        f.write('{"ok": 1}\n')
    A.DATA = tmp
    try:
        A.save("models.json", {"a": 1, "b": object()})    # json.dump writes part of the file, then raises TypeError
        raised = False
    except TypeError:
        raised = True
    ok = raised and open(p).read() == '{"ok": 1}\n' and not [f for f in os.listdir(tmp) if f.endswith(".tmp")]
    results.append(ok)
    print(f"[{'PASS' if ok else 'FAIL'}] atomic_save: a failed save leaves models.json intact (got {open(p).read()[:40]!r})")
    shutil.rmtree(tmp)

# 14. a refusal must carry a fix that works: the mass-drop line names the models (up to 20) and the exact
#     `--sync --allow-drops` command; the re-version line gives the --rebase --dry-run path (a plain --rebase would
#     itself refuse on drops). (Round-2 skeptic: the alarm used to say "--rebase", which refused too.)
if not ONLY or "refusal_fix_commands" in ONLY:
    real_parse = A.parse
    A.parse = lab_prefixed(real_parse)
    try:
        out = case("refusal_fix_commands", PAGE, ["--sync"], 2, False)
    finally:
        A.parse = real_parse
    first = next(m for m in json.load(open(os.path.join(REAL, "models.json")))["models"]
                 if (m.get("benchmarks") or {}).get("AA-Index") is not None)["name"]
    listed = out.split("Would drop: ", 1)[1].split(". ", 1)[0] if "Would drop: " in out else ""
    ok = ("If AA really renamed/delisted these: python3 scripts/aa_sync.py --sync --allow-drops" in out
          and first in listed and len(listed.split(" (+")[0].split(", ")) == 20)
    out2 = case("refusal_fix_commands", PAGE.replace(BANNER, NEXT_BANNER), ["--sync"], 2, False)
    ok = ok and "python3 scripts/aa_sync.py --rebase --dry-run, review, then --rebase (add --allow-drops if it refuses on drops)" in out2
    results.append(ok)
    print(f"[{'PASS' if ok else 'FAIL'}] refusal_fix_commands: names the drops (20 shown) and prints the exact commands")

print("ALL PASS" if results and all(results) else "SOME FAILED")
sys.exit(0 if results and all(results) else 1)
