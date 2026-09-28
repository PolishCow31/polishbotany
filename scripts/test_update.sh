#!/usr/bin/env bash
# Sandbox tests for scripts/update.sh: a throwaway git repo + bare remote in a fresh mktemp dir, with claude, osascript,
# aa_sync (no AA traffic) and market_sync (no market traffic) stubbed. Never touches the real repo, never deletes.
# Usage: bash scripts/test_update.sh all          every scenario, each in its own sandbox (exit 0 = all pass)
#        bash scripts/test_update.sh <scenario>   one scenario, verbose
#        SRC=<dir holding scripts/ + .gitignore> bash scripts/test_update.sh all     test a staged copy instead
# Run it after any edit to update.sh (or to merge.py's exit codes).
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
SRC=${SRC:-$(dirname "$HERE")}
SCENARIOS="happy fastdeath watchdog mergefail corrupt_left mergefail_streak rebase_window commitfail partial_merge
           nochange_reset marketfail rotate archiveonly fenced allrej garbage section_freeze aa_hang aa_fail_streak
           stale_alarm"
SC=${1:?usage: test_update.sh all|<scenario>}
if [ "$SC" = all ]; then
  fails=0
  for s in $SCENARIOS; do
    if SRC="$SRC" bash "$0" "$s" > /dev/null 2>&1; then echo "PASS $s"; else echo "FAIL $s   (rerun: bash $0 $s)"; fails=$((fails+1)); fi
  done
  echo "$fails failed"; [ $fails -eq 0 ]; exit $?
fi
case " $(echo $SCENARIOS) " in *" $SC "*) ;; *) echo "unknown scenario: $SC (have: $(echo $SCENARIOS))"; exit 2 ;; esac

SBX=$(mktemp -d "${TMPDIR:-/tmp}/botany-sbx.XXXXXX") || exit 1      # fresh every run: nothing to clean, nothing deleted
mkdir -p "$SBX/bin" "$SBX/AI/scripts" "$SBX/AI/data"
cd "$SBX" && git init -q --bare remote.git || exit 1
cd "$SBX/AI" || exit 1
git init -q && git config user.email t@t && git config user.name t && git remote add origin "$SBX/remote.git"
cp "$SRC/scripts/"{merge.py,market_sync.py,research-prompt.md,aa_sync.py} scripts/ || exit 1
cp "$SRC/.gitignore" .gitignore || exit 1
/usr/bin/python3 - "$SRC/scripts" "$SBX/AI/data" <<'PY' || exit 1
import os, shutil, sys
sys.path.insert(0, sys.argv[1])
import test_merge as TM                 # fixture() only: the cases run under __main__
d = TM.fixture()
for f in os.listdir(d):
    shutil.copy(os.path.join(d, f), sys.argv[2])
PY
# settle the fixture once (the every-merge maintenance), so "no data changes" is reachable
echo '{}' > data/_delta.json && SWEEP_STARTED=2026-09-28T12:00:00-04:00 /usr/bin/python3 scripts/merge.py > /dev/null
[ -f data/_delta.json ] && mv data/_delta.json "$SBX/settle_delta.json"
case "$SC" in                       # the stubbed `aa_sync.py --sync`: ok, hung (killed by its watchdog) or failing
  aa_hang)        printf 'import time\ntime.sleep(5)\nprint("aa-sync STUB woke up")\n' > scripts/aa_sync_stub.py ;;
  aa_fail_streak) printf 'import sys\nprint("aa-sync STUB failing")\nsys.exit(1)\n' > scripts/aa_sync_stub.py ;;
  *)              printf 'print("aa-sync STUB ok")\n' > scripts/aa_sync_stub.py ;;
