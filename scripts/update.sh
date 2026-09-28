#!/usr/bin/env bash
# Botany auto-update, every 3 hours (12AM/3AM/6AM/9AM/12PM/3PM/6PM/9PM ET). launchd target.
# AI proposes (claude -p -> data/_delta.json); merge.py applies; aa_sync.py + market_sync.py re-check AA scores and
# market odds against their sources' own data; git publishes.
set -uo pipefail
cd /Users/christian/Sites/AI || exit 1

CLAUDE=/Users/christian/.npm-global/bin/claude
MODEL=claude-opus-5-5   # pinned Sep 23 2026: with no --model this inherited the interactive Fable default and died on its weekly cap
LOG=scripts/update.log
ts() { date "+%Y-%m-%d %H:%M:%S"; }

# Log rotation: keep update.log under ~2 MB (one previous generation kept as update.log.1, gitignored).
if [ -f "$LOG" ] && [ "$(wc -c < "$LOG")" -gt 2097152 ]; then mv -f "$LOG" "$LOG.1"; fi

# The sweep's own clock: merge.py stamps the 3-hour slot + date from this, not from whenever the merge happens to
# run. BSD date prints -0400; the sed makes it -04:00 (python 3.9's fromisoformat needs the colon).
SWEEP_STARTED=$(date "+%Y-%m-%dT%H:%M:%S%z" | sed -E 's/([+-][0-9]{2})([0-9]{2})$/\1:\2/'); export SWEEP_STARTED

echo "=== $(ts) update start ===" >> "$LOG"

# DEAD-STREAK ALARM, layer 2 — alert on OUTCOME, not strings. During Aug 20-28 an expired token made claude -p HANG
# printing NOTHING (66 dead runs, zero notifications — nothing to grep). The streak counts consecutive sweeps that did
# not end in a successful publish (or a genuine "no data changes"): no delta, a merge failure or partial merge, a
# failed commit or push. It resets ONLY when a sweep merged cleanly and then published / had nothing to publish.
# (Sep 28 skeptic: it used to reset whenever a delta merely EXISTED, so a merge that failed every sweep froze
# publishing forever without an alarm.) Fires at 4 (~12h) and every 8th after (~daily while it lasts).
STREAKF=scripts/.dead_streak
bump_streak() {   # $1 = cause, as the log/notification should name it
  STREAK=$(( $(cat "$STREAKF" 2>/dev/null || echo 0) + 1 )); echo "$STREAK" > "$STREAKF"
  if [ "$STREAK" -eq 4 ] || { [ "$STREAK" -gt 4 ] && [ $(( (STREAK-4) % 8 )) -eq 0 ]; }; then
    case "$1" in
      usage*)             FIX="wait for the cap to reset, or point claude -p at a model with headroom" ;;
      merge*|commit*)     FIX="read the merge/commit errors in scripts/update.log (the delta's rejected items are listed there)" ;;
      push*)              FIX="check the network / GitHub credential (git push by hand to see the error)" ;;
      *)                  FIX="run claude, then /login" ;;
    esac
    echo "$(ts) DEAD STREAK: $STREAK consecutive sweeps without a successful update — cause: $1. Check scripts/update.log; likely fix: $FIX" >> "$LOG"
    osascript -e "display notification \"$STREAK sweeps without an update — $1. Fix: $FIX\" with title \"Botany updater: DEAD STREAK\" sound name \"Basso\"" 2>/dev/null || true
  fi
}
reset_streak() { echo 0 > "$STREAKF"; }

# 1. research pass -> proposes data/_delta.json (uses Max subscription, no API key)
#    --dangerously-skip-permissions is required: headless `claude -p` otherwise
#    queues tool calls pending an interactive approval that never comes, so the
#    delta is never written. Safe here — the AI only PROPOSES data/_delta.json;
#    merge.py is the deterministic authority that decides what actually lands.
#    WATCHDOG: a 25-min cap (perl alarm — macOS has no GNU `timeout`) so a hung/too-slow run can
#    NEVER block future launchd fires (launchd won't start a 2nd instance while one is running).
#    Non-zero exit (incl. the watchdog kill) does NOT abort — step 2 still merges whatever delta
#    was written before the cutoff, and logs if none was.
rm -f data/_delta.json
RUNOUT=$(mktemp -t ai-tracker-run)
T0=$(date +%s)
perl -e 'alarm shift @ARGV; exec @ARGV' 1500 \
  "$CLAUDE" -p --model "$MODEL" --dangerously-skip-permissions "$(cat scripts/research-prompt.md)" > "$RUNOUT" 2>&1
RC=$?
DUR=$(( $(date +%s) - T0 ))
# 142 = 128 + SIGALRM: the perl watchdog fired. Timing both cases tells a hang (1500s) from a fast death (~3s).
if [ "$RC" -eq 142 ]; then
  echo "$(ts) claude -p KILLED by 25-min watchdog (${DUR}s) — merging any delta it wrote" >> "$LOG"
elif [ "$RC" -ne 0 ]; then
  echo "$(ts) claude -p exited $RC after ${DUR}s — merging any delta it wrote" >> "$LOG"
