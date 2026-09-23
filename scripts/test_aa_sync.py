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
md5 = lambda p: hashlib.md5(open(p, "rb").read()).hexdigest()
results = []

def case(name, page, argv, want_exit, want_written, mutate=None):
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
# 2. AA re-versions (page says v4.4) -> refuse, write nothing, exit 2
case("re-version refuses --sync", PAGE.replace("Intelligence Index v4.3", "Intelligence Index v4.4"), ["--sync"], 2, False)
# 3. same, in check mode -> exit 2 (the alarm signal update.sh keys on)
case("re-version flagged by --check", PAGE.replace("Intelligence Index v4.3", "Intelligence Index v4.4"), [], 2, False)
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
    return PAGE.replace("Intelligence Index v4.3", "Intelligence Index")
def inflate(tmp):
    set_models(tmp, lambda ms: [m["benchmarks"].__setitem__("AA-Index", m["benchmarks"]["AA-Index"] + 12)
                                for m in ms if (m.get("benchmarks") or {}).get("AA-Index") is not None])
case("versionless page + mass shift -> refuse", shifted_page(), ["--sync"], 2, False, mutate=inflate)
# 11. versionless page, values unchanged -> normal sync (no false alarm)
case("versionless page, no shift -> no alarm", shifted_page(), ["--sync"], 0, False)

print("ALL PASS" if all(results) else "SOME FAILED")
sys.exit(0 if all(results) else 1)