esac
if [ "$SC" = marketfail ]; then printf 'import sys\nprint("market-sync STUB failing")\nsys.exit(3)\n' > scripts/market_sync.py
else printf 'print("market-sync STUB ok")\n' > scripts/market_sync.py; fi
GOOD_DELTA='{"news":[{"title":"t","source":"CNBC","url":"https://www.cnbc.com/2026/09/28/sbx.html","date":"2026-09-28","topic":"Models","blurb":"b"}],"editorial":{"pulse":"sandbox pulse"}}'
# merge.py stubs: a crash after a partial write (exit 1), or a merge that skipped a section (exit 3)
merge_stub() {   # $1 = exit code
  printf 'import json, sys\np="data/news.json"; d=json.load(open(p)); d["note"]="half-written by a crashing merge"\nopen(p,"w").write(json.dumps(d, indent=2)+"\\n")\nprint("merge STUB exiting %s")\nsys.exit(%s)\n' "$1" "$1" > scripts/merge.py
}
GOOD_CLAUDE=$(printf '#!/bin/bash\ncat > data/_delta.json <<J\n%s\nJ\necho "stub wrote delta"\n' "$GOOD_DELTA")
ALLREJ_DELTA='{"news":[{"title":"t","source":"Reuters","url":"https://reuters.com/x","date":"2026-09-28","topic":"Models","blurb":"b"}],"markets":[{"question":"q","platform":"Polymarket","forecast":"50%%","category":"release","relevantBenchmark":"other","resolveDate":"2026-12-31","url":"https://news.example.com/x"}]}'
FREEZE_DELTA='{"editorial":{"pulse":"pulse that lands"},"news":[{"title":"t","source":"Reuters","url":"https://reuters.com/y","date":"2026-09-28","topic":"Models","blurb":"b"}]}'
case "$SC" in
  happy|marketfail|rotate|archiveonly|commitfail|aa_hang|aa_fail_streak) echo "$GOOD_CLAUDE" > "$SBX/bin/claude" ;;
  fenced)          # a valid delta wrapped in a markdown fence: usable, merges, resets the streak
    printf '#!/bin/bash\nprintf "%%s\\n%%s\\n%%s\\n" "\\`\\`\\`json" %q "\\`\\`\\`" > data/_delta.json\n' "$GOOD_DELTA" > "$SBX/bin/claude" ;;
  allrej)          # every item rejected by the merge: exit 4, each sweep counts toward the dead streak
    printf '#!/bin/bash\ncat > data/_delta.json <<J\n%s\nJ\n' "$ALLREJ_DELTA" > "$SBX/bin/claude" ;;
  garbage)         # not JSON at all: exit 4, counts toward the dead streak
    printf '#!/bin/bash\necho "I could not finish the research this time." > data/_delta.json\n' > "$SBX/bin/claude" ;;
  section_freeze)  # the pulse lands every sweep, news is always rejected: its own alarm after 8 sweeps
    printf '#!/bin/bash\ncat > data/_delta.json <<J\n%s\nJ\n' "$FREEZE_DELTA" > "$SBX/bin/claude" ;;
  stale_alarm)     # 8 freeze sweeps (the alarm fires once), then an unusable delta: that merge returns early
    printf '#!/bin/bash\nn=$(cat %s/n 2>/dev/null || echo 0); n=$((n+1)); echo $n > %s/n\nif [ $n -le 8 ]; then cat > data/_delta.json <<J\n%s\nJ\nelse echo "not json" > data/_delta.json; fi\n' "$SBX" "$SBX" "$FREEZE_DELTA" > "$SBX/bin/claude" ;;
  partial_merge)   echo "$GOOD_CLAUDE" > "$SBX/bin/claude"; merge_stub 3 ;;
  mergefail|mergefail_streak) echo "$GOOD_CLAUDE" > "$SBX/bin/claude"; merge_stub 1 ;;
  rebase_window)   # a hand-run `aa_sync.py --rebase` edits meta.json while claude runs; then the merge crashes
    printf '#!/bin/bash\nsed -i "" "s/\\"aaScale\\": \\"v4.3\\"/\\"aaScale\\": \\"v9.9\\"/" data/meta.json\necho "{}" > data/_delta.json\n' > "$SBX/bin/claude"
    merge_stub 1 ;;
  corrupt_left)    # data/ already dirty (corrupted) when the merge runs: never restored, never published, counted
    printf '#!/bin/bash\necho "{}" > data/_delta.json\necho corrupt > data/models.json\n' > "$SBX/bin/claude" ;;
  nochange_reset)  # an accepted item that changes nothing (the same pulse): a clean merge, nothing to publish
    printf '#!/bin/bash\necho '"'"'{"editorial":{"pulse":"old pulse"}}'"'"' > data/_delta.json\n' > "$SBX/bin/claude" ;;
  fastdeath)   printf '#!/bin/bash\necho "Failed to authenticate: OAuth session expired"\nexit 3\n' > "$SBX/bin/claude" ;;
  watchdog)    printf '#!/bin/bash\nsleep 5\n' > "$SBX/bin/claude" ;;