fi
cat "$RUNOUT" >> "$LOG"
# AUTH DEATH DETECTOR, layer 1 — error strings, matched BROADLY. The Max OAuth cred expires
# ~monthly (Jun 27, Jul 26, Aug 20) and every claude -p consumer on this Mac dies (Botany, Plate,
# CyMCAT, Forge). LESSON from the Aug-20-29 outage: the CLI's wording CHANGES between versions
# ("Not logged in" → "401 OAuth access token has expired" → "OAuth session expired and could not
# be refreshed") — my exact-string match missed all of it. Match the STEMS (authenticat/oauth/
# /login); the no-delta guard keeps news prose from false-positiving (a real run writes a delta).
if [ ! -f data/_delta.json ] && grep -qiE "authenticat|not logged in|/login|oauth" "$RUNOUT"; then
  echo "$(ts) AUTH EXPIRED — claude -p signed out; EVERY claude-p daemon is down. Fix: claude → /login" >> "$LOG"
  osascript -e 'display notification "claude -p signed out — Botany, Plate + all claude-p daemons are DOWN. Fix: run claude, then /login" with title "Botany updater: AUTH EXPIRED" sound name "Basso"' 2>/dev/null || true
fi
# LIMIT DETECTOR, layer 1b — a usage cap is NOT an auth death, and the fix is different. Sep 21-22
# 2026: the Fable weekly cap was hit; claude -p died in ~3s with "You've reached your Fable 5 limit"
# for 11+ straight runs while layer 2 told him to /login. Capture the cause so layer 2 names it.
FAILCAUSE=""
if [ ! -f data/_delta.json ]; then
  CAP=$(grep -oiE "reached your [^.]*limit" "$RUNOUT" | head -1 | tr -d '"')
  if [ -n "$CAP" ]; then FAILCAUSE="usage cap ($CAP)"
  elif grep -qiE "authenticat|not logged in|/login|oauth" "$RUNOUT"; then FAILCAUSE="auth expired"; fi
fi
rm -f "$RUNOUT"

# 2. deterministic, authoritative merge. merge.py writes nothing until every output is built, but a crash inside its
#    write phase could still leave data/ half-merged: if data/ is clean (== HEAD) RIGHT BEFORE the merge, a failed
#    merge is undone with `git checkout -- data/`. Checked here, not at sweep start, so edits made by hand during the
#    25-min claude window (a manual `aa_sync.py --rebase`) are never wiped by that restore (Sep 28 skeptic).
#    Exit 3 = merged, but a section hit an unexpected error and was skipped: publish what landed, count it as a failure.
#    Exit 4 = the delta was unusable or not one item in it was accepted: a failed sweep for the streak (like no delta),
#    but aa_sync / market_sync still run and their changes still publish. (Round-2 skeptic: that case used to exit 0
#    and reset the streak while news, pulse and radar silently froze behind market_sync's daily "pushed".)
MERGED=0; PARTIAL=0; NOTHING=0
if [ -f data/_delta.json ]; then
  DATA_CLEAN=0
  if GS=$(git status --porcelain data/ 2>/dev/null) && [ -z "$GS" ]; then DATA_CLEAN=1; fi
  python3 scripts/merge.py >> "$LOG" 2>&1; MRC=$?
  if [ "$MRC" -ne 0 ] && [ "$MRC" -ne 3 ] && [ "$MRC" -ne 4 ]; then
    echo "$(ts) merge failed (exit $MRC)" >> "$LOG"
    if [ "$DATA_CLEAN" -eq 1 ]; then
      git checkout -q -- data/ 2>>"$LOG" && echo "$(ts) data/ restored to HEAD (it was clean right before the merge)" >> "$LOG"
    else
      echo "$(ts) data/ was not clean before the merge — left as is (nothing restored)" >> "$LOG"
    fi
    bump_streak "merge failed"
    exit 1
  fi
  [ "$MRC" -eq 3 ] && { PARTIAL=1; echo "$(ts) merge applied with a skipped section (see above)" >> "$LOG"; }
  [ "$MRC" -eq 4 ] && { NOTHING=1; echo "$(ts) merge landed nothing from the delta (see above)" >> "$LOG"; }
  [ "$MRC" -ne 4 ] && MERGED=1
  rm -f data/_delta.json
  # per-section freeze: merge.py lists, in scripts/.section_alarm, every section that has been offered items and
  # accepted none for 8 sweeps running (then every 8th). Other sections landing hide such a freeze from the streak.
  if [ -s scripts/.section_alarm ]; then
    while read -r SEC N; do
      [ -n "$SEC" ] || continue
      echo "$(ts) SECTION FREEZE: $SEC rejected $N sweeps running" >> "$LOG"
      osascript -e "display notification \"$SEC: every item rejected for $N sweeps. See scripts/update.log\" with title \"Botany updater: $SEC rejected $N sweeps running\" sound name \"Basso\"" 2>/dev/null || true
    done < scripts/.section_alarm
  fi
else
  echo "$(ts) no delta written" >> "$LOG"
fi