esac
chmod +x "$SBX/bin/claude"
printf '#!/bin/bash\necho "osascript $*" >> %s/osascript.calls\n' "$SBX" > "$SBX/bin/osascript"; chmod +x "$SBX/bin/osascript"
sed -e "s#cd /Users/christian/Sites/AI#cd $SBX/AI#" -e "s#^CLAUDE=.*#CLAUDE=$SBX/bin/claude#" \
    -e "s#python3 scripts/aa_sync.py --sync#python3 scripts/aa_sync_stub.py --sync#" "$SRC/scripts/update.sh" > scripts/update.sh
# The sandbox is only as safe as this rewrite: if update.sh's cd/CLAUDE lines ever change shape, the sed misses and the
# "sandboxed" copy would commit and push in the REAL repo. Refuse to run unless every rewrite provably landed.
grep -q "cd $SBX/AI" scripts/update.sh             || { echo "harness: cd not rewritten; refusing to run"; exit 1; }
grep -q "^CLAUDE=$SBX/bin/claude" scripts/update.sh || { echo "harness: CLAUDE not rewritten; refusing to run"; exit 1; }
grep -q "aa_sync_stub.py --sync" scripts/update.sh  || { echo "harness: aa_sync call not stubbed; refusing to run"; exit 1; }
grep -q "/Users/christian/Sites/AI" scripts/update.sh && { echo "harness: the real repo path survived the rewrite; refusing to run"; exit 1; }
[ "$SC" = watchdog ] && sed -i '' "s/alarm shift @ARGV; exec @ARGV' 1500/alarm shift @ARGV; exec @ARGV' 1/" scripts/update.sh
[ "$SC" = aa_hang ] && sed -i '' "s/exec @ARGV' 180 python3 scripts\/aa_sync_stub.py/exec @ARGV' 1 python3 scripts\/aa_sync_stub.py/" scripts/update.sh
chmod +x scripts/update.sh
git add -A && git commit -q -m init && git push -q -u origin HEAD 2>/dev/null
[ "$SC" = rotate ] && head -c 2200000 /dev/zero | tr '\0' 'x' > scripts/update.log
if [ "$SC" = archiveonly ]; then
  mkdir -p data/sources-archive && echo '{"month":"2026-01","sweeps":[]}' > data/sources-archive/2026-01.json; fi
[ "$SC" = nochange_reset ] && echo 3 > scripts/.dead_streak
[ "$SC" = commitfail ] && printf '#!/bin/sh\necho "pre-commit hook: refusing"\nexit 1\n' > .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit
RUNS=1; case "$SC" in mergefail_streak|allrej) RUNS=4 ;; section_freeze|aa_fail_streak) RUNS=8 ;; stale_alarm) RUNS=9 ;; esac
for i in $(seq 1 $RUNS); do
  PATH="$SBX/bin:/usr/bin:/bin:/usr/sbin:/sbin" /bin/bash scripts/update.sh 2>/dev/null; RC=$?
done
echo "--- sandbox: $SBX"
echo "--- update.sh exit (last run): $RC"; tail -14 scripts/update.log | cut -c1-200
echo "--- git log: $(git log --oneline | wc -l | tr -d ' ') commits; remote: $(git --git-dir="$SBX/remote.git" log --oneline 2>/dev/null | wc -l | tr -d ' '); streak: $(cat scripts/.dead_streak 2>/dev/null)"
ok=1; fail(){ echo "ASSERT FAILED: $*"; ok=0; }
case "$SC" in
  happy)
    [ $RC -eq 0 ] || fail "exit $RC"
    grep -q "merged: " scripts/update.log || fail "no merged line"
    grep -q "market-sync STUB ok" scripts/update.log || fail "market_sync not run"
    grep -q "pushed" scripts/update.log || fail "not pushed"
    /usr/bin/python3 -c "import json,re,sys; p=json.load(open('data/editorial.json'))['pulse']; sys.exit(0 if re.search(r'[+-]\d\d:\d\d$',p['updated']) and p['text']=='sandbox pulse' else 1)" || fail "pulse stamp not from SWEEP_STARTED (-HH:MM)"
    [ -f data/_delta.json ] && fail "delta not removed"
    [ "$(cat scripts/.dead_streak)" = 0 ] || fail "dead streak not reset after a clean merge + push" ;;
  fastdeath)
    [ $RC -eq 0 ] || fail "exit $RC"
    grep -Eq "claude -p exited 3 after [0-9]+s" scripts/update.log || fail "no timed exit line"
    grep -q "AUTH EXPIRED" scripts/update.log || fail "auth detector broke"
    grep -q "no delta written" scripts/update.log || fail "no-delta line missing"
    [ "$(cat scripts/.dead_streak)" = 1 ] || fail "dead streak not incremented" ;;
  watchdog)
    grep -Eq "claude -p KILLED by 25-min watchdog \([0-9]+s\)" scripts/update.log || fail "no watchdog line" ;;
  mergefail)          # merge.py crashed after half-writing news.json; data/ was clean right before the merge -> restored
    [ $RC -eq 1 ] || fail "exit $RC (want 1)"
    grep -q "merge failed" scripts/update.log || fail "no merge failed line"
    grep -q "data/ restored to HEAD" scripts/update.log || fail "not restored"
    [ -z "$(git status --porcelain data/)" ] || fail "data/ still dirty: $(git status --porcelain data/)"
    [ "$(cat scripts/.dead_streak)" = 1 ] || fail "streak $(cat scripts/.dead_streak), want 1" ;;
  corrupt_left)
    [ $RC -eq 1 ] || fail "exit $RC (want 1)"
    grep -q "JSONDecodeError" scripts/update.log || fail "merge didn't fail on the corrupt models.json"
    grep -q "was not clean before the merge — left as is" scripts/update.log || fail "no left-as-is line"
    [ "$(git log --oneline | wc -l | tr -d ' ')" = 1 ] || fail "something was committed"
    [ "$(cat scripts/.dead_streak)" = 1 ] || fail "streak $(cat scripts/.dead_streak), want 1" ;;
  mergefail_streak)   # a merge that fails every sweep must reach the alarm (old: streak reset because a delta existed)
    [ "$(cat scripts/.dead_streak)" = 4 ] || fail "streak is $(cat scripts/.dead_streak), want 4 after 4 failed merges"
    grep -q "DEAD STREAK: 4 consecutive sweeps" scripts/update.log || fail "no DEAD STREAK line"
    grep -q "Botany updater: DEAD STREAK" "$SBX/osascript.calls" 2>/dev/null || fail "no DEAD STREAK notification" ;;
  rebase_window)      # the restore must not wipe hand edits made during the claude window
    [ $RC -eq 1 ] || fail "exit $RC (want 1)"
    grep -q '"aaScale": "v9.9"' data/meta.json || fail "the manual meta.json edit was wiped by the restore"
    grep -q "was not clean before the merge — left as is" scripts/update.log || fail "no left-as-is line" ;;
  commitfail)         # a failed commit is not reported as pushed, and counts toward the streak
    grep -q "commit failed" scripts/update.log || fail "no 'commit failed' line"
    grep -q "pushed" scripts/update.log && fail "logged 'pushed' although the commit failed"
    [ "$(cat scripts/.dead_streak)" = 1 ] || fail "streak $(cat scripts/.dead_streak), want 1" ;;
  partial_merge)      # merge exit 3: publish what landed, but count the sweep toward the streak
    [ $RC -eq 0 ] || fail "exit $RC"
    grep -q "merge applied with a skipped section" scripts/update.log || fail "no partial line"
    grep -q "pushed" scripts/update.log || fail "partial merge not published"
    [ "$(cat scripts/.dead_streak)" = 1 ] || fail "streak $(cat scripts/.dead_streak), want 1" ;;
  nochange_reset)     # a clean merge with genuinely nothing to publish resets the streak
    grep -q "no data changes" scripts/update.log || fail "expected no data changes"
    [ "$(cat scripts/.dead_streak)" = 0 ] || fail "streak $(cat scripts/.dead_streak), want 0" ;;
  marketfail)
    [ $RC -eq 0 ] || fail "exit $RC"
    grep -q "market-sync exited non-zero — ignored" scripts/update.log || fail "market failure not tolerated"
    grep -q "pushed" scripts/update.log || fail "sweep did not continue to publish" ;;
  rotate)
    [ -f scripts/update.log.1 ] && [ "$(wc -c < scripts/update.log.1)" -gt 2097152 ] || fail "not rotated"
    [ "$(wc -c < scripts/update.log)" -lt 100000 ] || fail "new log not small" ;;
  archiveonly)
    [ -z "$(git status --porcelain data/)" ] || fail "untracked archive not committed: $(git status --porcelain data/)" ;;
  fenced)             # a fenced delta is usable: it merges, publishes, and the sweep counts as a success
    grep -q "sbx.html" data/news.json || fail "the fenced delta's news item didn't land"
    grep -q "pushed" scripts/update.log || fail "not pushed"
    [ "$(cat scripts/.dead_streak)" = 0 ] || fail "streak $(cat scripts/.dead_streak), want 0" ;;
  allrej)             # every item rejected 4 sweeps running = the DEAD STREAK alarm (it used to reset: exit 0)
    grep -q "merge: nothing accepted" scripts/update.log || fail "no 'nothing accepted' line"
    [ "$(cat scripts/.dead_streak)" = 4 ] || fail "streak $(cat scripts/.dead_streak), want 4"
    grep -q "Botany updater: DEAD STREAK" "$SBX/osascript.calls" 2>/dev/null || fail "no DEAD STREAK notification" ;;
  garbage)            # an unusable delta: exit-4 path, the streak goes up, the sweep still finishes
    [ $RC -eq 0 ] || fail "exit $RC"
    grep -q "merge: unusable delta" scripts/update.log || fail "no 'unusable delta' line"
    grep -q "merge landed nothing from the delta" scripts/update.log || fail "update.sh didn't take the exit-4 path"
    [ "$(cat scripts/.dead_streak)" = 1 ] || fail "streak $(cat scripts/.dead_streak), want 1" ;;
  section_freeze)     # news offered and rejected 8 sweeps running while the pulse lands: its own notification
    grep -q "SECTION FREEZE: news rejected 8 sweeps running" scripts/update.log || fail "no SECTION FREEZE line"
    grep -q "Botany updater: news rejected 8 sweeps running" "$SBX/osascript.calls" 2>/dev/null || fail "no section notification"
    [ "$(cat scripts/.dead_streak)" = 0 ] || fail "streak $(cat scripts/.dead_streak), want 0 (the pulse landed)" ;;
  stale_alarm)        # the 9th sweep's merge returned early (unusable delta): the 8th sweep's alarm must not re-fire
    grep -q "merge: unusable delta" scripts/update.log || fail "the 9th sweep didn't hit the unusable-delta path"
    [ "$(grep -c "Botany updater: news rejected 8 sweeps running" "$SBX/osascript.calls" 2>/dev/null)" = 1 ] \
      || fail "news freeze notified $(grep -c "news rejected" "$SBX/osascript.calls" 2>/dev/null) times, want 1"
    [ "$(grep -c "SECTION FREEZE: news rejected 8 sweeps running" scripts/update.log)" = 1 ] \
      || fail "update.sh logged the news freeze more than once" ;;
  aa_hang)            # a hung aa_sync is killed by its watchdog; the sweep still publishes
    grep -q "exec @ARGV' 1 python3 scripts/aa_sync_stub.py" scripts/update.sh || fail "harness: aa watchdog not shortened"
    grep -q "aa-sync KILLED by 180s watchdog" scripts/update.log || fail "aa_sync not killed/logged"
    grep -q "aa-sync STUB woke up" scripts/update.log && fail "aa_sync ran to completion (no watchdog)"
    grep -q "pushed" scripts/update.log || fail "the sweep didn't publish after the aa kill" ;;
  aa_fail_streak)     # aa_sync failing (exit 1) 8 sweeps running raises its own alarm
    [ "$(cat scripts/.aa_fail_streak 2>/dev/null)" = 8 ] || fail "aa fail streak $(cat scripts/.aa_fail_streak 2>/dev/null), want 8"
    grep -q "Botany: AA sync failing for a day (page layout changed?)" "$SBX/osascript.calls" 2>/dev/null || fail "no AA failing notification" ;;
esac
[ $ok -eq 1 ] && echo "SCENARIO $SC: PASS" && exit 0; echo "SCENARIO $SC: FAIL"; exit 1