# 2b. AA-Index column = a straight copy of Artificial Analysis's live index (scripts/aa_sync.py): fills new models,
#     mirrors re-scores. It REFUSES (exit 2, writes nothing) when AA has re-versioned its index or when a run would drop
#     too many existing values (AA renamed models); either way this alarms once a day, and the exact one-line fix is in
#     the log. (Sep 23 2026: a hand-pinned v4.1 scale froze the leaderboard for weeks after AA moved to v4.3.)
#     Any OTHER failure (1 = page fetch/parse, 142 = the 180s watchdog below) is counted in scripts/.aa_fail_streak and
#     alarms after 8 in a row (a day): a changed page layout would otherwise freeze the column silently.
#     WATCHDOG: urlopen's timeout doesn't cover DNS; a hung aa_sync would hang this script, and launchd never starts a
#     second instance while one runs — every later sweep would silently stop, streak alarm included.
perl -e 'alarm shift @ARGV; exec @ARGV' 180 python3 scripts/aa_sync.py --sync >> "$LOG" 2>&1; ARC=$?
AAF=scripts/.aa_fail_streak
if [ "$ARC" -eq 2 ]; then
  if [ "$(cat scripts/.aa_rescale_alarm 2>/dev/null)" != "$(date +%F)" ]; then
    date +%F > scripts/.aa_rescale_alarm
    osascript -e 'display notification "AA numbers are frozen until you act." with title "Botany: AA sync refused — the one-line fix is in scripts/update.log" sound name "Basso"' 2>/dev/null || true
  fi
elif [ "$ARC" -eq 0 ]; then
  echo 0 > "$AAF"
else
  [ "$ARC" -eq 142 ] && echo "$(ts) aa-sync KILLED by 180s watchdog" >> "$LOG"
  AAN=$(( $(cat "$AAF" 2>/dev/null || echo 0) + 1 )); echo "$AAN" > "$AAF"
  if [ $(( AAN % 8 )) -eq 0 ]; then
    echo "$(ts) AA SYNC FAILING: $AAN sweeps in a row (last exit $ARC)" >> "$LOG"
    osascript -e "display notification \"$AAN sweeps in a row without an AA-Index sync (last exit $ARC). See scripts/update.log\" with title \"Botany: AA sync failing for a day (page layout changed?)\" sound name \"Basso\"" 2>/dev/null || true
  fi
fi

# 2c. Market truth (scripts/market_sync.py): every market row re-checked against Polymarket / Manifold / Kalshi's own
#     public APIs — closed, resolved and dead markets dropped, live odds refreshed, asOf stamped. Runs every sweep,
#     delta or not, AFTER aa_sync so a slow market API can never delay the leaderboard sync. It always exits 0 and caps
#     itself at 90s; the perl alarm is the outer guard (a DNS stall can outlast urlopen's timeout).
perl -e 'alarm shift @ARGV; exec @ARGV' 150 python3 scripts/market_sync.py >> "$LOG" 2>&1 \
  || echo "$(ts) market-sync exited non-zero — ignored, the sweep continues" >> "$LOG"

# 3. publish only if the dataset actually changed (git add also picks up new data/sources-archive/ months). The
#    streak resets only on a clean merge that then published, or had genuinely nothing to publish.
if ! git diff --quiet data/ 2>/dev/null || [ -n "$(git ls-files --others --exclude-standard data/ 2>/dev/null)" ]; then
  if git add data/ 2>>"$LOG" && git commit -q -m "auto-update $(date +%F)" >>"$LOG" 2>&1; then
    # WATCHDOG: a push stuck on the network would hang the script (and every later launchd run) the same way.
    perl -e 'alarm shift @ARGV; exec @ARGV' 120 git push -q 2>>"$LOG"; PRC=$?
    if [ "$PRC" -eq 0 ]; then
      echo "$(ts) pushed" >> "$LOG"
      if [ "$MERGED" -eq 1 ] && [ "$PARTIAL" -eq 0 ]; then reset_streak
      elif [ "$PARTIAL" -eq 1 ]; then bump_streak "merge skipped a section"
      elif [ "$NOTHING" -eq 1 ]; then bump_streak "merge accepted nothing from the delta"
      else bump_streak "${FAILCAUSE:-no delta (auth? hang?)}"; fi
    else
      [ "$PRC" -eq 142 ] && echo "$(ts) git push KILLED by 120s watchdog" >> "$LOG"
      echo "$(ts) push failed (committed locally)" >> "$LOG"
      bump_streak "push failed"
    fi
  else
    echo "$(ts) commit failed — nothing published" >> "$LOG"
    bump_streak "commit failed"
  fi
else
  echo "$(ts) no data changes" >> "$LOG"
  if [ "$MERGED" -eq 1 ] && [ "$PARTIAL" -eq 0 ]; then reset_streak
  elif [ "$PARTIAL" -eq 1 ]; then bump_streak "merge skipped a section"
  elif [ "$NOTHING" -eq 1 ]; then bump_streak "merge accepted nothing from the delta"
  else bump_streak "${FAILCAUSE:-no delta (auth? hang?)}"; fi
fi
echo "=== $(ts) done ===" >> "$LOG"
